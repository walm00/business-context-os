# Context Routing Architecture

How CLEAR Context OS turns "I'm about to do task T" into a curated, freshness-flagged, source-of-truth-aware bundle of context. Routing is a derived layer on top of [`context-zones.md`](./context-zones.md) (zones), [`metadata-system.md`](./metadata-system.md) (per-doc metadata), and the typed-edge graph in [`context-index.json`](../../../.claude/quality/context-index.json) (`builds-on`, `references`, `depends-on`, `provides`).

For the user-facing surface see [`context-routing/SKILL.md`](../../../.claude/skills/context-routing/SKILL.md) and [`bundle.md`](../../../.claude/skills/context-routing/bundle.md). For zone-scoped sugar over the same backend see [`bcos-wiki/bundle.md`](../../../.claude/skills/bcos-wiki/bundle.md).

> **Net summary in one line:** a *task profile* names a job-to-be-done (e.g., `market-report:write`) and declares the *shape* of context that job needs — required zones, content families, source-of-truth ranking, freshness thresholds, traversal hints, coverage assertions. The bundle resolver walks the typed-edge graph at runtime, applies the rules deterministically, and returns a structured envelope. Mechanical-first (D-10 strict): LLM is opt-in via `--resolve-conflicts` / `--verify-coverage` flags only.

---

## Why Routing Exists

`/context search "stripe billing"` answers "what do we know about X?" — a great keyword retrieval surface (P2). But agents writing market reports, planning customer engagements, or logging architectural decisions don't have a query string in mind. They have a **task**, and the task implicitly demands:

- *which zones* to pull from (active for canonical truth, planned for proposals, collections for evidence, framework for spec, …),
- *which content families* must be present (competitor data, pricing data, market data),
- *who wins* when canonical and derived disagree,
- *how fresh* each zone must be for this task,
- *how deep* to walk relationships (`builds-on` two hops, `references` one hop),
- *what coverage* counts as "enough" (≥1 hit per family).

A keyword query can't carry that. A *profile* can.

---

## The Profile

A task profile is a declarative document with the following shape (per the catalog at [`_context.task-profiles.yml.tmpl`](../templates/_context.task-profiles.yml.tmpl)):

| Field | Meaning | Example |
|---|---|---|
| `id` | Stable profile identifier | `market-report:write` |
| `description` | One-line human description | `Writing a market report. …` |
| `required-zones` | Inline list of `<zone-id>=<true|false>`; `true` = required, `false` = optional | `[active=true, wiki=true, planned=false]` |
| `content-families` | Block list of named families with patterns + min-counts | `name=competitor-data, pattern=cluster=Competitive, required=true, min-count=1` |
| `source-of-truth-ranking` | Ordered list of zone IDs; first wins on conflict resolution | `[active, wiki, planned]` |
| `freshness-thresholds` | Per-zone `<zone-id>=<days|never>`; hits past threshold get verdict `past-threshold` | `[active=30, wiki=90, planned=never]` |
| `traversal-hints` | Edge kinds and depth caps to walk from seed hits | `[from-edge=builds-on, depth-cap=2]` |
| `coverage-assertions` | Per-family `<name>=<min-count>`; failures land in `missing-perspectives` | `[competitor-data=1]` |

Pattern grammar (used by `content-families` and applied to `context-index.json` doc records):

| Pattern | Matches when |
|---|---|
| `cluster=<value>` | `doc.cluster == <value>` |
| `tag=<value>` | `<value>` ∈ `doc.tags` |
| `page-type=<value>` | `doc.page_type == <value>` |
| `type=<value>` | `doc.type == <value>` |

Profiles describe the **shape** of context needed (patterns, thresholds, ranking), never the **instances** (specific slugs). The bundle resolver walks the typed-edge graph at runtime; profiles are stable across reorgs.

---

## The Catalog

Ten profiles ship with the framework template:

| Profile | When | Notable rule |
|---|---|---|
| `market-report:write` | Writing a market report | Canonical wins on conflict; pulls competitor + market + pricing |
| `engagement:plan` | Planning customer engagement | Live data preferred; wiki supports but never beats canonical |
| `architecture:design` | Designing or revising architecture | Framework spec + active data points anchor; wiki explainers support |
| `competitor:audit` | Running a competitor audit | Wiki source-summary + collections heavy; active anchors |
| `customer:onboard` | Customer onboarding | People + engagement context; live-data-leaning |
| `decision:log` | Logging an architectural / business decision | **Frozen-at-time evidence wins**; live data is supportive |
| `incident:postmortem` | Incident postmortem | Frozen-at-time evidence + decision context |
| `skill:author` | Authoring or modifying a skill | Framework spec authoritative; ecosystem state load-bearing |
| `plan:revise` | Revising a planned proposal | Other plans + active data points |
| `value-lookup:answer` | Answering measurement-shape questions (how much / when / who / top-N / biggest) | **Evidence wins over taxonomy**: collection-sidecar ranked highest, then manifest, then artifact, then active. For when the question shape is measurement, not definition. |

The catalog is loaded by [`load_task_profiles.py`](../../../.claude/scripts/load_task_profiles.py); validated by [`validate_task_profiles.py`](../../../.claude/scripts/validate_task_profiles.py) (wired into FIXED END / doc-lint). Per-repo override at `docs/.context.task-profiles.yml`.

### Catalog merge semantics

When both the framework template and the per-repo override exist, the loader **merges** them — the override no longer replaces the template wholesale:

| Profile ID is… | Result |
|---|---|
| In template only | Kept as-is from the framework. |
| In override only | Added to the catalog after the framework profiles. |
| In both          | Per-repo override **wins** — its entry replaces the framework's at the same position. |

**Migration note for existing plugins.** If your `docs/.context.task-profiles.yml` exists only because you needed to add a single profile alongside the framework's nine, you can now drop everything except the profile(s) you actually customise. Re-syncing on framework updates is no longer necessary — the merge handles it. (Deep-merging *within* a profile is intentionally not supported: redeclare the whole profile by ID to change it.)

---

## The Resolver

[`context_bundle.py`](../../../.claude/scripts/context_bundle.py) is the resolver. Single entry point: `resolve_bundle(profile_id, ...)` returns the envelope.

### Resolution steps (mechanical, deterministic)

1. **Load profile + corpus.** Profile via `load_task_profiles`; corpus via `context-index.json` (built by `context_index.py`).
2. **Build candidate pool.** Docs whose zone appears in `required-zones`.
3. **Walk typed edges.** From every seed in the pool, BFS over edges of the kinds declared in `traversal-hints` up to `depth-cap`. Each hop records `(from, edge, to, depth)` in `traversal-hops`.
4. **Group by zone.** Every pool hit lands in `by-zone[<zone-id>]`.
5. **Group by family.** Apply each family's pattern; matching hits land in `by-family[<family>]`.
6. **Compute freshness verdict.** Per-hit `fresh` / `stale` / `past-threshold` / `unknown` against the profile's per-zone thresholds. `never`-zones (e.g., `archive`) always return `fresh`.
7. **Detect conflicts.** Hits in the same family that share ≥1 `EXCLUSIVELY_OWNS` key across **different zones** are CLEAR-violation candidates. Resolved by `source-of-truth-ranking`: highest-ranked zone wins. Ties at the top zone-rank → `resolved-by: unresolved`.
8. **Compute coverage gaps.** Families failing `coverage-assertions[<family>]` min-count → `missing-perspectives`.
9. **Surface unsatisfied zones.** `required: true` zones with no docs → `unsatisfied-zone-requirements`.

Same fixture index → byte-identical envelope (modulo `generated-at`). Latency target: <1 second on a 200-doc corpus.

### Output envelope

