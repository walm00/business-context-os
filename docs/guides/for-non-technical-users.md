# For Non-Technical Users

**Plain language guide for people who are not comfortable with technical tools.**

---

## What Is This?

Business Context OS is a system that helps you and Claude keep your business information organized, accurate, and up-to-date.

Think about all the knowledge your business relies on: who your customers are, what makes you different, what your brand stands for, how you talk about your product. Right now, that knowledge probably lives in scattered documents, slide decks, people's heads, and shared drives. Some of it is outdated. Some of it contradicts other versions. Nobody is quite sure which version is the "real" one.

Business Context OS gives each piece of business knowledge a clear home, a clear owner, and clear boundaries. When you use Claude, it draws from these organized sources instead of getting confused by conflicting information.

**The result:** Consistent, trustworthy answers. Whether you are writing a marketing brief, preparing a pitch, onboarding a new team member, or asking Claude for help -- everyone works from the same source of truth.

---

## Key Concepts in Plain English

### Data Point

**What it is:** A specific topic your business needs to know about.

**Analogy:** Think of a filing cabinet. Each drawer has a label: "Brand," "Customers," "Product," "Competition." A data point is like one of those drawers -- it has a clear label, it contains specific information, and one person is responsible for keeping it organized and current.

**Examples:**
- "Brand Identity" -- everything about who your company is: mission, values, story
- "Target Audience" -- everything about who your customers are: segments, demographics, what they look like
- "Value Proposition" -- everything about why customers choose you: differentiators, benefits, proof

### Ownership

**What it is:** Each topic has one official source of truth, maintained by one person.

**Analogy:** In a well-run office, if you need the latest sales figures, you know to ask the sales director -- not dig through old spreadsheets or ask five different people. Ownership works the same way. Each data point has one person whose job it is to keep that information current.

**Why it matters:** When nobody owns a piece of information, nobody updates it. It slowly goes stale. Eventually it actively misleads people because it describes a business that no longer exists.

### Boundaries

**What it is:** Clear rules about what goes where. Like departments in a company -- marketing handles marketing, sales handles sales, and they coordinate but do not do each other's jobs.

**Analogy:** Imagine if every department started writing their own version of the company description. Marketing writes one for the website. Sales writes one for proposals. HR writes one for job postings. Six months later, all three are slightly different. Boundaries prevent this by saying: "The company description lives in Brand Identity. Everyone else references it."

**The two most important boundary rules:**
- **EXCLUSIVELY_OWNS** -- What ONLY this data point contains. You will find this information here and nowhere else.
- **STRICTLY_AVOIDS** -- What this data point does NOT contain, even if it seems related. With a note about where to find it instead.

### Architecture

**What it is:** The map showing how all your topics connect.

**Analogy:** Think of an organizational chart, but for your business knowledge instead of your people. It shows which topics exist, which ones relate to each other, and who is responsible for each area.

**What it looks like in practice:** A simple document (your "architecture canvas") that lists all your data points, groups them into clusters (like departments), and notes who owns what. You can see the whole picture at a glance.

### Context Rot

**What it is:** When your business information slowly gets outdated, contradictory, or unreliable.

**Analogy:** Think of a garden that nobody tends. Weeds creep in gradually. Plants you planted with care get overgrown. After a while, you cannot tell the flowers from the weeds. Context rot is the same thing happening to your business knowledge -- slowly, silently, and then suddenly everything is a mess.

**How it shows up:**
- Two people give different answers to the same question
- A new hire reads your brand guide and says "this is not what I was told in the interview"
- An agency produces work based on information that turns out to be outdated
- You update something in one place and realize three other documents now have the old version

### Cluster

**What it is:** A group of related data points that share a theme.

**Analogy:** Departments in a company. Your Brand & Identity cluster might contain Brand Identity, Brand Voice, and Messaging Framework -- all related to how your company presents itself. Your Audience & Market cluster might contain Target Audience and Competitive Landscape -- all related to your customers and market.

**Why it helps:** Clusters let you see the big picture without getting lost in individual data points. They also tell you who should coordinate: people who own data points in the same cluster should talk to each other regularly.

---

## How to Talk to Claude About Your Context

You do not need special commands or technical language. Here are everyday phrases you can use with Claude.

### Checking accuracy

- "Check if my Brand Identity data point is still accurate."
- "Is my Target Audience up to date? We have been focusing more on mid-market lately."
- "Review my Value Proposition -- does it still reflect our current product?"

### When things change

- "I am launching a new product next month. Which of my data points need updating?"
- "We just decided to change our mission statement. Walk me through what else needs to change."
- "A competitor just merged with another company. What should I review?"

### Finding problems

- "Is there overlap between my Messaging Framework and my Brand Voice? They feel like they are covering the same ground."
- "Audit my Brand & Identity cluster for consistency."
- "Are any of my data points contradicting each other?"

### Creating new context

- "Help me create a data point for our competitive landscape."
- "I want to add a new data point for our customer success stories. Help me define the boundaries."
- "We are entering a new market. What data points should I create?"

### Getting summaries

- "Summarize what my Target Audience data point says about our primary segment."
- "What does my architecture say about who owns our competitive positioning?"
- "Give me a quick health check on all my data points."

---

## The Files Explained

Your Business Context OS project contains several types of files. Here is what each type does in plain language.

