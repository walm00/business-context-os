# The `.private/` Folder

**Local-only context that never leaves your machine.**

---

## What It Is

`.private/` is a top-level folder shipped by the BCOS install. It is:

- **Gitignored by default** — covered by `.gitignore` (`.private/`), so nothing inside is committed, pushed, or shared
- **Created on install** — `install.sh` makes the folder; `update.py` ensures it exists on every update
- **Pre-populated with starter templates** — `README.md` (explains the folder) and `release-guide.md` (a customizable release-workflow template)
- **Read by Claude** — same trust level as your active `docs/*.md`. Claude uses content here when relevant to your query
- **Never modified by framework updates** — `update.py` only copies starter files if they don't already exist; your edits and additions survive every update

Open `.private/README.md` after install for the in-folder version of this guide.

---

## What Goes Here

Use `.private/` for content you want Claude to know about but never want to commit:

- **Sensitive business notes** — M&A discussions, HR decisions, investor conversations, legal matters
- **Internal pricing logic** — margin calculations, deal terms, pricing experiments
- **Competitive intelligence** — research you want Claude to factor in but never publish
- **Personal SOPs** — your decision frameworks, operating principles, individual workflows
- **Draft strategy** — half-formed thinking that isn't ready for the team yet
- **Release notes / publish workflow** — anything specific to how *you* ship, not how the framework ships

---

## `.private/` vs `docs/_<custom>/` — Which to Use

Both are opted out of framework scanning. The difference is whether the content gets committed to git.

| | `.private/` | `docs/_<custom>/` |
|---|-------------|-------------------|
| Gitignored | **Yes** (by default) | No (committed unless you gitignore it yourself) |
| Skipped by framework scans | Yes | Yes |
| Read by Claude | Yes — high trust | Yes — but framework treats it as opt-out |
| Survives team sync | No (local only) | Yes (in repo) |
| Survives `git clone` to a new machine | **No — bring your own backup** | Yes |
| Use case | Sensitive, personal, never-share | Working drafts, team-shared but informal |

**Rule of thumb:** if accidentally committing it would be bad, put it in `.private/`. If you want your team to see it but don't want maintenance jobs nagging, use `docs/_<custom>/`.

See [`folder-conventions.md`](./folder-conventions.md) for the full underscore-folder story.

---

## Backup

`.private/` is **not in git**. That means:

- A fresh clone on a new machine has an empty `.private/` (just the starter templates)
- Nothing is recoverable from git history
- If you reformat, lose your laptop, or `rm -rf` the folder, the contents are gone

If anything in `.private/` matters, back it up yourself. Options:

- **Encrypted cloud sync** — Cryptomator, rclone with encryption, age-encrypted tarballs to S3
- **External drive** — periodic copy
- **Git, but encrypted** — `git-crypt` or `transcrypt` if you want it in version control without exposing it
- **Personal repo** — a separate private GitHub repo just for `.private/` content (push manually, don't symlink)

The framework deliberately doesn't pick a backup strategy for you. Treat `.private/` like any other local-only document folder you'd be sad to lose.

---

## Framework Guarantees

The framework promises three things about `.private/`:

1. **Will create it** — install + update both ensure the folder exists
2. **Will leave your files alone** — `update.py` ([line 481-490](../../../.claude/scripts/update.py)) only copies starter templates if they're missing. It never overwrites, modifies, or deletes anything you put in `.private/`
3. **Will never scan it** — no maintenance job (index-health, doc-lint, context-audit, daydream) looks at `.private/`. It's invisible to the framework's quality bar

What the framework does *not* guarantee:

- Encryption at rest — that's your filesystem's job
- Backup — see above
- Sync across machines — bring your own mechanism (cloud drive, encrypted file-sync tool, etc.) if you need that

---

## Quick Setup

After install (or `update.py`), `.private/` already exists with two starter files:

```
.private/
├── README.md           # what this folder is (mirrors this guide, in-folder)
└── release-guide.md    # template release workflow — customize or delete
```

Add files freely. Claude will read them when relevant. Nothing else to configure.

---

## See Also

- [`folder-conventions.md`](./folder-conventions.md) — full underscore-folder convention, including `docs/_<custom>/`
- [`maintenance-guide.md`](./maintenance-guide.md) — how the framework treats active context (everything `.private/` is exempt from)
