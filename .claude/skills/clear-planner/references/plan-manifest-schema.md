# Plan Manifest Schema Reference

**Version:** 2.0.0
**Type:** PLAN manifests (implementation plans)

---

## Purpose & Consumers

This document defines the JSON schema for **plan manifests** (`plan-manifest.json`) - the implementation plan artifacts created by clear-planner at Step 7.

| Consumer              | How They Use This                                     |
| --------------------- | ----------------------------------------------------- |
| **clear-planner**     | Creates plan-manifest.json following this schema      |
| **builder**           | Validates approval status, reads tasks, executes plan |
| **ecosystem-manager** | Reads for learnings capture phase                     |

---

## Manifest Types in Ecosystem

**This schema is for PLAN manifests only.** Other manifest types exist:

| Type                  | Location                                               | Purpose                  | Schema                        |
| --------------------- | ------------------------------------------------------ | ------------------------ | ----------------------------- |
| **Planning Manifest** | `.claude/quality/sessions/{id}/planning-manifest.json` | Planner's workflow state | `planning-workflow-schema.md` |
| **Plan Manifest**     | `.claude/quality/sessions/{id}/plan-manifest.json`     | Implementation plan      | **This document**             |

**Do not confuse:**

- `planning-manifest.json` = Planner's own workflow state (8 steps)
- `plan-manifest.json` = The implementation plan being created

---

## Overview

Plan manifests are JSON documents that track the state of implementation plans. They enable:

- **Approval tracking** - Plans require explicit user approval before execution
- **State persistence** - Sessions survive across conversations
- **Task management** - Tasks are generated from manifests, not free-form
- **Audit trail** - Complete history of plan evolution and execution

---

