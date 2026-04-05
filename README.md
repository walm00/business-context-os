<p align="center">
  <h1 align="center">CLEAR Context OS</h1>
  <p align="center">
    <strong>Context Engineering for Claude Code</strong><br>
    Build your knowledge architecture. Keep it alive. Let it learn.
  </p>
  <p align="center">
    <a href="#-quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
    <a href="#-how-it-works">How It Works</a> &nbsp;&bull;&nbsp;
    <a href="#-skills--agents">Skills & Agents</a> &nbsp;&bull;&nbsp;
    <a href="#-installation">Installation</a> &nbsp;&bull;&nbsp;
    <a href="docs/guides/getting-started.md">Getting Started Guide</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/claude_code-ready-blueviolet" alt="Claude Code Ready">
    <img src="https://img.shields.io/badge/skills-10-blue" alt="10 Skills">
    <img src="https://img.shields.io/badge/methodology-CLEAR-green" alt="CLEAR Methodology">
    <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT License">
    <img src="https://img.shields.io/badge/free-open--source-brightgreen" alt="Free & Open Source">
  </p>
</p>

---

> Your AI had perfect context — two weeks ago. Since then your strategy shifted, your processes changed, you had three meetings that redefined your priorities, and your personal operating context evolved. But your AI is still working from the old picture.
>
> **CLEAR Context OS** doesn't just organize your knowledge. It *engineers* it — with ownership boundaries that prevent drift, a self-learning system that gets smarter every session, and strategic reflection that catches what maintenance misses. Think of it as a **living wiki + memory system** that Claude Code maintains alongside you.

---

## The Problem: Context Rot

Everyone using AI hits the same wall:

| Week 1 | Week 4 | Week 12 |
|--------|--------|---------|
| "Claude understands everything perfectly!" | "Wait, that's outdated..." | "I don't trust the outputs anymore. Starting over." |

**Context rot** is the silent degradation of AI context over time. It happens to everything — business strategy, personal SOPs, process docs, competitive intelligence, team knowledge, even your own priorities and operating context.

It happens because:

- **No ownership** — Same info lives in 5 files, each slightly different. Which is right?
- **No boundaries** — Brand voice bleeds into messaging, strategy contradicts the pitch deck, your personal notes conflict with the team docs
- **No maintenance** — Context was set up once and never revisited
- **No learning** — Same mistakes repeated because nothing was captured

**The cost:** Every decision based on stale context compounds the problem. You lose trust in AI and fall back to doing everything manually.

---

## The Solution: CLEAR Context Engineering

