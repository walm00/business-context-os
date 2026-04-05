---
name: context-onboarding
description: |
  First-run discovery skill. Scans an existing repo to discover what business context already exists,
  produces a Table of Context mapping all knowledge sources, and recommends which context data points
  to create first. The starting point for adopting Business Context OS in any project.

  WHEN TO USE:
  - First time setting up BCOS in a project ("scan my repo and show me what context exists")
  - Joining a new project and need to understand what's documented
  - Periodic re-scan to find new undocumented knowledge
---

# Context Onboarding

## Purpose

**This skill IS:**

- The recommended FIRST STEP when adopting Business Context OS
- A discovery tool that scans your repo to find existing business context
- The producer of your **Table of Context** -- a living map of all knowledge sources
- A recommender of which context data points to define first

**This skill IS NOT:**

- Creating data points for you (it maps what exists, you decide what to formalize)
- A one-time tool (re-run it periodically to discover undocumented knowledge)
- Required (you can skip this and follow the manual getting-started guide instead)

---

## When to Use

- "I just added BCOS to my project -- where do I start?"
- "Scan my repo and tell me what business context exists"
- "What documentation do I already have?"
- "Help me understand what's here before I create data points"
- "I joined this project -- give me the lay of the land"

---

## The Onboarding Process

### Phase 1: Scan (5-10 min)

Systematically explore the repo to find existing business context.

**Step 1: Locate documentation**

```
Scan these locations (in order):
1. README.md and root-level markdown files
2. docs/ folder (all levels)
3. CLAUDE.md and .claude/ folder
4. .claude/memory/ (if exists)
5. Any folder containing markdown, text, or documentation files
```

**Step 2: Classify what you find**

For each document or knowledge source discovered, identify:

| Field | What to Record |
|-------|----------------|
| **Location** | File path |
| **Type** | What kind of knowledge (brand, audience, product, process, technical, etc.) |
| **Scope** | What topic does it cover? |
| **Freshness** | Last modified date (from git or file metadata) |
| **Completeness** | Rough assessment: thorough, partial, stub, or outdated |
| **Overlap** | Does this cover the same ground as another file? |

**Step 3: Check for implicit context**

Look for business context that lives in non-obvious places:
- Comments in CLAUDE.md about how the business works
- Memory files (.claude/memory/) with business knowledge
- Configuration files that reveal business decisions
- Git commit messages that reference strategy or positioning
- README sections that describe the product/audience

### Phase 2: Map (5 min)

Organize findings into the **Table of Context**.

**Cluster the discovered knowledge** into natural groups:

