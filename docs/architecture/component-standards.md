# Component Standards -- Building for BCOS

How to add a new skill, agent, or hook to the CLEAR Context OS ecosystem.

---

## Skill Anatomy

Every skill lives in `.claude/skills/{skill-name}/SKILL.md`. A skill loads into the user's main context window, provides guidance or methodology, and can orchestrate agents.

### Required Frontmatter

```yaml
---
name: my-skill-name
description: |
  One-paragraph explanation of what this skill does.

  WHEN TO USE:
  - Trigger phrase 1
  - Trigger phrase 2

  WHEN NOT TO USE:
  - Anti-trigger 1
---
```

The `description` field is what Claude reads to decide whether to invoke the skill. Be specific about trigger phrases -- vague descriptions mean the skill never gets picked up.

### The IS / IS NOT Pattern

Every skill opens with a Purpose section that explicitly states what the skill does and does not do. This prevents scope creep -- without it, skills gradually absorb responsibilities from neighboring skills.

```markdown
## Purpose

**This skill IS:**
- [Specific responsibility 1]
- [Specific responsibility 2]

**This skill IS NOT:**
- [Thing that sounds similar but belongs elsewhere] (use X instead)
- [Common misconception about this skill's scope]
```

Write the IS NOT list first. It is easier to define boundaries when you start with what you exclude.

### Standard Sections

After Purpose, a skill typically contains:

1. **When to Use** -- trigger phrases as a bulleted list with `-->` pointing to the action
2. **The Process / Instructions** -- numbered steps for the workflow
3. **Automatic Handoffs** -- what to offer the user when the skill completes
4. **Integration with Other Skills** -- table showing which skills relate and how
5. **References** -- links to supporting documents

### Architecture Patterns

| Pattern | Directory Structure | When to Use |
|---------|-------------------|-------------|
| Simple Skill | `SKILL.md` only | Guidelines, methodology, lightweight workflows |
| Skill Plus References | `SKILL.md` + `references/*.md` | Skills needing templates, schemas, or detailed reference material |
| Overlay Skill | `SKILL.md` with methodology (no workflow steps) | Cross-cutting concerns like verification, testing, discipline |

---

## Agent Anatomy

Every agent lives in `.claude/agents/{agent-name}/AGENT.md`. An agent runs in an isolated context window via the `Agent` tool -- it cannot see the user's conversation.

### Required Frontmatter

```yaml
---
name: agent-name
description: One-line description of what this agent does.
category: Category
---
```

### Standard Sections

```markdown
## Purpose

**IS:** [What this agent does -- factual, read-only, analytical]
**IS NOT:** [Making changes, deciding, planning]

## When Skills Should Delegate Here

| Delegating Skill | What to Delegate | What Agent Returns |
|-----------------|-----------------|-------------------|
| skill-name | "Specific instruction" | Compact findings |

## How to Invoke

From any skill, use the Agent tool:
> Use the Agent tool (subagent_type: "AgentName") to [task].
> Return: [what you need back].

## Capabilities
- [Capability 1]
- [Capability 2]

## Constraints
- Read-only. Never creates, edits, or deletes files.
- No other agents. Cannot invoke other agents or skills.
- No decisions. Returns factual findings only.
- Compact returns. Summarize, don't dump raw content.
```

### The Key Constraint

**Skills CAN spawn agents. Agents CANNOT spawn agents.**

This is a Claude Code platform constraint, and it drives all orchestration decisions in BCOS. If your workflow needs multi-step coordination across agents, that coordination must live in a skill (which runs in the main context window). An agent that needs to invoke another agent is a design error -- restructure so the parent skill orchestrates both.

---

## Hook Anatomy

Hooks are Python scripts triggered by Claude Code lifecycle events. They validate and enforce standards automatically.

### settings.json Configuration

