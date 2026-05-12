# Collections Zone Architecture

How `docs/_collections/` works in CLEAR Context OS — what it holds, why files there are immutable, how the manifest pattern makes binary cargo first-class evidence, how its vocabularies grow with the business, and how it stays distinct from `_wiki/`, `_inbox/`, and active data points.

For the sibling zone mechanics see [`wiki-zone.md`](./wiki-zone.md) and [`content-routing.md`](./content-routing.md). For the philosophical placement of zones see [`system-design.md`](./system-design.md).

> **Net summary in one line:** files in `_collections/` are immutable evidence — invoices, signed contracts, brand kits, transcripts, exports. We *manifest the directory, not the files*: each subdirectory carries a required `_manifest.md` with one row per file, BCOS-aligned frontmatter, and bidirectional links to active data points. A schema-driven `.schema.yml` registry defines collection sub-types and their required manifest columns, so adding a new collection category is one edit, not five.

---

## Why a Collections Zone Exists

BCOS already has homes for *truth* (`docs/*.md` data points), *explanation* (`docs/_wiki/`), *future state* (`_planned/`), and *triage* (`_inbox/`). What's missing is a home for **artifacts the user receives or generates that should not be paraphrased**:

- An invoice PDF — paraphrasing it loses the signature, the line items, the amount in the original currency
- A signed contract — the file IS the legal instrument
- A brand kit zip — the assets ARE the brand
- A call transcript — the words spoken are the evidence
- A monthly Stripe export, a Salesforce dump, a downloaded report — the file IS the source of record

Editing these files corrupts evidence. Paraphrasing them into a data point loses fidelity. They need a zone with three properties: (1) **immutable** — the framework never rewrites these files; (2) **inventoried** — Claude knows what's there without opening every file; (3) **linked** — every artifact ties back to the data points it provides evidence for.

That's `_collections/`.

---

## The Immutability Constraint — and Why It Forces a Pattern

You can't put YAML frontmatter inside a PDF. You can't add a `version:` line to a docx. You can't bump `last-updated` on a zipped brand kit. The metadata has to live somewhere *adjacent* to the file, not inside it.

Pin-llm-wiki faces the same constraint with its `raw/<type>/` captures (verbatim, never edited) and solves it with a per-directory `README.md` that holds the metadata table. We adopt the same pattern, generalize it, and require it.

**The rule:** *manifest the directory, don't try to manifest the files.*

---

## Folder Layout

```
docs/_collections/
├── .schema.yml                         # Vocabulary registry — see "Schema and Governance"
├── README.md                           # Zone overview (auto-maintained)
│
├── invoices/                           # manifest-schema: invoices
│   ├── _manifest.md                    # required — one row per file
│   ├── 2026-04-08_acme-q2.pdf
│   ├── 2026-03-12_globex-march.pdf
│   └── .archive/                       # soft-deleted artifacts (see "Soft-Delete Pattern")
│       └── 2024-old-format.pdf
│
├── contracts/                          # manifest-schema: contracts
│   ├── _manifest.md
│   ├── 2026-04-08_acme-msa.pdf
│   ├── 2026-04-08_acme-msa.meta.md     # OPTIONAL sidecar — rich metadata
│   ├── 2026-03-15_globex-nda.pdf
│   └── .archive/
│
├── brand-kits/                         # manifest-schema: brand-kits
│   ├── _manifest.md
│   ├── brand-kit-v2.0.zip
│   └── brand-kit-v2.0.meta.md          # extracted color codes, font names
│
├── call-transcripts/                   # manifest-schema: call-transcripts
│   ├── _manifest.md
│   └── 2026-04-12_acme-discovery.md
│
├── statements/                         # manifest-schema: statements
│   ├── _manifest.md
│   └── 2026-Q1_stripe-export.csv
│
└── wiki-source-docs/                   # manifest-schema: custom — files referenced by _wiki/ pages (Path B in wiki-zone)
    ├── _manifest.md
    └── 2026-04-15_competitor-analysis.pdf
```

