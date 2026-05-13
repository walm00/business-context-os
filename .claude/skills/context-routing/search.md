# /context search

Mechanical cross-zone search over the canonical context-index.json. Returns
ranked hits in a shared schema; never re-walks `docs/`. **Never fires the LLM
implicitly** (D-10 strict — see SKILL.md guard rails).

## When to use

- "Find every doc about <topic> across the repo"
- "Show me wiki pages and plans on <topic>"
- "What's our latest on <topic>, ranked by source-of-truth?"
- Use `/wiki search <query>` for zone-scoped sugar over this same backend.

## Invocation

```
python .claude/scripts/context_search.py --query "<query>" \
    [--zone <zone-id>] \
    [--top-k N] \
    [--token-budget N] \
    [--semantic [--dry-run]] \
    [--explain] \
    [--json]
```

| Flag | Meaning |
|---|---|
| `--query` | Required. The search query. Tokenised, lowercased, stopwords dropped. |
| `--zone <zone-id>` | Restrict to a single zone. Valid IDs: `active`, `framework`, `wiki`, `wiki-internal`, `collection-manifest`, `collection-sidecar`, `collection-artifact`, `inbox`, `planned`, `archive`, `custom-optout`, `generated`. |
| `--top-k N` | Maximum hits returned. Default `10`. |
| `--token-budget N` | Aggregate summary token budget across hits. Default `8000`. Hits are truncated with `truncated: true` when exceeded. |
| `--semantic` | **Explicit opt-in** to LLM query reformulation (D-10). No auto-trigger. **Currently requires `--dry-run`** — the 3-candidate reformulation path is specified but the LLM client wiring is deferred. Non-dry-run `--semantic` exits non-zero with a clear error rather than silently running mechanical search. |
| `--dry-run` | With `--semantic`, record the opt-in (`escalation: semantic-dry-run`) without firing the LLM. The only currently supported `--semantic` mode. |
| `--explain` | Include a per-hit `score-breakdown` with matched/missing terms, field scores, match tier, and boosts. |
| `--json` | Emit JSON to stdout (otherwise human-readable). |
| `--index PATH` | Override the index path. Defaults to `.claude/quality/context-index.json`. |
| `--cross-repo` | Force cross-repo fallthrough on. Consults sibling repos registered with the same `.bcos-umbrella.json`. Mutually exclusive with `--no-cross-repo`. See "Cross-repo retrieval" below. |
| `--no-cross-repo` | Force cross-repo fallthrough off. Defeats per-portfolio opt-in for this one call. |

## Output

```jsonc
{
  "query": "stripe billing",
  "zones-searched": ["active", "wiki"],
  "zones-skipped-not-present": ["collection-artifact", "inbox"],
  "hits": [
    {
      "slug": "pricing",
      "zone": "active",
      "page-type": null,
      "cluster": "Revenue",
      "summary": "Pricing — (Revenue) — Subscription pricing tiers and billing through Stripe.",
      "builds-on": [],
      "freshness-days": 3,
      "last-reviewed": null,
      "score": 1.97,
      "citation-id": "active:pricing",
      "truncated": false,
      "score-breakdown": {
        "match-tier": "T5",
        "matched-terms": ["billing", "stripe"],
        "missing-terms": [],
        "field-scores": {"title": 0.0, "filename": 0.0, "path": 0.0, "headings": 0.0, "meta": 9.1, "ownership": 7.2, "body": 0.0},
        "phrase-matches": [],
        "coverage": 1.0,
        "role-boost": 1.5,
        "relation-boost": 0.0,
        "freshness-boost": 1.49,
        "final": 36.4
      }
    }
  ],
  "escalation": null
}
```

`score-breakdown` appears only when `--explain` or API `explain=true` is set.

## Ranking model (mechanical, deterministic)

For each candidate doc:

