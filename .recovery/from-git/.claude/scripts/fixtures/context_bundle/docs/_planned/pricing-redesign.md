---
name: Pricing Redesign
type: reference
cluster: Revenue
version: 0.2.0
status: draft
created: 2026-04-25
last-updated: 2026-05-03
tags: [pricing, redesign, proposal]
---

# Pricing Redesign

**DOMAIN:** Proposed new pricing tier names and pricing-page copy.

**EXCLUSIVELY_OWNS:**
- tier-names
- pricing-page-copy

The active `pricing.md` data point currently owns these fields. This planned
proposal reuses the same `EXCLUSIVELY_OWNS` keys to test the conflict
detector — the bundle resolver must flag this as a `source-of-truth-conflicts`
entry and rank `active` above `planned`.
