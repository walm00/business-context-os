# Client Project Pattern

> How to scaffold context for a scoped agency or consulting engagement. Use when the repo is about **one client, one engagement, with a defined delivery arc**.

---

## Purpose & Fit

Use this pattern when the repo is the working context for a specific client engagement — a scoped piece of agency or consulting work with a defined beginning, middle, and handoff. Signals: a client name in the repo name, an SOW or creative brief in `_inbox/`, stakeholder lists, milestone calendars, handoff plans. The core question the context answers is "what did we agree to do for this client, how is it going, and what happens when we finish?"

Scope rule: **ONE client, ONE engagement.** A second project with the same client spins up a new repo. Distinct from **product-service-pattern** (the agency's own brand and positioning) and **operational-pattern** (ongoing internal ops) — client-project is always finite and externally owned in outcome.

---

## Data Point Map

**Engagement Context**
- Client overview — who the client is, what business they're in, relevant history
- Engagement origin — how the work was won, what problem triggered it
- Stakeholder map — client-side people (sponsor, approver, day-to-day), agency-side team
- Business goals — the client's goals the engagement is in service of
- Success criteria — what "done well" looks like by the client's measure

**Scope & Delivery**
- Scope statement — in-scope and out-of-scope, with explicit exclusions
- Deliverables — the concrete artifacts we're producing
- Timeline & milestones — phases, approval gates, launch date
- Budget & commercials — fee structure, payment schedule, change-order process
- Risk register — known risks, mitigation approach, open decisions
- Status — current state of the engagement relative to plan

**Architecture & Handoff**
- Technical stack — systems chosen, hosting, third-party services, credentials ownership
- Integrations — what the deliverable plugs into on the client's side
- Handoff model — what the client takes over, what we continue to do post-launch
- Training & documentation — what we'll leave behind, who we'll train, how
- Maintenance terms — retainer vs. ad-hoc, SLAs if any, renewal decision points
- Communication cadence — meeting schedule, async channels, approval rhythms

---

## Relationships

- **Success criteria** references **Business goals** (criteria are how goals are measured) and shape **Scope & Delivery** (what we deliver must meet the criteria).
- **Deliverables** reference **Scope statement** (each deliverable lives inside scope) and **Timeline & milestones** (each deliverable hits a milestone).
- **Handoff model** references **Technical stack** (handoff covers the stack we chose) and **Maintenance terms** (handoff defines what we keep vs. hand over).
- **Risk register** cross-references **Scope**, **Timeline**, and **Integrations** — risks almost always land on one of those surfaces.
- **Stakeholder map** references **Communication cadence** (different stakeholders on different rhythms) and **Approval gates** inside Timeline (approver per gate).

Cross-references that tend to form: Deliverable ↔ Milestone; Stakeholder ↔ Approval gate; Risk ↔ Mitigation plan; Integration ↔ Credential owner; Training module ↔ Handoff item.

---

## Voice & Tone

Professional and accountable, written for two audiences at once — the internal team and the client. Scope and commercials are precise to the word: exact dates, exact dollar amounts, exact exclusions. Risk and status sections benefit from being blunt internally and carefully framed externally — the internal doc can say "timeline is slipping because stakeholder approvals are running 5 days late" while the client-facing update says the same thing more diplomatically. Expect the document to be re-read in a dispute: write it so the facts hold up when read months later.

---

## Template Mapping

- **Primary scaffold:** `docs/_bcos-framework/templates/table-of-context.client-project.md`
- **Current state:** `docs/_bcos-framework/templates/current-state.client-project.md`

Both templates exist and match this profile directly — the client-project table of context already covers Client Context, Scope & Deliverables, Architecture & Tech Stack, Handoff & Maintenance, Constraints & Open Questions, and Communication Cadence. Use as-is.
