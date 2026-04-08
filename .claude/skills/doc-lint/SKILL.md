---
name: doc-lint
description: |
  Validates documentation quality: markdown syntax, cross-references, JSON structure.

  WHEN TO USE:
  - Validating markdown files for quality issues
  - Checking cross-references between documents
  - Validating JSON structure in ecosystem files
  - As part of FIXED END validation in any scenario

  WHEN NOT TO USE:
  - Content quality auditing (use context-audit for that)
  - Making content changes (findings guide manual fixes)
allowed-tools: Read, Glob, Grep, Bash
---

# Doc-Lint Skill

## Purpose

**This skill IS:**

- **Markdown validator**: Checks MD040 (language tags), heading levels, link validity
- **Cross-reference checker**: Validates links between documents resolve
- **JSON structure validator**: Checks for duplicate keys, valid structure
- **Quality reporter**: Produces actionable findings with file:line references

**This skill IS NOT:**

- **Auto-fixer**: Reports issues, does not fix them
- **Content quality auditor**: Checks syntax, not content quality (that's context-audit)
- **Full linter**: Focused subset of checks relevant to context ecosystems

---

## Validation Categories

### 1. Markdown Quality

| Check                 | Severity | Description                             |
| --------------------- | -------- | --------------------------------------- |
| MD040                 | LOW      | Fenced code blocks without language tag |
| Heading jumps         | LOW      | h1 to h3 without h2                    |
| Broken internal links | MEDIUM   | Links to non-existent files             |
| Missing frontmatter   | MEDIUM   | SKILL.md or AGENT.md without frontmatter |
| Trailing whitespace   | LOW      | Lines ending with spaces                |

### 2. Cross-Reference Validation

| Check                  | Severity | Description                                  |
| ---------------------- | -------- | -------------------------------------------- |
| Broken file links      | HIGH     | Markdown links to files that don't exist     |
| Broken section anchors | MEDIUM   | Links to headings that don't exist in target |
| Orphaned documents     | LOW      | Files not referenced by any other document   |

### 3. JSON Structure Validation

| Check               | Severity | Description                      |
| ------------------- | -------- | -------------------------------- |
| Duplicate keys      | HIGH     | Same key appears twice in object |
| Duplicate IDs       | HIGH     | Same ID in array of objects      |
| Trailing commas     | MEDIUM   | Invalid JSON syntax              |
| Malformed structure | HIGH     | Parse errors                     |

---

## Invocation

### Inline (FIXED END)

Runs automatically as part of scenario FIXED END phases.

### Direct

```
@doc-lint {file-or-directory}
@doc-lint .claude/skills/
@doc-lint docs/context/
```

---

## Context-Aware Filtering

**Skip files that should not be validated:**

| Location                      | Handling           |
| ----------------------------- | ------------------ |
| `_archive/`                   | SKIP entirely      |
| `_inbox/`                     | SKIP entirely      |
| `_planned/`                   | Relaxed validation |
| `.claude/quality/sessions/*/` | SKIP (historical)  |
| Inside example blocks         | Relaxed validation |
| Intentionally invalid         | SKIP if marked     |

**Content markers that skip validation:**

- `// Invalid:` - Intentional bad example
- `# Bad example` - Intentional bad example
- `HISTORICAL:` - Audit documentation
- `...` in code - Partial snippet

---

## Output Schema

```json
{
  "mode": "doc_lint",
  "timestamp": "ISO-8601",
  "scope": {
    "files": ["list of files checked"],
    "skipped": ["list of files skipped with reason"]
  },
  "summary": {
    "high": 0,
    "medium": 0,
    "low": 0,
    "total": 0
  },
  "findings": [
    {
      "id": "LINT-001",
      "category": "markdown_quality | cross_reference | json_structure",
      "severity": "HIGH | MEDIUM | LOW",
      "location": "file:line",
      "issue": "Description of the issue",
      "suggestedFix": "Action to take"
    }
  ],
  "contextFiltered": [
    {
      "location": "file:line",
      "reason": "historical_session | archived | intentional_example"
    }
  ]
}
```

---

## Workflow

### Step 1: Discover Files

```bash
# For directory input
Glob: {directory}/**/*.md
Glob: {directory}/**/*.json
```

### Step 2: Apply Pre-Filter

Skip archived files, historical sessions, and intentionally invalid content.

### Step 3: Validate Each File

For each file:
- If `.md`: Run markdown quality checks and cross-reference validation
- If `.json`: Run JSON structure validation

### Step 4: Generate Report

Aggregate findings, apply context filtering, output report with file:line references.

---

## Integration with Scenarios

### DOCUMENTATION Scenario FIXED END

```
Px_001: Run markdown quality check    -> doc-lint (markdown category)
Px_002: Run example code validation   -> doc-lint (cross_reference category)
```

### AGENTING Scenario FIXED END

```
Px_001: Run JSON structure validation -> doc-lint (json_structure category)
Px_002: Run markdown quality check    -> doc-lint (markdown category)
```

---

## Key Principles

1. **Detection only** - Report issues, don't auto-fix
2. **Context-aware** - Skip historical/archived files
3. **Actionable** - Every finding has location and suggested fix
4. **Low noise** - Filter false positives before reporting

---

## Related Documents

- `docs/methodology/document-standards.md` - The standards this skill validates against (required fields, valid types, valid statuses)
- `.claude/skills/context-audit/SKILL.md` - For content quality auditing
- `.claude/skills/clear-planner/references/scenario-phases.md` - FIXED END integration
