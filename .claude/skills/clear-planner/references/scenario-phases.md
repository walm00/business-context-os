# Scenario Phases

**Purpose:** Defines phase structure for each scenario type with FIXED start/end and DYNAMIC middle.
**Consumer:** clear-planner ONLY (Step 5: Load Scenario Template)

---

## Structure Overview

Every scenario follows this pattern:

```
FIXED START (always)
  Required discovery and analysis tasks

DYNAMIC MIDDLE (planner generates)
  Based on user request - specific implementation work

FIXED END (always)
  Verification and learnings capture
```

**Why this structure:**

- FIXED START ensures proper discovery and analysis before work
- DYNAMIC MIDDLE adapts to the specific request
- FIXED END ensures verification and learnings capture

---

## DISCOVERY PROTOCOL (All Scenarios)

**Every scenario MUST begin with the Discovery Protocol before FIXED START.**

This ensures agents, skills, and lessons are discovered BEFORE any work begins.

| ID     | Task                    | Capability      | Invocation | Note          |
| ------ | ----------------------- | --------------- | ---------- | ------------- |
| P0_001 | Run agent discovery     | core-discipline | `inline`   | **MANDATORY** |
| P0_002 | Run skill discovery     | core-discipline | `inline`   | **MANDATORY** |
| P0_003 | Load applicable lessons | core-discipline | `inline`   | **MANDATORY** |
| P0_004 | Establish context       | core-discipline | `inline`   | **MANDATORY** |

**Discovery Protocol Details:**

```
P0_001: Run agent discovery
  - Execute: bash .claude/agents/agent-discovery/find_agents.sh
  - Purpose: Find agents relevant to this work
  - Output: List of applicable agents

P0_002: Run skill discovery
  - Execute: bash .claude/skills/skill-discovery/find_skills.sh -q "{task description}"
  - Purpose: Find skills/overlays applicable to scenario
  - Output: List of applicable skills

P0_003: Load applicable lessons
  - Execute: python .claude/scripts/find_lessons.py --tags "{relevant tags}"
  - Purpose: Load institutional knowledge before work
  - Output: Relevant lessons to apply

P0_004: Establish context
  - Read authority documents if needed
  - Purpose: Ensure proper context before planning
  - Output: Context established
```

_Note: P0_xxx runs BEFORE P1_xxx in ALL scenarios. See `discovery-protocol.md` for full details._

---

## AGENTING Scenario

**Trigger:** Work affects `/.claude` folders (agents, skills, ecosystem)

### FIXED START

| ID     | Task                                | Capability      | Invocation | Note |
| ------ | ----------------------------------- | --------------- | ---------- | ---- |
| P1_001 | Discover existing agents and skills | core-discipline | `inline`   | -    |
| P1_002 | Check for ecosystem overlaps        | ecosystem-manager | `skill`  | Recommended |

### DYNAMIC MIDDLE (planner generates)

Based on request, include tasks like:

- Design architecture
- Create AGENT.md/SKILL.md
- Create reference documentation
- Test agent invocation

### FIXED END

| ID     | Task                          | Capability                     | Invocation | Note            |
| ------ | ----------------------------- | ------------------------------ | ---------- | --------------- |
| Px_001 | Run JSON structure validation | doc-lint                       | `inline`   | If JSON files   |
| Px_002 | Run markdown quality check    | doc-lint                       | `inline`   | MD040, links    |
| Px_003 | Run integration audit         | ecosystem-manager              | `inline`   | **MANDATORY**   |
| Px_004 | Update ecosystem state        | ecosystem-manager              | `inline`   | **MANDATORY**   |
| Px_005 | Capture learnings             | ecosystem-manager              | `skill`    | **MANDATORY**   |

**Px_003 Integration Audit** — the step that was missing. Run BEFORE committing:

```bash
# Mechanical scan: what might be affected?
python .claude/scripts/analyze_integration.py --staged
```

Then apply AI reasoning to the script's output:

1. **Existing skills/agents**: For each, check if it references, consumes, or produces anything that overlaps with the new/changed files. If yes, flag which section needs updating and why.
2. **install.sh**: Does it install the new files? If not, add them.
3. **settings.json**: If new hooks were created, are they registered?
4. **.gitignore**: Do new generated/state paths need ignoring?
5. **state.json**: Does the ecosystem inventory match reality?

**Output**: Table of `file → needs update → why`. If gaps found, add fix tasks to the plan and execute them BEFORE committing. Do NOT skip this step.

**Px_004 Update Ecosystem State**:

```bash
bash .claude/agents/agent-discovery/find_agents.sh
bash .claude/skills/skill-discovery/find_skills.sh
```

Compare output against `.claude/quality/ecosystem/state.json`. Update counts, lists, and `lastUpdated`.

---

## DOCUMENTATION Scenario

**Trigger:** Work affects `/docs` folder

### FIXED START

| ID     | Task                            | Capability      | Invocation | Note |
| ------ | ------------------------------- | --------------- | ---------- | ---- |
| P1_001 | Discover existing documentation | core-discipline | `inline`   | -    |
| P1_002 | Gather context from codebase    | core-discipline | `inline`   | -    |

### DYNAMIC MIDDLE (planner generates)

Based on request, include tasks like:

- Create initial draft
- Review for completeness
- Apply refinements
- Update cross-references

### FIXED END

| ID     | Task                                      | Capability                     | Invocation | Note            |
| ------ | ----------------------------------------- | ------------------------------ | ---------- | --------------- |
| Px_001 | Run markdown quality check                | doc-lint                       | `inline`   | MD040, links    |
| Px_002 | Verify cross-references                   | doc-lint                       | `inline`   | Internal links  |
| Px_003 | Check skill/hook references to changed paths | ecosystem-manager           | `inline`   | **MANDATORY**   |
| Px_004 | Capture learnings                         | ecosystem-manager              | `skill`    | **MANDATORY**   |

**Px_003 Reference Check** — verify that skills/hooks referencing changed doc paths still work:

```bash
python .claude/scripts/analyze_integration.py --staged
```

If the script flags skills that reference renamed/moved/deleted doc paths, fix them before committing.

---

## Task Field Reference

| Field                | Required | Description                                     |
| -------------------- | -------- | ----------------------------------------------- |
| `id`                 | Yes      | Format: `P{phase}_{sequence}` (e.g., `P1_001`)  |
| `phase`              | Yes      | Phase number (integer)                          |
| `content`            | Yes      | Task description (imperative form)              |
| `activeForm`         | Yes      | Present tense for progress display              |
| `requiredCapability` | Yes      | `{ "type": "agent" | "skill", "name": "..." }`  |
| `invocationMethod`   | Yes      | HOW to invoke the capability (see below)        |
| `skillOverlays`      | No       | Active methodology skills during task           |
| `outputArtifact`     | No       | Expected output file path                       |
| `note`               | No       | Additional context (e.g., "RECOMMENDED")        |
| `status`             | Auto     | `pending` -> `in_progress` -> `completed`        |

### invocationMethod Field

Specifies HOW to invoke the required capability:

```json
"invocationMethod": {
  "method": "task" | "skill" | "inline",
  "skillName": "skill-name",
  "note": "Additional context"
}
```

| Method   | Description                        | When to Use                         |
| -------- | ---------------------------------- | ----------------------------------- |
| `task`   | Invoke via Task tool (new context) | Agents that need isolated execution |
| `skill`  | Invoke via skill tool              | Skills                              |
| `inline` | Execute in current context         | Overlay skills, lightweight work    |

---

## Variables

| Variable        | Description              | Example                                            |
| --------------- | ------------------------ | -------------------------------------------------- |
| `{session}`     | Session folder           | `.claude/quality/sessions/20260127_120000_feature` |
| `{name}`        | Agent/skill/feature name | `score-calculator`                                 |
| `{target-path}` | Target file path         | `docs/context/feature.md`                          |
