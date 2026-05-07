---
name: context-onboarding
description: |
  First-run onboarding skill. Gets a new user from zero to a working context system.
  Claude asks one direct question upfront to pick the right scaffolding, then works from what the user shares — no long assessment ceremony beyond that.
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

Claude asks ONE direct question upfront — "what kind of project is this?" — and uses the answer to pick the right template + pattern doc. After that, Claude figures out the rest from what the user says and what's in the repo. No long path-chooser; just one gate that routes scaffolding correctly.

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

## Step 0: Identify Project Type + Discover Sources

Two short `AskUserQuestion` gates, in order: what kind of project this is (0a), then where the knowledge lives (0b). Pre-fill both from what you can see before asking — the user confirms or overrides.

### 0a. Project type

**Before anything else, ask what kind of project this is.** The answer picks the template + pattern doc Claude uses for the rest of onboarding. This is the one question that isn't inferred silently — one direct question is the ceremony.

**Pre-fill suggestion first:** glance at any URLs the user shared, files they dropped, README contents, repo structure (frontend code? Dockerfile + cron? marketing copy? client names? spec docs + ADRs? runbooks and on-call docs? pricing / enablement / battlecards?). Use that to pick the most likely answer as the suggested option, but still ask.

Two levels, only ask the follow-up when needed.

**Level 1 — always ask. Use the `AskUserQuestion` tool:**

- Question: "What's this repo primarily about? (This picks the scaffolding — you can change it later.)"
- Options:
  - **Product** (external product, service, or company context)
  - **Product development** (R&D, specs, architecture, engineering roadmap)
  - **Internal tool** (dashboards, scripts, internal apps, developer tools)
  - **Marketing** (marketing site, campaigns, content strategy)
  - **GTM / sales** (pricing, positioning, sales enablement, partnerships)
  - **Operations** (ops runbooks, processes, infrastructure docs)
  - **Client work** (agency engagement scoped to one client)
  - **Team playbook / personal** (team practices, ops runbook, personal projects)

**Level 2 — only when the Level 1 answer is ambiguous.** Skip if repo signals already disambiguate.

