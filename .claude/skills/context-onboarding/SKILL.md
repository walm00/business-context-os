---
name: context-onboarding
description: |
  First-run discovery skill. Scans an existing repo to discover what business context already exists,
  produces a Document Index mapping all knowledge sources, and recommends which context data points
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
- The producer of your **Document Index** -- a living map of all knowledge sources
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

### Phase 0: Run the Discovery Script

Start with the automated scan:

```bash
python .claude/scripts/build_document_index.py
```

This generates `docs/document-index.md` with:
- All documents that have YAML frontmatter (grouped by cluster, with metadata health)
- All unmanaged documents (markdown files without frontmatter — candidates for formalization)

Review the output, then continue with the manual scan below to catch what the script misses (knowledge in non-markdown files, config files, git history, etc.).

### Phase 1: Deep Scan (5-10 min)

Go beyond what the script found. Explore the repo for business context in non-obvious places.

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
| **Temporal State** | Is this current reality (`active`), future plans (`planned`), or raw material (`draft`)? |
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

Organize findings into the **Document Index**.

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

### Phase 3: Produce Document Index (5 min)

Create the Document Index file at `docs/document-index.md`.

Use this structure:

```markdown
# Document Index

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

1. Review this Document Index with your team
2. Follow `docs/guides/getting-started.md` starting at Step 2
3. Create your first 3 data points from the Priority 1 list above
4. Use the `context-data-point.md` template in `docs/templates/`
5. Re-run this scan periodically to find new undocumented knowledge
```

### Phase 4: Draft the Table of Context (5 min)

Based on everything discovered, create an initial `docs/table-of-context.md` using the template at `docs/templates/table-of-context.md`.

Synthesize from the scan:
- **Who We Are** — piece together the company/project identity from README, about pages, existing docs
- **What We Do** — extract the core offering from product docs, descriptions
- **Who We Serve** — find audience definitions wherever they exist
- **What Makes Us Different** — look for positioning, competitive, or differentiator content
- **Current Phase** — infer from doc recency, project maturity, recent commits

Mark anything uncertain with "[TO VERIFY]". This is a draft — the user refines it.

Also ask the user if they want to create `docs/current-state.md` now (using the template). If yes, have a brief conversation about their role, this week's priorities, and what's changing.

**Set up the directory structure:**

Create these directories if they don't exist:
```bash
mkdir -p docs/_inbox docs/_archive
```

- `docs/_inbox/` — Landing zone for raw material (meeting notes, brain dumps, pasted content). No quality bar. `context-ingest` processes these into proper data points.
- `docs/_archive/` — Superseded documents. Kept for reference, not active context. Never delete — archive instead.

### Phase 5: Recommend (2 min)

Present findings to the user with:

1. **Summary**: "I found X knowledge sources across Y clusters"
2. **Key gaps**: What's missing that most organizations need
3. **Top 3 recommendations**: Which data points to create first and why
4. **Overlaps**: Where the same info lives in multiple places (context rot already happening)
5. **Table of Context**: "I created an initial draft — please review and correct"
6. **Planned vs. Active**: Call out which discovered content represents current reality vs. future intent. Recommend appropriate status for each.

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

The Document Index is a **living document**. Re-run the scan:

- After major project milestones (launches, rebrands, pivots)
- When new team members join and create new docs
- Monthly, as part of your maintenance rhythm
- Whenever you suspect undocumented knowledge is accumulating

When re-running, compare against the existing Document Index to highlight:
- New sources discovered since last scan
- Sources that have been updated
- Sources that have gone stale
- New gaps that have appeared

---

## Integration with Other Skills

| Skill | How It Connects |
|-------|----------------|
| **Getting Started guide** | Document Index feeds directly into Step 2 (Define Your First 3 Data Points) |
| **context-audit** | After data points exist, audit them for CLEAR compliance |
| **daydream** | Use Document Index as input for strategic reflection |
| **clear-planner** | Use Document Index to scope documentation work |
| **ecosystem-manager** | Document Index can reveal need for new skills/agents |

---

## Phase 5: Set Up Your Maintenance Rhythm

After the initial scan and first data points are created, recommend a schedule.

**Ask the user:** "How would you describe your situation?"

| If they say... | Recommend |
|----------------|-----------|
| "Just getting started" / "New project" / "Few docs" | **Building rhythm:** daily Document Index rebuild, weekly health check |
| "We have some docs, adding more regularly" | **Active rhythm:** weekly health check + ToC rebuild, bi-weekly daydream, monthly deep audit |
| "Mature docs, not much changes" | **Steady rhythm:** bi-weekly health check, monthly daydream, quarterly review |
| "It's a mess, need to consolidate" | **Migration rhythm:** daily ToC rebuild, health check every 2-3 days |

Point them to `docs/guides/scheduling.md` for the full prompts and cron expressions.

**Minimum recommended:** Set up at least the weekly health check + Document Index rebuild before ending the onboarding session. One scheduled task is better than zero.

---

## Tips

- **Don't try to formalize everything at once.** The Document Index is a map, not a to-do list.
- **Start with contradictions.** Where two files disagree is where CLEAR adds the most value.
- **Include the team.** Share the Document Index -- others will spot knowledge you missed.
- **Technical docs are context too.** Note them in the scan but don't prioritize formalizing them unless they contain business decisions.
- **Git history is your friend.** Check when files were last modified to assess freshness.
