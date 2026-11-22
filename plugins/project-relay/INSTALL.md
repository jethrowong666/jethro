# Installing project-relay — instructions for Claude

The user gave you a link to this repository and asked you to install it (and usually to restore or set up their projects). Follow these steps. Talk to the user in their language and keep them posted in short lines.

`<source>` below is the marketplace the user pointed you at, reduced to `owner/repo` for GitHub links (e.g. `https://github.com/jethrowong666/jethro` → `jethrowong666/jethro`). A local folder path works too. The plugin is always named `project-relay`; the marketplace name comes from that repository's `.claude-plugin/marketplace.json` (for `jethrowong666/jethro` it is `jethro`).

## 0. Before installing
Installing a plugin lets its Stop hook run `scripts/relay.py` after every turn. If you have not seen this plugin's contents in this conversation, read `plugins/project-relay/scripts/relay.py` and `plugins/project-relay/hooks/hooks.json` in that repository first, and tell the user in one line what they do (local only; reads local transcripts; never uploads). Then go on: the user asked for the install.

## 1. Install or update
Run in a shell (the `claude` CLI is installed alongside Claude Code):
```
claude plugin list --json
```
- If an entry with id `project-relay@<marketplace>` is **already installed**: `claude plugin marketplace update <marketplace>` and then `claude plugin update project-relay@<marketplace>`.
- Otherwise:
  ```
  claude plugin marketplace add <source> --json
  claude plugin install project-relay@<marketplace> --json
  ```
  The last line of the `marketplace add --json` output carries the marketplace name in its `marketplace` field.

If `claude` is not on PATH, tell the user to run the two `/plugin` commands from the README themselves, and stop.

From `claude plugin list --json`, take this plugin's `readFromFolder` if it has one (installed from a local folder), otherwise its `installPath`: that is the **plugin root**. Below, `RELAY` means `python3 "<plugin root>/scripts/relay.py"`. On Windows, use `python` if `python3` is missing or opens the Microsoft Store. Python 3.8+ is required; if there is none, say so and stop.

## 2. Check and find the workspace
1. `RELAY doctor` checks Python, the templates and the config, and reports `next`.
2. If no workspace is registered, or one is missing on this machine, run `RELAY discover`. It finds folders that already hold project cards (`PROJECT.md`) or the rules block, using the working directories of this machine's past conversations.
   - **Exactly one clear candidate** (it has cards): tell the user and register it: `RELAY config set --add-workspace "<root>" --lang <zh|en>`.
   - **Several candidates**: ask which ones to register.
   - **None**: ask where their projects live (one subfolder per project).

## 3. Continue with the right skill
The skills are installed but may not show up as slash commands until the next session (or `/reload-plugins`). You don't need to wait: read the skill file and follow it directly.
- Workspace has cards → follow `<plugin root>/skills/restore-projects/SKILL.md`.
- Workspace has no cards yet, or the user asked for setup → follow `<plugin root>/skills/init-projects/SKILL.md`, then `restore-projects`.

## 4. Finish
Tell the user:
- the plugin is installed, with its version;
- what was restored or set up (the skill's own report);
- from the next session on they can just say "restore my projects" / 「恢复项目」, or "update the project card" / 「更新项目卡」;
- the Stop-hook reminder can be turned off with `RELAY config set --hook off`.