Hooks are registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/my_hook.py\"",
            "timeout": 10,
            "statusMessage": "Running my check..."
          }
        ]
      }
    ]
  }
}
```

**Key fields:**

| Field | Purpose |
|-------|---------|
| `matcher` | Which tool triggers the hook (`Edit`, `Write`, etc.) |
| `type` | Always `"command"` for script hooks |
| `command` | Path to the Python script (use `$CLAUDE_PROJECT_DIR` for portability) |
| `timeout` | Seconds before the hook is killed (keep short -- 10s is typical) |
| `statusMessage` | What the user sees while the hook runs |

### Hook Input and Output

**Input:** The hook receives JSON on stdin containing the tool invocation details:

```json
{
  "tool_input": {
    "file_path": "/path/to/edited/file.md"
  }
}
```

**Output:**
- Exit code `0` = pass (no issues, or issues reported as warnings)
- Exit code `2` = block (prevent the tool action from completing)

### Philosophy: Warn, Don't Block

PostToolUse hooks should warn via stderr, not block via exit code 2. Blocking edits mid-flow is too disruptive. The warning appears in Claude's context, and Claude self-corrects on the next action.

The current `post_edit_frontmatter_check.py` hook always exits 0 and prints warnings to stderr when issues are found.

### Current Hooks

| Hook | Event | Matcher | What It Enforces |
|------|-------|---------|-----------------|
| `post_edit_frontmatter_check.py` | PostToolUse | Edit, Write | Required YAML frontmatter fields, valid status/type enums |

### Adding a New Hook

1. **Create the script** in `.claude/hooks/` using snake_case naming
2. **Read stdin** as JSON to get the tool input
3. **Decide scope** -- which files need validation (use path checks to skip irrelevant files)
4. **Report issues** via stderr (for warnings) or exit code 2 (for blocking)
5. **Add to settings.json** under the appropriate event and matcher
6. **Test manually** by running the script with piped JSON input
7. **Update reference-index.json** with the new hook entry

---

## TodoWrite Integration

Progress tracking in BCOS uses the TodoWrite tool, following patterns defined in `.claude/skills/todo-utilities/references/todo-patterns.md`.

### Critical Rule: Inline, Not Invoked

TodoWrite calls MUST run in the main context window. If a skill delegates TodoWrite to an agent (via `Task()`), the calls execute in an isolated context -- invisible to the user. The entire purpose of progress tracking is user visibility.

**This means:** Skills copy TodoWrite patterns inline into their own workflow. They do not invoke todo-utilities as a separate task.

### Key Patterns

| Pattern | When to Use | Rules |
|---------|------------|-------|
| Sequential | Tasks depend on each other | Initialize full list up front. One task `in_progress` at a time. |
| Parallel | Independent tasks | Mark all parallel tasks `in_progress` at once. Complete all after all return. |
| Error Recovery | A step fails | Update activeForm to show what went wrong. Inject fix tasks dynamically. |
| Workflow Gate | User approval needed | Gate task stays `in_progress` until user responds. Don't auto-advance. |
| Long-Running | Bulk operations | Show counts in activeForm: `(10/47)`. Update every 10 items, not every item. |
| Automatic Handoff | Skill completes | Mandatory follow-ups just happen. Optional follow-ups are offered as questions. |

### Anti-Patterns

- **Empty initial list** -- Never start with `TodoWrite([])` then add items later. Initialize the full list immediately.
- **Skipping the pre-agent update** -- Always mark a task `in_progress` BEFORE invoking the agent, not after.
- **TodoWrite inside a delegated agent** -- The agent's TodoWrite overwrites the parent's list. Always update TodoWrite from the parent skill.
- **Stale tasks** -- Start each workflow with a clean list. Don't carry over completed tasks from previous runs.

---

## Delegation Pattern

When to use the `explore` agent vs. staying in the main context window.

### Delegate to Explore Agent

- Reading more than 5 files
- Scanning a directory for patterns or inventory
- Keyword search across all docs
- Reading git diffs of 10+ files
- Validating frontmatter across 20+ documents

### Stay in Main Window

- Reading 1-3 targeted files
- Synthesis, reflection, and decision-making
- User-facing interaction (triage, approval gates)
- Cross-reference updates (need full graph awareness)
- Plan creation (architecture decisions need full context)

### How Delegation Works

```
Use the Agent tool (subagent_type: "Explore") to scan docs/ for all files
mentioning "pricing". Return: file paths, relevant excerpts, frontmatter status.
```

The agent runs in its own context window, reads files, and returns a compact summary. The main session never loads raw file content -- it only receives the summary. This keeps the main context window available for reasoning.

### Scaling Guide

| Context Size | Strategy |
|-------------|----------|
| < 20 docs | No delegation needed. Everything fits in main window. |
| 20-50 docs | Delegate full scans (onboarding, audit). Keep targeted reads in main. |
| 50-100 docs | Delegate ALL bulk reads. Batch audit by cluster. |
| 100+ docs | Run Python scripts for inventory. Agent-per-cluster for audits. Main window only for synthesis. |

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Skill directories | kebab-case | `context-ingest`, `clear-planner` |
| Agent directories | kebab-case | `explore`, `agent-discovery` |
| Skill definition file | Uppercase, exact name | `SKILL.md` |
| Agent definition file | Uppercase, exact name | `AGENT.md` |
| Reference docs | kebab-case in `references/` | `references/todo-patterns.md` |
| Python scripts | snake_case | `.claude/scripts/build_document_index.py` |
| Python hooks | snake_case | `.claude/hooks/post_edit_frontmatter_check.py` |

---

## Testing a New Component

Before merging a new skill, agent, or hook:

1. **Read it in isolation** -- Does the SKILL.md or AGENT.md stand alone? Can someone understand the component without reading other files?

2. **Check cross-references** -- Do all files mentioned in the component actually exist? Run:
   ```bash
   # Extract referenced paths and verify they exist
   grep -oP '`[^`]+\.(md|py|sh|json)`' .claude/skills/my-skill/SKILL.md
   ```

3. **Check the ecosystem** -- Does this overlap with an existing skill or agent? Read the ECOSYSTEM-MAP.md and check IS/IS NOT sections of similar components.

4. **Run ecosystem-manager audit** -- Use the ecosystem-manager skill to run overlap detection and health checks.

5. **Update ecosystem registries:**
   - `.claude/ECOSYSTEM-MAP.md` -- Add the new component
   - `.claude/registries/reference-index.json` -- Add any new reference docs
   - `.claude/quality/ecosystem/state.json` -- Run discovery scripts to update

---

## Directory Structure Reference

```
.claude/
  agents/
    {agent-name}/
      AGENT.md
      references/           (optional)
    agent-discovery/
      find_agents.sh        (discovery script)
  skills/
    {skill-name}/
      SKILL.md
      references/           (optional)
    skill-discovery/
      find_skills.sh        (discovery script)
  hooks/
    post_edit_frontmatter_check.py
  scripts/
    build_document_index.py
  quality/
    ecosystem/
      state.json            (current inventory snapshot)
      config.json           (ecosystem configuration)
      lessons.json          (institutional knowledge)
    sessions/
      {YYYYMMDD_HHMMSS_slug}/
  registries/
    reference-index.json
  ECOSYSTEM-MAP.md
```

### Agent vs. Skill Decision

| Question | Agent | Skill |
|----------|-------|-------|
| Heavy analysis or bulk reading? | Yes | No |
| Loads into user's context window? | No | Yes |
| Provides methodology or guidelines? | No | Yes |
| Needs isolated execution context? | Yes | No |
| Orchestrates other agents? | No | Yes (skills orchestrate) |
