# Context Search Fixtures

Synthetic corpus across three zones (`active`, `wiki`, `planned`) with distinct
vocabularies so `test_context_search.py` can assert ranking, filtering, and
citation behaviour.

## Documents

| Path | Zone | Distinguishing signals |
|---|---|---|
| `docs/pricing.md` | active | `name: Pricing`, cluster `Revenue`, tags `[pricing, stripe, billing]` |
| `docs/laura.md` | active | `name: Laura - Sales Lead`, cluster `People`, tags `[sales, role, lead]` |
| `docs/_wiki/pages/linkedin-tone.md` | wiki | `name: LinkedIn Tone`, cluster `Marketing`, tags `[linkedin, tone, social, voice]` |
| `docs/_wiki/pages/stripe-integration.md` | wiki | `name: Stripe Integration`, cluster `Revenue`, tags `[stripe, integration, billing, api]` |
| `docs/_planned/launch-plan.md` | planned | `name: Launch Plan`, cluster `Marketing`, tags `[launch, marketing, gtm]` |

## What the test asserts

- Query `"stripe billing"` ranks `pricing.md` and `stripe-integration.md` above
  `laura.md` / `linkedin-tone.md` / `launch-plan.md`.
- `--zone wiki` returns only wiki hits.
- `--top-k 1` returns exactly one hit.
- Citation IDs are stable across runs (slug-derived).
- `--semantic` is opt-in only; no auto-trigger on 0-hit queries (D-10 strict).
- Empty corpus returns empty hit list with `zones-skipped-not-present` populated.

The test points `context_search.py` at a fixture-built `context-index.json` so
the corpus is deterministic — no dependency on the live repo state.
