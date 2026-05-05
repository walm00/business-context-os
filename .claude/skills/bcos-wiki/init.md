# /wiki init — scaffold the wiki zone

(Skill-directory paths are defined in `SKILL.md`.)

## Inverse Guard (must NOT already exist)

If `docs/_wiki/.config.yml` exists in the repo, **stop** with:
> *"A wiki zone already exists here (`docs/_wiki/.config.yml` found). Use `/wiki run <url>` to ingest a new source, `/wiki promote <inbox-path>` to convert an inbox capture, or `/wiki schema list` to inspect the vocabulary."*

Only proceed if absent.

---

## Interview (AskUserQuestion-driven, per BCOS UX rule)

Run **`AskUserQuestion`** with these six questions. Present them in one structured prompt — not as a chained interrogation. The user answers all six in one round.

| Question key | Prompt | Type | Default | Notes |
|---|---|---|---|---|
| `domain` | "What is this wiki about?" | text | (required) | One short phrase, used as the wiki's display name. Example: `BCOS framework operations` or `agentic AI frameworks`. |
| `detail_level` | "Default detail level for ingests?" | enum | `standard` | `brief` ≈ 5–15k tokens · `standard` ≈ 30–80k tokens · `deep` ≈ 100–500k+ tokens. Per-source overrides via `<!-- detail:X -->` queue tags. |
| `source_types` | "Which Path A source types?" | multi-select | `[web, github, youtube]` | Pick the URL types you'll actually ingest. Reduces clutter in `raw/` if narrower. |
| `auto_lint` | "When should lint run automatically?" | enum | `batch` | `batch` (after each `/wiki run`) · `per-ingest` (after every single source) · `never` (only `/wiki lint`). |
| `auto_mark_complete` | "After successful ingest, flip the queue line to `[x]` automatically?" | bool | `true` | Recommended `true` — saves a manual checkbox toggle. |
| `enable_path_b` | "Enable Path B (local content / inbox-promotion)?" | bool | `true` | Set `false` to disable `/wiki promote` and `/wiki create`. URLs-only wikis can keep this off. |

Display a recap; ask a final confirmation question (`Proceed: yes / no / cancel`). If `no`/`cancel`, stop without writing anything.

---

## Scaffold creation

Create everything atomically (parent dirs first). On any error, leave a partial scaffold — do not roll back; humans review with `git status`.

### Step 1 — Config

Write `docs/_wiki/.config.yml`:

```yaml
# Wiki zone runtime config — see docs/_bcos-framework/architecture/wiki-zone.md
domain: "{{DOMAIN}}"
detail_level: {{DETAIL_LEVEL}}             # brief | standard | deep
source_types: {{SOURCE_TYPES_LIST}}         # YAML list, e.g. [web, github, youtube]
auto_lint: {{AUTO_LINT}}                   # batch | per-ingest | never
auto_mark_complete: {{AUTO_MARK_COMPLETE}} # true | false
enable_path_b: {{ENABLE_PATH_B}}            # true | false
created: {{TODAY}}
last-updated: {{TODAY}}
schema-source: docs/_wiki/.schema.yml      # local; falls back to framework template
```

### Step 2 — Schema

Copy the framework template into the project:
- Source: `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl`
- Destination: `docs/_wiki/.schema.yml`

Replace `TODAY` placeholder with today's date (`YYYY-MM-DD`). Keep all other defaults — the user can edit later via `/wiki schema add|rename|retire`.

If the framework template is missing (`update.py` hasn't run), fail with a clear message: *"Framework template missing at `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl`. Run `python .claude/scripts/update.py` first."*

### Step 3 — Directory structure

Create:
- `docs/_wiki/pages/` (with `.gitkeep`)
- `docs/_wiki/source-summary/` (with `.gitkeep`)
- `docs/_wiki/.archive/` (with `.gitkeep`)
- `docs/_wiki/raw/` (with subdirs per `source_types`: `web/`, `github/`, `youtube/`, plus `local/` if `enable_path_b: true`)

### Step 4 — `queue.md`

Read `<skill-dir>/templates/queue.md.tmpl`, no substitutions, write to `docs/_wiki/queue.md`.

### Step 5 — `overview.md`

Read `<skill-dir>/templates/overview.md.tmpl`, substitute `{{DOMAIN}}` and `{{TODAY}}`, write to `docs/_wiki/overview.md`.

### Step 6 — `log.md`

Read `<skill-dir>/templates/log.md.tmpl`, substitute `{{DOMAIN}}` and `{{TODAY}}`, write to `docs/_wiki/log.md`.

### Step 7 — `index.md` (initial)

Run `python .claude/scripts/refresh_wiki_index.py` to generate `docs/_wiki/index.md` from the (empty) page set. The script handles the empty-zone case correctly.

### Step 8 — `README.md`

Write a short `docs/_wiki/README.md` explaining the layout (one paragraph plus a link to `wiki-zone.md`). Include:
- "This zone is managed by the `bcos-wiki` skill — invoke with `/wiki`."
- "Pages live in `pages/` (internal) and `source-summary/` (external captures)."
- "`index.md` and `log.md` are derived/append-only — never hand-edit."
- "See `docs/_bcos-framework/architecture/wiki-zone.md` for full rules."

### Step 9 — Bump session diary

Append a one-liner to `docs/.session-diary.md`:
```
- {{TODAY}} — Wiki zone initialized (/wiki init). Domain: "{{DOMAIN}}". Detail: {{DETAIL_LEVEL}}.
```

### Step 10 — Smoke check

Run the frontmatter hook against `docs/_wiki/overview.md` (synthetic input) to confirm the schema-template fallback resolves and no `schema-violation` fires for a freshly-scaffolded zone. If the hook complains, surface its output with a hint to run `/wiki schema validate`.

---

## Confirmation

Print:

```
Wiki zone scaffolded.

  docs/_wiki/.config.yml          runtime config (domain, detail level, source types)
  docs/_wiki/.schema.yml          vocabulary registry (page-types, lint, auto-fixes)
  docs/_wiki/queue.md             pending URLs (Path A)
  docs/_wiki/overview.md          rolling cross-source synthesis
  docs/_wiki/log.md               append-only ingest history
  docs/_wiki/index.md             page table — DERIVED ARTIFACT (refresh_wiki_index.py)
  docs/_wiki/pages/               internal authored pages
  docs/_wiki/source-summary/      external captures (Path A)
  docs/_wiki/raw/<type>/          immutable source captures
  docs/_wiki/.archive/            soft-deleted pages

Next:
  /wiki queue <url>          add a URL without fetching
  /wiki run <url>            ingest a single URL
  /wiki run                  batch-process all queued URLs
  /wiki promote <inbox-path> convert an _inbox/ capture to a wiki page
  /wiki create from <path>   ingest a local file or pasted text

Bootstrap defaults: page-types [how-to, glossary, source-summary] are active.
Add more via /wiki schema add page-type <name> as real categories emerge.
```

---

## Notes

- **Idempotency:** `init` is one-shot. Re-running fails the inverse Guard above. To reset, archive `docs/_wiki/` to `docs/_archive/wiki-<date>/` manually and re-run.
- **Git policy:** see SKILL.md. Init scaffolds and stops — the human commits when ready.
- **No `AGENTS.md`:** BCOS has one `CLAUDE.md`. The wiki's behavior is documented in `wiki-zone.md`, not a parallel manual.
