# /wiki refresh — re-fetch or re-read an existing wiki source

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Invocation

```text
/wiki refresh <slug> [--full]
```

Refresh applies to existing pages. Path A pages re-fetch external sources; Path B pages re-read their local provenance source when available.

## D-05 refresh contract

Two tiers exist:

| Tier | Trigger | Behavior |
|---|---|---|
| Quick-check | before full cadence | HEAD/checksum only. If unchanged, bump `last-fetched` and log `no-change`. |
| Full rediscover | stale threshold or `--full` | Re-run source-type detection, companion discovery, and product discovery from scratch. |

HEAD-check is only a freshness signal. It never replaces full rediscovery.

## Flow

1. Resolve `<slug>` under `docs/_wiki/source-summary/` first, then `docs/_wiki/pages/`.
2. Read `provenance.kind`.
3. For `url-fetch`:
   - Read `source-url`.
   - **Quick-check tier (HEAD only, no body fetch):** call `_wiki_http.head_check(url)`; compare against stored `etag` / `last-modified` via `head_signals_unchanged()`. The stored `content-hash` is NOT consulted at this tier — a body hash is a full-tier validator, not a HEAD-response signal. If ETag/Last-Modified match, bump `last-fetched` and stop. The main thread does NOT fetch the body.
   - **Full-tier:** dispatch the Task tool with `wiki-fetch` (kind matching the source-summary's source-type). The sub-agent re-fetches the body, writes it to `_wiki/raw/<type>/<slug>.md`, and returns the structured ≤4000-team summary. After the sub-agent returns, the main thread calls `_wiki_http.body_content_unchanged(stored_hash, raw_body)` to confirm whether the bytes actually changed (catches the "ETag drifted but content identical" case). Validate the structured result with `_wiki_fetch_contract.validate_result()`. Then call `ingest.md` with the existing slug.
4. For `local-document`:
   - Re-read `provenance.source` if it is an existing local path. For non-trivial bodies (PDF, .docx, large markdown), dispatch `wiki-fetch` with `kind: pdf|docx|local` instead of inlining the read. Main thread receives only the structured summary.
   - If missing, report INFO `provenance-source-missing` and stop without rewriting.
   - If hash unchanged, bump `last-reviewed` only when the user confirms.
   - If changed, copy/extract to `docs/_wiki/raw/local/` and call `ingest.md`.
5. For `inbox-promotion`:
   - The original inbox file may be gone. If missing, stop with a note that this page refreshes through human review, not automatic source re-read.
6. Run `python .claude/scripts/refresh_wiki_index.py`.
7. Append to `log.md`.

## Output

```text
Refreshed: <slug>

  Mode:      quick-check | full-rediscover | local-reread | no-change
  Source:    <source-url or provenance.source>
  Page:      docs/_wiki/{pages|source-summary}/<slug>.md
  Index:     regenerated
  Log:       docs/_wiki/log.md
```

No agent commits. See `SKILL.md`.
