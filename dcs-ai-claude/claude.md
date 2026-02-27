# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DCS-AI is a monorepo containing a Next.js 15 (with Turbopack) frontend and NestJS backend that implements an AI-powered chatbot with MCP (Model Context Protocol) tool integration. The system uses **HTTP streaming with chunked transfer encoding** (NOT WebSockets) for real-time chat responses.

**Tech Stack:**
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Redux Toolkit, SWR, TailwindCSS
- **Backend**: NestJS, TypeScript, PostgreSQL (primary DB), Snowflake (sub)
- **AI**: LangChain, AI SDK, MCP Tools
- **Auth**: NextAuth with Microsoft SSO + JWT
- **Deployment**: Docker Hub + EC2 (current), ECS Fargate (planned)

## Essential Commands

### Client (Port 3000)
```bash
cd client
pnpm dev          # Development with Turbopack on port 3000
pnpm build        # Production build
pnpm test         # Playwright tests
pnpm lint         # ESLint + Biome linting
```

### Server (Port 3001)
```bash
cd server
pnpm dev          # Development on port 3001
pnpm build        # Production build
pnpm test         # Jest tests
pnpm migration:run    # Run Snowflake migrations
```

### Docker
```bash
# Build and run full stack
docker-compose up --build

# Individual services
docker-compose up client
docker-compose up server
```

## Architecture Patterns

### 1. Feature-Sliced Design (FSD) - Frontend

The client uses FSD architecture with strict layer hierarchy:

```
client/src/
├── app/          # Next.js App Router + global providers
├── pages/        # Next.js page components
├── widgets/      # Complex composite UI components
├── features/     # User interactions (hooks + UI)
├── entities/     # Business entities (model + api + ui)
└── shared/       # Shared utilities, UI kit, API client
```

**Critical Import Rule**: Higher layers can import from lower layers ONLY. Never import upward.
- ✅ `features/` can import from `entities/` and `shared/`
- ❌ `entities/` CANNOT import from `features/`

**FSD Layer Structure:**
```typescript
// entities/user/
├── model/
│   ├── types.ts       // TypeScript interfaces
│   └── store.ts       // Redux slice (if needed)
├── api/
│   └── user-api.ts    // API functions using apiClient
└── ui/
    └── user-card.tsx  // Presentational components

// features/user-profile/
├── model/
│   └── use-user-profile.ts  // Business logic hook
└── ui/
    └── user-profile-form.tsx // Interactive component
```

### 2. HTTP Streaming (NOT WebSockets)

**Critical**: Chat responses use HTTP streaming with chunked transfer encoding, NOT WebSockets or Server-Sent Events.

### 3. Authentication Flow

1. User logs in via Microsoft SSO (NextAuth)
2. Backend validates Azure AD token → issues JWT
3. JWT stored in httpOnly cookie
4. All API requests include JWT in cookie
5. NestJS guards (`@UseGuards(NextAuthGuard)`) validate JWT

**Frontend Session Access:**
```typescript
import { useSession } from 'next-auth/react';

const { data: session, status } = useSession();
// session.accessToken = JWT for API calls
```

**Backend Guard Usage:**
```typescript
@UseGuards(NextAuthGuard)
@Post('protected-endpoint')
async protectedRoute(@Request() req) {
  const userId = req.user.id; // Extracted from JWT
}
```

### 4. Database Strategy

- **PostgreSQL**: Primary database for ALL system data (chat, users, MCP, etc.)
- **Snowflake**: Sub/analytics only (not for primary data)

**When to use which:**
- Use PostgreSQL for: ALL system data - chat messages, users, MCP servers, external apps, etc.
- Use Snowflake for: Analytics queries, reporting (sub usage only)

**Connection Pattern** (server/src/database/):
```typescript
// PostgreSQL (primary - use for all system data)
import { InjectRepository } from '@nestjs/typeorm';
@InjectRepository(Entity) private repo: Repository<Entity>

// Snowflake (sub/analytics only)
import { SnowflakeService } from '@/database/snowflake.service';
const result = await this.snowflakeService.execute(query, binds);
```

### 5. MCP Tool Integration

MCP tools are dynamically registered and available in chat context.

**Backend Registration** (server/src/mcp/):
```typescript
@Post('servers')
async registerMcpServer(@Body() dto: CreateMcpServerDto) {
  // Validates MCP server config
  // Stores in PostgreSQL
  // Dynamically loads tools
}
```

**Frontend Usage** (client/src/entities/mcp-server/):
```typescript
// MCP tools are available in chat via special syntax
// User message: "Use @calculator to compute 5 + 3"
// Backend detects tool usage → executes MCP tool → streams result
```

## State Management

### Client-Side State

**Redux Toolkit** for global app state:
```typescript
// client/src/shared/model/store.ts
import { configureStore } from '@reduxjs/toolkit';

export const store = configureStore({
  reducer: {
    user: userReducer,
    chat: chatReducer,
  },
});
```

**SWR** for server state (data fetching):
```typescript
import useSWR from 'swr';

const { data, error, mutate } = useSWR('/api/chats', fetcher);
```

**Local State** (React hooks) for component-specific state.

## API Client Pattern

**Frontend** uses a custom `ApiClient` class (client/src/shared/api/client.ts) wrapping fetch:

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
```

**Backend** uses axios for external API calls:
```typescript
import axios from 'axios';

