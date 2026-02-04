---
name: 브랜드컷_brand-cut
description: 브랜드 패션 화보/에디토리얼 이미지 생성 통합 워크플로. 브랜드 라우팅 → DNA 로드 → 디렉터 페르소나 → 착장분석 → 프롬프트 조립 → 이미지 생성 → 검증까지 전체 파이프라인을 하나로 통합합니다.
user-invocable: true
argument-hint: [브랜드명] [스타일] [수량] (예: MLB 프리미엄 화보 5장)
---

# 브랜드컷 - 패션 에디토리얼 통합 워크플로

> **범용 레퍼런스**: Gemini API, 프롬프트 패턴, 배경 스타일, 유틸리티 함수 등
> 워크플로에 종속되지 않는 기초 지식은 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` 참조

## 사용법

```
/브랜드컷_brand-cut MLB 프리미엄 화보 5장
/브랜드컷_brand-cut Discovery 아웃도어 에디토리얼 3장
/브랜드컷_brand-cut Duvetica 럭셔리 에디토리얼 4장
/브랜드컷_brand-cut Banillaco 뷰티 셀피 3장
/브랜드컷_brand-cut SergioTacchini 레트로 화보 2장
```

### Python 워크플로 (API 연동용)

```python
from workflow import ImageGenerationWorkflow

workflow = ImageGenerationWorkflow(api_key="YOUR_API_KEY")

result = workflow.generate(
    user_input="MLB 프리미엄 화보 5장",
    # 또는 직접 지정
    # brand="mlb-marketing",
    # style="editorial",
    count=5,
    model_images=[face_pil1, face_pil2],  # 얼굴 유지용
    outfit_images=[outfit_pil1],           # 착장 반영용
    background_image=bg_pil,               # 배경 참조
    input_vars={"gender": "여성", "age": "20대 초반"},
    max_workers=4
)

print(f"생성 완료: {result['generated']}장")
for img in result['images']:
    img.save(f"output_{i}.png")
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   전체 파이프라인 (7단계)                                        ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

```
사용자 입력 → Step 1: 브랜드 라우팅
            → Step 2: 리소스 로드 (DNA + 디렉터 + 템플릿)
            → Step 3: 착장 분석 (VLM)
            → Step 4: 프롬프트 조립 (하이브리드 DX+JSON)
            → Step 4-B: Shot Card 시스템 (v2 프롬프트) ← NEW!
            → Step 5: 이미지 생성 (Gemini 3 Pro)
            → Step 6: 검증 (VLM 품질 판정)
            → Step 7: 스마트 재시도 (실패 이미지 자동 보정)
            → Step 8: 결과 반환

v1 경로: Step 1-2-3-4-5-6-7-8 (하이브리드 프롬프트)
v2 경로: Step 1-2-4B-5-6-7-8 (Shot Card 시스템, 착장 분석 스킵)
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 1: 브랜드 라우팅                                          ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

사용자 요청에서 브랜드를 감지하고 적합한 리소스를 매칭합니다.

## 브랜드 매칭 테이블

> 브랜드→DNA→디렉터 라우팅은 `CLAUDE.md`의 "브랜드 라우팅 테이블" 참조.

## 스타일 매칭 테이블

> 스타일→워크플로 라우팅은 `CLAUDE.md`의 "스타일 매칭" 참조.

## 참고: MLB 그래픽은 별도 워크플로

MLB 그래픽 (Shawn Stussy)은 **그래픽 디자인/제품 개발** 용도로, 화보컷 워크플로인 브랜드컷과는 다릅니다.
- MLB 화보컷 → 이 스킬 (브랜드컷 + Tyrone Lebon)
- MLB 그래픽 디자인 → `(MLB그래픽)_스트릿레전드_shawn-stussy` 스킬 별도 사용

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 2: 리소스 로드                                            ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 로드할 리소스 3종

```python
# 1. Brand DNA JSON 로드
brand_dna = load_json(f".claude/skills/brand-dna/{brand}.json")

# 2. 디렉터 페르소나 스킬 로드 (별도 파일 참조)
director = load_skill(f".claude/skills/{director_persona_folder}/SKILL.md")

# 3. 스타일 템플릿 선택
template = load_json(f".claude/skills/prompt-templates/{style}.json")
```

### 디렉터 페르소나 파일 위치 (참조용)

| 브랜드 | 디렉터 페르소나 경로 |
|--------|---------------------|
| MLB 마케팅 | `.claude/skills/(MLB마케팅)_시티미니멀_tyrone-lebon/SKILL.md` |
| Discovery | `.claude/skills/(Discovery)_테크니컬유틸리티_yosuke-aizawa/SKILL.md` |
| Duvetica | `.claude/skills/(Duvetica)_럭셔리장인_brunello-cucinelli/SKILL.md` |
| Sergio Tacchini | `.claude/skills/(SergioTacchini)_실루엣혁명_hedi-slimane/SKILL.md` |
| Banillaco | `.claude/skills/(Banillaco)_맑은뷰티_ahn-joo-young/SKILL.md` |
| 제품연출 (전 브랜드) | `.claude/skills/(제품연출)_한국힙이커머스_musinsa-29cm/SKILL.md` |

### Brand DNA JSON 위치

```
.claude/skills/brand-dna/
├── _index.json          # 라우팅 테이블
├── mlb-marketing.json   # MLB 마케팅 DNA
├── mlb-graphic.json     # MLB 그래픽 DNA
├── discovery.json       # Discovery DNA
├── duvetica.json        # Duvetica DNA
├── sergio-tacchini.json # Sergio Tacchini DNA
└── banillaco.json       # Banillaco DNA
```

### DNA + 템플릿 병합

```python
brand_dna = load_json(f"brand-dna/{brand}.json")
template = load_json(f"prompt-templates/{style}.json")

# 템플릿에 DNA 값 주입
final_prompt = template["prompt_builder"].format(**brand_dna)
negative = template["negative_prompt"] + brand_dna.get("forbidden_keywords", [])
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 3: 착장 분석 (VLM)                                       ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

착장 이미지에서 **이미지 생성 AI가 놓치기 쉬운 차별적 디테일**만 선별 추출합니다.

## 분석 프롬프트

```python
ANALYSIS_PROMPT = """당신은 패션 제품의 '차별적 디테일'만 찾아내는 선별적 분석가입니다.

아이템 제외 필터 (Strict Exclusion):
- 기본 무지 아이템: 로고, 그래픽, 특수 마감, 독특한 핏이 없는 평범한 아이템은 분석 생략
- 특이사항 없음: 브랜드 로고가 보이지 않고, 일반적인 레귤러 핏이며, 부자재 디테일이 전무한 경우

분석 집중 대상 (High Priority):
1. 변형된 실루엣: 벌룬핏, 가오리핏, 비대칭 커팅, 익스트림 크롭
2. 미세 부자재: 배색 스티치, 빈티지 워싱, 2-way 지퍼, 로고 각인 단추
3. 로고/그래픽 좌표: 브랜드 아이덴티티 위치 (정확한 상대적 좌표 필수)
4. 소재의 질감: 시어, 슬러브, 헤어리, 코팅 가공 등 시각적 특성

출력 포맷 (JSON):
{
  "detected_items": [
    {
      "category": "아이템명",
      "brand": { "name": "브랜드명", "logo_pos": "좌표", "type": "형태" },
      "blind_spot": ["놓치기 쉬운 디테일 2~3개"],
      "spec": { "fit": "실루엣", "shoulder": "어깨 구조", "finishing": "마감" },
      "texture": "시각적 재질 특성"
    }
  ]
}
"""
```

## 분석 함수

