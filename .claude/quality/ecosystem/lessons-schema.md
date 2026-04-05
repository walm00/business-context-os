# Lessons Schema - v1.0

Schema definition for the institutional lessons knowledge base.

---

## File Structure

```json
{
  "schemaVersion": "1.0",
  "lastUpdated": "YYYY-MM-DD",
  "totalLessons": <number>,
  "lessonsLearned": [ <Lesson[]> ]
}
```

---

## Lesson Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier. Format: `L-{ORIGIN}-{YYYYMMDD}-{SEQ}` |
| `date` | string | Yes | Date lesson was recorded. Format: `YYYY-MM-DD` |
| `source` | string | Yes | Where the lesson originated (e.g., "CLEAR methodology", "audit session", "incident review") |
| `type` | enum | Yes | Category of the lesson |
| `tags` | string[] | Yes | Hashtag taxonomy tags for searchability |
| `lesson` | string | Yes | The lesson itself. One to two sentences, actionable |
| `applicability` | string | Yes | When and where to apply this lesson |

---

## ID Format

```
L-{ORIGIN}-{YYYYMMDD}-{SEQ}
```

- **L** - Prefix (Lesson)
- **ORIGIN** - Source identifier (e.g., INIT, AUDIT, INCIDENT, RETRO, CONSOLIDATION)
- **YYYYMMDD** - Date recorded
- **SEQ** - Three-digit sequence number within that date and origin (001, 002, ...)

Examples:
- `L-INIT-20260404-001` - Initial seed lesson
- `L-AUDIT-20260415-003` - Third lesson from an audit on April 15
- `L-RETRO-20260501-001` - First lesson from a May retrospective

---

## Type Enum

| Value | Description |
|-------|-------------|
| `principle` | Fundamental truth about context management. Rarely changes. |
| `practice` | Proven technique or approach. Evolves with experience. |
| `pattern` | Recurring situation with a known effective response. |
| `anti-pattern` | Recurring situation with a known ineffective response to avoid. |

---

## Tag Taxonomy

Tags follow a three-tier system: mandatory, recommended, and custom.

### Tier 1: Mandatory (at least 1 required)

These map to CLEAR principles and core concerns. Every lesson must have at least one:

| Tag | When to Use |
|-----|------------|
| `#ownership` | Lessons about who owns what, single source of truth |
| `#linking` | Lessons about relationships, references, cross-connections |
| `#elimination` | Lessons about removing duplication, consolidation |
| `#alignment` | Lessons about consistency, naming, structure |
| `#refinement` | Lessons about improving, simplifying, clarifying |
| `#architecture` | Lessons about structural decisions, clusters, data points |
| `#maintenance` | Lessons about upkeep, freshness, review cycles |
| `#ecosystem` | Lessons about the skill/agent system itself |

### Tier 2: Recommended (use when applicable)

These add operational context. Use when they genuinely apply:

| Tag | When to Use |
|-----|------------|
| `#drift` | Context degradation, staleness, divergence |
| `#boundaries` | Scope definition, what belongs where |
| `#workflow` | Process and operational patterns |
| `#adoption` | Onboarding, progressive use, getting started |
| `#infrastructure` | Tooling, automation, scheduling |
| `#consolidation` | Merging, deduplication, cleanup |
| `#context` | General context management |
| `#simplicity` | Keeping things minimal and clear |
| `#consistency` | Uniform naming and structure |

### Tier 3: Custom (extend thoughtfully)

You may create new tags when Tier 1 and 2 don't fit. Before creating a custom tag:

1. **Check existing tags first.** Run `python .claude/scripts/find_lessons.py` to see all current tags.
2. **Check if a Tier 1 or 2 tag covers it.** Most lessons fit existing tags.
3. **If you must create one:** Use `#lowercase-kebab-case` format. Document it here by adding it to this section.
4. **Domain tags are welcome** when a lesson is specific to a business area: `#operations`, `#strategy`, `#onboarding`, `#compliance`, etc. These help filter lessons by function.

### Tag Selection Guidance

When tagging a new lesson, follow this process:

1. **Start with Tier 1.** Which CLEAR principle does this lesson relate to? Pick 1-2.
2. **Add Tier 2 if relevant.** Does an operational tag add useful context? Add it.
3. **Add a domain tag only if the lesson is specific** to a business area. Most CLEAR lessons are universal and don't need domain tags.
4. **Aim for 2-4 tags per lesson.** Fewer than 2 means under-categorized. More than 4 means over-tagged.

---

## Rules for Adding Lessons

1. **One lesson per entry.** Do not combine multiple insights into one record.
2. **Actionable wording.** The `lesson` field must be something a person can act on. Avoid vague observations.
3. **Specific applicability.** The `applicability` field must describe a concrete situation, not "always" or "everywhere."
4. **Check existing tags before creating new ones.** Run `python .claude/scripts/find_lessons.py` to see current tag distribution. Reuse existing tags when they fit. If creating a new tag, add it to the Tag Taxonomy in this document.
5. **Check for duplicates.** Before adding, search existing lessons by tags and keywords. If a similar lesson exists, consider updating it instead.
6. **Update totalLessons.** Keep the top-level count in sync.
7. **Update lastUpdated.** Set to the current date when any lesson is added or modified.

---

## Rules for Archiving/Removing Lessons

1. **Never delete without review.** Lessons should be reviewed before removal to confirm they are truly obsolete.
2. **Superseded lessons.** If a new lesson replaces an old one, note the old ID in the new lesson's `source` field (e.g., "Supersedes L-INIT-20260404-003").
3. **Consolidation.** When multiple lessons cover the same ground, consolidate into a single lesson. Use `L-CONSOLIDATION-{DATE}-{SEQ}` as the origin.
4. **Archive, do not delete.** Move removed lessons to a separate `lessons-archive.json` file rather than deleting them permanently.
5. **Update counts.** After any removal or consolidation, update `totalLessons` and `lastUpdated`.
