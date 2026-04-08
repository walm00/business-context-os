# Ownership Specification Format

**Purpose:** The formal specification for defining context data points with clear territories, boundaries, and relationships.

---

## Why Specify Ownership?

When a piece of organizational knowledge has no formal owner, it drifts. Different teams create their own versions. Nobody knows which is current. Updates happen in one place but not another.

The ownership specification solves this by giving each context data point a formal definition that answers six questions:

1. What does this data point cover?
2. What does ONLY this data point contain?
3. What must this data point NOT contain?
4. What does this data point depend on?
5. What does this data point cross-reference?
6. What consumes this data point downstream?

These six questions map to six keywords. Together, they form the complete specification for any context data point.

---

## The Six Keywords

### DOMAIN

**What this data point covers -- its territory.**

The DOMAIN is a one-to-three sentence description of this data point's scope and purpose. It should be clear enough that someone unfamiliar with your organization could understand what kind of knowledge lives here.

**Think of it as:** The answer to "What is this data point about?"

**Example:**
```
DOMAIN = [Brand voice and communication personality guidelines
          serving as the authoritative reference for how the brand
          speaks across all channels]
```

**Tips:**
- Start with the subject, not the organization name
- Include the purpose ("serving as..." or "providing...")
- Be specific enough to distinguish from neighboring data points

---

### EXCLUSIVELY_OWNS

**What ONLY this data point contains -- no other data point has this.**

This is the most important keyword. It defines the unique territory of this data point. If something appears in EXCLUSIVELY_OWNS, it should not appear in any other data point's EXCLUSIVELY_OWNS list.

**Think of it as:** The answer to "What can I find HERE and only here?"

**Example:**
```
EXCLUSIVELY_OWNS = [
  tone and personality attributes |
  writing style guidelines |
  vocabulary preferences and restrictions |
  channel-specific voice adaptations |
  voice dos and don'ts with examples
]
```

**Tips:**
- Use the pipe character `|` to separate items
- Each item should be a distinct piece of knowledge
- Be specific enough that there is no ambiguity about what belongs here
- If you are unsure whether something belongs here or in another data point, that is a sign your boundaries need clarification

---

### STRICTLY_AVOIDS

**What this data point must NOT contain -- it belongs somewhere else.**

Boundaries prevent drift. Without them, data points gradually absorb related content until they overlap with their neighbors. STRICTLY_AVOIDS draws a clear line.

**Think of it as:** The answer to "What should I NOT put here, even if it seems related?"

**Example:**
```
STRICTLY_AVOIDS = [
  specific messaging and taglines (-> Messaging Framework) |
  visual identity guidelines (-> Visual Identity) |
  audience demographics (-> Target Audience) |
  competitive positioning claims (-> Value Proposition)
]
```

**Tips:**
- Always note WHERE the avoided content belongs using the arrow notation `(-> Data Point Name)`
- This makes it easy for someone to find the right home for misplaced content
- Focus on the most common areas of confusion -- you do not need to list every possible thing this data point is NOT

---

### BUILDS_ON

**What upstream data points this data point depends on.**

Some data points cannot exist without others. Your Brand Voice BUILDS_ON your Brand Identity -- you need to know who you are before you can define how you sound. This keyword makes those dependencies explicit.

**Think of it as:** The answer to "What do I need to have in place BEFORE I can define this?"

**Example:**
```
BUILDS_ON = [brand_identity:core_personality_foundation]
```

**Format:** `data_point_name:what_it_provides`

**Tips:**
- Keep the dependency list short. If a data point BUILDS_ON more than 3-4 others, it may be too downstream or too broad.
- The `:what_it_provides` suffix explains WHY the dependency exists, not just that it does
- BUILDS_ON implies a hard dependency. If this upstream data point changes significantly, the downstream one likely needs review.

---

### REFERENCES

**What data points to cross-reference -- useful context, but not a hard dependency.**

Not every connection is a dependency. Sometimes a data point benefits from awareness of another data point without strictly depending on it. REFERENCES captures these softer connections.

**Think of it as:** The answer to "What else should I look at for useful context?"

**Example:**
```
REFERENCES = [target_audience:audience_communication_preferences]
```

**Format:** `data_point_name:what_to_look_at`

**Tips:**
- REFERENCES is lighter than BUILDS_ON. A change in a referenced data point may or may not require a review of this one.
- Use REFERENCES for "nice to know" connections and BUILDS_ON for "need to know" dependencies
- If you are unsure whether something is a dependency or a reference, ask: "Could this data point exist without the other?" If yes, it is a reference. If no, it is a dependency.

---

### PROVIDES

**What downstream data points consume this data point.**

This is the flip side of BUILDS_ON. It tells you who cares about your content -- who needs to be notified when you make changes.

**Think of it as:** The answer to "Who uses my output, and what do they use it for?"

