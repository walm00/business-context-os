---
name: "Autonomy + UX + Self-Learning — Pre-Approval Review (2026-05-05)"
type: review
cluster: "Framework Evolution"
version: 1.0.0
status: defaulted
created: 2026-05-05
last-updated: 2026-05-05
---

# Pre-Approval Review — 2026-05-05

Second review of the plan against current repo state, run the day after the plan was authored. The plan was promoted from `.private/_planned-archive/` back to `docs/_planned/` earlier today; this review verifies its assumptions still hold before Gate-2 approval.

> **Method.** First pass against working tree only flagged 4 hard misalignments. A second pass adding `git log` + `.gitignore` + worktree inspection downgraded most of them — the assets exist, they're just gitignored or parked in `.private/`. Only one is a real authoring error.

---

## TL;DR — what to patch before approval

| # | Concern | Severity (revised) | Status |
|---|---|---|---|
| A | Test paths use `tests/test_*.py` | **Real authoring error** | OPEN. Rewrite to `.claude/scripts/test_*.py` throughout. That folder is gitignored (`.gitignore:133`) — tests are dev-only by design and don't ship to public BCOS, which is fine. |
| B | `lint_json.py` doesn't exist (P9_001) | **Real authoring error** | OPEN. Replace with `python -m json.tool` (matches `publish.sh:107-120`) plus existing `analyze_integration.py --ci`. |
| C | The 7 cited lessons aren't in `lessons.json` | **FALSE ALARM** (query bug) | RESOLVED — see correction box below. |
| D | Soft-dep `wiki-missing-layers/` not in `_planned/` | **Decision, not blocker** | RESOLVED 2026-05-05 — promoted from `.private/_planned-archive/` to `docs/_planned/wiki-missing-layers/`. The schema-coordination clause in D-05/P4_009 stays as written; both plans now coordinate on `resolutions.jsonl`. |

Plus 4 soft clarifications (E–H) below that should be inlined for the implementer but don't gate approval.

> **Correction box — 2026-05-05 13:50.** Finding C above was a query bug in the original review pass: I queried `d.get('lessons', [])` against the lessons file, but the actual schema uses `lessonsLearned`. Re-running with the correct key shows the canonical `.claude/quality/ecosystem/lessons.json` actually has **22 lessons**, including ALL 7 plan-referenced lessons plus 6 more (`L-ECOSYSTEM-20260504-017` through `-022`) that were captured after the plan was authored. No capture-debt; no migration needed. Section C below is retained for archival honesty but should be read as "this concern was raised and dismissed." Apologies for the noise.

---

## Detailed findings

### A. `tests/` path convention — REAL ERROR

**Plan claims:** `tests/test_digest_typed_events.py`, `tests/test_resolutions_jsonl_schema.py`, `tests/test_red_takeover.py`, etc. (≈30 references across phases P0–P8).

**Repo reality (HEAD + working tree + git history):**
- No `tests/` directory has ever existed in git history (`git log --all -- 'tests/**'` empty).
- 7 test files DO live at `.claude/scripts/test_*.py` (`test_wiki_capability.py`, `test_context_index.py`, etc.) — but `.gitignore:133` excludes them (`.claude/scripts/test_*.py`). These were once tracked, then deliberately untracked by commit `33b3584` ("Remove .claude fixtures and tests") on 2026-05-05.
- Conclusion: **tests are dev-only by design, not shipped to public BCOS**. The plan's `tests/` paths are simply wrong — should be `.claude/scripts/test_*.py`.

**Action:** Find/replace `tests/test_` → `.claude/scripts/test_` in `implementation-plan.md` (every phase) and `plan-manifest.json` (every `outputArtifact` and `verification.command`). Add a one-liner to D-07 stating tests are gitignored dev infrastructure, intentional.

---

### B. `lint_json.py` (P9_001) — REAL ERROR

**Plan claims:** `python .claude/scripts/lint_json.py` runs JSON lint in P9_001.

**Repo reality:**
- Never existed in git history.
- `publish.sh:107-120` already does the JSON lint via `python3 -m json.tool` against the same file set.
- `analyze_integration.py --ci`, `validate_frontmatter.py`, `validate_references.py` cover everything else P9_001 needs.

**Action:** Rewrite P9_001 verification command to:
```
python -m json.tool .claude/quality/schedule-config.json &&
python -m json.tool .claude/quality/ecosystem/learned-rules.json &&
python -m json.tool .claude/quality/ecosystem/learning-blocklist.json &&
python .claude/scripts/analyze_integration.py --ci
```

---

### C. The 7 lessons — FALSE ALARM (RESOLVED)