```python
import json
from google import genai
from google.genai import types
from PIL import Image

def analyze_fashion_image(image_pil: Image.Image, api_key: str) -> dict:
    """
    이미지에서 유의미한 패션 디테일만 선별적으로 추출

    Returns:
        {"status": "success"|"skipped"|"error", "data": [...]}
    """
    client = genai.Client(api_key=api_key)

    # 효율적인 분석을 위한 다운샘플링 (512px)
    max_size = 512
    if max(image_pil.size) > max_size:
        image_pil.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[types.Content(role="user", parts=[
                types.Part(text=ANALYSIS_PROMPT), image_pil
            ])],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=800,
                response_mime_type="application/json"
            )
        )

        result = json.loads(response.text)
        detected = result.get("detected_items", [])

        if not detected:
            return {"status": "skipped", "data": []}
        return {"status": "success", "data": detected}

    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## 분석 결과를 프롬프트에 통합

```python
def build_clothing_prompt(base_prompt: str, clothing_analysis: dict) -> str:
    """착장 분석 결과를 프롬프트에 통합"""
    garment = clothing_analysis.get("garments", [{}])[0]
    if not garment:
        garment = clothing_analysis.get("detected_items", [{}])[0]

    category = garment.get("main_category", garment.get("category", "garment"))
    sub_category = garment.get("sub_category", "")
    fit = garment.get("fit", garment.get("spec", {}).get("fit", "regular"))

    colors = garment.get("colors", {})
    primary_color = colors.get("primary", "")

    key_details = garment.get("key_details", [])
    blind_spots = garment.get("blind_spot", [])

    brand = garment.get("brand", {})

    # 디테일 문자열 생성
    details_list = []
    for d in key_details:
        if d.get('type'):
            details_list.append(f"- {d.get('type')}: {d.get('location', '')} ({d.get('style', d.get('visibility', ''))})")
    for bs in blind_spots:
        details_list.append(f"- CRITICAL: {bs}")

    details_str = "\n".join(details_list) if details_list else "- No special details"

    return f"""
Based on the reference garment image, generate a photo where the model wears this EXACT garment.

## GARMENT SPECIFICATIONS (MUST MATCH EXACTLY):
- Category: {sub_category} ({category})
- Fit: {fit}
- Primary Color: {primary_color}

## KEY DETAILS TO PRESERVE (CRITICAL):
{details_str}

## BRAND/LOGO (DO NOT MODIFY OR REMOVE):
- Brand: {brand.get('detected', brand.get('name', 'unknown'))}
- Logo Location: {brand.get('logo_location', brand.get('logo_pos', 'unknown'))}

## CRITICAL INSTRUCTIONS:
1. The garment must be IDENTICAL to the reference image
2. DO NOT modify, simplify, or remove any logos or branding
3. Preserve exact color tones and fabric texture
4. Maintain all visible features (hood, zipper, pockets, etc.)

## SCENE DESCRIPTION:
{base_prompt}
"""
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 4: 프롬프트 조립 (하이브리드 DX+JSON)                    ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

> **프롬프트 템플릿, 배경 스타일, 유틸리티 함수는 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` 참조.**
> 여기서는 브랜드컷 워크플로에서의 **조립 순서**만 정의합니다.

## 브랜드컷 프롬프트 조립 순서

1. **하이브리드 베이스 생성** - `build_hybrid_prompt(style_key)` 또는 `build_simple_hybrid_prompt(background, mood)` 호출
2. **브랜드 DNA 주입** - `build_brand_prompt(base, brand)` 로 브랜드 키워드/색감/무드 적용
3. **착장 디테일 추가** - Step 3의 VLM 분석 결과를 프롬프트에 반영
4. **디렉터 페르소나 적용** - 해당 디렉터의 DO/DON'T, 키워드, 무드를 최종 프롬프트에 주입
5. **최종 조립** - `build_full_prompt(background_style, brand, clothing_analysis, mood)`

### 브랜드컷 전용 조립 규칙

- 디렉터 페르소나의 `forbidden_keywords`는 반드시 negative prompt에 포함
- 브랜드 DNA의 `color_temperature`를 lighting 섹션에 반영
- 착장 분석에서 추출한 `distinctive_details`만 프롬프트에 포함 (기본 무지 아이템은 생략)

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 4-B: Shot Card 시스템 (v2 프롬프트)                       ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

> **작성일**: 2026-02-04
> **테스트 결과**: v1 대비 포즈 다양성, 눈 크기, 의상 표현력, 색감 일관성 모두 개선 확인
> **검증 상태**: 3개 shot 생성 성공 (chair_power, floor_gaze, extreme_closeup_fierce)

## 개요

Shot Card System은 **포즈/표정/앵글을 VLM으로 사전 분석한 카탈로그(pose_library.json)**와
**구조화된 Key-Value 프롬프트 포맷**을 결합하여, v1의 제너릭한 결과물을 극복하는 v2 워크플로입니다.

### v1 vs v2 비교

| 항목 | v1 (기존 하이브리드) | v2 (Shot Card) |
|------|---------------------|----------------|
| **포즈 다양성** | 서있기/걷기 반복 | 의자, 바닥, 클로즈업 등 다양 |
| **눈 크기** | 작고 찡그림 | 크고 또렷 (개선) |
| **의상 누락** | 2-3벌 누락 빈번 | 전체 아이템 표현 |
| **색감** | 따뜻한/뉴트럴 톤 | 쿨톤 일관성 |
| **구도** | 제너릭 풀바디 | 다양한 앵글/프레이밍 |
| **프롬프트 형식** | Prose (문장) | Key-Value (구조화) |
| **참조 이미지** | 랜덤 할당 | 14-slot 전략적 배치 |

---

## Step 4-B-1: pose_library.json 구조

### 파일 위치
```
.claude/skills/prompt-templates/pose_library.json
```

### 생성 방법
```bash
python analyze_style_library.py
```

38개의 MLB 스타일 참조 이미지를 Gemini 2.5 Flash VLM으로 분석하여 생성.

### 엔트리 구조

```json
{
  "id": "S100",
  "pose_type": "sitting, powerful crossed-legs",
  "body_description": "Full body: seated on black leather chair, left leg crossed over right at knee. Torso upright with slight lean back, right arm rests on chair arm, left hand on left knee. Head centered with slight downward tilt.",
  "weight_distribution": "centered on seat, balanced between both hips",
  "legs": "left leg crossed over right at knee, both feet flat on floor (right heel lifted slightly)",
  "arms_hands": "right arm rests on chair arm naturally, left hand rests on left knee palm down",
  "head_tilt": "slight downward (5-10 degrees)",
  "torso_angle": "upright with slight backward lean (~10 degrees)",
  "expression_type": "neutral, composed",
  "eyes": "direct gaze to camera, calm, slightly narrowed",
  "mouth": "closed, relaxed",
  "expression_energy": "low-medium (confident but understated)",
  "framing": "full body",
  "camera_angle": "eye-level, straight on",
  "estimated_lens": "50mm equivalent (normal)",
  "environment_interaction": "seated on chair, natural posture",
  "background_type": "plain white studio backdrop, minimalist",
  "outfit_items_visible": [
    "black bomber jacket (opened)",
    "white inner tee (visible at collar)",
    "light wash jeans",
    "white sneakers",
    "black cap with white logo"
  ],
  "color_temperature": "cool neutral (white backdrop, natural skin tones)",
  "lighting_direction": "frontal soft diffused",
  "editorial_boldness": 5,
  "tags": ["sitting", "chair", "crossed-legs", "powerful-stance", "direct-gaze", "minimalist", "studio", "full-body", "neutral-expression"]
}
```

### 주요 필드 설명

| 필드 | 설명 | 활용 |
|------|------|------|
| `id` | 포즈 고유 ID (S001~S145) | Shot card에서 참조 |
| `pose_type` | 포즈 한 줄 요약 | 프롬프트 헤더 |
| `body_description` | 상세 신체 포지션 | 프롬프트 POSE 섹션 |
| `expression_type` | 표정 타입 | EXPRESSION 섹션 |
| `eyes`, `mouth` | 눈/입 디테일 | 표정 재현 |
| `framing` | 프레이밍 (full-body/upper-body/closeup) | FRAMING 섹션 |
| `camera_angle` | 카메라 앵글 | FRAMING 섹션 |
| `outfit_items_visible` | 보이는 의상 아이템 목록 | OUTFIT 섹션 |
| `editorial_boldness` | 에디토리얼 대담함 (1-10) | 스타일 강도 조절 |
| `tags` | 검색 태그 | 포즈 검색/필터링 |

---

## Step 4-B-2: Shot Card JSON 구조

### Shot Card 정의

하나의 생성 샷(shot)에 필요한 모든 정보를 담은 JSON 객체.

```json
{
  "shot_id": "chair_power",
  "pose_id": "S100",
  "expression_override": {
    "eyes": "large almond eyes, wide open, intense direct gaze",
    "mouth": "closed, subtle confident smirk",
    "energy": "medium-high (confident swagger)"
  },
  "framing_override": {
    "type": "full body",
    "camera_angle": "eye-level, straight on",
    "lens": "50mm"
  },
  "outfit_items": [
    {
      "label": "black bomber jacket",
      "state": "opened, relaxed fit",
      "ref_file": "mlb_style/bomber_01.jpg"
    },
    {
      "label": "white inner tee",
      "state": "visible at collar",
      "ref_file": null
    },
    {
      "label": "light wash jeans",
      "state": "regular fit",
      "ref_file": "mlb_style/jeans_02.jpg"
    },
    {
      "label": "white sneakers",
      "state": "clean, laced",
      "ref_file": "mlb_style/sneakers_03.jpg"
    },
    {
      "label": "black cap with white MLB logo",
      "state": "worn forward",
      "ref_file": "mlb_style/cap_04.jpg"
    }
  ],
  "face_refs": [0, 1, 2],
  "style_refs": ["mlb_editorial_01.jpg", "mlb_editorial_02.jpg"],
  "background": "plain white studio backdrop, minimalist, no texture",
  "lighting": "frontal soft diffused, even skin lighting, no harsh shadows"
}
```

### Shot Card 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| `shot_id` | Yes | 샷 고유 ID (사람이 읽을 수 있는 이름) |
| `pose_id` | Yes | pose_library.json의 id 참조 (예: "S100") |
| `expression_override` | No | 표정 오버라이드 (pose의 기본 표정 대신 사용) |
| `framing_override` | No | 프레이밍 오버라이드 (pose의 기본 프레이밍 대신 사용) |
| `outfit_items` | Yes | 의상 아이템 목록 (각 아이템은 label/state/ref_file) |
| `face_refs` | Yes | 얼굴 참조 이미지 인덱스 (MLB_KARINA 디렉토리 내) |
| `style_refs` | No | 스타일 참조 이미지 파일명 목록 |
| `background` | Yes | 배경 설명 |
| `lighting` | Yes | 조명 설명 |

---

## Step 4-B-3: 구조화 Key-Value 프롬프트 포맷

v1의 prose 스타일 프롬프트 대신, **명확한 섹션 헤더와 key: value 쌍**으로 구성.

### 포맷 예시

```
---GENERATION DIRECTIVE---

