# Common Protocols

Shared parsing rules for `/wiki run`, `/wiki queue`, and `/wiki refresh`.

## Source-type detection

Classify by URL:

| Pattern | Source type |
|---|---|
| `https://github.com/<org>/<repo>` | `github` |
| `https://youtu.be/...` or `https://www.youtube.com/watch?...` | `youtube` |
| everything else with `http://` or `https://` | `web` |

Reject non-HTTP URLs in Path A. Local files use `create.md` and `templates/protocols/local.md`.

## Slug derivation

1. Lowercase.
2. Remove protocol and `www.`.
3. For GitHub, use `<org>-<repo>` and ignore branch/path unless `<!-- branch:... -->` is supplied.
4. For YouTube, prefer channel/title metadata when available; otherwise use the video id.
5. Replace non-alphanumeric runs with `-`.
6. Trim leading/trailing `-`.
7. If the slug already exists, append `-2`, `-3`, etc. Do not overwrite without refresh.

## Inbox-line tag parsing

Queue lines use markdown checkbox syntax plus optional HTML-comment tags:

```markdown
- [ ] https://example.com <!-- detail:deep --> <!-- no-companion -->
```

Supported tags:

| Tag | Meaning |
|---|---|
| `<!-- detail:brief|standard|deep -->` | override config detail level |
| `<!-- companion:URL -->` | force companion GitHub URL for web sources |
| `<!-- no-companion -->` | suppress companion discovery |
| `<!-- branch:NAME -->` | GitHub branch override |
| `<!-- clone -->` | allow clone-based deep GitHub ingest |
| `<!-- refresh -->` | refresh a completed line on next batch run |
| `<!-- skip -->` | leave pending but do not process |

Unknown tags are preserved and ignored.

## Companion-fetch sub-protocol

For web sources, inspect the fetched content for a GitHub repository URL. Fetch a companion only when:

- source type is `web`
- exactly one product was discovered
- companion discovery found one canonical repo
- `<!-- no-companion -->` is absent

If `<!-- companion:URL -->` is present, use that URL instead. Apply a self-loop guard: the companion must not resolve to the same URL being ingested.
