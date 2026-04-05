# Ecosystem Changes Checklist

## After Any Ecosystem Change

Run this checklist after creating, modifying, or removing any agent or skill.

---

### Step 1: Verify Agent Discovery

```bash
bash .claude/agents/agent-discovery/find_agents.sh
```

- Confirm new/modified agents appear in output
- Confirm removed agents are absent
- Note the total count

### Step 2: Verify Skill Discovery

```bash
bash .claude/skills/skill-discovery/find_skills.sh
```

- Confirm new/modified skills appear in output
- Confirm removed skills are absent
- Note the total count

### Step 3: Compare Against state.json

Read `.claude/quality/ecosystem/state.json` and compare:

- Does the agent count match discovery output?
- Does the skill count match discovery output?
- Are all names accurate?
- Are any entries stale (exist in state.json but not on disk)?

### Step 4: Check for Broken Cross-References

Search for references to the changed component:

- Do any other agents/skills reference the old name?
- Do any reference files link to removed components?
- Are all `references/` paths valid?

### Step 5: Update state.json If Needed

If discovery results differ from state.json:

- Update the inventory arrays
- Update counts
- Update the `lastUpdated` timestamp

### Step 6: Update ECOSYSTEM-MAP.md If Needed

If the change adds a new category, removes a component, or changes relationships:

- Update `.claude/ECOSYSTEM-MAP.md`
- Keep the map accurate to the current state

### Step 7: Update reference-index.json If New Docs

If new reference documents were added:

- Add entries to the reference index
- Include path, description, and consumer information

### Step 8: Capture Lessons Learned

If anything notable happened during the change:

- What worked well?
- What was unexpected?
- What would you do differently?

Add to `.claude/quality/ecosystem/lessons.json` following the schema in `lessons-schema.md`.