### Your data point files

**Where:** In your project's documentation folder.

**What they are:** These are your actual business knowledge. Each file covers one specific topic (brand identity, target audience, value proposition, etc.). They contain the facts, definitions, and strategic interpretation that your team relies on.

**What you do with them:** Read them for reference. Update them when things change. This is where you spend most of your time.

### CLAUDE.md

**Where:** In the root of your project.

**What it is:** Instructions for Claude about how to work with your context. It tells Claude what your project is about, what rules to follow, and where to find things.

**What you do with it:** You generally do not need to edit this yourself. It is set up when you start the project. Think of it as the "employee handbook" that Claude reads before starting work.

### Templates

**Where:** In `docs/templates/`.

**What they are:** Fill-in-the-blank starting points for creating new data points, clusters, and architecture documents. Instead of starting from a blank page, you copy a template and fill in your specifics.

**What you do with them:** Copy them when you need to create something new. They include helpful comments explaining what goes in each section.

**Templates available:**
- `context-data-point.md` -- For creating a new data point
- `context-cluster.md` -- For grouping related data points
- `context-architecture-canvas.md` -- For mapping your entire architecture
- `maintenance-checklist.md` -- For tracking your review schedule

### Skills

**Where:** In `.claude/skills/`.

**What they are:** Specialized capabilities that make Claude better at helping you with specific tasks. Think of them as "training" for Claude -- a skill teaches Claude how to plan context changes, audit for problems, or verify quality.

**What you do with them:** You do not need to understand how they work. When they are activated, Claude uses them automatically. If you are at Tier 1 (foundation only), you do not need skills at all. See [adoption-tiers.md](./adoption-tiers.md) for when skills become relevant.

### Methodology docs

**Where:** In `docs/methodology/`.

**What they are:** The reference material explaining the CLEAR principles, the ownership specification format, how context architecture works, and the decision framework for handling changes. These are the "why" and "how" behind the system.

**What you do with them:** Read them if you want to understand the thinking behind the system. You do not need to read all of them to get started -- the [getting-started.md](./getting-started.md) guide covers what you need for Week 1.

---

## Frequently Asked Questions

### "Do I need to know how to code?"

No. Business Context OS works with plain text files (markdown format, which is just text with simple formatting like headings and bullet points). You create and edit files, organize folders, and have conversations with Claude. If you can write an email and organize a folder, you have the skills you need.

### "What is markdown?"

Markdown is a way of writing formatted text using plain characters. A line starting with `#` becomes a heading. A line starting with `-` becomes a bullet point. Text between `**` marks becomes **bold**. That is all you really need to know. Claude can handle the formatting for you if you prefer.

### "What if I make a mistake?"

Everything is saved with version control (like a time machine for your files). If you make a change you do not like, you can go back to any previous version. Nothing is permanently lost unless you deliberately choose to delete it. If you are not sure how to undo something, ask Claude or a team member who knows the tool.

### "How much time does this take?"

- **Getting started:** 2-3 hours for your initial setup (one time)
- **Weekly maintenance:** 5 minutes (a quick scan to check if anything changed)
- **Monthly audit:** 30 minutes (review one cluster for accuracy)
- **Quarterly review:** 2 hours (full architecture health check)

The weekly habit is the most important one. Most weeks it takes 60 seconds because nothing has changed.

### "Can my whole team use this?"

Yes. That is the point. Multiple people can own different data points, and everyone can reference them. When a marketer needs the audience definition, they look at the Target Audience data point. When a salesperson needs the value proposition, they look at the Value Proposition data point. Everyone gets the same answer.

Team usage tips:
- Assign one owner per data point (not a committee)
- Make sure everyone knows where the data points live
- When someone asks a question that a data point answers, point them to the data point instead of answering from memory

### "What is Claude Code?"

Claude Code is a tool that lets you work with Claude directly in your project files. Instead of copying your documents into a chat window, Claude can read and work with your actual files. This means Claude can check your data points, help you update them, and use them as context for any task you ask about.

Think of it as having Claude sitting at your desk, able to look at the same documents you are looking at, instead of having to describe everything over a chat window.

### "What if I am the only person using this?"

That works perfectly. Many people start as the sole maintainer, especially founders and solo marketers. The system is valuable even for one person because it:
- Keeps your thinking organized
- Prevents you from contradicting yourself across documents
- Gives Claude accurate context for better answers
- Makes it easy to hand off knowledge when you eventually hire or bring on partners

### "This sounds like a lot of process. Is it worth it?"

The process is minimal: define what you know, put it somewhere organized, check it regularly. The alternative is what most organizations do by default: scattered documents, conflicting versions, stale information, and constant uncertainty about what is current.

If you have ever spent 20 minutes looking for "the latest version" of your brand guidelines, or discovered that your website says something different from your pitch deck, or had to correct an agency because they worked from outdated information -- that is the cost of NOT having organized context. Business Context OS replaces that recurring cost with a small, predictable maintenance habit.

### "Where do I start?"

Follow the [getting-started.md](./getting-started.md) guide. It walks you through everything in about an hour, assumes no technical background, and gets you to a working system by the end.

---

**You do not need to understand how the system works under the hood to get value from it. You need to organize your knowledge, maintain it, and use it. That is it.**
