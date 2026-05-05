# Job: wiki-graveyard

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** monthly
**Nature:** archive-candidate scan — mostly judgement, one narrow metadata auto-fix

---

## Purpose

Find wiki pages that may no longer belong in the active wiki: stale pages,
orphan pages, and page-types with schema-defined expiry. The job proposes
archive candidates, but does not delete or move pages.

---

## Steps

### 1. Check whether the wiki zone exists

If `docs/_wiki/` does not exist, emit green with zero findings and note that the
wiki zone is absent.

### 2. Validate schema

Run:

```text
python .claude/scripts/wiki_schema.py validate
```

If validation fails, emit `verdict: red` and put each schema issue in
`actions_needed`.

### 3. Read archive thresholds

Read from `docs/_wiki/.schema.yml`, falling back to the framework template:

- `thresholds.graveyard-days`
- `thresholds.orphan-grace-days`
- each page-type's `auto-archive-after-days`

Default `graveyard-days` and `orphan-grace-days` to `365` when missing.

### 4. Find stale and orphan candidates

For each wiki page:

- If `last-reviewed` is older than `graveyard-days`, emit
  `graveyard-stale: <page> last-reviewed <date>`.
- If no other wiki page links to the page and it has had no edits within
  `orphan-grace-days`, emit `orphan-pages: <page> has no inbound wiki links`.
- If its page-type is retired, emit `retired-page-type: <page> uses retired type <type>`.

These are action items because archive decisions require judgement.

### 5. Apply narrow post-mortem expiry auto-fix

If a page has `page-type: post-mortem`, its schema page-type defines
`auto-archive-after-days`, and the page age exceeds that value, the job may
apply `wiki-archive-expired-post-mortem` when whitelisted.

This fix only changes frontmatter `status: archived`, bumps the patch version,
and updates `last-updated`. It does not move the file or edit the body.

### 6. Determine verdict

- `green` — no findings, or only expired post-mortem status was auto-fixed.
- `amber` — archive candidates need review.
- `red` — schema validation failed.
- `error` — scan crashed.

### 7. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 4,
  "auto_fixed": ["wiki-archive-expired-post-mortem in docs/_wiki/pages/outage-2026-02.md"],
  "actions_needed": [
    "graveyard-stale: docs/_wiki/pages/legacy-flow.md last-reviewed 2025-01-10",
    "orphan-pages: docs/_wiki/pages/unused-term.md has no inbound wiki links"
  ],
  "notes": "Checked 22 wiki pages for archive candidates."
}
```

---

## Auto-fixes allowed

- `wiki-archive-expired-post-mortem`

All other archival decisions remain action items.
