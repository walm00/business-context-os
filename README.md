<p align="center">
  <h1 align="center">Business Context OS</h1>
  <p align="center">
    <strong>Business Context Engineering for Claude Code</strong><br>
    Create order in your business knowledge. Keep it. Let it learn.
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
    <img src="https://img.shields.io/badge/skills-8-blue" alt="8 Skills">
    <img src="https://img.shields.io/badge/methodology-CLEAR-green" alt="CLEAR Methodology">
    <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT License">
    <img src="https://img.shields.io/badge/audience-non--technical-orange" alt="Non-technical Friendly">
  </p>
</p>

---

> Your AI understood your business perfectly — two weeks ago. Now your positioning shifted, your audience evolved, your competitor pivoted. But your AI context is frozen in time.
>
> **Business Context OS** doesn't just organize your context. It *engineers* it — with ownership boundaries that prevent drift, a self-learning system that gets smarter every session, and strategic reflection that catches what maintenance misses.

---

## The Problem: Context Rot

Every team using AI hits the same wall:

| Week 1 | Week 4 | Week 12 |
|--------|--------|---------|
| "Claude understands our business perfectly!" | "Wait, that's our old positioning..." | "I don't trust the outputs anymore. Starting over." |

**Context rot** is the silent degradation of AI context over time. It happens because:

- **No ownership** — Same info lives in 5 files, each slightly different
- **No boundaries** — Brand voice bleeds into messaging, positioning contradicts the pitch deck
- **No maintenance** — Context was set up once and never revisited
- **No learning** — Same mistakes repeated because nothing was captured

**The cost:** Every decision based on stale context compounds the problem. Teams lose trust in AI and fall back to manual work.

---

## The Solution: Business Context Engineering

Business Context OS is a **complete system** — methodology, skills, templates, and automation — that creates order in your business knowledge and keeps it ordered as your business evolves.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   📋 METHODOLOGY        🛠️ SKILLS           🧠 SELF-LEARNING   │
│                                                                 │
│   CLEAR principles      8 Claude Code       Lessons system      │
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

> "Scan my repo and create a Table of Context"

That's it. The `context-onboarding` skill scans your existing docs, maps what knowledge you already have, and recommends which context data points to create first.

---

## 🔧 How It Works

### The CLEAR Methodology

Five principles that prevent context rot. Each one addresses a specific failure mode:

| Principle | What It Prevents | In Practice |
|-----------|-----------------|-------------|
| **C** — Contextual Ownership | "Who owns this?" confusion | Every document has ONE owner, ONE source of truth |
| **L** — Linking | Copy-paste drift between docs | Reference the source, don't duplicate content |
| **E** — Elimination | Outdated info piling up | Consolidate duplicates, keep docs clean |
| **A** — Alignment | Context that serves no purpose | Every doc serves a business objective |
| **R** — Refinement | "Set and forget" decay | Structured review cycles, scheduled maintenance |

### Document Types

Any business knowledge that needs to stay accurate — across every function:

| Type | Examples |
|------|---------|
| 📋 **Context** | Company identity, value proposition, target audience, competitive positioning, investor narrative, partnership model |
| 📝 **Process** | Employee onboarding, content approval, sales handoff, release process, board reporting workflow, vendor evaluation |
| 📏 **Policy** | Brand usage, data handling, pricing rules, expense approval, hiring criteria, IP protection |
| 📚 **Reference** | Glossary, tool inventory, vendor contacts, org chart, tech stack, key metrics definitions |
| 🎯 **Playbook** | Crisis comms, competitive response, fundraising, product launch, market entry, M&A integration |

### The Metadata Standard

Every managed document has YAML frontmatter that enables tracking and auditing:

```yaml
---
name: "Company Value Proposition"
type: context
cluster: "Strategy & Positioning"
version: "1.2.0"              # Bump on EVERY change
status: active                 # draft | active | under-review | archived
owner: "Head of Strategy"
created: "2026-01-15"         # Set once, NEVER change
last-updated: "2026-04-05"   # MUST update on every edit
---
```

**The rule:** Every edit = update `last-updated` + bump `version`. No exceptions.

### Ownership Specification

The core of what prevents drift. Every document declares what it owns and what it doesn't:

