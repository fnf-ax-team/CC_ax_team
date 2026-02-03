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

## 필수 환경변수

```bash
GEMINI_API_KEY=key1,key2,key3   # 쉼표로 구분, 복수 키 가능 (rate limit 대응)
```

## 필수 모델

```python
# 반드시 이 모델만 사용 (다른 모델 사용 금지)
model = "gemini-3-pro-image-preview"
```

---

## 5종 콘텐츠 카테고리

| 카테고리 | 템플릿 | 목적 | 종횡비 | temperature |
|----------|--------|------|--------|-------------|
| **브랜드컷(화보)** | `templates/editorial.json` | 공식 화보/룩북 | 3:4 | 0.2 |
| **셀피** | `templates/selfie.json` | 인스타 셀카 | 9:16 | 0.3 |
| **일상컷** | `templates/daily_casual.json` | 일상 기록 사진 | 4:5 | 0.3 |
| **시딩UGC** | `templates/seeding_ugc.json` | 틱톡/릴스 시딩 콘텐츠 | 9:16 | 0.35 |
| **배경교체** | `templates/background-swap.json` | 기존 이미지 배경 변경 | 원본 유지 | 0.2 |

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

| 브랜드 | DNA 파일 | 디렉터 |
|--------|----------|--------|
| Banillaco (바닐라코) | `banillaco.json` | 맑은뷰티 (ahn-joo-young) |
| Discovery (디스커버리) | `discovery.json` | 테크니컬유틸리티 (yosuke-aizawa) |
| Duvetica (듀베티카) | `duvetica.json` | 럭셔리장인 (brunello-cucinelli) |
| MLB 마케팅 | `mlb-marketing.json` | 시티미니멀 (tyrone-lebon) |
| MLB 그래픽 | `mlb-graphic.json` | 스트릿레전드 (shawn-stussy) |
| Sergio Tacchini | `sergio-tacchini.json` | 실루엣혁명 (hedi-slimane) |

### 3. AI 판단으로 옵션 선택
각 템플릿 JSON 안의 옵션들 중 상황에 맞는 것을 AI가 자동 선택합니다.
사용자가 명시한 항목은 기본값보다 우선.

### 4. 프롬프트 조립 + 생성
카테고리별 템플릿 구조에 따라 프롬프트를 조립하고 Gemini API를 호출합니다.

```python
config = types.GenerateContentConfig(
    temperature=카테고리별_temperature,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio=카테고리별_비율,
        image_size="2K"
    )
)
```

### 5. 품질 검증
- **일반 카테고리**: 인물보존(35%) + 조명(20%) + 구도(15%) + 피부(15%) + 배경(15%)
- **시딩UGC**: UGC리얼리즘(35%) + 인물보존(25%) + 시나리오정합(20%) + 피부상태(10%) + Anti-Polish(10%)

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
├── SKILL.md                    # 이 파일 (통합 진입점)
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
├── directors/                  # 디렉터 페르소나
│   ├── (Banillaco)_맑은뷰티_ahn-joo-young/
│   ├── (Discovery)_테크니컬유틸리티_yosuke-aizawa/
│   ├── (Duvetica)_럭셔리장인_brunello-cucinelli/
│   ├── (MLB그래픽)_스트릿레전드_shawn-stussy/
│   ├── (MLB마케팅)_시티미니멀_tyrone-lebon/
│   ├── (SergioTacchini)_실루엣혁명_hedi-slimane/
│   └── (제품연출)_한국힙이커머스_musinsa-29cm/
└── skills/                     # 카테고리별 상세 스킬 문서
    ├── brand-cut.md
    ├── background-swap.md
    ├── daily-casual.md
    └── seeding-ugc.md
```

## Edge Cases

- **브랜드 미지정 시**: 범용 설정으로 생성 (brand_dna 없이 템플릿만 사용)
- **시딩UGC가 너무 깨끗하게 나올 때**: temperature 올림 (0.35→0.4→0.45) + Negative Prompt 강화
- **인물 보존 실패 시**: "THIS EXACT person" 지시어 강화 + 고해상도 정면 레퍼런스 사용
- **제품 렌더링 부정확 시**: 제품 특징을 프롬프트에 구체적으로 명시
