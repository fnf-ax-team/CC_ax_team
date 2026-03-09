# 🚀 AX팀 Claude Code 스킬 공유 레포지토리

> **AX팀 전용** Claude Code 커스텀 스킬 모음집입니다. 팀원들이 자유롭게 스킬을 추가/수정하고 공유할 수 있습니다.
> 가지고 있는 스킬들이 특정 업무를 위해 집약적인 케이스가 많을테니, 공유 -> 리뷰 -> 디벨롭하여 재공유 하는 형식으로 업데이트하면 좋을 거 같습니다.
> 아예 생으로 신규 스킬 제작시 공식 claude skill 문서 참고해서 one shot prompting으로 제작 지시하면 좋습니다: https://code.claude.com/docs/ko/skills

---

## ⭐ 핵심 기능: 스킬 푸시 (skill-push)

> **스킬 수정 후 GitHub 업데이트가 필요할 때, 아래 명령 하나로 끝!**

```
"스킬 업데이트해줘" 또는 "스킬 푸시해줘"
```

### skill-push 스킬이란?

| 기능 | 설명 |
|------|------|
| 📝 **자동 커밋** | 변경된 스킬 파일들을 자동으로 커밋 |
| 📤 **GitHub 푸시** | 한 번에 원격 저장소에 푸시 |
| 📋 **README 자동 업데이트** | 스킬 목록과 사용법을 자동으로 갱신 |

### 사용 방법

1. 스킬 파일(.md)을 수정하거나 새로 만듭니다
2. Claude Code에서 **"스킬 푸시해줘"** 라고 요청합니다
3. 자동으로 커밋 & 푸시 완료!

```
✅ 스킬 GitHub 푸시 완료!

📝 커밋 메시지: Update kpop-sns skill
📁 변경된 파일: skills/kpop-sns/SKILL.md
🔗 저장소: https://github.com/fnf-ax-team/CC_ax_team
```

---

## 스킬 목록

| 카테고리 | 스킬명 | 설명 |
|----------|--------|------|
| **관리** | **skill-push** | 스킬 변경사항 GitHub 푸시 & README 자동 업데이트 (macOS/Windows) |
| **동기화** | **skill-sync** | 팀 Private 저장소에서 스킬 동기화 (로컬/팀 분리 관리) |
| **SNS 분석** | **insta_scraper** | Instagram 릴스 바이럴 콘텐츠 수집 & AI 분석 |
| **K-pop** | kpop-sns | K-pop 그룹 공식 SNS 계정 검색 & 엑셀 저장 |
| **문서** | llm-api-docs | LLM API 공식 문서 수집 (Playwright MCP) |
| **세션 관리** | session-summary | 종합 세션 요약 문서 생성 |
| **보고서** | ceo-ppt | 회장님 보고용 PPT 자동 생성 (F&F 디자인) |
| **이미지 생성** | **fnf-image-gen** | AI 이미지 생성 통합 (브랜드컷, 셀피, 일상컷, 시딩UGC, 배경교체) |
| **시딩 콘텐츠** | **seeding-ugc** | 인플루언서 시딩용 UGC 이미지 생성 (TikTok/릴스/쇼츠) |
| **코어 모듈** | **core** | 이미지 생성 파이프라인 코어 (인플루언서, 브랜드컷, 셀피, 착장교체, 포즈, 배경교체) |
| **데이터베이스** | **db** | 프리셋 DB (배경/카메라/표정/포즈/스타일링 JSON) |
| **DCS Claude** | **dcs-ai-claude** | DCS AI 프로젝트 Claude 설정, 에이전트, 커맨드, 규칙, 스킬 |
| **DV 에이전트** | **dv-ai-super-agent** | DV AI 슈퍼에이전트 커맨드 (API, 캐시, 빌드, 커밋, 배포 등) |
| **대시보드 쿼리** | **influencer-dashboard-make-query** | 인플루언서 대시보드 Make 쿼리 (SQL 에이전트, 스키마 탐색) |
| **Make 공유** | **make-shared-resources** | Make 공유 리소스 (DDL, 도메인 지식, 연락처 관리) |
| **테스트** | **tests** | 인플루언서/착장 테스트 스크립트 (배치 실행, VLM 분석 등) |

---

## 📥 설치 방법

### 1. 레포지토리 클론

