# Defining Your Context

**A step-by-step guide to creating data points that actually work.**

---

## What Makes a Good Data Point

A data point is a specific topic your business needs to know about. It is the answer to one clear question: "Where does our team go for the truth about X?"

Good data points share three qualities:

1. **Focused.** Each data point covers one distinct area. "Brand Identity" is focused. "Everything About Our Brand" is not.

2. **Clearly bounded.** You can say with confidence what belongs in this data point and what does not. If someone asks "where does our tagline go?" there is one obvious answer.

3. **Actively maintained.** Someone specific is responsible for keeping it current. Not "the marketing team" -- a person with a name.

If a data point does not have these three qualities, it will rot. It will become another document that nobody trusts, and people will go back to asking each other instead.

---

## The Creation Process

Follow these steps for each new data point. The first time takes about 15-20 minutes. Once you have done it a few times, it takes 10.

### Step 1: Name It

Choose a clear, specific name. Use a noun or noun phrase. The name should tell someone unfamiliar with your organization what kind of knowledge lives here.

| Good names | Why they work |
|---|---|
| Brand Identity | Specific, clear scope |
| Target Audience | Tells you exactly what it covers |
| Value Proposition | Recognized business concept |
| Competitive Landscape | Clear domain |

| Weak names | Why they don't work |
|---|---|
| Brand Stuff | Vague, could mean anything |
| Strategy | Way too broad |
| Notes | Not a knowledge domain |
| Misc | This is where context goes to die |

**File naming:** Use lowercase with dashes for the file name: `brand-identity.md`, `target-audience.md`, `value-proposition.md`.

### Step 2: Define DOMAIN

Write one-to-three sentences describing what this data point covers -- its territory. A good DOMAIN statement answers: "What is this data point about?"

**Tips:**
- Start with the subject, not your company name
- Include the purpose (what is it for?)
- Be specific enough to distinguish from neighboring data points

**Examples:**

```
Brand Identity
DOMAIN: Core brand attributes, mission, vision, values, and brand
story serving as the foundational reference for who the company is
and what it stands for.
```

```
Target Audience
DOMAIN: Definitive target audience profile and customer
characteristics serving as the foundational reference for all
customer-related business strategy.
```

```
Value Proposition
DOMAIN: Key differentiators, customer-facing benefits, and the
core reason customers choose us over alternatives.
```

### Step 3: Define EXCLUSIVELY_OWNS

This is the most important step. List the specific items that ONLY this data point contains. If something appears in your EXCLUSIVELY_OWNS list, it should not appear in any other data point.

Think of it as answering: "What can I find HERE and only here?"

**Tips:**
- Be specific: "Mission statement" is better than "brand stuff"
- Aim for 3-8 items (less is vague, more is unwieldy)
- Each item should be a distinct piece of knowledge

**Example for Brand Identity:**

```
EXCLUSIVELY_OWNS:
- Mission statement
- Vision statement
- Brand values and their definitions
- Founding story and origin narrative
- Brand personality traits and attributes
- Core brand promise
```

**Example for Target Audience:**

```
EXCLUSIVELY_OWNS:
- Primary audience segment definition
- Secondary audience segment definition
- Target organization types and size criteria
- Decision-maker roles and authority profiles
- Geographic and industry targeting criteria
- Audience prioritization framework
```

### Step 4: Define STRICTLY_AVOIDS

This step prevents drift. Without boundaries, data points gradually absorb related content until they overlap with their neighbors. STRICTLY_AVOIDS draws a clear line.

Think of it as answering: "What should I NOT put here, even if it seems related?"

**Tips:**
- Always note WHERE the avoided content belongs using an arrow: `(-> Data Point Name)`
- Focus on the most common areas of confusion
- You do not need to list every possible thing this data point is NOT -- just the ones people are most likely to confuse

**Example for Brand Identity:**

```
STRICTLY_AVOIDS:
- Taglines and key messages (-> Messaging Framework)
- Tone of voice and writing style guidelines (-> Brand Voice)
- Visual identity: logo, colors, typography (-> Visual Identity)
- Audience demographics and segments (-> Target Audience)
- Product features and capabilities (-> Product Description)
```

**Example for Target Audience:**

```
STRICTLY_AVOIDS:
- Customer pain points and challenges (-> Customer Pain Points)
- Customer desired outcomes (-> Customer Desired Outcomes)
- Market-wide industry trends and sizing (-> Market Context)
- Brand communication preferences (-> Brand Voice)
- Competitive audience overlap analysis (-> Competitive Landscape)
```

### Step 5: Write the Content

Now fill in the actual knowledge. This is the core of your data point -- the facts, specifics, definitions, and details that your team needs.

Write it so that someone new to the team could read it and immediately use it. Avoid vague aspirations. Be concrete.

**Organize into logical subsections.** Here are examples by data point type:

| Data Point | Useful Subsections |
|---|---|
| Brand Identity | Mission, Vision, Values, Brand Story, Brand Personality |
| Target Audience | Primary Segment, Secondary Segment, Firmographics, Decision Makers |
| Value Proposition | Core Statement, Key Differentiators, Proof Points, Customer Benefits |
| Competitive Landscape | Market Position, Key Competitors, Differentiation, Gaps |
| Brand Voice | Tone Attributes, Writing Style, Vocabulary, Channel Adaptations |

