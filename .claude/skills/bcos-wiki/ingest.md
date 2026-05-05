# ingest — shared ingest pipeline (called by run / promote / create / refresh)

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

This file is the **internal contract** every entry point converges on after fetching/copying raw content. It is not a user-facing subcommand. `run`, `promote`, `create`, and `refresh` all call this file with a populated context dict.

---

## Inputs (caller-supplied context)

| Variable | Type | Notes |
|---|---|---|
| `slug` | string | Source identifier (e.g. `langchain-ai-langchain`, `docs.langchain.com`, `acme-onboarding-notes`). For multi-product source-summary, this is the **umbrella** slug. |
| `source_type` | enum | `web` \| `github` \| `youtube` \| `local` |
| `raw_path` | path | `docs/_wiki/raw/<type>/<slug>.md` (text) or `docs/_wiki/raw/local/<slug>.<ext>` (binary, Path B) |
| `effective_detail_level` | enum | `brief` \| `standard` \| `deep` |
| `today` | ISO date | `YYYY-MM-DD` |
| `companion_slug` | string \| null | `<org>-<repo>` if a web source has a companion GitHub repo (Path A only); else null |
| `companion_raw_path` | path \| null | `docs/_wiki/raw/github/<companion_slug>.md` if companion fetch succeeded |
| `products` | list | `[{name, slug, deep_link_url?, docs_url?, repo_url?}]` returned by web fetch step 5; ≥2 entries triggers the multi-product branch. `[]` for single-product, `null` for non-web. |
| `provenance` | dict | For Path B: `{kind, source_path, captured_on, promoted_by, notes?}`. For Path A: `{kind: "url-fetch", source: <url>, captured_on}`. |
| `page_type` | string | The `page-type:` to write into frontmatter. For Path A: always `source-summary`. For Path B: chosen by user via `AskUserQuestion` in `promote.md`/`create.md` (default `how-to`). |
| `cluster` | string | Required by BCOS frontmatter. For Path B: chosen by user. For Path A: derived (see Step 2b). |

---

## Step 1 — Read raw content

Read `raw_path` fully. If `companion_raw_path` is non-null, read that too.

In **deep multi-product mode** (Path A only — `products` ≥2), confirm the raw web file contains a `## Product: <Name>` section per product before continuing. If mismatched, abort and ask the human to re-fetch.

---

## Step 2 — Branch on shape

| Shape | Trigger | Output file count |
|---|---|---|
| **Standalone** | `companion_slug` is null AND `products` is null/empty | one page |
| **Unified web+github** | `source_type=web` AND `companion_slug` is non-null AND `products` is null/empty | one page (with `companion-urls:` + `raw-files:`) |
| **Multi-product umbrella** | `source_type=web` AND `effective_detail_level=deep` AND `products` ≥2 | umbrella + one sub per product |
| **Path B (any local)** | `source_type=local` | one page (always standalone-like) |

**Standalone / Unified / Path B:** continue with **Step 2a** (single page).
**Multi-product:** continue with **Step 2c** (umbrella + subs). Skip 2a/2b.

---

## Step 2a — Write a single page (standalone / unified / Path B)

Determine target file path:

- Path A `source-summary`: `docs/_wiki/source-summary/<slug>.md`
- Path B (any non-source-summary page-type): `docs/_wiki/pages/<slug>.md`
- Path B with `page-type: source-summary` is rare but allowed: `docs/_wiki/source-summary/<slug>.md`

### Frontmatter

