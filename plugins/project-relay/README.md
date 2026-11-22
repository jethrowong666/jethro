# project-relay

> 中文说明在下方 · [Chinese below](#中文说明)

Pick up any project where the last session left off — in another session, on another account or machine, or in another AI tool.

## The problem
Your projects live on disk, but their context lives in chat sessions. After you switch accounts or machines, archive old sessions, or hand a project to Codex or Gemini, the sidebar is empty, or an old session still "remembers" an outdated state and redoes or overwrites work.

## How it works
1. **A card per project.** Each project folder gets a `PROJECT.md`: what it is, current status, outputs, open issues, next steps, project rules, related conversations. The card on disk is the source of truth, not any single chat.
2. **Workspace rules.** A marked block in the workspace `CLAUDE.md` tells every session to read the card before working and update it afterwards. `AGENTS.md`-style tools can follow the same file.
3. **One-command sidebar rebuild** (Claude Code desktop app). `restore-projects` opens one session per project, filed under one sidebar group, skipping projects that already have a session. Each new session reads its card, reports where things stand, and waits.
4. **A reminder.** A Stop hook notices when a turn edited files in a carded project without updating its card, and asks Claude to update it once.

## Skills
| Skill | What it does |
|---|---|
| `init-projects` | Register a workspace, write the rules block, draft cards for every folder from its files and your local conversation history |
| `restore-projects` | Rebuild the sidebar: one session per project, grouped, duplicates skipped |
| `project-card` | Update the current project's card (the Stop hook points here) |

## Install
**The easy way: send Claude one message** (Claude Code desktop app, Code tab):
> Install project-relay from https://github.com/jethrowong666/jethro and restore my projects

Claude follows [INSTALL.md](INSTALL.md): installs or updates the plugin, finds your workspace (from folders that already hold project cards), and rebuilds the sidebar. On a first-time setup it drafts the cards instead.

**Manually:**
```
/plugin marketplace add jethrowong666/jethro
/plugin install project-relay@jethro
```
Then say "set up project relay" (first time) or "restore my projects" (after switching accounts or machines).
To try a local copy without installing: `claude --plugin-dir /path/to/project-relay`.

**Same machine, different account?** Plugins and their config live in your local Claude config folder, not in your account, so the plugin is usually still installed: just say "restore my projects".

## Requirements
- Python 3.8+ on PATH as `python3` or `python` (standard library only)
- Claude Code. Rebuilding the sidebar needs the **desktop app**. In the terminal CLI, `restore-projects` lists projects and `claude --resume` commands instead.

## Privacy
Everything runs locally. The helper script reads your local transcripts (`~/.claude/projects`) only to find which conversations belong to which project; nothing is uploaded. Cards drafted from transcripts should be reviewed before you share or commit them. Cards must never contain secrets.

## Config
`~/.claude/project-relay/config.json` (or under `CLAUDE_CONFIG_DIR`):
```json
{ "workspaces": ["/path/to/workspace"], "group": "Projects", "lang": "auto", "hook": "on" }
```
Edit it with `python3 scripts/relay.py config set --add-workspace <path> --group <name> --lang auto|zh|en --hook on|off`.
Other helpers: `doctor` (environment check and suggested next step), `discover` (find workspaces from local conversation history), `scan`, `digest <conversation id>`.

## Development
`python -m unittest discover -s tests` runs the offline tests; `claude plugin validate .` checks the manifest.

## Limitations
- Tested on Windows 11 so far; macOS and Linux are untested.
- The Stop hook only sees Edit / Write / NotebookEdit; files changed by shell commands are not detected.
- Matching old conversations to projects is heuristic (working directory or how often a folder is mentioned). Review drafted cards.
- Whether `claude --resume` can continue a conversation from another account has not been verified.

---

## 中文说明

让任何一个项目都能“接着上次干”：换会话、换账号、换电脑，或者换成别的 AI 工具都行。

**解决什么问题**：项目文件在磁盘上，项目的来龙去脉却在聊天会话里。换了账号或电脑、归档了旧会话、把项目交给 Codex / Gemini 之后，左侧列表空了；或者老会话还“记得”过时的进度，接着干就会重做或覆盖已经做好的东西。

**怎么做到**
1. **每个项目一张项目卡 `PROJECT.md`**：是什么、做到哪、成品在哪、遗留问题、下一步、本项目规矩、相关对话。进度以卡为准，不以某段聊天为准。
2. **工作区规矩**：在工作区的 `CLAUDE.md` 里写入一段带标记的规矩：动手前先读卡，干完更新卡。
3. **一键重建左侧会话**（Claude Code 桌面 App）：`restore-projects` 给每个项目开一个会话，归进同一个分组，已有的跳过。新会话先读卡、汇报现状，然后等你指示。
4. **收尾提醒**：这一轮改了某个项目的文件却没更新它的卡，Stop 钩子会请 Claude 补上（每轮只提醒一次）。

**三个 skill**：`init-projects`（首次配置、补卡）、`restore-projects`（重建左侧会话）、`project-card`（更新当前项目的卡）。

**安装**：最简单的办法是在 Claude 桌面 App 的 Code 页发一句话：

> 安装 https://github.com/jethrowong666/jethro 里的 project-relay 并恢复我的项目

Claude 会按 [INSTALL.md](INSTALL.md) 来做：安装或更新插件，从本机旧对话里认出放项目卡的工作区，然后重建左侧会话；如果是第一次用，就先帮你起草项目卡。
也可以手动安装，命令见上方 Install。装好后第一次说“初始化项目”，以后换号或换电脑说“恢复项目”。
**同一台电脑换号**：插件和配置存在本机的 Claude 配置目录里，不跟账号走，通常还装着，直接说“恢复项目”就行。

**隐私**：全部在本机运行。脚本读取本机对话记录，只是为了判断哪段对话属于哪个项目，不会上传。根据对话记录生成的项目卡，分享或提交前请先过目。项目卡里不要写任何密钥。

**已知局限**：目前只在 Windows 11 上测过；钩子识别不到用命令行改的文件；旧对话和项目的对应关系是推断出来的，生成的卡需要人工核对；`claude --resume` 能否接着另一个账号的对话尚未验证。
