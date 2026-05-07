---
name: "Wiki User-Action Scripts (follow-up to wiki-authority-temporal P5)"
type: orientation
cluster: "Framework Evolution"
version: 0.1.0
status: planned
created: 2026-05-06
last-updated: 2026-05-06
authority-docs:
  - .claude/quality/sessions/20260506_100433_wiki-authority-temporal/plan-manifest.json
  - docs/_planned/autonomy-ux-self-learning/implementation-plan.md
  - docs/_planned/wiki-headless-scripts/implementation-plan.md
follows-up-on: docs/_planned/autonomy-ux-self-learning/
---

# Wiki User-Action Scripts — Plan README

## Why this exists

This plan was split out from `wiki-authority-temporal` (P5) per D-08 in that
plan's manifest. P5 of `wiki-authority-temporal` aimed to add three dashboard
forms — `[Add URL to wiki]`, `[Promote inbox]`, `[Refresh page]` — that
trigger headless Python scripts mirroring the user actions today's
`/wiki run`, `/wiki promote`, and `/wiki refresh` perform inside Claude
chat.

The hard gate: those three scripts depend on `bcos-dashboard/run.py::SCRIPTABLE`
infrastructure that ships with `autonomy-ux-self-learning/`, which is still
`awaiting_approval` as of this writing. Building scripts without their
caller would mean unused code; deferring to a sibling plan is cleaner.

## When to start this plan

Start when **both** of the following are true:

1. `autonomy-ux-self-learning/` has shipped P3 (`headless-actions.md` + 9
   actions registered) and the dashboard's `SCRIPTABLE` registry exists.
2. `wiki-headless-scripts/` has shipped — its four maintenance scripts
   (`run_wiki_stale_propagation`, `run_wiki_source_refresh`,
   `run_wiki_graveyard`, `run_wiki_coverage_audit`) are the right model to
   copy from for these three user-action scripts.

The original plan-manifest in
`.claude/quality/sessions/20260506_100433_wiki-authority-temporal/plan-manifest.json`
already has the five P5 task descriptions ready to lift over — see
`P5_001` through `P5_005`. Pull them into this folder's
`implementation-plan.md` when triggering.

## Scope summary

Three new scripts under `.claude/scripts/`:

| Script | Card label | Notes |
|---|---|---|
| `run_wiki_ingest_url.py` | `[Add URL to wiki]` | Brief-mode mechanical (fetch + minimal page); standard / deep falls through to chat hint. Calls `_wiki_triage.classify()` post-write. |
| `run_wiki_promote_inbox.py` | `[Promote inbox file]` | Read inbox file; user-supplied page-type + cluster; provenance.kind = `inbox-promotion`. |
| `run_wiki_refresh_page.py` | `[Refresh wiki page]` | Uses `_wiki_http.py` HEAD/ETag quick-check tier; emits `wiki-temporal-supersession-candidate` when content materially changed. |

All three register with `bcos-dashboard/run.py::SCRIPTABLE` and emit typed
events compatible with `autonomy-ux-self-learning/` P1.

## Why I'm not building it now

- No caller exists. Even if the scripts worked, the dashboard form that
  invokes them does not yet render.
- The user-action API surface should match whatever shape
  `autonomy-ux-self-learning/` finalizes. Building before then risks rework.
- The four maintenance scripts in `wiki-headless-scripts/` are a cleaner
  reference model to copy from; that plan should ship first.

## Files in this folder (current)

- `README.md` (this file)

When activated, this folder will gain `implementation-plan.md` and
`plan-manifest.json` with the lifted P5 tasks plus a fresh FIXED END.

## Status

`planned`. Waiting on prerequisites listed above.
