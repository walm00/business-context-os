---
session-id: 20260501_102818_ecosystem-state-drift-fix
scenario: agenting
status: awaiting_approval
created: 2026-05-01
---

# Implementation Plan — Ecosystem state.json Drift Fix

## Problem Statement

**Across 14 BCOS-enabled repos surveyed, 8 of 12 actively-maintained repos show identical drift:** `state.json` frozen 8-22 days, skills on disk missing from inventory, `skill-discovery`/`agent-discovery` falsely flagged as missing skills on every monthly architecture-review run.

Five interlocking design gaps cause this:

1. **`lastAudit` field has no writer.** [update.py:219](../../scripts/update.py:219) preserves it; [job-architecture-review.md:142-143](../../skills/schedule-dispatcher/references/job-architecture-review.md:142) explicitly forbids writing it. Dead field.
2. **`update.py`'s `merge_ecosystem_state()` is purely additive from upstream's state.json** ([update.py:216-294](../../scripts/update.py:216)). Disk-blind. Can't see locally-added skills or deployed-only utility directories.
3. **Vestigial `skill-discovery`/`agent-discovery` directories** in deployed repos — bare `find_*.sh` scripts, no SKILL.md/AGENT.md. Get falsely classified as missing skills.
4. **Architecture-review uses two inconsistent ecosystem checks** — `analyze_integration.py --staged` (wrong flag) plus an ad-hoc Claude-driven directory listing that contradicts the marker-aware script.
5. **No auto-fix path.** `auto-fix-whitelist.md` has no `ecosystem-state-refresh` ID. Even when drift is detected, the dispatcher cannot fix it.

The framework's own lesson `L-INIT-20260404-009` states: *"Discovery scripts are the source of truth for what exists. State files record what discovery found, not the definition itself."* The current architecture violates this principle.

## Proposed Solution

Treat `state.json` as a **derived artifact** of disk state, not authored truth. Implement via a single deterministic regeneration script invoked at three checkpoints (install, daily, monthly). Use the SKILL.md/AGENT.md marker rule already in `analyze_integration.py` so classification logic stays in one place.

### Files affected

| Path | Action | Why |
|---|---|---|
| `.claude/scripts/refresh_ecosystem_state.py` | **NEW** | Disk-scan regenerator — single source of truth |
| `.claude/scripts/update.py` | MODIFY | Replace additive merge with refresh script invocation |
| `.claude/skills/schedule-dispatcher/references/job-index-health.md` | MODIFY | Add daily refresh step (cheap glob) |
| `.claude/skills/schedule-dispatcher/references/job-architecture-review.md` | MODIFY | Fix `--staged`→`--ci`, drop ad-hoc check, lift state.json prohibition |
| `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md` | MODIFY | Define `ecosystem-state-refresh` fix ID |
| `.claude/quality/schedule-config.template.json` | MODIFY | Add ID to default whitelist |

### What is NOT in scope

- Healing the 8 currently-drifted deployed repos. They heal automatically on their next `update.py` run once this ships. (Optional follow-up: one-shot ecosystem-manager pass per repo.)
- Refactoring `ecosystem-manager` SKILL.md (still references `find_*.sh` discovery scripts — that path keeps working).
- Removing the vestigial discovery directories from deployed repos. They get correctly classified as `utilities` by the new script — not dangerous, just deprecated.

## Tasks by Phase

### Phase 1 — Design (3 tasks)

| ID | Task | Status |
|---|---|---|
| P1_001 | Define classification rule (SKILL.md/AGENT.md markers) and document in script docstring | pending |
| P1_002 | Define output schema with utilities section + preservation policy for user-authored fields | pending |
| P1_003 | Define agent category inference (read AGENT.md frontmatter `category` field) | pending |

### Phase 2 — Implementation (5 tasks)

| ID | Task | Status |
|---|---|---|
| P2_001 | Create `refresh_ecosystem_state.py` with disk-scan logic | pending |
| P2_002 | Implement preservation logic for `overlayCapable`, `discoveryCapable`, `health`, `maintenanceBacklog` | pending |
| P2_003 | Implement utilities classification for marker-less directories | pending |
| P2_004 | Add CLI flags: `--dry-run`, `--json`, `--quiet` | pending |
| P2_005 | Test in dev repo — output should match curated state.json + new utilities section | pending |

### Phase 3 — Wire into update + daily (4 tasks)

| ID | Task | Status |
|---|---|---|
| P3_001 | Replace `merge_ecosystem_state()` call in `update.py` with refresh script invocation | pending |
| P3_002 | Remove dead `merge_ecosystem_state()` function (additive merge was the bug) | pending |
| P3_003 | Add Step 6 "Refresh ecosystem state" to `job-index-health.md` | pending |
| P3_004 | Verify: manual index-health run updates state.json correctly | pending |

### Phase 4 — Wire into auto-fix + monthly (4 tasks)

| ID | Task | Status |
|---|---|---|
| P4_001 | Define `ecosystem-state-refresh` ID in `auto-fix-whitelist.md` | pending |
| P4_002 | Add to default whitelist in `schedule-config.template.json` | pending |
| P4_003 | Update `job-architecture-review.md`: fix typo, drop ad-hoc check, lift prohibition | pending |
| P4_004 | Document derived-artifact policy in methodology docs | pending |

### Phase 5 — FIXED END (4 tasks, mandatory for AGENTING)

| ID | Task | Status |
|---|---|---|
| P5_001 | Run `analyze_integration.py --ci`; resolve coverage gaps | pending |
| P5_002 | Run `refresh_ecosystem_state.py` in dev repo; commit regenerated state.json | pending |
| P5_003 | Capture lesson: "State files mirroring disk should be regenerated, never authored" | pending |
| P5_004 | Verify all CI checks pass before commit | pending |

## Risks

- **Breaking change for repos that hand-edited state.json.** Mitigation: preservation logic keeps `overlayCapable`, `discoveryCapable`, `health`, `maintenanceBacklog`. The only fields that get rewritten are `inventory.skills.list`, `inventory.skills.total`, `inventory.agents.byCategory`, `inventory.agents.total`, `lastUpdated`, `lastAudit`. Categorical lists are filtered to skills/agents that still exist on disk — protects against stale entries but won't drop deliberate user-added entries.
- **One-time noise on first run.** Every deployed repo will produce a `state.json` diff on its next `update.py` run. Expected and benign — that's the drift being healed.
- **`update.py` merge function removal**. If anything else imports `merge_ecosystem_state`, it breaks. Grep confirms no other caller, but worth re-verifying in P3_002.

## Artifacts

- `plan-manifest.json` — `.claude/quality/sessions/20260501_102818_ecosystem-state-drift-fix/plan-manifest.json`
- `planning-manifest.json` — `.claude/quality/sessions/20260501_102818_ecosystem-state-drift-fix/planning-manifest.json`
- `implementation-plan.md` — this file

## Next Actions

| Action | Effect |
|---|---|
| **Approve** | Mark plan approved, hand off to implementation starting at P1_001 |
| **Modify** | Return to context-gathering with feedback |
| **Cancel** | Stop here, archive session |
