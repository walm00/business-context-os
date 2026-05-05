# /wiki queue — append URL(s) to queue.md without ingesting

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Purpose

`queue` lets the user (or any agent) add URLs to `docs/_wiki/queue.md`'s `## Pending` section **without fetching or ingesting**. Use it to surface a candidate source for later review/batch-ingest. Use `/wiki run <url>` instead when you want to ingest immediately (it auto-queues missing URLs and then ingests).

## Invocation

```
/wiki queue <url> [<url2> ...] [<inline tags>]
```

Inline tags (HTML-comment form) may follow each URL — see `templates/protocols/common.md` § Inbox-line tag parsing.

## Per-URL logic

For each URL:

1. **Read `queue.md`.**
2. If URL already under `## Completed`: skip + report:
   > *"`<url>` already ingested (under ## Completed). To re-fetch, add `<!-- refresh -->` to its line and run `/wiki run`."*
3. If URL already under `## Pending`: skip + report:
   > *"`<url>` already queued."*
4. Otherwise: append `- [ ] <url> <inline tags>` to the `## Pending` section, immediately before the `## Completed` heading.
5. Re-read `queue.md` before processing the next URL (avoid duplicate appends within a single invocation).

## Output

```
Queued for ingest — <wiki-domain>
{{TODAY}}

  Added:    N URL(s)
  Skipped:  M (already pending or completed)

Added:
  - https://...
  - https://...

Skipped (with reason):
  - https://...   already in ## Completed
  - https://...   already in ## Pending

Next: run `/wiki run` to batch-ingest, or `/wiki run <url>` for a single URL.
```

## Notes

- `queue` never fetches, never writes a raw file, never modifies any wiki page.
- Agents may call `queue` autonomously; that's its purpose. Other inbox mutations (move to Completed, mark `<!-- ingested -->`) are reserved for `run`/`refresh`/`remove`.
- No agent commits — see SKILL.md.
