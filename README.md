<p align="center">
  <h1 align="center">CLEAR Context OS</h1>
  <p align="center">
    <strong>Context engineering for Claude Code.</strong><br>
    Drop in your knowledge. Claude organizes it, keeps it alive, and uses it.
  </p>
  <p align="center">
    <a href="#install">Install</a> &nbsp;·&nbsp;
    <a href="#what-it-does">What it does</a> &nbsp;·&nbsp;
    <a href="#the-wiki-zone">Wiki zone</a> &nbsp;·&nbsp;
    <a href="docs/_bcos-framework/guides/getting-started.md">Getting Started</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/claude_code-ready-blueviolet" alt="Claude Code">
    <img src="https://img.shields.io/badge/methodology-CLEAR-green" alt="CLEAR Methodology">
    <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT">
  </p>
</p>

---

> Your AI had perfect context — two weeks ago. Then your strategy shifted, three meetings redefined priorities, and the docs you wrote on Monday are wrong by Friday. **CLEAR Context OS** turns your repo into a living knowledge base that Claude Code maintains alongside you. One source of truth per topic. Searchable. Task-aware. Never silently stale.

---

## Install

**One command. Drops into any repo.**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/walm00/business-context-os/main/install.sh)
```

Then open Claude Code in that repo and say:

> *"I want to set up my business context. Here's my website: [url]"*

Or drop everything you have — SOPs, brand docs, meeting notes, exports — into `docs/_inbox/` and ask:

> *"Process my inbox. Figure out where each piece belongs."*

Onboarding asks one question (project type), reads your inbox, asks if you have other sources (Google Drive, Notion, Confluence — fetched via MCP), then drafts the architecture for your review. **Nothing gets deleted. Originals are preserved or archived, never silently overwritten.** ~30 minutes to a working context system.

**Already installed? Update with:**

```bash
python .claude/scripts/update.py
```

Your `docs/` and `.private/` are never touched. Only the framework files (skills, hooks, scripts, templates) are refreshed.

---

## What it does

**Stops context rot in three ways:**

| | What it does | Why it matters |
|---|---|---|
| **Organize** | Every doc declares what it owns. CLEAR boundaries prevent the same fact living in 5 places. | One source of truth per topic. No more "which version is current?" |
| **Maintain** | Scheduled jobs check freshness, surface stale docs, propagate updates across linked content. | Context stays alive without you remembering to maintain it. |
| **Use** | `/context search` and `/context bundle <task>` give Claude curated, freshness-aware, source-of-truth-ranked context for the job at hand. | Your AI works from real, current knowledge — not whatever it last saw. |

The folder IS the signal: `docs/*.md` is current truth, `_planned/` is intent-not-yet-real, `_archive/` is history, `_inbox/` is unprocessed, `_collections/` is verbatim evidence (invoices, contracts, transcripts), `_wiki/` is explanatory derivative knowledge.

---

## The wiki zone

Inspired by [Karpathy's LLM Wiki approach](https://x.com/karpathy/status/1827143768459030896) — give the LLM a wiki of *your* knowledge, the way you'd brief a smart new hire.

Save anything to the wiki, from anywhere:

```text
/wiki run https://stripe.com/docs/api          ← fetch a URL, summarize, cite
/wiki create from /Users/me/Downloads/spec.pdf ← extract a PDF, link to the binary
/wiki promote docs/_inbox/meeting-notes.md     ← turn an inbox capture into a wiki page
```

The wiki holds **how-tos, runbooks, glossaries, source summaries, post-mortems, decision logs** — derivative knowledge that explains and supports your canonical data points. Every page cites what it builds on. Stale pages surface automatically when their sources advance.

Wiki content is searchable alongside the rest of your context:

```text
/context search "stripe billing"       ← cross-zone search, ranked by source-of-truth
/context bundle market-report:write    ← curated bundle for a specific task
```

---

## The dashboard

A local cockpit at <http://127.0.0.1:8091> that shows your system at a glance — no third-party services, no telemetry, no logins.

```bash
python .claude/scripts/bcos-dashboard/run.py
```

| Surface | What you see |
|---|---|
| **Cockpit** | One-line status (healthy / N waiting / heads-up). Per-job dot strip for every maintenance job (core BCOS + wiki zone). |
| **Update** | "Run full sync" button → `update.py` + CLAUDE.md drift review + auto-commit + push, with a live log drawer. |
| **Schedules** (`/settings/schedules`) | Per-job preset buttons (`daily`, `mon_wed_fri`, `weekly_mon`, `off`) + the global **auto-commit** toggle + auto-fix whitelist. Saves directly to `schedule-config.json`. |
| **Run history** (`/settings/runs`) | Last 20 dispatcher runs with filter chips (job / verdict / trigger). |
| **File health** (`/settings/files`) | Frontmatter / cross-reference / staleness findings with one-click fixes. |

The dashboard is read-mostly: data flows from the dispatcher's diary, the schedule config, and the canonical context index. Writes (mark-done, schedule preset, auto-commit toggle, file fix) go through dedicated POST endpoints.

---

## Requirements

- **Claude Code** (desktop app, CLI, or web)
- **Python 3.8+** on `PATH`
- **bash** (default macOS bash 3.2 is fine)

---

## Maintenance

Five scheduled tasks keep your knowledge alive — set up automatically during onboarding:

| Cadence | What runs |
|---|---|
| Daily | Index + health check, frontmatter validation, wiki staleness propagation |
| Weekly | Strategic reflection (daydream), lessons capture, deep cluster audit, wiki source refresh |
| Monthly | Architecture review with health score, wiki coverage audit |

You can tune any of it in plain English:

> *"Run the audit twice a week."*  · *"Move dispatcher to 08:30."*  · *"Turn off deep daydream."*

---

## CLEAR — the methodology

Five principles, one rule each:

- **C** — **Contextual Ownership** · one document owns each topic. No duplicates.
- **L** — **Linking** · reference sources; don't copy them.
- **E** — **Elimination** · consolidate; don't keep two versions.
- **A** — **Alignment** · context that doesn't support decisions doesn't belong.
- **R** — **Refinement** · structured maintenance, not ad-hoc fixes.

The whole framework is the mechanical implementation of these five rules.

---

## Contributing

Contributions welcome — open an issue or submit a PR targeting the `dev` branch. CI runs frontmatter, reference, and ecosystem-integration checks on every PR.

The fastest contribution path is **lessons learned.** As you use the system it captures insights; if you find one universal, contribute it back.

---

## Origin

Built by **[Guntis Coders](https://github.com/walm00)** after two years of operating context systems in production. The CLEAR methodology emerged from a practical problem: AI context degrades silently, and no amount of one-time documentation prevents it. The solution required a system — ownership boundaries, automated maintenance, self-learning, and structured reflection.

Background: [What is the Table of Contexts and why does it matter](https://medium.com/businessacademy-lv/what-is-the-table-of-contexts-and-why-does-it-matter-8ec2a9557e9f).

---

## License

[MIT](LICENSE)
