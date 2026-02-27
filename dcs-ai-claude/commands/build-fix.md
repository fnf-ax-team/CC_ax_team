---
description: Incrementally fix TypeScript and build errors
---

# Build and Fix

**⚡ Action Required**: Use the `Task` tool to spawn the `build-error-resolver` sub-agent.

```
Task({
  subagent_type: "build-error-resolver",
  prompt: "Run the build command and fix any errors. Parse error output, explain issues, and fix them one at a time.",
  description: "Fix build errors"
})
```

## Context for the Agent

The build-error-resolver agent will:

1. Run build: `pnpm build` (in client/ or server/)

2. Parse error output:
   - Group by file
   - Sort by severity

3. For each error:
   - Show error context (5 lines before/after)
   - Explain the issue
   - Propose fix
   - Apply fix
   - Re-run build
   - Verify error resolved

4. Stop if:
   - Fix introduces new errors
   - Same error persists after 3 attempts
   - User requests pause

5. Show summary:
   - Errors fixed
   - Errors remaining
   - New errors introduced

Fix one error at a time for safety!
