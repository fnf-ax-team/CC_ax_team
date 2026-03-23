---
name: notion-workspace-creator
description: >
  Notion 프로젝트 워크스페이스를 Notion API로 실제 생성하는 스킬.
  사용자가 /notion 이라고 입력하거나, "노션 워크스페이스 만들어줘", "노션 프로젝트 페이지 생성해줘",
  "프로젝트 노션 페이지 만들어줘" 등을 요청할 때 반드시 이 스킬을 사용한다.
  .env 설정 안내 → 프로젝트 정보 수집 → Notion API 호출 순서로 실행된다.
---

# Notion Workspace Creator

사용자가 입력한 프로젝트 정보를 바탕으로 Notion API를 통해 실제 워크스페이스 페이지와 DB를 생성한다.

---

## 기술 참고사항

- Windows 환경에서는 curl 대신 **Python urllib**을 사용하여 API를 호출한다 (이모지 인코딩 문제 방지).
- `.env` 파일은 반드시 **LF 줄바꿈**으로 저장한다 (`sed -i 's/\r$//' .env`).
- DB를 heading 바로 아래에 배치하려면 heading append → `POST /v1/databases` 순서로 **교차 배치**한다 (각각 페이지 하단에 추가되므로 순서 보장).
- Python 실행은 프로젝트의 `.venv/Scripts/python.exe` 또는 시스템 Python을 사용한다.

---

## 실행 순서 (반드시 아래 순서대로)

### STEP 1 — .env 확인 및 설정 안내

먼저 현재 디렉토리에 `.env` 파일이 존재하는지 확인한다.

```bash
test -f .env && echo "EXISTS" || echo "NOT_FOUND"
```

**.env가 없는 경우** → 사용자에게 아래 안내를 출력하고 입력을 요청한다:

```
Notion API 연동을 위해 아래 두 가지 정보가 필요합니다.

1. NOTION_API_KEY
   → https://www.notion.so/my-integrations 에서 새 integration 생성
   → "Internal Integration Token" 복사

2. NOTION_PARENT_PAGE_ID
   → 워크스페이스가 생성될 상위 Notion 페이지를 열고
   → URL에서 페이지 ID 복사: notion.so/[workspace]/[페이지제목]-{PAGE_ID}
   → ⚠️ URL에 ?v= 파라미터가 없는 일반 페이지여야 함 (데이터베이스 URL 불가)
   → 해당 페이지에서 우측 상단 ··· > Connections > 생성한 integration 연결 필수

위 두 값을 입력해주세요.
```

입력받은 후 `.env` 파일을 생성하고 줄바꿈을 정리한다:

```bash
cat > .env << EOF
NOTION_API_KEY=사용자입력값
NOTION_PARENT_PAGE_ID=사용자입력값
EOF
sed -i 's/\r$//' .env
echo ".env" >> .gitignore 2>/dev/null || true
```

**.env가 이미 있는 경우** → `sed -i 's/\r$//' .env` 실행 후 값을 로드하고 STEP 2로 진행한다.

---

### STEP 2 — 프로젝트 정보 수집

사용자에게 아래 항목을 한 번에 질문한다:

```
워크스페이스 생성을 위한 정보를 입력해주세요.

1. 페이지 제목 (프로젝트명을 입력해주세요.)

2. 프로젝트 주제
   예: "팀 내 분산된 지식과 업무 정보를 하나의 구조화된 시스템으로 통합하여,
       빠른 정보 접근과 효율적인 협업 환경을 구축한다."

3. PM 이름

4. 팀원 목록   예: Tim(프론트개발), Ryan(백엔드개발)
```

입력받은 값을 변수로 저장한다:
- `PROJECT_TITLE` — 페이지 제목
- `PROJECT_DESC` — 주제 (이를 바탕으로 ①②③ 목표를 Claude가 자동 생성)
- `PM_NAME` — PM 이름
- `MEMBERS` — 팀원 목록

**Claude의 목표 자동 생성 규칙**: `PROJECT_DESC`를 분석해 아래 형식으로 3가지 목표를 작성한다.
- ①현황 문제 또는 출발점을 정의하는 목표
- ②핵심 구축/개발 목표
- ③확장 또는 지속성 목표

---

### STEP 3 — Notion API로 페이지 및 DB 생성

Python 스크립트를 작성하여 실행한다. 각 호출은 이전 결과 ID를 사용하므로 **순서를 반드시 지킨다.**

#### 3-1. 메인 페이지 생성

`POST /v1/pages` 로 메인 페이지를 생성한다.

```python
data = {
    "parent": {"page_id": PARENT_PAGE_ID},
    "icon": {"type": "emoji", "emoji": "[주제_기반_이모지]"},
    "properties": {
        "title": {"title": [{"text": {"content": PROJECT_TITLE}}]}
    }
}
```

응답에서 `id` 필드 → `MAIN_PAGE_ID` 저장

