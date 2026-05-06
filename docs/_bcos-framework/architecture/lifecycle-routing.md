---
name: "Lifecycle Routing Architecture"
type: context
cluster: bcos-framework
version: "1.0.0"
status: active
created: "2026-05-05"
last-updated: "2026-05-05"
---

# Lifecycle Routing Architecture

How CLEAR Context OS routes active documents to their permanent homes — `_archive/`, `_wiki/`, or `_collections/` — using a declarative rules table and a classifier that composes frontmatter triggers, body-signal markers, and reality cross-checks.

For the `lifecycle:` frontmatter field spec (the author-facing API), see `docs/_bcos-framework/methodology/document-standards.md` § "Lifecycle Triggers". For zone semantics see [`context-zones.md`](./context-zones.md). For how lifecycle-sweep fits into the broader maintenance schedule, see [`maintenance-lifecycle.md`](./maintenance-lifecycle.md).

---

## The Problem

Every active document accumulates quietly. Without an exit contract, it looks active forever — even after the proposal was sent, the decision was made, the analysis was superseded, or the idea was quietly abandoned. `index-health` can detect structural orphans (no inbound cross-references), but it cannot distinguish a live SOP from a shipped audit. Lifecycle routing provides the missing layer: **content-aware classification with deterministic exit triggers**.

---

## Architecture Overview

```
docs/_active/                  lifecycle-sweep job (weekly)
      │                               │
      │    ┌──────────────────────────┤
      │    │  1. Load lifecycle-routing.yml rules
      │    │  2. For each active doc:
      │    │       a. Evaluate declared lifecycle: triggers (frontmatter)
      │    │       b. Scan body for signal markers
      │    │       c. Run reality cross-checks
      │    │       d. Classify → route_decision
      │    │  3. Execute route (surface-only in burn-in mode)
      │    │  4. Emit typed events → digest sidecar
      │    │  5. Record each decision → resolutions.jsonl
      └────┘
           │
     ┌─────┴──────────────────────────────────────────┐
     │  Routes to:                                     │
     │  _archive/<bucket>/   (most routes)             │
     │  _wiki/source-summary/ (research-dump route)   │
     │  _collections/<type>/ (evidence route)          │
     │  fold-into SOP        (meeting-notes / process) │
     └────────────────────────────────────────────────┘
```

The classifier is **composable**. A single document can match on all three signals: a declared `archive_when`, a `SENT:` body marker, AND a git-log reality check — the combination raises confidence above the auto-route threshold. A document with only one signal stays at the lower tier (preselect or flag-only) until the others confirm.

---

## Lifecycle-Routing Config

**File:** `.claude/quality/lifecycle-routing.yml`
**Schema version:** `1.0.0`
**Drift test:** `.claude/scripts/test_lifecycle_routing.py`

The config is the declarative table that `lifecycle_sweep.py` reads. It has two sections: a `global:` block controlling sweep behaviour, and a `rules:` list with one entry per routing pattern.

### Global block

```yaml
global:
  surface_only: true        # BURN-IN: flip to false after 2-week clean run
  burn_in_weeks: 2
  scan_zones: [active, inbox, planned]
  min_age_days: 7
  ambiguous_finding_type: lifecycle-route-ambiguous
  orphan_finding_type:     lifecycle-orphan-active
```

| Field | Type | Meaning |
|---|---|---|
| `surface_only` | bool | When `true` the sweep classifies but never moves files. Default for the 2-week burn-in. |
| `burn_in_weeks` | int | How many clean weeks before `surface_only` can be flipped to `false`. |
| `scan_zones` | list[zone-id] | Which zones `lifecycle_sweep.py` walks. Must be valid zone ids from `_context-zones.yml.tmpl`. |
| `min_age_days` | int | Docs younger than this (by `last-updated`) are never evaluated — avoids false-positives on new docs. |
| `ambiguous_finding_type` | string | Typed-event ID emitted when a trigger fires but reality check fails (from `typed-events.md`). |
| `orphan_finding_type` | string | Typed-event ID emitted for active-zone docs with no lifecycle field, no inbound xrefs, and age above threshold. |

### Rule block

Each rule in the `rules:` list matches one abstract document pattern. Rules are evaluated top-to-bottom; **first match with a passing reality-check wins**.

#### Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique kebab-case identifier. Used as the log/digest key and in sidecar findings. |
| `description` | string | Human-readable explanation of when this rule fires and where it routes. |
| `match` | object | Matching criteria (see below). At least `match.zones` is required. |
| `destination` | object | Where to route — `zone` + optional `bucket`. |
| `confidence-tier` | int (1–3) | How autonomously the sweep acts on this rule (see tier definitions). |
| `auto-fix-id` | string | Headless action ID from `headless-actions.md` to execute when auto-routing. |

#### `match` object

```yaml
match:
  zones: [active]                     # REQUIRED — zone ids to scan
  lifecycle-triggers:                 # optional — lifecycle field matchers
    - archive_when: [proposal-sent]
    - expires_after: any
  cluster-hints: [outbound, sales]    # optional — raises confidence when matched
  name-patterns: ["(?i)\\bsync\\b"]  # optional — regex on doc name field
```

