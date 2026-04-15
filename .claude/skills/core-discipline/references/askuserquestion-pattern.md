# AskUserQuestion Pattern

**Canonical usage pattern for structured user choice across all BCOS skills, workflows, and interactions.**

The `AskUserQuestion` tool renders a clickable menu in the Claude Code UI, integrates with the session dashboard (sessions with active questions show "Awaiting input"), and standardises how the user moves forward after Claude produces a result. Every BCOS skill that reaches a decision point should use it instead of prose questions.

---

## Why This Is A Rule

- **One consistent interface.** Users learn the pattern once; every skill follows it. Onboarding, ingest, tune, migrate, dispatcher output, update confirmations — all feel the same.
- **Dashboard-aware UX.** A session with an active `AskUserQuestion` shows as "Awaiting input" (yellow). A session with a prose question looks like normal text output and sits as "Ready" — the user has to open it to see there's a decision pending. Structured questions make attention-needed sessions visible at a glance.
- **Scannability.** A 2-4 option menu is faster to read and click than a paragraph of "would you like me to X, or alternatively Y, and by the way Z is also possible".
- **No dead-ends.** Prose questions often include a "what next?" without concrete choices. Structured choices always offer a path forward.
- **Judgement-preserving.** Forcing Claude to enumerate 2-4 options constrains the action space, which helps the user decide AND helps Claude avoid over-reaching.

---

## When to Use AskUserQuestion

Use it whenever Claude is about to ask the user to pick between possibilities, approve an action, or direct a next step. Common triggers:

| Situation | Example |
|---|---|
| Proposing changes that need approval | "Apply 12 framework updates?" / "Create these 5 data points?" |
| Offering competing approaches | "Synthesize into new DP, wrap existing, or map as external reference?" |
| Surfacing findings that need triage | "Walk me through action items / show full digest / dismiss" |
| Confirming destructive or semi-destructive ops | "Archive these 3 originals?" / "Migrate 5 old tasks to new dispatcher?" |
| Clarifying ambiguous user intent | "By 'weekly audit' do you mean Mondays or Fridays?" |
| Onboarding path selection | "Where does your knowledge live? Files / Connected system / Scratch?" |
| Config edits before writing | Every schedule-tune operation — show diff + ask |
| Workflow branching | "Continue with next item / pause / skip" |

## When NOT to Use AskUserQuestion

- **Information-only responses.** "Here's what I found." — no choice needed, no question.
- **Truly trivial acknowledgements** where adding a menu adds more friction than value. Example: user says "thanks, done" — Claude doesn't need to re-ask.
- **Free-form text input.** If the right answer genuinely requires the user to TYPE something (a name, a path, a custom schedule string), ask in prose. AskUserQuestion supports "Other" → free text as a fallback, but don't force users into a multi-step choice when they're going to type anyway.
- **Rapid-fire correction loops** inside a single thinking step. If Claude is drafting and catches its own issue, fix it internally — don't interrupt the user.
- **Scheduled-task clean-green output.** Per the dispatcher rule: when a run finishes green with zero findings, output a one-line summary and stop. The dashboard marks the session Ready. Asking a question on a clean run makes every yellow status meaningless.

---

## How to Structure a Good AskUserQuestion Call

### The question

- Short, specific, ends with a question mark
- Describes the decision, not a summary of what Claude just did (keep summary in the lead-in prose)
- Good: *"Apply 12 framework updates?"* / *"What should I do with these 5 original files?"* / *"Which cluster does this data point belong to?"*
- Bad: *"Let me know what you want to do"* / *"Is this okay?"* / *"Anything else?"*

### The header

- Under 12 characters, displayed as a chip in the UI
- Use a noun or short noun-phrase describing the decision class
- Good: `"Update"`, `"Next step"`, `"Data points"`, `"Schedule"`, `"Migration"`
- Bad: `"Please choose"`, `"Action"` (too generic), or >12 chars

### The options

