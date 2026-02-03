# 시딩UGC (Seeding UGC) - 인플루언서 시딩용 UGC 콘텐츠 생성
> 공통 설정은 [`../SKILL.md`](../SKILL.md) 참조


# 시딩UGC - 인플루언서 시딩용 UGC 콘텐츠 생성


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

# 파이프라인 (7단계)

```
사용자 입력 → Step 1: 브랜드 라우팅 + 템플릿 로드
            → Step 2: AI 시나리오 판단 (scenario, skin_state, camera_style 자동 선택)
            → Step 2.5: VLM 제품 분석 (제품 레퍼런스 → 자동 묘사 생성)
            → Step 3: 프롬프트 조립 (UGC 리얼리즘 최우선 + 제품 분석 결과 주입)
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

## Step 2.5: VLM 제품 분석 (Product VLM Analysis)

**제품 레퍼런스 이미지가 있을 때**, VLM으로 제품을 먼저 분석하고 그 결과를 프롬프트에 주입합니다.
배경 교체 워크플로의 모델 물리 분석(VFX)과 동일한 패턴입니다.

> **왜 필요한가?** 수동으로 제품 설명을 작성하면 캡/바디 구분, 투명도, 로고 위치 등 세부 사항이 부정확해짐.
> VLM이 직접 이미지를 보고 분석하면 훨씬 정확한 제품 묘사가 가능.

### 분석 프롬프트

```python
PRODUCT_ANALYSIS_PROMPT = """You are a product photography expert.
Analyze these reference images of a cosmetic product in EXTREME detail.

Describe the following with precision:
1. OVERALL SHAPE: Exact shape, proportions (height vs width ratio), silhouette
2. MATERIALS: What is each part made of? Transparent? Opaque? Frosted? Glossy? Matte?
3. TWO-PART STRUCTURE:
   - CAP/TOP: Material, color, opacity, what's inside (applicator?), shape of cap top
   - BODY/BOTTOM: Material, color, opacity, what's visible through it, shape
4. COLORS: Exact colors of each part. Is color from the material or from liquid inside?
5. LOGO/TEXT: What text/logo is on it? Where exactly? On which part? What color/font?
6. PROPORTIONS: How tall vs wide? Cap-to-body ratio?
7. APPLICATOR: What type? Doe-foot? Brush? Where is it attached?
8. HOW IT'S USED: When you pull the cap off, what happens? What does the separated state look like?

Be extremely specific. This description will be used to generate accurate product images.
Output as structured text, NOT JSON."""
```

### 분석 함수

```python
def analyze_product(ref_images, api_key):
    """VLM으로 제품 레퍼런스 이미지를 분석하여 상세 묘사 생성"""
    client = genai.Client(api_key=api_key)

    parts = []
    for i, img in enumerate(ref_images):
        parts.append(types.Part(text=f"PRODUCT IMAGE {i+1}:"))
        parts.append(pil_to_part(img, max_size=1024))
    parts.append(types.Part(text=PRODUCT_ANALYSIS_PROMPT))

    response = client.models.generate_content(
        model="gemini-2.5-flash",  # VLM 분석은 텍스트 모델 사용
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(temperature=0.1)
    )
    return response.text  # 상세 제품 묘사 텍스트
```

### 분석 결과를 프롬프트에 주입

```python
# Step 3에서 프롬프트 조립 시:
product_analysis = analyze_product([ref_product, ref_holding, ref_pose], api_key)

# BASE_PROMPT 안에 플레이스홀더로 주입
prompt = BASE_PROMPT.replace("{product_analysis}", product_analysis)
```

### 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **분석 우선** | 수동 제품 설명 대신 VLM 자동 분석 결과를 사용 |
| **레퍼런스 다각도** | 제품 전체샷 + 들고 있는 샷 + 사용 포즈 등 2-3장 제공 |
| **캐싱** | 동일 제품 반복 생성 시 분석 결과 재사용 (1회 분석 → N회 생성) |
| **폴백** | 분석 실패 시 brand-dna의 products 섹션 수동 설명으로 폴백 |

### brand-dna products 섹션 연동

VLM 분석이 실패할 경우, `brand-dna/{brand}.json`의 `products` 섹션에 저장된 수동 제품 설명을 사용합니다.

```python
# 폴백 예시
if product_analysis is None:
    with open(f"brand-dna/{brand}.json") as f:
        brand_data = json.load(f)
    product_analysis = json.dumps(brand_data.get("products", {}), indent=2)