| Sub-field | Meaning |
|---|---|
| `zones` | Which zones the sweep walks to apply this rule. Must be valid ids from `_context-zones.yml.tmpl`. Almost always `[active]`; `idea-dead` uses `[planned]`. |
| `lifecycle-triggers` | Trigger-type matchers. Each is a `key: value` pair where the key is one of the five lifecycle field names (`archive_when`, `expires_after`, `route_to_wiki_after_days`, `route_to_collection`, `fold_into`) and the value is a match expression (`[list of valid values]` or `any`). A doc matches if ANY declared trigger fires. |
| `cluster-hints` | List of `cluster` frontmatter values that increase confidence when matched. Used for pattern detection when the doc has no explicit `lifecycle:` field. |
| `name-patterns` | Python regex list matched against the doc's `name` frontmatter. Useful for snapshot/meeting-notes detection where naming convention is the signal. |

#### Lifecycle trigger types

| Trigger key | Fires when |
|---|---|
| `archive_when` | `lifecycle.archive_when` in frontmatter matches one of the listed values, AND the body-marker or reality-check for that value passes. |
| `expires_after` | Date arithmetic: `last-updated + lifecycle.expires_after_days < today`. |
| `route_to_wiki_after_days` | `lifecycle.route_to_wiki_after_days` days have elapsed since `last-updated`. |
| `route_to_collection` | `lifecycle.route_to_collection` is declared (any non-null value). |
| `fold_into` | `lifecycle.fold_into` is declared AND the target file exists. |
| `body-marker` | Body contains a matching marker pattern (no lifecycle field required). Confidence is lower without a frontmatter declaration. |
| `age-threshold` | Doc age (`today - last-updated`) exceeds the declared number of days. Used as a fallback signal for patterns where explicit lifecycle fields are rarely added. |

#### `destination` object

```yaml
destination:
  zone: archive          # MUST be a valid zone id in _context-zones.yml.tmpl
  bucket: outbound/sent  # optional sub-path appended to the zone's base path
```

The `zone` field is the authority. The `bucket` is advisory — `lifecycle_sweep.py` uses it to construct the target directory path (`docs/_archive/<bucket>/`), but never hardcodes zone base paths. Zone base paths are resolved at runtime via `_zone_for()`.

**Drift contract:** every `destination.zone` in `lifecycle-routing.yml` must be a valid id in `_context-zones.yml.tmpl`. Enforced by `.claude/scripts/test_lifecycle_routing.py`.

#### `body-markers` list

```yaml
body-markers:
  - pattern: "^SENT: "
    role: confirm
    confidence-boost: 0.4
  - pattern: "^SENT: "
    role: require    # negative example: if present, DISQUALIFY this rule
    confidence-boost: -1.0
```

| Sub-field | Type | Meaning |
|---|---|---|
| `pattern` | regex | Applied to each line of the body (`re.MULTILINE`). Case-sensitive unless `(?i)` is used. |
| `role` | enum | `confirm` — presence counts in favour of this route; `require` — absence of this marker disqualifies the rule (use with negative `confidence-boost`); `boost` — soft positive signal that raises but doesn't decide. |
| `confidence-boost` | float | Added to the rule's running confidence score when the pattern matches. Range –1.0 to +1.0. Negative values reduce confidence (use for disqualification logic). |

Body-marker patterns are drawn from the table in `document-standards.md` § "Body-marker table". Custom patterns per rule are allowed.

#### `reality-checks` list

```yaml
reality-checks:
  - id: sent-marker-present
    type: git-log-mention
    description: "Confirm SENT: marker was added after doc creation."
    fail-action: ambiguous
```

| Sub-field | Type | Meaning |
|---|---|---|
| `id` | string | Unique within this rule; referenced in sidecar findings and digest output. |
| `type` | enum | The cross-check to run (see check types below). |
| `description` | string | Plain-language description for the digest and user review. |
| `fail-action` | enum | `ambiguous` — emit `lifecycle-route-ambiguous` finding, stop routing; `warn` — log warning, continue at reduced confidence; `skip` — skip this rule, try next. |

**Reality check types:**

| Type | What it checks |
|---|---|
| `git-log-mention` | Searches git log for commits mentioning this doc, a declared body marker, or a sibling path. Catches both confirms (marker appeared after creation) and contradictions (marker is present but git shows no corresponding action). |
| `sibling-version-exists` | Checks whether a sibling file matching a naming pattern exists (e.g., an "as-sent" copy of a proposal). |
| `url-in-body` | Confirms at least one `https?://` URL is present in the body. Required for wiki promotion (source-summary must have a source). |
| `target-file-exists` | Confirms `lifecycle.fold_into` target exists at the declared path. |
| `next-period-doc-exists` | For snapshot detection: confirms a newer-period doc in the same name series exists in the active zone. |
| `manifest-row-exists` | For collection routes: confirms `_collections/<type>/_manifest.md` exists (or is ready to be created). |
| `skill-registry-check` | Searches git log for a merge commit referencing the audited artifact, or verifies the artifact's path exists in the live codebase. |