- **2-4 options.** Not 1 (that's not a question), not 5+ (decision fatigue). If you genuinely have more than 4, pick the top 3 and add "Something else" as the fourth with description like "I'll describe what I want".
- **Start with a verb.** The user reads what they'll GET by clicking. "Apply changes", "Show detail", "Dismiss for now" — not "Changes applied" or "Detail view".
- **Under 40 characters per label.** Anything longer means the question is doing work the option should do. Move prose to the `description` field.
- **Mutually exclusive** (unless `multiSelect: true`). No overlap.
- **At least one "DO something useful"** option — the affirmative path.
- **At least one "dismiss / defer / cancel"** option unless the action is truly non-skippable.
- **Recommended option first** with "(Recommended)" suffix if there's a clear best choice.

### The description field

Optional but useful for disambiguation. Use when:
- Two options look similar ("Apply" vs "Apply and close" — describe the difference)
- There's a subtle consequence worth flagging ("This cannot be undone easily")
- User needs context to choose ("Archive means the file moves to `_archive/` with a note — content is preserved")

---

## Canonical Examples

### Good: Approval of a proposed action

```
Question: "Apply 12 framework updates?"
Header: "Update"
Options:
  - Apply all 12
    description: "Copies new + modified files, merges settings.json and .gitignore additively."
  - Show me the full list first
    description: "I'll print each file name with what changes, then ask again."
  - Cancel
    description: "No changes made to your repo."
```

### Good: Onboarding path selection

```
Question: "Where does your business knowledge live right now?"
Header: "Sources"
Options:
  - Files I'll share
    description: "Drop them in docs/_inbox/ or point me to their location."
  - Connected system (Google Drive / Notion / Confluence)
    description: "I'll browse via MCP. Tell me which folders to look at."
  - Both
  - Starting from scratch
    description: "Use our conversation and your website to build context."
```

### Good: Dispatcher action-item triage

```
Lead-in (plain text):
  "Maintenance complete — verdict: amber.
   3 findings, 2 auto-fixed. Full report: docs/_inbox/daily-digest.md"

Question: "Maintenance found 3 things needing your attention. What next?"
Header: "Next step"
Options:
  - Walk me through them
    description: "I'll load each action item and ask what to do."
  - Show full digest
    description: "Display the whole report, then re-ask."
  - Dismiss for now
    description: "Session marks Ready. I won't revisit until tomorrow."
```

### Bad: Prose-masquerading question

```
"I can either apply the update, or we could first review each file.
Let me know how you'd like to proceed."
```

**Why it's bad:** no clickable menu, two options buried in prose, ambiguous trailing "let me know".

**Fix:** convert to AskUserQuestion with two options ("Apply", "Review first").

### Bad: Overstuffed options

```
Options:
  - Yes
  - Yes but only for the first two files
  - Yes but skip the broken-xref ones
  - Yes but also run the audit afterwards
  - No
```

**Why it's bad:** overlapping, requires the user to hold state across options, 5 choices.

**Fix:** ask the primary Yes/No first. If Yes, follow up with a separate AskUserQuestion for the modifiers.

---

## Special Case: Wrapping Scripts That Have Their Own Prompts

Several BCOS scripts use Python `input()` or bash `read` for interactive confirmation (e.g., `update.py` asks *"Apply N framework file updates? [y/N]"*). When Claude invokes these from a session, don't rely on the script's prompt — it won't surface as an interactive chat experience. Instead:

1. Invoke with a dry-run flag first (`update.py --dry-run`)
2. Parse the output to extract what would change
3. Present the summary as the lead-in to `AskUserQuestion`
4. Based on user's choice, re-invoke the script with `--yes` (or cancel)

This keeps the UX consistent across Claude-invoked and shell-invoked usage: the shell user gets the prompt, the Claude user gets the menu, the script logic stays identical.

### Pattern for `update.py`

```
1. Run: python .claude/scripts/update.py --dry-run
2. Parse: N new / M modified / K review / J auto-merge / X unchanged
3. AskUserQuestion:
   Question: "Apply N framework updates? (M modified + K new)"
   Header: "Update"
   Options:
     - Apply all
     - Show me the changed files first
     - Cancel
4. If "Apply all" → python .claude/scripts/update.py --yes
5. If "Show me" → print the file list, re-ask with narrower options
6. If "Cancel" → report "No changes" and stop
```

---

## Enforcement

This pattern is not optional for skill authors. If a skill reaches a decision point and doesn't use `AskUserQuestion`, that's a drift finding the `architecture-review` scheduled job will surface.

When contributing new skills or editing existing ones:

- Every decision point in the skill's workflow → `AskUserQuestion` call
- Every "should I X?" prose line → replace with `AskUserQuestion`
- Every list of options in the skill prose ("you can A, B, or C") → make them option labels

The goal is for a user interacting with BCOS to always see the same pattern: short summary, clickable choices, structured move-forward. No walls of text, no dead-end questions, no ambiguous "let me know".