```

> **참고**: `banillaco.json`의 `products.b_lip_tint` 섹션에 캡/바디 구조, 사용법, AI 흔한 오류 등이 사전 정의되어 있음.
> 다른 브랜드/제품도 동일 포맷으로 `products` 섹션을 추가하면 자동 폴백 가능.

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

### UGC 검증 기준 (시나리오별 분기)

UGC는 시나리오에 따라 검증 기준이 다릅니다. 공통 구조(검증→진단→강화→재시도)는 동일하지만, 기준 항목과 가중치가 다릅니다.

#### A. 일반 시딩UGC (인플루언서 제공용)

| 기준 | 가중치 | 설명 | 통과 기준 |
|------|--------|------|-----------|
| UGC 리얼리즘 | 35% | 실제 폰 촬영처럼 보이는가? | ≥ 85 |
| 인물 보존 | 25% | 얼굴/체형 원본 일치 | = 100 |
| 시나리오 정합성 | 20% | 요청한 상황이 잘 표현되었는가? | ≥ 80 |
| 피부 상태 | 10% | skin_state가 정확히 반영되었는가? | ≥ 80 |
| Anti-Polish | 10% | 과도하게 깨끗/프로페셔널하지 않은가? | ≥ 80 |

#### B. 얼굴 참조 UGC (특정 모델 재현 — 로션/스킨케어 등)

참조 이미지의 동일 인물을 재현해야 하는 UGC에 사용합니다.

| 기준 | 가중치 | 설명 | 통과 기준 |
|------|--------|------|-----------|
| face_preservation (얼굴 보존) | 30% | 참조 이미지와 동일 인물인가? (골격, 이목구비) | ≥ 85 |
| framing_closeup (프레이밍) | 15% | 클로즈업 셀피, 얼굴이 프레임의 70-80% | ≥ 80 |
| ugc_realism (UGC 리얼리즘) | 15% | TikTok/Reels 스크린샷처럼 보이는가? | ≥ 85 |
| bare_face_accuracy (쌩얼 정확도) | 15% | 메이크업 없는 자연스러운 피부인가? | ≥ 85 |
| scene_accuracy (장면 정확도) | 10% | 요청한 장면(화장대, 루틴 등)이 정확한가? | ≥ 80 |
| skin_realism (피부 리얼리즘) | 15% | 모공, 질감, 아침 피부 등 자연스러운가? | ≥ 85 |

**PASS 조건**: 모든 항목 개별 통과 AND 가중합산 ≥ 90.0

### 판정 (Assessment) — 3단계

```
RELEASE_READY    → 전 항목 개별 통과 + 가중합산 ≥ 90  → 파이프라인 종료
NEEDS_REFINEMENT → 가중합산 ≥ 80                     → 진단 후 재시도
REGENERATE       → 가중합산 < 80                     → 진단 후 재시도
```

### Anti-Polish 체크리스트 (이것들이 보이면 감점)
- [ ] 링라이트 캐치라이트 → -20점
- [ ] 완벽한 피부 보정 → -25점
- [ ] 스튜디오 조명 느낌 → -20점
- [ ] 완벽한 구도/센터링 → -10점
- [ ] 프로 모델 포즈 → -15점
- [ ] 컬러그레이딩 느낌 → -10점

### VLM 검증 프롬프트 (얼굴 참조 UGC용)

```python
VALIDATION_PROMPT = """You are a professional UGC content quality inspector for a K-beauty brand.
Evaluate this AI-generated image. You are also given the ORIGINAL face reference image.

SCORE EACH CRITERION (0-100):

1. face_preservation: Does she look like the SAME PERSON as the reference?
   - 90-100: Identical face, same bone structure, same features
   - 60-89: Similar but noticeable differences
   - 0-59: Different person entirely

2. framing_closeup: Is this a close-up selfie?
   - 90-100: Face fills 70-80% of frame, selfie angle
   - 60-89: Face prominent but framing not quite right
   - 0-59: Wrong framing entirely

3. ugc_realism: Does it look like a REAL TikTok/Reels screenshot?
   - 90-100: Could fool someone into thinking it's real UGC
   - 60-89: Mostly realistic but some AI artifacts
   - 0-59: Obviously AI-generated

4. bare_face_accuracy: Is this truly a bare/no-makeup face?
   - 90-100: Clearly no makeup, natural pores/unevenness
   - 60-89: Mostly bare but some areas too perfect
   - 0-59: Clearly wearing makeup

5. scene_accuracy: Is the scene correct?
   - 90-100: Correct setting, props, lighting, pose
   - 60-89: Partially correct
   - 0-59: Wrong setting entirely

6. skin_realism: Does the skin look REAL?
   - 90-100: Natural pores, real texture
   - 60-89: Mostly okay but some areas too smooth
   - 0-59: Plastic, airbrushed, obviously AI

Return ONLY valid JSON:
{
  "scores": {
    "face_preservation": <int>,
    "framing_closeup": <int>,
    "ugc_realism": <int>,
    "bare_face_accuracy": <int>,
    "scene_accuracy": <int>,
    "skin_realism": <int>
  },
  "issues": ["issue1", "issue2"],
  "strengths": ["strength1", "strength2"]
}"""
```

### 실패 진단 (Diagnosis)

점수가 통과 기준 미만인 항목을 자동 감지하여 강화문구를 선택합니다.

#### A. 일반 시딩UGC 진단

| 진단명 | 트리거 | 강화 내용 |
|--------|--------|-----------|
| `ugc_too_polished` | UGC 리얼리즘 < 85 | "more raw, more authentic, less polished" |
| `anti_polish_fail` | Anti-Polish < 80 | negative prompt 강화 + "imperfect framing" |
| `skin_state_wrong` | 피부 상태 < 80 | skin_state 프롬프트 구체화 |

temperature 변경: 상향 (0.35 → 0.4 → 0.45) — 더 랜덤한 변형 유도

#### B. 얼굴 참조 UGC 진단

| 진단명 | 트리거 조건 | 강화 내용 |
|--------|------------|-----------|
| `face_wrong` | face_preservation < 85 | "MUST match reference EXACTLY — same eye shape, nose, lip shape, jawline, face proportions" |
| `framing_too_wide` | framing_closeup < 85 | "CLOSER FRAMING: Face must fill 75-85% of frame, phone at arm's length" |
| `too_polished` | ugc_realism < 85 | "MORE RAW AND AUTHENTIC — slight noise, imperfect framing, casual composition" |
| `has_makeup` | bare_face_accuracy < 85 | "ABSOLUTELY NO MAKEUP — visible pores, slight redness, undereye circles" |
| `wrong_scene` | scene_accuracy < 85 | "Korean apartment VANITY, skincare bottles, morning sunlight, lotion application pose" |

temperature 변경: 하향 (0.30 → 0.25 → 0.20 → 0.15) — 참조 이미지에 더 가깝게

```python
DIAGNOSIS_MAP = {
    "face_wrong": {
        "trigger": lambda s: s.get("face_preservation", 0) < 85,
        "enhancements": [
            "CRITICAL: The generated face MUST match the reference image EXACTLY",
            "Same eye shape, nose bridge, lip fullness, jawline, face width",
            "This is the SAME PERSON - not a similar-looking person"
        ]
    },
    "framing_too_wide": {
        "trigger": lambda s: s.get("framing_closeup", 0) < 85,
        "enhancements": [
            "CLOSER FRAMING: Face must fill 75-85% of frame",
            "This is a SELFIE - phone at arm's length, close to face",
            "Minimal background visible, face is the ENTIRE photo"
        ]
    },
    "too_polished": {
        "trigger": lambda s: s.get("ugc_realism", 0) < 85,
        "enhancements": [
            "MORE RAW AND AUTHENTIC - real phone video screenshot",
            "Add slight image noise, imperfect framing, casual composition",
            "NOT professional photography - real TikTok morning routine content"
        ]
    },
    "has_makeup": {
        "trigger": lambda s: s.get("bare_face_accuracy", 0) < 85,
        "enhancements": [
            "ABSOLUTELY NO MAKEUP - bare face only",
            "No foundation, no concealer, no eye makeup, no lip color",
            "Natural skin imperfections: visible pores, slight redness, undereye circles"
        ]
    },
    "wrong_scene": {
        "trigger": lambda s: s.get("scene_accuracy", 0) < 85,
        "enhancements": [
            "Setting must be a Korean apartment VANITY/DRESSING TABLE",
            "Skincare bottles visible in blurred background",
            "Morning sunlight from window, warm golden tone"
        ]
    }
}
```

### 프롬프트 강화 (Enhancement)

진단에서 선택된 강화문구를 기존 프롬프트 뒤에 주입합니다:

```python
def enhance_prompt(base_prompt, scores):
    enhancements = []
    for issue_name, diag in DIAGNOSIS_MAP.items():
        if diag["trigger"](scores):
            enhancements.extend(diag["enhancements"])

    if enhancements:
        enhancement_text = "\n".join(f"- {e}" for e in enhancements)
        return base_prompt + f"\n\n=== QUALITY REINFORCEMENT (auto-enhanced) ===\n{enhancement_text}"
    return base_prompt
