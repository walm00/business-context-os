# CLEAR Principles Checks for Context Auditing

**Purpose:** Detailed compliance checks for each CLEAR principle when auditing context architecture.
**Consumer:** context-audit skill

---

## Overview

Each CLEAR principle maps to specific, verifiable checks. This reference provides the exhaustive checklist used during context audits.

---

## C -- Contextual Ownership Checks

**Principle:** Every piece of content has exactly one owning document — one source of truth for that topic.

### Checks

| ID    | Check                                | Severity | How to Verify                                                        |
| ----- | ------------------------------------ | -------- | -------------------------------------------------------------------- |
| C-001 | Single owner per data point          | CRITICAL | Search for same concept defined in multiple files                    |
| C-002 | Clear DOMAIN designation             | HIGH     | Each data point file declares what domain it owns                    |
| C-003 | No orphaned content                  | MEDIUM   | Every section is referenced by at least one consumer                 |
| C-004 | Ownership Specification exists       | HIGH     | Each data point has DOMAIN + EXCLUSIVELY_OWNS section defining its topic boundaries |
| C-005 | Boundary documentation exists        | MEDIUM   | Each data point describes what it covers AND what it does not cover  |
| C-006 | No cross-boundary reaching           | HIGH     | Data points do not modify or directly depend on another's internals  |
| C-007 | Ownership transfers are documented   | LOW      | If ownership moved, there is a record of the transfer                |

### Detection Patterns

```bash
# C-001: Find potential ownership conflicts
# Search for same key terms defined in multiple files
Grep: "## Definition" across all context files
# If same term defined in >1 file, ownership conflict exists

# C-003: Find orphaned sections
# Cross-reference all internal links
# Sections with zero incoming links may be orphaned

# C-006: Find cross-boundary violations
# Look for direct file reads between context areas
Grep: "import.*from.*context/" # or equivalent reference patterns
```

### Pass Criteria

- PASS: Every data point has exactly one owner, boundaries are clear
- PASS WITH FINDINGS: Minor boundary documentation gaps
- NEEDS ACTION: Ownership conflicts found
- BLOCKED: Critical ownership ambiguity preventing reliable context delivery

---

## L -- Linking Checks

**Principle:** Reference, don't duplicate. Link to the source of truth.

### Checks

| ID    | Check                                  | Severity | How to Verify                                                    |
| ----- | -------------------------------------- | -------- | ---------------------------------------------------------------- |
| L-001 | Cross-references use proper format     | MEDIUM   | Links follow consistent format (relative/absolute, syntax)       |
| L-002 | No copy-paste between data points      | HIGH     | Same paragraph or section does not appear in multiple files       |
| L-003 | Links resolve to existing targets      | HIGH     | All cross-references point to files/sections that exist           |
| L-004 | Source of truth is identifiable        | CRITICAL | For any piece of information, one authoritative source is clear  |
| L-005 | Backlinks are maintained               | LOW      | If A links to B, B is aware it is referenced by A               |
| L-006 | Link labels are descriptive            | LOW      | Links use meaningful text, not "click here" or bare URLs         |
| L-007 | No circular references                 | MEDIUM   | A links to B links to A creates loops without resolution         |

### Detection Patterns

```bash
# L-001: Check link format consistency
Grep: "\[.*\]\(.*\.md\)" # Find all markdown links
# Verify: all follow same relative/absolute pattern

# L-002: Detect duplicated paragraphs
# Compare text blocks across files
# Flag >3 consecutive identical sentences

# L-003: Verify link targets exist
# Extract all link targets from markdown
# Check each target file/section exists
```

### Pass Criteria

- PASS: All references link to sources, no duplication
- PASS WITH FINDINGS: Minor format inconsistencies
- NEEDS ACTION: Duplicated content found
- BLOCKED: Broken links to critical dependencies

---

## E -- Elimination Checks

**Principle:** Remove duplication. DRY content across the architecture.

### Checks

| ID    | Check                                    | Severity | How to Verify                                                |
| ----- | ---------------------------------------- | -------- | ------------------------------------------------------------ |
| E-001 | No duplicate information                 | HIGH     | Same fact not stated in multiple data points                 |
| E-002 | DRY content across architecture          | MEDIUM   | Shared concepts extracted to common location                 |
| E-003 | No redundant data points                 | HIGH     | No two data points cover the same concept                    |
| E-004 | Deprecated content is removed            | MEDIUM   | Old/superseded content not lingering in architecture         |
| E-005 | No copy-paste artifacts                  | LOW      | No leftover template boilerplate or placeholder text         |
| E-006 | Constants defined once                   | MEDIUM   | Threshold values, categories, enums defined in one location  |

### Detection Patterns

