# Wiki Schema Migration Helpers

This reference supports `/wiki schema rename|migrate`. Keep migrations small, reversible, and dry-run first.

Executable helper:

```text
python .claude/scripts/wiki_schema.py rename page-type <old> <new>
python .claude/scripts/wiki_schema.py rename page-type <old> <new> --apply
python .claude/scripts/wiki_schema.py migrate <from> <to>
```

The skill must use AskUserQuestion between the dry-run and `--apply`.

## Page-Type Rename

Inputs: `old`, `new`, `today`.

1. Walk `docs/_wiki/pages/*.md` and `docs/_wiki/source-summary/*.md`.
2. Select pages with `page-type: <old>`.
3. Dry-run output:
   - file path
   - old page-type
   - new page-type
   - version bump that would be applied
4. On confirmation:
   - replace `page-type: <old>` with `page-type: <new>`
   - bump `version` patch number
   - set `last-updated: <today>`
   - preserve `created`, references, body, and provenance
5. Append schema migration:

```yaml
- schema-version: <schema-version>
  applied: <today>
  operation: rename-page-type
  from: <old>
  to: <new>
  pages-migrated: <count>
  reversible-via: rename-page-type <new> <old>
```

6. Run `python .claude/scripts/refresh_wiki_index.py`.

## Required Field Add

Inputs: `page-type`, `field`, `default`.

Only auto-apply when `default` is non-empty and mechanically safe. Otherwise, report pages missing the field and stop for human edits.

## Schema-Version Drift

When the hook reports `schema-version-drift`, migrate by version number, not by guessing from file content. Unknown version pairs stop with a clear message.

## Recipe Registration Pattern (P4)

`/wiki schema migrate <from> <to>` is no longer a stub. Recipes live in `.claude/scripts/wiki_schema.py` under the `_MIGRATION_RECIPES` dict, keyed by `(from_version, to_version)`. Each recipe is a callable `recipe(page_path, page_text) -> str | None` that returns the new file text (success), or `None` (page is not a candidate for this migration).

To register a new recipe:

1. Write the transform as a top-level function (mechanical, deterministic, idempotent). Use `_wiki_yaml.apply_frontmatter()` for additive field changes — it preserves untouched lines byte-for-byte. For removals, use `_wiki_yaml._split_frontmatter()` + `_split_into_blocks()` to keep body separators intact.
2. Register both directions:

```python
_MIGRATION_RECIPES[("1.0", "1.1")] = [_migrate_source_summary_add_http_signals]
_MIGRATION_RECIPES[("1.1", "1.0")] = [_migrate_source_summary_strip_http_signals]
```

3. Add a round-trip test in `test_wiki_stubs.py`: `1.0 → 1.1 → 1.0` must be byte-identical to the pre-migration source on a representative fixture.

### Reference recipe — 1.0 → 1.1 (source-summary HTTP signals)

The shipped recipe adds optional `etag`, `last-modified`, `content-hash` fields to every `page-type: source-summary` page so the wiki-source-refresh quick-check tier can compare HEAD response headers against stored values. Pages of other page-types are returned unchanged. The reverse recipe strips the three fields and restores `schema-version: 1.0`. Both directions are exercised by `WikiSchemaMigration1To11Tests`.
