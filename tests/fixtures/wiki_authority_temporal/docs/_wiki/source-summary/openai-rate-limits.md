---
name: "OpenAI Rate Limits"
type: wiki
cluster: "Engineering"
version: 1.0.0
status: active
created: 2026-04-15
last-updated: 2026-04-15
domain: "OpenAI rate limit documentation summary"
exclusively-owns:
  - Rate-limit specifics from the OpenAI docs page
strictly-avoids:
  - Pricing (lives on a separate source-summary)
page-type: source-summary
last-reviewed: 2026-04-15
source-url: https://platform.openai.com/docs/guides/rate-limits
last-fetched: 2026-04-15
detail-level: brief
builds-on: []
references: []
provides: []
provenance:
  kind: url-fetch
  source: https://platform.openai.com/docs/guides/rate-limits
  captured-on: 2026-04-15
---

_All claims below are sourced from `../raw/web/openai-rate-limits.md` unless otherwise noted._

## What it does

OpenAI's rate limit policies for production accounts.

## Key features

- Tier-1 default: 500 requests / minute
- Higher tiers unlock with payment history

## When to use

Capacity planning.
