# /wiki create — ingest a local file or pasted text into the wiki (Path B)

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`. Many steps are shared with `promote.md`; differences flagged below.)

## Invocation

```
/wiki create from <path>           ← path to a local file (any location outside docs/_inbox/)
/wiki create from -                ← read pasted text from stdin / next user message
/wiki create from "<text>"         ← inline text, quoted
```

If `<path>` starts with `docs/_inbox/`, redirect to `/wiki promote <path>` instead — that path has its own provenance kind (`inbox-promotion`) and its own delete-after-promotion option.

## Pre-flight

1. Verify `enable_path_b: true` in `.config.yml`.
2. For path input: verify the file exists, is readable, is `.md` / `.txt` / `.pdf` / `.docx`. Other extensions: stop with the supported list.
3. For pasted text: minimum 50 chars (avoid accidental empty creates). If shorter, ask the user to confirm or expand.

---

## Interview (AskUserQuestion)

Same as `promote.md` — six questions: `page_type`, `slug`, `cluster`, `name`, `domain_oneline`, `builds_on`. **One additional question for Path-B-create:**

| Key | Prompt | Type | Default | Notes |
|---|---|---|---|---|
| `keep_source_link` | "Keep an absolute reference to the local source path?" | bool | true | When true, `provenance.source` records the original path (e.g. `/Users/.../doc.pdf`). When false, only the hash is recorded — useful when the source path is private/transient. |

Triage signals → suggested page-type: same heuristic as `promote.md`.

`delete_inbox_source` is N/A here (source isn't in `_inbox/`).

---

## Step 1 — Land raw content

For pasted text:
- Write directly to `docs/_wiki/raw/local/<slug>.md` with header stamp:
  ```
  <!-- wiki-source-stamp
  original-path: (pasted)
  captured-on: <today>
  promoted-by: <git user.name>
  promotion-action: /wiki create from (paste)
  -->
  ```

For text files (`.md`, `.txt`):
- Copy to `docs/_wiki/raw/local/<slug>.md` with header stamp recording the original absolute path (or just `(local file)` if `keep_source_link=false`).

For binary files (`.pdf`, `.docx`):
- **D-06 routing**: copy the binary byte-identical to `docs/_wiki/raw/local/<slug>.<ext>`.
- **Dispatch the Task tool with the `wiki-fetch` sub-agent** (`kind: pdf` or `docx`, `source: <abs path to binary>`, `raw-target: docs/_wiki/raw/local/<slug>.md`). The sub-agent runs the `pdf` / `docx` skills internally, writes the extracted markdown with the header stamp, and returns only the structured ≤4000-token summary. The main thread does NOT inline the extracted text. Validate the result with `_wiki_fetch_contract.validate_result()`.
- Never write to `docs/_collections/`.

---

## Step 2 — Hash + size

SHA-256 the source content (the binary or the pre-stamped markdown). Truncate hash to 16 hex chars. Record size. These go into `provenance.notes`.

---

## Step 3 — Call `ingest.md`

Read `ingest.md` and pass:

```yaml
slug: <user choice>
source_type: local
raw_path: docs/_wiki/raw/local/<slug>.md
effective_detail_level: standard
today: <today>
companion_slug: null
companion_raw_path: null
products: null
provenance:
  kind: local-document
  source: <absolute path or "(pasted)" or "(local file)" depending on keep_source_link>
  captured_on: <today>
  promoted_by: <git user.name>
  notes: "sha256:<hash16>; size:<bytes>; ext:<extension if binary>"
page_type: <user choice>
cluster: <user choice>
name_override: <user choice>
domain_override: <user choice>
builds_on_override: <user choice>
```

`ingest.md` writes the page at `docs/_wiki/pages/<slug>.md` (or `source-summary/<slug>.md` if `page_type: source-summary`).

---

## Step 4 — Hook validation + lint

Same as `promote.md` Step 5.

---

## Step 5 — `provenance-source-missing` lint reminder

If `keep_source_link=true` and the source was a local file, the `provenance-source-missing` lint check (INFO, not ERROR) will fire later if the file is moved/deleted. Mention this once in the post-create report:
> *"`provenance.source` records the absolute path. If the source file moves, the quarterly lint will surface this as INFO. To suppress, run `/wiki review <slug>` and clear/update `provenance.source`."*

If `keep_source_link=false`, this is irrelevant.

---

## Output report

```
Created: docs/_wiki/pages/<slug>.md (Path B local-document)

  Page-type:    <chosen>
  Cluster:      <chosen>
  Slug:         <slug>
  Source:       {{path | "(pasted)" | "(local file)"}}
  Raw:          docs/_wiki/raw/local/<slug>.md  ({{IF binary}}+ docs/_wiki/raw/local/<slug>.<ext>{{ENDIF}})
  Wiki page:    docs/_wiki/pages/<slug>.md
  Provenance:   local-document (sha256:<hash16>)

Updated: docs/_wiki/index.md (regenerated), overview.md, log.md
{{IF lint findings}}
Lint:    <findings>
```

Suggested commit: `wiki: create <slug>`. No auto-commit.

---

## Differences from `promote.md`

| Aspect | `promote` | `create` |
|---|---|---|
| Source location | Must be under `docs/_inbox/` | Anywhere except `docs/_inbox/` (or pasted text) |
| `provenance.kind` | `inbox-promotion` | `local-document` |
| Source deletion option | Yes — `delete_inbox_source` | No (source typically lives outside the repo) |
| URL detection | Yes — surfaces URLs in inbox content | Same; surfaces URLs in pasted/file content |
| Refresh semantics later | Re-promote from a new inbox file | `/wiki refresh` re-reads the local-document path; if missing, fires `provenance-source-missing` INFO |

Both paths converge on the same `ingest.md` pipeline and produce the same page shape.

---

## Notes

- **Refreshing a local-document page later:** `/wiki refresh <slug>` re-reads the source path (if `keep_source_link=true`), hash-compares, and only updates the wiki page if content changed. See `refresh.md`.
- **Pasted text refresh:** can't auto-refresh (no source). Re-running `/wiki create from "<new text>"` with the same slug is rejected; use `/wiki review <slug>` to bump `last-reviewed` after manual edits, or archive + recreate.
- **Git policy:** see SKILL.md.
