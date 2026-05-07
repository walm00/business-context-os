---
name: "Wiki Missing Layers — Implementation Plan & PRD"
type: playbook
cluster: "Framework Evolution"
version: 1.2.0
status: completed
created: 2026-05-04
last-updated: 2026-05-04
session-id: 20260504_154239_wiki-missing-layers
authority-docs:
  - docs/_bcos-framework/architecture/wiki-zone.md
  - docs/_bcos-framework/architecture/collections-zone.md
  - docs/_bcos-framework/architecture/system-design.md
  - docs/_planned/wiki-missing-layers/pre-flight-decisions.md
---

> **Status: approved (post-cleanup) 2026-05-04 18:25 UTC.** All 10 pre-flight decisions defaulted (D-01 → D-10; see `pre-flight-decisions.md`). Gate 2 approval at 16:05 UTC; pre-implementation audit at 18:10 UTC flagged six blockers (status drift, schema-violating IDs, D-10 contradiction, missing acknowledgement of `context_index.py`, weak TDD ordering, sparse per-task verification); cleanup pass at 18:25 UTC re-approved with conditions. See [plan-manifest.json](plan-manifest.json) `planStatusHistory` and `userApproval.conditions`.

# Wiki Missing Layers — Implementation Plan & PRD

> **Note:** The runtime planner state (planning-manifest.json + working artifacts) lives at `.claude/quality/sessions/20260504_154239_wiki-missing-layers/` and is gitignored. This is the durable, reviewable copy of the plan + PRD.

| Field | Value |
|---|---|
| **Session ID** | `20260504_154239_wiki-missing-layers` |
| **Branch** | `dev-guntis` (working tree); cleanup pass on `dev-guntis` directly |
| **Scenario** | AGENTING (primary) + DOCUMENTATION (secondary) |
| **Status** | `approved` (cleanup pass 2026-05-04 18:25 UTC) |
| **Total phases** | 7 (P1–P7) |
| **Total tasks** | 58 (all schema-compliant; all carry verification) |
| **Skills affected** | `bcos-wiki` (extended), `context-routing` (NEW) |
| **Agents affected** | `wiki-fetch` (NEW) |
| **Authority docs** | `wiki-zone.md`, `collections-zone.md`, `system-design.md` |
| **Trigger** | `/context search`, `/context bundle`, `/wiki search`, `/wiki bundle` (NEW commands) |

---

## 0. Foundation (already shipped)

The cleanup pass surfaced that `context_index.py` and `.claude/quality/context-index.json` were committed on the same day this plan was drafted (commit `871ff4d`, 2026-05-04 17:52 UTC). The plan now treats them as foundation:

| Asset | Role |
|---|---|
| [`.claude/scripts/context_index.py`](../../../.claude/scripts/context_index.py) | Canonical context model. Walks `docs/` once, parses frontmatter, derives folder/path facets (`zone`, `bucket`, `folder`, `path-tags`, `trust-level`, `is-canonical`), computes freshness (`age_days`, `reviewed_age_days`), builds typed-edge graph (`builds-on`, `depends-on`, `references`, `provides`, `consumed-by`). Stdlib-only, deterministic, ms-latency. |
| [`.claude/quality/context-index.json`](../../../.claude/quality/context-index.json) | Already-built corpus (52 docs in this repo). Source of truth for retrieval/routing — P2 search reads from it; P5 bundle resolver walks its edges. |
| [`.claude/scripts/build_document_index.py`](../../../.claude/scripts/build_document_index.py) | Consumer pattern. P2 follows the same shape. |
| [`.claude/agents/explore/AGENT.md`](../../../.claude/agents/explore/AGENT.md) | Sub-agent prior art. P3 `wiki-fetch` borrows shape. |

**Implication for the plan:**
- P1's `_context-zones.yml.tmpl` is a **declarative companion** to `context_index.py` (not a parallel zone model). A drift test enforces agreement.
- P2's `context_search.py` reads `.claude/quality/context-index.json` as its corpus (no re-walk).
- D-10 (mechanical-first) is already proven by `context_index.py` in production: stdlib-only, deterministic, byte-stable JSON output. The new layers preserve this discipline.

---

## 1. Problem Statement

The wiki-zone integration shipped (`e887eaa`) and the canonical context model shipped (`871ff4d`). Data is shaped right, the corpus is indexed, but several load-bearing layers are still missing:

**Gap 1 — No retrieval surface.** No `/wiki search`, no `/context search`, no top-K cap, no token budget on reads. An agent today greps, reads `index.md`, or wikilink-walks. The whole `wiki-zone.md:615-660` RAG-readiness section is "data is shaped right, layer comes later." Today the corpus is built but unread.

