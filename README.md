<p align="center">
  <h1 align="center">CLEAR Context OS</h1>
  <p align="center">
    <strong>Context Engineering for Claude Code</strong><br>
    Organize what you know. Build what's missing. Keep it alive. Let it learn.
  </p>
  <p align="center">
    <a href="#-quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
    <a href="#-how-it-works">How It Works</a> &nbsp;&bull;&nbsp;
    <a href="#-skills--agents">Skills & Agents</a> &nbsp;&bull;&nbsp;
    <a href="docs/_bcos-framework/guides/getting-started.md">Getting Started Guide</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/claude_code-ready-blueviolet" alt="Claude Code Ready">
    <img src="https://img.shields.io/badge/skills-14-blue" alt="14 Skills">
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

**The misconception:** "Just give AI more data." But more data without structure creates more confusion, not less. Five files saying slightly different things about your pricing is worse than one file that's right. Context engineering isn't about volume — it's about accuracy, ownership, and maintenance.

---

## The Solution: CLEAR Context Engineering

CLEAR Context OS is a **complete system** — methodology, skills, templates, and automation — for building a knowledge architecture that stays accurate as everything around it changes.

| | Organize | Maintain | Learn |
|---|---|---|---|
| **What** | CLEAR methodology + ownership boundaries | 13 skills + 4 hooks that automate maintenance | Lessons system captures insights every session |
| **How** | Every doc declares what it owns. No duplicates, no drift. | Session capture, integration audits, scheduled reviews | What worked, what didn't — your system gets smarter |
| **You do** | Define your data points (Claude helps) | Review what Claude surfaces | Approve or reject captured lessons |

---

## Requirements

- **Claude Code** — desktop app, CLI, or web
- **Python 3.8+** on `PATH` — used by hooks, validators, and the updater
- **bash** — only the installer and two hooks use it; the default macOS bash (3.2) is fine

**macOS-specific notes:**

- Install Python via `xcode-select --install` (Command Line Tools) or `brew install python`. The installer fails fast with instructions if `python3` is missing.
- If you use the python.org installer and the updater fails with an SSL error, run `/Applications/Python\ 3.x/Install\ Certificates.command` once. Homebrew and CLT Python don't hit this.
- Scheduled maintenance runs inside Claude Code itself (tasks live in `~/.claude/scheduled-tasks/`) — no `launchd` plist needed, but Claude Code must be running for tasks to fire.

---

## Quick Start

**New project:**

Click **"Use this template"** on GitHub. Open Claude Code and say:

> "I want to set up my business context. Here's my website: [url]"

