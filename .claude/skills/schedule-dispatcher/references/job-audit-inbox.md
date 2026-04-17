# Job: audit-inbox

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly (Friday)
**Nature:** structural — deep CLEAR audit + inbox aging + lessons consolidation

---

## Purpose

The end-of-week structural pass. Where `index-health` catches *new* drift daily, this job catches *accumulating* drift weekly — the things too expensive to check every day.

Three concerns, in priority order:

1. Light CLEAR audit across ALL clusters (breadth over depth — find obvious issues everywhere)
2. Inbox files older than 7 days get flagged for triage
3. Lessons get consolidation proposals (overlaps, staleness)

This job is moderately heavy (5-10 minutes). It's scheduled for Friday so any findings fit the typical "close out the week" mental model.

**Why light-all instead of deep-one-cluster:** a weekly pass across everything catches anything newly broken anywhere — a lint-level sweep. Deep ownership/completeness analysis is the job of the monthly `architecture-review`, which has the time budget for it. Splitting the roles avoids redundancy: `audit-inbox` = "does anything look wrong right now?", `architecture-review` = "is the structure still the right structure?".

---

## Steps

### 1. Rebuild the document index

Run `python .claude/scripts/build_document_index.py`. Capture. Non-fatal on error.

### 2. Light audit across all clusters

Invoke the `context-audit` skill with:

- Scope: `all` (every active cluster)
- Depth: `light` (lint-level pass, not the full structural audit)
- Auto-fix declaration: whatever intersection of `context-audit`'s detection IDs and the dispatcher's `auto_fix.whitelist`

What "light" means for this job — the checks that run:

- Boundary violations (a data point's content crossing its declared EXCLUSIVELY_OWNS)
- Broken cross-references (fast — use the index already rebuilt by `index-health` earlier today if that ran)
- Missing required frontmatter fields on active docs
- Stale content markers (TODO / FIXME / OUTDATED / DEPRECATED in active docs)
- Obvious duplication — same heading text in two or more active data points

What it does NOT check (those are `architecture-review`'s job):

- Full ownership-relationship analysis (BUILDS_ON, REFERENCES, PROVIDES graph walk)
- `last-updated` staleness reasoning (is the 90-day-old doc actually stale, or just stable?)
- Completeness gaps (what topics have no data point at all)
- Ecosystem drift (skills, hooks, state.json)

If the underlying `context-audit` skill does not currently distinguish light vs full, pass `depth: light` anyway — a future version of that skill should respect it; today's version will just run what it runs. Record in `notes` whether light mode was honoured.

Collect from context-audit:

- Findings by severity (critical / high / medium / low)
- Specific doc+issue pairs
- Any fixes it applied (should match the auto_fix.whitelist)

### 4. Scan inbox aging

List `docs/_inbox/*` (one level — do not recurse into `docs/_inbox/sessions/` which is auto-managed).

For each file, compute: `days_since_mtime`.

- `≥ 7 days` → action item: `"inbox aged: {filename} ({N} days) — triage (process, archive, or discard)"`
- `3-6 days` → informational, include count only in notes, no action item
- `< 3 days` → ignore

### 5. Propose lessons consolidation

Read `.claude/quality/ecosystem/lessons.json`.

For the dispatcher version of this job, DO NOT invoke the full `lessons-consolidate` skill (that's a heavy interactive pass). Instead, run its "dry-run" / report-only mode:

- Any two lessons with `similarity > threshold` → propose merge (action item)
- Any lesson whose `tags` reference a skill/concept that no longer exists → propose archival (action item)
- If `lessons.json` has grown past a size heuristic (e.g. 50+ active lessons) → recommend user run the full `lessons-consolidate` skill

If `lessons-consolidate` has a `--report-only` flag, use it. If not (v1.0-1.1 versions), do the similarity check inline with a naive cosine or keyword-overlap approach and note `"lessons check: naive — run the lessons-consolidate skill for authoritative results"`.

### 6. Classify output

`auto_fixed`: anything `context-audit` fixed in-scope (should be small — it's also bounded by the whitelist).

`actions_needed`: ordered by severity (critical first, then high, then the inbox-aged items, then lessons consolidation proposals). Cap at 10 items; if truncated, add a note.

### 7. Determine verdict

- 🟢 `green` — no critical or high findings, no aged inbox, no lesson consolidation pressure
- 🟡 `amber` — some high or medium findings, or 1-3 aged inbox items
- 🔴 `red` — any critical finding (missing frontmatter on active doc, ownership boundary violation, broken invariant), or 5+ aged inbox items
- ⚠️ `error` — audit skill or script crashed

### 8. Emit result

```json
{
  "verdict": "red",
  "findings_count": 7,
  "auto_fixed": [
    "eof-newline in docs/competitive-positioning.md"
  ],
  "actions_needed": [
    "CRITICAL: docs/new-playbook.md has no frontmatter — add template or move to _inbox",
    "HIGH: brand-identity.md and brand-voice.md both claim ownership of 'tone of voice' — resolve boundary",
    "inbox aged: docs/_inbox/Q1-notes.md (14 days) — triage",
    "inbox aged: docs/_inbox/competitor-call.md (9 days) — triage",
    "lessons: lesson 'always regen wake-up' and 'wake-up regen after moves' overlap — merge?"
  ],
  "notes": "Light pass across 5 clusters. Lesson check naive — full consolidate skill recommended within 30 days (48 active lessons)."
}
```

---

## What this job does NOT do

- Does not fix content or boundary issues — these are judgement calls
- Does not archive, process, or discard inbox files — user decides
- Does not merge or retire lessons — proposes only
- Does not do deep ownership / completeness / relationship analysis — that's `architecture-review`'s scope
- Does not compute a health score — `architecture-review` owns that output
