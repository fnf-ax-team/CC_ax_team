# DCS-AI Project Guidelines

AI-powered chatbot with MCP (Model Context Protocol) tool integration for enterprise use.

---

## When to Use

Reference this skill when working on the DCS-AI project. This guide contains:
- Architecture overview
- File structure
- Code patterns
- Testing requirements
- Deployment workflow

---

## Architecture Overview

**Tech Stack:**
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Redux Toolkit, SWR, TailwindCSS
- **Backend**: NestJS, TypeScript, PostgreSQL (primary), Snowflake (analytics/sub)
- **AI**: LangChain, AI SDK, MCP Tools
- **Auth**: NextAuth with Microsoft SSO + JWT
- **Deployment**: Docker Hub + EC2 (Turborepo monorepo)

**Services:**
```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  Next.js 15 + React 19 + TypeScript + TailwindCSS          │
│  Port: 3000 | Turbopack enabled                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Backend                             │
│  NestJS + TypeScript + LangChain                           │
│  Port: 3001 | HTTP Streaming (NOT WebSockets)              │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        ┌──────────┐                   ┌──────────┐
        │PostgreSQL│                   │Snowflake │
        │ (Primary)│                   │  (Sub)   │
        └──────────┘                   └──────────┘
              │
              ▼
    ┌──────────────────┐
    │   MCP Servers    │
    │ (Dynamic Tools)  │
    └──────────────────┘
```

---

## File Structure

```
DCS-AI/
├── client/                      # Next.js 15 Frontend
│   └── src/
│       ├── app/                 # Next.js App Router + providers
│       │   ├── api/             # API routes (NextAuth)
│       │   ├── (auth)/          # Auth-protected routes
│       │   └── chat/            # Chat pages
│       ├── pages/               # Page components
│       ├── widgets/             # Complex composite UI
│       ├── features/            # User interactions (hooks + UI)
│       │   ├── chat/            # Chat feature
│       │   └── mcp-server/      # MCP server management
│       ├── entities/            # Business entities
│       │   ├── chat/            # Chat entity (model/api/ui)
│       │   ├── user/            # User entity
│       │   └── mcp-server/      # MCP server entity
│       └── shared/              # Shared utilities
│           ├── api/             # API client (fetch wrapper)
│           ├── ui/              # UI kit components
│           ├── lib/             # Utilities
│           └── model/           # Redux store
│
├── server/                      # NestJS Backend
│   └── src/
│       ├── auth/                # Authentication (NextAuth guard)
│       ├── chat/                # Chat module
│       ├── mcp/                 # MCP tool integration
│       ├── database/            # Database services
│       │   ├── snowflake.service.ts  # Snowflake (sub/analytics)
│       │   └── entities/        # TypeORM entities (PostgreSQL)
│       └── common/              # Shared utilities
│
├── turbo.json                   # Turborepo configuration
├── pnpm-workspace.yaml          # pnpm workspace
└── package.json                 # Root package.json
```

---

## Code Patterns

### FSD Import Rules (Frontend)

```
app → pages → widgets → features → entities → shared
         ↓         ↓          ↓          ↓
    (can import from layers to the right only)
```

```typescript
// CORRECT: features importing from entities and shared
import { ChatMessage } from '@/entities/chat';
import { Button } from '@/shared/ui/button';

// WRONG: entities importing from features
import { useChatFeature } from '@/features/chat'; // NEVER DO THIS
```

### API Client (Frontend)

```typescript
import { apiClient } from '@/shared/api/client';

// GET request
const data = await apiClient.fetcher('/endpoint');

// POST with body
const response = await apiClient.fetcherRaw('/endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

// File download
const blob = await apiClient.downloadFile('/file/123');

// IMPORTANT: Always use credentials: 'include' for JWT
```

### HTTP Streaming (Backend)

```typescript
// CORRECT: HTTP streaming with chunked transfer encoding
@Post('chat/stream')
async streamChat(@Res() res: Response) {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Transfer-Encoding', 'chunked');

  for await (const chunk of this.chatService.streamResponse()) {
    res.write(chunk);
  }
  res.end();
}

// WRONG: WebSocket or SSE
// This project does NOT use WebSockets for chat
```

### Authentication (Backend)

```typescript
import { UseGuards } from '@nestjs/common';
import { NextAuthGuard } from '@/auth/guards/next-auth.guard';

@UseGuards(NextAuthGuard)
@Controller('chat')
export class ChatController {
  @Post()
  async createChat(@Request() req) {
    const userId = req.user.id; // Extracted from JWT
    // ...
  }
}
```

### Database Usage

**PostgreSQL is the primary database for ALL system data.**

