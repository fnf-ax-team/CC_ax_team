---
description: DCS-AI 프로젝트 온보딩 가이드. 새로운 팀원이 프로젝트 구조를 이해하고, 에이전트와 함께 개발하는 방법을 안내합니다.
---

# DCS-AI 프로젝트 가이드

DCS-AI에 오신 것을 환영합니다! 이 가이드는 프로젝트를 빠르게 이해하고 효율적으로 개발할 수 있도록 도와줍니다.

---

## 🏗️ 프로젝트 개요

**DCS-AI**는 AI 기반 챗봇과 MCP(Model Context Protocol) 도구 통합을 제공하는 엔터프라이즈 플랫폼입니다.

### 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | Next.js 15, React 19, TypeScript, Redux Toolkit, SWR, TailwindCSS |
| **Backend** | NestJS, TypeScript, LangChain, AI SDK |
| **Database** | PostgreSQL (Primary), Snowflake (Analytics) |
| **Auth** | NextAuth + Microsoft Azure AD SSO |
| **Infra** | Docker Hub + EC2, Turborepo 모노레포 |

### 핵심 기능

- 💬 AI 챗봇 (HTTP 스트리밍 응답)
- 🔧 MCP 도구 통합 (동적 도구 실행)
- 🔐 Microsoft SSO 인증
- 📊 Snowflake 분석 쿼리

---

## 📁 프로젝트 구조

```
DCS-AI/
├── client/                 # Next.js 15 Frontend (Port 3000)
│   └── src/
│       ├── app/           # App Router + providers
│       ├── pages/         # 페이지 컴포넌트
│       ├── widgets/       # 복합 UI (Sidebar, Header)
│       ├── features/      # 사용자 인터랙션 (hooks + UI)
│       ├── entities/      # 비즈니스 엔티티 (chat, user, mcp)
│       └── shared/        # 공유 유틸, UI 키트, API 클라이언트
│
├── server/                 # NestJS Backend (Port 3001)
│   └── src/
│       ├── auth/          # NextAuth 인증
│       ├── chat/          # 채팅 모듈
│       ├── mcp/           # MCP 도구 통합
│       └── database/      # TypeORM 엔티티, Snowflake
│
└── .claude/               # Claude Code 설정
    ├── agents/            # 전문 에이전트들
    ├── commands/          # 슬래시 명령어
    ├── rules/             # 코딩 규칙
    └── skills/            # 개발 패턴 가이드
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pnpm install

# 환경 변수 설정
cp client/.env.example client/.env.local
cp server/.env.example server/.env

# 개발 서버 실행 (Turborepo)
pnpm dev
```

### 2. 접속 확인

- Frontend: http://localhost:3000
- Backend: http://localhost:3001

### 3. 인증 설정

Microsoft Azure AD 인증이 필요합니다. `.env.local`에 다음을 설정하세요:

```bash
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
```

---

## 🤖 에이전트와 함께 개발하기

DCS-AI는 전문 에이전트들이 개발을 도와줍니다.

### 사용 가능한 에이전트

| 에이전트 | 용도 | 언제 사용? |
|----------|------|-----------|
| **planner** | 기능 구현 계획 | 새 기능 시작 전 |
| **architect** | 아키텍처 설계 | 구조적 결정이 필요할 때 |
| **tdd-guide** | 테스트 주도 개발 | 코드 작성 시 |
| **code-reviewer** | 코드 리뷰 | 코드 완성 후 |
| **security-reviewer** | 보안 검토 | 인증/API 코드 작성 시 |
| **build-error-resolver** | 빌드 에러 해결 | 컴파일 에러 발생 시 |
| **e2e-runner** | E2E 테스트 | 사용자 플로우 테스트 시 |
| **refactor-cleaner** | 코드 정리 | 죽은 코드 제거 시 |
| **doc-updater** | 문서 갱신 | 문서 업데이트 필요 시 |

### 추천 워크플로우

```
1. /plan     → 기능 계획 수립
2. /tdd      → 테스트 먼저 작성
3. 구현       → 코드 작성
4. /build-fix → 빌드 에러 해결
5. /code-review → 코드 리뷰
6. /e2e      → E2E 테스트 실행
```

---

## 📋 자주 사용하는 명령어

### 슬래시 명령어

| 명령어 | 설명 |
|--------|------|
| `/guide` | 이 온보딩 가이드 표시 |
| `/plan` | 기능 구현 계획 수립 |
| `/tdd` | TDD 워크플로우 시작 |
| `/code-review` | 코드 리뷰 실행 |
| `/build-fix` | 빌드 에러 해결 |
| `/e2e` | E2E 테스트 실행 |
| `/refactor-clean` | 죽은 코드 정리 |

