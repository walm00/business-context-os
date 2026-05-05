# /wiki promote — convert an _inbox/ capture into a wiki page (Path B)

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Invocation

```
/wiki promote <path-in-_inbox>
```

Where `<path-in-_inbox>` is a file under `docs/_inbox/`. If the path is anywhere else, return an error and suggest `/wiki create from <path>` instead.

## Pre-flight

1. Verify `enable_path_b: true` in `.config.yml`. If false, stop with a hint to enable Path B and re-run `/wiki init` (or hand-edit config).
2. Verify the file exists, is readable, is a text file (`.md`, `.txt`) or a supported binary (`.pdf`, `.docx`). If unsupported, stop with the supported list.
3. Verify the file is actually under `docs/_inbox/` (literal prefix match). If not, redirect to `/wiki create from`.

---

## Interview (AskUserQuestion)

Run **`AskUserQuestion`** with these questions:

| Key | Prompt | Type | Default | Notes |
|---|---|---|---|---|
| `page_type` | "What page-type should this become?" | enum (from schema) | suggest based on content (see triage signals below) | Options come from `_wiki/.schema.yml` `page-types:` list — query at runtime, don't hardcode. |
| `slug` | "Slug for the wiki page (kebab-case, no extension)?" | text | derive from filename (drop `_inbox/` prefix and date stamp; kebab-case) | Becomes `docs/_wiki/pages/<slug>.md`. |
| `cluster` | "Cluster for this page?" | enum + free-text | suggest based on content keywords | Pulled from `docs/document-index.md`. If `allow-cluster-not-in-source: false`, MUST pick existing; else free-text allowed. |
| `name` | "Human-readable title for the page?" | text | first heading in source if present, else slug-titled | Goes into `name:` frontmatter. |
| `domain_oneline` | "One-sentence description of what this page covers?" | text | derived from first paragraph | Goes into `domain:` (Level 1 ownership spec). |
| `builds_on` | "Which data points does this page build on? (paths to docs/*.md, comma-separated)" | text | (none) | Required for `how-to`, `runbook`, `faq` per default schema. Format: relative paths with `.md` (D-04), e.g. `../brand-voice.md`. |
| `delete_inbox_source` | "Delete original `_inbox/` file after promotion?" | bool | true | Recommended `true` — content lives immutably in `_wiki/raw/local/` after promotion. Set `false` if you want a backup. |

### Triage signals → suggested page-type

Read the first 500 chars of the inbox file. Suggest:

| If content looks like… | Suggest |
|---|---|
| Steps, "How to", procedure | `how-to` |
| What/when/why happened, timeline | `post-mortem` |
| Definitions list, glossary | `glossary` |
| Decision narrative, "we picked X over Y because…" | `decision-log` |
| Q&A | `faq` |
| Operational response runbook ("when X breaks, do Y") | `runbook` |
| External-source-shaped content (a blog post, transcript, article) | `source-summary` |
| None of the above | `how-to` (most common default) |

---

## Step 1 — Move source to raw

For text files (`.md`, `.txt`):
- Copy `docs/_inbox/<filename>` → `docs/_wiki/raw/local/<slug>.md`
- Prepend a header stamp:
  ```
  <!-- wiki-source-stamp
  original-path: docs/_inbox/<filename>
  captured-on: <today>
  promoted-by: <git user.name fallback to "user">
  promotion-action: /wiki promote
  -->
  ```
- The body of the original file becomes the body of the raw file (verbatim, no edits).

For binary files (`.pdf`, `.docx`) — D-06 routing:
- Copy `docs/_inbox/<filename>` → `docs/_wiki/raw/local/<slug>.<ext>` (binary, byte-identical).
- **Dispatch the Task tool with the `wiki-fetch` sub-agent** (`kind: pdf` or `docx`, `source: <abs path to binary>`, `raw-target: docs/_wiki/raw/local/<slug>.md`). The sub-agent runs the `pdf` / `docx` skills internally to extract the markdown body, writes it to `raw-target`, and returns the structured ≤4000-token summary. The main thread receives only the summary — never the full extracted text. Validate the result with `_wiki_fetch_contract.validate_result()` before consuming.
- **Never write to `docs/_collections/`.** Per D-06: implicit cross-zone writes blur boundaries; users who want this in `_collections/` use explicit `/collections add`.

