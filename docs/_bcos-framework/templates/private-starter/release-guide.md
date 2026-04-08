# Release Guide

Your private release workflow. Customize this for your project.

---

## Versioning (Semver)

```
v1.2.3
│ │ └── PATCH: bug fixes, typos, small tweaks
│ └──── MINOR: new features, non-breaking changes
└────── MAJOR: breaking changes (users need to adjust)
```

## When to Release

- A coherent set of improvements is merged and stable
- You've tested the changes work together
- The accumulated changes are worth announcing

## Release Notes Template

```markdown
## What's New

- **[Feature]** — [one-line user benefit]

## Improvements

- [What's better now]

## Fixes

- [What was broken → fixed]
```

## Checklist

- [ ] All changes merged to main
- [ ] CI passes
- [ ] Version number follows semver
- [ ] Release notes written (user perspective)
- [ ] No sensitive content in committed files
