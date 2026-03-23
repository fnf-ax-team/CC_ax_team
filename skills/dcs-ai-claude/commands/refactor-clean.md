---
description: Safely identify and remove dead code with test verification
---

# Refactor Clean

**⚡ Action Required**: Use the `Task` tool to spawn the `refactor-cleaner` sub-agent.

```
Task({
  subagent_type: "refactor-cleaner",
  prompt: "Analyze the codebase for dead code and safely remove it. Run tests before and after each deletion.",
  description: "Dead code cleanup"
})
```

## Context for the Agent

The refactor-cleaner agent will:

1. Run dead code analysis:
   - Find unused exports and files
   - Find unused dependencies
   - Find unused TypeScript exports

2. Categorize findings by severity:
   - SAFE: Test files, unused utilities
   - CAUTION: API routes, components
   - DANGER: Config files, main entry points

3. Propose safe deletions only

4. Before each deletion:
   - Run full test suite
   - Verify tests pass
   - Apply change
   - Re-run tests
   - Rollback if tests fail

5. Show summary of cleaned items

## Safety Rules

- Never delete code without running tests first
- Only delete SAFE category items automatically
- CAUTION items require user confirmation
- DANGER items are flagged but never auto-deleted