```

### 스마트 재시도 (Auto-Retry) — 최대 4라운드

```
┌──────────┐
│ Round 1  │ temp=0.30, 원본 프롬프트
└────┬─────┘
     ↓ 검증 실패
┌──────────┐
│  진단    │ face_wrong 감지 (face=75 < 85)
└────┬─────┘
     ↓
┌──────────┐
│  강화    │ 프롬프트 + "MUST match reference EXACTLY..."
└────┬─────┘
     ↓
┌──────────┐
│ Round 2  │ temp=0.25, 강화 프롬프트
└────┬─────┘
     ↓ 검증 실패 (여전히 face < 85)
     ... Round 3, 4 반복 ...
     ↓
┌──────────┐
│  종료    │ 4라운드 후 최고 점수 이미지를 최종 결과로 저장
└──────────┘
```

```python
MAX_ROUNDS = 4
PASS_SCORE = 90.0

def run_ugc_pipeline():
    best_img, best_score, best_result = None, 0, None
    prompt = BASE_PROMPT
    temperature = 0.30

    for round_num in range(1, MAX_ROUNDS + 1):
        # 1. 생성
        img = generate_image(prompt, temperature=temperature)

        # 2. VLM 검증
        result = validate_image(img)
        scores = result["scores"]
        total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

        # 3. 판정
        all_pass = all(scores[k] >= PASS_THRESHOLDS[k] for k in PASS_THRESHOLDS)
        assessment = "RELEASE_READY" if (all_pass and total >= PASS_SCORE) else \
                     "NEEDS_REFINEMENT" if total >= 80 else "REGENERATE"

        # 4. 최고 점수 추적
        if total > best_score:
            best_score, best_img, best_result = total, img, result

        # 5. 통과 시 종료
        if assessment == "RELEASE_READY":
            break

        # 6. 진단 + 강화 (다음 라운드 준비)
        if round_num < MAX_ROUNDS:
            prompt = enhance_prompt(BASE_PROMPT, scores)
            temperature = max(0.15, temperature - 0.05)

    # 최종: 최고 점수 이미지 저장 + 검증 리포트 JSON 저장
    best_img.save("ugc_final.png")
    save_json("ugc_validation.json", best_result)