- If the user picked **"Product"** (and the repo doesn't obviously lean one way — e.g. marketing site + pricing page → external product; spec docs + ADRs + architecture → R&D), ask:
  - Question: "External-facing product/service, or product development (R&D)?"
  - Options:
    - **External product / service** (the product as sold — brand, positioning, customers)
    - **Product development** (how the product is built — specs, architecture, roadmap)
- If the user picked **"Internal tool"** (and the repo doesn't make the sub-shape obvious — e.g. a React frontend → app; cron config + Dockerfile with no UI → automation), ask:
  - Question: "Is it more of an app or an automation?"
  - Options:
    - **App with UI + internal users** (web dashboard, internal admin tool, back-office app)
    - **Automation / CLI / pipeline / service** (no UI — scripts, ETL, cron jobs, backend services)

Claude should silently pre-fill the Level 1 option based on inference, and skip Level 2 entirely when pre-fill confidence is high on the sub-shape. Carry the resolved profile through to Step 1 (profile → template + pattern mapping) and Step 2 (cluster naming).

### 0b. Source discovery

**Now find out where the knowledge lives.**

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

**First-run routing principle:** onboarding is allowed to identify all BCOS
zones, but it should only create active data points after the user approves the
architecture. Route material by what it *is*, not by file type alone:

| Material | First-run handling |
|---|---|
| Canonical facts, current decisions, project/task/business reality | Draft active data points in `docs/*.md` |
| Raw notes, unsorted snippets, uncertain material | Keep in `docs/_inbox/` until triaged |
| Future ideas, plans, or maybes | Park in `docs/_planned/` |
| Verbatim evidence artifacts: invoices, contracts, transcripts, exports, brand kits, reports as received | Route to `docs/_collections/<type>/` with manifest discipline, or map externally if too large |
| Explanatory material: how-tos, glossaries, runbooks, post-mortems, decision narratives, source summaries | Route through `bcos-wiki`: `/wiki create`, `/wiki promote`, or `/wiki queue add` |

**For connected external systems:**
- Ask what kind of docs to look for — adapt the prompt to the project type from Step 0a:
  - **External product / service:** "Company info, processes, brand guidelines?"
  - **Product development:** "PRDs, RFCs / ADRs, architecture diagrams, spec docs?"
  - **Internal tool:** "Architecture docs, runbooks, ADRs, ops guides?"
  - **Marketing:** "Campaign briefs, content calendars, editorial guidelines, performance reports?"
  - **GTM / sales:** "Sales plays, battlecards, pricing docs, enablement materials, partner agreements?"
  - **Operations:** "Runbooks, on-call playbooks, incident post-mortems, SLI / SLO docs?"
  - **Client work:** "Client briefs, SOWs, design files, meeting notes?"
  - **Team playbook / personal:** "SOPs, team docs, notes, references?"
- Fetch only what's relevant for context — NOT bulk collections (invoices, call logs, etc.)
- For large collections (100+ similar files): don't copy — map where they are (see handling modes in Step 2a)

**Non-breaking guarantee:**
- Never modify files outside `docs/` and `.claude/`
- Never rename source files — originals keep their name
- Never delete anything — archive only, after user approval
- Create alongside, not instead of — new data points coexist with originals
- **NEVER create folders not defined in the architecture.** Valid folders are:
  `docs/` (active), `_inbox/`, `_planned/`, `_archive/`, `_collections/`, `_collections/[type]/`, `_wiki/`
  If content doesn't fit these, ask the user — don't invent new folders

---

## Step 1: Gather Information + Identify Profile

Read everything available from the sources discovered in Step 0. The knowledge categories you extract depend on the project type from Step 0a:

**The knowledge categories to extract come from the resolved profile's pattern doc in `docs/_bcos-framework/patterns/`.** Open the matching pattern doc, read its "Data Point Map" section, and use those clusters as the extraction targets. A short per-profile pointer:

- **External product / service** → see `docs/_bcos-framework/patterns/product-service-pattern.md`. The generic "business identity → operations → strategy" shape below also works as a fallback.
- **Product development** → see `docs/_bcos-framework/patterns/product-development-pattern.md`. Categories lean toward product scope, architecture, features & specs, technical decisions, team & roadmap.
- **Internal tool → app** → see `docs/_bcos-framework/patterns/internal-tool-app-pattern.md` and `table-of-context.internal-tool.md`. Categories: what the tool is, what it does, who uses it, how it works, upstream/downstream, operational model, current state.
- **Internal tool → automation** → see `docs/_bcos-framework/patterns/internal-tool-automation-pattern.md`. Shared template with app — different cluster emphasis (pipeline identity, behavior & ownership, architecture & operations).
- **Marketing** → see `docs/_bcos-framework/patterns/marketing-pattern.md`. Brand adjacency, campaigns & content, channels & performance, editorial voice.
- **GTM / sales** → see `docs/_bcos-framework/patterns/gtm-pattern.md`. Target ICP, positioning & messaging, pricing & packaging, sales motion & enablement, partner & channel.
- **Operations** → see `docs/_bcos-framework/patterns/operational-pattern.md`. System map, runbooks & procedures, on-call & escalation, SLIs & incidents, change management.
- **Client work** → see `docs/_bcos-framework/patterns/client-project-pattern.md` and `table-of-context.client-project.md`. Engagement context, scope & delivery, architecture & handoff.
- **Team playbook / personal** → no dedicated pattern doc yet. Use the generic shape below and pick cluster names from what the content actually is.

**Generic fallback categories** — use these when the profile is "Team playbook / personal" or when a pattern-doc-specific map doesn't yet exist:

**Business identity:** (product/service only — skip for internal-tool, client-project, operational, gtm, marketing, product-development)
1. **Who they are** — identity, mission, founding story
2. **What they do** — core offering, product/service
3. **Who they serve** — target audience, customer segments
4. **What makes them different** — positioning, differentiators
5. **What phase they're in** — startup, growth, mature, pivoting

**Operations & processes:** (applies across most project types)
6. **How they work** — workflows, SOPs, approval chains, team processes
7. **What rules they follow** — brand guidelines, pricing rules, decision frameworks, policies
8. **What they reference** — glossaries, tool inventories, org charts, tech stacks, contact lists

**Strategy & playbooks:** (product/service and playbook profiles)
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

### Profile → template + pattern mapping

The Step 0a answer already decided the profile. This table maps each resolved answer to the template variant and pattern doc Claude uses for drafting. Pattern docs live in `docs/_bcos-framework/patterns/` and describe the data-point map, relationships, and voice for each profile — read the matching pattern doc before drafting.

| Resolved profile (from Step 0a) | Template | Pattern doc | Notes |
|---|---|---|---|
| **External product / service** | `docs/_bcos-framework/templates/table-of-context.md` + `current-state.md` | `docs/_bcos-framework/patterns/product-service-pattern.md` | Default. Brand + business identity + GTM overview. |
| **Product development** | `table-of-context.md` + `current-state.md` (fallback) | `docs/_bcos-framework/patterns/product-development-pattern.md` | **TODO: dedicated template variant not yet built.** Pattern doc notes this — reuse product/service scaffolding and lean on the pattern's cluster map. |
| **Internal tool → app** | `docs/_bcos-framework/templates/table-of-context.internal-tool.md` + `current-state.internal-tool.md` | `docs/_bcos-framework/patterns/internal-tool-app-pattern.md` | App shape: UI + internal users + persistence. |
| **Internal tool → automation** | `docs/_bcos-framework/templates/table-of-context.internal-tool.md` + `current-state.internal-tool.md` | `docs/_bcos-framework/patterns/internal-tool-automation-pattern.md` | No UI: scripts, CLIs, pipelines, services. Shared template, different cluster emphasis. |
| **Marketing** | `table-of-context.md` + `current-state.md` (fallback) | `docs/_bcos-framework/patterns/marketing-pattern.md` | **TODO: dedicated template variant not yet built.** Pattern doc notes this — reuse product/service scaffolding. Expect brand inheritance from a sibling product-service repo. |
| **GTM / sales** | `table-of-context.md` + `current-state.md` (fallback) | `docs/_bcos-framework/patterns/gtm-pattern.md` | **TODO: dedicated template variant not yet built.** Pattern doc notes this — reuse product/service scaffolding. Expect positioning inheritance from a sibling product-service repo. |
| **Operations** | `table-of-context.internal-tool.md` + `current-state.internal-tool.md` (fallback) | `docs/_bcos-framework/patterns/operational-pattern.md` | **TODO: dedicated template variant not yet built.** Pattern doc notes this — reuse internal-tool templates and treat scope as the team's operational layer across many systems. |
| **Client work** | `docs/_bcos-framework/templates/table-of-context.client-project.md` + `current-state.client-project.md` | `docs/_bcos-framework/patterns/client-project-pattern.md` | External deliverable scoped to one client. One client, one engagement. |
| **Team playbook / personal** | `table-of-context.md` + `current-state.md` (fallback) | No dedicated pattern yet (fallback: `product-service-pattern.md` for shape only) | **TODO: dedicated pattern + template not yet built.** Reuse product/service scaffolding, lean heavily on the content the user shares, adapt clusters to what the content actually is. |

**Pick sensible cluster names** based on the profile — don't present a formal "profile assessment" to the user, just use the right cluster names in your drafted data points. Cluster hints (these mirror the "Data Point Map" in each pattern doc):

| Resolved profile | Likely clusters |
|---|---|
| External product / service | Business Identity, Offerings & Positioning, Market & Customers, Brand & Voice, GTM Overview |
| Product development | Product Scope & Vision, Architecture, Features & Specs, Technical Decisions, Team & Roadmap |
| Internal tool → app | Tool Identity, Users & Capabilities, Architecture & Operations |
| Internal tool → automation | Pipeline Identity, Behavior & Ownership, Architecture & Operations |
| Marketing | Brand Adjacency, Campaigns & Content, Channels & Performance, Editorial Voice |
| GTM / sales | Target ICP, Positioning & Messaging, Pricing & Packaging, Sales Motion & Enablement, Partner & Channel |
| Operations | System Map, Runbooks & Procedures, On-Call & Escalation, SLIs & Incidents, Change Management |
| Client work | Engagement Context, Scope & Delivery, Architecture & Handoff |
| Team playbook / personal | Pick 2-4 clusters from the content the user shares (TODO: refine when variant is built) |

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
| **Wiki** | Explainers, how-tos, source summaries, decision narratives, post-mortems, or material the user asks to make into a wiki page | Route through `bcos-wiki` (`/wiki create`, `/wiki promote`, `/wiki queue add`) so schema, index, queue, and log stay aligned | Yes for source captures; page body is derivative explanation |

**Stable-vs-volatile rule (applies to synthesize and wrap modes):** A data point is for *durable* truth. When deciding what to bake into a synthesized data point:

- **Extract:** stable concepts (mission, positioning, audience definition, pricing model, decision frameworks, methodology, glossary), critical rules (brand guidelines, policies), and historical facts that won't change (founding date, signed agreements, past pivots).
- **Don't extract — reference instead:** volatile numbers (current MRR, headcount, this-quarter KPIs), time-series data (monthly metrics, invoice ledgers), and operational state with its own system of record (CRM pipeline, accounting books). For these, create a `reference` data point in **map** mode pointing at the source, or note where the live number lives — don't copy a snapshot that will rot.

**Rule of thumb:** if a fact will be wrong within 90 days, point at the source. If it reflects a decision or definition, extract it. A good data point should still read as true a year from now even when every number in the business has moved.

**CRITICAL for wrap and catalog modes:** Never rewrite, shorten, rephrase, or "improve" the original content. SOPs and processes especially — changing a step could break a real workflow. Add CLEAR structure (frontmatter, ownership spec) AROUND the content but leave the content itself untouched. Flag contradictions or outdated items for the user to decide, but don't fix them yourself.

**Wiki mode boundary:** Do not use wiki pages as canonical reality. Wiki pages
explain, summarize, narrate, or teach; they cite data points through
`builds-on:`. Path B binaries captured for wiki stay under
`docs/_wiki/raw/local/`. Do not write them to `_collections/` unless the user
explicitly asks for a collection/evidence operation.

**Edge cases:**
- Brand guidelines with rules → **policy**, mode: **wrap** (preserve the rules exactly)
- Brand identity describing who we are → **context**, mode: **synthesize** (combine from multiple sources)
- Onboarding doc with steps → **process**, mode: **wrap** (preserve the exact steps)
- Onboarding overview describing the team → **context**, mode: **synthesize**
- Templates that define a standard → **reference**, mode: **catalog** (don't modify at all)
- If one source mixes types → split into separate data points, each with its own mode
- 200 call transcripts in Google Drive → mode: **map** (create external reference, don't copy)
- Bulk local files (reports, invoices) the user wants to keep → route to `docs/_collections/[type]/`, no frontmatter required
- "Make this a wiki page" / "turn this into an explainer" / URL to summarize later → mode: **wiki** (`/wiki create`, `/wiki promote`, or `/wiki queue add`)

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
- Add useful `tags` in frontmatter for every managed data point/wiki page. Tags are warning-only during adoption, but they power search, dashboard filters, Galaxy, and mechanical retrieval.
- Use `last-updated` only when content/metadata changes. Use `last-reviewed` when a doc is checked and confirmed without changing content, especially when `review-cycle` is present. Folder-derived facets such as `zone`, `folder`, and `path-tags` are generated by `.claude/scripts/context_index.py`; do not duplicate them in YAML.

---

## Step 3: Verify — Quality Check

Before showing the user, verify the work yourself:

1. **Nothing lost check** — for every source item in your content inventory, confirm it appears in at least one data point. List any gaps.
2. **Ownership check** — every data point has a clear DOMAIN and EXCLUSIVELY_OWNS. No two data points claim the same topic.
3. **Cross-reference check** — STRICTLY_AVOIDS entries point to real data points. Links resolve.
4. **Content quality** — no placeholder text, no empty sections, no "TBD" entries. If you can't fill a section from sources, cut it.
5. **Metadata** — all required YAML frontmatter fields present and correct; tags present where possible; `last-reviewed` used when review happened without content mutation.

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

After data points and the document index are in place, the next checklist item is scheduled maintenance. In v1.2 this is ONE task per repo — the `bcos-{project}` dispatcher. It runs daily, reads `.claude/quality/schedule-config.json`, and decides which maintenance jobs are due today.

**Before creating anything, resolve two variables:**

1. **`{REPO_PATH}`** — the absolute path to this repo's root directory (the current working directory)
2. **`{PROJECT}`** — a short slug derived from the repo folder name. Lowercase, hyphens only, no spaces. Examples: `leverage`, `tystiq`, `acme-corp`.

### 6a. Seed the config file

Copy `.claude/quality/schedule-config.template.json` → `.claude/quality/schedule-config.json`. Keep all the `_comment` and `_about` fields — users will read them.

If the file already exists, don't overwrite. Skip to 6b.

### 6b. Ensure the diary directory exists

The diary lives at `.claude/hook_state/schedule-diary.jsonl` (gitignored). Ensure the `.claude/hook_state/` directory exists (it usually does from install.sh — check and create if missing). Don't create the JSONL file itself; the dispatcher will create it on first run.

### 6b-pre. Permissions preflight (CRITICAL — prevents stuck dispatcher runs)

Scheduled dispatcher runs spawn fresh Claude Code sessions with no human watching. Every permission prompt that fires in those sessions becomes a stuck task — Laura's experience: "almost none of the scheduled tasks did fire, just one and it stuck." This step prevents that.

**Read `.claude/settings.json` and verify these markers exist** (the install.sh ships them; this verification is for repos that installed before v1.5 or had a custom settings.json):

Required entries (from the comprehensive shipped allowlist):

- `Bash(python .claude/scripts/:*)` — catch-all for every dispatcher script
- `Bash(python3 .claude/scripts/:*)` — same, for python3 alias
- `Bash(git status --porcelain)` and `Bash(git commit -m bcos:*)` — auto-commit step
- `Edit(.claude/quality/**)` and `Write(.claude/quality/**)` — derived state files
- `Edit(docs/_wiki/index.md)` — wiki refresh
- `Edit(docs/_archive/**)` — archive moves from headless actions
- `Skill(bcos-wiki:*)`, `Skill(context-ingest:*)`, `Skill(schedule-tune:*)` — sibling skills the dispatcher delegates to

If the local `.claude/settings.json` is missing any of the above, **stop and run `python .claude/scripts/update.py`** before continuing — the update script's `merge_settings_json` will additively add every missing entry from the shipped settings.json without touching user customizations. Then re-read settings.json to confirm.

If the user has a non-default `.claude/settings.local.json` that REJECTS any of these (via a `deny` rule or stale allowlist), surface the conflict and ask the user to resolve before proceeding — do not silently work around it.

The full SoT of required entries lives in `docs/_bcos-framework/architecture/permissions-catalog.md`. If anything in that catalog is missing from settings.json, the dispatcher will hit a permission prompt sooner or later.

### 6b-cross. Cross-repo workflow check

**Ask whether scheduled workflows will span multiple repos** (umbrella + sub-repos, portfolio mode, sibling-repo writes). If yes, recommend mirroring the project allowlist to user-level settings so cross-repo writes don't prompt:

Use `AskUserQuestion`:

- Question: "Will scheduled workflows touch other repos on this machine (umbrella → sub-repos, sibling repos, portfolio mode)?"
- Options:
  - **No, single repo only** — project-level perms are enough; skip mirroring
  - **Yes, multi-repo** — mirror the allowlist to `~/.claude/settings.json` so cross-repo runs don't stall
  - **Not sure** — explain trade-offs and let the user decide

If the answer is "Yes, multi-repo" (or the user confirms after explanation), run:

```bash
python .claude/scripts/install_global_permissions.py
```

Confirm output shows entries merged. The script is idempotent and additive — it never removes or reorders existing user-level rules. Trust-model notes live in `docs/_bcos-framework/architecture/permissions-catalog.md` under "Cross-repo workflows".

### 6b-mcp. MCP scheduled-tasks permission (one-time prompt — encourage "Always allow")

The next step (6d) calls `mcp__scheduled-tasks__create_scheduled_task` to create the OS-level cron task. On first invocation, Claude Code will prompt the user to approve the MCP tool. **Tell the user this is coming, and that "Always allow" is the right choice:**

> I'm about to create the daily dispatcher task. Claude Code will prompt you to allow the `mcp__scheduled-tasks__create_scheduled_task` tool — pick **"Always allow"** so future scheduled runs don't get stuck on permission prompts. (You can revoke it later in `~/.claude/settings.json` if needed.)

This is the only MCP permission BCOS needs the user to grant interactively. Everything else is shipped in the project-level allowlist.

### 6c. Ask about the dispatcher time

Default is 09:00 local. Use `AskUserQuestion`:

- Question: "When should the morning dispatcher run?"
- Options:
  - **09:00 (default)** — runs at 9am local
  - **Earlier (7:00-8:30)** — pick a specific time
  - **Later (10:00-12:00)** — pick a specific time

If user picks "earlier" or "later", follow up with a specific-time question. Resolve to a concrete `HH:MM`.

### 6d. Create the single dispatcher task

Use `mcp__scheduled-tasks__create_scheduled_task` with:

- `taskId`: `bcos-{project}` (e.g. `bcos-leverage`)
- `cronExpression`: derive from the user's chosen time. `09:00` → `"0 9 * * *"`, `08:30` → `"30 8 * * *"`.
- `description`: `BCOS daily maintenance dispatcher for {project}`
- `prompt` (literal, with `{REPO_PATH}` substituted):

```
Working directory: {REPO_PATH}

IMPORTANT: First ensure the working directory is {REPO_PATH}. If the session is running elsewhere, cd there before starting.

Run the schedule-dispatcher skill to execute today's scheduled CLEAR maintenance. It will:
1. Read .claude/quality/schedule-config.json
2. Determine which jobs are scheduled for today based on day-of-week / day-of-month
3. Execute each job in sequence, appending one diary entry per job
4. Write a consolidated digest to docs/_inbox/daily-digest.md
5. Report a one-line summary

Keep output focused. If everything is green with no action items, say so in one line.
```

### 6e. Verify the task actually exists

Before declaring success, confirm the OS-level task was created. Use `mcp__scheduled-tasks__list_scheduled_tasks` and check that `bcos-{project}` appears with the correct cron expression. If it's missing, surface the error and stop — don't claim success on a half-failed setup.

### 6f. Offer cadence tuning (optional)

The template ships with every job set to `daily`. That's intentional — fresh setups should over-monitor for the first 1-2 weeks until the auto-tuner suggests reductions after green-run streaks. But power users sometimes want to tune up front.

Use `AskUserQuestion`:

- Question: "Default is daily for everything (recommended). Want to adjust any cadences now?"
- Options:
  - **Keep defaults** — runs daily for now; auto-tuner will suggest reductions after ~5 green runs
  - **Adjust now** — invoke the `schedule-tune` skill so the user can describe changes in plain English

If user picks "Adjust now", invoke `schedule-tune`. If "Keep defaults", continue.

### 6g. Confirm and close out

Check off "Dispatcher task created" in the onboarding checklist. Tell the user:

> Maintenance is live. One task, `bcos-{project}`, runs every morning at {time}. It produces `docs/_inbox/daily-digest.md` and a one-line summary. You can change frequencies anytime by telling me things like "run audit twice a week" or "turn off deep daydream" — I'll handle the config edit via the `schedule-tune` skill.
>
> Want to test it now with "run today's maintenance now"?

Don't auto-run. Let the user invoke the first run on their terms.

### Why this shape

Scheduled tasks live in `~/.claude/scheduled-tasks/` — user-global, not per-repo. One task per repo keeps the user-global task list short and unambiguous, and eliminates the time-collision problem that 5 separate per-repo tasks used to cause.

**Don't skip this step.** Users who don't set up the dispatcher will hit context rot within weeks. The default config is aggressive (daily index-health, weekly everything else) — the dispatcher will suggest reductions once it sees green runs stacking up.

**Never mention migration during onboarding.** Migration is a separate path triggered only when `update.py` finds pre-existing v1.x tasks. A fresh install has nothing to migrate and should never see the word.

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

- **Capture everything, don't limit arbitrarily.** Create as many data points as the content demands. Better to have proper coverage than to lose information. A complex business with a deep doc pile may legitimately need 15-25+ data points across all main domains — that's the right answer, not a problem to minimize.
- **Cover all main domains before refining any one of them.** A complete-but-rough architecture beats a polished-but-partial one. Gaps stay invisible until something breaks; rough boundaries can be sharpened later.
- **Stable in, volatile out.** Bake stable concepts and historical facts into data points. For numbers that change often (revenue, headcount, KPIs, pipeline, books), use map mode and point at the source — don't snapshot a number that will be wrong next month.
- **Draft real content, not placeholders.** If you can't fill a section, cut it — don't leave it empty.
- **Ask focused questions, not questionnaires.** 2-3 max.
- **Keep it conversational.** This is their first experience. Helpful, not bureaucratic.
- **No jargon on first contact.** Say "data point" only after you've shown them one. Before that, say "a doc about your [topic]."
- **Project type is one direct question, not an assessment.** Step 0a is the only gate. Pre-fill the suggested answer from signals in the repo/sources, but still ask. Don't wrap it in a formal "project profile assessment" or a long questionnaire — one question, then move on.
