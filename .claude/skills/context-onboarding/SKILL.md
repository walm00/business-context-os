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
| User shares a URL, pitch deck, or describes their business | Gather from those sources, ask 2-3 follow-ups if needed |
| Repo already has docs/, README, markdown files with business content | Scan the repo, map what exists |
| User drops files in `docs/_inbox/` | Read those files — but STILL ask if there's more before proceeding |
| User has MCP connectors (Google Drive, Notion, etc.) | Ask what to look at — don't fetch everything |
| User just says "help me get started" or "what do I do next?" | Quick-check repo, check for MCP connectors, then ask where their knowledge lives |
| Mix of the above | Combine all available sources |

---

## Step 0: Discover Sources

**Before reading anything, find out where the knowledge lives.**

**ALWAYS use the `AskUserQuestion` tool — even if files already exist in `_inbox/`:**

If files are already in `_inbox/`, acknowledge them first ("I can see X files in your inbox"), then ask:

- Question: "I found [N] files in your inbox. Anything else to include before I start? Website URL, Google Drive docs, other materials?"
- Options:
  - **That's everything** (proceed with what's in the inbox)
  - **Here's more** (I'll share URLs, drop more files, or point you to a connected system)
  - **Check my connected systems too** (Google Drive, Notion, Confluence via MCP)

If NO files in `_inbox/`, ask:

