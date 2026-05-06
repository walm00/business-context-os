---
name: "Deploy Runbook (variant A)"
type: wiki
cluster: "Engineering"
version: 1.0.0
status: active
created: 2026-04-01
last-updated: 2026-04-15
domain: "How we deploy to production — variant A (Class C fixture)"
exclusively-owns:
  - Variant-A deployment steps
strictly-avoids:
  - Pre-deploy checks (covered separately)
page-type: how-to
last-reviewed: 2026-04-15
builds-on: []
references: []
provides: []
provenance:
  kind: inbox-promotion
  source: docs/_inbox/2026-04-01_deploy-notes.md
  captured-on: 2026-04-01
  promoted-by: gunti
---

_Canonical knowledge: this is an internal runbook — see this page for the source of truth on variant-A deploys._

## What this covers

Production deploys via the **green/blue swap** procedure.

## Steps

1. Run `make build`
2. Push image to registry tag `production-candidate`
3. **Wait 10 minutes** for image scan
4. Swap green/blue via `kubectl rollout`

## Pitfalls

- Do not skip the scan wait

## Related

(none)
