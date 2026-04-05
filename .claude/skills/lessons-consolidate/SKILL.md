---
name: lessons-consolidate
description: Periodic maintenance of institutional knowledge. Analyzes lessons for staleness, overlaps, and gaps. Keeps lessons.json healthy.
category: maintenance
---

# Lessons Consolidate

## Purpose

**This skill IS:**
- A periodic curator of institutional knowledge in lessons.json
- A tool for detecting stale, overlapping, or contradictory lessons
- A way to keep the lessons collection healthy and useful

**This skill IS NOT:**
- For capturing new lessons (use ecosystem-manager for that)
- Automatically scheduled (invoke it periodically)
- A replacement for reading lessons (it maintains, doesn't apply them)

---

## When to Use

- Monthly or every 10-15 sessions (whichever comes first)
- When lessons.json feels cluttered
- When you suspect lessons are outdated
- When you want to understand patterns across sessions

---

## Modes

### 1. Analyze

Check the current state of lessons.json:

```bash
python .claude/scripts/consolidate_lessons.py
```

Identifies:
- **Stale lessons**: Referenced concepts that no longer exist
- **Overlapping lessons**: Multiple lessons saying the same thing
- **Contradictions**: Lessons that conflict with each other
- **Tag gaps**: Important topics with no lessons
- **Usage patterns**: Which tags are over/under-represented

### 2. Consolidate

After analysis, with user approval:
- Archive stale lessons (don't delete - move to archived section)
- Merge overlapping lessons into single stronger lessons
- Flag contradictions for user resolution
- Suggest new lessons for uncovered areas

### 3. Report

Generate a health summary:
- Total lessons and trend
- Tag distribution
- Staleness assessment
- Recommendations for next actions

---

## Guidelines

**Good lessons are:**
- Specific enough to act on
- General enough to apply to future situations
- Tagged with relevant categories
- Tied to a real experience (not hypothetical)

**Remove or archive when:**
- The lesson references something that no longer exists
- The lesson has been superseded by a better one
- The lesson is too vague to be useful
- The lesson contradicts current practice

---

## References

- Lessons file: `.claude/quality/ecosystem/lessons.json`
- Schema: `.claude/quality/ecosystem/lessons-schema.md`
- Consolidation script: `.claude/scripts/consolidate_lessons.py`