**Gap 2 — No sub-agent isolation in any wiki path.** `run.md` Pass 1 fetches URLs into the main thread; one 200k fetch per URL with a per-fetch (not cumulative) guard. A queue with 5 deep URLs saturates main context before the first ingest finishes. Same shape in `wiki-source-refresh` full-tier and PDF/.docx extraction in promote/create. Canonical sub-agent shape (work-in >> result-out) is unused throughout.

**Gap 3 — Phantom claims and stubs:**
- Quick-check tier in `wiki-zone.md` says "HEAD-only or equivalent" — no actual HEAD/ETag/Last-Modified code anywhere.
- Schema migration: `wiki_schema.py:470-479` returns "no executable migration recipe registered." Empty box, load-bearing the moment schema-version bumps. **Verified failing during audit:** `python .claude/scripts/wiki_schema.py migrate 1.0 1.1` → "No executable migration recipe."
- Lint ID `duplication-vs-data-point` registered + described in `lint.md` Step K with Jaccard threshold; no implementation. Phantom check.

**Gap 4 — Three hand-rolled YAML parsers** in `post_edit_frontmatter_check.py`, `refresh_wiki_index.py`, `wiki_schema.py`. Different YAML subsets handled differently. Multi-line scalars or anchors will silently parse three different ways. Defensible to skip PyYAML; cost is parser drift.

**Gap 5 (architectural — most important) — No task-driven cross-zone routing.**

The wiki answers "what do we know about X?" (when retrieval ships). It does NOT answer "I'm about to do task T — what context bundle do I need, with what freshness, with what source-of-truth ranking, and what perspectives am I missing?"

The materials exist (typed edges, provenance, page-types, clusters in `context-index.json`) but there's no **task profile** layer.

**Goal:** ship the missing layers — read foundation, sub-agent isolation, stub repair, task-driven cross-zone routing — in a form that:

1. Operates across all zones (wiki + plans + context docs + collections + lessons + skills + registries + sessions)
2. Remains **mechanical-first** (Python + YAML + file-system traversal); LLM is opt-in escalation only via explicit flags. **No auto-trigger paths.**
3. Handles graceful absence (zones not yet initialized in a fresh repo)
4. Preserves the determinism of `context_index.py` and the existing wiki capability (byte-stable indexes, idempotent regeneration, deterministic tests)

**Non-goals (v1):**
- Vector store / graph database (P6 only when mechanical search hits a precision wall)
- Cross-tool adapter (`AGENTS.md`-style universal manual)
- Atlas / galaxy node-type extension
- Decision log / engagement / customer zones (out of scope here; tracked as follow-ups)

---

## 2. User Stories

| As a... | I want to... | So that... |
|---|---|---|
| BCOS user | run `/context search "competitor pricing"` | I get hits from wiki + plans + context docs + collections in one ranked list |
| BCOS user | run `/wiki search "stripe billing"` | I get a wiki-only result set (faster, narrower) |
| BCOS user | run `/context bundle market-report:write` | I get a structured bundle: by-zone hits, freshness, source-of-truth conflicts, missing perspectives |
| BCOS user | drop a 100k-token PDF into `/wiki create from /path/spec.pdf` | extraction happens in a sub-agent; main context only sees the structured summary |
| BCOS user | run `/wiki run` on a queue of 5 deep URLs | each URL fetches in its own sub-agent; main context never holds all 5 raw bodies |
| BCOS user | run `python .claude/scripts/wiki_schema.py migrate --from 1.0 --to 1.1` | a real migration runs (not a stub) |
| BCOS user | edit a wiki page with multi-line YAML scalars | all three downstream parsers handle it identically (no drift) |
| Agent doing `architecture:design` | request `/context bundle architecture:design` | I get system-design + relevant ADR + relevant wiki source-summary + plans, ranked by source-of-truth, freshness-flagged |
| Agent doing `engagement:plan` | request `/context bundle engagement:plan` | live HubSpot data wins where applicable; static engagement page fallback; wiki source-summary supports |
| Agent doing `decision:log` | request `/context bundle decision:log` | frozen-at-time data wins (the decision was made on what was true then) |
| Maintenance dispatcher | continue running daily/weekly/quarterly jobs | unchanged; the missing-layers work doesn't disrupt scheduled maintenance |

---

## 3. Discovery Results

