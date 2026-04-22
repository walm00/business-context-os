# Internal Tool — App Pattern

> How to scaffold context for an internal app with UI and human users. Use when the repo is about **a tool an internal team uses day-to-day through a UI**.

---

## Purpose & Fit

Use this pattern when the repo is an internal-facing web app, dashboard, admin console, or back-office tool with a UI, persisted state, and identifiable users inside the company. Signals: a frontend framework (React / Next.js / Vue / similar), auth through internal SSO, a backing database, user roles, screenshots of UIs in the docs, references to "the team uses it to…". The core question the context answers is "what does this tool do for which internal users, and how is it kept alive?"

Distinct from **internal-tool-automation-pattern** (no UI — scripts, pipelines, services), **product-service-pattern** (external-facing product), and **product-development-pattern** (R&D context for a product being built rather than a tool in active internal use).

---

## Data Point Map

**Tool Identity**
- Tool overview — what it is, what team owns it, what status it's in (active / deprecated / frozen)
- Purpose & value — the internal problem it solves and what it replaced
- Ownership & stakeholders — owning team, primary maintainer(s), stakeholder groups
- Lifecycle stage — in-build / active / stable / deprecating, and what that implies

**Users & Capabilities**
- User roles — the internal user types and rough headcounts per role
- Core capabilities — the 4-8 things users actually reach for this tool to do
- Access & permissions — how access is granted, who can do what, review cadence
- Usage patterns — who uses it daily vs. weekly vs. monthly, and for what
- UX surface area — main screens / views, major workflows through the UI

**Architecture & Operations**
- System architecture — frontend / backend / data layer at a high level
- Integrations — what systems it reads from or writes to, including SSO and analytics
- Deployment model — hosting, release pipeline, environments
- Monitoring & on-call — dashboards, alert routing, paging owners
- Known issues & debt — current limitations, active incidents, tracked debt
- Change management — how features ship, who approves, how users are notified

---

## Relationships

- **User roles** references **Core capabilities** (roles map to which capabilities they use) and **Access & permissions** (roles drive permissions).
- **Core capabilities** references **System architecture** (capabilities are implemented by components) and **Integrations** (many capabilities depend on an upstream system).
- **Known issues & debt** often cross-references specific **Core capabilities** and **Integrations** where the pain lives.
- **Ownership & stakeholders** references **Monitoring & on-call** (the owning team is usually the pager target).
- **Lifecycle stage** influences which cluster carries the most weight: in-build leans on Architecture; active leans on Users & Capabilities; deprecating leans on Known issues + change management.

Cross-references that tend to form: User role ↔ Permission set; Capability ↔ Integration it depends on; On-call rotation ↔ Owning team.

---

## Voice & Tone

Factual and operational. Present-tense, matter-of-fact, timestamped observations. Users care that the doc is **current and accurate**, not that it's elegant. Screenshots and system diagrams help; narrative doesn't. Known issues should be listed plainly with ticket references — don't euphemize. "As of [date]" prefixes on anything that will age (performance numbers, user counts, incident status) keep the doc honest.

---

## Template Mapping

- **Primary scaffold:** `docs/_bcos-framework/templates/table-of-context.internal-tool.md`
- **Current state:** `docs/_bcos-framework/templates/current-state.internal-tool.md`

Both templates exist and cover the app shape — the "Section Applicability" table at the top of `table-of-context.internal-tool.md` shows which sections matter more for apps vs. pipelines. Use all ✓ rows in the "App (UI + users)" column.
