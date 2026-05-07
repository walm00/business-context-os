---
name: "Autonomy + UX + Self-Learning — Pre-Flight Decisions"
type: decision-log
cluster: "Framework Evolution"
version: 1.0.0
status: defaulted
created: 2026-05-04
last-updated: 2026-05-04
---

# Pre-Flight Decisions (D-01 → D-05)

All five decisions defaulted at Gate 1 alignment (2026-05-04 19:25 UTC). User's prompt to `/clear-planner` provided defaults that are sound; none rise to a structure-changing gate.

---

## D-01 — Plan file location

**Decision:** `docs/_planned/autonomy-ux-self-learning/`

**Why:** Matches the existing `_planned/` convention. Companion plans `wiki-missing-layers/` and `wiki-zone-integration/` use the same shape (directory with `implementation-plan.md` + `plan-manifest.json` + `README.md` + `pre-flight-decisions.md`). Consistency aids resumption.

**How to apply:** All durable plan artifacts live here. Working planner state (this session's `planning-manifest.json`) lives in `.claude/quality/sessions/20260504_191019_autonomy-ux-self-learning/` and is gitignored.

---

## D-02 — Phase 8 inclusion

**Decision:** Keep as Phase 8 in this plan, marked CONDITIONAL with explicit entry criteria.

**Why considered for split:** Silent tier is a different risk class than P5/P7 ladder transitions — a wrongly-promoted silent rule produces broken state for an entire week before the auditor catches it. Argument for separate plan: P0–P7 deliver real value standalone.

**Why kept in plan:** Splitting creates two artifacts to maintain and adds friction at the moment the user is ready to opt into silent tier. Keeping it as a CONDITIONAL phase with explicit entry criteria (P8_000 gate task) preserves both the deferral and the readiness.

**Entry criteria for P8 (mandatory; checked by P8_000):**
1. Auditor has been clean (no critical demotions) for 6+ consecutive weeks
2. User has set `learning.silent_tier_opt_in: true` in `schedule-config.json`
3. User explicitly invokes "begin Phase 8" via planner or direct task

**How to apply:** P0–P7 + P9 are the v1.0 ship surface. P8 is post-stability; do not start it as a side effect of P7 stability.

---

## D-03 — Phase 2 vs Phase 3 ordering

**Decision:** Dashboard view + button bindings first (P2), then headless actions slot in (P3).

**Why:** They are technically independent (P2 can render cards from typed events without P3's action handlers; P3's handlers can run from chat without P2's UI). But the dashboard is what makes headless actions accessible to non-power-users. Shipping P3 first means the user gets a `/api/actions/headless` endpoint that nothing visible calls.

**How to apply:** Implement P2's cockpit refactor and `block_on_red` gate first. P3 adds the action handlers that P2's primary buttons invoke.

---

## D-04 — Resolution recording shape

**Decision:** Hook on existing skills (dispatcher + ingest + ad-hoc fix-skills) via shared library `record_resolution.py`. No new dedicated skill.

**Why considered for new skill:** A `record-fix` skill would be more discoverable in `find_skills.sh` output and could carry its own SKILL.md describing the trigger taxonomy.

**Why hook + library wins:** The skill would never be invoked by the user directly — it would always be a sub-call from another skill that just applied a fix. A shared Python library called from those skills is less code, less indirection, and doesn't pollute the skill registry with a non-user-facing entry. Discovery cost is paid once via the library's docstring + the contract doc at `docs/_bcos-framework/architecture/typed-events.md`.

**How to apply:** P4_002 implements the library. P4_003/P4_004 wire it into `/api/actions/resolve` (dashboard) and the headless action endpoint (chat path). Future fix-paths (e.g. context-ingest contradiction-resolution) call the same library.

---

## D-05 — Job naming for the auditor

**Decision:** `auto-fix-audit`

**Why:** Parallel to existing `wiki-coverage-audit`'s "audit-a-specific-surface" convention. The job audits the auto-fix surface (silent + headless + chat-bulk-fix paths). Alternatives considered:
- `learning-audit` — implies the audit is about the learning ladder, but the ladder is downstream; the audit's primary job is reversal/validation/flap detection on the fix surface itself
- `resolution-audit` — too vague; the job doesn't audit individual resolutions, it audits patterns across them

**How to apply:** Job reference doc at `.claude/skills/schedule-dispatcher/references/job-auto-fix-audit.md` (P6_002). Cron entry as `auto-fix-audit` in `schedule-config.json` (P6_004).