```yaml
---
# BCOS-required (per docs/_bcos-framework/architecture/metadata-system.md)
name: "{{NAME}}"                           # human title (from raw, or user-provided for Path B)
type: wiki
cluster: "{{CLUSTER}}"
version: 1.0.0
status: active
created: {{TODAY}}
last-updated: {{TODAY}}

# Ownership (Level 1 minimum)
domain: "{{DOMAIN_ONELINE}}"
exclusively-owns:
  - {{...derive from content...}}
strictly-avoids: []

# Wiki extensions
page-type: {{PAGE_TYPE}}
last-reviewed: {{TODAY}}

# Relationships (D-04 reference-format rule)
builds-on:                                 # cross-zone: paths with .md
  - ../{{...data-point.md...}}             # ONLY if page-type's required-fields includes builds-on
references: []                             # intra-zone: bare slugs (no .md)
provides: []

# Provenance (always present)
provenance:
  kind: {{provenance.kind}}                # url-fetch | inbox-promotion | local-document
  source: {{provenance.source}}             # URL or local source-path
  captured-on: {{provenance.captured_on}}
{{...promoted-by, notes... if Path B...}}

# Source-summary shape discriminators (ONLY when page-type: source-summary)
{{IF SHAPE = standalone}}
source-url: {{...}}
detail-level: {{effective_detail_level}}
last-fetched: {{TODAY}}

{{IF SHAPE = unified web+github}}
source-url: {{web URL}}
companion-urls:
  - https://github.com/{{org}}/{{repo}}
raw-files:                                 # cross-zone: paths with .md (D-04)
  - ../raw/web/{{slug}}.md
  - ../raw/github/{{companion_slug}}.md
detail-level: {{effective_detail_level}}
last-fetched: {{TODAY}}
---
```

**Update vs create:** if `<target>.md` exists, preserve `created`, `tags`-ish fields the user added, and `references` (peer cross-refs); always overwrite `last-updated`, `last-fetched`, `detail-level`. Ingest must NOT clobber human-curated `references` or `builds-on`.

### Body structure

1. Summary paragraph (1–3 sentences) — what the source is and why it matters in this domain.
2. Banner citation immediately after summary:
   - For `source-summary` standalone: `_All claims below are sourced from `../raw/<type>/<slug>.md` unless otherwise noted._`
   - For `source-summary` unified: same banner pointing to **the web raw file**; inline `(../raw/github/<companion_slug>.md)` on github-derived paragraphs.
   - For Path B page-types (how-to/runbook/post-mortem/etc.): `_Canonical knowledge: [[<builds-on-slug-1>]] | [[<builds-on-slug-2>]] — see those for the source of truth._`
3. Sectioned body — one of these per page-type:

| `page-type` | Required H2 sections (in order) |
|---|---|
| `how-to` | `## What this covers` · `## Steps` · `## Pitfalls` · `## Related` |
| `glossary` | `## Terms` (alphabetical definition list — `**Term** — definition`) |
| `runbook` | `## When to run this` · `## Procedure` · `## Verification` · `## Rollback` |
| `post-mortem` | `## Summary` · `## Timeline` · `## Root cause` · `## What we did` · `## What we learned` |
| `decision-log` | `## Decision` · `## Context` · `## Alternatives considered` · `## Why this one` · `## Reversibility` |
| `faq` | `## Questions` (each Q as `### Q: ...`, then plain-text answer) |
| `source-summary` (web/github standalone) | `## What it does` · `## Key features` · `## Architecture & concepts` · `## Main APIs` · `## When to use` · `## Ecosystem` |
| `source-summary` (youtube standalone) | `## What this video covers` · `## Key points by chapter` · `## Notable quotes` · `## Speaker context` |
| `source-summary` (unified web+github) | `## What it does` (web) · `## Key features` (web+github) · `## Architecture` (github) · `## Installation` (github) · `## Example usage` (github) · `## When to use` (web) · `## Maintenance status` (github) · `## Ecosystem` (web) |

For Path B local-document (`page-type: source-summary`): use the standalone web/github layout, citing `../raw/local/<slug>.md` in the banner.

### Formatting rules

- **No H1** in the body. Filename = title.
- **No `---` horizontal rules** between body sections (the only `---` are the YAML frontmatter delimiters).
- Per-paragraph inline citations only when a paragraph cites a **secondary** raw file (not the banner-cited primary).

### Tags & related (`references` field)

`references:` lists slugs (no `.md`, per D-04) of existing wiki pages with substantial conceptual overlap. Read each candidate's summary paragraph to judge overlap. Casual mentions don't count.

**Bidirectional update:** for every slug `Y` you add to this page's `references`, also append this page's slug to `Y`'s `references` list. Update `Y`'s `last-updated` to today. Without this, references drift one-way.

After 2a, continue with **Step 2b** (cluster/product grouping), then **Step 4**.

---

## Step 2b — Cluster grouping (single-page flows only)

