# /wiki schema — govern wiki vocabulary

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

This is the P4 executable surface. Use the helper below for all schema reads,
dry-runs, validations, and migrations:

```text
python .claude/scripts/wiki_schema.py <subcommand>
```

## Invocation

```text
/wiki schema list
/wiki schema add page-type <name>
/wiki schema rename page-type <old> <new>
/wiki schema retire page-type <name>
/wiki schema validate
/wiki schema migrate <from> <to>
```

## Shared rules

- Read `docs/_wiki/.schema.yml`; fall back to `docs/_bcos-framework/templates/_wiki.schema.yml.tmpl` for read-only validation when project schema is missing.
- Use `AskUserQuestion` before any schema mutation.
- Always run the helper without `--apply` first and show the dry-run diff before applying changes.
- Only re-run with `--apply` after AskUserQuestion confirmation.
- Append every mutation to `_wiki/log.md` and to the schema `migrations:` list.
- Never hand-edit `docs/_wiki/index.md`; run `refresh_wiki_index.py` after page-affecting migrations.

## `list`

Run:

```text
python .claude/scripts/wiki_schema.py list
```

Prints registered page-types, statuses, detail-levels, provenance kinds, lint checks, and auto-fixes.

## `add page-type <name>`

Dry-run first:

```text
python .claude/scripts/wiki_schema.py add page-type <name> --description "<description>" --required-fields "<csv>"
```

Ask for:

| Field | Default |
|---|---|
| description | derived from name |
| folder | `pages` |
| required-fields | `[]` |
| review-cadence-days | `180` |
| auto-archive-after-days | `null` |

On confirmation, re-run with `--apply`. The helper writes `_wiki/.schema.yml`,
appends the migration to `_wiki/log.md`, and creates a skill page-type template
when running against this framework repo.

## `rename page-type <old> <new>`

1. Count affected pages.
2. Show a file-by-file dry-run.
3. On confirmation, rewrite frontmatter, bump page versions, update `last-updated`, append migration history, and run `refresh_wiki_index.py`.
4. The inverse operation must be obvious in the report.

Commands:

```text
python .claude/scripts/wiki_schema.py rename page-type <old> <new>
python .claude/scripts/wiki_schema.py rename page-type <old> <new> --apply
```

## `retire page-type <name>`

Mark the type retired in schema without invalidating existing pages. New pages should not use retired page-types; lint reports INFO for existing pages.

Commands:

```text
python .claude/scripts/wiki_schema.py retire page-type <name>
python .claude/scripts/wiki_schema.py retire page-type <name> --apply
```

## `validate`

Walk all `docs/_wiki/pages/*.md` and `docs/_wiki/source-summary/*.md`, then apply hook-level wiki validation. Report `schema-violation`, `reference-format-mismatch`, `folder-mismatch`, and `schema-version-drift`.

```text
python .claude/scripts/wiki_schema.py validate
```

## `migrate <from> <to>`

Read `references/migration-helpers.md`, run the matching migration recipe, and require a dry-run diff before writing.

```text
python .claude/scripts/wiki_schema.py migrate <from> <to>
python .claude/scripts/wiki_schema.py migrate <from> <to> --apply
```

### Registered recipes

| From | To | What it does | Reversible |
|---|---|---|---|
| `1.0` | `1.1` | Add optional `etag` / `last-modified` / `content-hash` to source-summary pages (HTTP refresh signals) | yes (`1.1 -> 1.0`) |
| `1.1` | `1.2` | Add `authority:` to every wiki page using the mechanical default (path + page-type + provenance.kind). Non-clobbering — explicit values declared by the user are preserved. Audit trail appended to `.claude/quality/migration-log.jsonl`. | yes (`1.2 -> 1.1`) — strips `authority:` from every page (explicit overrides are recorded in the migration log so they can be restored manually if needed) |

Schema 1.2 also introduces `source-published`, `supersedes`, `superseded-by` as **optional** fields on `source-summary` pages. The migration does NOT auto-write these — they are added per-page by ingest-time triage (`Step 7.5` in `ingest.md`) when a Class B temporal-supersession candidate is detected.

After running `migrate 1.1 1.2 --apply`, run `validate` to confirm the schema-version bump is recorded and `lint` to surface any `authority-default-questionable` INFO findings.

No agent commits. See `SKILL.md`.
