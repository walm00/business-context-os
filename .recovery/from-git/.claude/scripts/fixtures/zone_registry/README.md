# Zone Registry Test Fixtures

Synthetic `docs/` tree covering every zone `.claude/scripts/context_index.py` classifies.

Used by `test_zone_registry.py` to assert that the zones declared in
`docs/_bcos-framework/templates/_context-zones.yml.tmpl` agree with the zones
`context_index.py._zone_for()` returns when run over this fixture.

**Layout — one minimal `.md` per zone:**

| Fixture path | Expected zone |
|---|---|
| `docs/sample-active.md` | `active` |
| `docs/_bcos-framework/architecture/sample-framework.md` | `framework` |
| `docs/_wiki/pages/sample-wiki-page.md` | `wiki` |
| `docs/_wiki/source-summary/sample-source-summary.md` | `wiki` |
| `docs/_wiki/index.md` | `generated` (hardcoded in `GENERATED_PATHS`) |
| `docs/_wiki/raw/sample-raw.md` | `wiki-internal` |
| `docs/_collections/sample-col/_manifest.md` | `collection-manifest` |
| `docs/_collections/sample-col/sample-artifact.txt.meta.md` | `collection-sidecar` |
| `docs/_collections/sample-col/sample-note.md` | `collection-artifact` |
| `docs/_inbox/sample-inbox.md` | `inbox` |
| `docs/_planned/sample-planned.md` | `planned` |
| `docs/_archive/sample-archive.md` | `archive` |
| `docs/_custom-folder/sample-custom.md` | `custom-optout` |
| `docs/document-index.md` | `generated` |

Each fixture file is the smallest valid frontmatter+body that passes context_index.py
parsing without warnings (where the zone requires base metadata).

**Drift contract:** if `context_index.py._zone_for()` learns a new zone, add a
fixture here AND a matching entry to `_context-zones.yml.tmpl`. The test fails
loudly otherwise.
