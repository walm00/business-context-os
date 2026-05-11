---
name: "Permissions Catalog"
type: reference
cluster: "BCOS Framework"
version: "1.0.0"
status: active
created: "2026-05-07"
last-updated: "2026-05-07"
---

# Permissions Catalog

## Ownership Specification

**DOMAIN:** Source of truth for the Claude Code permissions BCOS ships in `.claude/settings.json`. Maps every `permissions.allow` entry to the script, skill, file path, or workflow that depends on it.

**EXCLUSIVELY_OWNS:**
- The canonical list of permissions BCOS expects to be present at install time
- The mapping from each permission to the BCOS component(s) that need it
- The rationale for why each permission is shipped vs. left for user approval at runtime

**STRICTLY_AVOIDS:**
- The actual `settings.json` file (lives at `.claude/settings.json` — this catalog documents what's in it)
- Hook configuration semantics (see `docs/_bcos-framework/architecture/system-design.md`)
- User-level permissions in `~/.claude/settings.json` (out of scope — BCOS only owns project-level)

---

## Why this exists

Scheduled dispatcher runs spawn fresh Claude Code sessions with no human at the keyboard. Every permission prompt in those sessions becomes a stuck task. The fix is to ship the full set of permissions BCOS needs by default, so the dispatcher never has to ask.

This catalog is the SoT against which `.claude/settings.json` is maintained. When a new dispatcher job, script, or skill is added, the maintainer should:

1. Add the permission to `.claude/settings.json` (the live shipped file)
2. Add an entry here mapping the permission to the component
3. Confirm `update.py`'s `merge_settings_json` will propagate the new entry to existing installs (it does, additively, by default)

---

## Catalog

### Read access

| Permission | Why needed |
|---|---|
| `Read(**)` | All BCOS components read across the repo. Read-only is low-risk and avoiding piecemeal Read rules keeps the file legible. |
| `Glob` | Used by every job that walks `docs/`, `_wiki/`, `.claude/skills/`, etc. |
| `Grep` | Used by `context-search`, `analyze_crossrefs`, `validate_references`, audit jobs. |

### Python script invocations

A catch-all prefix lets the dispatcher run any framework script without per-script approval. The explicit list below the catch-all is for clarity and as a fallback if a future Claude Code release tightens prefix semantics.

| Permission | Why needed |
|---|---|
| `Bash(python .claude/scripts/:*)` | Catch-all: every framework script lives under `.claude/scripts/`. The dispatcher and jobs invoke them directly via `python <path>`. |
| `Bash(python3 .claude/scripts/:*)` | Same, for `python3` alias on systems that expose only python3. |

Explicit per-script entries (also shipped — redundant with the catch-all but defensive):

| Script | Used by |
|---|---|
| `append_diary.py` | dispatcher Step 4 (every job appends a diary entry) |
| `build_document_index.py` | `index-health`, `audit-inbox`, `architecture-review`, `daydream-deep`, `wiki-coverage-audit` |
| `generate_wakeup_context.py` | `index-health` Step 2 |
| `analyze_crossrefs.py` | `daydream-deep` Step 2 |
| `analyze_integration.py` | `architecture-review` Step 3 (`--ci` mode) |
| `prune_sessions.py` | auto-fix `prune-sessions` (whitelisted) |
| `prune_diary.py` | auto-fix `prune-diary` (whitelisted) |
| `refresh_ecosystem_state.py` | `index-health` Step 3, `architecture-review` Step 3, auto-fix `ecosystem-state-refresh` |
| `refresh_wiki_index.py` | `index-health` Step 4, `wiki-coverage-audit`, `wiki-stale-propagation`, auto-fix `wiki-index-refresh` |
| `lifecycle_sweep.py` | `lifecycle-sweep` job (preferred headless path) |
| `auto_fix_audit.py` | `auto-fix-audit` job (resolution-log auditor) |
| `context_index.py` | dispatcher Step 2.5 (regenerates `.claude/quality/context-index.json` once per run) |
| `context_search.py`, `context_bundle.py` | `context-routing` skill (`/context search`, `/context bundle`) |
| `promote_resolutions.py` | self-learning ladder (regenerates `learned-rules.json`) |
| `record_resolution.py` | resolution log writer for auto-fixes and headless clicks |
| `digest_sidecar.py` | dispatcher Step 7 (writes `daily-digest.json` for dashboard) |
| `consolidate_lessons.py`, `find_lessons.py` | `lessons-consolidate` skill |
| `bcos_inventory.py` | ecosystem state inventory |
| `load_zone_registry.py`, `load_task_profiles.py`, `validate_task_profiles.py` | shared loaders for context-routing, used by multiple skills |
| `validate_frontmatter.py`, `validate_references.py` | CI hooks and `index-health` |
| `wiki_schema.py` | every wiki job (`wiki-source-refresh`, `wiki-graveyard`, `wiki-coverage-audit`) validates schema before scanning |
| `wiki_failed_ingest.py` | `wiki-failed-ingest` job |
| `run_wiki_canonical_drift.py` | `wiki-canonical-drift` job |
| `run_wiki_coverage_audit.py` | `wiki-coverage-audit` job |
| `run_wiki_graveyard.py` | `wiki-graveyard` job |
| `run_wiki_source_refresh.py` | `wiki-source-refresh` job |
| `run_wiki_stale_propagation.py` | `wiki-stale-propagation` job |
| `cmd_wiki_*.py` | individual `bcos-wiki` slash commands (`/wiki init`, `/wiki lint`, etc.) |
| `update.py --dry-run`, `update.py --check` | safe to allow; the destructive `update.py` (no flag) requires explicit user approval each time |

### Bash utilities

| Permission | Why needed |
|---|---|
| `Bash(bash .claude/scripts/set_profile.sh:*)` | Switch gitignore profile (shared/personal) — used during onboarding and update |
| `Bash(bash .claude/skills/skill-discovery/find_skills.sh)` | Skill discovery during ecosystem checks |
| `Bash(bash .claude/agents/agent-discovery/find_agents.sh)` | Agent discovery during ecosystem checks |
| `Bash(mkdir -p .claude/hook_state:*)`, `Bash(mkdir -p .claude/quality/sessions:*)`, `Bash(mkdir -p .claude/quality/ecosystem:*)`, `Bash(mkdir -p docs/_inbox:*)`, `Bash(mkdir -p docs/_archive:*)`, `Bash(mkdir -p docs/_planned:*)`, `Bash(mkdir -p docs/_collections:*)`, `Bash(mkdir -p docs/_wiki:*)` | Directory creation for BCOS-managed paths, including dynamic subdirectories like clear-planner's session folders (`.claude/quality/sessions/{YYYYMMDD}_{HHMMSS}_{slug}/`). Each rule is scoped to a specific BCOS path; we deliberately do NOT ship blanket `Bash(mkdir:*)`. |
| `Bash(touch .claude/hook_state/.gitkeep)` | Maintain gitkeep markers |
| `Bash(chmod +x .claude/hooks/:*)`, `Bash(chmod +x .claude/scripts/:*)` | Make shell hooks executable on first install (Linux/macOS) |

**Skill author rule — use relative paths only.** The `mkdir` rules above only match if the skill invokes mkdir with a **relative** path from the project root (e.g. `mkdir -p .claude/quality/sessions/foo`). If a skill expands the path to an absolute form (`mkdir -p "$CLAUDE_PROJECT_DIR/.claude/quality/sessions/foo"` or a hardcoded `C:/Users/.../foo`) the rule will not match and the unattended session will hit a permission prompt. Skills should always use the relative path verbatim — Claude Code is rooted at the project directory, so relative paths Just Work. This is documented in clear-planner's Step 1 as a blocking instruction.

### Git operations

The dispatcher's auto-commit step (Step 7b) and the headless action handlers need a narrow set of git commands. We do NOT ship `git push` or any destructive operation.

| Permission | Why needed |
|---|---|
| `Bash(git status)`, `Bash(git status --porcelain)`, `Bash(git status --porcelain:*)` | Auto-commit clean-tree check |
| `Bash(git rev-parse --abbrev-ref HEAD)`, `Bash(git rev-parse:*)` | Branch allowlist check, current-commit detection |
| `Bash(git diff --stat HEAD)`, `Bash(git diff --stat:*)`, `Bash(git diff --name-only:*)` | Pre-commit summary, ecosystem audit |
| `Bash(git log --oneline:*)`, `Bash(git log -n:*)` | Recent-history checks for daydream + diff resolution |
| `Bash(git branch --show-current)` | Branch detection (publish.sh, dispatcher) |
| `Bash(git remote -v)` | Remote checks during update.py |
| `Bash(git add docs/document-index.md)` etc. (specific files) | Auto-commit Step 7b — only files in the ALLOWED list are addable |
| `Bash(git commit -m bcos:*)` | Auto-commit Step 7b — message always begins `bcos: daily maintenance ...` |

We deliberately do NOT ship: `git push`, `git reset`, `git checkout`, `git mv`, `git rm`, `git revert`. These need user confirmation each time. (The dispatcher never invokes them; headless actions that propose them are surfaced as one-click cards in the dashboard, not silent.)

### Edit/Write — files BCOS owns

| Path glob | Used by |
|---|---|
| `.claude/hook_state/**` | Diary file, hook state, session capture |
| `.claude/quality/ecosystem/**` | `state.json`, `lessons.json`, `resolutions.jsonl`, `learned-rules.json`, `learning-blocklist.json` |
| `.claude/quality/schedule-config.json` | `schedule-tune` skill writes here |
| `.claude/quality/context-index.json` | dispatcher Step 2.5 cache |
| `.claude/quality/bcos-inventory.json` | `bcos_inventory.py` |
| `.claude/quality/sessions/**` | session capture files |
| `.claude/quality/atlas-ignore.json` | atlas exclusion list |
| `docs/.wake-up-context.md` | `index-health` Step 2 (regenerated) |
| `docs/.session-diary.md` | hooks + `prune-diary` auto-fix |
| `docs/.onboarding-checklist.md` | `context-onboarding` skill |
| `docs/document-index.md` | `build_document_index.py` (regenerated) |
| `docs/_inbox/**` | `daily-digest.md`, `daily-digest.json`, captured material |
| `docs/_planned/**` | AI-generated plans synthesised from inbox material, transcripts, daydream output, etc. — usually framework-authored, not hand-typed |
| `docs/_archive/**` | archive-on-supersede moves |
| `docs/_wiki/index.md` | `refresh_wiki_index.py` (regenerated) |
| `docs/_wiki/log.md` | wiki ingest log |
| `docs/_wiki/queue.md` | wiki queue (mark-ingested fix) |
| `docs/_wiki/overview.md` | wiki overview metadata |
| `docs/_wiki/.archive/**` | archived wiki pages |
| `docs/_wiki/raw/**` | wiki raw captures |
| `docs/_wiki/source-summary/**` | external-reference summaries |
| `docs/_wiki/pages/**` | authored wiki pages |

We deliberately do NOT ship blanket `Edit(docs/**)` / `Write(docs/**)`. Canonical data points (`docs/*.md` at the root) are user-authored — every edit there should ask, even from inside the dispatcher. `docs/_collections/**` (verbatim evidence — invoices, contracts, transcripts) and `docs/_bcos-framework/**` (framework files, only changed via `update.py`) are also off-limits to dispatcher writes.

### Skills the dispatcher delegates to

| Skill | Used by |
|---|---|
| `schedule-dispatcher` | the cron task itself |
| `schedule-tune` | dispatcher Step 8 (apply suggestions), user requests |
| `context-audit` | `audit-inbox`, `architecture-review` |
| `context-ingest` | `lifecycle-sweep` (route-to-collection delegates to Path 5) |
| `context-routing` | `/context search`, `/context bundle` |
| `daydream` | `daydream-lessons`, `daydream-deep` |
| `doc-lint` | quality gates |
| `ecosystem-manager` | meta-skill operations |
| `lessons-consolidate` | `audit-inbox` (report-only) and direct invocation |
| `bcos-wiki` | `wiki-source-refresh` (refresh path), `lifecycle-sweep` (promote-to-wiki), all `/wiki *` commands |
| `learning` | self-learning ladder management |
| `clear-planner` | planning gates for non-trivial changes |
| `context-onboarding` | first-run flow |
| `context-mine` | conversation export ingestion |
| `core-discipline` | always-active skill discovery enforcer |

### Permissions NOT shipped — left for user approval at runtime

These tools are deliberately omitted from the shipped allowlist because:

- **`mcp__scheduled-tasks__*`** — depends on the user having the `scheduled-tasks` MCP server configured. Onboarding Step 6 explicitly tells the user to pick "Always allow" on the first prompt, which adds it to their personal allowlist.
- **`WebFetch`, `WebSearch`** — used during ingest and capture, but the URLs vary per request. Approving wholesale would be too broad. The user is normally at the keyboard during ingest.
- **`Bash(git push:*)`, `Bash(git reset:*)`, `Bash(git mv:*)`, `Bash(git revert:*)`, `Bash(rm:*)`** — destructive. The dispatcher never needs them. Headless action handlers that propose moves surface as one-click dashboard cards instead.
- **Generic `Bash`, `Edit`, `Write`** — too broad. We allowlist specifically.

---

## Cross-repo workflows — mirroring perms to user-level settings

The shipped `.claude/settings.json` is **project-local**: it applies only when Claude is rooted in this repo. When BCOS schedules and workflows span multiple repos (umbrella + sub-repos, portfolio mode, sibling-repo writes, syncing context across a multi-repo system), every cross-repo write hits a permission prompt and the unattended scheduled session stalls.

**Common cross-repo scenarios**

| Scenario | Reads | Writes |
|---|---|---|
| Umbrella reads sub-repos for context | `Read(**)` is unrestricted — works today | n/a |
| Workflow mines transcripts in repo A → drafts a `_planned/` doc in umbrella repo | works (cross-repo read + scoped write to umbrella's `_planned/**`) | works ONLY if umbrella has the same shipped allowlist |
| Workflow in umbrella writes back to a sub-repo's `_inbox/` | n/a | needs `Edit(docs/_inbox/**)` to be honored when session is rooted in the SUB-repo too |
| Multiple BCOS-installed repos all running their own dispatchers nightly | each read/write is local to its own repo | works today, no cross-repo perms needed |
| `/context search --cross-repo` or per-portfolio `auto_fallthrough` reading sibling repos' `context-index.json` | `Read(**)` unrestricted — works today, no permission setup needed | n/a (cross-repo retrieval is read-only) |

The first three scenarios are why we ship a mirror script. Cross-repo retrieval (`/context search --cross-repo`, `/context bundle --cross-repo`) is read-only and falls under existing `Read(**)` coverage — no new perms needed. Contract in [`cross-repo-retrieval.md`](cross-repo-retrieval.md).

**The fix: mirror this allowlist into `~/.claude/settings.json` (user-level, applies everywhere)**

```bash
python .claude/scripts/install_global_permissions.py            # apply
python .claude/scripts/install_global_permissions.py --dry-run  # preview first
```

The merge is **additive** — your existing user-level rules are never removed, replaced, or reordered. Re-running the script is a no-op once everything is in sync.

**What gets mirrored**: every entry under `permissions.allow` from the project settings. Hooks are NOT mirrored (they're project-specific by design).

**What this does to your trust model**: a rule like `Bash(python .claude/scripts/refresh_ecosystem_state.py:*)` at user level allows that command in **any** repo on this machine that has a script of that name. If you only check out BCOS-installed repos (the script names are unambiguous and BCOS-owned), this is exactly what you want. If you frequently check out untrusted repos that might shadow BCOS script names, prefer the project-level approach and run BCOS install in each repo separately. **Note:** we don't ship blanket `Bash`/`Edit`/`Write` or destructive git commands at any level, so even at user-level the surface stays scoped.

**To revoke later**: open `~/.claude/settings.json` and remove the rules you no longer want. The script never deletes anything from user-level settings.

### Cross-workstation portability

The mirror script handles cross-repo coverage on **one** machine. Three things still don't travel between workstations on their own:

| File / location | What it carries | Portability options |
|---|---|---|
| `~/.claude/settings.json` | Cross-repo permissions written by `install_global_permissions.py` | (a) Sync `~/.claude/` via Syncthing, OR (b) re-run the installer on each workstation |
| `~/.claude/scheduled-tasks/<task>.json` | Your actual cron/Task-Scheduler entries | (a) Sync `~/.claude/` via Syncthing, OR (b) re-run onboarding Step 6 per machine |
| `~/.claude/projects/<project>/sessions/` | Conversation history | Stays per-machine — large, machine-specific, not useful to sync |

**Recommended setup for a multi-workstation maintainer:**

1. Sync `~/.claude/` via Syncthing across your workstations (excluding `~/.claude/projects/*/sessions/` if you want to keep history machine-local).
2. Run `install_global_permissions.py` once on your primary machine — Syncthing carries the user-level rules to the others.
3. Run onboarding Step 6 per repo on the primary machine — Syncthing carries the scheduled-task entries.

**For a single-workstation user:** ignore the above; the mirror script is sufficient.

The same Syncthing pattern is what handles BCOS event-log files (`.claude/quality/ecosystem/resolutions.jsonl` etc.) which are deliberately gitignored on every profile — append-only logs across multi-machine workflows produce git merge conflicts that silently truncate the auditor's history. Syncthing them works; git tracking them does not.

---

## How to extend

Adding a new dispatcher job, script, or skill:

1. Determine the minimum set of new permissions needed (script invocation, write paths, sibling skill calls).
2. Edit `.claude/settings.json` and append to `permissions.allow`. Use a glob/prefix when reasonable, but stay narrow.
3. Add the corresponding rows to this catalog (under "Catalog" → matching subsection).
4. Run `python .claude/scripts/update.py --dry-run` against an existing install to confirm the additive merge picks up the new entries cleanly.
5. Document the new job/script in its reference file (`.claude/skills/schedule-dispatcher/references/job-*.md`) and link the permission rationale to this catalog if it's non-obvious.

---

## Maintenance signals

| Signal | What it means |
|---|---|
| Dispatcher runs report `verdict: error` with "permission denied" or "tool not allowed" | A new component slipped in without its permission. Find the offending tool call, add it here and to settings.json. |
| Existing install upgrades via `update.py` and the merge reports 0 new entries when this catalog has new rows | Either the rows were added but `.claude/settings.json` wasn't, or the rows were already present in the user's settings. Check both. |
| User reports "scheduled task didn't fire" or "stuck on permission prompt" | Open `~/.claude/projects/<project>/sessions/<latest>.jsonl` and grep for `permission` to see what was asked. Add it. |

---

## Related

- `.claude/settings.json` — the live shipped allowlist
- `.claude/scripts/update.py` — the merge function (`merge_settings_json`)
- `.claude/skills/context-onboarding/SKILL.md` — Step 6b-pre verifies these entries are present
- `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md` — separate concern (which fixes are silent), parallel to this (which permissions are shipped)
