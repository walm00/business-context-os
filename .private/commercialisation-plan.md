# BCOS Commercialisation Plan

**Status:** Strategic draft
**Created:** 2026-04-06
**Owner:** Guntis
**Confidential:** Yes — gitignored, not for public repo

---

## Executive Summary

Business Context OS is an open source methodology + skill package for business context engineering with Claude Code. The commercial opportunity is a **managed MCP server** that automates what the repo teaches people to do manually — turning a DIY framework into a plug-and-play service.

**Model:** Open core — free repo builds credibility and audience, paid MCP server captures revenue from users who want automation and simplicity.

---

## The Two Layers

### Layer 1: Open Source Repo (Free)

**What it is:** The full BCOS package — methodology, 9 skills, templates, scripts, guides.

**Licence:** CC BY-NC-SA 4.0 — free to use internally, cannot sell or commercialise.

**Purpose:**
- Establish authority on business context engineering
- Build community and contributor base
- Drive awareness (every star, fork, and article = marketing)
- Prove the methodology works before asking anyone to pay

**Success metrics:**
- GitHub stars (visibility)
- Forks (adoption signal)
- Issues/PRs (engagement)
- Mentions in articles, videos, discussions

### Layer 2: BCOS MCP Server (Paid)

**What it is:** A hosted MCP server that Claude Code connects to. Automates context management — onboarding, auditing, scheduling, health monitoring, drift alerts.

**Command:** `claude mcp add bcos-server --url https://api.bcos.io`

**Purpose:**
- Revenue
- Stickier user experience (persistent state, cross-session memory)
- Features the repo alone cannot deliver (cloud scheduling, team sync, dashboards)

---

## What the MCP Server Does That the Repo Cannot

| Capability | Free Repo (DIY) | MCP Server (Managed) |
|-----------|-----------------|---------------------|
| Context onboarding | Read SKILL.md, follow steps manually | "Onboard my context" → automatic scan, classification, draft generation |
| Health monitoring | Run scripts manually, remember to check | Automated scheduled audits, drift detection, health score |
| Daydream / reflection | Remember to trigger it, read output | Scheduled, proactive — surfaces insights without prompting |
| Cross-session memory | Lost between Claude sessions | Persistent — remembers every audit, every decision, every change |
| Team collaboration | Single user, single machine | Shared context architecture, role-based views, change notifications |
| Drift alerts | Manual comparison | "Your competitive-positioning hasn't been updated in 45 days" |
| Context health dashboard | None (CLI only) | Web dashboard: health scores, timelines, gap analysis |
| Backup & versioning | Git (manual) | Automatic snapshots, rollback, change history |

---

## Pricing Strategy

### Tier Structure

| Tier | Price | Target | What You Get |
|------|-------|--------|-------------|
| **Community** | Free | Individual users exploring BCOS | Repo access, community support, basic MCP health check (1 project, 10 docs) |
| **Professional** | $15/mo | Freelancers, solo consultants, small teams | Full MCP automation, unlimited docs, scheduled audits, drift alerts, 3 projects |
| **Team** | $39/mo | Agencies, departments, growing companies | Everything in Pro + team collaboration, shared context, role-based access, 10 projects |
| **Enterprise** | Custom | Large orgs, multi-department | Custom onboarding, SLA, SSO, unlimited projects, dedicated support |

### Why These Numbers

- $15/mo is impulse-buy territory for professionals who bill $100+/hr
- The MCP server saves 2-4 hours/month on context maintenance → 10-20x ROI at $15
- $39/mo team tier is where real revenue scales (agencies managing multiple client contexts)
- Enterprise is the long tail play — custom pricing, high LTV

### Conversion Funnel

```
GitHub visitor (free)
  ↓ stars repo, clones it
BCOS user (free)
  ↓ uses it for 2-4 weeks, sees value, wants automation
Free MCP tier (free)
  ↓ hits limits (1 project, no scheduling)
Professional ($15/mo)
  ↓ brings it to their team
Team ($39/mo)
  ↓ company adopts it across departments
Enterprise (custom)
```

Expected conversion rates (based on MCP market benchmarks):
- Free → Professional: 3-5% of active users
- Professional → Team: 15-25% of Pro users
- Team → Enterprise: case-by-case

---

## Technical Architecture

### MCP Server Stack

