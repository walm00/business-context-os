# Fixture wiki — wiki-authority-temporal plan

Self-contained mini-repo used by the four test files in `tests/test_wiki_*` for the
authority + temporal-supersession + 4-class-triage work.

Schema version pre-migration is **1.1**. Tests exercise the 1.1 → 1.2 migration
recipe (which adds `authority` defaults + temporal fields).

## Fixture layout

```
docs/
├── financial-operations.md            Canonical: Stripe negotiated rate (2.5% + 25¢)
├── api-pricing-reference.md           Canonical: 2024 OpenAI rates (deliberately stale, last-updated 2024-09-01)
└── _wiki/
    ├── .schema.yml                    schema-version: 1.1
    ├── pages/
    │   ├── deploy-runbook-a.md        Class C side: how-to, "wait 10 min for scan"
    │   ├── deploy-runbook-b.md        Class C side: how-to, "wait 2 min for scan"   ← conflicts with A
    │   └── glossary-tooling.md        glossary → internal-reference default
    └── source-summary/
        ├── stripe-pricing-2024.md     Class B chain head (2024 rate)
        ├── stripe-pricing-2025.md     Class B successor (2025 capture, same rate)
        ├── stripe-conflicts-with-canonical.md  Class A: claims 2.9% + 30¢ vs canonical 2.5% + 25¢
        ├── openai-rate-limits.md      Plain external-reference (control case)
        ├── openai-pricing-2026.md     Class D: $10/$30 (newer) vs canonical $30/$60 (2024-09 stale)
        └── acme-vendor-contract-extract.md   provenance.kind: local-document
```

## Triage cases this fixture exercises

| Case | Pages | Expected class | Confidence inputs |
|---|---|---|---|
| Stripe asymmetry | `stripe-conflicts-with-canonical` vs `financial-operations.md` | A — authority-asymmetry | high (same builds-on target, same key, divergent values) |
| Stripe timeline | `stripe-pricing-2024` + `stripe-pricing-2025` | B — temporal-supersession-candidate | high (same source-url, same cluster, different last-fetched) |
| Deploy runbooks | `deploy-runbook-a` + `deploy-runbook-b` | C — true-contradiction | high (both authority: canonical-process, same cluster, current last-reviewed, key="scan wait" diverges) |
| OpenAI pricing drift | `openai-pricing-2026` vs `api-pricing-reference.md` | D — canonical-drift-suggestion | high (canonical last-updated > 6mo, divergent values, same cluster) |

## Authority defaults this fixture exercises

| Page | Path | page-type | provenance.kind | Expected default authority |
|---|---|---|---|---|
| `deploy-runbook-a` | `pages/` | how-to | inbox-promotion | canonical-process |
| `deploy-runbook-b` | `pages/` | how-to | inbox-promotion | canonical-process |
| `glossary-tooling` | `pages/` | glossary | inbox-promotion | internal-reference |
| `stripe-pricing-2024` | `source-summary/` | source-summary | url-fetch | external-reference |
| `stripe-pricing-2025` | `source-summary/` | source-summary | url-fetch | external-reference |
| `stripe-conflicts-with-canonical` | `source-summary/` | source-summary | url-fetch | external-reference |
| `openai-rate-limits` | `source-summary/` | source-summary | url-fetch | external-reference |
| `openai-pricing-2026` | `source-summary/` | source-summary | url-fetch | external-reference |
| `acme-vendor-contract-extract` | `source-summary/` | source-summary | local-document | external-reference |

`external-evidence` is reserved for the rare case where a wiki page is verbatim
evidence (e.g., a regulatory filing extract). The mechanical default never
assigns it — must be explicit. None of the fixture pages declare it.

## How to run tests against this fixture

```bash
pytest tests/test_wiki_authority_field.py -v
pytest tests/test_wiki_temporal_fields.py -v
pytest tests/test_wiki_triage_detector.py -v
pytest tests/test_wiki_canonical_drift_job.py -v
```

Each test file points its `--root` at `tests/fixtures/wiki_authority_temporal/`.

## Mutability

Tests should treat this fixture as **read-only by default** — copy it into a
`tmp_path` per-test to mutate. The 1.1 → 1.2 migration test runs against a
copy; the original frontmatter stays at 1.1 so reruns work.
