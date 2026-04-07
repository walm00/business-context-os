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

## Step 2: Plan the Data Point Architecture

**Don't limit to 3 data points.** Analyze ALL the content and plan however many data points are needed to capture everything properly. Nothing gets lost — only duplications and conflicts get resolved.

### 2a. Content inventory

List every piece of content you found. For each item:
- **Source** — where it came from (file, URL, user input)
- **Topics covered** — what knowledge it contains
- **Overlaps** — does it duplicate or contradict another source?
- **Quality** — is it current, outdated, or a fragment?

### 2b. Plan the data points

Group the content inventory into logical data points. Each data point should:
- Own one clear topic (no overlap with other data points)
- Contain all the knowledge about that topic from all sources
- Consolidate duplicates — pick the best version, merge the rest
- Resolve contradictions — flag them for the user to decide

Present the plan to the user:

```
Based on what I found, here's the data point structure I recommend:

[Cluster Name]
  1. [Data Point Name] — [what it covers] (sources: file1.md, website about page)
  2. [Data Point Name] — [what it covers] (sources: pitch-deck.pdf, user input)

[Cluster Name]
  3. [Data Point Name] — [what it covers] (sources: readme.md, strategy-doc.md)
  ...

Conflicts found:
  - [Topic]: file1.md says X, file2.md says Y — which is current?

Nothing is lost. [N] sources → [M] data points. Want me to proceed or adjust the structure?
```

**Wait for approval before creating files.** The user needs to see the full plan and resolve any conflicts first.

### 2c. Create the data points

After the user approves the plan, create each data point in `docs/`:

```markdown
---
name: "[Data Point Name]"
type: context
cluster: "[Cluster]"
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

[Real content synthesized from sources. Not placeholders.]

## Context

[Why this matters. How to use it. Strategic implications.]
```

**Pre-fill everything.** Draft real content from what you learned. The user edits — they don't write from scratch.

**If drafting from existing repo docs:** do NOT move, rename, or reorganize the original files yet. Create new CLEAR data points alongside them. The user decides when to archive the originals.

---

## Step 3: Verify — Quality Check

Before showing the user, verify the work yourself:

1. **Nothing lost check** — for every source item in your content inventory, confirm it appears in at least one data point. List any gaps.
2. **Ownership check** — every data point has a clear DOMAIN and EXCLUSIVELY_OWNS. No two data points claim the same topic.
3. **Cross-reference check** — STRICTLY_AVOIDS entries point to real data points. Links resolve.
4. **Content quality** — no placeholder text, no empty sections, no "TBD" entries. If you can't fill a section from sources, cut it.
5. **Metadata** — all YAML frontmatter fields present and correct.

Then present the results:

```
Here are [N] data points based on [what you shared / what I found]:

[Cluster Name]
  1. [Name] — [one-line summary]
  2. [Name] — [one-line summary]

[Cluster Name]
  3. [Name] — [one-line summary]
  ...

Coverage check:
  - [X] sources processed → [Y] data points created
  - [Z] conflicts resolved (list if any)
  - No content was dropped

Take a look — anything off, missing, or wrong? I'll adjust whatever needs fixing.
```

After the user approves (with any corrections applied):
- Set status to `active` on approved data points
- Create `docs/_inbox/`, `docs/_planned/`, `docs/_archive/` if they don't exist

---

## Step 4: Archive Originals

**Only after the user approves the new data points.** Never archive before approval.

If there were existing source files in the repo (old docs, scattered markdown, inbox files):

1. Show the user which original files are now fully captured in the new data points
2. Ask: "These originals are now covered by the new data points. Want me to move them to _archive/?"
3. If yes — move each file to `docs/_archive/` with a note in the file explaining what replaced it
4. If no — leave them in place. The user may want to keep them around for now.

**Never delete source files.** Archive only. The originals stay available for reference.

---

## Step 5: Update the Onboarding Checklist

The checklist ships with install at `docs/.onboarding-checklist.md`. After data points are approved:

1. Check off "Initial data points created and approved"
2. Tell the user what's left:

```
Data points are live. Your onboarding checklist (docs/.onboarding-checklist.md)
tracks what's left to set up — I'll remind you once per session until it's done.

Want to keep going or pick it up next time?
```

---

## Step 6: Set Up Scheduled Maintenance

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

- **Capture everything, don't limit arbitrarily.** Create as many data points as the content demands. Better to have proper coverage than to lose information.
- **Draft real content, not placeholders.** If you can't fill a section, cut it — don't leave it empty.
- **Ask focused questions, not questionnaires.** 2-3 max.
- **Keep it conversational.** This is their first experience. Helpful, not bureaucratic.
- **No jargon on first contact.** Say "data point" only after you've shown them one. Before that, say "a doc about your [topic]."
- **Profile detection is silent.** Don't present a "project profile assessment" — just use it to make better cluster and data point choices.
