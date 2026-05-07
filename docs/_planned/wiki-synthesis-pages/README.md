---
name: "Wiki Synthesis Pages — Deferral Decision"
type: orientation
cluster: "Framework Evolution"
version: 0.1.0
status: planned
created: 2026-05-06
last-updated: 2026-05-06
authority-docs:
  - .claude/quality/sessions/20260506_100433_wiki-authority-temporal/plan-manifest.json
  - docs/_bcos-framework/architecture/wiki-zone.md
follows-up-on: docs/_planned/wiki-authority-temporal/
---

# Wiki Synthesis Pages — Deferral Decision

## What this would be

A new wiki page-type — `synthesis` — for persisting Q&A answers as permanent,
citable wiki pages with explicit provenance.

Inspired by `6eanut/llm-wiki`'s synthesis pattern (Karpathy's "wiki as
compounding artifact" idea): when a user asks a question, the LLM searches
the wiki, reads relevant pages, synthesizes an answer, and the answer
itself can be filed back as a new wiki page that other queries can build
on. Closes the compounding loop — exploratory queries become persistent
knowledge.

Concrete shape (if it ships):

```yaml
---
name: "Why we picked Postgres over Mongo (synthesis 2026-04)"
type: wiki
page-type: synthesis
authority: internal-reference          # explicit; never auto-derived
created: 2026-04-15
last-updated: 2026-04-15
cluster: "Engineering"
query: "Why did we go with Postgres instead of Mongo?"
based_on:                              # bare slugs, intra-zone
  - postgres-decision-log
  - mongo-evaluation-notes
  - q1-pricing-incident
confidence: high                       # high | medium | low
contradictions_found: []
gaps_noted: []
---
```

Filename: `synth-YYYY-MM-DD-<slug>.md`. Folder: `_wiki/pages/`.

## Why this is deferred (D-07 from `wiki-authority-temporal`)

Three things have to be true before `synthesis` earns a slot in the schema:

1. **Volume signal.** > 20 ad-hoc saved Q&A files have accumulated as
   uncategorized markdown notes (in `.private/`, in inboxes, in chat
   exports). Synthesis as a registered page-type pays its complexity cost
   only when it's solving a real organizational problem; below that
   threshold the file-with-notes pattern works fine.
2. **Persona signal.** Persona D (portfolio CEO — like THEO) or persona E
   (consulting CEO with multi-client engagements) onboards and explicitly
   asks for cross-engagement synthesis. These are the personas where the
   compounding-Q&A model has the most leverage; solo founders and senior
   operators get most of the value from existing page-types.
3. **External signal.** BCOS reaches public release and external usage
   produces requests for the synthesis pattern, OR the upstream `llm-wiki`
   ecosystem matures and synthesis becomes a recognized convention with
   field expectations to inherit.

When **any two** of those signals are present, reactivate this folder by
adding `implementation-plan.md` + `plan-manifest.json` and running
`/wiki schema add page-type synthesis` once the plan ships.

## Why I'm not building it now

- **Volume isn't there.** This repo has zero accumulated Q&A files that
  would migrate cleanly into a synthesis page-type. Building the type
  before there's content for it = speculative complexity per
  `wiki.schema.yml.tmpl`'s growth principle: *"Add real page-types as you
  discover real categories you keep wanting. Don't predict — observe."*
- **Other gaps are higher leverage.** Authority semantics, temporal
  awareness, and dispatcher-routed conflict triage (the four other
  llm-wiki review takeaways shipped in the parent plan) compound for
  every wiki user. Synthesis only compounds for users who explore.
- **The schema is ready when it's wanted.** Once the trigger conditions
  fire, `/wiki schema add page-type synthesis --required-fields query,based_on,confidence`
  is a one-line addition (P4 schema-governance work in
  `wiki-missing-layers/` already shipped). No structural work blocks.

## What this folder will contain when activated

- `README.md` (this file — keep it as historical context)
- `implementation-plan.md` (created when reactivating)
- `plan-manifest.json` (created when reactivating)
- `pre-flight-decisions.md` (only if the activation surfaces decisions
  beyond the synthesis-page-type defaults)

## Related decisions

- `wiki-authority-temporal/plan-manifest.json::preFlightDecisions[D-07]` —
  the originating deferral decision and its revisit triggers
- `docs/_bcos-framework/architecture/wiki-zone.md` "Schema and Governance"
  — how new page-types are added without code changes
- `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl` — the registry
  growth principle this deferral honors

## Status

`planned`. Reactivation gated on the three trigger signals above.
