---
name: YAML Edge Cases
type: wiki
page-type: explainer
cluster: Fixtures
version: 1.0.0
status: active
created: 2026-04-01
last-updated: 2026-05-04
last-reviewed: 2026-05-04
quoted-string: "value with: colon and #hash"
single-quoted: 'value with [brackets]'
empty-value:
inline-list: [a, b, c]
inline-list-with-spaces: [alpha beta, gamma delta]
multi-line-list:
  - first item
  - second item
  - third item with: colon
mixed-case-values:
  - Alpha
  - Beta-Gamma
  - 2026-05-04
references:
  - some-other-page
  - another-page
tags: [yaml, edge-case, fixture]
---

# YAML Edge Cases

Frontmatter with every shape the legacy parsers support. The consolidated
`_wiki_yaml.py` parser must produce the same dict as each of:

- `extract_frontmatter` (post_edit_frontmatter_check.py)
- `parse_frontmatter` (refresh_wiki_index.py)
- the inline parser inside `wiki_schema.py`

A drift test loads this file with all four parsers and asserts they agree on
every required field.
