# Umbrella BCOS — Product Requirements Document

## Product Vision

**One-liner:** A multi-project orchestration layer that makes BCOS work across project boundaries without sacrificing standalone simplicity.

**The problem:** Operators managing multiple interconnected projects each install BCOS independently. Each project becomes a well-organized knowledge island — but the islands can't see each other. There's no way to search across projects, route content to the right project, audit consistency across the portfolio, or maintain a strategic view of the whole picture.

**The solution:** Umbrella BCOS sits above multiple node BCOS instances and provides the cross-project "connective tissue" — shared context, cross-project references, portfolio-level synthesis, and intelligent content routing.

**Design philosophy:** Nodes stay dumb alone, become smart together. The umbrella adds power without adding complexity to the standalone experience.

---

## Target Users

### Primary: Solo Operator / Small Team Lead

- Manages 3-10 interconnected projects
- Each project has its own BCOS installation
- Needs to see the big picture across all projects
- Frequently creates content that could belong to multiple projects
- Wants to reference insights from one project while working in another

**Example persona:** Guntis — managing:
- **Leverage AI** (service) — helping executives build AI systems
- **Theo App** (product) — the main product/legal entity
- **Auditor** (tool) — quality auditing for agents and repos
- **Theo Website** (website) — the marketing/Lovable site
- **Customer engagements** — various client builds

These projects are deeply interconnected. Leverage AI uses Theo App's product specs. The website needs content from both. The auditor's methodology applies to client engagements. A skill built for one project should be usable in another.

### Secondary: Consultant / Agency

- Manages a portfolio of client engagement projects
- Uses a standard methodology across engagements
- Needs to reuse tools, skills, and templates across client projects
- Wants to capture learnings at the portfolio level, not just per-engagement

---

## Use Cases

### UC-1: Portfolio Overview

**As** an operator with 5 projects, **I want** to see the status and health of all projects at a glance, **so that** I know where to focus my attention.

**Acceptance:** Running `project-navigator` with "show portfolio" displays all projects, their BCOS health, last update dates, and any cross-project issues.

### UC-2: Cross-Project Content Routing

**As** an operator who just had an insight about pricing, **I want** the system to determine which project owns pricing context, **so that** the insight lands in the right place without me remembering the ownership structure of every project.

**Acceptance:** `cross-project-ingest` classifies the content, checks the project registry, and either routes it directly (if clear) or presents options (if ambiguous).

### UC-3: Cross-Project Search

**As** an operator, **I want** to search for "engagement process" across all projects, **so that** I find relevant content regardless of which project it lives in.

**Acceptance:** `project-navigator` search delegates to explore agents (one per project), returns a unified result set with project attribution.

### UC-4: Impact Analysis

**As** an operator who just updated Theo App's product description, **I want** to know which other projects reference it, **so that** I can update them too.

**Acceptance:** `project-navigator` traces the PROVIDES chain from `@theo-app/product-description` and lists all downstream consumers across projects.

### UC-5: Cross-Project Audit

**As** an operator, **I want** to audit context consistency across my entire portfolio, **so that** I catch ownership conflicts, broken references, and stale shared context.

**Acceptance:** `cross-project-audit` runs CLEAR checks plus cross-project categories (CP-A through CP-F) and produces a prioritized report.

### UC-6: Strategic Synthesis

**As** an operator, **I want** a synthesized view of what's happening across all my projects, **so that** I can make strategic decisions that consider the whole picture.

**Acceptance:** The umbrella `table-of-context.md` and `project-map.md` provide a current, cross-project strategic view. `portfolio-daydream` offers periodic reflection.

### UC-7: Engagement Lifecycle

**As** a consultant, **I want** to spin up a new client engagement with BCOS pre-configured and connected to my portfolio, **so that** the engagement immediately benefits from my methodology and tools.

**Acceptance:** Registering a new engagement creates a node BCOS instance, drops `.bcos-umbrella.json`, adds to registry. On completion, the engagement can be archived and optionally disconnected.

### UC-8: Skill Portability

**As** an operator who built an "engagement launcher" skill in Leverage AI, **I want** to use that skill in client engagement projects, **so that** I don't rebuild the same capability per-project.

**Acceptance:** Skills can be referenced across projects via `@project/skill-name`. The umbrella provides a mechanism to share or copy skills between nodes.

