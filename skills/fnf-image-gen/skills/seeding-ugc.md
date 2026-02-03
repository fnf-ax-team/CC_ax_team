---
name: 시딩UGC_seeding-ugc
description: 인플루언서 시딩용 UGC 콘텐츠 이미지 생성 워크플로. TikTok/릴스/쇼츠용 영상 가이드 프레임. 진짜 UGC처럼 보여야 하며 실제 릴리즈 예정. 시나리오 선택 → 피부상태 설정 → 프롬프트 조립 → 생성 → 리얼리즘 검증.
user-invocable: true
argument-hint: [브랜드명] [시나리오] [수량] (예: Banillaco 두통+햇빛 선케어 시딩 3장)
---

# 시딩UGC - 인플루언서 시딩용 UGC 콘텐츠 생성

> **범용 레퍼런스**: Gemini API, 프롬프트 패턴, 유틸리티 함수 등
> 워크플로에 종속되지 않는 기초 지식은 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` 참조

> **템플릿 파일**: `prompt-templates/seeding_ugc.json`

## 핵심 원칙

> **진짜처럼 보여야 한다. 프로페셔널하게 보이면 실패. 완벽하면 실패.**
> **폰으로 대충 찍은 것 같아야 성공.**

이 스킬의 결과물은 실제 TikTok/YouTube Shorts/Instagram Reels에 릴리즈됩니다.
인플루언서에게 제공하는 시딩 콘텐츠 가이드 또는 직접 사용 이미지입니다.

### 다른 스킬과의 차이

| 항목 | 브랜드컷 | 셀피 | 일상컷 | **시딩UGC** |
|------|----------|------|--------|------------|
| 목적 | 공식 화보 | SNS 셀카 | 일상 기록 | **시딩 콘텐츠** |
| 미학 | 프로페셔널 | 예쁘게 | 자연스럽게 | **날것 그대로** |
| 피부 | 완벽한 보정 | 자연스럽지만 깨끗 | 약간의 결점 | **결점이 핵심** |
| 조명 | 스튜디오 | 링라이트/자연광 | 있는 그대로 | **비호감 조명 OK** |
| 포즈 | 모델 포즈 | 셀카 포즈 | 일상 동작 | **불편한 상황 포즈** |
| 프로덕션 느낌 | 높음 | 중간 | 낮음 | **없어야 함** |

## 사용법

```
/시딩UGC_seeding-ugc Banillaco 두통+햇빛 선케어 시딩 3장
/시딩UGC_seeding-ugc Banillaco 유분 고민 → 사용 후 비교 4장
/시딩UGC_seeding-ugc 아침 루틴 스킨케어 과정 5장
/시딩UGC_seeding-ugc 운동 후 땀 세안 진정케어 3장
/시딩UGC_seeding-ugc 다크서클 고민 아이크림 before/after 2장
```

### Python 워크플로 (API 연동용)

```python
from workflow import ImageGenerationWorkflow

workflow = ImageGenerationWorkflow(api_key="YOUR_API_KEY")

result = workflow.generate(
    user_input="Banillaco 두통+햇빛 선케어 시딩 3장",
    template="seeding_ugc",          # 시딩 UGC 템플릿
    model_images=[face_pil],          # 얼굴 유지용
    input_vars={
        "gender": "여성",
        "age": "20대 초반",
        "scenario": "headache_sun",    # AI가 자동 선택 또는 지정
        "skin_state": "oily_shiny",
        "camera_style": "selfie_complaint"
    },
    count=3,
    max_workers=4
)
```

---

# 파이프라인 (6단계)

```
사용자 입력 → Step 1: 브랜드 라우팅 + 템플릿 로드
            → Step 2: AI 시나리오 판단 (scenario, skin_state, camera_style 자동 선택)
            → Step 3: 프롬프트 조립 (UGC 리얼리즘 최우선)
            → Step 4: 이미지 생성 (Gemini 3 Pro, 2K)
            → Step 5: 리얼리즘 검증 (UGC 전용 기준)
            → Step 6: 결과 반환 + 시딩 가이드 메모