1. Tokenize query and indexed fields with conservative normalization: case-folding, punctuation/hyphen splitting, stopword removal, and entity possessive/plural alignment (`Arnold`, `Arnolds`, `Arnold's`).
2. Score fields separately with weighted `tf × idf`:
   - title/name highest
   - filename/path/path-tags very high
   - headings high
   - tags/type/status/cluster medium
   - DOMAIN / EXCLUSIVELY_OWNS / STRICTLY_AVOIDS medium-low
   - first paragraph lower
3. Assign a match tier before sorting by raw score:
   - `T5`: exact phrase or all query terms in title/name
   - `T4`: all terms covered by filename/path/entity fields
   - `T3`: all terms matched anywhere in indexed fields
   - `T2`: phrase or majority match in authoritative fields
   - `T1`: partial match
4. Apply zone-priority boost from the registry's `source-of-truth-role`:
   - `canonical` ×1.5, `derived` ×1.2, `evidence` ×1.1, `system` ×1.0, `future` ×0.9, `historical` ×0.7, `opted-out` ×0.5.
5. Apply relation/freshness boosts inside the same match tier. Freshness is a tie-breaker signal; it cannot make a one-term partial match outrank a title/path/entity all-term match.
6. Sort by match tier, then boosted score, then stable citation id; take top-K; format hits.

Latency target: <500ms on the 52-doc canonical corpus. Deterministic given a fixed corpus — same query at the same git ref returns byte-identical output (modulo `score` floats that are deliberately rounded).

## Examples

```
# Cross-zone:
python .claude/scripts/context_search.py --query "stripe billing"

# Wiki only:
python .claude/scripts/context_search.py --query "linkedin tone" --zone wiki

# Plans + active only via two calls (zone filter is single-zone today):
python .claude/scripts/context_search.py --query "launch" --zone active
python .claude/scripts/context_search.py --query "launch" --zone planned

# JSON for programmatic consumption:
python .claude/scripts/context_search.py --query "pricing" --top-k 3 --json

# Explain why the ranker ordered hits:
python .claude/scripts/context_search.py --query "arnolds nda" --explain --json

# Opt into semantic reformulation, dry-run (no LLM call):
python .claude/scripts/context_search.py --query "fuzzy phrase" --semantic --dry-run

# Non-dry-run --semantic currently exits non-zero (LLM wiring deferred):
python .claude/scripts/context_search.py --query "fuzzy phrase" --semantic
# error: --semantic requires --dry-run for now. ...

# Cross-repo fallthrough (force on for one call):
python .claude/scripts/context_search.py --query "incident response" --cross-repo

# Cross-repo fallthrough (force off, overriding per-portfolio opt-in):
python .claude/scripts/context_search.py --query "incident response" --no-cross-repo
```

## Cross-repo retrieval — three-stage filter

When the local repo registers an umbrella (`.bcos-umbrella.json`) and the user opts in (`retrieval.auto_fallthrough: true`, or the `--cross-repo` flag), search consults sibling BCOS repos through a three-stage filter — never blindly. Hierarchy: this-repo across all zones first; cross-repo last.

### Stage 1 — local search

The default BM25 ranker runs against this repo's `context-index.json` (all zones in one pass). If the top hit is T5 + full coverage, the search is **complete** and stops here. No peek. No `cross-repo-suggestions` field emitted.

### Stage 2 — peek (only if local insufficient)

If the local result fires any signal in `retrieval.miss_signals` (default `["zero-hit", "low-coverage"]`), the framework scans each sibling's `context-index.json` for **metadata matches only**:

| Field class | Fields |
|---|---|
| Authoritative | `name`, `filename`, `exclusively_owns`, `page_type` |
| Supporting | `tags`, `headings`, `cluster` |

No body text. No BM25. No LLM. Per-sibling match counts feed into the strength classifier:

- **strong**: one sibling has `≥peek_min_strong_matches` (default 1) authoritative-field matches AND no rival has any authoritative match → **deep-fetch** (Stage 3).
- **marginal**: any sibling has metadata matches but doesn't meet strong → emit `cross-repo-suggestions`, **no deep-fetch**.
- **none**: no sibling has any metadata match → silent skip.

### Stage 3 — deep-fetch (only on peek-strong)