If the source contained URLs that look like Path A candidates (web/github/youtube), surface them in the post-promote report:
> *"Found N URL(s) in the source that could be ingested via `/wiki run`. Listed below — review and queue manually if relevant."*

---

## Step 2 — Compute hash + size for provenance

Hash the binary (or the raw text after stamp normalization) with SHA-256. Truncate to 16 hex chars. Record file size in bytes. These go into `provenance.notes` for future drift detection.

---

## Step 3 — Call `ingest.md`

Read `ingest.md` and follow it with this context:

```yaml
slug: <user choice>
source_type: local
raw_path: docs/_wiki/raw/local/<slug>.md
effective_detail_level: standard      # Path B doesn't have detail-level tiers; use schema default
today: <today>
companion_slug: null
companion_raw_path: null
products: null
provenance:
  kind: inbox-promotion
  source: docs/_inbox/<filename>
  captured_on: <today>
  promoted_by: <git user.name>
  notes: "sha256:<hash16>; size:<bytes>; ext:<extension if binary>"
page_type: <user choice>
cluster: <user choice>
name_override: <user choice — overrides ingest.md's auto-derivation>
domain_override: <user choice>
builds_on_override: <user choice — comma-split list>
```

`ingest.md` writes the page at `docs/_wiki/pages/<slug>.md` (or `source-summary/<slug>.md` if user picked `source-summary`), banner-citing `../raw/local/<slug>.md`.

---

## Step 4 — Delete inbox source (if user chose true)

If `delete_inbox_source = true`:
- Delete `docs/_inbox/<filename>`
- Note in the post-promote report: `Deleted: docs/_inbox/<filename> (content preserved at docs/_wiki/raw/local/<slug>.md).`

If `false`: leave the original in `_inbox/` and note it remains. Warn that running `context-ingest` later might re-process the same content; suggest the user manually move it or add a sentinel.

---

## Step 5 — Hook validation + lint

The frontmatter hook fires on the page write automatically. If it complains, surface its output. If `auto_lint: per-ingest`, run `lint.md`.

---

## Output report

```
Promoted: docs/_inbox/<filename> → docs/_wiki/pages/<slug>.md

  Page-type:    <chosen>
  Cluster:      <chosen>
  Slug:         <slug>
  Raw:          docs/_wiki/raw/local/<slug>.md  ({{IF binary}}+ docs/_wiki/raw/local/<slug>.<ext>{{ENDIF}})
  Wiki page:    docs/_wiki/pages/<slug>.md
  Provenance:   inbox-promotion ← docs/_inbox/<filename> (sha256:<hash16>)
  {{IF deleted}}
  Deleted:      docs/_inbox/<filename>
  {{ELSE}}
  Note:         Original kept at docs/_inbox/<filename>; consider deleting after review.

  {{IF URLs found in source}}
  URLs detected (not auto-queued — review):
    - https://...
    - https://...

Updated: docs/_wiki/index.md (regenerated), overview.md, log.md
{{IF lint findings}}
Lint:    <findings>
```

Suggested commit: `wiki: promote <slug> from _inbox`. No auto-commit.

---

## Notes

- **Reversibility:** if you regret a promotion, the page is in `_wiki/pages/`, the raw is in `_wiki/raw/local/`, and (if `delete_inbox_source=false`) the original is still in `_inbox/`. To fully roll back: `/wiki archive <slug>` (soft-delete) and manually restore the inbox file.
- **Re-promotion:** if you run `/wiki promote` again on the same inbox file (after `delete_inbox_source=false`), the slug check will catch existing slugs and prompt you to either pick a different slug or use `/wiki refresh <slug>` instead.
- **No `_collections/` writes (D-06):** binaries stay in `_wiki/raw/local/`. Users who want a binary in `_collections/` as standalone evidence run `/collections add` explicitly.
- **Git policy:** see SKILL.md.