## Complete Manifest Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Planning Manifest",
  "type": "object",
  "required": [
    "sessionId",
    "triggeredBy",
    "scenarioType",
    "taskDescription",
    "createdAt",
    "planStatus",
    "planStatusHistory"
  ],

  "properties": {
    "sessionId": {
      "type": "string",
      "description": "Unique identifier for this session (date-first for chronological sorting)",
      "pattern": "^[0-9]{8}_[0-9]{6}_[a-z-]+$",
      "examples": ["20260124_143052_feature-dashboard", "20260124_150000_agent-creation"]
    },

    "triggeredBy": {
      "type": "string",
      "enum": ["clear-planner", "ecosystem-manager", "manual"],
      "description": "Which agent/skill initiated this planning session"
    },

    "scenarioType": {
      "type": "string",
      "enum": ["agenting", "documentation"],
      "description": "Type of work being planned. Two scenarios: agenting (agents/skills), documentation (context docs)"
    },

    "taskDescription": {
      "type": "string",
      "minLength": 10,
      "description": "Human-readable description of what this plan accomplishes"
    },

    "createdAt": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of manifest creation"
    },

    "planStatus": {
      "type": "string",
      "enum": [
        "draft",
        "awaiting_approval",
        "approved",
        "needs_revision",
        "rejected",
        "abandoned",
        "in_progress",
        "completed"
      ],
      "description": "Current status of the plan"
    },

    "planStatusHistory": {
      "type": "array",
      "items": { "$ref": "#/$defs/statusHistoryEntry" },
      "description": "Complete history of status changes"
    },

    "userApproval": {
      "oneOf": [{ "type": "null" }, { "$ref": "#/$defs/userApproval" }],
      "description": "User approval details, null if not yet reviewed"
    },

    "discoveryResults": {
      "$ref": "#/$defs/discoveryResults",
      "description": "Results from capability discovery phase"
    },

    "requiredCapabilities": {
      "type": "array",
      "items": { "$ref": "#/$defs/capability" },
      "description": "Agents/skills needed to execute this plan"
    },

    "tasks": {
      "type": "array",
      "items": { "$ref": "#/$defs/task" },
      "description": "Individual tasks to be executed"
    },

    "plan": {
      "$ref": "#/$defs/planDetails",
      "description": "High-level plan structure"
    },

    "lessonsCapture": {
      "$ref": "#/$defs/lessonsCapture",
      "description": "Structured output from learnings capture"
    },

    "relevantLessons": {
      "type": "array",
      "items": { "$ref": "#/$defs/relevantLesson" },
      "description": "Lessons loaded during Discovery phase that apply to this session"
    },

    "followUpTasks": {
      "type": "array",
      "items": { "$ref": "#/$defs/followUpTask" },
      "description": "Tasks for follow-up sessions identified during this session"
    }
  },

  "$defs": {
    "statusHistoryEntry": {
      "type": "object",
      "required": ["status", "timestamp", "event"],
      "properties": {
        "status": {
          "type": "string",
          "enum": [
            "draft",
            "awaiting_approval",
            "approved",
            "needs_revision",
            "rejected",
            "abandoned",
            "in_progress",
            "completed"
          ]
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        },
        "event": {
          "type": "string",
          "description": "Human-readable description of what triggered this status change"
        },
        "triggeredBy": {
          "type": "string",
          "description": "Who/what triggered this change (user, agent, system)"
        }
      }
    },

    "userApproval": {
      "type": "object",
      "required": ["approved", "timestamp", "approvalType"],
      "properties": {
        "approved": {
          "type": "boolean",
          "description": "Whether the plan was approved"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        },
        "approvalType": {
          "type": "string",
          "enum": ["explicit", "implicit", "rejected_with_feedback", "conditional"],
          "description": "How the approval was given"
        },
        "userComment": {
          "type": "string",
          "description": "User's comment when approving/rejecting"
        },
        "modifications": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of requested modifications if rejected"
        },
        "conditions": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Conditions attached to approval"
        }
      }
    },

    "discoveryResults": {
      "type": "object",
      "properties": {
        "agentsFound": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Names of relevant agents discovered"
        },
        "skillsFound": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Names of relevant skills discovered"
        },
        "reuseCandidates": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Existing patterns that could be reused"
        },
        "gapsIdentified": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Missing capabilities that need to be created"
        }
      }
    },

    "capability": {
      "type": "object",
      "required": ["type", "name", "phase", "reason"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["agent", "skill"]
        },
        "name": {
          "type": "string",
          "description": "Name of the agent or skill"
        },
        "phase": {
          "type": "string",
          "description": "Which phase this capability is needed for"
        },
        "reason": {
          "type": "string",
          "description": "Why this capability is needed"
        }
      }
    },

    "task": {
      "type": "object",
      "required": ["id", "phase", "content", "status"],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^P[0-9]+_[0-9]{3}$",
          "description": "Task identifier: P{phase}_{sequence}",
          "examples": ["P1_000", "P2_001"]
        },
        "phase": {
          "type": "integer",
          "minimum": 1,
          "description": "Phase number this task belongs to"
        },
        "content": {
          "type": "string",
          "description": "What needs to be done"
        },
        "activeForm": {
          "type": "string",
          "description": "Present continuous form for display (e.g., 'Creating schema')"
        },
        "requiredCapability": {
          "$ref": "#/$defs/taskCapability",
          "description": "Agent/skill needed to execute this task"
        },
        "outputArtifact": {
          "oneOf": [{ "type": "string" }, { "type": "null" }],
          "description": "File path of expected output, null if no file output"
        },
        "verification": {
          "$ref": "#/$defs/verification",
          "description": "How to verify task completion"
        },
        "status": {
          "type": "string",
          "enum": ["pending", "in_progress", "completed", "blocked", "skipped"],
          "description": "Current task status"
        },
        "dependsOn": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Task IDs that must complete before this task"
        },
        "completedAt": {
          "type": "string",
          "format": "date-time",
          "description": "When the task was completed"
        },
        "note": {
          "type": "string",
          "description": "Additional notes about the task"
        },
        "skillOverlays": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Skills that remain active throughout task execution"
        }
      }
    },

    "taskCapability": {
      "type": "object",
      "required": ["type", "name"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["agent", "skill"]
        },
        "name": {
          "type": "string"
        }
      }
    },

    "verification": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "file_exists",
            "file_exists_with_content",
            "file_contains",
            "file_not_exists",
            "command_success",
            "custom"
          ]
        },
        "path": {
          "type": "string",
          "description": "File path for file-based verifications"
        },
        "patterns": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Patterns to search for in file_contains"
        },
        "command": {
          "type": "string",
          "description": "Command to run for command_success"
        },
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "command": { "type": "string" },
              "expected": { "type": "string" }
            }
          },
          "description": "Multiple checks for custom verification"
        }
      }
    },

    "planDetails": {
      "type": "object",
      "properties": {
        "totalPhases": {
          "type": "integer",
          "minimum": 1
        },
        "phases": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of phase names"
        }
      }
    },

    "lessonsCapture": {
      "type": "object",
      "description": "Output from learnings capture phase",
      "properties": {
        "reviewedConversation": {
          "type": "boolean",
          "description": "Whether the conversation was reviewed for learnings"
        },
        "newLessons": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "type", "tags", "lesson", "applicability"],
            "properties": {
              "id": { "type": "string", "pattern": "^L[0-9]{3}$" },
              "type": {
                "type": "string",
                "enum": [
                  "system",
                  "interaction",
                  "workflow",
                  "agent-design",
                  "discovery-gap"
                ]
              },
              "tags": { "type": "array", "items": { "type": "string" } },
              "lesson": { "type": "string" },
              "applicability": { "type": "string" },
              "relatedLessons": { "type": "array", "items": { "type": "string" } }
            }
          }
        },
        "action": {
          "type": "string",
          "enum": ["NO_UPDATE", "UPDATE_LESSONS_JSON"],
          "description": "What action to take with captured lessons"
        }
      }
    },

    "relevantLesson": {
      "type": "object",
      "description": "A lesson loaded during Discovery that applies to this session",
      "properties": {
        "id": { "type": "string" },
        "lesson": { "type": "string" },
        "applicability": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } }
      }
    },

    "followUpTask": {
      "type": "object",
      "description": "A task identified for follow-up in a future session",
      "required": ["id", "description", "priority"],
      "properties": {
        "id": { "type": "string", "pattern": "^FU_[0-9]{3}$" },
        "description": { "type": "string" },
        "priority": { "type": "string", "enum": ["critical", "high", "medium", "low"] },
        "files": { "type": "array", "items": { "type": "string" } },
        "reason": { "type": "string" },
        "sourceTask": { "type": "string", "description": "Task ID that identified this follow-up" }
      }
    }
  }
}
```

---

## Status Transitions

### Valid Transitions

```
draft ----------------------> awaiting_approval
                                  |
                                  |-> approved ------> in_progress --> completed
                                  |
                                  |-> needs_revision --> awaiting_approval
                                  |
                                  |-> rejected
                                  |
                                  \-> abandoned

