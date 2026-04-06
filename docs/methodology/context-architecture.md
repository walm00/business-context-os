# Context Architecture

**Purpose:** Define the map of what your organization knows, who owns what, and how pieces connect.

---

## What Is a Context Architecture?

Every organization has institutional knowledge spread across documents, decks, people's heads, and shared drives. A context architecture is the deliberate structure you put around that knowledge so it stays accurate, findable, and useful.

Think of it as the blueprint for your organization's knowledge. Just like a building has an architecture that says where the walls go, where the plumbing runs, and which rooms connect to which -- your context architecture says:

- **What distinct pieces of knowledge exist** (your context data points)
- **Who owns each piece** (clear accountability)
- **How pieces relate to each other** (dependencies and references)
- **What boundaries exist** (what belongs where, and what does not)

Without a context architecture, knowledge sprawls. The same concept gets described in five places. Nobody knows which version is current. New team members cannot find what they need. AI tools fed this context produce inconsistent results because the context itself is inconsistent.

With a context architecture, every piece of organizational knowledge has a home, an owner, and clear boundaries.

---

## Context Data Points

A **context data point** is a specific, bounded piece of organizational knowledge. It has a clear purpose, a defined scope, and an explicit owner.

Context data points are the building blocks of your architecture. Each one answers a specific question about your organization:

| Question | Data Point |
|---|---|
| What do we sell? | Product Description |
| Who do we sell to? | Target Audience |
| What makes us different? | Value Proposition |
| How does our brand sound? | Brand Voice |
| What problem exists in the market? | Problem Statement |
| How do we make money? | Business Model |
| What do our customers struggle with? | Customer Pain Points |
| What do our customers want to achieve? | Customer Desired Outcomes |

Each data point is NOT a document. It is a **knowledge domain** — a topic area with clear boundaries that your organization needs to keep accurate over time.

### Data Points vs. Operational Data

This distinction matters. A data point is the **knowledge that tells you what things should say**, not the things themselves:

| Data Point (BCOS manages this) | Operational Data (BCOS does NOT manage this) |
|-------------------------------|----------------------------------------------|
| "Our Target Audience" — the definition, segments, logic | Individual customer records, CRM entries |
| "Our Pricing Model" — the structure, tiers, rationale | Individual invoices and quotes |
| "Our Sales Process" — the steps, roles, handoffs | Individual deal notes and call logs |
| "Our Outreach Strategy" — messaging, channels, approach | Individual emails and messages sent |
| "Our Brand Voice" — the guidelines, tone, dos/don'ts | Individual social media posts |

A data point captures **knowledge that doesn't change every day but drifts if nobody maintains it**. It's the stuff people disagree about because there's no single source of truth.

If you're thinking "should I put all my invoices in BCOS?" — no. Put your **pricing model** in BCOS. The invoices are generated FROM that knowledge. BCOS manages the source, not the outputs.

### What Makes a Good Data Point

A well-defined data point has:

- **A clear domain** -- You can explain in one sentence what it covers
- **Exclusive ownership** -- It contains things that no other data point contains
- **Explicit boundaries** -- You know what it does NOT contain
- **Defined relationships** -- You know what it depends on and what depends on it

A poorly defined data point:

- Overlaps with other data points ("Is our competitive positioning in the Value Proposition or the Market Context?")
- Has no clear boundary ("Brand Voice" that also includes messaging, taglines, and audience descriptions)
- Depends on everything ("Strategy" that references every other data point)

---

## The Cluster Concept

Data points naturally group into **clusters** -- collections of related knowledge that serve a common strategic function.

Clusters help you see the big picture without getting lost in individual data points. They also help you identify gaps: if you have a well-developed Brand & Identity cluster but no Audience & Market cluster, you know where to focus next.

### Common Cluster Patterns

These are starting points, not requirements. Your organization's clusters should reflect YOUR reality.

**Brand & Identity Cluster**

The knowledge that defines who you are and how you present yourself.

