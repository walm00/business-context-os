# Document Standards

**The minimum quality bar for every document in your context architecture.**

---

## What Counts as a "Document"

CLEAR Context OS manages any document that represents organizational knowledge. Not just brand or strategy -- anything your team needs to stay aligned on.

### Document Types

| Type | What It Is | Examples |
|------|-----------|---------|
| **context** | Business knowledge with clear ownership | Company identity, value proposition, investor narrative, competitive positioning, team structure, market context |
| **process** | How something is done (SOPs, workflows) | Employee onboarding, sales handoff, content approval, board reporting, vendor evaluation, release process |
| **policy** | Rules and decisions that govern behavior | Data handling, pricing rules, expense approval, hiring criteria, brand usage, IP protection |
| **reference** | Lookup information that rarely changes | Glossary, tool inventory, vendor contacts, org chart, key metrics definitions, tech stack |
| **playbook** | Decision guides for recurring situations | Crisis comms, fundraising, product launch, competitive response, market entry, M&A integration |
| **wiki** | Explanatory or source-summary page in `docs/_wiki/` | How-to pages, glossaries, decision logs, post-mortems, source summaries |

All types follow the same metadata standard and quality bar. The ownership specification (DOMAIN, EXCLUSIVELY_OWNS, etc.) applies to all of them -- a process document needs clear boundaries just as much as a brand guide does.

`type: wiki` documents are governed by the wiki-zone extension, not the normal flat active-doc model. Use `docs/_bcos-framework/architecture/wiki-zone.md` and `docs/_wiki/.schema.yml` for page-type-specific rules.

---

## Metadata Standard (YAML Frontmatter)

Every managed document MUST have a YAML frontmatter header. This is the machine-readable metadata that enables auditing, tracking, and discovery.

### Required Fields

```yaml
---
name: "Document Name"
type: context                   # context | process | policy | reference | playbook | wiki
cluster: "Parent Cluster"       # Which cluster this belongs to
version: "1.0.0"               # Semantic versioning: major.minor.patch
status: active                  # draft | active | under-review | archived
created: "2026-04-05"          # ISO date, set once, NEVER change
last-updated: "2026-04-05"     # ISO date, MUST update on every change
---
```

### Optional Fields