> **Resolution 2026-05-05:** All 7 lessons are present in canonical `.claude/quality/ecosystem/lessons.json` (which has 22 lessons total). The original concern below was a query bug — wrong JSON key. Section retained for archival honesty.

**Original (incorrect) finding follows:**



**Plan claims** (in `relevantLessons[]`): `L-DASHBOARD-20260425-010/011/012`, `L-ECOSYSTEM-20260501-013`, `L-ECOSYSTEM-20260504-014/015/016`.

**Repo reality:**
- Main `lessons.json`: `totalLessons: 0`, `lessonsLearned: []`. Reset to starter via commit `6e65188` ("Replace lessons.json with starter template"). Not gitignored — tracked but emptied.
- 5 worktrees DO have these lessons:
  - `compassionate-rubin-e1965d`: 16 lessons including all 7
  - `confident-knuth-ca4d77`: 16 lessons including all 7
  - `jolly-cerf-6b5d97`: 16 lessons including all 7
  - `friendly-ptolemy-4bef71`: 13 lessons including 4 of 7
  - `frosty-satoshi-57d7ab`: 13 lessons including 4 of 7
  - `musing-agnesi-a66a4e`: 12 lessons including 3 of 7
- `lessons-starter.json` has 9 `L-INIT-*` lessons; none of the L-DASHBOARD or L-ECOSYSTEM-2026050x lessons.

**Why this is capture-debt rather than blocker:** the 7 lessons are real artefacts of past sessions; they were just never propagated from worktree-local `lessons.json` back to `.claude/quality/ecosystem/lessons.json`. The plan's rationale is sound; the references just don't resolve in HEAD.

**Action — pick one:**
1. **Inline.** Edit `relevantLessons[]` in `plan-manifest.json` to keep IDs but replace `lesson:` and `applicability:` text with the rationale verbatim, so the plan stands alone without depending on `lessons.json` lookup.
2. **Capture-and-cite.** Add a P0_005 task: "Migrate 7 referenced lessons from worktree (`.claude/worktrees/compassionate-rubin-e1965d/.claude/quality/ecosystem/lessons.json` is the most complete source) into main `lessons.json`. Verify via `python -m json.tool` and frontmatter-style schema check."

Recommendation: **option 2** (capture). The lessons are useful beyond this plan; merging them back to main is good hygiene anyway.

---

### D. `wiki-missing-layers/` soft-dep — RESOLVED 2026-05-05

