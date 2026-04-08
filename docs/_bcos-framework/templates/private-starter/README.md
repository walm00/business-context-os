# .private/ — Local-Only Context

This folder is **gitignored**. Nothing here is committed, pushed, or shared. Claude reads it, but it never leaves your machine.

## What goes here

- **Competitive analysis** — intelligence you want Claude to know but not publish
- **Pricing discussions** — internal pricing logic, margin calculations, deal terms
- **Personal SOPs** — your decision frameworks, operating principles, personal workflows
- **Sensitive business notes** — M&A, HR decisions, investor conversations, legal
- **Release guide** — your versioning and publishing workflow (if applicable)
- **Planning documents** — strategic thinking that isn't ready for the team yet

## How Claude uses it

Claude reads `.private/` files when they're relevant to your query. The folder is mentioned in CLAUDE.md as a trusted location — same trust level as active `docs/`.

## Rules

- **Never committed to git** — .gitignore covers the entire folder
- **Never modified by framework updates** — update.py copies starter templates but never overwrites your files
- **Your responsibility to back up** — since it's not in git, use your own backup method if this content matters
