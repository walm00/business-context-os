# Job: auto-fix-audit

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly (Friday)
**Nature:** mechanical — read-only audit on the self-learning ladder; surfaces amber findings, never auto-disables (v0.1)
**Boundary:** node — own-repo paths only (no `../`, no absolute paths outside `$CLAUDE_PROJECT_DIR`, no sibling-repo names). Enforced by dispatcher Step 4a preflight.

<!-- emits-finding-types: machine-readable; consumed by .claude/scripts/test_finding_type_coverage.py (P1_007). Schema: docs/_bcos-framework/architecture/typed-events.md -->
```yaml
emits-finding-types:
  - rule-reversal-spike
  - rule-downstream-error
```

---

## Purpose

The auto-fix auditor is the safety brake on the self-learning ladder. Every other phase pushes toward more autonomy — preselect (P5) → auto-apply (P7) → silent (P8). This job pushes back: it watches the resolution log for signals that a learned rule (or a silently-applied auto-fix) is producing trouble, and surfaces a card recommending demotion.

**v0.1 ships ONE check** (reversal-rate). P7 adds Check 2 (validation-failure auto-disable — the only check with auto-action authority) and Check 3 (downstream-error correlation). P8 adds Checks 4–5 (semantic drift via opt-in LLM, and cross-rule flap detection).

Per [implementation-plan.md §D-04](../../../../docs/_planned/autonomy-ux-self-learning/implementation-plan.md): the auditor is what makes the ladder safe to be aggressive. Without this brake, any push toward "silent" would be a gamble.

---

## Steps

### 1. Load the resolution log

Read `.claude/quality/ecosystem/resolutions.jsonl`. Each row carries the 14-field schema; we care about `ts`, `finding_type`, `action_taken`, and `outcome` for Check 1.

### 2. Run Check 1 — reversal rate

For every `(finding_type, action_taken)` rule with at least 3 applied events in the last 7 days:

- Count `n_applied` = events with `outcome="applied"` inside the 7-day window
- Count `n_reverted` = events with `outcome="reverted"` inside the same window
- `reversal_rate` = `n_reverted / n_applied`

If `reversal_rate > 5%`, emit a `rule-reversal-spike` finding with:

```json
{
  "finding_type": "rule-reversal-spike",
  "verdict": "amber",
  "emitted_by": "auto-fix-audit",
  "finding_attrs": {
    "rule_id": "<finding_type>::<action_taken>",
    "underlying_finding_type": "<finding_type>",
    "underlying_action_taken": "<action_taken>",
    "n_applied": 12,
    "n_reverted": 2,
    "reversal_rate": 0.1667,
    "window_days": 7,
    "threshold_percent": 5
  },
  "suggested_actions": ["demote-rule", "show-evidence", "keep-silent"]
}
```

The cockpit renders this as an amber card titled "Rule reversal rate high" with three buttons matching the suggested actions.

### 3. Emit findings into the digest

The dispatcher folds the auditor's `findings[]` into the daily digest sidecar like any other job's emission. Findings persist in `docs/_inbox/daily-digest.json` until the user resolves them.

### 4. Verdict

- `green` if no findings
- `amber` if any findings (all v0.1 findings are amber-tier)
- `red` is reserved for future Check 2 (validation-failure auto-disable) where the auditor takes auto-action

---

## What this job does NOT do (v0.1)

- Does **not** auto-disable any rule. Reversal-rate findings are recommend-only per D-04. Only Check 2 (P7_005, validation-failure correlation with N≥5 across ≥3 distinct files in 24h) ever auto-disables — and that's a different signal class.
- Does **not** modify `learned-rules.json` directly. Demotion happens when the user clicks the [Demote] button, which calls `promote_resolutions.add_to_blocklist(rule_id)` and triggers regeneration.
- Does **not** read git history. v0.1 detects reversals via the `outcome="reverted"` field on resolution events; it doesn't try to correlate with `git diff -p` output. P7 may upgrade to per-target pairing using `applied_diff_hash`.

---

## Implementer notes

- The `outcome="reverted"` event is recorded by the cockpit's "Undo" button (which calls `unmark_resolved()` and writes a new resolution row with `outcome="reverted"`) and by the future P7_003 auto-apply countdown's manual-revert path.
- Reversal-rate calculation excludes `outcome="skipped"` (dry-run handler results from P3 v0.1) and `outcome="errored"` rows. Only applied/reverted move the rate.
- The `REVERSAL_MIN_N` constant in `auto_fix_audit.py` keeps the auditor quiet for rules with too-small samples (single reversal of 2 events would be a 50% spurious spike). v0.1 uses 3.

## Outputs

Paths this job writes that are eligible for dispatcher auto-commit on a tick where this job runs with verdict ≠ skipped. Globs allowed; resolved against `git status --porcelain` (rename destinations only). Empty list = job writes nothing committable on its own (findings flow to the global digest sidecar, which is already in `GLOBAL_ALLOWED`).

- (none)

## See also

- [`auto_fix_audit.py`](../../../scripts/auto_fix_audit.py) — implementation
- [`auto-fix-whitelist.md`](./auto-fix-whitelist.md) — silent fix tier (also subject to this auditor's reversal check)
- [`headless-actions.md`](./headless-actions.md) — one-click tier (also subject)
- [`docs/_bcos-framework/architecture/typed-events.md`](../../../../docs/_bcos-framework/architecture/typed-events.md) — `rule-reversal-spike` enum entry
