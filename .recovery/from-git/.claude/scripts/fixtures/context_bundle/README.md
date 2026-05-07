# Context Bundle Fixtures (P5)

Inputs for `test_context_capability.py` — task-driven cross-zone routing.

## Profiles (in `profiles.yml`)

| Profile | What it tests |
|---|---|
| `market-report:write` | Cross-zone bundle pulling competitor / market / pricing families from active + wiki + planned. Used to verify by-zone, by-family, freshness verdicts, traversal-hops, and source-of-truth ranking. |
| `engagement:plan` | Live-data-leaning profile. Used to verify per-profile precedence overrides — for engagement work, derived (wiki) supports but never beats canonical (active). |

## Fixture corpus (under `docs/`)

| Path | Zone | Cluster | Notes |
|---|---|---|---|
| `docs/pricing.md` | active | Revenue | Stripe billing data point. Fresh. Conflicts with `_planned/pricing-redesign.md` on tier names. |
| `docs/competitors.md` | active | Competitive | Competitor positioning. Stale (older than 30d). |
| `docs/_wiki/pages/market-overview.md` | wiki | Market | Market explainer. Reviewed recently. |
| `docs/_wiki/pages/stripe-integration.md` | wiki | Revenue | Builds-on `pricing.md`. Reviewed recently. |
| `docs/_planned/pricing-redesign.md` | planned | Revenue | Proposes new tier names; status: draft. The conflict with active `pricing.md` is the test target — ranking must put active first. |

## What the test asserts

- Bundle resolution per profile produces a deterministic envelope.
- `by-zone` groups hits per zone correctly.
- `by-family` groups hits per declared content family.
- `freshness` reports per-hit verdict (`fresh` / `stale` / `past-threshold`) against profile thresholds.
- `source-of-truth-conflicts` flags `pricing.md` vs `pricing-redesign.md` (same family, ≥1 overlapping `exclusively_owns`).
- `missing-perspectives` flags families whose `min-count` isn't met.
- `traversal-hops` records edges followed (e.g., `stripe-integration` → `pricing` via `builds-on`).
- `unsatisfied-zone-requirements` populates when an `optional: false` profile zone is absent (or empty).
- Default mechanical run never invokes LLM (D-10 strict). `--resolve-conflicts` and `--verify-coverage` are explicit opt-in only.
- Determinism: running twice on the same fixture index produces byte-identical bundle output (modulo `generated-at`).
