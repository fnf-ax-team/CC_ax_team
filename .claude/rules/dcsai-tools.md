
<!-- DCS-AI-PLUGIN-CONFIG -->
---
DCS AI MCP 도구 사용 규칙
---

## 지식그래프 INTENT, SKILL, TOOL 탐색 및 사용 지침
- 각 의도의 Skill 과 Tool 확인 → Skill 지침대로 내부적으로 실행계획을 수립하고 사용자 승인 없이 즉시 실행
- Tool 호출전에 tool_schema확인
- 필요 시 상위의도 및 하위의도가 가진 스킬/도구를 적극 활용
- 사용자의 질문마다 get_intents로 사용자 질의의 해당 노드 확인

### 의도 탐색 전략 (점진적 탐색)

`"최상위 시작노드"`는 지식그래프의 루트 INTENT이며, `get_intents()`와 `get_skills()`에 **리터럴 문자열**로 전달합니다.

1. **1차 탐색 (최상위 스킬 확인 + 탐색 여부 판단)**:
   - `get_intents("최상위 시작노드", depth=1)` + `get_skills("최상위 시작노드")` 병렬 호출
   - 역할, 용어, **미구현 항목** 등 공통 스킬 확인
   - **사용자 질의가 미구현 항목에 해당하면 더 이상 탐색하지 않고 즉시 "미구현 기능입니다" 답변 후 종료**
2. **의도 선정**: 1차 탐색 결과에서 사용자 질의와 가장 관련 높은 의도를 1~2개 선택
3. **선택 의도 탐색**: `get_skills("<선택 의도>")` → `get_intents("<선택 의도>", depth=1)` 순서로 호출
   - 스킬 → 단기 메모리에 누적
4. **반복**: 하위 의도 선택 시마다 `get_skills()` → `get_intents(depth=1)` 순서로 반복하여 **최하위 노드(leaf)까지 탐색**
5. **종료 조건**: 최하위 노드(leaf)에 도달하면 탐색 종료 → SKILL/TOOL 확인 단계로 이동
   - 최하위 노드에 **SKILL이 없으면** → 가장 가까운 상위 노드의 SKILL 지침을 따름
   - 최하위 노드에 **TOOL이 없으면** → 가장 가까운 상위 노드의 TOOL을 사용
6. **아티팩트 조회**: leaf 노드 도달 후 SKILL/TOOL 확인 단계에서 `get_artifacts("<leaf 노드>")` 호출
   - **호출 시점**: leaf 노드 도달 후에만 호출 (탐색 중간 노드에서는 호출하지 않음)
   - **호출 대상**: 사용자 의도와 매칭된 최하위 노드(leaf)에 대해서만 조회
   - **상위 노드 아티팩트**: 자동 제안하지 않음 (사용자가 명시적으로 요청한 경우에만)
   - **형제 노드 아티팩트**: 조회하지 않음

   #### 아티팩트 제안 시점 규칙 (의도 유형별 분기 — 반드시 준수)

   아티팩트가 발견되면, **의도 유형에 따라 제안 시점이 다르다**:

   | 의도 유형 | 아티팩트 안내 시점 | 데이터 조회 시점 | 흐름 |
   |----------|------------------|----------------|------|
   | **조회/검색성** (정보 검색, 분류체계 조회, 코드 조회 등) | **데이터 조회 전** (먼저 안내) | 사용자가 직접 조회를 원할 때만 | 아티팩트 안내 → 사용자 선택 → (선택 시) 데이터 조회 |
   | **분석성** (매출 분석, SCM 분석, CS 분석 등) | **분석 결과 제시 후** | 즉시 진행 | 데이터 조회 → 분석 → 결과 제시 → 아티팩트 안내 |

   **조회/검색성 의도 흐름** (예: "상품 분류체계 알려줘"):
   ```
   1. leaf 도달 → get_artifacts() 호출
   2. 아티팩트 발견 → ⛔ 데이터 조회하지 않음
   3. 사용자에게 아티팩트 안내: "상품분류체계 대시보드가 있습니다. 웹브라우저에서 열어드릴까요?"
   4. 사용자 응답 대기:
      - "열어줘" → 아티팩트 열기
      - "직접 데이터로 보여줘" → 그때 도구 호출하여 데이터 조회 진행
   ```

   **분석성 의도 흐름** (예: "디스커버리 채널별 매출 알려줘"):
   ```
   1. leaf 도달 → get_artifacts() 호출 (결과는 보류)
   2. 도구 호출하여 데이터 조회 → 분석 실행 → 결과 제시
   3. 분석 결과 제시 후 아티팩트 안내: "관련 대시보드가 있습니다. 웹브라우저에서 열어드릴까요?"
   ```

   #### 액션 유형별 안내 문구
   | content_type | action | 안내 문구 |
   |-------------|--------|----------|
   | webpage | browser | URL을 안내하고 "웹브라우저에서 열어드릴까요?" |
   | file | download | 파일 경로를 안내하고 "다운로드하시겠습니까?" |