**이모지 선택 기준** (Claude가 주제를 분석해 자동 선택):
- 데이터/지식관리 → 🗂️ (`\U0001F5C2`)
- 앱/서비스 개발 → 💻 (`\U0001F4BB`)
- 마케팅/브랜드 → 📣 (`\U0001F4E3`)
- 운영/프로세스/자동화 → 🤖 (`\U0001F916`)
- 분석/리서치 → 🔍 (`\U0001F50D`)
- 기타 → 📋 (`\U0001F4CB`)

---

#### 3-2. 페이지 본문 블록 추가

`PATCH /v1/blocks/{MAIN_PAGE_ID}/children` 로 아래 블록들을 순서대로 추가한다.

**전체 페이지 레이아웃:**

```
column_list (2컬럼)
├── 좌측 컬럼 (좁게)
│   ├── quote "목차" (bold)
│   │   └── table_of_contents
│   ├── paragraph (빈 줄 - 간격용)
│   ├── quote "담당자" (bold)
│   │   ├── paragraph "👤PM : [PM_NAME]"
│   │   └── paragraph "👥팀원 : [MEMBERS]"
│   └── paragraph (빈 줄 - 간격용)
│
└── 우측 컬럼 (넓게 — 프로젝트 개요만)
    ├── heading_2 "■ 프로젝트 개요"
    └── callout (gray_background, 📌)
        └── [PROJECT_DESC] 기반 본문 + ①②③ 목표

(페이지 레벨 — heading과 DB를 교차 배치)
├── heading_2 "■ 주요 개발 항목"
├── DB1: 주요 개발 항목
├── heading_2 "■ WBS"
├── DB2: WBS
├── heading_2 "■ OUTPUT"
├── DB3: OUTPUT
├── heading_2 "■ References"
├── DB4: References
├── heading_2 "■ 회의/보고자료"
└── DB5: 회의/보고자료
```

**구현 순서:**

**Batch 1** — 메인 column_list (프로젝트 개요만 우측 컬럼에 포함):

```
column_list
├── 좌측: quote(목차+TOC), 빈줄, quote(담당자+PM/팀원), 빈줄
└── 우측: heading_2(프로젝트 개요), callout(설명+목표)
```

**Batch 2** — heading과 DB를 페이지 레벨에 교차 생성:

각 섹션마다 heading append → `POST /v1/databases` 순서로 호출한다.
Notion API는 새 블록을 항상 페이지 하단에 추가하므로,
heading → DB 순서로 교차 호출하면 heading 바로 아래에 DB가 배치된다.

```
1. PATCH blocks/children → heading "■ 주요 개발 항목"
   POST databases → DB1 (주요 개발 항목)
2. PATCH blocks/children → heading "■ WBS"
   POST databases → DB2 (WBS)
3. PATCH blocks/children → heading "■ OUTPUT"
   POST databases → DB3 (OUTPUT)
4. PATCH blocks/children → heading "■ References"
   POST databases → DB4 (References)
5. PATCH blocks/children → heading "■ 회의/보고자료"
   POST databases → DB5 (회의/보고자료)
```

> ⚠️ Notion API는 column 폭(width) 비율 지정을 지원하지 않는다.
> 생성 후 Notion 앱에서 좌측 컬럼을 드래그하여 좁게 조정해야 한다.

---

#### 3-3. DB 속성 및 예시 데이터 생성

`POST /v1/databases` 로 생성 시 속성을 함께 지정한다. 이후 `POST /v1/pages` 로 예시 항목을 추가한다.

---

**DB 1 — 주요 개발 항목** (`POST /v1/databases` — heading 추가 직후 호출)

```json
{
  "properties": {
    "제목":    { "title": {} },
    "담당자":  { "people": {} },
    "유형":    { "select": { "options": [
      { "name": "기획", "color": "blue" },
      { "name": "개발", "color": "orange" },
      { "name": "공통", "color": "green" }
    ]}},
    "상태":    { "select": { "options": [
      { "name": "완료",     "color": "green" },
      { "name": "진행 중", "color": "blue" },
      { "name": "시작 전", "color": "gray" },
      { "name": "취소·홀드","color": "red" }
    ]}},
    "진행률":  { "number": { "format": "percent" } },
    "시작일":  { "date": {} },
    "마감일":  { "date": {} }
  }
}
```

예시 항목 2개 (`POST /v1/pages`):
1. "요구사항 정의 및 범위 확정" — 기획, 완료, 100%
2. "운영 환경 배포 및 모니터링" — 개발, 진행 중, 70%

---

**DB 2 — WBS** (`POST /v1/databases` — heading 추가 직후 호출)

```json
{
  "properties": {
    "작업명":  { "title": {} },
    "유형":    { "select": { "options": [기획/개발/공통] } },
    "상태":    { "select": { "options": [완료/진행 중/시작 전/취소·홀드] } },
    "진행률":  { "number": { "format": "percent" } },
    "시작일":  { "date": {} },
    "마감일":  { "date": {} },
    "담당자":  { "people": {} }
  }
}
```

