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

**Ask user to clarify if not specified:**

```
What should I audit?

Options:
1. Specific context area (e.g., "competitive intelligence data points")
2. Specific directory (e.g., "docs/context/")
3. Cross-cutting concern (e.g., "all pricing-related data points")
4. Full context architecture
5. Recent changes

Recommendation for large scopes: Start with one area, then expand.

Please specify scope.
```

---

### Step 2: Gather and Check Metadata

1. **Scan target area for all managed documents:**

   ```bash
   Glob: [user-specified scope]/**/*.md
   Read: [identified files]
   ```

2. **Check YAML frontmatter on every document:**

   Required fields (see `docs/methodology/document-standards.md`):
   - `name` - present and non-empty
   - `type` - valid value: context | process | policy | reference | playbook
   - `cluster` - present and non-empty
   - `version` - follows semantic versioning (x.y.z)
   - `status` - valid value: draft | active | under-review | archived
   - `owner` - present, not "TBD" or blank
   - `created` - valid ISO date, immutable (should never change between versions)
   - `last-updated` - valid ISO date, must be >= created date

3. **Flag metadata issues:**
   - Missing frontmatter entirely = CRITICAL
   - Missing required fields = HIGH
   - Stale `last-updated` (>90 days for active docs with a review-cycle) = MEDIUM
   - Missing optional fields = LOW (informational)

4. **Search for patterns:**
   ```bash
   Grep: "TODO|FIXME"           # Unresolved items
   Grep: [domain-specific terms] # Check consistency
   ```

---

### Step 3: CLEAR Audit Categories

**SAFETY RULE: When duplication is found, consolidate into the owning document first, then clean up the duplicate. Never delete content without ensuring it lives in its authoritative home. The goal is clean, single-source-of-truth documents -- not cluttered ones with archived sections everywhere.**

Run all five audit categories against the scoped files.

#### A. Contextual Ownership Issues

**Look for:**

1. **Multiple owners for same content:**

   ```
   ISSUE: "Company mission" defined in both company-overview.md AND strategic-plan.md
   VIOLATION: No clear single owner for mission statement
   RESOLUTION: Designate one as owner, other links to it
   ```

2. **Unclear responsibility:**

   ```
   ISSUE: data-point-helpers.md contains unrelated sections:
   - Pricing analysis helpers
   - Competitor identification helpers
   - Market sizing helpers
   VIOLATION: Mixed responsibility in one data point
   RESOLUTION: Split by domain
   ```

3. **Orphaned content:**

   ```
   ISSUE: Section in context doc not referenced by any other doc
   VIOLATION: Content exists without clear consumer
   RESOLUTION: Link from consumers or remove if obsolete
   ```

**Audit output:**

```markdown
## Ownership Issues

### Critical: Content Without Single Owner

#### Issue 1: Market Segment Duplication

- **Files:**
  - `docs/context/company-overview.md` (includes mission statement)
  - `docs/context/strategic-plan.md` (also states mission)
- **CLEAR Violation:** No single owner for mission statement
- **Recommendation:** Designate company-overview.md as owner, strategic-plan.md links to it
- **Effort:** LOW (1 hour)
- **Value:** HIGH (prevents future divergence)
- **Priority:** QUICK WIN
```

#### B. Linking Issues (Should Reference, Not Duplicate)

**Look for:**

1. **Duplicated information across data points:**

   ```
   ISSUE: Company description appears in 3 separate context documents
   VIOLATION: Should link to single source, not copy
   ```

2. **Copy-paste between data points:**

   ```
   ISSUE: Same methodology explanation in multiple docs
   VIOLATION: DRY principle -- link to one authority source
   ```

3. **Inconsistent cross-references:**
   ```
   ISSUE: Some docs use relative links, others use absolute
   VIOLATION: Inconsistent linking format
   ```

**Audit output:**

```markdown
## Linking Issues

### High: Information Duplication

#### Issue 1: Company Description Scattered

- **Pattern:** Company overview text
- **Locations:**
  - `brand-identity.md` (lines 20-35)
  - `competitive-positioning.md` (lines 5-15)
  - `value-proposition.md` (lines 10-20)
- **CLEAR Violation:** Should link to single source
- **Recommendation:**
  - Define once in `brand-identity.md` (it EXCLUSIVELY_OWNS brand story)
  - Other data points reference: "See Brand Identity for company overview"
- **Effort:** LOW (30 minutes)
- **Value:** HIGH (prevents divergence)
- **Priority:** QUICK WIN
```

#### C. Elimination Issues (Remove Duplication)

**Detect duplication:**

1. **Same content in multiple places:**

   ```
   ISSUE: Identical pricing tier definitions in 4 documents
   RESOLUTION: Extract to single authority, others reference it
   ```

2. **Redundant data points:**

   ```
   ISSUE: Two data points covering same concept with slight variation
   RESOLUTION: Merge into one comprehensive data point
   ```