```
┌──────────────────────────────────────────────┐
│  Claude Code (user's machine)                │
│  └── MCP connection to bcos-server           │
└──────────────┬───────────────────────────────┘
               │ MCP protocol (stdio or SSE)
               ▼
┌──────────────────────────────────────────────┐
│  BCOS MCP Server                             │
│  ├── Tools:                                  │
│  │   ├── bcos_onboard       (scan + classify)│
│  │   ├── bcos_ingest        (integrate new)  │
│  │   ├── bcos_audit         (health check)   │
│  │   ├── bcos_daydream      (reflection)     │
│  │   ├── bcos_status        (health score)   │
│  │   └── bcos_recommend     (what to do next)│
│  ├── Resources:                              │
│  │   ├── context://health   (current scores) │
│  │   ├── context://docs     (document index) │
│  │   └── context://history  (change timeline)│
│  └── Prompts:                                │
│      ├── weekly-review                       │
│      └── onboarding-wizard                   │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  Backend                                     │
│  ├── Auth (API keys, Stripe for billing)     │
│  ├── Storage (user context state, history)   │
│  ├── Scheduler (cron for audits, daydreams)  │
│  └── Notifications (email, Slack webhook)    │
└──────────────────────────────────────────────┘
```

### Build vs Buy Decisions

| Component | Approach | Notes |
|-----------|----------|-------|
| MCP server framework | Build on official MCP SDK | TypeScript or Python |
| Auth & billing | Stripe + API keys | Standard, well-documented |
| State storage | Supabase or PlanetScale | Managed, cheap at small scale |
| Scheduler | Cloud Functions + cron trigger | Vercel cron / AWS EventBridge |
| Email notifications | Resend or SendGrid | Transactional only at first |
| Web dashboard | Next.js + Supabase | Phase 2 — not needed at launch |

---

## Go-to-Market Timeline

### Phase 0: Foundation (Now — Month 1)

**Goal:** Ship the open source repo. Build credibility.

- [x] BCOS repo complete with all skills, templates, methodology
- [x] CC BY-NC-SA licence (protects commercial rights)
- [x] GitHub repo configured (main/dev branches, issue templates)
- [ ] Make repo public
- [ ] Write launch article (Medium / Substack) — "Why your AI context rots and how to fix it"
- [ ] Post to r/ClaudeAI, r/claudeskills, Hacker News
- [ ] Share on LinkedIn with THEO positioning angle
- [ ] Create 2-3 example context architectures (different industries)

**Target:** 50-100 stars, 10-20 forks, initial community signal

### Phase 1: Listen (Month 1-2)

**Goal:** Understand what users struggle with. Collect pain points.

- [ ] Monitor GitHub issues — what are people asking for help with?
- [ ] Join discussions — what's confusing, what's missing?
- [ ] Track which skills people use most vs. skip
- [ ] Identify the top 3 "I wish this was easier" moments
- [ ] Build relationships with early adopters (potential beta testers)

**Target:** 200 stars, clear understanding of paid product requirements

### Phase 2: Prototype MCP Server (Month 2-3)

**Goal:** Build minimum viable MCP server with core automation.

- [ ] MCP server with 3 tools: `bcos_onboard`, `bcos_audit`, `bcos_status`
- [ ] Persistent state (remember context across sessions)
- [ ] Free tier: 1 project, 10 docs, manual triggers only
- [ ] API key auth
- [ ] Deploy to Vercel or Railway

**Target:** Working MCP server that 5-10 beta users can test

### Phase 3: Beta (Month 3-4)

**Goal:** Validate willingness to pay.

- [ ] Invite 10-20 users from Phase 1 community
- [ ] Add scheduling (automated audits, daydream triggers)
- [ ] Add drift alerts (email when docs go stale)
- [ ] Collect feedback — what's worth paying for? What's missing?
- [ ] Stripe integration for Pro tier

**Target:** 5+ users willing to pay $15/mo. If not → iterate or pivot.

### Phase 4: Launch (Month 4-5)

**Goal:** Public launch of paid tier.

- [ ] Landing page at bcos.io (or similar)
- [ ] Free + Pro tiers live
- [ ] Documentation for MCP server setup
- [ ] Launch article: "From DIY to managed — BCOS MCP Server"
- [ ] Product Hunt launch
- [ ] Add to MCP directories (mcpize, mcp.so, etc.)

**Target:** 50 free users, 5-10 paying users, $75-150 MRR

### Phase 5: Scale (Month 5-8)

