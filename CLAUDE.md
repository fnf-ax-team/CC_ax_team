# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 자동 노트 규칙

사용자가 **"노트 <"** 로 시작하는 메시지를 보내면, 즉시 `/oh-my-claudecode:note` 스킬을 호출하여 notepad.md에 기록한다. 별도 확인 없이 바로 저장.

**기록 방식**: 사용자가 `<` 뒤에 짧게 써도, Claude가 현재 대화 맥락을 분석하여 아래 항목을 자동으로 채워서 상세하게 기록한다:

```
## [날짜] 세션 노트

### 작업 목표
- 이번 세션에서 하려던 것

### 완료된 작업
- 구체적으로 뭘 했는지 (파일명, 함수명 포함)

### 미완료 / 다음 할 일
- 어디서 멈췄는지, 다음에 뭘 해야 하는지

### 핵심 결정사항
- 기술 선택, 아키텍처 결정 등 (있으면)

### 참고 파일
- 관련 파일 경로 목록
```

- 예: `노트 < 피그마 작업 중간 저장` → Claude가 대화 내용 기반으로 위 양식을 채워서 저장
- 새 세션 시작 시 `notepad.md`를 확인하면 이전 작업 맥락 복원 가능

## Project Overview

FNF Studio is an AI-powered image generation platform for fashion brand photography. It uses the Gemini API to generate and edit images with background replacement, brand-specific styling, and quality validation workflows.

## Key Commands

### Run the Streamlit Web App
```bash
streamlit run app_background_studio.py
```

### Run the FastAPI Backend
```bash
uvicorn api.main:app --reload
# or
python api/main.py
```

### Run Tests
```bash
# API tests
pytest api/tests/ -v

# Run specific test
pytest api/tests/test_tasks.py -v
```

### Run Image Generation Pipeline
```bash
# Full pipeline: generate + validate + classify
python pipeline.py -i [input_folder] -o [output_folder] -b [batch_script]

# Validation only (already generated images)
python pipeline.py -i [original_folder] -o [generated_folder] --skip-generation
```

### Run Auto-Retry Pipeline
```bash
python run_auto_retry_pipeline.py --input ./images --output ./outputs --background "modern concrete wall"
```

## Architecture

### Core Components

1. **Web App** (`app_background_studio.py`) - Streamlit-based interactive UI for background generation workflows

2. **REST API** (`api/`) - FastAPI backend for task management
   - `main.py` - Entry point with CORS, exception handlers
   - `routers/tasks.py` - Task CRUD endpoints
   - `database.py` - SQLite async database with SQLAlchemy
   - `config.py` - Pydantic settings from .env

3. **Image Generation Pipeline** (`pipeline.py`) - Main orchestrator for batch image processing
   - Parallel generation with multi-key rotation
   - Quality validation (5 criteria with weights)
   - Automatic classification to `release/` or `review/`

4. **Auto-Retry Pipeline** (`auto_retry_pipeline/`) - Smart retry system
   - `validator.py` - Quality validation
   - `diagnoser.py` - Failure diagnosis
   - `enhancer.py` - Prompt enhancement based on diagnosis
   - `pipeline.py` - Orchestrates generate → validate → diagnose → enhance → retry loop

5. **Claude Skills** (`.claude/skills/`) - Modular prompt templates and workflows
   - `브랜드컷_brand-cut/` - 브랜드 패션 화보 통합 워크플로 (라우팅 → 생성 → 검증 → 리트라이)
   - `brand-dna/` - Brand-specific DNA files (JSON)
   - `prompt-templates/` - Style templates (editorial, selfie, etc.)
   - Director personas (7개: MLB마케팅, MLB그래픽, Discovery, Duvetica, SergioTacchini, Banillaco, 제품연출)
   - `배경교체_background-swap/` - Background replacement workflow
   - `시딩UGC_seeding-ugc/` - Influencer seeding UGC workflow

### Workflow Architecture

```
User Input → Brand Routing → Load Brand DNA → Load Template →
Outfit Analysis (VLM) → Director Vision → Prompt Assembly → Image Generation
```

See `docs/ARCHITECTURE.md` for detailed flow diagram.

---

## Gemini API 절대 규칙

이 섹션의 규칙은 **모든 이미지 생성 작업에 항상 적용**됩니다. 위반 시 생성물 전체 삭제 후 재생성 필요.

### 모델 선택