**Three artifact types, three handling rules:**

| Artifact form | Manifest treatment | Sidecar? | Reason |
|---------------|--------------------|----------|--------|
| Binary (PDF, .docx, .zip, .png) | Required row | Optional — when row can't carry the metadata | We can't put frontmatter in a PDF |
| Plain text/markdown (transcripts, exports) | Required row | Rare — only when extracted facts deserve structure | The file itself can be glob-searched |
| Structured data (CSV, JSON exports) | Required row | Optional — when extracted KPIs deserve their own page | The file is machine-readable |

---

## The `_manifest.md` Schema

One per subdirectory. Required. The manifest is the awareness surface — Claude reads it at session start and during retrieval; it never opens the underlying PDFs unless a query specifically demands it.

### Frontmatter (BCOS-aligned)

```yaml
---
type: collection-manifest
collection: contracts                 # subdirectory name
manifest-schema: contracts            # contracts | invoices | brand-kits | call-transcripts | statements | reports | custom
version: 1.4.0                        # bumped on every row change
created: 2026-01-15
last-updated: 2026-04-30
last-scanned: 2026-04-30              # auto-updated by collections-scan
file-count: 12                        # auto-maintained
owner: gunti
status: active

cluster: partnerships                 # primary cluster (single, BCOS convention)
related-clusters:                     # optional cross-cutting clusters
  - vendor-relationships

# Aggregated cross-zone references (graph-ready)
related-data-points:                  # data points that any row in this manifest cites
  - partnerships.md
  - vendor-relationships.md
---
```

### Body — the file table

The columns vary by `manifest-schema`. Pre-defined schemas have known required columns; lint enforces them.

**Schema: `contracts`**

```markdown
# Contracts — manifest

| File | Counterparty | Type | Signed | Expires | Status | Related data point |
|------|--------------|------|--------|---------|--------|--------------------|
| 2026-04-08_acme-msa.pdf | Acme Corp | MSA | 2026-04-08 | 2028-04-08 | active | [partnerships](../../partnerships.md) |
| 2026-03-15_globex-nda.pdf | Globex | NDA | 2026-03-15 | perpetual | active | [partnerships](../../partnerships.md) |
| 2025-09-01_initech-saas.pdf | Initech | SaaS | 2025-09-01 | 2026-09-01 | **expiring-soon** | [vendor-relationships](../../vendor-relationships.md) |
```

**Schema: `invoices`**

| File | Client | Amount | Currency | Issued | Paid | Related data point |

**Schema: `brand-kits`**

| File | Version | Asset count | Formats | Valid from | Related data point |

**Schema: `call-transcripts`**

| File | Date | Participants | Topics | Outcome | Related data point |

**Schema: `statements`**

| File | Period | Source | Key numbers | Related data point |

**Schema: `reports`**

Derived analytical reports — produced by an internal pipeline (financial audits, competitive-intel exports, customer-discovery rollups). The manifest row is the awareness surface; pair it with a `.meta.md` sidecar (see "Derived-Report Sidecar" below) when the report has key numbers worth ranking against value-lookup queries.

| File | Period | Report type | Audience | Run date | Related data point |
|------|--------|-------------|----------|----------|--------------------|
| 2026-04-30_q1-revenue.xlsx | 2026-Q1 | Revenue rollup | Investors | 2026-04-30 | [revenue-model](../../revenue-model.md) |
| 2026-02-15_competitive-landscape.html | 2026-02 | Competitive scan | Internal | 2026-02-15 | [competitive-positioning](../../competitive-positioning.md) |

**Schema: `custom`**

User-defined columns. Lint reports schema as `INFO` ("custom schema in use, no column-level validation"). All other manifest checks still apply (untracked, orphan, expiry).

**The full enumeration of available `manifest-schema` values lives in `_collections/.schema.yml` (see "Schema and Governance" below).** New schemas are added there, not by editing this document.

