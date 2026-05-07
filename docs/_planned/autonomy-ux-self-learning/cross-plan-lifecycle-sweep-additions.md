# Cross-plan note — lifecycle-sweep additions (2026-05-06)

This note records the strictly-additive changes the `lifecycle-sweep` plan
made to the autonomy-ux-self-learning registries. Schema-version stayed at
`1.0.0` — no breaking changes — but the typed-event enum and headless-action
registry both grew. Future autonomy-ux work needs to know about these
additions to avoid namespace collisions.

## What lifecycle-sweep added

### 4 new finding_types

Added under a new `### lifecycle-sweep (4)` block in
[`docs/_bcos-framework/architecture/typed-events.md`](../../_bcos-framework/architecture/typed-events.md):

| ID | Emitter | Cockpit role |
|---|---|---|
| `lifecycle-trigger-fired` | `lifecycle-sweep` | preselect card with `lifecycle-route-*` action |
| `lifecycle-body-marker-confirmed` | `lifecycle-sweep` | preselect card (high confidence — body marker passed) |
| `lifecycle-route-ambiguous` | `lifecycle-sweep` | amber takeover — needs user judgement |
| `lifecycle-orphan-active` | `lifecycle-sweep` | flag-only — never auto-routed |

`finding_attrs` shapes were registered in the same file alongside the existing
shape table.

### 4 new headless-actions

Added at the bottom of
[`.claude/skills/schedule-dispatcher/references/headless-actions.md`](../../../.claude/skills/schedule-dispatcher/references/headless-actions.md)
with full schema (applies-to, type, label, reversible-by, telemetry-event,
requires-write, default-trigger):

| Action ID | Type | Telemetry event | Reversible by |
|---|---|---|---|
| `lifecycle-route-archive` | `move` | `lifecycle-archived` | `git mv` back to original path |
| `lifecycle-route-wiki` | `move` | `lifecycle-promoted-to-wiki` | `/wiki archive {slug}` + `git revert` |
| `lifecycle-route-collection` | `move` | `lifecycle-routed-to-collection` | `git mv` back + remove manifest row |
| `lifecycle-fold-into` | `metadata-edit` | `lifecycle-folded` | `git revert` of the fold commit |

Handlers registered in
[`bcos-dashboard/headless_actions.py`](../../../.claude/scripts/bcos-dashboard/headless_actions.py)
under the same naming convention as the existing 12 actions.

### Burn-in protocol

All four `lifecycle-route-*` IDs are **defined** in the auto-fix-whitelist
reference but **NOT shipped** in `schedule-config.template.json`'s `auto_fix.whitelist`. They need three independent gates before silent-tier
auto-fix can fire:

1. `.claude/quality/lifecycle-routing.yml` `global.surface_only` = `false`
2. The action ID added to `auto_fix.whitelist` in user's `schedule-config.json`
3. The matching routing rule's `confidence-tier` = `1` (no default rule ships at tier 1)

Until ALL three gates pass, the four actions only fire from the dashboard
"Run now" or one-click card flow — never from the silent dispatcher tier.

## What this means for autonomy-ux next steps

- **P5 promote_resolutions.py needs no code change.** The auto-pick logic
  reads `(finding_type, action_taken)` pairs from `resolutions.jsonl`
  generically; new lifecycle pairs flow through naturally once they
  accumulate ≥3 events at consistency=1.0.
- **P6 auditor needs no code change.** Reversal-rate detection is also
  generic over `(rule_id, action_taken)`.
- **P8 silent tier (when it lands)** must respect the lifecycle burn-in
  gates — silent-fire is ONE of three gates, not the only one. Adding a
  lifecycle rule to the silent tier should require all three gates plus
  the silent-tier criteria from autonomy-ux P8.

## What the 4 reserved IDs are

For the autonomy-ux v0.2 docs:

```
finding_types:    lifecycle-trigger-fired
                  lifecycle-body-marker-confirmed
                  lifecycle-route-ambiguous
                  lifecycle-orphan-active

headless actions: lifecycle-route-archive
                  lifecycle-route-wiki
                  lifecycle-route-collection
                  lifecycle-fold-into

telemetry events: lifecycle-archived
                  lifecycle-promoted-to-wiki
                  lifecycle-routed-to-collection
                  lifecycle-folded
```

Reservation date: 2026-05-06. Owning plan: `docs/_planned/lifecycle-sweep/`.
