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

### 프롬프트 작성 핵심 원칙

1. **물리적 현상 묘사**: 추상적 표현("아름다운", "자연스러운 느낌")을 배제하고 물리적으로 관찰 가능한 현상을 묘사합니다.
   - X: "자연스러운 피부"
   - O: "visible fine pores, subtle sebum shine on T-zone, fine texture visible up close"

2. **5단계 레이어 순서**: AI가 이미지를 그리는 순서에 맞춰 프롬프트를 구성합니다. 순서가 곧 우선순위입니다.
   1. **기본 설정**: "Natural smartphone selfie" + device profile (iPhone 15 Pro front camera, 12MP TrueDepth camera)
   2. **피사체**: gender, country, age, expression, skin texture, hair, attire
   3. **★ Visual Action 상세 묘사 ★**: 입력된 Visual Action을 구체적 물리적 동작으로 변환 (가장 중요!)
   4. **환경/배경**: bright clean location + simple clean background + comfortable atmosphere
   5. **조명/기술**: soft natural lighting + even illumination + natural colors + sharp focus on face

3. **Visual Action 최우선 원칙 ★★★**: Visual Action은 이미지의 핵심 동작/장면을 정의하는 가장 중요한 입력값입니다.
   - Visual Action에 명시된 동작, 자세, 표정, 상황을 프롬프트의 중심에 배치
   - 추상적 동작이 아닌 구체적 물리 동작으로 변환:
     - "크림 바르기" → "using index finger to gently spread white cream on cheek in circular motion"
     - "피부 상태 확인하며 고민" → "examining skin closely with slightly concerned expression, touching chin area"
     - "제품 보여주며 만족한 표정" → "holding product near face, showing satisfied smile with slight head tilt"

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

#### 1단계: 시나리오/동작 기반 자동 결정 (최우선)

**핵심 원칙**: 틱톡/릴스 시딩 콘텐츠에서 제품 사용 장면은 **폰을 거치하고 양손을 자유롭게 쓰는 GRWM(Get Ready With Me) 구도**가 표준입니다. 셀카 포즈(한 손에 폰)는 "고민 보여주기"나 "결과 확인" 장면에만 사용합니다.

| 동작/상황 | → camera_style | 이유 |
|-----------|----------------|------|
| 제품 바르기 (파운데이션, 크림, 세럼 등) | `propped_timelapse` | 양손 필요, GRWM 스타일 |
| 스킨케어 루틴 전체 과정 | `propped_timelapse` | 양손 필요, 고정 카메라 |
| 클렌징/세안 | `propped_timelapse` | 양손 필요 |
| 메이크업 과정 | `propped_timelapse` | 양손 필요, 거울 앞 고정 |
| 마스크팩 붙이기 | `propped_timelapse` | 양손 필요 |
| 피부 고민 보여주기 (트러블, 유분 등) | `selfie_complaint` | 한 손으로 문제 부위 가리키기 |
| 결과/비포애프터 확인 | `selfie_complaint` | 한 손 셀카로 결과 보여주기 |
| 거울 앞 셀카 (제품 사용 X) | `mirror_film` | 거울 앞 상태 확인 |
| 텍스처/발색 클로즈업 | `pov_application` | 손등/팔 클로즈업 |
| 야외/일상 장면 | `friend_recording` | 제3자 촬영 느낌 |

#### 2단계: 사용자 키워드 오버라이드

사용자가 명시적으로 camera style을 지정하면 1단계를 오버라이드합니다:

| 사용자 키워드 | → camera_style |
|---------------|----------------|
| "셀카", "클로즈업" | `selfie_complaint` |
| "거울" | `mirror_film` |
| "텍스처", "사용법" | `pov_application` |
| "야외", "캔디드" | `friend_recording` |
| "고정", "GRWM", "겟레디" | `propped_timelapse` |

#### propped_timelapse 구도 상세 (GRWM 표준)

**절대 규칙: 카메라/폰이 프레임에 절대 보이면 안 됨.** 카메라가 촬영하고 있으므로 카메라 자체는 보이지 않는 것이 물리적으로 당연함.

