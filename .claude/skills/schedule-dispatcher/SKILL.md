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

If the config is malformed, STOP. Emit a typed `framework-config-malformed` finding (schema 1.1.0+, `category: "bcos-framework"`) with `finding_attrs = {file: ".claude/quality/schedule-config.json", parse_error: "{message}" | null, missing_fields: [...] | null}`. Write the minimum-shape sidecar (with this finding + `overall_verdict: "red"` + empty `jobs[]`) AND a `framework-config-malformed` row to `.claude/hook_state/bcos-framework-issues.jsonl` via the Step 7c writer pattern. Write a diary entry `dispatcher.error` with the validation failure. Report to the user: "schedule-config.json is malformed — fix before the dispatcher can run. Use the `schedule-tune` skill to repair it." Note: the chat-echo follows the **error scenario** template from Step 7.3, not the normal compact card.

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

## Step 2.5: Refresh the Context Index (once per run)

Before running any job, regenerate `.claude/quality/context-index.json` exactly **once**:

```
python .claude/scripts/context_index.py --write
```

Every job downstream that needs frontmatter / zone / cluster facets must call `load_context_index_cached()` from `context_index.py` rather than re-walking `docs/`. The cache TTL is 10 min (longer than a full dispatcher cycle), so all jobs in this run hit the same in-memory snapshot. This turns N full-tree walks per dispatcher tick into one — the difference matters for repos with hundreds of docs.

If a job has its own private parser for legacy reasons, that's fine — but new jobs and edits to existing jobs should prefer the cached helper.

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

**Data-corruption surfacing.** JSONL loaders (`auto_fix_audit._load_rows`, `promote_resolutions._load_rows`, `_load_diary`, etc.) use `_jsonl_safe.safe_load_jsonl()` which records dropped (malformed) lines in a `_LAST_LOAD_REPORT` module-global. When a job that uses these loaders completes with `_LAST_LOAD_REPORT.dropped > 0`, surface the report as a `data-corruption-detected` action item in the digest — the auditor's denominator silently shrinks otherwise. New loaders SHOULD use `safe_load_jsonl` rather than the legacy `try/except: continue` pattern; the helper signature returns `(rows, report)` so callers can include the finding without changing call-site shape.

Wiki jobs are first-class job references and use the same dispatcher contract:

| Job | Reference | Notes |
|-----|-----------|-------|
| `wiki-stale-propagation` | `references/job-wiki-stale-propagation.md` | Daily metadata scan for wiki pages whose `builds-on` sources changed after `last-reviewed`. |
| `wiki-source-refresh` | `references/job-wiki-source-refresh.md` | Weekly two-tier refresh check: HEAD-only quick check at `stale_threshold_days/4`, full refresh-must-rediscover at `stale_threshold_days`. |
| `wiki-graveyard` | `references/job-wiki-graveyard.md` | Monthly stale/orphan/archive-candidate scan. |
| `wiki-coverage-audit` | `references/job-wiki-coverage-audit.md` | Quarterly cross-zone coverage scan and permissive cluster-drift INFO reporting. |

---

## Step 4b: Completion Checklist — every scheduled job MUST produce a verdict

After Step 4 completes (last job returned), verify that **every job listed in Step 2's run-list produced exactly one diary entry in this dispatcher tick**. This is the silent-skip guard: a job whose reference file is missing, whose runner threw before the `try/except` could catch it, or that was implicitly forgotten by Claude during execution must NOT disappear unnoticed.

