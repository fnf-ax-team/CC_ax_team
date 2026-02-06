---
description: Enforce test-driven development. Write tests FIRST, then implement.
---

# TDD (Test-Driven Development)

**⚡ Action Required**: Use the `Task` tool to spawn the `tdd-guide` sub-agent.

```
Task({
  subagent_type: "tdd-guide",
  prompt: "Guide TDD implementation for the requested feature. Follow RED-GREEN-REFACTOR cycle: write failing test first, then minimal implementation, then refactor.",
  description: "TDD development"
})
```

## Context for the Agent

The tdd-guide agent will enforce:

```
RED → GREEN → REFACTOR → REPEAT

RED:      Write a failing test
GREEN:    Write minimal code to pass
REFACTOR: Improve code, keep tests passing
REPEAT:   Next feature/scenario
```

## DCS-AI Test Stack

- **Backend (server/)**: Jest + NestJS Testing Module
- **Frontend (client/)**: Playwright

## TDD Cycle Example

### 1. SCAFFOLD - Define Interface
```typescript
interface CreateMessageDto {
  content: string;
  chatId: string;
}
```

### 2. RED - Write Failing Test
```typescript
describe('ChatService', () => {
  it('should create message', async () => {
    const result = await service.createMessage(dto);
    expect(result.content).toBe('Hello');
  });
});
```

### 3. GREEN - Minimal Implementation
```typescript
async createMessage(dto: CreateMessageDto) {
  return this.repo.save({ ...dto, role: 'user' });
}
```

### 4. REFACTOR - Improve
Add validation, error handling while keeping tests green.

## Coverage Requirements

- Minimum: 80% for all code
- 100% required for: Auth, MCP tools, Chat handling

## Test Commands

```bash
# Backend
cd server && pnpm test

# Frontend E2E
cd client && pnpm test
```

**Remember**: No code without tests. Tests are not optional.
