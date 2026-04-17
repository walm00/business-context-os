# Job: index-health

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily
**Nature:** mechanical — rebuild inventory, scan for structural issues, apply whitelisted fixes

---

## Purpose

The cheap, everyday check. Keeps the document index current and catches structural drift (missing frontmatter, broken links, metadata gaps) within 24 hours of it happening.

Because this job is run daily and is fast, any fix it applies is low-stakes — the user will see it the next morning regardless.

---

## Steps

### 1. Rebuild the document index

Run:

```
python .claude/scripts/build_document_index.py
```

Capture the output. If the script errors, emit `verdict: error` with the error message in `notes` and stop.

### 2. Regenerate the wake-up context

Run:

```
python .claude/scripts/generate_wakeup_context.py
```

Non-fatal if this fails — note it but continue.

### 3. Scan docs for structural issues

Scan `docs/*.md` (recursively) but **skip** these folders:

- `docs/_inbox/` — raw material, no quality bar
- `docs/_planned/` — future state, different rules
- `docs/_archive/` — historical, untouched
- `docs/_collections/` — bulk files, no frontmatter required
- `docs/_bcos-framework/` — framework, synced from upstream

For each remaining file, check:

| Issue ID                      | What to look for                                                     |
|-------------------------------|----------------------------------------------------------------------|
| `missing-frontmatter`         | No YAML frontmatter block at all, or empty block                     |
| `missing-required-field`      | Required field missing: name, type, cluster, version, status, created, last-updated |
| `missing-last-updated`        | `last-updated` field absent (but other frontmatter present)          |
| `frontmatter-field-order`     | All required fields present, but not in canonical order              |
| `broken-xref`                 | Markdown link pointing to a non-existent file                        |
| `broken-xref-single-candidate`| broken-xref where exactly one file with matching basename exists     |
| `trailing-whitespace`         | Lines ending in spaces/tabs                                          |
| `eof-newline`                 | File does not end in exactly one newline                             |

Use `build_document_index.py`'s output as the source of truth for "which files exist" — do not re-glob.

### 4. Apply auto-fixes

For each issue, check against the dispatcher's `auto_fix.whitelist`. If allowed:

- Apply the fix (see `auto-fix-whitelist.md` for exact semantics)
- Record it in `auto_fixed` output field: one string per fix, format: `{issue-id} in {relative-path}`

If not allowed, record it in `actions_needed`: one string per item, format: `{issue-id}: {relative-path} — {short description}`.

### 5. Determine verdict

- 🟢 `green` — no findings, or every finding was auto-fixed
- 🟡 `amber` — one or more items remain in `actions_needed`, all non-critical (missing fields, broken xref without candidate, etc.)
- 🔴 `red` — any critical item: missing-frontmatter entirely on an active doc, or index script errored
- ⚠️ `error` — the scan itself failed (script crash, permission error, etc.)

### 6. Emit result

Return to the dispatcher:

```json
{
  "verdict": "amber",
  "findings_count": 3,
  "auto_fixed": [
    "missing-last-updated in docs/brand-identity.md",
    "eof-newline in docs/competitive-positioning.md"
  ],
  "actions_needed": [
    "missing-frontmatter: docs/new-playbook.md — has no YAML block, needs a template"
  ],
  "notes": "Index rebuilt: 24 docs (unchanged from yesterday)."
}
```

Keep `notes` to one short sentence. Anything longer belongs in the digest.

---

## What this job does NOT do

- Does not read, interpret, or validate the *content* of docs — only their structure and metadata
- Does not make judgement calls about whether a doc should exist, be split, or be archived
- Does not touch `docs/_inbox/` contents (left for `audit-inbox` to process)
- Does not consolidate lessons (`lessons-consolidate` skill)
- Does not do strategic reflection (that's the daydream jobs)

Keep this job dumb and fast. Its value is in the 364 days a year it runs and finds nothing.