1. Build `expected_jobs` = the ordered list from Step 2 (jobs marked due today + on-demand overrides).
2. Read back the diary entries appended during this tick (use the dispatcher's in-memory record, or the tail of `.claude/hook_state/schedule-diary.jsonl` filtered to the current run's `ts` prefix if you're running on-demand).
3. For each job in `expected_jobs`, confirm a diary entry exists. If any job is missing:
   - Append a `verdict: "error"` diary entry for it with `"notes": "job skipped silently — no completion record produced"`.
   - **Schema 1.1.0+:** emit a typed `dispatcher-silent-skip` finding (`category: "bcos-framework"`, verdict `red`, `emitted_by: "dispatcher"`) into the in-memory findings list — Step 4c will then route it through stickiness compute and Step 7c will append it to `bcos-framework-issues.jsonl`. `finding_attrs = {job: "{job_id}", expected_after: "{tick_start_ts}", last_diary_ts: "{tail_ts}" | null, missing_artifact: null}`. This replaces the prose action-item; the dashboard renders it as an acknowledge-only card with "Reported to BCOS" footer.
   - Set the overall dispatcher verdict to `red` (silent skips are critical — they mean the safety surface lied).

Do NOT proceed to Step 5 (auto-fixes) until the checklist passes. A silent skip on a destructive job (lifecycle-sweep auto-routing, wiki-archive-expired-post-mortem, etc.) would let policy violations land unannounced; better to halt and surface.

**Rationale.** This was added after the 2026-05-05 incident in `theo-portfolio` where `command-center-schedules-snapshot` silently dropped out of a tick, leaving the downstream dashboard 24h stale with no error trail. Dispatcher behavior is now: "every scheduled job either completes with a verdict or surfaces as a `red` error — no third path."

---

## Step 4c: Compute Headline + Finding Stickiness

**Added in schema 1.1.0.** Before applying auto-fixes (Step 5) or rendering the digest (Step 7), enrich each finding emitted in Step 4 with three computed fields and produce the run's headline string. This step is the load-bearing source of the dashboard's stuck-badge UX — without it, every dispatcher tick re-emits findings as if they were fresh and the user has no signal that a problem is recurring.

**Inputs:** raw findings from Step 4, last 30 diary entries (already read in Step 3), the classifier in [`references/finding-categories.md`](./references/finding-categories.md).

### Per-finding enrichment

For each `Finding` in the in-memory findings list:

1. **Resolve `category`** by looking up `finding_type` in the classifier table in `finding-categories.md`. Default: `repo-context` if unmapped (sidecars stay backward-compat with 1.0.0 emitters). Any unmapped ID is a contract violation — emit a `schema-validation-failed` framework finding alongside.
2. **Compute the finding-identity tuple** `(finding_type, primary_attr_value, emitted_by)` — the primary_attr key per finding_type is in `finding-categories.md`'s classifier tables. For singletons (no per-instance primary key, e.g. `lessons-count-high`) use the string `"singleton"`.
3. **Match against prior tick.** Scan diary entries from the **immediately-prior dispatcher tick** (the most-recent run before today, identified by the latest `ts` < today's run window). If any prior finding has the same identity tuple:
   - `consecutive_runs = prior.consecutive_runs + 1`
   - `first_seen = prior.first_seen` (preserve)
4. **No match → fresh finding.**
   - `consecutive_runs = 1`
   - `first_seen = today` (ISO `YYYY-MM-DD`)
5. **Strict reset semantics.** If the identity tuple appeared 2 ticks ago but NOT in the immediately-prior tick, it's a fresh finding (consecutive_runs = 1). One missing tick resets — the dispatcher does not "remember" through gaps. Rationale: a finding that disappeared and came back is a different incident than one that never went away; treating them the same would mask intermittent flicker.
6. **Stuck severity override.** When `consecutive_runs >= 3`, mark `severity_override = "stuck"` in-memory (the renderer in Step 7 picks this up; the sidecar JSON also gets a `severity_override` field if present).
7. **Acknowledge-only routing for framework findings.** If `category == "bcos-framework"`, force `suggested_actions = ["acknowledge"]`. The job may have proposed other actions; the dispatcher overrides. Framework findings never get Fix buttons.

If the diary is empty or insufficient (< 1 prior tick available), every finding gets `consecutive_runs = 1, first_seen = today`. The count auto-corrects on subsequent runs.

### Headline computation

The headline is a single sentence rendered at the top of both the .md digest (Step 7) and the chat echo. Computed deterministically from the enriched findings + per-job verdicts:

| Run shape | Headline template |
|---|---|
| Green clean (0 findings, 0 framework) | "{Nth consecutive green run.}{recovery callout if any job verdict flipped error→green this tick.}" |
| Green with frequency suggestions only | "All {N} jobs green. {M} frequency suggestions to consider." + recovery callout if any |
| Amber, no stuck | "{N} action items{; M auto-fixed if M>0}{; recovery callout if any}." |
| Amber WITH stuck (>=1 finding with consecutive_runs >= 3) | "{N} stuck — oldest from {first_seen of oldest stuck finding}. Will not resolve on its own." |
| Red (any critical / silent-skip / framework red) | "{N} critical: {top finding's display label}{; '+M other' if N>1}." |
| Error (>=1 job verdict='error') | "{N} jobs errored: {first errored job's name}{; '+M other' if N>1}." |

**Recovery callout** = "lifecycle-sweep recovered (3 prior errors cleared)" or similar. Computed by scanning prior 3 diary entries for the same job_id with `verdict in {"error", "red"}` followed by today's `"green"`.

The headline gets a new top-level field in the sidecar JSON: `headline` (string), added in 1.1.0.

### Output

After Step 4c completes, the in-memory findings list has all 1.1.0 fields populated:
- `category` (always)
- `first_seen` (always)
- `consecutive_runs` (always, ≥1)
- `severity_override` (only when `consecutive_runs >= 3`)
- `suggested_actions` (forced to `["acknowledge"]` for framework category)

And the run has a `headline` string ready for Step 7.

Step 5 (auto-fix application) then operates only on `category: "repo-context"` findings. Framework findings are NEVER auto-fixable — the dispatcher refuses to apply any whitelisted fix that targets a framework path.

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

**Schema 1.1.0+: the digest is rendered FROM the typed-event sidecar, not authored separately.** The dispatcher writes two co-located artifacts:

- `docs/_inbox/daily-digest.json` — typed-event sidecar (canonical, dashboard reads this; see [`typed-events.md`](../../../docs/_bcos-framework/architecture/typed-events.md))
- `docs/_inbox/daily-digest.md` — markdown renderer of the same in-memory data (humans without a dashboard read this)

Both are overwritten each run. One file, always latest. History lives in the diary.

**Field parity is non-negotiable.** If the .md says "3 action items" the JSON `findings[]` must have 3 entries with `category: "repo-context"`. The wiring test `test_digest_typed_events.py` asserts this; do not let them drift.

### 7.1 Markdown template

Fixed structure. Conditional sections render ONLY when their counts are non-zero — a green clean run is ~5 lines, an amber run with 5 findings is ~40 lines. Markdown tables for lists of ≥2 (eyes track columns faster than bullets). Single-item sections render as a one-line bullet.

```markdown
# Daily Maintenance Digest — {YYYY-MM-DD}

**{🟢 green | 🟡 amber | 🔴 red | ⚠️ error}** · {N} ran · {findings-summary} · {K} auto-fixed · {duration}

**Headline:** {computed in Step 4c}

## ⚠️ Action needed ({count_repo_context_amber_red})

| # | Job | File / Target | Issue | Stickiness |
|---|---|---|---|---|
| 1 | `{emitted_by}` | `{primary_attr}` | {one-line meaning} | {`🔁 Nth run` if consecutive_runs ≥ 3, else blank} |
| 2 | ... | ... | ... | ... |

## 🔧 Auto-fixed ({count})

- ✓ `{fix_id}` on `{target}` ({detail})
- ✓ ...

## 🔧 BCOS framework issues ({count_bcos_framework})

> **Acknowledge-only.** These are framework bugs reported for transparency. Do not attempt to fix in this repo — `update.py` would overwrite. The framework owner is responsible for these.

| # | Finding | Detail | First seen |
|---|---|---|---|
| 1 | `{finding_type}` | {primary_attr_value} | {first_seen} |

## 📊 Jobs ({N})

| Job | | Findings | Note |
|---|---|---|---|
| {job} | {🟢 green / 🟡 amber / 🔴 red / ⚠️ error} | {finding_count} | {`📉 suggest weekly` / `✅ recovered` / `🔁 stuck` as applicable} |
| ... | ... | ... | ... |

## 💡 Suggestions ({M}) — say "tune schedule"

- 📉 `{job}` {current_schedule} → {suggested_schedule} · {reason}
- 📈 ...

---
Run at {ISO timestamp} · `.claude/hook_state/schedule-diary.jsonl`
Auto-commit: {✓ committed (sha) | ✗ skipped (reason)}
```

### 7.2 Section-render rules

| Section | Rendered when | Notes |
|---|---|---|
| Verdict bar | Always | Single line; emoji + counts + duration. **`{findings-summary}` shape:** if framework findings count is 0, render `"{M} findings"` (single number). If ≥1 framework finding, render split form `"{M_repo} repo · {M_framework} framework"` so the user immediately sees the split. Either way, total = M_repo + M_framework. |
| `Headline` | Always | One sentence from Step 4c |
| `⚠️ Action needed` | `≥1` repo-context finding with verdict amber/red | Table for ≥2 rows; single-line bullet for exactly 1 |
| `🔧 Auto-fixed` | `≥1` `auto_fixed[]` entry | Bullet list (rare to exceed 5) |
| `🔧 BCOS framework issues` | `≥1` `category: "bcos-framework"` finding | Separated block with acknowledge-only banner — never folded into `Action needed` |
| `📊 Jobs` | Always (always ≥1 job ran) | Table; verdict emoji + finding count + inline status markers in Note column |
| `💡 Suggestions` | `≥1` `frequency-suggestion` finding | Bullet list |
| Footer | Always | Run timestamp, diary path, auto-commit status |

**Inline status markers in the Jobs table** (Note column):

| Marker | When |
|---|---|
| `📉 suggest weekly` (or similar) | A `frequency-suggestion` finding targets this job |
| `✅ recovered` | This job's prior 3 diary entries had `error`/`red` and today is `green` |
| `🔁 stuck (Nx)` | This job has ≥1 finding with `consecutive_runs ≥ 3`; N = max consecutive_runs across its findings |

### 7.3 Chat-echo (3-line compact card per scenario)

After writing the .md file, echo a FIXED 3-line markdown block to the chat output. **Do not improvise.** The block is what every Claude Code dashboard session card shows; deterministic formatting keeps the dashboard scannable across repos.

The shape is always:

```markdown
**{verdict-emoji} {repo-or-portfolio-name} {state}** · {ran} ran · {findings} findings · {fixed} fixed
{top-line: ONE sentence — usually identical to the .md headline}
→ {action hint with concrete commands the user can say}
```

The third line ALWAYS gives the user a concrete next action. Pick the hint per scenario:

| Scenario | Verdict bar example | Top line | Action hint |
|---|---|---|---|
| Green clean | `**🟢 BCOS green** · 1 ran · 0 findings · 0 fixed · 4s` | `Headline string from Step 4c, e.g. "10th consecutive green run."` | `→ Nothing to act on. Say "mark read" or ignore.` |
| Green with suggestions | `**🟢 BCOS green** · 9 ran · 0 findings · 0 fixed · 5m` | `All 9 jobs green. 3 frequency suggestions emitted.` | `→ Say "tune schedule" / "show suggestions" / "ignore".` |
| Amber, no stuck | `**🟡 BCOS amber** · 9 ran · 2 findings · 0 fixed` | `Top: {finding type} on {primary_attr}{; +N other}.` | `→ Say "fix it" / "show digest" / "mark read".` |
| Amber WITH stuck | `**🟡 BCOS stuck** · 9 ran · 3 findings (2 stuck)` | `2 findings unresolved 3+ runs — won't resolve on their own.` | `→ Say "fix it" / "show stuck" / "snooze 7d".` |
| Red critical / silent-skip | `**🔴 BCOS red** · 5 ran · 2 repo · 1 framework` | `{finding_type} on {primary_attr}{; +N other}.` | `→ Open daily-digest.md for the safety surface. Say "retry" / "investigate".` |
| Error (job crashed) | `**⚠️ BCOS error** · 9 scheduled, 7 clean, 2 errored` | `{first errored job} {error message snippet}{; +N other}.` | `→ Say "retry failed jobs" / "show errors" / "skip".` |

The verdict bar's `{findings-summary}` segment uses the same split rule as Step 7.2 — `"3 findings"` when zero framework, `"2 repo · 1 framework"` when ≥1 framework.

**When framework findings present** (regardless of scenario), append ONE extra line BEFORE the action hint:

```markdown
⚠️ {N} BCOS framework issue{s} logged (acknowledge-only — Guntis will fix in next release)
```

This is the cleanest possible chat surface for the user across all dispatcher invocations. The full detail lives in `docs/_inbox/daily-digest.md`; the chat just orients and hands off.

---

## Step 7b: Auto-Commit Generated Artifacts (optional, clean-tree only)

If `digest.auto_commit` is true in `schedule-config.json` (default: `false`), commit the generated artifacts so the next session starts from a clean tree and the diary/index are versioned.

**Branch allowlist (skip commit on short-lived feature branches):**

1. Read `digest.auto_commit_branches` from `schedule-config.json`. Default: `["main", "master", "dev", "develop"]`.
2. Run `git rev-parse --abbrev-ref HEAD` to get the current branch.
3. If the current branch is **not** in the allowlist → **skip** the commit entirely. Still write the digest file to disk (so it's available locally), but record `auto_commit: skipped (branch {name} not in allowlist)` in the digest. The user's feature-branch PR diff stays clean of unrelated digest commits; the next session on a long-lived branch picks up the digest naturally.
4. If the current branch IS in the allowlist → proceed to the clean-tree rule below.

**Clean-tree rule (borrowed from the command-center update flow):**

1. Run `git status --porcelain`. Collect all changed paths.
2. Let `ALLOWED` = exactly these paths:
   - `docs/document-index.md`
   - `docs/.wake-up-context.md`
   - `docs/.session-diary.md`
   - `docs/.onboarding-checklist.md`
   - `docs/_inbox/daily-digest.md`
   - `docs/_inbox/daily-digest.json`
   - `.claude/hook_state/schedule-diary.jsonl`
   - `.claude/quality/ecosystem/state.json` (if touched by ecosystem jobs)
   - `.claude/quality/context-index.json` (regenerated in Step 2.5; ignore if `.gitignore` excludes it on this install — the path appears in `git status` only when it's tracked from before the ignore rule landed)
3. If **every** changed path is in `ALLOWED` → proceed to commit.
   Otherwise → **skip** the commit entirely. Do not stage, do not branch. Record `auto_commit: skipped (tree not clean outside generated artifacts)` in the digest. The user will see the dirty state next session and decide manually.
4. On commit:
   - `git add` each `ALLOWED` path that actually changed (never `git add .`)
   - `git commit -m "bcos: daily maintenance {YYYY-MM-DD}"` — no push, ever
   - If commit fails (pre-commit hook, etc.), do not retry — record the error in the digest and continue
5. Never create a new branch. Never push. Never skip hooks.

This mirrors the update.py policy: "commit only if the tree is clean outside the files we own." If a user has in-progress work, the dispatcher stays out of the way entirely.

---

## Step 7c: Append BCOS-Framework Issues to Local Log

**Added in schema 1.1.0.** When this dispatcher tick produced any finding with `category: "bcos-framework"`, append one JSONL line per such finding to `.claude/hook_state/bcos-framework-issues.jsonl`.

This local log is the **producer side** of the umbrella portfolio-aggregation contract (see [`portfolio-framework-issues-feed.md`](../../../docs/_bcos-framework/architecture/portfolio-framework-issues-feed.md)). Each sibling repo writes its own log; the umbrella's Command Center walker (opt-in, only when umbrella installed) reads and aggregates across siblings. A BCOS install with no umbrella still writes the log — it just sits locally until somebody (or the dashboard) reads it. **No opt-out at the framework level**: every sibling writes its own log on every tick when framework findings present. Transparent by default.

### Line shape

One JSON object per line, written via the same `append_diary.py` atomic-append helper used for the diary (avoids the sensitive-file approval prompt on `.claude/` writes):

```json
{
  "ts": "2026-05-12T09:00:42Z",
  "run_at": "2026-05-12T09:00:00Z",
  "sibling_id": null,
  "finding_type": "dispatcher-silent-skip",
  "verdict": "red",
  "emitted_by": "dispatcher",
  "first_seen": "2026-05-12",
  "consecutive_runs": 1,
  "finding_attrs": { "...": "per typed-events.md shape" }
}
```

Fields:
- `ts` — when the log line was appended (line-level timestamp; distinct from `run_at`)
- `run_at` — when the dispatcher tick started (matches the sidecar's top-level `run_at`)
- `sibling_id` — **always `null` on the producer side.** The umbrella walker fills this in when aggregating, prefixed with the sibling's project ID from `.bcos-umbrella.json`
- `finding_type`, `verdict`, `emitted_by`, `first_seen`, `consecutive_runs`, `finding_attrs` — copied verbatim from the Finding in `daily-digest.json`

### When NOT to write

- Zero framework findings this tick → do not write anything to the file. The log only grows when something happened. (Reader code handles "file does not exist" as "no framework issues from this sibling".)
- Framework finding categorised as `repo-context` by mistake (classifier bug) → do not write. Surface a `schema-validation-failed` framework finding instead and let the next tick correct.

### Retention + size

Framework issues are append-only. Never trimmed by BCOS itself. The umbrella walker applies its own retention window (default 7 days for portfolio view) when reading — the underlying file keeps the full history for audit. Expected size: a clean dev cycle produces 0 lines; a single bug-cycle from emit → fix → next-update can produce up to 1 line per affected sibling per dispatcher tick. Realistically under 1MB per sibling per year.

### Failure modes

- File does not exist → create on first append (the helper handles this).
- Write fails → log the failure as a NEW framework finding (`framework-config-malformed` with `finding_attrs.parse_error = "log write failed: {message}"`) and continue. The dispatcher does NOT retry — repeated failures are caught by the next tick's safety surface.
- Disk full → same as write fails. The dispatcher's job is to surface, not to ensure infinite reliability.

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
- Malformed config → emit `framework-config-malformed` typed finding (see Step 1), stop, don't guess
- A job reference file is missing → emit `job-reference-missing` typed finding (`category: "bcos-framework"`, verdict `red`, `finding_attrs = {job: "{name}", expected_path: ".claude/skills/schedule-dispatcher/references/job-{name}.md"}`), skip that job, log to diary, continue. The framework finding routes to `bcos-framework-issues.jsonl` via Step 7c.
- A job errors → log `"verdict":"error"`, continue. If the error originated in a framework-managed code path (auto-fix handler, dispatcher itself), also emit a `auto-fix-handler-threw` framework finding.
- Diary file doesn't exist → create it, write the first entry
- A JSONL loader reports `_LAST_LOAD_REPORT.dropped > 0` → emit `data-corruption-detected` typed finding with the file path + dropped line count

Never silently swallow errors. Every dispatcher run produces either a digest OR a user-facing error message. **Schema 1.1.0+: framework-level error conditions emit typed `bcos-framework` findings rather than prose-only notes**, so they route through the same dashboard + portfolio aggregation surface as scheduled findings.

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
