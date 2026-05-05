# /wiki run — process queue or ingest a single URL (Path A)

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`. The `ingest.md` shared pipeline is called as the final step.)

## Invocation forms

```
/wiki run                       ← batch: process every "Pending" item in queue.md
/wiki run <url> [tags]          ← single: queue if missing, then ingest
```

In **single-URL mode**, if the URL isn't already in `queue.md`, it's appended to `## Pending` (with any tags from the invocation) and then ingested. Tags are **ignored** if the URL is already pending — the existing line's tags win.

### Single-URL error cases (stop immediately)

| Condition | Message |
|---|---|
| URL under `## Completed` | "URL already ingested. To re-fetch, add `<!-- refresh -->` to its line and run `/wiki run`." |
| URL under `## Pending` with `<!-- skip -->` | "URL is marked `<!-- skip -->` — remove the tag from `queue.md` to process it." |

---

## Setup

Read `docs/_wiki/.config.yml` and extract: `domain`, `detail_level`, `source_types`, `auto_mark_complete`, `auto_lint`.

Set `today = current date YYYY-MM-DD`. Initialize an **ingest log** (in-memory list of `{pass, url, slug, outcome}` entries).

`mode = "single"` if invocation has a URL arg, else `"batch"`.

---

## Pass 0 — Auto-queue (single mode only)

Skip in batch mode.

Read `queue.md`:
- URL in `## Completed` → fire the error case above.
- URL in `## Pending` → use existing line as-is (ignore invocation tags).
- URL not present → append `- [ ] <url> <any tags from invocation>` to `## Pending`. Re-read `queue.md` after the mutation.

Continue to Pass 1.

---

## Pass 1 — Ingest pending items

Read `queue.md`. Collect all `- [ ] ...` lines under `## Pending`, in order.

In single mode, filter to just the target URL line.

For each line:

### 1. Skip check

If line contains `<!-- skip -->`: log `{pass: 1, url, outcome: skipped}`, leave the line, continue.

### 2. Parse the line

Read `templates/protocols/common.md` § Inbox-line tag parsing. Extract:
- `url`
- `effective_detail_level` (`<!-- detail:X -->` override or config default)
- `companion_override_url` (from `<!-- companion:URL -->`)
- `suppress_companion` (from `<!-- no-companion -->`)
- `branch_override` (from `<!-- branch:NAME -->`, GitHub only)
- `clone_flag` (from `<!-- clone -->`, GitHub deep only)

### 3. Source type + slug + raw path

Read `templates/protocols/common.md` § Source-type detection and § Slug derivation. Determine:
- `source_type` ∈ {web, github, youtube}
- `slug`
- `raw_path` = `docs/_wiki/raw/<source_type>/<slug>.md`

If `source_type` is not in `.config.yml` `source_types`, note the mismatch in the post-ingest report but proceed (user explicitly requested this URL).

### 4. Fetch — dispatch via `wiki-fetch` sub-agent (P3)

**The main thread MUST NOT fetch the body inline. Do not fetch inline. Dispatch the Task tool with the `wiki-fetch` sub-agent and receive only the structured ≤4000-token result.** Inlining a 100k-token URL into main saturates the context window before a single page lands; the sub-agent isolates the expensive read.

Pre-dispatch, consult the cumulative budget guard for the **whole batch**. The guard returns a concrete dispatch plan (`decision.batches`) — never roll your own batching:

```python
from _wiki_budget import decide_dispatch_strategy
decision = decide_dispatch_strategy(
    n_invocations=len(pending_lines),
    projected_tokens_per_result=4000,   # wiki-fetch contract cap
    max_main_context=200_000,
)
# decision.strategy:               "parallel" or "serial"
# decision.max_parallel_batch_size: largest N that fits under threshold
# decision.batches:                 ((0,1,2,3), (4,5,6,7), (8,9)) — concrete dispatch plan
```

Iterate `decision.batches` directly: each batch is a tuple of indices into `pending_lines`. Dispatch one Task invocation per index in the current batch concurrently; await them all before moving to the next batch. When `decision.strategy == "parallel"` the list contains a single batch with every index — equivalent to "dispatch all at once." This makes serial-vs-parallel a single code path; no operator-side math.

For each pending URL, dispatch one `wiki-fetch` Task invocation with the input descriptor:

```jsonc
{
  "kind": "<web|github|youtube>",
  "source": "<url>",
  "extraction-mode": "<shallow|deep>",   // from effective_detail_level
  "raw-target": "_wiki/raw/<source_type>/<slug>.md"
}
```

The agent writes the raw body to `raw-target` on disk and returns the structured ≤4000-token summary (title, h2-outline, key-sentences, suggested-page-type, suggested-cluster, raw-file-pointer, citation-banner-fields). Validate every result with `_wiki_fetch_contract.validate_result()` before consuming it; reject malformed outputs.

When `decision.strategy == "parallel"`, dispatch all N invocations concurrently. When `serial`, dispatch the first batch, wait for results, then dispatch the next batch — the budget guard prevents the cumulative return from saturating main context.

