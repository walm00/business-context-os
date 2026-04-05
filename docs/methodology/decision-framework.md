# Decision Framework

**Purpose:** When and how to apply CLEAR actions to your organization's context.

---

## The Decision Tree

When you encounter potential duplication, overlap, or confusion in your organizational context, work through these four questions in order:

```
1. Is this truly the same information?
   |-- YES --> Consider consolidation
   |-- NO  --> Different purpose, keep separate

2. Is this pattern stable?
   |-- YES --> Consolidate now
   |-- NO  --> Wait until proven

3. Would consolidation complicate understanding?
   |-- YES --> Keep separate with cross-reference
   |-- NO  --> Consolidate to improve clarity

4. Is this actively maintained by different teams?
   |-- YES --> Keep separate with clear ownership
   |-- NO  --> Consolidate for maintainability
```

### How to Read the Tree

**Question 1** filters out false positives. Two things that LOOK similar often serve different purposes. Your website product description and your investor pitch product description may describe the same product, but they exist for different audiences, are maintained on different schedules, and have different success criteria. They are not duplicates. They are adaptations.

**Question 2** prevents premature consolidation. If a concept is still being debated, shaped, or experimented with, forcing it into a single authority creates more problems than it solves. Wait until the team agrees on what it IS before deciding where it LIVES.

**Question 3** prevents over-abstraction. Sometimes two separate documents are clearer than one combined document, even if they share content. If merging would require constant mental context-switching to understand, the consolidation hurts more than it helps.

**Question 4** respects organizational reality. If two different teams own two different versions and both have legitimate reasons to maintain their own, forcing consolidation creates organizational friction. Instead, give each team clear ownership and establish cross-references.

---

## When to Act: Five Triggers for Context Maintenance

Not every inconsistency needs immediate attention. Here are five specific situations where action is justified:

### 1. The Contradiction Trigger

**What it looks like:** Two documents make conflicting claims about the same fact.

Example: The brand guide says "Founded in 2019." The About page says "Founded in 2020." A prospect notices the discrepancy.

**Action:** Determine which is correct. Update the authority. Update or redirect all downstream references.

**Urgency:** High. Contradictions erode trust with external audiences and create internal confusion.

### 2. The "Which One?" Trigger

**What it looks like:** Someone asks "Which version of X should I use?" and nobody knows the answer.

Example: A new team member needs the target audience definition. They find three documents that each define the audience differently. They ask in Slack which one to use. Nobody responds with confidence.

**Action:** Designate one as the authority. Archive or update the others to reference it.

**Urgency:** Medium-high. This is a sign that ownership is unclear. The longer it persists, the more versions will be created.

### 3. The Drift Trigger

**What it looks like:** You update something in one place and realize the same information exists in other places that are now out of date.

Example: You update the company's value proposition for a new product launch. Afterwards, you realize the old value proposition still lives in the sales deck, the job posting template, and the partner portal.

**Action:** Consolidate the value proposition into one authority. Update downstream documents to reference it.

**Urgency:** Medium. The drift has already happened. Address it before the next update cycle.

### 4. The Bloat Trigger

**What it looks like:** A single document has grown to cover too many topics and is becoming hard to navigate.

Example: Your "Brand Guidelines" started as a focused brand identity document. Over two years, it has absorbed voice guidelines, messaging frameworks, visual identity specs, audience descriptions, and competitive positioning notes. It is now 40 pages long and nobody reads the whole thing.

**Action:** Split into multiple data points with clear ownership boundaries. See [ownership-specification.md](./ownership-specification.md) for how to define boundaries.

**Urgency:** Medium. Bloat slows everyone down but rarely causes acute crises.

### 5. The New Initiative Trigger

**What it looks like:** A new project, market, or product creates a need for context that does not fit cleanly into existing data points.

Example: Your company is expanding into the German market. Existing data points cover your current (US) market. The German expansion needs market context, regulatory considerations, and localized messaging that do not belong in the existing US-focused documents.

**Action:** Create new data points for the expansion, with clear BUILDS_ON relationships to the existing data points they derive from.

**Urgency:** Low-medium. Address it at the start of the initiative, before ad hoc documents proliferate.

---

## When to Wait: Three Reasons to Leave Things As They Are

Not every imperfection requires immediate action. Here are three situations where waiting is the right choice:

### 1. The Concept Is Still Forming

**What it looks like:** The team is actively debating, experimenting with, or evolving a concept. There is no consensus yet.

Example: Your company is exploring a new positioning strategy. Three different teams have drafted positioning statements. They are deliberately different because the team is testing approaches.

**Why to wait:** Consolidating now would force a premature decision. Let the concept stabilize first. Once the team agrees on the direction, THEN consolidate.

**How to know it is time to act:** When the team stops debating and starts using one version consistently, the concept is stable enough to formalize.

### 2. The Cost Exceeds the Benefit

**What it looks like:** Fixing the issue would require significant effort across multiple teams, but the inconsistency is minor and rarely causes confusion.

Example: Your internal wiki and your sales deck use slightly different wording for the company tagline. The meaning is identical. Nobody has been confused by the difference.

**Why to wait:** Organizational capital is finite. Spend it on changes that matter. A minor wording variation that causes no confusion is not worth a cross-team coordination effort.

**How to know it is time to act:** When the minor inconsistency causes an actual problem (customer confusion, team disagreement, wrong information used in a decision).

### 3. The Owner Is About to Change

**What it looks like:** An organizational restructure, leadership change, or strategic pivot is imminent. The data point's ownership or scope is about to shift.