> **Resolution:** Plan promoted from `.private/_planned-archive/wiki-missing-layers/` to `docs/_planned/wiki-missing-layers/` on 2026-05-05 (mirror of the autonomy plan's earlier promotion). Both plans are now active in `docs/_planned/` and coordinate on the `resolutions.jsonl` schema as originally designed. D-05 and P4_009 stay as written.

**Original finding follows:**



**Plan claims:** Soft-dep on `docs/_planned/wiki-missing-layers/` for `resolutions.jsonl` schema coordination.

**Repo reality:**
- Not in `docs/_planned/` (HEAD has only `autonomy-ux-self-learning/` after today's promotion).
- Original location: `docs/_planned/wiki-missing-layers/` was committed in `686292f` ("Add wiki-missing-layers plan to _planned/ (approved at Gate 2)"), then archived into `.private/_planned-archive/` along with several other plans by `33b3584`.
- Currently sits at `.private/_planned-archive/wiki-missing-layers/` — same parking lot the autonomy plan came from this morning.
- Worktrees that contained both plans (`jolly-cerf-6b5d97`, `compassionate-rubin-e1965d`, etc.) confirm they were intended as sibling plans coordinating on the same schema.

**Why this is decision-not-blocker:** the soft-dep mechanism (first-shipper creates `resolutions.jsonl`; other extends) is sound but only kicks in if both plans are active. With wiki-missing-layers parked, autonomy plan is the sole creator de facto.

**Action — pick one:**
1. **Promote wiki-missing-layers back too** (mirror of what we did for autonomy this morning). Keep D-05 + P4_009 as written; both plans coordinate.
2. **Drop the coordination clause.** Edit D-05 + P4_009 to say "autonomy plan is the sole creator of `resolutions.jsonl`; if `wiki-missing-layers/` is later un-archived and needs the same schema, this plan's contract becomes the spec it must match."

Recommendation: depends on whether wiki-missing-layers is still alive. The 2026-05-04 diary entry says its main problems "remain real" but flagged metadata/schema drift before implementation. If it's coming back, **option 1**; if it's truly parked, **option 2**.

---

### E. Schema migration for `digest.auto_commit` (P2_006) — clarify

`digest.auto_commit` is currently a flat boolean, written/read by:
- `set_auto_commit(enabled: bool)` ([schedule_editor.py via run.py:267-273](.claude/scripts/bcos-dashboard/run.py))
- `_post_auto_commit` POST handler at `/api/schedule/auto-commit`
- `_get_auto_commit` GET handler

P2_006 changes the schema to `{enabled, block_on_red}`. Without an explicit migration, the existing endpoints break.

**Action:** P2_006 should specify the migration: keep `digest.auto_commit` as flat boolean for `enabled`, add a sibling `digest.auto_commit_block_on_red: bool` (default `true`). This avoids touching `set_auto_commit()` signature and keeps the existing endpoint working. Or, if the nested object is preferred, P2_007 must include the `set_auto_commit` refactor + a new `set_auto_commit_block_on_red` setter.

---

### F. P4_008 `pending-validations.jsonl` location — note compatibility with new dispatcher rule

This session added a rule to dispatcher SKILL.md: "no ad-hoc helper scripts in `.claude/hook_state/`" (sensitive folder triggers approval prompts). P4_008 places `pending-validations.jsonl` (data file) in that folder — fully compatible: `schedule-diary.jsonl` and `actions-resolved.jsonl` already live there as data files. Only `.py` script creation is forbidden.

**Action:** P4_008 should briefly say "data-only, no helper scripts in `.claude/hook_state/`" so a future implementer doesn't accidentally invent a `drain_validations.py` there.

---

### G. P3 chat-intercept hook — needs explicit design

P3/P4 require capturing `natural_language_command` (the user's free-text fix phrase) for `bulk_id` grouping (P4_005) and `user_specificity` classification (P4_006).

**Repo reality:** `.claude/hooks/` has only `auto_save_session.sh`, `precompact_save.sh`, `post_edit_frontmatter_check.py`, `post_commit_context_check.py`. No `UserPromptSubmit` hook exists. The current `Stop` hook fires after assistant turn, not on user input.

**Available approaches:**
1. Add a `UserPromptSubmit` hook (Claude Code supports this matcher) that captures user text into a transient file, drained when the next headless action fires.
2. Accept that `natural_language_command` is supplied by the AI assistant as a parameter when calling `/api/actions/headless` (the assistant already sees the user phrase in context).
3. Skip the field in v0.1; classify `user_specificity` heuristically from `action_target` patterns.

**Action:** Add a P3_008 task: "Decide chat-intercept mechanism for `natural_language_command` capture: hook-based vs assistant-supplied vs heuristic." This is currently an unstated assumption in the plan.

---

### H. P5_004 `architecture-review` integration point — clarify

P5_004 says "Wire promotion read into monthly `architecture-review` (extend `job-architecture-review.md` to surface 'rules learned this month' with breakdown by `trigger`)".

[job-architecture-review.md](.claude/skills/schedule-dispatcher/references/job-architecture-review.md) is pure markdown without structured slots; "extend" means adding a new step + section. Needs to specify: where in the existing 5-step procedure does the new "Read learned-rules.json" step go, and which heading does the surfaced output land under?

**Action:** Cosmetic; specify at task time. Example: "Add new step 6 'Surface learned rules' between current step 5 (Lessons retention) and step 6 (Output). Surface as a new section in the monthly report under heading 'Rules learned this month'."

---

## Things still aligned (confirmed by git history)

- All 9 `job-*.md` references present in HEAD ✓
- 12 auto-fix IDs match between [auto-fix-whitelist.md](.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md) and [schedule-config.template.json](.claude/quality/schedule-config.template.json) ✓
- All bcos-dashboard scripts plan claims to extend exist (`labels.py`, `digest_parser.py`, `actions_resolved.py`, `cockpit.py`, `server.py`, `run.py`) ✓
- No prior implementation of `block_on_red`, `finding_type`, `resolutions.jsonl`, `headless-action`, `record_resolution`, or `learned-rules` anywhere in HEAD or worktrees → greenfield, no merge conflicts ✓
- `bcos-wiki` skill present and healthy ✓
- `append_diary.py` exists for non-prompt diary writes (used by P1 sidecar pattern) ✓
- `.claude/hook_state/*` gitignored except `.gitkeep` — confirms data files there are dev-local by design (consistent with P4_008's `pending-validations.jsonl`) ✓

---

## Recommended approval path

After the 2026-05-05 corrections, only A, B, and the soft items E–H are open:

1. Apply patches A and B (real authoring errors) directly to `implementation-plan.md` + `plan-manifest.json`.
2. Inline soft clarifications E–H as parenthetical notes in their respective tasks.
3. Update `plan-manifest.json` `planStatus` from `awaiting_approval` to `approved` with a `userApproval` block.
4. Bump `implementation-plan.md` version 1.0.0 → 1.1.0 and `last-updated` → 2026-05-05.

After those, P0_001 can begin in a fresh session.
