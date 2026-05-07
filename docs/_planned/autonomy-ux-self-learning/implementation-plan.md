---
name: "Autonomy + UX + Self-Learning — Implementation Plan & PRD"
type: playbook
cluster: "Framework Evolution"
version: 1.1.0
status: approved
created: 2026-05-04
last-updated: 2026-05-05
session-id: 20260504_191019_autonomy-ux-self-learning
authority-docs:
  - .claude/skills/schedule-dispatcher/SKILL.md
  - .claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md
  - .claude/scripts/bcos-dashboard/README.md
  - docs/_bcos-framework/architecture/system-design.md
  - docs/_bcos-framework/architecture/maintenance-lifecycle.md
soft-dependencies:
  - docs/_planned/wiki-missing-layers/ (in implementation; resolutions.jsonl schema fields are coordinated, not duplicated)
---

> **Status: approved (Gate 2) 2026-05-05.** Gate 1 alignment passed 2026-05-04. All 5 pre-flight decisions defaulted (D-01 → D-05; see `pre-flight-decisions.md`). Approved at Gate 2 on 2026-05-05 after pre-approval review (see `review-notes-2026-05-05.md`); v1.1.0 corrects test paths (`tests/test_*.py` → `.claude/scripts/test_*.py`, gitignored dev convention) and P9_001's verification command. This plan is SEPARATE from `wiki-missing-layers/` (also active in `docs/_planned/`) but shares the `resolutions.jsonl` schema contract — whichever ships first creates the file; the other extends.

## Implementer notes (2026-05-05 pre-approval review)

Read these once before starting any phase; they pin down assumptions the v1.0 plan left implicit. Full context in `review-notes-2026-05-05.md` (sections E–H).

- **Tests live at `.claude/scripts/test_*.py`** — gitignored (`.gitignore:133`) by design. Tests are dev-only infrastructure; they don't ship to public BCOS via `publish.sh`. This is intentional, not a bug.
- **P2_006 schema migration** — Keep `digest.auto_commit` as a flat boolean (current shape; preserves `set_auto_commit(enabled: bool)` and the `/api/schedule/auto-commit` endpoint). Add a sibling `digest.auto_commit_block_on_red: bool` (default `true`). Avoids touching the existing endpoint signature; introduces no breaking change for users who already flipped `auto_commit` to `true`.
- **P4_008 location compatibility** — `pending-validations.jsonl` goes in `.claude/hook_state/` alongside `schedule-diary.jsonl` and `actions-resolved.jsonl`. **Data files only.** Do NOT create any `.py` helper scripts inside `.claude/hook_state/` — that folder is treated as sensitive by Claude Code, so any `.py` write/edit/delete triggers an approval prompt regardless of `permissions.allow`. See dispatcher SKILL.md "Step 4 — Run Each Job" for the rule.
- **P3 chat-intercept (new sub-task P3_008)** — `natural_language_command` capture for `bulk_id` (P4_005) + `user_specificity` classifier (P4_006) needs an explicit mechanism. Three options ranked by cost: (a) assistant-supplied as a parameter to `/api/actions/headless` — cheapest, works today, no hook changes; (b) `UserPromptSubmit` hook captures user text into `.claude/hook_state/pending-commands.jsonl`, drained by the next headless call; (c) skip the field in v0.1, classify `user_specificity` heuristically from `action_target` patterns. Recommended: start with (a) for P3, add (b) only if assistant-supplied phrases drift from actual user intent more than 5% of the time. Capture this decision in P3_008 before P4 begins.
- **P5_004 architecture-review integration point** — `job-architecture-review.md` is plain markdown without structured slots. Insert a new "Step 6: Surface learned rules this month" between current Step 5 (Lessons retention) and the existing output step. Render as a new section in the monthly report under heading `## Rules learned this month`, broken down by `trigger` (dashboard-click vs chat-bulk-fix vs chat-targeted-fix vs scheduled-headless).

# Autonomy + UX + Self-Learning — Implementation Plan & PRD

> **Note:** The runtime planner state (planning-manifest.json + working artifacts) lives at `.claude/quality/sessions/20260504_191019_autonomy-ux-self-learning/` and is gitignored. This is the durable, reviewable copy.

