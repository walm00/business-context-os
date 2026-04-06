# Business Context OS - Ecosystem Map

This is your navigation hub for the Business Context OS ecosystem. Use this document to find any skill, agent, or reference material in the package.

---

## Skills

| Skill | Purpose | Tier |
|-------|---------|------|
| context-onboarding | Initial repo scan, produces Document Index | 1 |
| context-ingest | Integrate new sources into existing data points | 1 |
| core-discipline | Bootstrap - proactive skill discovery | 1 |
| doc-lint | Documentation quality validation | 1 |
| clear-planner | Implementation planning with sessions | 2 |
| context-audit | CLEAR compliance auditing | 2 |
| daydream | Strategic reflection on context architecture | 2 |
| ecosystem-manager | Agent/skill ecosystem maintenance | 2 |
| lessons-consolidate | Institutional knowledge maintenance | 2 |

**Tier 1** - Always active or frequently invoked. Foundation skills.
**Tier 2** - Invoked for specific workflows. Core operational skills.

---

## Agents

| Agent | Purpose | Invoked By |
|-------|---------|------------|
| explore | Fast read-only exploration | Manual |

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `.claude/skills/` | All skill definitions (SKILL.md files) |
| `.claude/agents/` | All agent definitions (AGENT.md files) |
| `.claude/quality/ecosystem/` | Ecosystem config, state, and lessons |
| `.claude/quality/sessions/` | Planning session artifacts |
| `.claude/scripts/` | Utility scripts (lessons search, consolidation) |
| `.claude/registries/` | Machine-readable indexes |
| `docs/methodology/` | CLEAR methodology reference |
| `docs/guides/` | User-facing guides |
| `docs/templates/` | Data point and cluster templates |

---

## Where Do I Start?

1. **New to Business Context OS?** Start with [Getting Started](docs/guides/getting-started.md)
2. **Defining your context?** See [Defining Your Context](docs/guides/defining-your-context.md)
3. **Maintaining existing context?** See [Maintenance Guide](docs/guides/maintenance-guide.md)
4. **Looking for a template?** Check [docs/templates/](docs/templates/)
5. **Understanding the methodology?** Read [CLEAR Principles](docs/methodology/clear-principles.md)

---

## Discovery Scripts

- **Find all agents:** `bash .claude/agents/agent-discovery/find_agents.sh`
- **Find all skills:** `bash .claude/skills/skill-discovery/find_skills.sh`
- **Search lessons:** `python .claude/scripts/find_lessons.py --tags #context`
- **Analyze lessons:** `python .claude/scripts/consolidate_lessons.py`
