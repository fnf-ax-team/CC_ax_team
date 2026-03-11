# FNF AI Studio MCP 서버 배포 가이드

F&F AI Studio의 이미지 생성 워크플로를 MCP 서버로 배포하여, 다른 팀원들이 Claude Desktop / ORBIT에서 사용할 수 있도록 하는 가이드입니다.

---

## 목차

1. [개요](#1-개요)
2. [사전 준비](#2-사전-준비)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [로컬 테스트](#4-로컬-테스트)
5. [GitHub 푸시](#5-github-푸시)
6. [ORBIT 마켓플레이스 등록](#6-orbit-마켓플레이스-등록)
7. [사용자 가이드](#7-사용자-가이드-구독자용)
8. [관리 및 재배포](#8-관리-및-재배포)
9. [문제 해결](#9-문제-해결)

---

## 1. 개요

### 제공 도구 (MCP Tools)

| Tool | 설명 | 필수 입력 |
|------|------|----------|
| `generate_brandcut` | 브랜드컷(에디토리얼 화보) 생성 | 얼굴 이미지, 착장 이미지, 프롬프트 |
| `swap_background` | 배경 교체 (인물 보존) | 원본 이미지, 배경 스타일 |
| `swap_outfit` | 착장 교체 (얼굴/포즈 유지) | 원본 이미지, 착장 이미지 |
| `generate_influencer` | AI 인플루언서 이미지 생성 | 캐릭터 이름 |
| `list_options` | 비율/해상도/비용 조회 | (없음) |
| `list_presets` | 프리셋/캐릭터 목록 조회 | (없음) |

### 비용

| 해상도 | 장당 비용 |
|--------|----------|
| 1K (1024px) | 190원 |
| 2K (2048px) | 190원 |
| 4K (4096px) | 380원 |

---

## 2. 사전 준비

### 필수 요구사항

- **Python 3.11+** (권장: 3.13)
- **uv** 패키지 매니저 설치
- **GEMINI_API_KEY** (Gemini API 키, 쉼표 구분으로 복수 키 지원)
- **GitHub 접근 권한** (`fnf-process` Organization)

### uv 설치 (아직 없는 경우)

```bash
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```bash
# .env
GEMINI_API_KEY=key1,key2,key3
```

> 여러 키를 쉼표로 구분하면 자동 로테이션됩니다 (rate limit 대응).

---

## 3. 프로젝트 구조

```
New-fnf-studio/
├── pyproject.toml           # MCP 서버 패키지 설정
├── fnf_studio_mcp/          # MCP 서버 코드
│   ├── __init__.py
│   ├── server.py            # FastMCP 서버 + 6개 도구
│   └── helpers.py           # 이미지 I/O, stdout 보호
├── core/                    # 기존 이미지 생성 모듈 (수정 없음)
│   ├── brandcut/
│   ├── background_swap/
│   ├── outfit_swap/
│   ├── ai_influencer/
│   ├── api.py
│   ├── config.py
│   └── options.py
└── docs/
    └── MCP_DEPLOYMENT_GUIDE.md  # 이 문서
```

### 핵심 파일 설명

| 파일 | 역할 |
|------|------|
| `pyproject.toml` | uvx 호환 패키지 정의. `fnf-studio-mcp` 명령어 등록 |
| `fnf_studio_mcp/server.py` | MCP 서버 메인. 6개 도구를 FastMCP로 등록 |
| `fnf_studio_mcp/helpers.py` | stdout 보호 (stdio 프로토콜 보호) + 이미지 로드/저장 |

---

## 4. 로컬 테스트

### 4-1. 의존성 설치

```bash
cd D:\FNF_Studio_TEST\New-fnf-studio
uv sync
```

### 4-2. 서버 직접 실행

```bash
uv run fnf-studio-mcp
```

> stdio 모드로 시작됩니다. JSON-RPC 메시지를 stdin으로 보내 테스트할 수 있습니다.

### 4-3. MCP Inspector로 테스트 (권장)

```bash
mcp dev fnf_studio_mcp/server.py
```

> 브라우저에서 MCP Inspector가 열리며, 각 도구를 GUI로 테스트할 수 있습니다.

### 4-4. Claude Desktop에서 테스트

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "fnf-studio": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\FNF_Studio_TEST\\New-fnf-studio",
        "run",
        "fnf-studio-mcp"
      ],
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

---

## 5. GitHub 푸시

### 5-1. Repository 확인

- **Repository**: `https://github.com/fnf-process/fnf-studio`
- **Organization**: `fnf-process`

### 5-2. 원격 저장소 연결

```bash
cd D:\FNF_Studio_TEST\New-fnf-studio

# remote 추가
git remote add origin https://github.com/fnf-process/fnf-studio.git

# 또는 기존 remote 변경
git remote set-url origin https://github.com/fnf-process/fnf-studio.git
```

### 5-3. 보안 체크리스트

커밋 전 반드시 확인:

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지
- [ ] API 키가 코드에 하드코딩되지 않았는지
- [ ] `.env.example`만 커밋되는지
- [ ] `db/` 폴더가 `.gitignore`에 포함되어 있는지 (12GB+, 별도 배포)
- [ ] `Fnf_studio_outputs/`가 `.gitignore`에 포함되어 있는지

### 5-4. 커밋 및 푸시

```bash
git add pyproject.toml fnf_studio_mcp/ docs/MCP_DEPLOYMENT_GUIDE.md
git commit -m "feat: MCP 서버 추가 (브랜드컷/배경교체/착장교체/인플루언서)"
git push -u origin main
```

---

## 6. ORBIT 마켓플레이스 등록

### 6-1. 등록 화면 접속

ORBIT 마켓플레이스 메인 → **서버 등록** 버튼 클릭

### 6-2. Step 1 - 기본 정보

| 항목 | 입력값 |
|------|--------|
| **서버 이름** | FNF AI Studio |
| **설명** | F&F 브랜드 AI 이미지 생성 (브랜드컷/인플루언서/배경교체/착장교체) |
| **카테고리** | 이미지 생성 |
| **공개 범위** | Private (승인 필요) |

**요약 설명 (Markdown):**

```markdown
## FNF AI Studio MCP Server

F&F 패션 브랜드 AI 이미지 생성 도구입니다.

### 제공 도구
| Tool | 설명 |
|------|------|
| generate_brandcut | 브랜드 에디토리얼 화보 생성 |
| swap_background | 배경 교체 (인물 보존) |
| swap_outfit | 착장 교체 (얼굴/포즈 유지) |
| generate_influencer | AI 인플루언서 이미지 생성 |
| list_options | 비율/해상도/비용 조회 |
| list_presets | 프리셋/캐릭터 목록 조회 |

### 필요 환경변수
- GEMINI_API_KEY: Gemini API 키 (쉼표 구분 복수 키 지원)

### 비용
- 1K/2K: 190원/장, 4K: 380원/장
```

### 6-3. Step 2 - 실행 설정 (Configuration)

**stdio JSON 설정 (로컬 프로젝트 방식):**

> `db/` 폴더(프리셋, 캐릭터 이미지 등 12GB+)가 필요하므로, 프로젝트 폴더를 직접 참조하는 `--directory` 방식을 사용합니다.

```json
{
  "mcpServers": {
    "fnf-studio": {
      "command": "uv",
      "args": [
        "--directory",
        "{프로젝트_경로}",
        "run",
        "fnf-studio-mcp"
      ],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

> `{프로젝트_경로}`를 실제 로컬 경로로 변경하세요. 예: `D:\\FNF_Studio_TEST\\New-fnf-studio`

**환경변수 등록:**

| 변수명 | 타입 | 설명 |
|--------|------|------|
| `GEMINI_API_KEY` | Secret (암호화) | Gemini API 키 |

### 6-4. Step 3 - 검토 및 등록

- 입력 정보 최종 확인
- **서비스 등록하기** 클릭
- 관리자 승인 대기 (검수중 → 승인)

> 승인 완료 후 다른 사용자가 구독 요청을 보낼 수 있습니다.

---

## 7. 사용자 가이드 (구독자용)

### 초기 설정 (필수)

1. **GitHub에서 코드 clone:**

```bash
git clone https://github.com/fnf-process/fnf-studio.git
cd fnf-studio
```

2. **db/ 데이터 복사:**

`db/` 폴더(프리셋, 캐릭터 이미지 등)는 GitHub에 포함되지 않습니다.
공유 드라이브에서 `db/` 폴더를 다운로드하여 프로젝트 루트에 배치하세요.

```
fnf-studio/
├── core/          ← GitHub에서 clone
├── fnf_studio_mcp/ ← GitHub에서 clone
├── db/            ← 공유 드라이브에서 복사
└── ...
```

3. **환경변수 설정:**

```bash
# .env 파일 생성
cp .env.example .env
# GEMINI_API_KEY 입력
```

4. **의존성 설치:**

```bash
uv sync
```

### 사용 예시

Claude Desktop 또는 ORBIT에서:

```
"MLB 여름 컬렉션 브랜드컷을 생성해줘.
얼굴: C:\images\face.jpg
착장: C:\images\outfit_top.jpg, C:\images\outfit_bottom.jpg
비율: 3:4, 해상도: 2K"
```

AI가 자동으로 `generate_brandcut` 도구를 호출합니다.

### 결과 확인

생성 결과는 `Fnf_studio_outputs/` 폴더에 저장됩니다:

```
Fnf_studio_outputs/brand_cut/20260311_143052_mcp/
├── images/
│   ├── input_face_01.jpg
│   ├── input_outfit_01.jpg
│   └── output_001.jpg
├── prompt.json
├── config.json
└── validation.json
```

---

## 8. 관리 및 재배포

### 코드 업데이트 후 재배포

1. 코드 수정 후 GitHub에 푸시
2. ORBIT 마켓플레이스 → 서비스 설정 → **서비스 재배포** 클릭

```bash
git add -A
git commit -m "fix: 브랜드컷 검증 기준 업데이트"
git push origin main
```

### 구독자 관리

- ORBIT → **구독자 관리** 메뉴에서 구독 요청 승인/반려

### 로그 확인

- ORBIT → **Logs** 메뉴에서 MCP 호출 로그 확인

---

## 9. 문제 해결

### uvx 실행 오류

```bash
# 캐시 삭제 후 재시도
uv cache clean
uvx --from git+https://github.com/fnf-process/fnf-studio.git fnf-studio-mcp
```

### GEMINI_API_KEY 오류

- `.env` 파일에 키가 설정되어 있는지 확인
- ORBIT의 경우 환경변수가 Secret으로 등록되어 있는지 확인

### core 모듈 import 오류

```bash
# pyproject.toml에 core가 packages에 포함되어 있는지 확인
[tool.hatch.build.targets.wheel]
packages = ["fnf_studio_mcp", "core"]
```

### stdout 오염 (MCP 프로토콜 오류)

core/ 모듈에 새로운 `print()` 호출이 추가된 경우, `protect_stdout()` 컨텍스트 매니저 내에서 호출되고 있는지 확인.

### 생성 시간 초과

이미지 생성은 1장당 10~30초, 재시도 포함 최대 90초 소요될 수 있습니다. MCP 클라이언트의 타임아웃 설정을 확인하세요.

---

## 부록: pyproject.toml 전체

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "fnf-studio-mcp"
version = "0.1.0"
description = "FNF AI Studio MCP Server - AI image generation for fashion brands"
readme = "docs/MCP_DEPLOYMENT_GUIDE.md"
requires-python = ">=3.11"
authors = [
    { name = "F&F AX Team" },
]
dependencies = [
    "mcp[cli]>=1.0.0",
    "google-genai>=1.50.0",
    "Pillow>=10.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "numpy>=1.24.0",
]

[project.scripts]
fnf-studio-mcp = "fnf_studio_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["fnf_studio_mcp", "core"]
```