```bash
# E-001: Find duplicate facts
# Compare key definitions across files
# Flag when same definition appears in >1 location

# E-003: Find redundant data points
# List all data point purpose statements
# Flag overlapping purpose descriptions

# E-006: Find scattered constants
Grep: "threshold|limit|maximum|minimum" # across all context files
# Flag same value defined in multiple places
```

### Pass Criteria

- PASS: No duplication, single source of truth for all facts
- PASS WITH FINDINGS: Minor constant duplication
- NEEDS ACTION: Significant content duplication found
- BLOCKED: Contradictory duplicate information (different values for same concept)

---

## A -- Alignment Checks

**Principle:** Consistent naming, format, and compatible structures.

### Checks

| ID    | Check                                  | Severity | How to Verify                                                     |
| ----- | -------------------------------------- | -------- | ----------------------------------------------------------------- |
| A-001 | Consistent naming conventions          | HIGH     | Same concept uses same name everywhere (no synonyms)              |
| A-002 | Consistent format across data points   | MEDIUM   | Similar content types use same structural format                  |
| A-003 | Compatible data structures             | HIGH     | Related data points use compatible schemas                        |
| A-004 | Consistent frontmatter schema          | MEDIUM   | All data point files follow same frontmatter format               |
| A-005 | Terminology glossary exists            | LOW      | Canonical terms are defined in one place                          |
| A-006 | Date formats are consistent            | LOW      | All dates use same format (ISO 8601 recommended)                  |
| A-007 | Heading hierarchy is consistent        | LOW      | All docs use same heading level conventions                       |

### Detection Patterns

```bash
# A-001: Check naming consistency
Grep: "market.category|market_category|marketCategory"
# Flag if >1 naming convention used for same concept

# A-002: Check format consistency
# Compare structure of similar data points
# Flag when tables vs lists used for same type of information

# A-004: Check frontmatter consistency
Grep: "^---" # Find all files with frontmatter
# Compare frontmatter fields across files
```

### Pass Criteria

- PASS: Consistent naming, format, and structure throughout
- PASS WITH FINDINGS: Minor format variations in low-priority areas
- NEEDS ACTION: Naming conflicts or structural incompatibilities
- BLOCKED: Critical naming collision causing wrong data resolution

---

## R -- Refinement Checks

**Principle:** Clear language, self-documenting, proper maintenance documentation.

### Checks

| ID    | Check                                 | Severity | How to Verify                                                    |
| ----- | ------------------------------------- | -------- | ---------------------------------------------------------------- |
| R-001 | Clear, specific language              | MEDIUM   | No vague terms like "various factors" or "etc."                  |
| R-002 | Self-documenting structure            | MEDIUM   | Data point purpose is clear from reading it                      |
| R-003 | Proper maintenance documentation      | LOW      | Last-reviewed date, review cadence documented                    |
| R-004 | Reasonable data point size            | MEDIUM   | No single data point covers >3 distinct concepts                 |
| R-005 | Examples provided where helpful       | LOW      | Complex concepts have illustrative examples                      |
| R-006 | No jargon without definition          | LOW      | Domain-specific terms are defined on first use or in glossary    |
| R-007 | Change history is traceable           | LOW      | Can determine when and why data point was last modified          |

### Detection Patterns

```bash
# R-001: Find vague language
Grep: "various|several|some|etc\.|and more|and so on"
# Flag as potential clarity improvement

# R-004: Check data point complexity
# Count distinct h2 sections in each file
# Flag files with >5 major sections as potentially too complex

# R-003: Check for maintenance metadata
Grep: "last.reviewed|last.updated|review.date"
# Flag files missing maintenance dates
```

### Pass Criteria

- PASS: Clear language, well-structured, maintained
- PASS WITH FINDINGS: Minor clarity improvements possible
- NEEDS ACTION: Complex data points need splitting, vague language needs specificity
- BLOCKED: Critical data point is unintelligible or severely outdated

---

## Aggregate Audit Status

Combine individual principle results:

| Aggregate Status     | Condition                                                 |
| -------------------- | --------------------------------------------------------- |
| **PASS**             | All principles PASS                                       |
| **PASS_WITH_FINDINGS** | All principles PASS or PASS WITH FINDINGS               |
| **NEEDS_ACTION**     | At least one principle NEEDS ACTION, none BLOCKED         |
| **BLOCKED**          | At least one principle BLOCKED                            |

---

## Quick Reference

### Must-Check (Every Audit)

1. C-001: Single owner per data point
2. L-003: All links resolve
3. L-004: Source of truth identifiable
4. E-001: No duplicate information
5. A-001: Consistent naming

### Should-Check (Thorough Audit)

6. C-005: Boundary documentation
7. E-003: No redundant data points
8. A-002: Format consistency
9. R-001: Clear language
10. R-004: Reasonable data point size

### Nice-to-Check (Full Audit)

11. L-005: Backlinks maintained
12. A-005: Terminology glossary
13. R-003: Maintenance documentation
14. R-005: Examples provided