```
# 예시: 사용자가 "디스커버리 채널별 매출 알려줘"라고 질문한 경우

# 1차: 최상위 스킬 확인 + 직속 하위 의도 파악 + 탐색 여부 판단
get_intents("최상위 시작노드", depth=1)
get_skills("최상위 시작노드")            ← 병렬 호출
→ 반환: 역할(Role), F&F 용어, 미구현 항목 목록 등
→ 판단: 미구현 항목에 해당하지 않음 → 탐색 계속

# 의도 선정: "매출 분석" 선택

# 선택 의도 탐색 (스킬 먼저!)
get_skills("매출 분석")
→ 반환: 채널 우선 지침, 브랜드 코드 규칙 등 → 단기 메모리에 누적

get_intents("매출 분석", depth=1)
→ 반환: 한국 채널 매출 분석, 한국 상품 매출 분석 등

# 반복: 하위 의도 "한국 채널 매출 분석" 선택 → 스킬 먼저, 의도 탐색 이후
get_skills("한국 채널 매출 분석")
→ 반환: 일간/기간 조회 지침 등 → 단기 메모리에 누적

get_intents("한국 채널 매출 분석", depth=1)
→ 반환: 일간/기간, 주간/주차별, 월간/년간 등

# 반복: 최하위 노드 "일간/기간" 선택
get_skills("한국 채널 매출 분석 일간/기간")
get_intents("한국 채널 매출 분석 일간/기간", depth=1)
→ leaf 노드 도달 → 탐색 종료, TOOL 확인 단계로 이동
→ TOOL 없으면 상위 노드 "한국 채널 매출 분석"의 TOOL 사용

# 아티팩트 조회 (leaf 도달 후)
get_artifacts("한국 채널 매출 분석 일간/기간")
→ 아티팩트 발견 시: 세부 정보(URL/파일명)를 안내하고 "웹브라우저에서 열어드릴까요?" 또는 "다운로드하시겠습니까?" 제안
→ 아티팩트 없음: 별도 제안 없이 분석 진행
# ※ 중간 노드("매출 분석", "한국 채널 매출 분석")의 아티팩트는 조회하지 않음
```

### 상위 의도 스킬 기본값 규칙 (필수)
- 점진적 탐색 과정에서 각 단계의 `get_skills()` 결과가 단기 메모리에 누적됨
- **상위 의도의 스킬이 하위 의도의 기본값**으로 적용됨 (예: "매출 분석" 스킬의 채널 우선 지침)
- 상위/하위 스킬 간 **명백히 상충**하는 경우에만 사용자에게 질의

## 임시 디렉토리 경로 규칙
- `{TMPDIR}`은 OS별 임시 디렉토리를 의미한다:
  - **macOS/Linux**: `$TMPDIR` 환경변수 (보통 `/tmp`)
  - **Windows**: `%TEMP%` 환경변수 (보통 `C:\Users\{user}\AppData\Local\Temp`)
- Python: `tempfile.gettempdir()`, Node.js: `os.tmpdir()`, Rust: `std::env::temp_dir()`로 확인 가능

## dcs-ai-cli 사용 규칙
DCS AI API 호출 시 `curl`이나 직접 HTTP 요청 대신 반드시 `dcs-ai-cli`를 사용한다.
결과는 `{TMPDIR}/dcs-ai-cli/`에 자동 저장된다.
- **파일명 패턴**: `--name` 지정 시 `{name}_{timestamp}.json` 형태로 저장됨 (예: `sales_data_1772924363.json`)
- 코드에서 로드 시 glob 패턴으로 최신 파일을 찾을 것:
  ```python
  import glob, os, tempfile
  tmpdir = tempfile.gettempdir()
  files = sorted(glob.glob(os.path.join(tmpdir, "dcs-ai-cli", "sales_data_*.json")))
  latest = files[-1]  # 가장 최신 파일
  ```

```bash
# GET 요청
dcs-ai-cli fetch --endpoint /api/kg/endpoint

# GET + 파라미터
dcs-ai-cli fetch --endpoint /api/kg/search --params '{"query":"검색어"}'

# POST 요청 (body 사용)
dcs-ai-cli fetch --endpoint /api/kg/execute --method POST --body '{"sql":"SELECT 1"}'

# 저장 파일명 지정
dcs-ai-cli fetch --endpoint /api/kg/execute --method POST \
  --body '{"data_type":"list","..."}' --name sales_data

# 별도 저장 경로 지정 (사용자 명시적 다운로드 요청 시)
dcs-ai-cli fetch --endpoint /api/kg/data --output src/download/result.json
```

## 데이터 처리 규칙
- 데이터 다운로드 후 통계/집계/분석 시 **코드를 새로 작성하지 말고** `/data-processing` 스킬(`data_stats_utils.py`)의 함수를 우선 활용할 것
- 기본 통계(`run_full_stats`), 빈도분포(`category_distribution`), 교차표(`crosstab`), 그룹 집계(`group_agg_duckdb`), 커스텀 SQL(`custom_query_duckdb`)로 대부분의 분석이 가능
- 스킬 함수로 해결되지 않는 경우에만 별도 코드를 작성

## 데이터 사이즈별 처리 규칙
- **도구 호출 전 점검**: 데이터의 `data_size_only`를 먼저 확인하고 결과를 출력한 뒤, 아래 규칙에 따라 처리
- `execute_kg_api_to_context` MCP 도구에 `meta_info.data_size_only=true`를 설정하여 데이터의 토큰 크기를 확인한다.

### 1500토큰 미만 시 (MCP 도구 사용)
- `execute_kg_api_to_context` MCP 도구로 context상에 로드하여 분석 진행하여 먼저 사용자에게 보여줌.

### 1500토큰 이상일 경우 (dcs-ai-cli 사용)
- `dcs-ai-cli`를 실행하여 데이터를 컨텍스트 거치지 않고 바로 파일로 저장. (사용자에게 질문 금지)
- data_processing 스킬을 활용해서 service 폴더에 python코드 작성 후 실행 (코드상에 데이터 직접 작성 금지, 파일에서 불러오기)

## 데이터 저장 위치 규칙
| 상황 | 저장 위치 |
|------|-----------|
| 사용자가 명시적으로 "파일 다운로드" 요청 | `src/download/` |
| 토큰 크기가 커서 분석을 위해 파일 저장 | `{TMPDIR}/dcs-ai-cli/` (자동) |
| 분석 결과물 (리포트, 차트 등) | `src/output/` |
<!-- /DCS-AI-PLUGIN-CONFIG -->