**Example:**
```
PROVIDES = [
  voice_guidelines -> messaging_framework,
  content_guidelines -> marketing_plans
]
```

**Format:** `what_you_provide -> who_consumes_it`

**Tips:**
- This keyword is essential for change management. When you update a data point, PROVIDES tells you exactly which downstream data points to review.
- Keep the description of what you provide specific. "voice_guidelines" is better than "everything"
- If PROVIDES is empty, either this data point is a leaf node (nothing depends on it) or you have not mapped the relationships yet

---

## Template

Use this template to define any new context data point. Start with DOMAIN and EXCLUSIVELY_OWNS (Level 1). Add the remaining keywords as your needs grow.

```
[Data Point Name]

DOMAIN = [One-to-three sentence description of this data point's
          scope and purpose]

EXCLUSIVELY_OWNS = [
  first piece of unique knowledge |
  second piece of unique knowledge |
  third piece of unique knowledge |
  ... add as many as needed
]

STRICTLY_AVOIDS = [
  content that belongs elsewhere (-> Where It Belongs) |
  more content that belongs elsewhere (-> Where It Belongs) |
  ... focus on common areas of confusion
]

BUILDS_ON = [upstream_data_point:what_it_provides]
REFERENCES = [related_data_point:what_to_look_at]
PROVIDES = [what_you_provide -> downstream_consumer]
```

---

## Complete Example: Brand Voice

Here is a fully worked ownership specification for a "Brand Voice" data point. This example shows all six keywords in use with realistic content.

```
Brand Voice

DOMAIN = [Brand voice and communication personality guidelines
          serving as the authoritative reference for how the brand
          speaks across all channels]

EXCLUSIVELY_OWNS = [
  tone and personality attributes |
  writing style guidelines |
  vocabulary preferences and restrictions |
  channel-specific voice adaptations |
  voice dos and don'ts with examples
]

STRICTLY_AVOIDS = [
  specific messaging and taglines (-> Messaging Framework) |
  visual identity guidelines (-> Visual Identity) |
  audience demographics (-> Target Audience) |
  competitive positioning claims (-> Value Proposition)
]

BUILDS_ON = [brand_identity:core_personality_foundation]
REFERENCES = [target_audience:audience_communication_preferences]
PROVIDES = [
  voice_guidelines -> messaging_framework,
  content_guidelines -> marketing_plans
]
```

**What this specification tells you at a glance:**

- **Scope:** This data point covers how the brand sounds, not what it says (messaging) or how it looks (visual identity)
- **Unique content:** Tone, style, vocabulary, channel adaptations, and examples. You will only find these HERE.
- **Boundaries:** If someone tries to add a tagline to this data point, the specification redirects them to the Messaging Framework.
- **Dependency:** Brand Voice depends on Brand Identity. If the brand's core personality changes, the voice needs to be reviewed.
- **Reference:** Brand Voice benefits from knowing about audience communication preferences, but does not strictly depend on them.
- **Consumers:** Both the Messaging Framework and Marketing Plans rely on this data point's voice guidelines. If the voice changes, both need review.

---

## Second Example: Target Audience

```
Target Audience

DOMAIN = [Definitive target audience profile and customer
          characteristics serving as the foundational reference
          for all customer-related business strategy]

EXCLUSIVELY_OWNS = [
  target organization types and size specifications |
  decision-maker roles and authority profiles |
  customer demographic and firmographic characteristics |
  audience segmentation and prioritization frameworks |
  geographic and industry targeting criteria |
  customer qualification standards and selection criteria |
  primary and secondary audience distinctions |
  audience-product alignment and strategic rationale
]

STRICTLY_AVOIDS = [
  customer pain points and challenges (-> Customer Pain Points) |
  customer desired outcomes and benefits (-> Customer Desired Outcomes) |
  customer tasks and jobs-to-be-done (-> Customer Jobs to Be Done) |
  market-wide industry segmentation and sizing (-> Market Context) |
  brand communication preferences (-> Brand Voice)
]

BUILDS_ON = [
  brand_identity:strategic_alignment,
  product_description:product_context_for_targeting,
  market_context:market_foundation_for_targeting_decisions
]
REFERENCES = [competitive_landscape:competitor_audience_overlap]
PROVIDES = [
  audience_foundation -> customer_pain_points,
  audience_foundation -> customer_desired_outcomes,
  audience_foundation -> customer_jobs_to_be_done,
  customer_context -> strategic_goals,
  targeting_criteria -> marketing_plans
]
```

Notice the clear separation: Target Audience owns WHO the customers are. It explicitly avoids their pain points, desired outcomes, and tasks -- those belong to their own data points. This prevents the common problem of a "target audience" document that balloons into a catch-all customer intelligence dump.

---

## Why Boundaries Matter

