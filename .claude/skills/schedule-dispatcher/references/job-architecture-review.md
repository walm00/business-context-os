# Job: architecture-review

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** monthly (1st of month)
**Nature:** deep — full-architecture CLEAR audit + ecosystem sanity + lessons retention review

---

## Purpose

The monthly "zoom all the way out" pass. Covers every cluster, every data point, and the `.claude/` ecosystem itself. Produces a health score and a three-item priority list for the coming month.

This job is expensive — budget 10-15 minutes of session time. It's the ONE job in the dispatcher that's allowed to be slow.

---

## Steps

### 1. Rebuild the document index

`python .claude/scripts/build_document_index.py`. Required — this job relies on an up-to-date inventory.

### 2. Full CLEAR audit across ALL clusters

Invoke the `context-audit` skill with:

- Scope: `all`
- Depth: `full`
- Report format: structured (not interactive prompts)

Unlike `audit-inbox` which is one cluster per week, this sweeps every active data point. Expect findings. Do not cap them aggressively — this is the annual-checkup equivalent; bulk is expected and useful.

Collect:

- Total findings, by severity
- Findings per cluster (for the health-score calculation)
- Any fixes applied (bounded by `auto_fix.whitelist` — same rule as every other job)

### 3. Ecosystem check

**Refresh state.json from disk first.** This is the marker-based source of truth — it classifies directories with `SKILL.md` as skills, with `AGENT.md` as agents, and anything else (e.g., utility shell-script directories) as `inventory.utilities`. The refresh is on the `auto_fix.whitelist` as `ecosystem-state-refresh`, so apply it now if the whitelist allows:

```
python .claude/scripts/refresh_ecosystem_state.py
```

If the script changed anything, capture its summary line for `auto_fixed` (e.g. `state.json refreshed: +1 skill(s)`). If the user disabled `ecosystem-state-refresh` in their whitelist, run it with `--dry-run` instead and surface the proposed change as an action item.

**Then run the structural integration audit:**

```
python .claude/scripts/analyze_integration.py --ci
```

(If either script is missing, skip and note in `notes` — this can happen on very old installs that haven't run `update.py` since the framework added the script.)

`analyze_integration.py --ci` checks for:

- Skills/agents/hooks/scripts on disk that are not wired into `install.sh`, `settings.json`, `state.json`, or `.gitignore`
- Cross-reference gaps where existing files mention paths that no longer exist

Treat any remaining gaps as action items at HIGH severity. (The state.json freshness gap is now self-healing via the refresh step above and should not appear here.)

### 4. Lessons retention review

Read `.claude/quality/ecosystem/lessons.json`. For each lesson:

- **Age check** — lesson created more than 6 months ago
- **Relevance check** — lesson references a concept/skill that still exists
- **Violation check** — is there any signal in recent diary that this lesson is still being violated (worth keeping) or hasn't been violated in months (can retire)?

Surface three subsets:

- Retirement candidates — stale, not referenced, older than 6 months
- Sharp-still — recently violated, keep prominent
- Merge candidates — multiple lessons saying the same thing

These all become action items. Never auto-modify `lessons.json` from this job — it's too important to touch without user approval.

### 5. Compute a health score

A rough 0-10 score based on:

- 10 points baseline
- -1 per critical finding (max -5)
- -0.5 per high finding (max -3)
- -0.25 per medium finding (max -1.5)
- -1 if `analyze_integration.py --ci` reports unresolved coverage gaps (e.g. a hook on disk not registered in `settings.json`). The state.json refresh in Step 3 already heals inventory drift, so drift in *that* file alone never costs a point.
- -1 if `lessons.json` has > 50 active lessons and no recent consolidation
- +1 if zero critical, zero high findings AND no integration coverage gaps (bonus for clean month)

Floor at 0, cap at 10. Integer-round to one decimal.

The purpose is NOT to be statistically rigorous — it's to give the user a month-over-month trend line they can glance at. Any score below 7 warrants attention; any score below 5 is a red flag.

### 6. Propose three priorities for next month

Based on the findings, pick three concrete recommendations the user should do before next month's review. Format each as: *"{verb} {target} — {why it matters}"*.

Examples:

- "Resolve the brand-identity / brand-voice ownership overlap — two data points claiming the same topic causes answer divergence."
- "Process the 4 inbox items older than 30 days — they're preventing the _inbox signal from meaning anything."
- "Review and consolidate 12 overlapping lessons — lessons.json is getting noisy, value per read is dropping."

If there are fewer than three worth flagging, surface fewer. Do not manufacture work.

### 7. Classify output

- `auto_fixed` — whatever the audit fixed in-scope
- `actions_needed` — all findings by severity, with the three priority recommendations at the TOP prefixed `PRIORITY 1/2/3:`
- `notes` — the health score + the one-line strategic takeaway ("what's the system getting right this month?")

### 8. Determine verdict

- 🟢 `green` — health score ≥ 8, zero critical, zero integration coverage gaps (state.json refresh from Step 3 doesn't count as a finding when the auto-fix succeeded — that's a healed state, not drift)
- 🟡 `amber` — health score 5-7, some findings, no criticals
- 🔴 `red` — health score < 5, OR any critical finding, OR `analyze_integration.py --ci` reports unresolved coverage gaps, OR the state.json refresh failed to apply (whitelist disabled OR script error)
- ⚠️ `error` — audit or integration analysis crashed

### 9. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 23,
  "auto_fixed": [
    "missing-last-updated in 3 files",
    "eof-newline in 2 files"
  ],
  "actions_needed": [
    "PRIORITY 1: resolve brand-identity / brand-voice ownership overlap",
    "PRIORITY 2: process 4 inbox items aged > 30 days",
    "PRIORITY 3: consolidate 12 overlapping lessons",
    "HIGH: customer-insights.md last-updated 124 days ago — confirm still current",
    "HIGH: messaging-framework references non-existent 'brand-personality.md'",
    "MEDIUM: ... (17 more findings)"
  ],
  "notes": "Health score: 7.2/10. System strength this month: inbox processing steady (3 files triaged, none aged). Focus next month: ownership boundaries."
}
```

---

## What this job does NOT do

- Does not fix anything outside the whitelist — even "obvious" fixes stay as action items at this depth
- Does not modify `lessons.json` — proposals only
- Does not re-audit a cluster just because it was flagged red — that's next week's `audit-inbox` work
- Does not produce a health score more precise than one decimal — false precision is worse than no score

State.json IS modified by this job — via the whitelisted `ecosystem-state-refresh` fix (see Step 3). Treating state.json as a derived artifact rather than authored truth is a deliberate design choice; see lesson L-INIT-20260404-009.