---

## Functional Requirements

### FR-1: Project Registration

| ID | Requirement |
|----|-------------|
| FR-1.1 | Register an existing BCOS node by path (submodule, directory, or external reference) |
| FR-1.2 | Drop `.bcos-umbrella.json` into registered node's root |
| FR-1.3 | Add project to `.claude/registries/projects.json` with metadata |
| FR-1.4 | Unregister a node (remove `.bcos-umbrella.json`, update registry) |
| FR-1.5 | Support project roles: `product`, `service`, `tool`, `website`, `engagement` |
| FR-1.6 | Track project status: `active`, `paused`, `archived` |

### FR-2: Cross-Project Search

| ID | Requirement |
|----|-------------|
| FR-2.1 | Search data points across all registered projects by keyword |
| FR-2.2 | Search within a specific project subset |
| FR-2.3 | Return results with project attribution |
| FR-2.4 | Delegate to explore agents (one per project) for context window efficiency |

### FR-3: Cross-Project Content Routing

| ID | Requirement |
|----|-------------|
| FR-3.1 | Classify incoming content by type (same as standard context-ingest) |
| FR-3.2 | Determine which project owns the topic (check registry + project domains) |
| FR-3.3 | Route to correct project's docs/ with standard ingest flow |
| FR-3.4 | Handle ambiguous routing (present options to user) |
| FR-3.5 | Support routing to umbrella docs/ for cross-project content |

### FR-4: Cross-Project Audit

| ID | Requirement |
|----|-------------|
| FR-4.1 | Standard CLEAR audit per project (delegated) |
| FR-4.2 | Cross-project ownership conflict detection |
| FR-4.3 | Broken cross-project reference detection (@project/ refs) |
| FR-4.4 | Stale shared context detection (umbrella data points vs. node references) |
| FR-4.5 | Orphaned node detection |
| FR-4.6 | BCOS version drift detection across nodes |

### FR-5: Portfolio Synthesis

| ID | Requirement |
|----|-------------|
| FR-5.1 | Umbrella-level `table-of-context.md` synthesizing all projects |
| FR-5.2 | Umbrella-level `current-state.md` with cross-project status |
| FR-5.3 | `project-map.md` with visual dependency graph (mermaid) |
| FR-5.4 | Portfolio wake-up context (compressed, aggregated from nodes) |

### FR-6: Cross-Project References

| ID | Requirement |
|----|-------------|
| FR-6.1 | `@project-id/data-point-name` syntax for cross-project refs |
| FR-6.2 | Reference resolution against project registry |
| FR-6.3 | Validation hook for broken references |
| FR-6.4 | Support in ownership specs (BUILDS_ON, REFERENCES, PROVIDES) |
| FR-6.5 | Support in frontmatter (depends-on, consumed-by) |

### FR-7: Shared Context

| ID | Requirement |
|----|-------------|
| FR-7.1 | Umbrella-level data points (brand identity, strategic goals, etc.) |
| FR-7.2 | Nodes declare which umbrella data points they inherit |
| FR-7.3 | Nodes declare which data points they provide to umbrella |
| FR-7.4 | Change propagation awareness (umbrella change → notify affected nodes) |

### FR-8: Portfolio Reflection

| ID | Requirement |
|----|-------------|
| FR-8.1 | Cross-project change detection (what changed across portfolio recently) |
| FR-8.2 | Cross-project pattern identification |
| FR-8.3 | Shared context opportunity detection (duplication across nodes) |
| FR-8.4 | Dependency strain detection |

### FR-9: Update and Sync

| ID | Requirement |
|----|-------------|
| FR-9.1 | Detect BCOS version mismatches across nodes |
| FR-9.2 | Suggest bulk update to latest BCOS version |
| FR-9.3 | Pull-based sync (umbrella checks nodes, not push) |
| FR-9.4 | Registry auto-sync (detect new/removed projects under projects/) |

### FR-10: Engagement Lifecycle

| ID | Requirement |
|----|-------------|
| FR-10.1 | Create new engagement (install node BCOS + register) |
| FR-10.2 | Archive completed engagement (update status, preserve docs) |
| FR-10.3 | Remove disconnected engagement (unregister, restore standalone) |
| FR-10.4 | Capture engagement learnings at umbrella level |