### The Drift Problem

Without explicit boundaries, context drifts. Here is how it typically plays out:

**Without boundaries:**

1. Someone creates a brand guide with a section about "our story"
2. The pitch deck team writes their own version of the brand story, adapted for investors
3. The website team writes a third version for the About page
4. The sales team extracts key points for their introductory email
5. Six months later, the four versions tell slightly different stories. One says the company was founded in 2019, another says 2020. One emphasizes the technology, another emphasizes the founder's vision.

Nobody is wrong. They all started from the same source. But without a clear authority and explicit boundaries, natural drift produced four conflicting versions.

**With boundaries:**

1. Brand Identity OWNS the brand story. It is the single authority.
2. The pitch deck REFERENCES Brand Identity and adapts the tone for investors -- but the facts come from the authority.
3. The website REFERENCES Brand Identity and adapts the length for the About page -- but the facts come from the authority.
4. The sales email REFERENCES Brand Identity and excerpts the key points -- but the facts come from the authority.
5. When the brand story is updated, it is updated in ONE place. All downstream uses inherit the change.

The ownership specification makes this structure explicit and enforceable.

### What Happens When Boundaries Are Missing

| Symptom | Root Cause | Specification Fix |
|---|---|---|
| "Which version of X is correct?" | No clear authority | Define DOMAIN and EXCLUSIVELY_OWNS |
| "I updated X but Y still has the old version" | Duplicate content | Define STRICTLY_AVOIDS to prevent duplication |
| "Changing X broke Y" | Hidden dependency | Define BUILDS_ON and PROVIDES to make dependencies visible |
| "This document has gotten way too long" | Scope creep | Define STRICTLY_AVOIDS to redirect content to proper homes |
| "Two teams disagree about what belongs here" | Overlapping ownership | Define EXCLUSIVELY_OWNS for both and resolve the overlap |

---

## Common Mistakes

### 1. Overlapping EXCLUSIVELY_OWNS

**The problem:** Two data points both claim exclusive ownership of the same concept.

Example: Brand Voice says it EXCLUSIVELY_OWNS "key brand messages" and Messaging Framework says it EXCLUSIVELY_OWNS "core brand messaging."

**The fix:** Clarify the distinction. Perhaps Brand Voice owns the TONE of messaging (how it sounds) and Messaging Framework owns the CONTENT of messaging (what it says). If they truly overlap, one must cede territory to the other.

### 2. Circular Dependencies

**The problem:** Data Point A BUILDS_ON Data Point B, and Data Point B BUILDS_ON Data Point A.

Example: Value Proposition depends on Target Audience (need to know who to speak to), and Target Audience depends on Value Proposition (need to know what value to target for).

**The fix:** Determine which comes first logically. Usually one is more foundational. In this case, Target Audience is likely foundational (you define who you serve first), and Value Proposition BUILDS_ON it. The reverse connection is a REFERENCE, not a dependency.

### 3. Over-Specification

**The problem:** Every data point has 20 items in EXCLUSIVELY_OWNS, 15 in STRICTLY_AVOIDS, and dependencies on 10 other data points.

**The fix:** Start simple. You can always add detail later. An over-specified architecture is as hard to maintain as no architecture at all. Aim for 3-8 items in EXCLUSIVELY_OWNS and 2-5 in STRICTLY_AVOIDS.

### 4. Under-Specification

**The problem:** DOMAIN says "stuff about our brand" and EXCLUSIVELY_OWNS is empty.

**The fix:** If you cannot articulate what this data point exclusively owns, it is either too vague or it does not need to exist as a standalone data point. Be specific enough that someone could determine whether a given piece of content belongs here or not.

### 5. Ignoring PROVIDES

**The problem:** Data points are specified in isolation without tracking who consumes them downstream.

**The fix:** PROVIDES is your change management tool. Without it, you cannot answer the question "If I update this, what else might break?" Fill it in as you discover consumers, even if it is not complete on day one.

---

## Getting Started

You do not need to write full specifications for all your data points at once. Here is a practical approach:

1. **Start with DOMAIN and EXCLUSIVELY_OWNS for your 5-8 core data points.** This alone prevents most ownership conflicts.

2. **Add STRICTLY_AVOIDS when overlap appears.** You will know it is time when two teams disagree about where something belongs.

3. **Add BUILDS_ON and REFERENCES when dependencies matter.** You will know it is time when changing one data point unexpectedly affects another.

4. **Add PROVIDES when you need change management.** You will know it is time when updates to one data point are not making it to downstream consumers.

See [context-architecture.md](./context-architecture.md) for the broader framework of how data points fit together, and [clear-principles.md](./clear-principles.md) for the principles that guide all of this.

---

**The ownership specification is a tool for clarity, not bureaucracy. Use as much of it as you need, and no more.**