| Field | Value |
|---|---|
| **Session ID** | `20260504_191019_autonomy-ux-self-learning` |
| **Branch** | `claude/compassionate-rubin-e1965d` (worktree) |
| **Scenario** | AGENTING (primary) + DOCUMENTATION (secondary) |
| **Status** | `awaiting_approval` |
| **Total phases** | 10 (P0 foundation + P1–P8 + P9 fixed-end; P8 is CONDITIONAL) |
| **Total tasks** | 70 |
| **Skills affected** | `schedule-dispatcher` (extended), `schedule-tune`, `lessons-consolidate`, `daydream` |
| **Skills new** | None (no new skill earns its weight; new functionality lives in references + scripts + dispatcher hooks) |
| **Agents affected** | None |
| **Estimate** | 38–46 days for P0–P7+P9; +7 days P8 if entry criteria met |

---

## 0. Foundation (already shipped — do not re-build)

This plan composes on existing infrastructure. Treating the following as foundation, not in-scope:

| Asset | Role |
|---|---|
| [.claude/skills/schedule-dispatcher/SKILL.md](../../.claude/skills/schedule-dispatcher/SKILL.md) | Single-task dispatcher, 9 jobs already routed; this plan adds a 10th (`auto-fix-audit`) |
| [.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md](../../.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md) | 12 silent auto-fix IDs; this plan adds a parallel `headless-actions.md` for one-click cards |
| [.claude/scripts/bcos-dashboard/](../../.claude/scripts/bcos-dashboard/) | Cockpit + collectors + endpoints + `digest_parser.py` + `actions_resolved.py` + `labels.py`; this plan extends labels and actions_resolved, adds card renderers |
| [.claude/quality/schedule-config.json](../../.claude/quality/schedule-config.json) | Per-job autonomy + auto-fix whitelist; this plan extends with `headless_actions.enabled[]` and `digest.auto_commit.block_on_red` |
| [.claude/scripts/append_diary.py](../../.claude/scripts/append_diary.py) + diary JSONL | Append-only history; this plan adds a parallel `resolutions.jsonl` for fix events specifically |

---

## 1. Problem Statement

The previous audit (this conversation, 2026-05-04 18:00 UTC) established the BCOS UX/autonomy problem in concrete terms:

**Problem 1 — Line-level digest is prose, not data.** Action items today are strings like `inbox aged: docs/_inbox/Q1-notes.md (14 days) — triage`. The digest is dashboard-shaped at the section level (`digest_parser.py` round-trips it cleanly) but at the line level it's free-text, which makes one-click button extraction harder than it needs to be. Cards in the cockpit currently re-parse prose.

**Problem 2 — Too much chat noise on green days.** `auto_fixed[]` lists, per-job `notes` lines (`Custom _-folders skipped: 2 folder(s)`), and INFO-tier coverage findings all surface in chat verbatim regardless of verdict. The user reads them every morning. Power-user logging is mixed with judgement-required signals.

**Problem 3 — Most "decision" cards are mechanical.** 21 of 24 distinct finding types (87%) are deterministically resolvable with one click — `inbox-aged` triage, `stale-propagation` mark-reviewed, `source-summary` refresh-now, `graveyard-stale` archive, frequency-tuning suggestions, etc. Today they all surface as prose, requiring the user to type back into Claude or manually edit files.

**Problem 4 — No memory across sessions.** Every time the same finding type appears, the user makes the same call cold. The system never notices "you have archived `_planned/` items 7 times in a row when they reach 180 days — should this be the default?" There is no `resolutions.jsonl`, no learning ladder, no audit trail of resolution decisions.

**Problem 5 — No backstop on autonomy.** The auto-fix whitelist has 12 IDs that fire silently. There is no mechanism that asks: did anyone undo these? Are they producing validation failures downstream? Is rule A's auto-fix sometimes undoing rule B's? Without an auditor, drift accumulates silently — and any aggressive promotion of new rules to "silent" is a gamble.

**Goal:** ship the autonomy + UX + self-learning surface in a form that:

1. **Mechanical-first** — Python + JSON + file-system traversal; LLM is opt-in escalation only (P8 semantic-drift check, gated behind `--semantic`).
2. **Schema fields shipped from day 1** — the 12 fields of `resolutions.jsonl` are all written from P4, even though P5–P8 are the only consumers. No backfill debt.
3. **Defends user judgement where it matters** — boundary violations, monthly priorities, daydream-deep structural recommendations, contradiction resolution stay in the "requires user creativity" bucket. Ladder cannot reach them.
4. **Auditor as brake** — every promotion-tier change has a corresponding auditor check that can demote (recommend) or, in the validation-failure case only, auto-disable. The auditor is what makes the ladder safe to be aggressive on.
5. **User can always demote/forget/disable** — no rule gets locked in. `/learning forget <rule-id>`, "Demote rule" buttons everywhere, `learning-blocklist.json` for explicit refusal.
6. **Audit visibility** — every promoted rule shows evidence in the cockpit (`/settings/learning` panel). Nothing is silent in the meta-sense; the user can SEE what learned rules exist even if individual fires are silent.

