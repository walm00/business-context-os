---
name: "Cross-repo retrieval — umbrella-aware fallthrough"
type: architecture
cluster: "Framework Evolution"
version: 1.1.0
status: active
created: 2026-05-10
last-updated: 2026-05-11
authority: canonical
exclusively-owns:
  - umbrella fallthrough contract for /context retrieval
  - minimum projects.json fields the framework consumes
  - .bcos-umbrella.json retrieval block schema
  - cross-repo citation-id format
strictly-avoids:
  - full projects.json schema (lives in the umbrella host's `umbrella-onboarding` skill)
  - umbrella-side write paths (this doc covers consumer-side only)
  - permissions setup (covered by permissions-catalog.md)
builds-on:
  - docs/_bcos-framework/architecture/permissions-catalog.md
  - docs/_planned/wiki-missing-layers/pre-flight-decisions.md
references:
  - .bcos-umbrella.json
  - .claude/skills/context-routing/SKILL.md
---

# Cross-repo retrieval — umbrella-aware fallthrough

## Why this exists

`/context search` and `/context bundle` operate on this repo's `.claude/quality/context-index.json`. When the user has a portfolio of BCOS-enabled siblings registered with an umbrella host (e.g. `my-portfolio`), the framework has no way to consult them — even though `.bcos-umbrella.json` is sitting in the repo root and each sibling already maintains its own context index daily.

This doc defines the **consumer-side contract** the framework reads from. The umbrella owns the canonical `projects.json` schema in its own onboarding skill; the framework consumes a documented minimum.

## D-10 reconciliation

D-10 (pre-flight-decisions.md, wiki-missing-layers) states: *"no auto-trigger, no auto-fallback, no hidden cost — even for mechanical paths."*

The user's portfolio intent ("auto on local-miss") contradicts framework-default D-10 strict. The reconciliation is **per-portfolio opt-in**:

- Fresh installs without `.bcos-umbrella.json` → bit-for-bit identical to today. No cross-repo I/O ever fires.
- Repos with `.bcos-umbrella.json` but no `retrieval` block → bit-for-bit identical to today. No cross-repo I/O ever fires.
- Repos with `.bcos-umbrella.json.retrieval.auto_fallthrough: true` → fallthrough enabled.
- Flags `--cross-repo` / `--no-cross-repo` override the config on a single invocation.

The framework default doesn't change. The user's portfolio decision does. D-10 honored at framework level.

## The opt-in block

Added to `.bcos-umbrella.json` (the file is gitignored and per-machine; each sibling has its own):

```json
{
  "schemaVersion": 1,
  "umbrella": { "id": "...", "path": "...", "registeredAt": "..." },
  "node": { "id": "...", "role": "..." },
  "shared_context": { "extra_exposes": [] },
  "retrieval": {
    "auto_fallthrough": true,
    "miss_signals": ["zero-hit", "low-coverage"],
    "max_sibling_hops": 3,
    "per_sibling_timeout_ms": 1000,
    "peek_min_strong_matches": 1,
    "peek_max_strong_rivals": 0
  }
}
```

All fields under `retrieval` are optional. Defaults if `retrieval` block present but field absent:

| Field | Default | Meaning |
|---|---|---|
| `auto_fallthrough` | `false` | Whether to consult siblings automatically on local-insufficient |
| `miss_signals` | `["zero-hit", "low-coverage"]` | Which signals count as "local insufficient" — see Local-insufficient definition below |
| `max_sibling_hops` | `5` | Maximum number of sibling repos to query in one pass |
| `per_sibling_timeout_ms` | `1000` | Per-sibling read+rank timeout; graceful skip on exceed |
| `peek_min_strong_matches` | `1` | Min # of authoritative-field matches for peek-strong (auto-fetch) |
| `peek_max_strong_rivals` | `0` | Max # of rival siblings tolerated for peek-strong (above = marginal) |

If `retrieval` block is absent entirely → no cross-repo I/O ever fires implicitly. Same behavior as a single-repo BCOS install.

## Local-insufficient definition

The trigger for the cross-repo gate. A search/bundle result counts as "local-insufficient" when **any** signal listed in `miss_signals` applies (OR-semantics — even partial local coverage is enough to consult siblings).

| Signal | What it means | When it fires |
|---|---|---|
| `zero-hit` | `hits == []` | The mechanical scorer returned no candidates |
| `low-coverage` | Top hit's `coverage` < 1.0 | Query terms not fully covered locally |
| `low-tier` | Top hit's `match-tier` ≤ T2 | Only partial/non-authoritative matches locally |
| `unsatisfied-zone-requirements` | `unsatisfied-zone-requirements != []` (bundle only) | A declared profile zone is absent from the corpus |

**Default `miss_signals`**: `["zero-hit", "low-coverage"]`. Rationale: a task that "really needs something missing here" can be either zero local hits OR partial local coverage. Both warrant peeking at siblings.

**Lockouts:** `low-tier` and `unsatisfied-zone-requirements` are NOT in the default list — they need explicit opt-in per portfolio. They're more aggressive triggers (every T2 hit OR every missing zone fires the peek).

**Always-emitted fields on hits** (search only): `match-tier` and `coverage` are now first-class hit fields (no longer hidden behind `--explain`). They're cheap (one int + one float per hit) and required by the gate evaluators.

**No LLM judgment in the miss decision.** All signals are deterministic. D-10 invariant preserved.

## Peek vs. deep-fetch (the three-stage filter)

Cross-repo retrieval doesn't blindly fire when local is insufficient — it consults siblings via a **cheap metadata peek** first, and only deep-fetches when the peek points to a clear sibling winner. This prevents "overkill every prompt": the BM25 ranker against sibling docs is only invoked when one sibling cleanly owns the topic.

```text
[local search across all zones in this repo]
   │
   ├─ T5 hit + full coverage    → answer. No peek. Cross-repo skipped.
   │
   └─ insufficient (per miss_signals)
        │
        ├─ explicit --cross-repo flag  → bypass peek → deep-fetch
        │
        └─ auto-fallthrough opt-in
             ▼
        [peek_sibling_corpora — metadata-only scan]
             │
             ├─ strong (clear winner)     → deep-fetch sibling corpus → merge hits
             ├─ marginal (some matches)   → emit cross-repo-suggestions, NO deep-fetch
             ├─ ambiguous (multi-sibling) → emit cross-repo-suggestions for all, NO deep-fetch
             └─ none (no metadata match)  → silent skip, trigger=peek-empty
```

### What the peek scans

Metadata fields only. No body text. No BM25 ranker. No LLM.

| Field | Class |
|---|---|
| `name` (title) | Authoritative |
| `filename` | Authoritative |
| `exclusively_owns` | Authoritative |
| `page_type` | Authoritative |
| `tags` | Supporting |
| `headings` | Supporting |
| `cluster` | Supporting |

A doc matches a query token if the token appears (case-insensitive substring) in any of these fields. The peek counts the docs that match per sibling, split into authoritative-match vs supporting-match buckets.

### Peek strength thresholds

| Setting | Default | Meaning |
|---|---|---|
| `peek_min_strong_matches` | `1` | Minimum # of docs with any authoritative-field match for the candidate to qualify as "strong" |
| `peek_max_strong_rivals` | `0` | Maximum # of OTHER siblings allowed to have any authoritative match (above 0 = ambiguity → marginal) |

**Default semantics**: peek is strong when exactly one sibling has at least one authoritative-field match AND no other sibling has any authoritative-field match. Conservative — auto-fetch only when one sibling clearly owns the topic.

Tune per portfolio:
- `peek_min_strong_matches: 3` → only deep-fetch when a sibling has 3+ docs matching. Reduces false-positive auto-fetches.
- `peek_max_strong_rivals: 1` → tolerate one rival sibling. Less paranoid about ambiguity.

### What `cross-repo-suggestions` looks like

Emitted when peek = marginal. Absent otherwise.

```jsonc
{
  "cross-repo-suggestions": {
    "peek-strength": "marginal",
    "suggestions": [
      {
        "sibling-id": "executions-os",
        "match-count": 3,
        "authoritative-match-count": 2,
        "top-citations": ["executions-os:wiki:incident-response", "executions-os:active:on-call"],
        "reasons": ["name-match", "tags-match", "exclusively_owns-match"]
      }
    ],
    "siblings-skipped": []
  }
}
```

The calling agent (Claude) consumes this and decides whether to surface the suggestion to the user ("executions-os has a runbook on incident response — want me to pull it in?") or include it silently. UX wiring is outside the framework — this doc only defines the data contract.

## The minimum contract — what `projects.json[i]` must provide

The umbrella's `projects.json` is written by the `umbrella-onboarding` skill (lives in the `bcos-umbrella` plugin on the umbrella host, not in this framework). The framework reads it as a flat list of project entries with the following minimum schema:

```json
{
  "schemaVersion": 1,
  "projects": [
    {
      "id": "string — must match the sibling's .bcos-umbrella.json.node.id",
      "path": "string — relative-to-umbrella path to sibling repo root",
      "exposes": ["string", ...]
    }
  ]
}
```

| Field | Required by framework? | Meaning |
|---|---|---|
| `schemaVersion` | yes | Currently `1`. Framework refuses to consume unknown major versions. |
| `projects[].id` | yes | Used to prefix sibling-hit citations. Must match the sibling repo's own `.bcos-umbrella.json.node.id`. |
| `projects[].path` | yes | Relative to the umbrella repo root. Framework resolves `<umbrella.path>/<projects[].path>` to find the sibling. |
| `projects[].exposes` | no | Optional list of doc-path globs the sibling shares. If absent → framework reads the sibling's full `context-index.json`. If present → framework filters the sibling's index by these globs before ranking. |

The umbrella schema may carry additional fields the framework ignores (UI grouping, role, last-sync timestamps, etc.). Forward-compatible by design.

### Per-sibling override

Each sibling repo may declare additional shared paths in its own `.bcos-umbrella.json.shared_context.extra_exposes`. The framework merges this on top of `projects[].exposes` when reading that sibling's corpus.

## Deep-fetch (peek-strong path)

When the peek says one sibling clearly owns the topic, the framework deep-fetches:

```text
Resolve .bcos-umbrella.json:
  - Read umbrella.path
  - <umbrella.path>/projects.json
  - Parse projects[]
   │
   ▼
For each project (capped by max_sibling_hops):
  - Resolve <umbrella>/<project.path>/.claude/quality/context-index.json
  - Filter docs[] by project.exposes globs (if present)
  - Merge in sibling's own .bcos-umbrella.json.shared_context.extra_exposes
  - Run mechanical search (BM25) against the sibling's filtered corpus
  - Tag each sibling hit's citation with `<project.id>:` prefix
  - Per-sibling timeout: per_sibling_timeout_ms (default 1000ms)
   │
   ▼
Merge sibling hits with local hits:
  - Local always wins on tie (authority hierarchy preserved)
  - Combined sort: (-tier, -score, citation_id)
  - Output trimmed to top_k
```

## Citation-ID format

Local hits (unchanged from today): `<zone>:<relative-path>`

```text
active:pricing
wiki:how-to-deploy
planned:wiki-missing-layers/README
```

Sibling hits (new format, **only** when the hit came from a sibling repo): `<sibling-id>:<zone>:<relative-path>`

```text
initiatives-os:active:roadmap-q3
executions-os:wiki:incident-response-runbook
```

The `<sibling-id>` is `projects[i].id` from the umbrella's `projects.json`, which matches the sibling's `.bcos-umbrella.json.node.id`. Backwards-compatible: anything that consumes local citations sees no format change.

## Output envelope additions

`/context search` and `/context bundle` gain two new top-level fields:

- **`cross-repo-status`** — what the gate decided (always present when `.bcos-umbrella.json` exists)
- **`cross-repo-suggestions`** — peek output for marginal cases (only present when peek = marginal)

```json
{
  "query": "...",
  "zones-searched": [...],
  "zones-skipped-not-present": [...],
  "hits": [...],
  "escalation": null,
  "cross-repo-status": {
    "attempted": true,
    "trigger": "auto-fallthrough" | "explicit-flag" | "explicit-no" | "not-opted-in" | "local-sufficient" | "peek-empty" | "peek-marginal",
    "umbrella-id": "my-portfolio" | null,
    "local-insufficient-signal": "zero-hit" | "low-coverage" | "low-tier" | "unsatisfied-zone-requirements" | null,
    "siblings-queried": [
      {"id": "...", "hits": 0, "took-ms": 12}
    ],
    "siblings-skipped": [
      {"id": "...", "reason": "timeout" | "unreachable" | "malformed-index" | "exposes-empty"}
    ]
  }
}
```

When fallthrough does NOT fire: `cross-repo-status` is either absent (default-config repos) or `{ "attempted": false, "trigger": "not-triggered" }`. Callers can detect single-repo behavior cleanly.

## Graceful absence

The framework treats every cross-repo I/O failure as a per-sibling skip, never a hard error.

| Condition | Behavior |
|---|---|
| `.bcos-umbrella.json` absent | `retrieval` block doesn't apply; behavior unchanged |
| `umbrella.path` resolves to a non-existent directory | `cross-repo-status.siblings-skipped[].reason = "unreachable"` (entire umbrella) |
| `projects.json` absent or malformed | Same; entire umbrella skipped |
| Single sibling's `path` resolves to a non-existent directory | That sibling's entry: `reason = "unreachable"` |
| Single sibling's `context-index.json` absent | That sibling's entry: `reason = "no-index"` |
| Single sibling's `context-index.json` malformed | That sibling's entry: `reason = "malformed-index"` |
| Single sibling exceeds `per_sibling_timeout_ms` | `reason = "timeout"` |
| All siblings filtered out by exposes globs | `reason = "exposes-empty"` |
| Unknown `projects.json.schemaVersion` major | `reason = "unsupported-schema-version"` (entire umbrella) |

**No cross-repo failure ever raises.** The local result is always returned; sibling failures appear only as skip entries in `cross-repo-status`.

## Authority hierarchy under cross-repo

Local docs always outrank sibling docs on the same `EXCLUSIVELY_OWNS` key. The framework will never let a sibling overwrite your canonical truth — only fill gaps.

| Conflict shape | Resolution |
|---|---|
| Local has the data point; sibling also has it (same `EXCLUSIVELY_OWNS` key) | Local wins. Sibling hit is suppressed from results. Conflict logged in `source-of-truth-conflicts[]` (bundle only). |
| Local does NOT have the data point; sibling has it | Sibling hit returned normally. No conflict. |
| Multiple siblings have it (none local) | Tie-broken by `projects[]` order in the umbrella's `projects.json`. Conflict logged. |

## Permissions

No new permissions are required. Per `permissions-catalog.md:47`, `Read(**)` is unrestricted across BCOS components. Reading `<umbrella>/projects.json` and `<sibling>/.claude/quality/context-index.json` falls under this rule.

Cross-repo *write* workflows still need the mirror-to-user-level perms step documented in `permissions-catalog.md:184-212`. This cross-repo *retrieval* feature is read-only and does not need that step.

## What this doc does NOT cover

| Topic | Lives where |
|---|---|
| Full `projects.json` schema | `umbrella-onboarding` skill (umbrella host) |
| Writing `.bcos-umbrella.json` | `umbrella-onboarding` skill (umbrella host) |
| Per-repo permissions setup | `permissions-catalog.md` |
| Cross-repo dispatcher workflows | `scheduling.md` |
| Embeddings / semantic cross-repo | Deferred; covered by P6 of wiki-missing-layers when it ships |

## Implementation references

- `.claude/scripts/cross_repo_fetch.py` — the helper that implements the fallthrough flow above
- `.claude/scripts/context_search.py` — extended with `--cross-repo` flag and config-driven fallthrough
- `.claude/scripts/context_bundle.py` — same
- `.claude/skills/context-routing/SKILL.md`, `search.md`, `bundle.md` — user-facing docs
- `.claude/tests/cross_repo_fixtures/` — synthetic test data
- `.claude/tests/test_cross_repo_search.py` — 6 scenarios validating the contract above
