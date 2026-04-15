---
name: schedule-migrate
description: |
  One-time migration helper for existing BCOS installs upgrading from v1.0 or
  v1.1 (five standalone scheduled tasks) to v1.2 (single dispatcher task).

  Invoked by `update.py` via the `.claude/MIGRATION-NEEDED.md` flag file. Also
  safe to invoke manually — detects whether anything needs migrating and exits
  silently if not.

  WHEN TO USE:
  - `.claude/MIGRATION-NEEDED.md` exists (automatic trigger from update.py)
  - User explicitly says "migrate my scheduled tasks" or "run schedule-migrate"

  DO NOT USE:
  - On fresh installs — there's nothing to migrate
  - For routine config changes (that's `schedule-tune`)
  - For daily maintenance runs (that's `schedule-dispatcher`)
category: maintenance
---

# Schedule Migrate

## Purpose

When BCOS moves from five standalone scheduled tasks to one dispatcher, existing installs need a controlled transition:

1. Discover which old tasks belong to this repo
2. Create the new `bcos-{project}` dispatcher
3. Seed `schedule-config.json` (preserving any enable/disable state from old tasks where possible)
4. Disable the old tasks (they won't be deleted — user removes them via UI when convenient)
5. Write a boundary entry to the diary
6. Delete the migration flag

**The skill is idempotent and silent when there's nothing to do.** Running it twice is safe. Running it on a fresh install that never had v1.x tasks is a one-line no-op.

---

## Preconditions

- The repo must have `docs/` and `.claude/quality/` (i.e. BCOS is installed)
- The `mcp__scheduled-tasks__list_scheduled_tasks` tool must be available (otherwise migration cannot proceed — report and exit)

No other preconditions. The skill does its own detection and exits cleanly if there's nothing to migrate.

---

## Step 1: Derive the project slug

The slug is the lowercased, hyphen-only form of the current repo's folder name. Examples:

- `C:\Users\name\Documents\GitHub\the-leverage-ai` → `leverage` (or `the-leverage-ai` — see below)
- `C:\Users\name\Documents\GitHub\tystiq` → `tystiq`
- `C:\Users\name\Documents\GitHub\project-nurture-trunk` → `nurture` (or `project-nurture-trunk`)

**There's ambiguity here.** A user who created old tasks via manual setup may have picked any short slug, not necessarily the folder name. We can't know for sure.

Strategy:

1. Compute candidates: the full folder name, common shortenings (strip `-ai`, `-trunk`, `the-`, `project-`, etc.)
2. List scheduled tasks via MCP
3. Look for any task matching patterns like `{candidate}-index`, `{candidate}-daydream`, `{candidate}-audit`, `{candidate}-architecture`, or the older variants (`{candidate}-daily-index`, `{candidate}-weekly-audit`, `{candidate}-monthly-architecture`, etc.)
4. If multiple candidates match tasks, show the user the detected groups and ask which one belongs to this repo. If only one matches, proceed automatically.

---

## Step 2: Detect old tasks

Known v1.0 / v1.1 task ID patterns (prefix + suffix):

| Suffix                | Maps to new job         |
|-----------------------|-------------------------|
| `-index`              | `index-health`          |
| `-daily-index`        | `index-health`          |
| `-daydream`           | `daydream-lessons`      |
| `-daydream-deep`      | `daydream-deep`         |
| `-weekly-audit`       | `audit-inbox`           |
| `-audit`              | `audit-inbox`           |
| `-deep-audit`         | `audit-inbox`           |
| `-weekly-health`      | `daydream-lessons`      |
| `-biweekly-daydream`  | `daydream-deep`         |
| `-monthly-deep-audit` | `audit-inbox`           |
| `-monthly-architecture` | `architecture-review` |
| `-architecture`       | `architecture-review`   |
| `-quarterly-architecture` | `architecture-review` |
| `-lessons-capture`    | (merge into `daydream-lessons`, discard as standalone) |

Match case-insensitively. For each match, record:

- Original task ID
- Original `enabled` state
- Original cron expression
- Mapped new-job name

If zero matches across all candidate slugs → output one line: *"No v1.x scheduled tasks found for this repo. Migration not needed."* Delete `.claude/MIGRATION-NEEDED.md` if it exists. Exit.

---

## Step 3: Confirm the new dispatcher's slug

The detected slug (from old task names) may not be the slug the user wants for their new dispatcher. Example: `the-leverage-ai` repo's old tasks use slug `clear`. The user probably prefers `leverage` for the new task, not `clear`.

Show detection + propose a slug:

```
Found 5 v1.x scheduled tasks for this repo:

  clear-daily-index            → index-health        (enabled)
  clear-monday-daydream        → daydream-lessons    (enabled, runs daily despite name)
  clear-wednesday-daydream     → daydream-deep       (enabled, runs daily despite name)
  clear-friday-audit           → audit-inbox         (enabled, runs daily despite name)
  clear-monthly-architecture   → architecture-review (enabled, runs daily despite name)

New dispatcher name:
  Default suggestion: bcos-leverage  (derived from folder name: the-leverage-ai)
  Old tasks used slug: clear
```

Use `AskUserQuestion` to get the slug:

- Question: "What should the new dispatcher task be called?"
- Options:
  - **bcos-{folder-derived}** — recommended, matches the repo folder (e.g. `bcos-leverage`)
  - **bcos-{detected}** — reuse the slug from old tasks (e.g. `bcos-clear`)
  - **Something else** — user types a custom slug

The "folder-derived" suggestion should be the most sensible stripping of the folder name (`the-leverage-ai` → `leverage`, `project-nurture-trunk` → `nurture`, etc.). If folder-derived and detected happen to be the same, collapse to a single "looks right — proceed" option.

For custom slug: validate it matches `[a-z0-9][a-z0-9-]*` (kebab-case), reject otherwise with a polite re-ask.

### Confirm the full migration plan

Once slug is chosen, show the complete plan:

```
Migration will:
  1. Create a new scheduled task `bcos-leverage` running daily at 09:00
  2. Create .claude/quality/schedule-config.json from the template
  3. Disable the 5 old tasks (they will not be deleted — you can remove them from the UI when ready)
  4. Write a boundary entry to the diary
  5. Delete .claude/MIGRATION-NEEDED.md

Proceed?
```

Options: **Proceed** / **Show me more detail first** / **Cancel**.

If "Show me more detail" → print the full prompt text of each old task and the new config contents, ask again.

If "Cancel" → do nothing, do NOT delete the flag, exit. The flag remains so the next session will offer migration again.

---

## Step 4: Create the new dispatcher task

Use `mcp__scheduled-tasks__create_scheduled_task`:

- `taskId`: `bcos-{slug}`
- `cronExpression`: `0 9 * * *` (default — user can retune later via `schedule-tune`)
- `description`: `BCOS daily maintenance dispatcher for {slug}`
- `prompt`:

```
Working directory: {ABSOLUTE_REPO_PATH}

IMPORTANT: First ensure the working directory is {ABSOLUTE_REPO_PATH}. If the session is running elsewhere, cd there before starting.

Run the schedule-dispatcher skill to execute today's scheduled CLEAR maintenance. It will:
1. Read .claude/quality/schedule-config.json
2. Determine which jobs are scheduled for today based on day-of-week / day-of-month
3. Execute each job in sequence, appending one diary entry per job
4. Write a consolidated digest to docs/_inbox/daily-digest.md
5. Report a one-line summary

Keep output focused. If everything is green with no action items, say so in one line.
```

Fill `{ABSOLUTE_REPO_PATH}` with the repo's absolute path as seen on the current system.

If the MCP call fails, stop. Do NOT disable the old tasks. Report the error and leave the flag in place for retry.

---

## Step 5: Seed `schedule-config.json`

Copy `.claude/quality/schedule-config.template.json` → `.claude/quality/schedule-config.json`.

During the copy:

- Preserve all `_comment` / `_about` fields (user will read them)
- Preserve all default schedule values
- For each job in the new config, override `enabled` if the mapped old task was disabled. Example: if `leverage-daydream-deep` had `enabled: false`, set `jobs.daydream-deep.enabled: false` in the new config.
- Do NOT attempt to migrate the old tasks' cron expressions to the new schedule field — the old crons were daily-bugged (as in your local setup) and porting them would bake in the bug. Use the v1.2 defaults. The user can retune later via `schedule-tune`.

If `schedule-config.json` already exists (unusual — user manually created?), ask before overwriting: *"schedule-config.json already exists. Overwrite with defaults, or keep current?"*

---

## Step 6: Disable the old tasks

For each detected old task, use `mcp__scheduled-tasks__update_scheduled_task` to set `enabled: false`.

Do NOT delete the tasks — the MCP surface does not expose deletion, and leaving disabled tasks is harmless. Tell the user they can right-click → delete in the Claude Code UI when they want a clean list.

If an update call fails for any old task, log which one failed but continue with the rest. A partial disable is better than rolling back a successful new-task creation.

---

## Step 7: Write diary boundary entry

Append to `.claude/hook_state/schedule-diary.jsonl` (create the directory and file if missing):

```json
{"ts":"{ISO_NOW}","job":"_migration","verdict":"migrated","findings_count":0,"notes":"migrated from v1.x: disabled {N} old tasks, created bcos-{slug}. old tasks: {comma-separated list}"}
```

The `_migration` job name is a reserved sentinel — regular diary analyzers should ignore entries with underscore-prefixed job names.

---

## Step 8: Delete the migration flag

`rm .claude/MIGRATION-NEEDED.md` (or `os.remove` via the appropriate tool).

After this step, nothing on disk tells Claude migration is pending, so subsequent sessions will be silent on the topic.

---

## Step 9: Report completion

Tell the user in one short paragraph:

```
Migration complete.

  • Created: bcos-leverage (runs daily 09:00)
  • Disabled 5 old tasks — delete them via the UI when convenient
  • schedule-config.json seeded with defaults (preserving your enable/disable choices)
  • Diary boundary entry written

Tomorrow morning's run produces docs/_inbox/daily-digest.md. Want to test it now?
  → say "run today's maintenance now"
```

Offer the test run but don't invoke it automatically.

---

## Failure modes

| What went wrong                           | What to do                                                    |
|-------------------------------------------|---------------------------------------------------------------|
| MCP `list_scheduled_tasks` unavailable    | Report, leave flag, exit                                      |
| User chose "Cancel" at confirmation       | Do nothing, leave flag, exit (will offer again next session)  |
| New task creation failed                  | Report, leave flag + old tasks untouched, exit                |
| Config write failed after task creation   | Disable the new task so daily runs don't fire without config, report, leave flag |
| One old task failed to disable            | Continue, report the failed one at the end                    |
| Diary write failed                        | Warn but continue — diary is not critical                     |
| Flag deletion failed                      | Warn — next session will re-offer migration, but the skill will detect "already migrated" on step 2 and exit silently |

The idempotency from Step 2 is the safety net: if any step fails and the flag survives, re-running the skill finds no v1.x tasks (because they're already disabled — detection only counts enabled ones... wait, see below).

### Idempotency detail

Step 2 detects old tasks regardless of `enabled` state. So on a retry after partial success, the already-disabled old tasks would still be detected and the skill would want to "migrate" them again.

Fix: Step 2 also checks whether `bcos-{slug}` exists. If yes → treat as "migration already happened, mopping up". Skip task creation, skip config seeding. Only re-attempt disabling any old tasks that are still enabled. Then re-attempt flag deletion.

This keeps the skill safe to invoke repeatedly.

---

## When invoked manually with nothing to do

If the user says "migrate my schedules" but detection finds zero v1.x tasks AND no `bcos-{slug}` task yet (fresh install), redirect gently:

> *"No v1.x scheduled tasks to migrate here — this repo looks like a fresh BCOS install. For first-time setup, use `context-onboarding` Step 6 (it handles the dispatcher task creation). Or tell me 'set up scheduling' and I'll handle it."*

If the user says "migrate my schedules" but detection finds a `bcos-{slug}` task already running AND no leftover v1.x tasks:

> *"Migration has already completed for this repo. Dispatcher `bcos-{slug}` is running. To change anything, use natural language: 'run audit twice a week', 'turn off deep daydream', etc."*

No confusion, no accidental double-migration.

---

## Notes

- The skill is meant to be run ONCE per repo. After success, the flag file is deleted and the skill stays on disk (framework file) but is effectively dormant.
- If `update.py` for some reason re-syncs this skill, nothing breaks — next invocation detects the completed state and exits.
- The old tasks stay disabled on disk, not deleted. This is intentional — the user can delete them when they want (the MCP surface doesn't allow programmatic deletion anyway as of the v1.2 design date).
- The boundary diary entry is the ONLY persistent trace of migration in the repo. Subsequent daily runs continue from that point cleanly.
