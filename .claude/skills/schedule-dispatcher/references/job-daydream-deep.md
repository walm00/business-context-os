# Job: daydream-deep

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly (Wednesday)
**Nature:** strategic — deeper mid-week reflection on architectural fit
**Boundary:** node — own-repo paths only (no `../`, no absolute paths outside `$CLAUDE_PROJECT_DIR`, no sibling-repo names). Enforced by dispatcher Step 4a preflight.

<!-- emits-finding-types: machine-readable; consumed by .claude/scripts/test_finding_type_coverage.py. Schema: docs/_bcos-framework/architecture/typed-events.md -->
```yaml
emits-finding-types:
  - architecture-misalignment
  - datapoint-should-split
  - datapoint-should-merge
  - datapoint-should-retire
  - datapoint-missing
  - cluster-needs-restructuring
```

---

## Purpose

The "bigger lens" reflection. Where `daydream-lessons` asks *"what happened this week?"*, this job asks *"is our context architecture still the right shape for the business we actually are now?"*

It runs mid-week intentionally — separated from Monday's operational reflection so the output isn't blurred with immediate to-do thinking. Nothing about this job is mechanical.

---

## Steps

### 1. Load orientation

Same as `daydream-lessons` — read wake-up context, session diary, current-state, table-of-context.

Also read the `_bcos-framework/architecture/` layer if the user wants an architecture-aware reflection (optional — include only if `docs/_bcos-framework/architecture/architecture-canvas.md` or equivalent exists and has user-authored content, not just template placeholders).

### 2. Rebuild index + analyse cross-references

Run:

```
python .claude/scripts/build_document_index.py
python .claude/scripts/analyze_crossrefs.py
```

(If `analyze_crossrefs.py` does not exist in the installed version, skip it and note — the dispatcher should not fail on missing scripts.)

### 3. Invoke the `daydream` skill in deep mode

Pass these inputs:

- Mode: `deep` (longer pass, structural focus)
- Focus questions (in addition to whatever `daydream` covers by default):
  1. Is there a data point that should be *split* into two? (Topic has grown beyond single ownership.)
  2. Is there a data point that should be *merged* with another? (Excessive cross-referencing, overlapping domains.)
  3. Is there a data point that should be *retired*? (No longer reflects anything real.)
  4. Is there a data point that *doesn't exist yet* but should? (Knowledge lives in sessions but never made it into a doc.)
  5. Is there a cluster that needs restructuring? (Shape of the business has changed.)
- Output target: ONE concrete recommendation, not a list. The deep daydream is supposed to force a single "if I could do one thing this week" choice.

### 4. Classify output

- `auto_fixed` — always empty. This is strategic; nothing gets fixed automatically.
- `actions_needed` — zero or one item (the single concrete recommendation). If the daydream genuinely produced multiple equally-important candidates, list up to 3 but make the first one the lead.
- `notes` — the supporting rationale in 2-3 sentences.

If the deep daydream finds literally nothing worth changing, that's a real signal — emit `verdict: green` with `notes: "Architecture feels aligned — no structural change warranted this week."` Don't manufacture work.

### 5. Determine verdict

- 🟢 `green` — no structural change warranted; architecture is aligned with current reality
- 🟡 `amber` — one concrete recommendation that's worth considering but not urgent
- 🔴 `red` — a misalignment that's actively causing problems (e.g. two docs claim ownership of the same topic, or a cluster has grown far beyond what its structure can hold)
- ⚠️ `error` — daydream skill errored

### 6. Emit result

Example (green week):

```json
{
  "verdict": "green",
  "findings_count": 0,
  "auto_fixed": [],
  "actions_needed": [],
  "notes": "Architecture aligned. No data point needs splitting, merging, or retiring. Watch: customer-insights has grown 40% in last month — may warrant a split by segment next quarter."
}
```

Example (amber):

```json
{
  "verdict": "amber",
  "findings_count": 1,
  "auto_fixed": [],
  "actions_needed": [
    "consider splitting customer-insights.md — enterprise and SMB segments have diverged enough to warrant separate data points"
  ],
  "notes": "Rationale: 6 of last 8 sessions discussed enterprise and SMB in tandem but with contradictory framing. Split would clarify ownership. Not urgent — wait for one more session to confirm."
}
```

---

## What this job does NOT do

- Does not make structural changes itself — never splits, merges, or retires data points
- Does not duplicate `daydream-lessons` — this is strategic, that is operational
- Does not run if there's no meaningful context yet (< 5 data points) — in that case, emit `verdict: green` with `notes: "Context still forming — deep daydream skipped. Recommend disabling this job until you have at least 5 active data points."`
- Does not repeat last week's observations unless they're still relevant (check diary for last 3 runs — if same observation has been flagged 3 weeks running and nothing changed, escalate to `red`)

---

## Outputs

Paths this job writes that are eligible for dispatcher auto-commit on a tick where this job runs with verdict ≠ skipped. Globs allowed; resolved against `git status --porcelain` (rename destinations only). Empty list = job writes nothing committable on its own (findings flow to the global digest sidecar, which is already in `GLOBAL_ALLOWED`).

- (none)
