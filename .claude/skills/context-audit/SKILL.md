---
name: context-audit
description: |
  Audits context architecture for CLEAR compliance, boundary enforcement, and consistency.

  WHEN TO USE:
  - User says "audit context for CLEAR"
  - User asks "check for duplication across data points"
  - User requests "find boundary violations in [area]"
  - Planning restructuring work
  - Before adding new data points (cleanup existing first)
  - Context quality improvement initiatives

  WHEN NOT TO USE:
  - Planning new features (use clear-planner instead)
  - Markdown syntax checking (use doc-lint instead)
  - Making changes directly (audit only, findings guide manual fixes)
allowed-tools: Read, Glob, Grep, Bash
---

# Context Audit

## Purpose

**This skill IS:**

- Auditing context data points for CLEAR compliance
- Finding duplication and ownership conflicts across data points
- Identifying boundary violations between context areas
- Enforcing consistency in naming, format, and structure
- Providing prioritized findings with improvement recommendations

**This skill IS NOT:**

- Making changes to context (audit only -- findings guide manual fixes)
- A fix-it tool (this finds problems, you fix them based on findings)
- Checking markdown syntax (use doc-lint for that)
- Planning new work (use clear-planner for that)

---

---

## Instructions

### Step 1: Define Audit Scope

**If not specified, use the `AskUserQuestion` tool:**

- Question: "What should I audit?"
- Options:
  - **Specific area** (e.g., competitive intelligence data points)
  - **Full architecture** (all active data points — comprehensive)
  - **Recent changes** (only docs modified recently)
  - **Cross-cutting concern** (e.g., all pricing-related data points across clusters)

---

### Step 2: Gather and Check Metadata

**Context window strategy:** For scopes with 20+ documents, delegate the metadata scanning to an explore agent. Keep the main window for CLEAR analysis (Step 3).

```
# For large scopes:
Agent (Explore): "Read all .md files in [scope]. Skip dot-prefixed files
(.session-diary.md, .wake-up-context.md, .onboarding-checklist.md) — these are
conventions, not managed data points. For each remaining file, extract YAML
frontmatter and check: all 7 required fields present? status valid? last-updated
within 90 days (180 days for _planned/)? Return a validation table."
```

For small scopes (< 20 files), scan directly:

1. **Scan target area for all managed documents:**

   ```bash
   Glob: [user-specified scope]/**/*.md
   Read: [identified files]
   ```

2. **Check YAML frontmatter on every document:**

   Required fields (see `docs/_bcos-framework/methodology/document-standards.md`):
   - `name` - present and non-empty
   - `type` - valid value: context | process | policy | reference | playbook
   - `cluster` - present and non-empty
   - `version` - follows semantic versioning (x.y.z)
   - `status` - valid value: draft | active | under-review | archived
   - `created` - valid ISO date, immutable (should never change between versions)
   - `last-updated` - valid ISO date, must be >= created date

3. **Flag metadata issues:**
   - Missing frontmatter entirely = CRITICAL
   - Missing required fields = HIGH
   - Stale `last-updated` (>90 days for active docs with a review-cycle) = MEDIUM
   - Docs in `_planned/` use relaxed staleness: 180 days = MEDIUM
   - Missing optional fields = LOW (informational)
   - Docs in `_planned/` with incomplete cross-references = LOW (informational, not error)

4. **Folder-based checks:**
   - Document in `docs/_planned/` older than 6 months → flag: "Consider promoting to active (move to docs/ root) or discarding"
   - Active document in `docs/` that `depends-on` a `_planned/` document → flag: "Forward-looking dependency — not yet real"
   - Files in `docs/_inbox/` → skip audit entirely (raw material, no quality bar)
   - Files in `docs/_archive/` → skip audit or report separately (historical, not active)
   - Files in `docs/_collections/` → skip full CLEAR audit (no frontmatter required), but verify collection indexes are current if they exist
   - External reference data points (type: reference with an "External Source" section) → verify the source description is complete, don't try to validate external paths

4. **Search for patterns:**
   ```bash
   Grep: "TODO|FIXME"           # Unresolved items
   Grep: [domain-specific terms] # Check consistency
   ```

---

### Step 3: CLEAR Audit Categories

**SAFETY RULE:** When duplication is found, consolidate into the owning document first, then clean up the duplicate. Never delete without ensuring content lives in its authoritative home.

> For background on consolidation principles, see `docs/_bcos-framework/methodology/document-standards.md`

Run all five audit categories against the scoped files.

#### A. Contextual Ownership Issues

Look for: multiple owners for same content, unclear responsibility (mixed domains in one doc), orphaned content (no consumers).

