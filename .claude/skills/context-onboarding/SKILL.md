---
name: context-onboarding
description: |
  First-run onboarding skill. Two paths: (A) gather info about the user's business from shared
  sources and draft data points, or (B) scan an existing repo to discover what context exists.
  Both paths end with 3 drafted data points for the user to review.

  WHEN TO USE:
  - "I want to set up my business context"
  - "Here's my website / pitch deck / LinkedIn — build my context"
  - "Scan my repo and show me what context exists"
  - First time adopting CLEAR Context OS in any project
---

# Context Onboarding

## Purpose

Help a new user go from zero to **3 working data points in 20-30 minutes**. Claude does the heavy lifting (reading, synthesizing, drafting). The user validates the result.

Two paths to the same outcome:

| Path | When to use | What Claude does |
|------|------------|-----------------|
| **A: Fresh start** | No existing docs, or scattered docs outside the repo | Gathers info from shared sources, asks follow-up questions, drafts data points |
| **B: Existing repo** | Docs already in the repo | Scans the repo, maps what exists, drafts data points from existing content |

---

## Path A: Fresh Start (No Existing Docs)

**Trigger phrases:**
- "I want to set up my business context"
- "Here's my website: [url]"
- "I dropped a pitch deck in _inbox/"
- "Let me tell you about my business"

### Step 1: Gather sources

Ask the user to share any combination of:

```
"Share anything that helps me understand your business:

 - Your website URL
 - LinkedIn company page URL
 - A pitch deck or one-pager (drop in docs/_inbox/)
 - A Google Drive folder (if MCP connector is set up)
 - Or just describe: what you do, who you serve, what phase you're in

The more you share, the better your context will be."
```

### Step 2: Read and synthesize

Read all shared sources. Extract:
- **Who they are** — company/project identity, mission, founding story
- **What they do** — core offering, product/service description
- **Who they serve** — target audience, customer segments
- **What makes them different** — positioning, differentiators, value proposition
- **What phase they're in** — startup, growth, mature, pivoting

If anything is unclear or missing, ask focused follow-up questions (2-3 max, not a questionnaire).

### Step 3: Draft 3 data points

Based on what you learned, draft the 3 most important data points. For most businesses, these are:

1. **Brand Identity / Company Identity** — who they are
2. **Target Audience** — who they serve
3. **Value Proposition** — why customers choose them

For each data point, create a file in `docs/` using the template structure:

```markdown
---
name: "[Data Point Name]"
type: context
cluster: "[Best fit cluster]"
version: "1.0.0"
status: draft
created: "[today]"
last-updated: "[today]"
---

# [Data Point Name]

## Ownership Specification

**DOMAIN:** [One sentence — what this covers]

**EXCLUSIVELY_OWNS:**
- [Item 1]
- [Item 2]
- [Item 3]

**STRICTLY_AVOIDS:**
- [Topic that belongs elsewhere] (see: [other-data-point])

## Content

[The actual business knowledge, synthesized from the sources shared]

## Context

[Strategic implications — why this matters, how to use it]
```

**Pre-fill everything you can** from the sources. Don't leave empty sections for the user to fill — draft real content. The user edits, not writes from scratch.

### Step 4: Present for review

Show the user all 3 data points and ask them to review:

```
"I've drafted 3 data points based on what you shared:

1. [Name] — [one-line DOMAIN summary]
2. [Name] — [one-line DOMAIN summary]
3. [Name] — [one-line DOMAIN summary]

Please review each one:
- Is the DOMAIN accurate?
- Is EXCLUSIVELY_OWNS complete?
- Is the content correct?

I'll adjust anything that's off."
```

---

## Path B: Existing Repo (Has Docs)

**Trigger phrases:**
- "Scan my repo and show me what context exists"
- "What documentation do I already have?"
- "I joined this project — give me the lay of the land"

### Step 1: Scan

Locate all documentation in the repo:

```
1. README.md and root-level markdown files
2. docs/ folder (all levels)
3. CLAUDE.md and .claude/ folder
4. Any folder containing markdown, text, or documentation files
```

For repos with 20+ documents, delegate scanning to explore agents:
```
Agent (Explore): "Scan docs/ for all .md files. For each: path, first 5 content lines, any YAML frontmatter."
```

For small repos (< 20 files), scan directly.

### Step 2: Map what you found

For each document, identify: what topic it covers, how fresh it is, how complete it is.

Group findings into natural clusters (Brand & Identity, Audience & Market, Product & Value, Operations, Strategy, etc.).

**Key things to flag:**
- Same topic covered in multiple files (contradiction risk)
- Important topics with no documentation at all
- Content that's significantly outdated

### Step 3: Show the user what you found

Present a clear summary:

```
"I found [X] documents covering these topics:

[Topic 1] — found in [file], [freshness assessment]
[Topic 2] — found in [file1] and [file2] (overlap — same topic, two places)
[Topic 3] — no documentation found (gap)
...

Based on this, I recommend formalizing these 3 as CLEAR data points first:
1. [Name] — because [reason: contradiction, critical gap, or scattered across files]
2. [Name] — because [reason]
3. [Name] — because [reason]

Want me to draft them?"
```

### Step 4: Draft 3 data points

Same as Path A Step 3, but pull content from the existing docs instead of external sources.

**Critical rule: do NOT reorganize or move existing files.** Create new CLEAR data points alongside what already exists. The user's files stay where they are.

### Step 5: Present for review

Same as Path A Step 4.

---

## After Both Paths

Once the user has reviewed and approved their 3 data points:

1. **Set status to active** on the approved data points
2. **Create folder structure** if it doesn't exist:
   ```bash
   mkdir -p docs/_inbox docs/_planned docs/_archive
   ```
3. **Offer next steps** (don't push — offer):
   - "Want me to run a quick audit on these 3 data points?"
   - "You have files in _inbox/ — want me to process them?"
   - "Your context is set up. The getting-started guide recommends a 5-minute weekly check-in to keep things current."

---

## Prioritization Logic

When recommending which 3 data points to create first:

1. **Contradictory content** — same topic, different versions in different files (highest value to fix)
2. **Critical gaps** — important business context with no documentation at all
3. **Scattered fragments** — useful content spread across multiple files
4. **Already solid** — good content that just needs CLEAR formalization
5. **Stale content** — exists but significantly outdated

---

## Tips

- **Don't try to formalize everything at once.** Start with 3. Add more when these feel stable.
- **Draft real content, not placeholders.** The user should review filled-in data points, not empty templates.
- **Ask focused questions, not questionnaires.** 2-3 follow-up questions max. Don't interrogate.
- **For Path B: map, don't move.** The user's existing file structure stays intact.
- **Keep it conversational.** This is the user's first experience with the system. Make it feel helpful, not bureaucratic.
