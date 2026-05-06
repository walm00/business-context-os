# Triage confidence scoring

How `_wiki_triage.classify()` (schema 1.2) assigns a `confidence ∈ [0.0, 1.0]`
to each finding. Mechanical-only — no LLM. Same inputs always produce the same
score (D-09).

## Common gates (apply before any class fires)

| Gate | What it checks | Pass condition |
|---|---|---|
| Authority gate | `_effective_authority()` returns the right value for the class | A: not `canonical-process` · C: `canonical-process` · D: `external-reference` |
| Cluster gate (default) | Both pages share the same `cluster:` | Equal cluster strings |
| Cluster gate (`--strict`) | Cross-cluster comparison allowed | confidence × **0.7** multiplier (D-04) |
| Numeric-fact gate | Both pages contain at least one number-with-unit token | non-empty token sets after `_NUMERIC_FACT_RE` |
| Content-overlap gate | Pages cover similar ground (Jaccard over content tokens) | A,D: ≥ 0.10 · C: ≥ 0.20 |

Numeric-fact tokens preserve the unit. `"10 minutes"`, `"2 minutes"`, `"$30"`,
`"2.9%"`, `"30¢"` are distinct tokens. Bare numbers from numbered lists are
stripped before tokenization.

## Class A — authority asymmetry

**Trigger:** new wiki page (non-canonical-process) with at least one numeric
fact diverging from a numeric fact on its `builds-on:` canonical target.

```
confidence = min(1.0, 0.55 + content_overlap)
```

Auto-action: `annotation` when `confidence ≥ 0.85` (AUTO_APPLY_CONFIDENCE).

Worked example — `stripe-conflicts-with-canonical.md` (declares `2.9% + 30¢`)
vs `financial-operations.md` (declares `2.5% + 25¢`):
- Content overlap ≈ 0.40 (both pages talk about Stripe rates)
- `0.55 + 0.40 = 0.95` → auto-apply annotation

## Class B — temporal-supersession candidate

**Trigger:** two pages share the same `source-url` and same cluster but
have different temporal signals (`source-published`, falling back to
`last-fetched`, falling back to `created`).

```
confidence = 0.92  (constant — same URL is a strong, unambiguous signal)
```

Auto-action: `supersession-link` when `confidence ≥ 0.85` (always for B).

Direction is determined by date: the page with the later temporal signal
becomes the successor (declares `supersedes:`); the earlier one becomes the
predecessor (gets `superseded-by:` written by the bidirectional helper).

## Class C — true contradiction

**Trigger:** two pages with `authority: canonical-process` in the same
cluster, both within `DEFAULT_REVIEW_CADENCE_DAYS` of `last-reviewed`, with
diverging numeric facts in BOTH directions (each page has at least one number
the other doesn't).

```
confidence = min(1.0, 0.60 + content_overlap × 0.40)
```

Auto-action: never (`auto_action = None`). Class C **always** interrupts the
user via `AskUserQuestion`, regardless of confidence. The score is reported
in the prompt so the user can judge how strong the signal is.

Worked example — `deploy-runbook-a.md` (`Wait 10 minutes`) vs
`deploy-runbook-b.md` (`Wait 2 minutes`):
- Content overlap ≈ 0.85 (nearly identical body)
- `0.60 + 0.85 × 0.40 = 0.94`

## Class D — canonical-drift suggestion

**Trigger:** new external-reference fact diverges from a `builds-on:`
canonical doc, AND that canonical doc's `last-updated` is older than
`STALE_CANONICAL_DAYS` (180 days, ≈ 6 months).

```
age_bonus  = min(0.20, age_days / 1825)             # caps at 0.20 once canonical is ≥ 5 years old
confidence = min(1.0, 0.50 + content_overlap + age_bonus)
```

Auto-action: never. Class D suggests human review; ingest never edits
canonical `docs/*.md` files. The daily `wiki-canonical-drift` dispatcher job
runs the same scan and emits the same finding type — ingest-time emission
catches drift as it lands; the daily job catches drift that accumulates.

## Where the constants live

| Name | Module | Default | Notes |
|---|---|---|---|
| `STALE_CANONICAL_DAYS` | `_wiki_triage.py` | 180 | Class D fires once canonical doc is older than this |
| `DEFAULT_REVIEW_CADENCE_DAYS` | `_wiki_triage.py` | 180 | Class C requires both pages reviewed within this window |
| `AUTO_APPLY_CONFIDENCE` | `_wiki_triage.py` | 0.85 | Below this, findings queue for review |
| `STRICT_CROSS_CLUSTER_MULTIPLIER` | `_wiki_triage.py` | 0.7 | D-04 multiplier for `--strict` cross-cluster scans |

Tune by editing the module constants (no schema change needed) and re-running
the regression suite (`test_wiki_triage_detector.py`).

## What triage does NOT do

- No LLM call (D-09). Body-content fuzzy contradiction detection (e.g., "we
  ship in 24 hours" vs "two business days") is opt-in via a deferred
  `--semantic` flag, not in this plan.
- No edits to canonical `docs/*.md` files. Class A annotations are wiki-side
  only. Class D emits findings only.
- No cross-cluster comparison by default (D-04). Use `strict=True` to opt in,
  with the 0.7 confidence multiplier applied.
- No deduplication of findings across multiple ingests. The dispatcher's
  `wiki-canonical-drift` job runs daily and is idempotent on stable input,
  so the digest stays clean.
