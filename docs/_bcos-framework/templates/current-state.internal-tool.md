# Current State (Internal Tool)

> What's happening with the tool RIGHT NOW. Usage, reliability, recent changes, active issues, next priorities.
> This is the operational layer — the weather, not the climate.
>
> **Works for apps, services, CLIs, scripts, pipelines, and libraries.** Skip sections that don't apply to your shape.
>
> **Update cadence:** Weekly (quick refresh) + after incidents, releases, ownership changes.
> **Owner:** <!-- The person whose tool this reflects — usually the tech lead or primary maintainer -->

---

## My Role

<!-- Your role relative to this tool. Helps Claude calibrate advice. -->
<!-- Example: "Tech lead for Pulse. Responsible for roadmap, ownership, and incident response. Day-to-day: mostly reviewing PRs and triaging. Not involved in: ad-hoc SQL query design, analyst workflows." -->

## This Week's Focus

<!-- 2-5 priorities for the tool this week. -->
<!-- Example:
- Ship cohort-retention query fix (PLAT-1842)
- Onboard two new analysts to saved-query patterns
- Review capacity plan ahead of Q2 traffic
- Pair with SRE on auth-refresh flake (PLAT-1901)
-->

## Usage Snapshot

<!-- Rough pulse on who's using the tool and how. -->
<!-- Example:
- WAU: 68 (up from 52 last month — exec dashboard adoption)
- Heaviest users: analyst-team, 30% of total queries
- New trend: CS team running per-account usage lookups more often
- Notable drop: PM dashboards used less on Mondays since weekly review moved to Wednesdays
-->

## Reliability Snapshot

<!-- Uptime, incident count, p95s, anything worth flagging. Don't copy metrics — summarize. -->
<!-- Example:
- No SEV-1s this week
- One SEV-3 Tuesday (auth refresh flake, 18 min partial degradation)
- p95 query latency: 1.8s (target: <2s)
- Pipeline failures: 2 auto-retries, both succeeded
-->

## Recent Changes

<!-- What shipped, what changed in the tool or its environment. -->
<!-- Example:
- Shipped: saved-query tagging (2026-04-15)
- Shipped: new exec dashboard (2026-04-12)
- Dependency upgrade: Next.js 14.2 → 14.3 (2026-04-09)
- Ownership: CS team now owns the per-account-usage feature end-to-end
-->

## Active Issues

<!-- Known issues currently impacting users or nearing deadline. -->
<!-- Example:
- OPEN: Cohort retention timeout on 90-day windows (PLAT-1842, in review)
- OPEN: Auth refresh flake during SSO re-key (PLAT-1901, needs SRE pair)
- DECIDED: CSV export of large results is WONTFIX — docs updated to point to notebook workflow
-->

## Coming Up (Next 2-4 Weeks)

<!-- What's on the horizon — planned releases, deprecations, capacity work, ownership changes. -->
<!-- Example:
- Q2 capacity plan review: April 30
- Deprecation: legacy `/v1/metrics` endpoint, removing May 15
- New consumer onboarding: Finance team wants to pull revenue cohorts
- On-call handoff: rotation expands to include new hire week of May 6
-->

## What Changed Recently (for data-point drift)

<!-- Changes that existing data points may not have caught up with yet. This is the most valuable section for maintenance. -->
<!-- Example:
- Pipeline now writes to a second downstream (Finance warehouse) — integrations data point needs update
- PM role grouping changed after re-org — users-and-roles needs a refresh
- Backend split into two services in March — architecture-overview still shows the monolith
-->

---

## How to Use This File

- **Claude reads this alongside `table-of-context.internal-tool.md`** for the full picture (stable + current)
- **Weekly refresh:** 5 minutes updating priorities, usage, reliability, and what changed
- **Scheduled health checks** compare this against data-point last-updated dates to find drift
- **Context-ingest** may update "What Changed Recently" when integrating new observations (incident reports, user feedback, release notes)

This file is intentionally informal. Don't overthink formatting. The value is in keeping it current, not making it pretty.
