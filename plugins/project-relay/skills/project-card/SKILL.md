---
name: project-card
description: Create or update the PROJECT.md card for the project being worked on - status, outputs, open issues, next steps, project rules, related conversations. Use when the user says "update the project card", "save progress", "hand this off", "更新项目卡", "记一下进度", "交接一下", or when project-relay's Stop hook asks for a card update.
---

# project-card

Keep the project's `PROJECT.md` current so the next session (any account, machine or tool) can continue from it.
Write in the card's existing language; for a new card, the user's language (templates in `<plugin root>/templates/`, the plugin root being two levels above this skill's base directory).

## Steps
1. Work out which project: the folder you have been working in, under a registered workspace. If the folder's card has `parent:`, update the parent's card instead. If it is unclear, ask.
2. Read the current card (if any) and what this conversation actually did: files changed, outputs produced, decisions the user made, problems left open.
3. Edit the card, don't rewrite it:
   - bump `updated` to today
   - **Current status**: replace what is outdated; keep it short; point to files by relative path; include versions or commit hashes when there are any
   - **Open issues**: remove what was resolved, add what is new
   - **Next steps**: refresh
   - **Project rules**: add any new standing instruction the user gave for this project
   - **Related conversations**: add this session's first 8 characters with a few words on what it did
4. Keep the frontmatter `title` unchanged unless the user asks; it is the sidebar session name.
5. No secrets (API keys, tokens, passwords) in the card, ever.
6. Tell the user in one line what changed in the card. If the project is a git repo, don't commit unless asked.