**Non-goals (v1):**
- Vector store / embedding-based similarity for findings (P8 is the only LLM-touching phase, and only for body-content semantic drift)
- Auto-promotion across silent tier without explicit user opt-in
- Cross-repo learning (resolutions stay per-repo under `.claude/`)
- Rewriting the diary or wake-up-context layers
- Touching `_planned/wiki-missing-layers/` work in flight

---

## 2. User Stories

| As a... | I want to... | So that... |
|---|---|---|
| BCOS user (morning) | open the cockpit and see "All clear" on green days | I don't read 9 lines of per-job notes that don't need me |
| BCOS user (amber day) | see N cards with one-click primary actions | I can clear the morning queue without typing into chat |
| BCOS user (red day) | see auto-commit paused with a clear unblock path | I know critical state is not silently committed |
| BCOS user (after a week) | see "✨ suggested" badge on cards where my past pattern picks the default | I save a click on the things I've already decided |
| BCOS user (after 6 weeks) | see auto-apply tier with 10-second undo on rules I've consistently approved | I stop confirming the same call repeatedly |
| BCOS user (any time) | open `/settings/learning` and see what rules the system has learned | nothing about my own behavior surprises me |
| BCOS user (any time) | see a red card "rule X auto-disabled — N validation failures" | broken rules don't keep producing broken state |
| BCOS user (any time) | run `/learning forget <rule-id>` | a wrongly-learned rule doesn't lock me in |

---

## 3. Architecture Decisions

### D-01 — Mechanical-first, LLM-when-mechanical-exhausts
P0–P7 are pure Python + JSON + filesystem. P8 introduces one LLM check (semantic-drift) gated behind explicit `--semantic` flag, mirroring the wiki-missing-layers D-10 discipline.

### D-02 — Schema fields shipped from day 1
`resolutions.jsonl` has all 12 fields (`ts`, `finding_type`, `finding_attrs`, `action_taken`, `action_target`, `outcome`, `time_to_resolution_s`, `trigger`, `bulk_id`, `natural_language_command`, `user_specificity`, `applied_diff_summary`, `applied_diff_hash`, `subsequent_validation_status`) from P4. Even though P5–P8 are the consumers, no migration debt.

### D-03 — Derived-vs-authored separation
`resolutions.jsonl` = authored truth (append-only event log). `learned-rules.json` = derived from resolutions via `promote_resolutions.py`. Per L-ECOSYSTEM-20260501-013, derived files must be regeneratable byte-stable from source. `auto-fix-whitelist.md` stays human-edited; `learned-rules.json` is the machine-readable layer the dispatcher reads in addition.

### D-04 — Auditor is the only component that can auto-disable
The auditor has narrow auto-action authority: only `subsequent_validation_status: failed` AND N≥5 across ≥3 distinct files in 24h triggers auto-disable. Reversal-rate spikes recommend-only (one-click confirm). Cross-rule flap detection recommend-only.

### D-05 — Soft dependency on wiki-missing-layers
The `resolutions.jsonl` schema is shared. Whichever plan ships first creates the file; the other extends. Both plans' P4 cite the same schema contract doc. No duplicate writers; a shared `record_resolution.py` library.