| 항목 | 설명 |
|------|------|
| **카메라** | **프레임에 절대 보이지 않음** - 카메라가 촬영 중이므로 물리적으로 안 보임 |
| **앵글** | 약간 아래에서 위로 올려다보는 각도 (폰이 책상/선반 위에 세워져 있으므로) 또는 정면 eye-level |
| **손** | 양손 자유. 한 손에 손거울/제품, 다른 손으로 퍼프/브러시/손가락으로 바르기 |
| **시선** | 손거울을 보며 바르기 OR 카메라(=시청자)를 보며 바르기. 둘 다 자연스러움 |
| **소도구** | 손거울, 퍼프/스펀지, 브러시, 쿠션팩트, 앞머리 롤러/헤어밴드 등 실제 GRWM 소품 |
| **프레이밍** | 얼굴+어깨+상반신, 약간 오프센터 OK |
| **안정성** | 대체로 안정적이나 즉석 거치라 미세한 흔들림 |
| **프롬프트 필수 포함** | "filmed by propped phone, camera NOT visible in frame, both hands free, GRWM style, looking at hand mirror or looking at camera while applying" |
| **Negative 필수 포함** | "phone visible in frame, camera visible, smartphone in shot, hand holding phone" |

> **mirror_film 주의사항**: 거울 반사 구도가 아닌 거울 앞에서 프론트카메라로 직접 찍는 방식. 폰이 거울에 비치는 구도 사용 금지 (유령 핸드폰 방지). 프롬프트에 "NOT reflected in mirror, direct front camera shot" 명시 필요.

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
| `glowing_natural` | `healthy_glowing` |
| `fresh_morning` | `healthy_glowing` |
| `skincare_satisfied` | `post_product` |

### healthy_skin 시나리오 (추가)

pain_point만이 아닌 건강한 피부 상태의 시나리오도 지원합니다:

| 시나리오 | 설명 | 피부 상태 | 표정 |
|----------|------|-----------|------|
| `glowing_natural` | 자연스러운 건강한 피부 셀카 | healthy_glowing | 편안한 미소, 자신감 |
| `fresh_morning` | 상쾌한 아침 느낌 | healthy_glowing | 부드러운 미소, 산뜻함 |
| `skincare_satisfied` | 스킨케어 후 만족감 | post_product | 만족스러운 표정, 자연스러운 자신감 |

### skin_states 정의 (전체)

| skin_state | 설명 |
|------------|------|
| `normal_daily` | 일상 피부, 보이는 모공, 약간의 불균일, 미세한 붉음 |
| `oily_shiny` | T존 과도한 유분, 번들거림, 확대된 모공, 기름기 |
| `dry_flaky` | 건조 각질, 벗겨짐, 당기는 느낌, 광택 없음 |
| `bare_clean` | 세안 직후 약간 축축, 무제품, 모공/피부결 노출 |
| `post_product` | 제품 적용 후 미묘한 광택, 촉촉하지만 자연스러움 |
| `healthy_glowing` | 자연스러운 건강 광택, 미세 모공 보이지만 깨끗하고 맑음, 자연스러운 윤기 |
| `sun_damaged` | 자외선 손상, 붉음, 따가운 느낌 |
| `sweaty_flushed` | 땀, 상기된 피부, 붉음 |
| `blemished` | 트러블, 여드름, 붉은 부위 |
| `tired_dull` | 피곤한 피부, 칙칙함, 생기 없음 |

## Step 3: 프롬프트 조립

### 프롬프트 구조
```
[Layer 1 - 기본 설정] "Natural smartphone selfie" + "iPhone 15 Pro front camera 12MP TrueDepth camera" + "still frame from video"
[Layer 2 - 피사체] gender + country + age + expression + skin_state + makeup + hair + attire
[Layer 3 - ★ Visual Action ★] 입력된 Visual Action을 구체적 물리 동작으로 변환하여 배치 (최우선)
[Layer 4 - 환경/배경] location + background + atmosphere + depth
[Layer 5 - 조명/기술] lighting + color_temperature + focus + color_science + overall_feel
+ [subtle brand product in scene]
```

