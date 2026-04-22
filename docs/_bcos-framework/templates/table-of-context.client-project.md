# Table of Context (Client Project)

> The essential picture of a specific client engagement. Read this first before any project-context work.
> This is the synthesized truth — derived from your data points, not duplicating them.
>
> **Scope:** ONE client engagement, ONE deliverable arc. If you're working with this client on a second engagement, spin up a new bcos.
>
> **Update cadence:** Weekly during active engagement + at every major milestone (kickoff, design sign-off, launch, handoff).
> **Owner:** <!-- The person who has final say on "what is this engagement" — usually the account lead or project lead -->

---

## Client Context

<!-- 2-3 sentences. Who the client is, what business they're in, why they hired us. -->
<!-- Example: "Hearth Bakeries is a regional bakery chain with 12 locations across the Pacific Northwest. Family-owned since 1987, growing ~10% YoY. They hired us to rebuild their marketing site and location finder after a decade on a WordPress stack that they can no longer maintain in-house." -->

## Scope & Deliverables

<!-- What we're delivering. Be specific about what's in and what's out. -->
<!-- Example:
**In scope:**
- Marketing site rebuild (home, about, locations, menu, contact, blog)
- Location finder with per-location hours and specials
- CMS with editor training for two in-house staff
- SEO migration and 301-redirect plan

**Out of scope:**
- E-commerce / online ordering (deferred to Phase 2)
- Mobile app
- Design system beyond what's needed for the site
-->

## Architecture & Tech Stack

<!-- High-level tech choices and why. Not a full design doc — just the map. -->
<!-- Example: "Next.js 14 (App Router) hosted on Vercel. Sanity CMS for content. Cloudflare for DNS and edge caching. Location data in Sanity; hours and specials editable per location. Analytics via Plausible (client preference — lightweight, no cookie banner)." -->

## Handoff & Maintenance Model

<!-- What happens after we ship. Who owns what, what we continue to do, where the client takes over. -->
<!-- Example:
- **Day-to-day content updates:** Client's in-house staff via Sanity (trained by us pre-launch)
- **Technical maintenance:** Us, on a $2k/month retainer for 6 months post-launch, then client evaluates
- **Hosting bill:** Client pays Vercel + Cloudflare directly, starting at launch
- **Escalation path:** Account lead remains point of contact during retainer; handoff to Sanity's support after
-->

## Known Constraints & Open Questions

<!-- What we know limits the work, and what's still unresolved. This is where risk lives. -->
<!-- Example:
**Constraints:**
- Budget cap: $65k fixed-fee
- Launch deadline: July 1 (client's 40th anniversary promotion)
- Client's CMO approves all copy — needs 48h review window
- Must preserve existing URLs for SEO (no redesigns to URL structure)

**Open questions:**
- Do we migrate the blog archive (280 posts) or archive it to a read-only subdomain? (Decision by May 15)
- Does the location finder need multi-language (Spanish)? CMO undecided.
- Post-launch retainer — monthly or ad-hoc? Client wants to see proposal by June 1.
-->

## Communication Cadence

<!-- How we stay in sync with the client. Meetings, channels, approval gates. -->
<!-- Example:
- **Weekly standup:** Wednesdays 10am with project sponsor + us (30 min)
- **Design reviews:** Async via Figma comments, resolved within 48h
- **Approval gates:** Design sign-off (May 1), content freeze (June 10), launch go/no-go (June 28)
- **Channels:** Slack Connect for day-to-day, email for formal approvals
- **Escalation:** Account lead → Agency partner → Client CMO
-->

---

## Engagement Architecture

<!-- Auto-populated summary. How many data points, which clusters, when last audited. -->

**Data points:** <!-- e.g., "6 active, 1 draft" -->
**Clusters:** <!-- e.g., "Engagement Context (1), Scope & Delivery (2), Architecture & Handoff (3)" -->
**Last audit:** <!-- date -->
**Last significant change:** <!-- e.g., "2026-05-02: Design sign-off reached; scope frozen" -->

---

## How to Use This File

- **Claude reads this at session start** for any engagement-related work
- **Weekly standup prep:** use this alongside `current-state.client-project.md` to frame status updates
- **Context-onboarding** generates an initial draft from kickoff materials (SOW, creative brief, stakeholder map)
- **You update it** at milestones — not every standup, only when the shape of the engagement shifts (scope change, stakeholder change, architecture pivot)

If a section feels wrong, update the underlying data point first (source of truth), then update this synthesis to match.
