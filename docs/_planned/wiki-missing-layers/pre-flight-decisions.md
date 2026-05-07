---
name: "Wiki Missing Layers — Pre-Flight Decisions"
type: reference
cluster: "Framework Evolution"
version: 1.1.0
status: approved
created: 2026-05-04
last-updated: 2026-05-04
---

# Pre-Flight Decisions

10 design decisions the planner defaulted before producing the implementation plan. Approved at Gate 2 (2026-05-04 16:05 UTC). The pre-implementation cleanup pass (2026-05-04 18:25 UTC) tightened **D-10** to remove an auto-trigger LLM path that had crept into P1's task description — see the D-10 entry below.

---

## D-01 — Search command naming

**Question:** `/wiki search` (zone-scoped) vs `/context search` (cross-zone) vs both?

**Default:** **Both, sharing one backend.**

- `/context search <query>` — umbrella, returns hits typed by zone (default for most agents).
- `/wiki search <query>` — zone-scoped sugar over the same backend (power-user value, narrower hit set, lower latency).

**Reasoning:** No code cost — shared `wiki_search.py` (or `context_search.py`) with a `--zone` filter. Two surfaces, one engine.

---

## D-02 — Collections: real zone vs saved-query view

**Question:** Does `_collections/` get its own backend in the search/bundle surface, or is it a saved-query that runs against other zones?

**Default:** **Real zone.**

**Reasoning:** Already spec'd that way in `collections-zone.md` with the `_manifest.md` pattern. Saved-query would conflate evidence with explanation.

---

## D-03 — HubSpot / live MCP precedence

**Question:** When HubSpot (or any live MCP) and a static doc disagree on the same fact, who wins?

**Default:** **Per-profile, not global.**

- `engagement:plan`, `customer:onboard` profiles: **live > static** (current contact role, current pipeline stage).
- `decision:log`, `incident:postmortem` profiles: **frozen-at-time-of-decision > live** (the decision was made on what was true then).
- `architecture:design` profile: **explicit data points > live MCP** (canonical truth wins for design decisions).

**Reasoning:** Source-of-truth ranking is a property of the task, not a global rule. The profile catalog encodes this.

---

## D-04 — Task profile location: framework vs per-repo

**Question:** Where does the task-profile catalog live?

**Default:** **Framework template + per-repo override.**

- Framework template: `docs/_bcos-framework/templates/_context.task-profiles.yml.tmpl`
- Per-repo override: `docs/.context.task-profiles.yml` (created on demand)

**Reasoning:** Mirrors `_wiki.schema.yml.tmpl` pattern. Ships defaults; allows per-repo evolution.

---

## D-05 — Profile granularity: concrete slugs vs patterns

**Question:** Does a task profile name CONCRETE content (specific slugs / paths) or PATTERNS (zone + cluster + page-type + tag-match)?

**Default:** **Patterns.**

**Reasoning:** Concrete slugs would rot the moment a doc renames or moves. Patterns leverage the typed-edge graph (`cluster:`, `page-type:`, `domain:`, `references:`). The bundle resolver walks the graph at runtime; profiles describe the *shape* of context needed, not the *instances*.

---

## D-06 — `_planned/` as a retrievable zone

**Question:** Is `_planned/` queryable by `/context search` and addressable by task profiles?

**Default:** **Yes.**

**Reasoning:** Plans declare intent. Profiles like `engagement:plan` and `architecture:design` should pull active plans. Freshness via `status: draft|active|approved|archived` + `last-updated`. `_archive/` is a separate zone (historical, read-only).

---

## D-07 — Missing-zone handling

**Question:** When a profile requires a zone that doesn't exist in the current repo (e.g., `_wiki/` not initialized), what happens?

**Default:** **Graceful absence.**

Profiles declare zones as `required: true|false`. Missing required zones surface as `unsatisfied-zone-requirements: [...]` in the bundle output — the agent decides whether to proceed, ask the user, or trigger initialization. Not a hard failure.

**Reasoning:** Repos are populated in stages. The plan must not break when a zone isn't ready yet.

---

## D-08 — `.claude/skills/` retrievability

**Question:** Are skill SKILL.md bodies + `references/` exposed via `/context search`?

**Default:** **Yes, but de-prioritized by default.**