| Discovery | Result |
|---|---|
| Existing agents | 1 — `explore` (basis for `wiki-fetch` shape; `wiki-fetch` is new because output contract differs) |
| Existing skills | 14 — see `plan-manifest.json` `discoveryResults.skillsFound`; `bcos-wiki` is the only one extended; `context-routing` is new |
| Canonical scripts | `context_index.py`, `build_document_index.py`, `refresh_wiki_index.py`, `wiki_schema.py`, `validate_frontmatter.py`, `validate_references.py`, `test_wiki_capability.py` (16 tests green), `test_context_index.py` (4 tests green), `analyze_integration.py`, `refresh_ecosystem_state.py` |
| Canonical artifacts | `.claude/quality/context-index.json` (52 docs, frontmatter+edges+ownership+freshness+warnings), `.claude/quality/ecosystem/state.json` (14 skills, 1 agent), `.claude/quality/ecosystem/lessons.json` (16 lessons), `.claude/quality/schedule-config.template.json` |
| Lessons applicable | L-014 (plan manifest as regression artifact), L-015 (dispatcher routing pattern), L-016 (framework-doc executable testability) — all relevant |
| Skill overlaps | None — `/context search` and `/context bundle` are genuinely new capabilities. `/wiki search` and `/wiki bundle` are sugar over the same backend. |
| Wiki sub-skill files | 12 (archive, create, ingest, init, lint, promote, queue, refresh, remove, review, run, schema) — `search.md` and `bundle.md` are new |
| New scripts in this plan | `_wiki_yaml.py`, `_wiki_http.py`, `_wiki_lint.py` (or removed), `context_search.py`, `context_bundle.py`, `load_zone_registry.py`, `load_task_profiles.py`, `validate_task_profiles.py`, `test_zone_registry.py`, `test_context_search.py`, `test_context_capability.py`, optionally `generate_embeddings.py` + `test_embedding_search.py` (P6 conditional) |
| Reuse candidates | `context_index.py` (canonical model — P1 wraps, P2 reads), `context-index.json` (search corpus — P2 reads directly, P5 walks edges), `explore` (sub-agent prior art), `ecosystem-manager` + `doc-lint` (FIXED END), `AskUserQuestion` (P4_009 lint decision; P5_009 conflict UX), `wiki-zone-integration` plan precedent |
| Repo state | Fresh framework-development. Most zones spec'd but not initialized. Plan must work for empty + populated. |

---

## 4. Proposed Solution

A 7-phase delivery (P1–P7), with TDD ordering inside each implementation phase: fixture creation → failing regression test → implementation tasks → red→green driver → documentation deltas. **Every task carries a `verification` block in the manifest.**

```
P1 — Zone Registry (foundational; declarative companion to context_index.py)
  |
  +--> P2 — Cross-zone search (mechanical BM25 over context-index.json; LLM only via --semantic flag)
  |
  +--> P3 — Sub-agent isolation (work-in >> result-out)
  |
  +--> P4 — Wiki stub repair (HEAD/ETag, migration, Jaccard, YAML consolidation)
  |
  P5 — Task-driven cross-zone routing  (depends on P1 + P2)
  |
  P6 — Embeddings  (CONDITIONAL on P2 outcomes)
  |
  P7 — FIXED END (doc-lint + integration audit + ecosystem state + learnings)
```

**Sequencing:** P1 first (foundation). P2 + P3 + P4 in parallel after P1 (independent surfaces). P5 requires P1 + P2. P6 conditional on P2. P7 mandatory gate at end.

**Why this order:**

1. **P1 first** — every downstream layer queries the zone registry; without it, search/bundle have to hardcode zone knowledge. P1 also locks in the declarative-companion contract with `context_index.py`.
2. **P2 + P3 + P4 parallel** — independent. P2 ships read foundation, P3 ships isolation pattern, P4 cleans up wiki internals. None depend on each other.
3. **P5 last (before optional P6)** — the architectural layer. Needs P1's zone registry to know what to traverse, and P2's search backend to fetch hits.
4. **P6 conditional** — only ship embeddings if mechanical search demonstrably fails in real use. Don't pre-build.
5. **P7 mandatory** — non-negotiable per AGENTING template.

**TDD ordering inside each phase:** every implementation phase opens with `P{N}_001` (fixture creation) and `P{N}_002` (failing regression test) BEFORE any implementation tasks. The phase closes with a red→green driver task before documentation deltas. This makes every phase self-verifying and preserves the determinism `context_index.py` already established.

---

## 5. Phase Detail

### P1 — Zone Registry (Foundational)

**Goal:** A declarative companion to `context_index.py` for "what zones exist, how to address them, what's their freshness model, what's their source-of-truth role." Everything downstream reads this YAML; a drift test enforces agreement with the Python model.

**Tasks (8):** P1_001 (fixtures) → P1_002 (failing test) → P1_003 (`context-zones.md`) → P1_004 (`_context-zones.yml.tmpl`) → P1_005 (`load_zone_registry.py`) → P1_006 (drift test green) → P1_007 (`system-design.md`) → P1_008 (`wiki-zone.md` cross-link).

