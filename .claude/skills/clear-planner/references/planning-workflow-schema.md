# Planning Workflow Schema

**Version:** 1.0.0
**Purpose:** Defines the clear-planner's own workflow state tracking via `planning-manifest.json`

---

## Overview

The clear-planner tracks its own 8-step workflow state using a `planning-manifest.json` file. This enables:

- **Self-awareness** - Planner knows where it is in the workflow
- **State persistence** - Can resume after interruptions
- **Iteration tracking** - Counts how many times gates are cycled
- **Auditability** - Clear record of planning process

---

## When to Create

Create `planning-manifest.json` at **Step 1** (Understand Intent) for every new planning request.

**Location:** `.claude/quality/sessions/{sessionId}/planning-manifest.json`

---

## 8-Step Workflow

```
Step 1: Understand Intent          -> Create planning-manifest.json
    |
Step 2: Run Discovery
    |
Step 3: Detect Scenario
    |
Step 4: Gather Context             <- Return here on "Adjust" or "Modify"
    |
Step 5: Load Scenario Template
    |
Step 6: Present Approach           -> GATE: "Proceed" / "Adjust"
    |
Step 7: Create Session Artifacts   -> Creates plan-manifest.json + implementation-plan.md
    |
Step 8: Present Full Plan          -> GATE: "Approve" / "Modify" / "Cancel"
    |
HANDOFF to implementation
```

---

## Decision Gates

### Gate 1: Approach Alignment (Step 6)

| Response      | Behavior                                             |
| ------------- | ---------------------------------------------------- |
| **"Proceed"** | Continue to Step 7 (Create Session & Artifacts)      |
| **"Adjust"**  | Return to Step 4 (Gather Context) with user feedback |

**Why this gate exists:** Creating plan-manifest.json and implementation-plan.md takes effort. Get approach alignment first to avoid wasted work.

### Gate 2: Plan Approval (Step 8)

| Response      | Behavior                                                                   |
| ------------- | -------------------------------------------------------------------------- |
| **"Approve"** | Update manifests (status="approved") -> Handoff to implementation          |
| **"Modify"**  | Return to Step 4 (Gather Context) with existing plan as additional context |
| **"Cancel"**  | Stop planning, archive session                                             |

---

