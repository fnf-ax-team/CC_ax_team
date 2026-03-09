---
description: Generate and run end-to-end tests with Playwright
---

# E2E Testing

**⚡ Action Required**: Use the `Task` tool to spawn the `e2e-runner` sub-agent.

```
Task({
  subagent_type: "e2e-runner",
  prompt: "Generate and run E2E tests for the specified user flow. Use Playwright with Page Object Model pattern.",
  description: "E2E testing"
})
```

## Context for the Agent

The e2e-runner agent will:

1. **Analyze user flow** and identify test scenarios
2. **Generate Playwright test** using Page Object Model pattern
3. **Run tests** across browsers (Chrome, Firefox, Safari)
4. **Capture failures** with screenshots, videos, and traces
5. **Generate report** with results and artifacts
6. **Identify flaky tests** and recommend fixes

## DCS-AI Critical Flows

**Must Test:**
- Chat message sending and AI response
- MCP tool execution
- User authentication flow
- HTTP streaming responses

## Test Artifacts

- HTML Report with timeline and results
- Screenshots on failure
- Video recording on failure
- Trace files for debugging

## Quick Commands

```bash
# Run all E2E tests
cd client && pnpm test

# Run specific test
pnpm exec playwright test tests/e2e/chat.spec.ts

# Debug mode
pnpm exec playwright test --debug

# View report
pnpm exec playwright show-report
```
