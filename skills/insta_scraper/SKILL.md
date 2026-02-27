---
name: insta-scraper
description: |
  Instagram 릴스 바이럴 콘텐츠를 수집하고 분석합니다.
  Apify API로 해시태그 검색, 가중치 점수 계산, AI 필터링/요약을 수행합니다.
  "인스타 릴스 분석", "바이럴 콘텐츠 찾아", "instagram scraper" 등의 요청 시 사용하세요.
---

# Instagram Reels Scraper - 바이럴 콘텐츠 수집 및 AI 분석

Instagram 해시태그 기반 릴스 수집 및 분석 도구입니다.
**조회수/좋아요/댓글 가중치 점수**로 바이럴 콘텐츠를 선정하고, **Gemini AI**로 뷰티 관련 필터링 및 콘텐츠 요약을 수행합니다.

## When to Use This Skill

다음과 같은 요청 시 이 스킬을 사용하세요:
- "인스타 릴스 바이럴 콘텐츠 찾아줘"
- "해시태그로 Instagram 릴스 검색해"
- "뷰티 릴스 TOP3 분석해줘"
- "Instagram 트렌드 분석"
- "인스타 릴스 크롤링해"

## Configuration

### Required Environment Variables

```bash
# .env 파일 설정 필수
APIFY_API_TOKEN=your_apify_token_here
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL (선택사항)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Feature Flags
ENABLE_AI_SUMMARY=True
ENABLE_DB_SAVE=False
AUTO_ANALYZE_ALL=False
```

### config.py Settings

```python
# 수집 설정
INSTAGRAM_TARGET_COUNT = 30          # 키워드당 수집할 릴스 개수
INSTAGRAM_FETCH_BUFFER = 50          # Apify API 요청 개수
INSTAGRAM_MAX_DAYS_OLD = 30          # 최대 게시일 (0 = 제한없음)
INSTAGRAM_TOP_N = 3                  # 최종 분석할 상위 N개
INSTAGRAM_CRAWL_TIMEOUT = 300        # 타임아웃 (초)

# 필터 설정
INSTAGRAM_KEYWORD_FILTER = False     # 키워드 필터 (caption에 키워드 포함 필수)
INSTAGRAM_AD_FILTER = True           # 광고 필터 (광고 게시물 제외)
INSTAGRAM_TARGET_SUBCATEGORY = ""    # 특정 서브카테고리만 (빈 문자열 = 전체)
```

### keywords_insta.json Structure

```json
{
  "categories": [
    {
      "category": "뷰티",
      "subcategories": [
        {
          "subcategory": "스킨케어",
          "keywords": ["스킨케어루틴", "피부관리", "클렌징"]
        }
      ]
    }
  ]
}
```

## Your Task

### Step 1: 환경 확인 및 설정 검증

1. **필수 파일 존재 확인**
   ```bash
   ls -la C:/claude/insta_scraper.py
   ls -la C:/claude/config.py
   ls -la C:/claude/keywords_insta.json
   ls -la C:/claude/.env
   ```

2. **.env 파일 검증**
   - APIFY_API_TOKEN이 설정되어 있는지 확인
   - GEMINI_API_KEY가 설정되어 있는지 확인 (AI 분석 시)

   **토큰 없는 경우 사용자에게 안내:**
   ```
   [ERROR] API 토큰이 설정되지 않았습니다.

   1. Apify 토큰 발급: https://console.apify.com/account/integrations
   2. Gemini API 키 발급: https://aistudio.google.com/apikey
   3. .env 파일에 추가:
      APIFY_API_TOKEN=your_token_here
      GEMINI_API_KEY=your_key_here
   ```

3. **필수 패키지 확인**
   ```bash
   pip list | grep -E "apify-client|google-generativeai|psycopg2|python-dotenv"
   ```

### Step 2: 사용자 요구사항 수집

**AskUserQuestion** 도구를 사용하여 분석 모드를 선택받습니다.

```json
{
  "questions": [{
    "question": "어떤 방식으로 Instagram 릴스를 분석할까요?",
    "header": "분석 모드",
    "multiSelect": false,
    "options": [
      {
        "label": "단일 키워드 분석 (Recommended)",
        "description": "특정 키워드 하나로 빠르게 TOP3 릴스 분석"
      },
      {
        "label": "서브카테고리 분석",
        "description": "특정 서브카테고리의 모든 키워드를 수집하고 통합 분석"
      },
      {
        "label": "전체 자동 분석",
        "description": "keywords_insta.json의 모든 서브카테고리를 순차 분석 (시간 소요)"
      }
    ]
  }]
}
```

**선택에 따라 추가 질문:**

- **단일 키워드 분석 선택 시:**
  ```json
  {
    "questions": [{
      "question": "검색할 Instagram 해시태그를 입력하세요 (예: 스킨케어루틴)",
      "header": "키워드 입력",
      "multiSelect": false,
      "options": [
        {"label": "직접 입력", "description": "원하는 해시태그를 입력합니다"}
      ]
    }]
  }
  ```

- **서브카테고리 분석 선택 시:**
  keywords_insta.json에서 서브카테고리 목록을 파싱하여 선택지 제공

