# Table of Context (Internal Tool)

> The essential picture of what this internal tool IS. Read this first before any tool-related context work.
> This is the synthesized truth — derived from your data points, not duplicating them.
>
> **Works for apps, services, CLIs, scripts, pipelines, and libraries.** Fill the sections that apply to your tool shape and skip the rest. The "Section applicability" table below is a quick guide.
>
> **Update cadence:** Monthly, or when something fundamental changes (rewrite, new major dependency, ownership handoff, deprecation).
> **Owner:** <!-- The person with final say on "what is this tool" — usually the tech lead or primary maintainer -->

---

## Section Applicability

Use this as a quick guide. ✓ = usually matters, ○ = sometimes useful, — = typically skip.

| Section | App (UI + users) | Service (backend, no UI) | CLI / Script | Pipeline / ETL | Library |
|---|:-:|:-:|:-:|:-:|:-:|
| What it is | ✓ | ✓ | ✓ | ✓ | ✓ |
| What it does | ✓ | ✓ | ✓ | ✓ | ✓ |
| Who uses it | ✓ | ○ (consumers) | ✓ | ○ (triggers/owners) | ○ (importers) |
| How it works | ✓ | ✓ | ○ | ✓ | ✓ |
| Upstream & downstream | ✓ | ✓ | ○ | ✓ | ✓ |
| Operational model | ✓ | ✓ | ○ | ✓ | — |
| Current state / Known issues | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## What It Is

<!-- 2-3 sentences. One-line description, type of tool, status. -->
<!-- Example (app): "Pulse is an internal product-analytics dashboard used by PMs, data analysts, and execs. Web app built on Next.js + Postgres, deployed to our internal cluster. In active use since 2024; ownership moved from Data Eng to the Product Platform team in Q1 2026." -->
<!-- Example (pipeline): "Driftlog is an Airflow-based ETL pipeline that ingests service logs from our production clusters into the Snowflake data warehouse. Runs every 15 minutes. Owned by Data Eng." -->

## What It Does

<!-- 3-6 bullets. Core capability, key workflows it supports. Not feature lists — the things people actually reach for it to do. -->
<!-- Example (app):
- "Track feature adoption across product areas — who's using what, how often"
- "Cohort retention and funnel analysis for PM-defined user segments"
- "Exec dashboards for weekly business review (WAU, MAU, top features)"
- "Ad-hoc SQL via saved-query interface for analysts who don't want to use the notebook" -->

## Who Uses It

<!-- Internal users, roles, usage patterns. Include rough volumes if known. For services/libraries, list the SYSTEMS that consume the tool instead of people. -->
<!-- Example (app):
- **PMs (~40)** — daily-weekly usage, mostly adoption dashboards
- **Data analysts (~12)** — daily usage, heavy SQL
- **Execs (~15)** — weekly check-ins on summary dashboards
- **Customer Success (~25)** — ad-hoc, looking up individual account usage -->

## How It Works

<!-- High-level architecture and main components. Not a full design doc — just enough that a new maintainer knows the map. -->
<!-- Example (app): "Next.js frontend → API Gateway → Python analytics service → read replicas of the product DB + Snowflake. Auth through internal SSO. Saved queries stored in the analytics service's own Postgres." -->

## Upstream & Downstream

<!-- Dependencies, integrations, data sources, consumers. What this tool reads from, what reads from it. -->
<!-- Example (pipeline):
- **Upstream:** production service logs (Kafka topics: `svc.billing.*`, `svc.auth.*`), Snowflake source schemas
- **Downstream:** `analytics.events` table in Snowflake (consumed by Pulse, Looker, and three team-owned notebooks)
- **Blast radius:** if this breaks, exec dashboards go stale within 2 hours -->

## Operational Model

<!-- How it's deployed, monitored, maintained, on-call. This is where "known good running state" lives. -->
<!-- Example:
- **Deployment:** GitHub Actions → internal cluster; blue/green with auto-rollback
- **Monitoring:** Datadog dashboard `internal-tools/pulse`; PagerDuty service `pulse-prod`
- **On-call:** Product Platform team, standard rotation
- **Maintenance windows:** Tuesdays 10-11pm UTC for schema migrations -->

## Current State / Known Issues

<!-- What's working, what's rough. Date the observations so they age gracefully. -->
<!-- Example:
- ✅ Dashboards load <2s for queries under 30-day window (as of 2026-03)
- ⚠️ Cohort retention queries on 90+ day windows time out intermittently (known; tracked in PLAT-1842)
- ⚠️ Saved-query export to CSV breaks for results >100k rows (workaround: use notebook)
- 🔴 Auth refresh is flaky when SSO re-keys — users have to reload (tracked in PLAT-1901) -->

---

## Context Architecture

<!-- Auto-populated summary. How many data points, which clusters, when last audited. -->

**Data points:** <!-- e.g., "7 active, 1 draft" -->
**Clusters:** <!-- e.g., "Tool Identity (1), Users & Capabilities (2), Architecture & Operations (3)" -->
**Last audit:** <!-- date -->
**Last significant change:** <!-- e.g., "2026-02-18: Documented handoff from Data Eng to Product Platform" -->

---

## How to Use This File

- **Claude reads this at session start** for any tool-context-related work
- **Scheduled maintenance** uses this as input to detect drift — e.g. "operational model section says on-call is Team X, but last 5 incidents were paged to Team Y"
- **Context-onboarding** generates an initial draft during first setup
- **You update it** when something fundamental changes about the tool — not every sprint, only when the map shifts

If a section feels wrong, update the underlying data point first (that's the source of truth), then update this synthesis to match.
