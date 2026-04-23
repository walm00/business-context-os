# Contributing to CLEAR Context OS

Thank you for your interest in contributing! Whether you've found a better way to structure context, built a useful skill, or improved the docs — we welcome your input.

## Getting Started

1. **Fork** the repo
2. **Branch** off `dev` (never commit directly to `main` or `dev`)
3. **Make your changes** on your feature branch
4. **Open a PR** targeting `dev`

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/business-context-os.git
cd business-context-os
git checkout -b feature/your-feature dev
```

No build step required. BCOS is documentation and Python scripts — no compilation, no dependencies beyond Python 3.6+.

## What to Contribute

### Lessons (Easiest)

The fastest way to improve CLEAR Context OS is through lessons learned. As you use the system, it captures what works and what doesn't in `.claude/quality/ecosystem/lessons.json`. If you discover a universal pattern — not specific to your situation — contribute it back.

### Skills

New skills for context workflows. Follow the skill anatomy in `docs/_bcos-framework/architecture/component-standards.md`:
- YAML frontmatter with name, description, WHEN TO USE
- Purpose section (IS / IS NOT)
- Numbered workflow steps
- Integration with Other Skills section

### Patterns

Project-type Data Point Maps (client project, GTM, internal tool, etc.) live under `docs/_bcos-framework/patterns/`. Follow the shape of the existing files — one markdown file per project type, with the data-point inventory and ownership grid.

### Documentation

Improvements to guides, methodology, or templates. Accuracy and clarity matter more than volume.

## Standards

- **Follow CLEAR principles** in everything you contribute
- **YAML frontmatter** on all managed documents
- **Kebab-case** for file and directory names
- **One owner per concept** — don't create overlapping data points
- **Reference, don't duplicate** — link to existing content

## Pull Request Process

1. Describe what changed and why
2. Reference any related issues
3. Ensure all docs have proper frontmatter
4. Target `dev` branch (not `main`)

PRs are reviewed for CLEAR compliance, consistency with existing patterns, and clarity.

## Architecture Docs

If you want to understand HOW the system is built before contributing, start with `docs/_bcos-framework/architecture/system-design.md`. The architecture docs explain design decisions, the skill graph, and component standards.

## Questions?

Open an issue with the "question" label or start a Discussion.