```python
# 무조건 이것만 사용
IMAGE_MODEL = "gemini-3-pro-image-preview"

# 절대 금지 (아래 모델 사용 금지)
# "gemini-2.0-flash-exp-image-generation"  → 인물 축소, 배경 합성 품질 낮음, 색감 불일치
# "gemini-2.0-flash"                       → 위와 동일
# "gemini-2.5-flash"                       → 텍스트 전용, 최대 1024px만 지원
```

### 해상도 설정

| 설정 | 해상도 (1:1 기준) | 용도 |
|------|------------------|------|
| `1K` | 1024x1024 | 테스트용 |
| `2K` | 2048x2048 | **일반 제작용 (기본값)** |
| `4K` | 4096x4096 | 고품질 최종 결과물 |

### Temperature 가이드

| 용도 | Temperature | 설명 |
|------|-------------|------|
| 배경 교체 / 참조 이미지 보존 | `0.2` | 충실도 최대 |
| 브랜드컷 에디토리얼 | `0.2 ~ 0.3` | 착장 충실도 유지 |
| 셀피 / 일상컷 | `0.3` | 자연스러운 변형 |
| 시딩 UGC | `0.35` | 자연스러운 다양성 |
| 자유 생성 | `0.3 ~ 0.5` | 창의적 다양성 |
| 실험적/아트 | `0.7 ~ 0.9` | 다양한 결과 |

### 콘텐츠 타입별 기본 설정

| 타입 | Template | Aspect Ratio | Temperature | 용도 |
|------|----------|--------------|-------------|------|
| Editorial/Brand Cut | editorial.json | 3:4 | 0.2 | 전문 브랜드 화보 |
| Selfie | selfie.json | 9:16 | 0.3 | 셀카/SNS |
| Daily Casual | daily_casual.json | 4:5 | 0.3 | 일상컷 |
| Seeding UGC | seeding_ugc.json | 9:16 | 0.35 | 인플루언서 시딩 |
| Background Swap | background-swap.json | Original | 0.2 | 배경 교체 |

### API 설정 코드 패턴

```python
config=types.GenerateContentConfig(
    temperature=0.2,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="3:4",
        image_size="2K"
    )
)
```

### API 키 관리

```bash
# .env format - multiple keys for rate limit rotation
GEMINI_API_KEY=key1,key2,key3,key4,key5
```

반드시 `get_next_api_key()` 패턴으로 thread-safe 로테이션 사용. 단일 키 하드코딩 금지.

### 에러 처리 표준

| 에러 | 코드 | 재시도 가능 |
|------|------|------------|
| 429 / rate limit | RATE_LIMIT | Yes (대기 후) |
| 503 / overloaded | SERVER_OVERLOAD | Yes (대기 후) |
| timeout | TIMEOUT | Yes (대기 후) |
| 401 / api key | AUTH_ERROR | No |
| safety / blocked | SAFETY_BLOCK | No |

재시도 시 `(attempt + 1) * 5`초 대기, 최대 3회.

---

## 브랜드 라우팅 테이블

모든 브랜드 관련 작업에서 이 테이블로 매칭합니다.

| 트리거 키워드 | 브랜드 | DNA 파일 | 디렉터 페르소나 |
|--------------|--------|----------|----------------|
| MLB, 영앤리치, 프리미엄, 시크, 마케팅 화보 | MLB 마케팅 | `mlb-marketing.json` | `(MLB마케팅)_시티미니멀_tyrone-lebon` |
| MLB 그래픽, 스트릿, 올드스쿨, 바시티 | MLB 그래픽 | `mlb-graphic.json` | `(MLB그래픽)_스트릿레전드_shawn-stussy` |
| Discovery, 아웃도어, 고프코어, 테크니컬 | Discovery | `discovery.json` | `(Discovery)_테크니컬유틸리티_yosuke-aizawa` |
| Duvetica, 럭셔리, 다운, 이탈리안, 장인 | Duvetica | `duvetica.json` | `(Duvetica)_럭셔리장인_brunello-cucinelli` |
| Sergio, 테니스, 레트로, 80s, 슬림 | Sergio Tacchini | `sergio-tacchini.json` | `(SergioTacchini)_실루엣혁명_hedi-slimane` |
| Banila, 뷰티, 색조, 맑은, K-뷰티 | Banillaco | `banillaco.json` | `(Banillaco)_맑은뷰티_ahn-joo-young` |
| 제품컷, 제품 연출, 플랫레이, 행잉, 히어로샷, 이커머스 | 제품연출 (전 브랜드) | 해당 브랜드 DNA | `(제품연출)_한국힙이커머스_musinsa-29cm` |