type: ultra_photorealistic_fashion_editorial
quality: 8k, maximum detail, professional photography
reference_fidelity: CRITICAL - follow all reference images EXACTLY

---POSE DETAILS (from pose_library S100)---
Full body: seated on black leather chair, left leg crossed over right at knee.
Torso upright with slight lean back, right arm rests on chair arm, left hand on left knee.
Head centered with slight downward tilt.

weight_distribution: centered on seat, balanced between both hips
legs: left leg crossed over right at knee, both feet flat on floor (right heel lifted slightly)
arms_hands: right arm rests on chair arm naturally, left hand rests on left knee palm down
head_tilt: slight downward (5-10 degrees)
torso_angle: upright with slight backward lean (~10 degrees)

---FRAMING---
type: full body
camera_angle: eye-level, straight on
lens: 50mm equivalent (normal perspective)

---EXPRESSION---
CRITICAL: LARGE ALMOND EYES, WIDE OPEN, INTENSE DIRECT GAZE
eyes: large almond eyes, wide open, intense direct gaze
mouth: closed, subtle confident smirk
energy: medium-high (confident swagger)

---OUTFIT (MANDATORY - ALL 5 ITEMS MUST BE VISIBLE)---
1. [MANDATORY] black bomber jacket - opened, relaxed fit
2. [MANDATORY] white inner tee - visible at collar
3. [MANDATORY] light wash jeans - regular fit
4. [MANDATORY] white sneakers - clean, laced
5. [MANDATORY] black cap with white MLB logo - worn forward

CRITICAL: All 5 items above MUST appear in the final image. NO substitutions.

---BACKGROUND---
plain white studio backdrop, minimalist, no texture

---LIGHTING---
frontal soft diffused, even skin lighting, no harsh shadows

---COLOR TEMPERATURE---
cool neutral tones, white backdrop, natural skin tones

---SKIN---
natural skin texture with visible pores, subtle imperfections, realistic subsurface scattering
NO plastic skin, NO waxy appearance, NO airbrushed look

---FORBIDDEN---
warm tones, golden hour, graffiti, dirty backgrounds, extra fingers, plastic skin, text overlays

---STYLE---
MLB Marketing Editorial in the style of Tyrone Lebon - The Old Money Rebel
```

### v1 Prose 스타일과 비교

**v1 (Prose)**:
```
Generate an ultra photorealistic fashion editorial image featuring a young
adult woman in her mid-20s seated on a black leather chair with her left
leg crossed over her right. She should wear a black bomber jacket (opened),
white inner tee, light wash jeans, white sneakers, and a black cap with
white MLB logo. Her expression should be neutral with a direct gaze to the
camera. The background should be a plain white studio backdrop...
```

→ AI가 문장을 파싱하며 디테일을 놓침. 의상 누락 빈번.

**v2 (Key-Value)**:
```
---OUTFIT (MANDATORY - ALL 5 ITEMS MUST BE VISIBLE)---
1. [MANDATORY] black bomber jacket - opened, relaxed fit
2. [MANDATORY] white inner tee - visible at collar
3. [MANDATORY] light wash jeans - regular fit
4. [MANDATORY] white sneakers - clean, laced
5. [MANDATORY] black cap with white MLB logo - worn forward

CRITICAL: All 5 items above MUST appear in the final image. NO substitutions.
```

→ 명확한 체크리스트. 누락 방지.

---

## Step 4-B-4: Reference Image Allocation (14-slot 전략)

Gemini API는 최대 약 14개의 이미지를 동시에 입력 가능 (모델에 따라 다름, 안전하게 14개로 제한).

### 우선순위 순서

| 우선순위 | 타입 | 개수 | 설명 |
|---------|------|------|------|
| 1 | Pose Reference | 1 | pose_id에 해당하는 포즈 이미지 (필수) |
| 2 | Face References | 2-4 | 얼굴 참조 (최소 2개, 권장 3개) |
| 3 | Outfit References | N | outfit_items에 ref_file 지정된 아이템 (전부 포함 필수) |
| 4 | Style References | 0-2 | 분위기 참조 (슬롯 남으면 포함) |

### Allocation 로직

```python
def allocate_references(shot_card: dict, pose_library: dict, max_slots: int = 14) -> list:
    """
    14-slot 전략에 따라 참조 이미지 할당

    Returns:
        List of (image_pil, label) tuples
    """
    refs = []

    # 1. Pose reference (최우선)
    pose_id = shot_card["pose_id"]
    pose_data = pose_library.get(pose_id)
    if pose_data and pose_data.get("image_file"):
        pose_img = Image.open(pose_data["image_file"])
        refs.append((pose_img, f"[POSE REFERENCE - Generate EXACTLY this pose]: {pose_id}"))

    # 2. Face references (2-4개)
    face_indices = shot_card.get("face_refs", [])
    for idx in face_indices[:4]:  # 최대 4개
        face_img = load_face_ref(idx)  # MLB_KARINA/{idx}.jpg
        refs.append((face_img, f"[FACE REFERENCE {idx+1} - Preserve facial features EXACTLY]:\nCRITICAL: LARGE ALMOND EYES, WIDE OPEN"))

    # 3. Outfit references (전부 포함 필수)
    for item in shot_card.get("outfit_items", []):
        ref_file = item.get("ref_file")
        if ref_file:
            outfit_img = Image.open(ref_file)
            refs.append((outfit_img, f"[OUTFIT REFERENCE - {item['label']}]: {item['state']}"))

    # 4. Style references (슬롯 남으면)
    remaining_slots = max_slots - len(refs)
    style_files = shot_card.get("style_refs", [])
    for style_file in style_files[:remaining_slots]:
        style_img = Image.open(style_file)
        refs.append((style_img, "[STYLE REFERENCE - Overall mood and color grading]:"))

    return refs[:max_slots]
```

### Reference Label 전략

각 참조 이미지에는 **명확한 역할 라벨**을 붙임.

| 타입 | 라벨 예시 |
|------|----------|
| Pose | `[POSE REFERENCE - Generate EXACTLY this pose]: S100` |
| Face | `[FACE REFERENCE 1 - Preserve facial features EXACTLY]:\nCRITICAL: LARGE ALMOND EYES, WIDE OPEN` |
| Outfit | `[OUTFIT REFERENCE - black bomber jacket]: opened, relaxed fit` |
| Style | `[STYLE REFERENCE - Overall mood and color grading]:` |

---

## Step 4-B-5: build_prompt_parts() 순서

```python
def build_prompt_parts(shot_card: dict, pose_library: dict) -> list:
    """
    Shot card에서 multimodal parts 생성 (text + images)

    Returns:
        List of types.Part (text or inline_data)
    """
    parts = []

    # 1. Structured text prompt
    text_prompt = build_structured_prompt(shot_card, pose_library)
    parts.append(types.Part.from_text(text_prompt))

    # 2. References (14-slot allocation)
    refs = allocate_references(shot_card, pose_library, max_slots=14)

    for img_pil, label in refs:
        # Label as text
        parts.append(types.Part.from_text(label))
        # Image as inline data
        parts.append(pil_to_part(img_pil))

    return parts
```

### Parts 순서 Diagram

```
[Text Prompt]
  ↓
[Pose Label] → [Pose Image]
  ↓
[Face Label 1] → [Face Image 1]
  ↓
[Face Label 2] → [Face Image 2]
  ↓
[Face Label 3] → [Face Image 3]
  ↓
[Outfit Label 1] → [Outfit Image 1]
  ↓
[Outfit Label 2] → [Outfit Image 2]
  ↓
...
  ↓
[Style Label 1] → [Style Image 1]
  ↓