The protocol files (`templates/protocols/web.md`, `github.md`, `youtube.md`) describe the per-kind extraction rules the sub-agent applies internally. The main thread never reads them directly — that body work happens inside `wiki-fetch`.

**Per-fetch token guard (legacy):** Inside the sub-agent, if a single fetch projects > 100,000 tokens of input, halt that one invocation with `error.kind: input-too-large`. The cumulative guard above operates on outputs (≤4000 each), not inputs.

**Failure handling:**

| Failure | Action |
|---|---|
| YouTube — no transcript | Append `<!-- fetch-failed:no-transcript -->` to the line. Leave under `## Pending`. Log + continue. |
| 4xx/5xx HTTP | Append `<!-- fetch-failed:http-<code> -->`. Leave pending. Log + continue. |
| Other unexpected | Log error; leave pending; continue. |

### 5. Companion fetch (web sources only)

Read `templates/protocols/common.md` § Companion-fetch sub-protocol. Companion fetch runs only when:
- `source_type = web` AND
- Web protocol step 7 returned non-null `companion_github_url` AND
- `suppress_companion = false` AND
- `len(products) < 2` (multi-product mode skips companion)

If `companion_override_url` is set, use it instead of the discovered URL.

**Self-loop guard:** if the companion URL resolves to the same repo as the inbox URL (e.g. running `/wiki run https://github.com/x/y` and the page mentions itself), discard.

### 6. Call `ingest.md`

Read `ingest.md` and follow it with this context:

```yaml
slug: <derived>
source_type: <web|github|youtube>
raw_path: <derived>
effective_detail_level: <derived>
today: <today>
companion_slug: <or null>
companion_raw_path: <or null>
products: <list from web fetch step 5, or null/empty>
provenance:
  kind: url-fetch
  source: <original URL>
  captured_on: <today>
page_type: source-summary
cluster: <null — let ingest.md Step 2b derive>
```

Append `{pass: 1, url, slug, outcome: ingested}` to the ingest log.

### 7. Re-read queue before next item

`queue.md` was mutated by `ingest.md` Step 7. Re-read it before processing the next pending item to avoid stale state.

---

## Pass 2 — Refresh tagged items (batch mode only)

Skip in single mode (single-URL ingests don't trigger refresh sweeps).

Re-read `queue.md`. Collect all lines under `## Completed` containing `<!-- refresh -->` (any `[ ]` / `[x]` state). For each, run the **refresh flow** — read `refresh.md` and apply it to that slug. Append `{pass: 2, ...}` log entries.

D-05 two-tier refresh: refresh.md decides whether to run quick-check (HEAD only) or full rediscover based on `last-fetched` age and config thresholds.

---

## Post-ingest lint

| `auto_lint` | Action |
|---|---|
| `batch` | After Pass 1+2, run `lint.md` once over the whole zone. Include report in summary. |
| `never` | Skip. |
| `per-ingest` (single mode) | Lint after the single ingest. |
| `per-ingest` (batch mode) | Skipped here; lint fires once at end via `batch` semantics — never per-item in batch. |

---

## Summary report

### Batch mode

```
Wiki ingest complete — <domain>
{{TODAY}}

Pass 1 — pending:
  Ingested: N
  Skipped:  N  (<!-- skip --> tag)
  Failed:   N  (fetch errors logged above)

Pass 2 — refresh:
  Updated:    N
  No-change:  N

Index regeneration: docs/_wiki/index.md (M page(s))
{{IF lint ran}}
Lint: <N ERROR, N WARN, N INFO — see report above>
{{IF lint skipped}}
Lint: skipped (auto_lint: <never|per-ingest>)
```

### Single mode

```
Ingested: <url>

  Type:        <github | youtube | web>
  Page-type:   source-summary
  Cluster:     <derived>
  Slug:        <slug>
  Raw:         docs/_wiki/raw/<type>/<slug>.md
  Wiki page:   docs/_wiki/source-summary/<slug>.md
  Detail:      <effective_detail_level>
  Companion:   docs/_wiki/raw/github/<org>-<repo>.md   ← only when companion fetch succeeded
  Products:    p1, p2, ...                              ← only in multi-product mode
  Sub-pages:   docs/_wiki/source-summary/<slug>-p1.md, ...

Updated: docs/_wiki/index.md (regenerated), overview.md, log.md, queue.md
{{IF lint ran}}
Lint: <findings>
```

If `companion` fetch was attempted but failed: `Companion: fetch failed (<reason>) — web-only page produced.`

If `source_type` not in config: `Note: source type <type> is not in this wiki's source_types config.`

Suggested commit message (don't auto-commit): `wiki: ingest <slug>` or `wiki: refresh <slug>`.

---

## Notes

- **Idempotency:** items remain under `## Pending` until successfully ingested. A crashed run can be re-executed safely.
- **`<!-- skip -->` is persistent:** remove the tag manually to process the item.
- **Partial raw on crash:** the partial raw file gets overwritten on re-fetch — no manual cleanup needed.
- **Git:** no agent commits. See SKILL.md.
