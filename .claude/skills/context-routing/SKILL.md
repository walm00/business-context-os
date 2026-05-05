---
name: context-routing
description: "Cross-zone retrieval and task-driven bundle resolution for BCOS. /context search ranks docs across every zone in one shared schema; /context bundle (P5) returns a curated, freshness-flagged, source-of-truth-aware context bundle for a declared task. Mechanical-first; LLM is opt-in via --semantic / --resolve-conflicts / --verify-coverage flags only. Invoke with /context."
trigger: "/context"
version: "0.1.0"
last_updated: "2026-05-04"
authority-docs:
  - docs/_bcos-framework/architecture/context-zones.md
  - docs/_bcos-framework/architecture/system-design.md
  - docs/_planned/wiki-missing-layers/pre-flight-decisions.md
  - docs/_planned/wiki-missing-layers/implementation-plan.md
---

# /context

Cross-zone read foundation for BCOS. Reads the canonical corpus at
`.claude/quality/context-index.json` (built by `context_index.py`) and exposes:

- **`/context search`** — ranked hits across every zone (active, wiki, planned, collections, framework, …). Mechanical BM25; LLM-touching paths require explicit `--semantic` opt-in.
- **`/context bundle`** *(P5, not yet implemented)* — task-driven curated bundle: by-zone hits, freshness verdicts, source-of-truth conflicts, missing perspectives. LLM-touching paths require explicit `--resolve-conflicts` / `--verify-coverage` opt-in.

For zone-scoped sugar, see `/wiki search` (P2) and `/wiki bundle` (P5) which share this backend.

## Trigger phrases

- **`/context`** with subcommands: `search`, `bundle` (P5)
- "Find docs about competitor pricing across the whole repo"
- "Search the wiki and the plans for stripe billing"
- "Build me a context bundle for writing a market report" *(P5)*
- "What do we have on linkedin tone, ranked by source-of-truth?"

## Pipeline at a glance

```
docs/  →  context_index.py  →  .claude/quality/context-index.json
                                              ↓
                       /context search   →   context_search.py
                                              ↓
                                              ranked hits (zone-typed, citation-id'd)

                       /context bundle   →   context_bundle.py  (P5)
                                              ↓
                                              { by-zone, freshness, conflicts,
                                                missing-perspectives, traversal }
```

## Subcommands

| Command | Status | Phase | What it does |
|---|---|---|---|
| `search <query>` | implemented | P2 | Mechanical BM25 over the canonical context-index.json; cross-zone or `--zone <id>` filtered |
| `bundle <profile>` | implemented | P5 | Task-driven curated bundle per a profile from `_context.task-profiles.yml` — see `bundle.md` |

## Dispatch

1. Identify the subcommand from the first word after `/context`.
2. Route — read the sibling file in this skill directory and follow its instructions:
   - `search` → `search.md`
   - `bundle` → `bundle.md`
3. Do not proceed past dispatch before reading the target file.

## Guard rails

### D-10 strict — mechanical-first, opt-in escalation only

The default path for every subcommand is mechanical Python. **No LLM call ever fires implicitly.** LLM-touching paths exist only behind explicit flags:

- `/context search --semantic` — LLM reformulates the query into mechanical candidates.
- `/context bundle --resolve-conflicts` — LLM resolves unresolved source-of-truth conflicts. *(P5)*
- `/context bundle --verify-coverage` — LLM verifies prose-perspective coverage. *(P5)*

There is **no auto-trigger on 0-hit, no auto-fallback, no hidden cost**. If the user wants LLM help, they ask for it. If they don't, the engine returns the mechanical answer.

### Empty zones are graceful

When a declared zone is absent from the current repo (e.g., `_wiki/` not initialized, `_collections/` empty), search returns an empty hit list for that zone and surfaces it under `zones-skipped-not-present`. The agent decides whether to proceed, ask the user, or trigger initialization. Not a hard failure.

### Citation IDs are stable

Every hit carries a `citation-id` of the form `zone:slug` (for example, `wiki:linkedin-tone`, `planned:wiki-missing-layers`). The ID is path-derived and survives whitespace edits. Other agents reference back via this ID.

## Architectural placement

- [`context-zones.md`](../../../docs/_bcos-framework/architecture/context-zones.md) — what each zone is and how the path classifier maps to a declarative registry.
- [`context_index.py`](../../scripts/context_index.py) — the canonical model that builds `context-index.json`. Cross-zone retrieval reads this; never re-walks `docs/`.
- [`load_zone_registry.py`](../../scripts/load_zone_registry.py) — the loader every cross-zone consumer goes through.
- [`bcos-wiki/SKILL.md`](../bcos-wiki/SKILL.md) — `/wiki search` and `/wiki bundle` are zone-scoped sugar over this skill's backend.

## Related skills

- `bcos-wiki` — wiki zone authoring; provides `/wiki search` (zone-scoped sugar over this backend).
- `context-ingest` — entry point for new content; routing decisions read the same zone registry.
- `context-audit` — CLEAR compliance auditing; reads the same canonical model.
- `clear-planner` — implementation planning; profile-driven bundles (P5) help the planner ground decisions.

## Reference

- `search.md` — invoke `context_search.py`; flag handling; output formatting.
- `bundle.md` — invoke `context_bundle.py`; profile resolution; conflict surfacing; opt-in LLM escalation gating.