```markdown
DOMAIN: Customer-facing value statements and core differentiation framework

EXCLUSIVELY_OWNS:
- Primary value proposition statement
- Key differentiators (why us vs. alternatives)
- Benefit hierarchy (what matters most to customers)
- Proof points and evidence for each claim

STRICTLY_AVOIDS:
- Product feature details (see: product-overview)
- Pricing and packaging (see: pricing-model)
- Competitor analysis (see: competitive-positioning)
- Customer testimonials (see: customer-insights)
```

When two documents disagree, the ownership spec tells you which one is authoritative. No more "which version is right?"

---

## 🛠️ Skills & Agents

### 8 Skills for Context Lifecycle

<table>
<tr>
<td width="50%">

#### 🔍 Context Onboarding
**First-run discovery.** Scans your repo, maps existing knowledge, produces a **Table of Context**, recommends what to formalize first.

*"Scan my repo and show me what business context exists"*

</td>
<td width="50%">

#### 📋 Clear Planner
**Structured planning with sessions.** 8-step workflow with approval gates. Session manifests track progress so you can pause and resume. Two scenarios: documentation + ecosystem work.

*"Plan the restructuring of our audience data points"*

</td>
</tr>
<tr>
<td>

#### 🔎 Context Audit
**CLEAR compliance checking.** Scans documents for boundary violations, stale content, ownership gaps, duplication, naming inconsistencies. Metadata validation against the document standard.

*"Audit my Brand & Identity cluster for CLEAR compliance"*

</td>
<td>

#### 💭 Daydream
**Strategic reflection.** Steps back from daily maintenance to ask bigger questions. What's missing? What's changed? What connections are we not seeing? What context will we need in 6 months?

*"Let's daydream about our context architecture"*

</td>
</tr>
<tr>
<td>

#### 🏗️ Ecosystem Manager
**Keeps the tools in order too.** Overlap detection before creating new skills/agents. Ecosystem health audits. The same CLEAR discipline applied to the system itself.

*"I want to create a new skill — check for overlaps first"*

</td>
<td>

#### 🧠 Lessons Consolidate
**Self-learning system.** Captures what worked and what didn't after every session. Consolidates over time — merges overlaps, archives stale lessons, fills gaps. Your context system gets smarter.

*"Run lessons consolidation — what have we learned?"*

</td>
</tr>
<tr>
<td>

#### ⚡ Core Discipline
**Always-on bootstrap.** The 1% Rule: if there's even a 1% chance a skill applies, invoke it. Ensures the right skill fires at the right time, every time.

*Always active — no invocation needed*

</td>
<td>

#### 📄 Doc-Lint
**Structural validation.** Checks markdown syntax, heading hierarchy, broken cross-references, JSON structure. The formatting layer under the content layer.

*"Lint my documentation for structural issues"*

</td>
</tr>
</table>

### 1 Agent

| Agent | Purpose |
|-------|---------|
| 🔭 **Explore** | Fast read-only exploration of your project. Searches files, reads content, answers questions about structure. |

---

## 📦 What's In The Box

```
business-context-os/
│
├── docs/
│   ├── methodology/              # The intellectual core
│   │   ├── clear-principles.md       # 5 principles with business examples
│   │   ├── context-architecture.md   # How to structure your knowledge
│   │   ├── ownership-specification.md # The 6 keywords that prevent drift
│   │   ├── document-standards.md     # Metadata, quality bar, versioning
│   │   └── decision-framework.md     # When to act, when to wait
│   │
│   ├── guides/                   # User-facing documentation
│   │   ├── getting-started.md        # Zero-jargon Week 1 walkthrough
│   │   ├── defining-your-context.md  # Step-by-step data point creation
│   │   ├── maintenance-guide.md      # Keeping context alive long-term
│   │   ├── scheduling.md            # Automated recurring maintenance
│   │   ├── adoption-tiers.md         # Incremental adoption path
│   │   └── for-non-technical-users.md # Plain language, no jargon
│   │
│   └── templates/                # Fill-in-the-blank starting points
│       ├── context-data-point.md     # Single document template
│       ├── context-cluster.md        # Group related documents
│       ├── context-architecture-canvas.md  # Full architecture planning
│       └── maintenance-checklist.md  # Weekly/monthly/quarterly checks
│
├── .claude/
│   ├── skills/                   # 8 skills (see above)
│   ├── agents/                   # 1 agent (explore)
│   ├── quality/ecosystem/        # State, config, lessons (self-learning)
│   ├── scripts/                  # Discovery and consolidation scripts
│   └── registries/               # Machine-readable document index
│
├── examples/
│   └── brand-strategy/           # Complete worked example
│       ├── context-architecture.md   # Architecture for a brand team
│       └── data-points/             # 8 realistic data points (Acme Co)
│
├── CLAUDE.md                     # Claude Code instructions
├── install.sh                    # Installer for existing projects
└── LICENSE                       # MIT
```

