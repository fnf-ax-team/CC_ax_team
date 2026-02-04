---
name: fnf-image-gen
description: AI 이미지 생성 통합 스킬. 브랜드컷(화보), 셀피, 일상컷, 시딩UGC, 배경교체 5종 콘텐츠를 Gemini API로 생성. "화보 만들어줘", "시딩 이미지 생성해줘", "배경 바꿔줘" 등으로 트리거.
---

# FNF Image Generation - AI 이미지 생성 통합 스킬

> Gemini 3 Pro Image API를 활용한 5종 콘텐츠 생성 시스템

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "화보 만들어줘", "브랜드컷 생성해줘", "룩북 이미지"
- "셀피 이미지 만들어줘", "인스타 셀카 스타일로"
- "일상컷 생성해줘", "남친샷 스타일로", "친구가 찍어준 느낌"
- "시딩 이미지 만들어줘", "틱톡 시딩 콘텐츠", "UGC 스타일로"
- "배경 바꿔줘", "배경 교체해줘"

> **Gemini API 규칙 (모델, 해상도, Temperature, API키, 에러처리)** → `CLAUDE.md` 참조
> **브랜드 라우팅 테이블** → `CLAUDE.md` 참조

---

## 5종 콘텐츠 카테고리

| 카테고리 | 템플릿 | 목적 |
|----------|--------|------|
| **브랜드컷(화보)** | `templates/editorial.json` | 공식 화보/룩북 |
| **셀피** | `templates/selfie.json` | 인스타 셀카 |
| **일상컷** | `templates/daily_casual.json` | 일상 기록 사진 |
| **시딩UGC** | `templates/seeding_ugc.json` | 틱톡/릴스 시딩 콘텐츠 |
| **배경교체** | `templates/background-swap.json` | 기존 이미지 배경 변경 |

### 카테고리 선택 기준

```
사용자 입력 분석:
  "화보", "룩북", "에디토리얼"     → 브랜드컷
  "셀카", "셀피", "인스타"         → 셀피
  "일상", "친구가 찍어준", "남친샷" → 일상컷
  "시딩", "UGC", "틱톡", "릴스"    → 시딩UGC
  "배경 바꿔", "배경 교체"         → 배경교체
```

---

## Your Task

### 1. 카테고리 판단
사용자 요청에서 5종 중 적합한 카테고리를 선택합니다.

### 2. 브랜드 라우팅
브랜드가 언급되면 `brand-dna/` 에서 해당 JSON을 로드합니다.

> 브랜드 → DNA → 디렉터 매칭 테이블 → `CLAUDE.md` "브랜드 라우팅 테이블" 참조

### 3. AI 판단으로 옵션 선택
각 템플릿 JSON 안의 옵션들 중 상황에 맞는 것을 AI가 자동 선택합니다.
사용자가 명시한 항목은 기본값보다 우선.

### 4. 프롬프트 조립 + 생성
카테고리별 템플릿 구조에 따라 프롬프트를 조립하고 Gemini API를 호출합니다.

> API 설정 코드 패턴 → `CLAUDE.md` "Gemini API 절대 규칙" 참조

### 4.5 VLM 제품 분석 (제품 레퍼런스 있을 때)
제품 레퍼런스 이미지가 제공되면, **생성 전에 VLM으로 제품을 자동 분석**하여 상세 묘사를 생성합니다.
배경 교체의 모델 물리 분석(VFX)과 동일한 패턴입니다.
- VLM 분석 결과(형태, 재질, 투명도, 로고 위치, 사용법 등)를 프롬프트에 자동 주입
- 수동 설명보다 정확도 40%+ 향상 (product_accuracy 0→30 → 98 검증됨)
- 분석 실패 시 `brand-dna/{brand}.json`의 `products` 섹션으로 폴백

### 5. 품질 검증

> 워크플로별 검증 기준 (브랜드컷 6항목 / 배경교체 7항목 / UGC 5항목) → `CLAUDE.md` "품질 검증 기준" 참조

---

## 시딩UGC 핵심 원칙

> **진짜처럼 보여야 한다. 프로페셔널하게 보이면 실패.**

### 시나리오 (15개)

**Pain Point (고민호소):** headache_sun, oily_frustration, acne_concern, dryness_flaking, dark_circles, wind_mess

