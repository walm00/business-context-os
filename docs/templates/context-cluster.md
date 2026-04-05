# Context Cluster Template

> A cluster groups related data points that share a common theme. Copy this file, rename it to match your cluster (e.g., `brand-and-identity.md`), and fill in each section.

---

```yaml
# --- Cluster Metadata ---
cluster-name: "Your Cluster Name"       # e.g., "Brand & Identity"
purpose: ""                              # One sentence: what strategic area does this cluster serve?
version: "1.0.0"
last-updated: "YYYY-MM-DD"
cluster-owner: "Name or Role"           # Who is accountable for this cluster's health?
```

---

## Cluster Purpose

<!-- Describe in 2-3 sentences what this cluster exists to capture.
     What strategic questions does it answer?
     Example: "This cluster captures everything about who we are as a brand --- our identity,
     voice, and story. It answers: What do we stand for? How do we express ourselves?" -->

---

## Data Points in This Cluster

<!-- List every data point that belongs to this cluster. -->

| Data Point | Domain Summary | Owner | Status |
|------------|---------------|-------|--------|
| <!-- e.g., brand-identity --> | <!-- e.g., Core brand attributes, mission, vision, story --> | <!-- e.g., Brand Lead --> | <!-- active --> |
| <!-- e.g., brand-voice --> | <!-- e.g., Tone, personality, writing style guidelines --> | <!-- e.g., Content Lead --> | <!-- active --> |
| | | | |
| | | | |

---

## Cluster Boundaries

### What This Cluster Covers
<!-- Be specific about what falls inside this cluster's scope. -->
- <!-- e.g., "Brand identity elements: mission, vision, values, story" -->
- <!-- e.g., "Brand expression: voice, tone, personality" -->

### What This Cluster Does NOT Cover
<!-- Explicitly state what belongs to other clusters to prevent scope creep. -->
- <!-- e.g., "Customer data and audience profiles (see: Audience & Market cluster)" -->
- <!-- e.g., "Product features and pricing (see: Product & Value cluster)" -->

---

## Internal Relationships

<!-- How do data points WITHIN this cluster connect to each other? -->

### Data Flow Within Cluster

<!-- Describe how information moves between data points in this cluster.
     Example:
     - brand-identity PROVIDES brand personality traits TO brand-voice
     - brand-voice REFERENCES brand-identity for personality alignment -->

| From | To | Relationship |
|------|----|-------------|
| <!-- e.g., brand-identity --> | <!-- e.g., brand-voice --> | <!-- e.g., Personality traits guide voice development --> |
| | | |
| | | |

### Key Dependencies
<!-- Which data point must exist first? What's the natural build order? -->
1. <!-- e.g., "brand-identity must be established before brand-voice can be defined" -->
2. <!-- e.g., "brand-voice should be finalized before messaging-framework is built" -->

---

## Cross-Cluster Dependencies

<!-- How does this cluster relate to other clusters? -->

### This Cluster Provides To
<!-- What does this cluster output to other clusters? -->

| Receiving Cluster | What It Receives | Specific Data Points |
|-------------------|-----------------|---------------------|
| <!-- e.g., Audience & Market --> | <!-- e.g., Brand positioning context --> | <!-- e.g., brand-identity provides positioning foundation --> |
| | | |

### This Cluster Depends On
<!-- What does this cluster need from other clusters? -->

| Source Cluster | What It Provides | Specific Data Points |
|----------------|-----------------|---------------------|
| <!-- e.g., Audience & Market --> | <!-- e.g., Customer understanding shapes brand story --> | <!-- e.g., customer-insights informs brand-identity --> |
| | | |

---

## Cluster Health

### Completeness Check
- [ ] All data points listed above have been created
- [ ] Every data point has an assigned owner
- [ ] Ownership specs are complete (no gaps or overlaps between data points)
- [ ] Internal relationships are documented
- [ ] Cross-cluster dependencies are confirmed with other cluster owners

### Review Schedule
- **Cluster review frequency:** <!-- e.g., "Quarterly" -->
- **Next scheduled review:** <!-- YYYY-MM-DD -->
- **Review led by:** <!-- Name or Role -->