| Data Point | What It Covers |
|---|---|
| Brand Identity | Core personality, mission, values, origin story |
| Brand Voice | Tone, communication style, vocabulary, channel adaptations |
| Visual Identity | Logo usage, color palette, typography, imagery guidelines |
| Messaging Framework | Key messages, taglines, elevator pitches, proof points |

**Audience & Market Cluster**

The knowledge that defines who you serve and the landscape you operate in.

| Data Point | What It Covers |
|---|---|
| Target Audience | Demographics, firmographics, segments, qualification criteria |
| Customer Pain Points | Frustrations, challenges, inefficiencies your audience faces |
| Customer Desired Outcomes | Aspirations, goals, success metrics your audience wants |
| Market Context | Industry trends, market dynamics, regulatory environment |
| Competitive Landscape | Key competitors, positioning gaps, differentiation opportunities |

**Product & Value Cluster**

The knowledge that defines what you offer and why it matters.

| Data Point | What It Covers |
|---|---|
| Product Description | What it is, what it does, how it works at a high level |
| Product Features | Specific capabilities, specifications, limitations |
| Value Proposition | Why choose us, key differentiators, customer-facing benefits |
| Problem Statement | The market-level problem your product addresses |
| Solution Scope | What is included, what is excluded, known limitations |

**Strategy & Operations Cluster**

The knowledge that defines how you operate and where you are headed.

| Data Point | What It Covers |
|---|---|
| Business Model | How you create and capture value, stakeholder relationships |
| Strategic Goals | Current priorities, OKRs, growth targets |
| Key Metrics | How you measure success, benchmarks, reporting cadence |
| Geographic Scope | Markets served, regional considerations, expansion plans |

---

## How Many Data Points to Start With

**Recommendation: Start with 5-8 data points.**

Starting with too few means your data points are too broad and will develop internal contradictions. Starting with too many creates overhead before you have the discipline to maintain them.

### A Practical Starting Set

For most organizations, these 5-8 data points cover the essential ground:

1. **Brand Identity** -- Who we are
2. **Brand Voice** -- How we sound
3. **Target Audience** -- Who we serve
4. **Product Description** -- What we offer
5. **Value Proposition** -- Why choose us
6. **Competitive Landscape** -- Who else is out there (optional to start)
7. **Business Model** -- How we make money (optional to start)
8. **Customer Pain Points** -- What our audience struggles with (optional to start)

Start with the first five. Add more when you feel confident that the first five are stable, well-owned, and consistently maintained.

### The Expansion Pattern

```
Month 1-2:  5 core data points, basic ownership
Month 3-4:  Add 2-3 more as gaps become apparent
Month 5-6:  Refine relationships between data points
Month 7+:   Add specialized data points as needed
```

Do not rush this. A small, well-maintained context architecture beats a large, neglected one every time.

---

## Progressive Disclosure

You do not need to define everything about every data point on day one. Context architecture supports **progressive disclosure** -- start simple, add structure as complexity demands it.

### Level 1: Domain + Ownership (Start Here)

For each data point, define just two things:

- **DOMAIN** -- What this data point covers (one sentence)
- **EXCLUSIVELY_OWNS** -- What ONLY this data point contains

This is enough to prevent the most common problem: overlapping definitions that create confusion and inconsistency.

**Example at Level 1:**

```
Brand Voice
  DOMAIN = How our brand communicates across all channels
  EXCLUSIVELY_OWNS = Tone attributes, writing style, vocabulary guidelines
```

### Level 2: Add Boundaries

When you start noticing content creeping across data points, add:

- **STRICTLY_AVOIDS** -- What this data point must NOT contain (it belongs elsewhere)

**Example at Level 2:**

```
Brand Voice
  DOMAIN = How our brand communicates across all channels
  EXCLUSIVELY_OWNS = Tone attributes, writing style, vocabulary guidelines
  STRICTLY_AVOIDS = Specific taglines (Messaging Framework),
                    audience demographics (Target Audience),
                    visual guidelines (Visual Identity)
```