### Step 6: Write the Context

After the facts, add strategic interpretation. Not just WHAT the facts are, but what they MEAN.

Answer these questions:
- Why does this matter for the business?
- How should teams use this information in their daily work?
- What decisions does this data point support?
- What tensions or tradeoffs exist?

**Example context section for Target Audience:**

> We deliberately focus on mid-market companies (50-500 employees) even though enterprise deals are larger, because our product's self-serve model fits this segment best. Sales should qualify prospects against these criteria before investing significant time. Marketing campaigns should speak to the daily reality of operations leads, not C-suite concerns.

### Step 7: Add Relationships (When Ready)

You do not need relationships on day one. Add them when your architecture matures and you start noticing how data points depend on each other.

Three relationship types:

**BUILDS_ON** -- Hard dependencies. This data point cannot exist without the upstream one. If the upstream data point changes significantly, this one needs review.

```
BUILDS_ON: brand_identity:core_personality_foundation
```

This means: "Brand Voice is built on the core personality defined in Brand Identity."

**REFERENCES** -- Soft connections. Useful context, but not a hard dependency. A change in the referenced data point may or may not require a review here.

```
REFERENCES: target_audience:audience_communication_preferences
```

**PROVIDES** -- Downstream consumers. Who uses the output of this data point? This is your change management tool -- when you update this data point, check these consumers.

```
PROVIDES:
  voice_guidelines -> messaging_framework
  content_guidelines -> marketing_plans
```

---

## Common Starting Architectures

Here are three ready-made starting patterns. Pick the one closest to your situation, then customize.

### Pattern 1: Brand Team (6 data points)

For marketing teams focused on brand consistency and messaging.

| Data Point | What It Covers | Example Owner |
|---|---|---|
| Brand Identity | Mission, vision, values, story, personality | Brand Director |
| Target Audience | Customer segments, demographics, firmographics | Marketing Director |
| Messaging Framework | Key messages, taglines, elevator pitches, proof points | Content Lead |
| Brand Voice | Tone, writing style, vocabulary, channel adaptations | Content Lead |
| Competitive Positioning | Market position, differentiation, competitor awareness | Strategy Lead |
| Value Proposition | Why choose us, key differentiators, customer benefits | Marketing Director |

**Cluster structure:**
- Brand & Identity: Brand Identity, Brand Voice, Messaging Framework
- Audience & Market: Target Audience, Competitive Positioning
- Product & Value: Value Proposition

### Pattern 2: Product Team (6 data points)

For product-led organizations where the product is the story.

| Data Point | What It Covers | Example Owner |
|---|---|---|
| Product Description | What it is, what it does, how it works | Product Lead |
| Product Features | Specific capabilities, specifications, limitations | Product Lead |
| Target Audience | Who uses it, buyer vs user profiles, segments | Marketing Lead |
| Market Context | Industry trends, regulatory environment, market dynamics | Strategy Lead |
| Competitive Landscape | Key competitors, positioning gaps, differentiation | Strategy Lead |
| Product Roadmap | Where the product is headed, upcoming capabilities | Product Lead |

**Cluster structure:**
- Product & Value: Product Description, Product Features, Product Roadmap
- Audience & Market: Target Audience, Market Context, Competitive Landscape

### Pattern 3: Founder / CEO (5 data points)

For early-stage companies where the founder holds most of the context.

| Data Point | What It Covers | Example Owner |
|---|---|---|
| Company Identity | Who we are, why we exist, our story, our values | Founder |
| Target Audience | Who we serve, what they look like, how we find them | Founder |
| Value Proposition | Why us, what makes us different, core benefits | Founder |
| Market Context | The landscape we operate in, trends, opportunities | Founder |
| Key Metrics | How we measure success, current benchmarks, targets | Founder |

**Cluster structure:**
- Foundation: Company Identity, Value Proposition
- Market: Target Audience, Market Context
- Operations: Key Metrics

**Note for founders:** You will likely be the owner of all 5 to start. That is fine. As you hire, transfer ownership to domain experts. The transfer is easy because the boundaries are already defined.

---

## Testing Your Data Points

Before you call your data points "done," run these three tests.

### Test 1: The "Where Does This Go?" Test

Pick a random piece of business knowledge -- something your team discusses regularly. Examples:
- "We were founded in 2019"
- "Our primary competitor just raised $50M"
- "Our customers struggle with manual reporting"
- "Our brand should feel approachable but professional"

For each one, ask: **Which data point does this belong to?**

- If the answer is clear and immediate: your boundaries are working.
- If you hesitate or could argue for two places: your boundaries need sharpening. Add STRICTLY_AVOIDS to clarify which data point does NOT own it.
- If nothing fits: you may need a new data point.

### Test 2: The "Who Owns This?" Test

Pick 5 different pieces of knowledge from across your business. For each one, ask: **Who is the one person responsible for keeping this accurate?**

