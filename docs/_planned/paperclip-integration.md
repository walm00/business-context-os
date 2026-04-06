---
name: "Paperclip Integration Exploration"
type: reference
cluster: "Strategy & Operations"
version: "1.1.0"
status: draft
created: "2026-04-06"
last-updated: "2026-04-06"
relationships:
  - type: informs
    target: "docs/current-state.md"
    context: "Potential future tooling decision"
---

# Paperclip + CLEAR Context OS Integration

## What Is Paperclip?

[paperclipai/paperclip](https://github.com/paperclipai/paperclip) is an open-source AI agent orchestration platform. It coordinates teams of AI agents (Claude Code, Codex, etc.) toward shared business objectives with org charts, task ticketing, budget enforcement, and audit trails.

**Tagline:** "If OpenClaw is an employee, Paperclip is the company."

### Key Capabilities

- **Heartbeat scheduler** — agents wake on cron schedules or event triggers (task assignment, @-mentions)
- **Budget enforcement** — per-agent monthly token/cost limits, atomically enforced
- **Audit system** — immutable logs with full tool-call tracing
- **Agent abstraction** — supports any agent via HTTP or process adapters (Claude Code is first-class)
- **Task management** — work distribution with goal ancestry tracking
- **Multi-tenancy** — data isolation across companies

### Architecture

- **Monorepo**: pnpm workspaces — `server/` (Express/Node.js), `ui/` (React), `cli/`, `packages/db` (Prisma), adapters, plugins
- **Database**: PostgreSQL required (embedded PGlite for local dev, external for production)
- **Storage**: local disk or S3 (pluggable provider)
- **Agent model**: server-push — Paperclip spawns agents as subprocesses or calls HTTP endpoints. Agents don't poll.

## Why These Two Systems Are Complementary

| Concern | BCOS Provides | Paperclip Provides |
|---------|--------------|-------------------|
| **What's true** | Owned, linked, maintained business context | Nothing — it has no knowledge layer |
| **Who does what** | Nothing — single-agent only | Org charts, roles, task assignment |
| **When things happen** | Manual skill invocation | Heartbeat scheduling, cron, event triggers |
| **How much it costs** | Nothing | Per-agent budget caps, cost tracking |
| **What happened** | Version history in git | Immutable audit logs with decision reasoning |

**BCOS is the knowledge layer. Paperclip is the orchestration layer.**

Without BCOS, Paperclip agents have no structured, maintained context — they'll suffer from context rot just like any other system. Without Paperclip, BCOS maintenance depends on a human remembering to run audits, daydreams, and inbox triage.

## How They Work Together

### The Two-Layer Model

**Important:** These are two completely independent environments. Paperclip does NOT run on your machine. It runs its own headless Claude Code instances as subprocesses on the Paperclip server (VPS, Railway, Docker container). Your interactive Claude Code and Paperclip's autonomous agents share only the git repo — nothing else.

```
┌──────────────────────────────────────────────────┐
│  YOUR MACHINE (interactive layer)                 │
│  You + Claude Code running locally/interactively  │
│  - Ask questions, get answers from BCOS context   │
│  - Trigger skills manually (audit, daydream)      │
│  - Make decisions, update strategy                │
│  - Push changes → shared git repo                 │
└──────────────┬───────────────────────────────────┘
               │ shared git repo on GitHub
┌──────────────▼───────────────────────────────────┐
│  PAPERCLIP SERVER (autonomous layer)              │
│  Runs on Railway / Fly.io / VPS / Docker          │
│  Has its own Claude Code installed headlessly      │
│  - Heartbeat fires → spawns `claude --headless`   │
│  - Agent runs as subprocess ON THE SERVER          │
│  - Reads BCOS context from cloned repo            │
│  - Performs scheduled maintenance:                 │
│    · Context audits (CLEAR compliance)            │
│    · Daydream sessions (strategic reflection)     │
│    · Inbox triage (process _inbox/ material)      │
│    · Lessons consolidation                        │
│  - Commits + pushes results → shared git repo     │
│  - Process exits, Paperclip logs cost + output    │
│  - Budget-capped, audit-logged                    │
└──────────────────────────────────────────────────┘
```

### Integration Method: Git as the Bridge

**File-sync via git** is the right approach (not API). Reasons:

1. BCOS is markdown files with YAML frontmatter — no database, no API to build
2. Paperclip already spawns Claude Code as a subprocess with a workspace directory — that workspace **is** the BCOS repo
3. Git provides versioning, conflict detection, and audit trail for free
4. Zero new code required to start — just configure Paperclip to point at the repo
5. BCOS's topical ownership boundaries naturally minimize merge conflicts (two agents rarely edit the same file)

### Context Ownership Is Not User Ownership

BCOS's "single owner per document" refers to **topical ownership** — which document owns which subject matter — not user-level access control. This makes multi-agent integration clean: any Paperclip agent can write to any document, and BCOS's ownership boundaries tell each agent *where* to put information about a given topic. No ACL conflicts.

## Deployment Architecture

### Paperclip Server Requirements

Paperclip's server is a **long-running Node.js process** — it cannot run on Vercel serverless. It manages heartbeat scheduling, WebSocket connections, and agent subprocess spawning.

**Viable hosting options:**

| Option | Pros | Cons |
|--------|------|------|
| **Railway** | Easy Node.js + Postgres, git deploy | Cost scales with usage |
| **Fly.io** | Persistent VMs, good for long-running | More config than Railway |
| **Render** | Simple, supports background workers | Free tier sleeps |
| **VPS** (Hetzner, DO) | Cheapest for always-on | More ops work |
| **Docker** (anywhere) | Pre-built Dockerfile included | Need to manage infra |

### PostgreSQL

- **Local dev**: embedded PGlite — zero setup, just `pnpm dev`
- **Production**: any external Postgres instance
- **Supabase works** — Paperclip just needs a standard `DATABASE_URL` connection string. Supabase provides exactly that.

### Suggested Stack

```
Paperclip server  → Railway / Fly.io (persistent Node.js)
PostgreSQL        → Supabase (managed Postgres, free tier available)
BCOS repo         → GitHub (shared between you and Paperclip agents)
Paperclip UI      → Same server (bundled in Docker) or Vercel (static)
```

## Concrete Agent Setup

### Agent 1: Context Auditor

- **Schedule**: Weekly (Sunday night)
- **Task**: Run BCOS context-audit skill, commit findings
- **Budget**: Low (mostly reads, light writes)

### Agent 2: Inbox Processor

- **Schedule**: Daily
- **Task**: Triage `docs/_inbox/` — route material to `_planned/` or integrate into active docs
- **Budget**: Medium

### Agent 3: Daydreamer

- **Schedule**: Bi-weekly
- **Task**: Run BCOS daydream skill — strategic reflection on context gaps and evolution
- **Budget**: Medium

### Agent 4: Lessons Consolidator

- **Schedule**: Weekly
- **Task**: Analyze lessons for staleness, overlaps, gaps
- **Budget**: Low

## Open Questions

1. **Conflict resolution** — When a Paperclip agent and the interactive user edit the same file simultaneously, how to handle? Git merge is the default, but should Paperclip agents create PRs instead of direct commits for review?
2. **Agent CLAUDE.md** — Should Paperclip agents get a different CLAUDE.md than the interactive user? Probably yes — more constrained, task-specific instructions.
3. **Notification loop** — When a Paperclip agent finds issues during audit, how does the interactive user get notified? GitHub issues? PR comments? A dedicated `_inbox/agent-findings/` folder?
4. **Maturity** — Paperclip is early-stage open source. How stable is it for production use?

## Next Steps

1. Run Paperclip locally (`pnpm dev`) and register a Claude Code agent
2. Point the agent at a clone of the BCOS repo
3. Configure a simple heartbeat (daily context audit)
4. Validate the git-sync workflow end-to-end
5. Evaluate stability before committing to production deployment
