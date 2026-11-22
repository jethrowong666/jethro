"""Offline tests for scripts/relay.py. Run: python -m unittest discover -s tests

Builds a throwaway workspace and Claude config dir; never touches the real ones.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = os.path.join(os.path.dirname(HERE), "scripts", "relay.py")


def card(path, title, parent=None, ids=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = "title: %s\n" % title + ("parent: %s\n" % parent if parent else "")
    body = "\n".join("- `%s`: x" % i for i in ids)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n%supdated: 2026-01-01\n---\n\n# %s\n\n%s\n" % (fm, title, body))


class RelayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.ws = os.path.join(t, "ws")
        self.cfg = os.path.join(t, "cfg")
        card(os.path.join(self.ws, "alpha", "PROJECT.md"), "Alpha", ids=["aaaaaaaa"])
        card(os.path.join(self.ws, "alpha-old", "PROJECT.md"), "Alpha", parent="alpha")
        os.makedirs(os.path.join(self.ws, "beta"))
        os.makedirs(os.path.join(self.ws, ".hidden"))
        tdir = os.path.join(self.cfg, "projects", "x")
        os.makedirs(tdir)
        self.write_transcript(os.path.join(tdir, "aaaaaaaa-1111.jsonl"), [("user", "hello")])
        self.write_transcript(os.path.join(tdir, "bbbbbbbb-2222.jsonl"),
                              [("user", "work on beta " * 6), ("user", "alpha once")])
        self.env = dict(os.environ, CLAUDE_CONFIG_DIR=self.cfg, PYTHONIOENCODING="utf-8")
        self.run_relay("config", "set", "--add-workspace", self.ws, "--lang", "en")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write_transcript(path, items):
        with open(path, "w", encoding="utf-8") as f:
            for kind, payload in items:
                if kind == "user":
                    d = {"type": "user", "message": {"role": "user", "content": payload}}
                elif kind == "result":
                    d = {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}
                else:  # edit
                    d = {"type": "assistant", "message": {"content": [
                        {"type": "tool_use", "name": kind, "input": {"file_path": payload}}]}}
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    def run_relay(self, *args, stdin=""):
        p = subprocess.run([sys.executable, "-I", RELAY] + list(args), input=stdin, capture_output=True,
                           text=True, encoding="utf-8", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def hook(self, edits, active=False):
        tp = os.path.join(self.tmp.name, "t.jsonl")
        items = [("user", "previous turn"), ("Edit", os.path.join(self.ws, "beta", "old.txt")),
                 ("user", "this turn")]
        for e in edits:
            items += [("Write", e), ("result", "")]
        self.write_transcript(tp, items)
        out = self.run_relay("hook-stop", stdin=json.dumps({"transcript_path": tp, "stop_hook_active": active}))
        return json.loads(out)

    # ---- scan ----
    def test_scan(self):
        d = json.loads(self.run_relay("scan"))
        self.assertEqual([f["folder"] for f in d["folders_without_card"]], ["beta"])
        (p,) = d["projects"]
        self.assertEqual(p["title"], "Alpha")
        self.assertEqual(sorted(p["members"]), ["alpha", "alpha-old"])
        self.assertEqual([t["id"][:8] for t in p["transcripts"]], ["aaaaaaaa"])  # from the card
        beta = d["folders_without_card"][0]["transcripts"]
        self.assertEqual([t["id"][:8] for t in beta], ["bbbbbbbb"])  # mentioned 6 times

    def test_scan_exclude(self):
        d = json.loads(self.run_relay("scan", "--exclude", "aaaaaaaa"))
        self.assertEqual(d["projects"][0]["transcripts"], [])

    # ---- discover / doctor ----
    def test_discover_unregistered(self):
        self.run_relay("config", "set", "--remove-workspace", self.ws)
        tp = os.path.join(self.cfg, "projects", "x", "cccccccc-3333.jsonl")
        with open(tp, "w", encoding="utf-8") as f:  # a past session that ran inside a project folder
            f.write(json.dumps({"type": "user", "cwd": os.path.join(self.ws, "alpha"),
                                "message": {"content": "hi"}}) + "\n")
        found = json.loads(self.run_relay("discover"))
        self.assertEqual([os.path.normcase(f["root"]) for f in found], [os.path.normcase(self.ws)])
        self.assertEqual(found[0]["cards"], 2)
        self.assertFalse(found[0]["registered"])

    def test_doctor(self):
        d = json.loads(self.run_relay("doctor"))
        self.assertTrue(d["python_ok"] and d["templates_ok"])
        self.assertTrue(d["next"].startswith("ready"))
        self.run_relay("config", "set", "--remove-workspace", self.ws)
        self.assertIn("no workspace", json.loads(self.run_relay("doctor"))["next"])

    # ---- rules ----
    def test_rules_idempotent(self):
        path = os.path.join(self.ws, "CLAUDE.md")
        open(path, "w", encoding="utf-8").write("# Mine\nkeep me\n")
        self.run_relay("rules", self.ws, "--lang", "en")
        self.run_relay("rules", self.ws, "--lang", "zh")
        text = open(path, encoding="utf-8").read()
        self.assertTrue(text.startswith("# Mine\nkeep me"))
        self.assertEqual(text.count("project-relay:start"), 1)
        self.assertIn("项目卡", text)

    # ---- Stop hook ----
    def test_hook_reminds(self):
        r = self.hook([os.path.join(self.ws, "alpha", "main.py")])
        self.assertEqual(r.get("decision"), "block")
        self.assertIn("alpha", r["reason"])
        self.assertNotIn("beta", r["reason"])  # previous turn is ignored

    def test_hook_card_updated(self):
        self.assertEqual(self.hook([os.path.join(self.ws, "alpha", "main.py"),
                                    os.path.join(self.ws, "alpha", "PROJECT.md")]), {})

    def test_hook_satellite_points_to_parent(self):
        r = self.hook([os.path.join(self.ws, "alpha-old", "x.py")])
        self.assertIn(os.path.join("alpha", "PROJECT.md").lower(), r["reason"].lower())
        self.assertEqual(self.hook([os.path.join(self.ws, "alpha-old", "x.py"),
                                    os.path.join(self.ws, "alpha", "PROJECT.md")]), {})

    def test_hook_ignores(self):
        self.assertEqual(self.hook([os.path.join(self.ws, "alpha", "main.py")], active=True), {})
        self.assertEqual(self.hook([os.path.join(self.ws, "CLAUDE.md")]), {})          # workspace root
        self.assertEqual(self.hook([os.path.join(self.ws, "beta", "x.py")]), {})       # no card
        self.assertEqual(self.hook([os.path.join(self.tmp.name, "elsewhere.txt")]), {})  # outside
        self.assertEqual(json.loads(self.run_relay("hook-stop", stdin="not json")), {})

    def test_hook_off(self):
        self.run_relay("config", "set", "--hook", "off")
        self.assertEqual(self.hook([os.path.join(self.ws, "alpha", "main.py")]), {})


if __name__ == "__main__":
    unittest.main()