## Planning Manifest Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Planning Manifest",
  "type": "object",
  "required": ["planningSessionId", "triggeredBy", "createdAt", "currentStep", "workflow"],

  "properties": {
    "planningSessionId": {
      "type": "string",
      "description": "Session ID (matches folder name)",
      "pattern": "^[0-9]{8}_[0-9]{6}_[a-z-]+$"
    },

    "triggeredBy": {
      "type": "string",
      "const": "clear-planner",
      "description": "Always clear-planner for this manifest type"
    },

    "createdAt": {
      "type": "string",
      "format": "date-time"
    },

    "currentStep": {
      "type": "integer",
      "minimum": 1,
      "maximum": 8,
      "description": "Current step number in workflow"
    },

    "workflow": {
      "$ref": "#/$defs/workflow"
    },

    "gates": {
      "$ref": "#/$defs/gates"
    },

    "intent": {
      "type": "string",
      "description": "Brief description of user's intent"
    },

    "scenarioType": {
      "type": "string",
      "enum": ["agenting", "documentation"],
      "description": "Detected scenario type"
    },

    "discoveryResults": {
      "type": "object",
      "description": "Results from Step 2 discovery"
    }
  },

  "$defs": {
    "workflow": {
      "type": "object",
      "required": ["steps"],
      "properties": {
        "steps": {
          "type": "array",
          "items": { "$ref": "#/$defs/step" },
          "minItems": 8,
          "maxItems": 8
        }
      }
    },

    "step": {
      "type": "object",
      "required": ["step", "name", "status"],
      "properties": {
        "step": {
          "type": "integer",
          "minimum": 1,
          "maximum": 8
        },
        "name": {
          "type": "string"
        },
        "status": {
          "type": "string",
          "enum": ["pending", "in_progress", "completed"]
        },
        "result": {
          "type": "string",
          "description": "Optional result (e.g., scenario type for Step 3)"
        },
        "iterations": {
          "type": "integer",
          "description": "Number of times this step was executed"
        },
        "gate": {
          "$ref": "#/$defs/gateResult"
        }
      }
    },

    "gateResult": {
      "type": "object",
      "properties": {
        "response": {
          "type": "string",
          "description": "User's response at gate"
        },
        "iterations": {
          "type": "integer",
          "description": "Number of gate cycles"
        }
      }
    },

    "gates": {
      "type": "object",
      "properties": {
        "approach": {
          "type": "object",
          "properties": {
            "options": {
              "type": "array",
              "items": { "type": "string" },
              "const": ["Proceed", "Adjust"]
            },
            "behavior": {
              "type": "object",
              "properties": {
                "Proceed": { "const": "Continue to Step 7 (Create Session & Artifacts)" },
                "Adjust": { "const": "Return to Step 4 (Gather Context) with feedback" }
              }
            }
          }
        },
        "approval": {
          "type": "object",
          "properties": {
            "options": {
              "type": "array",
              "items": { "type": "string" },
              "const": ["Approve", "Modify", "Cancel"]
            },
            "behavior": {
              "type": "object",
              "properties": {
                "Approve": { "const": "Update manifests (status=approved) -> Handoff to implementation" },
                "Modify": {
                  "const": "Return to Step 4 (Gather Context) with existing plan as context"
                },
                "Cancel": { "const": "Stop planning" }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## Example Planning Manifest

```json
{
  "planningSessionId": "20260127_060000_feature-dashboard",
  "triggeredBy": "clear-planner",
  "createdAt": "2026-01-27T06:00:00Z",
  "currentStep": 6,
  "workflow": {
    "steps": [
      { "step": 1, "name": "Understand Intent", "status": "completed" },
      { "step": 2, "name": "Run Discovery", "status": "completed" },
      { "step": 3, "name": "Detect Scenario", "status": "completed", "result": "documentation" },
      { "step": 4, "name": "Gather Context", "status": "completed", "iterations": 2 },
      { "step": 5, "name": "Load Scenario Template", "status": "completed" },
      { "step": 6, "name": "Present Approach for Alignment", "status": "in_progress" },
      { "step": 7, "name": "Create Session & Artifacts", "status": "pending" },
      { "step": 8, "name": "Present Full Plan for Approval", "status": "pending" }
    ]
  },
  "gates": {
    "approach": {
      "options": ["Proceed", "Adjust"],
      "behavior": {
        "Proceed": "Continue to Step 7 (Create Session & Artifacts)",
        "Adjust": "Return to Step 4 (Gather Context) with feedback"
      }
    },
    "approval": {
      "options": ["Approve", "Modify", "Cancel"],
      "behavior": {
        "Approve": "Handoff to implementation",
        "Modify": "Return to Step 4 (Gather Context) with existing plan as context",
        "Cancel": "Stop planning"
      }
    }
  },
  "intent": "Update company overview after strategic pivot",
  "scenarioType": "documentation",
  "discoveryResults": {
    "agentsFound": ["explore"],
    "skillsFound": ["context-audit", "doc-lint"]
  }
}
```

---

## Session Folder Structure

After completing the 8-step workflow, a session folder contains:

```
.claude/quality/sessions/{sessionId}/
  planning-manifest.json    <- Planner's workflow state (created Step 1)
  plan-manifest.json        <- Implementation plan (created Step 7)
  implementation-plan.md    <- Human-readable plan (created Step 7)
```

---

## References

- Plan Manifest Schema: `plan-manifest-schema.md`
- Scenario Phases: `scenario-phases.md`
- Clear Planner SKILL: `../SKILL.md`
