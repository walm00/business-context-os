# Maintenance Guide

**How to keep your context alive. This is what separates a useful system from another abandoned document.**

---

## Why Context Dies

Every organization has a graveyard of abandoned documents. Brand guides nobody reads. Strategy decks from two quarters ago. Audience profiles that describe customers you no longer serve. These documents did not fail because they were bad. They failed because nobody maintained them.

Context dies in five specific ways. Understanding them is the first step to preventing them.

### 1. Neglect

**What it looks like:** A data point was created, used enthusiastically for a month, and then forgotten. Six months later, it describes a business that no longer exists.

**Why it happens:** No clear ownership boundaries were defined. It was "everyone's topic," which means nobody knew what it covered or what belonged elsewhere.

**How to prevent it:** Every data point has a clear Ownership Specification -- a defined DOMAIN, EXCLUSIVELY_OWNS list, and STRICTLY_AVOIDS boundaries. When the topic boundaries are explicit, maintenance responsibility is obvious.

### 2. Drift

**What it looks like:** The same concept exists in multiple places, and the versions have slowly diverged. Your website says one thing about your audience, your sales deck says something slightly different, and your brand guide says a third thing. All three were correct at some point. None are correct now.

**Why it happens:** People copy information instead of referencing the source. Each copy evolves independently.

**How to prevent it:** One data point owns each concept. Everything else references it. When the source changes, it changes in one place.

### 3. Accumulation

**What it looks like:** Data points grow and grow, absorbing related content, edge cases, historical notes, and "might be useful" information until they are too long to scan and too broad to trust.

**Why it happens:** Adding is easy. Removing feels risky. So content piles up.

**How to prevent it:** STRICTLY_AVOIDS boundaries prevent accumulation. Regular reviews actively remove outdated content. Removing stale context is as important as adding new context.

### 4. Ownership Vacuum

**What it looks like:** A data point's Ownership Specification has gone stale -- the DOMAIN no longer reflects what the business actually needs, or the EXCLUSIVELY_OWNS list no longer matches reality. The data point is effectively orphaned.

**Why it happens:** Ownership boundaries are not reviewed when the business evolves. New topics emerge that no data point claims, or existing boundaries no longer make sense.

**How to prevent it:** Review Ownership Specifications during quarterly deep reviews. When the business changes, update DOMAIN and EXCLUSIVELY_OWNS to match current reality. Ensure no topic falls outside all data points' boundaries.

### 5. Change Blindness

**What it looks like:** The real world has changed, but the context has not caught up. You launched a new product three months ago, but your value proposition still describes the old offering. A competitor was acquired, but your competitive landscape still lists them as independent.

**Why it happens:** Business changes happen in meetings, Slack messages, and quick decisions. They do not automatically flow into context documents.

**How to prevent it:** Trigger-based reviews. Specific business events automatically prompt a context review. See the trigger list later in this guide.

---

## The Maintenance Rhythm

Maintenance is a habit, not a project. Build it into your team's routine with this three-tier rhythm.

**Want Claude to do this automatically?** See [scheduling.md](./scheduling.md) to set up recurring scheduled tasks that run these checks without you having to remember.

### Weekly: Quick Scan (5 minutes)

**When:** Pick a consistent day. Monday morning works well.

**Who:** Each data point owner checks their own data points.

**What to do:**

Ask yourself one question: **Did anything happen this week that affects my data points?**

- New product announcements
- Customer feedback that shifts understanding
- Competitive moves
- Internal strategy changes
- Team or leadership changes

If yes: flag the affected data point for update.
If no: you are done. Most weeks, this takes 60 seconds.

**Tip:** Set a recurring 5-minute calendar reminder. The habit matters more than the duration.

### Monthly: Cluster Audit (30 minutes)

**When:** First week of each month.

**Who:** Rotate through cluster owners. Review one cluster per month.

**What to do:**

Pick one cluster to review. Open each data point in that cluster and check:

1. **Accuracy** -- Is the content still true? Have any facts changed?
2. **Completeness** -- Is anything missing that should be captured?
3. **Boundaries** -- Are the EXCLUSIVELY_OWNS and STRICTLY_AVOIDS sections still correct? Any new overlaps creeping in?
4. **Relationships** -- Do the BUILDS_ON, REFERENCES, and PROVIDES connections still make sense?
5. **Freshness** -- Update the "last updated" date if any changes were made.

After checking the data points, do one cross-check: ask someone from a different team whether this cluster still matches their understanding. A 5-minute conversation. Note any discrepancies.

### Quarterly: Deep Review (2 hours)

**When:** End of each quarter.

**Who:** The architecture owner plus all cluster owners.

**What to review:**

**Completeness**
- Are all data points still relevant? Should any be archived?
- Are there gaps -- knowledge that exists in people's heads but not in a data point?
- Should any new data points or clusters be created?

**Accuracy**
- Has any data point gone stale (not updated in 3+ months while the business has changed)?
- Are there contradictions between data points?
- Does the architecture reflect your CURRENT strategy, not last quarter's?

**Ownership**
- Does every data point have a current, well-defined Ownership Specification?
- Have any DOMAIN or EXCLUSIVELY_OWNS boundaries gone stale? Update immediately.
- Are boundaries clear? Any disputes or gray areas?

**Relationships**
- Review the relationship map in your architecture canvas.
- Are there new dependencies that need documenting?
- Are there relationships that no longer exist?

**Usage**
- Is the team actually using the context architecture? Ask around.
- What is working? What is causing friction?
- Are there structures or formats that need improvement?

