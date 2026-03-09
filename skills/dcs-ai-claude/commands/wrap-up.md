---
description: Summarize current session and update documentation
---

# Wrap Up Session

**⚡ Action Required**: Use the `Task` tool to spawn the `doc-summarizer` sub-agent.

```
Task({
  subagent_type: "doc-summarizer",
  prompt: "Summarize this session's work and update docs/SESSION_LOG.md with a detailed summary including: what was discussed, what was implemented, key decisions made, and any follow-up items.",
  description: "Session wrap-up"
})
```

## What This Command Does

1. **Analyze Session** - Review conversation and changes made
2. **Summarize Work** - Create a human-readable summary
3. **Document Decisions** - Record key decisions and rationale
4. **List Follow-ups** - Identify pending tasks or issues
5. **Update SESSION_LOG.md** - Append detailed entry

## When to Use

Use `/wrap-up` when:
- Ending a development session
- Before switching to a different task
- After completing a major feature
- Before handing off to another team member

## Output Format

```markdown
## YYYY-MM-DD HH:MM - Session Summary

### What Was Done
- [Bullet points of completed work]

### Key Decisions
- [Important decisions made and why]

### Code Changes
- [List of modified files with brief description]

### Follow-up Items
- [ ] [Pending tasks]
- [ ] [Issues to investigate]

### Notes
[Any additional context for future reference]
```

## Example Usage

```
User: /wrap-up

Agent (doc-summarizer):
# Session Summary - 2025-01-22

## What Was Done
- Configured Claude Code for DCS-AI project
- Created 9 custom agents for development workflows
- Set up 9 slash commands with sub-agent integration
- Added hooks for auto-formatting and session logging

## Key Decisions
- Used Task tool pattern to connect commands with sub-agents
- Chose stop hook for auto-logging instead of manual
- SESSION_LOG.md placed in docs/ directory

## Code Changes
- .claude/settings.json - Added session logging hook
- .claude/commands/*.md - Updated 7 commands
- .claude/agents/doc-summarizer.md - New agent

## Follow-up Items
- [ ] Test all commands with team
- [ ] Add more project-specific rules
- [ ] Consider adding pre-commit hooks

---
✅ Session logged to docs/SESSION_LOG.md
```

## Integration

- **Stop Hook** automatically logs basic info (files, commits)
- **`/wrap-up`** adds detailed human-written summary
- Both write to `docs/SESSION_LOG.md`

Use `/wrap-up` for important sessions where context matters.
