# Adoption Tiers

**Not everyone needs everything. Start where it makes sense and grow when the need is real.**

---

## The Two Tiers

Business Context OS is designed for incremental adoption. You do not need to use everything from day one. Each tier builds on the previous one, adding capabilities as your needs grow.

```
Tier 1: Foundation         Tier 2: Skills
(Manual, Week 1)           (Assisted, Weeks 2-3)

Organized context     -->  Claude helps maintain
Clear ownership            Structured planning
Boundary protection        Automated audits
                           Strategic reflection
                           Ecosystem management
```

Most organizations should start at Tier 1 and stay there until they genuinely need more. There is no pressure to advance. A well-maintained Tier 1 architecture is more valuable than a neglected Tier 2 one.

---

## Tier 1: Foundation

**When:** Week 1. No automation needed.

**What you do:** Understand the CLEAR principles, define your data points, create your architecture canvas, and start using it in conversations with Claude.

### What you get

- **Organized context.** Every piece of business knowledge has a defined home.
- **Clear ownership.** Each data point has one person responsible for accuracy.
- **Boundary protection.** EXCLUSIVELY_OWNS and STRICTLY_AVOIDS prevent content from drifting between data points.
- **Consistent answers.** When someone asks "who is our audience?" or "what makes us different?" there is one trusted source.

### What it involves

| Activity | Time | Frequency |
|---|---|---|
| Read the CLEAR principles | 30 min | Once |
| Define 3-5 data points | 1-2 hours | Once (then add over time) |
| Create architecture canvas | 30 min | Once |
| Weekly quick scan | 5 min | Weekly |
| Monthly cluster audit | 30 min | Monthly |
| Quarterly deep review | 2 hours | Quarterly |

### Skills needed

None beyond what you already have. You are creating and editing markdown files and having conversations with Claude. If you can write a document and organize a folder, you have the skills.

### How to start

Follow the [getting-started.md](./getting-started.md) guide. It walks you through everything in about an hour.

### When you are ready for Tier 2

You will know it is time when:
- You have 5+ data points and maintaining them manually feels like overhead
- You want Claude to proactively check your context for problems
- You are making changes that affect multiple data points and want help tracing the impact
- You find yourself forgetting the weekly scan or rushing through the monthly audit

---

## Tier 2: Skills

**When:** Weeks 2-3, after your foundation is solid.

**What you do:** Activate skills that let Claude help you plan changes, audit your context, reflect on your architecture, and manage your ecosystem.

### What you get

Everything from Tier 1, plus:

- **Structured planning.** When you need to make changes that affect multiple data points, Claude creates a plan before you start, identifying all affected areas and the right order of operations.
- **Automated audits.** Claude can review your data points for boundary violations, stale content, ownership gaps, and relationship inconsistencies without you manually checking each one.
- **Strategic reflection.** Claude can step back and think about your context architecture at a higher level, identifying structural patterns and opportunities you might miss in day-to-day maintenance.
- **Ecosystem management.** Tools for maintaining your skills and agents as a system, creating new components when needed, and keeping everything aligned.
- **Institutional knowledge.** Lessons from past maintenance are captured and consolidated, so your context system learns from experience.

### Skills activated at this tier

Business Context OS includes built-in skills -- specialized capabilities that Claude can use when working with your context. At Tier 2, you activate five:

| Skill | What it does |
|---|---|
| **clear-planner** | Creates structured plans for context changes. When you say "I need to update our positioning for a new product launch," it maps out which data points are affected, in what order, and what to check. |
| **context-audit** | Reviews data points and clusters for problems: boundary violations, stale content, missing ownership, relationship gaps, contradictions between data points. |
| **daydream** | Strategic reflection on your context architecture. Steps back from day-to-day maintenance to think about structural patterns, gaps, and opportunities. |
| **ecosystem-manager** | Maintains the health of your skills and agents. Helps you create new components, audit existing ones, and keep the ecosystem aligned with your needs. |
| **lessons-consolidate** | Captures patterns from past maintenance. Over time, your context system gets smarter about where problems tend to emerge and what review cadences work best. |

### How to activate

Your skills live in the `.claude/skills/` folder. Activation is handled through your project configuration. If you need help, Claude can walk you through it -- just ask: "Help me activate Tier 2 skills for my context architecture."