**Example finding format:**
```
ISSUE: "Company mission" defined in both company-overview.md AND strategic-plan.md
VIOLATION: No clear single owner
RESOLUTION: Designate one as owner, other links to it
EFFORT: LOW | VALUE: HIGH | PRIORITY: QUICK WIN
```

#### B. Linking Issues (Should Reference, Not Duplicate)

Look for: duplicated information across data points, copy-paste between docs, inconsistent cross-reference format (relative vs absolute links).

#### C. Elimination Issues (Remove Duplication)

Look for: same content in multiple places, redundant data points covering same concept, hardcoded values repeated across docs. Resolution is always: extract to single authority, others reference it.

#### D. Alignment Issues (Consistency Problems)

Look for: naming inconsistency (e.g., `market_category` vs `marketCategory`), format differences (tables vs lists for same content type), structure inconsistency in frontmatter.

#### E. Refinement Issues (Clarity Problems)

Look for: overly complex data points (500+ lines covering multiple concepts -- split them), vague language ("various market factors"), missing maintenance metadata (no `last-updated` or `review-cycle`).

---

### Step 4: Technical Debt Identification

**Search for debt markers:**

```bash
Grep: "TODO"
Grep: "FIXME"
Grep: "OUTDATED"
Grep: "DEPRECATED"
```

**Categorize debt:**

```markdown
## Technical Debt

### Active TODOs
- X total found
- Y urgent (>6 months old)
- Z recent (<2 months)

### Stale Content
- Documents not updated in >6 months
- Broken cross-references
- Orphaned sections
```

---

### Step 5: Priority Matrix

Score each issue: `Priority = (Impact x Frequency) / (Effort x Risk)`

| Impact Level | Score | Effort Level | Score |
|-------------|-------|-------------|-------|
| CRITICAL (blocks context delivery) | 10 | Quick (< 1 hour) | 0.5 |
| HIGH (causes wrong decisions) | 7 | Medium (1-4 hours) | 2 |
| MEDIUM (slows consumers) | 5 | Large (1+ day) | 8 |
| LOW (minor inconvenience) | 2 | | |

Classify into quadrants: **QUICK WINS** (high value, low effort -- do first), **BIG WINS** (high value, high effort -- plan carefully), **LOW PRIORITY**, **AVOID**.

---

### Step 6: Generate Output

Produce a report with these sections:
1. **Executive Summary** -- total issues, critical count, quick win count
2. **CLEAR Analysis** -- one subsection per category (C/L/E/A/R) with findings
3. **Priority Matrix** -- issues sorted into quadrants
4. **Recommendations** -- immediate actions, this sprint, ongoing

---

## Severity Levels

| Severity     | Description                                   | Action Timeline   |
| ------------ | --------------------------------------------- | ----------------- |
| **CRITICAL** | Boundary violation, wrong information served  | Fix immediately   |
| **HIGH**     | Duplication causing divergence, broken links   | Fix this sprint   |
| **MEDIUM**   | Inconsistency, unclear ownership              | Fix when in area  |
| **LOW**      | Style issues, minor naming differences        | Nice to have      |

---

## Archive Compression Convention

When archiving a document (moving to `docs/_archive/`), also append a compressed summary line to `docs/_archive/index.md`:

```markdown
## Archive Index

| Date | Document | Summary |
|------|----------|---------|
| 2026-04-07 | pricing-strategy-v1.md | Original flat-rate pricing model. Superseded by usage-based model in v2. |
```

**Who does what:**
- AI writes the 1-line summary (requires understanding the document)
- The append to `_archive/index.md` is a simple file write (mechanical)
- If `_archive/index.md` doesn't exist, create it with the table header

This ensures archived documents remain discoverable without reading full files.

---

## Document Index Maintenance

After every audit, refresh the Document Index:

```bash
python .claude/scripts/build_document_index.py
```

This regenerates `docs/document-index.md` from current file state — picks up new data points, reflects renames, updates metadata health. No manual editing needed.

If the script isn't available or the Document Index needs enrichment beyond what the script provides (gap analysis, recommendations), update it manually.

---

> **Architecture docs:** For metadata validation rules, see [`docs/_bcos-framework/architecture/metadata-system.md`](../../docs/_bcos-framework/architecture/metadata-system.md)

## References

- `references/clear-principles-checks.md` - Detailed CLEAR compliance checks
- `docs/_bcos-framework/methodology/clear-principles.md` - CLEAR methodology overview
- `docs/_bcos-framework/architecture/content-routing.md` - Content routing paths (6 paths including collections and external references)
- `.claude/skills/doc-lint/SKILL.md` - For markdown syntax validation
- `.claude/skills/ecosystem-manager/SKILL.md` - For ecosystem health auditing
