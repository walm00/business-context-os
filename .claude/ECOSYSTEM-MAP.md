# CLEAR Context OS - Ecosystem Map

This is your navigation hub for the CLEAR Context OS ecosystem. Use this document to find any skill, agent, or reference material in the package.

---

## Skills

| Skill | Purpose | Tier |
|-------|---------|------|
| context-onboarding | First-run onboarding: scans repo, drafts data points, sets up maintenance | 1 |
| context-ingest | Integrate new sources into existing data points | 1 |
| context-mine | Extract context from conversations, chat exports, meeting transcripts | 1 |
| core-discipline | Bootstrap - proactive skill discovery | 1 |
| doc-lint | Documentation quality validation | 1 |
| clear-planner | Implementation planning with sessions | 2 |
| context-audit | CLEAR compliance auditing | 2 |
| daydream | Strategic reflection on context architecture | 2 |
| ecosystem-manager | Agent/skill ecosystem maintenance | 2 |
| lessons-consolidate | Institutional knowledge maintenance | 2 |
| todo-utilities | Shared TodoWrite patterns (reference, not invocable) | — |

**Tier 1** - Always active or frequently invoked. Foundation skills.
**Tier 2** - Invoked for specific workflows. Core operational skills.
**—** - Reference/utility (not directly invoked, used by other skills).

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
| `.claude/scripts/` | Utility scripts (index builder, pruning, cross-ref analysis, integration audit, lessons, updates) |
| `.claude/hooks/` | Claude Code enforcement hooks |
| `.claude/registries/` | Machine-readable indexes |
| `docs/methodology/` | CLEAR methodology reference |
| `docs/guides/` | User-facing guides |
| `docs/templates/` | Data point and cluster templates |
| `docs/architecture/` | Developer/contributor architecture docs |

---

## Where Do I Start?

1. **New to CLEAR Context OS?** Start with [Getting Started](docs/guides/getting-started.md)
2. **Defining your context?** See [Defining Your Context](docs/guides/defining-your-context.md)
3. **Maintaining existing context?** See [Maintenance Guide](docs/guides/maintenance-guide.md)
4. **Looking for a template?** Check [docs/templates/](docs/templates/)
5. **Understanding the methodology?** Read [CLEAR Principles](docs/methodology/clear-principles.md)

---

## CI Checks (GitHub Actions)

Automated checks run on every push and PR. Defined in `.github/workflows/ci.yml`.

| Job | What it validates | Run locally |
|-----|-------------------|-------------|
| **validate-json** | All JSON files parse correctly | `python -m json.tool .claude/quality/ecosystem/state.json` |
| **validate-frontmatter** | YAML frontmatter on all managed markdown | `python .github/scripts/validate_frontmatter.py` |
| **validate-references** | All registry paths resolve, state.json accuracy | `python .github/scripts/validate_references.py` |
| **validate-ecosystem** | Ecosystem wiring (install.sh, settings.json coverage) | `python .claude/scripts/analyze_integration.py --ci` |

---

## Discovery Scripts

- **Rebuild Document Index:** `python .claude/scripts/build_document_index.py`
- **Dry run (preview only):** `python .claude/scripts/build_document_index.py --dry-run`
- **Find all agents:** `bash .claude/agents/agent-discovery/find_agents.sh`
- **Find all skills:** `bash .claude/skills/skill-discovery/find_skills.sh`
- **Search lessons:** `python .claude/scripts/find_lessons.py --tags #context`
- **Analyze lessons:** `python .claude/scripts/consolidate_lessons.py`
- **Cross-reference analysis:** `python .claude/scripts/analyze_crossrefs.py`
- **Integration audit:** `python .claude/scripts/analyze_integration.py --staged`
- **Generate wake-up context:** `python .claude/scripts/generate_wakeup_context.py`
- **Prune old sessions:** `python .claude/scripts/prune_sessions.py`
- **Prune old diary entries:** `python .claude/scripts/prune_diary.py`
- **Update framework:** `python .claude/scripts/update.py`
