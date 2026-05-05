# Job: wiki-coverage-audit

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** quarterly
**Nature:** cross-zone coverage scan — suggestion-only

---

## Purpose

Surface useful wiki expansion opportunities:

- Active data points with no wiki explainer.
- Frequently mentioned inbox topics that are not yet explained.
- Wiki pages whose `cluster:` is not represented in `docs/document-index.md`
  under the permissive v1 cluster rule from D-03.

This job does not create pages. It produces candidates for `/wiki create` or
`/wiki promote`.

---

## Steps

### 1. Rebuild source inventories

Run:

```text
python .claude/scripts/build_document_index.py
python .claude/scripts/refresh_wiki_index.py --quiet
```

If `build_document_index.py` fails, emit `verdict: error`. If wiki index refresh
changes `docs/_wiki/index.md` and `wiki-index-refresh` is whitelisted, record it
as auto-fixed.

### 2. Validate wiki schema

Run:

```text
python .claude/scripts/wiki_schema.py validate
```

If validation fails, emit `verdict: red` and put schema issues in
`actions_needed`.

### 3. Find data points without explainers

For each active data point in `docs/*.md` and non-underscore subfolders:

1. Check whether any wiki page lists that data point in `builds-on`.
2. If none exists, emit an INFO action item:
   `coverage-gap: <data-point> has no wiki explainer`.

Do not flag data points under `_planned/`, `_archive/`, `_inbox/`,
`_collections/`, `_bcos-framework/`, or custom `_` folders.

### 4. Surface cluster drift

Compare wiki page `cluster:` values against the cluster list in
`docs/document-index.md`. Because D-03 keeps v1 permissive, cluster drift is
INFO only:

`cluster-mismatch: <wiki-page> uses cluster <cluster> not present in document-index.md`.

### 5. Mine inbox mentions lightly

Read filenames and first headings under `docs/_inbox/` only. Do not process raw
inbox content deeply in this job. If a term appears repeatedly and no wiki page
title/reference covers it, emit:

`coverage-gap: repeated inbox topic <term> may deserve /wiki create`.

### 6. Determine verdict

- `green` — no coverage candidates.
- `amber` — candidates found.
- `red` — schema validation failed.
- `error` — inventory build failed.

### 7. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 5,
  "auto_fixed": ["wiki-index-refresh in docs/_wiki/index.md"],
  "actions_needed": [
    "coverage-gap: docs/customer-onboarding.md has no wiki explainer",
    "cluster-mismatch: docs/_wiki/pages/new-area.md uses cluster Enablement not present in document-index.md"
  ],
  "notes": "Coverage audit found 5 wiki expansion candidates."
}
```

---

## Auto-fixes allowed

- `wiki-index-refresh`

Creating wiki pages and changing clusters require explicit user judgement.
