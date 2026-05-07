# Sub-Agent Isolation Fixtures (P3)

Inputs for `test_wiki_fetch.py` — the P3 acceptance tests for sub-agent
isolation, contract shape, and cumulative token budgeting.

## Files

| File | Used by | What it exercises |
|---|---|---|
| `expected-result.json` | contract test | The exact shape `wiki-fetch` returns: `{title, h2-outline, key-sentences, suggested-page-type, suggested-cluster, raw-file-pointer, citation-banner-fields, error?}`. The validator in `_wiki_fetch_contract.py` rejects malformed outputs. |
| `cumulative-budget-cases.json` | budget guard test | A list of `(N, projected-result-tokens, max-context, expected-decision)` tuples driving the budget guard. Decisions: `parallel` (cumulative ≤ 80%), `serial` (cumulative > 80%). |

The scale test (`test_rejects_result_carrying_full_url_body`) used to ship a 504KB committed fixture; it now synthesizes a ~100k-token body in `setUpClass` so the assertion runs against a real big body without bloating the repo.

## Why these are minimal

P3 is mostly a wiring + isolation discipline phase. The actual sub-agent
dispatch happens via Claude's Task tool at runtime, not via Python scripts.
The Python-side tests verify:

1. The agent definition file exists with the documented contract shape.
2. The dispatch wiring in run.md / refresh.md / promote.md / create.md
   references `wiki-fetch` and the Task tool (string-grep assertion).
3. The cumulative budget calculator returns the right serialize-or-parallel
   decision for representative inputs.
4. The result schema validator accepts the canonical output and rejects
   malformed variants.

End-to-end "main context never holds full HTML" assertions live in the
runtime conversation log — the Python harness can't observe Claude's
context window directly. The closest mechanical proxy is "the wiring docs
explicitly call the Task tool, not inline fetch."