**Existing project:**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/walm00/business-context-os/main/install.sh)
```

Or tell Claude: *"Install CLEAR Context OS from https://github.com/walm00/business-context-os"*

**Already have docs?** SOPs, brand guidelines, strategy docs, processes — bring them all:

> "Scan my repo and show me what business context already exists."

Or dump everything into `docs/_inbox/` and ask: *"Process my inbox — figure out what goes where."*

Claude classifies each piece, organizes it with proper ownership boundaries, and **preserves your existing content** — SOPs and processes are wrapped with structure, not rewritten. Connect Google Drive, Notion, or Confluence via MCP to pull docs directly.

**20-30 minutes to working context.** Nothing gets lost.

---

## How It Works

### The CLEAR Methodology

Five principles that prevent context rot:

| Principle | What It Prevents | In Practice |
|-----------|-----------------|-------------|
| **C** — Contextual Ownership | "Which version is right?" | One document, one source of truth per topic |
| **L** — Linking | Copy-paste drift | Reference the source, don't duplicate |
| **E** — Elimination | Stale info piling up | Consolidate, don't keep two versions |
| **A** — Alignment | Context without purpose | If it doesn't support decisions, it doesn't belong |
| **R** — Refinement | "Set and forget" decay | Structured maintenance, not ad-hoc fixes |

### What's In The Box

```
business-context-os/
│
├── docs/
│   ├── *.md                     # Your active context — current reality
│   ├── _inbox/                  # Raw material + auto-captured sessions
│   ├── _planned/                # Ideas — not yet real
│   ├── _archive/                # Superseded — historical reference
│   ├── _collections/            # High-volume files — transcripts, reports, invoices
│   ├── _bcos-framework/
│   │   ├── methodology/         # CLEAR principles, ownership spec, standards
│   │   ├── guides/              # Getting started, maintenance, scheduling
│   │   ├── architecture/        # System design (for contributors)
│   │   └── templates/           # Data point, cluster, architecture templates
│
├── .claude/
│   ├── skills/                  # 13 skills (see below)
│   ├── agents/                  # 1 agent (explore)
│   ├── hooks/                   # Frontmatter check, session + pre-compact capture, commit check, opt-in pre-commit validator
│   ├── scripts/                 # Index builder, update, validators, pruning, cross-ref + ecosystem analysis, lessons, wake-up context, publish
│   └── registries/              # Entity registry, reference indexes
│
├── .github/
│   └── workflows/ci.yml         # 4 automated checks on every PR
│
├── examples/brand-strategy/     # Complete worked example (8 data points)
├── CLAUDE.md                    # Claude Code instructions (lean — ~650 tokens)
└── install.sh                   # One-command installer
```

**The folder IS the signal.** Claude knows `_planned/` is an idea and `_archive/` is history before opening the file.

### Document Types

Different content gets different treatment. Business context is synthesized from sources. SOPs and policies are preserved exactly as-is. Reference material is cataloged untouched.

| Type | Examples | How it's handled |
|------|---------|-----------------|
| 📋 **Context** | Company identity, value proposition, target audience | Synthesized from multiple sources |
| 📝 **Process** | Onboarding, sales handoff, content approval | Wrapped — your content preserved exactly |
| 📏 **Policy** | Brand usage, pricing rules, decision frameworks | Wrapped — rules preserved, not rewritten |
| 📚 **Reference** | Glossary, tool inventory, org chart, tech stack | Cataloged — just add metadata |
| 🎯 **Playbook** | Crisis comms, competitive response, product launch | Wrapped — response steps preserved |

---

## Skills & Agents

### 14 Skills

<table>
<tr>
<td width="50%">

#### 🔍 Context Onboarding
**First-run discovery.** Scans your repo, connected systems, or uploaded files. Classifies content, preserves existing docs, builds your architecture.

*"I have docs in my repo and Google Drive — help me organize them"*

</td>
<td width="50%">

#### 📥 Context Ingest
**Single entry point for everything new.** Meeting notes, articles, brain dumps — triage, classify, and route.

*"Here's a document — figure out where it goes"*

</td>
</tr>
<tr>
<td>

#### ⛏️ Context Mine
**Extract context from conversations.** Slack exports, meeting transcripts, chat logs — pulls out decisions, discoveries, and action items.

*"Extract context from this Slack export"*

</td>
<td>

#### 🔎 Context Audit
**CLEAR compliance checking.** Boundary violations, stale content, ownership gaps, duplication, naming drift.

*"Audit my context for CLEAR compliance"*

</td>
</tr>
<tr>
<td>

#### 💭 Daydream
**Strategic reflection.** What's missing? What's changed? What connections are we not seeing?

*"Let's daydream about our context architecture"*

</td>
<td>

#### 📋 Clear Planner
**Structured planning.** 8-step workflow with approval gates and mandatory integration audits.

*"Plan the restructuring of our audience data points"*

</td>
</tr>
<tr>
<td>

#### 🏗️ Ecosystem Manager
**Keeps the tools in order.** Overlap detection, ecosystem audits, integration checks before commits.

*"I want to create a new skill — check for overlaps"*

</td>
<td>

#### 🧠 Lessons Consolidate
**Self-learning.** Captures what worked and what didn't. Merges overlaps, archives stale lessons.

*"What have we learned?"*

</td>
</tr>
<tr>
<td>

#### ⚡ Core Discipline
**Always-on bootstrap.** Ensures the right skill fires at the right time. Enforces the compounding rule.

*Always active — no invocation needed*

</td>
<td>

#### 📄 Doc-Lint
**Structural validation.** Markdown syntax, cross-references, JSON structure.

*"Lint my documentation"*

</td>
</tr>
<tr>
<td>

#### 📐 Todo Utilities
**Shared patterns.** Standard progress tracking used by other skills internally.

*Referenced by other skills, not invoked directly*

</td>
<td>

#### ⏰ Schedule Dispatcher
**Daily maintenance runner.** Reads the schedule, runs due jobs, writes one consolidated digest — green/amber/red verdicts at a glance.

*Runs automatically each morning via the `bcos-{project}` scheduled task*

</td>
</tr>
<tr>
<td>

#### 🎛️ Schedule Tune
**Natural-language config editor.** Describe what you want — *"run audit twice a week"* — and it edits `schedule-config.json` with a before/after diff and confirmation.

*"Turn off deep daydream"* · *"Move dispatcher to 08:30"*

</td>
<td>

<!-- intentionally empty — odd count of skills in this row -->

</td>
</tr>
</table>

### Enforcement & Automation

| Mechanism | What It Does |
|-----------|-------------|
| 🔒 **Frontmatter Hook** | Validates metadata every time Claude edits a doc |
| 💾 **Session Capture** | Auto-saves context every 15 messages — decisions, discoveries, follow-ups |
| 🚨 **PreCompact Save** | Emergency capture before context window compression |
| 📋 **Commit Check** | Flags ecosystem drift after every git commit |
| 🔍 **Integration Audit** | Scans for stale cross-references before shipping changes |
| ✅ **CI Checks** | 4 automated checks on every PR: JSON validation, frontmatter, references, ecosystem integrity |

---

## Maintenance

Context that isn't maintained rots. These tasks keep your knowledge alive:

| Task | Schedule | What Happens |
|------|----------|-------------|
| **Index + health check** | Daily | Rebuild index, flag unmanaged docs, check boundaries and cross-references |
| **Daydream + lessons** | Monday | Strategic reflection + lessons capture + session pruning |
| **Mid-week daydream** | Wednesday | Deeper reflection on gaps, connections, and staleness |
| **Deep audit + inbox** | Friday | Thorough cluster audit, lessons consolidation, inbox processing |
| **Architecture review** | Monthly | Full architecture + ecosystem review with health score |

All 5 are set up automatically during onboarding. See [scheduling.md](docs/_bcos-framework/guides/scheduling.md) for exact task definitions.

---

## Updating

Framework updates are automatic. Your business context is never touched.

```bash
python .claude/scripts/update.py            # interactive
python .claude/scripts/update.py --yes      # auto-apply
```

The script updates skills, hooks, scripts, methodology docs, templates, and examples. Your `docs/`, `CLAUDE.md`, and `.private/` stay exactly as they are.

---

## Philosophy

**Living systems, not one-time setups.** Your business changes. Your context should evolve with it — structurally, not chaotically.

**Self-learning.** The lessons system captures what works and what doesn't. Your context architecture gets smarter with every cycle.

**The same discipline everywhere.** CLEAR principles apply to the tools themselves. The `ecosystem-manager` keeps skills and agents as ordered as the documents.

---

## Contributing

Contributions welcome — open an issue or submit a PR targeting the `dev` branch.

**CI checks run automatically on every PR.** Before pushing, you can run them locally:

```bash
python .claude/scripts/validate_frontmatter.py    # Check YAML metadata
python .claude/scripts/validate_references.py     # Check file paths resolve
python .claude/scripts/analyze_integration.py --ci  # Check ecosystem wiring
```

The fastest contribution path: **lessons learned.** As you use the system, it captures insights in `lessons.json`. If you find something universal, contribute it back.

---

## Origin

CLEAR Context OS was created by **[Guntis Coders](https://github.com/walm00)** after two years of building and operating context systems in production — first for competitive intelligence work, then for broader business context management.

The **CLEAR methodology** (Contextual Ownership, Linking, Elimination, Alignment, Refinement) emerged from a practical problem: AI context degrades silently over time, and no amount of one-time documentation prevents it. The solution required a system — not just documents, but ownership boundaries, automated maintenance, self-learning, and structured reflection.

The **Table of Context** concept — a living synthesis of what your business IS, distinct from the file inventory — was first articulated in a [Medium article on business context engineering](https://medium.com/businessacademy-lv/what-is-the-table-of-contexts-and-why-does-it-matter-8ec2a9557e9f) and became a core architectural pattern.

## License

[MIT](LICENSE) — Free to use, modify, distribute. No restrictions.

---

<p align="center">
  <strong>CLEAR Context OS</strong><br>
  Stop context rot. Start building knowledge that lasts.
</p>
