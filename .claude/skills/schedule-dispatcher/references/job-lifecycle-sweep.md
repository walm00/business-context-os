# Job: lifecycle-sweep

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly (Friday)
**Nature:** classifier scan + (after burn-in) declarative auto-routing

<!-- emits-finding-types: machine-readable; consumed by .claude/scripts/test_finding_type_coverage.py. Schema: docs/_bcos-framework/architecture/typed-events.md -->
```yaml
emits-finding-types:
  - lifecycle-trigger-fired
  - lifecycle-body-marker-confirmed
  - lifecycle-route-ambiguous
  - lifecycle-orphan-active
```

---

## Preferred execution path (headless)

If `.claude/scripts/lifecycle_sweep.py` exists, run it directly:

```bash
python .claude/scripts/lifecycle_sweep.py
```

The script does the full classification, sidecar merge, diary append, and
(when burn-in flag is flipped) the auto-route execution in one shot. Add
`--apply` to override `surface_only` in the config; add `--dry-run` to print
the result JSON without touching disk; add `--rule <id>` to scope a single
routing rule. The chat-driven steps below are the fallback contract reference.

---

## Purpose

End-user docs accumulate without exit triggers. `index-health` detects orphans
by graph topology (no inbound xrefs) — that's a *symptom*, not a classification.
It can't distinguish a shipped audit from a live SOP, a sent proposal from a
draft, a research dump ready for wiki promotion from a canonical data point.

Lifecycle-sweep adds the missing classification: it walks the active / inbox /
planned zones, evaluates each doc against `.claude/quality/lifecycle-routing.yml`
rules, and emits typed-event findings for the dashboard cockpit. After a
2-week surface-only burn-in with 0 false-positives, the same classifications
become auto-routes via the headless-action handlers (`lifecycle-route-archive`,
`lifecycle-route-wiki`, `lifecycle-route-collection`, `lifecycle-fold-into`).

The job never replicates move logic. Wiki promotion delegates to `bcos-wiki`;
collection routing delegates to `context-ingest` Path 5; archive moves use
`git mv`; fold-into is chat-confirmed.

---

## Steps (fallback / contract reference)

### 1. Load routing config

Read `.claude/quality/lifecycle-routing.yml`:

- `global.surface_only` (default `true`) — when true, never mutate filesystem
- `global.scan_zones` (default `[active, inbox, planned]`)
- `global.min_age_days` (default `7`) — fresh docs are never routed
- `rules[]` — declarative rule table (9 default patterns)

### 2. Walk scan zones

For each `.md` file whose `_zone_for(path)` returns one of the configured
`scan_zones`, classify against the rule table.

### 3. Per-doc classification

For each doc:

- Parse frontmatter (nested-map aware — `lifecycle:` is a nested object).
- Strip frontmatter; scan body for canonical markers (`SENT:`, `DECISION:`,
  `RESOLVED:`, `OUTCOME:`, `PUBLISHED:`, `ABANDONED:`), staleness markers
  (`TODO`, `PENDING`, `DRAFT`, `FIXME`), and external URLs.
- Apply rules in declared order. Each rule's `body-markers` gate the match
  (role=`require` with negative confidence-boost = "if present, disqualify").
- Run each rule's `reality-checks` (git-log, sibling-file, target-exists,
  next-period, manifest-row, url-in-body). Failed checks honour the rule's
  `fail-action`: `ambiguous` emits `lifecycle-route-ambiguous`; `skip` tries
  the next rule; `warn` continues at lower confidence.
- First rule with all reality-checks passing wins; emit one of:
  - `lifecycle-body-marker-confirmed` (body marker drove the decision)
  - `lifecycle-trigger-fired` (frontmatter trigger drove the decision)

### 4. Orphan-active fallback

If no rule matches and the doc lives in `active` zone with no `lifecycle:`
field and age ≥ `min_age_days × 8`, emit `lifecycle-orphan-active`. This is
flag-only — never auto-routed.

### 5. Auto-route (only when surface_only=false AND verdict=auto)

Tier-1 confidence rules with passing reality-checks call:

- `lifecycle-route-archive` → `git mv {file} docs/_archive/{rule.bucket}/{name}`
- `lifecycle-route-wiki` → delegates to `bcos-wiki` `/wiki promote {slug}`
- `lifecycle-route-collection` → delegates to `context-ingest` Path 5
- `lifecycle-fold-into` → surfaces fold target; chat-confirms before edit

Default config ships with NO tier-1 rules. All 9 default rules are tier 2 or 3.
Tier 1 is reserved for post-burn-in promotion.

### 6. Determine verdict

- `green` — no findings (all docs leave_alone or only orphan-active flags)
- `amber` — findings exist (preselect cards or ambiguous)
- `red` — schema validation crashed or routing config malformed
- `error` — sweep crashed mid-walk

### 7. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 3,
  "auto_fixed": [],
  "actions_needed": [
    "lifecycle-body-marker-confirmed: docs/proposals/acme.md",
    "lifecycle-route-ambiguous: docs/notes/2026-04-15-sync.md",
    "lifecycle-orphan-active: docs/strategy/old-thesis.md"
  ],
  "notes": "Scanned 142 docs across active,inbox,planned; 3 routing finding(s); surface-only."
}
```

The script also writes to `docs/_inbox/daily-digest.json` (sidecar) and
`.claude/hook_state/schedule-diary.jsonl` (audit trail) so cards render
immediately and history accumulates.

---

## Auto-fixes allowed

Behind the burn-in protocol (default `surface_only: true`):

- `lifecycle-route-archive`
- `lifecycle-route-wiki`
- `lifecycle-route-collection`
- `lifecycle-fold-into`

All four are gated:

1. `lifecycle-routing.yml` `global.surface_only` must be `false`
2. The action ID must appear in `schedule-config.json` `auto_fix.whitelist`
3. The matching rule's `confidence-tier` must be `1` (no default rule ships at tier 1)

Until ALL three conditions hold, lifecycle-sweep emits findings only — the
user must click cards in the dashboard to apply each route. This protects
canonical docs from a misfired classifier in the early-feedback window.

---

## Cross-references

- Spec: [`docs/_bcos-framework/architecture/lifecycle-routing.md`](../../../../docs/_bcos-framework/architecture/lifecycle-routing.md)
- Trigger schema: [`docs/_bcos-framework/methodology/document-standards.md`](../../../../docs/_bcos-framework/methodology/document-standards.md) §"Lifecycle Triggers"
- Routing config: [`.claude/quality/lifecycle-routing.yml`](../../../quality/lifecycle-routing.yml)
- Headless actions: [`headless-actions.md`](./headless-actions.md) §`lifecycle-route-*` / §`lifecycle-fold-into`
- Plan: [`docs/_planned/lifecycle-sweep/`](../../../../docs/_planned/lifecycle-sweep/)