- Question: "Where does your business knowledge live right now?"
- Options:
  - **I have files to share** (drop them in docs/_inbox/ or point me to them)
  - **Connected system** (Google Drive, Notion, Confluence — I can browse via MCP)
  - **Both** (local files + connected systems)
  - **Starting from scratch** (no existing docs — let's create from conversation)

Based on the answer:

| Source type | What to do |
|---|---|
| **Local files** | Ask user to drop them in `docs/_inbox/`, or point to their location |
| **MCP-connected system** (Google Drive, Notion, Confluence) | Ask what folders/docs to look at — browse selectively, don't fetch everything |
| **External system, not connected** | Note it — create an external reference data point later (Step 2) |
| **Starting from scratch** | Skip to Step 1, use website/conversation to gather info |

**For connected external systems:**
- Ask: "What kind of docs should I look for? Company info, processes, brand guidelines?"
- Fetch only what's relevant for business context — NOT bulk collections (invoices, call logs, etc.)
- For large collections (100+ similar files): don't copy — map where they are (see handling modes in Step 2a)

**Non-breaking guarantee:**
- Never modify files outside `docs/` and `.claude/`
- Never rename source files — originals keep their name
- Never delete anything — archive only, after user approval
- Create alongside, not instead of — new data points coexist with originals
- **NEVER create folders not defined in the architecture.** Valid folders are:
  `docs/` (active), `_inbox/`, `_planned/`, `_archive/`, `_collections/`, `_collections/[type]/`
  If content doesn't fit these, ask the user — don't invent new folders

---

## Step 1: Gather Information + Identify Profile

Read everything available from the sources discovered in Step 0. Extract knowledge across all these areas (not all will apply):

**Business identity:**
1. **Who they are** — identity, mission, founding story
2. **What they do** — core offering, product/service
3. **Who they serve** — target audience, customer segments
4. **What makes them different** — positioning, differentiators
5. **What phase they're in** — startup, growth, mature, pivoting

**Operations & processes:**
6. **How they work** — workflows, SOPs, approval chains, team processes
7. **What rules they follow** — brand guidelines, pricing rules, decision frameworks, policies
8. **What they reference** — glossaries, tool inventories, org charts, tech stacks, contact lists

**Strategy & playbooks:**
9. **How they respond** — crisis comms, competitive response, launch playbooks, market entry plans
10. **What they've learned** — past decisions, post-mortems, strategic pivots

**Sources to read** (use whatever's available):
- Website URL → use WebFetch
- LinkedIn company page → use WebFetch
- Pitch deck / one-pager in `docs/_inbox/` → read the file
- Existing repo docs → scan with Glob + Read
- Connected systems (Google Drive, Notion) → browse selectively via MCP tools
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

**Use as many clusters as the content demands.** Don't limit arbitrarily — if the user has content spanning 6 areas, use 6 clusters. Don't present a cluster taxonomy to the user — just use the right cluster names in your drafted data points.

---

## Step 2: Plan the Data Point Architecture

**Don't limit to 3 data points.** Analyze ALL the content and plan however many data points are needed to capture everything properly. Nothing gets lost — only duplications and conflicts get resolved.

### 2a. Content inventory + classification

List every piece of content you found. For each item:
- **Source** — where it came from (file, URL, user input, MCP system)
- **Topics covered** — what knowledge it contains
- **Document type** — classify using the type guide below
- **Handling mode** — how to process it (see handling guide below)
- **Overlaps** — does it duplicate or contradict another source?
- **Quality** — is it current, outdated, or a fragment?

**Type classification guide:**

| If content... | Type | Signal |
|---|---|---|
| Describes what something IS (identity, market, audience, positioning) | **context** | Answers "what is" questions |
| Describes how to DO something (steps, workflows, SOPs, checklists) | **process** | Answers "how to" questions |
| Defines rules, standards, or constraints (brand rules, pricing policy, approval criteria) | **policy** | Answers "must / must not" questions |
| Is lookup/reference data (glossary, org chart, tool list, tech stack, contacts) | **reference** | Answers "what's the..." factual lookups |
| Is a situational response guide (crisis plan, launch playbook, competitive response) | **playbook** | Answers "what do we do when..." questions |

**Handling mode guide:**

| Mode | When to use | What Claude does | Content preserved? |
|---|---|---|---|
| **Synthesize** | Raw info from multiple sources (website, pitch, brain dump, conversation) | Combine into new data points with CLEAR structure | No — Claude writes new content from sources |
| **Wrap** | Existing structured doc (SOP, process doc, policy, brand rules) | Add CLEAR frontmatter + ownership spec around existing content | **Yes — preserve original text exactly** |
| **Catalog** | Reference material (templates, checklists, glossaries, inventories) | Add minimal frontmatter, keep content completely as-is | **Yes — preserve as-is** |
| **Map** | External bulk collections too large to copy (call transcripts, invoices, reports in Drive/Notion) | Create a reference data point describing where and how to find them | N/A — nothing is copied locally |

**CRITICAL for wrap and catalog modes:** Never rewrite, shorten, rephrase, or "improve" the original content. SOPs and processes especially — changing a step could break a real workflow. Add CLEAR structure (frontmatter, ownership spec) AROUND the content but leave the content itself untouched. Flag contradictions or outdated items for the user to decide, but don't fix them yourself.

**Edge cases:**
- Brand guidelines with rules → **policy**, mode: **wrap** (preserve the rules exactly)
- Brand identity describing who we are → **context**, mode: **synthesize** (combine from multiple sources)
- Onboarding doc with steps → **process**, mode: **wrap** (preserve the exact steps)
- Onboarding overview describing the team → **context**, mode: **synthesize**
- Templates that define a standard → **reference**, mode: **catalog** (don't modify at all)
- If one source mixes types → split into separate data points, each with its own mode
- 200 call transcripts in Google Drive → mode: **map** (create external reference, don't copy)
- Bulk local files (reports, invoices) the user wants to keep → route to `docs/_collections/[type]/`, no frontmatter required

### 2b. Plan the data points

Group the content inventory into logical data points. Each data point should:
- Own one clear topic (no overlap with other data points)
- Contain all the knowledge about that topic from all sources
- Consolidate duplicates — pick the best version, merge the rest
- Resolve contradictions — flag them for the user to decide

Present the plan to the user, then **STOP and use the `AskUserQuestion` tool before creating any files.**

Show the plan:

```
Based on what I found, here's the data point structure I recommend:

[Cluster Name]
  1. [Data Point Name] (context, synthesize) — [what it covers] (sources: file1.md, website)
  2. [Data Point Name] (process, wrap) — [what it covers, content preserved as-is] (source: sop-doc.md)

[Cluster Name]
  3. [Data Point Name] (policy, wrap) — [what it covers, content preserved] (source: brand-guidelines.pdf)
  4. [Data Point Name] (reference, catalog) — [what it covers] (source: tech-stack.md)

External references (not copied):
  5. Sales Call Transcripts (reference, map) — ~200 files in Google Drive > Sales > Calls

Conflicts found:
  - [Topic]: file1.md says X, file2.md says Y — which is current?

Nothing is lost. [N] sources → [M] data points + [E] external references.
```

**MANDATORY — use `AskUserQuestion` tool immediately after showing the plan. Do NOT type the options as text:**
- Question: "Does this structure look right?"
- Options: **Proceed** (create the data points) / **Adjust** (tell me what to change)

**Wait for the user's response before creating any files.**

### 2c. Create the data points

After the user approves the plan, create each data point in `docs/`. **The approach depends on the handling mode:**

**For SYNTHESIZE mode** (raw info → new data point):

```markdown
---
name: "[Data Point Name]"
type: "[classified type]"          # context | process | policy | reference | playbook
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

**For WRAP mode** (existing structured doc → add CLEAR structure around it):

Add frontmatter + ownership spec at the top. Keep the original content below **exactly as-is**:

```markdown
---
name: "[Original Doc Title]"
type: process                      # or policy, playbook — whatever fits
cluster: "[Cluster]"
version: "1.0.0"
status: draft
created: "[today]"
last-updated: "[today]"
---

# [Original Doc Title]

## Ownership Specification

**DOMAIN:** [What this document covers]

**EXCLUSIVELY_OWNS:**
- [Items this doc is the authority on]

**STRICTLY_AVOIDS:**
- [Topics that belong elsewhere]

## Content

[ORIGINAL CONTENT PRESERVED EXACTLY AS-IS — do not rewrite, shorten, or rephrase]
```

**For CATALOG mode** (reference material → minimal metadata):

Same as wrap but even lighter — just frontmatter, no ownership spec needed if the content is self-explanatory:

```markdown
---
name: "[Title]"
type: reference
cluster: "[Cluster]"
version: "1.0.0"
status: active
created: "[today]"
last-updated: "[today]"
---

[ORIGINAL CONTENT PRESERVED AS-IS]
```

**For MAP mode** (external collection → reference data point):

Create a reference data point that describes WHERE to find content, not the content itself:

```markdown
---
name: "[Collection Name]"
type: reference
cluster: "[Cluster]"
version: "1.0.0"
status: active
created: "[today]"
last-updated: "[today]"
---

# [Collection Name]

## Ownership Specification

**DOMAIN:** Location and access instructions for [what this collection contains].

**EXCLUSIVELY_OWNS:**
- Access instructions for this external collection
- Summary of what's available and how to search it

## External Source

- **System:** [Google Drive / Notion / Confluence / etc.]
- **Path:** [Folder path or workspace location]
- **Format:** [File types, naming patterns if any]
- **Volume:** [Approximate count, growth rate]
- **Access:** [MCP tool name, or manual export instructions]
- **How to find specific files:** [Search tips — by date, keyword, entity name]

## When to Fetch

- [Scenario 1 when you'd want to pull from this collection]
- [Scenario 2]
- [Scenario 3]
```

**General rules for all modes:**
- **Default to flat in `docs/` root** — use `cluster` frontmatter for grouping, not folders. Example: `docs/brand-identity.md` not `docs/brand-identity/brand-identity.md`. If the user explicitly requests subdirectories for organization, that's fine — but don't create them unprompted
- Do NOT move, rename, or reorganize original source files
- Create new CLEAR data points alongside originals — user decides when to archive
- Pre-fill everything — user edits, they don't write from scratch

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

Coverage: [X] sources → [Y] data points. No content dropped.
```

**MANDATORY — use `AskUserQuestion` tool immediately after showing results. Do NOT type the options as text:**
- Question: "Everything look right? Ready to activate these data points?"
- Options: **Activate** (set all to active, run index + wake-up) / **Adjust** (tell me what to fix)

After the user approves (with any corrections applied):
- Set status to `active` on approved data points
- Create `docs/_inbox/`, `docs/_planned/`, `docs/_archive/` if they don't exist
- Run `python .claude/scripts/build_document_index.py` to generate the Document Index with DOMAIN one-liners
- Run `python .claude/scripts/generate_wakeup_context.py` to generate the Wake-Up Context for instant session orientation

---

## Step 4: Archive Originals

**Only after the user approves the new data points.** Never archive before approval.

If there were existing source files in the repo (old docs, scattered markdown, inbox files):

1. Show the user which original files are now fully captured in the new data points
2. **Use the `AskUserQuestion` tool:**
   - Question: "These originals are now covered by the new data points. What should I do with them?"
   - Options: **Archive them** (move to _archive/ with a note) / **Keep alongside** (leave in place for now)
3. If archive — move each file to `docs/_archive/` with a note explaining what replaced it
4. If keep — leave them in place

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

**After the user is set up, let them know about ongoing tools:**
- **New content in the future:** use `context-ingest` to add, classify, and route new material
- **First quality check:** recommend running `context-audit` to verify the fresh architecture
- **Architecture reference:** the content routing logic is defined in `docs/_bcos-framework/architecture/content-routing.md` (6 routing paths)

---

## Step 6: Set Up Scheduled Maintenance

After data points and the document index are in place, the next checklist item is scheduled maintenance.

1. Read `docs/_bcos-framework/guides/scheduling.md` — it has exact task definitions (ID, cron, prompt) for all 5 tasks
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