[Style Label 2] → [Style Image 2]
```

---

## Step 4-B-6: build_structured_prompt() 함수

```python
def build_structured_prompt(shot_card: dict, pose_library: dict) -> str:
    """
    Shot card + pose_library에서 구조화 Key-Value 프롬프트 생성
    """
    pose_id = shot_card["pose_id"]
    pose_data = pose_library.get(pose_id, {})

    # Expression override
    expr = shot_card.get("expression_override", {})
    eyes = expr.get("eyes", pose_data.get("eyes", "neutral"))
    mouth = expr.get("mouth", pose_data.get("mouth", "closed"))
    energy = expr.get("energy", pose_data.get("expression_energy", "medium"))

    # Framing override
    frame = shot_card.get("framing_override", {})
    framing_type = frame.get("type", pose_data.get("framing", "full body"))
    camera_angle = frame.get("camera_angle", pose_data.get("camera_angle", "eye-level"))
    lens = frame.get("lens", pose_data.get("estimated_lens", "50mm"))

    # Outfit checklist
    outfit_items = shot_card.get("outfit_items", [])
    outfit_lines = []
    for i, item in enumerate(outfit_items, 1):
        outfit_lines.append(f"{i}. [MANDATORY] {item['label']} - {item['state']}")

    outfit_str = "\n".join(outfit_lines)

    # Background, Lighting
    bg = shot_card.get("background", "neutral background")
    lighting = shot_card.get("lighting", "soft diffused")

    # Assemble
    prompt = f"""---GENERATION DIRECTIVE---

type: ultra_photorealistic_fashion_editorial
quality: 8k, maximum detail, professional photography
reference_fidelity: CRITICAL - follow all reference images EXACTLY

---POSE DETAILS (from pose_library {pose_id})---
{pose_data.get('body_description', 'standard pose')}

weight_distribution: {pose_data.get('weight_distribution', 'balanced')}
legs: {pose_data.get('legs', 'natural stance')}
arms_hands: {pose_data.get('arms_hands', 'relaxed at sides')}
head_tilt: {pose_data.get('head_tilt', 'neutral')}
torso_angle: {pose_data.get('torso_angle', 'upright')}

---FRAMING---
type: {framing_type}
camera_angle: {camera_angle}
lens: {lens}

---EXPRESSION---
CRITICAL: LARGE ALMOND EYES, WIDE OPEN, INTENSE DIRECT GAZE
eyes: {eyes}
mouth: {mouth}
energy: {energy}

---OUTFIT (MANDATORY - ALL {len(outfit_items)} ITEMS MUST BE VISIBLE)---
{outfit_str}

CRITICAL: All {len(outfit_items)} items above MUST appear in the final image. NO substitutions.

---BACKGROUND---
{bg}

---LIGHTING---
{lighting}

---COLOR TEMPERATURE---
cool neutral tones, natural skin tones

---SKIN---
natural skin texture with visible pores, subtle imperfections, realistic subsurface scattering
NO plastic skin, NO waxy appearance, NO airbrushed look

---FORBIDDEN---
warm tones, golden hour, graffiti, dirty backgrounds, extra fingers, plastic skin, text overlays

---STYLE---
MLB Marketing Editorial in the style of Tyrone Lebon - The Old Money Rebel
"""

    return prompt
```

---

## Step 4-B-7: 샷 카드 기반 생성 스크립트

### 파일: `generate_brandcut_v2.py`

```python
from google import genai
from google.genai import types
from PIL import Image
import json

def load_pose_library(path: str = ".claude/skills/prompt-templates/pose_library.json") -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {entry["id"]: entry for entry in data}

def generate_from_shot_card(
    shot_card: dict,
    pose_library: dict,
    api_key: str,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: str = "3:4",
    image_size: str = "2K",
    temperature: float = 0.2
) -> Image.Image:
    """Shot card 기반 이미지 생성"""

    client = genai.Client(api_key=api_key)

    # 1. Build prompt parts
    parts = build_prompt_parts(shot_card, pose_library)

    # 2. Generate
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
    )

    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config
    )

    # 3. Extract image
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                img_bytes = part.inline_data.data
                return Image.open(io.BytesIO(img_bytes))

    raise ValueError("No image generated")

# Example usage
if __name__ == "__main__":
    pose_lib = load_pose_library()

    shot = {
        "shot_id": "chair_power",
        "pose_id": "S100",
        "expression_override": {
            "eyes": "large almond eyes, wide open, intense direct gaze",
            "mouth": "closed, subtle confident smirk",
            "energy": "medium-high (confident swagger)"
        },
        "outfit_items": [
            {"label": "black bomber jacket", "state": "opened", "ref_file": "ref/bomber.jpg"},
            {"label": "white inner tee", "state": "visible", "ref_file": None},
            {"label": "light wash jeans", "state": "regular fit", "ref_file": "ref/jeans.jpg"},
            {"label": "white sneakers", "state": "clean", "ref_file": "ref/sneakers.jpg"},
            {"label": "black cap", "state": "worn forward", "ref_file": "ref/cap.jpg"}
        ],
        "face_refs": [0, 1, 2],
        "style_refs": ["mlb_01.jpg", "mlb_02.jpg"],
        "background": "plain white studio backdrop",
        "lighting": "frontal soft diffused"
    }

    result_img = generate_from_shot_card(shot, pose_lib, api_key=os.getenv("GEMINI_API_KEY"))
    result_img.save("output_chair_power.png")
```

---

## Step 4-B-8: 검증된 Shot 예시

### 2026-02-04 테스트 결과

3개 shot 생성 완료, 모두 v1 대비 개선 확인:

| Shot ID | Pose ID | 특징 | v1 대비 개선 |
|---------|---------|------|-------------|
| `chair_power` | S100 | 의자에 앉아 다리 꼬기, 정면 응시 | 포즈 정확도 ↑, 의상 전부 표현 ↑ |
| `floor_gaze` | S099 | 바닥에 앉아 시선 아래, 편안한 포즈 | 눈 크기 ↑, 색감 쿨톤 유지 ↑ |
| `extreme_closeup_fierce` | S096 | 극단적 클로즈업, 강렬한 표정 | 표정 디테일 ↑, 플라스틱 피부 감소 ↑ |

### Shot Card Template (chair_power)

```json
{
  "shot_id": "chair_power",
  "pose_id": "S100",
  "expression_override": {
    "eyes": "large almond eyes, wide open, intense direct gaze",
    "mouth": "closed, subtle confident smirk",
    "energy": "medium-high (confident swagger)"
  },
  "framing_override": {
    "type": "full body",
    "camera_angle": "eye-level, straight on",
    "lens": "50mm"
  },
  "outfit_items": [
    {
      "label": "black bomber jacket",
      "state": "opened, relaxed fit",
      "ref_file": "mlb_style/bomber_01.jpg"
    },
    {
      "label": "white inner tee",
      "state": "visible at collar",
      "ref_file": null
    },
    {
      "label": "light wash jeans",
      "state": "regular fit",
      "ref_file": "mlb_style/jeans_02.jpg"
    },
    {
      "label": "white sneakers",
      "state": "clean, laced",
      "ref_file": "mlb_style/sneakers_03.jpg"
    },
    {
      "label": "black cap with white MLB logo",
      "state": "worn forward",
      "ref_file": "mlb_style/cap_04.jpg"
    }
  ],
  "face_refs": [0, 1, 2],
  "style_refs": ["mlb_editorial_01.jpg", "mlb_editorial_02.jpg"],
  "background": "plain white studio backdrop, minimalist, no texture",
  "lighting": "frontal soft diffused, even skin lighting, no harsh shadows"
}
```

---

## Step 4-B-9: v2 워크플로 전체 흐름

```
1. Shot Card 준비 (JSON)
   ↓
2. pose_library.json 로드
   ↓
3. build_structured_prompt(shot_card, pose_library)
   → 구조화 Key-Value 텍스트 프롬프트 생성
   ↓
4. allocate_references(shot_card, pose_library, max_slots=14)
   → 우선순위에 따라 참조 이미지 할당 (pose > face > outfit > style)
   ↓
5. build_prompt_parts(shot_card, pose_library)
   → [Text, Pose, Face1, Face2, Face3, Outfit1, Outfit2, ..., Style1, Style2] parts 조립
   ↓
6. generate_content(model="gemini-3-pro-image-preview", contents=parts, config=...)
   → Gemini API 호출 (aspect_ratio=3:4, image_size=2K, temperature=0.2)
   ↓
7. 결과 이미지 추출
   ↓
8. VLM 검증 (Step 6 그대로 적용)
   ↓