### FR-11: Setup and Migration

| ID | Requirement |
|----|-------------|
| FR-11.1 | `install-umbrella.sh` — single command to scaffold a new umbrella repo |
| FR-11.2 | `register-node` workflow — add an existing BCOS repo as a submodule + register in projects.json + drop `.bcos-umbrella.json` |
| FR-11.3 | `unregister-node` workflow — remove `.bcos-umbrella.json` + update registry (node reverts to standalone) |
| FR-11.4 | Support three migration scenarios: fresh start, migrate existing repos (submodules), convert subdirectories |
| FR-11.5 | Migration safety: no path breakage, no remote changes, no BCOS modifications, fully reversible, incremental |
| FR-11.6 | Public-facing migration guide: "I have N repos with BCOS, how do I umbrella them?" — clear, step-by-step |
| FR-11.7 | Default recommendation: git submodules (least disruptive, repos keep their GitHub URLs/CI/history) |
| FR-11.8 | Example repo structure shipped with the umbrella (or linked) showing a working setup with 2-3 nodes |

---

## Non-Functional Requirements

### NFR-1: Standalone Guarantee

**The most important non-functional requirement.**

Removing `.bcos-umbrella.json` from a node restores 100% standalone behavior. No broken references, no missing dependencies, no degraded functionality. The node must work exactly as if the umbrella never existed.

**Implication:** All cross-project features are additive. Nothing in a node's core behavior depends on the umbrella's existence.

### NFR-2: BCOS Compatibility

The umbrella must work with any standard BCOS version (current and future). This means:
- Umbrella reads node docs/ using standard frontmatter — no custom fields required
- Umbrella reads node .claude/ structure using standard layout — no custom extensions required
- Cross-project reference format (`@project/`) is umbrella-only syntax — nodes don't need to parse it

### NFR-3: Git Strategy Flexibility

Support both git submodules and subdirectories. The registry's `git.type` field tracks the model per project. Mixing models in one umbrella is supported.

### NFR-4: Context Window Efficiency

The umbrella must never attempt to load all node docs into a single context window. Cross-project operations must delegate to explore agents (one per project) and synthesize from summaries.

**Hard limit guidance:** 
- Umbrella main window: umbrella docs/ only (typically 5-15 docs)
- Per-project scan: delegated agent
- Maximum parallel agents: match project count (typically 3-7)

### NFR-5: Incremental Adoption

- Can start with 2 projects, add more over time
- Not all projects need to be registered on day one
- Projects can be added or removed at any point
- No "big bang" setup required

### NFR-6: No Lock-In

- Removing the umbrella doesn't degrade any node
- Nodes can be moved to a different umbrella
- The umbrella repo is portable (move it, rename it, restructure it)

---

## MVP Scope

### Phase 1: Foundation (MVP)

**Goal:** Cross-project visibility and navigation.

| Component | What ships |
|-----------|-----------|
| **Project registry** | `projects.json` with full schema |
| **Project map** | `project-map.md` with mermaid graph |
| **Umbrella docs** | `table-of-context.md`, `current-state.md`, `wake-up-context.md` |
| **project-navigator skill** | Portfolio overview, cross-project search, content routing |
| **Cross-project reference format** | `@project/data-point` syntax + validation |
| **Node interface** | `.bcos-umbrella.json` spec + drop mechanism |
| **Umbrella CLAUDE.md** | Bootstrap that knows about all projects |
| **Install script** | `install-umbrella.sh` — set up umbrella structure + register nodes |
| **Migration guide** | Step-by-step for all 3 scenarios (fresh, migrate existing, convert subdirs) |
| **register/unregister workflow** | Add or remove nodes with one command |

**Success criteria:** User can set up an umbrella over existing repos in <30 minutes, see all projects at a glance, search across them, and route content to the right project.

### Phase 2: Integrity

**Goal:** Cross-project consistency and health.

| Component | What ships |
|-----------|-----------|
| **cross-project-audit skill** | All CP-A through CP-F audit categories |
| **cross-project-ingest skill** | Full routing with project awareness |
| **Change impact analysis** | Trace PROVIDES chains across projects |
| **Version sync** | Detect and resolve BCOS version mismatches |
| **Shared context management** | Umbrella data points with inheritance tracking |

