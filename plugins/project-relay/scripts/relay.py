#!/usr/bin/env python3
"""project-relay helper. Standard library only; Python 3.8+.

Subcommands
  config show | config set [--add-workspace P] [--remove-workspace P] [--group NAME] [--lang auto|zh|en] [--hook on|off]
  scan    [--root P ...] [--exclude SESSION_ID ...]   JSON: projects, cards, related transcripts, folders without a card
  digest  <transcript id or prefix> [--grep WORD] [--max N]   condensed text of one local transcript
  rules   <workspace root> [--lang zh|en]   insert/update the project-relay block in <root>/CLAUDE.md
  discover [--path P ...]   find folders that look like workspaces (cards / rules block / transcript cwds)
  doctor      environment and config check, with the suggested next step
  hook-stop   Stop-hook handler (reads hook JSON on stdin)

Everything runs locally. Transcripts are read from <claude config dir>/projects and never sent anywhere.
"""
import argparse
import glob
import io
import json
import os
import re
import sys
from datetime import datetime

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
CONFIG_PATH = os.path.join(CONFIG_DIR, "project-relay", "config.json")
TRANSCRIPT_GLOB = os.path.join(CONFIG_DIR, "projects", "*", "*.jsonl")
CARD = "PROJECT.md"
SKIP_DIRS = {"node_modules", "__pycache__", "venv", "dist", "build"}
DEFAULT_CONFIG = {"workspaces": [], "group": "", "lang": "auto", "hook": "on"}
BLOCK_START = "<!-- project-relay:start -->"
BLOCK_END = "<!-- project-relay:end -->"