### Step 3: 스크립트 실행

선택된 모드에 따라 Python 스크립트 실행:

1. **단일 키워드 분석**
   ```bash
   cd C:/claude
   python -c "
   from insta_scraper import get_viral_reels, generate_ai_summary
   import json
   from datetime import datetime

   # 사용자 입력 키워드
   keyword = '사용자_입력_키워드'

   # 릴스 수집
   reels = get_viral_reels(keyword)

   # AI 분석 (TOP 3)
   for idx, reel in enumerate(reels[:3], 1):
       summary = generate_ai_summary(reel)
       reel['ai_summary'] = summary
       print(f'\\n=== 릴스 {idx}번 ===')
       print(f'URL: {reel[\"url\"]}')
       print(f'점수: {reel[\"weighted_score\"]}')
       print(f'조회수: {reel[\"views\"]:,}')
       print(f'좋아요: {reel[\"likes\"]:,}')
       print(f'댓글: {reel[\"comments\"]:,}')
       if summary:
           print(f'AI 요약:\\n{summary}')

   # JSON 저장
   timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
   output_file = f'instagram_{keyword}_{timestamp}.json'
   with open(output_file, 'w', encoding='utf-8') as f:
       json.dump({'keyword': keyword, 'reels': reels[:3]}, f, indent=2, ensure_ascii=False)

   print(f'\\n결과 저장: {output_file}')
   "
   ```

2. **서브카테고리 분석**
   ```bash
   cd C:/claude
   # config.py에서 INSTAGRAM_TARGET_SUBCATEGORY 설정 변경
   python insta_scraper.py
   ```

3. **전체 자동 분석**
   ```bash
   cd C:/claude
   # .env 파일에서 AUTO_ANALYZE_ALL=True 설정
   python insta_scraper.py
   ```

### Step 4: 결과 분석 및 리포트 생성

스크립트 실행 완료 후 생성된 JSON 파일을 읽어서 결과를 정리합니다.

```bash
# 가장 최근 생성된 JSON 파일 찾기
ls -t C:/claude/instagram_*.json | head -1
```

**리포트 형식:**

```markdown
## Instagram 릴스 분석 완료

### 분석 정보
- **키워드/카테고리**: {keyword or subcategory}
- **수집 일시**: YYYY-MM-DD HH:MM:SS
- **총 수집 릴스**: {total_reels}개
- **AI 분석 릴스**: {top_n}개
- **필터 설정**:
  - 게시일 제한: {MAX_DAYS_OLD}일 이내
  - 광고 필터: {AD_FILTER ? '활성화' : '비활성화'}
  - 키워드 필터: {KEYWORD_FILTER ? '활성화' : '비활성화'}

### TOP 3 바이럴 릴스

#### 1위 - @{owner_username} ({weighted_score} 점)
- **URL**: {url}
- **조회수**: {views:,}
- **좋아요**: {likes:,}
- **댓글**: {comments:,}
- **게시일**: {days_ago}일 전

**AI 분석:**
{ai_summary}

---

#### 2위 - @{owner_username} ({weighted_score} 점)
...

---

#### 3위 - @{owner_username} ({weighted_score} 점)
...

---

### 채널 전략 인사이트 (AI)

{channel_strategy}

### 점수 계산 공식
- **조회수 20%** + **좋아요 40%** + **댓글 40%**
- 다양성 필터: 동일 계정 중복 제외

### 데이터 저장
- JSON 파일: `{output_file}`
- PostgreSQL: {DB 저장 여부}
```

### Step 5: 후속 작업 제안

분석 결과를 바탕으로 사용자에게 다음 액션을 제안:

```markdown
### 다음 단계 제안

1. **다른 키워드 분석**
   - 관련 키워드로 추가 분석을 진행할까요?

2. **세부 설정 변경**
   - 날짜 범위, 필터 설정을 조정하여 재분석할까요?

3. **DB 저장**
   - PostgreSQL에 결과를 저장할까요? (ENABLE_DB_SAVE=True)

4. **엑셀 리포트 생성**
   - JSON 데이터를 Excel 파일로 변환할까요?
```

## Error Handling

### API 토큰 오류
```
[ERROR] APIFY_API_TOKEN이 설정되지 않았습니다!

해결 방법:
1. .env.example 파일을 복사하여 .env 파일 생성
2. Apify 토큰 발급: https://console.apify.com/account/integrations
3. .env 파일에 토큰 추가
```

### 키워드 파일 없음
```
[ERROR] keywords_insta.json 파일을 찾을 수 없습니다!

현재 디렉토리: {현재 경로}

해결 방법:
1. keywords_insta.json 파일이 프로젝트 루트에 있는지 확인
2. JSON 형식이 올바른지 검증
```

### API 타임아웃
```
[TIMEOUT] 크롤링 타임아웃 ({CRAWL_TIMEOUT}초 초과)

해결 방법:
1. config.py에서 INSTAGRAM_CRAWL_TIMEOUT 값 증가
2. INSTAGRAM_FETCH_BUFFER 값 감소 (더 적게 요청)
3. 네트워크 연결 상태 확인
```

