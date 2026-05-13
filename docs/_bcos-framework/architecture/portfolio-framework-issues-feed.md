---
name: Portfolio Framework Issues Feed
type: architecture
status: active
version: 1.0.0
created: 2026-05-12
last-updated: 2026-05-12
authority: canonical-process
tags: [framework, umbrella, portfolio, dispatcher, contract]
domain: framework-infrastructure
exclusively-owns: portfolio-framework-issues-feed
builds-on:
  - docs/_bcos-framework/architecture/typed-events.md
  - docs/_bcos-framework/architecture/cross-repo-retrieval.md
---

# Portfolio Framework Issues Feed — Cross-Sibling Aggregation Contract

The producer-consumer contract between BCOS (each sibling repo) and `bcos-umbrella` (the portfolio host) for surfacing framework-level findings across a portfolio of registered BCOS-enabled repos.

**TL;DR:** every BCOS sibling writes its own `.claude/hook_state/bcos-framework-issues.jsonl` on every dispatcher tick when at least one `category: "bcos-framework"` finding fires. The umbrella's Command Center, when opt-in is enabled, walks each registered sibling's log on its own daily cadence, aggregates the last N days into a portfolio-wide view, and routes the result to the framework owner. The owner — typically one engineer responsible for the BCOS framework itself — sees which framework bugs are firing in which siblings, prioritizes upstream fixes, and ships them via the next BCOS release.

**Lessons applied:**

- [`L-ECOSYSTEM-20260510-018`](../../../.claude/quality/ecosystem/lessons.json) — minimum contract for out-of-tree consumers. BCOS documents *what fields the framework writes*. The umbrella owns its own full schema for the aggregation layer.
- [`L-ECOSYSTEM-20260510-017`](../../../.claude/quality/ecosystem/lessons.json) — opt-in dial in user config when framework strictness conflicts with user intent. The producer side (always-on log writing) is the framework default. The consumer side (cross-sibling aggregation) is opt-in via `.bcos-umbrella.json.framework_issues.aggregate`. Framework invariant preserved; user agency preserved per-portfolio.
- [`L-ECOSYSTEM-20260510-019`](../../../.claude/quality/ecosystem/lessons.json) — additive top-level block over folding into existing fields. Framework findings get their own dedicated log file, not folded into the existing diary or sidecar.

---

## Producer contract — BCOS side (every sibling)

### What gets written

`.claude/hook_state/bcos-framework-issues.jsonl` — one JSON object per line, append-only, written by the dispatcher's Step 7c after every tick that produced ≥1 `category: "bcos-framework"` finding.