```jsonc
{
  "profile-id": "market-report:write",
  "generated-at": "2026-05-04T19:00:00Z",
  "by-zone": { "active": [...], "wiki": [...], "planned": [...] },
  "by-family": { "competitor-data": [...], "market-data": [...], "pricing-data": [...] },
  "freshness": [
    { "path": "docs/competitors.md", "verdict": "past-threshold", "days-since": 80, "threshold": 30 }
  ],
  "source-of-truth-conflicts": [
    {
      "family": "pricing-data",
      "shared-owns": "tier-names",
      "candidates": [
        { "path": "docs/pricing.md", "zone": "active", ... },
        { "path": "docs/_planned/pricing-redesign.md", "zone": "planned", ... }
      ],
      "resolution": "docs/pricing.md",
      "resolved-by": "rank",
      "reason": "highest-ranked zone: active"
    }
  ],
  "missing-perspectives": [],
  "traversal-hops": [
    { "from": "docs/_wiki/pages/stripe-integration.md", "edge": "builds-on", "to": "docs/pricing.md", "depth": 1 }
  ],
  "unsatisfied-zone-requirements": [],
  "escalations": []
}
```

A hit (per-doc summary inside `by-zone` / `by-family` / `candidates`) carries: `path`, `name`, `zone`, `cluster`, `page-type`, `type`, `tags`, `exclusively_owns`, `last-updated`, `last-reviewed`, `age_days`. Other context-index fields are intentionally trimmed to keep the envelope small.

---

## Source-of-Truth Ranking — How Conflict Resolution Works

The CLEAR principle: every fact has exactly one canonical home. When two docs declare the same `EXCLUSIVELY_OWNS` key, that's either a real boundary violation or a forking proposal in `_planned/`. Both cases must surface to the human; the routing layer's job is to flag them, not silence them.

The resolver:

1. Indexes hits by `EXCLUSIVELY_OWNS` keys per family.
2. Any owns-key with ≥2 hits **across different zones** is a candidate conflict.
3. Resolution uses the profile's `source-of-truth-ranking`: the candidate whose zone appears earliest wins. Ties at the top zone-rank → `unresolved`.
4. Same-zone duplicates are NOT conflicts (those should already trip the `duplication-vs-data-point` lint before the resolver runs).

**Per-profile ranking is intentional** — `decision:log` ranks `collection-artifact` (frozen evidence) above `active`; `engagement:plan` does the opposite. Ranking is a property of the task, not a global constant.

---

## Freshness Verdicts

Per-hit verdict against the profile's per-zone threshold:

| Verdict | When |
|---|---|
| `fresh` | Threshold is `never`, or `age_days <= threshold/2` |
| `stale` | `threshold/2 < age_days <= threshold` |
| `past-threshold` | `age_days > threshold` |
| `unknown` | `age_days` is null (no `last-updated` field) |

The `freshness-field` per zone is determined by the [zone registry](./context-zones.md): `active` uses `last-updated`, `wiki` pages use `last-reviewed`, wiki `source-summary` uses `last-fetched` (via the `freshness-by-page-type` override).

---

## D-10 Strict — No Auto-Trigger

The default mechanical run never invokes the LLM. Two opt-in flags exist; both currently require `--dry-run` until the LLM client wiring lands:

| Flag | What it would do (when wired) | Today |
|---|---|---|
| `--resolve-conflicts` | LLM picks winners among `resolved-by: unresolved` candidates | Records `resolve-conflicts-dry-run` in `escalations`; non-dry-run raises `LLMEscalationNotImplementedError` |
| `--verify-coverage` | LLM verifies prose-level coverage of declared perspectives | Records `verify-coverage-dry-run`; non-dry-run raises |

The principle is the same as `/context search --semantic` (P2): mechanical default; explicit flag is the only escalation path; non-dry-run fails loudly rather than silently returning the mechanical envelope while pretending to have escalated.

---

## Determinism and Cost

- **Determinism.** Same fixture index → byte-identical envelope (modulo `generated-at`). Bundle output is suitable for diffing across runs to detect drift.
- **Cost.** O(N × F) for family grouping (N = pool size, F = profile families). Edge walking is BFS bounded by `depth-cap`; per-seed work is O(E) over outgoing edges. Conflict detection is O(F × O²) where O is owns-keys per family — for typical profiles this is well under a millisecond.
- **No LLM cost** unless the user opts in.

