---
name: init-projects
description: First-time setup for project-relay. Registers a workspace folder, writes the project-relay rules into its CLAUDE.md, and drafts a PROJECT.md card for every project folder from its files and past local conversations. Use when the user says "set up project relay", "init projects", "give my projects cards", "初始化项目", "给项目建项目卡", or adds a new workspace.
---

# init-projects

Set up a workspace so any session, account, machine or AI tool can pick up each project where the last one left off.
Talk to the user in their language. Write cards in the user's language (`templates/PROJECT.zh.md` for Chinese, `templates/PROJECT.en.md` otherwise).

**Helper script.** The plugin root is two levels above this skill's base directory. Below, `RELAY` means:
`python3 "<plugin root>/scripts/relay.py"`. On Windows, if `python3` is missing or opens the Microsoft Store, use `python`. The script needs only the Python standard library (3.8+).

## 1. Pick the workspace
- Run `RELAY doctor` and `RELAY discover` first. `discover` lists folders that already hold cards or the rules block, found through this machine's past conversations; offer those as suggestions.
- Ask which folder holds the projects (one subfolder per project), unless the user already said or exactly one suggestion obviously fits.
- Register it and the preferences:
  `RELAY config set --add-workspace "<folder>" --lang <zh|en|auto> --group "<sidebar group name>"`
  Suggest the group name 「我的项目」 for Chinese users, "Projects" otherwise. The Stop-hook reminder is on by default; mention `--hook off` turns it off.

## 2. Write the workspace rules
`RELAY rules "<folder>" --lang <zh|en>` creates or updates a marked block in `<folder>/CLAUDE.md`; text outside the block is kept. Tell the user it did this.
Ask whether they have personal preferences that apply to all projects (language, budget limits, preferred tools, things never to do). If so, add them to `<folder>/CLAUDE.md` **outside** the marked block, under a heading like "Personal preferences".

## 3. Scan
`RELAY scan --exclude <this session's id>` returns JSON: `projects` (folders that already have cards), `folders_without_card`, and for each, related local transcripts (`hits` = "card", "cwd", or a mention count).

If there are more than ~15 folders without a card, ask whether to card all of them or only some.

## 4. Draft a card for each folder without one
For each folder:
1. Look at it: list the directory; read README / CLAUDE.md / AGENTS.md / package manifests; for git repos, `git log --oneline -5` and `git status -s`; note outputs (names, sizes, dates).
2. If it has related transcripts, read the gist: `RELAY digest <id> --grep "<folder name>" --max 20000`. Prefer the most recent ones.
3. Write `<folder>/PROJECT.md` from the template. Keep it factual and short. Where you are unsure, write "to confirm" (or 「待确认」) instead of guessing. List the transcripts you used under related conversations (first 8 chars, in backticks).
4. If the folder is clearly a satellite of another project (old copy, asset store, second repo of the same product), write only a short card: frontmatter `title` equal to the main project's, plus `parent: <main folder name>`, and one line pointing to the main card.
5. Never copy API keys, tokens or passwords into a card.

Work through folders one at a time and keep the user posted in one short line per folder.

## 5. Report
A table: folder, title, new card / existing card, things marked "to confirm". Ask the user to skim the new cards.
If some project folders are git repos, mention that the new `PROJECT.md` is uncommitted and offer to commit it (don't push unless asked).
Finally suggest running `restore-projects` to put every project in the sidebar.
