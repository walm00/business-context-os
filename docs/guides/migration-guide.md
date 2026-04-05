# Migration Guide

**How to go from 50 messy documents to an organized context architecture.**

---

## Who This Is For

You have existing documentation. Lots of it. Maybe it's scattered across Google Docs, Notion, markdown files, PDFs, slide decks, and people's heads. Some of it's outdated. Some of it contradicts other versions. Nobody's sure which is the "real" one.

This guide walks you through consolidating that chaos into a CLEAR-compliant context architecture — without losing anything important along the way.

---

## Before You Start

**Run context-onboarding first.** Ask Claude:

> "Scan my repo and create a Document Index"

This gives you a map of what exists before you start reorganizing. Don't skip this — you need the inventory before you can consolidate.

**Set expectations:** This is not a one-day project. For 20+ existing documents, expect 2-3 sessions spread over a week. The system is designed for incremental migration, not a big bang.

---

## The Migration Process

### Phase 1: Triage (30 min)

Look at your Document Index and sort every existing document into one of four buckets:

| Bucket | What Goes Here | Example |
|--------|---------------|---------|
| **Keep as-is** | Already well-structured, has a clear owner and scope | A brand guide that one person maintains |
| **Consolidate** | Multiple docs covering the same topic — merge into one | 3 different "audience profile" documents |
| **Extract** | One mega-doc that covers too many topics — split it | A 40-page strategy deck covering brand, audience, market, AND product |
| **Archive** | Outdated, superseded, or no longer relevant | Last year's competitive analysis that nobody references |

**Don't overthink this.** Triage by gut feel. You can re-sort later.

### Phase 2: Identify Your First 5 Knowledge Domains (30 min)

Look at the "Consolidate" and "Extract" buckets. Which topics come up most often across your documents?

Common patterns:

| If you keep seeing... | The knowledge domain is... |
|----------------------|---------------------------|
| Multiple descriptions of what the company does | Company Identity |
| Audience definitions that differ by team | Target Audience |
| Pricing info scattered across docs | Pricing Model |
| Competitive info in various formats | Competitive Landscape |
| Process docs that contradict each other | [The specific process] |
| Strategy described differently in different decks | Strategic Direction |

Pick the 5 most critical ones. These become your first 5 data points.

### Phase 3: Consolidate One at a Time (1-2 hours, spread across sessions)

For each of your 5 knowledge domains:

**Step 1: Gather all sources**

Find every document that contains information about this topic. Pull the relevant sections.

**Step 2: Create the data point**

Copy `docs/templates/context-data-point.md`. Fill in:
- `name`, `type`, `owner`, `created`, `last-updated`
- `DOMAIN` — one sentence
- `EXCLUSIVELY_OWNS` — what belongs here

**Step 3: Use context-ingest**

Tell Claude:

> "Here are 3 documents that all describe our target audience. Consolidate them into the target-audience data point. Flag any contradictions."

Claude reads all three, identifies the best/most current version of each fact, merges them into one clean data point, and flags contradictions for you to resolve.

**Step 4: Set boundaries**

Fill in `STRICTLY_AVOIDS` — what does NOT belong in this data point. This is what prevents the document from becoming another mega-doc over time.

**Step 5: Clean up the sources**

For each original document you consolidated from:
- If the ENTIRE document was absorbed → archive it (or delete if you have git history)
- If only a SECTION was relevant → remove that section and add a cross-reference: "See [data-point-name] for this topic"

### Phase 4: Connect (30 min)

After your first 5 data points exist, add relationships:
- `BUILDS_ON` — which data points feed into this one?
- `REFERENCES` — which data points does this one look up?
- `PROVIDES` — which data points use this one's content?

You don't need to get this perfect. Relationships emerge naturally as you use the system.

### Phase 5: Expand Gradually

Don't try to migrate everything at once. After the first 5:

1. Use the system for 1-2 weeks
2. Notice which knowledge is still scattered or missing
3. Add data points as the need becomes clear
4. Run context-audit to check health

**The migration rhythm:** one new data point per week. Not five per day.

---

## Common Migration Patterns

### The Mega-Document

**Problem:** One 30-page brand guide that covers identity, voice, messaging, audience, positioning, and competitive landscape.

**Solution:** Split it into 4-6 data points. Each section becomes its own data point with clear boundaries. The original document can be archived or kept as a read-only "original reference."

**How to split:**
1. Identify the natural topic breaks in the mega-doc
2. Create a data point for each major section
3. Use context-ingest to route each section to its data point
4. Add STRICTLY_AVOIDS to prevent re-accumulation

### The Contradiction Pile

**Problem:** Sales says the audience is "SMB founders." Marketing says "mid-market ops leaders." The website says both. Nobody knows which is current.

**Solution:** Create ONE Target Audience data point. Consolidate all versions. Where they contradict, present both to the decision-maker and get a ruling. Document the resolution. Set EXCLUSIVELY_OWNS to make it clear this is the single source.

### The Knowledge-in-Heads Problem

**Problem:** The best context about your business lives in the founder's head, not in any document.

**Solution:** Use context-ingest with verbal input. Tell Claude:

> "I'm going to describe our competitive positioning. Capture this as a data point."

Then talk. Claude structures what you say into a proper data point with ownership spec, content, and context sections. Review and refine.

### The Living-in-Slides Problem

**Problem:** Key business context lives in presentation decks, not documents. You can't easily reference slide 14 of a 40-slide deck.

**Solution:** Extract the knowledge from the slides into data points. The slides become a PRESENTATION of the knowledge, not the source. The data point is the source. When the slides need updating, they pull from the data point — not the other way around.

---

## What NOT to Migrate

Not everything needs to be a data point:

- **Transactional records** (invoices, receipts, contracts) — these are operational data, not knowledge domains
- **Meeting notes** — unless they contain decisions that need to be permanent. Extract the decisions, archive the notes.
- **Individual communications** (emails, messages) — extract patterns or decisions if relevant, but the messages themselves are not data points
- **Historical documents** that are no longer relevant — archive them, don't convert them
- **Technical documentation** that's well-maintained elsewhere (API docs, code docs) — don't duplicate

**The test:** "If this information became inaccurate, would it cause bad decisions?" If yes, it's a knowledge domain worth managing. If no, it's operational data — leave it where it is.

---

## Migration Checklist

- [ ] Ran context-onboarding to get Document Index
- [ ] Triaged all existing docs into Keep/Consolidate/Extract/Archive
- [ ] Identified first 5 knowledge domains
- [ ] Created 5 data points with ownership specs
- [ ] Used context-ingest to consolidate from existing docs
- [ ] Set STRICTLY_AVOIDS boundaries on each
- [ ] Added cross-references to replace removed sections in original docs
- [ ] Connected data points with BUILDS_ON / REFERENCES / PROVIDES
- [ ] Archived or cleaned up source documents
- [ ] Updated Document Index
- [ ] Set up weekly maintenance rhythm
