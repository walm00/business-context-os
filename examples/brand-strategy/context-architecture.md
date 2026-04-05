# Context Architecture: Acme Co Brand Strategy

---

## Organization Overview

**Organization:** Acme Co

**What we do:** B2B SaaS platform that helps mid-market teams (50-500 people) plan, track, and deliver projects without the complexity of enterprise tools or the limitations of simple to-do apps.

**Who we serve:** Operations leaders, project managers, and team leads at mid-market companies who have outgrown spreadsheets but find enterprise project management tools overwhelming and expensive.

**Stage:** Growth-stage (Series B, 120 employees, 800+ customers)

**Why we built this context architecture:** After our Series B, we brought on two agencies (creative and PR) and hired 15 new people across marketing and sales. We found that every brief, pitch, and campaign started with a 45-minute "who are we again?" conversation. This architecture is our single source of truth for brand decisions.

---

## Cluster Structure

### Cluster 1: Brand & Identity
**Purpose:** Captures who we are --- our identity, voice, and how we express ourselves.
**Owner:** VP of Marketing

| Data Point | Domain | Owner | Status |
|------------|--------|-------|--------|
| brand-identity | Core brand attributes, mission, vision, story | Brand Lead | Active |
| brand-voice | Tone, personality, writing style, guidelines | Content Lead | Active |
| messaging-framework | Key messages, taglines, proof points, hierarchy | Brand Lead | Active |

### Cluster 2: Audience & Market
**Purpose:** Captures who we serve, what they need, and the market we operate in.
**Owner:** Director of Marketing

| Data Point | Domain | Owner | Status |
|------------|--------|-------|--------|
| target-audience | Customer segments, demographics, firmographics | Marketing Director | Active |
| customer-insights | Pain points, needs, behavioral patterns, feedback | Customer Research Lead | Active |
| market-context | Market landscape, trends, industry dynamics | Strategy Lead | Active |

### Cluster 3: Product & Value
**Purpose:** Captures what we offer and why it matters in the competitive landscape.
**Owner:** Head of Product Marketing

| Data Point | Domain | Owner | Status |
|------------|--------|-------|--------|
| value-proposition | Core value statements, benefit hierarchy | Product Marketing Lead | Active |
| competitive-positioning | Differentiation, market position, competitor awareness | Strategy Lead | Active |

---

## Data Point Inventory

| # | Data Point | Cluster | Owner | Status | Last Updated |
|---|-----------|---------|-------|--------|-------------|
| 1 | brand-identity | Brand & Identity | Brand Lead | Active | 2026-03-15 |
| 2 | brand-voice | Brand & Identity | Content Lead | Active | 2026-03-15 |
| 3 | messaging-framework | Brand & Identity | Brand Lead | Active | 2026-03-15 |
| 4 | target-audience | Audience & Market | Marketing Director | Active | 2026-03-15 |
| 5 | customer-insights | Audience & Market | Customer Research Lead | Active | 2026-03-15 |
| 6 | market-context | Audience & Market | Strategy Lead | Active | 2026-03-15 |
| 7 | value-proposition | Product & Value | Product Marketing Lead | Active | 2026-03-15 |
| 8 | competitive-positioning | Product & Value | Strategy Lead | Active | 2026-03-15 |

---

## Relationship Map

### How Data Points Connect

```
                    BRAND & IDENTITY
                    ================
                    brand-identity
                      │       │
            PROVIDES  │       │  PROVIDES
          (personality)       (story, values)
                      │       │
                      v       v
                brand-voice   messaging-framework
                      │               │
                      │    PROVIDES   │
                      │   (voice)     │
                      └───────>───────┘
                              │
                              │ REFERENCES (audience, insights)
                              v
                    AUDIENCE & MARKET
                    ================
                target-audience ←──REFERENCES── market-context
                      │                              │
                      │ BUILDS_ON                    │
                      v                              │
                customer-insights ───REFERENCES───>──┘
                      │
                      │ BUILDS_ON (pain points)
                      v
                    PRODUCT & VALUE
                    ===============
                value-proposition ←──REFERENCES── competitive-positioning
                      │                              │
                      └──────────PROVIDES────────────┘
                           (value claims inform positioning)
```

### Key Relationship Details

| From | To | Type | What Flows |
|------|----|------|-----------|
| brand-identity | brand-voice | PROVIDES | Personality traits guide voice development |
| brand-identity | messaging-framework | PROVIDES | Brand story and values shape message hierarchy |
| brand-voice | messaging-framework | PROVIDES | Voice guidelines shape how messages are written |
| target-audience | messaging-framework | REFERENCES | Audience segments inform message targeting |
| customer-insights | brand-identity | BUILDS_ON | Pain points shape brand story |
| customer-insights | value-proposition | BUILDS_ON | Pain points define what value to emphasize |
| market-context | competitive-positioning | REFERENCES | Market trends inform positioning strategy |
| market-context | target-audience | REFERENCES | Market dynamics shape segment priorities |
| value-proposition | competitive-positioning | PROVIDES | Value claims inform differentiation strategy |
| competitive-positioning | messaging-framework | REFERENCES | Differentiation shapes proof points |

---

## Maintenance Schedule

### Weekly Quick Check (Every Monday, 5 min)
Each data point owner scans for anything that changed in the past week.

### Monthly Cluster Review (First week of each month, 30 min)
Rotate through clusters:
- **January, April, July, October:** Brand & Identity
- **February, May, August, November:** Audience & Market
- **March, June, September, December:** Product & Value

### Quarterly Architecture Review (End of quarter, 2 hours)
All cluster owners meet to review the full architecture: gaps, overlaps, stale data, ownership changes.

### Annual Planning Alignment (January)
Align architecture with annual strategy. Add or retire clusters as needed.

---

## Growth Plan

### Current State (Phase 1: Foundation)
All 8 data points across 3 clusters are active and maintained.

### Phase 2: Expansion (Q3 2026)
- Add **Content & Channel Strategy** cluster
  - Data points: channel-strategy, content-pillars, editorial-calendar-context
- Add **Sales Enablement** data point to Product & Value cluster

### Phase 3: Maturity (Q1 2027)
- Add **Culture & Employer Brand** cluster for recruitment marketing
- Add **Partner Ecosystem** data point to Audience & Market cluster
- Integrate context architecture into agency onboarding process
- Build quarterly "context health score" reporting
