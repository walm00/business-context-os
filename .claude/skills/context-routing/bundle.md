# /context bundle

Task-driven cross-zone routing. Reads a profile from
`_context.task-profiles.yml.tmpl` (or per-repo override) and resolves a
structured bundle envelope from `.claude/quality/context-index.json`.

For the prose reference and the full per-profile schema, see [`context-routing.md`](../../../docs/_bcos-framework/architecture/context-routing.md).

## When to use

- "I'm about to write a market report — give me the context bundle"
- "Plan a customer engagement — what do we know, by zone, with freshness?"
- "Run a competitor audit — pull every relevant doc with source-of-truth ranking"
- For zone-scoped sugar (wiki only), use `/wiki bundle <profile>` which routes to the same backend.

## Invocation

```
python .claude/scripts/context_bundle.py --profile <profile-id> \
    [--profiles-path PATH] \
    [--index PATH | --index-root PATH] \
    [--resolve-conflicts [--dry-run]] \
    [--verify-coverage [--dry-run]] \
    [--json]
```

| Flag | Meaning |
|---|---|
| `--profile <id>` | Required. Profile identifier (e.g., `market-report:write`, `engagement:plan`). Must exist in the catalog. |
| `--profiles-path PATH` | Override the catalog path. Defaults to per-repo `docs/.context.task-profiles.yml`, falling back to the framework template. |
| `--index PATH` | Read context-index.json from this path. Defaults to `.claude/quality/context-index.json`. |
| `--index-root PATH` | Build a fresh in-memory index from the given docs root. Useful for tests / fixtures. Mutually exclusive with `--index`. |
| `--resolve-conflicts` | **Explicit opt-in** to LLM conflict resolution (D-10). Requires `--dry-run` until the LLM client wiring lands. |
| `--verify-coverage` | **Explicit opt-in** to LLM coverage verification (D-10). Requires `--dry-run` until the LLM client wiring lands. |
| `--dry-run` | With either `--resolve-conflicts` or `--verify-coverage`, record the opt-in (`escalations: [...-dry-run]`) without firing the LLM. |
| `--json` | Emit JSON to stdout (otherwise human-readable). |
| `--cross-repo` | Force cross-repo fallthrough on. Sibling bundles appear in a separate `cross-repo-hits` block — never merged into `by-zone` / `by-family`. See "Cross-repo retrieval" below. |
| `--no-cross-repo` | Force cross-repo fallthrough off. |

## Output envelope

```jsonc
{
  "profile-id": "market-report:write",
  "generated-at": "2026-05-04T19:00:00Z",
  "by-zone": {
    "active": [{ "path": "docs/pricing.md", "name": "Pricing", ... }, ...],
    "wiki":   [...],
    "planned":[...]
  },
  "by-family": {
    "competitor-data": [...],
    "market-data":     [...],
    "pricing-data":    [...]
  },
  "freshness": [
    { "path": "docs/competitors.md", "verdict": "past-threshold", "days-since": 80, "threshold": 30 }
  ],
  "source-of-truth-conflicts": [
    {
      "family": "pricing-data",
      "shared-owns": "tier-names",
      "candidates": [
        { "path": "docs/pricing.md", "zone": "active", ... },
        { "path": "docs/_planned/pricing-redesign.md", "zone": "planned", ... }
      ],
      "resolution": "docs/pricing.md",
      "resolved-by": "rank",
      "reason": "highest-ranked zone: active"
    }
  ],
  "missing-perspectives": [],
  "traversal-hops": [
    { "from": "docs/_wiki/pages/stripe-integration.md", "edge": "builds-on", "to": "docs/pricing.md", "depth": 1 }
  ],
  "unsatisfied-zone-requirements": [],
  "stale-claims-by-doc": {
    "docs/cost-structure.md": [
      {
        "section": "Cost taxonomy",
        "last-confirmed": "2025-10-15",
        "see-evidence": "docs/_collections/reports/audit-2025-02-to-2026-04/theo_financial_report.meta.md",
        "note": "October 2025 baseline; Q1-Q2 2026 actuals captured in audit run, not yet folded back."
      }
    ]
  },
  "escalations": []
}
```

`stale-claims-by-doc` is a separate top-level block (per lesson L-019: extend with new blocks, never fold). It is populated only for pool docs that declare `stale-claims:` in their frontmatter. Consumers that don't care about per-claim staleness ignore the block; the core envelope shape is unchanged. See [document-standards.md "Stale Claims"](../../../docs/_bcos-framework/methodology/document-standards.md) for the frontmatter shape.

## Resolution semantics (mechanical, deterministic)

For each candidate doc in declared profile zones:

1. **Group by zone** — every hit lands in `by-zone[<zone-id>]`.
2. **Group by family** — apply each profile family's pattern (`cluster=X`, `tag=Y`, `page-type=Z`, `type=W`); matching docs land in `by-family[<family>]`.
3. **Walk edges** — from each seed doc, BFS over typed edges declared by `traversal-hints` (e.g., `builds-on`) up to `depth-cap`. Hops accumulate in `traversal-hops`.
4. **Freshness** — per-hit verdict (`fresh` / `stale` / `past-threshold` / `unknown` / `fresh` for `never`-zones) using profile's per-zone thresholds.
5. **Conflicts** — hits in the same family that share ≥1 `EXCLUSIVELY_OWNS` key across different zones are CLEAR-violation candidates. Resolved by the profile's `source-of-truth-ranking`: highest-ranked zone wins. Ties at the top zone-rank produce `resolved-by: unresolved`.
6. **Coverage** — families failing `coverage-assertions[<family>]` min-count surface in `missing-perspectives`.
7. **Unsatisfied zones** — required zones absent from the corpus surface in `unsatisfied-zone-requirements`.