```

---

## Step 1: 브랜드 라우팅 + 템플릿 로드

`seeding_ugc.json` 템플릿과 brand DNA를 로드합니다.
시딩UGC는 주로 뷰티/스킨케어 브랜드에 사용되지만, 모든 브랜드에 적용 가능합니다.

## Step 2: AI 시나리오 판단

사용자 요청에서 시나리오를 자동 판단합니다.

### 시나리오 카테고리 자동 매칭

| 사용자 키워드 | → 카테고리 | → 구체 시나리오 |
|---------------|------------|-----------------|
| "두통", "햇빛", "자외선", "여름" | `pain_point` | `headache_sun` |
| "번들거림", "유분", "기름" | `pain_point` | `oily_frustration` |
| "트러블", "여드름", "뾰루지" | `pain_point` | `acne_concern` |
| "건조", "각질", "당김" | `pain_point` | `dryness_flaking` |
| "다크서클", "피곤", "수면부족" | `pain_point` | `dark_circles` |
| "바람", "엉망", "흐트러진" | `pain_point` | `wind_mess` |
| "전", "before", "사용 전" | `before_after` | `before_*` |
| "후", "after", "사용 후" | `before_after` | `after_*` |
| "전후", "비교", "before/after" | `before_after` | before + after 쌍 |
| "아침", "모닝", "루틴" | `daily_routine` | `morning_routine` |
| "출근", "터치업" | `daily_routine` | `commute_touchup` |
| "낮", "리프레시" | `daily_routine` | `midday_refresh` |
| "저녁", "클렌징", "나이트" | `daily_routine` | `night_routine` |
| "운동", "땀", "헬스" | `daily_routine` | `workout_post` |

### Camera Style 자동 매칭

| 사용자 키워드 | → camera_style |
|---------------|----------------|
| "셀카", "클로즈업", "고민" | `selfie_complaint` |
| "거울", "루틴", "바르기" | `mirror_film` |
| "텍스처", "사용법" | `pov_application` |
| "야외", "일상", "캔디드" | `friend_recording` |
| "전체과정", "고정" | `propped_timelapse` |

### Skin State 자동 매칭

시나리오에 따라 적합한 피부 상태가 자동 결정됩니다:

| 시나리오 | → 기본 skin_state |
|----------|-------------------|
| `headache_sun` | `sun_damaged` + `sweaty_flushed` |
| `oily_frustration` | `oily_shiny` |
| `acne_concern` | `blemished` |
| `dryness_flaking` | `dry_flaky` |
| `dark_circles` | `tired_dull` |
| `before_skincare` | `bare_clean` |
| `after_skincare` | `post_product` |
| `morning_routine` | `bare_clean` → `post_product` |
| `workout_post` | `sweaty_flushed` |

## Step 3: 프롬프트 조립

### 프롬프트 구조
```
[shooting_style: raw UGC] + [device: iPhone front camera] +
[still frame from video] + [subject + skin_state] +
[scenario prompt_fragment] + [camera_style angle/framing] +
[unflattering lighting] + [real environment] +
[technical: video screenshot feel] +
[subtle brand product in scene]
```

### 예시 조립 결과 (두통+햇빛 시나리오)
```
raw UGC content, TikTok/Reels style, authentic unfiltered,
iPhone 15 Pro front camera 12MP 24mm f/1.9, still frame from video,
young Korean woman early 20s, natural unguarded expression,
REAL skin: visible pores uneven texture natural imperfections,
very oily and sweaty visible shine on T-zone slight sunburn redness,
eyes closed or squinting hand touching forehead as if having headache,
strong direct sunlight creating harsh shadows and bright highlights on face,
front camera selfie close to face slightly unflattering angle,
outdoor in direct harsh sunlight,
slightly shaky handheld phone feel, slightly off-center frame,
video screenshot feel NOT a carefully taken photo,
subtle Banillaco suncare product visible nearby
```

### 핵심: Negative Prompt 반드시 포함
```
professional studio lighting, perfect skin retouching, beauty filter applied,
ring light catchlight, perfectly composed frame, color graded cinematic look,
model pose, styled hair and makeup, clean minimalist background,
magazine quality, AI generated look, plastic smooth skin, symmetrical perfect face
```

## Step 4: 이미지 생성

```python
# Gemini API 호출
config = types.GenerateContentConfig(
    temperature=0.35,   # 일반보다 살짝 높음 (자연스러운 변형 유도)
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="9:16",   # TikTok/릴스/쇼츠 세로 포맷 필수
        image_size="2K"
    )
)
```

| 설정 | 값 | 비고 |
|------|-----|------|
| 모델 | `gemini-3-pro-image-preview` | 필수 |
| temperature | 0.35 | 자연스러운 변형 유도 (일반 0.3보다 약간 높음) |
| 비율 | 9:16 | TikTok/릴스/쇼츠 필수 |
| 해상도 | 2K | 프로덕션 릴리즈 품질 |

## Step 5: 리얼리즘 검증 (UGC 전용)

**일반 품질 검증과 반대 방향**입니다. 너무 잘 나오면 실패.

### UGC 리얼리즘 검증 기준

| 기준 | 가중치 | 설명 | 통과 기준 |
|------|--------|------|-----------|
| UGC 리얼리즘 | 35% | 실제 폰 촬영처럼 보이는가? | ≥ 85 |
| 인물 보존 | 25% | 얼굴/체형 원본 일치 | = 100 |
| 시나리오 정합성 | 20% | 요청한 상황이 잘 표현되었는가? | ≥ 80 |
| 피부 상태 | 10% | skin_state가 정확히 반영되었는가? | ≥ 80 |
| Anti-Polish | 10% | 과도하게 깨끗/프로페셔널하지 않은가? | ≥ 80 |

### Anti-Polish 체크리스트 (이것들이 보이면 감점)
- [ ] 링라이트 캐치라이트 → -20점
- [ ] 완벽한 피부 보정 → -25점
- [ ] 스튜디오 조명 느낌 → -20점
- [ ] 완벽한 구도/센터링 → -10점
- [ ] 프로 모델 포즈 → -15점
- [ ] 컬러그레이딩 느낌 → -10점

### 실패 시 재시도 전략
- UGC 리얼리즘 < 85: "more raw, more authentic, less polished" 프롬프트 강화
- Anti-Polish < 80: negative prompt 강화 + "imperfect framing, slightly shaky" 추가
- 피부 상태 미반영: skin_state 프롬프트 더 구체적으로 강화
- temperature 상향: 0.35 → 0.4 → 0.45 (더 랜덤한 변형 유도)

## Step 6: 결과 반환 + 시딩 가이드 메모

생성된 이미지와 함께 시딩 가이드 메모를 생성합니다:

```json
{
  "images": ["output_1.png", "output_2.png", "output_3.png"],
  "seeding_guide": {
    "scenario": "headache_sun",
    "target_platform": "TikTok/Reels/Shorts",
    "suggested_caption": "진짜 어제 햇빛 너무 세서 두통 왔는데... 🥵",
    "suggested_hashtags": ["#선크림추천", "#여름필수템", "#자외선차단"],
    "product_placement": "자연스럽게 손에 들고 있거나 옆에 놓인 상태",
    "content_direction": "불편한 상황 → 제품 사용 → 해결 서사"
  },
  "quality_scores": {
    "ugc_realism": 92,
    "person_preservation": 100,
    "scenario_accuracy": 88,
    "skin_state_accuracy": 85,
    "anti_polish": 90
  }
}
```

---

## Before/After 페어 생성

Before/After 시나리오는 자동으로 2장을 페어로 생성합니다:

```
사용자: "스킨케어 전후 비교 시딩 이미지"

→ Before 이미지: bare_clean skin_state, 세안 직후, 불만족 표정
→ After 이미지: post_product skin_state, 같은 환경, 만족 표정, 제품 보임
→ 동일 인물, 동일 환경, 피부 상태만 변화
```

### Before/After 일관성 규칙
| 항목 | Before/After 동일 | 변화 |
|------|-------------------|------|
| 인물 | 동일 | - |
| 환경/배경 | 동일 | - |
| 카메라 앵글 | 동일 | - |
| 조명 | 동일 | - |
| 피부 상태 | - | 변화 (before → after) |
| 표정 | - | 변화 (불만 → 만족) |
| 제품 | 보이지 않음 | 손에 들거나 옆에 |