Any status --> abandoned (user cancels)
```

### Transition Rules

| From                | To                  | Trigger               | Requirements                            |
| ------------------- | ------------------- | --------------------- | --------------------------------------- |
| `draft`             | `awaiting_approval` | Plan complete         | Plan has at least one task              |
| `awaiting_approval` | `approved`          | User approves         | userApproval.approved = true            |
| `awaiting_approval` | `needs_revision`    | User requests changes | userApproval.modifications not empty    |
| `awaiting_approval` | `rejected`          | User rejects          | userApproval.approved = false           |
| `needs_revision`    | `awaiting_approval` | Revisions complete    | Changes address all modifications       |
| `approved`          | `in_progress`       | Execution starts      | First task marked in_progress           |
| `in_progress`       | `completed`         | All tasks done        | All tasks have status completed/skipped |
| Any                 | `abandoned`         | User cancels          | Explicit user request                   |

### Critical Rule: Approval Gating

**Implementation CANNOT start unless:**

```javascript
manifest.planStatus === 'approved' &&
  manifest.userApproval !== null &&
  manifest.userApproval.approved === true;
```

This prevents:

- Starting work before user reviews plan
- Proceeding after user rejection
- Continuing after user requests changes

---

## Task Schema Details

### Task ID Format

```
P{phase}_{sequence}

Examples:
- P1_000 - Phase 1, first task (prerequisite/foundation)
- P1_001 - Phase 1, second task
- P2_001 - Phase 2, first task
- P5_003 - Phase 5, fourth task
```

### Task Status Flow

```
pending --> in_progress --> completed
              |
              \--> blocked (dependency not met)

pending --> skipped (no longer needed)
```

---

## Session ID Format

**Format:** `{YYYYMMDD}_{HHMMSS}_{type}`

**Why date-first:** Sessions automatically sort newest to oldest with `ls`.

| Scenario      | Type Suffix             | Example                              |
| ------------- | ----------------------- | ------------------------------------ |
| Agenting      | `agent-*`, `skill-*`    | `20260124_150000_agent-creation`     |
| Documentation | `docs-*`                | `20260124_160000_docs-context-update` |

---

## File Locations

**Required files for a valid session:**

| File                     | Purpose                  | Created At | Required? |
| ------------------------ | ------------------------ | ---------- | --------- |
| `planning-manifest.json` | Planner's workflow state | Step 1     | **YES**   |
| `plan-manifest.json`     | Implementation plan      | Step 7     | **YES**   |
| `implementation-plan.md` | Human-readable plan      | Step 7     | **YES**   |
| `*_report.json`          | Quality audit reports    | Execution  | NO        |