9. 필요시 재시도 (Step 7 그대로 적용)
```

---

## Step 4-B-10: v1과 v2 선택 가이드

| 상황 | 권장 버전 |
|------|----------|
| 포즈/앵글이 정해져 있고, 정확히 재현해야 함 | **v2 (Shot Card)** |
| 38개 포즈 라이브러리 중 하나를 선택 가능 | **v2** |
| 의상이 3개 이상이고 누락 없이 전부 표현해야 함 | **v2** |
| 얼굴 크기/눈 크기 문제 (작게 나오는 경우) | **v2** (LARGE EYES 명시) |
| 색감 일관성이 중요 (쿨톤/웜톤 명확히) | **v2** (KEY-VALUE로 명시) |
| 빠른 프로토타입, 포즈는 자유 | **v1 (하이브리드)** |
| 참조 이미지 없이 텍스트만으로 생성 | **v1** |
| 착장 분석(VLM)이 필요한 경우 | **v1** (Step 3 포함) |

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 5: 이미지 생성 (Gemini 3 Pro)                            ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

> **모델/해상도/Temperature 절대 규칙은 `CLAUDE.md` 참조.**
> **API 코드 패턴, 유틸리티 함수는 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` 참조.**
> 여기서는 브랜드컷 워크플로에서의 **생성 실행 로직**만 정의합니다.

## 브랜드컷 생성 실행 순서

1. **API 클라이언트 초기화** - `get_next_api_key()`로 키 로테이션
2. **참조 이미지 준비** - 얼굴/착장/배경 이미지를 `pil_to_part()`로 변환
3. **프롬프트 파츠 조립** - `[text_part, face_part, outfit_part, ...]` 순서
4. **생성 호출** - `call_gemini_with_retry()` 사용, 브랜드컷 기본 설정:
   - model: `gemini-3-pro-image-preview`
   - aspect_ratio: `3:4` (에디토리얼) / `9:16` (셀피)
   - resolution: `2K`
   - temperature: `0.2` (참조 보존) ~ `0.3` (자유 생성)
5. **결과 저장** - `save_image(pil_img, prefix, brand, workflow)` 사용

## 병렬 생성 (다수 이미지)

```python
from concurrent.futures import ThreadPoolExecutor

def generate_batch(prompts: list, max_workers: int = 4):
    """브랜드컷 배치 생성 - 키 로테이션으로 rate limit 분산"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(call_gemini_with_retry, p) for p in prompts]
        return [f.result() for f in futures]
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 6: 브랜드컷 품질 검증                                     ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 브랜드컷 검증 기준

⚠️ 브랜드컷은 **처음부터 생성**하는 워크플로이므로, 배경교체의 "원본 보존" 검증과는 완전히 다릅니다.
**생성된 이미지 자체의 퀄리티**를 평가합니다.

### 검증 항목 (6가지)

| 항목 | 설명 | 가중치 | 통과 기준 |
|------|------|--------|-----------|
| **photorealism** | 포토리얼리즘 (실제 사진처럼 보이는지) | **25%** | ≥ 85 |
| **anatomy** | 해부학적 정확성 (손가락, 비율, 관절, 얼굴) | **20%** | ≥ 90 |
| **brand_compliance** | 브랜드 톤앤매너 준수 (색온도, 금지요소, 무드, 디렉터 스타일) | **20%** | ≥ 80 |
| **outfit_accuracy** | 착장 재현도 (참조 이미지 준 경우 로고/디테일 유지) | **15%** | ≥ 85 |
| **composition** | 구도/프레이밍 퀄리티 (앵글, 배치, 여백) | **10%** | ≥ 80 |
| **lighting_mood** | 조명/분위기 (디렉터 의도 반영, 색온도) | **10%** | ≥ 80 |

### 판정 기준

- **RELEASE_READY**: 전체 가중 평균 ≥ 90 AND anatomy ≥ 90 AND photorealism ≥ 85
- **NEEDS_REFINEMENT**: 전체 가중 평균 ≥ 80 BUT anatomy 또는 photorealism 미달
- **REGENERATE**: 전체 가중 평균 < 80 또는 anatomy < 70

### 즉시 실패 (Auto-Fail) 조건

다음 중 하나라도 해당하면 점수와 무관하게 **REGENERATE**:

| 조건 | 설명 |
|------|------|
| 손가락 이상 | 6개 이상 또는 기형적 손가락 |
| 얼굴 왜곡 | 비대칭, 이중 이미지, 흐림 |
| 텍스트/워터마크 | 의도하지 않은 텍스트가 이미지에 포함 |
| 브랜드 금지 요소 | brand_dna.forbidden_keywords에 해당하는 요소 존재 |
| 톤앤매너 불일치 | 색온도가 브랜드 방향과 정반대 (예: MLB에 골든아워/웜톤) |
| 플라스틱 피부 | AI 특유의 매끈한 플라스틱 텍스처 |
| NSFW | 부적절한 콘텐츠 |

### 검증 프롬프트 (VLM)

```python
def validate_brand_cut(
    generated_image,
    brand_dna: dict,
    outfit_reference=None,
    director_style: str = "",
    client=None,
    model: str = "gemini-2.5-flash"
) -> dict:
    """브랜드컷 생성 이미지 검증 (원본 비교 없음)"""

    outfit_instruction = ""
    if outfit_reference:
        outfit_instruction = """
6. outfit_accuracy (0-100): Does the generated outfit match the reference?
   - Logo placement and design preserved
   - Color accuracy
   - Garment silhouette and fit
   - Key details (hood, zipper, pockets, etc.)"""

    forbidden = ", ".join(brand_dna.get("forbidden_keywords", []))
    brand_mood = ", ".join(brand_dna.get("identity", {}).get("mood", []))

    prompt = f"""You are a professional fashion photography quality inspector.
Evaluate this AI-generated fashion editorial image.

THIS IS NOT A COMPARISON - evaluate the generated image BY ITSELF.

BRAND REQUIREMENTS:
- Brand mood: {brand_mood}
- Forbidden elements: {forbidden}
- Director style: {director_style}

SCORE EACH CRITERION (0-100):

1. photorealism (0-100): Does it look like a real photograph?
   - Natural skin texture (pores, subtle imperfections, NOT plastic)
   - Realistic hair strands and texture
   - Natural fabric draping and wrinkles
   - Believable lighting on skin and materials
   - No AI artifacts, no uncanny valley

2. anatomy (0-100): Is human anatomy correct?
   - Correct number of fingers (5 per hand)
   - Natural body proportions
   - Correct joint articulation
   - Symmetrical face (unless intentional pose)
   - Natural hand poses (no melted/fused fingers)
   - Ears, teeth, eyes all correct

3. brand_compliance (0-100): Does it match the brand's tone & manner?
   Sub-checks (all must align):
   a. COLOR TEMPERATURE: Does the color grading match the brand?
      - MLB: cool tones ONLY (teal, steel gray, desaturated). Warm/golden = FAIL
      - Discovery: earth tones, muted naturals
      - Duvetica: refined neutrals, understated luxury
      - Banillaco: soft pastels, clean whites, luminous
      - SergioTacchini: retro color palette, classic sport
   b. FORBIDDEN ELEMENTS: Are any brand-forbidden elements present?
      - Check against brand_dna.forbidden_keywords
      - MLB: warm tones, golden hour, graffiti, dirty backgrounds
      - Each brand has specific forbidden list
   c. MOOD/ATMOSPHERE: Does the overall vibe match the brand identity?
      - MLB Marketing: arrogant luxury, bored chic, rebellious swagger
      - MLB Graphic: street legend, old-school cool
      - Discovery: technical utility, outdoor adventure
      - Duvetica: quiet luxury, Italian craftsmanship
      - Banillaco: fresh, luminous, K-beauty glow
      - SergioTacchini: slim silhouette, rock & roll
   d. DIRECTOR STYLE: Does it reflect the assigned director's vision?
      - If director_style is specified, evaluate adherence

   Scoring guide:
   - 90-100: Perfect brand alignment, could publish immediately
   - 70-89: Mostly aligned, minor tone/mood deviations
   - 50-69: Noticeable brand mismatch (wrong color temp, wrong mood)
   - 0-49: Completely off-brand (warm tones for MLB, dirty for Duvetica, etc.)

4. composition (0-100): Is the composition professional?
   - Good framing and subject placement
   - Appropriate camera angle
   - Background supports (not competes with) the subject
   - Professional-grade editorial composition

5. lighting_mood (0-100): Is the lighting and mood right?
   - Lighting direction is consistent and intentional
   - Shadows are natural and well-placed
   - Color grading matches intended mood
   - Overall atmosphere is cohesive
{outfit_instruction}

AUTO-FAIL CONDITIONS (check these first!):
- Extra/missing/deformed fingers → anatomy = 0
- Plastic/waxy skin → photorealism = 0
- Unintended text/watermark in image → auto_fail = true
- Forbidden brand elements → brand_compliance = 0
- Color temperature completely opposite to brand DNA (e.g., warm golden for MLB cool brand) → brand_compliance = 0
- NSFW content → auto_fail = true

RESPOND IN JSON:
{{
  "photorealism": <int 0-100>,
  "anatomy": <int 0-100>,
  "brand_compliance": <int 0-100>,
  "brand_compliance_detail": {{
    "color_temperature": <int 0-100>,
    "forbidden_check": <int 0-100>,
    "mood_match": <int 0-100>,
    "director_style_match": <int 0-100 or null>
  }},
  "outfit_accuracy": <int 0-100 or null if no reference>,
  "composition": <int 0-100>,
  "lighting_mood": <int 0-100>,
  "auto_fail": <bool>,
  "auto_fail_reason": "<string or null>",
  "issues": ["<issue1>", "<issue2>"],
  "strengths": ["<strength1>", "<strength2>"],
  "overall_assessment": "RELEASE_READY" | "NEEDS_REFINEMENT" | "REGENERATE"
}}"""

    parts = [prompt, generated_image]
    if outfit_reference:
        parts.append(outfit_reference)

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1
    )

    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=gen_config
    )

    result = json.loads(response.text)

    # 가중 평균 계산
    weights = {
        "photorealism": 0.25,
        "anatomy": 0.20,
        "brand_compliance": 0.20,
        "outfit_accuracy": 0.15,
        "composition": 0.10,
        "lighting_mood": 0.10
    }

    if result.get("outfit_accuracy") is None:
        # 착장 참조 없는 경우 가중치 재분배
        weights.pop("outfit_accuracy")
        weights["photorealism"] = 0.30
        weights["anatomy"] = 0.25
        weights["brand_compliance"] = 0.25
        weights["composition"] = 0.10
        weights["lighting_mood"] = 0.10

    total = sum(
        result.get(k, 0) * v
        for k, v in weights.items()
    )
    result["total_score"] = round(total, 1)

    # Auto-fail 처리
    if result.get("auto_fail"):
        result["overall_assessment"] = "REGENERATE"

    # 판정 로직
    if not result.get("auto_fail"):
        if total >= 90 and result["anatomy"] >= 90 and result["photorealism"] >= 85:
            result["overall_assessment"] = "RELEASE_READY"
        elif total >= 80:
            result["overall_assessment"] = "NEEDS_REFINEMENT"
        else:
            result["overall_assessment"] = "REGENERATE"

    return result
