# Getting Started with Business Context OS

**Your Week 1 walkthrough. No technical background required.**

---

## What You'll Build

By the end of this guide, you will have a **living context system** -- a structured, organized home for the business knowledge your team relies on every day.

Instead of your brand story living in five different documents (each slightly different), your audience definition meaning something different to sales and marketing, or your value proposition being a moving target depending on who you ask -- you will have ONE trusted source for each piece of knowledge, with clear ownership and boundaries.

This system grows with your business. It is not a one-time exercise. It is a practice that keeps your organizational knowledge accurate, consistent, and useful -- whether a person or an AI tool is looking for it.

**Total time for this guide: about 1 hour.** Then 5 minutes per week to keep it alive.

---

## Prerequisites

You need two things:

1. **Claude Code installed** on your computer
2. **This repository cloned** to your local machine

If you are not sure about either of these, ask your IT person or a technically inclined colleague for help with the initial setup. Once it is set up, you will not need technical skills to use the system.

---

## Step 0 (Recommended): Let Claude Scan Your Repo First

If you already have documents, READMEs, guides, or any business knowledge in your project, start here. Ask Claude:

> "Scan my repo and create a Document Index -- show me what business context already exists."

This invokes the **context-onboarding** skill, which will:
1. Scan your repo for existing documentation and knowledge sources
2. Classify what it finds by topic (brand, audience, product, strategy, etc.)
3. Produce a **Document Index** at `docs/document-index.md`
4. Recommend which data points to create first, based on what already exists

**This step takes 5-15 minutes** and gives you a map before you start building. The recommendations from the scan feed directly into Step 2 below.

If you are starting with a blank project and no existing docs, skip to Step 1.

---

## Step 1: Understand Your Starting Point (10 minutes)

Before creating anything, take 10 minutes to think about the context your team already relies on. If you ran Step 0, review your Document Index alongside these questions. If not, grab a notebook or open a blank document and answer these three questions.

### Question 1: What context does your team rely on?

Think about the documents, definitions, and knowledge that your team uses regularly. Common examples:

- Company description or about page
- Key processes or SOPs
- Customer or audience profiles
- Product or service descriptions
- Strategic plans or OKRs
- Competitive landscape or market context
- Team structure or org context
- Brand guidelines or messaging docs

Write down everything that comes to mind. Do not filter. You are making an inventory.

### Question 2: Which pieces get outdated fastest?

Look at your list. Circle the ones that change most often or feel unreliable. These are your highest-priority candidates.

