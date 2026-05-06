---
name: "Tooling Glossary"
type: wiki
cluster: "Engineering"
version: 1.0.0
status: active
created: 2026-03-01
last-updated: 2026-03-01
domain: "Definitions of internal tooling terms"
exclusively-owns:
  - Definitions of internally-coined tooling terms
strictly-avoids:
  - Vendor-specific terms (those belong on the vendor's source-summary page)
page-type: glossary
last-reviewed: 2026-03-01
builds-on: []
references: []
provides: []
provenance:
  kind: inbox-promotion
  source: docs/_inbox/2026-03-01_tooling-terms.md
  captured-on: 2026-03-01
  promoted-by: gunti
---

_Canonical knowledge: this glossary explains internal terminology — for the underlying tools see their respective source-summary pages._

## Terms

**Green/blue swap** — Production traffic is shifted between two identical environments to enable zero-downtime deploys.

**Production-candidate** — Image tag applied after build but before scan-pass.
