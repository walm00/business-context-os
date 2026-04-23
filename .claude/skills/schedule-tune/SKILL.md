---
name: schedule-tune
description: |
  Natural-language editor for .claude/quality/schedule-config.json. Users talk
  about maintenance scheduling in everyday language ("run audit twice a week",
  "turn off deep daydream", "switch dispatcher to 08:30") — this skill parses
  intent, validates against the schema, shows a concrete diff, asks for
  confirmation, and writes the change.

  WHEN TO USE:
  - User wants to change how often a job runs
  - User wants to enable / disable a job
  - User wants to add or remove an auto-fix ID from the whitelist
  - User wants to change the dispatcher's daily time
  - User wants to reset config to defaults
  - User asks "what's my current maintenance schedule?" (read-only query mode)

  DO NOT USE:
  - For actually running jobs (that's the `schedule-dispatcher` skill)
  - For onboarding first-time setup (that's `context-onboarding` Step 6)
category: maintenance
---

# Schedule Tune

## Purpose

Claude edits `schedule-config.json` on the user's behalf. Regular users shouldn't be editing JSON with specific schema rules — they describe what they want, Claude does the translation.

The skill is defensive: it validates every change, shows the exact before/after diff, and refuses to write anything malformed. If the user's intent is ambiguous, it asks a clarifying question rather than guessing.

---

## Preconditions

- `.claude/quality/schedule-config.json` must exist. If it does not, stop and say: *"No schedule config found. If you haven't set up BCOS scheduling yet, run `context-onboarding` Step 6. If you think config should exist, check you're in the right repo."*
- The file must parse as JSON. If malformed, stop and say: *"schedule-config.json is malformed. I can repair it from the template — want me to reset it to defaults?"* — if yes, copy from `.claude/quality/schedule-config.template.json`, strip `_comment` / `_about` fields, write.

---

## Supported intents

Recognise the user utterance and map to a structured edit.

### 1. Change a job's schedule

**Utterances:** *"run audit twice a week"*, *"change daydream to every 3 days"*, *"switch architecture review to quarterly"*, *"run index-health on weekdays only"*, *"audit on Tuesdays and Fridays"*

**Edit:** `jobs.{job}.schedule = <new value>`

**Value resolution:**
- Simple weekday → use shortcut (`"mon"`, `"tue"` etc.)
- "daily" / "every day" → `"daily"`
- "weekdays" / "Monday through Friday" → `"weekdays"`
- "weekly" alone → ambiguous, ask which day (default offered: current value if it's already a single weekday, else Monday)
- "twice a week" → ask which days (offer Tue+Fri default), resolve to `"tue,fri"` shorthand (if config supports comma-separated) or raw cron `"0 9 * * 2,5"`
- "N times a week" with N>2 → offer specific day set
- "every N days" / "every other day" → `"every-{N}d"`
- "monthly" → `"1st"` (default 1st of month)
- "quarterly" → raw cron `"0 9 1 */3 *"` (first of every 3rd month)
- "never" / "off" / "disable this" → `"off"` OR set `enabled: false` — ask user which they mean. Disabling via `enabled: false` keeps config; `"off"` in schedule also works but is less intuitive. Default to `enabled: false` unless user insists on schedule-based off.
- Raw cron string — accept as-is after validation

**Ambiguity rule:** if the natural-language time has more than one valid interpretation, use `AskUserQuestion` with specific options. Never guess.

### 2. Enable / disable a job

**Utterances:** *"turn off the deep daydream"*, *"disable architecture review"*, *"turn index-health back on"*

**Edit:** `jobs.{job}.enabled = false | true`

**Edge case:** if the user says "turn off X" and X is already off, say so and do nothing: *"daydream-deep is already disabled."*

### 3. Change the dispatcher time

**Utterances:** *"run the dispatcher at 08:30"*, *"move morning maintenance to 07:00"*

**This is TWO edits:**

1. Update `dispatcher.time_hint` in config (informational)
2. Update the actual scheduled task's cron via `mcp__scheduled-tasks__update_scheduled_task` — that's what actually moves the run

Derive the cron from the time: `"08:30"` → `"30 8 * * *"`. Use the existing task ID `bcos-{project}` (discover by listing tasks filtered for prefix `bcos-`).

If the scheduled task doesn't exist, the time_hint update is pointless — say: *"No bcos dispatcher task found for this repo. Want me to create one?"* (offers to invoke `context-onboarding` Step 6.)

### 4. Auto-fix whitelist changes

**Utterances:** *"stop auto-fixing trailing whitespace"*, *"enable auto-fix for broken cross-references"*, *"turn off all auto-fixes"*, *"add eof-newline to auto-fix"*

**Edit:** `auto_fix.whitelist += [id]` or `auto_fix.whitelist -= [id]`. Or `auto_fix.enabled = false` for "turn off all".

**Validation:** the fix ID must appear in `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md`. If user names an ID that doesn't exist, list the supported IDs and ask which one they meant.

### 5. Digest destination changes

**Utterances:** *"write the digest to a different file"*, *"stop writing the digest file"*

**Edit:** `digest.path` or `digest.write_file`.

**Validation:** `path` must be under `docs/` (we do not let users direct the digest elsewhere). If they try to set it outside `docs/`, refuse and explain.

### 6. Tuning parameters

**Utterances:** *"suggest less aggressively"*, *"wait 5 green runs before suggesting reduction instead of 3"*

**Edit:** `tuning.suggest_reduce_after_green_runs` (int ≥ 1), `tuning.suggest_increase_if_findings_trending_up` (bool).

### 7. Reset to defaults

**Utterances:** *"reset maintenance schedule to defaults"*, *"start over with the config"*

**Action:** copy `.claude/quality/schedule-config.template.json` → `.claude/quality/schedule-config.json`. Strip `_comment` / `_about` fields during copy.

**Always confirm before resetting.** User's current customisations are wiped.

### 8. Read-only query

**Utterances:** *"what's my maintenance schedule?"*, *"when does audit run?"*, *"is architecture-review enabled?"*

**Action:** read config, summarise in plain language. Do NOT modify anything. Do NOT ask "want me to change it?" — that's for the user to initiate.

Example output: *"Your current schedule: index-health daily, daydream-lessons Monday, daydream-deep Wednesday, audit-inbox Friday, architecture-review 1st of month. Dispatcher runs at 09:00 local. All jobs enabled."*

---

## The standard edit flow

Every change follows the same five-step pattern:

1. **Parse intent** — which section, which key, what new value
2. **Validate** — check against schema rules (see Validation Rules below)
3. **Propose** — show the diff in human-readable form
4. **Confirm** — use `AskUserQuestion` with Apply / Cancel (/ Change) options
5. **Write** — atomic replace, preserve `_comment` / `_about` fields, preserve unrelated keys

### The proposal format

Always show before→after, not just after. Use ✏️ for field edits, ✅ for enable, ❌ for disable, so the diff is scannable at a glance:

```
Proposed change to schedule-config.json:

  ✏️ jobs.audit-inbox.schedule:
    "fri"  →  "tue,fri"

No other changes.
```

Enable/disable example:

```
Proposed change to schedule-config.json:

  ❌ jobs.daydream-deep.enabled:
    true  →  false

No other changes.
```

If the change is on the scheduled task itself (time change):

```
Proposed changes:

  Config file:
    ✏️ dispatcher.time_hint:  "09:00"  →  "08:30"

  Scheduled task bcos-leverage:
    ✏️ cronExpression:  "0 9 * * *"  →  "30 8 * * *"

Both will be applied together.
```

### Confirmation is not optional

Always ask. Even for trivial changes. The user saying "apply" once is faster than the user reversing an unintended change.

Exception: read-only queries (intent #8). Those produce output with no confirmation step.

---

## Validation Rules

Reject any edit that violates these rules. Explain the rule when refusing.

### `schedule` field

Valid values:

- Literal: `"daily"`, `"weekdays"`, `"weekends"`, `"off"`
- Weekday: `"mon"`, `"tue"`, `"wed"`, `"thu"`, `"fri"`, `"sat"`, `"sun"`
- Comma-separated weekday list: `"mon,wed,fri"` (any non-empty subset)
- Day-of-month: `"1st"` through `"31st"`, or `"last"`
- Interval: `"every-Nd"` where N ≥ 1 (e.g. `"every-2d"`, `"every-14d"`)
- Raw cron: 5 whitespace-separated fields, parseable standard cron

Invalid: anything else. Empty strings, typos, non-existent days.

### `enabled` field

Must be `true` or `false`. Not 1/0, not strings.

### `auto_fix.whitelist` field

Each entry must be a known fix ID (defined in `auto-fix-whitelist.md`). Known IDs as of v1.2:

- `missing-last-updated`
- `frontmatter-field-order`
- `trailing-whitespace`
- `eof-newline`
- `broken-xref-single-candidate`

When a new fix ID is added to the framework, it becomes valid. Otherwise, reject unknown IDs with: *"'{name}' is not a known auto-fix ID. Supported: {list}."*

### `digest.path` field

Must start with `docs/`. Must end in `.md`. Must not contain `..` or absolute prefixes.

### `tuning` fields

- `suggest_reduce_after_green_runs` — integer, 1 ≤ N ≤ 30
- `suggest_increase_if_findings_trending_up` — bool

### Dispatcher cron (via MCP update)

When updating the scheduled task's cron:

- Must be a valid 5-field cron
- Hour must be 0-23
- If the user proposes a cron that would run more than once per day, refuse: *"Dispatcher is designed to run once daily. For multiple runs, use individual jobs with their own schedule fields instead."*

---

## Writing the config

Preserve the file's structure:

- Keep all `_comment` / `_about` fields in place
- Keep the key order stable
- Pretty-print with 2-space indentation
- Always end the file with a single trailing newline

Use an atomic write pattern: write to `schedule-config.json.new`, validate by re-parsing, rename over the original. If validation of the written file fails (shouldn't happen, but defensive), restore from the original and report the bug.

---

## Quick reference: common transformations

| User says                              | Config edit                                                    |
|----------------------------------------|----------------------------------------------------------------|
| "run audit on Tuesday instead of Friday" | `jobs.audit-inbox.schedule: "fri" → "tue"`                    |
| "run audit twice a week"               | ask which days → e.g. `"tue,fri"`                              |
| "disable daydream-deep"                | `jobs.daydream-deep.enabled: true → false`                     |
| "bring daydream-deep back"             | `jobs.daydream-deep.enabled: false → true`                     |
| "dispatcher at 8:30"                   | `dispatcher.time_hint: "09:00" → "08:30"` + cron update on task |
| "run index-health weekdays only"       | `jobs.index-health.schedule: "daily" → "weekdays"`             |
| "monthly architecture review"          | already default — no change (if already "1st")                 |
| "quarterly architecture review"        | `jobs.architecture-review.schedule: "1st" → "0 9 1 */3 *"`     |
| "stop auto-fixing whitespace"          | remove `trailing-whitespace` from `auto_fix.whitelist`         |
| "what's scheduled for Friday?"         | read-only: audit-inbox runs Fridays                            |

---

## Error reporting

When something goes wrong, say what, say why, offer a path forward:

- Unknown job name → list known jobs, ask which one
- Unknown fix ID → list known IDs
- Invalid schedule value → show the supported formats
- Config file missing → suggest onboarding or migration
- MCP update failed (time change) → revert config change, explain

Never write a partial edit. Atomicity matters — either all proposed changes apply, or none do.
