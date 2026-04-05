---
name: ecosystem-manager
description: Agent ecosystem expert for creating, maintaining, and auditing agents and skills. Prevents ecosystem drift and overlap.
category: ecosystem
---

# Ecosystem Manager

## Purpose

**This skill IS:**
- The steward of your agent and skill ecosystem
- The advisor for creating new agents or skills (overlap detection, gap analysis)
- The auditor for ecosystem health (drift, conflicts, unused components)
- The keeper of institutional knowledge (lessons learned)

**This skill IS NOT:**
- An implementation tool (it advises, you build)
- A substitute for clear-planner (use planner for implementation plans)
- Automatically invoked (call it when you need ecosystem guidance)

---

## When to Use

- "I want to create a new agent/skill" --> overlap detection first
- "Are there any conflicts in my ecosystem?" --> ecosystem audit
- "What agents/skills do I have?" --> inventory scan
- "Capture what we learned from this session" --> learnings capture

---

## Capabilities

### 1. Ecosystem Inventory

Run discovery to see what exists:

```bash
# Find existing agents
bash .claude/agents/agent-discovery/find_agents.sh

# Find existing skills
bash .claude/skills/skill-discovery/find_skills.sh
```

Compare against `.claude/quality/ecosystem/state.json` for drift detection.

### 2. Overlap Detection

Before creating anything new:
- Search existing agents/skills for similar purpose
- Check if the need can be met by extending an existing component
- Recommend: **extend**, **merge**, or **create new**

### 3. Ecosystem Health Audit

Check for:
- **Drift**: state.json doesn't match actual files
- **Conflicts**: multiple agents/skills claiming same responsibility
- **Orphans**: agents/skills that nothing references
- **Missing standards**: agents without proper AGENT.md structure

### 4. Learnings Capture

After significant work sessions, capture institutional knowledge:
- What worked well?
- What was surprising?
- What should be done differently next time?

Store in `.claude/quality/ecosystem/lessons.json` using the schema in `lessons-schema.md`.

### 5. New Agent/Skill Guidance

When creating new components, ensure:

**For Agents (AGENT.md):**
- Has frontmatter: name, description, category
- Has IS / IS NOT sections
- Has clear Input/Output specification
- Has Internal Workflow
- Doesn't overlap with existing agents

**For Skills (SKILL.md):**
- Has frontmatter: name, description, category
- Has IS / IS NOT sections
- Has clear "When to Use" section
- References only agents/skills that exist
- Doesn't overlap with existing skills

---

## Ecosystem Standards

### Agent vs Skill Decision

| Question | Agent | Skill |
|----------|-------|-------|
| Heavy analysis work? | Yes | No |
| Loads into user context? | No | Yes |
| Methodology/guidelines? | No | Yes |
| Needs isolated context? | Yes | No |
| Orchestrates other agents? | No | Yes |

### Naming Convention
- **kebab-case** for all directories
- AGENT.md for agents, SKILL.md for skills
- References in `references/` subdirectory

### Required Sections

**Agent:** Purpose (IS/IS NOT), Input, Output, Internal Workflow
**Skill:** Purpose (IS/IS NOT), When to Use, Capabilities or Workflow

---

## Post-Change Checklist

After any ecosystem change:

- [ ] Discovery scripts find the new/modified component
- [ ] state.json updated with current inventory
- [ ] No naming conflicts
- [ ] Cross-references resolve
- [ ] ECOSYSTEM-MAP.md updated if needed
- [ ] reference-index.json updated if new reference docs added

---

## References

- Ecosystem state: `.claude/quality/ecosystem/state.json`
- Ecosystem config: `.claude/quality/ecosystem/config.json`
- Lessons: `.claude/quality/ecosystem/lessons.json`
- Lessons schema: `.claude/quality/ecosystem/lessons-schema.md`
- Ecosystem map: `.claude/ECOSYSTEM-MAP.md`

> **Architecture docs:** For component standards, see [`docs/architecture/component-standards.md`](../../docs/architecture/component-standards.md)
