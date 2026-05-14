# Changelog

All notable changes to CLEAR Context OS will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [1.5.0] — 2026-05-14

### Added — Multi-plugin permissions write contract

Pending v2.0.0 release. Three coordinated framework primitives implementing the [Multi-Plugin Permissions Write Contract](docs/_bcos-framework/architecture/permissions-write-contract.md):

- **`_bcosManagedPermissions` marker key** in `.claude/settings.json` —
  BCOS now tracks its slice of `permissions.allow` in a top-level marker key.
  Enables multi-plugin coexistence (bcos-umbrella will ship the parallel
  `_bcosManagedUmbrellaPermissions` slice in a coordinated release).
- **5-state reconciler** (`SettingsReconciler` in
  `.claude/scripts/_settings_reconciler.py`) — ADD / ADOPT / NOOP /
  RESPECT_USER_REMOVAL (tombstone) / REVOKE. Atomic temp+rename writes.
  `merge_settings_json` (now in `_settings_merge.py`) is marker-aware and
  preserves user-added rules. First run after upgrade silently ADOPTs every
  currently-shipped rule into the marker — zero disruption for existing
  installs.
- **`reset_permissions_marker.py` rescue command** — drops the marker so
  the next `update.py` re-ADOPTs from current `allow`. Use this if a
  tombstone has trapped a rule you want to re-enable.
- **STRUCTURAL_PATTERNS layer in `validate_permissions_catalog.py`** —
  recognizes pattern-class primitives (skill registration, owned write zones,
  dispatcher auto-commit, python-shim variants) so the validator doesn't
  flag every shipped skill/zone as a separate catalog drift. Reverse-drift
  dropped from 91 → 0 false positives.
- **Install/update preflight (advisory)** — `install.sh` and `update.py`
  now emit an `[ADVISORY]` line at the end of each run when permissions drift
  is detected. Never blocks install/update — surfaces the issue and points
  at the catalog SoT for resolution.
- **New `permissions-write-contract.md` architecture doc** — defines the
  five rules every plugin that writes Claude Code settings must follow
  (one writer per surface, marker-key namespacing, 5-state reconciler,
  additive across plugin boundaries, idempotency) + install/update/uninstall
  lifecycle + SDLC checklist.
- **Permission catalog gap fixes** (shipped without v2.0 cut, additive):
  `find_skills.sh:*` / `find_agents.sh:*` glob variants;
  `.github/scripts/validate_*.py` mirrors for ecosystem-manager Step 3;
  quoted-shim `"$CLAUDE_PROJECT_DIR/.claude/bin/python3"` form;
  `cat .claude/quality/last-daydream.txt`; `Skill(ecosystem-planner)`
  registration.
