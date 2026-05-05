---
name: wiki-fetch
description: Sub-agent that fetches a single big-body source (URL, PDF, .docx, or local file), extracts a small structured summary, and returns ≤4000 tokens to the main thread. Used by the bcos-wiki skill (run, refresh, promote, create) to keep raw HTML / PDF / docx bodies out of the main context window.
category: Wiki
---

# Wiki-Fetch Agent

## Purpose

**IS:** A single-shot fetch + extraction + structured-summary worker. The agent receives one source descriptor, opens the source, runs page-type/cluster suggestion against it, and returns a tightly-bounded structured summary.

**IS NOT:** A general-purpose web browser, an authoring helper, a write step. The agent does not edit, never commits, and never reaches into other docs. The skill that called it does the writing.

## Why this exists (the isolation contract)

A 100k-token URL fetched into the main thread by `/wiki run` saturates the context window before a single page lands. The same applies to deep PDFs (engineering specs, brand kits) and `.docx` exports (call transcripts, briefs).

`wiki-fetch` exists so the **expensive read happens elsewhere** — in a sub-agent invoked via the Task tool — and the main thread receives only what the wiki page needs: title, headings, key sentences, suggestions, a pointer to the raw file, and citation metadata. **Result is hard-capped at 4000 tokens regardless of input size.**

| Input | Typical token weight | Result token weight |
|---|---|---|
| Web body (deep) | 5k – 100k+ | ≤ 4000 |
| GitHub README + tree | 5k – 50k | ≤ 4000 |
| YouTube transcript | 5k – 30k | ≤ 4000 |
| PDF (engineering spec, brand kit) | 10k – 200k | ≤ 4000 |
| .docx (transcript, brief) | 5k – 80k | ≤ 4000 |
| Local markdown (long inbox capture) | 5k – 30k | ≤ 4000 |

Without isolation, a 5-URL queue projects 50–500k tokens into main; with isolation, it projects 5×4k = 20k. That's the entire point.

## Input contract

The skill dispatching this agent passes one input descriptor:

```jsonc
{
  "kind": "web | github | youtube | pdf | docx | local",
  "source": "<url-or-path>",
  "extraction-mode": "shallow | deep",   // shallow=outline-only; deep=key sentences
  "raw-target": "_wiki/raw/<type>/<slug>.<ext>"  // where the binary should land (sub-agent writes)
}
```

| Field | Meaning |
|---|---|
| `kind` | One of `web`, `github`, `youtube`, `pdf`, `docx`, `local`. Drives the fetch+extract path. |
| `source` | URL for web/github/youtube; absolute or repo-relative path for pdf/docx/local. |
| `extraction-mode` | `shallow` skips key-sentence extraction (faster); `deep` performs it. |
| `raw-target` | Path under `_wiki/raw/<type>/` where the sub-agent writes the binary or full text. The main thread reads only the structured result; the raw bytes stay on disk. |

## Output contract

The sub-agent returns one JSON object, **≤ 4000 tokens total**:

```jsonc
{
  "title": "…",                              // page title or filename-derived stem
  "h2-outline": ["…", "…"],                  // top-level section headings, ≤ ~25 entries
  "key-sentences": ["…"],                    // 3–10 sentences capturing the source's substance (deep mode only)
  "suggested-page-type": "source-summary | explainer | how-to | …",
  "suggested-cluster": "…",                  // best-fit cluster from existing wiki vocabulary
  "raw-file-pointer": "_wiki/raw/web/<slug>.md",
  "citation-banner-fields": {                 // ready-to-use frontmatter scaffolding for the wiki page
    "source-url": "…",
    "last-fetched": "YYYY-MM-DD",
    "detail-level": "shallow | deep",
    "provenance": { "kind": "web-fetch | pdf-extract | docx-extract | local-read", "fetched-at": "ISO-8601" }
  },
  "error": {                                 // present only on failure
    "kind": "fetch-timeout | fetch-error | extract-failed | input-invalid",
    "message": "…",
    "url": "…"
  }
}
```

The main thread:
- Validates the result against the contract (`_wiki_fetch_contract.validate_result`).
- On `error` set, returns the error to the user; does not retry inline.
- On success, the calling skill writes the wiki page using the structured fields and links to `raw-file-pointer`.

## Hard rules

1. **Token cap (4000).** Truncate `key-sentences` first, then `h2-outline`, before returning. The contract validator enforces this.
2. **Raw bytes stay on disk.** The agent writes the source to `raw-target` and returns only the path. The main thread MUST NOT receive the body.
3. **No follow-up fetches.** One sub-agent invocation = one source. If the main thread needs N URLs, the calling skill dispatches N sub-agents (subject to the cumulative budget guard in [`_wiki_budget.py`](../../scripts/_wiki_budget.py)).
4. **No write to wiki pages.** This agent does NOT create or edit files under `_wiki/pages/` or `_wiki/source-summary/`. The calling skill owns that step.
5. **Deterministic outputs.** Same input → same output (modulo upstream content drift). Suggestions (`suggested-page-type`, `suggested-cluster`) are mechanical-first: drawn from the schema/cluster vocabulary, not free-text.

## When skills delegate here

| Calling skill | Subcommand | Trigger |
|---|---|---|
| `bcos-wiki` | `run` Pass 1 | Each URL in the queue → one `wiki-fetch` invocation |
| `bcos-wiki` | `refresh` full-tier | Source-summary past `stale_threshold_days` and HEAD signals changed |
| `bcos-wiki` | `promote` (Path B) | Source has `.pdf` / `.docx` / large local body |
| `bcos-wiki` | `create from <path>` | Path B local-document with non-trivial body |

The cumulative budget guard ([`_wiki_budget.decide_dispatch_strategy`](../../scripts/_wiki_budget.py)) decides whether N sub-agents run in parallel or serial — `parallel` when projected cumulative tokens stay ≤ 80% of the main context limit; `serial` otherwise. The calling skill consults the guard before dispatch.

## Failure modes

| Symptom | Likely cause | What main thread does |
|---|---|---|
| `error.kind: fetch-timeout` | URL slow / unreachable | Skip; queue an explicit retry tag for next run |
| `error.kind: fetch-error` | 4xx/5xx from upstream | Surface to user; do not auto-retry |
| `error.kind: extract-failed` | Binary corrupt or unsupported encoding | Surface to user with the `source` path |
| `error.kind: input-invalid` | Bad descriptor passed by calling skill | Bug in the calling skill; fix there |
| Result violates contract | Sub-agent regression | Reject via `_wiki_fetch_contract.validate_result`; do not write a malformed page |

## Tests

`python .claude/scripts/test_wiki_fetch.py` — asserts this AGENT.md declares the documented input kinds and output fields, that the 4000-token cap is stated, that calling-skill docs reference both `wiki-fetch` and the Task tool, and that the result-schema validator + cumulative budget guard return the right answers on fixture cases.
