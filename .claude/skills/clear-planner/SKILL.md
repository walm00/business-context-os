---
name: clear-planner
description: |
  Creates implementation plans for ALL work scenarios. MANDATORY entry point for the PLAN phase.

  8-step workflow: Intent -> Discovery -> Scenario -> Context -> Template -> Approach -> Session -> Approval

  2 scenarios: AGENTING (ecosystem work), DOCUMENTATION (context creation & refinement)
allowed-tools: Read, Glob, Grep, Bash, Task
---

# Clear Planner

## Purpose

Creates implementation plans. Invoked FIRST for every user request.

**This skill IS:**

- The mandatory entry point for the PLAN phase of any significant work
- An 8-step workflow that produces approved implementation plans
- The bridge between user intent and structured execution

**This skill IS NOT:** Executing the plan (that's the builder's job)

---

## 8-Step Workflow

```
Step 1: Understand Intent        -> Create planning-manifest.json
    |
Step 2: Run Discovery
    |
Step 3: Detect Scenario (agenting / documentation)
    |
Step 4: Gather Context           <- Return here on "Adjust" or "Modify"
    |
Step 5: Load Scenario Template
    |
Step 6: Present Approach         -> GATE: "Proceed" / "Adjust"
    |
Step 7: Create Session Artifacts -> Creates plan-manifest.json + implementation-plan.md
    |
Step 8: Present Full Plan        -> GATE: "Approve" / "Modify" / "Cancel"
    |
HANDOFF to implementation
```

**Self-tracking:** See `references/planning-workflow-schema.md` for the planner's own state tracking.

---

## Step 1: Understand Intent

Parse the user's request:

- What do they want to accomplish?
- What files/systems are involved?
- Is there a clear objective?

**Create the session folder + planning-manifest.json in one step:**

```
.claude/quality/sessions/{YYYYMMDD}_{HHMMSS}_{slug}/
  planning-manifest.json   <- Track planner's own workflow state
```

**Do NOT call `mkdir` first.** Use the `Write` tool directly on
`.claude/quality/sessions/{YYYYMMDD}_{HHMMSS}_{slug}/planning-manifest.json`.
Write auto-creates any missing parent directories, and the shipped allowlist
already covers `Write(.claude/quality/sessions/**)` — so the folder pops into
existence without a permission prompt, regardless of OS or whether the
working-dir reference is relative or absolute. (Calling `mkdir` adds a Bash
permission round-trip with no benefit; previous skill versions did, which
caused intermittent prompts on Windows where path resolution sometimes
expanded to absolutes outside the allowlist.)

**If unclear:** Ask clarifying questions before proceeding.

---

## CRITICAL: Manifest Maintenance

**After EACH step, update `planning-manifest.json`:**

1. Mark current step `status: "completed"` with result
2. Set next step `status: "in_progress"`
3. Update `currentStep` integer
4. Populate result fields as work is done

```json
{
  "currentStep": 2,
  "workflow": {
    "steps": [
      { "step": 1, "name": "Understand Intent", "status": "completed", "result": "..." },
      { "step": 2, "name": "Run Discovery", "status": "in_progress" }
    ]
  }
}
```

**This is NON-NEGOTIABLE.** See `references/planning-workflow-schema.md` for full schema.

---

## Step 2: Run Discovery

**Run all three discovery scripts:**

```bash
# Find existing agents
bash .claude/agents/agent-discovery/find_agents.sh

# Find existing skills
bash .claude/skills/skill-discovery/find_skills.sh

# Find relevant lessons
python .claude/scripts/find_lessons.py --tags "#{scenarioType}"
```

**Document findings** for inclusion in manifest.

---

## Step 3: Detect Scenario

**Two scenarios based on what's affected:**

| Scenario          | Trigger                                    | Description                                        |
| ----------------- | ------------------------------------------ | -------------------------------------------------- |
| **AGENTING**      | Affects `/.claude` folders                 | Agent/skill creation, modification, ecosystem work |
| **DOCUMENTATION** | Affects `/docs` folder or context data points | Context creation, updates, refinement           |

**Mixed work:** If both apply, identify primary scenario and note secondary.

---

## Step 4: Gather Context (Scenario-Specific)

### AGENTING Scenario

**Recommended: Use ecosystem-manager skill for context gathering.**

Before creating or modifying agents/skills:
1. Run discovery scripts (Step 2 results)
2. Check for overlaps with existing agents/skills
3. Review relevant lessons
4. Identify gaps and design recommendations

If the ecosystem-manager skill is available, invoke it for overlap detection and ecosystem analysis.

### DOCUMENTATION Scenario

Self-discovery: review discovery results, identify related docs, check cross-references, verify alignment.

---

## Step 5: Load Scenario Template

Load the appropriate template from `references/scenario-phases.md` (defines phases, tasks, capabilities, and learnings capture). Templates: `agenting`, `documentation`.

---

## Step 6: Present Approach for Alignment

Present to user before creating documents: (1) restatement of intent, (2) key discovery findings (agents, overlaps, lessons), (3) proposed approach (scenario, phases, risks).

**Then use the `AskUserQuestion` tool:**
- Question: "Does this approach look right?"
- Options: **Proceed** (create plan artifacts) / **Adjust** (revise — tell me what to change)

### Gate 1: Approach Alignment

