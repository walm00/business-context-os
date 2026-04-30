# Gitignore Profiles

**One BCOS, two install styles. Pick the one that matches how you'll use the repo.**

---

## Why Profiles Exist

BCOS gets installed into very different kinds of repositories:

- **Shared / team repos** — BCOS lives alongside an app, a marketing site, or a multi-tenant codebase. The team uses BCOS for context but doesn't want runtime artifacts (per-user session diaries, accumulated lessons, daily digests) cluttering the codebase.
- **Personal knowledge repos** — BCOS *is* the repo. Knowledge artifacts are the entire point. You want session history, lessons, digests, and indexes synced across machines so nothing is lost when you switch workstations or restore from backup.

The same `.gitignore` can't serve both. Profiles solve it: one source of truth (a template), two rendered outputs.

---

## The Two Profiles

### `shared` (default)

**Use this when** BCOS is dropped into a repo that has its own purpose — an app codebase, a team workspace, a multi-tenant project.

**Behavior:** Runtime artifacts are gitignored, so the host codebase stays clean.

Files ignored *only* in this profile:
- `.claude/quality/sessions/*` — quality session data (per-user, per-machine)
- `.claude/quality/ecosystem/lessons.json` — accumulated lessons
- `docs/.session-diary.md` — session continuity notes
- `docs/.wake-up-context.md` — auto-generated snapshot
- `docs/document-index.md` — auto-generated index
- `docs/_inbox/daily-digest.md` — runtime maintenance output

### `personal`

**Use this when** the entire repo exists to be your knowledge base. It's private, will never be shared with collaborators, and exists primarily so you can sync context across machines and have a remote backup.

**Behavior:** Knowledge artifacts ARE tracked. Only secrets, OS noise, and machine-local files stay ignored.

What's still ignored in `personal`:
- Secrets (`.env*`)
- OS noise (`.DS_Store`, `Thumbs.db`, `__pycache__`, `*.swp`, etc.)
- IDE files (`.vscode/`, `.idea/`)
- Machine-local Claude state (`.claude/settings.local.json`, `.claude/hook_state/*`, `.claude/bcos-claude-reference.md`)
- Per-machine schedule config (`.claude/quality/schedule-config.json` — cron times differ per machine; only the `.template.json` ships)
- Sync tooling markers (`.stfolder/`)
- Private strategy folder (`.private/`)

---

## How It Works

**Single source of truth:** `.claude/templates/gitignore.template`

The template uses section markers:

```gitignore
# === ALWAYS ===            <- ignored regardless of profile
# === SHARED ONLY ===       <- only ignored when profile = shared
# === PERSONAL ONLY ===     <- only ignored when profile = personal
```

**Generator:** `.claude/scripts/set_profile.sh`

```bash
bash .claude/scripts/set_profile.sh           # show current profile
bash .claude/scripts/set_profile.sh shared    # render shared
bash .claude/scripts/set_profile.sh personal  # render personal
```

The script:
1. Reads the template
2. Strips the inactive profile block
3. Shows a diff of what will change
4. Writes `.gitignore` (with a "do not edit by hand" header)
5. Writes the chosen profile to `.claude/bcos-profile`
6. Prints next-step instructions

**State:** `.claude/bcos-profile` (single line — `shared` or `personal`)

This file is committed so the chosen profile is part of the repo's contract. Anyone cloning the repo gets the same `.gitignore` semantics.

---

## Switching Profiles

### Fresh install
`install.sh` generates a `shared` `.gitignore` automatically (preserving current behavior). The install summary tells you how to switch to `personal` if that's what you want.

### After install — going `shared` → `personal`

```bash
bash .claude/scripts/set_profile.sh personal
git status     # see what's newly tracked
git add .gitignore .claude/bcos-profile
# then review the newly-tracked files (diary, lessons, digests)
# and decide what you want to commit
```

**Heads-up:** Files that were previously gitignored may contain content you didn't realize was being recorded (session notes, lesson entries). Skim them before committing — once it's in git history, removing it cleanly is annoying.

### Going `personal` → `shared`

```bash
bash .claude/scripts/set_profile.sh shared
```

The script writes the new `.gitignore` and profile marker. **It does not `git rm` anything that was previously committed** — it just stops tracking *future* changes to those files. If you want them removed from the repo, do that manually:

```bash
git rm --cached docs/.session-diary.md
git rm --cached docs/.wake-up-context.md
# etc.
git commit -m "Untrack BCOS runtime artifacts (back to shared profile)"
```

Decide carefully — if you committed a year of session diary, deleting it loses history.

---

## Editing the Template

If you need to add or change a rule:

1. Edit `.claude/templates/gitignore.template` (not `.gitignore` directly)
2. Place the rule in the correct section (`ALWAYS` / `SHARED ONLY` / `PERSONAL ONLY`)
3. Re-run `set_profile.sh <current-profile>` to regenerate
4. Commit both files

If you edit `.gitignore` directly, your changes will be wiped the next time anyone runs `set_profile.sh` or `update.py`. The template is the source of truth.

---

## When Two Profiles Aren't Enough

If you find yourself wanting a third profile (e.g. `client-project` somewhere between the two), open an issue or extend the template with a new marker (`# === CLIENT_PROJECT ONLY ===`) and add the matching branch in `set_profile.sh`. The mechanism is intentionally simple — adding a third profile is a ~5-line change.

So far, two has been enough.
