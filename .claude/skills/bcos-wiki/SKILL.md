---
name: bcos-wiki
description: "Wiki zone manager for BCOS — the universal long-form and cross-cutting content destination per plugin-storage-contract.md Rule 2. Stores runbooks, SOPs, decision logs, how-tos, glossaries, post-mortems, FAQs, meeting notes, and plugin cross-cutting context (charters, transcripts, research, customer-call notes). Two ingest paths: Path B (local files, pasted text, inbox promotion — runbooks/scripts/SOPs/notes) and Path A (external URLs / GitHub / YouTube). Schema-validated frontmatter, banner citations, builds-on graph for references, two-tier refresh, supersedes chains. Schema-driven, CLEAR-governed, derived-artifact. Invoke with /wiki."
trigger: "/wiki"
version: "1.1.0"
last_updated: "2026-05-13"
authority-docs:
  - docs/_bcos-framework/architecture/plugin-storage-contract.md
  - docs/_bcos-framework/architecture/wiki-zone.md
  - docs/_bcos-framework/templates/_wiki.schema.yml.tmpl
  - docs/_planned/wiki-zone-integration/pre-flight-decisions.md
---

# /wiki

> **See also:** `context-ingest` is the single public entry point for new material. If the user dropped raw content of unknown shape ("here's a doc", "save this"), prefer `context-ingest` — it dispatches here automatically when the input is a URL or an `_inbox/` capture. Use `/wiki` directly only when the user explicitly names the wiki (`/wiki run`, "promote to wiki", "add to the wiki").

## What this skill stores

The wiki is BCOS's universal long-form / cross-cutting content destination — canonical per [`plugin-storage-contract.md`](../../../docs/_bcos-framework/architecture/plugin-storage-contract.md) Rule 2. **Anything operational or explanatory that isn't a canonical data point and isn't legal-weight evidence lives here.** That includes:

- **Operational truth (authority: `canonical-process`)** — runbooks, SOPs, how-tos, decision logs, post-mortems, playbooks, tutorials, scripts-with-context
- **Internal reference (authority: `internal-reference`)** — glossaries, FAQs, internal explainers
- **Plugin cross-cutting content** — charters, meeting transcripts, WhatsApp / Slack exports, email captures, customer-call notes, research clippings (Rule 2 worked examples)
- **External sources (authority: `external-reference`)** — captured URLs / GitHub repos / YouTube transcripts via Path A, with banner citations to the verbatim raw capture

Routes all of the above into `docs/_wiki/` as first-class managed documents: schema-validated frontmatter, derived `index.md`, BCOS-compatible CLEAR ownership, builds-on graph for cross-references, two-tier refresh for staying current, supersedes chains for temporal succession.

**What does NOT belong here:** canonical data points (those live in `docs/*.md`); legal-weight evidence (signed contracts, regulatory filings → `_collections/`); plugin-private structured records (those live in `docs/_<plugin>/` per Rule 1).

## Trigger phrases

- **`/wiki`** with subcommands: `init`, `init --defaults`, `run`, `queue`, `promote`, `create`, `review`, `archive`, `refresh`, `lint`, `remove`, `schema`, `search`
- "Add this URL to the wiki"
- "Promote this `_inbox/` capture into a wiki page"
- "Store this runbook / SOP / decision log / transcript in the wiki" (Path B)
- "Ingest this PDF as a wiki source-summary"
- "Run the wiki refresh"
- "Initialize the wiki zone" (interactive) or "scaffold the wiki with defaults" (headless `--defaults`)

## Pipeline at a glance

Two ingest paths converge on the same schema-validated wiki page. Path B (local content) is the common case for operational/explanatory knowledge; Path A (URLs) handles external sources.

```
PATH B — local content                          PATH A — external URLs
(runbooks, SOPs, decision logs,                 (web articles, GitHub repos,
 transcripts, scripts, notes, …)                 YouTube transcripts)

/wiki create from <path-or-paste>               queue.md  (URLs, human-curated)
/wiki promote docs/_inbox/<file>.md                  ↓  fetch (web | github | youtube)
        ↓                                       docs/_wiki/raw/<type>/  (immutable)
docs/_wiki/raw/local/<slug>.md                       ↓
(+ binary <slug>.<ext> if PDF/.docx)            docs/_wiki/source-summary/<slug>.md
        ↓                                       (3 structural shapes: standalone,
docs/_wiki/pages/<slug>.md                       unified, umbrella+sub)
(page-type: how-to | runbook | decision-log |
 post-mortem | glossary | faq | playbook |               ↓
 tutorial | meeting-notes | …)                  banner citation: raw/<type>/<slug>.md

        ↘                                       ↙
         schema-validated frontmatter, builds-on graph,
         provenance, authority value, supersedes chain
                          ↓
                  refresh_wiki_index.py
                          ↓
              docs/_wiki/index.md (derived)
```

