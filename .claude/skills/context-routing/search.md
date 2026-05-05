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
| `--json` | Emit JSON to stdout (otherwise human-readable). |
| `--index PATH` | Override the index path. Defaults to `.claude/quality/context-index.json`. |

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
      "truncated": false
    }
  ],
  "escalation": null
}
```

## Ranking model (mechanical, deterministic)

For each candidate doc:

1. Tokenize query and the doc's *searchable text* (name + filename + cluster + type + page-type + status + DOMAIN + tags + EXCLUSIVELY_OWNS + STRICTLY_AVOIDS + path-tags).
2. BM25-style score: per-term `tf × idf` summed across query tokens.
3. Apply zone-priority boost from the registry's `source-of-truth-role`:
   - `canonical` ×1.5, `derived` ×1.2, `evidence` ×1.1, `system` ×1.0, `future` ×0.9, `historical` ×0.7, `opted-out` ×0.5.
4. Apply gentle recency boost based on `age_days` (`last-updated` distance).
5. Sort descending; take top-K; format hits.

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

# Opt into semantic reformulation, dry-run (no LLM call):
python .claude/scripts/context_search.py --query "fuzzy phrase" --semantic --dry-run

# Non-dry-run --semantic currently exits non-zero (LLM wiring deferred):
python .claude/scripts/context_search.py --query "fuzzy phrase" --semantic
# error: --semantic requires --dry-run for now. ...
```

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

`python .claude/scripts/test_context_search.py` — 15 assertions covering schema, ranking, zone filter, top-K cap, citation stability, D-10 escalation rules, empty-corpus handling, and CLI smoke tests.
