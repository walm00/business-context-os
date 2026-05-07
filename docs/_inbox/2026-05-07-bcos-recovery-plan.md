---
title: BCOS-dev incident recovery plan — 2026-05-07
created: 2026-05-07
source: dispatch session (Cowork) + sibling Claude Code session (forensic audit)
topic: 80-file deletion incident, recovery plan, prevention checklist
status: ready-for-execution
routes_to: same
incident-id: bcos-2026-05-07-gitignore-deletion
---

# BCOS-dev incident recovery plan — 2026-05-07

## 1. Executive summary

This morning a `set_profile.sh`-style sync script for the bcos-dev private/dev → public/dev squash-merge workflow mutated `.gitignore` **before** rebuilding the index. The mutation reclassified ~80 untracked working-tree files as ignored, then a follow-on clean step removed them. Casualties include the substantial galaxy dashboard work, the bcos-galaxy/ and bcos-dashboard/ trees, several test files and fixtures, ecosystem JSONs, and a tranche of dispatcher session captures.

Two independent investigations have converged on the same picture. The destructive agent's own forensic audit (run in its own Claude Code session) confirmed which files were destroyed, which survived in git history, and which were never committed at all. The recovery investigation in this Cowork dispatch session confirmed that the `compassionate-rubin-e1965d` git worktree on disk holds a fresher galaxy.js (137KB vs the 40KB version tracked in git) plus the rest of the galaxy work — that worktree is the freshest source for the high-value tranche.

This document is a directive for the other agent (the one that caused the deletion) to execute against. **Do Option 2 — stage all recoverable artifacts into a `.recovery/` tree under the bcos-dev repo root, generate a manifest, then stop and wait for Guntis's review before promoting anything to canonical paths.** Do not run a direct restore script (Option 1). Direct restore risks clobbering files still in flight on disk and masks gaps that human review needs to see.

## 2. The confirmed picture — what survived where

| Source | What's there | Notes |
|---|---|---|
| `compassionate-rubin-e1965d` worktree (freshest) | galaxy.js 137KB; 9 galaxy files total; 12 dispatcher session captures dated 2026-04-07 → 2026-05-04; fresher ecosystem JSONs (state, learned-rules, blocklist, resolutions, lessons); context-index files; schedule-config.template; 4 test files | Highest-priority pull. Worktree is fresher than git HEAD for every overlapping file. Use `cp -p` to preserve mtimes. |
| Git history (this repo) | bcos-galaxy/ 8 files; bcos-dashboard/ 24 files; 7 `test_*.py`; fixtures/ 40 files; pre_commit_validate.sh; ecosystem JSONs (older); bcos-inventory; document-index; session-diary snapshot; daily-digest.json | Use only for items the worktree does not carry, OR where the worktree copy is unexpectedly older. Record source commit per file. |
| Sibling repos (e.g. agent-skill-auditor) | pre_commit_validate.sh (12 copies across siblings — pick newest mtime); schedule-config.json structural template; partial wiki fixtures | Cross-repo grep, then sort by mtime. Document source repo and mtime per file in the manifest. |
| `~/.claude/` (outside repo, untouched) | 6 memory files: MEMORY.md, feedback_pr-copywriting.md, feedback_publish-workflow.md, project_two-repo-setup.md, reference_release-log.md, user_guntis.md; Claude Code chat history | Not affected by the incident. Reference only — do not copy into `.recovery/` unless a derived artifact in the repo depends on them. |
| Already in repo (untracked, on disk, untouched) | All 6 `docs/_planned/` implementation plans: autonomy-ux-self-learning, lifecycle-sweep, wiki-headless-scripts, wiki-missing-layers, wiki-synthesis-pages, wiki-user-action-scripts | Survived the gitignore mutation. Verify mtimes before any operation that touches `.gitignore` again. |
| Only on the other workstation (Syncthing or manual sync) | `.private/` content (leverage, mempalace, paperclip, dashboard, audit notes); `.bcos-umbrella.json`; dispatcher session captures dated 2026-05-04 through 2026-05-07; this session's preflight tests (`tests/test_publish_preflight.py` + `tests/fixtures/preflight/`) likely absent there too | Requires Guntis to act from the other machine. See Section 5. |

