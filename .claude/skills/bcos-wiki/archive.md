# /wiki archive — soft-delete a wiki page

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Invocation

```text
/wiki archive <slug> [--reason "<short reason>"]
```

Archive is the default removal path. It preserves the page and raw evidence, checks dangling references, regenerates the derived index, and records the action in `log.md`.

## Flow

1. Resolve `<slug>` under `docs/_wiki/pages/` or `docs/_wiki/source-summary/`.
2. Scan wiki pages, `overview.md`, and `queue.md` for:
   - `[[<slug>]]`
   - markdown links to the page path
   - frontmatter `references:`, `subpages:`, or `parent-slug:` pointing at `<slug>`
3. If references exist, report them first. Continue only when the user explicitly confirms archive despite dangling references.
4. Move the page to `docs/_wiki/.archive/<YYYY-MM-DD>_<slug>.md`.
5. Update its frontmatter:
   - `status: archived`
   - `last-updated: {{TODAY}}`
   - add or update `archived-on: {{TODAY}}`
   - add or update `archive-reason: "<reason>"`
6. Keep raw files in place unless the user also requested `/wiki remove`.
7. Run `python .claude/scripts/refresh_wiki_index.py`.
8. Append a log entry.

## Output

```text
Archived: <slug>

  Moved:      docs/_wiki/{pages|source-summary}/<slug>.md
          -> docs/_wiki/.archive/<YYYY-MM-DD>_<slug>.md
  References: <N> dangling reference(s) reported
  Index:      regenerated
  Log:        docs/_wiki/log.md
```

No agent commits. See `SKILL.md`.