```bash
# Windows
cd C:\Users\{사용자명}\.claude
git clone https://github.com/fnf-ax-team/CC_ax_team.git skills

# Mac/Linux
cd ~/.claude
git clone https://github.com/fnf-ax-team/CC_ax_team.git skills
```

### 2. 기존 스킬 폴더가 있는 경우

```bash
# 기존 폴더 백업
mv skills skills_backup

# 새로 클론
git clone https://github.com/fnf-ax-team/CC_ax_team.git skills

# 필요한 기존 스킬 복사
cp -r skills_backup/* skills/
```

### 3. Claude Code 재시작

VSCode에서 `Ctrl+Shift+P` → "Developer: Reload Window"

---

## 📝 스킬 사용법

### 🔧 skill-push
스킬 변경사항을 GitHub에 푸시하고 README를 자동 업데이트합니다.

**사용 예시:**
- "스킬 업데이트해줘"
- "스킬 푸시해줘"
- "스킬 깃허브에 올려줘"

---

### skill-sync
팀 Private 저장소(CC_ax_team)에서 최신 스킬을 가져와 `team/` 폴더에 동기화합니다.

**핵심 기능:**
- 로컬 스킬과 팀 스킬 **분리 관리** (충돌 방지)
- Git Credential Manager로 **자동 인증**
- 동일 스킬명 공존 가능 (로컬 우선, `team:` 접두사로 팀 버전 호출)

**사용 예시:**
- "팀 스킬 동기화해줘"
- "skill sync"
- "팀 저장소 최신 스킬 받아줘"

**스킬 호출 방법 (동기화 후):**
```
/ceo-ppt          → 로컬 버전 (커스텀)
/team:ceo-ppt     → 팀 버전 (표준)
```

---

### insta_scraper
Instagram 릴스 바이럴 콘텐츠를 수집하고 AI로 분석합니다.

**사용 예시:**
- "인스타 릴스 바이럴 콘텐츠 찾아줘"
- "해시태그로 Instagram 릴스 검색해"
- "뷰티 릴스 TOP3 분석해줘"

**주요 기능:**
- Apify API로 해시태그 검색
- 가중치 점수 계산 (조회수 20% + 좋아요 40% + 댓글 40%)
- Gemini AI로 뷰티 관련 필터링/요약

**필수 환경변수:**
- `APIFY_API_TOKEN`
- `GEMINI_API_KEY`

---

### kpop-sns
K-pop 아티스트/그룹의 공식 SNS 계정을 검색하고 엑셀에 저장합니다.

**사용 예시:**
- "BTS 공식 계정 알려줘"
- "aespa 인스타 주소 찾아줘"
- "NewJeans SNS 계정 정리해줘"

---

### 📚 llm-api-docs
LLM API 공식 문서를 Playwright MCP로 수집합니다.

**사용 예시:**
- "Gemini API 문서 가져와줘"
- "Claude 최신 모델 정보 알려줘"
- "Grok API 가격 정리해줘"

**필수 요구사항:** Playwright MCP 설치 필요 (스킬 실행 시 자동 안내)

---

### 📋 session-summary
전체 대화 세션을 분석하여 상세한 마크다운 문서를 생성합니다.

**사용 예시:**
- "/session-summary"
- "세션 요약해줘"
- "대화 정리해줘"

---

### 📊 ceo-ppt
회장님 보고용 PPT를 자동 생성합니다. F&F 디자인 가이드 적용.

**사용 예시:**
- "보고자료 만들어줘"
- "마케팅 AX 보고 PPT 만들어줘"
- "PPT 만들어줘"

**생성 구조:**
- 표지 → 아젠다 구분 슬라이드 → 본문 (아젠다당 1-2장) → EOD

**디자인 스펙:**
- 슬라이드: 16:9 와이드스크린
- 배경색: `#F2F2F2`
- 폰트: Pretendard (ExtraBold, SemiBold)
- F&F 로고 자동 삽입

---

### seeding-ugc (시딩UGC)
인플루언서 시딩용 UGC 콘텐츠 이미지를 생성합니다. TikTok/릴스/쇼츠용 9:16 세로 포맷.

**핵심 원칙:** 진짜처럼 보여야 한다. 프로페셔널하게 보이면 실패.

