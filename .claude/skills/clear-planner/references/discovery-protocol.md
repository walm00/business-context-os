# Discovery Protocol

**Purpose:** Mandatory discovery steps that run BEFORE FIXED START in ALL scenarios.
**Consumer:** clear-planner (all scenarios)

---

## Overview

The Discovery Protocol ensures that agents, skills, and lessons are discovered BEFORE any work begins. This prevents:

- Recreating existing infrastructure
- Missing applicable overlays
- Ignoring institutional knowledge (lessons)
- Working without proper context

**Key Principle:** Discovery is NOT optional. It runs for EVERY scenario.

---

## Protocol Steps

### P0_001: Run Agent Discovery

**Purpose:** Find agents relevant to the current work.

**Execution:**

```bash
bash .claude/agents/agent-discovery/find_agents.sh
```

**Output:** List of agents that may be applicable.

**What to Look For:**

- Agents that handle similar work
- Agents that could be extended vs creating new
- Quality audit agents for FIXED END

---

### P0_002: Run Skill Discovery

**Purpose:** Find skills and overlays applicable to the scenario.

**Execution:**

```bash
# General discovery
bash .claude/skills/skill-discovery/find_skills.sh -q "{task description}"

# Scenario-specific overlays
bash .claude/skills/skill-discovery/find_skills.sh --overlays {scenario}
```

**Output:** List of skills, including overlay candidates.

**What to Look For:**

- Overlay skills for the scenario (core-discipline for agenting, context-audit for documentation)
- Skills that could be reused
- Skills that might conflict

---

### P0_003: Load Applicable Lessons

**Purpose:** Load institutional knowledge before work begins.

**Execution:**

```bash
# By scenario tags
python .claude/scripts/find_lessons.py --tags "#{scenario}"

# By specific topic
python .claude/scripts/find_lessons.py --keyword "{topic}"

# By involved agents
python .claude/scripts/find_lessons.py --keyword "{agent-name}"
```

**Output:** Relevant lessons to apply during this session.

**What to Look For:**

- Lessons about similar work done before
- Lessons about pitfalls to avoid
- Lessons about patterns to follow

**Example Tags by Scenario:**

| Scenario      | Tags to Query                              |
| ------------- | ------------------------------------------ |
| AGENTING      | `#agenting`, `#agent-design`, `#ecosystem` |
| DOCUMENTATION | `#documentation`, `#context-audit`         |

---

### P0_004: Establish Context

**Purpose:** Read authority documents and establish proper context.

**Execution:** Read relevant documents based on scenario:

| Scenario      | Documents to Read                                 |
| ------------- | ------------------------------------------------- |
| AGENTING      | Ecosystem map, ecosystem reference documentation  |
| DOCUMENTATION | Existing docs inventory, cross-reference registry |

**Output:** Context established for planning.

---

## Integration with Scenarios

### How Discovery Protocol Fits

```
DISCOVERY PROTOCOL (P0_xxx) - MANDATORY
  P0_001: Run agent discovery
  P0_002: Run skill discovery
  P0_003: Load applicable lessons
  P0_004: Establish context

FIXED START (P1_xxx) - Scenario-specific
  ...

DYNAMIC MIDDLE (Px_xxx) - Planner generates
  ...

FIXED END (Px_xxx) - Scenario-specific
  ...
```

### Task Schema for Discovery Protocol

```json
{
  "id": "P0_001",
  "phase": 0,
  "phaseName": "Discovery Protocol",
  "content": "Run agent discovery",
  "activeForm": "Discovering agents",
  "requiredCapability": {
    "type": "skill",
    "name": "core-discipline"
  },
  "invocationMethod": {
    "method": "inline",
    "note": "Discovery runs in current context"
  },
  "note": "MANDATORY"
}
```

---

## Why Discovery Protocol Matters

Without discovery:

- Create new agent that duplicates existing one
- Miss overlay skill that would help
- Ignore lesson about known pitfall
- Work without proper context

With discovery:

- Find existing agent to extend
- Apply relevant overlay skills
- Learn from past mistakes
- Work with full context

---

## Verification

After Discovery Protocol completes, verify:

| Check               | How to Verify                                 |
| ------------------- | --------------------------------------------- |
| Agents discovered   | List of relevant agents identified            |
| Skills discovered   | List of applicable skills/overlays identified |
| Lessons loaded      | Relevant lessons queried and noted            |
| Context established | Authority documents read if needed            |

---

## Related Documents

- `scenario-phases.md` - Scenario definitions with FIXED START/END
- `plan-manifest-schema.md` - Manifest schema with discoveryResults
- `core-discipline/SKILL.md` - Discovery mindset skill
- `.claude/quality/ecosystem/lessons.json` - Lessons database