**Before/After (전후비교):** before_skincare, after_skincare, before_makeup, after_makeup

**Daily Routine (일상루틴):** morning_routine, commute_touchup, midday_refresh, night_routine, workout_post

### Negative Prompt (시딩UGC 필수)
```
professional studio lighting, perfect skin retouching, beauty filter,
ring light catchlight, perfectly composed frame, color graded cinematic look,
model pose, clean minimalist background, magazine quality,
AI generated look, plastic smooth skin,
app UI overlay, duplicate phone, ghost phone,
extra hands, public restroom, text overlay, watermark
```

---

## 폴더 구조

```
fnf-image-gen/
├── SKILL.md                    # 이 파일 (통합 문서)
├── workflows/                  # 워크플로 상세 문서
│   ├── editorial.md            # 브랜드컷 워크플로
│   ├── selfie.md               # 셀피 워크플로 (작성 예정)
│   ├── daily-casual.md         # 일상컷 워크플로
│   ├── seeding-ugc.md          # 시딩UGC 워크플로
│   └── background-swap.md      # 배경교체 워크플로
├── templates/                  # 프롬프트 템플릿
│   ├── editorial.json          # 브랜드컷(화보)
│   ├── selfie.json             # 셀피
│   ├── daily_casual.json       # 일상컷
│   ├── seeding_ugc.json        # 시딩UGC
│   └── background-swap.json    # 배경교체
├── brand-dna/                  # 브랜드 DNA
│   ├── banillaco.json
│   ├── discovery.json
│   ├── duvetica.json
│   ├── mlb-marketing.json
│   ├── mlb-graphic.json
│   └── sergio-tacchini.json
└── directors/                  # 디렉터 페르소나
    ├── (Banillaco)_맑은뷰티_ahn-joo-young/
    ├── (Discovery)_테크니컬유틸리티_yosuke-aizawa/
    ├── (Duvetica)_럭셔리장인_brunello-cucinelli/
    ├── (MLB그래픽)_스트릿레전드_shawn-stussy/
    ├── (MLB마케팅)_시티미니멀_tyrone-lebon/
    ├── (SergioTacchini)_실루엣혁명_hedi-slimane/
    └── (제품연출)_한국힙이커머스_musinsa-29cm/
```

---

## 워크플로 상세

각 카테고리의 상세 워크플로는 `workflows/` 폴더에서 확인:

| 카테고리 | 워크플로 파일 | 설명 |
|----------|-------------|------|
| 브랜드컷 | [`workflows/editorial.md`](workflows/editorial.md) | 7단계 파이프라인 + 검증 + 재시도 |
| 셀피 | [`workflows/selfie.md`](workflows/selfie.md) | (작성 예정) |
| 일상컷 | [`workflows/daily-casual.md`](workflows/daily-casual.md) | 5단계 파이프라인 |
| 시딩UGC | [`workflows/seeding-ugc.md`](workflows/seeding-ugc.md) | 7단계 파이프라인 + UGC 검증 |
| 배경교체 | [`workflows/background-swap.md`](workflows/background-swap.md) | VFX/VLM 분석 + 9단계 파이프라인 |

---

## Edge Cases

- **브랜드 미지정 시**: 범용 설정으로 생성 (brand_dna 없이 템플릿만 사용)
- **시딩UGC가 너무 깨끗하게 나올 때**: temperature 올림 (0.35→0.4→0.45) + Negative Prompt 강화
- **인물 보존 실패 시**: "THIS EXACT person" 지시어 강화 + 고해상도 정면 레퍼런스 사용
- **제품 렌더링 부정확 시**: 제품 특징을 프롬프트에 구체적으로 명시

---

**작성일**: 2026-02-02
**버전**: 2.0 (워크플로 분리)
**통합 출처**: fnf-generate, 브랜드라우팅_brand-routing, 프롬프트패턴_prompt-patterns, 이미지생성기본_image-generation-base, 검증품질관리_validation-quality, 착장분석_clothing-analysis, 배경교체, 배경분석, 배경생성워크플로우, 오브젝트보존, quality-check, 모델분석
**참고**: editorial-prompt, selfie-prompt는 이 스킬에 통합됨
