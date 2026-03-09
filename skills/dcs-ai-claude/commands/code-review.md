---
description: Review code changes for security vulnerabilities, code quality, and best practices
---

# Code Review

**⚡ Action Required**: Use the `Task` tool to spawn the `code-reviewer` sub-agent.

```
Task({
  subagent_type: "code-reviewer",
  prompt: "Review the uncommitted code changes. Run git diff to see changes and provide a comprehensive review.",
  description: "Code review"
})
```

## Context for the Agent

The code-reviewer agent will check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Missing input validation
- Insecure dependencies
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- console.log statements
- TODO/FIXME comments

**Best Practices (MEDIUM):**
- Mutation patterns (use immutable instead)
- Missing tests for new code
- Accessibility issues (a11y)

## Approval Criteria

- ✅ Approve: No CRITICAL or HIGH issues
- ⚠️ Warning: MEDIUM issues only
- ❌ Block: CRITICAL or HIGH issues found

Never approve code with security vulnerabilities!