### Level 3: Add Relationships

When your data points become interconnected and you need to track dependencies, add:

- **BUILDS_ON** -- Upstream data points this depends on
- **REFERENCES** -- Data points to cross-reference
- **PROVIDES** -- Downstream data points that consume this

**Example at Level 3:**

This is the full ownership specification. See [ownership-specification.md](./ownership-specification.md) for the complete format and detailed examples.

---

## The Ownership Specification Format

Each context data point can be formally specified using six keywords that define its territory, boundaries, and relationships. This format is the core of Business Context OS.

The full specification format is documented in [ownership-specification.md](./ownership-specification.md), which covers:

- The six keywords and what each means
- A fill-in-the-blank template
- A complete worked example
- Common mistakes and how to avoid them

You do not need the full specification to get started. Begin with Level 1 (Domain + Ownership) and add the remaining keywords as your needs grow.

---

## When to Add New Data Points

Your context architecture should grow organically. Here are signs that you need to split an existing data point or add a new one:

**Split an existing data point when:**

- A single data point is being maintained by two different teams with different priorities
- The document is growing too large to scan quickly (a rough guideline: if scrolling takes more than a few seconds, it may be too broad)
- Two distinct concepts are forced together. Ask: "Could someone need one of these without the other?" If yes, they should be separate.
- Stakeholders disagree about what belongs in this data point -- the disagreement often reveals two different purposes hiding inside one container

**Add a new data point when:**

- You discover a concept that does not fit cleanly into any existing data point
- Multiple existing data points reference the same piece of information that has no official home
- A new business initiative creates a new category of knowledge (e.g., entering a new market creates a need for a "Market Expansion" data point)
- AI tools or team members keep asking a question that no data point answers

**Example of a justified split:**

Your "Brand Guidelines" data point has grown to include brand identity, brand voice, visual identity, and messaging. Teams are starting to argue about what goes where. The voice team wants to update tone guidelines but is afraid of breaking the visual identity section.

Split into:
- Brand Identity (personality, values, origin)
- Brand Voice (tone, style, vocabulary)
- Visual Identity (logo, colors, typography)
- Messaging Framework (taglines, elevator pitches, proof points)

Each now has a clear owner and can evolve independently.

---

## When to Merge Data Points

Over-fragmentation is just as harmful as under-fragmentation. Here are signs you have too many data points:

**Merge data points when:**

- Two data points always change together -- if updating one always requires updating the other, they are probably one concept
- A data point has very thin content that does not justify standalone ownership
- The relationship between two data points is confusing because they are too similar
- Teams cannot remember which data point to update for a given change
- You find yourself creating "bridge" documents just to connect two data points that should be one

**Example of a justified merge:**

You have separate "Customer Demographics" and "Customer Firmographics" data points. They are always updated together, always referenced together, and maintained by the same person. Merge them into a single "Target Audience Profile" data point.

---

## Quick Start Guide

1. **List your essential knowledge areas.** What does your organization need to know about itself to operate effectively? Write each one on a sticky note or in a list.

2. **Group them into clusters.** Which pieces of knowledge naturally belong together? Use the cluster patterns above as inspiration, not prescription.

3. **Define 5-8 data points.** For each one, write a one-sentence DOMAIN and a short EXCLUSIVELY_OWNS list. That is enough to start.

4. **Assign owners.** Each data point needs one person or team responsible for keeping it current. Not a committee. One owner.

5. **Start using them.** When someone asks "what do we do?" or "who do we sell to?" point them to the relevant data point. When something changes, update the authority and notify downstream consumers.

6. **Grow gradually.** Add boundaries (STRICTLY_AVOIDS) when overlap appears. Add relationships (BUILDS_ON, REFERENCES, PROVIDES) when dependencies matter. See [ownership-specification.md](./ownership-specification.md) for the full format.

---

**Remember: A small, well-maintained context architecture is worth more than a large, neglected one. Start simple. Grow when the need is real.**
