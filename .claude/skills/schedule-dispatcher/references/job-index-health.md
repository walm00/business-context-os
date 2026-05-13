# Job: index-health

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily
**Nature:** mechanical — rebuild inventory, scan for structural issues, apply whitelisted fixes
**Boundary:** node — own-repo paths only (no `../`, no absolute paths outside `$CLAUDE_PROJECT_DIR`, no sibling-repo names). Enforced by dispatcher Step 4a preflight.

<!-- emits-finding-types: machine-readable; consumed by .claude/scripts/test_finding_type_coverage.py. Schema: docs/_bcos-framework/architecture/typed-events.md -->
```yaml
emits-finding-types:
  - missing-frontmatter
  - missing-required-field
  - missing-last-updated
  - frontmatter-field-order
  - broken-xref
  - broken-xref-single-candidate
  - trailing-whitespace
  - eof-newline
```

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

### 3. Refresh ecosystem state

Run:

```
python .claude/scripts/refresh_ecosystem_state.py --quiet
```

This regenerates `.claude/quality/ecosystem/state.json` from disk by globbing
`.claude/skills/*/SKILL.md` and `.claude/agents/*/AGENT.md`. Anything in those
trees without the marker file is recorded as a `utility`, not a skill/agent.

Why daily: the script is cheap (a few globs + JSON write), keeps state.json
within 24h of any user-added skill, and prevents the false-positive drift that
would otherwise accumulate until the monthly architecture-review run.

If the script changed anything, capture its summary line (e.g. `state.json
refreshed: +1 skill(s)`) and add it to the `notes` field of your result so the
digest shows what was reconciled. If the script errored, log the error in
`notes` and continue — non-fatal.

See `auto-fix-whitelist.md` (`ecosystem-state-refresh` ID) for the full safety
rationale: deterministic, idempotent, no business-content change, reversible
by `git diff`.

### 4. Refresh wiki index

Run:

```
python .claude/scripts/refresh_wiki_index.py --quiet
```

This regenerates `docs/_wiki/index.md` from the frontmatter of every page
under `docs/_wiki/pages/` and `docs/_wiki/source-summary/`. Like `state.json`,
the wiki index is a **derived artifact** — hand-edits get overwritten by
design (lesson L-INIT-20260404-009; pre-flight decision D-11). The script
no-ops cleanly when no `_wiki/` zone exists, so this step is safe on repos
that haven't adopted the wiki.

If the script reported a change, capture its summary line for `notes` (e.g.
`refresh_wiki_index: docs/_wiki/index.md updated (12 page(s))`). If it
errored, log the error in `notes` and continue — non-fatal.

See `auto-fix-whitelist.md` (`wiki-index-refresh` ID) for the full safety
rationale: same derived-artifact pattern as `ecosystem-state-refresh`.

### 5. Scan + auto-fix in one mechanical pass

Run:

```
python .claude/scripts/scan_docs_structure.py --json --apply-whitelist <comma-joined-fix-ids-from-schedule-config>
```

The script is the single source of truth for what step 5/6 used to describe in prose. It:

- Iterates `docs/**/*.md` and processes only files whose zone is `active` (everything under `_inbox/`, `_planned/`, `_archive/`, `_collections/`, `_bcos-framework/`, `_wiki/`, dotfiles, and any user `_<custom>/` folder is skipped by `context_index._zone_for`)
- Checks each file against all 8 issue IDs listed below
- Applies any fix ID present in `--apply-whitelist` inline and emits the result under `auto_fixed`
- Reports anything not auto-fixed under `actions_needed`
- Emits a single JSON document on stdout — capture it directly into your result

Pass the **intersection** of your dispatcher's `auto_fix.whitelist` config and the IDs this scanner knows how to apply: `missing-last-updated`, `frontmatter-field-order`, `trailing-whitespace`, `eof-newline`, `broken-xref-single-candidate`.

**Issue IDs the scanner emits:**

| Issue ID                      | What it means                                                        |
|-------------------------------|----------------------------------------------------------------------|
| `missing-frontmatter`         | No YAML frontmatter block at all, or empty block                     |
| `missing-required-field`      | Required field missing: name, type, cluster, version, status, created, last-updated |
| `missing-last-updated`        | Only `last-updated` is missing (other required fields present)       |
| `frontmatter-field-order`     | All required fields present, but not in canonical order              |
| `broken-xref`                 | Markdown link to a non-existent **local** file; 0 or ≥2 basename candidates |
| `broken-xref-single-candidate`| Broken xref where exactly one file with matching basename exists     |
| `trailing-whitespace`         | Lines ending in spaces/tabs                                          |
| `eof-newline`                 | File does not end in exactly one newline                             |

Notes baked into the script (do not re-describe in prose elsewhere):

- URI-scheme links (`http://`, `mailto:`, `computer://`, `obsidian://`, any `^[a-z][a-z0-9+.-]*:`) and pure fragment links (`#anchor`) are excluded from xref checks
- `owner` is NOT a required field — the canonical required set is `name, type, cluster, version, status, created, last-updated`
- The basename index for single-candidate resolution covers all `docs/**/*.md` (including wiki and inbox), so the scanner can correctly point an `active` doc at a sibling that has moved

If the script crashes, the JSON's `verdict` will be `error` and `notes` will contain the exception. Surface that verbatim in your result and stop — do not improvise replacement scans.

### 6. Determine verdict

- 🟢 `green` — no findings, or every finding was auto-fixed
- 🟡 `amber` — one or more items remain in `actions_needed`, all non-critical (missing fields, broken xref without candidate, etc.)
- 🔴 `red` — any critical item: missing-frontmatter entirely on an active doc, or index script errored
- ⚠️ `error` — the scan itself failed (script crash, permission error, etc.)

### 7. Emit result

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
  "notes": "Index rebuilt: 24 docs (unchanged from yesterday). 2 custom _-folders skipped (8 files)."
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