### 터미널 명령어

```bash
# 개발
pnpm dev              # 전체 개발 서버
pnpm dev:client       # 프론트엔드만
pnpm dev:server       # 백엔드만

# 테스트
cd client && pnpm test          # Playwright E2E
cd server && pnpm test          # Jest 유닛 테스트

# 빌드
pnpm build            # 전체 빌드
pnpm lint             # 린트 검사
```

---

## 🏛️ 핵심 아키텍처 패턴

### 1. FSD (Feature-Sliced Design) - Frontend

```
Import 규칙: app → pages → widgets → features → entities → shared
            (상위 레이어는 하위 레이어만 import 가능)
```

```typescript
// ✅ 올바른 import
import { Button } from '@/shared/ui/button';
import { ChatMessage } from '@/entities/chat';

// ❌ 잘못된 import (entities에서 features import 불가)
import { useChatInput } from '@/features/chat';
```

### 2. HTTP 스트리밍 (NOT WebSocket)

```typescript
// Backend: 청크 전송
res.setHeader('Content-Type', 'text/event-stream');
res.setHeader('Transfer-Encoding', 'chunked');

for await (const chunk of aiStream) {
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}
```

### 3. 데이터베이스 전략

| DB | 용도 |
|----|------|
| **PostgreSQL** | 모든 시스템 데이터 (채팅, 사용자, MCP) |
| **Snowflake** | 분석 쿼리만 (읽기 전용) |

### 4. 인증 플로우

```
User → Microsoft SSO → NextAuth Session → JWT Cookie → NestJS Guard
```

---

## 💡 개발 팁

### 1. 새 기능 추가 시

```bash
# 1. 계획 수립
/plan 사용자가 채팅 내보내기를 할 수 있는 기능

# 2. TDD로 개발
/tdd 채팅 내보내기 API 엔드포인트

# 3. 코드 리뷰
/code-review
```

### 2. 에러 발생 시

```bash
# TypeScript 에러
/build-fix

# 보안 관련 이슈
security-reviewer 에이전트 사용
```

### 3. 공유 UI 먼저 확인

```typescript
// 새 컴포넌트 만들기 전에 shared/ui 확인
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Card } from '@/shared/ui/card';
```

---

## 📚 참고 자료

### 프로젝트 문서

| 문서 | 위치 |
|------|------|
| 프로젝트 규칙 | `.claude/CLAUDE.md` |
| DCS-AI 가이드라인 | `.claude/skills/dcs-ai-guidelines.md` |
| 백엔드 패턴 | `.claude/skills/backend-patterns.md` |
| 프론트엔드 패턴 | `.claude/skills/frontend-patterns.md` |
| 보안 규칙 | `.claude/rules/security.md` |
| 코딩 스타일 | `.claude/rules/coding-style.md` |

### MCP 서버 (`.mcp.json`)

| 서버 | 용도 |
|------|------|
| context7 | 라이브러리 문서 조회 |
| serena | 코드 분석 |
| github | GitHub 작업 |
| memory | 세션 간 메모리 |

---

## ❌ 하지 말아야 할 것들

1. **WebSocket으로 채팅 구현** → HTTP 스트리밍 사용
2. **FSD 레이어 규칙 위반** → 상위→하위만 import
3. **Snowflake에 시스템 데이터 저장** → PostgreSQL 사용
4. **하드코딩된 시크릿** → 환경 변수 사용
5. **fetch/axios 혼용** → Frontend는 `apiClient`, Backend는 `axios`
6. **console.log 남기기** → 커밋 전 제거

---

## 🆘 도움이 필요할 때

### 질문하기

```bash
# 아키텍처 질문
architect 에이전트에게 물어보세요

# 테스트 방법
tdd-guide 에이전트에게 물어보세요

# 보안 검토
security-reviewer 에이전트에게 물어보세요
```

### 코드 탐색

```bash
# 특정 기능 찾기
"채팅 메시지 저장하는 코드 찾아줘"

# 아키텍처 이해
"MCP 도구가 어떻게 실행되는지 설명해줘"

# 패턴 확인
"이 프로젝트에서 API 호출은 어떻게 하나요?"
```

---

## 🎯 다음 단계

1. **환경 설정 완료** - `pnpm dev`로 개발 서버 실행
2. **프로젝트 탐색** - 주요 폴더 구조 파악
3. **첫 번째 기능** - `/plan`으로 시작해서 `/tdd`로 개발
4. **코드 리뷰** - `/code-review`로 품질 확인

---

**Happy Coding! 🚀**

질문이 있으면 언제든 물어보세요. 에이전트들이 도와드립니다.
