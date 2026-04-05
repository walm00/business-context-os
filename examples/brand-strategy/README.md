# Brand Strategy Example

## Who This Is For

- Brand and marketing teams building or refining brand strategy
- Founders establishing brand identity for the first time
- Strategy consultants setting up brand frameworks for clients
- Anyone who needs a complete, structured record of brand decisions

## What This Demonstrates

A complete context architecture for brand strategy, using a fictional company called **Acme Co** --- a B2B SaaS company that helps mid-market teams manage projects more effectively.

This example includes:

- **8 data points** organized into **3 clusters**
- Fully worked ownership specifications showing how to prevent overlap
- Realistic content that reads like actual brand strategy documentation
- Cross-references between data points demonstrating how they connect

## The Architecture at a Glance

### Cluster 1: Brand & Identity
| Data Point | What It Covers |
|------------|---------------|
| brand-identity | Mission, vision, values, brand story |
| brand-voice | Tone, personality, writing style |
| messaging-framework | Key messages, taglines, proof points |

### Cluster 2: Audience & Market
| Data Point | What It Covers |
|------------|---------------|
| target-audience | Customer segments, demographics, firmographics |
| customer-insights | Pain points, needs, behavioral patterns |
| market-context | Market trends, industry dynamics, regulatory factors |

### Cluster 3: Product & Value
| Data Point | What It Covers |
|------------|---------------|
| value-proposition | Core value statements, benefit hierarchy |
| competitive-positioning | Differentiation, market position, competitor awareness |

## How to Use This Example

1. **Read the architecture document** (`context-architecture.md`) to see how everything fits together
2. **Browse the data points** in `data-points/` to see fully worked examples
3. **Copy the entire folder** to start your own brand strategy context
4. **Rename "Acme Co"** to your company and replace the content with your own
5. **Adjust the structure** --- add, remove, or rename data points to match your needs

## Key Patterns to Notice

- **Ownership boundaries are explicit.** Every data point states what it owns and what it avoids. This prevents the #1 problem in brand documentation: the same information written differently in three places.
- **Data points reference each other.** Instead of duplicating audience information in the messaging framework, it points to `target-audience`. One source of truth.
- **Content and Context are separate sections.** Facts (Content) are kept apart from interpretation (Context). This makes updates easier --- you can change a fact without rewriting the strategic analysis, or update the strategy without touching the facts.
- **Maintenance triggers are specific.** Instead of vague "review regularly," each data point lists the exact events that should trigger a review.
