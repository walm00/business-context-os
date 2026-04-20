# Changelog

All notable changes to CLEAR Context OS will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

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
