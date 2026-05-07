---
name: "Context Base — Missing Layers (search, sub-agent isolation, stub repair, task-driven routing, embeddings)"
type: reference
cluster: "Framework Evolution"
version: 1.2.0
status: completed
created: 2026-05-04
last-updated: 2026-05-04
---

# Context Base — Missing Layers

Polished proposal for the next layers of BCOS's context base: a cross-zone retrieval surface, sub-agent isolation for big-body work, wiki-zone stub repair, and (architecturally most important) task-driven cross-zone routing. Wiki is one zone among several — this plan operates on the whole context surface, not just `_wiki/`.

## Status

**`completed` (2026-05-04).** All 7 phases shipped:

- **P1 — Zone Registry** (8/8): canonical zone classifier + declarative companion + drift test
- **P2 — Cross-Zone Search** (9/9): mechanical BM25 over `context-index.json`; `--semantic` opt-in only
- **P3 — Sub-Agent Isolation** (9/9): `wiki-fetch` agent, contract validator, cumulative budget guard with concrete batch plan
- **P4 — Wiki Stub Repair** (9/9): consolidated YAML parser, real HEAD/ETag check, real schema 1.0↔1.1 migration, Jaccard duplication lint
- **P5 — Task-Driven Cross-Zone Routing** (12/12): 9 built-in profiles, bundle resolver, conflict detection, freshness verdicts, traversal hops
- **P6 — Embeddings** (deferred): conditional on real precision-wall evidence; not triggered
- **P7 — FIXED END** (5/5): doc-lint clean, integration audit clean, ecosystem state refreshed, 6 institutional learnings captured

**130 tests across 7 suites green. Ecosystem HEALTHY. Ready for public release.**

See [plan-manifest.json](plan-manifest.json) `planStatusHistory` for the full delivery trail (Gate 2 approval, post-Gate-2 cleanup pass, three rounds of audit fixes during implementation, P7 closure).

## Why now

The wiki-zone integration shipped (`e887eaa Integrate wiki zone`). The canonical context model also shipped on 2026-05-04 (`871ff4d Generate context index; add frontmatter warnings`) — `.claude/scripts/context_index.py` and `.claude/quality/context-index.json` now provide a single normalized model of every zone's frontmatter, edges, ownership, and freshness.

Data is shaped right and a canonical model exists, but several load-bearing layers are still missing:

1. No retrieval surface across zones (grep-and-pray today, even though the corpus index is built).
2. No sub-agent isolation for big-body work (200k-token URL fetches saturate main context).
3. Phantom stubs in wiki (HEAD/ETag claim, `duplication-vs-data-point` lint, schema migration).
4. Three hand-rolled YAML parsers risk silent drift.
5. **No task-driven context routing.** The wiki answers "what do we know about X?"; it does NOT answer "I'm about to do task T — what context bundle do I need, with what freshness, what source-of-truth ranking, what perspectives am I missing?"

## Scope

**Context-base-wide.** The plan targets every zone where context lives, not just wiki:

| Zone | Path | State today |
|---|---|---|
| Top-level data points | `docs/<slug>.md` | Empty in this repo (templated; populated in real deployments) |
| Framework spec | `docs/_bcos-framework/{methodology,architecture,guides,templates,patterns}/` | Populated (24 files) |
| Plans | `docs/_planned/` | This proposal + others |
| Inbox | `docs/_inbox/` | Empty |
| Collections | `docs/_collections/` | Empty placeholder; spec'd in `collections-zone.md` |
| Archive | `docs/_archive/` | Empty |
| Wiki | `docs/_wiki/` | Spec'd; not initialized in this repo |
| Skills (as context) | `.claude/skills/*/SKILL.md` + `references/` | 14 skills |
| Lessons | `.claude/quality/ecosystem/lessons.json` | 16 entries |
| Registries | `.claude/registries/{entities,reference-index}.json` | Populated |
| Sessions | `.claude/quality/sessions/*/` | 12 historical planning records |

The plan must work for empty zones (graceful absence) and populated zones (full retrieval).

## Foundation already in place

| Asset | Role in this plan |
|---|---|
| `.claude/scripts/context_index.py` | Canonical context model. P1 wraps its zone semantics declaratively; P2 reads its JSON output as search corpus. |
| `.claude/quality/context-index.json` | Already-built corpus (52 docs in this repo) with frontmatter, edges, ownership, freshness, warnings. P2 reads this directly — no re-walk. |
| `.claude/scripts/build_document_index.py` | Consumer pattern of `context_index.py`. P2 search follows the same shape. |
| `.claude/agents/explore/AGENT.md` | Sub-agent prior art. P3 `wiki-fetch` borrows shape (work-in >> result-out). |

## Authority documents

- `docs/_bcos-framework/architecture/wiki-zone.md` — wiki zone spec; revised by P4 + P5
- `docs/_bcos-framework/architecture/collections-zone.md` — collections zone spec
- `docs/_bcos-framework/architecture/system-design.md` — overall ecosystem map; revised by P1
- `pre-flight-decisions.md` — 10 design decisions (D-01 through D-10); D-10 is mechanical-first / opt-in-only LLM (strict)

## Files in this proposal

| File | What it is |
|---|---|
| `pre-flight-decisions.md` | The 10 decisions (D-10 is mechanical-first / no-auto-trigger LLM, strict) |
| `implementation-plan.md` | PRD-style — problem, user stories, 7-phase delivery (P1–P7), risks, rollback, mechanical-vs-LLM split per phase |
| `plan-manifest.json` | Machine-readable plan — 58 tasks, 7 phases, follow-ups, JSON-schema compliant (task IDs match `^P[0-9]+_[0-9]{3}$`, phase ≥ 1, every task carries verification) |

## Sequencing

```
P1 (zone registry — declarative companion to context_index.py)
  |
  +--> P2 (cross-zone search over context-index.json) ---> P5 (task-driven routing)
  |                                                          ^
  +--> P3 (sub-agent isolation)                              |
  |                                                          |
  +--> P4 (wiki stub repair) -------------------------------+
  |
  P6 (embeddings) — CONDITIONAL on P2 outcomes
  |
  P7 (FIXED END — doc-lint, integration audit, ecosystem state, learnings)
```

P2, P3, P4 can land in parallel after P1. P5 requires P1 + P2. P6 is conditional on P2 outcomes.

**TDD ordering inside each phase:** fixture creation → failing regression test → implementation tasks → red→green driver → documentation deltas. Every task carries a `verification` block in the manifest.

## When this proposal graduates

Once approved and implemented, this folder moves to `docs/_archive/wiki-missing-layers/` (or is deleted). The shipped reality is documented in:

- `docs/_bcos-framework/architecture/context-zones.md` (NEW — created in P1)
- `docs/_bcos-framework/architecture/context-routing.md` (NEW — created in P5; or merged into existing `content-routing.md`)
- `docs/_bcos-framework/architecture/wiki-zone.md` (revised — P4 stub repair, P2/P5 retrieval surface notes)
- `.claude/skills/bcos-wiki/SKILL.md` (revised — `/wiki search` + `/wiki bundle` subcommands)
- `.claude/skills/context-routing/SKILL.md` (NEW — `/context search`, `/context bundle`)
- `.claude/agents/wiki-fetch/AGENT.md` (NEW — sub-agent for big-body work)
- `docs/_bcos-framework/templates/_context-zones.yml.tmpl` (NEW — zone registry, P1)
- `docs/_bcos-framework/templates/_context.task-profiles.yml.tmpl` (NEW — profile catalog, P5)