This step assigns `cluster:` for **Path A** when no caller override is given. Path B always uses the user-provided cluster.

Heuristic, in order:
1. If a unified or umbrella page is being written and a partner (web↔github) page already exists with `cluster: X`, use `X`.
2. If `_wiki/.schema.yml` `clusters.allow-cluster-not-in-source: false`, the cluster MUST exist in `docs/document-index.md`. Pick the closest match by token overlap with the page name; if no candidate >0.4 score, ask the user via `AskUserQuestion` (offering existing clusters as options).
3. Otherwise, derive a cluster slug from the source's domain or repo name (e.g. `langchain.com` → `LangChain`, `langchain-ai-langchain` → `LangChain`).

If clusters were grouped (e.g. web partner found existing github partner), update **both** pages' `cluster` to match. Note the grouping in the post-ingest report so the human can verify.

---

## Step 2c — Multi-product (umbrella + subs)

(Path A web `deep` mode with `products` ≥2.)

### 2c.1 — Resolve sub slugs

For each `p` in `products`: `sub_slug = "<slug>-<p.slug>"`. Sub source URL = `p.deep_link_url` if non-null else the umbrella URL.

### 2c.2 — Umbrella page

Path: `docs/_wiki/source-summary/<slug>.md`

Frontmatter additions over Step 2a:

```yaml
subpages:                                  # bare slugs (D-04 intra-zone)
  - {{slug}}-{{p1.slug}}
  - {{slug}}-{{p2.slug}}
```

Omit `companion-urls` and `raw-files`. Body is a hub:

```
<Summary>

_All claims below are sourced from `../raw/web/<slug>.md` unless otherwise noted._

## Products
- [[{{slug}}-{{p1.slug}}]] — <one-sentence what-it-is>
- [[{{slug}}-{{p2.slug}}]] — <one-sentence what-it-is>

## Architecture
<optional — how products fit together>

## When to use the platform
<operator-facing, banner-covered>

## Documentation
<docs structure summary>
```

The umbrella is a hub; details live on subs.

### 2c.3 — Each sub page

Path: `docs/_wiki/source-summary/<slug>-<p.slug>.md`

Frontmatter additions:

```yaml
parent-slug: {{slug}}                      # bare slug (D-04)
source-url: {{p.deep_link_url or umbrella URL}}
detail-level: deep
last-fetched: {{TODAY}}
```

Omit `subpages`, `companion-urls`, `raw-files`.

Body uses the standalone web/product layout, banner-citing the **same** raw file as the umbrella (`../raw/web/<slug>.md`). Subs share one raw file with the umbrella by design — that's the explicit constraint of multi-product deep mode.

### 2c.4 — Tags & references across the family

- Umbrella `references:` describes the platform's relationships to **non-family** wiki pages.
- Each sub's `references:` may include sibling sub slugs only on real functional dependency. Default empty.
- Bidirectional rule still applies for cross-family references.

---

## Step 3 — Do NOT create extra cross-source pages

`overview.md` is the **only** cross-source page. Ingest writes source/internal pages plus appends to `overview.md` (Step 5). No other synthesis pages.

In multi-product flow, the umbrella + subs are all source pages even though one ingest produced them.

---

## Step 4 — Update `index.md` (DERIVED — call the script)

`docs/_wiki/index.md` is a derived artifact (D-11). After writing source pages:

```
python .claude/scripts/refresh_wiki_index.py
```

Capture the script's summary line for the post-ingest report. Do not hand-edit `index.md`.

---

## Step 5 — Update `overview.md`

Read `docs/_wiki/overview.md`. The body invariant is **one paragraph per `sources:` entry, in order** (`len(sources) == paragraph_count`).

For each new slug to add (umbrella + each sub for multi-product; just `<slug>` otherwise):

- If `[[<slug>]]` already in `sources:` → refresh path: bump `updated:` only; don't add a paragraph.
- If `sources:` empty → replace placeholder body with an opening paragraph describing what this source covers and what it contributes. Cite `[[<slug>]]`. Update `sources:` frontmatter to `sources: ["[[<slug>]]"]`.
- Otherwise → append a new dedicated paragraph at the end. Don't merge into existing paragraphs. Cite `[[<slug>]]` at least once. Append `  - "[[<slug>]]"` to the `sources:` list.