Same fixture index → byte-identical bundle (modulo `generated-at`). Latency target: <1s for typical bundles on a 200-doc corpus.

## Cross-repo retrieval — three-stage filter

Same three-stage filter as `/context search` (see [`search.md`](search.md#cross-repo-retrieval--three-stage-filter) for the canonical write-up). Local first across all zones; peek only if local insufficient; deep-fetch only on peek-strong.

**Local-insufficient for bundles** — bundle's "hits" view for the gate evaluator is the flat list of all hits across `by-family` plus `unsatisfied-zone-requirements`. Default `miss_signals` (`["zero-hit", "low-coverage"]`) effectively reduces to "all families are empty" for bundles, since the hits don't carry the `coverage` field. To trigger on missing required zones too, add `"unsatisfied-zone-requirements"` to the portfolio's `miss_signals`.

**Peek query tokens** — derived from the profile's families (pattern values + family names). Falls back to splitting the profile-id on non-alphanumerics for unknown profiles. The peek looks for these tokens in sibling metadata fields.

**Deep-fetch result shape — same as before** (peek-strong path):

```jsonc
{
  "profile-id": "incident-response:write",
  "by-zone": { ... },         // local hits only
  "by-family": { ... },       // local hits only
  "cross-repo-hits": {        // only present on peek-strong → deep-fetch
    "executions-os": {
      "by-zone": {"wiki": [{"path": "...", "source-repo": "executions-os", ...}]},
      "by-family": { ... },
      "unsatisfied-zone-requirements": []
    }
  },
  "cross-repo-status": {
    "attempted": true,
    "trigger": "auto-fallthrough",
    "umbrella-id": "my-portfolio",
    "local-insufficient-signal": "zero-hit",
    "siblings-queried": [{"id": "executions-os", "hits": 1, "took-ms": 14}],
    "siblings-skipped": []
  }
}
```

**Peek-marginal shape** (no deep-fetch, suggestions only):

```jsonc
{
  "by-zone": { ... },
  "by-family": { ... },
  "cross-repo-status": {"attempted": false, "trigger": "peek-marginal", ...},
  "cross-repo-suggestions": {
    "peek-strength": "marginal",
    "suggestions": [
      {"sibling-id": "executions-os", "match-count": 2, "authoritative-match-count": 1,
       "top-citations": ["executions-os:wiki:incident-response"],
       "reasons": ["tags-match"]}
    ]
  }
}
```

**Why sibling bundles never merge into local `by-zone` / `by-family`**: bundles drive downstream decisions like source-of-truth conflict resolution. Auto-merging a sibling's `pricing-data` hits would let a sibling implicitly override local authority. Conservative separation lets the calling agent opt into cross-repo data deliberately.

**Framework default**: in a repo without `.bcos-umbrella.json`, no cross-repo I/O fires. See [`docs/_bcos-framework/architecture/cross-repo-retrieval.md`](../../../docs/_bcos-framework/architecture/cross-repo-retrieval.md) for the full contract.

## D-10 strict — no auto-trigger

Two LLM-touching paths exist behind explicit flags. Both also currently require `--dry-run`:

- `--resolve-conflicts` — LLM picks the winner among `resolved-by: unresolved` candidates. Until the LLM client is wired in, non-dry-run raises `LLMEscalationNotImplementedError` with a clear message; the CLI exits non-zero.
- `--verify-coverage` — LLM verifies the bundle covers declared perspectives (prose-level coverage). Same flag-gating.

The default mechanical run **never** auto-fires either path. If you want LLM help, ask for it explicitly.

## Examples

```
# Cross-zone bundle for a market-report write task:
python .claude/scripts/context_bundle.py --profile market-report:write

# JSON for programmatic consumption:
python .claude/scripts/context_bundle.py --profile engagement:plan --json

# Build from a fixture root (testing):
python .claude/scripts/context_bundle.py --profile market-report:write \
    --index-root .claude/scripts/fixtures/context_bundle \
    --profiles-path .claude/scripts/fixtures/context_bundle/profiles.yml

# Opt into conflict resolution (dry-run only for now):
python .claude/scripts/context_bundle.py --profile market-report:write \
    --resolve-conflicts --dry-run
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `profile not found: <id>` | Profile id mismatch | Run `python .claude/scripts/load_task_profiles.py` to list available profiles |
| `unsatisfied-zone-requirements` populated | Required zone absent in this repo | Initialize the zone (e.g., `/wiki init`) or mark the requirement optional in your repo override |
| All conflicts `resolved-by: unresolved` | Profile has no `source-of-truth-ranking` or candidates share the top zone | Add ranking to the profile or refine `EXCLUSIVELY_OWNS` boundaries |
| `--resolve-conflicts` exits non-zero | Non-dry-run while LLM wiring is deferred | Pass `--dry-run` to validate the opt-in envelope; full path lands in a follow-up |

## Tests

`python .claude/scripts/test_context_capability.py` — 20 tests covering loader, validator, envelope shape, by-zone / by-family grouping, conflict detection + ranking, coverage gaps, traversal walking, freshness verdicts, determinism, empty-corpus handling, D-10 escalation gating, and CLI smoke.