```

### 검증 결과 예시

```json
{
  "photorealism": 92,
  "anatomy": 95,
  "brand_compliance": 88,
  "outfit_accuracy": 90,
  "composition": 85,
  "lighting_mood": 90,
  "total_score": 91.1,
  "auto_fail": false,
  "auto_fail_reason": null,
  "issues": ["배경 건물에 미세한 텍스트 잔상"],
  "strengths": ["자연스러운 피부 질감", "브랜드 쿨톤 정확", "전문적 구도"],
  "overall_assessment": "RELEASE_READY"
}
```

### 배치 검증

```python
def validate_brand_cut_batch(
    images: list,
    brand_dna: dict,
    outfit_references: list = None,
    director_style: str = "",
    client=None
) -> dict:
    """배치 브랜드컷 검증"""
    results = []

    for i, img in enumerate(images):
        outfit_ref = outfit_references[i] if outfit_references and i < len(outfit_references) else None

        result = validate_brand_cut(
            generated_image=img,
            brand_dna=brand_dna,
            outfit_reference=outfit_ref,
            director_style=director_style,
            client=client
        )
        result["index"] = i
        results.append(result)

    release = [r for r in results if r["overall_assessment"] == "RELEASE_READY"]
    refine = [r for r in results if r["overall_assessment"] == "NEEDS_REFINEMENT"]
    regen = [r for r in results if r["overall_assessment"] == "REGENERATE"]

    return {
        "total": len(images),
        "release_ready": len(release),
        "needs_refinement": len(refine),
        "regenerate": len(regen),
        "pass_rate": len(release) / len(images) if images else 0,
        "results": results
    }
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 7: 스마트 재시도 (실패 이미지 자동 보정)                   ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 재시도 흐름

검증에서 **REGENERATE** 또는 **NEEDS_REFINEMENT** 판정을 받은 이미지만 골라서,
실패 원인을 진단하고 프롬프트를 보강한 뒤 해당 이미지만 재생성합니다.

```
생성 (N장) → 검증 → RELEASE_READY → 완료 ✓
                  → NEEDS_REFINEMENT ─┐
                  → REGENERATE ───────┤
                                      ↓
                              실패 원인 진단
                                      ↓
                              원인별 프롬프트 보강
                                      ↓
                              해당 이미지만 재생성 (temp 낮춤)
                                      ↓
                              다시 검증 (최대 3회)
                                      ↓
                              3회 실패 → manual_review/로 이동
```

### 실패 원인 진단 (6가지 카테고리)

| 실패 원인 | 감지 조건 | 프롬프트 보강 전략 |
|-----------|----------|-------------------|
| **anatomy_error** | anatomy < 90 또는 손가락/관절 이슈 | 해부학 강조 키워드 추가 |
| **plastic_skin** | photorealism < 85 또는 피부 관련 이슈 | 피부 질감 키워드 강화 |
| **brand_mismatch** | brand_compliance < 80 또는 톤앤매너 불일치 | 브랜드 DNA 키워드 재주입 + 금지 요소 negative에 추가 |
| **outfit_drift** | outfit_accuracy < 85 (참조 있는 경우) | 착장 디테일 반복 강조 |
| **composition_weak** | composition < 80 | 구도/앵글 지시 구체화 |
| **mood_off** | lighting_mood < 80 | 조명/분위기 키워드 강화 |

### 원인별 프롬프트 보강 로직

```python
# 실패 원인별 프롬프트 보강 매핑
RETRY_ENHANCEMENTS = {
    "anatomy_error": {
        "positive": [
            "anatomically correct human body",
            "exactly 5 fingers on each hand",
            "natural joint articulation",
            "correct body proportions",
            "realistic hand poses with natural finger separation"
        ],
        "negative": [
            "extra fingers", "missing fingers", "deformed hands",
            "unnatural joints", "wrong proportions", "fused fingers",
            "melted fingers", "extra limbs"
        ],
        "temperature_adjust": -0.05  # 낮춰서 안정화
    },
    "plastic_skin": {
        "positive": [
            "ultra realistic skin texture with natural pores",
            "visible skin imperfections and subtle blemishes",
            "natural subsurface scattering on skin",
            "realistic hair strands with individual detail",
            "natural fabric texture with real wrinkles"
        ],
        "negative": [
            "plastic skin", "waxy skin", "airbrushed",
            "smooth perfect skin", "CGI look", "3D render",
            "artificial texture", "uncanny valley"
        ],
        "temperature_adjust": -0.05
    },
    "brand_mismatch": {
        "positive": [],  # brand_dna.keywords에서 동적으로 로드
        "negative": [],  # brand_dna.forbidden_keywords에서 동적으로 로드
        "temperature_adjust": 0,
        "dynamic": True,  # brand_dna에서 키워드 동적 주입
        "action": "reload_brand_dna_keywords_and_reinject"
    },
    "outfit_drift": {
        "positive": [
            "EXACT garment reproduction from reference",
            "preserve ALL logo placement and design",
            "maintain exact color and fabric texture",
            "keep all garment details: hood, zipper, pockets, buttons"
        ],
        "negative": [
            "modified clothing", "changed outfit", "different garment",
            "missing logo", "wrong color"
        ],
        "temperature_adjust": -0.1  # 착장 보존에는 낮은 temp
    },
    "composition_weak": {
        "positive": [
            "professional editorial composition",
            "rule of thirds framing",
            "model as clear focal point",
            "balanced negative space"
        ],
        "negative": [
            "awkward framing", "cut off limbs", "unbalanced composition"
        ],
        "temperature_adjust": 0
    },
    "mood_off": {
        "positive": [],  # director_style에서 동적으로 로드
        "negative": [],
        "temperature_adjust": 0,
        "dynamic": True,
        "action": "reload_director_mood_keywords"
    }
}
```

### 재시도 엔진

