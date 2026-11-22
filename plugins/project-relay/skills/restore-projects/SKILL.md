---
name: restore-projects
description: Rebuild the sidebar from project cards - one Claude Code desktop session per project in the registered workspaces, filed under one sidebar group, skipping projects that already have a session. Use after switching accounts or machines, when the sidebar is empty or missing projects, or when the user says "restore my projects", "list all projects in the sidebar", "恢复项目", "把项目列到左边", "同步项目会话".
---

# restore-projects

Project files, `PROJECT.md` cards and local transcripts live on disk; the desktop app's sidebar does not carry over between accounts or machines. This skill rebuilds the sidebar from the cards.
Talk to the user in their language.

**Helper script.** The plugin root is two levels above this skill's base directory. `RELAY` means `python3 "<plugin root>/scripts/relay.py"` (use `python` on Windows if `python3` is missing or opens the Microsoft Store).

**Tools.** This needs the desktop app's session tools: `mcp__ccd_session__start_session`, `mcp__ccd_session_mgmt__list_sessions`, `mcp__ccd_session_mgmt__get_session`, `mcp__ccd_sidebar__list_groups`, `mcp__ccd_sidebar__create_group`, `mcp__ccd_sidebar__move_sessions`. Load any deferred ones with a single ToolSearch call. If they don't exist (terminal CLI, IDE), skip steps 3–5: list the projects with their status and the `claude --resume <id>` command for each project's latest conversation instead.

## 1. Scan
- `RELAY doctor`. If no workspace is registered (new machine, fresh config) or a registered one is missing here, run `RELAY discover`: it finds folders holding project cards from this machine's past conversations. One clear candidate with cards → tell the user and register it (`RELAY config set --add-workspace "<root>"`); several → ask which; none → follow the `init-projects` skill instead.
- Get this session's id (`get_session` with `self`), then `RELAY scan --exclude <that id>`.
- If `folders_without_card` is not empty, say which folders have no card and offer to card them via `init-projects` first. Without cards they are skipped.

## 2. Plan
Get existing sessions with `list_sessions` (`limit: 200`). A project is **already present** if a non-archived session's title equals the card `title` exactly. Everything else is **missing**.
If more than 10 projects are missing, ask whether to open all of them or only the most recently updated ones (each session uses a little quota). Otherwise list the missing ones in one line and go on.

## 3. Start one session per missing project
Call `start_session` for each, all in one message:
- `initiation`: `"user_asked"`, `context`: `"fresh"`, `use_worktree`: `false`
- `title`: the card `title`, verbatim
- `name`: the main folder name, lowercase, only `a-z0-9-`, at most 24 characters
- `prompt` (fill in; write it in the user's language):
  ```
  This is the dedicated session for project "<title>". Folders: <each path in paths>.
  For now do one thing: read the project card <card> (plus CLAUDE.md / AGENTS.md in those folders if present) and report in two or three sentences: where it stands, the most important open issue, and the candidate next steps. Then stop and wait for the user.
  Do not modify, generate, render or delete anything.
  From now on, whenever you work here: re-read the card first and update it at the end (rules in the workspace CLAUDE.md).
  Past conversation details: RELAY digest <id> --grep <keyword>   (spell out the full RELAY command)
  Related conversations: <8-char ids from transcripts>
  ```
- `background`: "The user rotates between sessions, accounts, machines or tools; the project card on disk is the source of truth. This session was opened by project-relay's restore-projects to continue this project." Add the card's project rules in one or two lines. Never include secrets.

## 4. File them under one group
1. Group name: `group` from the config, or 「我的项目」 / "Projects" by language if empty. Find it with `list_groups`, create it with `create_group` if missing.
2. Sessions you just started are nested under this session and move with it: call `move_sessions` with `["self"]`.
3. Also move already-present project sessions that are not in the group. If an error says a session is nested, move its parent as the error suggests.

## 5. Report
A table: project, session (new / existing, as a link `[title](#<sessionId>)`), card `updated` date. Then one line: to continue an old conversation verbatim in a terminal, run `claude --resume <full id>` (ids are in the scan output).

## Notes
- This skill only reads files and opens sessions; it changes nothing in the projects.
- Running it twice is safe: present projects are skipped.