## 3. Why Option 2, not Option 1

Staging into `.recovery/` means nothing on the canonical tree gets clobbered. Guntis reviews the manifest, sees which version of each file came from which source, and explicitly chooses what to promote. A direct restore script (Option 1) would write straight to canonical paths — that risks overwriting files still in flight, and silently glosses over gaps that human review needs to see. A two-phase staging-then-promote flow is slower by minutes and saves hours of "wait, which version did we end up with" archaeology later.

## 4. Execution sequence — directive for the other agent

Run these in order. Do not skip ahead. Stop at step 6.

### Step 1 — Create `.recovery/` staging tree

At bcos-dev repo root:

```bash
mkdir -p .recovery/{from-worktree,from-git,from-siblings}
```

Inside each subfolder, mirror the original repo-relative paths (e.g. `.recovery/from-worktree/bcos-galaxy/galaxy.js`). This makes the manifest's "original-path" column trivial to derive and the eventual promotion script trivial to write.

Add `.recovery/` to `.gitignore` immediately so the staging tree itself does not become a tracked artifact. Do this **before** any further operations that touch `.gitignore` — and stash untracked first per Section 7's prevention rule.

### Step 2 — Pull from `compassionate-rubin-e1965d` worktree

This is the freshest source. Pull each of the following into `.recovery/from-worktree/<original-path>` using `cp -p` so mtimes are preserved:

- `bcos-galaxy/` — full 9 files including galaxy.js (137KB)
- The 12 dispatcher session captures dated 2026-04-07 → 2026-05-04 (`.claude/quality/sessions/`)
- Ecosystem JSONs: state, learned-rules, blocklist, resolutions, lessons
- context-index files
- schedule-config.template
- 4 test files (enumerate by listing `tests/` in the worktree and diffing against current bcos-dev `tests/`)

Locate the worktree first via `git worktree list` to confirm path. Verify each file's size and mtime before copy and after copy.

### Step 3 — Pull from git history

For each item not retrieved from the worktree (worktree is fresher; do not double-pull), restore from git history into `.recovery/from-git/<original-path>`. Use one of:

```bash
git show <commit>:<path> > .recovery/from-git/<path>
# or
git restore --source=<commit> --worktree --staged -- <path>   # then move into .recovery/
```

Targets (only those NOT already pulled from the worktree):

- `bcos-dashboard/` — 24 files
- 7 `test_*.py` files not already in worktree
- `fixtures/` — 40 files
- `pre_commit_validate.sh` (compare against sibling-repo version in Step 4; keep both, let the manifest mark the winner)
- bcos-inventory, document-index, session-diary snapshot, daily-digest.json
- Older ecosystem JSONs only if the worktree did not have them

For each file, record the source commit SHA in the manifest.

### Step 4 — Cross-pull from sibling repos

Search siblings (start with agent-skill-auditor; widen if needed):

```bash
find ~/Documents/GitHub -name "pre_commit_validate.sh" -printf "%T@ %p\n" | sort -n
```

Take the newest-mtime copy. Repeat for `schedule-config.json` template and any wiki fixtures. Drop into `.recovery/from-siblings/<original-path>`. Record source repo and mtime per file in the manifest.

### Step 5 — Generate `.recovery/MANIFEST.md`

One row per recovered file. Group by category (galaxy / dashboard / tests / fixtures / ecosystem / dispatcher-sessions / scripts / misc). Columns:

| source | original-path | size | mtime | sha256 | suggested-action |