```yaml
---
# ... required fields above ...
tags: [brand, messaging, external]    # Expected for search and filtering; warning-only if absent
review-cycle: monthly                  # weekly | monthly | quarterly | annual | trigger-based
last-reviewed: "2026-05-05"           # Last validation check, even when content did not change
next-review: "2026-05-05"             # When the next review is due
depends-on: [brand-identity]          # Documents this one requires as input
consumed-by: [messaging-framework]    # Documents that use this one as input
source: "https://..."                 # Original source if migrated from elsewhere
confidentiality: internal             # public | internal | confidential | restricted
---
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable document name |
| `type` | Yes | Document classification (see types above) |
| `cluster` | Yes | Parent cluster for grouping |
| `version` | Yes | Semantic version. Bump on every change (see versioning rules) |
| `status` | Yes | Lifecycle state (see status definitions below) |
| `created` | Yes | Date document was first created. Set once, never change. |
| `last-updated` | Yes | Date content was last changed. MUST update on every edit. |
| `tags` | No | Free-form labels for discovery and filtering. Expected on managed docs and wiki pages; missing tags are warning-only during adoption. |
| `review-cycle` | No | How often this should be reviewed |
| `last-reviewed` | No | Last date the doc was checked and confirmed. This is not the same as `last-updated`; review can happen without content changes. Expected when `review-cycle` exists. |
| `next-review` | No | Specific date for next scheduled review |
| `depends-on` | No | Upstream documents (maps to BUILDS_ON in ownership spec) |
| `consumed-by` | No | Downstream documents (maps to PROVIDES in ownership spec) |
| `source` | No | Where the original content came from |
| `confidentiality` | No | Access level classification |

Wiki-zone pages add fields such as `page-type`, `domain`, `exclusively-owns`, `builds-on`, `references`, `last-reviewed`, and source-summary provenance fields. Source summaries also keep `last-fetched`; that records source refresh, while `last-reviewed` records validation of the authored summary. The authoritative list lives in `docs/_wiki/.schema.yml`; the framework fallback template is `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl`.

### Mechanical Index Facets

The canonical context index derives fields from the path so authors do not duplicate them in frontmatter:

| Derived field | Meaning |
|---------------|---------|
| `zone` | Active, wiki, collection-manifest, inbox, planned, archive, framework, generated, or custom opt-out |
| `bucket` | Lifecycle bucket used by Atlas/Galaxy: `active`, `_inbox`, `_planned`, `_archive`, `_bcos-framework`, `_collections` |
| `folder` | Parent path of the file |
| `path-tags` | Folder components used as searchable facets |
| `trust-level` | Derived trust class such as high, high-derived, future, historical, low, system, or evidence |

These fields are emitted by `.claude/scripts/context_index.py` into `.claude/quality/context-index.json` and rendered into `docs/document-index.md`. Do not hand-maintain them in YAML.

### Mandatory Refinement Step

**Every time you update a document, you MUST:**

1. Update `last-updated` to today's date
2. Bump the `version` number (at least patch: x.x.+1)
3. Never touch `created` -- it's immutable history

### Status Definitions

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `draft` | In progress, not yet reliable | New documents being written, content being refined |
| `active` | Current, accurate, trustworthy | The default state for maintained docs. This IS reality today. |
| `under-review` | Flagged for accuracy check | When a trigger event occurs or staleness detected |
| `archived` | No longer current but preserved | Superseded docs. Never delete -- archive instead. |

### Document Locations (The Folder Structure)

**The folder a document lives in tells Claude what it IS before the file is even opened.** This is the primary signal — more reliable than metadata fields because it's visible in every glob, grep, and file listing.

```
docs/
├── *.md                    # ACTIVE CONTEXT — current reality, act on it
├── _inbox/                 # RAW MATERIAL — meeting notes, brain dumps, unprocessed
├── _planned/               # POLISHED IDEAS — documented but not yet real, may never be
├── _archive/               # SUPERSEDED — was real once, kept for reference
├── _collections/           # MANAGED MATERIALS — binary/local assets with manifests
├── _wiki/                  # EXPLANATORY LAYER — wiki pages, source summaries, raw captures
├── table-of-context.md     # Synthesis layer (stable, monthly)
├── current-state.md        # Operations layer (fluid, weekly)
└── document-index.md       # Auto-generated inventory
```

| Folder | What lives here | Quality bar | Claude should... |
|--------|----------------|-------------|-----------------|
| `docs/*.md` | Active context — current business reality | Full CLEAR compliance | Trust and act on this content |
| `docs/_inbox/` | Raw dumps — meeting notes, transcripts, pasted content | None (no frontmatter required) | Process via `context-ingest`, not reference directly |
| `docs/_planned/` | Polished ideas — defined concepts that may or may not happen | Frontmatter recommended, linking optional | Read but NOT treat as current reality |
| `docs/_archive/` | Superseded docs — no longer current | As-was when archived | Reference for history only, not as current truth |
| `docs/_collections/` | Managed binary/material collections | Manifest-driven, collection-specific | Treat manifests as authoritative, not binary filenames alone |
| `docs/_wiki/pages/` | Wiki explainers | Wiki frontmatter schema + ownership fields | Use as high-trust explanatory context built on data points |
| `docs/_wiki/source-summary/` | Source summaries | Wiki source-summary schema | Use as high-trust summaries of captured sources |
| `docs/_wiki/raw/`, `queue.md`, `index.md`, `log.md` | Source captures and mechanical artifacts | Managed by `bcos-wiki` | Do not edit as canonical business truth |

**Why folders instead of a status field?** When Claude searches for "pricing" and finds `docs/_planned/enterprise-pricing.md`, the path itself signals "this is an idea, not reality" — before the file is even opened. A status field buried in YAML frontmatter is easy to miss after the content is already in context.

**Moving documents between folders:**
- `_inbox/ → docs/` — raw material refined into active context (via `context-ingest`)
- `_inbox/ → _planned/` — raw idea polished into a documented concept
- `_planned/ → docs/` — idea becomes reality (build full relationships and ownership spec)
- `docs/ → _archive/` — superseded by newer version or no longer relevant
- `_inbox/ → _wiki/pages/` — raw material promoted into an explanatory wiki page via `/wiki promote`
- URL/local source → `_wiki/source-summary/` plus `_wiki/raw/` — source captured and summarized via `/wiki create` or `/wiki run`

**Wiki-zone exception to flat active docs:** normal active data points stay flat under `docs/*.md`, but `docs/_wiki/` intentionally uses semantic subfolders. `docs/_wiki/pages/` and `docs/_wiki/source-summary/` are governed by `docs/_bcos-framework/architecture/wiki-zone.md`; `docs/_wiki/source-summary/` is the authorized exception to the flat active-doc folder rule.

---

## Minimum Quality Bar

Every document must meet these checks to be considered healthy. This is what `context-audit` and `doc-lint` verify.

### Level 1: Exists and Is Findable

- [ ] Has YAML frontmatter with all required fields
- [ ] Lives in the correct cluster directory
- [ ] Is listed in the Document Index (if one exists)
- [ ] Filename matches content (kebab-case, descriptive)

### Level 2: Has Clear Ownership

- [ ] Has an Ownership Specification section with DOMAIN and EXCLUSIVELY_OWNS at minimum
- [ ] DOMAIN is a clear, one-sentence scope statement
- [ ] EXCLUSIVELY_OWNS lists at least 3 specific items

### Level 3: Is Bounded

- [ ] STRICTLY_AVOIDS lists what belongs elsewhere (with cross-references)
- [ ] No content duplicated from another document
- [ ] Cross-references use linking, not copying

### Level 4: Is Current

- [ ] `last-updated` is recent relative to review cycle
- [ ] `status` accurately reflects the document's state
- [ ] Content matches current business reality
- [ ] No stale references to things that have changed

### Level 5: Is Connected

- [ ] BUILDS_ON / REFERENCES / PROVIDES relationships are documented
- [ ] `depends-on` and `consumed-by` in frontmatter match ownership spec
- [ ] Cross-references to other documents resolve (no broken links)

**Minimum to be "active":** Levels 1-3 must pass. Levels 4-5 are the ongoing maintenance standard.

**Documents in `docs/_planned/`** should have frontmatter but get relaxed rules: staleness threshold is 180 days (vs 90 for active), incomplete cross-references are informational (not errors), and linking is optional until promoted to active.

**Documents in `docs/_inbox/`** don't need to meet any quality bar. They're raw material waiting to be processed by `context-ingest`. No frontmatter required.

**Documents in `docs/_wiki/pages/` and `docs/_wiki/source-summary/`** must satisfy wiki-zone schema rules instead of the standard active-doc template. They still need clear ownership, bounded relationships, and current metadata, but their source-of-authority relationship is expressed with `builds-on:` and source provenance rather than by duplicating canonical data-point content.

---

## The Golden Rule: Consolidate, Don't Carelessly Delete

**When auditing or refining, the goal is clean, authoritative documents -- not cluttered ones.**

| If you find... | Do this |
|----------------|---------|
| **Duplicated content** | Identify the owning document. Merge the best version there. Remove the duplicate from the other document and replace with a cross-reference. |
| **Outdated information** | Update it. If the old version matters for history, note the change in a brief changelog at the bottom -- but don't leave stale content inline. Keep active docs clean. |
| **Wrong information** | Fix it. Set `status: under-review` if you're unsure of the correct version. Escalate to the owner. |
| **Irrelevant content** | Move it to the document that OWNS that topic. If no owner exists, create one or remove it. |
| **Contradictory content** | Figure out which version is correct. Consolidate into the owning document. Remove the contradiction from the other. |

**The principle:** Place content where it belongs, then clean up. Don't leave duplicates "just in case." Don't clutter active documents with archived sections and old versions. Git history exists for a reason.

**What "don't carelessly delete" means:** Before removing a paragraph, make sure the information lives somewhere authoritative. Merge first, then remove the duplicate. The goal is one clean source of truth, not two messy ones.

**Changelog (optional, lightweight):** If a document needs change history, add a brief section at the bottom:

```markdown
## Changelog

- **1.2.0** (2026-04-05) - Consolidated audience segments from old marketing deck
- **1.1.0** (2026-03-15) - Added secondary audience definition
- **1.0.0** (2026-02-01) - Initial version
```

Keep it short. Three to five recent entries. Not a full git log.

---

## Ownership Disputes

When two people or documents claim the same content:

1. **Check the specs.** Read both EXCLUSIVELY_OWNS sections. Usually the answer is already there — one document owns the concept, the other should reference it.
2. **If genuinely ambiguous:** the architecture owner (whoever maintains the Document Index) decides. Their decision is documented by updating both ownership specs.
3. **If no architecture owner exists:** the person who created the data point first is the default owner. The other party splits out their distinct angle into a separate data point with clear boundaries.

The goal is not to prevent disagreement — it's to resolve it in the ownership spec so the same question never comes up twice.

---

## Ownership Specification Format

The ownership spec is the heart of every document. It prevents overlap and drift.

**Required for all document types** (context, process, policy, reference, playbook):

```markdown
## Ownership Specification

**DOMAIN:** [One sentence: what this document covers]

**EXCLUSIVELY_OWNS:**
- [Item 1: something ONLY this document contains]
- [Item 2]
- [Item 3]

**STRICTLY_AVOIDS:**
- [Item that belongs to another document] (see: [other-document])
- [Item that belongs elsewhere] (see: [which-document])
```

**Recommended (add when relationships emerge):**

```markdown
**BUILDS_ON:**
- [upstream-document]: [what it provides to this document]

**REFERENCES:**
- [related-document]: [what this document looks up but doesn't modify]

**PROVIDES:**
- [what this document outputs] -> [downstream-document]
```

### Ownership Spec for Process Documents

Process documents (SOPs, workflows) use the same format but with process-specific content:

```markdown
## Ownership Specification

**DOMAIN:** The content approval workflow from draft submission through final publication.

**EXCLUSIVELY_OWNS:**
- Step-by-step approval process
- Role responsibilities at each step
- Escalation paths and timelines
- Approval criteria and quality gates
- Template links for each stage

**STRICTLY_AVOIDS:**
- Content creation guidelines (see: content-standards)
- Brand voice rules (see: brand-voice)
- Publishing tool documentation (see: tool-reference)
- Legal review requirements (see: legal-compliance-policy)
```

---

## What Gets Audited

When `context-audit` runs, it checks every managed document against this standard:

### Metadata Checks
- All required frontmatter fields present and non-empty
- `status` is a valid value
- `type` is a valid value
- `version` follows semantic versioning format
- `created` is present and immutable (never changed after creation)
- `last-updated` is recent relative to review cycle

### Ownership Checks
- DOMAIN exists and is a clear statement
- EXCLUSIVELY_OWNS has at least 3 items
- STRICTLY_AVOIDS exists and references other documents
- No two documents have overlapping EXCLUSIVELY_OWNS items

### Content Checks
- No duplicated content between documents (same paragraph in two places)
- Cross-references use `(see: document-name)` format, not copy-paste
- Archived documents have `status: archived`, not just abandoned

### Relationship Checks
- All documents referenced in BUILDS_ON / REFERENCES / PROVIDES exist
- `depends-on` and `consumed-by` frontmatter matches ownership spec
- No circular dependencies
- No orphan documents (not referenced by anything and not a top-level entry point)

---

## Versioning Rules

Use semantic versioning for documents:

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Typo fix, formatting | Patch (x.x.**1**) | 1.0.0 -> 1.0.1 |
| New content added, section expanded | Minor (x.**1**.0) | 1.0.1 -> 1.1.0 |
| Major restructure, ownership boundary change | Major (**2**.0.0) | 1.1.0 -> 2.0.0 |

**Every edit = update `last-updated` + bump `version`. No exceptions.**

Never touch `created`. It's the document's birth certificate.

---

## Quick Reference

**Creating a new document:**
1. Copy the appropriate template from `docs/templates/`
2. Fill in all required frontmatter fields (`created` = today)
3. Write DOMAIN and EXCLUSIVELY_OWNS at minimum
4. Add STRICTLY_AVOIDS to prevent future overlap
5. Set `status: draft` until content is complete
6. Change to `status: active` when ready for use
7. If it's a polished idea/plan that may not happen yet — put it in `docs/_planned/` instead of root `docs/`

**Updating an existing document:**
1. Make your changes
2. Update `last-updated` to today
3. Bump `version` (at least patch: x.x.+1)
4. Check that your changes don't violate EXCLUSIVELY_OWNS boundaries
5. Never touch `created`

**Reviewing an existing document:**
1. Check `last-updated` -- how old is it?
2. Read the content -- still accurate?
3. Check cross-references -- still resolve?
4. Check EXCLUSIVELY_OWNS -- still correct boundaries?
5. If you made changes: update `last-updated` + bump version
6. If nothing changed: no metadata update needed
