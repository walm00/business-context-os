# Product Development Pattern

> How to scaffold context for product R&D — specs, architecture, engineering roadmap. Use when the repo is about **how a product is being built**, not how it's sold.

---

## Purpose & Fit

Use this pattern when the repo exists for the engineering and product teams building a shipping product: specifications, architecture diagrams, technical decision records, feature roadmaps, API designs. Signals: PRDs or spec docs, RFCs / ADRs, architecture diagrams, an engineering roadmap, feature tickets organized by area, no marketing content. The core question the context answers is "what are we building, how is it structured, and where is it going?"

Distinct from **product-service-pattern** (external-facing positioning) and **internal-tool-app-pattern** (internal UI used by employees). This pattern is for the **development artifacts** of a product, whether that product is external-facing or internal. If the repo contains both GTM and R&D content, split: use this pattern for the R&D repo and product-service for the GTM repo.

---

## Data Point Map

**Product Scope & Vision**
- Product overview — what the product is, the problem it solves, its current status (alpha / beta / GA)
- North-star vision — 12-24 month direction, the shape the product is trying to grow into
- Non-goals — explicitly what this product is not doing, so scope debates have an anchor
- Success metrics — product-level KPIs engineering is accountable to

**Architecture**
- System architecture — high-level components, data flow, major services
- Data model — primary entities, relationships, where they live
- Integration surfaces — public API, webhooks, SDK, internal service contracts
- Infrastructure — hosting, compute model, storage, critical third-party dependencies

**Features & Specs**
- Feature inventory — shipped features, their owners, their current health
- Active specs — work in flight with linked PRDs or design docs
- Deprecated / sunset features — what's on the way out and when
- Known limitations — the things the product cannot currently do, and the "why"

**Technical Decisions**
- Architecture decision records — one per significant decision, with the tradeoff captured
- Technology choices — chosen stacks and the reasoning (this is where "why Postgres over Mongo" lives)
- Engineering principles — testing standards, code review norms, release cadence rules
- Technical debt register — known debt items with rough cost / risk

**Team & Roadmap**
- Team structure — squads / pods, ownership boundaries, who owns which area
- Current roadmap — next 1-3 quarters, with commitment levels
- Dependencies & blockers — cross-team asks, vendor risks, open decisions
- Release process — how code ships, who signs off, rollback posture

---

## Relationships

- **Features & Specs** reference **Architecture** (features live on top of components) and **Product Scope & Vision** (each feature serves a piece of the vision).
- **Technical Decisions** reference **Architecture** (decisions shape the architecture) — ADRs are effectively versioned deltas to the architecture record.
- **Team & Roadmap** references **Features & Specs** (roadmap is sequenced features) and **Technical Decisions** (team structure often reflects architecture).
- **Non-goals** references **North-star vision** — they exist to preserve scope clarity against drift.
- **Known limitations** often has a cross-reference to a deprecated decision in **Technical Decisions** or a debt item.

Cross-references that tend to form: ADR ↔ Architecture (ADRs amend the architecture record); Feature ↔ Team ownership (every feature has a team); Roadmap ↔ Dependencies (roadmap items block on dependencies).

---

## Voice & Tone

Precise and technical. Spec-like. Diagrams and bullet lists are fine here — unlike the product-service pattern, visual structure helps comprehension more than narrative does. Decisions are captured with the **tradeoff** explicit, not just the outcome. Timestamps matter: "as of 2026-Q2" beats "recently." Candor about limitations and debt is the norm — hiding them in the context doc breaks the doc's utility later.

---

## Template Mapping

- **Primary scaffold:** partial fit with `docs/_bcos-framework/templates/table-of-context.md` — the structure works but the prompts lean business-y. A product-development variant would sharpen sections like "Who We Serve" (really: which users / API consumers) and "What Makes Us Different" (really: architectural bets and principles).
- **Current state:** partial fit with `docs/_bcos-framework/templates/current-state.md`.

**TODO (follow-up):** create `table-of-context.product-development.md` and `current-state.product-development.md` variants. Cluster hints for the new variants: Product Scope & Vision / Architecture / Features & Specs / Technical Decisions / Team & Roadmap. Until variants exist, reuse the product-service templates and rename sections to match the cluster map above.
