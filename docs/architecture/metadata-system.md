# Metadata System -- The Complete Reference

Every managed document in Business Context OS carries YAML frontmatter metadata. This metadata enables automated health checks (hooks and scripts), discovery (Document Index generation), and enforcement (context-audit). This is the single reference for all validation rules.

---

## YAML Frontmatter -- Required Fields

Every managed document in `docs/` (excluding `_inbox/`) MUST have these fields:

| Field | Type | Rules | Enforced By |
|-------|------|-------|-------------|
| `name` | string | Non-empty, human-readable document name | hook, audit, index script |
| `type` | enum | `context` &#124; `process` &#124; `policy` &#124; `reference` &#124; `playbook` | hook, audit |
| `cluster` | string | Non-empty, names the parent cluster this belongs to | audit, index script |
| `version` | semver | `x.y.z` format. Bump on every change. | audit |
| `status` | enum | `draft` &#124; `active` &#124; `under-review` &#124; `archived` | hook, audit |
| `owner` | string | Specific person or role. Not blank, not `TBD`, not `todo`, not `none`. | hook, audit |
| `created` | ISO date | `YYYY-MM-DD`. Set once when document is created. NEVER change. | audit |
| `last-updated` | ISO date | `YYYY-MM-DD`. MUST update on every edit. Must be >= `created`. | audit |

### Example

```yaml
---
name: "Brand Voice"
type: context
cluster: "Brand & Identity"
version: "1.2.0"
status: active
owner: "Marketing Lead"
created: "2026-01-15"
last-updated: "2026-04-01"
---
```

---

## Optional Fields

| Field | Type | Purpose |
|-------|------|---------|
| `tags` | list of strings | Free-form labels for search and filtering |
| `review-cycle` | enum | `weekly` &#124; `monthly` &#124; `quarterly` &#124; `annual` &#124; `trigger-based` |
| `next-review` | ISO date | When the next review is due |
| `depends-on` | list of strings | Upstream documents (maps to BUILDS_ON in ownership spec) |
| `consumed-by` | list of strings | Downstream documents (maps to PROVIDES in ownership spec) |
| `source` | URL or string | Where the original content came from |
| `confidentiality` | enum | `public` &#124; `internal` &#124; `confidential` &#124; `restricted` |

---

## Folder-Based Inference

The file path supplements metadata. Claude uses the folder to determine trust level before opening the file.

| Location | What It Means | Metadata Requirements |
|----------|--------------|----------------------|
| `docs/*.md` | Active context -- current business reality | Full compliance required. All 8 required fields. |
| `docs/_inbox/` | Raw material -- meeting notes, brain dumps | No metadata required. Skip all validation. |
| `docs/_planned/` | Polished ideas -- documented but not yet real | Frontmatter recommended. Relaxed staleness (180 days). Incomplete cross-references are informational, not errors. |
| `docs/_archive/` | Superseded -- was real once, kept for reference | As-was when archived. Skip audit or report separately. |

### Document Movement

| From | To | Trigger |
|------|-----|---------|
| `_inbox/` | `docs/` | Raw material refined into active context (via context-ingest) |
| `_inbox/` | `_planned/` | Raw idea polished into a documented concept |
| `_planned/` | `docs/` | Idea becomes reality (build full relationships and ownership spec) |
| `docs/` | `_archive/` | Superseded or no longer relevant (never delete -- archive) |

---

## Validation Rules -- Complete Matrix

| Check | Severity | What Validates It | Scope |
|-------|----------|------------------|-------|
| Frontmatter exists | CRITICAL | hook, audit | `docs/` excluding `_inbox/`, `_archive/` |
| All 8 required fields present | HIGH | hook, audit, index script | `docs/` excluding `_inbox/`, `_archive/` |
| `status` is valid enum | WARNING | hook, audit | All files with frontmatter |
| `type` is valid enum | WARNING | hook, audit | All files with frontmatter |
| `owner` is not blank/TBD/none | WARNING | hook, audit | All files with frontmatter |
| `version` follows semver | MEDIUM | audit | All managed docs |
| `created` is immutable | MEDIUM | audit | Compare across versions |
| `last-updated` >= `created` | MEDIUM | audit | All managed docs |
| `last-updated` within 90 days | MEDIUM | audit | Active docs with review-cycle |
| `last-updated` within 180 days | MEDIUM | audit | `_planned/` docs |
| DOMAIN exists and is clear | HIGH | audit | All active docs |
| EXCLUSIVELY_OWNS has 3+ items | HIGH | audit | All active docs |
| STRICTLY_AVOIDS exists | MEDIUM | audit | All active docs |
| Cross-references resolve | HIGH | audit | All docs with BUILDS_ON/REFERENCES/PROVIDES |
| No duplicated content | HIGH | audit | Cross-document comparison |
| No circular dependencies | MEDIUM | audit | Relationship graph |
| `depends-on`/`consumed-by` match ownership spec | MEDIUM | audit | Docs with both frontmatter links and ownership spec |

---

## Hook Enforcement

**Script:** `.claude/hooks/post_edit_frontmatter_check.py`
**Event:** PostToolUse (fires after Edit or Write)

### What It Validates

1. YAML frontmatter block exists (delimited by `---`)
2. All 8 required fields are present
3. `status` is one of: `draft`, `active`, `under-review`, `archived`
4. `type` is one of: `context`, `process`, `policy`, `reference`, `playbook`
5. `owner` is not blank, `TBD`, `todo`, or `none`

### When It Fires

After every Edit or Write tool call on a `.md` file under `docs/`.

### What It Skips

Files in these paths are excluded from validation:

- `docs/methodology/`
- `docs/guides/`
- `docs/templates/`
- `docs/_inbox/`
- `docs/_archive/`
- `docs/document-index.md`

### Behavior

The hook always exits 0 (non-blocking). When issues are found, it prints warnings to stderr. Claude sees these warnings in its context and self-corrects. This is by design -- blocking edits mid-flow is too disruptive.

### settings.json Configuration

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/post_edit_frontmatter_check.py\"",
            "timeout": 10,
            "statusMessage": "Checking frontmatter compliance..."
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/post_edit_frontmatter_check.py\"",
            "timeout": 10,
            "statusMessage": "Checking frontmatter compliance..."
          }
        ]
      }
    ]
  }
}
```

---

## Script Enforcement

**Script:** `.claude/scripts/build_document_index.py`
**Output:** `docs/document-index.md`

### What It Reports

The script scans `docs/` and generates a Document Index with:

- **Managed docs** -- files with YAML frontmatter, grouped by cluster
- **Unmanaged docs** -- files without frontmatter (candidates for formalization)
- **Incomplete metadata** -- managed docs missing one or more required fields
- **Inbox items** -- raw material in `_inbox/`, listed separately
- **Planned items** -- polished ideas in `_planned/`, listed separately
- **Archive items** -- superseded docs in `_archive/`, listed separately

### What It Skips

The script excludes framework files that are not user content:

- `docs/methodology/`
- `docs/guides/`
- `docs/templates/`
- `docs/document-index.md` (its own output)

### User Notes Preservation

The generated Document Index has two zones:

1. **Auto-generated section** -- overwritten every run (inventory, health, coverage)
2. **User notes section** -- preserved across runs (priorities, decisions, external references)

Zone boundaries are marked with HTML comments. The script reads the existing file, extracts user notes, regenerates the auto section, and re-attaches the user notes.

### Running the Script

```bash
python .claude/scripts/build_document_index.py              # Default: scan docs/
python .claude/scripts/build_document_index.py --path .     # Scan everything
python .claude/scripts/build_document_index.py --dry-run    # Print to stdout
```

---

## Staleness Thresholds

| Document Location | Threshold | Severity | Meaning |
|-------------------|-----------|----------|---------|
| `docs/*.md` (active) | 90 days | MEDIUM | Active docs not updated in 90 days are flagged by context-audit |
| `docs/_planned/` | 180 days | MEDIUM | Planned docs older than 6 months should be promoted to active or discarded |
| `docs/_inbox/` | N/A | N/A | No staleness check -- raw material has no quality bar |
| `docs/_archive/` | N/A | N/A | No staleness check -- historical, frozen as-was |

Staleness is measured from the `last-updated` field in frontmatter (or filesystem modification date for unmanaged files). The context-audit skill flags stale documents and recommends action.

---

## Quality Levels (L1-L5)

Documents progress through five quality levels. Levels 1-3 are required for `status: active`. Levels 4-5 are the ongoing maintenance standard.

### Level 1: Exists and Is Findable

- Has YAML frontmatter with all 8 required fields
- Lives in the correct cluster directory
- Is listed in the Document Index
- Filename is kebab-case and descriptive

### Level 2: Has Clear Ownership

- `owner` names a specific person or role
- Has an Ownership Specification section with DOMAIN at minimum
- DOMAIN is a clear, one-sentence scope statement
- EXCLUSIVELY_OWNS lists at least 3 specific items

### Level 3: Is Bounded

- STRICTLY_AVOIDS lists what belongs elsewhere (with cross-references)
- No content duplicated from another document
- Cross-references use linking, not copying

### Level 4: Is Current

- `last-updated` is recent relative to review cycle
- `status` accurately reflects the document's state
- Content matches current business reality
- No stale references to things that have changed

### Level 5: Is Connected

- BUILDS_ON / REFERENCES / PROVIDES relationships are documented
- `depends-on` and `consumed-by` in frontmatter match ownership spec
- Cross-references to other documents resolve (no broken links)

**Minimum to be "active":** Levels 1-3 must pass.

**Documents in `docs/_planned/`:** Frontmatter recommended, linking optional until promoted to active.

**Documents in `docs/_inbox/`:** No quality bar. Raw material waiting to be processed.

---

## Version Bumping Rules

Every edit to a document requires two metadata updates: bump `version` and set `last-updated` to today. Never touch `created`.

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Typo fix, formatting, minor wording | Patch (`x.x.+1`) | `1.0.0` -> `1.0.1` |
| New content added, section expanded, new examples | Minor (`x.+1.0`) | `1.0.1` -> `1.1.0` |
| Major restructure, ownership boundary change, split/merge | Major (`+1.0.0`) | `1.1.0` -> `2.0.0` |

### Status Definitions

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `draft` | In progress, not yet reliable | New documents being written |
| `active` | Current, accurate, trustworthy | The default state for maintained docs |
| `under-review` | Flagged for accuracy check | Triggered by staleness detection or content dispute |
| `archived` | No longer current but preserved | Superseded docs. Never delete -- archive instead. |

---

## Document Type Definitions

| Type | What It Is | Examples |
|------|-----------|---------|
| `context` | Business knowledge with clear ownership | Company identity, value proposition, competitive positioning |
| `process` | How something is done | Employee onboarding, content approval, release process |
| `policy` | Rules and decisions that govern behavior | Pricing rules, hiring criteria, brand usage |
| `reference` | Lookup information that rarely changes | Glossary, tool inventory, org chart, key metrics |
| `playbook` | Decision guides for recurring situations | Crisis comms, product launch, competitive response |
