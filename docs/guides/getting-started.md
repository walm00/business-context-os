# Getting Started with CLEAR Context OS

**Install. Share what you know. Claude builds your context. You review.**

---

## What You'll Have When You're Done

A living context system -- 3 data points that are the single source of truth for your most important business knowledge. Each one has clear boundaries (what it covers, what it doesn't). Claude uses them to give you consistent, grounded answers.

**Time: 20-30 minutes.** Then 5 minutes per week to keep it alive.

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

## Step 2: Choose Your Path

### Path A: Starting fresh (no existing docs)

Tell Claude about your business. The more you share, the better your context will be.

> "I want to set up my business context. Here's what I have:"

Share **any combination** of these:

- **Your website URL** -- Claude reads it and extracts who you are, what you do, who you serve
- **LinkedIn company page** -- good for positioning, team size, industry
- **A pitch deck or one-pager** -- drop it in `docs/_inbox/` and point Claude to it
- **Google Drive folder** -- if you have an MCP connector set up
- **A short description** -- just tell Claude: what you do, who you serve, what phase you're in

Claude will read what you share, ask a few follow-up questions, and **draft your first 3 data points for you**. Each one will have:
- **DOMAIN** -- what it covers (one sentence)
- **EXCLUSIVELY_OWNS** -- what ONLY this document contains (3-5 items)
- **Content** -- the actual business knowledge, extracted from your sources

**You review and edit.** Claude does the heavy lifting, you validate the result.

### Path B: Already have docs in your repo

Tell Claude to scan what you have.

> "Scan my repo and show me what business context already exists."

Claude will:
1. **Read** your existing docs, READMEs, and any markdown files
2. **Map** what topics are covered and where
3. **Show you** what it found -- organized by topic
4. **Suggest** which 3 topics to formalize as CLEAR data points first
5. **Draft** those data points using content from your existing docs

**Your existing files stay exactly where they are.** Claude creates CLEAR data points alongside them -- it does not reorganize, rename, or move your files.

You review the drafts, adjust anything that's off, and you're done.

---

## Step 3: Review Your Data Points (15 minutes)

Claude will present 3 drafted data points. For each one, check:

- **Does the DOMAIN sentence accurately describe what this covers?** If not, adjust it.
- **Does EXCLUSIVELY_OWNS list the right things?** Add anything missing, remove anything that belongs elsewhere.
- **Is the content accurate?** Fix anything that's wrong or outdated.

Don't aim for perfect. Aim for "good enough to be useful." You'll refine over time.

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

The Ownership Specification is what prevents drift. DOMAIN says what this document covers. EXCLUSIVELY_OWNS says what can only be found here. STRICTLY_AVOIDS says what belongs somewhere else.

---

## Step 4: You're Done. Start Using It.

Your context system is live. Here's how to use it going forward.

### Point Claude to your context

When you start a conversation, you can say things like:

- "Use my data points as the source of truth for brand questions."
- "Before writing any messaging, check Value Proposition for our differentiators."
- "What does my Target Audience data point say about our primary segment?"

### When something changes, update one file

Changed your mission statement? Update Brand Identity. Discovered a new customer segment? Update Target Audience. Changed your pricing? Update Value Proposition.

**One place. One update. Everything that references it stays current.**

### Weekly check-in (5 minutes)

Once a week, ask yourself: did anything change this week that affects my data points?

- If yes: update the relevant data point
- If no: done

Most weeks, nothing changed and you're done in 60 seconds.

---

## What's Next

You now have working context. **Stay here until it feels natural.** There's no rush to do more.

When you're ready:

- **Add more data points** when you notice a topic that needs a clear home. See [defining-your-context.md](./defining-your-context.md) for the detailed guide.
- **Add boundaries** (STRICTLY_AVOIDS) when content starts creeping between data points.
- **Explore skills** when manual maintenance feels like overhead. See [adoption-tiers.md](./adoption-tiers.md).

**Start small. Use what you build. Grow when the need is real.**