**Success criteria:** User can audit consistency across the portfolio and route content with confidence.

### Phase 3: Intelligence

**Goal:** Strategic reflection and automation.

| Component | What ships |
|-----------|-----------|
| **portfolio-daydream skill** | Cross-project reflection (4 phases) |
| **Engagement lifecycle** | Create/archive/remove engagements |
| **Skill portability** | Share skills between projects |
| **Portfolio health dashboard** | Aggregated ecosystem health across nodes |
| **Auto-sync scripts** | Automated registry updates, stale detection |

**Success criteria:** The umbrella actively surfaces cross-project insights and automates routine maintenance.

### Future (Post-MVP)

- Multi-user support (different people own different projects)
- Notification system (Slack/email when cross-project changes detected)
- Template engagements (pre-configured engagement setups)
- Public API for external integrations
- Mode B node awareness (optional umbrella hooks in node BCOS framework)

---

## Technical Decisions

### Decision 1: Detection File Pattern

**Chosen:** `.bcos-umbrella.json` as the sole coupling mechanism.

**Rationale:** Minimal coupling. Easy to add, easy to remove. Gitignore-able if nodes don't want it in their repo history. Machine-readable. Extensible.

**Alternative considered:** Environment variables, symlinks, config in CLAUDE.md. All rejected for being less portable or harder to manage.

### Decision 2: Pull-Based Sync

**Chosen:** Umbrella checks nodes; nodes don't push to umbrella.

**Rationale:** Keeps nodes simple. No background processes, no webhooks, no push mechanisms. The umbrella is the smart layer; nodes are the simple ones.

**Tradeoff:** Umbrella discovers changes only when a session starts or when explicitly asked to sync. This is acceptable for the use case (single operator, not real-time collaboration).

### Decision 3: Node Awareness — Deferred

**Chosen:** Design supports both Mode A (umbrella owns all cross-project logic) and Mode B (nodes optionally detect umbrella). Decision deferred until real usage reveals which is needed.

**Starting point:** Mode A (nodes completely unaware). Add Mode B capabilities to the node BCOS framework only when demand is clear.

### Decision 4: Cross-Project Reference Is Umbrella-Only Syntax

**Chosen:** The `@project/data-point` syntax is recognized and resolved only by umbrella skills/scripts. Nodes don't need to parse it.

**Rationale:** Standalone guarantee. A node's context-ingest or context-audit don't need to understand cross-project references. Only umbrella-level skills resolve them.

**Future evolution:** If Mode B is adopted, node skills could optionally recognize `@project/` syntax when `.bcos-umbrella.json` is present.

---

## Success Metrics

| Metric | Target | How to measure |
|--------|--------|---------------|
| Content routing accuracy | >90% routes to correct project on first try | Track routing decisions in session diary |
| Cross-project search relevance | Finds relevant content in <30 seconds | User satisfaction with results |
| Audit coverage | All registered projects audited in one run | cross-project-audit completion |
| Standalone guarantee | Zero degradation when umbrella removed | Test: remove .bcos-umbrella.json, run node normally |
| Adoption friction | <30 minutes from existing BCOS nodes to working umbrella | Time from install-umbrella.sh to first cross-project search |

---

## Open Questions

1. **Engagement templates:** Should there be pre-configured engagement types (consultancy, app-build, audit) with starter data points?
2. **Skill sharing mechanism:** Copy skills between projects, symlink them, or reference them? Each has tradeoffs (independence vs. duplication vs. complexity).
3. **Umbrella notifications:** When a cross-project change is detected, how should the user be notified? Session start summary? Dedicated notification?
4. **Private nodes:** Should some nodes be able to hide their data points from siblings? (Client confidentiality in engagements)
5. **Multiple umbrellas:** Can a node belong to multiple umbrellas? (e.g., a tool used by two different portfolios) Probably not for MVP, but worth considering.

---

## Related Documents

- **Architecture:** `docs/_planned/umbrella-bcos-architecture.md` — Full technical design
- **Current BCOS framework:** `docs/_bcos-framework/architecture/system-design.md`
- **Ownership specification:** `docs/_bcos-framework/methodology/ownership-specification.md`
- **Content routing:** `docs/_bcos-framework/architecture/content-routing.md`
