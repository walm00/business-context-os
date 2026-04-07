# For Non-Technical Users

**Quick reference for CLEAR Context OS concepts. No jargon.**

If you want to get started right away, go to [getting-started.md](./getting-started.md). Come back here if you hit a term you don't understand.

---

## Key Concepts

| Concept | What it is | Analogy |
|---------|-----------|---------|
| **Data point** | A specific topic your business needs to know about. One file, one topic. | A drawer in a filing cabinet with a clear label. |
| **Ownership** | Each data point has clear boundaries -- what it covers and what it doesn't. | Departments in a company: marketing handles marketing, sales handles sales. |
| **DOMAIN** | One sentence describing what a data point covers. | The label on the drawer. |
| **EXCLUSIVELY_OWNS** | What can ONLY be found in this data point. | The contents list on the drawer -- if it's here, it's not anywhere else. |
| **STRICTLY_AVOIDS** | What this data point does NOT contain, with a note about where to find it instead. | A sign saying "for pricing, go to the pricing drawer." |
| **Cluster** | A group of related data points. | A section of the filing cabinet (Brand & Identity, Audience & Market, etc.). |
| **Context rot** | When business information slowly gets outdated or contradictory. | A garden nobody tends -- weeds creep in until you can't tell flowers from weeds. |

---

## How to Talk to Claude

You don't need special commands. Just talk normally:

- "Check if my Brand Identity data point is still accurate."
- "We just changed our pricing. Which data points need updating?"
- "Is there overlap between my Brand Voice and Messaging Framework?"
- "Help me create a data point for our competitive landscape."
- "Summarize what my Target Audience says about our primary segment."

---

## The Files

| Location | What's there | What you do with it |
|----------|-------------|-------------------|
| `docs/*.md` | Your data points -- actual business knowledge | Read, update when things change |
| `docs/_inbox/` | Raw material -- meeting notes, brain dumps | Drop stuff here for Claude to process later |
| `docs/_planned/` | Ideas and plans -- not yet real | Review occasionally, promote when ready |
| `docs/templates/` | Starting points for new data points | Copy when creating something new |
| `CLAUDE.md` | Instructions for Claude | You generally don't edit this |

---

## FAQ

**Do I need to know how to code?** No. You create and edit text files. If you can write an email, you have the skills you need.

**What if I make a mistake?** Everything is saved in version control. You can always go back. Ask Claude or a colleague if you're unsure how.

**How much time does this take?** About 30 minutes to set up. Then 5 minutes per week. Most weeks, nothing changed and you're done in 60 seconds.

**Can my whole team use this?** Yes. Different people can own different data points. Everyone references the same sources of truth.

**Where do I start?** Follow the [getting-started guide](./getting-started.md). It takes about 30 minutes.
