# Context Architecture Canvas

> This is your master planning document. It gives you a bird's-eye view of your entire context architecture: every cluster, every data point, how they connect, and who maintains them. Fill this out before creating individual files, then use it as your ongoing reference.

---

## 1. Organization Overview

**Organization name:** <!-- e.g., "Acme Co" -->

**What you do:** <!-- One sentence. e.g., "B2B SaaS for mid-market project management" -->

**Who you serve:** <!-- One sentence. e.g., "Operations and project leads at 50-500 person companies" -->

**Stage:** <!-- e.g., "Growth-stage startup", "Established mid-market", "Enterprise" -->

**Why you're building a context architecture:**
<!-- What problem are you solving? Examples:
     - "Our brand knowledge lives in people's heads, not in shared docs"
     - "Different teams give different answers about who we are"
     - "We need to onboard new agencies and team members faster"
     - "Our messaging is inconsistent across channels" -->

---

## 2. Cluster Planning

<!-- Identify the major categories of knowledge your organization needs to manage.
     Start with 2-4 clusters. You can always add more later. -->

### Planned Clusters

| # | Cluster Name | Purpose | Owner | Priority |
|---|-------------|---------|-------|----------|
| 1 | <!-- e.g., Brand & Identity --> | <!-- What strategic area does it serve? --> | <!-- Name/Role --> | <!-- High/Medium/Low --> |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

### Cluster Sequencing
<!-- Which cluster should you build first? Why? -->
1. **Start with:** <!-- e.g., "Brand & Identity --- foundational, everything else builds on it" -->
2. **Then:** <!-- e.g., "Audience & Market --- needed to validate brand decisions" -->
3. **Then:** <!-- e.g., "Product & Value --- connects brand to what you sell" -->

---

## 3. Data Point Inventory

<!-- List every data point you plan to create across all clusters. -->

| # | Data Point Name | Cluster | Owner | Status | Priority |
|---|----------------|---------|-------|--------|----------|
| 1 | <!-- e.g., brand-identity --> | <!-- Brand & Identity --> | <!-- Brand Lead --> | <!-- planned --> | <!-- High --> |
| 2 | <!-- e.g., target-audience --> | <!-- Audience & Market --> | <!-- Marketing Dir --> | <!-- planned --> | <!-- High --> |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |
| 9 | | | | | |
| 10 | | | | | |

---

## 4. Relationship Map

<!-- Document how data points connect across your architecture.
     This prevents duplication and shows information flow. -->

### Cross-Data-Point Relationships

| From Data Point | To Data Point | Relationship Type | Description |
|----------------|--------------|-------------------|-------------|
| <!-- e.g., brand-identity --> | <!-- brand-voice --> | PROVIDES | <!-- Brand personality traits guide voice --> |
| <!-- e.g., customer-insights --> | <!-- brand-identity --> | BUILDS_ON | <!-- Pain points shape brand story --> |
| <!-- e.g., target-audience --> | <!-- messaging-framework --> | REFERENCES | <!-- Audience segments inform message targeting --> |
| | | | |
| | | | |
| | | | |

### Relationship Types
- **PROVIDES:** Source creates outputs that the destination needs
- **BUILDS_ON:** Destination is built using content from the source
- **REFERENCES:** Destination reads the source for context but doesn't depend on it

### Dependency Diagram (Text)
<!-- Sketch your architecture in plain text. Example:

    brand-identity ──PROVIDES──> brand-voice
         │                           │
         │                           ├──PROVIDES──> messaging-framework
         │                           │
    BUILDS_ON                   REFERENCES
         │                           │
    customer-insights          target-audience
-->

```
<!-- Draw your diagram here -->
```

---

## 5. Maintenance Schedule

<!-- Assign review responsibilities across your team. -->

### Ownership Matrix

| Data Point | Owner | Review Frequency | Next Review Date |
|-----------|-------|-----------------|-----------------|
| <!-- e.g., brand-identity --> | <!-- Brand Lead --> | <!-- Quarterly --> | <!-- YYYY-MM-DD --> |
| | | | |
| | | | |
| | | | |

### Cluster-Level Reviews

| Cluster | Review Lead | Frequency | Next Review |
|---------|-----------|-----------|-------------|
| <!-- e.g., Brand & Identity --> | <!-- Brand Lead --> | <!-- Quarterly --> | <!-- YYYY-MM-DD --> |
| | | | |
| | | | |

### Annual Architecture Review
- **Date:** <!-- e.g., "January, aligned with annual planning" -->
- **Led by:** <!-- Name/Role -->
- **Scope:** Full architecture health, add/remove clusters, reassign ownership

---

## 6. Growth Plan

<!-- Context architectures should grow over time. Plan what to add next. -->

### Phase 1: Foundation (Now)
<!-- What are you building first? List the clusters and data points. -->
- Cluster: <!-- e.g., Brand & Identity -->
  - Data points: <!-- e.g., brand-identity, brand-voice -->
- Cluster: <!-- e.g., Audience & Market -->
  - Data points: <!-- e.g., target-audience, customer-insights -->

### Phase 2: Expansion (Next Quarter)
<!-- What will you add once the foundation is solid? -->
- Cluster: <!-- e.g., Product & Value -->
  - Data points: <!-- e.g., value-proposition, competitive-positioning -->
- New cluster: <!-- e.g., "Content & Channel Strategy" -->

### Phase 3: Maturity (6+ Months)
<!-- What does a mature architecture look like for your organization? -->
- Additional clusters: <!-- e.g., "Sales Enablement", "Culture & Employer Brand" -->
- Automation: <!-- e.g., "Trigger-based reviews connected to product launch calendar" -->
- Integration: <!-- e.g., "Context architecture feeds into agency briefs, onboarding docs" -->

### Parking Lot
<!-- Ideas for data points or clusters you're not ready to build yet. -->
- <!-- e.g., "Employer brand data point --- needed when hiring ramps up" -->
- <!-- e.g., "Channel strategy cluster --- add when we expand beyond 3 channels" -->
- <!-- e.g., "Partner ecosystem data point --- relevant after first partnership" -->