```

### 재시도 예시

```
[UGC] >> 로션 UGC 생성 파이프라인 시작

--- Round 1/4 (temp=0.30) ---
[GEN] Image generated: 1536x2752
[VAL] face_preservation: 75 [FAIL]
      framing_closeup: 95 [PASS]
      ugc_realism: 95 [PASS]
      bare_face_accuracy: 95 [PASS]
      scene_accuracy: 95 [PASS]
      skin_realism: 90 [PASS]
      TOTAL: 88.3
      ASSESSMENT: NEEDS_REFINEMENT
[DIAG] Issues: [face_wrong]
[DIAG] 프롬프트 강화: +얼굴 일치 키워드, temp 0.30→0.25

--- Round 2/4 (temp=0.25) ---
[GEN] Image generated: 1536x2752
[VAL] face_preservation: 80 [FAIL]
      TOTAL: 89.5
      ASSESSMENT: NEEDS_REFINEMENT
[DIAG] Issues: [face_wrong]
[DIAG] temp 0.25→0.20

--- Round 3/4 (temp=0.20) ---
[GEN] Image generated: 1536x2752
[VAL] face_preservation: 88 [PASS]
      TOTAL: 91.2
      ASSESSMENT: RELEASE_READY ✓

[PIPELINE] PASSED on round 3!
[FINAL] Best image saved to: ugc_final.png
[FINAL] Best score: 91.2
```

### 알려진 한계

| 한계 | 설명 | 대응 |
|------|------|------|
| 얼굴 보존 한계 | Gemini는 단일 참조 이미지로 정확한 얼굴 재현이 어려움 | 다각도 참조 이미지 추가, 얼굴 특징 텍스트 서술 강화 |
| temperature 딜레마 | 낮추면 참조에 가깝지만 다양성 감소, 올리면 UGC 느낌 좋지만 얼굴 이탈 | 시나리오별 최적 temperature 범위 설정 |
| 4라운드 한계 | API 비용과 시간 제약으로 무한 재시도 불가 | 4라운드 최고 점수 이미지를 수동 검토용으로 저장 |

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


---

**통합일**: 2026-02-03
**최종 업데이트**: 2026-02-03 (UGC 검증-진단-강화-재시도 파이프라인 상세 추가, 얼굴 참조 UGC 기준 신설)
**통합 출처**: brand-cut, background-swap, daily-casual, seeding-ugc