---

## How Consumers Use the Bundle

Typical agent flow:

1. The user kicks off a task: "Write me a market report."
2. The agent runs `/context bundle market-report:write --json`.
3. The agent reads the envelope and decides what to actually load:
   - Walks `by-zone["active"]` first (canonical truth).
   - Pulls `by-family["competitor-data"]` to ground the competitor section.
   - Notes `freshness` — anything `past-threshold` gets a *"this hit is stale"* annotation in the output.
   - Surfaces `source-of-truth-conflicts` to the user before drafting: *"`pricing-data` has a conflict between `docs/pricing.md` (active) and `docs/_planned/pricing-redesign.md` (planned). Treating active as authoritative; flagging the planned proposal."*
   - Treats `missing-perspectives` as gaps to call out: *"I don't have any `market-data` hits. The report will reflect this."*
   - Uses `traversal-hops` to follow `builds-on` chains where appropriate.

The bundle is reference data, not a directive. The agent decides what to actually pull into context based on the envelope — which is the whole point of keeping the envelope small.

---

## How Routing Composes With the Rest of the Architecture

- [`context-zones.md`](./context-zones.md) — zones, freshness models, source-of-truth roles. Routing reads the registry to know what zones exist and how to address them.
- [`metadata-system.md`](./metadata-system.md) — per-doc fields. Routing uses `cluster`, `tags`, `page_type`, `type`, `exclusively_owns`, `last-updated`, `last-reviewed`.
- [`wiki-zone.md`](./wiki-zone.md) — wiki-zone specifics including `freshness-by-page-type`. Routing reads `freshness-thresholds` accordingly.
- [`collections-zone.md`](./collections-zone.md) — collections (evidence) zone. `decision:log` and `incident:postmortem` profiles rank `collection-artifact` highly.
- [`content-routing.md`](./content-routing.md) — *write-side* routing (where new content lands). Distinct from the *read-side* routing this doc covers.
- [`system-design.md`](./system-design.md) — overall ecosystem map; references both context-zones and context-routing.

---

## Tests

[`test_context_capability.py`](../../../.claude/scripts/test_context_capability.py) — 20 mechanical assertions:

- Loader returns normalized profile entries.
- Validator rejects unknown zones, missing IDs, malformed entries.
- Envelope contains every required key.
- `by-zone` groups hits correctly.
- `by-family` applies pattern matching correctly.
- Conflict detection on overlapping `EXCLUSIVELY_OWNS` across zones.
- Conflict resolution picks the highest-ranked zone.
- Freshness verdicts use per-zone thresholds.
- Coverage gaps surface only when min-count unmet.
- Traversal walks `builds-on` edges to depth-cap.
- Determinism: two runs produce identical envelopes (modulo `generated-at`).
- Empty corpus surfaces `unsatisfied-zone-requirements`.
- D-10: default doesn't escalate; opt-in flags are the only LLM trigger.
- Non-dry-run opt-in raises `LLMEscalationNotImplementedError`.
- CLI smoke against the fixture profile + corpus.

---

## Summary

- A profile names a task and declares the shape of context it needs.
- The resolver walks the typed-edge graph deterministically and returns a structured envelope.
- Conflicts surface mechanically; resolution uses per-profile ranking; ties stay unresolved for the human.
- Freshness is per-zone, threshold-driven, with `never` as a first-class option.
- LLM is opt-in only via explicit flags. The default is honest mechanical Python.
- Profiles describe shapes, not instances. Reorgs don't break them.

The bundle is the layer that makes wiki + plans + context docs + collections + lessons + skills + registries function as a coordinated context base, not a pile of zones. Without P5, retrieval is keyword-search-and-pray; with P5, an agent declares its task and gets a curated, ranked, freshness-flagged, gap-aware bundle.