CLEAR Context OS is a **complete system** — methodology, skills, templates, and automation — for building a knowledge architecture that stays accurate as everything around it changes. It works for business knowledge, personal operating context, SOPs, competitive intelligence, team processes — anything that needs to stay current.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   📋 METHODOLOGY        🛠️ SKILLS           🧠 SELF-LEARNING   │
│                                                                 │
│   CLEAR principles      10 Claude Code      Lessons system      │
│   Ownership spec        skills that         that captures       │
│   Document standards    automate            insights every      │
│   Decision framework    maintenance         session             │
│                                                                 │
│   ─────────────────────────────────────────────────────────     │
│                                                                 │
│   📄 TEMPLATES          🔍 ONBOARDING       💭 REFLECTION       │
│                                                                 │
│   Data point            Scans your repo     Daydream skill      │
│   Cluster               Maps what exists    for strategic       │
│   Architecture          Recommends what     "what if"           │
│   Maintenance           to create first     thinking            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# Clone into your project
git clone https://github.com/walm00/business-context-os.git /tmp/bcos
cd /path/to/your/project
bash /tmp/bcos/install.sh
```

Then ask Claude:

> "Scan my repo and create a Document Index"

That's it. The `context-onboarding` skill scans your existing docs, maps what knowledge you already have, sets up your folder structure, and recommends which context data points to create first.

---

## 🔧 How It Works

### The CLEAR Methodology

Five principles that prevent context rot. Each one addresses a specific failure mode:

| Principle | What It Prevents | In Practice |
|-----------|-----------------|-------------|
| **C** — Contextual Ownership | "Which version is right?" confusion | Every document declares its DOMAIN — what it exclusively owns. Not a person-owner, but a topic-owner: one document, one source of truth for that subject. |
| **L** — Linking | Copy-paste drift between docs | Reference the source, don't duplicate content. If pricing changes, you update ONE file — everything else links to it. |
| **E** — Elimination | Outdated info and duplication piling up | Consolidate and centralise. Don't keep two versions "just in case." Like DRY in code — single source of truth. |
| **A** — Alignment | Context that serves unknown purposes | Every document serves a clear function — if you can't explain what decisions it supports, it doesn't belong. |
| **R** — Refinement | "Set and forget" decay | The structure (ownership, linking, metadata, scheduling) is what ENABLES systematic refinement. Without it, maintenance is ad-hoc guesswork. |

### Document Types

Any knowledge that needs to stay accurate — business, personal, operational, strategic:

| Type | Examples |
|------|---------|
| 📋 **Context** | Company identity, value proposition, target audience, competitive positioning, investor narrative, personal operating context, team structure |
| 📝 **Process** | Employee onboarding, content approval, sales handoff, release process, board reporting, vendor evaluation, personal workflows and SOPs |
| 📏 **Policy** | Brand usage, data handling, pricing rules, expense approval, hiring criteria, IP protection, decision-making frameworks |
| 📚 **Reference** | Glossary, tool inventory, vendor contacts, org chart, tech stack, key metrics definitions, personal contacts and resources |
| 🎯 **Playbook** | Crisis comms, competitive response, fundraising, product launch, market entry, M&A integration, client engagement playbooks |

### The Metadata Standard

Every managed document has YAML frontmatter that enables automated tracking, auditing, and enforcement:

```yaml
---
name: "Company Value Proposition"
type: context
cluster: "Strategy & Positioning"
version: "1.2.0"              # Bump on EVERY change
status: active                 # draft | active | under-review | archived
owner: "Head of Strategy"
created: "2026-01-15"         # Set once, NEVER change
last-updated: "2026-04-05"    # MUST update on every edit
---
```

**The rule:** Every edit = update `last-updated` + bump `version`. No exceptions. A PostToolUse hook automatically validates this when Claude edits your docs.

### The Folder Structure

```
docs/
├── *.md                 # Active context — current reality. Claude trusts this.
├── _inbox/              # Raw material — meeting notes, brain dumps. No quality bar.
├── _planned/            # Polished ideas — may or may not happen. Not yet real.
├── _archive/            # Superseded — kept for reference, not active.
├── table-of-context.md  # Business synthesis (stable, monthly)
├── current-state.md     # Operational priorities (fluid, weekly)
└── document-index.md    # Auto-generated inventory
```

**The folder IS the signal.** When Claude finds `docs/_planned/enterprise-pricing.md`, it knows that's an idea — not reality — before opening the file.

### Ownership Specification

The core of what prevents drift. Every document declares what it owns and what it doesn't:

```markdown
DOMAIN: Customer-facing value statements and core differentiation framework

EXCLUSIVELY_OWNS:
- Primary value proposition statement
- Key differentiators (why us vs. alternatives)
- Benefit hierarchy (what matters most to customers)

