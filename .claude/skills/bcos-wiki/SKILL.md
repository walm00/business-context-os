---
name: bcos-wiki
description: "Wiki zone manager for BCOS. Ingests URLs / local docs / inbox captures into docs/_wiki/ as schema-validated pages with banner citations, three structural shapes for source-summary, and two-tier refresh. Schema-driven, CLEAR-governed, derived-artifact. Invoke with /wiki."
trigger: "/wiki"
version: "1.0.0"
last_updated: "2026-05-02"
authority-docs:
  - docs/_bcos-framework/architecture/wiki-zone.md
  - docs/_bcos-framework/templates/_wiki.schema.yml.tmpl
  - docs/_planned/wiki-zone-integration/pre-flight-decisions.md
---

# /wiki

Wiki-zone manager for BCOS. Routes URL ingests, local-document promotions, and inbox captures into `docs/_wiki/` as first-class managed documents (schema-validated frontmatter, derived `index.md`, BCOS-compatible CLEAR ownership).

## Trigger phrases

- **`/wiki`** with subcommands: `init`, `run`, `queue`, `promote`, `create`, `review`, `archive`, `refresh`, `lint`, `remove`, `schema`, `search`
- "Add this URL to the wiki"
- "Promote this `_inbox/` capture into a wiki page"
- "Ingest this PDF as a wiki source-summary"
- "Run the wiki refresh"
- "Initialize the wiki zone"

## Pipeline at a glance

```
queue.md (URLs, human-curated)
    ↓  fetch (web | github | youtube)            ← Path A
docs/_wiki/raw/<type>/  (immutable captures)
    ↓  ingest (banner citation; 3 shapes)
docs/_wiki/source-summary/<slug>.md  ← schema-validated
                                  ↓
                              refresh_wiki_index.py (derived index)


/wiki promote docs/_inbox/<file>.md          ← Path B (inbox-promotion)
/wiki create from <path-or-paste>            ← Path B (local-document)
    ↓
docs/_wiki/raw/local/<slug>.<ext>            (binaries) + .md (extraction)
    ↓
docs/_wiki/pages/<slug>.md                   ← provenance frontmatter
                                  ↓
                              refresh_wiki_index.py
```

## Subcommands

| Command | Status | Phase | What it does |
|---|---|---|---|
| `init` | implemented | P3 | Scaffold `docs/_wiki/` (config + schema + page templates + queue + log + overview); never overwrite |
| `run [<url>]` | implemented | P3 | Path A: batch (no arg) processes all `## Pending` queue items; single (with URL) auto-queues + ingests |
| `queue <url> [tags]` | implemented | P3 | Append URL to `## Pending` of `queue.md` without fetching |
| `ingest` | shared protocol | P3 | Internal — called by `run`/`promote`/`create`; shared pipeline. Not a user-facing entry |
| `promote <inbox-path>` | implemented | P3 | Path B: convert an `_inbox/` capture into a wiki page; provenance.kind = inbox-promotion |
| `create from <path-or-paste>` | implemented | P3 | Path B: ingest a local file or pasted text; provenance.kind = local-document |
| `review <slug>` | implemented | P3 | Bump `last-reviewed`; optionally re-pull `builds-on` data points to verify |
| `archive <slug>` | implemented | P3 | Soft-delete to `_wiki/.archive/` with dangling-reference scan |
| `refresh <slug>` | implemented | P3 | Path A: re-fetch a `source-summary` page (refresh-must-rediscover applies, D-05 two-tier) |
| `lint` | implemented | P3 | Run wiki-specific lint checks on demand (also runs via daily/scheduled jobs) |
| `remove <slug>` | implemented | P3 | Hard remove (vs `archive` soft-delete) — only when the user explicitly wants the page+raw gone |
| `schema list\|add\|rename\|retire\|validate\|migrate` | P4 | Vocabulary governance — see `schema.md` (P4) |
| `search <query>` | implemented | P2 | Zone-scoped sugar over `/context search --zone wiki` (mechanical BM25; `--semantic` opt-in only) — see `search.md` |
| `bundle <profile>` | implemented | P5 | Zone-scoped sugar over `/context bundle <profile>` (mechanical task-driven routing; `--resolve-conflicts` / `--verify-coverage` opt-in only) — see `bundle.md` |

## Dispatch

1. Identify the subcommand from the first word after `/wiki`.
2. **Guard (every subcommand except `init`):** confirm `docs/_wiki/.config.yml` exists. If missing, stop with:
   > *"No wiki zone here (`docs/_wiki/.config.yml` missing). Run `/wiki init` to scaffold one first."*
   Subcommand files repeat this guard by reference; you only enforce it once per invocation.
3. Route — read the sibling file in this skill directory and follow its instructions:
   - `init` → `init.md` (no Guard)
   - `run` → `run.md`
   - `queue` → `queue.md`
   - `promote` → `promote.md`
   - `create` → `create.md`
   - `review` → `review.md`
   - `archive` → `archive.md`
   - `refresh` → `refresh.md`
   - `lint` → `lint.md`
   - `remove` → `remove.md`
   - `schema` → `schema.md` (P4)
   - `search` → `search.md` (P2; zone-scoped sugar over `/context search`)
   - `bundle` → `bundle.md` (P5; zone-scoped sugar over `/context bundle`)