---

## 📥 Installation

### Option A: New Project

Click **"Use this template"** on GitHub. Everything is ready.

### Option B: Existing Project

```bash
# Clone BCOS
git clone https://github.com/walm00/business-context-os.git /tmp/bcos

# Go to YOUR project
cd /path/to/your/project

# Install (never overwrites existing files)
bash /tmp/bcos/install.sh
```

The installer copies skills, agents, docs, and templates into your project. If you already have a `CLAUDE.md`, it saves a reference copy for you to merge manually.

### Option C: Manual

Copy `.claude/`, `docs/`, and `examples/` into your project. Merge `CLAUDE.md` into your existing one.

### Verify

```bash
bash .claude/skills/skill-discovery/find_skills.sh   # Should show: 8 skills
bash .claude/agents/agent-discovery/find_agents.sh   # Should show: 1 agent
```

---

## ⏰ Scheduled Maintenance

Set up recurring tasks so Claude maintains your context automatically:

| Task | Frequency | What Happens |
|------|-----------|-------------|
| **Health check** | Weekly | Quick CLEAR audit across all documents |
| **Daydream** | Bi-weekly | Strategic reflection on architecture gaps |
| **Deep audit + lessons** | Monthly | Thorough cluster audit, lessons consolidation, repo re-scan |
| **Architecture review** | Quarterly | Full review of context vs. business reality |

See [scheduling.md](docs/guides/scheduling.md) for ready-to-use prompts and cron expressions.

---

## 🎯 Who Is This For?

| Role | Use Case |
|------|----------|
| **Founders & CEOs** | Company identity, investor narrative, strategic vision, board materials — grounded in reality, not last quarter's deck |
| **Operations Leaders** | SOPs, process docs, vendor contracts, compliance policies — that reflect how work actually gets done |
| **Strategy & Growth** | Market context, competitive positioning, partnership models, expansion playbooks |
| **Marketing & Brand** | Brand voice, audience segments, messaging frameworks, campaign context |
| **Agencies & Consultants** | Multiple client contexts without cross-contamination or staleness |
| **Product Teams** | Product positioning, feature context, user research, roadmap rationale |
| **People & Culture** | Hiring playbooks, onboarding SOPs, culture docs, team structure context |

**No coding required.** If you can write a document and organize a folder, you can use Business Context OS. The system is role-agnostic — CLEAR methodology works the same whether you're managing investor materials or onboarding docs.

---

## 🌱 Adoption Path

| | Tier 1: Foundation | Tier 2: Skills |
|--|-------------------|----------------|
| **When** | Week 1 | Weeks 2-3 |
| **What** | CLEAR methodology + data points + templates | Skills for planning, auditing, reflection |
| **Time** | 2-3 hours setup, 5 min/week | 1-2 hours setup, ongoing |
| **You get** | Organized, owned, bounded context | Self-maintaining, self-learning context system |

Start with Tier 1. Move to Tier 2 when manual maintenance feels like overhead. Extend with custom skills when you need more — the `ecosystem-manager` skill guides you through creating new tools.

---

## 💡 Philosophy

**Living systems, not one-time setups.** Your business changes. Your market changes. Your AI context should change with them — structurally, not chaotically.

**Order that maintains itself.** CLEAR doesn't just organize your documents. It creates a system where drift is caught early, duplication is consolidated, and every piece of knowledge has a clear home.

**Self-learning.** The lessons system captures what works and what doesn't. Your context architecture gets smarter with every maintenance cycle.

**The same discipline everywhere.** The `ecosystem-manager` applies CLEAR principles to your skills and agents themselves. Tools stay as ordered as documents.

---

## 🤝 Contributing

Contributions welcome. Whether you've found a better way to structure business context, built a useful skill, or improved the docs — open an issue or submit a PR.

## 📄 License

MIT. See [LICENSE](LICENSE).

---

<p align="center">
  <strong>Business Context OS</strong><br>
  Built on the CLEAR methodology. Designed for Claude Code.<br>
  Stop context rot. Start context engineering.
</p>