Common answers:
- Competitive information (market moves fast)
- Process docs (workflows evolve but docs lag behind)
- Strategic direction (pivots happen, docs don't follow)
- Team context (people join, leave, change roles)
- Customer profiles (evolve as you learn more)

### Question 3: Where do people disagree about "the truth"?

Think about recent moments when two people on your team gave different answers to the same question. Examples:

- "Who is our target audience?" and marketing says one thing while sales says another
- "What makes us different from [competitor]?" and the website says one thing while the pitch deck says another
- "What is our brand voice?" and the social team has one interpretation while the email team has another

These disagreements are the clearest signal that you need organized context. Write down 2-3 examples.

**You now have a picture of your starting point.** Keep these notes -- you will use them in the next step.

---

## Step 2: Define Your First 3 Data Points (30 minutes)

A **data point** is a specific topic your business needs to know about. Think of it as one box in a filing cabinet -- it has a label, clear contents, and one person responsible for it.

You will start with just three. Not ten. Not twenty. Three.

### Pick your 3 most important data points

Look at your notes from Step 1. Which three pieces of business knowledge are most critical? For most organizations, it is some combination of these:

| If your biggest need is... | Start with these 3 |
|---|---|
| Brand consistency | Brand Identity, Brand Voice, Messaging |
| Customer clarity | Target Audience, Value Proposition, Customer Pain Points |
| Market positioning | Value Proposition, Competitive Landscape, Target Audience |
| General foundation | Brand Identity, Target Audience, Value Proposition |

**Not sure? Start with Brand Identity, Target Audience, and Value Proposition.** These three cover the most ground for any organization.

### Create each data point

For each of your 3 data points, copy the template at `docs/templates/context-data-point.md` and rename it. Use lowercase with dashes: `brand-identity.md`, `target-audience.md`, `value-proposition.md`.

For each one, fill in just two things to start:

**DOMAIN** -- What does this data point cover? Write one sentence.

**EXCLUSIVELY_OWNS** -- What can ONLY be found here? Write 3-5 bullet points.

That is it. Do not fill in every section of the template. Do not worry about relationships or boundaries yet. Start with what this data point IS and what it OWNS.

### Example: Brand Identity

Here is what a minimal first draft looks like:

```
DOMAIN: Core brand attributes, mission, vision, values, and brand story.

EXCLUSIVELY_OWNS:
- Mission statement
- Vision statement
- Brand values (the 4 core values)
- Founding story
- Brand personality traits
```

### Example: Target Audience

```
DOMAIN: Who we serve -- target customer profiles, segments, and qualification criteria.

EXCLUSIVELY_OWNS:
- Primary audience segment definition
- Secondary audience segment definition
- Company size and industry targeting criteria
- Decision-maker roles we sell to
- Geographic focus areas
```

### Example: Value Proposition

```
DOMAIN: Why customers choose us -- our key differentiators and the value we deliver.

EXCLUSIVELY_OWNS:
- Core value proposition statement
- Key differentiators (what makes us different)
- Customer-facing benefits
- Proof points and evidence
```

**Spend about 10 minutes on each data point.** They do not need to be perfect. They need to exist. You will refine them over time.

---

## Step 3: Set Up Your Architecture (15 minutes)

Now that you have your three data points, give them a home.

### Copy the architecture canvas

Copy the template at `docs/templates/context-architecture-canvas.md` and save it as your working architecture document.

### Fill in the basics

You do not need to fill in every section. Focus on these three:

**1. Organization Overview** -- Write your company name, what you do, and who you serve. One sentence each.

**2. Cluster Planning** -- A cluster is just a group of related data points. Your first three data points probably fit into 1-2 clusters. Common clusters:

- **Brand & Identity** -- for brand identity, brand voice, messaging
- **Audience & Market** -- for target audience, competitive landscape, market context
- **Product & Value** -- for value proposition, product description, features

Write down which cluster each of your 3 data points belongs to.

**3. Data Point Inventory** -- List your 3 data points, their cluster, and who owns each one. Ownership means: one person who is responsible for keeping it accurate. Not a committee. One name.

### That is your architecture

It is intentionally simple. A small, well-maintained architecture is worth far more than a large, neglected one. You will add to it over time.

---

## Step 4: Start Using It (Ongoing)

Your context system is only valuable if you actually use it. Here is how.

### Tell Claude about your context

When you start a Claude Code conversation, point Claude to your context architecture. You can say things like:

- "My business context is organized in docs/. Brand Identity is the authority on our mission, values, and brand story."
- "When I ask about our target audience, use the Target Audience data point as the source of truth."
- "Before writing any messaging, check the Value Proposition data point for our key differentiators."

Claude will use your data points as the authoritative source, giving you consistent answers grounded in your actual business knowledge.

### When something changes, update the owning data point

This is the most important habit to build. When something changes in your business:

1. Identify which data point owns that information
2. Update that data point
3. Done

Examples:
- Revised your mission statement? Update Brand Identity.
- Discovered a new customer segment? Update Target Audience.
- Changed your pricing model? Update Value Proposition.

The key insight: **update ONE place, and everything that references it stays current.**

### Weekly check-in (5 minutes)

Set a recurring 5-minute calendar reminder. Every week, ask yourself:

- Did anything happen this week that affects any of my data points?
- If yes: update the relevant data point
- If no: done

Most weeks, the answer is "nothing changed" and you are done in 60 seconds.

---

## What's Next

You now have the foundation of a living context system. From here, you have options:

- **Keep it simple.** Many organizations thrive with just the foundation -- organized data points, clear ownership, weekly maintenance. There is no pressure to do more.

- **Add more data points.** When you feel confident that your first 3 are stable and well-maintained, add 2-3 more. See [defining-your-context.md](./defining-your-context.md) for detailed guidance on creating data points.

- **Add boundaries.** When you notice content creeping between data points (your Target Audience starts absorbing messaging, your Brand Identity starts including product descriptions), add STRICTLY_AVOIDS boundaries. See [defining-your-context.md](./defining-your-context.md).

- **Explore automation.** If you want Claude to help you audit, plan, and maintain your context, see [adoption-tiers.md](./adoption-tiers.md) for the incremental path from manual to automated.

- **Learn maintenance practices.** To keep your context alive over months and years, see [maintenance-guide.md](./maintenance-guide.md).

- **If this is all new to you,** start with [for-non-technical-users.md](./for-non-technical-users.md) for a plain-language explanation of every concept.

---

**Remember: Start small. Use what you build. Grow when the need is real.**