- **`record_daydream.py` helper** — replaces the daydream Step 6
  `echo "{date}" > .claude/quality/last-daydream.txt` shell redirect
  (which didn't fit the allowlist shape) with a covered Python script.
- **Wiki zone is now mandatory at install** — install.sh creates the full
  `_wiki/` structure including `.schema.d/` and `.gitkeep` markers on empty
  subdirectories; `update.py` calls `ensure_wiki_zone()` to backfill on
  upgrades from pre-wiki installs.
- **Wiki schedules default to daily** — `schedule-config.template.json`
  now ships `wiki-source-refresh`, `wiki-graveyard`, and `wiki-coverage-audit`
  on `daily` (matching BCOS's "starts daily, tune down once stable" pattern).
  Cheap when nothing's due.

### Changed

- **Fresh-install profile default flipped from `shared` to `personal`.**
  `install.sh` now renders `.gitignore` from the `personal` profile when
  no `.gitignore` exists in the target repo, matching the common BCOS
  use case (private, single-owner knowledge repo synced across
  workstations). Team / multi-tenant installs switch with
  `bash .claude/scripts/set_profile.sh shared`. Touches `install.sh`,
  `set_profile.sh`, `bcos_profile.py` (`DEFAULT_PROFILE`), and
  `gitignore-profiles.md`. Existing installs are unaffected — the
  default only applies when `.gitignore` is absent. Companion fix on
  the umbrella side (profile-aware `umbrella-onboarding` Step 5b +
  `.gitignore`-stripping reconciler) is tracked in
  [docs/_inbox/2026-05-13-umbrella-binding-tracking-profile-mismatch.md](docs/_inbox/2026-05-13-umbrella-binding-tracking-profile-mismatch.md).

## [1.4.0] — 2026-05-13

Dispatcher boundary + scheduled-task cwd verification. Five
coordinated phases from the 2026-05-13 master plan, shipped in
lock-step with `bcos-umbrella` 0.1.21 (umbrella-side preflight +
audit + permissions reconciler).

Motivation: 2026-05-13 surfaced three failure modes from
cross-repo operation by scheduled jobs — improvised scratch scripts
(`_xref_check.py`, `_scan_docs_tmp.py` written on the fly by two
different siblings), a sibling whose `Working directory:` pointed at
the umbrella host (blocking all downstream writes), and 6 of 16
registered siblings missing from the portfolio's `additionalDirectories`. This release closes the
node-side half of that loop (umbrella side ships separately).

### Added

- **Step 4a preflight** in `schedule-dispatcher/SKILL.md` (Phase 3).
  Before running each job, the dispatcher scans the job spec for
  cross-repo references: `../` segments, absolute paths outside
  `$CLAUDE_PROJECT_DIR` / `$HOME/.claude/` / `$BCOS_PY` / `/tmp/`,
  and known sibling-repo names harvested from `.bcos-umbrella.json`
  (fallback: path-only scan when umbrella-absent). On match: emit
  typed `node-job-cross-repo-reference` finding (category
  `bcos-framework`, verdict `red`, `finding_attrs = {job,
  offending_path, location}`), skip the job, log `verdict:error` to
  diary, continue.
- **`audit_node_configs.py`** (Phase 4). Portfolio-level cold-scan
  equivalent of Step 4a. Walks every BCOS-installed sibling under
  `--root`, scans each enabled job's `job-{name}.md` spec for
  cross-repo references, emits `{scanned, clean, violations}` JSON.
  Exit code always 0 — verdict in payload, advisory CI compatible.
  Live validation: 6 BCOS siblings, 0 violations.
- **Working-directory verification** in `context-onboarding`
  SKILL.md Step 6e (Phase 5). After confirming the scheduled task
  exists, Reads its SKILL.md prompt body and verifies the `Working
  directory: <value>` line matches `{REPO_PATH}` exactly. On mismatch:
  emit typed `scheduled-task-cwd-mismatch` finding (same shape as
  `bcos-umbrella`'s audit-time emission for dashboard dedupe), route
  through `bcos-framework-issues.jsonl`, AskUserQuestion to choose
  Recreate vs Leave-as-is. Closes the silent-write-block failure
  mode (a sibling's task pointed at the umbrella host instead of the
  sibling's own repo) at registration time.
- **`validate_permissions_catalog.py`** + CI hook (Phase 0).
  Bidirectional drift check between `permissions-catalog.md` and
  `.claude/settings.json`. Advisory (continue-on-error). Catches
  catalog rows with no matching allowlist entry AND allowlist
  entries with no catalog rationale row.
- **`_scheduled_task_cwd.py`** helper module. Pure-function
  `parse_working_directory()` + `paths_equivalent()`. Used by
  `context-onboarding` Step 6e to verify cwd without a runtime
  dependency on the umbrella plugin.
- **Three new typed finding_types** in
  `docs/_bcos-framework/architecture/typed-events.md` (schema 1.1.0
  additive; framework category 7 → 9):
  - `node-job-cross-repo-reference` — Phase 3.
  - `scheduled-task-cwd-mismatch` — Phase 5 (shared with umbrella).
  - All emitted with `category: "bcos-framework"`, acknowledge-only.
- **Boundary stamps** on every `job-*.md` reference doc
  (`**Boundary:** node — own-repo paths only`). Pairs the prose
  contract with the runtime preflight: a reader can verify
  enforcement by following the stamp's Step 4a reference.

### Coordination contracts (paired with bcos-umbrella 0.1.21)

| Surface | Side | Finding type | Attrs shape |
|---|---|---|---|
| BCOS dispatcher Step 4a | node | `node-job-cross-repo-reference` | `{job, offending_path, location}` |
| Umbrella dispatcher Step 4a | umbrella | `umbrella-job-write-outside-host` | `{job, write_target, location}` |
| BCOS context-onboarding Step 6e + umbrella audit | shared | `scheduled-task-cwd-mismatch` | `{sibling_id, expected_cwd, actual_cwd, task_name, platform}` |

`location` enum (`_run` / `_claude_step` / `spec_prose`) shared
across the node-side + umbrella-side preflight findings for renderer
parity.

### Tests

47 net new tests across the release:

- `test_audit_node_configs.py` (16) — TDD: tests written first.
  Includes regression coverage for the two false-positive classes
  surfaced during live smoke (`**Boundary:**` stamp line documenting
  the rule itself; markdown link URLs `[text](../path)` and inline
  backtick code in `## See also` sections).
- `test_finding_type_coverage.py` (3) — labels coverage gap that
  was already promised by `labels.py`'s docstring. Asserts every
  enum entry has a `FINDING_TYPE_LABELS` entry.
- `test_node_job_boundary_stamp.py` (3) — every
  schedule-dispatcher `job-*.md` carries the boundary stamp and the
  stamp references Step 4a.
- `test_context_onboarding_cwd_check.py` (19) — TDD. Step 6e prose
  contract (7), typed-events wiring (4), helper unit tests (8).
- `test_digest_typed_events.py` (+1 enum extension, baseline updated).

Plus 7 pre-existing brittle wiki/search tests unpinned to assert
against invariants instead of moment-in-time values (separate
commit; closes 6 failures + 1 error that had been carrying along).

Full discovery: 234 tests, all green.

### Lesson captured

- **Job specs using prose verbs (scan/check/validate) without a
  `_run` script invite Claude to improvise.** Convert to `_run` with
  a real script. Tags: `#dispatcher #boundary #scheduled-tasks`.
  Surfaced by 2026-05-13 incidents in two siblings where prose-only
  job specs led Claude to write scratch helpers (`_xref_check.py`,
  `_scan_docs_tmp.py`) on the fly instead of failing loudly.

## [1.3.0] — 2026-04-23

### Added

- **Comprehensive permission defaults for scheduled maintenance.** `.claude/settings.json` now ships a 179-entry allowlist covering every component the dispatcher and its jobs actually invoke: a catch-all prefix (`Bash(python .claude/scripts/:*)`, `Bash(python3 .claude/scripts/:*)`) plus explicit entries for every framework script (~35 of them, from `refresh_ecosystem_state.py` through every `run_wiki_*.py` runner and every `cmd_wiki_*.py` slash command); the narrow set of git commands the auto-commit step uses (`git status --porcelain`, `git rev-parse --abbrev-ref HEAD`, specific `git add` paths, `git commit -m bcos:*`); writes to every BCOS-owned path (`.claude/hook_state/**`, `.claude/quality/**`, `docs/_inbox/**`, `docs/_planned/**`, `docs/_archive/**`, `docs/_wiki/index.md`, `docs/_wiki/log.md`, `docs/_wiki/queue.md`, `docs/_wiki/.archive/**`, `docs/_wiki/raw/**`, `docs/_wiki/source-summary/**`, `docs/_wiki/pages/**`); and every dispatcher-invoked skill (`bcos-wiki`, `context-ingest`, `schedule-tune`, `learning`, `context-routing`, `clear-planner`, `context-mine`, `context-onboarding`, `core-discipline`, plus the existing six). Existing installs pick up the new entries via `update.py`'s additive `merge_settings_json`. Destructive permissions are deliberately NOT shipped (`git push`, `git reset`, `git rm`, blanket `Bash`/`Edit`/`Write`). The full mapping of permission → component lives in [`docs/_bcos-framework/architecture/permissions-catalog.md`](docs/_bcos-framework/architecture/permissions-catalog.md) — that's the SoT to keep in sync when adding new jobs. Closes the "almost no scheduled tasks fire, and the one that does gets stuck on a permission prompt" failure mode reported by an early adopter.
- **Cross-repo permissions installer** (`.claude/scripts/install_global_permissions.py`). When BCOS workflows span multiple repos (umbrella + sub-repos, portfolio mode, sibling-repo writes) the project-level allowlist isn't enough — cross-repo writes still prompt and stall the unattended session. The installer mirrors the project allowlist into `~/.claude/settings.json` (user-level, applies in every project on the machine) using the same additive merge logic as `update.py` — existing user-level rules are preserved, re-running is a no-op. Hooks are not mirrored (they're project-specific by design). Trust-model details and revocation guidance live in the catalog under "Cross-repo workflows".
- **Scanner skip rules for generated files** in `job-index-health.md`: `document-index.md` and any dot-prefixed file under `docs/` (`.wake-up-context.md`, `.session-diary.md`, `.onboarding-checklist.md`, `.portfolio-aggregate.md`) are excluded from frontmatter checks. Eliminates the most-repeated false positive across multi-repo installs. Also clarifies that `owner` is not a required frontmatter field.
- **`prune-sessions` and `prune-diary` on the default auto-fix whitelist.** Both scripts are deterministic, write only to their managed directories, and reversible via git. Documented in `auto-fix-whitelist.md`.
- **Opt-in auto-commit for generated artifacts.** New `digest.auto_commit` flag in `schedule-config.json` (default: `false`). When enabled, the dispatcher commits its own generated files (digest, index, diary, wake-up context, onboarding-checklist, ecosystem state) at the end of a run — but **only if every changed path in the working tree is on the allowlist**. Otherwise it skips entirely. Never branches, never pushes, never `git add .`. Mirrors the command-center update policy: stay out of the way if the user has in-progress work.

### Changed — Breaking

- **Removed pre-v1.2 migration tooling.** The `schedule-migrate` skill, `run_migration_detection` in `update.py`, the `MIGRATION-NEEDED.md` flag file, the CLAUDE.md migration-check block, and the one-time framework-folder archival (`docs/architecture` → `docs/_bcos-framework/architecture`) are all deleted. `update.py` is ~300 lines lighter.
- **Removed convention-file backfills** for `docs/.onboarding-checklist.md` and `docs/.session-diary.md` from `update.py`. Fresh installs get these from `install.sh`; existing post-v1.2 installs already have them.

### Upgrading from pre-v1.2

If you are still on a v1.0 / v1.1 install (five standalone scheduled tasks per repo rather than the single `bcos-{project}` dispatcher), **do not update directly to v1.3**. The migration helper shipped only in v1.2.x.

Two-step upgrade:

1. Check out BCOS at tag `v1.2.1` (or any `1.2.x`) and run `python .claude/scripts/update.py`. It detects your old tasks, writes `.claude/MIGRATION-NEEDED.md`, and the next Claude session offers to run `schedule-migrate`. Let it complete.
2. Update to v1.3 (or newer) via `python .claude/scripts/update.py` as usual.

Fresh installs (post-v1.2) — no action needed; you never had the old tasks.

### Migration (post-v1.2 users)

- Nothing required. Updates flow through `update.py` as usual.
- New `auto_commit` flag is `false` by default — flip it on with the `schedule-tune` skill ("turn on auto_commit") once you've had a week of clean runs.
- New whitelist entries (`prune-sessions`, `prune-diary`) apply to fresh installs only, since `update.py` does not overwrite your existing `schedule-config.json`. To adopt them on an existing install: `schedule-tune` → "add prune-sessions and prune-diary to the whitelist."

---

## [1.2.1] — 2026-04-20

### Added

- **Permission allowlist for auto-generated paths.** `.claude/settings.json` now ships a `permissions.allow` block covering only dispatcher-owned state files: `.claude/hook_state/**`, `.claude/quality/ecosystem/**`, `docs/.wake-up-context.md`, `docs/.session-diary.md`, `docs/.onboarding-checklist.md`, `docs/document-index.md`, `docs/_inbox/daily-digest.md`. Framework code paths (`.claude/skills/**`, `.claude/agents/**`, `.claude/scripts/**`, `.claude/hooks/**`, `.claude/settings.json`, `.claude/quality/schedule-config.json`) intentionally stay prompting — this prevents Claude from fixing skills or hooks mid-run and drifting from the BCOS repo standard.
- **`.claude/scripts/append_diary.py`** — dedicated helper that appends one JSON line to `.claude/hook_state/schedule-diary.jsonl`. Hard-coded target path (refuses any other write), creates `hook_state/` on first run, and pairs with the `Bash(python .claude/scripts/append_diary.py:*)` allowlist entry so diary writes never prompt.

### Changed

- **`schedule-dispatcher` SKILL** now writes diary entries via `append_diary.py` instead of `echo … >> schedule-diary.jsonl`. Raw redirects into `.claude/` triggered the sensitive-file approval prompt on every append; the helper avoids that and also handles first-run directory creation.
- **`update.py` `merge_settings_json`** is now additive for `permissions.allow` as well as hooks. Existing user rules are never removed or reordered; upstream rules are appended if absent. Status line: `settings.json: merged N new entries (hooks + permissions) from upstream.`

### Migration

- Existing installs pick the allowlist up on the next `python .claude/scripts/update.py` run. Nothing else to do.
- If you want the prompts gone before updating, the same entries can be mirrored into `~/.claude/settings.json` for an immediate, cross-project effect.

---

## [1.2.0] — 2026-04-15

### Changed — Breaking

- **Scheduled maintenance consolidated into a single dispatcher per repo.** v1.0 and v1.1 installs created five standalone scheduled tasks (`{slug}-index`, `{slug}-daydream`, `{slug}-daydream-deep`, `{slug}-audit`, `{slug}-architecture`). v1.2 replaces them with one task — `bcos-{slug}` — that runs daily, reads `.claude/quality/schedule-config.json`, and decides which maintenance jobs are due based on day-of-week / day-of-month. Output is one consolidated digest at `docs/_inbox/daily-digest.md`, one diary per repo.
- **Framework docs moved to `docs/_bcos-framework/`**. Paths `docs/architecture/`, `docs/guides/`, `docs/methodology/`, `docs/templates/` are relocated under `docs/_bcos-framework/`. `update.py` migrates existing installs automatically.

### Added

- **`schedule-dispatcher` skill** — single-task dispatcher that coordinates all maintenance jobs
- **`schedule-tune` skill** — natural-language config editor ("run audit twice a week", "turn off deep daydream")
- **`schedule-migrate` skill** — one-time v1.x → v1.2 migration helper; idempotent and silent when there's nothing to do
- **`schedule-config.template.json`** — default config shipped and synced by update.py
- **Five job references** under `.claude/skills/schedule-dispatcher/references/` — one per maintenance job, each with explicit auto-fix vs action-item rules
- **Auto-fix whitelist** — five conservative structural fixes allowed by default (missing `last-updated`, frontmatter field order, trailing whitespace, EOF newline, broken xref with single rename candidate). Everything else stays as an action item for user review
- **Schedule diary** — append-only JSONL at `.claude/hook_state/schedule-diary.jsonl`, gitignored, used for frequency-tuning suggestions
- **Daily digest** — consolidated morning report at `docs/_inbox/daily-digest.md`, overwritten each scheduled run. On-demand runs append sections instead of overwriting
- **Adaptive tuning (suggestion-only)** — dispatcher surfaces frequency-change suggestions based on diary patterns; never auto-modifies config
- **Interactive final step when attention is actually needed** — when a run produces action items, frequency suggestions, or an error, it ends with an `AskUserQuestion` presenting 2-4 concrete next-step options (walk through action items, show full digest, tune schedule, dismiss, etc.). Clean green runs skip the question and end with a one-line summary, so the Claude Code dashboard's "Awaiting input" status stays a meaningful priority signal rather than every run turning yellow.

### Migration

- Running `python .claude/scripts/update.py` on existing v1.0 / v1.1 installs scans `~/.claude/scheduled-tasks/` for known old task IDs matching the repo's project slug. If found (and no `bcos-{slug}` already exists), writes `.claude/MIGRATION-NEEDED.md` with detection details.
- Next session, Claude reads the flag and offers to run `schedule-migrate`. One prompt per session, never nags.
- Migration creates the new dispatcher, seeds `schedule-config.json` (preserving any enable/disable state from the old tasks), disables the old tasks (deletion is user-initiated via the UI), writes a boundary entry to the diary, and deletes the flag.
- **Fresh installs never trigger migration logic.** The migration path exists only for the narrow case of upgrading an existing BCOS repo.

### Fixed

- Eliminated the time-collision problem from multiple per-repo scheduled tasks running at the same minute.
- Eliminated the "weekly" / "monthly" naming drift where misconfigured crons caused tasks labelled weekly to actually run daily. The new dispatcher model has one cron per repo (the dispatcher itself); individual job cadence lives in config, not in task names.
- **`update.py` no longer deletes the old `docs/architecture/`, `docs/guides/`, `docs/methodology/`, `docs/templates/` folders during the framework-layout migration.** Previously the script called `shutil.rmtree` on those paths, which would have wiped any custom files a user happened to have dropped there. It now archives the whole folder to `docs/_archive/migrated-{name}-{date}/` for the user to review and clean up manually. Zero data-loss risk on upgrade.

### Notes for Contributors

- The dispatcher does NOT re-implement logic from `daydream`, `context-audit`, or `lessons-consolidate` — it orchestrates them. Updating those skills automatically improves dispatcher runs.
- Auto-fix whitelist additions must satisfy five safety criteria (see `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md`): no judgement calls, no content changes, idempotent, auditable, reversible by git.

---

## [1.1.0] — 2026-04-07

### Changed

- Version bump reflecting framework refinements since 1.0.0 (undocumented drift consolidated into this release's changelog retroactively).

---

## [1.0.0] — 2026-04-06

### Added

- **CLEAR Methodology** — 5 principles (Contextual Ownership, Linking, Elimination, Alignment, Refinement) with full documentation
- **10 Skills** — context-onboarding, context-ingest, context-audit, daydream, clear-planner, ecosystem-manager, lessons-consolidate, core-discipline, doc-lint, todo-utilities
- **1 Agent** — explore (read-only scanning delegate for context window management)
- **Folder architecture** — `_inbox/` (raw material), `_planned/` (polished ideas), `_archive/` (superseded)
- **Frontmatter enforcement** — PostToolUse hook validates YAML metadata on every doc edit
- **Document Index builder** — Python script auto-generates file inventory with metadata health
- **Self-learning system** — Lessons capture and consolidation across sessions
- **Scheduled maintenance** — Adaptive rhythms (building, active, steady, migration phases)
- **Architecture docs** — Developer documentation (system design, content routing, component standards, metadata system, maintenance lifecycle)
- **Brand strategy example** — Complete worked example with 8 data points (Acme Co)
- **Templates** — Data point, cluster, architecture canvas, table of context, current state, maintenance checklist
- **7 guides** — Getting started, defining context, maintenance, scheduling, migration, adoption tiers, non-technical users
