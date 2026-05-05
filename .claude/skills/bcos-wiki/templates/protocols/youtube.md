# YouTube Fetch Protocol

Used by `/wiki run` for YouTube URLs.

## Steps

1. Resolve canonical video URL and video id.
2. Fetch title, channel, publish date, description, and transcript when available.
3. If no transcript is available, return `fetch-failed:no-transcript`.
4. Segment transcript by chapters when chapter metadata exists; otherwise use time-window chunks.
5. Apply token guard before writing raw content.
6. Write raw markdown to `docs/_wiki/raw/youtube/<slug>.md` with:

```markdown
<!-- wiki-source-stamp
source-url: <youtube-url>
source-type: youtube
captured-on: <today>
detail-level: <brief|standard|deep>
-->
```

## Output to `run.md`

Return title, channel, transcript metadata, raw path, slug, and projected token count.