브랜드 미감지 시 사용자에게 질문: "어떤 브랜드의 이미지를 생성할까요?"

### 스타일 매칭

| 트리거 키워드 | 스타일 | 워크플로 |
|--------------|--------|---------|
| 화보, 에디토리얼, 매거진, 패션 | editorial | `브랜드컷_brand-cut` |
| 셀피, 일상, SNS, 캐주얼 | selfie | `브랜드컷_brand-cut` |
| 배경 교체, 배경 바꿔 | background-swap | `배경교체_background-swap` |
| 시딩, UGC, 인플루언서, 틱톡, 릴스 | seeding_ugc | `시딩UGC_seeding-ugc` |
| 일상컷, 남친샷, 산책, 데일리 | daily_casual | `일상컷_daily-casual` |
| 제품컷, 물촬, 상세페이지 | product | `(제품연출)_한국힙이커머스_musinsa-29cm` |

---

## 품질 검증 기준

### 표준 검증 (브랜드컷/배경교체)

| Criterion | Weight | 설명 |
|-----------|--------|------|
| model_preservation | 35% | 인물 보존도 (Must be 100) |
| lighting_match | 20% | 조명 일치도 |
| perspective_match | 15% | 원근감 일치도 |
| ground_contact | 15% | 지면 접촉 자연스러움 |
| edge_quality | 15% | 경계 품질 |

**Pass 조건**: `model_preservation = 100` AND `total >= 95`

### UGC 검증 (시딩 UGC 전용)

| Criterion | Weight | 설명 |
|-----------|--------|------|
| realism | 35% | 실제 폰 촬영 같은 자연스러움 |
| person_preservation | 25% | 인물 보존도 |
| scenario_fit | 20% | 시나리오 적합성 |
| skin_condition | 10% | 피부 상태 자연스러움 |
| anti_polish_factor | 10% | 과도한 보정 방지 |

**UGC 원칙**: "너무 잘 나오면 실패" - 폰으로 대충 찍은 것 같아야 성공

---

## Output Directory Structure

모든 출력은 `Fnf_studio_outputs/` 단일 폴더로 통합됩니다. (`core/config.py`의 `OUTPUT_BASE_DIR`)

```
Fnf_studio_outputs/
├── {brand}/{workflow}/  # 브랜드별/워크플로별 하위 폴더
│   ├── release/         # Passed quality check (total≥95, model_preservation=100)
│   ├── manual_review/   # Auto-retry pipeline failures
│   │   └── diagnosis/   # JSON diagnosis files
│   ├── logs/            # Pipeline reports
│   └── _temp/           # 임시 파일 (자동 정리)
├── seeding_ugc/         # 시딩 UGC 결과물
├── edit/                # 틴트/편집 결과물
└── logs/                # 전체 파이프라인 리포트
```

---

## 스킬 참조 가이드

이미지 생성 코드 작성 시 아래 스킬을 참조하세요:

| 스킬 | 경로 | 참조 시점 |
|------|------|----------|
| 이미지생성 레퍼런스 | `.claude/skills/이미지생성_레퍼런스_image-gen-reference/SKILL.md` | 코드 패턴, 유틸리티 함수, 프롬프트 템플릿 필요 시 |
| 브랜드컷 워크플로 | `.claude/skills/브랜드컷_brand-cut/SKILL.md` | 브랜드 화보 파이프라인 구현 시 |
| 배경교체 워크플로 | `.claude/skills/배경교체_background-swap/SKILL.md` | 배경 교체 파이프라인 구현 시 |
| 시딩UGC 워크플로 | `.claude/skills/시딩UGC_seeding-ugc/SKILL.md` | UGC 생성 파이프라인 구현 시 |

---

## 자동 스킬 호출 규칙

### 프론트엔드 작업 시 자동 호출
다음 키워드 감지 시 **반드시** `frontend-design:frontend-design` 스킬을 호출:
- 한국어: 프론트엔드, 프론트, 컴포넌트, 버튼, 페이지, 화면, 대시보드, 랜딩페이지, 웹페이지, UI, 인터페이스
- 영어: frontend, component, button, page, dashboard, landing page, interface

**호출 방법:**
```
Skill(skill="frontend-design:frontend-design", args="[사용자 요청 내용]")
```