**Mechanical components:** YAML schema, markdown documentation, drift test — all deterministic, runs in <1 second.

**LLM components:** None.

**Acceptance:**
- `python .claude/scripts/test_zone_registry.py` passes — every zone `context_index.py._zone_for()` returns appears in the YAML, and vice versa.
- `_context-zones.yml.tmpl` is loadable as YAML and conforms to its declared schema.
- `system-design.md` and `wiki-zone.md` cross-link to `context-zones.md`.
- Re-running tests produces byte-identical output.

**Why this can ship independently:** Pure foundation. After P1, downstream phases have a registry to read; without it, P2 hardcodes zone knowledge.

**Risks:**
- Bikeshedding zone definitions. Mitigation: seed from `context_index.py._zone_for()` outputs (the model is the spec).
- Drift between markdown, YAML, and Python. Mitigation: drift test is the contract.

**Documentation deltas:** `context-zones.md` (NEW), `system-design.md` (revised), `wiki-zone.md` (revised — link to `context-zones.md`).

---

### P2 — Cross-Zone Read Foundation

**Goal:** `/context search <query>` returns zone-typed hits with shared output schema. Reads `.claude/quality/context-index.json` as corpus (no re-walk). Wiki-scoped sugar `/wiki search` shares the same backend.

**Tasks (9):** P2_001 (fixtures) → P2_002 (failing test) → P2_003 (`context_search.py` mechanical) → P2_004 (citation-id) → P2_005 (`context-routing/SKILL.md`) → P2_006 (`--semantic` opt-in) → P2_007 (`/wiki search` sugar) → P2_008 (red→green) → P2_009 (docs delta).

**Mechanical components:** `context_search.py` reads `context-index.json`. BM25-style ranking (term frequency × inverse document frequency × recency boost × zone-priority from `_context-zones.yml`). Top-K + token-budget. `--zone` filter. Citation-id generator (slug-stable). Runs in <500ms on the 52-doc corpus; deterministic.

**LLM components:**
- **`--semantic` flag** (D-10 strict opt-in): user explicitly passes `--semantic`; LLM reformulates query into 3 candidates; each runs mechanically; results merge. **NO auto-trigger.** Hard caps: 2000 tokens / 5s latency / 1 LLM call per invocation.

**Escalation rules (D-10 strict):**
1. **Default: mechanical-only.** No LLM call regardless of result count.
2. **`--semantic` flag set:** the ONLY trigger for LLM reformulation.
3. **0-hit result:** returned as-is. The agent can choose to retry with `--semantic` if appropriate.
4. **Hard latency budget:** 5 seconds for the LLM call. On timeout, return mechanical 0-hit with `escalation: timeout`.

> **Why no auto-trigger:** D-10 is mechanical-first / LLM-on-explicit-opt-in. Auto-triggers re-introduce hidden LLM cost paths and break the "what you ask for is what you get" contract. The audit verdict surfaced this as a contradiction; the cleanup pass made `--semantic` the sole path.

**Acceptance:**
- `/context search "linkedin tone"` returns ranked hits across zones with shared schema.
- `/wiki search "linkedin tone"` returns the same hits filtered to `zone: wiki`.
- Empty repo (no top-level data points, no `_wiki/`) returns empty hit list with `zones-skipped-not-present: [...]`. No crash.
- Citation IDs stable: re-running search after a whitespace-only edit returns the same `citation-id`.
- LLM escalation triggers ONLY on `--semantic` flag (no auto-trigger; verified by test).
- Token budget: aggregate hit body content ≤ 8000 tokens; if exceeded, top hits truncated with `truncated: true`.
- Latency: <500ms mechanical, <5s with `--semantic`.

**Why this can ship independently:** Reads `context-index.json` directly. No dependency on P3, P4, P5.

**Risks:**
- BM25 tuning. Mitigation: defaults from zone registry's `zone-priority`; tunable per-repo.
- Empty-zone handling. Mitigation: per-zone backend returns `[]` gracefully; zone registry's `optional: true` controls absence logging.
- LLM escalation cost. Mitigation: D-10 strict; flag is opt-in only; hard caps.

**Documentation deltas:** `wiki-zone.md` (RAG-readiness section rewritten), `context-zones.md` (search entry-point), `bcos-wiki/SKILL.md` (dispatch + `/wiki search`), new `context-routing/SKILL.md` + `search.md`.

---

### P3 — Sub-Agent Isolation for Big-Body Work

**Goal:** Big-body fetches (URL ingest, PDF/.docx extraction, full-tier source refresh) happen in sub-agents. Raw bodies stay there; only structured summaries return. Main context never holds 200k+ tokens of HTML.