### Why markdown links instead of `[[wikilinks]]`

Wikilinks `[[slug]]` are reserved for `_wiki/` ↔ `_wiki/` refs (the wiki's internal graph). Cross-zone references — collection → data point, wiki → data point, wiki → collection — use standard markdown links so the dependency direction is unambiguous and `doc-lint` resolves them with the existing path-checking.

---

## Sidecar `.meta.md` — When the Row Isn't Enough

Default: a manifest row covers the file. **Sidecar only when the artifact deserves richer metadata** the row can't fit:

- A 50-page MSA with 5 key clauses worth indexing
- A brand kit with extracted color codes (`#1a73e8`), font names, asset inventory
- A call transcript with a structured "Decisions" / "Action Items" extraction

```yaml
# 2026-04-08_acme-msa.meta.md (sits next to 2026-04-08_acme-msa.pdf)
---
type: collection-sidecar
collection: contracts
artifact-file: 2026-04-08_acme-msa.pdf
version: 1.0.0
created: 2026-04-09
last-updated: 2026-04-09
owner: gunti
status: active

cluster: partnerships
builds-on:                              # data points this artifact provides evidence for
  - partnerships.md
  - pricing-model.md

# Sidecar-specific
extracted-on: 2026-04-09
extraction-method: human                # human | llm | mixed
key-fields:
  counterparty: Acme Corp
  effective-date: 2026-04-08
  expiry-date: 2028-04-08
  governing-law: Delaware
  termination-clause: section 12.3
  payment-terms: net-30
---

## Key clauses

### Section 4 — Service levels
99.5% uptime SLA, 4-hour response time...

### Section 12.3 — Termination
Either party may terminate with 30-day written notice...
```

**Sidecar discipline:**
- Sidecar is hand-written or LLM-extracted on ingest, then human-reviewed.
- Sidecar follows BCOS frontmatter rules (versioned, owned, status).
- Sidecar can be edited independently; the artifact PDF stays immutable.
- If a sidecar contradicts the artifact (someone mis-extracted a date), the artifact wins — sidecar is a derived view, not the source.

### Derived-Report Sidecar

Derived reports (Excel/CSV/HTML produced by an internal pipeline) are a recurring artifact category — financial audits, competitive-intel scans, customer-discovery rollups, product-metrics summaries. They benefit from a sidecar that names the **period**, the **freshness window**, and the **key fields** the resolver should rank against `value-lookup:answer` queries.

```yaml
# 2026-04-30_q1-revenue.meta.md (sits next to 2026-04-30_q1-revenue.xlsx)
---
type: collection-sidecar
collection: reports
artifact-file: 2026-04-30_q1-revenue.xlsx
version: 1.0.0
created: 2026-04-30
last-updated: 2026-04-30
owner: gunti
status: active

cluster: revenue
builds-on:                              # data points this evidence supports
  - revenue-model.md
  - customer-base.md

# Derived-report sidecar fields
period: "2026-Q1"
generated-from: docs/_collections/raw-data/q1-2026-stripe-export.csv
generation-date: 2026-04-30
generation-method: scripts/generate_revenue_report.py
freshness: fresh                        # fresh | stale | regenerate-now
freshness-window: 90d                   # past this, retrieval flags as stale
extracted-on: 2026-04-30
extraction-method: human                # human | llm | mixed

key-fields:
  total-mrr: 42000
  largest-customer: Acme Corp
  largest-customer-mrr: 8500
  new-customers-q1: 7
  churned-customers-q1: 2
---

## Q1 2026 — Revenue summary

(Prose context distilled from the xlsx — anchors for value-shape questions.)
```

**Field reference:**

| Field | Purpose |
|---|---|
| `period` | Time window the report covers — quarter, month, audit span. Free-form string; the resolver does not parse semantics. |
| `generated-from` | Repo-relative path to the raw input. Lets the next pipeline run identify what to re-process. |
| `generation-date` | When this output was produced. Compared against `freshness-window` to decide regenerate-now. |
| `generation-method` | Pipeline script or process. Lets a maintainer find how to regenerate without reading the manifest. |
| `freshness` | Author's current verdict: `fresh` / `stale` / `regenerate-now`. The freshness-window expiry is mechanical; this field is the human override. |
| `freshness-window` | Duration after which retrieval flags this sidecar as stale (`Nd`, `Nw`, `Nm`). |
| `key-fields` | Domain-specific extracted values. The framework specifies the **shape** (map of name → value), not the **vocabulary** — finance uses `total-spend-eur`, revenue uses `total-mrr`, competitive intel uses `top-3-competitors`, etc. |

**Lifecycle:**

1. The same pipeline that produces the report writes the sidecar (or a follow-up `extract_keyfields.py` step).
2. When `freshness-window` expires, the next pipeline run regenerates the sidecar with updated `key-fields:`.
3. `collections-scan` may surface `freshness: stale` or window-expired sidecars in its log.
4. Authors who want to flag a stale claim that still references this sidecar use `stale-claims:` on the canonical doc (see [`document-standards.md`](../methodology/document-standards.md)).

**Why this matters:** the `value-lookup:answer` task profile (catalog: `_context.task-profiles.yml.tmpl`) ranks `collection-sidecar` **above** `collection-manifest`, `collection-artifact`, and active data points — precisely because the sidecar's `key-fields:` is evidence-extracted, fresh, and structured for measurement-shape questions. Without the sidecar, the resolver falls back to canonical taxonomy, which is the wrong answer for "how much / when / who / top-N" queries.

---

## Naming Convention — Soft, Scanned, Not Enforced

Adopt pin-llm-wiki's `YYYY-MM-DD_<descriptor>.<ext>` as a **suggestion**. Three rules:

1. **Never rename user files.** If someone uploads `Acme Q3 Review.pdf`, that's the filename. Don't auto-rename to `2026-04-08_acme-q3-review.pdf` — you'll break external references that point to the original name.
2. **Soft-flag inconsistency.** `collections-scan` reports filename-convention violations as **INFO**, never **WARN**.
3. **Encourage forward.** New uploads through `context-ingest` are gently nudged toward the convention via `AskUserQuestion`: "Filename violates convention. Rename to `2026-04-08_acme-q3-review.pdf`?" with options *Rename* / *Keep as-is* / *Always keep as-is for this collection*.

Filename length under 100 characters to avoid cross-platform issues (already in current `content-routing.md` Path 5 — keeping).

---

## Soft-Delete Pattern

Ported from pin-llm-wiki's `wiki/.archive/` mechanism with a dangling-reference scan.

When `/collection archive <file>` runs:

1. **File moves** from `_collections/<type>/<file>` → `_collections/<type>/.archive/<file>`
2. **Manifest row updates:** `status: archived`, append `archived: <date>` column (manifest gets one more column the first time something is archived; lint accepts column variance for archive-related fields)
3. **Dangling-reference scan** runs across `docs/*.md`, `_wiki/**/*.md`, and other manifest tables for any markdown link or sidecar reference to the archived file. Findings are **reported, not auto-fixed** — the user decides whether to update references, archive the citing doc, or restore the artifact.
4. **Sidecar moves with the artifact** if one exists.

**Restore:** `/collection restore <file>` reverses the move and resets manifest row `status: active`.

**Hard-delete:** never automated. Files in `.archive/` stay until a human deletes via OS file ops + manually edits the manifest. The framework treats `.archive/` as cold storage.

---

## The `collections-scan` Job

New scheduled job, weekly cadence by default. Ten checks.

| # | Detection | Severity | What gets reported |
|---|-----------|----------|--------------------|
| 1 | File on disk, no manifest row | WARN | "Untracked file: `_collections/invoices/q2-2026.pdf` — add manifest row" |
| 2 | Manifest row, file missing on disk | ERROR | "Orphan manifest row: `2025-deleted-doc.pdf`" |
| 3 | Sidecar `.meta.md` references missing artifact | ERROR | Same orphan logic, with sidecar path |
| 4 | `status: active` AND `expires < today + 30d` | WARN | "Expiring soon: 2 contracts" + list |
| 5 | `status: active` AND `expires < today` | ERROR | "Expired but still marked active" |
| 6 | Row with empty `Related data point` column | INFO | "N files unlinked to active context" |
| 7 | Filename violates suggested convention | INFO | Soft nudge only |
| 8 | Subdirectory >20 files but no `_manifest.md` | WARN | "Manifest required" |
| 9 | Manifest `manifest-schema` doesn't match required columns | ERROR | "Missing required column: `Counterparty`" |
| 10 | `Related data point` link resolves to a renamed/archived data point | ERROR | "Broken link: `[partnerships](...)` no longer exists" |

**Auto-fixes (whitelisted):**
- Update `last-scanned: <today>` in manifest frontmatter on every run
- Update `file-count: <n>` in manifest frontmatter
- Move row `status` from `active` → `expiring-soon` when within 30d of expiry
- Move row `status` from `expiring-soon`/`active` → `expired` when past expiry

**Wired into `.claude/quality/schedule-config.json`:**

```json
{
  "jobs": {
    "collections-scan": {
      "enabled": true,
      "schedule": "weekly",
      "_about": "Scan all _collections/<type>/ for manifest consistency, untracked files, orphans, expiry, and broken cross-zone links. Auto-fixes: last-scanned, file-count, derived status transitions."
    }
  },
  "auto_fix": {
    "whitelist": [
      "collections-update-last-scanned",
      "collections-update-file-count",
      "collections-mark-expiring-soon",
      "collections-mark-expired"
    ]
  }
}
```

---

## Wake-Up Awareness

Generated into `docs/.wake-up-context.md` (the ~200-token snapshot Claude reads at session start).

The wake-up generator (`python .claude/scripts/generate_wakeup_context.py`) reads each `_manifest.md` frontmatter — `file-count`, status counts — and emits one line per collection:

```
Collections: 47 invoices, 3 brand kits, 12 contracts (1 expiring soon, 0 expired)
```

This is the equivalent of pin-llm-wiki's `wiki/index.md` "*N sources ingested.*" Claude now knows, in one line, what evidence exists without scanning the directories.

---

## Quarterly Coverage Audit (daydream-adjacent)

Folded into the existing `daydream` skill's quarterly run, or as a standalone `collections-coverage` job:

**Question:** "Which active data points have collection evidence but no link, or vice versa?"

**Detection examples:**
- `business-model.md` exists but no invoice in `_collections/invoices/` cites it as `Related data point` → are invoices being captured at all?
- 12 contracts in `_collections/contracts/` exist but no `partnerships.md` data point → coverage gap (suggest creating one)
- `target-audience.md` exists but no call transcript in `_collections/call-transcripts/` cites it → are we capturing customer conversations?

This applies BCOS's **compounding rule** to evidence: a new collection item should prompt *"does this evidence any data point? Should one exist if not?"* and an active data point should prompt *"is there evidence we should be linking?"*

---

## Integration with `context-ingest` (Path 5 extension)

`context-ingest` Path 5 (Collection) currently routes bulk files to `_collections/<type>/`. Extend with manifest discipline:

**On each Path 5 routing:**

1. Confirm or pick the `<type>` subdirectory (existing behavior)
2. Confirm or pick the filename convention (new — `AskUserQuestion`: rename to convention / keep as-is)
3. Move the file into the subdirectory
4. **Append a manifest row** — `AskUserQuestion`-driven for the schema-required columns (e.g., contracts: counterparty, type, signed, expires)
5. **Prompt for `Related data point`** — `AskUserQuestion` lists candidate data points (top 3 by cluster match) + "create new" + "leave empty for now"
6. **Optionally prompt for sidecar** — only when artifact is binary and large (>10 pages PDF, multi-asset zip, etc.): "This artifact looks substantial. Create a sidecar `.meta.md`?"

The manifest row + optional sidecar happen *in the same ingest turn* as the file move. No silent uploads.

---

## Integration with `_wiki/`

`_collections/` and `_wiki/` are complementary:

| Direction | What happens |
|-----------|--------------|
| Wiki ingest captures a local file or URL | Capture stays inside `_wiki/raw/<type>/`; the authored page lands in `_wiki/pages/` or `_wiki/source-summary/` and cites canonical data points with `builds-on:` |
| Wiki page references an existing collection artifact | Markdown link from wiki body: `see [Acme MSA](../../_collections/contracts/2026-04-08_acme-msa.pdf)` — `wiki-link-check` verifies it resolves |
| User wants the source file stored as standalone evidence | Run an explicit collection operation; add the file to `_collections/<type>/` with a manifest row, then link from the wiki page |
| Collection artifact archived | Dangling-ref scan finds wiki pages citing it → reported in collections-scan output → user decides whether to update wiki, archive wiki page, or restore artifact |
| Collections-scan finds an unlinked artifact | INFO finding can be paired with `coverage-gap` (wiki check) — "this artifact has no link from data points OR wiki — should one exist?" |

**Boundary rule:** Wiki ingest does not implicitly write to `_collections/`.
`_collections/` is for user-owned evidence with value independent of a wiki
page. `_wiki/raw/` is for source captures created by wiki workflows. If the
same file deserves both treatment paths, do them as two explicit operations so
the user can see the evidence decision.

**Naming alignment:** `_wiki/raw/<type>/` previously used `README.md` (pin-llm-wiki native). For consistency across zones, both rename to `_manifest.md`. This is a single search-and-replace in the adopted pin-llm-wiki skill.

---

## Future RAG / Vector / Knowledge-Graph Compatibility

The collections zone becomes the **evidence layer** in a future RAG/graph stack. The design choices that make it ready:

### Graph readiness

| Source | Edge type | Direction | What populates |
|--------|-----------|-----------|----------------|
| Manifest row `Related data point` column | `EVIDENCES` | artifact → data point | One per row |
| Sidecar `builds-on:` frontmatter | `EVIDENCES` | artifact → data point | One per data point |
| Manifest frontmatter `cluster:` + `related-clusters:` | `BELONGS_TO_CLUSTER` | manifest → cluster | One per cluster |
| Wiki page markdown link to artifact | `CITES_EVIDENCE` | wiki page → artifact | Resolved at lint time |
| Sidecar `key-fields:` | Node attributes | — | Searchable structured properties |

A graph generator can walk `_collections/<type>/_manifest.md` + sidecar frontmatter and emit nodes (artifacts) + edges (artifact ↔ data point ↔ cluster ↔ wiki page). Combined with the wiki graph and the data-point graph, this is one connected business-context graph.

### Retrieval readiness

For RAG over collections:

- **Binary files** (PDF, docx) need extraction at index time — but the **manifest row + sidecar `.meta.md`** are already structured retrieval targets. Retrieval can return "manifest row + sidecar key-fields" without ever opening the PDF.
- **Text files** (transcripts, exports) are directly indexable. The manifest row + filename are retrieval anchors.
- **Provenance** for any retrieved chunk: chunk → file → manifest row → cluster → data point. Always traceable.

### Embedding-update logic

- File added → embed only the manifest row + sidecar (binary) or full content + manifest row (text)
- File archived → invalidate file's embeddings; update graph edges
- Sidecar updated → re-embed sidecar; manifest row unchanged unless table changed
- Manifest schema upgrade (e.g., new column) → re-embed table only

### What's deliberately NOT pre-built

We don't add explicit chunking markers, pre-extracted PDF text, or a graph-store schema *now*. The structural choices today (one manifest per directory, sidecars with frontmatter, kebab cross-zone links) carry the cost; the retrieval/embedding layer slots in later without re-formatting.

---

## Schema and Governance

Vocabularies in `_collections/` should grow with the business, not be chiseled in stone. The collections zone exposes its vocabulary via a single registry file, **`_collections/.schema.yml`**, that drives manifest validation, lint, and tooling. Every collection sub-type, every required-column list, every naming convention lives in one place. Schema-versioned. Migrating between versions is a defined operation (parallel to `_wiki/.schema.yml` — see [`wiki-zone.md`](./wiki-zone.md) "Schema and Governance").

### `_collections/.schema.yml` registry

```yaml
schema-version: 1
last-updated: 2026-04-30
last-migrated: null

manifest-schemas:
  invoices:
    description: "Invoices issued or received"
    required-columns: [File, Client, Amount, Currency, Issued, Paid, "Related data point"]
    file-naming-convention: "YYYY-MM-DD_<client>-<descriptor>.<ext>"
  contracts:
    description: "Signed agreements (MSA, NDA, SaaS)"
    required-columns: [File, Counterparty, Type, Signed, Expires, Status, "Related data point"]
    expiry-warning-days: 30
    auto-status-transitions: true     # active → expiring-soon → expired (managed by collections-scan)
  brand-kits:
    description: "Brand asset bundles"
    required-columns: [File, Version, "Asset count", Formats, "Valid from", "Related data point"]
  call-transcripts:
    description: "Recorded customer or partner conversations"
    required-columns: [File, Date, Participants, Topics, Outcome, "Related data point"]
  statements:
    description: "Financial / system exports (Stripe, Salesforce, etc.)"
    required-columns: [File, Period, Source, "Key numbers", "Related data point"]
  reports:
    description: "Derived analytical reports (Excel/CSV/HTML produced by an internal pipeline). Often paired with a `.meta.md` sidecar carrying period, freshness window, and extracted key-fields."
    required-columns: [File, Period, "Report type", Audience, "Run date", "Related data point"]
    file-naming-convention: "YYYY-MM-DD_<report-slug>.<ext>"
  custom:
    description: "User-defined; only base validation applies"
    required-columns: [File, "Related data point"]

statuses:
  - active
  - expiring-soon                     # auto-set when within expiry-warning-days
  - expired                           # auto-set when past expires
  - archived                          # soft-deleted to .archive/
  - historical                        # kept for reference, not actively used

# Cluster vocabulary inherits from BCOS (single source of truth)
cluster-source: docs/document-index.md
allow-cluster-not-in-index: false

# What `bcos init` should scaffold in a new repo
bootstrap-defaults:
  schemas: [custom]                   # start minimal; add specific schemas as collections grow
  note: "Start minimal. Add manifest-schemas as you discover real artifact categories. The 'custom' schema covers anything that doesn't fit a registered type."
```

### Governance operations

| Command | What it does |
|---------|--------------|
| `/collection schema list` | Show current vocabulary (read-only) |
| `/collection schema add <schema-name>` | `AskUserQuestion`-driven: add manifest-schema with required-columns, naming-convention, optional expiry semantics |
| `/collection schema rename <from> <to>` | Migrate every manifest declaring `manifest-schema: <from>`; record in collections log |
| `/collection schema retire <schema-name>` | Mark deprecated; lint existing manifests with migration hint |
| `/collection schema validate` | Walk every `_manifest.md`; verify columns and statuses against schema |
| `/collection schema migrate <from> <to>` | Versioned migration with dry-run diff |

### Bootstrap behavior on `bcos init` in a new repo

- `_collections/.schema.yml` is scaffolded with **only the `custom` schema** — no upfront speculation about whether the user will have invoices, contracts, etc.
- First time `context-ingest` Path 5 routes to a new collection sub-type, it offers `AskUserQuestion`: *"This collection looks like contracts. Add `contracts` as a registered manifest-schema, or use `custom`?"*
- Real-usage drives schema growth.

### Same pattern across BCOS

The schema-driven principle applies symmetrically:
- **`_wiki/.schema.yml`** — page-types, statuses, detail-levels, provenance-kinds, forbidden-builds-on-paths
- **`_collections/.schema.yml`** — manifest-schemas, statuses, cluster-source
- **`.claude/quality/lint-checks.json`** — registry of lint check IDs
- **`.claude/quality/schedule-config.json`** — scheduled jobs with required `_about` field

The principle: **adding a category should be one edit, not five.**

---

## Distinctions — Quick Reference

| Looks like… | But is actually… | Decision rule |
|-------------|------------------|---------------|
| A wiki page | A sidecar | Does it sit next to a binary file with the same root? Sidecar. |
| A sidecar | A wiki page | Does it explain how to do something? Wiki. Does it just summarize one artifact's contents? Sidecar. |
| A data point | A sidecar | Does it assert canonical truth about the business? Data point. Is it derivative of one specific artifact? Sidecar. |
| A manifest | An index | Is it required and machine-validated? Manifest. Is it optional and human-curated? Index. (Manifests subsume the prior optional `_index.md` concept.) |
| `_collections/` | `_inbox/` | Is the file the truth (artifact)? Collections. Is it raw text awaiting triage? Inbox. |
| `_collections/` | `_wiki/raw/` | Is it user-uploaded evidence? Collections. Is it bot-generated capture (URL fetch)? Wiki raw. (Both use `_manifest.md`.) |

---

## Adoption Plan

**1. Documentation updates**
- ✅ `CLAUDE.md` — `_collections/` row updated to flag manifest requirement *(this turn)*
- ✅ `folder-conventions.md` — `_collections/` row updated to mention manifest *(this turn)*
- ✅ `content-routing.md` Path 5 — promote `_index.md` from optional to required, rename to `_manifest.md`, add expiry/sidecar fields *(this turn)*
- This document (`collections-zone.md`) becomes the authoritative reference

**2. Schema templates** (next concrete step):
- `templates/_manifest.md.tmpl` (per `manifest-schema`: contracts, invoices, brand-kits, call-transcripts, statements, custom)
- `templates/<artifact>.meta.md.tmpl` (sidecar template)

**3. Lint script:**
- `.claude/scripts/collections_scan.py` — implements the 10 checks above
- Wired into `.claude/quality/schedule-config.json` per the JSON above
- Returns findings in the standard dispatcher format

**4. `context-ingest` extension:**
- Path 5 routing learns the new `AskUserQuestion`-driven manifest-row authoring
- Filename-convention nudge becomes a structured option

**5. Wake-up generator extension:**
- `generate_wakeup_context.py` reads each `_manifest.md` frontmatter
- Emits one-line collection summary in the wake-up snapshot

**6. Daydream extension:**
- Quarterly coverage audit added to `daydream` skill or as standalone `collections-coverage` job

**7. `_wiki/` zone alignment:**
- Rename `_wiki/raw/<type>/README.md` → `_wiki/raw/<type>/_manifest.md` for cross-zone consistency
- Update `wiki-zone.md` adoption plan with this rename

**Out of scope for v1:**
- PDF text extraction at scan time (deferred to RAG layer)
- Auto-population of sidecar `key-fields` via LLM extraction (manual/prompted only)
- Graph export to vector store (deferred to RAG layer)

---

## See Also

- [`wiki-zone.md`](./wiki-zone.md) — sibling zone for derivative explanatory content
- [`content-routing.md`](./content-routing.md) — Path 5 (Collection) routing mechanics
- [`system-design.md`](./system-design.md) — Why zones exist
- [`../guides/folder-conventions.md`](../guides/folder-conventions.md) — Folder-level rules across all zones
- pin-llm-wiki upstream — `https://github.com/ndjordjevic/pin-llm-wiki` (origin of the manifest + soft-delete + dangling-ref-scan patterns)

---

**Status:** v2 design — schema-governance layer added; ready for template + script scaffolding.
**Created:** 2026-04-30
**Last Updated:** 2026-05-04
**Version:** 2.0.1