**The two paths produce the same wiki page format.** Page-type is in the frontmatter, not in the folder layout. The difference is just origin: Path B from local content (with a `provenance:` block recording the source); Path A from external URLs (with `source-url`, `last-fetched`, `detail-level` and one of three structural shapes).

## Subcommands

| Command | Status | Phase | What it does |
|---|---|---|---|
| `init` | implemented | P3 | Scaffold `docs/_wiki/` (config + schema + page templates + queue + log + overview); never overwrite. Interactive — 6-question AskUserQuestion interview. |
| `init --defaults` | implemented | P3 | Headless scaffold with sensible defaults (display_name = git repo basename; detail_level=standard; source_types=[web,github,youtube]; auto_lint=batch; auto_mark_complete=true; enable_path_b=true). Delegates to [`cmd_wiki_init.py`](../../scripts/cmd_wiki_init.py). Idempotent — no-op on existing zone. Used by the Guard's auto-init flow and by `ensure_wiki_zone.py` for plugin installs. |
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
2. **Guard (every subcommand except `init`):** confirm `docs/_wiki/.config.yml` exists. If missing, follow the **Guard — auto-init flow** below. Subcommand files repeat this guard by reference; you only enforce it once per invocation.
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

### Guard — auto-init flow (when `_wiki/.config.yml` is missing)

The pre-2026-05-13 behavior was a hard-stop: print *"No wiki zone here. Run `/wiki init` first."* and exit. That created a dead-end for downstream agents (observed in a downstream session) — agents would fall back to writing operational content into `docs/operations/` instead of the wiki. The current behavior turns the guard into a structured choice while preserving the hard-stop semantics for headless callers.

**Branch 1 — headless caller (`$BCOS_NONINTERACTIVE=1` set, OR `--yes` passed):**

Keep the original hard-stop behavior — print:

> *"No wiki zone here (`docs/_wiki/.config.yml` missing). This is a non-interactive context (BCOS_NONINTERACTIVE=1). Plugin install scripts should call `.claude/scripts/ensure_wiki_zone.py` to scaffold the zone before invoking `/wiki *`. Interactive users: run `/wiki init` or `/wiki init --defaults`."*

Return non-zero. Do not scaffold silently — explicit consent (per L-ECOSYSTEM-20260510-017) is preserved.

**Branch 2 — interactive caller (no headless override):**

Fire **`AskUserQuestion`** with the user's actual operation in scope. Example wording for `/wiki create from <path>`:

> *Q: "No wiki zone is initialized in this repo yet. How would you like to proceed?"*
>
> - **Init with defaults + store this runbook** *(Recommended — calls `cmd_wiki_init.py` with sensible defaults: display_name from git basename, all source-types, Path B enabled. Takes one operation; you can refine later via `/wiki schema`.)*
> - **Run the full `/wiki init` interview, then proceed** *(6 questions; lets you set detail-level, source-types, lint cadence, Path B enable per your preference.)*
> - **Cancel** *(don't init, don't proceed with the current operation.)*

On selection:

| Choice | Behavior |
|---|---|
| Init with defaults + proceed | Run `.claude/scripts/cmd_wiki_init.py` (or equivalent `ensure_wiki_zone.py` call). Report the JSON result. Then resume the original subcommand (`create from`, `promote`, `run`, etc.) as if the Guard had passed. |
| Full interview + proceed | Read `init.md` and run the 6-question interactive scaffold. After successful init, resume the original subcommand. |
| Cancel | Print the hard-stop message and exit. No state mutation. |

The dispatched subcommand files (`create.md`, `promote.md`, `run.md`, `refresh.md`, `lint.md`, `archive.md`, `review.md`, `remove.md`, `schema.md`, `search.md`, `bundle.md`, `queue.md`) all reference *"the `.config.yml` Guard defined in `SKILL.md`"* — they inherit this AskUserQuestion path automatically, no per-file changes needed.

**Why this preserves D-08 (pre-flight-decisions.md):** D-08 required substrate-readiness checks before write operations. The check is still mandatory; the user just gets a structured way to satisfy it in one turn. Silent auto-scaffolding (which would weaken D-08) is explicitly prevented by the headless branch.

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