**Tasks (9):** P3_001 (fixtures) → P3_002 (failing test) → P3_003 (`wiki-fetch/AGENT.md`) → P3_004 (wire `run.md`) → P3_005 (wire `refresh.md`) → P3_006 (wire `promote.md`/`create.md`) → P3_007 (cumulative budget guard) → P3_008 (red→green) → P3_009 (docs delta).

**Mechanical components:** Agent definition (`AGENT.md`), wiring across `run.md`/`refresh.md`/`promote.md`/`create.md`, cumulative token budget math, contract tests.

**LLM components:**
- **Inside `wiki-fetch` sub-agent only.** That's what isolation means: the sub-agent IS the LLM call. Each invocation: ~5–50k input tokens (raw body), ~2–4k output tokens (structured summary).
- Main thread holds NO LLM calls for fetching during P3.

**Escalation rules:**
- Always use sub-agent for: URL fetches, PDF/.docx extraction, refresh full-tier.
- Never inline-fetch in main.
- If sub-agent fails, return error structure to main; main decides retry/skip/ask.
- Cumulative budget > 80% main-context limit → serialize remaining sub-agents.

**Acceptance:**
- `/wiki run` on 5-URL queue dispatches 5 sub-agents (verifiable in tool-call log), each ≤4000-token result.
- Main context never holds full HTML body of any fetched URL.
- `/wiki create from /tmp/spec.pdf` dispatches sub-agent; binary lands at `_wiki/raw/local/`.
- Cumulative-guard fires on synthetic 10-URL batch where each result projects 10k tokens.
- Contract test verifies sub-agent output schema.

**Why this can ship independently:** No dependency on P2, P4, P5. Pure refactor of existing fetch paths.

**Risks:**
- Contract drift. Mitigation: contract test rejects malformed outputs.
- Sub-agent latency. Mitigation: parallel dispatch where cumulative budget allows.
- Re-architecture risk. Mitigation: keep old code paths behind feature flag during P3; flip after smoke test.

**Documentation deltas:** `wiki-zone.md` (Operational Discipline), `bcos-wiki/SKILL.md`, `run.md`, `refresh.md`, `promote.md`, `create.md`.

---

### P4 — Wiki Stub Repair

**Goal:** Eliminate phantom claims and parser drift in the wiki capability. Make the wiki internally honest (what's documented = what's implemented).

**Tasks (9):** P4_001 (fixtures) → P4_002 (failing tests) → P4_003 (`_wiki_yaml.py` consolidation) → P4_004 (`_wiki_http.py` HEAD/ETag) → P4_005 (source-summary frontmatter additions) → P4_006 (migration recipe 1.0↔1.1) → P4_007 (Jaccard lint OR removal via AskUserQuestion) → P4_008 (red→green) → P4_009 (docs delta).

**Mechanical components:** All of P4. HTTP HEAD + hash compare, Jaccard math, YAML parser, schema migration recipes, tests. Deterministic; runs in <2s for full test suite.

**LLM components:** None.

**Acceptance:**
- `python .claude/scripts/wiki_schema.py migrate --from 1.0 --to 1.1` runs a real migration on test fixture; output reversible (`--from 1.1 --to 1.0` reverts).
- `wiki-source-refresh` quick-check tier emits HEAD-check results: `{url, etag-changed, last-modified-changed, content-hash-changed, decision}`.
- `_wiki/.config.yml` enables quick-check tier explicitly (default `enabled: true` after P4).
- `duplication-vs-data-point` lint either flags real duplication on test fixture (Jaccard impl) OR is removed cleanly from registry + docs (no phantom).
- All three call-sites use `_wiki_yaml.py`; old hand-rolled parsing deleted.
- Tests pass: HEAD round-trip, migration round-trip, lint detection (or removal verification), parser equivalence.

**Why this can ship independently:** Pure cleanup. No dependency on P2, P3, P5.

**Risks:**
- Jaccard implementation effort. Mitigation: removal is clean fallback; user approves either path via AskUserQuestion.
- YAML parser consolidation breaks existing pages. Mitigation: parser-equivalence test on fixtures.
- Migration recipe complexity. Mitigation: 1.0↔1.1 is the trivial case (add fields); recipe is the *pattern*.

**Documentation deltas:** `wiki-zone.md`, `lint.md`, `migration-helpers.md`, `_wiki.schema.yml.tmpl`.

---

### P5 — Task-Driven Cross-Zone Routing (the Architectural One)

**Goal:** An agent doing task T calls `/context bundle <profile>` and gets a curated, structured bundle from across zones with freshness verdicts, source-of-truth ranking, conflict detection, missing-perspective callouts, and traversal hops — all mechanical by default.

**Depends on:** P1 (zone registry) + P2 (search backend).

