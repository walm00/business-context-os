# Document Template

> Copy this file, rename it to match your document (e.g., `brand-identity.md`, `content-approval-process.md`), and fill in each section. Remove all hint comments once complete.
>
> Works for any document type: context, process, policy, reference, or playbook.
> See `docs/methodology/document-standards.md` for full metadata reference.

---

```yaml
---
# --- Required: every document must have these ---
name: "Your Document Name"            # e.g., "Brand Identity", "Content Approval Process"
type: context                         # context | process | policy | reference | playbook
cluster: "Parent Cluster Name"        # e.g., "Brand & Identity", "Operations"
version: "1.0.0"                      # Bump on EVERY change (patch/minor/major)
status: draft                         # draft | active | planned | under-review | archived
owner: "Name or Role"                 # e.g., "Head of Marketing", "Ops Lead"
created: "YYYY-MM-DD"                 # Set once, NEVER change
last-updated: "YYYY-MM-DD"            # MUST update on every edit

# --- Optional: add when useful ---
# tags: [brand, external]
# review-cycle: monthly               # weekly | monthly | quarterly | annual
# next-review: "YYYY-MM-DD"
# depends-on: [other-document-name]
# consumed-by: [downstream-document]
---
```

> **Tip:** Use `status: active` for documents describing current reality. Use `status: planned` for future intent (expansion plans, product ideas, strategic initiatives not yet launched). Use `status: draft` for raw material still being processed — these typically live in `docs/_inbox/`.

---

## Ownership Specification

<!-- The ownership spec prevents overlap between data points. Fill in every field. -->

**DOMAIN:** <!-- One sentence describing what this data point covers. Example: "Core brand attributes, mission, vision, and brand story." -->

**EXCLUSIVELY_OWNS:**
<!-- Bullet list of specific items ONLY this data point is responsible for. Be precise. -->
- <!-- e.g., "Mission statement" -->
- <!-- e.g., "Brand values" -->
- <!-- e.g., "Founding story" -->

**STRICTLY_AVOIDS:**
<!-- Bullet list of items that belong to OTHER data points. Always note which data point owns them. -->
- <!-- e.g., "Taglines and key messages (see: messaging-framework)" -->
- <!-- e.g., "Audience demographics (see: target-audience)" -->

**BUILDS_ON:**
<!-- Other data points whose content feeds INTO this one. Leave empty if none. -->
- <!-- e.g., "customer-insights: pain points inform brand story" -->

**REFERENCES:**
<!-- Other data points this one reads but does not modify. -->
- <!-- e.g., "market-context: industry trends shape brand positioning" -->

**PROVIDES:**
<!-- What this data point outputs to OTHER data points. -->
- <!-- e.g., "brand-voice: brand personality traits guide voice development" -->

---

## Content

<!-- This is the core knowledge section. Write the actual facts, specifics, definitions, and details.
     Be concrete. Avoid vague aspirations. Write what someone new to the team could read and immediately use. -->

### [Subsection 1]
<!-- Organize your content into logical subsections. Example subsections:
     - For brand identity: Mission, Vision, Values, Brand Story
     - For target audience: Primary Segment, Secondary Segment, Firmographics
     - For competitive positioning: Market Position, Differentiation, Competitor Awareness -->

### [Subsection 2]

### [Subsection 3]

---

## Context

<!-- Strategic interpretation. Not just WHAT the facts are, but what they MEAN.
     - Why does this matter for the business?
     - How should teams use this information in their daily work?
     - What decisions does this data point support?
     - What tensions or tradeoffs exist? -->

### Strategic Implications

### Application Guidance
<!-- How should different teams or roles use this data point? -->

---

## Sources

<!-- Optional but recommended. Track where key claims come from.
     Helps verify accuracy during reviews and shows confidence level. -->

| Claim | Source | Date | Confidence |
|-------|--------|------|------------|
| <!-- e.g., "Market growing 15% YoY" --> | <!-- e.g., "Industry Report 2026" --> | <!-- YYYY-MM-DD --> | <!-- High/Medium/Low --> |

<!-- Confidence guide:
     High = verified from authoritative source (official report, signed document, direct observation)
     Medium = from credible but secondary source (news article, team member report, industry estimate)
     Low = inferred, estimated, or from unverified source (conversation, assumption, outdated data) -->

---

## Maintenance

### Review Schedule
<!-- How often should this data point be reviewed? Monthly? Quarterly? -->
- **Regular review:** <!-- e.g., "Quarterly" -->
- **Owner responsible for review:** <!-- e.g., "Brand Lead" -->

### Maintenance Triggers
<!-- Events that should prompt an immediate review, regardless of schedule. -->
- <!-- e.g., "Company rebrand or visual identity refresh" -->
- <!-- e.g., "New product launch that changes value proposition" -->
- <!-- e.g., "Leadership change affecting brand direction" -->
- <!-- e.g., "Merger or acquisition" -->

### Change Log
<!-- Track significant updates. -->
| Date | Version | Change Summary | Changed By |
|------|---------|----------------|------------|
| YYYY-MM-DD | 1.0.0 | Initial creation | Name |