예시 항목 4개 (⚠️ **시작일은 생성 당일 날짜(오늘)로 지정**):
1. "[①기획 및 분석] 현황 분석 및 요구사항 수집" — 기획, 완료, 100%, 시작일=오늘
2. "[①기획 및 분석] 화면 기획 및 프로토타입 검토" — 기획, 완료, 90%, 시작일=오늘
3. "[②개발 및 배포] 핵심 기능 개발" — 개발, 진행 중, 80%, 시작일=오늘
4. "[②개발 및 배포] 통합 테스트 및 성능 검증" — 공통, 진행 중, 40%, 시작일=오늘

```python
from datetime import date
today = date.today().isoformat()  # "YYYY-MM-DD"
# 각 WBS 항목의 시작일 속성에 적용:
"시작일": {"date": {"start": today}}
```

---

**DB 3 — OUTPUT** (`POST /v1/databases` — heading 추가 직후 호출)

```json
{
  "properties": {
    "제목":   { "title": {} },
    "담당자": { "people": {} },
    "역할":   { "select": { "options": [
      { "name": "프로세스/전략", "color": "blue" },
      { "name": "프로세스/DATA","color": "purple" }
    ]}},
    "상태":   { "select": { "options": [
      { "name": "예정",     "color": "gray" },
      { "name": "진행중",   "color": "blue" },
      { "name": "완료",     "color": "green" },
      { "name": "홀딩/취소","color": "red" }
    ]}}
  }
}
```

예시 항목 4개 (각 상태 1개):
- "Sprint Planning" — 예정
- "기능 명세서 작성" — 진행중
- "요구사항 정의서" — 완료
- "레거시 마이그레이션" — 홀딩/취소

---

**DB 4 — References** (`POST /v1/databases`)

```json
{
  "properties": {
    "제목": { "title": {} },
    "URL":  { "url": {} },
    "태그": { "multi_select": { "options": [
      { "name": "문서",     "color": "blue" },
      { "name": "GitHub",  "color": "gray" },
      { "name": "Template","color": "yellow" }
    ]}}
  }
}
```

예시 항목 3개:
1. "사용자 매뉴얼" — Template
2. "GitHub Repository" — GitHub
3. "시스템 아키텍처 문서" — 문서

---

**DB 5 — 회의/보고자료** (`POST /v1/databases`)

```json
{
  "properties": {
    "미팅명":  { "title": {} },
    "참석자":  { "people": {} },
    "구분":    { "select": { "options": [
      { "name": "정기", "color": "green" },
      { "name": "스팟", "color": "gray" }
    ]}},
    "Date":   { "date": {} }
  }
}
```

예시 항목 2개:
1. "유관부서 협의" — 스팟
2. "정기 스탠드업" — 정기

---

### STEP 4 — 완료 안내 출력

```
Notion 워크스페이스 생성 완료!

페이지 링크: https://notion.so/[MAIN_PAGE_ID 하이픈 제거]

생성된 구성:
  ├ 메인 페이지: [PROJECT_TITLE]
  ├ DB: 주요 개발 항목
  ├ DB: WBS
  ├ DB: OUTPUT
  ├ DB: References
  └ DB: 회의/보고자료

⚠️ 수동 설정 필요 (Notion API 미지원):
  1. 전체 너비: 페이지 우측 상단 ··· > Full width 활성화
  2. 컬럼 폭 조정: 좌측 컬럼(목차/담당자)을 드래그하여 좁게 조정
  3. DB 제목 숨김: 각 DB의 ··· > Hide database title
  4. 뷰 변경:
     • 주요 개발 항목 → Gallery 뷰
     • WBS → Timeline 뷰 (시작일/마감일 기준)
     • OUTPUT → Board 뷰 (상태 기준 그룹핑)
```

---

## 에러 처리

| 상황 | 메시지 |
|------|--------|
| 401 Unauthorized | "NOTION_API_KEY가 올바르지 않습니다. `.env`를 삭제 후 다시 실행해주세요." |
| 404 Not Found | "NOTION_PARENT_PAGE_ID를 확인해주세요. integration이 해당 페이지에 연결되어 있어야 합니다. URL에서 ?v= 파라미터 없는 페이지 ID를 사용해야 합니다." |
| 개별 DB 생성 실패 | 실패한 DB명과 오류 코드를 출력하고 나머지 단계는 계속 진행 |

---

## 주의사항

- `.env`는 생성 즉시 `.gitignore`에 추가 (API Key 노출 방지)
- `.env` 파일은 LF 줄바꿈으로 저장 (`sed -i 's/\r$//' .env`)
- Notion API 버전: `2022-06-28` 고정
- 모든 DB는 `"is_inline": true` 로 생성
- DB는 heading 추가 → `POST /v1/databases` 교차 호출로 heading 바로 아래에 배치 (`child_database` 블록은 API 미지원)
- 상태 색상 고정: 완료=green, 진행 중=blue, 시작 전·홀드=gray, 취소=red
- WBS 예시 항목의 시작일은 생성 당일 날짜로 자동 설정
- Gallery / Board / Timeline 뷰, DB 제목 숨김, 컬럼 폭 조정은 API 생성 후 Notion 앱에서 수동 설정 필요