const response = await axios.get(externalUrl, {
  headers: { Authorization: `Bearer ${token}` },
  params: { page, limit },
});
```

### API URL Structure (CRITICAL)

**URL Prefix 구조:**
- Frontend `apiClient` base URL: `http://localhost:3001/server` (이미 `/server` 포함)
- Backend global prefix: `server` (main.ts에서 `app.setGlobalPrefix('server')`)

**올바른 패턴:**
```typescript
// Frontend API 호출 - /server 이후 경로만 사용
const BASE_URL = '/admin/tool-strategy';  // ✅ 올바름
const BASE_URL = '/api/admin/tool-strategy';  // ❌ 잘못됨 - /api 중복

// Backend Controller - /server 이후 경로만 사용
@Controller('admin/tool-strategy')  // ✅ 올바름
@Controller('api/admin/tool-strategy')  // ❌ 잘못됨 - /api 불필요

// SWR 키도 동일
useSWR('/admin/tool-strategy', ...)  // ✅ 올바름
useSWR('/api/admin/tool-strategy', ...)  // ❌ 잘못됨
```

**최종 API 경로:** `http://localhost:3001/server/admin/tool-strategy`

## Module Dependencies

### Critical Frontend Dependencies
- `ai` (4.3.13): AI SDK for streaming responses
- `@ai-sdk/react`: React hooks for chat UI
- `next-auth` (^4.24.11): Authentication
- `@reduxjs/toolkit` (^2.8.2): State management
- `swr` (^2.2.5): Data fetching
- `axios` (^1.10.0): HTTP client for API calls

### Critical Backend Dependencies
- `@nestjs/common`, `@nestjs/core`: NestJS framework
- `langchain`: AI orchestration
- `snowflake-sdk`: Snowflake database
- `typeorm`: PostgreSQL ORM
- `@nestjs/passport`, `passport-jwt`: Authentication
- `axios` (^1.6.2): External API calls

## Testing

### Frontend (Playwright)
```bash
cd client
pnpm test
```

Tests in `client/tests/` directory. Environment variable `PLAYWRIGHT=True` is set during test runs.

### Backend (Jest)
```bash
cd server
pnpm test
```

Tests in `server/src/**/*.spec.ts`. Uses in-memory database for unit tests.

## Code Style Highlights

### Import Organization
```typescript
// 1. External packages
import { useState } from 'react';
import { useRouter } from 'next/navigation';

// 2. Absolute imports (@/...)
import { apiClient } from '@/shared/api/client';
import { Button } from '@/shared/ui/button';

// 3. Relative imports
import { UserCard } from '../ui/user-card';
```

### Component Pattern
```typescript
interface Props {
  userId: string;
  onUpdate?: () => void;
}

export function UserProfile({ userId, onUpdate }: Props) {
  // 1. Hooks
  const [state, setState] = useState();

  // 2. Effects
  useEffect(() => {}, []);

  // 3. Handlers
  const handleClick = () => {};

  // 4. Render
  return <div>...</div>;
}
```

### Naming Conventions
- **Components**: PascalCase (`UserProfile.tsx`)
- **Hooks**: camelCase with `use` prefix (`useUserProfile.ts`)
- **API functions**: camelCase (`getUserProfile`)
- **Types/Interfaces**: PascalCase (`UserProfile`)
- **Constants**: UPPER_SNAKE_CASE (`API_BASE_URL`)


## Deployment

**Current**: Docker Hub + EC2
- Images pushed to Docker Hub registry
- EC2 instances pull and run containers
- Nginx reverse proxy on EC2

**Planned**: ECS Fargate
- Container orchestration with ECS
- Auto-scaling based on load
- Application Load Balancer

**Build for Production:**
```bash
# Build Docker images
docker build -t dcs-ai-client:latest ./client
docker build -t dcs-ai-server:latest ./server

# Push to registry
docker push dcs-ai-client:latest
docker push dcs-ai-server:latest
```

## Common Pitfalls

1. **Don't use WebSockets for chat** - Use HTTP streaming pattern
2. **Don't break FSD import rules** - Higher layers only import from lower
3. **Don't mix fetch and axios** - Frontend uses fetch (apiClient), backend uses axios for external APIs
4. **Don't forget JWT in API calls** - Use `credentials: 'include'` for fetch
5. **PostgreSQL is primary** - ALL system data in PostgreSQL. Snowflake is sub/analytics only
6. **Don't skip TypeScript types** - All entities need proper type definitions
7. **Don't create new architecture patterns** - Follow existing FSD structure
8. **Use Shared UI First** - Don't create new one while it already was
9. **Don't add /api prefix to endpoints** - apiClient base URL already includes `/server`, Controller는 `/server` 이후 경로만 사용

## Useful References

- **FSD Architecture**: [.cursor/rules/frontend_fsd_architecture.mdc](.cursor/rules/frontend_fsd_architecture.mdc)
- **Code Style Guide**: [DCS-AI_CODE_STYLE_GUIDE.md](DCS-AI_CODE_STYLE_GUIDE.md)
- **Architecture Diagrams**: [DCS-AI_Architecture_Diagrams.md](DCS-AI_Architecture_Diagrams.md)