4. Do not proceed past dispatch before reading the target file.

## Guard rails (universal — apply to every subcommand)

### Git policy (canonical)

**Never run `git commit` or `git push`** after `init`, `run`, `ingest`, `promote`, `create`, `review`, `archive`, `refresh`, `lint`, `remove`, or `schema` — unless the human explicitly asked to commit in this conversation. List what changed and stop. The human reviews diffs and runs `git commit` / `git push` when ready.

This matches BCOS's broader convention (see `docs/.session-diary.md` and `CLAUDE.md`'s "Auto-commit" policy).

### Frontmatter discipline (D-04)

Every wiki page satisfies BCOS's standard required fields **plus** the wiki extensions defined in `_wiki/.schema.yml`. The PostToolUse hook validates this on every save and emits these IDs on violation: `schema-violation`, `reference-format-mismatch`, `forbidden-builds-on-target`, `provenance-required`, `shape-conflict`, `folder-mismatch`, `schema-version-drift`.

**Reference-format rule** (slugs intra-zone, paths cross-zone):
- `references:`, `subpages:`, `parent-slug:`, body `[[...]]` → bare slug, no `.md`
- `builds-on:`, `raw-files:`, body `[text](../path.md)` → relative path with `.md`

### Derived artifacts (D-11)

- `docs/_wiki/index.md` — regenerated by `.claude/scripts/refresh_wiki_index.py`. **Never hand-edit.** All ingest subcommands call this script as their final step.
- `docs/_wiki/log.md` — append-only. Only ingest/refresh/remove/archive may add entries; never rewrite.
- `docs/_wiki/overview.md` — authored prose. Updated by `ingest` (one paragraph per source-summary, in `sources:` order).

### Token guard (D-05)

Any single fetch projected to exceed **200,000 tokens** halts and asks the user to confirm or downgrade `detail-level`. This applies to `run`, `refresh`, and `create` (when source content is large).

### Path B writes never cross zones (D-06)

`promote` and `create` keep binaries in `docs/_wiki/raw/local/<slug>.<ext>` alongside their markdown extraction. They do **not** write to `docs/_collections/`. Users who want a binary in collections-as-evidence must run `/collections add` explicitly.

### Cluster permissive default (D-03)

When `_wiki/.schema.yml` has `clusters.allow-cluster-not-in-source: true` (v1 default), wiki pages may declare a `cluster:` not yet in `docs/document-index.md` — drift surfaces via the quarterly `wiki-coverage-audit` as INFO, not ERROR. Tighten to `false` only after the cluster-mint follow-up (`FU_006`) lands.

## File layout (in this skill)

```
.claude/skills/bcos-wiki/
├── SKILL.md                ← this file
├── init.md                 ← /wiki init
├── run.md                  ← /wiki run [<url>]
├── ingest.md               ← shared ingest pipeline (called by run/promote/create/refresh)
├── queue.md                ← /wiki queue
├── promote.md              ← /wiki promote
├── create.md               ← /wiki create from
├── review.md               ← /wiki review
├── archive.md              ← /wiki archive
├── refresh.md              ← /wiki refresh
├── lint.md                 ← /wiki lint
├── remove.md               ← /wiki remove
├── schema.md               ← /wiki schema  (P4)
├── references/
│   └── migration-helpers.md   ← schema-version migration recipes (P4)
├── templates/
│   ├── protocols/
│   │   ├── common.md       ← URL parsing, slug derivation, inbox-tag DSL
│   │   ├── web.md
│   │   ├── github.md
│   │   ├── youtube.md
│   │   └── local.md        ← Path B: binary handling, hash, extraction
│   ├── page-types/
│   │   ├── how-to.md
│   │   ├── glossary.md
│   │   └── source-summary.md
│   ├── raw/
│   │   ├── web-README.md.tmpl
│   │   ├── github-README.md.tmpl
│   │   ├── youtube-README.md.tmpl
│   │   └── local-README.md.tmpl
│   ├── queue.md.tmpl
│   ├── overview.md.tmpl
│   ├── log.md.tmpl
│   └── README.md.tmpl
```

`templates/page-types/` are starter bodies for each registered `page-type`. New types added via `/wiki schema add page-type <name>` get a stub auto-created.

## What the skill does NOT do

- Write data points (those live in `docs/*.md` — use `context-ingest` and the data-point template)
- Touch `docs/_collections/` (evidence zone — explicit user actions only, see D-06)
- Cross-tool adapter manuals (`AGENTS.md`-style) — BCOS uses one `CLAUDE.md`
- Auto-commit or auto-push (see Git policy above)

## See also

- `docs/_bcos-framework/architecture/wiki-zone.md` — full architecture spec
- `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl` — vocabulary registry
- `docs/_planned/wiki-zone-integration/pre-flight-decisions.md` — D-01 → D-11 decision rationale