#### Confidence tiers

| Tier | Label | Behaviour |
|---|---|---|
| `1` | auto | Route is applied automatically. Requires `surface_only: false` AND burn-in confirmed AND `auto-fix-whitelist.md` entry. In practice: only after 2+ weeks of zero false-positives. |
| `2` | preselect | Finding is surfaced on the dashboard with the route pre-selected. User accepts or rejects. Applies in surface-only mode. |
| `3` | flag-only | Finding is surfaced as a card. No pre-selected action. User must explicitly decide. Used for process experiments, dead ideas, audit archival — decisions that need human sign-off. |

---

## The Nine Default Rules

| Rule ID | Source Zone | Destination | Tier | Key trigger |
|---|---|---|---|---|
| `outbound-sent` | active | archive/outbound/sent | 2 | `archive_when: proposal-sent` + `^SENT:` marker |
| `outbound-abandoned` | active | archive/abandoned | 2 | `expires_after` elapsed + no `^SENT:` |
| `decision` | active | archive/decisions | 2 | `archive_when: decision-made` + `^DECISION:` or `^RESOLVED:` |
| `meeting-notes` | active | archive/meetings (or fold) | 2 | `fold_into` declared + target exists |
| `research-dump` | active | wiki/source-summary | 2 | `route_to_wiki_after_days` elapsed + URL in body |
| `snapshot` | active | archive/snapshots | 2 | name-pattern (Q1/monthly/etc.) + next-period sibling exists |
| `process-experiment` | active | archive/abandoned (or fold) | 3 | `fold_into` or `archive_when: abandoned` |
| `idea-dead` | planned | archive/abandoned | 3 | age > 90d + no recent git edit |
| `audit-of-shipped` | active | archive/audits | 3 | audited artifact confirmed shipped in git log |

All rules default to `confidence-tier: 2` or `3`. No rule ships at tier 1 — auto-routing is gated behind the 2-week burn-in protocol.

---

## Burn-In Protocol

The sweep ships with `global.surface_only: true`. This means:

1. **Week 1–2:** Sweep runs on its Friday slot. Classifies every active doc. Emits findings. Surfaces dashboard cards. **Never moves files.**
2. **Human review:** The user reviews each week's findings. False-positives are noted in the session diary.
3. **After 2 clean weeks:** If zero false-positives are confirmed, flip `surface_only: false` in `lifecycle-routing.yml`. Tier-2 routes become auto-applied (preselect). Tier-3 stays flag-only forever.
4. **auto-fix-whitelist.md:** `lifecycle-route-*` ids must also be declared in the whitelist (done in P4_003). Both gates must be open before any file moves automatically.

---

## Relationship to Other Architecture

| System | Connection |
|---|---|
| `document-standards.md` | Defines the `lifecycle:` frontmatter field and body-marker table. lifecycle-routing.yml consumes the same trigger names and marker patterns. |
| `context-zones.md` + `_context-zones.yml.tmpl` | `destination.zone` and `match.zones` must reference zone ids declared here. Enforced by drift test. |
| `content-routing.md` | lifecycle-sweep is **Path 8** (outbound from active zone via trigger). Existing paths 1–7 are for incoming content; path 8 is the first outbound path. |
| `maintenance-lifecycle.md` | lifecycle-sweep runs weekly (Friday) in the Steady phase. Registered as a dispatcher job. |
| `typed-events.md` | Sweep emits four finding types: `lifecycle-trigger-fired`, `lifecycle-body-marker-confirmed`, `lifecycle-route-ambiguous`, `lifecycle-orphan-active`. |
| `headless-actions.md` | Four headless actions: `lifecycle-route-archive`, `lifecycle-route-wiki`, `lifecycle-route-collection`, `lifecycle-fold-into`. Each maps to an `auto-fix-id` in a routing rule. |
| `digest_sidecar.py` | Sweep writes findings into the daily-digest.json sidecar using `SCHEMA_VERSION="1.0.0"`. |
| `record_resolution.py` | Every applied route writes a 14-field row to `resolutions.jsonl`. `promote_resolutions.py` then auto-promotes consistent `(lifecycle-*, lifecycle-route-*)` pairs into the self-learning ladder. |

---

## Extending the Routing Table

To add a new routing rule:

1. Add an entry to `.claude/quality/lifecycle-routing.yml` following the schema above.
2. Choose a `destination.zone` from `_context-zones.yml.tmpl`. Do NOT invent zone IDs.
3. Set `confidence-tier: 3` initially. Promote to tier 2 after validating against real docs.
4. Add the corresponding `auto-fix-id` to `auto-fix-whitelist.md` when ready for auto-route.
5. Run `.claude/scripts/test_lifecycle_routing.py` — all 15 tests must pass.

To add a new reality-check type, add the handling code to `lifecycle_sweep.py` and document the type in the "Reality check types" table above.
