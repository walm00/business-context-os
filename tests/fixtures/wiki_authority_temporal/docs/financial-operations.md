---
name: "Financial Operations"
type: context
cluster: "Finance"
version: 1.0.0
status: active
created: 2026-01-15
last-updated: 2026-01-15
domain: "Day-to-day financial operations including payment processor terms"
exclusively-owns:
  - Negotiated payment processor rates
  - Invoicing cadence
strictly-avoids:
  - Public pricing pages of vendors (those live in _wiki/source-summary/)
---

# Financial Operations

## Payment processor

We use Stripe. Our negotiated rate is **2.5% + 25¢** per transaction (effective 2026-01-15, 24-month contract).

## Invoicing

Net-30 default; net-15 for new clients.
