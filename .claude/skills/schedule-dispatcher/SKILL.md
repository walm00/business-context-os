---
name: schedule-dispatcher
description: |
  Single-task dispatcher for CLEAR Context OS scheduled maintenance. Runs from
  the daily scheduled task, reads schedule-config.json, determines which jobs
  are due today, runs them in sequence, appends to the diary, writes a
  consolidated morning digest, and surfaces any frequency-tuning suggestions.

  WHEN TO USE:
  - Invoked automatically each morning by the `bcos-{PROJECT}` scheduled task
  - User says "run today's maintenance now" (manual dispatch)
  - User says "run the [job-name] job" (runs one job on demand, skips others)
category: maintenance
---

# Schedule Dispatcher

## Purpose

**One task, one report, one diary entry per job.** The dispatcher replaces the
previous model of 5 standalone scheduled tasks. It is invoked once per day,
reads configuration, and runs whichever maintenance jobs are due.

The dispatcher never decides on its own to change frequencies or skip jobs that
are due — it surfaces suggestions in the morning report and waits for the user
to approve a change (via the `schedule-tune` skill).

---

## Preconditions

Before doing anything, verify the working directory is a BCOS-enabled repo:

1. Confirm `.claude/quality/schedule-config.json` exists
2. Confirm `docs/` exists
3. Confirm `.claude/hook_state/` exists (create if missing — used for diary)

If any are missing, stop and report: "Dispatcher invoked outside a BCOS repo, or BCOS is not fully installed. Run `python .claude/scripts/update.py` first."

---

## Step 1: Read Configuration

Read `.claude/quality/schedule-config.json`. Validate required fields:

- `version` (string)
- `jobs` (object) — each entry must have `enabled` (bool) and `schedule` (string)
- `auto_fix.enabled` (bool)
- `auto_fix.whitelist` (array of strings)
- `digest` (object) — `write_file` (bool) and `path` (string)

If the config is malformed, STOP. Write a diary entry `dispatcher.error` with the validation failure, report to the user: "schedule-config.json is malformed — fix before the dispatcher can run. Use the `schedule-tune` skill to repair it."

---

## Step 2: Determine Today's Jobs

For each entry in `jobs`, decide if it should run today. Compare `schedule` against the current local date:

| `schedule` value   | Runs when                                          |
|--------------------|----------------------------------------------------|
| `"daily"`          | Every day                                          |
| `"mon"`..`"sun"`   | Only on that weekday                               |
| `"weekdays"`       | Monday through Friday                              |
| `"weekends"`       | Saturday and Sunday                                |
| `"1st"`, `"15th"`  | Only on that day-of-month                          |
| `"last"`           | Last day of the current month                      |
| `"every-Nd"`       | If N or more days since last successful diary run  |
| A raw cron string  | If today matches the cron's DOW and DOM fields     |
| `"off"`            | Never                                              |

If `enabled` is false, skip regardless of schedule.

**For on-demand dispatch** (user said "run the audit-inbox job"): skip this step, run only the named job.

Build an ordered list of jobs to run. Order: `index-health` first (always, if enabled), then the rest by config order. Put `architecture-review` last.

---

## Step 3: Read Recent Diary

Read up to the last 30 entries from `.claude/hook_state/schedule-diary.jsonl`.
Build a per-job summary:

- How many consecutive green runs?
- Findings trend (flat / rising / falling)?
- Last run timestamp per job?

This is used later for frequency-tuning suggestions. Do not change anything based on the diary — suggestions only.

---

## Step 4: Run Each Job

For each job in the list:

1. Load the job reference file from `.claude/skills/schedule-dispatcher/references/job-{name}.md`
2. Follow the reference's steps (they're self-contained, the dispatcher does not interpret them further)
3. Collect from each job:
   - `verdict`: one of `green`, `amber`, `red`, or `error`
   - `findings_count`: integer
   - `auto_fixed`: list of short strings describing fixes applied
   - `actions_needed`: list of short strings describing items requiring user judgement
   - `notes`: optional free-text (one short paragraph max)

4. Append a diary entry immediately after each job completes (do not batch — if the dispatcher crashes mid-run, we want the partial history). Use the helper script — it creates `.claude/hook_state/` on first run and matches the allowlisted command prefix so it never prompts:

```bash
python .claude/scripts/append_diary.py '{"ts":"2026-04-15T09:04:12","job":"index-health","verdict":"green","findings_count":0,"auto_fixed":[],"actions_needed":[],"duration_s":4}'
```

Do NOT use `echo ... >> .claude/hook_state/schedule-diary.jsonl` — raw redirects into `.claude/` trigger the sensitive-file approval prompt on every append.

If a job errors, catch the error, log `"verdict":"error"` with `"notes":"{short error message}"`, and continue to the next job. Do not stop the dispatcher on one job's failure.

Wiki jobs are first-class job references and use the same dispatcher contract:

| Job | Reference | Notes |
|-----|-----------|-------|
| `wiki-stale-propagation` | `references/job-wiki-stale-propagation.md` | Daily metadata scan for wiki pages whose `builds-on` sources changed after `last-reviewed`. |
| `wiki-source-refresh` | `references/job-wiki-source-refresh.md` | Weekly two-tier refresh check: HEAD-only quick check at `stale_threshold_days/4`, full refresh-must-rediscover at `stale_threshold_days`. |
| `wiki-graveyard` | `references/job-wiki-graveyard.md` | Monthly stale/orphan/archive-candidate scan. |
| `wiki-coverage-audit` | `references/job-wiki-coverage-audit.md` | Quarterly cross-zone coverage scan and permissive cluster-drift INFO reporting. |

---

## Step 5: Apply Auto-Fixes

The job references declare which fixes they're *allowed* to apply automatically. The dispatcher enforces policy:

1. Read `auto_fix.whitelist` from config
2. For each auto-fix proposed by a job, verify it's on the whitelist
3. If allowed → the job already applied it; log in diary
4. If NOT allowed → demote it to `actions_needed` in the report

See `references/auto-fix-whitelist.md` for the full list of recognised fix IDs and what each one does.

Never attempt a fix outside the whitelist, even if a job proposes it. That path is for user review.

---

## Step 6: Generate Frequency-Tuning Suggestions

For each job run today, check recent diary:

- **3 consecutive green runs with 0 findings** → suggest reducing frequency by one step:
  - `daily` → `weekdays`
  - `weekdays` → `mon` (or similar)
  - `mon` → `1st`
  - Any → `off` is never suggested
- **Findings trending up over last 3 runs** → suggest increasing frequency one step
- **Last run was `error`** → suggest investigating, not frequency change

Suggestions are just lines in the report. Prefix each line with 📉 for "reduce frequency" or 📈 for "increase frequency" so the direction is obvious at a glance. Format:

> 📉 `daydream-deep` has been green 3 runs running. Consider running it less often — tell me "run daydream-deep only on the 1st" and I'll update config.

> 📈 `audit-inbox` findings trending up over last 3 runs. Consider running it more often — tell me "run audit-inbox daily" and I'll update config.

Do NOT change the config automatically. The user must go through `schedule-tune`.

---

## Step 7: Write Consolidated Digest

If `digest.write_file` is true, write a single Markdown file to `digest.path` (default `docs/_inbox/daily-digest.md`). **Overwrite** — one file, always latest. History lives in the diary.

Structure of the digest:

```markdown
# Daily Maintenance Digest — {YYYY-MM-DD}

**Overall:** {🟢 green|🟡 amber|🔴 red} — {N} jobs ran, {M} findings, {K} auto-fixed.

## ⚠️ Action needed ({count})

- [ ] {job-name}: {short description of action}
- [ ] ...

(If no actions, write "None — everything's clean.")

## 🔧 Auto-fixed ({count})

- {job-name}: {fix description}
- ...

## Per-job summary

### index-health — {🟢 green|🟡 amber|🔴 red|⚠️ error}
{one-line summary, optional details}

### daydream-lessons — {🟢 green|🟡 amber|🔴 red|⚠️ error}
...

## 💡 Frequency suggestions

- {📉 or 📈 prefix}{suggestion line with exact command the user can say}

(If none, omit this section entirely.)

---
_Run at {timestamp}. Full history: `.claude/hook_state/schedule-diary.jsonl`_
```

Also echo a compressed version of this report to the chat output so the user sees it without opening the file.

---

## Step 7b: Auto-Commit Generated Artifacts (optional, clean-tree only)

If `digest.auto_commit` is true in `schedule-config.json` (default: `false`), commit the generated artifacts so the next session starts from a clean tree and the diary/index are versioned.

