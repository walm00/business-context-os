---
name: context-ingest
description: |
  Integrates new knowledge sources into existing context data points. Takes raw input
  (documents, URLs, meeting notes, pasted content) and routes the knowledge to the
  correct owning data points — or recommends creating new ones.

  WHEN TO USE:
  - "Here's a document — integrate it into my context"
  - "I just had a meeting — capture the key decisions"
  - "Read this article and update our market context"
  - "Our competitor just announced X — update positioning"
  - Any time new information needs to enter the context architecture
---

# Context Ingest

## Purpose

**This skill IS:**

- The entry point for getting new knowledge INTO your context architecture
- A router that sends information to the correct owning data point
- A classifier that determines what type of knowledge you're adding
- The mechanism that makes your context system compound over time

**This skill IS NOT:**

- Creating the initial context architecture (use `context-onboarding` for that)
- Auditing existing context (use `context-audit` for that)
- A raw file storage system (it extracts and integrates, not archives)

---

## When to Use

- "Here's our new brand guidelines PDF — integrate it"
- "Update our context with these meeting notes"
- "I read this article about our market — capture the key insights"
- "Our competitor just launched a new product — update competitive positioning"
- "Here's our updated pricing — make sure context reflects it"
- "I pasted some notes — figure out where they belong"

---

## The Ingest Process

### Step 1: Receive the Source

Accept input in any form:
- A file path (markdown, PDF, text)
- A URL (Claude reads the page)
- Pasted text in the conversation
- A description of what changed ("we decided to pivot to enterprise")

Note what the source is and where it came from. This becomes the source citation.

### Step 2: Classify the Content

Identify what KIND of knowledge this is:

| Content Type | Route To |
|-------------|----------|
| Company identity, mission, values | Company/identity data points |
| Customer info, audience, segments | Audience data points |
| Product/service changes | Product/value data points |
| Process changes, workflow updates | Process documents |
| Market shifts, competitor moves | Market/competitive data points |
| Policy changes, rules | Policy documents |
| New facts, reference data | Reference documents |
| Strategic decisions, direction changes | Strategy data points |

If the content spans multiple types, split it and route each piece separately.

**Temporal classification — is this about now or the future?**

| Signal in the content | Status to assign |
|----------------------|-----------------|
| "We currently...", "Our pricing is...", "We serve..." | `active` — current reality |
| "We plan to...", "Next quarter we will...", "We're considering..." | `planned` — future intent |
| "We used to...", "Previously...", "Before the pivot..." | May need `archived` |

**Important:** Do not merge future-state content into an active document without discussing with the user. If someone says "we plan to add enterprise pricing", that belongs in `docs/_planned/enterprise-pricing.md`, not in the active pricing doc. When the plan becomes reality, move it to `docs/` root and build full cross-references.

### Step 3: Find the Owner

For each piece of knowledge:

1. **Check existing data points** — does one already OWN this topic?
   - Read the EXCLUSIVELY_OWNS section of candidate data points
   - If a clear owner exists → route there

2. **Check STRICTLY_AVOIDS** — make sure you're not putting it in the wrong place
   - If data point X says "STRICTLY_AVOIDS competitor analysis" → don't put competitor info there

3. **No owner found?** → Recommend creating a new data point
   - Suggest a name, cluster, and initial DOMAIN
   - Use the template from `docs/templates/context-data-point.md`

### Step 4: Integrate

For each affected data point:

1. **Read the current content** of the owning data point
2. **Merge the new knowledge** into the appropriate section:
   - New facts → Content section
   - New strategic implications → Context section
   - Source info → Sources section (if it exists)
3. **Check for contradictions** with existing content:
   - If the new info contradicts existing content → flag it, don't silently overwrite
   - Present both versions to the user and ask which is current
4. **Update metadata:**
   - Bump `version` (at least patch)
   - Update `last-updated` to today
   - Never touch `created`

### Step 5: Update Cross-References

After integrating:

1. **Check relationships** — does this new knowledge affect other data points?
   - If market context changed → competitive positioning may need review
   - If audience changed → messaging and value prop may need review
2. **Update BUILDS_ON / REFERENCES / PROVIDES** if new connections emerged
3. **Update Document Index** (`docs/document-index.md`) if it exists:
   - Add the source to "Knowledge Sources Found"
   - Update coverage assessment if gaps were filled

### Step 6: Report

Summarize what happened:

```
## Ingest Summary

**Source:** [what was ingested]
**Date:** [today]

### Updates Made
- **[data-point-name]** (v1.2.0 → v1.3.0): Added [what]
- **[data-point-name]** (v2.0.1 → v2.0.2): Updated [what]

### Contradictions Found
- [data-point]: new info says X, existing content says Y → [resolved/flagged]

### New Data Points Recommended
- [suggested name]: [why needed]

### Cross-References Updated
- [data-point-A] now REFERENCES [data-point-B]

### Document Index
- [Updated / No changes needed]
```

---

## Handling Contradictions

When new information contradicts existing content:

1. **Don't silently overwrite.** The existing content may be deliberately different.
2. **Present both versions** to the user:
   - "Your market-context data point says X. The new source says Y. Which is current?"
3. **If user confirms the new version:** Update the data point, note the change in the changelog.
4. **If user says 'keep both':** Note the contradiction in the Context section as a known tension.
5. **If user is unsure:** Flag the data point as `status: under-review`.

---

## Batch Ingest

For multiple sources at once:

1. List all sources first
2. Classify each one
3. Group by target data point
4. Process one data point at a time (merge all relevant sources into it)
5. Report all changes at the end

**Recommendation:** Ingest one source at a time when possible. Stay involved. Check the summaries. Guide emphasis. Batch ingest is faster but less supervised.

---

## Source Citation

When integrating new knowledge, preserve where it came from:

```markdown
## Sources

| Claim | Source | Date | Confidence |
|-------|--------|------|------------|
| Market growing 15% YoY | Industry Report 2026 | 2026-03-15 | High |
| Competitor X raised Series B | TechCrunch article | 2026-04-01 | High |
| Customer segment shifting to enterprise | Q1 sales review | 2026-04-05 | Medium |
```

Not every claim needs a source. Use this for important facts, statistics, and claims that might be challenged or need periodic verification.

---

## Integration with Other Skills

| Skill | How It Connects |
|-------|----------------|
| **context-onboarding** | Onboarding discovers what exists; ingest adds new knowledge to it |
| **context-audit** | After ingest, audit catches any boundary violations introduced |
| **daydream** | Reflection may reveal knowledge gaps; ingest fills them |
| **core-discipline** | Compounding rule triggers ingest: "file this insight back into context" |
| **clear-planner** | Large ingests (10+ sources) may need a plan first |