```typescript
// PostgreSQL: ALL system data (chat, users, MCP, etc.)
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ChatMessage } from '@/database/entities/chat-message.entity';

@Injectable()
export class ChatService {
  constructor(
    @InjectRepository(ChatMessage)
    private chatRepo: Repository<ChatMessage>
  ) {}

  async getChatHistory(userId: string) {
    return this.chatRepo.find({ where: { userId } });
  }
}

// Snowflake: ONLY for analytics/sub queries (not primary data)
import { SnowflakeService } from '@/database/snowflake.service';

@Injectable()
export class AnalyticsService {
  constructor(private snowflake: SnowflakeService) {}

  async getAnalytics() {
    return this.snowflake.execute('SELECT * FROM analytics_view');
  }
}
```

### State Management (Frontend)

```typescript
// Redux Toolkit for global state
import { useSelector, useDispatch } from 'react-redux';
import { selectUser } from '@/entities/user/model/store';

// SWR for server state
import useSWR from 'swr';
const { data, mutate } = useSWR('/api/chats', fetcher);

// Local state for component-specific state
const [isOpen, setIsOpen] = useState(false);
```

### Component Pattern (Frontend)

```typescript
interface Props {
  chatId: string;
  onSend?: (message: string) => void;
}

export function ChatInput({ chatId, onSend }: Props) {
  // 1. Hooks
  const [message, setMessage] = useState('');
  const { data: session } = useSession();

  // 2. Effects
  useEffect(() => {
    // setup
  }, [chatId]);

  // 3. Handlers
  const handleSubmit = () => {
    onSend?.(message);
    setMessage('');
  };

  // 4. Render
  return (
    <form onSubmit={handleSubmit}>
      <input value={message} onChange={e => setMessage(e.target.value)} />
      <Button type="submit">Send</Button>
    </form>
  );
}
```

---

## Testing Requirements

### Frontend (Playwright)

```bash
# Run all E2E tests
cd client && pnpm test

# Run specific test
pnpm exec playwright test tests/chat.spec.ts
```

**Test structure:**
```typescript
// client/tests/chat.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Chat', () => {
  test('should send message', async ({ page }) => {
    await page.goto('/chat');
    await page.fill('[data-testid="chat-input"]', 'Hello');
    await page.click('[data-testid="send-button"]');
    await expect(page.locator('.message')).toContainText('Hello');
  });
});
```

### Backend (Jest)

```bash
# Run all tests
cd server && pnpm test

# Run with coverage
pnpm test -- --coverage

# Run specific test
pnpm test -- chat.service.spec.ts
```

**Test structure:**
```typescript
// server/src/chat/chat.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { ChatService } from './chat.service';

describe('ChatService', () => {
  let service: ChatService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [ChatService],
    }).compile();

    service = module.get<ChatService>(ChatService);
  });

  it('should create chat message', async () => {
    const result = await service.createMessage({
      content: 'Hello',
      userId: 'user-1',
    });
    expect(result.content).toBe('Hello');
  });
});
```

---

## Deployment Workflow

### Pre-Deployment Checklist

- [ ] All tests passing (`pnpm test` in both client and server)
- [ ] Build succeeds (`pnpm build`)
- [ ] No TypeScript errors
- [ ] No hardcoded secrets
- [ ] Environment variables documented

### Development Commands (Turborepo)

```bash
# Run both client and server
pnpm dev

# Run only client
pnpm dev:client

# Run only server
pnpm dev:server

# Build all
pnpm build

# Lint all
pnpm lint
```

### Docker Deployment

```bash
# Build images
docker build -t dcs-ai-client:latest ./client
docker build -t dcs-ai-server:latest ./server

# Push to registry
docker push dcs-ai-client:latest
docker push dcs-ai-server:latest

# Run with docker-compose
docker-compose up --build
```

### Environment Variables

```bash
# Client (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret
AZURE_AD_CLIENT_ID=xxx
AZURE_AD_CLIENT_SECRET=xxx
AZURE_AD_TENANT_ID=xxx

# Server (.env)
PORT=3001
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=xxx
POSTGRES_PASSWORD=xxx
POSTGRES_DATABASE=xxx
JWT_SECRET=your-jwt-secret

# Snowflake (sub/analytics only)
SNOWFLAKE_ACCOUNT=xxx
SNOWFLAKE_USER=xxx
SNOWFLAKE_PASSWORD=xxx
SNOWFLAKE_DATABASE=xxx
```

---

## Critical Rules

1. **No WebSockets for chat** - Use HTTP streaming with chunked transfer encoding
2. **FSD import rules** - Higher layers import from lower layers only
3. **API client consistency** - Frontend uses `apiClient` (fetch), backend uses `axios` for external APIs
4. **JWT in all requests** - Use `credentials: 'include'` for fetch
5. **PostgreSQL is primary** - ALL system data (chat, users, MCP) in PostgreSQL. Snowflake is sub/analytics only
6. **TypeScript strict** - All entities need proper type definitions
7. **Use shared UI** - Check `@/shared/ui` before creating new components
8. **No console.log** - Use proper logging in production

---

## Related Skills

- `coding-standards.md` - General coding best practices
- `backend-patterns.md` - NestJS and API patterns
- `frontend-patterns.md` - React and Next.js patterns