| Response | Behavior |
| --- | --- |
| **"Proceed"** | Continue to Step 7 |
| **"Adjust"** | Return to Step 4 with user feedback |

**WAIT for user response before Step 7.**

---

## Step 7: Create Session & Artifacts

**Only after user "Proceed" from Step 6.**

**Session folder already exists from Step 1.** Add the plan artifacts:

```
.claude/quality/sessions/{YYYYMMDD}_{HHMMSS}_{slug}/
  planning-manifest.json    <- Already exists (from Step 1)
  plan-manifest.json        <- Create now
  implementation-plan.md    <- Create now
```

**Create two files:**

### plan-manifest.json

```json
{
  "sessionId": "20260127_120000_feature-name",
  "triggeredBy": "clear-planner",
  "scenarioType": "documentation",
  "taskDescription": "Brief description of what we're doing",
  "createdAt": "2026-01-27T12:00:00Z",
  "planStatus": "awaiting_approval",
  "discoveryResults": {
    "agentsFound": [],
    "skillsFound": [],
    "relevantLessons": []
  },
  "plan": {
    "totalPhases": 5,
    "phases": ["Phase 1: ...", "Phase 2: ..."]
  },
  "tasks": [
    {
      "id": "P1_001",
      "phase": 1,
      "content": "Task description",
      "activeForm": "Doing the task",
      "status": "pending"
    }
  ]
}
```

### implementation-plan.md

Structure: Header (session ID, scenario, status) -> Discovery Results -> Problem Statement -> Proposed Solution -> Tasks by Phase (table per phase with ID/Task/Status) -> Artifacts (paths to session files) -> Next Actions (Approve/Modify/Cancel).

> For full template, see `references/plan-manifest-schema.md`

---

## Step 8: Present Full Plan for Approval

**Present to user with:**

1. **Summary** - What will be done
2. **Task list** - Organized by phase
3. **URLs to artifacts:**
   - `{session}/plan-manifest.json`
   - `{session}/implementation-plan.md`

**Then use the `AskUserQuestion` tool:**
- Question: "Ready to implement this plan?"
- Options: **Approve** (start implementation) / **Modify** (revise — tell me what to change) / **Cancel** (stop here)

### Gate 2: Plan Approval

| Response      | Behavior                                                                  |
| ------------- | ------------------------------------------------------------------------- |
| **"Approve"** | 1. Update manifests (status="approved") 2. Handoff to implementation      |
| **"Modify"**  | Return to Step 4 (Gather Context) with existing plan as additional context |
| **"Cancel"**  | Stop planning, archive session                                            |

**CRITICAL: STOP AND WAIT for user approval.**

Do not proceed with execution until user explicitly says "Approve".

**On "Approve":**

1. Update `planning-manifest.json`: Set Step 8 status="completed", gate.response="Approve"
2. Update `plan-manifest.json`: Set planStatus="approved", add userApproval object
3. Handoff to implementation

---

## Mandatory Final Phase (All Scenarios)

Every AGENTING plan **MUST** include an integration audit + ecosystem state update + learnings capture phase.
Every DOCUMENTATION plan **MUST** include a reference check + learnings capture phase.

These are defined in the scenario FIXED END (see `references/scenario-phases.md`) and are **non-negotiable**.

| Phase               | Purpose                              | How                                                       | Mandatory?          |
| ------------------- | ------------------------------------ | --------------------------------------------------------- | ------------------- |
| Integration Audit   | Detect stale references in ecosystem | `python .claude/scripts/analyze_integration.py --staged` + AI review | **YES** (AGENTING)  |
| Ecosystem State     | Keep inventory accurate              | Run discovery scripts, update state.json                  | **YES** (AGENTING)  |
| Reference Check     | Verify skill/hook path references    | `python .claude/scripts/analyze_integration.py --staged`  | **YES** (DOCUMENTATION) |
| Learnings Capture   | Institutional knowledge              | ecosystem-manager skill                                   | **YES** (all)       |

**Why this is mandatory:** Without integration audits, new components ship with stale cross-references in existing skills. The ecosystem drifts silently. The cost of fixing it later is 3-5x higher than catching it in the FIXED END.

---

## Scenario-Specific Requirements

| Scenario          | Key Requirement                                                    |
| ----------------- | ------------------------------------------------------------------ |
| **AGENTING**      | Check for ecosystem overlaps + run integration audit before commit |
| **DOCUMENTATION** | Verify cross-references + check skill/hook path references         |

---

## Plan Status States

| Status              | Meaning                | Next Action            |
| ------------------- | ---------------------- | ---------------------- |
| `awaiting_approval` | Plan ready for review  | Wait for user response |
| `approved`          | User approved          | Begin execution        |
| `needs_revision`    | User requested changes | Revise and re-present  |
| `completed`         | All tasks done         | Archive session        |

---

## References

**Schemas:**

- `references/planning-workflow-schema.md` - Planner's self-tracking (`planning-manifest.json`)
- `references/plan-manifest-schema.md` - Implementation plan (`plan-manifest.json`)

**Templates:**

- `references/scenario-phases.md` - Scenario phase templates (FIXED start/end + DYNAMIC middle)

**Discovery Scripts:**

- `.claude/agents/agent-discovery/find_agents.sh`
- `.claude/skills/skill-discovery/find_skills.sh`
- `.claude/scripts/find_lessons.py`
