# Context Maintenance Checklist

> Use this checklist to keep your context architecture accurate and alive. Stale context is worse than no context --- it gives teams false confidence in outdated information.

---

## Weekly Quick Check (5 minutes)

**When:** Every Monday morning (or pick a consistent day)
**Who:** Each data point owner checks their own data points

- [ ] Did anything happen this week that affects my data points?
  - New product announcements
  - Customer feedback that shifts understanding
  - Competitive moves
  - Internal strategy changes
  - Team or leadership changes
- [ ] If yes: flag the affected data point for update (change status to `under-review`)
- [ ] If no: no action needed

**Tip:** Set a recurring 5-minute calendar reminder. Most weeks, the answer is "nothing changed" and you're done in 60 seconds.

---

## Monthly Review (30 minutes)

**When:** First week of each month
**Who:** Rotate through cluster owners (one cluster per month)

### Cluster Audit
- [ ] Pick one cluster to review this month: _______________
- [ ] Open each data point in the cluster and verify:
  - [ ] **Accuracy:** Is the content still true? Any facts that have changed?
  - [ ] **Completeness:** Is anything missing that should be captured?
  - [ ] **Ownership boundaries:** Are the EXCLUSIVELY_OWNS and STRICTLY_AVOIDS sections still correct? Any new overlaps?
  - [ ] **Relationships:** Do the BUILDS_ON, REFERENCES, and PROVIDES connections still make sense?
  - [ ] **Version and date:** Update `last-updated` in frontmatter if any changes were made

### Cross-Check
- [ ] Ask one person from a different team: "Does this cluster still match your understanding?" (5-minute conversation)
- [ ] Note any discrepancies for correction

### Monthly Log
| Month | Cluster Reviewed | Issues Found | Actions Taken | Reviewed By |
|-------|-----------------|-------------|---------------|-------------|
| | | | | |

---

## Quarterly Deep Review (2 hours)

**When:** End of each quarter
**Who:** Architecture owner + all cluster owners

### Architecture Health Check

#### Completeness
- [ ] Are all data points still relevant? Should any be archived?
- [ ] Are there gaps --- knowledge that exists in people's heads but not in a data point?
- [ ] Should any new data points be created?
- [ ] Should any new clusters be added?

#### Accuracy
- [ ] Has any data point gone stale (not updated in 3+ months and the domain has changed)?
- [ ] Are there contradictions between data points?
- [ ] Does the context architecture reflect the company's current strategy, not last quarter's?

#### Ownership
- [ ] Does every data point have a current, active owner?
- [ ] Have any owners changed roles or left the team? Reassign immediately.
- [ ] Are ownership boundaries clear? Any disputes or gray areas?

#### Relationships
- [ ] Review the relationship map in your architecture canvas
- [ ] Are there new dependencies that need documenting?
- [ ] Are there relationships that no longer exist?

#### Usage
- [ ] Is the team actually using the context architecture? Ask around.
- [ ] What's working well? What's friction?
- [ ] Are there formats or structures that need improvement?

### Quarterly Summary
| Quarter | Data Points Reviewed | Added | Archived | Ownership Changes | Key Decisions |
|---------|---------------------|-------|----------|-------------------|---------------|
| | | | | | |

---

## Trigger-Based Reviews

> These events should prompt an immediate review --- don't wait for the next scheduled check.

### Product & Offering Changes
- [ ] **New product or service launch** --- Review: value-proposition, messaging-framework, competitive-positioning
- [ ] **Product sunset or discontinuation** --- Review: value-proposition, messaging-framework
- [ ] **Pricing change** --- Review: value-proposition, competitive-positioning
- [ ] **Major feature release** --- Review: value-proposition, customer-insights

### Brand & Identity Changes
- [ ] **Rebrand or visual identity refresh** --- Review: brand-identity, brand-voice, messaging-framework
- [ ] **New brand campaign** --- Review: messaging-framework, brand-voice
- [ ] **Mission or vision update** --- Review: brand-identity (then cascade to all data points that REFERENCE it)

### Market Changes
- [ ] **New competitor enters the market** --- Review: competitive-positioning, market-context
- [ ] **Major competitor move** (acquisition, pivot, new product) --- Review: competitive-positioning
- [ ] **Industry regulation change** --- Review: market-context, value-proposition
- [ ] **Market shift or disruption** --- Review: market-context, competitive-positioning

### Audience & Customer Changes
- [ ] **New customer segment identified** --- Review: target-audience, messaging-framework
- [ ] **Major customer feedback pattern** --- Review: customer-insights, value-proposition
- [ ] **Customer churn spike** --- Review: customer-insights, value-proposition

### Organizational Changes
- [ ] **Leadership change** --- Review: brand-identity (mission/vision), architecture ownership
- [ ] **Team restructuring** --- Review: all ownership assignments
- [ ] **Merger or acquisition** --- Review: entire architecture
- [ ] **New agency or partner onboarded** --- Verify architecture is up-to-date for handoff

---

## Red Flags: Immediate Review Required

> If you notice any of these, stop and fix the context architecture before it causes downstream problems.

- [ ] **Two teams giving different answers** about the same topic (e.g., different descriptions of the target audience)
- [ ] **A data point hasn't been updated in 6+ months** and the business has changed
- [ ] **Nobody knows who owns a data point** --- ownership has lapsed
- [ ] **A new hire reads a data point and says "this doesn't match what I was told"**
- [ ] **An agency or partner produces work that contradicts your context** --- the brief was built on stale data
- [ ] **A data point owner says "I didn't know that was my responsibility"** --- ownership spec needs clarification
- [ ] **Conflicting information exists** between two data points (e.g., brand-identity says one thing about values, messaging-framework implies different values)

### Red Flag Response
1. Flag the affected data point(s) --- change status to `under-review`
2. Notify the data point owner(s)
3. Schedule a 30-minute review within the current week
4. Update content, re-verify ownership boundaries
5. Communicate changes to affected teams
6. Log the incident in the quarterly summary

---

## Annual Planning Alignment

**When:** During annual strategic planning
**Who:** Architecture owner + senior leadership

- [ ] Does the architecture still match the company's strategic direction?
- [ ] Are new clusters needed for new strategic priorities?
- [ ] Should any clusters be retired?
- [ ] Update the Growth Plan in the Architecture Canvas
- [ ] Set ownership and review schedules for the new year