### Gemini API 오류
```
[WARNING] Gemini API 초기화 실패: {error}

AI 요약 없이 진행합니다.

해결 방법:
1. GEMINI_API_KEY 확인
2. google-generativeai 패키지 설치: pip install google-generativeai
3. API 키 발급: https://aistudio.google.com/apikey
```

### DB 연결 오류
```
[ERROR] 데이터베이스 연결 실패: {error}

해결 방법:
1. PostgreSQL 서버가 실행 중인지 확인
2. .env 파일의 DB 정보 확인 (POSTGRES_HOST, POSTGRES_PASSWORD)
3. psycopg2 패키지 설치: pip install psycopg2-binary
4. DB 저장 비활성화: ENABLE_DB_SAVE=False
```

### 수집 결과 없음
```
[WARNING] 결과 없음 (타임아웃 또는 데이터 부족)

가능한 원인:
1. 해시태그가 존재하지 않거나 게시물이 없음
2. 필터 조건이 너무 엄격함 (날짜, 키워드, 광고 필터)
3. Apify API 할당량 초과

해결 방법:
1. 다른 키워드로 시도
2. MAX_DAYS_OLD 값 증가 또는 0으로 설정 (제한 없음)
3. KEYWORD_FILTER, AD_FILTER를 False로 설정
```

## Important Notes

### 1. API 사용량 및 비용

- **Apify API**:
  - Actor 실행마다 크레딧 소모
  - 무료 티어: 월 $5 크레딧
  - instagram-hashtag-scraper: 약 $0.01-0.05/실행

- **Google Gemini API**:
  - 무료 티어: 분당 15회 요청
  - 1,500회/일 제한
  - API 호출 간 2초 딜레이 적용 (rate limit 방지)

### 2. 수집 제한 및 최적화

- **Apify Actor 제한**:
  - maxItems: 최대 수집 개수 (FETCH_BUFFER)
  - timeout: 크롤링 타임아웃 (CRAWL_TIMEOUT)
  - 키워드당 평균 2-5분 소요

- **최적화 팁**:
  - FETCH_BUFFER를 30-50으로 설정 (너무 크면 타임아웃)
  - 전체 자동 분석은 시간이 많이 소모됨 (서브카테고리당 5-10분)
  - 여러 키워드 분석 시 API 호출 간 2초 대기

### 3. 필터링 알고리즘

- **날짜 필터**: MAX_DAYS_OLD일 이내 게시물만 수집
- **키워드 필터**: caption에 검색 키워드가 포함된 게시물만
- **광고 필터**: caption에 "광고" 또는 "AD" 키워드 제외
- **뷰티 필터**: Gemini AI로 뷰티 관련 콘텐츠만 선별
- **다양성 필터**: 동일 계정의 중복 릴스 제외

### 4. 점수 계산 공식

```
weighted_score = (views × 0.2) + (likes × 0.4) + (comments × 0.4)
```

- 조회수(views)보다 참여도(likes, comments)에 더 높은 가중치
- 조회수가 0이어도 좋아요/댓글만으로 평가 가능
- -1 값은 0으로 변환 (Instagram API의 비공개 표시)

### 5. AI 분석 구조

1. **개별 릴스 분석** (TOP N개):
   - 핵심 내용 요약
   - 타겟 오디언스 분석
   - 인기 요인 분석
   - 콘텐츠 스타일 분류
   - 톤앤무드 카테고리화

2. **채널 전략 인사이트** (TOP 3 종합):
   - 공통 성공 패턴 도출
   - 알고리즘 전략 제시
   - "이 카테고리는 [X] 전략을 쓸 때 터진다" 정의

### 6. 데이터 저장

- **JSON 파일**:
  - 파일명: `instagram_{category}_{subcategory}_{timestamp}.json`
  - 인코딩: UTF-8
  - 포함 내용: metadata, top_reels, all_reels, channel_strategy

- **PostgreSQL DB** (선택사항):
  - 테이블: `fnco_influencer.mst_plan_issue_top_content`
  - 주간 데이터: 월요일-일요일 기준
  - ON CONFLICT: post_id 기준 업데이트

### 7. 윤리적 사용

- **Instagram 이용약관 준수**:
  - 공개 게시물만 수집
  - 개인정보 보호
  - 과도한 크롤링 금지

- **저작권 주의**:
  - 수집된 콘텐츠는 분석 목적으로만 사용
  - 무단 재배포 금지
  - 출처 명시 필수

### 8. 성능 고려사항

- **메모리 사용**:
  - 대량 데이터 수집 시 메모리 사용량 증가
  - 전체 자동 분석 시 충분한 RAM 필요 (최소 4GB)

- **네트워크 대역폭**:
  - 썸네일 이미지 다운로드 없음 (URL만 저장)
  - API 응답만 처리하여 트래픽 최소화

### 9. 확장 가능성

현재 스크립트를 기반으로 추가 가능한 기능:
- TikTok, YouTube Shorts 크롤링 확장
- 경쟁사 채널 벤치마킹 자동화
- 트렌드 추이 시계열 분석
- Slack/Discord 알림 연동
- Dashboard 시각화 (Streamlit, Dash)