**사용 예시:**
- "Banillaco 두통+햇빛 선케어 시딩 3장"
- "유분 고민 → 사용 후 비교 4장"
- "아침 루틴 스킨케어 과정 5장"

**주요 기능:**
- 5단계 레이어 프롬프트 구조 (기본설정 → 피사체 → Visual Action → 환경 → 조명)
- Visual Action 최우선 원칙 (동작/자세를 프롬프트 중심에 배치)
- UGC 리얼리즘 검증 + Anti-Polish 체크
- Before/After 페어 자동 생성
- 시나리오 자동 매칭 (pain_point, before_after, daily_routine, healthy_skin)
- GRWM 촬영 규칙 강화 (카메라 프레임 노출 방지)

**필수 환경변수:** `GEMINI_API_KEY`

---

### fnf-image-gen (AI 이미지 생성)
Gemini 3 Pro Image API를 활용한 5종 콘텐츠 생성 통합 스킬.

**5종 카테고리:**

| 카테고리 | 설명 | 종횡비 |
|----------|------|--------|
| 브랜드컷(화보) | 공식 화보/룩북 | 3:4 |
| 셀피 | 인스타 셀카 | 9:16 |
| 일상컷 | 타인 촬영/타이머 일상 사진 | 4:5 |
| 시딩UGC | 틱톡/릴스 시딩 콘텐츠 | 9:16 |
| 배경교체 | 기존 사진 배경 변경 | 원본유지 |

**[NEW] 브랜드컷 v2 Shot Card 시스템:**
- VLM 분석 기반 포즈/표정/앵글 카탈로그 (`pose_library.json`)
- 구조화 Key-Value 프롬프트 (의상 누락 방지, 포즈 다양성 향상)
- 14-slot 참조 이미지 전략적 배치

**사용 예시:**
- "바닐라코 화보 생성해줘" (브랜드컷)
- "인스타 셀카 스타일로" (셀피)
- "남친샷 스타일로 생성해줘" (일상컷)
- "시딩용 UGC 만들어줘" (시딩UGC)
- "이 사진 배경을 런던 거리로" (배경교체)

**지원 브랜드:** Banillaco, Discovery, Duvetica, MLB(마케팅/그래픽), Sergio Tacchini

**필수 환경변수:** `GEMINI_API_KEY` (복수 키 쉼표 구분 가능)

