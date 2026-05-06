---
name: learning
description: "Manage the BCOS self-learning ladder: list learned rules, forget a rule, regenerate learned-rules.json from resolutions.jsonl. Mechanical-only — reads/writes derived artifacts; the actual learning happens via record_resolution.py at click time. Invoke with /learning."
trigger: "/learning"
version: "1.0.0"
last_updated: "2026-05-05"
authority-docs:
  - docs/_planned/autonomy-ux-self-learning/implementation-plan.md
  - docs/_bcos-framework/architecture/typed-events.md
  - .claude/skills/schedule-dispatcher/references/headless-actions.md
---

# /learning — Self-learning ladder management

Surface for inspecting and editing the rules BCOS has learned from your resolution clicks.

## How learning works (one paragraph)

Every dashboard card click and every headless action writes a row to `.claude/quality/ecosystem/resolutions.jsonl` via `record_resolution.py`. The `promote_resolutions.py` script reads that log, groups by `(finding_type, action_taken)`, and promotes pairs that meet tier thresholds into `.claude/quality/ecosystem/learned-rules.json`. The cockpit reads `learned-rules.json` to add a "✨ suggested" badge on cards where you've consistently picked the same action.

Tier thresholds:

| Tier | Required signal | Behavior |
|---|---|---|
| **preselect** (P5, current) | N≥3 + consistency=1.0 | Pre-fills the radio button on the matching card. Doesn't apply anything. |
| **auto-apply** (P7, future) | N≥5 + consistency≥0.9 + 14d span | Applies after a 10-second undo countdown. |
| **silent** (P8, gated) | N≥10 + consistency≥0.95 + 6w auditor-clean + opt-in | Fires without a card. Per-rule user click required to promote into this tier. |

`learning-blocklist.json` is the user's veto: rules in there are excluded from learned-rules.json regardless of evidence.

## Subcommands

### `/learning list`

Show all currently-learned rules grouped by tier with their evidence counts.

**Reads:** `.claude/quality/ecosystem/learned-rules.json`
**Side effects:** none
**Output:** table of `{rule_id, tier, n, consistency, last_observed, calendar_span_days}`.

If `learned-rules.json` is missing or empty, say so and suggest `/learning regenerate`.

### `/learning forget <rule-id>`

Add a rule to `learning-blocklist.json` and regenerate `learned-rules.json`. The rule disappears from the cockpit's "✨ suggested" badges immediately and won't be relearned even if more supporting evidence accumulates.

**Required arg:** `<rule-id>` in `<finding_type>::<action_taken>` form (e.g. `inbox-aged::inbox-aged-archive`).

**Mechanism:** call `promote_resolutions.add_to_blocklist(rule_id)` then `promote_resolutions.regenerate()`. Both are idempotent.

If the user supplies a partial ID (e.g. just `inbox-aged`), list matching rules and ask which they meant via `AskUserQuestion`.

### `/learning unblock <rule-id>`

Reverse of `forget`. Removes the rule from the blocklist; the next `regenerate` call will repromote it if its evidence still meets a tier threshold.

### `/learning regenerate`

Recompute `learned-rules.json` from `resolutions.jsonl` + `learning-blocklist.json`. Byte-stable: re-running with no event changes produces identical bytes.

**Mechanism:** `python .claude/scripts/promote_resolutions.py` (the module's `__main__` calls `regenerate()`).

Useful after a manual edit to `learning-blocklist.json`, or to force a refresh if the cockpit seems to have stale badges.

### `/learning evidence <rule-id>`

Show the resolution events backing a learned rule: timestamps, triggers, targets, NL commands. Helps you decide whether the rule was learned for the right reason.

**Mechanism:** filter `resolutions.jsonl` rows where `(finding_type, action_taken)` matches the rule_id parts. Sort by `ts`. Show last 10 by default; `--all` for the full log.

## Implementation pointers

- `.claude/scripts/promote_resolutions.py` — `compute_rules()`, `regenerate()`, `add_to_blocklist()`, `remove_from_blocklist()`, `is_blocked()`, `is_suggested()`
- `.claude/scripts/record_resolution.py` — `ResolutionEvent`, `record()`, `load_all_rows()`
- `.claude/quality/ecosystem/resolutions.jsonl` — append-only event log
- `.claude/quality/ecosystem/learned-rules.json` — derived artifact (regen byte-stable)
- `.claude/quality/ecosystem/learning-blocklist.json` — user veto list

## When to invoke proactively

If the user says any of:
- "forget that rule" / "stop suggesting X"
- "what has the system learned"
- "why is the cockpit suggesting X"
- "regenerate the learning data"
- "show me the evidence for rule X"

Run the matching subcommand directly. For ambiguous phrasings, use `AskUserQuestion` with `list / forget / regenerate` as options.

## Authority + invariants

- Never edit `resolutions.jsonl` directly — it's append-only authoritative.
- Never hand-edit `learned-rules.json` — it's regeneratable. If the user wants to change it, they edit `learning-blocklist.json` (or future per-rule overrides) and regen.
- A rule that's been blocklisted shouldn't reappear silently on the next regen.
