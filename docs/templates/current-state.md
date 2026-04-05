# Current State

> What's happening RIGHT NOW. Priorities, recent changes, active decisions, upcoming events.
> This is the operational layer — the weather, not the climate.
>
> **Update cadence:** Weekly (quick refresh) + after significant events.
> **Owner:** <!-- The person whose priorities this reflects — usually the primary user -->

---

## Who I Am

<!-- Your role, responsibilities, what you're accountable for. Helps Claude calibrate advice. -->
<!-- Example: "CEO / Co-founder. Responsible for strategy, fundraising, and key partnerships. Day-to-day: product direction + hiring. Not involved in: engineering decisions, marketing execution." -->

## This Week's Focus

<!-- 2-5 priorities for the current week. Be specific. -->
<!-- Example:
- Finalize Series A term sheet (deadline: Thursday)
- Review new market entry plan for US
- Interview 2 senior engineering candidates
- Prepare board update deck
-->

## Last Week's Highlights

<!-- What happened that matters. Decisions made, milestones hit, surprises. -->
<!-- Example:
- Closed partnership with [Company X] — affects competitive positioning
- Decided to pause hiring for marketing role — budget reallocation
- Customer churn spike in SMB segment — need to investigate
-->

## Coming Up (Next 2-4 Weeks)

<!-- What's on the horizon. Events, deadlines, decisions approaching. -->
<!-- Example:
- Board meeting: April 15
- US market launch target: May 1
- Quarterly pricing review: end of April
- New product feature release: April 20
-->

## Active Decisions

<!-- Things in flux. Decisions being made that affect context. Helps Claude know what's uncertain. -->
<!-- Example:
- OPEN: Should we raise pricing for new customers? (deciding by April 10)
- OPEN: Hire a VP Sales or promote from within? (interviewing both options)
- DECIDED: Moving to enterprise-first positioning (announced March 28)
- DECIDED: Sunsetting free tier (effective May 1)
-->

## What Changed Recently

<!-- Business changes that context documents may not have caught up with yet. -->
<!-- This is the most valuable section for maintenance — it tells daydream and audit what to check. -->
<!-- Example:
- Competitor Y was acquired by Z (March 25) — competitive-positioning needs update
- New customer segment emerging: fintech ops teams — not in target-audience yet
- Rebranded from "ProjectFlow" to "FlowOps" — brand-identity updated, messaging not yet
-->

---

## Connections to Context Architecture

When you update this file, check if any changes should propagate to data points:

| If this changed... | Check this data point... |
|--------------------|-----------------------|
| Market position or competitive landscape | competitive-positioning |
| Customer segment or audience shift | target-audience |
| Product direction or features | value-proposition, product-overview |
| Pricing or business model | pricing-model, business-model |
| Brand, name, identity | brand-identity, messaging-framework |
| Team structure or roles | org-context, process docs |

---

## How to Use This File

- **Claude reads this alongside table-of-context.md** for the full picture (stable + current)
- **Weekly refresh:** Spend 5 minutes updating priorities, highlights, and what changed
- **Daydream skill** uses "What Changed Recently" to identify data points that need review
- **Scheduled health checks** compare this against data point last-updated dates to find drift
- **Context-ingest** may update "What Changed Recently" when integrating new information

This file is intentionally informal. Don't overthink formatting. The value is in keeping it current, not making it pretty.
