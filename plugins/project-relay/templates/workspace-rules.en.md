## Project relay rules (project-relay)

Each subfolder of this workspace is a project. A project may be advanced by different sessions, accounts, machines
or AI tools in turn, so **the project card `PROJECT.md` on disk is the source of truth, not any one chat history.**

- **Before working**: read the project's `PROJECT.md` (and its `CLAUDE.md` / `AGENTS.md` if present). If it differs from what you remember, trust the card.
- **At the end of each turn that did real work** (produced output, changed code, made a decision): update the card: `updated` date, current status, open issues, next steps, and add this session's 8-character id under related conversations. Pure discussion needs no update.
- The frontmatter `title` is the sidebar session name; don't change it casually. A card with `parent:` marks a satellite folder whose status lives in the parent's card.
- When creating a new project folder, create its card too.
- Never put API keys, passwords or other secrets in a card.
- Don't advance the same project from two sessions at once.
- Sidebar sessions missing? Run `restore-projects` to rebuild them.