STRICTLY_AVOIDS:
- Product feature details (see: product-overview)
- Pricing and packaging (see: pricing-model)
- Competitor analysis (see: competitive-positioning)
```

When two documents disagree, the ownership spec tells you which one is authoritative. No more "which version is right?"

---

## 🛠️ Skills & Agents

### 10 Skills for the Full Context Lifecycle

<table>
<tr>
<td width="50%">

#### 🔍 Context Onboarding
**First-run discovery.** Scans your repo, maps existing knowledge, produces a **Document Index**, sets up folder zones (`_inbox/`, `_planned/`, `_archive/`), recommends what to formalize first.

*"Scan my repo and show me what context exists"*

</td>
<td width="50%">

#### 📥 Context Ingest
**Single entry point for everything new.** YouTube link, meeting notes, article, brain dump — triage it: dump to inbox, park as an idea, or integrate into active docs. Claude reads, classifies, and routes.

*"Here's a document — figure out where it goes"*

</td>
</tr>
<tr>
<td>

#### 🔎 Context Audit
**CLEAR compliance checking.** Scans documents for boundary violations, stale content, ownership gaps, duplication, naming drift. Metadata validation with severity levels and priority matrix.

*"Audit my context for CLEAR compliance"*

</td>
<td>

#### 💭 Daydream
**Strategic reflection.** Steps back from daily work to ask bigger questions. What's missing? What's changed? What connections are we not seeing? Are any planned docs ready to become active?

*"Let's daydream about our context architecture"*

</td>
</tr>
<tr>
<td>

#### 📋 Clear Planner
**Structured planning with sessions.** 8-step workflow with approval gates. Session manifests track progress. Two scenarios: documentation + ecosystem work.

*"Plan the restructuring of our audience data points"*

</td>
<td>

#### 🏗️ Ecosystem Manager
**Keeps the tools in order too.** Overlap detection before creating new skills/agents. Ecosystem health audits. CLEAR discipline applied to the system itself.

*"I want to create a new skill — check for overlaps first"*

</td>
</tr>
<tr>
<td>

#### 🧠 Lessons Consolidate
**Self-learning system.** Captures what worked and what didn't after every session. Consolidates over time — merges overlaps, archives stale lessons, fills gaps. Your system gets smarter.

*"Run lessons consolidation — what have we learned?"*

</td>
<td>

#### ⚡ Core Discipline
**Always-on bootstrap.** If there's even a chance a skill applies, invoke it. Ensures the right skill fires at the right time. Enforces the compounding rule: every task produces answer + context updates.

*Always active — no invocation needed*

</td>
</tr>
<tr>
<td>

#### 📄 Doc-Lint
**Structural validation.** Checks markdown syntax, heading hierarchy, broken cross-references, JSON structure. Knows about folder zones — skips `_inbox/` and `_archive/`.

*"Lint my documentation for structural issues"*

</td>
<td>

#### 📐 Todo Utilities
**Shared pattern library.** Not invoked directly — provides standard TodoWrite patterns (sequential, parallel, error recovery, workflow gates) that other skills copy inline for consistent progress tracking.

*Referenced by other skills, not invoked*

</td>
</tr>
</table>

### 1 Agent

| Agent | Purpose |
|-------|---------|
| 🔭 **Explore** | Fast read-only scanning. Skills delegate heavy file reading here to keep the main context window clean. Searches files, reads content, returns compact summaries. |

### Enforcement

| Mechanism | What It Does |
|-----------|-------------|
| 🔒 **Frontmatter Hook** | PostToolUse hook validates YAML frontmatter every time Claude edits a doc. Warns about missing fields, invalid status, blank owner. |
| 📜 **build_document_index.py** | Python script auto-generates the Document Index with inventory, metadata health, and separate sections for inbox/planned/archive. |

---

## 📦 What's In The Box

```
business-context-os/
│
├── docs/
│   ├── methodology/              # The CLEAR intellectual core
│   │   ├── clear-principles.md       # 5 principles with rationale
│   │   ├── context-architecture.md   # Knowledge structure + context window management
│   │   ├── ownership-specification.md # The 6 keywords that prevent drift
│   │   ├── document-standards.md     # Metadata, quality levels, versioning
│   │   └── decision-framework.md     # When to act, when to wait
│   │
│   ├── guides/                   # How to use it
│   │   ├── getting-started.md        # Week 1 walkthrough
│   │   ├── defining-your-context.md  # Step-by-step data point creation
│   │   ├── maintenance-guide.md      # Keeping context alive long-term
│   │   ├── scheduling.md            # Automated recurring maintenance
│   │   ├── migration-guide.md        # Moving from messy docs to CLEAR
│   │   ├── adoption-tiers.md         # Incremental adoption path
│   │   └── for-non-technical-users.md # Plain language, no jargon
│   │
│   ├── architecture/             # How it's built (for contributors)
│   │   ├── system-design.md          # Full system overview with Mermaid diagrams
│   │   ├── content-routing.md        # How content enters and flows
│   │   ├── component-standards.md    # How to build new skills/agents/hooks
│   │   ├── metadata-system.md        # All validation rules in one place
│   │   └── maintenance-lifecycle.md  # Scheduled rhythms and trigger chains
│   │
│   ├── templates/                # Fill-in-the-blank starting points
│   │   ├── context-data-point.md     # Single document template
│   │   ├── context-cluster.md        # Group related documents
│   │   ├── context-architecture-canvas.md  # Full architecture planning
│   │   ├── table-of-context.md       # Business synthesis template
│   │   ├── current-state.md          # Operational priorities template
│   │   └── maintenance-checklist.md  # Weekly/monthly/quarterly checks
│   │
│   ├── _inbox/                   # Raw material landing zone
│   ├── _planned/                 # Polished ideas, not yet active
│   └── _archive/                 # Superseded documents
│
├── .claude/
│   ├── skills/                   # 10 skills (see above)
│   ├── agents/                   # 1 agent (explore)
│   ├── hooks/                    # Automated enforcement (frontmatter validation)
│   ├── quality/ecosystem/        # State, config, lessons (self-learning)
│   ├── scripts/                  # Document index builder, lesson tools
│   └── registries/               # Machine-readable indexes
│
├── examples/
│   └── brand-strategy/           # Complete worked example
│       ├── context-architecture.md   # Architecture for a brand team
│       └── data-points/             # 8 realistic data points (Acme Co)
│
├── CLAUDE.md                     # Claude Code instructions + session bootstrap
├── install.sh                    # Installer for existing projects
└── LICENSE                       # MIT
```

---

## 📥 Installation

### Option A: New Project

Click **"Use this template"** on GitHub. Everything is ready — folder zones, skills, templates, hooks.

### Option B: Existing Project

```bash
# Clone BCOS
git clone https://github.com/walm00/business-context-os.git /tmp/bcos