- General `/context search` includes them, ranked below docs/wiki/plans (skills are usually found via Claude Code's native skill-discovery).
- `skill:author` task profile pulls SKILL.md bodies as authoritative reference (high rank).

**Reasoning:** Skills are context for the meta-task of building/modifying skills. Not noise for everyday queries.

---

## D-09 — Plan file location

**Question:** Where do these planning artifacts live?

**Default:** **`docs/_planned/wiki-missing-layers/`** with three files (`README.md`, `implementation-plan.md`, `plan-manifest.json`) plus this `pre-flight-decisions.md`.

**Reasoning:** Mirrors `wiki-zone-integration/` precedent exactly. Runtime planner state at `.claude/quality/sessions/20260504_154239_wiki-missing-layers/` is gitignored as designed.

---

## D-10 — Mechanical-first principle (NEW — added mid-planning)

**Question:** What's the mechanical/LLM split for each new component?

**Default:** **Mechanical-first; LLM-on-escalation only.**

| Layer | Default substrate | LLM escalation |
|---|---|---|
| `/context search` keyword query | Mechanical: BM25 over `context-index.json` (frontmatter index already shipped 2026-05-04) | **Only when user explicitly passes `--semantic`** (no auto-trigger; updated in cleanup pass) |
| `/context search` ranking | Mechanical: BM25-style frequency + recency + zone-priority | LLM only as Phase 5 (embeddings) when keyword precision wall hit |
| `/context bundle` profile resolution | Mechanical: declarative YAML rules → graph walk → freshness check | None by default |
| Source-of-truth conflict resolution | Mechanical: precedence rules in profile + deterministic ordering by `provenance.kind` + `last-updated` | LLM only when mechanical rules don't decide it (logged as `conflict-unresolved`) |
| Coverage assertions | Mechanical: "does the bundle have ≥1 entry per declared family? does each entry pass freshness threshold?" | LLM optional verification: "is this perspective adequately represented in the body" |
| Conflict detection | Mechanical: structured-field disagreement (pricing, role, status) | LLM second-pass: prose-claim disagreement |
| Relation traversal | Pure mechanical: graph walk over typed edges, depth cap | Never |
| HEAD/ETag/Last-Modified (P3) | Pure mechanical: HTTP HEAD + hash compare | Never |
| Schema migration recipes (P3) | Pure mechanical: parametric Python recipes | Never |
| YAML parsing (P3) | Pure mechanical: consolidated `_wiki_yaml.py` parser | Never |
| Sub-agent fetch (P2) | Mechanical: HTTP/PDF/.docx extraction | LLM ONLY for body summarization on return (the value the sub-agent provides) |

**Reasoning:** The current bcos-dev wiki capability is already strongly mechanical (PostToolUse hook is Python, `refresh_wiki_index.py` is byte-deterministic, `wiki_schema.py` is a CLI tool, tests pass deterministically). The same discipline now lives in `context_index.py` / `context-index.json` (shipped 2026-05-04, commit `871ff4d`): stdlib-only, deterministic, ms-latency, byte-stable JSON output. That's a strength — fast, cheap, debuggable, reproducible. The new layers must preserve and extend it. **LLM is an opt-in escalation via explicit flags only. No auto-trigger paths anywhere** (the cleanup pass corrected a P1 task that proposed auto-triggering LLM reformulation on 0-hit unstructured queries).

**Each phase below explicitly calls out:**
- **Mechanical components** — pure Python / YAML / file-system traversal, runnable in milliseconds, deterministic
- **LLM components** — what genuinely needs an LLM call, why mechanical falls short, expected token / latency cost
- **Escalation rules** — when does the system go from mechanical to LLM (e.g., "fall back to LLM only when keyword search returns zero hits AND the query has no recognizable structured terms")

---

## Decision summary

| ID | Decision | Default |
|---|---|---|
| D-01 | Search command naming | `/wiki search` + `/context search`, shared backend |
| D-02 | Collections as zone | Real zone |
| D-03 | Live MCP precedence | Per-profile, not global |
| D-04 | Task-profile location | Framework template + per-repo override |
| D-05 | Profile granularity | Patterns, not concrete slugs |
| D-06 | `_planned/` retrievability | Yes, addressable as zone |
| D-07 | Missing-zone handling | Graceful absence + `unsatisfied-zone-requirements` |
| D-08 | `.claude/skills/` retrievability | Yes, de-prioritized by default |
| D-09 | Plan file location | `docs/_planned/wiki-missing-layers/` |
| **D-10** | **Mechanical/LLM split** | **Mechanical-first; LLM-on-escalation only** |

**Approved at Gate 2 (2026-05-04 16:05 UTC).** Re-approved with cleanup-pass conditions (2026-05-04 18:25 UTC) — D-10 wording tightened to "explicit flag is the ONLY escalation path; no auto-trigger." See [plan-manifest.json](plan-manifest.json) `userApproval.conditions`.