```python
def diagnose_failure(validation_result: dict) -> list:
    """검증 결과에서 실패 원인 진단"""
    issues = []

    if validation_result.get("anatomy", 100) < 90:
        issues.append("anatomy_error")

    if validation_result.get("photorealism", 100) < 85:
        issues.append("plastic_skin")

    if validation_result.get("brand_compliance", 100) < 80:
        issues.append("brand_mismatch")
        # brand_compliance_detail에서 세부 원인 추출
        detail = validation_result.get("brand_compliance_detail", {})
        if detail.get("color_temperature", 100) < 70:
            issues.append("brand_mismatch:color_temperature")
        if detail.get("mood_match", 100) < 70:
            issues.append("brand_mismatch:mood")

    if validation_result.get("outfit_accuracy") is not None and validation_result["outfit_accuracy"] < 85:
        issues.append("outfit_drift")

    if validation_result.get("composition", 100) < 80:
        issues.append("composition_weak")

    if validation_result.get("lighting_mood", 100) < 80:
        issues.append("mood_off")

    # auto_fail인 경우 해당 원인 추가
    if validation_result.get("auto_fail"):
        reason = validation_result.get("auto_fail_reason", "")
        if "finger" in reason.lower():
            issues.append("anatomy_error")
        if "plastic" in reason.lower() or "skin" in reason.lower():
            issues.append("plastic_skin")
        if "brand" in reason.lower() or "forbidden" in reason.lower() or "color" in reason.lower():
            issues.append("brand_mismatch")

    return list(set(issues))  # 중복 제거


def enhance_prompt(
    original_prompt: str,
    failure_issues: list,
    brand_dna: dict = None,
    director_style: str = ""
) -> tuple:
    """실패 원인 기반 프롬프트 보강. (enhanced_prompt, temp_adjustment) 반환"""

    additions_positive = []
    additions_negative = []
    temp_adjust = 0

    for issue in failure_issues:
        # brand_mismatch 세부 원인 처리
        base_issue = issue.split(":")[0]
        enhancement = RETRY_ENHANCEMENTS.get(base_issue, {})

        if enhancement.get("dynamic"):
            # 브랜드 DNA에서 동적 키워드 로드
            if base_issue == "brand_mismatch" and brand_dna:
                additions_positive.extend(brand_dna.get("keywords", {}).get("style", []))
                additions_positive.extend(brand_dna.get("keywords", {}).get("mood", []))
                additions_negative.extend(brand_dna.get("forbidden_keywords", []))
            elif base_issue == "mood_off" and director_style:
                additions_positive.append(f"Directed in the style of {director_style}")
        else:
            additions_positive.extend(enhancement.get("positive", []))
            additions_negative.extend(enhancement.get("negative", []))

        temp_adjust += enhancement.get("temperature_adjust", 0)

    # 프롬프트 보강
    enhanced = original_prompt

    if additions_positive:
        positive_str = ", ".join(additions_positive)
        enhanced += f"\n\n## QUALITY REINFORCEMENT (자동 보강):\n{positive_str}"

    if additions_negative:
        negative_str = ", ".join(additions_negative)
        enhanced += f"\n\n## MUST AVOID (자동 추가):\n{negative_str}"

    return enhanced, temp_adjust


def retry_failed_images(
    failed_results: list,
    original_prompts: list,
    brand_dna: dict,
    director_style: str = "",
    outfit_references: list = None,
    base_temperature: float = 0.3,
    max_retries: int = 3,
    client=None
) -> list:
    """실패한 이미지만 골라서 재시도"""

    final_results = []

    for result in failed_results:
        idx = result["index"]
        original_prompt = original_prompts[idx]
        outfit_ref = outfit_references[idx] if outfit_references and idx < len(outfit_references) else None

        current_prompt = original_prompt
        current_temp = base_temperature

        for attempt in range(max_retries):
            # 1. 실패 원인 진단
            issues = diagnose_failure(result)
            log_info(f"[재시도 {attempt+1}/{max_retries}] 이미지 #{idx} - 원인: {issues}")

            # 2. 프롬프트 보강
            current_prompt, temp_adj = enhance_prompt(
                current_prompt, issues, brand_dna, director_style
            )
            current_temp = max(0.1, current_temp + temp_adj)  # 최소 0.1

            # 3. 재생성
            new_image = call_gemini_with_retry(
                prompt_parts=[types.Part(text=current_prompt)] +
                    ([pil_to_part(outfit_ref)] if outfit_ref else []),
                temperature=current_temp
            )

            # 4. 재검증
            result = validate_brand_cut(
                generated_image=new_image,
                brand_dna=brand_dna,
                outfit_reference=outfit_ref,
                director_style=director_style,
                client=client
            )
            result["index"] = idx
            result["retry_attempt"] = attempt + 1
            result["diagnosed_issues"] = issues

            # 5. 통과 여부
            if result["overall_assessment"] == "RELEASE_READY":
                log_info(f"[재시도 성공] 이미지 #{idx} - {attempt+1}회 만에 통과")
                break

            log_warn(f"[재시도 실패] 이미지 #{idx} - {attempt+1}회차 점수: {result['total_score']}")

        # 3회 다 실패하면 manual_review로
        if result["overall_assessment"] != "RELEASE_READY":
            result["final_status"] = "MANUAL_REVIEW"
            log_warn(f"[최종 실패] 이미지 #{idx} → manual_review/로 이동")
        else:
            result["final_status"] = "RELEASE_READY"

        final_results.append(result)

    return final_results
```

### 재시도 예시

```
[FNF] >> 5장 생성 완료, 검증 시작...
[FNF] 이미지 #0: RELEASE_READY (92.3점) ✓
[FNF] 이미지 #1: RELEASE_READY (90.5점) ✓
[FNF] 이미지 #2: REGENERATE (78.2점) - anatomy_error, plastic_skin
[FNF] 이미지 #3: RELEASE_READY (91.0점) ✓
[FNF] 이미지 #4: NEEDS_REFINEMENT (84.1점) - brand_mismatch:color_temperature

[FNF] >> 실패 2장 재시도 시작...

[FNF] [재시도 1/3] 이미지 #2 - 원인: [anatomy_error, plastic_skin]
[FNF]   프롬프트 보강: +해부학 키워드, +피부 질감 키워드, temp 0.3→0.2
[FNF]   재생성 중...
[FNF]   재검증: 89.5점 (NEEDS_REFINEMENT) - anatomy 87
[FNF] [재시도 2/3] 이미지 #2 - 원인: [anatomy_error]
[FNF]   프롬프트 보강: +해부학 키워드 강화, temp 0.2→0.15
[FNF]   재생성 중...
[FNF]   재검증: 91.2점 (RELEASE_READY) ✓
[FNF] [재시도 성공] 이미지 #2 - 2회 만에 통과

[FNF] [재시도 1/3] 이미지 #4 - 원인: [brand_mismatch:color_temperature]
[FNF]   프롬프트 보강: +MLB 쿨톤 키워드, -warm tones/-golden hour, temp 유지
[FNF]   재생성 중...
[FNF]   재검증: 90.8점 (RELEASE_READY) ✓
[FNF] [재시도 성공] 이미지 #4 - 1회 만에 통과

[FNF] >> 최종 결과: 5/5 RELEASE_READY (재시도 2장 성공)
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 8: 결과 반환                                              ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 출력 형식

```json
{
  "status": "success",
  "brand": "mlb-marketing",
  "style": "editorial",
  "count": 5,
  "generated": 5,
  "prompts_used": ["prompt1", "prompt2"],
  "images": ["image1", "image2"],
  "validation": {
    "passed": 4,
    "failed": 1,
    "pass_rate": 0.8
  }
}
```

## 파일 저장 및 출력 구조

> `save_image()` 함수 및 출력 디렉토리 구조는 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` Section 6 및 `CLAUDE.md` 참조.

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   배경 스타일 프리셋                                              ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

> 배경 스타일 프리셋 (`CONCRETE_STYLES`, `CITY_STYLES`, `STUDIO_STYLES`)은
> `이미지생성_레퍼런스_image-gen-reference/SKILL.md` Section 7 참조.

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   참조 이미지 처리                                                ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

> 참조 이미지 프롬프트 (`REFERENCE_PROMPTS`, `build_reference_prompt`, `build_background_swap_with_vehicle`)는
> `이미지생성_레퍼런스_image-gen-reference/SKILL.md` Section 8 참조.

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   배치 처리                                                       ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## BatchProcessor 클래스

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json, os, time

class BatchProcessor:
    """대량 이미지 생성을 위한 배치 프로세서"""

    def __init__(self, max_workers: int = 5, retry_count: int = 3, delay_between: float = 0.5):
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.delay_between = delay_between
        self.results = []
        self.errors = []

    def process(self, items: list, process_func, output_dir: str = None) -> dict:
        """배치 처리 실행"""
        start_time = datetime.now()
        self.results = []
        self.errors = []

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        total = len(items)
        print(f"[FNF] 배치 처리 시작: {total}개 아이템, {self.max_workers} workers")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_with_retry, item, process_func, idx, output_dir): idx
                for idx, item in enumerate(items)
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.errors.append({"index": idx, "error": str(e)})
                time.sleep(self.delay_between)

        duration = (datetime.now() - start_time).total_seconds()
        return {
            "total": total,
            "success": len(self.results),
            "failed": len(self.errors),
            "duration_sec": round(duration, 2),
            "results": self.results,
            "errors": self.errors
        }

    def _process_with_retry(self, item, process_func, idx, output_dir):
        last_error = None
        for attempt in range(self.retry_count):
            try:
                result_image = process_func(item)
                if output_dir and result_image:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
                    filepath = os.path.join(output_dir, f"result_{idx:04d}_{timestamp}.png")
                    result_image.save(filepath, "PNG")
                    return {"index": idx, "filepath": filepath, "status": "success"}
                return {"index": idx, "status": "success"}
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep((attempt + 1) * 3)
        raise last_error
```

## 배치 처리 설정 가이드

```
max_workers    : 5 (기본), API 키 개수에 맞춰 조정
                 - API 키 1개: 2-3
                 - API 키 5개: 5-8
                 - API 키 10개+: 10-15
