# Getting Started with CLEAR Context OS

**Install. Talk to Claude. Review what it drafts.**

---

## What You'll Have When You're Done

3 data points — single sources of truth for your most important business knowledge. Each has clear boundaries (what it covers, what it doesn't). Claude uses them to give you consistent, grounded answers.

**Time: ~30 minutes.** Then 5 minutes per week to keep it current.

---

## Step 1: Install (2 minutes)

```bash
# Clone BCOS into your project
git clone https://github.com/walm00/business-context-os.git /tmp/bcos
cd /path/to/your/project
bash /tmp/bcos/install.sh
```

Or click "Use this template" on GitHub to start a new project.

---

## Step 2: Tell Claude About Your Business

Open Claude Code and say something like:

> "Help me set up my business context."

That's it. Claude will look at what's in your repo, ask what you can share, and figure out the best approach. You might:

- **Share a URL** — your website, LinkedIn page, anything public
- **Drop files in `docs/_inbox/`** — pitch decks, one-pagers, meeting notes
- **Just describe it** — what you do, who you serve, what phase you're in
- **Point to existing docs** — if you already have READMEs or docs with business content

Claude reads whatever you give it, asks 2-3 follow-up questions if needed, and drafts 3 data points.

**If your repo already has docs:** Claude will scan them, show you what it found, and draft data points from your existing content. Your files stay exactly where they are.

---

## Step 3: Review the Drafts (15 minutes)

Claude presents 3 data points. For each, check:

- **DOMAIN** — does the one-sentence description match what this covers?
- **EXCLUSIVELY_OWNS** — is anything missing or misplaced?
- **Content** — is it accurate?

Don't aim for perfect. Aim for useful. You'll refine over time.

### What a good data point looks like

```markdown
## Ownership Specification

**DOMAIN:** Core brand attributes, mission, vision, values, and brand story.

**EXCLUSIVELY_OWNS:**
- Mission statement
- Vision statement
- Brand values
- Founding story
- Brand personality traits

**STRICTLY_AVOIDS:**
- How the brand sounds in writing (see: brand-voice)
- Customer-facing taglines and messages (see: messaging-framework)
```

The Ownership Specification prevents drift. DOMAIN says what the document covers. EXCLUSIVELY_OWNS says what can only be found here. STRICTLY_AVOIDS says what belongs somewhere else.

---

## Step 4: Use It

Your context is live. From here:

- **Ask Claude things** — "What does my Target Audience say about our primary segment?"
- **When something changes, update one file** — changed your pricing? Update Value Proposition. One place, one update.
- **Weekly: did anything change?** If yes, update the data point. If no, done. Most weeks: 60 seconds.

---

## What's Next

Stay here until it feels natural. No rush.

When you're ready:

- **Add more data points** when a topic needs a clear home. See [defining-your-context.md](./defining-your-context.md).
- **Add boundaries** (STRICTLY_AVOIDS) when content starts creeping between data points.
- **Explore skills** when manual maintenance feels like overhead. See [adoption-tiers.md](./adoption-tiers.md).
