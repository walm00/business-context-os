# Product / Service Pattern

> How to scaffold context for an external-facing product, service, company, or consulting practice. This is the default profile — use it when the repo is about **what a business is and sells to the outside world**.

---

## Purpose & Fit

Use this pattern when the repo describes an external-facing business entity — SaaS product, agency, consulting practice, DTC brand, two-sided marketplace. Signals: a marketing site, pricing page, customer case studies, positioning docs, brand guidelines, GTM plans. The core question the context answers is "who are we, to whom, and what do we sell?"

Do **not** use this pattern for: internal tools (see `internal-tool-app-pattern.md` / `internal-tool-automation-pattern.md`), standalone engineering R&D context (see `product-development-pattern.md`), or scoped client engagements (see `client-project-pattern.md`).

---

## Data Point Map

Organized by cluster. Each bullet is a candidate data point — capture the ones that have real content, skip the ones that don't.

**Business Identity**
- Company overview — legal entity, founding story, stage, headcount, location
- Mission & vision — what we're trying to change in the world
- Leadership & ownership — founders, key executives, ownership structure
- Current phase — startup / growth / mature / pivoting, and the focus it implies

**Offerings & Positioning**
- Core offering — what the product or service actually is, in one paragraph
- Value proposition — the outcome customers buy, not the features
- Competitive positioning — category, frame, and the stance we take
- Differentiators — the 2-4 structural advantages that are hard to copy
- Pricing & packaging — tiers, price points, monetization logic

**Market & Customers**
- Target ICP — primary customer segment(s), firmographic + behavioral detail
- Customer insights — jobs-to-be-done, pain points, buying triggers
- Market context — category size, trends, regulatory or technical forces
- Competitive landscape — named competitors, how we win vs. lose

**Brand & Voice**
- Brand identity — personality, visual system cues, what the brand stands for
- Voice & tone — how we sound in copy, email, sales conversations
- Messaging framework — primary message, supporting pillars, proof points

**GTM Overview**
- Acquisition motion — inbound / outbound / PLG / partner-led, summary only
- Sales & onboarding flow — how a lead becomes a customer
- Retention & expansion — how customers grow with us over time

---

## Relationships

- **Value proposition** references **target ICP** (who the outcome is for) and **differentiators** (why we deliver it best).
- **Competitive positioning** references **market context** (the frame) and **differentiators** (our claim within it).
- **Messaging framework** pulls from **value proposition** and **voice & tone** — messaging is the output, not the source.
- **Pricing & packaging** references **target ICP** (what each segment will pay) and **core offering** (what's inside each tier).
- **GTM overview** references the whole **Market & Customers** cluster — it's the action layer on top.
- **Current phase** shapes which data points matter most: early-stage repos lean heavily on Business Identity + Offerings; mature ones lean on GTM + Brand.

Cross-references that tend to form: Customer Insights ↔ Messaging Framework (one informs the other); Differentiators ↔ Competitive Positioning (tightly coupled); Brand Identity ↔ Voice & Tone (parent / child).

---

## Voice & Tone

Narrative and strategic. Content here reads like the inside of a leadership deck, not a product spec. Full sentences, confident claims, honest about constraints. Marketing polish is optional — internal context benefits from being a little blunter than the public site. Avoid feature-listing; the product is not the point, the customer outcome is. When the business is multi-market or multi-product, prefer clarity over completeness — one crisp frame beats four hedged ones.

---

## Template Mapping

- **Primary scaffold:** `docs/_bcos-framework/templates/table-of-context.md`
- **Current state:** `docs/_bcos-framework/templates/current-state.md`

Both templates already exist and fit this profile without modification. This is the default / reference shape that the other patterns diverge from.