3. **Hardcoded values repeated:**
   ```
   ISSUE: Same threshold values defined in multiple contexts
   RESOLUTION: Define constants in one place
   ```

#### D. Alignment Issues (Consistency Problems)

**Check for:**

1. **Naming inconsistency:**

   ```
   ISSUE: "market_category" in one doc, "marketCategory" in another, "Market Category" in third
   RESOLUTION: Pick one convention, apply everywhere
   ```

2. **Format differences:**

   ```
   ISSUE: Some data points use tables, others use lists for same type of information
   RESOLUTION: Standardize format per content type
   ```

3. **Structure inconsistency:**
   ```
   ISSUE: Data point frontmatter varies between documents
   RESOLUTION: Define standard frontmatter schema, apply consistently
   ```

#### E. Refinement Issues (Clarity Problems)

**Check for:**

1. **Overly complex data points:**

   ```
   ISSUE: Single data point covers 5 different concepts across 500 lines
   RESOLUTION: Split into focused data points, one concept each
   ```

2. **Unclear language:**

   ```
   ISSUE: Vague descriptions like "various market factors"
   RESOLUTION: Use precise, specific language
   ```

3. **Missing maintenance documentation:**
   ```
   ISSUE: No indication of when document was last updated
   RESOLUTION: Ensure last-updated date and review-cycle are set in frontmatter
   ```

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

**Calculate for each issue:**

```
Priority = (Impact x Frequency) / (Effort x Risk)

Impact:
- CRITICAL: Prevents accurate context delivery (10)
- HIGH: Causes confusion or wrong decisions (7)
- MEDIUM: Slows context consumers (5)
- LOW: Minor inconvenience (2)

Effort (hours):
- Quick (< 1 hour): 0.5
- Medium (1-4 hours): 2
- Large (1+ day): 8
```

**Priority Quadrants:**

```
                 High Value
                     |
         QUICK WINS  |  BIG WINS
         (Do first)  | (Plan carefully)
    Low  ------------|------------ High
    Effort           |            Effort
         LOW         |  AVOID
         PRIORITY    | (Not worth it)
                     |
                 Low Value
```

---

### Step 6: Generate Output

**Output format:**

```markdown
# Context Audit Report: [Scope]

**Audit Date:** [Date]
**Scope:** [What was audited]

## Executive Summary

- Total Issues: X
- Critical: Y (boundary violations, blocking)
- Quick Wins: Z (< 1 hour, high value)

## CLEAR Analysis

### Contextual Ownership
[Ownership conflicts found...]

### Linking
[Should reference, not duplicate...]

### Elimination
[Duplication to remove...]

### Alignment
[Consistency issues...]

### Refinement
[Clarity improvements...]

## Priority Matrix

### QUICK WINS (High Value, Low Effort)
[List...]

### BIG WINS (High Value, High Effort)
[List with modular plans...]

### LOW PRIORITY
[List...]

## Recommendations

### Immediate Actions
1. Fix critical boundary violations
2. Complete quick wins
3. Standardize naming conventions

### This Sprint
1. Merge duplicate data points
2. Fix broken cross-references
3. Add missing ownership designations

### Ongoing
1. Regular context audit cadence
2. Ownership review when adding new data points
3. Cross-reference validation across data points
```

---

## Severity Levels

| Severity     | Description                                   | Action Timeline   |
| ------------ | --------------------------------------------- | ----------------- |
| **CRITICAL** | Boundary violation, wrong information served  | Fix immediately   |
| **HIGH**     | Duplication causing divergence, broken links   | Fix this sprint   |
| **MEDIUM**   | Inconsistency, unclear ownership              | Fix when in area  |
| **LOW**      | Style issues, minor naming differences        | Nice to have      |

---

## Quick Reference Checklist

Before declaring any context area "clean":

- [ ] Every data point has exactly one owner
- [ ] No content is duplicated across data points
- [ ] All cross-references resolve
- [ ] Naming is consistent throughout
- [ ] No orphaned content exists
- [ ] Frontmatter follows standard schema
- [ ] Last-reviewed dates are current
- [ ] No stale TODOs older than 6 months
- [ ] Document Index (`docs/document-index.md`) is up to date

---

## Document Index Maintenance

After every audit, refresh the Document Index:

```bash
python .claude/scripts/build_document_index.py
```

This regenerates `docs/document-index.md` from current file state — picks up new data points, reflects renames, updates metadata health. No manual editing needed.

If the script isn't available or the Document Index needs enrichment beyond what the script provides (gap analysis, recommendations), update it manually.

---

## References

- `references/clear-principles-checks.md` - Detailed CLEAR compliance checks
- `docs/methodology/clear-principles.md` - CLEAR methodology overview
- `.claude/skills/doc-lint/SKILL.md` - For markdown syntax validation
- `.claude/skills/ecosystem-manager/SKILL.md` - For ecosystem health auditing