- If you can name one person for each: ownership is clear.
- If you say "the team" or "everyone": nobody owns it, which means nobody will update it.
- If two people both claim ownership: your EXCLUSIVELY_OWNS lists overlap.

### Test 3: The "What Changed?" Test

Imagine a specific change. Examples:
- "We just changed our mission statement"
- "We discovered a new competitor"
- "Our primary audience segment shifted from SMBs to mid-market"

Now trace the change through your architecture:

1. Which data point gets updated first?
2. Which other data points need to be reviewed?
3. Who needs to be notified?

If you can answer all three, your architecture is working. If you cannot, you are missing relationships (BUILDS_ON, REFERENCES, PROVIDES) between data points.

---

## Growing Over Time

Your context architecture should grow organically. Here is how to know when to add, split, or merge.

### When to add a new data point

- You discover a concept that does not fit cleanly into any existing data point
- Multiple existing data points reference the same piece of information that has no official home
- A new business initiative creates a new category of knowledge (entering a new market, launching a new product line)
- People keep asking a question that no data point answers

### When to split an existing data point

- A single data point is being maintained by two people with different priorities
- The document is getting long enough that people skip reading it
- Stakeholders disagree about what belongs in it -- the disagreement often reveals two different topics hiding inside one container

### When to merge data points

- Two data points always change together -- if updating one always requires updating the other
- A data point has very thin content that does not justify standalone ownership
- Teams cannot remember which data point to update for a given change

### The growth pattern

The right *number* of data points scales with the complexity of the business — a solo consultancy might need 4, a multi-product company with several markets might need 25. What matters is that **every main domain is covered from day one**. Don't artificially cap the count to feel "minimal" — gaps in coverage hurt more than extra data points do.

What grows over time isn't usually the count — it's the depth and the relationship graph:

```
Phase 1 (initial):       Cover every main domain. Basic ownership on each.
                         Count = however many domains the business actually has.
Phase 2 (refinement):    Sharpen boundaries (EXCLUSIVELY_OWNS, STRICTLY_AVOIDS).
                         Split data points that turned out to be two topics.
Phase 3 (relationships): Define BUILDS_ON / REFERENCES / PROVIDES between data points.
Phase 4 (specialization): Add specialized data points as new initiatives create
                          genuinely new categories of knowledge.
```

**Do not rush refinement.** A complete-but-rough architecture beats a polished-but-partial one — you can sharpen boundaries on existing data points later, but missing domains stay invisible until something breaks.

---

### What goes IN a data point vs. stays in the source

A data point is the **canonical, durable** statement of a topic. Not every fact about that topic belongs inside it.

**Extract into the data point:**
- Stable concepts: mission, positioning, target audience definition, brand values, pricing *model*, decision frameworks, methodology, glossary terms
- Historical facts that won't change: founding date, original thesis, past pivots, signed agreements, key people decisions
- Critical rules and constraints: brand guidelines, policies, escalation rules
- Relationships: who owns what, which data point feeds which

**Leave in the source file (and reference it):**
- Volatile numbers that change often: current MRR, headcount, current campaign spend, this quarter's KPIs
- Time-series data: monthly metrics, transaction logs, invoice ledgers, performance reports
- Operational state that has its own system of record: CRM pipeline, accounting books, ticket queues
- Bulk verbatim artifacts: contracts as signed, call transcripts, exports — these go in `_collections/` with a manifest, not into a data point

**Rule of thumb:** if a fact will be wrong within 90 days, don't bake it into a data point — point at the source. If a fact reflects a decision or definition, extract it. The data point should still be true a year from now even if every number in the business has moved.

---

## Quick Reference

### Data Point Creation Checklist

- [ ] Name chosen (clear, specific, noun-based)
- [ ] DOMAIN written (1-3 sentences, specific enough to distinguish from neighbors)
- [ ] EXCLUSIVELY_OWNS defined (3-8 specific items)
- [ ] STRICTLY_AVOIDS defined (common areas of confusion, with redirects)
- [ ] Content written (concrete facts, organized into subsections)
- [ ] Context written (strategic interpretation, application guidance)
- [ ] Ownership Specification defined (DOMAIN + EXCLUSIVELY_OWNS at minimum)
- [ ] Template used (`docs/templates/context-data-point.md`)

### Common Pitfalls

| Pitfall | What happens | How to fix |
|---|---|---|
| Too vague | DOMAIN says "brand stuff" -- nobody knows what goes here | Be specific: "Core brand attributes, mission, vision, values" |
| Too broad | One data point covers everything about customers | Split into Target Audience, Pain Points, Desired Outcomes |
| No boundaries | Content creeps in from everywhere | Add STRICTLY_AVOIDS with redirects |
| No ownership spec | No clear boundaries, content drifts and overlaps | Define DOMAIN + EXCLUSIVELY_OWNS at minimum |
| Over-engineered | 20 items in EXCLUSIVELY_OWNS, relationships to everything | Start with 3-5 items, add more when the need is real |

---

**Start with what matters most. Refine as you go. Perfect is the enemy of useful.**
