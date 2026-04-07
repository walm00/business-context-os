---
name: context-onboarding
description: |
  First-run onboarding skill. Gets a new user from zero to 3 working data points.
  Claude figures out the right approach based on what the user shares — no paths to choose.

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

**3 working data points, user-approved, in under 30 minutes.**

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

**Don't overthink this.** Read whatever the user gives you, synthesize it, draft 3 data points.

---

## Step 1: Gather Information

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

## After Setup

Don't push next steps. Offer one:

```
Your context is set up. When things change in your business, just tell me and I'll update the right data point.
```

If the user asks "what else can I do?":
- "Want me to check these 3 data points for consistency?"
- "You could drop meeting notes or docs in `docs/_inbox/` and I'll process them into your context."
- "A 5-minute weekly check keeps things current — just ask me 'anything changed this week?'"

---

## Tips

- **Don't try to formalize everything at once.** 3 data points. Add more when these feel stable.
- **Draft real content, not placeholders.** If you can't fill a section, cut it — don't leave it empty.
- **Ask focused questions, not questionnaires.** 2-3 max.
- **Keep it conversational.** This is their first experience. Helpful, not bureaucratic.
- **No jargon on first contact.** Say "data point" only after you've shown them one. Before that, say "a doc about your [topic]."
