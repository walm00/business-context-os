# GTM Pattern

> How to scaffold context for go-to-market: pricing, positioning, sales enablement, partnerships. Use when the repo is about **how a business wins customers and expands revenue**.

---

## Purpose & Fit

Use this pattern when the repo is focused on the commercial motion: sales plays, pricing strategy, positioning docs, sales enablement collateral, partner programs, channel strategy. Signals: sales playbooks, discovery / demo scripts, competitive battlecards, pricing models, deal review notes, partner agreements, enablement materials. The core question the context answers is "how do we turn the market into revenue, and what arms the team to do it?"

Distinct from **product-service-pattern** (which owns the strategic identity and positioning this pattern operationalizes) and **marketing-pattern** (brand expression at the content layer). In practice, product-service provides the strategic core; GTM turns it into a revenue motion; marketing turns it into stories told at scale. These three often overlap — use multiple patterns if the repo spans them.

---

## Data Point Map

**Target ICP**
- Primary ICP — the segment the team is actively selling into, with firmographic + behavioral detail
- Secondary ICP(s) — segments being explored or expanded to
- Buyer personas — the roles in the buying committee and what each cares about
- Disqualification criteria — who we explicitly don't sell to and why

**Positioning & Messaging**
- Sales positioning — the one-line frame the team uses to open conversations
- Competitive battlecards — one per major competitor with win / loss themes
- Proof points — case studies, references, metrics that prove claims
- Objection handling — common objections and tested responses

**Pricing & Packaging**
- Pricing model — SaaS per-seat, usage-based, fixed-fee, etc., with rationale
- Packaging — tiers or packages, what's in each, which segment each targets
- Discounting guidelines — approved discount ranges, approval thresholds
- Contract structure — standard terms, negotiable terms, legal guardrails

**Sales Motion & Enablement**
- Sales process stages — stages from lead to closed-won, with exit criteria
- Discovery framework — the questions reps run to qualify and diagnose
- Demo & proof-of-concept playbook — what a good demo / POC looks like
- Enablement inventory — training modules, onboarding path, ongoing certs
- Tooling — CRM, sales engagement platform, conversation intelligence, where deal data lives

**Partner & Channel**
- Partner inventory — active partners, their role (referral / reseller / integration)
- Partner motions — how each partner type is run, gated by what
- Channel economics — partner margins, commercial terms, P&L contribution
- Partner enablement — partner-facing training, collateral, review cadence

---

## Relationships

- **Target ICP** is upstream of almost everything — **Positioning**, **Packaging**, **Sales Motion**, and **Partner & Channel** all reference it.
- **Pricing & Packaging** references **Target ICP** (each tier targets a segment) and **Sales Motion** (discounting lives inside the sales process).
- **Competitive battlecards** reference **Sales positioning** and **Objection handling** — battlecards are positioning applied to a specific rival.
- **Enablement inventory** references **Discovery framework**, **Demo playbook**, and **Battlecards** — enablement is the thing that teaches reps to use the rest.
- **Partner motions** reference **Sales process stages** — partner deals flow through a variant of the direct pipeline.

Cross-references that tend to form: ICP ↔ Tier; Competitor ↔ Battlecard; Objection ↔ Proof point; Sales stage ↔ Enablement module; Partner ↔ Channel economics row.

---

## Voice & Tone

Concrete and confrontable. Sales enablement reads best when it's specific enough to be used in a live call: exact words, exact numbers, exact objections. Vagueness in GTM context is worse than wrong content — reps either use it or don't, and vague content doesn't get used. Keep battlecards honest about the competitor's real strengths; reps lose trust in battlecards that oversell. Pricing docs benefit from tables; process docs benefit from numbered stages with crisp exit criteria.

---

## Template Mapping

- **Primary scaffold:** partial fit with `docs/_bcos-framework/templates/table-of-context.md` — sections like "Who We Serve", "What Makes Us Different", "Business Model" overlap with GTM but don't go deep enough.
- **Current state:** partial fit with `docs/_bcos-framework/templates/current-state.md`.

**TODO (follow-up):** create `table-of-context.gtm.md` and `current-state.gtm.md`. Cluster hints: Target ICP / Positioning & Messaging / Pricing & Packaging / Sales Motion & Enablement / Partner & Channel. Until variants exist, reuse the product-service templates; expect heavy overlap with a sibling product-service repo and explicitly link to it so positioning is inherited rather than duplicated.