**Tasks (12):** P5_001 (fixtures) → P5_002 (failing test) → P5_003 (profile schema) → P5_004 (built-in catalog × 9) → P5_005 (override loader) → P5_006 (validator) → P5_007 (`context_bundle.py` resolver) → P5_008 (output formatter) → P5_009 (opt-in escalation flags) → P5_010 (skill surface) → P5_011 (red→green) → P5_012 (docs delta).

**Mechanical components:**
- Profile schema (YAML) + 9 built-in profiles (`market-report:write`, `engagement:plan`, `architecture:design`, `competitor:audit`, `customer:onboard`, `decision:log`, `incident:postmortem`, `skill:author`, `plan:revise`)
- Profile validator
- Bundle resolver: search → rank → traverse (graph walk over `context-index.json` edges) → freshness → conflict-detect → coverage-check
- Output formatter
- Skill wiring + tests

All deterministic. <1s for typical bundle on 200-page corpus.

**LLM components (D-10 strict opt-in only):**
- **`--resolve-conflicts`:** when mechanical source-of-truth ranking can't decide between two equally-ranked sources, LLM resolves. Sub-agent shape (per P3). Hard cap: 5 LLM calls per bundle, ~8k input each, ~500 output.
- **`--verify-coverage`:** when coverage assertion is "perspective adequately represented in body," LLM verifies. Hard cap: 1 call per bundle, ~6k input, ~500 output.

**Both flags are OFF by default. Both are explicit opt-in. Neither auto-fires.**

**Escalation rules (D-10 strict):**
1. Default: mechanical-only. Bundle returns conflicts as `unresolved` with reason; agent decides what to do.
2. `--resolve-conflicts`: LLM resolves only `unresolved` conflicts (not all candidates). Hard cap 5 calls.
3. `--verify-coverage`: LLM verifies prose-perspective coverage. Hard cap 1 call.
4. Both flags can combine; total LLM cost capped at 6 calls / ~50k tokens / ~30s latency per bundle.

**Acceptance:**
- `/context bundle market-report:write` returns structured bundle on fixture corpus, deterministic across runs (modulo `generated-at`).
- Each declared content-family produces hits OR shows up in `missing-perspectives`.
- `/wiki bundle market-report:write` returns same bundle filtered to wiki-zone hits.
- Fixture with two disagreeing source-of-truth candidates produces `source-of-truth-conflicts: [...resolution: unresolved...]` by default.
- With `--resolve-conflicts`, LLM resolves; hard cap respected.
- Empty repo returns bundle with `unsatisfied-zone-requirements: [...]` and empty `by-zone`. No crash.
- Profile validator passes for every built-in profile; wired into P7.
- All tests pass.

**Why this is the architectural one:** Without P5, retrieval is keyword-search-and-pray; with P5, an agent declares its task and gets a curated, ranked, freshness-flagged, gap-aware bundle.

**Risks:**
- Profile schema bikeshedding. Mitigation: ship 2 profiles end-to-end first (`market-report:write`, `engagement:plan`); add others after dogfooding.
- Source-of-truth edge cases. Mitigation: profile declares ranking explicitly; unresolved conflicts surface mechanically.
- Empty-repo gracefulness. Mitigation: every backend handles "zone not present"; surfaced as `unsatisfied-zone-requirements`.
- Scope creep into LLM features. Mitigation: D-10 strict; LLM gated behind explicit flags; reviewable at PR time.

**Documentation deltas:** `context-routing.md` (NEW or merged), `wiki-zone.md` (cross-link), `system-design.md` (add bundle layer), `bcos-wiki/SKILL.md`, `context-routing/SKILL.md`.

---

### P6 — Embeddings (Conditional)

**Goal:** If P2 mechanical search hits a precision wall in real use, ship embeddings as plug-in substrate behind the same API.

**Trigger condition:** Logged real-use cases where mechanical search returns wrong-relevant or zero hits despite content existing AND user reports it as a precision failure (not query failure). Capture in `lessons.json` over first 1–2 months post-P2.

**Tasks (6):** P6_001 (fixtures + eval set) → P6_002 (failing test) → P6_003 (embedding pipeline) → P6_004 (`--embedding` mode) → P6_005 (re-embed triggers) → P6_006 (red→green + docs).

**Mechanical components:** Pipeline plumbing, storage, search index lookup, scheduling integration.

**LLM components:** Embedding generation, re-embed triggers. Cost depends on model + corpus size; budget per-repo.

**Escalation rules:** P6 is itself the escalation. Triggered only when P2 mechanical fails in measurable ways.

