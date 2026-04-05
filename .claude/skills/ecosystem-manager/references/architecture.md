# Ecosystem Architecture Reference

## Core Principles

### Skills Orchestrate, Agents Execute

- **Skills** load into the user's context and provide guidance, workflows, methodology
- **Agents** are invoked via Task tool and run in isolated context for heavy analysis work
- Skills can invoke agents; agents cannot invoke other agents (Claude Code constraint)

### Session Management

- Each significant work session creates a folder under `.claude/quality/sessions/`
- Session format: `{YYYYMMDD}_{HHMMSS}_{slug}`
- Sessions contain manifests, plans, and artifacts from the work

### Discovery-First Inventory

- Always run discovery scripts before assuming what exists
- Discovery scripts are the source of truth, not memory
- `find_agents.sh` and `find_skills.sh` scan the filesystem

---

## Architecture Patterns

### 1. Simple Skill

A standalone skill with no agents or references.

```
.claude/skills/{skill-name}/
  SKILL.md
```

**When to use:** Guidelines, methodology, lightweight workflows.

### 2. Simple Agent

A standalone agent with no references.

```
.claude/agents/{agent-name}/
  AGENT.md
```

**When to use:** Heavy analysis, isolated execution context.

### 3. Skill Plus References

A skill with supporting reference documents.

```
.claude/skills/{skill-name}/
  SKILL.md
  references/
    reference-doc-1.md
    reference-doc-2.md
```

**When to use:** Skills that need templates, schemas, or detailed reference material.

### 4. Overlay Skill

A skill that remains active throughout task execution, influencing HOW work is done.

```
.claude/skills/{overlay-name}/
  SKILL.md    # Contains methodology, not workflow steps
```

**When to use:** Cross-cutting concerns like verification, discipline, testing methodology.

---

## Key Relationships

```
User Request
    |
    v
clear-planner (skill) -- creates plan
    |
    v
ecosystem-manager (skill) -- checks ecosystem health
    |
    v
Implementation -- executes plan
    |
    v
lessons-consolidate (skill) -- maintains knowledge base
```

---

## Directory Structure

```
.claude/
  agents/
    {agent-name}/
      AGENT.md
      references/        (optional)
    agent-discovery/
      find_agents.sh     (discovery script)
  skills/
    {skill-name}/
      SKILL.md
      references/        (optional)
    skill-discovery/
      find_skills.sh     (discovery script)
  quality/
    ecosystem/
      state.json         (current inventory snapshot)
      config.json        (ecosystem configuration)
      lessons.json       (institutional knowledge)
      lessons-schema.md  (schema for lessons)
    sessions/
      {session-id}/      (per-session artifacts)
  ECOSYSTEM-MAP.md       (high-level ecosystem overview)
```
