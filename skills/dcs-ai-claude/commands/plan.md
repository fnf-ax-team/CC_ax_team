---
description: Create implementation plan before writing code. WAIT for user confirmation.
---

# Plan

**⚡ Action Required**: Use the `Task` tool to spawn the `planner` sub-agent.

```
Task({
  subagent_type: "planner",
  prompt: "Create an implementation plan for the requested feature. Restate requirements, identify risks, break down into phases, and WAIT for user confirmation before proceeding.",
  description: "Implementation planning"
})
```

## Context for the Agent

The planner agent will:

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## Plan Output Format

```markdown
# Implementation Plan: [Feature Name]

## Requirements Restatement
- [Clear bullet points]

## Implementation Phases

### Phase 1: [Name]
- Step 1
- Step 2

### Phase 2: [Name]
- Step 1
- Step 2

## Dependencies
- [List external dependencies]

## Risks
- HIGH: [Risk description]
- MEDIUM: [Risk description]
- LOW: [Risk description]

## Estimated Complexity: [HIGH/MEDIUM/LOW]

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Important

**CRITICAL**: The planner agent will **NOT** write any code until you explicitly confirm the plan.

Respond with:
- "yes" or "proceed" to start implementation
- "modify: [changes]" to adjust the plan
- "no" to cancel