**Acceptance:**
- `/context search --embedding "<query>"` ships and demonstrably improves precision/recall on fixed eval set vs P2 mechanical.
- Re-embed triggers fire on `builds-on:` propagation.
- Same output schema as P2 — no API change for callers.
- All P2 tests still pass with `--embedding` mode.

**Why conditional:** Don't pre-build. Ship P2, observe real failures, then ship P6 if needed. D-10 puts the burden of proof on the LLM substrate.

**Risks:**
- Cost on large corpora. Mitigation: local-model option; per-repo budget.
- Stale embeddings. Mitigation: `wiki-stale-propagation` extension.
- Plug-in interface drift. Mitigation: P6 must not change `context_search.py` output schema.

**Documentation deltas:** `wiki-zone.md` (RAG section: "embeddings shipped"), `context-routing.md`.

---

### P7 — FIXED END (Mandatory per AGENTING Template)

**Tasks (5):** P7_001 (doc-lint JSON) → P7_002 (doc-lint markdown) → P7_003 (integration audit) → P7_004 (ecosystem state refresh) → P7_005 (learnings capture).

| Task | Capability | Mandatory? |
|---|---|---|
| `P7_001` | doc-lint — JSON structure validation (profile YAMLs, schema YAMLs, plan-manifest.json) | Yes |
| `P7_002` | doc-lint — Markdown quality check on revised docs (wiki-zone, context-zones, context-routing, system-design) | Yes |
| `P7_003` | ecosystem-manager — Integration audit: `python .claude/scripts/analyze_integration.py --ci` + AI review of cross-references between new SKILL.md, AGENT.md, scripts, hooks, settings | **Yes — non-negotiable** |
| `P7_004` | ecosystem-manager — Run `python .claude/scripts/refresh_ecosystem_state.py` to regenerate `state.json` reflecting `context-routing` skill + `wiki-fetch` agent | **Yes — non-negotiable** |
| `P7_005` | ecosystem-manager — Capture learnings (mechanical-first design choice, sub-agent contract pattern, profile-schema vocabulary, TDD ordering pattern, plan-manifest schema-compliance discipline) | **Yes — non-negotiable** |

---

## 6. Risks & Mitigations (Cross-Phase)

| Risk | Severity | Phase | Mitigation |
|---|---|---|---|
| Empty-repo problem (most zones not yet initialized) | High | All | Every backend handles "zone not present"; surfaced as `unsatisfied-zone-requirements`; `optional: true` flag in zone registry |
| Mechanical-first principle erodes as features accrete | High | P5, P6 | D-10 strict (no auto-trigger); each new feature must declare its mechanical/LLM split; reviewable at PR time |
| LLM escalation cost runaway | Medium | P2, P5 | Hard caps: token budget, latency budget, max calls per bundle; flags are opt-in only |
| Profile schema bikeshedding | Medium | P5 | Ship 2 profiles end-to-end first; iterate from real use |
| YAML parser consolidation breaks existing pages | Medium | P4 | Parser-equivalence test on fixtures; feature flag for one cycle |
| Sub-agent contract drift | Medium | P3 | Contract test on result schema; reject malformed |
| BM25 ranking tuning | Low | P2 | Defaults from zone registry; tunable per-repo; replace with embeddings (P6) if precision wall |
| Cross-zone graph traversal explodes | Low | P5 | Hard depth cap (default 2); per-edge fanout cap |
| Citation-id stability | Low | P2 | Slug-based, not line-based; tested across whitespace edits |
| Backward compat with P4 schema migration | Low | P4 | Migration recipe is reversible (1.0↔1.1); test verifies round-trip |
| Drift between context_index.py and YAML zone registry | Low | P1 | Drift test asserts agreement; FIXED END check |

---

## 7. Acceptance Criteria (Cumulative)

After all 7 phases (assuming P6 is triggered):

1. ✅ `python .claude/scripts/test_zone_registry.py` passes — context-zones registry intact and agrees with `context_index.py`.
2. ✅ `/context search "<query>"` returns ranked cross-zone hits with shared schema; `/wiki search` returns zone-scoped subset.
3. ✅ `/wiki run` on a 5-URL queue dispatches 5 sub-agents; main context never holds full bodies.
4. ✅ HEAD/ETag quick-check tier runs deterministically; `wiki_schema.py migrate 1.0→1.1` runs a real migration; `_wiki_yaml.py` is the single parser.
5. ✅ `duplication-vs-data-point` either flags real duplication (Jaccard) OR is removed cleanly.
6. ✅ `/context bundle market-report:write` returns structured bundle: `{by-zone, by-family, freshness, source-of-truth-conflicts, missing-perspectives, traversal-hops, unsatisfied-zone-requirements}`.
7. ✅ Built-in profile catalog (9 profiles) ships with framework template; per-repo override works.
8. ✅ Bundle resolution is mechanical-only by default; LLM escalation gated behind `--resolve-conflicts` / `--verify-coverage` flags. **No auto-trigger paths anywhere.**
9. ✅ Empty-repo case: bundle returns `unsatisfied-zone-requirements: [...]` without crash.
10. ✅ `/context search --embedding` (P6, conditional) demonstrably improves precision/recall vs mechanical baseline on fixed eval set.
11. ✅ Integration audit passes; ecosystem state reflects `context-routing` skill + `wiki-fetch` agent; doc-lint passes; learnings captured.