**Clean-tree rule (borrowed from the command-center update flow):**

1. Run `git status --porcelain`. Collect all changed paths.
2. Let `ALLOWED` = exactly these paths:
   - `docs/document-index.md`
   - `docs/.wake-up-context.md`
   - `docs/.session-diary.md`
   - `docs/.onboarding-checklist.md`
   - `docs/_inbox/daily-digest.md`
   - `.claude/hook_state/schedule-diary.jsonl`
   - `.claude/quality/ecosystem/state.json` (if touched by ecosystem jobs)
3. If **every** changed path is in `ALLOWED` → proceed to commit.
   Otherwise → **skip** the commit entirely. Do not stage, do not branch. Record `auto_commit: skipped (tree not clean outside generated artifacts)` in the digest. The user will see the dirty state next session and decide manually.
4. On commit:
   - `git add` each `ALLOWED` path that actually changed (never `git add .`)
   - `git commit -m "bcos: daily maintenance {YYYY-MM-DD}"` — no push, ever
   - If commit fails (pre-commit hook, etc.), do not retry — record the error in the digest and continue
5. Never create a new branch. Never push. Never skip hooks.

This mirrors the update.py policy: "commit only if the tree is clean outside the files we own." If a user has in-progress work, the dispatcher stays out of the way entirely.

---

## Step 8: Final Output — `AskUserQuestion` ONLY when there's something to decide

The last thing the dispatcher does depends on whether the run produced anything that needs user judgement. The goal is to make the Claude Code dashboard useful as a priority inbox: sessions that show up as "Awaiting input" (yellow) should genuinely need attention; sessions that show up as "Ready" (blue) should be bulk-dismissable.

### The decision rule

End with `AskUserQuestion` IF any of these are true:

- **Any action items** (amber or red verdict with non-empty `actions_needed` from any job)
- **Frequency-tuning suggestions emitted** (see Step 6)
- **Any job errored** (verdict `error`)

Otherwise — clean green run, zero findings, zero suggestions — output a short summary and stop. No question. The session marks itself "Ready" on the dashboard and the user can bulk-read-acknowledge it later.

**Why this rule:** if every run always asked a question, every scheduled run would show as "Awaiting input" in the dashboard even on clean days. The yellow marker would lose meaning. This rule makes "Awaiting input" a real signal.

### Output for clean green runs (no question)

Short, affirmative, one or two lines:

```
Maintenance complete — verdict: 🟢 green. Nothing to act on.
(Full report: docs/_inbox/daily-digest.md)
```

Or even shorter when the user is watching an on-demand run:

```
🟢 Green — nothing to act on.
```

Stop. No question. Do not add "let me know if…" or "want me to…". The dashboard handles the follow-through.

### Output when something needs attention

**Short lead-in** (2-4 lines max, above the question):

```
Maintenance complete — verdict: 🟡 amber.
3 findings, 2 auto-fixed. Full report: docs/_inbox/daily-digest.md
```

(Use 🔴 for red verdicts, ⚠️ for error.)

**Then `AskUserQuestion`** with a `header` under 12 chars (e.g. "Next step", "Maintenance") and 2-4 options tailored to what happened.

### Option templates by scenario

The dispatcher chooses options based on the aggregate result. At least one option must be a concrete "DO something useful" action; at least one must be a way to dismiss/defer.

(The "green, no findings, no suggestions" case is NOT listed here because that case does not use `AskUserQuestion` — see the decision rule above.)

**Green with frequency-tuning suggestions:**

| Option | When to use |
|---|---|
| Apply suggested changes | dispatcher has a concrete config edit to propose |
| Show me the rationale | why is the dispatcher suggesting this |
| Keep as-is | dismiss suggestion |

**Amber with action items (non-critical):**

| Option | When to use |
|---|---|
| Walk me through action items | triage them one by one |
| Show full digest | see everything at once |
| Dismiss for now | acknowledge, handle later |

**Red with critical items:**

| Option | When to use |
|---|---|
| Work through critical items | top priority, start now |
| Show full digest | see the context around the critical items |
| Snooze — I'll handle soon | the critical items are acknowledged but user is busy |

**Error (a job crashed):**

| Option | When to use |
|---|---|
| Retry the failed job(s) | second chance — transient issue |
| Show me the error detail | diagnose before retrying |
| Skip — investigate later | defer |

### Rules for option wording

