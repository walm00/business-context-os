---
name: "Autonomy + UX + Self-Learning — Plan README"
type: orientation
cluster: "Framework Evolution"
version: 1.0.0
status: awaiting_approval
created: 2026-05-04
last-updated: 2026-05-04
---

# Autonomy + UX + Self-Learning — Plan README

**One-paragraph orientation.** This plan ships the autonomy + UX + self-learning surface for the schedule-dispatcher / digest / dashboard / learning ecosystem. The principle: **complexity below the surface is fine; complexity at the user's hands is not.** Today the digest line-level format is prose, the dashboard re-parses it, and the user re-types decisions every day. This plan migrates action items to typed events, introduces one-click headless actions, records every fix to `resolutions.jsonl`, builds a self-learning ladder (preselect → auto-apply → silent), and adds an auto-fix auditor as the safety brake. Mechanical-first throughout; LLM only in the conditional Phase 8.

## Files in this folder

- [`implementation-plan.md`](implementation-plan.md) — full PRD + 70-task plan across 10 phases (P0 foundation + P1–P8 + P9 fixed-end; P8 conditional)
- [`plan-manifest.json`](plan-manifest.json) — machine-readable manifest; cross-session resumption format
- [`pre-flight-decisions.md`](pre-flight-decisions.md) — five pre-flight decisions (D-01 → D-05), all defaulted

## Status

| Field | Value |
|---|---|
| Status | `awaiting_approval` (Gate 2) |
| Total phases | 10 (P0–P9; P8 conditional) |
| Total tasks | 70 |
| Estimate | 38–46 days for P0–P7 + P9; +7 days P8 |
| Soft dependency | `docs/_planned/wiki-missing-layers/` (in implementation; coordinates on `resolutions.jsonl` schema) |

## Why this is separate from `wiki-missing-layers/`

The wiki/context plan delivers the cross-zone retrieval surface and sub-agent isolation. This plan delivers the autonomy + UX surface. They are independent in scope but share one schema (`resolutions.jsonl`'s 12 fields). Whichever plan ships its writer first creates the file; the other extends. Both plans cite the same schema contract — no duplication, no migration debt.

## Phase summary

| Phase | Title | Days | Mechanical/LLM |
|---|---|---|---|
| P0 | Foundation: fixture corpus + discovery wiring tests | 1 | Mechanical |
| P1 | Line-level digest structure (typed events + labels) | 3-5 | Mechanical |
| P2 | Dashboard cards + cockpit composition + `block_on_red` gate | 5-7 | Mechanical |
| P3 | Headless actions layer (`headless-actions.md` + 9 actions) | 5 | Mechanical |
| P4 | `resolutions.jsonl` infrastructure + chat-side recording hook | 5 | Mechanical |
| P5 | Self-learning v0.1 (preselect tier only) | 3 | Mechanical |
| P6 | Auto-fix auditor v0.1 (reversal detection only) | 5 | Mechanical |
| P7 | v0.2: auto-apply + auditor checks 2-3 + `/settings/learning` panel | 10 | Mechanical |
| P8 | **CONDITIONAL** — silent tier + LLM semantic-drift + flap detection | 7 | Mostly mechanical; one LLM check |
| P9 | **FIXED END** — JSON lint + MD lint + integration audit + ecosystem state + learnings | 1 | Mechanical |

## Resumption guide (for fresh sessions)

> Read [`plan-manifest.json`](plan-manifest.json), find the lowest-numbered task with `status: "pending"`, and start there. Each task's `verification` field tells you when it's done. If `dependsOn` is set, those tasks must be `completed` first.

The plan is designed to survive any session boundary. Task IDs (`P0_001` through `P9_005`) are stable; status is read from `plan-manifest.json`; tests assert reality matches the manifest.
