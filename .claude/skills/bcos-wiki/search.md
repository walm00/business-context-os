# /wiki search

Zone-scoped sugar for `/context search --zone wiki`. Identical backend, identical
output schema, identical D-10 escalation rules — just narrower by default.

For the full mechanical-search spec see [`context-routing/search.md`](../context-routing/search.md).

## When to use

- "What wiki pages do we have on <topic>?"
- "Search the wiki for <query>"
- Power-user value: faster than cross-zone search (smaller candidate set), narrower hit list, lower latency.
- For cross-zone search across `active`, `wiki`, `planned`, `collections`, etc., use `/context search` instead.

## Invocation

```
python .claude/scripts/context_search.py --query "<query>" --zone wiki [other flags]
```

`/wiki search <query>` is a thin wrapper around the cross-zone backend with `--zone wiki` pre-applied. Every flag from `/context search` works identically:

| Flag | Meaning |
|---|---|
| `--query` | Required search query. |
| `--top-k N` | Maximum hits returned. Default `10`. |
| `--token-budget N` | Aggregate summary token budget. Default `8000`. |
| `--semantic [--dry-run]` | **Explicit opt-in** to LLM query reformulation (D-10). No auto-trigger. |
| `--json` | Emit JSON to stdout. |
| `--index PATH` | Override path to `context-index.json`. |

The `--zone` flag is fixed to `wiki` for this command — passing a different value defeats the sugar; use `/context search` directly instead.

## Output

Same shared schema as `/context search` — see [`context-routing/search.md`](../context-routing/search.md#output). Every hit lives in the wiki zone; `zones-searched` is `["wiki"]`; `zones-skipped-not-present` lists every other declared zone (since they're filtered out, not searched).

Citation IDs follow the `wiki:<slug>` pattern, where `<slug>` is the file stem (e.g., `wiki:linkedin-tone`, `wiki:stripe-integration`). Stable across whitespace edits.

## Examples

```
# Wiki-only search:
python .claude/scripts/context_search.py --query "linkedin tone" --zone wiki

# Top hit only, JSON output:
python .claude/scripts/context_search.py --query "stripe" --zone wiki --top-k 1 --json

# Opt into semantic reformulation (no LLM fires under --dry-run):
python .claude/scripts/context_search.py --query "fuzzy phrase" --zone wiki --semantic --dry-run
```

## Guard rails (inherited)

### Wiki-zone guard

Like every `/wiki` subcommand, **search reads but never writes**. It does not create pages, does not refresh indexes, does not touch `_wiki/.config.yml`. Pure read.

If `docs/_wiki/.config.yml` is missing in the current repo, the search returns an empty hit list with `wiki` listed in `zones-skipped-not-present`. No error. The user can run `/wiki init` to scaffold the zone first.

### D-10 strict — no auto-trigger

The mechanical path is always the default. No 0-hit fallback, no hidden LLM cost. `--semantic` is the only escalation lever and it is explicit. See [`context-routing/SKILL.md`](../context-routing/SKILL.md#guard-rails) for the full rule.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty hits, `wiki` in `zones-skipped-not-present` | Wiki zone not initialized in this repo | `/wiki init` |
| Empty hits, wiki present | No wiki page matches the tokens | Try broader tokens, or `--semantic` opt-in, or `/context search` for cross-zone |
| Same query, drifting scores | Floating-point rounding | Stability checks should compare citation-ids, not scores |

## Tests

Wiki-search behaviour is exercised under `test_context_search.py` (`test_zone_filter_limits_results`, plus the shared schema and citation-stability tests). Adding `/wiki search`-specific behaviour later? Add the case to `test_context_search.py` and reference it from the wiki capability test if it touches wiki-zone surface.
