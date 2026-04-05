# Learnings Capture Reference

## When to Capture

Capture lessons after:
- Completing a significant implementation session
- Encountering unexpected behavior or blockers
- Discovering a pattern that should be repeated (or avoided)
- Resolving a non-obvious problem
- Any session where you think "I wish I'd known this before"

---

## Lesson Format

Each lesson in `lessons.json` follows this structure:

```json
{
  "id": "L-{ORIGIN}-{YYYYMMDD}-{SEQ}",
  "date": "YYYY-MM-DD",
  "source": "Description of the session or event",
  "type": "pattern | anti-pattern | insight | decision",
  "tags": ["relevant", "category", "tags"],
  "lesson": "Clear, actionable description of what was learned",
  "applicability": "When this lesson applies (context/conditions)"
}
```

### ID Format

`L-{ORIGIN}-{YYYYMMDD}-{SEQ}`

- **L**: Prefix (always "L" for lesson)
- **ORIGIN**: Short identifier for the source (e.g., "ECO" for ecosystem, "DOC" for documentation, "INIT" for initial setup)
- **YYYYMMDD**: Date the lesson was captured
- **SEQ**: Sequential number for that day (001, 002, etc.)

**Examples:**
- `L-ECO-20260315-001` - First ecosystem lesson on March 15, 2026
- `L-DOC-20260320-002` - Second documentation lesson on March 20, 2026
- `L-INIT-20260401-001` - First onboarding lesson on April 1, 2026

### Type Definitions

| Type         | Meaning                                          |
| ------------ | ------------------------------------------------ |
| pattern      | Something that worked well and should be repeated |
| anti-pattern | Something that caused problems and should be avoided |
| insight      | A realization that changes understanding          |
| decision     | A choice that was made and why                    |

---

## Quality Criteria for Good Lessons

A good lesson is:

1. **Specific enough to act on** - "Always run discovery before creating agents" (good) vs. "Be careful" (bad)
2. **General enough to apply again** - "Check for overlaps when adding skills" (good) vs. "The foo-skill conflicted with bar-skill on March 15" (too specific)
3. **Tagged accurately** - Tags should match the domain areas where this lesson applies
4. **Tied to real experience** - Based on something that actually happened, not hypothetical
5. **Self-contained** - Understandable without reading the full session history

---

## Anti-Patterns in Lesson Capture

Avoid these common problems:

### Too Vague
- Bad: "Planning is important"
- Good: "Running discovery scripts before planning prevents duplicate agent creation"

### Too Specific (Not Reusable)
- Bad: "The ecosystem-manager skill's SKILL.md needed a fix on line 42 on March 15"
- Good: "Skill SKILL.md files should be validated against the required sections checklist after creation"

### Duplicates
- Before adding a lesson, search existing lessons for similar content
- If a similar lesson exists, consider updating it instead of creating a duplicate
- Use `find_lessons.py --tags "relevant-tag"` to check

### Missing Applicability
- Bad: `"applicability": ""` (empty)
- Good: `"applicability": "When creating new skills in the ecosystem"` (clear context)

### Stale References
- Bad: Referencing a component or file that no longer exists
- Good: Reference concepts and patterns, not specific file paths that may change

---

## Storage

Lessons are stored in: `.claude/quality/ecosystem/lessons.json`

The schema is defined in: `.claude/quality/ecosystem/lessons-schema.md`

Use `python .claude/scripts/find_lessons.py --tags "tag"` to search lessons by tag.