Rules:
- Don't reference unrelated sources by default. Only mention another `[[page]]` when there's substantial overlap, direct product relationship, or specific conflict/comparison that helps the reader.
- For multi-product, the umbrella's paragraph may wikilink each sub via `[[<umbrella>-<product>]]`; sub paragraphs link back to `[[<umbrella>]]`.

**Sanity check** before write: post-edit body paragraph count MUST equal `len(sources)`. If it doesn't, fix it before writing.

Update `last-updated:` frontmatter on `overview.md`. Write.

---

## Step 6 — Append to `log.md`

Read `docs/_wiki/log.md`. Insert below frontmatter and the `# ... — log` heading (newest at top):

**Standalone / unified:**
```
## {{TODAY}} | ingest | {{slug}} | <one-line summary>

- Created: docs/_wiki/{pages|source-summary}/{{slug}}.md
- Updated: docs/_wiki/overview.md, docs/_wiki/log.md, docs/_wiki/index.md (regenerated)
{{IF unified}}
- Companion raw: docs/_wiki/raw/github/{{companion_slug}}.md
{{IF Path B}}
- Provenance: {{provenance.kind}} from {{provenance.source}}
```

**Multi-product:**
```
## {{TODAY}} | ingest | {{slug}} | multi-product (<N> products): <comma-separated names>

- Created: docs/_wiki/source-summary/{{slug}}.md, docs/_wiki/source-summary/{{slug}}-{{p1}}.md, ...
- Updated: docs/_wiki/overview.md, docs/_wiki/log.md, docs/_wiki/index.md (regenerated)
```

Write.

---

## Step 7 — Move queue line (Path A only)

For Path A, after a successful ingest:
1. Read `docs/_wiki/queue.md`.
2. Locate the URL's line under `## Pending`.
3. Append `<!-- ingested {{TODAY}} -->`.
4. If `auto_mark_complete: true`, flip `[ ]` → `[x]`.
5. Move the line from `## Pending` to the bottom of `## Completed`.
6. Write.

For Path B, there is no queue. Provenance lives in the page frontmatter (Step 2a).

---

## Step 8 — Post-ingest lint (config-driven)

Read `auto_lint` from `.config.yml`:
- `batch` → caller (`run.md`) handles the post-batch lint; this step is a no-op
- `per-ingest` → run `lint.md`; surface findings in the report
- `never` → skip

Single-source `run <url>`, `promote`, `create` always trigger `per-ingest` semantics if not `never`.

---

## Step 9 — Hook validation

Run the frontmatter hook against every newly-written page (the hook fires automatically on Edit/Write, but a manual sanity-check catches malformed templates). If the hook reports `schema-violation`, `reference-format-mismatch`, `forbidden-builds-on-target`, or `provenance-required`, surface those in the post-ingest report — they indicate either a template bug or a user-supplied frontmatter problem.

---

## Step 10 — Git

No agent commits. See SKILL.md Git policy.

---

## Output report (caller surfaces this to user)

```
Ingested: <slug>

  Type:        {{source_type}}
  Page-type:   {{page_type}}
  Cluster:     {{cluster}}
  Slug:        {{slug}}
  Raw:         {{raw_path}}
  Wiki page:   docs/_wiki/{pages|source-summary}/{{slug}}.md
  Detail:      {{effective_detail_level}}
  {{IF companion}}
  Companion:   docs/_wiki/raw/github/{{companion_slug}}.md
  {{IF multi-product}}
  Products:    {{p1.name}}, {{p2.name}}, ...
  Sub-pages:   docs/_wiki/source-summary/{{slug}}-{{p1.slug}}.md, ...
  {{IF Path B}}
  Provenance:  {{provenance.kind}} ← {{provenance.source}}

Updated: docs/_wiki/index.md (regenerated), overview.md, log.md, queue.md{{IF Path A}}
{{IF lint findings}}
Lint:    <N ERROR, N WARN, N INFO — see report below>
{{ELSE}}
Lint:    clean
```

Caller may suggest commit message: `wiki: ingest <slug>`. Caller never commits.
