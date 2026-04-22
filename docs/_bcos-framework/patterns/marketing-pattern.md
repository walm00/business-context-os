# Marketing Pattern

> How to scaffold context for a marketing site, content strategy, or campaign program. Use when the repo is about **how a brand goes to market at the content and channel layer**.

---

## Purpose & Fit

Use this pattern when the repo is about marketing execution: the marketing site, content calendar, campaign briefs, channel plans, editorial guidelines, SEO strategy. Signals: content pieces (blog posts, landing pages, emails), editorial calendars, channel performance dashboards, creative briefs, brand voice docs lived-in daily rather than aspirationally. The core question the context answers is "what do we say, where do we say it, and how do we know it's working?"

Distinct from **product-service-pattern** (which owns the strategic positioning and brand identity this pattern implements) and **gtm-pattern** (sales motion, pricing, partner strategy — the non-marketing half of go-to-market). In a larger org, marketing context is a **child** of product-service context — it inherits positioning and voice, and operationalizes them.

---

## Data Point Map

**Brand Adjacency**
- Brand & voice reference — short summary and a link to the source of truth (usually the product-service repo's brand data points)
- Positioning inheritance — the positioning this marketing work flows from
- Audience priorities — which segments marketing is actively engaging right now (a subset of the full ICP)

**Campaigns & Content**
- Active campaigns — current campaign briefs with goals, audiences, creative angles
- Content calendar — what's scheduled, who owns it, which channels
- Content pillars — the 3-6 recurring themes that content maps to
- Content inventory — major existing assets, where they live, their state
- Campaign post-mortems — what worked, what didn't, learnings captured

**Channels & Performance**
- Channel inventory — owned / earned / paid, with each channel's role in the mix
- Channel playbooks — what "good" looks like per channel (cadence, formats, norms)
- Performance dashboards — key metrics per channel, where they're tracked
- Attribution model — how marketing impact is measured end-to-end
- Budget & spend — channel-level budget, pacing, current burn

**Editorial Voice**
- Voice & tone in practice — how the brand voice translates to marketing copy specifically
- Copy standards — headline patterns, CTA phrasing, SEO title rules
- Visual standards — image treatments, video norms, template usage
- Approval & review process — who signs off, what triggers legal review, turnaround times

---

## Relationships

- **Brand Adjacency** cluster references the product-service repo — marketing context **inherits** rather than duplicates brand identity and positioning.
- **Active campaigns** references **Content calendar** (campaigns consume calendar slots), **Channels** (campaigns run through channels), and **Audience priorities** (campaigns target specific segments).
- **Content pillars** references **Audience priorities** — pillars exist because segments have distinct interests.
- **Channel playbooks** references **Editorial Voice** (how we sound on this channel) and **Performance dashboards** (how we measure it).
- **Campaign post-mortems** feed future **Active campaigns** and **Channel playbooks** — this is where learning gets consolidated.

Cross-references that tend to form: Campaign ↔ Channel; Content piece ↔ Content pillar; Channel ↔ Performance dashboard; Post-mortem ↔ Campaign.

---

## Voice & Tone

Mixed register. The **meta content** (briefs, playbooks, post-mortems) is operational and clipped. The **actual marketing content** referenced inside the context is whatever voice the brand has — upbeat, literary, technical, whatever. The pattern doc captures both: operational guidance on one side, clear pointers to the voice source on the other. Calendars and trackers are best kept as tables or structured lists, not prose. Post-mortems benefit from candor — "this campaign underperformed because X" beats "we saw mixed results."

---

## Template Mapping

- **Primary scaffold:** partial fit with `docs/_bcos-framework/templates/table-of-context.md` — the structure works but the business-identity-heavy prompts don't fit marketing's operational focus.
- **Current state:** partial fit with `docs/_bcos-framework/templates/current-state.md`.

**TODO (follow-up):** create `table-of-context.marketing.md` and `current-state.marketing.md`. Cluster hints: Brand Adjacency / Campaigns & Content / Channels & Performance / Editorial Voice. Until variants exist, reuse the product-service templates and rename sections to match the cluster map above; explicitly link to a parent product-service repo if one exists so brand inheritance is visible.