> 규칙/문서 구조는 위 [📌 CLAUDE.md](#-claudemd-이미지-생성-절대-규칙) 섹션 참조. 폴더 상세는 하단 [📂 폴더 구조](#-폴더-구조) 참조.

---

## 🔧 스킬 수정/추가 방법

### 1. 새 스킬 추가

```bash
# 새 스킬 폴더 생성
mkdir skills/새스킬명

# SKILL.md 파일 생성 (아래 템플릿 참고)
```

### 2. SKILL.md 템플릿

```markdown
---
name: 스킬-이름
description: 스킬에 대한 간단한 설명. 트리거 문구 예시를 포함하세요.
---

# 스킬 제목

스킬에 대한 상세 설명

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "트리거 문구 1"
- "트리거 문구 2"

## Your Task

1. 첫 번째 할 일
2. 두 번째 할 일
3. ...

## Output Format

출력 형식 설명

## Edge Cases

예외 상황 처리 방법
```

### 3. GitHub에 반영

```
"스킬 푸시해줘"
```

---

## 👥 팀 기여 가이드

1. **스킬 추가 시**: 팀원들에게 유용한 스킬인지 고려
2. **스킬 수정 시**: 기존 기능 호환성 유지
3. **커밋 메시지**: 명확하게 변경 내용 기술
4. **테스트**: 스킬 추가/수정 후 직접 테스트 필수

---

## 📂 폴더 구조

```
CC_ax_team/
├── .claude/                           # Claude Code 프로젝트 설정
├── Agent/                             # 에이전트 설정
├── README.md
├── requirements.txt
└── skills/                            # 모든 스킬 & 모듈 통합
    ├── README.md
    │
    │── ── 🎯 Claude Code 스킬 ──
    ├── ceo-ppt/                       # 📊 회장님 보고용 PPT
    ├── fnf-image-gen/                 # 🎨 AI 이미지 생성 통합
    │   ├── CLAUDE.md                  #   절대 규칙
    │   ├── SKILL.md                   #   워크플로 가이드
    │   ├── brand-dna/                 #   브랜드별 DNA JSON (6개)
    │   ├── directors/                 #   디렉터 페르소나 (7명)
    │   ├── templates/                 #   콘텐츠 타입별 프롬프트 템플릿
    │   └── workflows/                 #   워크플로 상세 파이프라인
    ├── insta_scraper/                 # 📱 Instagram 릴스 수집 & 분석
    ├── kpop-sns/                      # 🎤 K-pop 공식 SNS 검색
    ├── llm-api-docs/                  # 📚 LLM API 문서 수집
    ├── seeding-ugc/                   # 📱 시딩UGC 콘텐츠 생성
    ├── session-summary/               # 📋 세션 요약 문서 생성
    ├── skill-push/                    # 🔧 스킬 GitHub 푸시
    ├── skill-sync/                    # 🔄 팀 스킬 동기화
    │
    │── ── 🏗️ 코어 & 인프라 ──
    ├── core/                          # 🧠 이미지 생성 파이프라인 코어
    │   ├── ai_influencer/             #   인플루언서 이미지 생성
    │   ├── background_swap/           #   배경 교체
    │   ├── brandcut/                  #   브랜드컷 (v2 Shot Card)
    │   ├── ecommerce/                 #   이커머스 이미지
    │   ├── face_swap/                 #   얼굴 교체
    │   ├── multi_face_swap/           #   다중 얼굴 교체
    │   ├── outfit_swap/               #   착장 교체
    │   ├── pose_change/               #   포즈 변경
    │   ├── pose_copy/                 #   포즈 복사
    │   ├── seeding_ugc/               #   시딩 UGC
    │   ├── selfie/                    #   셀피 생성
    │   ├── shoe_rack_mockup/          #   슈랙 목업
    │   ├── validators/                #   품질 검증기
    │   ├── api.py                     #   API 키 관리
    │   ├── config.py                  #   공유 설정
    │   └── utils.py                   #   공통 유틸리티
    ├── db/                            # 💾 프리셋 데이터베이스
    │   ├── background_presets.json
    │   ├── camera_presets.json
    │   ├── expression_presets.json
    │   ├── pose_presets.json
    │   └── styling_preset_db.json
    │
    │── ── 🤖 팀별 Claude 설정 ──
    ├── dcs-ai-claude/                 # DCS AI 프로젝트 설정
    │   ├── agents/                    #   에이전트 (architect, reviewer 등 10종)
    │   ├── commands/                  #   커맨드 (build-fix, code-review 등 10종)
    │   ├── rules/                     #   규칙 (코딩스타일, 보안, 테스트 등)
    │   └── skills/                    #   DCS 전용 스킬
    ├── dv-ai-super-agent/             # DV AI 슈퍼에이전트
    │   └── commands/                  #   커맨드 (api, cache, dev, fix 등 14종)
    ├── influencer-dashboard-make-query/ # 인플루언서 대시보드 Make 쿼리
    │   └── claude/                    #   에이전트 + 커맨드 (SQL, 스키마 등)
    ├── make-shared-resources/         # Make 공유 리소스
    │   ├── agents/                    #   shared-search, shared-update
    │   ├── output-example-shared-resources/  # DDL, 도메인 지식 예시
    │   └── skills/                    #   shared-add 스킬
    │
    │── ── 🧪 테스트 ──
    └── tests/                         # 테스트 스크립트
        ├── influencer/                #   인플루언서 생성 테스트 (7개)
        └── 착장/                      #   착장 교체 병렬 테스트
```

---

## ⚠️ 주의사항

- 스킬 파일 경로에 **한글 폴더명**이 있으면 문제가 발생할 수 있음
- Playwright MCP가 필요한 스킬은 사전 설치 필요
- 엑셀 파일 수정 스킬은 **파일이 닫혀있어야** 정상 작동
- 이미지 생성 스킬 사용 시 **Gemini API Key** 필수 (.env에 GEMINI_API_KEY 설정)
- 이미지 생성 모델은 반드시 **gemini-3-pro-image-preview** 사용 (다른 모델 사용 금지)

---

**Made with ❤️ by AX Team**

_Last Updated: 2026-03-09 (core/db/dcs-ai-claude/dv-ai-super-agent/influencer-dashboard/make-shared/tests를 skills/로 통합, README 스킬 목록 및 폴더 구조 업데이트)_