Each sibling's `context-index.json` is loaded, optionally filtered by `projects[].exposes` globs, and the same BM25 ranker runs against it. Sibling hits get a `<sibling-id>:` prefix on their `citation-id` (e.g. `executions-os:wiki:incident-response`). Local hits sort ahead of sibling hits on tie — local authority is preserved.

### Output envelope additions

| Field | When present |
|---|---|
| `cross-repo-status` | Always, when `.bcos-umbrella.json` exists. Reports the gate decision. |
| `cross-repo-suggestions` | Only when peek = marginal. Lists per-sibling metadata matches the calling agent could surface to the user. |

```jsonc
{
  "hits": [...],
  "cross-repo-status": {
    "attempted": true,                  // deep-fetch ran
    "trigger": "auto-fallthrough",      // see triggers below
    "umbrella-id": "my-portfolio",
    "local-insufficient-signal": "low-coverage",
    "siblings-queried": [{"id": "executions-os", "hits": 4, "took-ms": 23}],
    "siblings-skipped": [{"id": "stalled-repo", "reason": "timeout"}]
  },
  "cross-repo-suggestions": {           // only on peek = marginal
    "peek-strength": "marginal",
    "suggestions": [
      {"sibling-id": "executions-os", "match-count": 1, "authoritative-match-count": 1,
       "top-citations": ["executions-os:wiki:incident-response"],
       "reasons": ["name-match", "filename-match"]}
    ],
    "siblings-skipped": []
  }
}
```

### Trigger values

| `trigger` | Meaning | Did sibling data load? |
|---|---|---|
| `explicit-no` | User passed `--no-cross-repo` | No |
| `not-opted-in` | Umbrella present but no `retrieval` block | No |
| `local-sufficient` | Local hit was T5+full coverage; peek not invoked | No |
| `peek-empty` | Peek ran but no sibling had any metadata match | No |
| `peek-marginal` | Peek ran, suggestions emitted | No (suggestions only) |
| `auto-fallthrough` | Peek-strong → deep-fetch ran | Yes |
| `explicit-flag` | User passed `--cross-repo` → bypassed peek → deep-fetch | Yes |

### Graceful failure

A missing umbrella directory, malformed `projects.json`, slow sibling exceeding `per_sibling_timeout_ms` — every failure is a typed skip entry, never a raised error. The local result is always returned.

### Framework default

In a repo with no `.bcos-umbrella.json`, no cross-repo I/O ever fires. D-10 strict invariant preserved at framework level. The user flips it on per portfolio by adding a `retrieval` block; see [`docs/_bcos-framework/architecture/cross-repo-retrieval.md`](../../../docs/_bcos-framework/architecture/cross-repo-retrieval.md).

## D-10 strict — no auto-trigger

The mechanical path is **always** the default. The engine never decides on its own that the query is "too hard" and reaches for the LLM. If you want semantic reformulation, pass `--semantic` explicitly. Otherwise:

- 0-hit unstructured query → returns 0 hits with `escalation: null`. The caller decides whether to retry with `--semantic` or refine the query.
- 0-hit structured query → returns 0 hits. Same rule. No fallback.

Auto-triggers were specifically removed in the wiki-missing-layers cleanup pass (2026-05-04). If you find code that auto-fires the LLM, that's a regression.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `index-missing` warning, empty hits | `.claude/quality/context-index.json` not built | Run `python .claude/scripts/context_index.py --write` |
| All zones in `zones-skipped-not-present` | Empty repo (no docs in expected zones) | Expected. Initialize the relevant zones first. |
| Same query returns slightly different scores | Floating-point rounding across runs | Check the test asserts citation-id stability, not score equality. |
| `--zone <foo>` returns nothing for an existing zone | Zone id typo | Run `python .claude/scripts/load_zone_registry.py` to list valid zone IDs. |

## Tests

`python .claude/scripts/test_context_search.py` — regression coverage for schema, field-aware ranking, title/entity/all-term priority, zone filter, top-K cap, citation stability, D-10 escalation rules, empty-corpus handling, service wrapper behavior, and CLI smoke tests.