| Cluster | Typical Contents |
|---------|-----------------|
| Company & Identity | Mission/values, company story, org structure, investor narrative |
| Audience & Market | Customer profiles, market research, competitive landscape, partner context |
| Product & Value | Product descriptions, value proposition, pricing model, feature context |
| Operations & Process | SOPs, workflows, approval processes, vendor management |
| Strategy & Growth | Business model, goals, OKRs, expansion plans, M&A context |
| Technical | Architecture docs, API docs, setup guides (note but don't formalize) |

**Identify gaps** -- common business context that's missing:
- Is there a clear description of what the company does?
- Are key processes documented (not just in people's heads)?
- Is the company's strategic direction written down?
- Are customer/audience definitions current?
- Is competitive context captured?

### Phase 3: Produce Table of Context (5 min)

Create the Table of Context file at `docs/table-of-context.md`.

Use this structure:

```markdown
# Table of Context

**Generated:** {date}
**Scanned by:** context-onboarding skill
**Status:** Initial scan

---

## Knowledge Sources Found

### [Cluster Name] (e.g., Brand & Identity)

| Source | Location | Type | Freshness | Completeness | Notes |
|--------|----------|------|-----------|--------------|-------|
| Company Overview | README.md | Company identity | 2025-11-15 | Thorough | Good candidate for formalization |
| Sales Process | docs/sales-process.md | Process | 2026-01-20 | Partial | Missing handoff steps |
| Team Context | CLAUDE.md (lines 45-60) | Reference | 2026-02-10 | Fragment | Embedded in instructions |

### [Next Cluster...]

[...repeat for each cluster...]

---

## Coverage Assessment

| Context Area | Status | Sources Found | Recommendation |
|--------------|--------|---------------|----------------|
| Brand Identity | Covered | 2 files | Consolidate into data point |
| Target Audience | Partial | 1 file (outdated) | Update and formalize |
| Value Proposition | Missing | None | Create from scratch |
| Competitive Positioning | Missing | None | Create from scratch |
| Brand Voice | Fragments | Scattered across 3 files | Consolidate into data point |
| Market Context | Partial | 1 file | Review and formalize |

---

## Recommended First Data Points

Based on this scan, here are the recommended first data points to create:

### Priority 1 (Start here)
1. **[Name]** -- [Why: has existing content to consolidate, high team value]
2. **[Name]** -- [Why: critical gap, frequently needed]
3. **[Name]** -- [Why: existing content is scattered/contradictory]

### Priority 2 (Add when Priority 1 is stable)
4. **[Name]** -- [Why]
5. **[Name]** -- [Why]

---

## Overlap & Drift Detected

| Topic | Found In | Issue |
|-------|----------|-------|
| Product description | README.md, pitch-deck.md, about.md | Three different versions |
| Audience definition | personas.md, CLAUDE.md | Contradictory segments |

These overlaps are your highest-value targets for CLEAR ownership.

---

## Next Steps

1. Review this Table of Context with your team
2. Follow `docs/guides/getting-started.md` starting at Step 2
3. Create your first 3 data points from the Priority 1 list above
4. Use the `context-data-point.md` template in `docs/templates/`
5. Re-run this scan periodically to find new undocumented knowledge
```

### Phase 4: Recommend (2 min)

Present findings to the user with:

1. **Summary**: "I found X knowledge sources across Y clusters"
2. **Key gaps**: What's missing that most organizations need
3. **Top 3 recommendations**: Which data points to create first and why
4. **Overlaps**: Where the same info lives in multiple places (context rot already happening)

---

## Prioritization Logic

When recommending which data points to create first, use this priority order:

1. **Contradictory content** -- same topic, different versions in different files (highest value to fix)
2. **Scattered fragments** -- useful content spread across multiple files (consolidation opportunity)
3. **Critical gaps** -- important business context with no documentation at all
4. **Stale content** -- exists but significantly outdated
5. **Already solid** -- good content that just needs CLEAR formalization

---

## Re-running the Scan

The Table of Context is a **living document**. Re-run the scan:

- After major project milestones (launches, rebrands, pivots)
- When new team members join and create new docs
- Monthly, as part of your maintenance rhythm
- Whenever you suspect undocumented knowledge is accumulating

When re-running, compare against the existing Table of Context to highlight:
- New sources discovered since last scan
- Sources that have been updated
- Sources that have gone stale
- New gaps that have appeared

---

## Integration with Other Skills

| Skill | How It Connects |
|-------|----------------|
| **Getting Started guide** | Table of Context feeds directly into Step 2 (Define Your First 3 Data Points) |
| **context-audit** | After data points exist, audit them for CLEAR compliance |
| **daydream** | Use Table of Context as input for strategic reflection |
| **clear-planner** | Use Table of Context to scope documentation work |
| **ecosystem-manager** | Table of Context can reveal need for new skills/agents |

---

## Tips

- **Don't try to formalize everything at once.** The Table of Context is a map, not a to-do list.
- **Start with contradictions.** Where two files disagree is where CLEAR adds the most value.
- **Include the team.** Share the Table of Context -- others will spot knowledge you missed.
- **Technical docs are context too.** Note them in the scan but don't prioritize formalizing them unless they contain business decisions.
- **Git history is your friend.** Check when files were last modified to assess freshness.