### Line shape

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
  "finding_attrs": {
    "job": "command-center-schedules-snapshot",
    "expected_after": "2026-05-12T09:00:00Z",
    "last_diary_ts": "2026-05-11T09:00:00Z",
    "missing_artifact": null
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `ts` | ISO-8601 | When this line was written (line-level). Distinct from `run_at`. |
| `run_at` | ISO-8601 | When the dispatcher tick that produced this finding started. Matches the sidecar's top-level `run_at`. Lets the consumer dedupe lines emitted by the same tick. |
| `sibling_id` | `null` on producer | **Always `null`** at write time. The umbrella walker fills this in when aggregating, prefixed with the sibling's project ID from `.bcos-umbrella.json`. |
| `finding_type` | string | One of the 9 `bcos-framework` finding_types enumerated in [`typed-events.md`](./typed-events.md). |
| `verdict` | `"red" \| "amber"` | Framework findings never carry verdict `green`. |
| `emitted_by` | string | Usually `"dispatcher"` for the dispatcher-emitted set; can also be a specific job ID (e.g. `auto-fix-audit` for `data-corruption-detected`) or a registration-time skill (`context-onboarding` for `scheduled-task-cwd-mismatch`). |
| `first_seen` | ISO date | When this exact finding first emitted across all prior ticks. From Step 4c stickiness compute. |
| `consecutive_runs` | int ≥ 1 | How many consecutive ticks this same `(finding_type, primary_attr, emitted_by)` tuple has appeared. From Step 4c. |
| `finding_attrs` | object | Per `finding_type` shape from [`typed-events.md`](./typed-events.md). |

### Producer-side guarantees

1. **No opt-out at the framework level.** Every sibling writes its own log on every relevant tick. Free at the I/O layer (atomic append, no file held open). Transparent to the user via their own dashboard.
2. **No cross-repo writes.** The producer NEVER reads or writes another sibling's data. All cross-sibling work is the umbrella's job (read-only walk).
3. **Append-only, never trimmed.** BCOS never deletes lines from this file. The consumer applies its own retention when reading. The full local history is auditable.
4. **Atomic appends.** Uses the same `append_diary.py` helper as the diary — one JSON object per line, no multiline entries, no half-writes.
5. **Failure isolation.** If the log write fails (disk full, permission, etc.), the dispatcher emits a new framework finding (`framework-config-malformed` with `parse_error: "log write failed..."`) and continues. The dispatcher does NOT retry — repeated failures surface on the next tick.

### Where this fires

The producer side is **already wired** as of schema 1.1.0:

- [`SKILL.md` Step 7c](../../../.claude/skills/schedule-dispatcher/SKILL.md) — append logic
- Triggered by any finding with `category: "bcos-framework"` enriched in [`Step 4c`](../../../.claude/skills/schedule-dispatcher/SKILL.md)
- Category source-of-truth: [`finding-categories.md`](../../../.claude/skills/schedule-dispatcher/references/finding-categories.md)

The umbrella does not need to negotiate or signal the producer in any way. The log exists if framework findings exist; the file is absent (or empty) if not.

---

## Consumer contract — bcos-umbrella side

### Opt-in flag

Aggregation is **opt-in per portfolio**, mirroring the `cross-repo-retrieval` pattern in [`cross-repo-retrieval.md`](./cross-repo-retrieval.md). In the umbrella host's `.bcos-umbrella.json`:

```json
{
  "framework_issues": {
    "aggregate": true,
    "retention_days": 7,
    "max_lines_per_sibling": 500,
    "cadence": "daily"
  }
}
```

| Field | Default | Notes |
|---|---|---|
| `aggregate` | `false` | When `false`, the umbrella ignores per-sibling logs entirely — no walks happen, no UI surface populates. When `true`, the umbrella runs the walker on its own cadence. |
| `retention_days` | `7` | Walker considers only lines with `ts` within this window. Older lines stay on disk in each sibling but don't surface in the portfolio view. |
| `max_lines_per_sibling` | `500` | Defensive cap. If a sibling's log has grown faster than expected (suggests a runaway emit), the walker truncates its read and surfaces a meta-finding to the framework owner. |
| `cadence` | `"daily"` | Run-frequency hint. Actual scheduling lives on the umbrella's own dispatcher (see `umbrella-schedule-config.json`). |

When `framework_issues` is absent from `.bcos-umbrella.json`, the umbrella behaves bit-for-bit as if `aggregate: false` — no walker fires, no UI surface, no cost.

### Walker behavior

The umbrella's aggregator job (a new entry in `umbrella-schedule-config.json`, see §"Umbrella-onboarding hook" below) does the following each tick:

1. Read `.bcos-umbrella.json.projects[]` to enumerate registered siblings.
2. For each sibling with a resolvable on-disk path (per the existing `cross-repo-retrieval.md` convention):
   - Open `${sibling}/.claude/hook_state/bcos-framework-issues.jsonl`.
   - If the file does not exist, treat as zero findings for that sibling. Continue.
   - Read up to `max_lines_per_sibling` lines from the tail.
   - Parse each line as JSON; skip malformed lines (mirror the dispatcher's `_jsonl_safe.safe_load_jsonl` pattern) and record a count of dropped lines.
   - Filter to entries where `ts >= now() - retention_days`.
3. For each accepted line, fill in `sibling_id = <project_id>` (from the sibling's `.bcos-umbrella.json.node.id` or the equivalent in `projects[].id`).
4. Aggregate across siblings into a single in-memory list, sorted by `ts` descending.
5. Write the aggregated result to `${umbrella}/docs/_inbox/portfolio-framework-issues.{md,json}` (consumer-owned path; the producer never touches this).
6. Emit a one-line summary to the umbrella's diary (`.claude/hook_state/umbrella-diary.jsonl` or equivalent).

### Walker-side guarantees

- **Read-only across siblings.** The walker never writes back to a sibling's tree. Cross-repo writes are forbidden by the framework invariant.
- **Snapshot-based, no locks.** Sibling logs may be appended while the walker reads. The walker opens a snapshot and tolerates partial-line tails; this is the same pattern used by the existing diary readers.
- **Fail-soft per sibling.** A missing log, malformed JSON, or unreachable sibling does NOT block the walker from completing. Each failure is surfaced as a meta-finding in the aggregated output.
- **No retention enforcement on producer.** The walker NEVER deletes or trims sibling logs. Sibling-side retention is the framework's concern (currently: never trim, indefinite append).

### Aggregated output shape

`portfolio-framework-issues.json` — written by the walker:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-05-12T09:30:00Z",
  "umbrella_id": "my-portfolio",
  "retention_days": 7,
  "siblings_polled": 5,
  "siblings_with_findings": 2,
  "lines_total": 8,
  "lines_dropped": 0,
  "findings": [
    {
      "sibling_id": "sibling-a",
      "ts": "2026-05-12T08:05:00Z",
      "run_at": "2026-05-12T08:00:00Z",
      "finding_type": "installer-seed-missing",
      "verdict": "amber",
      "emitted_by": "lifecycle-sweep",
      "first_seen": "2026-05-08",
      "consecutive_runs": 5,
      "finding_attrs": { "...": "..." }
    }
  ],
  "by_finding_type": {
    "installer-seed-missing": 3,
    "dispatcher-silent-skip": 1
  },
  "by_sibling": {
    "sibling-a": 2,
    "sibling-b": 6
  }
}
```

The `by_finding_type` and `by_sibling` rollups are derived; they let the Command Center renderer answer "is this a systemic framework issue or isolated to one sibling?" without re-aggregating.

---

## Umbrella-onboarding hook spec

The opt-in flag should be set during umbrella onboarding so users don't have to discover it. `bcos-umbrella`'s `umbrella-onboarding` skill should add this step:

### Recommended question wording

After the registered-siblings step ("we found N BCOS-enabled siblings at these paths..."), insert this question via `AskUserQuestion`:

> **Aggregate framework issues across your N registered projects?**
>
> When BCOS itself hits a bug — a job's reference file goes missing, the dispatcher silent-skips, schema validation fails — each sibling logs it locally as an "acknowledge-only" framework finding. By default these are visible only in that sibling's own dashboard.
>
> If you aggregate at the portfolio level, the umbrella's Command Center collects framework findings across all your siblings and surfaces them in one feed. Useful if:
> - you maintain the BCOS framework yourself and want to see which sibling repos hit which bugs
> - you operate a portfolio of BCOS-enabled repos and want one place to track framework health
>
> Default is OFF. You can flip it later via `umbrella-schedule-tune`.

Options:
- **Yes — aggregate framework issues**
- **No — keep findings per-sibling only** (Recommended for most users)
- **Tell me more** (shows this doc inline)

### Config writes when "Yes" is picked

The umbrella-onboarding skill writes to `.bcos-umbrella.json`:

```json
{
  "framework_issues": {
    "aggregate": true,
    "retention_days": 7,
    "max_lines_per_sibling": 500,
    "cadence": "daily"
  }
}
```

AND adds a new entry to `umbrella-schedule-config.json`:

```json
{
  "jobs": {
    "portfolio-framework-issues-aggregate": {
      "enabled": true,
      "schedule": "daily",
      "_about": "Walks each registered sibling's bcos-framework-issues.jsonl and aggregates the last retention_days into docs/_inbox/portfolio-framework-issues.{md,json}. Opt-in via .bcos-umbrella.json.framework_issues.aggregate."
    }
  }
}
```

### Config writes when "No" is picked

No write to `.bcos-umbrella.json` (absent block = opt-out). No new job entry. The user can still flip on later via `umbrella-schedule-tune` natural-language editing.

---

## Command Center rendering recommendations

The umbrella's Command Center (its dashboard equivalent of `bcos-dashboard`) consumes `portfolio-framework-issues.json`. Recommendations for the renderer:

### Grouping

Render findings in three lenses, toggleable via filter chips:

1. **By sibling** (default) — see "which projects are hitting BCOS bugs"
2. **By finding_type** — see "is this a systemic framework issue or isolated"
3. **By severity** — red findings pinned at top, amber below

### Systemic-issue highlight

When `by_finding_type[X] >= 3` (same finding_type firing in ≥3 siblings within the retention window), render a "🔍 systemic" badge above the findings of that type. This is the load-bearing signal for the framework owner: a bug affecting one sibling is incidental; one affecting three is a release-blocker.

### Stuck-finding pinning

Mirror BCOS dashboard's stuck logic: findings with `consecutive_runs >= 3` get a 🔁 stuck (Nx) chip and pin above non-stuck. In the portfolio view, this surfaces issues that have been recurring across multiple ticks WITHIN a sibling.

### Sibling chip styling

Each finding card carries a sibling chip (e.g. `[sibling-a]`). Clicking the chip filters to that sibling's findings only — useful when an owner wants to drill into one project.

### Empty state

When aggregation is enabled but no findings have fired in `retention_days`, render a positive empty state: "✅ All N siblings clean — no framework issues in the last {retention_days} days." This is signal: the framework is in a good state.

When `aggregate: false`, render nothing for this panel (not even an empty state — the user opted out).

---

## What this contract does NOT cover

Out of scope for the framework side:

- **Cross-machine sync.** This contract covers single-machine umbrella aggregation only. If sibling repos live on different machines, sync them via existing version control or a portfolio-wide sync tool — not BCOS's concern.
- **Bug ticketing.** Framework findings in the portfolio view are read-only. Converting them to tickets in Linear, Jira, GitHub, etc. is the framework owner's workflow — not the umbrella's job.
- **Auto-fix from the umbrella side.** The umbrella never writes back to a sibling. Framework bugs ship via BCOS upstream updates (`update.py`). Period.
- **Schema migration of `bcos-framework-issues.jsonl`.** This is 1.0.0. Future bumps follow the same additive principle as the daily-digest sidecar (new optional fields, never breaking).

---

## See also

- [`typed-events.md`](./typed-events.md) — `finding_type` enum + per-type `finding_attrs` shapes. Schema 1.1.0 is the contract this feed builds on.
- [`finding-categories.md`](../../../.claude/skills/schedule-dispatcher/references/finding-categories.md) — the load-bearing repo-context vs bcos-framework classifier.
- [`cross-repo-retrieval.md`](./cross-repo-retrieval.md) — sibling sister-pattern. Same `.bcos-umbrella.json` consumption, same opt-in dial principle.
- [`SKILL.md` Step 7c](../../../.claude/skills/schedule-dispatcher/SKILL.md) — producer-side writer.
