# Job: wiki-stale-propagation

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily
**Nature:** mechanical scan — detect source updates that should trigger human wiki review

---

## Purpose

Find wiki pages whose canonical source data points changed after the wiki page
was last reviewed. This keeps explanatory wiki pages from silently drifting
behind the active business reality they build on.

The job is metadata-only. It does not rewrite wiki page prose.

---

## Steps

### 1. Check whether the wiki zone exists

If `docs/_wiki/` does not exist, emit:

```json
{
  "verdict": "green",
  "findings_count": 0,
  "auto_fixed": [],
  "actions_needed": [],
  "notes": "Wiki zone not enabled; stale-propagation skipped."
}
```

### 2. Refresh derived wiki index

If `wiki-index-refresh` is on the dispatcher whitelist, run:

```text
python .claude/scripts/refresh_wiki_index.py --quiet
```

Record any change as `wiki-index-refresh in docs/_wiki/index.md`.

### 3. Validate schema before scanning

Run:

```text
python .claude/scripts/wiki_schema.py validate
```

If validation fails, emit `verdict: red` and put each schema error in
`actions_needed`. Do not continue; stale comparisons are unreliable when
frontmatter is malformed.

### 4. Compare `builds-on` timestamps

For each page under `docs/_wiki/pages/*.md` and
`docs/_wiki/source-summary/*.md`:

1. Read `last-reviewed` from the wiki page.
2. For each frontmatter `builds-on` path, resolve the referenced document.
3. Read the source document's `last-updated`.
4. If source `last-updated` is later than wiki `last-reviewed`, emit:
   `stale-propagation: <wiki-page> builds on <source> updated <date> after last-reviewed <date>`.

Missing or unreadable `builds-on` targets are action items; do not guess.

### 5. Determine verdict

- `green` — no findings, or only `wiki-index-refresh` auto-fixed.
- `amber` — one or more stale pages or missing source targets.
- `red` — schema validation failed.
- `error` — scripts or scanning crashed.

### 6. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 2,
  "auto_fixed": ["wiki-index-refresh in docs/_wiki/index.md"],
  "actions_needed": [
    "stale-propagation: docs/_wiki/pages/pricing-process.md builds on docs/current-state.md updated 2026-05-01 after last-reviewed 2026-04-10"
  ],
  "notes": "Checked 18 wiki pages for builds-on freshness."
}
```

---

## Auto-fixes allowed

- `wiki-index-refresh`

Everything else is an action item. Reviewing or rewriting wiki prose requires
human judgement.