- Keep each option under 40 characters
- Start with a verb ("Work through", "Show", "Dismiss") — user reads what they'll GET by clicking
- Never duplicate effort: if "show full digest" is already in chat, don't also offer "read the file"
- Never ask about things the user can't directly action from here. ("Do you want architecture review to run weekly?" is too abstract — `schedule-tune` handles that)
- If the user picks "Walk me through action items", the dispatcher follows up by loading the first action item and asking what to do about it — NOT by dumping them all

### What happens after the user picks

Route to the right behavior:

- **Walk me through action items** → load the first action item from the digest, explain it, ask what to do (fix, defer, needs-info). Loop until all handled or user dismisses.
- **Show full digest** → open/display `docs/_inbox/daily-digest.md` content in chat, then re-ask the original question with updated options (drop "show digest", keep actions)
- **Apply suggested changes** → invoke `schedule-tune` skill with the exact proposed config edit
- **Tune schedule** → invoke `schedule-tune` skill in interactive mode ("what would you like to change?")
- **Retry the failed job(s)** → re-run only the errored jobs (on-demand mode), then ask again with the new result
- **Dismiss / Snooze / Done, thanks** → single-line acknowledgement, exit cleanly. Do NOT offer further questions in this cycle — the user chose to stop.

### Example

```
Maintenance complete — verdict: amber.
3 findings, 2 auto-fixed. Full report: docs/_inbox/daily-digest.md
```

Then `AskUserQuestion`:

- question: "Maintenance found 3 things needing your attention. What next?"
- header: "Next step"
- options:
  - Walk me through them
  - Show full digest
  - Dismiss for now

If the user picks "Walk me through them", the dispatcher continues with the first action item. The flow is always **structured choice → guided next action**, never "here's a list, good luck."

---

## On-Demand Mode

If the user says "run the {job-name} job now" or "run today's maintenance now":

1. Skip the schedule predicate — run only the named job(s)
2. **Append** (do not overwrite) results to `docs/_inbox/daily-digest.md` under a clearly marked section:

   ```markdown
   ---

   ## On-demand run — {HH:MM} ({job-name})

   **Verdict:** {🟢 green|🟡 amber|🔴 red|⚠️ error} — {findings} findings, {fixed} auto-fixed.

   ### ⚠️ Action needed
   - ...

   ### 🔧 Auto-fixed
   - ...
   ```

   If `daily-digest.md` does not yet exist (no scheduled run happened today), create it with a minimal header before appending the on-demand section.

3. Do NOT emit frequency-tuning suggestions (one-off runs don't produce a reliable cadence signal)
4. DO append a diary entry per job with `"trigger":"on-demand"` so the run is tracked in history
5. Report a short summary inline in chat
6. **Follow the same decision rule as Step 8**: end with `AskUserQuestion` only if there are action items or an error. Clean green on-demand runs end with a one-line confirmation ("Green — nothing to act on.") and stop. When a question IS asked, typical on-demand options:
   - Walk me through the findings
   - Run another job
   - Show the on-demand section of the digest
   - Done, thanks

The morning scheduled run always OVERWRITES `daily-digest.md` fresh — so yesterday's on-demand sections are not preserved in the digest (diary retains them). This keeps the digest a "today's story" file without unbounded growth.

---

## Error Handling

The dispatcher is meant to survive imperfect repos:

- Missing config → stop with a helpful error (see Preconditions)
- Malformed config → stop, don't guess
- A job reference file is missing → skip that job, log to diary, continue
- A job errors → log `"verdict":"error"`, continue
- Diary file doesn't exist → create it, write the first entry

Never silently swallow errors. Every dispatcher run produces either a digest OR a user-facing error message.

---

## Related Skills

- `schedule-tune` — user-facing skill for changing config ("run audit twice a week")
- `context-audit`, `daydream`, `lessons-consolidate` — underlying skills the job references invoke

---

## Notes for implementers

- The dispatcher is a *coordinator*, not a doer. Actual work happens inside the job references. If a check is shared across multiple jobs, put it in `references/` as a shared reference, not inline in the dispatcher.
- Diary lines are atomic — one JSON object per line, no multiline entries, append-only.
- Never delete or rewrite diary entries. If a run was wrong, add a corrective entry, don't mutate history.
- Keep individual job runs under 2 minutes each if possible. The dispatcher session is time-bounded.