### D-06 — Phase gates measured in production-stable days
- 14 days default between phases (production-stable = ran successfully without rollback)
- 7 days for dashboard-only phases (P2, P7's panel work)
- 28 days for ladder-tier transitions in P5/P7/P8 (cooldown for the consistency signal to mature)

### D-07 — TDD ordering per phase
Each phase ships in this sequence: (1) fixture corpus extension → (2) failing test asserting contract → (3) implementation → (4) green test → (5) wiring test asserting cross-references agree (config + reference doc + dispatcher mention). Per L-ECOSYSTEM-20260504-014/015.

### D-08 — Single translation map for finding_type
Per L-DASHBOARD-20260425-010, `finding_type` IDs route through `labels.py` extension. Collectors emit raw IDs; renderers prefer `display_*` form, fall back to raw. One file (`labels.py`) controls UX-tier audience.

### D-09 — Cache invalidation in composing panels
Per L-DASHBOARD-20260425-012, every POST handler invalidates not just the touched panel but every panel that composes it. P2 adds explicit cache-invalidation tests.

### D-10 — Phase 8 entry is gated
Silent tier (P8) only enters after auditor runs clean for 6+ weeks AND user explicitly opts in via `learning.silent_tier_opt_in: true` in `schedule-config.json`. Default is `false`. P8 cannot ship as a side effect of P7 stability.

---

## 4. Phase Breakdown

### Phase 0 — Foundation: fixture corpus + discovery wiring tests (~1d, mechanical)

Establish the test scaffolding before anything else. Mirror the cleanup-pass discipline from wiki-missing-layers.

| ID | Task | Output | Verification |
|---|---|---|---|
| P0_001 | Create fixture digest corpus under `.claude/quality/fixtures/digests/` (green / amber / red sample digests with both prose AND typed-event sidecar) | `fixtures/digests/{green,amber,red}.{md,json}` | Files exist + parseable |
| P0_002 | Failing wiring test: `.claude/scripts/test_digest_typed_events.py` asserts every fixture produces typed events that round-trip through digest_parser | Test fails at P0; passes at P1 | `pytest .claude/scripts/test_digest_typed_events.py` red |
| P0_003 | Failing wiring test: `.claude/scripts/test_resolutions_jsonl_schema.py` asserts all 12 fields required from day 1 | Test fails at P0; passes at P4 | `pytest` red |
| P0_004 | Document the typed-event taxonomy contract in `docs/_bcos-framework/architecture/typed-events.md` (finding_type enum + finding_attrs shape per type) | New doc + cross-link from system-design.md | doc-lint clean; xref valid |

### Phase 1 — Line-level digest structure (3–5d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P1_001 | Define `finding_type` enum covering all action items emitted by 9 existing jobs (~20 types) | `finding_type` enum in `typed-events.md` | All current job references' action items map to one enum value |
| P1_002 | Define `finding_attrs` shape per finding_type (typed schema; e.g. `inbox-aged → {file, age_days, size_kb, first_heading}`) | Schema table in `typed-events.md` | Fixture parses against schema |
| P1_003 | Update each `job-*.md` reference doc to declare its emitted `finding_type` values | 9 reference docs updated | Wiring test (P1_007) passes |
| P1_004 | Implement digest sidecar JSON writer `.claude/scripts/digest_sidecar.py` (writes `daily-digest.json` next to `daily-digest.md`) | New script + unit tests | Sidecar produced on every dispatcher run |
| P1_005 | Extend `bcos-dashboard/labels.py` with `finding_type → display_label` map | labels.py extended | Coverage test asserts every enum value has a label |
| P1_006 | Update `digest_parser.py` to consume typed-event sidecar; renderer prefers `display_*` form, falls back to prose | digest_parser.py updated | P0_002 test passes green |
| P1_007 | Wiring test: every job reference declares its finding_types AND labels.py covers them all AND the sidecar JSON validates against schema | New test in tests/ | Green at P1 close |
| P1_008 | Update `system-design.md` and `schedule-dispatcher/SKILL.md` to cite typed-event contract | Two cross-links | doc-lint clean |

**Dashboard noise reduction (per audit Top-3):** P1 also strips `auto_fixed[]` listing, green-day `notes`, and INFO-tier coverage lines from CHAT output (kept in digest under `<details>` for power users). Done as part of P1_006.

### Phase 2 — Dashboard cards + cockpit composition + `block_on_red` gate (5–7d, mostly mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P2_001 | Failing test for green-view minimum (single-line headline, no per-job notes echo) | .claude/scripts/test_cockpit_green.py | Red at start, green at P2 close |
| P2_002 | Failing test for amber card shape: title ≤6 words, body ≤2 lines ≤80 chars/line, primary/secondary/tertiary/dismiss actions | .claude/scripts/test_card_shape.py | Red at start |
| P2_003 | Failing test for red takeover view AND `block_on_red` blocking auto-commit | .claude/scripts/test_red_takeover.py | Red at start |
| P2_004 | Implement card-rendering refactor in `bcos-dashboard/cockpit.py` (or dashboard.js) consuming typed events from P1 | cockpit refactor | P2_001-3 green |
| P2_005 | Extend `actions_resolved.py` to track auto-heal events separately from explicit dismissals (state-change-resolved path) | actions_resolved.py extended | New endpoint records auto-heal event distinctly |
| P2_006 | Add `digest.auto_commit.block_on_red` flag to `schedule-config.json` schema; default `true` | Config schema + JSON sample | Schema validates |
| P2_007 | Implement `block_on_red` gate in dispatcher Step 7b (skip auto-commit when verdict=red, surface "Auto-commit paused" chip) | dispatcher SKILL.md update + script | Red-fixture run does not auto-commit |
| P2_008 | Replace prose frequency suggestions with `Apply` cards bound to existing `/api/schedule/preset` | Card renderer + endpoint binding | Frequency-tuning fixture renders as card |
| P2_009 | Cache-invalidation tests for cockpit composition (per L-DASHBOARD-20260425-012) | .claude/scripts/test_cache_invalidation.py | Mutation handler invalidates every composing panel |
| P2_010 | Wiring test: every card type renders for at least one fixture finding | .claude/scripts/test_card_coverage.py | Green at P2 close |

### Phase 3 — Headless actions layer (5d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P3_001 | Failing wiring test for `headless-actions.md` schema: each action has `{id, label, type, reversible-by, telemetry-event}` | .claude/scripts/test_headless_actions.py | Red at start |
| P3_002 | Create `.claude/skills/schedule-dispatcher/references/headless-actions.md` with 9 action defs | New reference doc | doc-lint clean; schema valid |
| P3_003 | Implement `/api/actions/headless` dashboard endpoint that dispatches by `action.id` | Endpoint in server.py | Each action invokable |
| P3_004 | Implement each of 9 headless actions (inbox-aged triage, stale-propagation mark-reviewed, source-summary refresh, refresh-due, graveyard-stale archive, orphan-pages, retired-page-type migration, coverage-gap stub, lesson-candidate add) | 9 action handlers | Each action records resolution event (P4) |
| P3_005 | Add `headless_actions.enabled[]` array to `schedule-config.json`; default = all 9 enabled | Config schema | Disabled action returns 403 from endpoint |
| P3_006 | Wiring test: each headless action references a known finding_type, has a `reversible-by` clause, has a telemetry event | .claude/scripts/test_headless_wiring.py | Green at P3 close |
| P3_007 | Cross-link `auto-fix-whitelist.md` ↔ `headless-actions.md` so the relationship (silent vs one-click) is documented | Both docs updated | Cross-refs valid |

### Phase 4 — `resolutions.jsonl` infrastructure + chat-side recording (5d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P4_001 | Failing schema test: all 12 fields required from day 1 (P0_003 from earlier) | Already created in P0 | Green at P4 close |
| P4_002 | Implement shared library `.claude/scripts/record_resolution.py` | New script + unit tests | Library writes to `.claude/quality/ecosystem/resolutions.jsonl` append-only |
| P4_003 | Wire `record_resolution` into `/api/actions/resolve` (dashboard click path; trigger=`dashboard-click`) | actions_resolved.py extended | Click → resolution event |
| P4_004 | Wire `record_resolution` into headless action endpoint (P3) for `chat-bulk-fix` and `chat-targeted-fix` paths | Endpoint extended | Headless invocation → resolution event |
| P4_005 | Implement `bulk_id` grouping (UUID assigned per chat phrase; one bulk_id per command) | Library logic | One phrase = one bulk_id across N events |
| P4_006 | Implement `user_specificity` classifier (`global` / `category` / `targeted`) from `natural_language_command` pattern matching | Classifier in record_resolution.py | "fix it all" → global; "fix the wiki ones" → category; "fix this page" → targeted |
| P4_007 | Capture `applied_diff_summary` + `applied_diff_hash` via git diff -p at fix-application time | Capture function + tests | Hash deterministic for same diff |
| P4_008 | Lazy `subsequent_validation_status` writeback via transient `.claude/hook_state/pending-validations.jsonl`, drained by `post_edit_frontmatter_check.py` | Queue + drain logic | Hook stamps validation status within 24h |
| P4_009 | Soft-dep coordination: if wiki-missing-layers/P4 has shipped resolutions.jsonl writer, this phase EXTENDS rather than CREATES; else creates from scratch | Coordination check at P4 start | Plan honors first-shipper rule |
| P4_010 | Wiring test: every existing fix path (auto-fix whitelist, headless actions, chat bulk-fix) records a resolution event with all 12 fields | .claude/scripts/test_resolution_coverage.py | Green at P4 close |

### Phase 5 — Self-learning v0.1 (preselect tier only) (3d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P5_001 | Failing test for promotion-ladder logic at preselect tier (N≥3 + consistency=1.0 → preselect) | .claude/scripts/test_promotion_ladder.py | Red at start |
| P5_002 | Implement `.claude/scripts/promote_resolutions.py` (computes consistency, group counts) | New script | Test passes; learned-rules.json regenerates byte-stable |
| P5_003 | Implement `.claude/quality/ecosystem/learned-rules.json` schema (derived from resolutions, regeneratable per D-03) | Schema doc + sample | Schema validates |
| P5_004 | Wire promotion read into monthly `architecture-review` (extend job-architecture-review.md to surface "rules learned this month" with breakdown by `trigger`) | Job reference updated | Architecture-review fixture surfaces preselects |
| P5_005 | Render "✨ suggested" badge on cards where learned default applies (extend dashboard card renderer) | Card renderer extended | Badge appears for matching finding_type+action_taken pairs |
| P5_006 | Implement `/learning forget <rule-id>` slash command (removes from learned-rules.json + adds to `.claude/quality/ecosystem/learning-blocklist.json`) | New slash command | Forgetting clears badge on next render |
| P5_007 | Wiring test: learned-rules.json regenerates byte-stable from resolutions.jsonl + blocklist | .claude/scripts/test_derived_artifact.py | Per L-ECOSYSTEM-20260501-013 |

### Phase 6 — Auto-fix auditor v0.1 (reversal detection only) (5d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P6_001 | Failing test for reversal detection: fixture with applied_diff_hash followed by exact-inverse undo commit | .claude/scripts/test_auditor_reversal.py | Red at start |
| P6_002 | Create `.claude/skills/schedule-dispatcher/references/job-auto-fix-audit.md` (Friday weekly, autonomy=`auto`) | New job reference doc | doc-lint clean |
| P6_003 | Implement `.claude/scripts/auto_fix_audit.py` (reversal check via applied_diff_hash + 7-day commit window) | New script | P6_001 green |
| P6_004 | Add `auto-fix-audit` to `schedule-config.json` (cron Fri, autonomy=`auto`) | Config update | Dispatcher routes job |
| P6_005 | Implement >5% reversal threshold → amber card "Rule X had N reversals in 7 days. [Demote] [Show evidence] [Keep silent]" | Card renderer + amber path | Fixture triggers amber card |
| P6_006 | Wiring test: new job is registered in dispatcher SKILL AND has its reference doc AND emits typed events from P1 (per L-ECOSYSTEM-20260504-015) | .claude/scripts/test_auditor_wiring.py | Green at P6 close |
| P6_007 | Demotion path is recommend-only at v0.1: button click triggers user confirmation; no auto-action | Confirmation UI | No auto-demote path exists |

### Phase 7 — Self-learning v0.2 + auditor v0.2 (~10d, mostly mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P7_001 | Failing test for auto-apply tier (N≥5 + consistency≥0.9 + min_calendar_span_days≥14) | .claude/scripts/test_auto_apply_tier.py | Red at start |
| P7_002 | Extend `promote_resolutions.py` with auto-apply tier | Script extended | P7_001 green |
| P7_003 | Implement 10-second undo countdown UI on auto-apply cards (cockpit countdown component) | UI component | Manual click during 10s reverts; after 10s, applied + recorded |
| P7_004 | Failing test for validation-failure auto-disable: N≥5 across ≥3 distinct files in 24h | .claude/scripts/test_auditor_auto_disable.py | Red at start |
| P7_005 | Extend `auto_fix_audit.py` with Check 2 (validation-failure correlation) AND auto-disable path; only auto-action authority per D-04 | auto_fix_audit.py extended | Test green; min_distinct_targets enforced |
| P7_006 | Failing test for downstream-error correlation (Check 3): index-health flips green→amber within 24h of fix batch | .claude/scripts/test_auditor_downstream.py | Red at start |
| P7_007 | Extend `auto_fix_audit.py` with Check 3 (recommend-only via amber card) | auto_fix_audit.py extended | Test green |
| P7_008 | Implement `/settings/learning` dashboard panel: rules-being-watched / pending-promotion / promoted-to-suggest / promoted-to-auto-apply / auto-disabled | Panel + cockpit composition | Each tier renders with rule list |
| P7_009 | Implement evidence view per rule (sparkline of consistency over time + scrollable list of resolution events with bulk_id grouping) | Evidence view component | Drill-down works for fixture rule |
| P7_010 | Implement demote/forget buttons in `/settings/learning` (per-tier "demote" + global "forget") | Action buttons | Demotion flow records resolution event with `trigger: dashboard-click`, `action_taken: demote-rule` |
| P7_011 | Cache-invalidation tests for `/settings/learning` panel composition (per L-DASHBOARD-20260425-012) | .claude/scripts/test_learning_panel_cache.py | Mutation invalidates panel + cockpit summary |
| P7_012 | Wiring test: auto-disable carve-out fires at exactly the documented threshold; rules in `schema-migration-in-flight` state are skipped | .claude/scripts/test_auto_disable_threshold.py | Green at P7 close |

### Phase 8 — CONDITIONAL: silent tier + LLM semantic-drift + flap detection (~7d when triggered)

**Entry criteria (gated, must be checked before starting P8):**
1. Auditor has been clean (no critical demotions) for 6+ consecutive weeks
2. User has set `learning.silent_tier_opt_in: true` in `schedule-config.json`
3. User explicitly invokes "begin Phase 8" via planner or direct task

| ID | Task | Output | Verification |
|---|---|---|---|
| P8_000 | Entry-criteria gate: assert auditor history clean for 6+ weeks AND opt-in flag set; refuse to proceed otherwise | Gate script | Refusal path exits cleanly |
| P8_001 | Failing test for silent-tier promotion (N≥10 + consistency≥0.95 + 6+ weeks auditor-clean) | .claude/scripts/test_silent_tier.py | Red at start |
| P8_002 | Extend `promote_resolutions.py` with silent tier (writes to whitelist via human-confirmation flag — even silent promotion requires one explicit user click "OK to promote `<rule>` to silent") | Script + confirmation UI | One-time user click required per silent promotion |
| P8_003 | Failing test for cross-rule flap detection: A→B→A pattern in resolutions for same `(file, finding_type)` within 30d | .claude/scripts/test_flap_detection.py | Red at start |
| P8_004 | Implement Check 5 (cross-rule conflict / ping-pong, mechanical) in `auto_fix_audit.py` | Check 5 implementation | Test green |
| P8_005 | LLM-gated Check 4: semantic drift on body-touching fixes — does `domain:` still match the body after auto-fix? `--semantic` flag, opt-in only, never auto-fires | Check 4 + flag | Without flag, no LLM call ever |
| P8_006 | Wiring test: silent tier requires explicit user opt-in flag set in schedule-config.json AND blocks promotion if flag is false | .claude/scripts/test_silent_tier_gate.py | Green at P8 close |
| P8_007 | Doc updates: when to consider silent tier; what evidence to look for; how to roll back | New section in `maintenance-lifecycle.md` | doc-lint clean |

### Phase 9 — FIXED END (~1d, mechanical)

| ID | Task | Output | Verification |
|---|---|---|---|
| P9_001 | Run JSON lint on `schedule-config.json`, `headless-actions.md` schema, `learned-rules.json` schema, `resolutions.jsonl` schema | doc-lint output clean | All JSON parses + matches schema |
| P9_002 | Run markdown quality check (doc-lint) on every new/changed doc | MD040, links, headings | Clean output |
| P9_003 | Run integration audit: `python .claude/scripts/analyze_integration.py --staged` | Integration report | No stale cross-refs; new files registered |
| P9_004 | Update `.claude/quality/ecosystem/state.json` via discovery scripts | Refreshed state | `lastUpdated` matches today |
| P9_005 | Capture learnings via `ecosystem-manager` skill (lessons from P0–P8 surfaces) | Lessons appended to lessons.json | New lesson IDs added |

---

## 5. Cross-cutting Discipline

- **Every phase has a wiring test** that asserts (config + reference doc + dispatcher mention + endpoint registration) all agree. Per L-ECOSYSTEM-20260504-015.
- **Every phase ships TDD-first** — failing test before implementation. Per cleanup-pass precedent.
- **Plan-manifest is part of the regression suite** — a test asserts `plan-manifest.json[tasks].status` reflects implementation reality. Per L-ECOSYSTEM-20260504-014.
- **No phase starts before previous is production-stable for the gate window** (14d default, 7d dashboard-only, 28d ladder transitions). This is enforced by the planner reading the previous phase's `completedAt` from `plan-manifest.json`.
- **Cache invalidation is tested explicitly** — every panel that composes another panel has a POST-handler test that asserts both invalidations fire. Per L-DASHBOARD-20260425-012.

---

## 6. Risks & Mitigations

| ID | Risk | Mitigation |
|---|---|---|
| R-01 | `resolutions.jsonl` schema collision with wiki-missing-layers/P4 | P4_009 explicitly checks: if other plan shipped first, extend; else create. Both plans cite the same schema contract doc. |
| R-02 | Cockpit cache-invalidation gotcha (L-DASHBOARD-20260425-012) | P2_009 + P7_011 add explicit cache-invalidation tests for every composing panel. |
| R-03 | Auditor false-positives during schema-version-drift mass-disable rules | P7_005 enforces `min_distinct_targets: 3` AND skips rules with `schema-migration-in-flight: true` flag. |
| R-04 | Self-learning bias from one panicky cleanup session | P7_001 enforces `min_calendar_span_days = 14` so 3 clicks in one panic session don't promote. |
| R-05 | Ladder transitions destabilize a previously-quiet rule | P5/P7/P8 each have a 28-day cooldown gate; auditor's reversal-rate trendline surfaces regression within one week. |
| R-06 | User wrongly forgets a learned rule and never sees evidence again | `/learning forget` adds to `learning-blocklist.json` (not deletes); `/settings/learning` shows blocked rules with "unblock" path. |
| R-07 | Phase 8 LLM check costs creep up | P8_005 makes `--semantic` opt-in only; default is mechanical-only flap detection (Check 5). |
| R-08 | Silent-tier promotion is one-way | P8_002 requires explicit user click "OK to promote to silent" for each rule, even when ladder math says yes. Demote-from-silent path always available via `/learning forget`. |

---

## 7. Artifacts (created by this plan)

| Path | Type | Phase |
|---|---|---|
| `docs/_bcos-framework/architecture/typed-events.md` | Authority doc | P0 |
| `.claude/quality/fixtures/digests/{green,amber,red}.{md,json}` | Fixtures | P0 |
| `.claude/scripts/digest_sidecar.py` | Script | P1 |
| `.claude/skills/schedule-dispatcher/references/headless-actions.md` | Reference doc | P3 |
| `.claude/scripts/record_resolution.py` | Shared library | P4 |
| `.claude/quality/ecosystem/resolutions.jsonl` | Append-only event log | P4 (or shared with wiki-missing-layers) |
| `.claude/quality/hook_state/pending-validations.jsonl` | Transient queue | P4 |
| `.claude/scripts/promote_resolutions.py` | Script | P5 |
| `.claude/quality/ecosystem/learned-rules.json` | Derived artifact | P5 |
| `.claude/quality/ecosystem/learning-blocklist.json` | Authored truth | P5 |
| `.claude/skills/schedule-dispatcher/references/job-auto-fix-audit.md` | Reference doc | P6 |
| `.claude/scripts/auto_fix_audit.py` | Script | P6 |
| `/settings/learning` dashboard panel | UI | P7 |
| `/settings/auditor` dashboard panel | UI | P7 |
| Plus extensions to: `labels.py`, `digest_parser.py`, `actions_resolved.py`, `cockpit.py`, `server.py`, `schedule-config.json`, `system-design.md`, `schedule-dispatcher/SKILL.md`, every existing `job-*.md` reference | Edits | P1–P7 |

---

## 8. Next Actions

| Action | Description |
|---|---|
| **Approve** | Plan ready as written. Update manifests to `approved`; plan is committed; implementation can begin at P0 in a fresh session. |
| **Modify** | Plan needs revision. Tell me what to change (phase split, scope cut, ordering, dependency handling). I'll re-present at Gate 2. |
| **Cancel** | Stop here. Plan is archived; no implementation. |

---

## 9. References

- This plan: `docs/_planned/autonomy-ux-self-learning/`
  - `implementation-plan.md` (this file)
  - `plan-manifest.json` (machine-readable manifest)
  - `pre-flight-decisions.md` (defaulted decisions D-01 → D-05)
- Working planner state: `.claude/quality/sessions/20260504_191019_autonomy-ux-self-learning/` (gitignored)
- Soft dependency: `docs/_planned/wiki-missing-layers/` (in implementation; coordinates on `resolutions.jsonl`)
- Audit findings driving this plan: this conversation, 2026-05-04 18:00 UTC (UX/autonomy + maintenance/output + auto-fix-auditor extensions)