# ---------- config ----------
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_PATH):
        try:
            cfg.update(json.load(open(CONFIG_PATH, encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    json.dump(cfg, open(CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def norm(p):
    return os.path.normcase(os.path.abspath(os.path.expanduser(p)))


# ---------- cards ----------
def read_card(path):
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="utf-8", errors="ignore").read()
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    meta["card"] = path
    meta["ids"] = re.findall(r"`([0-9a-f]{8})`", text)
    return meta


def list_folders(root):
    try:
        names = os.listdir(root)
    except OSError:
        return []
    return sorted(n for n in names
                  if os.path.isdir(os.path.join(root, n)) and not n.startswith(".") and n not in SKIP_DIRS)


# ---------- transcripts ----------
def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return ""


def load_transcripts():
    out = []
    for path in glob.glob(TRANSCRIPT_GLOB):
        first_user, cwds, chunks = "", set(), []
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("cwd"):
                    cwds.add(norm(d["cwd"]))
                t = text_of((d.get("message") or {}).get("content"))
                if not t:
                    continue
                chunks.append(t)
                if d.get("type") == "user" and not first_user and not t.lstrip().startswith("<"):
                    first_user = t.strip().replace("\n", " ")[:80]
        out.append({
            "id": os.path.basename(path)[:-6],
            "mtime": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
            "size_kb": round(os.path.getsize(path) / 1024),
            "first_user": first_user,
            "_cwds": cwds,
            "_text": "\n".join(chunks),
        })
    return out


def public(t, hits):
    return {"id": t["id"], "mtime": t["mtime"], "size_kb": t["size_kb"], "hits": hits, "first_user": t["first_user"]}


# ---------- scan ----------
def scan(roots, exclude):
    transcripts = [t for t in load_transcripts() if not any(t["id"].startswith(e) for e in exclude)]
    by_id = {t["id"]: t for t in transcripts}
    result = {"config": CONFIG_PATH, "roots": [], "projects": [], "folders_without_card": [],
              "transcript_count": len(transcripts)}

    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        result["roots"].append(root)
        folders = list_folders(root)
        cards = {n: read_card(os.path.join(root, n, CARD)) for n in folders}

        # A transcript belongs to a folder if it ran inside it, or mentions it often
        # (>= 5 times and >= 50% of its most-mentioned folder; overview chats mention everything a little).
        matches = {n: [] for n in folders}
        for t in transcripts:
            counts = {n: len(re.findall(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", t["_text"])) for n in folders}
            top = max(counts.values() or [0])
            for n in folders:
                in_cwd = any(c.startswith(norm(os.path.join(root, n))) for c in t["_cwds"])
                if in_cwd or (counts[n] >= 5 and counts[n] >= 0.5 * top):
                    matches[n].append(public(t, "cwd" if in_cwd else counts[n]))

        def related(names):
            seen, out = set(), []
            for n in names:  # transcripts listed on the card come first
                for pre in (cards[n] or {}).get("ids", []):
                    for tid, t in by_id.items():
                        if tid.startswith(pre) and tid not in seen:
                            seen.add(tid)
                            out.append(public(t, "card"))
            for n in names:
                for t in matches[n]:
                    if t["id"] not in seen:
                        seen.add(t["id"])
                        out.append(t)
            return sorted(out, key=lambda t: t["mtime"], reverse=True)[:8]

        projects = {}
        for n in folders:
            c = cards[n]
            if c is None:
                result["folders_without_card"].append({"root": root, "folder": n, "transcripts": related([n])})
                continue
            key = c.get("parent") or n
            p = projects.setdefault(key, {"root": root, "main": key, "members": [], "title": None,
                                          "updated": None, "card": None})
            p["members"].append(n)
            if not c.get("parent"):
                p.update(title=c.get("title") or n, updated=c.get("updated"), card=c["card"])
        for p in projects.values():
            if p["title"] is None:  # parent folder has no card: fall back to the member's card
                sub = cards[p["members"][0]]
                p.update(title=sub.get("title") or p["main"], card=sub["card"])
            p["paths"] = [os.path.join(root, m) for m in p["members"]]
            p["transcripts"] = related(p["members"])
            result["projects"].append(p)
    result["projects"].sort(key=lambda p: (p["root"], p["main"]))
    return result


# ---------- discover / doctor ----------
def count_cards(root):
    return sum(1 for n in list_folders(root) if os.path.isfile(os.path.join(root, n, CARD)))


def has_rules_block(root):
    p = os.path.join(root, "CLAUDE.md")
    return os.path.isfile(p) and BLOCK_START in open(p, encoding="utf-8", errors="ignore").read()


def discover(extra):
    """Find folders that look like project-relay workspaces: registered ones, given paths, and the working
    directories of local transcripts (plus their parents). A folder qualifies if it holds the rules block or
    at least one subfolder with a PROJECT.md card."""
    cfg = load_config()
    registered = {norm(w) for w in cfg.get("workspaces", [])}
    candidates = {}
    for p in list(cfg.get("workspaces", [])) + list(extra):
        candidates[norm(p)] = os.path.abspath(os.path.expanduser(p))
    for path in glob.glob(TRANSCRIPT_GLOB):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(r'"cwd"\s*:\s*"((?:[^"\\]|\\.)*)"', line)
                if m:
                    cwd = json.loads('"%s"' % m.group(1))
                    for c in (cwd, os.path.dirname(cwd), os.path.dirname(os.path.dirname(cwd))):
                        if c and os.path.isdir(c):
                            candidates.setdefault(norm(c), os.path.abspath(c))
                    break  # the first cwd of a transcript is enough
    found = []
    for key, root in sorted(candidates.items()):
        cards, block = count_cards(root), has_rules_block(root)
        if cards or block or key in registered:
            found.append({"root": root, "cards": cards, "rules_block": block, "registered": key in registered,
                          "exists": os.path.isdir(root)})
    # a workspace nested inside another qualifying one is usually just a project folder: drop it
    roots = [f["root"] for f in found if f["cards"] >= 2 or f["rules_block"] or f["registered"]]
    out = []
    for f in found:
        inner = any(norm(f["root"]).startswith(norm(r) + os.sep) for r in roots if norm(r) != norm(f["root"]))
        if not inner:
            out.append(f)
    return out


def doctor():
    cfg = load_config()
    checks = {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 8),
        "plugin_root": PLUGIN_ROOT,
        "templates_ok": all(os.path.isfile(os.path.join(PLUGIN_ROOT, "templates", f)) for f in
                            ("PROJECT.zh.md", "PROJECT.en.md", "workspace-rules.zh.md", "workspace-rules.en.md")),
        "config_path": CONFIG_PATH,
        "config_exists": os.path.isfile(CONFIG_PATH),
        "config": cfg,
        "transcripts": len(glob.glob(TRANSCRIPT_GLOB)),
        "workspaces": [{"root": w, "exists": os.path.isdir(w), "cards": count_cards(w),
                        "rules_block": has_rules_block(w)} for w in cfg.get("workspaces", [])],
    }
    if not cfg.get("workspaces"):
        checks["next"] = "no workspace registered: run `discover`, then `config set --add-workspace`"
    elif any(not w["exists"] for w in checks["workspaces"]):
        checks["next"] = "a registered workspace is missing on this machine: fix it with `config set`"
    elif not any(w["cards"] for w in checks["workspaces"]):
        checks["next"] = "workspaces have no cards yet: run the init-projects skill"
    else:
        checks["next"] = "ready: run the restore-projects skill"
    return checks


# ---------- digest ----------
def digest(prefix, grep, limit):
    paths = [p for p in glob.glob(TRANSCRIPT_GLOB) if os.path.basename(p).startswith(prefix)]
    if not paths:
        print("transcript not found: " + prefix)
        return
    out = []
    for line in open(paths[0], encoding="utf-8", errors="ignore"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = text_of((d.get("message") or {}).get("content")).strip()
        if not t or t.startswith("<"):
            continue
        if d.get("type") == "user":
            item = "U: " + t[:600]
        elif d.get("type") == "assistant" and len(t) > 200:
            item = "A: " + t[:1500]
        else:
            continue
        if grep and grep not in item:
            continue
        out.append(item)
    text = "\n\n".join(out)
    print(text[-limit:] if len(text) > limit else text)


# ---------- workspace rules ----------
def install_rules(root, lang):
    lang = "zh" if lang == "zh" else "en"
    block = open(os.path.join(PLUGIN_ROOT, "templates", "workspace-rules.%s.md" % lang), encoding="utf-8").read().strip()
    block = "%s\n%s\n%s" % (BLOCK_START, block, BLOCK_END)
    path = os.path.join(os.path.abspath(root), "CLAUDE.md")
    old = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    if BLOCK_START in old and BLOCK_END in old:
        new = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), lambda _: block, old, flags=re.S)
        action = "updated"
    else:
        new = (old.rstrip() + "\n\n" if old.strip() else "") + block + "\n"
        action = "appended" if old.strip() else "created"
    open(path, "w", encoding="utf-8").write(new)
    print(json.dumps({"file": path, "action": action}, ensure_ascii=False))


# ---------- Stop hook ----------
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
REMIND = {
    "zh": "project-relay：这一轮改了 {names} 的文件，但没有更新项目卡。请把这轮的进度、遗留问题和下一步写进 {cards}"
          "（更新 updated 日期，在“相关对话”里补上本会话 ID 前 8 位）。确实不需要更新的话，说明原因后结束即可。",
    "en": "project-relay: this turn edited files in {names} but did not update the project card. Record this turn's "
          "progress, open issues and next steps in {cards} (bump `updated`, add this session's 8-char id under related "
          "conversations). If no update is warranted, say why and stop.",
}


def edited_paths(transcript_path):
    entries = []
    for line in open(transcript_path, encoding="utf-8", errors="ignore"):
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    start = 0
    for i, d in enumerate(entries):  # the turn begins at the last real user message (not a tool result)
        if d.get("type") == "user" and text_of((d.get("message") or {}).get("content")).strip():
            start = i
    paths = []
    for d in entries[start:]:
        content = (d.get("message") or {}).get("content")
        if d.get("type") != "assistant" or not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in EDIT_TOOLS:
                inp = b.get("input") or {}
                p = inp.get("file_path") or inp.get("notebook_path")
                if p:
                    paths.append(p)
    return paths


def hook_stop():
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}
    cfg = load_config()
    if cfg.get("hook") == "off" or event.get("stop_hook_active") or not event.get("transcript_path"):
        print("{}")
        return
    roots = [os.path.abspath(os.path.expanduser(r)) for r in cfg.get("workspaces", [])]
    touched, updated = {}, set()  # normalized card path -> (folder name, card path as displayed)
    for p in edited_paths(event["transcript_path"]):
        ap_ = os.path.abspath(p)
        for r in roots:
            if not norm(ap_).startswith(norm(r) + os.sep):
                continue
            rel = ap_[len(r) + 1:].split(os.sep)
            if len(rel) < 2:  # a file directly in the workspace root
                continue
            own = os.path.join(r, rel[0])
            card = read_card(os.path.join(own, CARD))
            if card is None:
                continue
            folder = os.path.join(r, card["parent"]) if card.get("parent") else own
            card_path = os.path.join(folder, CARD)
            if norm(ap_) in (norm(os.path.join(own, CARD)), norm(card_path)):
                updated.add(norm(card_path))
            else:
                touched[norm(card_path)] = (os.path.basename(folder), card_path)
    missing = [v for k, v in touched.items() if k not in updated]
    if not missing:
        print("{}")
        return
    lang = cfg.get("lang") if cfg.get("lang") in REMIND else "en"
    if cfg.get("lang") == "auto":
        lang = "zh" if any(re.search(r"[一-鿿]", c) for _, c in missing) else "en"
    reason = REMIND[lang].format(names=", ".join(sorted({n for n, _ in missing})),
                                 cards=", ".join(sorted({c for _, c in missing})))
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(prog="relay.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("config")
    c.add_argument("action", choices=["show", "set"])
    c.add_argument("--add-workspace", action="append", default=[])
    c.add_argument("--remove-workspace", action="append", default=[])
    c.add_argument("--group")
    c.add_argument("--lang", choices=["auto", "zh", "en"])
    c.add_argument("--hook", choices=["on", "off"])
    s = sub.add_parser("scan")
    s.add_argument("--root", action="append", default=[])
    s.add_argument("--exclude", action="append", default=[])
    d = sub.add_parser("digest")
    d.add_argument("id")
    d.add_argument("--grep")
    d.add_argument("--max", type=int, default=40000)
    r = sub.add_parser("rules")
    r.add_argument("root")
    r.add_argument("--lang", default="en")
    sub.add_parser("hook-stop")
    v = sub.add_parser("discover")
    v.add_argument("--path", action="append", default=[])
    sub.add_parser("doctor")
    a = ap.parse_args()

    if a.cmd == "config":
        cfg = load_config()
        if a.action == "set":
            ws = [w for w in cfg.get("workspaces", []) if norm(w) not in {norm(x) for x in a.remove_workspace}]
            for w in a.add_workspace:
                w = os.path.abspath(os.path.expanduser(w))
                if norm(w) not in {norm(x) for x in ws}:
                    ws.append(w)
            cfg["workspaces"] = ws
            for k in ("group", "lang", "hook"):
                if getattr(a, k) is not None:
                    cfg[k] = getattr(a, k)
            save_config(cfg)
        print(json.dumps(dict(cfg, path=CONFIG_PATH), ensure_ascii=False, indent=2))
    elif a.cmd == "scan":
        roots = a.root or load_config().get("workspaces", [])
        if not roots:
            print(json.dumps({"error": "no workspace configured; run the init-projects skill first",
                              "config": CONFIG_PATH}, ensure_ascii=False))
            return
        print(json.dumps(scan(roots, a.exclude), ensure_ascii=False, indent=1))
    elif a.cmd == "digest":
        digest(a.id, a.grep, a.max)
    elif a.cmd == "rules":
        install_rules(a.root, a.lang)
    elif a.cmd == "discover":
        print(json.dumps(discover(a.path), ensure_ascii=False, indent=1))
    elif a.cmd == "doctor":
        print(json.dumps(doctor(), ensure_ascii=False, indent=1))
    elif a.cmd == "hook-stop":
        try:
            hook_stop()
        except Exception:
            print("{}")  # a broken reminder must never block the user's session


if __name__ == "__main__":
    main()
