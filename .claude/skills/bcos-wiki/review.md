# /wiki review — mark a wiki page reviewed

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Invocation

```text
/wiki review <slug> [--notes "<short note>"]
```

Use this after a human has checked a page against its `builds-on:` data points or source material. This is a metadata operation, not a rewrite.

## Flow

1. Resolve `<slug>` to exactly one page under `docs/_wiki/pages/` or `docs/_wiki/source-summary/`.
2. If no page exists, stop and suggest `/wiki lint` to list known slugs.
3. If more than one page exists, stop and ask the user to pick the folder-specific path.
4. Read frontmatter and update:
   - `last-reviewed: {{TODAY}}`
   - `last-updated: {{TODAY}}` only when review notes or metadata changed.
5. If the page has `builds-on:`, read each target and report any target with `last-updated > previous last-reviewed`.
6. Append one entry to `docs/_wiki/log.md`:

```markdown
## {{TODAY}} | review | {{slug}} | reviewed against upstream context

- Page: docs/_wiki/{pages|source-summary}/{{slug}}.md
- Previous last-reviewed: {{OLD_DATE}}
- Notes: {{NOTES_OR_NONE}}
```

7. Run the frontmatter hook for the page. If it reports `schema-violation`, `reference-format-mismatch`, or `forbidden-builds-on-target`, surface the issue and leave the metadata change in place for review.

## Output

```text
Reviewed: <slug>

  Page:           docs/_wiki/{pages|source-summary}/<slug>.md
  Last-reviewed:  <old> -> <today>
  Upstream drift: <N> builds-on target(s) newer than prior review
  Log:            docs/_wiki/log.md
```

No agent commits. See `SKILL.md`.