# Go to YOUR project
cd /path/to/your/project

# Install (never overwrites existing files)
bash /tmp/bcos/install.sh
```

The installer copies skills, agents, docs, templates, hooks, and scripts. Creates `_inbox/`, `_planned/`, `_archive/` folder zones. If you already have a `CLAUDE.md`, it saves a reference copy for manual merge.

### Option C: Manual

Copy `.claude/`, `docs/`, and `examples/` into your project. Merge `CLAUDE.md` into your existing one.

### Verify

```bash
bash .claude/skills/skill-discovery/find_skills.sh   # Should show: 10 skills
bash .claude/agents/agent-discovery/find_agents.sh   # Should show: 1 agent
```

---

## ⏰ Scheduled Maintenance

Context that isn't maintained rots. Set up recurring tasks so Claude keeps your knowledge alive:

| Task | Frequency | What Happens |
|------|-----------|-------------|
| **Document Index rebuild** | Weekly | `build_document_index.py` refreshes file inventory and metadata health |
| **Health check** | Weekly | Quick CLEAR audit across active documents |
| **Daydream** | Bi-weekly | Strategic reflection — what changed, what's stale, what's ready to activate |
| **Deep audit + lessons** | Monthly | Thorough audit, lessons consolidation, inbox processing |
| **Architecture review** | Quarterly | Full review of context vs. reality, _planned/ triage |

These frequencies adapt by phase. See [scheduling.md](docs/guides/scheduling.md) for phase-specific rhythms and ready-to-use prompts.

---

## 🎯 Who Is This For?

| Role | What You'll Manage |
|------|-------------------|
| **Founders & CEOs** | Company identity, investor narrative, strategic vision, decision frameworks — grounded in reality, not last quarter's deck |
| **Solopreneurs & Indie Builders** | Personal operating context, SOPs, client processes, product positioning — your whole business in one place |
| **Operations Leaders** | SOPs, process docs, vendor contracts, compliance policies — reflecting how work actually gets done |
| **Strategy & Growth** | Market context, competitive positioning, partnership models, expansion playbooks |
| **Marketing & Brand** | Brand voice, audience segments, messaging frameworks, campaign context |
| **Agencies & Consultants** | Multiple client contexts without cross-contamination or staleness |
| **Developers** | Project context, architecture decisions, team knowledge, onboarding docs — the non-code side of your codebase |

**The system is role-agnostic.** CLEAR methodology works the same whether you're managing investor materials, personal SOPs, or team onboarding docs.

---

## 🌱 Adoption Path

| | Tier 1: Foundation | Tier 2: Skills |
|--|-------------------|----------------|
| **When** | Week 1 | Weeks 2-3 |
| **What** | CLEAR methodology + data points + templates | Skills for planning, auditing, reflection, ingestion |
| **Time** | 2-3 hours setup, 5 min/week | 1-2 hours setup, ongoing |
| **You get** | Organized, owned, bounded context | Self-maintaining, self-learning context system |

Start with Tier 1. Move to Tier 2 when manual maintenance feels like overhead. Extend with custom skills when you need more — the `ecosystem-manager` skill guides you through creating new tools.

---

## 💡 Philosophy

**Living systems, not one-time setups.** Your business changes. Your priorities change. Your knowledge evolves. Your AI context should evolve with it — structurally, not chaotically.

**Order that maintains itself.** CLEAR doesn't just organize your documents. It creates a system where drift is caught early, duplication is centralised, and every piece of knowledge has a clear home.

**Self-learning.** The lessons system captures what works and what doesn't. Your context architecture gets smarter with every maintenance cycle.

**The same discipline everywhere.** The `ecosystem-manager` applies CLEAR principles to your skills and agents themselves. The tools stay as ordered as the documents.

---

## 🤝 Contributing

Contributions welcome. Whether you've found a better way to structure context, built a useful skill, or improved the docs — open an issue or submit a PR.

### Branch Strategy

| Branch | Purpose | Who uses it |
|--------|---------|-------------|
| `main` | Stable releases — what users download | Everyone using BCOS |
| `dev` | Active development — where contributions land | Contributors |

**For contributors:** fork the repo, branch off `dev`, open your PR targeting `dev`. When `dev` is stable it gets squash-merged into `main` as a clean release.

### Contributing via Lessons

The fastest way to improve BCOS is through **lessons learned**. As you use the system, it captures what works and what doesn't in `.claude/quality/ecosystem/lessons.json`. If you discover a pattern that would help everyone — a better way to structure a data point, a common mistake to avoid, a workflow improvement — you can contribute that lesson back.

**How:**
1. Use BCOS normally — lessons accumulate automatically
2. Review your lessons: look for ones that are universal, not specific to your situation
3. Open a PR with the lesson added to the repo's `lessons.json`
4. Include context: what happened, why it matters, what the lesson changes

This is the most natural contribution path — you're already generating insights by using the system.

### Other Contributions

- New skills (maintenance workflows, context patterns)
- Examples for specific industries or functions
- Improvements to existing skills or methodology docs
- Better templates for context data points

### For Contributors: Architecture Docs

If you want to understand HOW BCOS is built (not just how to use it), start with `docs/architecture/system-design.md`. The architecture docs explain design decisions, the skill graph, component standards, and why things are built the way they are.

## 📖 Origin

CLEAR Context OS was created by **[Guntis Coders](https://github.com/walm00)** after two years of building and operating context systems in production — first for competitive intelligence work, then for broader business context management.

The **CLEAR methodology** (Contextual Ownership, Linking, Elimination, Alignment, Refinement) emerged from a practical problem: AI context degrades silently over time, and no amount of one-time documentation prevents it. The solution required a system — not just documents, but ownership boundaries, automated maintenance, self-learning, and structured reflection.

The **Table of Context** concept — a living synthesis of what your business IS, distinct from the file inventory — was first articulated in a [Medium article on business context engineering](https://medium.com/businessacademy-lv/what-is-the-table-of-contexts-and-why-does-it-matter-8ec2a9557e9f) and became a core architectural pattern.

This isn't a theoretical framework. Every skill, every pattern, every architectural decision was tested in real-world use before being abstracted into this open-source package.

## 📄 License

[MIT](LICENSE) — Free to use, modify, distribute. No restrictions.

---

<p align="center">
  <strong>CLEAR Context OS</strong><br>
  Context engineering for Claude Code.<br>
  Stop context rot. Start building knowledge that lasts.
</p>