### Scheduling recurring maintenance

Once skills are active, you can set up **automatic scheduled tasks** so Claude runs health checks, audits, and reflections on a recurring basis without you having to remember.

See [scheduling.md](./scheduling.md) for the full guide. The recommended schedule:

| Task | Frequency | What it does |
|------|-----------|--------------|
| Context health check | Weekly | Quick CLEAR audit + doc-lint across all data points |
| Strategic daydream | Bi-weekly | Reflection on architecture gaps and evolution |
| Deep audit + lessons | Monthly | Thorough cluster audit, lessons consolidation, repo re-scan |
| Architecture review | Quarterly | Full review of whether architecture matches business reality |

Start with the weekly health check. Add more as the value becomes clear.

### Time investment

| Activity | Time |
|---|---|
| Initial skill setup | 1-2 hours |
| Schedule setup | 30 min (one time) |
| Reviewing scheduled results | 5-15 min/week |
| Using skills in daily work | Ongoing (part of normal Claude conversations) |

---

## Growing Your Ecosystem

When you need more than what the package provides, you can create new skills and agents tailored to your specific needs.

### When to extend

You will know it is time when:
- You have a recurring workflow that could be automated with a skill
- You need a specialized agent for a domain-specific task
- Multiple people are maintaining context and you need coordination
- You want systematic review processes with formal validation steps

### How to extend

The `ecosystem-manager` skill is your guide for creating new components. It provides:

- **Ecosystem analysis.** Understand what you have, what is working, and where the gaps are.
- **Component creation.** Step-by-step guidance for creating new skills and agents that follow the package conventions.
- **Conflict detection.** Ensures new components do not overlap with or contradict existing ones.
- **Health tracking.** Monitors the overall ecosystem as it grows.

Ask Claude: "Help me create a new skill for [your use case]" and ecosystem-manager will guide the process.

### The package gives you the foundation

Business Context OS provides the methodology, the core skills, and the patterns. You extend it for your specific needs. There is no fixed ceiling -- the ecosystem grows with you.

---

## Choosing Your Tier

Use this decision helper to find your starting point.

### "I just need organized context"

**Start at Tier 1.**

You want your business knowledge organized, owned, and consistent. You are comfortable maintaining it manually with a weekly 5-minute habit and monthly check-ins. This is the right choice for most small teams and early-stage companies.

### "I want Claude to help me maintain it"

**Start at Tier 1, move to Tier 2 when your foundation is solid.**

You want the structure of Tier 1 plus automated help: audits that catch problems you might miss, plans that trace the impact of changes, and reflection that surfaces structural opportunities. Move to Tier 2 once you have 5+ well-maintained data points.

---

## Moving Between Tiers

Each tier builds on the previous one. Moving up adds capabilities without replacing what you already have.

### Tier 1 to Tier 2

**Prerequisites:**
- 5+ active data points with clear ownership
- Architecture canvas completed
- Weekly maintenance habit established
- At least one monthly cluster audit completed

**What changes:**
- You start using skills in Claude conversations (planning, auditing, reflection)
- Maintenance becomes partially automated
- You gain proactive problem detection

**What stays the same:**
- Your data points, clusters, and architecture
- Your maintenance rhythm (weekly, monthly, quarterly)
- Your ownership model

### Moving back down

You can always simplify. If Tier 2 feels like overhead, return to Tier 1. Your data points, ownership, and architecture remain intact regardless of tier. The tiers only affect how much automation assists your maintenance.

---

## Tier Comparison at a Glance

| | Tier 1: Foundation | Tier 2: Skills |
|---|---|---|
| **Setup time** | 2-3 hours | 1-2 hours additional |
| **Weekly effort** | 5 min | 5 min (audit review as needed) |
| **Skills needed** | Markdown editing, Claude conversations | Same as Tier 1 |
| **Best for** | Small teams, getting started | Growing teams, 5-10+ data points |
| **Main benefit** | Organization and ownership | Automated quality, planning, and reflection |
| **Risk of skipping** | N/A (must start here) | Missing problems, manual overhead |

---

**Start at Tier 1. Stay there until you need more. Each tier earns its place by solving real problems, not theoretical ones.**