**Goal:** Team tier + growth.

- [ ] Team features (shared context, multi-user)
- [ ] Web dashboard (visual health scores, timelines)
- [ ] Integration with Slack (drift alerts as DMs)
- [ ] Content marketing: case studies, "how Company X uses BCOS"
- [ ] Explore partnerships with Claude Code influencers / consultants

**Target:** 200 free users, 30-50 paying users, $500-1000 MRR

---

## Competitive Landscape

### Direct (Context Management for AI)

| Competitor | What They Do | Our Advantage |
|-----------|-------------|---------------|
| Manual CLAUDE.md files | Everyone's DIY approach | We have a methodology, they have a file |
| Loreto.io | Skill extraction from content | Different problem — they extract skills, we manage business context |
| Prompt engineering tools | One-shot prompt improvement | We're about persistent, evolving context — not single prompts |

### Adjacent

| Category | Examples | Relationship |
|----------|---------|-------------|
| Knowledge management | Notion, Confluence, Obsidian | We complement these — BCOS manages the AI context layer on top |
| AI agent frameworks | LangGraph, CrewAI, AutoGen | Different layer — they orchestrate agents, we manage the knowledge agents need |
| MCP server ecosystem | 11,000+ servers | We're one of them, but methodology-first rather than tool-first |

### Moat

1. **Methodology depth** — CLEAR isn't a feature, it's a system. Hard to copy the thinking behind it.
2. **First mover** — No one else is doing "business context engineering" as a category.
3. **Community knowledge** — Lessons, patterns, examples accumulate over time. Network effect.
4. **THEO connection** — Real-world validation from a production competitive intelligence system.

---

## Revenue Projections (Conservative)

| Month | Free Users | Paid Users | MRR | Notes |
|-------|-----------|-----------|-----|-------|
| 1-2 | 50-100 | 0 | $0 | Open source phase |
| 3-4 | 150-300 | 5-10 | $75-150 | Beta launch |
| 5-6 | 300-500 | 20-30 | $300-570 | Public launch |
| 7-9 | 500-1000 | 40-60 | $600-1200 | Growth + team tier |
| 10-12 | 1000-2000 | 80-120 | $1400-2800 | Mature product |

These are conservative. The MCP ecosystem is growing fast — [projected to hit $5.56B by 2034](https://dev.to/krisying/mcp-servers-are-the-new-saas-how-im-monetizing-ai-tool-integrations-in-2026-2e9e). Early entrants with genuine methodology depth will capture disproportionate share.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Anthropic builds this natively into Claude | Medium | High | Stay ahead on methodology depth. If they do it, they'll do it generically — BCOS is opinionated and that's the value. |
| Low conversion to paid | Medium | Medium | Validate with beta before investing in scale. Pivot to consulting/training if SaaS doesn't work. |
| Someone forks and competes | Low | Medium | CC BY-NC-SA blocks commercial forks. Methodology depth is hard to copy. |
| Claude Code market doesn't grow | Low | High | Hedge by making methodology tool-agnostic. CLEAR works with any AI assistant. |
| Over-engineering before validation | Medium | Medium | Strict phased approach. Don't build Phase 5 features until Phase 3 validates demand. |

---

## Alternative Revenue Streams (if MCP server doesn't scale)

1. **Consulting / Implementation** — "We'll set up BCOS for your organisation" ($2-5K per engagement)
2. **Training / Workshops** — "Business Context Engineering Masterclass" ($200-500 per seat)
3. **Templates Marketplace** — Industry-specific context architectures ($50-100 per template pack)
4. **Enterprise Audits** — "We'll audit your AI context and tell you what's broken" ($5-10K)
5. **Book / Course** — "The CLEAR Method" — methodology as educational content

---

## Key Decisions to Make

| Decision | Options | When to Decide |
|----------|---------|---------------|
| Domain name | bcos.io, businesscontextos.com, clearmethod.io | Before Phase 4 launch |
| MCP server language | TypeScript (matches ecosystem) vs Python (matches scripts) | Before Phase 2 build |
| Hosting | Vercel, Railway, Fly.io, AWS | Before Phase 2 build |
| Billing | Stripe only vs Stripe + LemonSqueezy | Before Phase 3 beta |
| Company structure | Solo, LLC, Ltd | Before accepting first payment |

---

## Next Action

**Immediate:** Make the repo public. Write the launch article. Start Phase 0.

Everything else follows from community response.