---

## 8. Rollback Strategy

| Phase | Rollback |
|---|---|
| P1 (zone registry) | Revert `context-zones.md` + template; downstream code falls back to `context_index.py` directly (worse, but functional) |
| P2 (cross-zone search) | Delete `context_search.py`, `context-routing/SKILL.md`, `bcos-wiki/search.md`; existing wiki pages unaffected |
| P3 (sub-agent isolation) | Revert `wiki-fetch` agent + `run.md`/`refresh.md`/`promote.md`/`create.md` changes; old inline-fetch flow returns |
| P4 (stub repair) | Revert HEAD/ETag impl, schema migration recipe, lint impl, `_wiki_yaml.py`; existing pages remain readable |
| P5 (task routing) | Delete `context_bundle.py`, profile templates, `bundle.md`; P2 search remains functional |
| P6 (embeddings) | Delete embedding pipeline + storage; `--embedding` mode no-ops; mechanical search remains the default |
| P7 | N/A — gating, not destructive |

Each phase independently revertible. P1 (zone registry doc) is a soft dependency downstream — rolling back doesn't break code, just removes documented intent.

---

## 9. Out of Scope (Deliberate)

| Feature | Why deferred | Tracked as |
|---|---|---|
| Decision log / ADR zone | Spec'd as wiki page-type; standalone zone is separate work | `FU_001` |
| Engagement / customer / account zone | Pattern doc exists; zone instantiation per-deployment | `FU_002` |
| HubSpot / live MCP integration in bundle resolver | Profile schema accommodates it (D-03); MCP plumbing is separate | `FU_003` |
| Atlas / galaxy node-type extension | Visualization layer; not foundational | `FU_004` |
| Vector store / graph database | Spec'd as P6; only triggered if mechanical hits precision wall | `FU_005` |
| Cross-tool adapter (`AGENTS.md`-style) | Speculative | `FU_006` |
| `_collections/.schema.yml` governance | Same pattern, separate work | `FU_007` (carry-over from wiki-zone-integration) |
| Wire `context_index.py` output into `generate_wakeup_context.py` | Wake-up context currently no-ops on empty top-level data points; could surface zone/freshness summary | `FU_008` (NEW; surfaced during cleanup pass) |

---

## 10. Artifacts

| File | Path |
|---|---|
| Planning manifest (workflow state) | `.claude/quality/sessions/20260504_154239_wiki-missing-layers/planning-manifest.json` |
| Plan manifest | `docs/_planned/wiki-missing-layers/plan-manifest.json` (canonical) + runtime mirror in session dir |
| This implementation plan | `docs/_planned/wiki-missing-layers/implementation-plan.md` |
| Durable plan README | `docs/_planned/wiki-missing-layers/README.md` |
| Pre-flight decisions | `docs/_planned/wiki-missing-layers/pre-flight-decisions.md` |
| Authority — wiki zone spec | `docs/_bcos-framework/architecture/wiki-zone.md` |
| Authority — collections zone spec | `docs/_bcos-framework/architecture/collections-zone.md` |
| Authority — system design | `docs/_bcos-framework/architecture/system-design.md` |
| **Foundation (already shipped)** — canonical context model | `.claude/scripts/context_index.py` |
| **Foundation (already shipped)** — canonical corpus index | `.claude/quality/context-index.json` |
| **NEW (P1)** — context zones registry | `docs/_bcos-framework/architecture/context-zones.md` |
| **NEW (P1)** — context-zones template | `docs/_bcos-framework/templates/_context-zones.yml.tmpl` |
| **NEW (P5)** — task-profiles template | `docs/_bcos-framework/templates/_context.task-profiles.yml.tmpl` |
| **NEW (P5)** — context routing doc | `docs/_bcos-framework/architecture/context-routing.md` |

---

## 11. Next Actions

| Action | What happens |
|---|---|
| **Begin P1** | Start P1_001 (zone-registry fixtures); follow TDD ordering through P1_006 red→green; ship `context-zones.md` + YAML template + drift test |
| **Modify** | Return to Step 4 (Gather Context) with this plan as additional context; revise per feedback |

---

**End of plan.**
