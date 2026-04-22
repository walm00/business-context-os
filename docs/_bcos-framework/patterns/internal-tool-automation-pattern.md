# Internal Tool — Automation Pattern

> How to scaffold context for an internal automation — scripts, pipelines, CLIs, cron jobs, services without a UI. Use when the repo is about **a running system with no human-facing interface**.

---

## Purpose & Fit

Use this pattern when the repo is a backend automation: ETL pipelines, scheduled jobs, CLIs, internal services, data processors, background workers. Signals: no frontend code, a Dockerfile and cron / Airflow / systemd config, scripts under `bin/` or `scripts/`, logs and metrics as the primary observability surface, human "users" limited to those who trigger or own it. The core question the context answers is "what does this pipeline do, when does it run, what depends on it, and who owns it?"

Distinct from **internal-tool-app-pattern** (UI + users) and **operational-pattern** (runbooks across multiple systems). This pattern is for a **single automated system**. If the repo is one automation among many that a team runs, also consider the operational-pattern for the cross-system view.

---

## Data Point Map

**Pipeline Identity**
- Pipeline overview — what it does in one paragraph, and what kind of automation it is (ETL / cron / CLI / event-driven service / batch job)
- Purpose — the outcome it produces for the business, not the mechanics
- Ownership — owning team, primary maintainer, escalation contact
- Lifecycle stage — in-build / active / stable / deprecating, and what that implies

**Behavior & Ownership**
- Trigger model — schedule / event / manual / continuous, with the specifics (cron expression, event topic, etc.)
- Inputs — data sources, upstream systems, expected input shape
- Outputs — what the pipeline writes, where, and which downstream systems consume it
- Behavior & stages — the main processing steps in order, with what each stage does
- Failure modes — what "broken" looks like, common causes, blast radius
- Change ownership — who can modify the pipeline, who reviews, what gates changes

**Architecture & Operations**
- Tech stack — language, orchestrator, key libraries, where it runs
- Dependencies — upstream services, secrets, credentials, third-party APIs
- Deployment model — how it gets to production, rollback posture
- Monitoring — metrics, logs, alerts, who gets paged
- SLAs & runtime expectations — "should complete in under N minutes", data freshness targets
- Known issues & debt — current limitations, tracked incidents, maintenance backlog
- Cost model — cloud cost, API quota usage, data volume trends

---

## Relationships

- **Inputs** and **Outputs** together define the **blast radius** — downstream consumers live in Outputs, upstream risks live in Inputs.
- **Trigger model** references **Dependencies** (triggers often depend on upstream events or schedules) and **SLAs** (trigger cadence defines freshness).
- **Failure modes** references **Monitoring** (each failure mode should have an alert) and **Dependencies** (most failures trace to a dependency).
- **Behavior & stages** references **Tech stack** (stages are implemented in specific tools) and **Outputs** (final stage writes the output).
- **Ownership** references **Change ownership** and **Monitoring** — usually the same team, but not always.

Cross-references that tend to form: Input ↔ Upstream dependency; Output ↔ Downstream consumer; Failure mode ↔ Alert + Runbook step; Stage ↔ Metric that measures it.

---

## Voice & Tone

Terse and operational. Pipelines are described more like infrastructure than product — declarative statements, no storytelling. Exact values matter: cron expressions literal, not "every morning"; data volumes with units; freshness SLAs with numbers. Where a human decision is encoded, capture the decision with a one-line reason. Diagrams of the data flow are more useful here than prose.

---

## Template Mapping

- **Primary scaffold:** `docs/_bcos-framework/templates/table-of-context.internal-tool.md`
- **Current state:** `docs/_bcos-framework/templates/current-state.internal-tool.md`

Shared with the internal-tool app pattern — different cluster emphasis. Use the "Pipeline / ETL" and "CLI / Script" columns in the template's "Section Applicability" table: "Who uses it" is about triggers and owners rather than human users, "Upstream & downstream" becomes central, and the "UX surface area" section is skipped.