`suggested-action` is one of:
- `PROMOTE` — clearly the freshest, no conflict, copy straight to canonical path
- `SKIP` — superseded by another row in the manifest
- `NEEDS-MERGE` — exists at the canonical path already with different content, or two recovery sources disagree; needs human eyes

The manifest is the single artifact Guntis reviews. Make it readable — group by category, sort within each group by `suggested-action` then `original-path`.

### Step 6 — Stop. Wait for Guntis to review the manifest.

Do not promote anything to canonical paths in this run. Surface the manifest path and a one-paragraph summary (counts per category, counts per suggested-action). Wait for explicit go-ahead.

### Step 7 — Second pass (only after Guntis approves)

Generate a promotion script with a `--dry-run` flag. The script reads `.recovery/MANIFEST.md`, filters to rows marked `PROMOTE`, and copies from `.recovery/<source>/<original-path>` to `<original-path>` at the repo root. For `NEEDS-MERGE` rows, the script prints the diff and exits non-zero — those require Guntis's per-file decision.

Run `--dry-run` first. Print the full diff. Run for real only on Guntis's explicit say-so.

## 5. Other-workstation grab list

When Guntis is on the other machine, pull the following (Syncthing pull preferred; manual `rsync` over SSH as fallback):

- `.private/` directory in full — covers leverage, mempalace, paperclip, dashboard, audit notes
- `.bcos-umbrella.json`
- Dispatcher session captures dated 2026-05-04 through 2026-05-07 (under `.claude/quality/sessions/`)
- The preflight tests if they were written there (likely not — those were written this session on the affected machine; accept the loss if absent)

`rsync` sketch:

```bash
rsync -avzP --include='.private/***' --include='.bcos-umbrella.json' \
  --include='.claude/quality/sessions/2026-05-0[4-7]*' \
  user@other-workstation:/path/to/business-context-os-dev/ \
  /path/to/business-context-os-dev/
```

Stage these into `.recovery/from-other-workstation/` for symmetry with the rest of the manifest.

## 6. What's truly lost — accept, regen

Three items. Do not spend recovery cycles on them:

1. **Preflight tests written this session** (`tests/test_publish_preflight.py` + `tests/fixtures/preflight/`). Small surface, well under a day's work to rebuild. Use the actual incident as the canonical test case: a sync that mutates `.gitignore` while untracked files exist must fail preflight.
2. **May 4–7 dispatcher sessions on this machine.** Most of the signal already aggregated into the May audit reports. The session transcripts themselves are nice-to-have, not load-bearing.
3. **`.wake-up-context.md`.** Regenerable from current state, no semantic loss.

## 7. Prevention checklist — three changes before next time

1. **Stash untracked before any gitignore mutation.** The sync wrapper must run `git stash --include-untracked` before touching `.gitignore`, rebuild the index, then `git stash pop`. This single change kills the class of bug that produced today's incident. No other change in this list is as load-bearing as this one.
2. **Pre-flight gate on `.gitignore` writes.** Before any operation that mutates `.gitignore`, count untracked files. If the count exceeds a threshold (start at N=10), block and require an explicit `--allow-untracked-clean` flag. The script wants to be paranoid — let it be paranoid.
3. **Daily worktree snapshots, scheduled.** The `compassionate-rubin-e1965d` worktree existed by accident and saved galaxy.js. Make daily worktree snapshots a scheduled job, not luck. Keep at least 7 days of rolling snapshots; 30 days for tagged checkpoints.

## 8. Sources

- **This dispatch session's recovery investigation** (Cowork session, 2026-05-07) — confirmed `compassionate-rubin-e1965d` worktree contents, sibling-repo cross-references, and the `.recovery/` staging plan.
- **The destructive agent's forensic audit** — separate Claude Code session, 2026-05-07. Confirmed the gitignore-then-clean failure mode, enumerated the ~80 deleted files, and classified each as recoverable-from-git, recoverable-from-worktree, recoverable-from-sibling, or never-committed.
