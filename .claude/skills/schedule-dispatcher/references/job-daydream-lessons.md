# Job: daydream-lessons

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly (Monday)
**Nature:** reflective — strategic daydream + lessons capture + session pruning

---

## Purpose

The weekly step-back. Asks: *"Did anything change this week that the context architecture hasn't caught up with?"* Also harvests lessons from recent sessions into the institutional-knowledge file, and prunes old session/diary noise.

This job is inherently judgement-heavy. It produces suggestions, not fixes — almost everything ends up as an action item.

---

## Steps

### 1. Load orientation

Read, in order:

1. `docs/.wake-up-context.md` (if present)
2. `docs/.session-diary.md` (if present)
3. `docs/current-state.md` (if present)
4. `docs/table-of-context.md` (if present)

Missing files are not fatal — just reduce the context available for reflection.

### 2. Rebuild the document index

Run:

```
python .claude/scripts/build_document_index.py
```

This ensures the reflection has current inventory. Non-fatal if it fails — note and continue.

### 3. Invoke the `daydream` skill

The existing `daydream` skill handles the actual 4-phase reflection (What Changed → Reflect → Imagine → Capture). Do NOT re-implement its logic here.

Pass the daydream skill these inputs:

- Mode: `weekly` (cheap pass, not deep)
- Scope: `docs/` user content only (it already excludes `_bcos-framework/`)
- Maximum output: 5-8 bullets in the reflection phase
- Suppress the interactive "save to file?" prompts — the dispatcher is non-interactive

Collect from daydream:

- List of observations (what changed, what's drifting)
- List of specific doc updates recommended
- Any concrete "one highest-value next action" suggestion

### 4. Capture lessons

Read `.claude/quality/ecosystem/lessons.json`. Check recent session captures (`.claude/quality/sessions/` if present).

For each candidate lesson:

- If it clearly duplicates an existing lesson → note as `action-needed` item: *"candidate lesson X overlaps existing lesson Y — consolidate?"*
- If it's a net-new lesson → note as action-needed: *"capture new lesson: {one-line summary}"*
- Do NOT write to `lessons.json` directly — that's the `lessons-consolidate` skill's job, invoked separately. This job only *surfaces* candidates.

### 5. Prune sessions and diary

Run these two scripts, capturing their summaries:

```
python .claude/scripts/prune_sessions.py
python .claude/scripts/prune_diary.py
```

These are write operations, but they're documented safe housekeeping (keeping recent entries, archiving old ones). They count as auto-fixed *only* if `prune-sessions` and `prune-diary` are on the `auto_fix.whitelist`.

**IMPORTANT:** These IDs are not on the default whitelist. The dispatcher WILL skip them unless the user has explicitly added them. By default, this job only *reports* "sessions/diary would prune N entries — run manually if you want that cleaned up."

(Proposal for Phase 2: add `prune-sessions` and `prune-diary` to the default whitelist once we have one production run showing they behave. Do not bake them in without evidence.)

### 6. Classify output

Split daydream results into:

- `auto_fixed` — empty unless specific low-stakes cleanups were done
- `actions_needed` — the reflective observations, lesson candidates, and recommended doc updates
- `notes` — the "highest-value next action" line, verbatim

Keep `actions_needed` to a maximum of 8 items. If daydream produced more, pick the top 8 by impact and note in `notes`: *"(+N more observations — see full daydream output)"*.

### 7. Determine verdict

- `green` — zero observations, clean week (rare and suspicious; note this in the report)
- `amber` — 1-5 observations, all of routine significance
- `red` — one or more observations of strategic significance (e.g. a data point claims a fact that current-state contradicts; a whole cluster feels stale)
- `error` — daydream skill crashed or wake-up context was unreadable

### 8. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 4,
  "auto_fixed": [],
  "actions_needed": [
    "daydream: brand-identity.md claims 'early-stage' but current-state is growth — reconcile",
    "daydream: customer-insights has no mention of segment added in Q1 sessions — update",
    "lesson candidate: 'ask before archiving' — overlaps existing lesson, consider merging",
    "lesson candidate: 'always regen wake-up after big doc moves' — new, worth capturing"
  ],
  "notes": "Highest-value next action: reconcile brand-identity vs current-state stage claim."
}
```

---

## What this job does NOT do

- Does not edit data point content (`context-ingest` or manual edits do that)
- Does not commit lessons to `lessons.json` (that's `lessons-consolidate`)
- Does not archive, split, or merge data points (those are user decisions)
- Does not replace the user's reading of the wake-up context — it complements it

This job is the "widen your lens once a week" routine. If it never finds anything for three weeks, that's a signal to extend its frequency, not to delete it.