retry_count    : 3 (기본), rate limit 에러 시 재시도
delay_between  : 0.5초 (기본), 429 에러 많으면 1.0~2.0으로 증가
예상 처리 시간 : 이미지당 10~30초
                 100장 x 20초 / 5 workers = 약 7분
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   에러 처리                                                       ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

| 에러 | 코드 | 재시도 가능 | 대응 |
|-----|------|------------|------|
| 브랜드 미감지 | `BRAND_NOT_FOUND` | No | "어떤 브랜드?" 질문 |
| 스타일 미감지 | `STYLE_NOT_FOUND` | No | 기본값 editorial 사용 |
| API 사용량 초과 | `RATE_LIMIT` | Yes | 키 로테이션 + 5초 대기 |
| 서버 과부하 | `SERVER_OVERLOAD` | Yes | 5/10/15초 대기 후 재시도 |
| 요청 시간 초과 | `TIMEOUT` | Yes | 재시도 3회 후 스킵 |
| API 키 오류 | `AUTH_ERROR` | No | 키 확인 안내 |
| 콘텐츠 정책 위반 | `SAFETY_BLOCK` | No | 프롬프트 수정 안내 |
| 이미지 생성 결과 없음 | `NO_RESULT` | Yes | 재시도 |
| 검증 불합격 | `VALIDATION_FAIL` | Yes | 프롬프트 보강 후 재생성 |

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   핵심 규칙 (절대 규칙)                                          ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

### 1. 모델 선택
- **무조건** `gemini-3-pro-image-preview` 사용
- `gemini-2.x` 계열 절대 금지 (인물 축소, 색감 불일치)
- 위반 시 전부 삭제 후 재생성

### 2. 포토리얼리즘
- 피부 질감: 자연스러운 모공, 미세한 결점 포함 (플라스틱 금지)
- 머리카락: 개별 가닥이 보이는 자연스러운 텍스처
- 직물: 자연스러운 주름과 드레이핑
- 해부학: 손가락 5개, 정상 관절, 자연스러운 비율

### 3. 해상도
- `image_size` 파라미터로 설정 (PIL 리사이즈 금지)
- 테스트: 1K, 제작: 2K, 최종: 4K

### 4. Temperature
- 브랜드컷 (착장 참조 있음): 0.2~0.3 (착장 충실도 유지)
- 브랜드컷 (자유 생성): 0.3~0.5 (창의적 다양성)
- 실험적/아트: 0.7~0.9

### 5. 프롬프트
- DX 반복 강조 (모델 보존) + JSON 구조화 (분위기/물리) = 하이브리드
- 너무 길면 품질 저하 (핵심만)
- 모순 지시 금지

### 6. API 키
- .env에서 로드 (하드코딩 절대 금지)
- 복수 키 로테이션 사용 (`get_next_api_key()`)

### 7. 착장 분석
- 512px 다운샘플링 필수
- `response_mime_type="application/json"` 사용
- temperature 0.2 (일관성)

### 8. 검증 합격 조건
- 전체 가중 평균 ≥ 90
- anatomy ≥ 90 (해부학 오류 불허)
- photorealism ≥ 85 (포토리얼리즘 필수)
- auto_fail 조건 없어야 함
- 세 조건 모두 충족해야 RELEASE_READY

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   DO / DON'T                                                     ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

### DO

- **모델**: `gemini-3-pro-image-preview` 사용 (절대 규칙)
- **해상도**: `image_size` 파라미터 사용 (PIL 리사이즈 금지)
- **Temperature**: 0.2~0.3 (착장 참조), 0.3~0.5 (자유 생성)
- **포토리얼리즘**: 자연스러운 피부 질감, 해부학 정확성 확인
- **브랜드 DNA**: forbidden_keywords 위반 여부 체크
- **해부학 검증**: 손가락 개수, 관절, 비율 반드시 확인
- **배치 처리**: `BatchProcessor` 또는 `batch_generate()` 사용
- **API 키**: `get_next_api_key()` 로테이션 사용
- **재시도**: `call_gemini_with_retry()` 사용
- **착장 분석**: 512px 다운샘플, JSON 강제 반환
- **구체적 배경**: "concrete wall" 대신 "raw exposed concrete with form marks"
- **색상 매칭**: 배경이 인물과 어울리도록 지시
- **검증 필수**: 생성 후 반드시 VLM 검증

### DON'T

- **gemini-2.0, gemini-2.5 계열 사용 금지**
- **PIL로 업스케일 금지** (품질 손실)
- **API 키 하드코딩 금지**
- **재시도 없이 API 호출 금지**
- **단일 스레드로 대량 처리 금지**
- **너무 긴 프롬프트** (수십 줄은 오히려 품질 저하)
- **모호한 배경 지시** ("nice background" 금지)
- **충돌하는 지시** ("don't change" + "make it different" 모순)
- **불필요한 반복** (3번이면 충분, 5번은 과다)
- **원본 해상도 착장 분석** (512px 다운샘플링 필수)
- **검증 건너뛰기** (프로덕션 전 필수)
- **플라스틱/왁스 피부 허용 금지**
- **해부학 오류 무시 금지** (손가락 6개 등)
- **브랜드 금지 요소 포함된 이미지 릴리즈 금지**

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   실전 예시                                                       ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 예시: `/브랜드컷_brand-cut MLB 프리미엄 화보 3장`

**실행 흐름**:

1. **브랜드 라우팅**: "MLB" + "프리미엄" --> MLB 마케팅 --> `mlb-marketing.json`
2. **리소스 로드**:
   - DNA: `.claude/skills/brand-dna/mlb-marketing.json`
   - 디렉터: `.claude/skills/(MLB마케팅)_시티미니멀_tyrone-lebon/SKILL.md`
   - 템플릿: `prompt-templates/editorial.json`
3. **착장 분석**: VLM으로 착장 디테일 추출
4. **프롬프트 생성**:
   ```
   ultra_photorealistic_editorial, 8k, 여성, 20대 중반,
   East Asian, cool expression, old money meets streetwear,
   confident_standing pose, minimalist concrete mansion,
   softbox lighting, soft_diffused...

   in the style of Tyrone Lebon (The Old Money Rebel),
   가장 완벽하고 비싼 공간을, 가장 지루해하는 표정으로 장악한다
   ```
5. **이미지 생성**: 3장 병렬 생성 (Gemini 3 Pro, 2K, temp=0.3)
6. **검증**: 각 이미지 VLM 검증 (photorealism≥85, anatomy≥90, total≥90)
7. **결과**:
   ```json
   {
     "status": "success",
     "brand": "mlb-marketing",
     "style": "editorial",
     "count": 3,
     "generated": 3,
     "validation": { "passed": 3, "failed": 0, "pass_rate": 1.0 }
   }
   ```

---

## 관련 파일 (참조용)

```
.claude/skills/
├── brand-dna/                              # 브랜드 DNA JSON 파일들
│   ├── _index.json
│   ├── mlb-marketing.json
│   ├── mlb-graphic.json
│   ├── discovery.json
│   ├── duvetica.json
│   ├── sergio-tacchini.json
│   └── banillaco.json
├── prompt-templates/                       # 스타일 템플릿
│   ├── editorial.json
│   ├── selfie.json
│   ├── pose_library.json                   # [v2] 포즈/표정/앵글 VLM 분석 카탈로그 (38 entries)
│   ├── MLB_editorial.json                  # [v2] MLB 에디토리얼 v2 템플릿
│   └── backgrounds/                        # 배경 프리셋
├── (MLB마케팅)_시티미니멀_tyrone-lebon/     # 디렉터 페르소나
├── (MLB그래픽)_스트릿레전드_shawn-stussy/
├── (Discovery)_테크니컬유틸리티_yosuke-aizawa/
├── (Duvetica)_럭셔리장인_brunello-cucinelli/
├── (SergioTacchini)_실루엣혁명_hedi-slimane/
├── (Banillaco)_맑은뷰티_ahn-joo-young/
└── (제품연출)_한국힙이커머스_musinsa-29cm/
```

### v2 Shot Card 관련 스크립트

```
project_root/
├── analyze_style_library.py                # [v2] VLM 포즈 분석 스크립트 (38개 참조 이미지 분석)
├── generate_brandcut_v2.py                 # [v2] Shot card 기반 생성 스크립트
└── [기존 v1 스크립트들...]
```

---

**작성일**: 2026-02-04 (v2 Shot Card System 추가)
**버전**: 2.0
**통합 출처**: fnf-generate, 브랜드라우팅_brand-routing, 프롬프트패턴_prompt-patterns, 이미지생성기본_image-generation-base, 검증품질관리_validation-quality, 착장분석_clothing-analysis
**참고**: editorial-prompt, selfie-prompt는 이 스킬에 통합됨
**v2 추가**: pose_library.json 기반 Shot Card System, 구조화 Key-Value 프롬프트, 14-slot Reference Allocation
