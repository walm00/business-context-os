# Operational Pattern

> How to scaffold context for ops runbooks, processes, infra documentation, and SRE-flavored working knowledge. Use when the repo is about **keeping multiple systems and processes running reliably**.

---

## Purpose & Fit

Use this pattern when the repo is an operational knowledge base: runbooks, on-call playbooks, infrastructure docs, change management processes, incident post-mortems, SLIs and SLOs. Signals: a `runbooks/` folder, on-call schedules, incident archives, infrastructure-as-code docs, SRE-style process docs, references to pagers and escalation paths. The core question the context answers is "when something breaks or changes, what does the team do?"

Distinct from **internal-tool-app-pattern** and **internal-tool-automation-pattern**, which each document **one system**. This pattern documents a **team's operational knowledge across many systems** — the cross-cutting layer. If a single system's runbook needs to live somewhere, it can live in the tool-specific repo; the cross-system posture lives here.

---

## Data Point Map

**System Map**
- System inventory — the list of systems this team operates, with a one-line purpose each
- Ownership matrix — which team / pod owns which system, primary + backup
- Criticality tiers — tier 1 / 2 / 3 classification with what each tier implies
- Architecture landscape — how the systems connect (diagrams or prose)

**Runbooks & Procedures**
- Runbook inventory — index of runbooks with purpose and last-verified date
- Standard operating procedures — recurring operational tasks (rotations, rollouts, cleanups)
- Environment & access — how to get access to each system, permission request flow
- Configuration management — where config lives, how it's versioned, how it's rolled out

**On-Call & Escalation**
- On-call rotation — the rotation model, handoff rules, coverage expectations
- Escalation paths — who escalates to whom, by severity, with response-time targets
- Paging rules — what pages, what doesn't, how pager fatigue is managed
- On-call enablement — onboarding for a new on-call, the required shadowing / training

**SLIs & Incidents**
- Service level indicators — per-system SLIs, current SLO targets, error budgets
- Monitoring & observability — dashboards, alerting tools, log / trace destinations
- Incident history — recent incidents with blast radius and resolution
- Post-mortem register — post-mortems with action items and their status
- Recurring-incident patterns — failure modes that show up repeatedly

**Change Management**
- Change process — how changes get planned, reviewed, approved, deployed
- Change windows — allowed / blocked windows, freeze periods, release trains
- Rollback posture — what rolling back looks like per system
- Communication protocols — customer / stakeholder notifications, status page rules

---

## Relationships

- **System inventory** is the spine — **Runbooks**, **On-call**, **SLIs**, and **Change process** all reference systems by name.
- **Ownership matrix** references **On-call rotation** (rotation is per-system) and **Escalation paths** (escalation is per-owner).
- **Incident history** references **System inventory** (which system broke) and drives **Post-mortem register** entries.
- **Recurring-incident patterns** references **Post-mortems** (the pattern is detected across them) and **SLIs** (patterns show up as SLO misses).
- **Change windows** references **Criticality tiers** — tier 1 systems have tighter windows.

Cross-references that tend to form: System ↔ Runbook; System ↔ SLI; Incident ↔ Post-mortem ↔ Action item; On-call rotation ↔ Escalation path; Change ↔ Communication protocol.

---

## Voice & Tone

Precise and boring, on purpose. Runbooks should read like a flight checklist — steps numbered, commands literal, expected outputs stated. Prose is for context and rationale; procedures are for steps. Dates and owners are attached to everything that ages (runbooks, SLO targets, rotations). Post-mortems are blameless but specific — "the monitor didn't fire because X config was wrong" is more useful than "monitoring gaps". Avoid jargon shortcuts in runbooks; the page will be read at 3am by someone on their first on-call shift.

---

## Template Mapping

- **Primary scaffold:** partial fit with `docs/_bcos-framework/templates/current-state.internal-tool.md` — it handles per-system current state well but doesn't model the cross-system operational layer.
- **Current state:** partial fit as above.

**TODO (follow-up):** create `table-of-context.operational.md` and `current-state.operational.md`. Cluster hints: System Map / Runbooks & Procedures / On-Call & Escalation / SLIs & Incidents / Change Management. A major template need here is support for **per-system rows** (the system inventory) as structured data rather than prose — until a variant exists, reuse `table-of-context.internal-tool.md` and treat the whole repo's scope as a synthetic "tool" whose sub-systems live inside.