---

## Using Claude for Maintenance

Claude can help you maintain your context. Here are specific things you can ask.

### Audit a data point

Ask Claude to review a specific data point for accuracy and completeness:

- "Review my Brand Identity data point. Is anything outdated or missing?"
- "Check my Target Audience -- does it still accurately describe who we serve?"
- "Audit my Value Proposition for consistency with what our website says."

### Check boundaries

Ask Claude to look for overlap and boundary violations:

- "Is there overlap between my Messaging Framework and my Brand Voice?"
- "Does my Target Audience contain any information that should be in Customer Pain Points?"
- "Check all my data points for content that has drifted outside its boundaries."

### Identify drift

Ask Claude to compare your context against other sources:

- "Compare what my Value Proposition says vs. what our website homepage says."
- "Does my Brand Identity match the 'About Us' section on our website?"
- "Are there contradictions between my Target Audience and my Messaging Framework?"

### Plan updates after changes

Ask Claude to help you trace the impact of a business change:

- "I am launching a new product next month. Which data points need updating?"
- "We just hired a new VP of Marketing. What context ownership needs to transfer?"
- "A major competitor just pivoted. Walk me through what to review."

### Run a maintenance check

Ask Claude to run through the maintenance checklist:

- "Run a weekly quick scan across all my data points."
- "Do a monthly audit of my Brand & Identity cluster."
- "Help me prepare for my quarterly deep review."

---

## When Things Change

Business changes are the #1 trigger for context updates. Here is a guide to which data points to review for common changes.

### New Product Launch

| Review This | Because |
|---|---|
| Value Proposition | New product may change what makes you different |
| Product Description | New product needs to be captured |
| Messaging Framework | New messages needed for launch |
| Target Audience | New product may serve different or additional segments |
| Competitive Landscape | New product changes your competitive position |

### Rebrand

| Review This | Because |
|---|---|
| Brand Identity | Core identity is changing -- this is ground zero |
| Brand Voice | Voice often shifts during a rebrand |
| Messaging Framework | All messages need to reflect new brand |
| Visual Identity | If you have this data point, it is the most affected |
| Value Proposition | Rebrand may reframe how you talk about value |

A rebrand cascades through everything. Start with Brand Identity and work outward through every data point that REFERENCES or BUILDS_ON it.

### New Market Entry

| Review This | Because |
|---|---|
| Market Context | New market dynamics, regulations, trends |
| Target Audience | New or adapted audience segments for this market |
| Competitive Landscape | Different competitors in the new market |
| Messaging Framework | Messages may need localization or adaptation |
| Value Proposition | Value may resonate differently in new market |

You may also need entirely new data points for market-specific context.

### Team Restructure

| Review This | Because |
|---|---|
| All ownership assignments | People may have moved or left |
| Architecture canvas | Review schedule may need updating |
| Cluster ownership | Cluster leads may have changed |

The most important action: **reassign every orphaned data point before anything else.** An unowned data point starts rotting immediately.

### Competitor Shift

| Review This | Because |
|---|---|
| Competitive Landscape | Direct impact -- capture the change |
| Value Proposition | Your differentiation may have shifted |
| Messaging Framework | May need new competitive messaging |
| Market Context | If the shift reflects a broader market trend |

---

## Red Flags

These are signs your context needs immediate attention. Do not wait for the next scheduled review.

**Two teams giving different answers about the same topic.** Example: marketing describes the target audience one way, sales describes it differently. This means either the data point is unclear, not being used, or not being maintained.

**A data point has not been updated in 6+ months and the business has changed.** Stale context is worse than no context. It gives people false confidence in outdated information.

**Nobody knows who owns a data point.** Ownership has lapsed. The data point is orphaned and will rot.

**A new hire reads a data point and says "this does not match what I was told."** Your onboarding is exposing the gap between context and reality. Fix the context.

**An agency or partner produces work that contradicts your context.** They were probably working from stale or incomplete information. Check what they were given.

**Conflicting information exists between two data points.** Example: Brand Identity says one thing about values, Messaging Framework implies different values. This is a boundary violation.

### Red Flag Response

1. Flag the affected data point(s) -- change status to "under-review"
2. Notify the data point owner(s)
3. Schedule a 30-minute review within the current week
4. Update content, re-verify ownership boundaries
5. Communicate changes to affected teams

---

## The Maintenance Mindset

Context is a garden, not a monument.

A monument is built once and admired. It does not change. It does not grow. Eventually it weathers and crumbles, and people stop visiting.

A garden is alive. It grows, changes with the seasons, and requires regular attention. Not hours of work every day -- just consistent, small acts of care. Pull a weed. Water what is growing. Prune what is overgrown. Plant something new when the time is right.

Your context architecture is a garden. The weekly 5-minute scan is pulling weeds. The monthly audit is pruning. The quarterly review is stepping back and asking whether the layout still works. And when your business changes -- a new product, a new market, a new strategy -- that is a new season, and the garden adapts.

The organizations that get the most value from this system are not the ones with the most data points or the most sophisticated architecture. They are the ones who maintain what they have. Consistently. Every week.

Five minutes a week. That is the cost of context that your whole team can trust.

---

**See also:**
- [getting-started.md](./getting-started.md) -- If you have not set up your architecture yet
- [defining-your-context.md](./defining-your-context.md) -- For creating new data points
- [adoption-tiers.md](./adoption-tiers.md) -- For adding automation to your maintenance
- The maintenance checklist template at `docs/templates/maintenance-checklist.md` for a printable version
