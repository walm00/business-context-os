# Wiki Stub Repair Fixtures

Inputs for `test_wiki_stubs.py` — the P4 acceptance tests for HEAD/ETag,
schema migration, and the consolidated YAML parser.

## Files

| File | Used by | What it exercises |
|---|---|---|
| `source-summary-pre.md` | migration test | A 1.0-schema source-summary page (no etag/last-modified/content-hash). Migration 1.0→1.1 should add those fields without touching anything else. |
| `source-summary-post.md` | migration test | The same page after a clean 1.0→1.1 migration. Running 1.1→1.0 on this returns to `source-summary-pre.md` byte-identically. |
| `head-response.json` | HEAD test | Mock `HTTPResponse` headers — `ETag`, `Last-Modified`, `Content-Length`, `Content-Type`. The HEAD helper turns these into a dict the quick-check tier compares against frontmatter. |
| `yaml-edge-cases.md` | parser test | Frontmatter that exercises every shape the existing three hand-rolled parsers support: scalar, inline list, multi-line list, quoted strings, special characters in values. The new `_wiki_yaml.py` must produce the same keys/values as the legacy parsers do today. |

## Why these are minimal

P4 is a cleanup phase — fixtures are smallest-possible-things-that-prove-the-bug-is-fixed. Heavy fixtures live in `_wiki/` proper once the wiki zone is initialized.