### 예시 조립 결과 (건강한 피부 셀카 시나리오 - 5레이어 구조)
```
[Layer 1] Natural smartphone selfie, iPhone 15 Pro front camera 12MP TrueDepth camera, still frame from TikTok video,
[Layer 2] young Korean woman early 20s, natural relaxed expression with gentle smile, healthy glowing skin with visible fine texture, clean and clear complexion with subtle natural radiance, minimal natural makeup fresh faced look, neat casual hair pulled back with white headband, wearing clean white casual top,
[Layer 3 - Visual Action] ONE hand gently touching cheek to show healthy skin while other hand holds phone at comfortable selfie angle slightly above eye level, close-up selfie face fills 75% of frame with full face visible,
[Layer 4] bright clean room background with white wall and soft natural window light visible, soft blurred background focus on face,
[Layer 5] soft even lighting flattering the face without harsh shadows, neutral to slightly warm daylight color temperature, face in sharp focus, natural skin tones accurate colors, high quality TikTok viral content style, authentic yet appealing natural beauty moment
```

### 예시 조립 결과 (두통+햇빛 시나리오 - 5레이어 구조)
```
[Layer 1] Natural smartphone selfie, iPhone 15 Pro front camera 12MP TrueDepth camera, still frame from video,
[Layer 2] young Korean woman early 20s, natural unguarded expression, REAL skin visible pores uneven texture natural imperfections, very oily and sweaty visible shine on T-zone slight sunburn redness,
[Layer 3 - Visual Action] eyes closed or squinting, ONE hand touching forehead as if having headache from strong sunlight, other hand holding phone, pained uncomfortable expression,
[Layer 4] outdoor in direct harsh sunlight, bright overexposed background,
[Layer 5] strong direct sunlight creating harsh shadows and bright highlights on face, slightly shaky handheld phone feel, slightly off-center frame, video screenshot feel NOT a carefully taken photo, subtle Banillaco suncare product visible nearby
```

### 핵심: Negative Prompt 반드시 포함
```
professional studio lighting, heavy beauty filter, over-retouched skin,
ring light catchlight in eyes, perfectly posed model shot, magazine editorial look,
AI generated artifacts, plastic smooth skin with no texture, overly symmetrical face,
TikTok interface, Instagram Reels UI, YouTube Shorts UI, social media app interface,
like button, comment button, share button, follow button, profile icon,
music info overlay, hashtag overlay, progress bar, timestamp overlay, app UI overlay,
duplicate phone, extra phone, ghost phone, floating phone,
extra hands, duplicate hands, distorted hands, deformed fingers,
unwanted text overlay, watermark, logo, brand name text,
professional model pose, fashion photography lighting, advertising photo look,
stock photo aesthetic, harsh unflattering shadows, dark gloomy lighting,
dirty messy background, blurry out of focus face
```

### 자막 배치 규칙

- **자막이 명시된 경우에만** 자막 생성 (Visual Action 또는 Audio/Narration에 자막 내용이 있을 때)
  - 위치: 화면 좌우 중앙, 상하로는 하단 1/3 영역 (lower third)
  - 피사체(얼굴): 화면 상단~중앙에 배치하여 자막 공간 확보
  - 프롬프트에 포함: "Korean subtitle text positioned at horizontal center, lower third of the frame"
  - 자막이 얼굴을 가리지 않도록 구도 설계
- **자막이 명시되지 않은 경우**: 텍스트 없이 순수 이미지만 생성 (텍스트 오버레이 금지)
- 한글 시나리오의 경우 한글로 자막 노출

### 앱 인터페이스 금지 (절대 준수)

- TikTok, Instagram Reels, YouTube Shorts 등 앱 UI 요소 절대 포함 금지
- 금지 요소: 좋아요/댓글/공유 버튼, 프로필 아이콘, 팔로우 버튼, 음악 정보, 해시태그 오버레이, 진행 바, 타임스탬프
- 이미지는 순수한 영상 프레임만 표현 (앱 인터페이스 없는 깨끗한 화면)

### 피부 표현 가이드

- 피부는 시나리오에 맞게 표현하되, 기본적으로 건강하고 자연스러워야 함
- 미세한 피부결(fine texture)과 모공은 자연스럽게 보여도 됨
- 과도하게 매끄럽거나 플라스틱처럼 보이면 안됨 (AI 느낌 = 실패)
- pain_point 시나리오: 해당 문제가 자연스럽게 보이되 과도하게 강조하지 않음
- healthy/after 시나리오: 자연스러운 건강한 광택(healthy glow) OK

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
