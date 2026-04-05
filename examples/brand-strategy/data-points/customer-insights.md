# Customer Insights

```yaml
name: "Customer Insights"
cluster: "Audience & Market"
version: "1.1.0"
last-updated: "2026-03-15"
status: "active"
owner: "Customer Research Lead"
```

---

## Ownership Specification

**DOMAIN:** Customer pain points, needs, behaviors, feedback patterns, and satisfaction drivers.

**EXCLUSIVELY_OWNS:**
- Key customer pain points (ranked by frequency and severity)
- Unmet needs and wish-list items
- Behavioral patterns (how customers actually use the product vs. how we expect them to)
- Customer feedback themes (aggregated from support, NPS, interviews, and reviews)
- Satisfaction drivers (what keeps customers renewing)
- Churn indicators (what predicts customer loss)
- Jobs-to-be-done analysis

**STRICTLY_AVOIDS:**
- Audience demographics, firmographics, and segment definitions (see: target-audience)
- Product feature specifications and roadmap (internal documentation)
- Market-level trends and industry analysis (see: market-context)
- Messaging and how to communicate about pain points (see: messaging-framework)

**BUILDS_ON:**
- target-audience: Segment definitions scope where to gather insights (which customers to study)

**REFERENCES:**
- value-proposition: Value claims should be tested against actual customer feedback
- market-context: Market-level trends provide context for customer-level behaviors

**PROVIDES:**
- brand-identity: Customer pain points shape the brand story ("this is why we exist")
- value-proposition: Pain points and needs define what value to emphasize
- messaging-framework: Customer language informs how we write messages
- competitive-positioning: Customer frustrations with alternatives inform differentiation

---

## Content

### Key Pain Points

Ranked by frequency (how often customers mention this) and severity (how much it affects their work). Based on aggregated data from NPS surveys (n=680), customer interviews (n=45), support tickets (2,400 analyzed), and G2/Capterra reviews (320 analyzed). Data as of Q4 2025.

#### Pain Point 1: "I spend my mornings chasing status updates"
- **Frequency:** Mentioned by 78% of prospects during sales calls
- **Severity:** High --- directly costs 6-10 hours per week per operations leader
- **Detail:** Before Acme, operations leaders start every day by checking Slack channels, sending follow-up emails, updating spreadsheets, and sitting in status meetings. They describe this as "managing the management tool" rather than managing projects. The frustration is not that they lack a tool --- it is that their existing tools create more coordination work, not less.
- **Customer quote pattern:** Variations of "I became a full-time status chaser instead of doing my actual job"

#### Pain Point 2: "We bought a tool and nobody uses it"
- **Frequency:** Mentioned by 64% of prospects who are switching from another tool
- **Severity:** High --- sunk cost (financial and political) from failed tool adoption
- **Detail:** The most emotionally charged pain point. Operations leaders who championed a previous tool that failed to get adoption carry a personal scar. They are more cautious about the next purchase, more skeptical of promises, and more focused on adoption evidence than features. This is why adoption metrics are our most powerful sales tool.
- **Customer quote pattern:** Variations of "I can't go back to my team with another tool they won't use"

#### Pain Point 3: "I can't see across projects and teams"
- **Frequency:** Mentioned by 61% of operations leaders
- **Severity:** Medium-High --- leads to blind spots, resource conflicts, missed deadlines
- **Detail:** Individual projects are managed (sometimes well), but there is no cross-project view. An operations leader managing 5-8 concurrent projects has to mentally stitch together status from different spreadsheets, Slack channels, or tool dashboards. They cannot answer simple questions like "which team is overloaded this month?" without spending an hour compiling data.
- **Customer quote pattern:** Variations of "I don't know what I don't know until something blows up"

#### Pain Point 4: "Enterprise tools are overkill for us"
- **Frequency:** Mentioned by 52% of prospects
- **Severity:** Medium --- frustration, wasted budget, team resistance
- **Detail:** Companies that tried enterprise project management tools describe the experience as "bringing a tank to a knife fight." The tools require dedicated administrators, extensive configuration, training programs, and often a change management consultant. Mid-market companies do not have the staff or budget for this. They want something between a to-do list and an enterprise suite.
- **Customer quote pattern:** Variations of "We spent three months configuring it and we're still only using 20% of the features"

#### Pain Point 5: "Our process knowledge lives in people's heads"
- **Frequency:** Mentioned by 43% of customers
- **Severity:** Medium --- creates fragility, slows onboarding, risks knowledge loss
- **Detail:** When a team lead leaves or goes on vacation, their projects stumble because nobody else knows the status, the dependencies, or the unwritten rules. Process knowledge is informal and personal. Customers want a tool that captures enough context that projects survive personnel changes.
- **Customer quote pattern:** Variations of "When Sarah went on maternity leave, three projects stalled because nobody knew what she knew"

### Unmet Needs

Based on feature requests, customer advisory board feedback, and support ticket analysis.

