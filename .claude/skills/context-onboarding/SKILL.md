---
name: context-onboarding
description: |
  First-run onboarding skill. Gets a new user from zero to a working context system.
  Claude figures out the right approach based on what the user shares — no paths to choose.
  Creates a checklist that tracks setup progress across sessions and self-removes when done.

  WHEN TO USE:
  - "I want to set up my business context"
  - "Here's my website / pitch deck / LinkedIn"
  - "Scan my repo and show me what context exists"
  - "What do I do next?" (after install)
  - "Help me get started"
  - First time adopting CLEAR Context OS in any project
---

# Context Onboarding

## Goal

**Working context system, user-approved, in under 30 minutes.**

Claude does the drafting. The user reviews and corrects. No questionnaires, no choices to make.

---

## How It Works

Claude figures out the approach from what the user says and what's in the repo. Don't ask the user to "choose a path" — just start.

### Signals → What to do

| What you see | What you do |
|---|---|
| User shares a URL, pitch deck, or describes their business | Gather from those sources, ask 2-3 follow-ups if needed, draft data points |
| Repo already has docs/, README, markdown files with business content | Scan the repo, map what exists, draft data points from existing content |
| User just says "help me get started" or "what do I do next?" | Quick-check the repo. If it has docs with business content, scan. If not, ask: "Tell me about your business — a website URL, a quick description, anything works." |
| User drops files in `docs/_inbox/` | Read those files, treat them as source material, draft data points |
| Mix of the above | Combine everything. Read the URLs AND scan the repo. More signal = better drafts. |

**Don't overthink this.** Read whatever the user gives you, synthesize it, draft data points.

---

## Step 1: Gather Information + Identify Profile

Read everything available. Extract these five things:

1. **Who they are** — identity, mission, founding story
2. **What they do** — core offering, product/service
3. **Who they serve** — target audience, customer segments
4. **What makes them different** — positioning, differentiators
5. **What phase they're in** — startup, growth, mature, pivoting

**Sources to read** (use whatever's available):
- Website URL → use WebFetch
- LinkedIn company page → use WebFetch
- Pitch deck / one-pager in `docs/_inbox/` → read the file
- Existing repo docs → scan with Glob + Read
- What the user tells you directly

**If something is unclear:** ask 2-3 focused follow-up questions. Not a questionnaire — just the gaps that matter most.

**If scanning the repo:** also flag these:
- Same topic in multiple files (contradiction risk)
- Important topics with no docs at all (gaps)
- Content that looks significantly outdated

### Identify the project profile

While gathering info, figure out what kind of project this is. Don't ask directly — infer from what you see:

| Signal | Profile |
|---|---|
| Solo founder, freelancer, side project | **Personal / Small** |
| Team, departments, multiple products | **Company / Large** |
| Code repos, APIs, technical docs | **IT / Development** |
| Campaigns, brand guides, content calendars | **Marketing / Brand** |
| Pipelines, CRM mentions, deal stages | **Sales** |
| Mix of the above | **Combination** (most common) |

**Use the profile to pick sensible cluster names** for the data points you draft. Don't present this as a formal "profile assessment" to the user — just use it to make better choices:

| Profile | Likely clusters |
|---|---|
| Personal / Small | Brand & Identity, Offering, Audience |
| Company / Large | Brand & Identity, Audience & Market, Product & Value, Operations, Strategy |
| IT / Development | Product & Architecture, Users & Market, Team & Process |
| Marketing / Brand | Brand & Identity, Audience & Segments, Messaging & Content |
| Sales | Value Proposition, Target Market, Sales Process |
| Combination | Pick from above based on what matters most right now |

**Start with 2-4 clusters max.** The user can add more later. Don't present a cluster taxonomy — just use the right cluster names in your drafted data points.

---

## Step 2: Draft 3 Data Points

Pick the 3 most important. For most businesses:

1. **Brand Identity / Company Identity** — who they are
2. **Target Audience** — who they serve
3. **Value Proposition / Offering** — what they do and why it wins

If the repo scan revealed contradictions or critical gaps, prioritize those instead:
1. Contradictory content (same topic, different versions) — highest value
2. Critical gaps (important topic, no docs)
3. Scattered fragments (useful content spread across files)

### Data point format

Create each as a file in `docs/`:

```markdown
---
name: "[Data Point Name]"
type: context
cluster: "[Best fit cluster from profile]"
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

[The actual business knowledge, synthesized from sources. Real content, not placeholders.]

## Context

[Why this matters. How to use it. Strategic implications.]
```

**Pre-fill everything.** Draft real content from what you learned. The user edits — they don't write from scratch.

**If drafting from existing repo docs:** do NOT move, rename, or reorganize existing files. Create new CLEAR data points alongside them.

---

## Step 3: Review

Show the user what you drafted:

```
Here are 3 data points based on [what you shared / what I found in the repo]:

1. [Name] — [one-line summary]
2. [Name] — [one-line summary]
3. [Name] — [one-line summary]

Take a look — anything off or missing? I'll adjust whatever needs fixing.
```

After the user approves (with any corrections applied):
- Set status to `active` on approved data points
- Create `docs/_inbox/`, `docs/_planned/`, `docs/_archive/` if they don't exist

---

## Step 4: Update the Onboarding Checklist

The checklist ships with install at `docs/.onboarding-checklist.md`. After data points are approved:

1. Check off "Initial data points created and approved"
2. Tell the user what's left:

```
Data points are live. Your onboarding checklist (docs/.onboarding-checklist.md)
tracks what's left to set up — I'll remind you once per session until it's done.

Want to keep going or pick it up next time?
```

---

## Step 5: Set Up Scheduled Maintenance

After data points and the document index are in place, the next checklist item is scheduled maintenance.

1. Read `docs/guides/scheduling.md` — it has exact task definitions (ID, cron, prompt) for all 5 tasks
2. Create all 5 scheduled tasks using the scheduled tasks tool, copying each task's ID, schedule, description, and prompt exactly as defined
3. Check off "Scheduled maintenance tasks created" in the onboarding checklist
4. Tell the user: "Maintenance schedules are active — daily health checks, weekly reflections, monthly architecture review. You can adjust frequency anytime."

**Don't skip this step.** Users who don't set up scheduled maintenance will hit context rot within weeks.

---

## Checklist: Session-Start Behavior

**This section is for Claude, not the user.**

CLAUDE.md tells Claude to read `docs/.onboarding-checklist.md` at session start. When reading it:

1. Find the first unchecked item
2. Mention it once: "Your onboarding checklist has [item] next. Want to do that now?"
3. If the user says yes, do it. If no, move on.
4. After completing any item, check the box in the file.

**Don't nag.** One mention per session.

### Self-Removal

When ALL items are checked:

1. Delete `docs/.onboarding-checklist.md`
2. Remove the onboarding checklist line from CLAUDE.md (line 1 under "Session Start: Read These First")
3. Tell the user: "Onboarding complete — checklist removed."

---

## Tips

- **Don't try to formalize everything at once.** 3 data points. Add more when these feel stable.
- **Draft real content, not placeholders.** If you can't fill a section, cut it — don't leave it empty.
- **Ask focused questions, not questionnaires.** 2-3 max.
- **Keep it conversational.** This is their first experience. Helpful, not bureaucratic.
- **No jargon on first contact.** Say "data point" only after you've shown them one. Before that, say "a doc about your [topic]."
- **Profile detection is silent.** Don't present a "project profile assessment" — just use it to make better cluster and data point choices.
