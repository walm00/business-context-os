---
name: context-mine
description: Extracts structured context from conversation exports (Slack, meeting transcripts, chat logs) into _inbox for processing.
category: context-management
---

# Context Mine

## Purpose

**This skill IS:**
- An extraction tool that reads conversation exports and pulls out actionable context
- A bridge between unstructured conversations and the CLEAR context architecture
- A preprocessor that dumps structured summaries to `docs/_inbox/` for review

**This skill IS NOT:**
- A replacement for context-ingest (mine extracts, ingest classifies and routes)
- An automatic integration tool (everything goes to _inbox for human review)
- A real-time conversation monitor (works on exports/transcripts after the fact)

---

## When to Use

- "Extract context from this Slack export"
- "Mine this meeting transcript for decisions"
- "Process this chat log into actionable items"
- "I have a conversation dump, what did we decide?"

---

## Supported Input Formats

| Format | Source | How to Provide |
|--------|--------|---------------|
| Plain text | Any conversation copy-paste | Paste directly into chat |
| Slack JSON export | Slack workspace export | Provide file path |
| Meeting transcript | Otter.ai, Fireflies, manual notes | Paste or provide file path |
| Chat history | Any Q&A format | Paste or provide file path |

---

## Extraction Categories

For each conversation, extract into these categories:

### Decisions Made
Things that were decided, with enough context to understand why.
```
- Decision: [what was decided]
  Rationale: [why, if stated]
  Affects: [what data points this might update]
```

### Discoveries
New information learned that wasn't known before.
```
- Discovery: [what was learned]
  Source: [who said it / where it came from]
  Relevance: [which data point or cluster this relates to]
```

### Action Items
Tasks, follow-ups, commitments.
```
- [ ] [action item]
  Owner: [who, if mentioned]
  Deadline: [when, if mentioned]
```

### Preferences & Positions
Opinions, stances, preferences expressed by key people.
```
- Preference: [what was expressed]
  Who: [who said it]
  Context: [in response to what]
```

### Problems & Risks
Issues raised, concerns flagged, blockers identified.
```
- Problem: [what was flagged]
  Severity: [high/medium/low based on language used]
  Status: [resolved in conversation or still open]
```

---

## Workflow

### Step 1: Receive Input

Accept the conversation in any supported format. If pasted directly, work with it as-is. If a file path, read the file.

### Step 2: Scan and Extract

Read through the conversation and extract items into the 5 categories above. Guidelines:
- **Be selective** — only extract items with clear business relevance
- **Preserve attribution** — note who said what when possible
- **Link to data points** — if an extracted item relates to a known data point, note which one
- **Skip small talk** — ignore greetings, scheduling logistics, off-topic chatter

### Step 3: Write to Inbox

Create one or more files in `docs/_inbox/` with frontmatter:

```yaml
---
type: session-capture
source: "[slack-export | meeting-transcript | chat-log | paste]"
date: "YYYY-MM-DD"
status: raw
mined-from: "[filename or 'direct paste']"
---
```

### Step 4: Summarize

Report to the user:
- How many items extracted per category
- Which existing data points are likely affected
- Recommend: "Run context-ingest to classify and route these items"

---

## What AI Does vs What's Mechanical

| Task | Who |
|------|-----|
| Read and understand conversation content | AI |
| Identify decisions, discoveries, action items | AI |
| Link extracted items to existing data points | AI |
| Create the output file with frontmatter | AI (template is simple enough) |
| Deduplication check against existing _inbox files | Script (compare filenames) |
| Routing into data points | context-ingest skill (separate step) |

---

## Example Output

```markdown
---
type: session-capture
source: slack-export
date: 2026-04-07
status: raw
mined-from: "product-channel-export-april.json"
---

## Decisions
- Switched to usage-based pricing for enterprise tier
  Rationale: Customer interviews showed resistance to per-seat model
  Affects: pricing-strategy.md, value-proposition.md

## Discoveries
- Competitor X launched a free tier targeting our mid-market segment
  Source: Sales team discussion in #product channel
  Relevance: competitive-positioning.md

## Action Items
- [ ] Update pricing page with new enterprise model
- [ ] Schedule competitive response meeting for Friday

## Problems
- Enterprise onboarding flow takes 3 weeks — customers complaining
  Severity: high
  Status: open — no resolution in conversation
```

---

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| **context-ingest** | Mine outputs TO inbox, ingest processes FROM inbox |
| **context-audit** | Mine can surface items that reveal stale data points |
| **ecosystem-manager** | Mine may discover patterns worth capturing as lessons |