| Need | Priority | Current Workaround | Frequency |
|------|----------|-------------------|-----------|
| Better resource capacity planning across projects | High | Spreadsheets, manual tracking | Requested by 38% of customers |
| Lightweight time tracking tied to projects (not time sheets) | Medium | Separate tools (Toggl, Harvest) | Requested by 29% of customers |
| Client-facing project views (for agencies/services firms) | Medium | Exporting to PDFs, separate dashboards | Requested by 24% of customers |
| Automated weekly summary emails to leadership | Medium | Manual weekly reports | Requested by 22% of customers |
| Integration with finance tools for project cost tracking | Low | Manual reconciliation | Requested by 15% of customers |

### Behavioral Patterns

**How customers actually use Acme (vs. how we designed it):**

| Expected Behavior | Actual Behavior | Implication |
|-------------------|----------------|-------------|
| Teams use detailed project plans with subtasks | Most teams use high-level milestones with check-in updates | Simplify default views; move detailed planning to optional layer |
| Project managers are primary users | Team leads who manage projects part-time are the real users | Design for people who spend 20 minutes/day in the tool, not 4 hours |
| Status meetings are replaced by the tool | Status meetings are shortened, not eliminated. Teams use Acme to prep for shorter meetings. | Position as "better meetings" not "no meetings" |
| Custom workflows are built for each project type | 70% of teams use default templates with minor tweaks | Keep investing in smart defaults; do not push heavy customization |
| Mobile app is used for quick updates | Mobile usage is primarily view-only (checking status) | Prioritize mobile read experience over mobile editing |

### Satisfaction Drivers

What keeps customers renewing (from annual retention analysis, FY2025):

1. **Team adoption held** (mentioned by 89% of renewing customers): "Our team actually uses it" is the #1 reason for renewal.
2. **Visible time savings** (mentioned by 72%): Customers who can point to specific hours saved per week renew at 97%.
3. **Reduced coordination friction** (mentioned by 65%): Fewer "where does this stand?" conversations.
4. **Fast customer support** (mentioned by 58%): Response times under 4 hours for non-critical issues.
5. **Product stability** (mentioned by 51%): "It just works" --- no significant downtime or data issues.

### Churn Indicators

Early warning signs that a customer is at risk (from churn analysis, FY2025):

| Indicator | Detection Point | Risk Level |
|-----------|----------------|------------|
| Active user rate drops below 50% | Month 3-4 | High |
| Primary champion leaves the company | Any time | High |
| No new projects created in 30 days | After month 2 | Medium |
| Support ticket volume spikes (frustration) | Any time | Medium |
| Customer stops attending product webinars/updates | After month 6 | Low |

---

## Context

### Strategic Implications
Pain points 1 and 2 ("chasing status updates" and "failed tool adoption") are our market entry narrative. Every prospect has experienced at least one of these. Leading with these pain points in marketing and sales creates immediate emotional recognition --- the prospect thinks "they understand my problem."

The behavioral patterns section is strategically valuable because it reveals a gap between how we market the product and how customers use it. We should align our marketing more closely with actual behavior: "shorter, better meetings" is more honest and credible than "eliminate status meetings."

The churn indicators provide a direct input to customer success strategy. The highest-impact intervention is monitoring active user rates at month 3-4 and proactively reaching out when adoption dips.

### Application Guidance
- **For marketing:** Use pain point language verbatim (anonymized) in ads, landing pages, and content. "I became a full-time status chaser" is more powerful than any copywriter's version.
- **For sales:** Pain points 1 and 2 are discovery call openers. Ask prospects "how much time do you spend each week on status updates?" and "have you tried a project management tool before? How did adoption go?"
- **For product:** The behavioral patterns table should be reviewed quarterly with the product team. Design for actual behavior, not intended behavior. The unmet needs table is an input to roadmap prioritization.
- **For customer success:** Build an early warning dashboard based on churn indicators. Intervene at the "active user rate drops" signal --- this is the most predictive and actionable indicator.

---

## Maintenance

### Review Schedule
- **Regular review:** Quarterly (aligned with NPS survey cycles and support ticket analysis)
- **Owner responsible for review:** Customer Research Lead

### Maintenance Triggers
- Quarterly NPS survey results are available
- Customer advisory board meeting surfaces new themes
- Support ticket analysis reveals a new high-frequency pain point
- Churn analysis shows a new pattern
- Major product release changes behavioral patterns
- New segment (e.g., healthcare) shows different pain point priorities
- Customer feedback contradicts existing insights

### Change Log
| Date | Version | Change Summary | Changed By |
|------|---------|----------------|------------|
| 2026-03-15 | 1.1.0 | Added churn indicators from FY2025 analysis; updated satisfaction drivers with current data; added behavioral patterns section | Customer Research Lead |
| 2025-09-01 | 1.0.0 | Initial creation based on H1 2025 customer research program | Customer Research Lead |
