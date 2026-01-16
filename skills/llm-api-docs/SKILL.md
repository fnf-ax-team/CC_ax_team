---
name: llm-api-docs
description: LLM API 공식 문서를 Playwright MCP로 수집합니다. "Gemini API 문서", "Claude 가격", "Grok 모델 정보", "OpenAI API 최신 문서" 등의 요청 시 사용하세요. 동적 웹페이지도 정확하게 스크래핑합니다.
---

# LLM API 문서 수집 스킬 (Playwright MCP)

LLM API의 공식 문서를 Playwright MCP를 사용하여 정확하게 수집하고 마크다운으로 정리합니다.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "Gemini API 문서 가져와줘"
- "Claude 최신 모델 정보 알려줘"
- "Grok API 가격 정리해줘"
- "OpenAI GPT 모델 목록 가져와"
- "LLM API 문서 수집해줘"
- "{LLM이름} API 최신 정보"

## Prerequisites Check (CRITICAL)

스킬 실행 전 **반드시** Playwright MCP 설치 여부를 확인하세요:

### Step 1: MCP 도구 확인

```
mcp__playwright__browser_snapshot 도구가 사용 가능한지 확인
```

### Step 2: 설치되지 않은 경우

1. **프로젝트 루트에 `.mcp.json` 파일 생성**:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

2. **사용자에게 안내**:

```
Playwright MCP가 설치되어 있지 않습니다.

설치 방법:
1. 위의 .mcp.json 파일이 프로젝트 루트에 생성되었습니다.
2. Claude Code를 재시작해주세요 (Ctrl+Shift+P → "Developer: Reload Window")
3. 재시작 후 다시 요청해주세요.
```

3. **브라우저 미설치 오류 시**:

```bash
npx playwright install chromium
```

## Your Task

### 1. LLM 이름 파싱

사용자 입력에서 LLM 이름 추출:
- **Gemini** / Google AI
- **Claude** / Anthropic
- **Grok** / xAI
- **GPT** / OpenAI
- **Llama** / Meta

### 2. 공식 문서 URL 매핑

| LLM | 문서 URL | 수집 대상 |
|-----|----------|-----------|
| **Gemini** | https://ai.google.dev/gemini-api/docs/models | 모델, 가격, 기능 |
| **Claude** | https://docs.anthropic.com/en/docs/about-claude/models/all-models | 모델, 가격, 기능 |
| **Grok** | https://docs.x.ai/docs/models | 모델, 가격, 기능, Rate Limits |
| **OpenAI** | https://platform.openai.com/docs/models | 모델, 가격, 기능 |

### 3. Playwright MCP로 페이지 수집

각 페이지에 대해:

```
1. browser_navigate → URL 이동
2. browser_wait_for → 페이지 로드 대기 (2-3초)
3. browser_snapshot → DOM 스냅샷 캡처
4. 필요시 browser_click → 탭/섹션 확장
5. browser_close → 브라우저 닫기
```

### 4. LLM별 스크래핑 전략

#### Grok (docs.x.ai)
- 동적 테이블 렌더링 대기 필수
- "Loading models..." 텍스트가 사라질 때까지 대기
- Rate Limits, Pricing 섹션 별도 확인

#### Gemini (ai.google.dev)
- 모델 테이블이 여러 섹션으로 분리됨
- Pricing 페이지 별도: https://ai.google.dev/gemini-api/docs/pricing

#### Claude (docs.anthropic.com)
- 모델 정보와 가격이 다른 페이지
- Pricing: https://www.anthropic.com/pricing

#### OpenAI (platform.openai.com)
- 로그인 없이 접근 가능한 공개 문서만 수집
- Models 페이지에서 주요 정보 확인

## Output Format

### 마크다운 구조

```markdown
# {LLM} API 최신 문서 정보

## 개요
{LLM 간단 설명}

---

## 사용 가능한 모델

| 모델 | Model ID | 컨텍스트 | Max Output | 특징 |
|------|----------|----------|------------|------|
| ... | ... | ... | ... | ... |

---

## 가격 정책 (100만 토큰당, USD)

| 모델 | Input | Output | 비고 |
|------|-------|--------|------|
| ... | ... | ... | ... |

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| ... | ... |

---

## SDK 사용 예시

```python
# 코드 예시
```

---

## 공식 리소스

- **API 문서**: {URL}
- **가격 정보**: {URL}
- **릴리스 노트**: {URL}

---

_문서 수집일: YYYY-MM-DD | 출처: 공식 문서_
```

## Error Handling

### 페이지 로드 실패
- 3초 대기 후 재시도
- 재시도 실패 시 WebSearch로 대체 정보 수집
- 사용자에게 부분 결과 + 오류 알림

### 동적 콘텐츠 미로드
- browser_wait_for로 특정 텍스트 대기
- 최대 10초 대기
- 타임아웃 시 현재 상태로 진행

### 접근 차단 (403/Rate Limit)
- WebSearch로 캐시된 정보 검색
- 대체 소스 (llm-stats.com, openrouter.ai) 활용
- 결과에 "일부 정보는 대체 소스에서 수집됨" 표시

## File Output

### 저장 위치
`{프로젝트 루트}/{llm_name}_api_docs_{YYYYMMDD}.md`

### 예시
- `gemini_api_docs_20260108.md`
- `claude_api_docs_20260108.md`
- `grok_api_docs_20260108.md`

## After Completion

1. 수집된 정보를 마크다운 테이블로 표시
2. 파일 저장 완료 메시지
3. 수집 성공률 표시 (예: "4개 섹션 중 4개 수집 완료")
4. 공식 문서 링크 제공
5. 브라우저 닫기 확인

## Example Workflow

사용자: "Grok API 문서 가져와줘"

1. [체크] Playwright MCP 설치 확인 ✓
2. [이동] https://docs.x.ai/docs/models
3. [대기] 페이지 로드 완료 (2초)
4. [캡처] browser_snapshot으로 DOM 추출
5. [파싱] 모델 테이블, 가격, Rate Limits 추출
6. [저장] grok_api_docs_20260108.md 생성
7. [출력] 마크다운 테이블로 결과 표시
8. [종료] 브라우저 닫기

완료: "Grok API 문서를 수집했습니다. 10개 모델 정보가 grok_api_docs_20260108.md에 저장되었습니다."

## Notes

- WebFetch는 동적 페이지에서 실패할 수 있음 → Playwright MCP 우선 사용
- 가격 정보는 자주 변경되므로 수집일자 표시 필수
- 공식 문서 URL이 변경될 수 있으므로 실패 시 WebSearch로 최신 URL 확인