Example: Your VP of Marketing is leaving next month. The brand strategy they own will be reviewed and potentially revised by their successor.

**Why to wait:** Consolidating now may be wasted effort if the new owner takes a different direction. Focus on documenting the current state clearly so the new owner can make informed decisions.

**How to know it is time to act:** When the new owner is in place and has had time to assess the current state.

---

## The Pragmatic Rule

**Consolidate AFTER a pattern is proven stable. Do not abstract prematurely.**

This is the single most important rule in context management. It is also the most commonly violated.

The temptation is strong: you see the same information in two places and immediately want to consolidate. But if both versions are still evolving, consolidation creates a bottleneck. Changes that should be independent become coupled. Experimentation becomes harder because every change goes through a shared authority.

**The pattern:**

```
Phase 1: Diverge intentionally
  Multiple versions exist because the concept is being explored.
  This is HEALTHY. Do not consolidate.

Phase 2: Converge naturally
  The team gravitates toward one version. Others fall out of use.
  This is the SIGNAL. The concept is stabilizing.

Phase 3: Consolidate deliberately
  Designate the winning version as the authority.
  Update or archive the others.
  Define the ownership specification.
  This is the ACTION.
```

**Premature consolidation is more expensive than temporary duplication.** Duplicates are easy to merge later. A premature abstraction is hard to undo because downstream consumers have already built on it.

---

## Quick Decision Matrix

Use this matrix to prioritize context maintenance work. Assess each potential action on two dimensions: **impact** (how much confusion or risk does this inconsistency create?) and **effort** (how much work is required to fix it?).

```
                     HIGH IMPACT
                         |
    +---------+----------+----------+---------+
    |         |          |          |         |
    |         | BIG WINS |  QUICK   |         |
    |         |          |  WINS    |         |
    |         | Plan it  |  Do it   |         |
    |         | Schedule | now      |         |
    |         | for next |          |         |
    |         | cycle    |          |         |
    +---------+----------+----------+---------+
HIGH EFFORT  |          |          |    LOW EFFORT
    +---------+----------+----------+---------+
    |         |          |          |         |
    |         |  AVOID   | NICE TO  |         |
    |         |          | HAVE     |         |
    |         | Not      | Backlog  |         |
    |         | worth it | for slow |         |
    |         | now      | periods  |         |
    |         |          |          |         |
    +---------+----------+----------+---------+
                         |
                     LOW IMPACT
```

### Quick Wins (High Impact, Low Effort)

Do these now. They deliver immediate clarity with minimal work.

**Examples:**
- Designating one of two existing audience definitions as the authority (just a decision + one redirect)
- Adding a STRICTLY_AVOIDS line to a data point that keeps absorbing unrelated content (one edit)
- Updating a cross-reference that points to an outdated document (one link change)

### Big Wins (High Impact, High Effort)

Plan and schedule these. They are worth the investment but require coordination.

**Examples:**
- Splitting a bloated brand guidelines document into 4 separate data points with ownership specifications
- Consolidating 5 different versions of the value proposition into one authority with downstream updates
- Creating a new cluster of data points for a major business initiative (market expansion, product launch)

### Nice to Have (Low Impact, Low Effort)

Put these on a backlog. Do them during slow periods or when you are already working in the area.

**Examples:**
- Standardizing minor wording differences that cause no confusion
- Adding PROVIDES relationships to well-established data points that have never mapped their downstream consumers
- Cleaning up formatting inconsistencies across data point specifications

### Avoid (Low Impact, High Effort)

Do not spend time on these unless the situation changes.

**Examples:**
- Merging two data points maintained by different teams that work well independently
- Refactoring a context architecture that is working despite being imperfect
- Consolidating experimental content that is still actively being shaped

---

## Putting It All Together

When you notice a context problem:

1. **Identify the trigger.** Which of the five triggers applies? (Contradiction, "Which One?", Drift, Bloat, New Initiative)

2. **Check the wait conditions.** Is the concept still forming? Does the cost exceed the benefit? Is the owner about to change? If yes to any, document the issue and wait.

3. **Run the decision tree.** Is it truly the same information? Is the pattern stable? Would consolidation complicate understanding? Is it maintained by different teams?

4. **Assess impact and effort.** Place it on the Quick Decision Matrix. This tells you WHEN to act, not just WHETHER to act.

5. **Apply the appropriate CLEAR action:**
   - **Ownership unclear?** Define DOMAIN and EXCLUSIVELY_OWNS (C - Contextual Ownership)
   - **Content duplicated?** Consolidate to one authority, redirect others (L - Linking, E - Elimination)
   - **Terminology inconsistent?** Standardize terms in the authority document (A - Alignment)
   - **Structure confusing?** Simplify and restructure for clarity (R - Refinement)

6. **Notify downstream consumers.** Check the PROVIDES keyword of affected data points. Update or notify everyone who depends on what changed.

---

## A Note on Perfectionism

Context architecture is a practice, not a destination. Your context will never be perfectly organized. New inconsistencies will emerge as your business evolves.

The goal is not zero duplication or perfect specification. The goal is that when someone -- a team member, a partner, an AI tool -- needs a specific piece of organizational knowledge, they can find the authoritative version quickly and trust that it is current.

Good enough, maintained consistently, beats perfect but abandoned.

---

**See also:**
- [clear-principles.md](./clear-principles.md) -- The five CLEAR principles
- [context-architecture.md](./context-architecture.md) -- How to structure your data points into clusters
- [ownership-specification.md](./ownership-specification.md) -- The six-keyword specification format
