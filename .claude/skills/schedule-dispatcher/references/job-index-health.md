# Job: index-health

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily
**Nature:** mechanical — rebuild inventory, scan for structural issues, apply whitelisted fixes

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

### 5. Scan docs for structural issues

Scan `docs/*.md` (recursively) but **skip any top-level `docs/_<name>/` folder** — the underscore prefix is the framework's opt-out convention. The framework-managed underscores are:

- `docs/_inbox/` — raw material, no quality bar (categorized separately by the indexer)
- `docs/_planned/` — future state, different rules (categorized separately)
- `docs/_archive/` — historical, untouched (categorized separately)
- `docs/_collections/` — bulk files, no frontmatter required (categorized separately)
- `docs/_bcos-framework/` — framework, synced from upstream (silent skip)

**Any other `docs/_<custom>/` folder a user creates is also skipped** — that's the whole point of the convention. The indexer counts them and reports a one-line summary in its stdout, e.g. `Custom _-folders skipped: 2 folder(s), 8 file(s)`. Surface that count in the `notes` field of your result so users see it in the digest. Do not list folder names or file contents — `_*` is opt-out from visibility, not just from validation.

Also skip these **generated / convention files** (no frontmatter by design — flagging them is a false positive that recurs every run):

- `docs/document-index.md` — auto-generated index
- Any dot-prefixed basename (`.wake-up-context.md`, `.session-diary.md`, `.onboarding-checklist.md`, `.portfolio-aggregate.md`, and any other `docs/.*.md`)

Note on `owner` field: `owner` is **not** a required frontmatter field (see `docs/_bcos-framework/methodology/document-standards.md`). Do not flag it as `missing-required-field`. The required list is exactly: `name, type, cluster, version, status, created, last-updated`.

Also skip these **generated / convention files** (no frontmatter by design — flagging them is a false positive that recurs every run):

- `docs/document-index.md` — auto-generated index
- Any dot-prefixed basename (`.wake-up-context.md`, `.session-diary.md`, `.onboarding-checklist.md`, `.portfolio-aggregate.md`, and any other `docs/.*.md`)

Note on `owner` field: `owner` is **not** a required frontmatter field (see `docs/_bcos-framework/methodology/document-standards.md`). Do not flag it as `missing-required-field`. The required list is exactly: `name, type, cluster, version, status, created, last-updated`.

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

### 6. Apply auto-fixes

For each issue, check against the dispatcher's `auto_fix.whitelist`. If allowed:

- Apply the fix (see `auto-fix-whitelist.md` for exact semantics)
- Record it in `auto_fixed` output field: one string per fix, format: `{issue-id} in {relative-path}`

If not allowed, record it in `actions_needed`: one string per item, format: `{issue-id}: {relative-path} — {short description}`.

### 7. Determine verdict

- 🟢 `green` — no findings, or every finding was auto-fixed
- 🟡 `amber` — one or more items remain in `actions_needed`, all non-critical (missing fields, broken xref without candidate, etc.)
- 🔴 `red` — any critical item: missing-frontmatter entirely on an active doc, or index script errored
- ⚠️ `error` — the scan itself failed (script crash, permission error, etc.)

### 8. Emit result

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
