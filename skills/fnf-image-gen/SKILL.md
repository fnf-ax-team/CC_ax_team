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
├── SKILL.md                    # 이 파일 (통합 문서)
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

## Edge Cases

- **브랜드 미지정 시**: 범용 설정으로 생성 (brand_dna 없이 템플릿만 사용)
- **시딩UGC가 너무 깨끗하게 나올 때**: temperature 올림 (0.35→0.4→0.45) + Negative Prompt 강화
- **인물 보존 실패 시**: "THIS EXACT person" 지시어 강화 + 고해상도 정면 레퍼런스 사용
- **제품 렌더링 부정확 시**: 제품 특징을 프롬프트에 구체적으로 명시

---

# 브랜드컷 (Brand Cut) 상세

# 브랜드컷 - 패션 에디토리얼 통합 워크플로


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
            → Step 5: 이미지 생성 (Gemini 3 Pro)
            → Step 6: 검증 (VLM 품질 판정)
            → Step 7: 스마트 재시도 (실패 이미지 자동 보정)
            → Step 8: 결과 반환
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

| 트리거 키워드 | 브랜드 | DNA 스킬 | 디렉터 페르소나 |
|--------------|--------|----------|----------------|
| MLB, 영앤리치, 프리미엄, 시크, 마케팅 화보 | MLB 마케팅 | `mlb-marketing.json` | `(MLB마케팅)_시티미니멀_tyrone-lebon` |
| Discovery, 아웃도어, 고프코어, 테크니컬 | Discovery | `discovery.json` | `(Discovery)_테크니컬유틸리티_yosuke-aizawa` |
| Duvetica, 럭셔리, 다운, 이탈리안, 장인 | Duvetica | `duvetica.json` | `(Duvetica)_럭셔리장인_brunello-cucinelli` |
| Sergio, 테니스, 레트로, 80s, 슬림 | Sergio Tacchini | `sergio-tacchini.json` | `(SergioTacchini)_실루엣혁명_hedi-slimane` |
| Banila, 뷰티, 색조, 맑은, K-뷰티 | Banillaco | `banillaco.json` | `(Banillaco)_맑은뷰티_ahn-joo-young` |
| 제품컷, 제품 연출, 플랫레이, 행잉, 히어로샷, 이커머스, 상세페이지 | 제품연출 (전 브랜드) | 해당 브랜드 DNA 사용 | `(제품연출)_한국힙이커머스_musinsa-29cm` |

### 제품연출 디렉터 특이사항

`(제품연출)_한국힙이커머스_musinsa-29cm`는 특정 브랜드에 종속되지 않는 **전 브랜드 공통** 제품 연출 디렉터입니다.
- 모델 착용이 아닌 **제품 단독 촬영** (플랫레이, 행잉, 히어로샷, 컨텍스트)
- 브랜드 DNA는 해당 제품의 브랜드 DNA를 그대로 사용
- 브랜드별 적용 가이드가 디렉터 스킬 내에 포함되어 있음 (MLB/Discovery/Duvetica/SergioTacchini/Banillaco 각각)
- "제품컷", "물촬", "상품사진", "이커머스" 키워드 감지 시 이 디렉터 호출

## 스타일 매칭 테이블

| 트리거 키워드 | 스타일 | 용도 |
|--------------|------|------|
| 화보, 에디토리얼, 매거진, 패션, 프로페셔널 | editorial | 전문 화보 |
| 셀피, 일상, SNS, 캐주얼, 자연스러운 | selfie | 셀카/일상 |
| 배경 교체, 배경 바꿔 | (별도 스킬) | 배경 스왑 - `배경교체_background-swap` 스킬 사용 |

## 브랜드 미감지 시

브랜드를 특정할 수 없으면 사용자에게 질문:
> "어떤 브랜드의 이미지를 생성할까요? (MLB/Discovery/Duvetica/SergioTacchini/Banillaco)"

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

## 테스트 결과 요약 (2026-01-27)

| 항목 | DX 스타일 (반복 강조) | JSON 템플릿 (구조화) |
|------|---------------------|---------------------|
| 성공률 | 8/10 | 8/10 |
| **모델 보존** | **8/8 (100%)** | 7/8 (87.5%) |
| 색온도/분위기 | 보통 | **더 정확** |
| 공간감/디테일 | 보통 | **더 풍부** |

### 핵심 발견 & 결론

1. **DX 반복 강조** ("DO NOT SHRINK" x3) --> **모델 축소 방지에 효과적**
2. **JSON 구조화** (physics, lighting, color_palette) --> **분위기/색온도 표현에 효과적**
3. **결론**: DX의 반복 강조 + JSON의 구조화된 기술 명세를 결합한 **하이브리드 방식** 채택

## 프롬프트 작성 3원칙

1. **DX 반복 강조** - 모델 보존 관련 키워드 3회 반복 (필수!)
2. **JSON 구조화** - 물리/조명/색온도는 구조화된 명세 사용
3. **짧고 간결하게** - 핵심 지시만 포함 (길면 품질 저하)

## 하이브리드 프롬프트 템플릿

```python
HYBRID_TEMPLATE = {
    "preservation": {
        "person": {
            "face": "identical to input - same features, expression, hair",
            "body": "identical to input - same pose, proportions, position",
            "clothing": "identical to input - same garments, colors, details",
            "scale": "identical to input - person height ratio must match exactly",
            "critical_rule": "Frame fill ratio must be 97%"
        },
        "objects": {
            "vehicles": "preserve if present",
            "props": "preserve if present"
        }
    },
    "physics": {
        "lighting": {
            "direction": "match original light source direction",
            "intensity": "match original lighting intensity",
            "color_temperature": "maintain original color temperature"
        },
        "perspective": {
            "horizon_line": "match original horizon position",
            "focal_length": "match original lens perspective"
        },
        "shadows": {
            "direction": "consistent with light source",
            "softness": "match original shadow characteristics"
        }
    },
    "technical": {
        "resolution": "match input resolution",
        "aspect_ratio": "match input aspect ratio",
        "quality": "professional photography, no artifacts, seamless compositing"
    }
}
```

## 필수 DX 키워드 (배경 교체 시)

```
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1
DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
PERSON PRESERVATION (100% IDENTICAL)
```

## 하이브리드 프롬프트 생성 함수

```python
BACKGROUND_STYLES = {
    "minimal_industrial": {
        "location": "minimal industrial studio",
        "materials": "clean concrete wall, polished metal panels",
        "color_palette": "neutral gray, silver accents",
        "atmosphere": "editorial, fashion-forward",
        "lighting_style": "soft studio lighting"
    },
    "contemporary_soft": {
        "location": "contemporary design space",
        "materials": "smooth concrete, brushed steel accents",
        "color_palette": "warm gray, subtle metallic",
        "atmosphere": "soft, elegant, refined",
        "lighting_style": "soft diffused daylight"
    },
    "modern_cool": {
        "location": "modern architectural interior",
        "materials": "cool gray concrete, chrome metal details",
        "color_palette": "cool gray, chrome silver",
        "atmosphere": "cool, urban, sophisticated",
        "lighting_style": "cool ambient lighting"
    },
    "gallery_minimal": {
        "location": "art gallery space",
        "materials": "gallery-style concrete wall, minimal metal frames",
        "color_palette": "white, silver, light gray",
        "atmosphere": "minimalist, clean, artistic",
        "lighting_style": "gallery track lighting"
    },
    "urban_industrial": {
        "location": "urban industrial structure",
        "materials": "urban concrete, polished steel beams",
        "color_palette": "industrial gray, metallic",
        "atmosphere": "industrial chic, contemporary",
        "lighting_style": "natural urban light with shadows"
    }
}


def build_hybrid_prompt(style_key: str, custom_style: dict = None) -> str:
    """
    하이브리드 프롬프트 생성 (DX 반복 강조 + JSON 구조화)

    Args:
        style_key: BACKGROUND_STYLES의 키 또는 "custom"
        custom_style: 커스텀 스타일 딕셔너리

    Returns:
        최적화된 하이브리드 프롬프트
    """
    style = custom_style if custom_style else BACKGROUND_STYLES.get(
        style_key, BACKGROUND_STYLES["minimal_industrial"]
    )
    T = HYBRID_TEMPLATE

    return f"""EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
The person's size must be IDENTICAL to input.

MODEL PRESERVATION (100% IDENTICAL):
- FACE: {T['preservation']['person']['face']}
- BODY: {T['preservation']['person']['body']}
- CLOTHING: {T['preservation']['person']['clothing']}
- SCALE: {T['preservation']['person']['scale']}
- CRITICAL: {T['preservation']['person']['critical_rule']}

PHYSICS CONSTRAINTS:
- Lighting direction: {T['physics']['lighting']['direction']}
- Lighting intensity: {T['physics']['lighting']['intensity']}
- Color temperature: {T['physics']['lighting']['color_temperature']}
- Perspective: {T['physics']['perspective']['horizon_line']}
- Shadows: {T['physics']['shadows']['direction']}, {T['physics']['shadows']['softness']}

BACKGROUND SPECIFICATION:
- Location: {style['location']}
- Materials: {style['materials']}
- Color palette: {style['color_palette']}
- Atmosphere: {style['atmosphere']}
- Lighting style: {style['lighting_style']}

OUTPUT REQUIREMENTS:
- Resolution: {T['technical']['resolution']}
- Aspect ratio: {T['technical']['aspect_ratio']}
- Quality: {T['technical']['quality']}"""
```

### 간결 버전 (테스트/빠른 사용)

```python
def build_simple_hybrid_prompt(background: str, mood: str = "") -> str:
    """간결한 하이브리드 프롬프트 (필수 요소만)"""
    return f"""EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
PERSON PRESERVATION (100% IDENTICAL)

PHYSICS: Match original lighting direction, intensity, color temperature

BACKGROUND: {background}
MOOD: {mood if mood else 'Natural, professional'}
QUALITY: Professional photography, seamless compositing"""
```

## 브랜드 DNA 프롬프트 주입

```python
BRAND_DNA = {
    "mlb": {
        "style": "Streetwear, youth culture, sporty casual",
        "colors": "Team colors, bold graphics",
        "mood": "Energetic, confident, urban",
        "keywords": ["street", "sporty", "logo prominent", "youth culture"]
    },
    "discovery": {
        "style": "Outdoor technical, gorpcore, functional",
        "colors": "Earth tones, technical colors",
        "mood": "Adventure, exploration, authentic",
        "keywords": ["outdoor", "technical", "functional", "adventure"]
    },
    "duvetica": {
        "style": "Italian luxury, premium down, refined",
        "colors": "Sophisticated neutrals, deep tones",
        "mood": "Elegant, understated luxury",
        "keywords": ["luxury", "Italian", "premium", "refined"]
    },
    "banillaco": {
        "style": "K-beauty, fresh, luminous",
        "colors": "Soft pastels, clean whites",
        "mood": "Fresh, youthful, glowing",
        "keywords": ["beauty", "glass skin", "luminous", "fresh"]
    }
}


def build_brand_prompt(base_prompt: str, brand: str) -> str:
    """브랜드 DNA를 프롬프트에 적용"""
    dna = BRAND_DNA.get(brand.lower(), {})
    if not dna:
        return base_prompt

    return f"""
## BRAND DNA: {brand.upper()}
- Style: {dna.get('style', '')}
- Color Palette: {dna.get('colors', '')}
- Mood: {dna.get('mood', '')}
- Keywords: {', '.join(dna.get('keywords', []))}

## PROMPT:
{base_prompt}

Ensure the final image reflects the brand's DNA while maintaining the subject's integrity.
"""
```

## 전체 프롬프트 조합

```python
def build_full_prompt(
    background_style: str,
    brand: str = None,
    clothing_analysis: dict = None,
    mood: str = None
) -> str:
    """전체 프롬프트 생성 (배경 + 브랜드 + 착장)"""
    # 1. 기본 배경 프롬프트
    base = build_hybrid_prompt(background_style)

    # 2. 브랜드 DNA 적용
    if brand:
        base = build_brand_prompt(base, brand)

    # 3. 착장 디테일 추가
    if clothing_analysis:
        base = build_clothing_prompt(base, clothing_analysis)

    return base
```

## 에디토리얼 프롬프트 JSON 구조 (9 섹션)

전문 화보 생성 시 아래 구조를 참조하여 상세 프롬프트를 구성합니다.

```json
{
  "meta": {
    "aspect_ratio": "4:5 / 3:4 / 9:16",
    "quality": "ultra_photorealistic_editorial / 8k",
    "camera": "Hasselblad H6D-100c / Canon EOS R5 / Sony A7R IV",
    "lens": "85mm f/1.4 / 50mm f/1.2 / 70-200mm f/2.8",
    "style": "high-end fashion / vogue aesthetic / editorial portrait"
  },
  "subject": {
    "gender": "여성/남성",
    "age": "20대 초반/중반/후반",
    "emotion": "차가운 자신감/따뜻한 미소/초연함",
    "face": { "shape": "", "skin": "", "eyes": "", "expression": "" },
    "hair": { "color": "", "length": "", "style": "", "texture": "" },
    "makeup": { "style": "", "eyes": "", "lips": "", "contour": "" }
  },
  "outfit": {
    "clothing_type": "", "color": "", "material": "",
    "fit": "", "brand_aesthetic": "", "details": ""
  },
  "pose": {
    "body_position": "", "body_angle": "", "head_angle": "",
    "arms": { "right": "", "left": "" },
    "hands": { "gesture": "", "details": "" }
  },
  "scene": {
    "location": "", "setting_type": "",
    "background": { "type": "", "color": "", "elements": [] },
    "atmosphere": ""
  },
  "lighting": {
    "type": "", "setup": "버터플라이/렘브란트/스플릿",
    "main_light": "", "fill_light": "", "rim_light": "",
    "color_temperature": "", "contrast": ""
  },
  "camera_perspective": {
    "framing": "클로즈업/미디엄/풀샷",
    "angle": "아이레벨/하이앵글/로우앵글",
    "depth_of_field": "", "lens_effect": ""
  },
  "technical": {
    "resolution": "8k/4k", "skin_texture": "초사실적",
    "color_grading": "", "sharpness": ""
  },
  "negative_prompt": [
    "만화", "일러스트레이션", "3D 렌더링", "낮은 품질",
    "나쁜 해부학", "왜곡된 손", "플라스틱 피부", "워터마크"
  ]
}
```

### 화보 스타일별 특징

| 스타일 | 조명 | 포즈 | 무드 |
|--------|------|------|------|
| 하이패션 에디토리얼 | 드라마틱 스튜디오, 강한 대비 | 역동적, 예술적 | 초연함, 강렬함 |
| 뷰티 에디토리얼 | 부드럽고 균일한 뷰티 라이팅 | 클로즈업, 얼굴 강조 | 빛나는, 완벽한 |
| 라이프스타일/럭셔리 | 자연광, 영화적 조명 | 우아한, 여유로운 | 세련됨, 여유로움 |
| 야외 로케이션 | 골든아워, 자연광 | 여행/모험 컨셉 | 자연스러운 |

### 카메라 & 렌즈 추천

| 촬영 유형 | 추천 카메라 | 추천 렌즈 |
|----------|------------|----------|
| 스튜디오 인물 | Hasselblad H6D | 85mm f/1.8, 100mm f/2.2 |
| 패션 풀샷 | Phase One | 50mm f/1.4, 35mm f/1.4 |
| 뷰티 클로즈업 | Canon EOS R5 | 100mm macro, 85mm f/1.2 |
| 야외 로케이션 | Sony A7R IV | 70-200mm f/2.8, 24-70mm f/2.8 |

### 조명 셋업 가이드

| 셋업 | 효과 | 적합한 상황 |
|------|------|------------|
| 버터플라이 | 대칭적, 글래머러스 | 뷰티, 글램 |
| 렘브란트 | 드라마틱, 예술적 | 드라마틱 인물 |
| 루프 | 자연스러운 그림자 | 일반 인물 |
| 스플릿 | 강한 대비, 미스터리 | 무드 촬영 |
| 하이키 | 밝고 깨끗함 | 뷰티, 상업 |
| 로우키 | 어둡고 분위기 있는 | 패션, 아트 |

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Step 5: 이미지 생성 (Gemini 3 Pro)                            ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

# ╔══════════════════════════════════════════════╗
# ║   절대 규칙: gemini-3-pro-image-preview ONLY ║
# ╚══════════════════════════════════════════════╝

```python
# 절대 금지
IMAGE_MODEL = "gemini-2.0-flash-exp-image-generation"  # 금지!
IMAGE_MODEL = "gemini-2.0-flash"  # 금지!
IMAGE_MODEL = "gemini-2.5-flash"  # 텍스트 전용, 금지!

# 무조건 이것만 사용
IMAGE_MODEL = "gemini-3-pro-image-preview"
```

**이유**:
- `gemini-2.0` 계열: 인물 축소, 배경 합성 품질 낮음, 색감 불일치
- `gemini-2.5-flash-image`: 속도/효율성 최적화, 최대 1024px만 지원
- `gemini-3-pro-image-preview`: 전문 애셋 제작, **최대 4K 지원**, 고급 추론

**위반 시**: 생성된 이미지 전부 삭제 후 재생성 필요

## Gemini 3 Pro 핵심 기능

| 기능 | 설명 |
|------|------|
| **고해상도 출력** | 1K, 2K, 4K 시각적 요소 생성 내장 |
| **고급 텍스트 렌더링** | 인포그래픽, 마케팅 애셋용 |
| **사고 모드 (Thinking)** | 복잡한 프롬프트 추론 후 최종 출력 |
| **최대 14개 참조 이미지** | 객체 6개 + 인물 5개 혼합 가능 |

## 해상도 설정

| 설정 | 해상도 (1:1 기준) | 용도 |
|------|------------------|------|
| `1K` | 1024x1024 | 테스트용 |
| `2K` | 2048x2048 | 일반 제작용 |
| `4K` | 4096x4096 | **고품질 최종 결과물** |

## Temperature 설정

| 용도 | Temperature | 설명 |
|------|-------------|------|
| 참조 이미지 보존 (착장/얼굴) | `0.2 ~ 0.3` | 착장 충실도 유지 |
| 브랜드컷 자유 생성 | `0.3 ~ 0.5` | 창의적 다양성 |
| 실험적/아트 | `0.7 ~ 0.9` | 다양한 결과 |

## 최소 생성 코드 (Quick Start)

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

# 1. API 설정
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 2. 이미지 생성
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[types.Content(role="user", parts=[types.Part(text="프롬프트")])],
    config=types.GenerateContentConfig(
        temperature=0.2,
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio="3:4", image_size="2K")
    )
)

# 3. 결과 저장
for part in response.candidates[0].content.parts:
    if part.inline_data:
        Image.open(BytesIO(part.inline_data.data)).save("output.png")
        break
```

## 참조 이미지 포함 시

```python
def pil_to_part(pil_img, max_size=1024):
    """PIL Image -> Gemini API Part (리사이즈 포함)"""
    if max(pil_img.size) > max_size:
        pil_img = pil_img.copy()
        pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    pil_img.save(buffer, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue()))

ref_img = Image.open("reference.png")
parts = [types.Part(text="프롬프트"), pil_to_part(ref_img)]

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[types.Content(role="user", parts=parts)],
    config=types.GenerateContentConfig(
        temperature=0.2,
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio="3:4", image_size="2K")
    )
)
```

## 유틸리티 함수

```python
from io import BytesIO
import base64

def base64_to_pil(base64_str: str) -> Image.Image:
    """프론트엔드 base64 -> PIL Image"""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    return Image.open(BytesIO(base64.b64decode(base64_str))).convert("RGB")

def pil_to_base64(pil_img: Image.Image, format: str = "PNG") -> str:
    """PIL Image -> 프론트엔드 base64"""
    buffer = BytesIO()
    pil_img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def get_aspect_ratio(width: int, height: int) -> str:
    """이미지 크기에서 가장 가까운 표준 비율 반환"""
    ratio = width / height
    ratios = {
        "1:1": 1.0, "2:3": 0.667, "3:2": 1.5, "3:4": 0.75, "4:3": 1.333,
        "4:5": 0.8, "5:4": 1.25, "9:16": 0.5625, "16:9": 1.778, "21:9": 2.333
    }
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))
```

## API 키 관리

```python
import os
import threading

def load_api_keys() -> list:
    """
    .env에서 API 키 로드
    형식: GEMINI_API_KEY=키1,키2,키3
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    api_keys = []

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if ',' in value:
                        api_keys.extend([k.strip() for k in value.split(',')])
                    else:
                        api_keys.append(value.strip())

    return api_keys if api_keys else [os.environ.get("GEMINI_API_KEY", "")]

# Thread-safe 키 로테이션
_key_lock = threading.Lock()
_key_index = 0
_api_keys = None

def get_next_api_key() -> str:
    """Thread-safe API 키 로테이션"""
    global _key_index, _api_keys
    if _api_keys is None:
        _api_keys = load_api_keys()
    with _key_lock:
        key = _api_keys[_key_index % len(_api_keys)]
        _key_index += 1
        return key
```

## API 재시도 로직

```python
import time
from google import genai

def call_gemini_with_retry(
    prompt_parts: list,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    temperature: float = 0.2,
    max_retries: int = 3
) -> Image.Image:
    """Gemini API 호출 + 자동 재시도 + 키 로테이션"""

    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=get_next_api_key())
            response = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=prompt_parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution
                    )
                )
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            raise Exception("이미지 생성 결과 없음")

        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ["429", "503", "overloaded", "timeout"]):
                wait_time = (attempt + 1) * 5
                print(f"[WARN] API 오류, {wait_time}초 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise

    raise Exception(f"최대 재시도 횟수({max_retries}) 초과")
```

## 에러 처리

```python
class ImageGenerationError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN", retryable: bool = False):
        self.message = message
        self.code = code
        self.retryable = retryable
        super().__init__(message)

def handle_error(e: Exception) -> dict:
    """표준 에러 응답 생성"""
    error_str = str(e).lower()

    error_map = {
        ("429", "rate"): ("API 사용량 초과", "RATE_LIMIT", True),
        ("503", "overloaded"): ("서버 과부하", "SERVER_OVERLOAD", True),
        ("timeout",): ("요청 시간 초과", "TIMEOUT", True),
        ("api key", "401"): ("API 키 오류", "AUTH_ERROR", False),
        ("safety", "blocked"): ("콘텐츠 정책 위반", "SAFETY_BLOCK", False),
    }

    for keywords, (msg, code, retryable) in error_map.items():
        if any(k in error_str for k in keywords):
            return {"success": False, "error": msg, "code": code, "retryable": retryable}

    return {"success": False, "error": str(e), "code": "UNKNOWN", "retryable": False}
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

## 파일 저장 패턴

```python
import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "Fnf_studio_outputs")

def save_image(
    pil_img: Image.Image,
    prefix: str = "generated",
    brand: str = None,
    workflow: str = None
) -> str:
    """
    이미지 저장 (브랜드/워크플로우별 폴더 구조)
    구조: Fnf_studio_outputs/{brand}/{workflow}/{prefix}_{timestamp}.png
    """
    out_dir = OUTPUT_DIR
    if brand:
        out_dir = os.path.join(out_dir, brand)
    if workflow:
        out_dir = os.path.join(out_dir, workflow)
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"{prefix}_{timestamp}.png")

    pil_img.save(filepath, "PNG")
    return filepath
```

## 출력 디렉토리 구조

```
output/
├── release/           # 합격 (total>=90, anatomy>=90, photorealism>=85)
├── review/            # 불합격 (수동 검토 필요)
├── manual_review/     # 자동 재시도 실패
│   └── diagnosis/     # JSON 진단 파일
├── logs/              # 파이프라인 리포트
└── pipeline_report_*.json
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   배경 스타일 프리셋                                              ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 콘크리트 스타일 (4종)

```python
CONCRETE_STYLES = {
    '1_raw': '''Raw exposed concrete wall with visible texture and form marks.
Industrial, authentic, slightly weathered. Like a construction site or parking garage.''',

    '2_smooth': '''Smooth polished concrete wall, minimalist and clean.
Modern architectural finish, subtle gray tones. Like a contemporary museum exterior.''',

    '3_metal': '''Concrete wall with metal elements - steel beams, industrial fixtures.
Urban industrial aesthetic, mixed materials. Like a modern warehouse district.''',

    '4_brutalist': '''Brutalist architecture style - massive concrete forms, geometric shapes.
Bold, monumental, dramatic shadows. Like a 70s government building or university.'''
}
```

## 도시 스타일 (7종)

```python
CITY_STYLES = {
    'california_affluent': '''Sunny California affluent neighborhood.
Warm golden light, palm trees, clean sidewalks, upscale residential area.
Beverly Hills / Malibu / Bel Air aesthetic.''',

    'california_retro': '''1970s California retro aesthetic.
Warm film tones, vintage signage, retro architecture.
Palm Springs / Venice Beach vintage vibe.''',

    'london_affluent': '''Upscale London neighborhood.
Classic Georgian townhouses, brick facades, manicured gardens.
Mayfair / Kensington / Chelsea aesthetic.''',

    'london_mayfair': '''London Mayfair district.
Elegant storefronts, wrought iron railings, cobblestone details.
Luxury retail and residential mix.''',

    'hollywood_simple': '''Clean Hollywood urban setting.
Modern American commercial buildings, clean lines.
Subtle urban backdrop, not distracting.''',

    'tokyo_shibuya': '''Tokyo Shibuya crossing area.
Neon lights, dense urban, modern Japanese architecture.
Dynamic, energetic atmosphere.''',

    'paris_marais': '''Paris Le Marais district.
Historic stone buildings, ornate balconies, charming streets.
Artistic, bohemian atmosphere.'''
}
```

## 스튜디오 스타일 (4종)

```python
STUDIO_STYLES = {
    'white_cyclorama': '''Pure white studio cyclorama background.
Seamless white curve, soft even lighting.
Clean, professional fashion photography setup.''',

    'gray_seamless': '''Medium gray seamless paper background.
Neutral, versatile, professional.
Classic editorial photography setup.''',

    'black_dramatic': '''Black studio background with dramatic lighting.
High contrast, moody, editorial.
Fashion magazine cover aesthetic.''',

    'natural_window': '''Studio with large natural window light.
Soft directional light, subtle shadows.
Bright, airy, lifestyle photography feel.'''
}
```

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   참조 이미지 처리                                                ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 참조 유형별 프롬프트

```python
REFERENCE_PROMPTS = {
    "style": """Based on the reference image, generate with:
- Similar lighting style and quality
- Same color palette and tonal range
- Matching mood and atmosphere""",

    "pose": """Based on the reference image, generate with:
- Same pose and body position
- Similar framing and composition
- Matching camera angle""",

    "background": """Based on the reference image, generate with:
- Same background environment
- Similar depth and spatial arrangement
- Matching ambient lighting""",

    "clothing": """Based on the reference garment image, the model wears this EXACT garment.

CRITICAL - Preserve EXACTLY:
- Garment shape and silhouette (DO NOT change)
- All colors including primary and secondary
- Logo/branding placement and design (DO NOT modify or remove)
- All features: hood, zipper, pockets, buttons
- Fabric texture and material appearance
- Fit style (oversized/regular/slim) and length

The garment must be IDENTICAL to reference.""",

    "all": """Based on the reference image, generate a new image that closely follows:
- Lighting: Match the light direction, quality, and shadows
- Colors: Use the same color palette and tonal balance
- Composition: Follow the framing and subject placement
- Mood: Capture the same atmosphere and feeling
- Style: Replicate the overall photographic style"""
}


def build_reference_prompt(base_prompt: str, reference_type: str = "style") -> str:
    """참조 이미지용 프롬프트 생성"""
    instruction = REFERENCE_PROMPTS.get(reference_type, REFERENCE_PROMPTS["style"])
    return f"{instruction}\n\nNow generate:\n{base_prompt}"
```

## 차량/객체 보존 배경 교체

```python
def build_background_swap_with_vehicle(
    style_desc: str,
    analysis: dict
) -> str:
    """배경 교체용 프롬프트 (차량 보존, 색상 매칭 포함)"""
    has_vehicle = analysis.get("has_vehicle", False)
    vehicle_desc = analysis.get("vehicle_description", "")
    ground = analysis.get("ground", {})
    lighting = analysis.get("lighting", {})
    color = analysis.get("color_grading", {})

    vehicle_instruction = ""
    if has_vehicle:
        vehicle_instruction = f"""
=== CRITICAL: VEHICLE PRESERVATION ===
THERE IS A VEHICLE IN THIS IMAGE: {vehicle_desc}
YOU MUST KEEP THIS VEHICLE EXACTLY AS IT IS.
DO NOT REMOVE, HIDE, OR MODIFY THE VEHICLE IN ANY WAY.
The vehicle is part of the original composition and MUST remain visible.
"""

    return f"""
CRITICAL: SEAMLESS COMPOSITING - NO STICKER EFFECT

SCALE 1:1 - DO NOT SHRINK THE PERSON.
Keep person exactly same size, pose, face, clothing.
{vehicle_instruction}
=== COLOR MATCHING (MOST IMPORTANT) ===
The background MUST match the original image's color grading:
- Overall warmth: {color.get('overall_warmth', 'neutral')}
- Saturation: {color.get('saturation', 'medium')}

Apply the SAME color grading to the background as the person has.
The entire image must look like ONE photo, not a composite.

=== GROUND CONTINUITY ===
- Ground material: {ground.get('material', 'concrete')}
- Ground color: {ground.get('color', 'gray')} ({ground.get('tone', 'neutral')} tone)
- The ground MUST continue seamlessly from foreground to background

=== LIGHTING MATCH ===
- Direction: {lighting.get('direction', 'front')}
- Intensity: {lighting.get('intensity', 'soft')}
- Color temperature: {lighting.get('color_temp', 'neutral')}

=== BACKGROUND STYLE ===
{style_desc}

=== PRESERVATION REQUIREMENTS ===
- KEEP ALL OBJECTS FROM ORIGINAL (especially vehicles!)
- Person size: IDENTICAL to input
- DO NOT add new people, cars, or objects
- DO NOT remove anything from the original scene

The goal: Look like it was actually shot at this location, not composited.
"""
```

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
│   └── backgrounds/                        # 배경 프리셋
├── (MLB마케팅)_시티미니멀_tyrone-lebon/     # 디렉터 페르소나
├── (MLB그래픽)_스트릿레전드_shawn-stussy/
├── (Discovery)_테크니컬유틸리티_yosuke-aizawa/
├── (Duvetica)_럭셔리장인_brunello-cucinelli/
├── (SergioTacchini)_실루엣혁명_hedi-slimane/
├── (Banillaco)_맑은뷰티_ahn-joo-young/
└── (제품연출)_한국힙이커머스_musinsa-29cm/
```

---

**작성일**: 2026-02-02
**버전**: 1.0
**통합 출처**: fnf-generate, 브랜드라우팅_brand-routing, 프롬프트패턴_prompt-patterns, 이미지생성기본_image-generation-base, 검증품질관리_validation-quality, 착장분석_clothing-analysis
**참고**: editorial-prompt, selfie-prompt는 이 스킬에 통합됨


---

# 배경교체 (Background Swap) 상세

# Background Swap - 배경 교체 통합 워크플로우

## 사용법

### Python
```python
from background_swap import swap

# 단일 이미지 (빠른 모드: 생성 + 품질 점수 리포트)
swap("photo.jpg", "캘리포니아 해변 석양")

# 고품질 모드 (생성 + 검증 + 진단 + 자동 재시도)
swap("photo.jpg", "파리 카페 테라스", enable_retry=True)

# 폴더 전체 + 시안 여러 장
swap("./images", "런던 브릭 골목", variations=3)

# 전체 옵션
swap("./images", "도쿄 네온 골목",
     output_dir="./tokyo_results",
     variations=2,
     enable_retry=True,
     max_retries=2,
     image_size="2K")

# Sweep 모드 (Fast 생성 + 사후 일괄 검증 + 자동 재생성)
swap("./images", "베를린 콘크리트 벽",
     enable_sweep=True, max_sweep_rounds=2,
     image_size="2K")
```

### CLI
```bash
# 빠른 모드
python background_swap.py photo.jpg "캘리포니아 해변 석양"

# 고품질 모드 (--retry)
python background_swap.py photo.jpg "파리 카페 테라스" --retry

# 전체 옵션
python background_swap.py ./images "런던 브릭 골목" -v 3 --retry --size 2K -o ./outputs

# Sweep 모드 (배치 생성 후 자동 검증 + 재생성)
python background_swap.py ./images "베를린 콘크리트 벽" --sweep --sweep-rounds 2
```

## 핵심 특징

- **프리셋 없음**: 원하는 배경 자유롭게 입력
- **검증된 프롬프트**: AutoRetryPipeline과 동일한 BASE_PRESERVATION_PROMPT 사용
- **7-criteria 품질 검증**: 모든 생성 결과에 품질 점수 포함
- **선택적 자동 재시도**: `enable_retry=True`로 품질 보장 모드 활성화
- **ONE UNIT 보존**: 인물+차량+오브젝트를 하나의 단위로 자동 보존
- **VFX 물리 분석**: 카메라, 조명, 포즈 의존성 자동 감지
- **VLM 배경 분석**: 참조 이미지에서 배경 설명 자동 추출
- **2.5K 출력**: 고해상도
- **병렬 처리**: 6 workers

## 모드 비교

| 항목 | Fast Mode (기본) | Quality Mode (`--retry`) | Sweep Mode (`--sweep`) |
|------|-----------------|--------------------------|------------------------|
| 생성 | 1회 | 최대 3회 (1 + 2 재시도) | 1회 (Fast) |
| 사후 검증 | 점수만 (참고) | 이미지별 통과/실패 | 배치 일괄 검증 |
| 재생성 | 없음 | 이미지별 진단+보강+재생성 | 실패분만 자동 재생성 (retry 포함) |
| Temperature | 0.2 고정 | 0.2 -> 0.1 -> 0.05 | 0.2 (초기) -> retry시 0.1 -> 0.05 |
| 속도 | 빠름 | 실패 시 느림 | Fast + 실패분만 추가 처리 |
| 용도 | 프롬프트 방향 테스트 | 소량 프로덕션 | **대량 프로덕션 (추천)** |
| Sweep 루프 | - | - | 검증->실패추출->재생성->재검증 (최대 N라운드) |

## 파라미터

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `input_path` | 이미지 파일 또는 폴더 | (필수) |
| `background` | 원하는 배경 설명 | (필수) |
| `output_dir` | 출력 폴더 | `./outputs` |
| `variations` | 시안 개수 | 1 |
| `max_images` | 최대 이미지 수 | 전체 |
| `max_workers` | 병렬 처리 수 | 6 |
| **`enable_retry`** | **자동 재시도 (진단+보강+재생성)** | **False** |
| **`max_retries`** | **최대 재시도 횟수** | **2** |
| **`image_size`** | **출력 해상도 (1K/2K/4K)** | **2K** |
| **`enable_sweep`** | **Sweep 모드 (사후 일괄 검증 + 자동 재생성)** | **False** |
| **`max_sweep_rounds`** | **최대 sweep 라운드 수** | **2** |

---

## Sweep 모드 워크플로우

대량 배치에서 Fast Mode의 속도와 Quality Mode의 품질 보증을 결합.

```
Step 1: Fast Mode 배치 생성 (전체 이미지)
  |
Step 2: 일괄 품질 검증 (원본 vs 생성 매칭)
  |--- 통과율 >= 95% --> 완료
  +--- 통과율 < 95%
  |
Step 3: QUALITY_ISSUE 이미지 추출
  |
Step 4: 실패분 재생성 (enable_retry=True, 진단+보강 포함)
  |
Step 5: 재검증 --> 통과율 체크
  |--- >= 95% 또는 max_rounds 도달 --> 완료
  +--- < 95% --> Step 3 반복
```

---

## 대화형 워크플로우

사용자와 자연스럽게 대화하며 배경 컨셉을 조율하고 생성하는 워크플로우.

### 전체 흐름 (6단계)

1. **컨셉 수집** - 사용자가 원하는 배경 파악
2. **포인트 정리** - 핵심 요소 정리해서 확인
3. **조율** - 피드백 반영하며 구체화
4. **테스트** - 샘플 생성해서 확인
5. **전체 적용** - 확정되면 배치 실행
6. **검수** - 품질 확인 및 리뷰 처리

### 실행 모드별 검수 규칙

**테스트 모드 (2~3장 샘플)**
- 검수 없이 빠르게 생성만. `max_retries=0` 설정, 검증/재시도 스킵
- 사용자가 직접 눈으로 확인하고 피드백
- 목적: 프롬프트 방향 확인, 빠른 이터레이션

**전체 배치 모드 (확정 후 전체 실행)**
- `max_retries=2` 설정, 자동 검증 + 재시도 활성화
- 완료 후 배치 검증 실행:
  ```bash
  python background_swap.py ./images "배경" --sweep
  ```
- 검수 기준: model_preservation=100 AND total >= 95
- QUALITY_ISSUE 이미지는 manual_review 폴더로 분류

### 4대 원칙

1. **영문 프롬프트 숨김** - 영문 프롬프트는 내부 처리용, 사용자에게 설명하지 않음
2. **이모지 금지** - 이모지 사용하지 않음
3. **친절한 척 금지** - 불필요한 존댓말이나 과도한 친절함 배제, 일만 함
4. **다른 스타일 제안 금지** - 사용자가 요청한 방향 외 다른 스타일 제안하지 않음

### 대화 예시

```
사용자: 베를린 느낌으로

Claude: 베를린 어떤 느낌? 모던? 클래식? 참조 있으면 보여줘.

사용자: 모던한 느낌

Claude: 모던 베를린.
        **포인트:**
        - 유리+철골 건축
        - 차가운 톤
        - 미래적
        이런 방향?

사용자: 좋아

Claude: 테스트 몇 장?

사용자: 2장

Claude: 2장 생성합니다.
```

### 내부 처리 (사용자에게 보이지 않음)

```python
# 1. 컨셉 이해
def understand_concept(user_input, reference_image=None):
    if reference_image:
        visual_analysis = analyze_reference_image(reference_image)
    points = extract_key_points(user_input, visual_analysis)
    return points

# 2. 영문 프롬프트 생성 (내부용)
def generate_internal_prompt(points, adjustments=None):
    base_prompt = translate_points_to_english(points)
    if adjustments:
        base_prompt = apply_adjustments(base_prompt, adjustments)
    return base_prompt

# 3. 테스트 이미지 선택
def select_test_images(input_dir, count):
    images = list_images(input_dir)
    selected = select_diverse_samples(images, count)
    return selected

# 4. 전체 배치 실행 (항상 AutoRetryPipeline 사용)
def run_full_batch(input_dir, output_dir, confirmed_prompt):
    from auto_retry_pipeline import AutoRetryPipeline
    pipeline = AutoRetryPipeline()
    result = pipeline.run(input_dir, output_dir, confirmed_prompt)
    return result
```

---

## 파이프라인 (전체 흐름)

```
입력 이미지
    |
    v
[1] 모델 물리 분석 (VFX) -----> 카메라/조명/포즈/설치논리 JSON
    |
    v
[2] 배경 분석 (VLM) ----------> 배경 텍스트 설명 또는 JSON
    |
    v
[3] 오브젝트 보존 프롬프트 ----> ONE UNIT 보존 지시문
    |
    v
[4] 프롬프트 조립 ------------> BASE_PRESERVATION_PROMPT + 분석 결과 + 배경 설명
    |
    v
[5] 이미지 생성 (Gemini) -----> temperature 0.2, 2K
    |
    v
[6] 7-criteria 품질 검증
    |--- PASS (total >= 95, model_preservation = 100) --> 완료 (release/)
    |--- FAIL --> [7] 실패 원인 진단 (6가지 이슈)
                      |
                      v
                  [8] 이슈별 프롬프트 보강
                      |
                      v
                  [9] 재생성 (temperature 0.1) --> [6] 재검증
                      (최대 2회 재시도, temperature 0.2 -> 0.1 -> 0.05)
```

---

## 모델 물리 분석 (VFX)

VFX 슈퍼바이저 관점에서 인물 사진의 물리적 제약 조건을 수치화하여, 배경 합성 시 공간적 불일치를 방지한다.

### 6대 분석 영역

| 영역 | 추출값 | 용도 |
|------|--------|------|
| Camera Geometry | horizon_y, perspective, focal_length_vibe | 원근/소실점 매칭 |
| Lighting Physics | direction_clock, elevation, softness, color_temp | 조명 방향/강도 매칭 |
| Pose Dependency | pose_type, support_required, support_direction | 지지대 필요 여부 판단 |
| Installation Logic | prop_detected, is_fixed_prop, forbidden_contexts | 소품 배치 규칙 |
| Physics Anchors | contact_points [x,y], shadow_casting_direction | 접지/그림자 정합 |
| Semantic Style | vibe, recommended_locations | 분위기 매칭 |

### ANALYSIS_PROMPT

```python
ANALYSIS_PROMPT = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한
물리적 제약 조건을 수치화된 데이터로 추출해야 합니다.

## 분석 집중 대상:

### 1. Camera Geometry (카메라 지오메트리)
- 수평선 높이: 이미지 높이 기준 0.0~1.0 정규화 좌표
- 원근감: eye-level | high-angle | low-angle
- 초점 거리 느낌: 35mm | 50mm | 85mm

### 2. Lighting Physics (조명 물리)
- 광원 방향: 시계 방향 1~12시
- 고도: low | mid | high
- 부드러움: 0.0 (hard) ~ 1.0 (soft)
- 색온도: K 값 또는 warm/neutral/cool

### 3. Pose Dependency (포즈 의존성) - CRITICAL
- 포즈 타입: standing | sitting | leaning | crouching | lying
- 지지대 필요 여부:
  - leaning -> 반드시 기댈 수 있는 벽/기둥/난간 필요
  - sitting -> 반드시 앉을 수 있는 의자/벤치/바닥 필요
  - standing -> 지지대 불필요
- 지지대 방향: behind | left | right | below
- 지지대 거리: close(접촉) | near(30cm이내) | far(30cm이상)

### 4. Installation Logic (설치 논리) - CRITICAL
- 소품 감지: 모델이 사용 중인 소품 식별
- 고정형 여부: 고정형 vs 이동형 판별
- 배치 규칙: 상세한 공간 논리
- 금지 컨텍스트: 소품이 자연스럽게 존재할 수 없는 장소

### 5. Physics Anchors (물리적 앵커)
- 접촉점: [x, y] 정규화 좌표
- 그림자 방향: [x, y] 벡터

### 6. Semantic Style (의미적 스타일)
- 분위기: street_editorial | studio | indoor | outdoor
- 추천 위치: ["subway", "lounge", "shop_interior"] 등
"""
```

### JSON 출력 형식

```json
{
  "geometry": {
    "horizon_y": 0.65,
    "perspective": "eye-level",
    "camera_height": "eye-level",
    "viewing_angle": "3/4",
    "focal_length_vibe": "50mm"
  },
  "lighting": {
    "direction_clock": "10",
    "elevation": "mid",
    "softness": 0.7,
    "color_temp": "5500K"
  },
  "pose_dependency": {
    "pose_type": "leaning",
    "support_required": true,
    "support_type": "wall or pillar",
    "support_direction": "behind-left",
    "support_distance": "close",
    "prompt_requirement": "Background MUST include a wall or pillar behind-left of the model for leaning"
  },
  "installation_logic": {
    "prop_detected": "고정형 외다리 의자",
    "is_fixed_prop": true,
    "placement_rule": "Must be against a wall. Cannot be placed in open spaces.",
    "forbidden_contexts": ["길 한복판", "야외 공원 중앙", "계단 중간"]
  },
  "physics_anchors": {
    "contact_points": [
      {"label": "left_foot", "coord": [0.3, 0.92]},
      {"label": "chair_base", "coord": [0.5, 0.88]}
    ],
    "shadow_casting_direction": [0.2, 0.8]
  },
  "semantic_style": {
    "vibe": "street_editorial",
    "recommended_locations": ["subway", "lounge", "shop_interior"]
  }
}
```

### analyze_model_physics() 함수

```python
import json
from google import genai
from google.genai import types
from PIL import Image

def analyze_model_physics(image_pil: Image.Image, api_key: str, additional_context: str = ""):
    """
    모델 이미지의 물리적/맥락적 키값을 추출.

    Returns:
        {"status": "success"|"error", "data": {...}, "generated_guideline": str}
    """
    client = genai.Client(api_key=api_key)

    # 1024px 다운샘플링 (공간 분석이므로 높은 해상도)
    max_size = 1024
    if max(image_pil.size) > max_size:
        image_pil.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    system_instruction = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한 물리적 제약 조건을 수치화된 데이터로 추출해야 합니다."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[types.Content(role="user", parts=[
            types.Part(text=ANALYSIS_PROMPT + f"\n{additional_context}"),
            image_pil
        ])],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            max_output_tokens=1200,
            response_mime_type="application/json"
        )
    )

    result = json.loads(response.text)
    guideline = build_background_guideline(result)

    return {"status": "success", "data": result, "generated_guideline": guideline}
```

### build_background_guideline() 함수

```python
def build_background_guideline(analysis_data: dict) -> str:
    """추출된 키값을 배경 생성 프롬프트 가이드라인으로 조립."""
    geom = analysis_data.get('geometry', {})
    light = analysis_data.get('lighting', {})
    pose = analysis_data.get('pose_dependency', {})
    logic = analysis_data.get('installation_logic', {})
    style = analysis_data.get('semantic_style', {})

    parts = []

    if geom:
        parts.append(f"Perspective: {geom.get('perspective', 'eye-level')} with vanishing point at y={geom.get('horizon_y', 0.5)}")
        if geom.get('focal_length_vibe'):
            parts.append(f"Focal length vibe: {geom['focal_length_vibe']}")

    if light:
        parts.append(f"Lighting: Source from {light.get('direction_clock', '12')} o'clock, {light.get('elevation', 'mid')} elevation, {light.get('softness', 0.5)} softness")
        if light.get('color_temp'):
            parts.append(f"Color temperature: {light['color_temp']}")

    # 포즈 의존성 - 가장 중요
    if pose and pose.get('support_required'):
        parts.append(f"CRITICAL - POSE SUPPORT: {pose.get('prompt_requirement', 'Support structure required')}")

    if logic:
        if logic.get('placement_rule'):
            parts.append(f"Spatial Logic: {logic['placement_rule']}")
        if logic.get('forbidden_contexts'):
            parts.append(f"Avoid: {', '.join(logic['forbidden_contexts'])}")

    if style and style.get('vibe'):
        parts.append(f"Style vibe: {style['vibe']}")

    return "Create a professional background. " + ". ".join(parts) + "."
```

---

## 배경 분석 (VLM)

배경 이미지를 구체적인 텍스트 설명으로 변환하여 프롬프트에 바로 사용할 수 있도록 한다.

### 분석 타입

| 분석 타입 | 출력 형식 | 용도 | 해상도 |
|----------|----------|------|--------|
| 기본 분석 | 텍스트 (2-4문장) | 이미지 생성 프롬프트 | 512px |
| 배경교체용 상세 분석 | JSON | 차량/바닥/색보정 매칭 | 1024px |
| 포토 디렉터 분석 | JSON | 합성 기획 (조명/그림자/색상) | 512px |

### BACKGROUND_ANALYSIS_PROMPT (기본)

```python
BACKGROUND_ANALYSIS_PROMPT = """You are a professional location scout and set designer. Analyze this background image and provide a DETAILED, SPECIFIC text description that can be used directly in image generation prompts.

## What to Analyze:
1. **Location Type**: What kind of place is this? (cafe, street, interior, outdoor, etc.)
2. **Specific Elements**: Furniture, architectural details, decorative items, plants, windows, doors, etc.
3. **Materials & Textures**: Wood, concrete, glass, fabric, metal, etc.
4. **Color Palette**: Dominant colors, accent colors, overall tone
5. **Lighting**: Natural light source, artificial lights, shadows, brightness
6. **Atmosphere**: Clean/minimal, cozy, industrial, luxury, casual, etc.

## Output Format:
Provide a SINGLE, DETAILED text description (2-4 sentences) that captures:
- The specific location and its key elements
- Materials and textures visible
- Color scheme and lighting
- Overall atmosphere

Example format:
"minimalist cafe interior, wooden table with terracotta legs, white built-in sofa, large open window, potted trees, warm natural light, beige/cream tones"

Be SPECIFIC and DETAILED. Use concrete nouns and descriptive adjectives.
Return ONLY the text description, no JSON, no markdown, no explanations."""
```

### analyze_background() 함수

```python
def analyze_background(image_pil: Image.Image) -> str:
    """배경 이미지를 구체적인 텍스트 설명으로 변환."""
    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)
    model = get_text_model()

    # 512px 다운샘플링
    image_part = pil_to_part(image_pil, max_size=512)

    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[
            types.Part(text=BACKGROUND_ANALYSIS_PROMPT),
            types.Part(text="\n\n[Background image to analyze]:"),
            image_part
        ])],
        config=types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.9,
            max_output_tokens=512
        )
    )

    # 마크다운 코드 블록 제거
    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join([l for l in lines if not l.strip().startswith("```")])

    return text.strip()
```

### BACKGROUND_SWAP_ANALYSIS_PROMPT (차량/바닥/색보정)

```python
BACKGROUND_SWAP_ANALYSIS_PROMPT = """
Analyze this photo for seamless background replacement. Return JSON only:

{
  "has_vehicle": true/false,
  "vehicle_description": "car/motorcycle/bicycle type and color if exists",
  "ground": {
    "material": "concrete/asphalt/sand/tile/etc",
    "color": "specific color like beige/gray/brown",
    "tone": "warm/neutral/cool"
  },
  "lighting": {
    "direction": "front/back/left/right/top",
    "intensity": "soft/medium/hard",
    "color_temp": "warm/neutral/cool"
  },
  "color_grading": {
    "overall_warmth": "warm/neutral/cool",
    "saturation": "low/medium/high"
  }
}
"""
```

### analyze_for_background_swap() 함수

```python
def analyze_for_background_swap(image_pil: Image.Image) -> dict:
    """배경 교체용 상세 분석 (차량 감지, 바닥 톤 매칭, 색보정 포함)."""
    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)

    image_part = pil_to_part(image_pil, max_size=1024)

    response = client.models.generate_content(
        model="gemini-3-flash-preview",  # 분석용
        contents=[types.Content(role="user", parts=[
            types.Part(text=BACKGROUND_SWAP_ANALYSIS_PROMPT),
            image_part,
        ])],
        config=types.GenerateContentConfig(temperature=0.1)
    )

    text = response.text
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()

    return json.loads(text.strip())
```

### 분석 결과 활용

```python
analysis = analyze_for_background_swap(source_image)

# 차량 보존 지시문 생성
if analysis.get("has_vehicle"):
    vehicle_instruction = f"""
=== CRITICAL: VEHICLE PRESERVATION ===
THERE IS A VEHICLE IN THIS IMAGE: {analysis['vehicle_description']}
YOU MUST KEEP THIS VEHICLE EXACTLY AS IT IS.
DO NOT REMOVE, HIDE, OR MODIFY THE VEHICLE IN ANY WAY.
"""

# 바닥 연속성 지시문 생성
ground = analysis.get("ground", {})
ground_instruction = f"""
=== GROUND CONTINUITY ===
- Ground material: {ground.get('material', 'concrete')}
- Ground color: {ground.get('color', 'gray')} ({ground.get('tone', 'neutral')} tone)
- The ground MUST continue seamlessly from foreground to background
"""

# 색보정 매칭 지시문 생성
color = analysis.get("color_grading", {})
color_instruction = f"""
=== COLOR MATCHING ===
- Overall warmth: {color.get('overall_warmth', 'neutral')}
- Saturation: {color.get('saturation', 'medium')}
Apply the SAME color grading to the background as the person has.
"""
```

### 포토 디렉터 상세 분석 결과 형식 (JSON)

```json
{
  "source_style": {
    "sharpness": "sharp",
    "contrast": "medium",
    "saturation": "natural",
    "photographic_style": "editorial",
    "depth_of_field": "shallow"
  },
  "environment": {
    "location_type": "cafe",
    "tone_mood": "calm and modern minimalist",
    "color_palette": "cool gray tones with subtle blue undertones",
    "ground_surface": "concrete",
    "wall_textures": "smooth concrete"
  },
  "lighting_design": {
    "key_light": "natural window light from left",
    "fill_light": "ambient light fills shadows softly",
    "rim_light": "subtle edge highlights from window"
  },
  "shadow_design": {
    "ground_shadow": "soft shadow falls to the right, about 2 feet long",
    "body_shadow": "soft shadows on person to match environment"
  },
  "color_design": {
    "temperature": "slightly cool to match background",
    "environment_reflection": "subtle blue-gray tones reflected on person"
  },
  "ground_connection": {
    "shadow_type": "soft ambient occlusion",
    "surface_material": "concrete",
    "surface_condition": "smooth"
  }
}
```

---

## 오브젝트 보존 (ONE UNIT)

### 핵심 개념

```
문제: 인물과 차를 따로 보존하라고 하면 AI가 혼란 -> 둘 다 변형됨
해결: 인물+차+오브젝트 = 하나의 FOREGROUND SUBJECT로 묶어서 보존
```

배경교체 스킬은 이 보존 프롬프트를 **자동으로 포함**한다. 사용자가 별도로 호출할 필요 없음.

### 3단계 보존 레벨

**BASIC - 모든 배경교체에 기본 적용**
```
FRAMING: Model fills 90% of the frame height. KEEP THIS.
DO NOT make the model smaller. DO NOT zoom out.

The BLACK CAR (if exists) is a PROP, not background.

COPY EXACTLY FROM INPUT:
- Model size in frame (CRITICAL - must be same %)
- Model face, pose, clothes, hair
- Any vehicle/object near model (color, shape, position)

REPLACE: Background only
```

**DETAILED - 차량이 확인된 경우**
```
=== FOREGROUND SUBJECT PRESERVATION (CRITICAL) ===

SUBJECT = Person + Vehicle as ONE CONNECTED UNIT
Treat them as a SINGLE subject, NOT separate objects.

DO NOT MODIFY THE SUBJECT:
- Person: exact face, body, clothes, pose, hair
- Vehicle: exact color, model, wheels, reflections, position
- Their spatial relationship: distance, angle, contact points
- Combined shadows on ground

The person and vehicle are ONE COMPOSITION.
Moving, resizing, or modifying either one breaks the composition.

ONLY REPLACE: Background environment behind this unit
```

**FULL - 최대 강도**
```
=== FOREGROUND SUBJECT = ONE UNIT (DO NOT SEPARATE) ===

Everything in foreground (person + vehicle + objects) = SINGLE SUBJECT
This is NOT "person" + "car". This is ONE connected unit.

ABSOLUTE PRESERVATION:
- Person: 100% identical (face, body, clothing, pose, expression)
- Vehicle (if exists): 100% identical (color, shape, wheels, reflections)
- Objects (if exist): 100% identical
- All contact points and spatial relationships: LOCKED
- All shadows: preserve direction and shape

NEVER:
- Separate person from vehicle
- Move person relative to vehicle
- Change vehicle color/shape/size
- Add new people, cars, or objects

ONLY CHANGE: Background behind the foreground subject
```

### Python 사용법

```python
PRESERVATION_BASIC = """
FOREGROUND SUBJECT = ALL foreground elements as ONE UNIT
(person, vehicle, objects - whatever exists in foreground)

PRESERVE 100% IDENTICAL:
- Every person: face, body, clothing, pose, hair, expression
- Every object/vehicle near the person (if any): color, shape, position
- Spatial relationships between all foreground elements

ONLY CHANGE: Background environment
"""

# 프롬프트에 삽입
full_prompt = f"""
{PRESERVATION_BASIC}

BACKGROUND: {your_background_description}
"""
```

---

## 프롬프트 구조

검증된 `BASE_PRESERVATION_PROMPT` 사용 (AutoRetryPipeline과 동일):

```
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

MODEL PRESERVATION (100% IDENTICAL):
- FACE: identical to input - same features, expression, hair
- BODY: identical to input - same pose, proportions, position
- CLOTHING: identical to input - same garments, colors, logos, details
- SCALE: identical to input - person height ratio must match exactly

PHYSICS CONSTRAINTS:
- Match original lighting direction and intensity
- Match original perspective and horizon line
- Shadows consistent with light source

OUTPUT: Professional fashion photography, seamless compositing, no artifacts

BACKGROUND CHANGE:
{사용자 입력 배경 설명}
```

분석 결과가 있을 경우 추가되는 요소:

```python
# VFX 분석 결과 통합
if model_analysis:
    prompt += f"\n{model_analysis['generated_guideline']}"

# 차량 감지 시 ONE UNIT 보존 삽입
if bg_analysis.get("has_vehicle"):
    prompt = PRESERVATION_DETAILED + "\n" + prompt

# 바닥/색보정 매칭
prompt += ground_instruction + color_instruction
```

---

## 품질 검증 (7-criteria)

모든 생성 결과에 아래 7개 항목의 검수 점수가 포함된다.

| 항목 | 비중 | 설명 |
|------|------|------|
| model_preservation | 30% | 인물 보존 (포즈, 얼굴, 의상, 스케일) |
| physics_plausibility | 15% | 물리적 타당성 (앉기->의자, 기대기->벽) |
| ground_contact | 13% | 접지감 (발/그림자 자연스러움) |
| lighting_match | 12% | 조명 방향/강도 일치 |
| prop_style_consistency | 12% | 소품-배경 스타일 일치 |
| edge_quality | 10% | 인물 경계면 깔끔함 |
| perspective_match | 8% | 카메라 앵글/원근 일치 |

### PASS 기준
- `model_preservation = 100` (필수)
- `physics_plausibility >= 50` (필수)
- `total >= 95`

### 검증 스크립트

검증은 background_swap.py에 내장되어 있음. 별도 스크립트 불필요.

```bash
# Quality Mode (이미지별 검증 + 자동 재시도)
python background_swap.py photo.jpg "배경" --retry

# Sweep Mode (배치 일괄 검증 + 실패분 재생성)
python background_swap.py ./images "배경" --sweep
```

### 배치 결과 요약

```
=== Quality Check Report ===
Total: 66 images
RELEASE_READY: 52 (78.8%)
QUALITY_ISSUE: 14 (21.2%)

Top Issues:
1. lighting_match: 12 images
2. perspective_match: 8 images
3. ground_contact: 5 images
```

### 이전 5-criteria 시스템과의 관계

quality-check 스킬이 사용하던 이전 5-criteria 체계(model_preservation 35%, object_preservation 25%, color_temperature 20%, lighting_match 15%, edge_quality 10%)는 현재 7-criteria 시스템으로 대체됨. 이전 `object_preservation` 항목은 `prop_style_consistency` + ONE UNIT 보존 프롬프트로 흡수되었고, `color_temperature`는 `lighting_match` + VLM 배경분석의 `color_grading`으로 커버된다.

---

## 재시도 워크플로우 (enable_retry=True)

```
1. 생성 (temperature=0.2)
   |
2. 7-criteria 품질 검증
   |-- PASS -> 완료
   +-- FAIL |
3. 실패 원인 진단 (6가지 이슈 감지)
   - POSE_MISMATCH, FACE_CHANGED, SCALE_SHRUNK
   - PHYSICS_ERROR, CLOTHING_CHANGED, PROP_STYLE_MISMATCH
   |
4. 이슈별 프롬프트 보강
   - 각 이슈에 맞는 전용 강화 템플릿 적용
   |
5. 재생성 (temperature=0.1)
   |
6. 재검증 -> 실패 시 3-5 반복 (temperature=0.05)
```

---

## 배경 예시

```python
# 도시
swap(img, "캘리포니아 해변 석양과 팜트리")
swap(img, "파리 에펠탑이 보이는 카페 테라스")
swap(img, "뉴욕 브루클린 브릭월 앞")

# 자연
swap(img, "눈 내리는 스위스 산장")
swap(img, "하와이 열대 해변")

# 실내
swap(img, "모던 화이트 스튜디오")
swap(img, "럭셔리 호텔 로비")
```

---

## 모델 / 환경 설정

`gemini-3-pro-image-preview` 사용 (품질 보장)

```bash
# .env 파일
GEMINI_API_KEY=key1,key2,key3
```

여러 키 쉼표로 구분하면 자동 로테이션

---

## 아키텍처

`core/` 공통 모듈과 `auto_retry_pipeline/` 컴포넌트를 공유:

```
core/
+-- utils.py      -> ImageUtils, ApiKeyManager
+-- prompts.py    -> BASE_PRESERVATION_PROMPT, build_generation_prompt
+-- config.py     -> PipelineConfig

auto_retry_pipeline/
+-- generator.py  -> ImageGenerator (생성)
+-- validator.py  -> QualityValidator (검증)
+-- diagnoser.py  -> IssueDiagnoser (진단) [retry only]
+-- enhancer.py   -> PromptEnhancer (보강) [retry only]
```

---

## DO/DON'T

### DO

- 1024px 다운샘플링 (모델 물리 분석 - 공간 분석이므로 높은 해상도)
- 512px 다운샘플링 (배경 분석 - 텍스트 추출이므로 낮은 해상도 가능)
- `response_mime_type="application/json"` (VFX 분석 시 JSON 강제 반환)
- temperature 0.1 (VFX 분석 - 일관된 수치 추출)
- temperature 0.2 (배경 분석 - 정확한 분석)
- temperature 0.2 (이미지 생성 - 첫 시도)
- ONE UNIT 개념 적용 (인물+차량+오브젝트 = 하나의 덩어리)
- 항상 `AutoRetryPipeline` 사용 (background_swap.py 아님)
- 영문 프롬프트는 내부 처리용으로만 (사용자에게 노출하지 않음)
- 배치 모드에서 반드시 7-criteria 품질 검증 실행 (--retry 또는 --sweep)

### DON'T

- 원본 해상도 그대로 VLM에 전달 (다운샘플링 필수)
- 높은 temperature로 VFX 수치 추출 (일관성 저하)
- 인물과 차량을 개별 보존 지시 (반드시 ONE UNIT)
- 설치 논리 무시 (고정형 의자가 길 한복판에 있으면 부자연스러움)
- 접촉점 좌표 누락 (배경 합성 시 접지 불일치)
- 금지 컨텍스트 누락 (물리적으로 불가능한 배경 생성)
- 사용자에게 영문 프롬프트 설명
- 이모지 사용
- 과도한 친절함
- 사용자가 요청하지 않은 다른 스타일 제안
- 이전 5-criteria 기준 사용 (7-criteria가 최신)

---

## 관련 스킬

- **브랜드컷_brand-cut**: 화보컷 생성 워크플로우

---

**통합일**: 2026-02-02
**통합 출처**: 배경교체, 배경분석, 배경생성워크플로우, 오브젝트보존, quality-check, 모델분석


---

# 일상컷 (Daily Casual) 상세

# 일상컷 - 캐주얼 데일리 사진 생성 워크플로


> **템플릿 파일**: `prompt-templates/daily_casual.json`

## 컨셉

셀피(본인 촬영)가 아닌, **다른 사람이 찍어주거나 타이머/거치대로 촬영한 캐주얼 일상 사진**.
브랜드컷(에디토리얼)과 셀피의 중간 지점으로, 자연스럽고 꾸미지 않은 느낌이 핵심.

### 셀피 vs 일상컷 차이

| 항목 | 셀피 | 일상컷 |
|------|------|--------|
| 촬영자 | 본인 (팔 뻗기) | 타인 또는 타이머 |
| 프레이밍 | 얼굴 클로즈업~상반신 | 상반신~전신 다양 |
| 앵글 | 높은 각도 (셀카 앵글) | eye-level 또는 다양한 각도 |
| 렌즈 왜곡 | 강한 wide-angle | 보통 수준 |
| 포즈 | 셀카 포즈 | 자연스러운 일상 동작 |
| 배경 | 보케 처리 | 배경 인식 가능 |

## 사용법

```
/일상컷_daily-casual MLB 카페에서 앉아있는 사진 3장
/일상컷_daily-casual Discovery 거리 걸어가는 스트릿 컷 2장
/일상컷_daily-casual Banillaco 골든아워 공원 산책 4장
/일상컷_daily-casual 남친짤 느낌 데이트룩 카페 2장
```

### Python 워크플로 (API 연동용)

```python
from workflow import ImageGenerationWorkflow

workflow = ImageGenerationWorkflow(api_key="YOUR_API_KEY")

result = workflow.generate(
    user_input="MLB 카페에서 앉아있는 사진 3장",
    template="daily_casual",        # 일상컷 템플릿
    model_images=[face_pil],         # 얼굴 유지용
    outfit_images=[outfit_pil],      # 착장 반영용
    input_vars={
        "gender": "여성",
        "age": "20대 초반",
        "shot_type": "sitting_candid",  # AI가 자동 선택 또는 지정
        "location": "카페 내부",
        "lighting": "indoor_ambient"
    },
    count=3,
    max_workers=4
)
```

---

# 파이프라인 (5단계)

```
사용자 입력 → Step 1: 브랜드 라우팅 + 템플릿 로드
            → Step 2: AI 판단 (shot_type, pose, lighting 자동 선택)
            → Step 3: 프롬프트 조립
            → Step 4: 이미지 생성 (Gemini 3 Pro, 2K)
            → Step 5: 검증 + 결과 반환
```

---

## Step 1: 브랜드 라우팅 + 템플릿 로드

사용자 요청에서 브랜드를 감지하고, `daily_casual.json` 템플릿과 해당 brand DNA를 로드합니다.

| 키워드 | 브랜드 | DNA 파일 |
|--------|--------|----------|
| MLB, 엠엘비 | MLB Marketing | `mlb-marketing.json` |
| Discovery, 디스커버리 | Discovery | `discovery.json` |
| Duvetica, 두베티카 | Duvetica | `duvetica.json` |
| Banillaco, 바닐라코, 뷰티 | Banillaco | `banillaco.json` |
| SergioTacchini, 세르지오 | Sergio Tacchini | `sergio-tacchini.json` |

## Step 2: AI 판단 (자동 선택)

`daily_casual.json`의 `_ai_guide`에 따라 사용자 요청에서 키워드를 파악하고 최적 조합을 선택합니다.

### Shot Type 자동 매칭

| 사용자 키워드 | → shot_type |
|---------------|-------------|
| "친구가 찍어준", "스냅" | `friend_snap` |
| "남친짤", "여친짤", "데이트" | `boyfriend_shot` |
| "걸어가는", "거리", "스트릿" | `walking_candid` |
| "카페", "앉아있는", "벤치" | `sitting_candid` |
| "OOTD", "전신", "코디" | `timer_shot` |
| "뒷모습", "감성", "풍경" | `over_shoulder` |

### Pose 자동 매칭

| 사용자 키워드 | → pose_type |
|---------------|-------------|
| "서있는", "기본" | `natural_stand` |
| "걷는", "걸어가는" | `walking` |
| "기대", "벽", "쿨한" | `leaning` |
| "앉아", "카페" | `sitting_casual` |
| "캔디드", "자연스러운" | `looking_away` |
| "웃는", "밝은" | `laughing` |

### Lighting 자동 매칭

| 사용자 키워드 | → lighting |
|---------------|------------|
| "야외", "맑은 날" | `outdoor_daylight` |
| "석양", "노을", "감성" | `golden_hour` |
| "흐린", "부드러운" | `overcast` |
| "카페", "실내" | `indoor_ambient` |
| "밤", "네온" | `night_street` |

## Step 3: 프롬프트 조립

선택된 shot_type, pose, lighting과 brand DNA를 병합하여 Gemini API 프롬프트를 조립합니다.

### 프롬프트 구조
```
[shooting_style] + [device] + [subject 정보] + [attire/brand] +
[pose prompt_fragment] + [shot_type 특성] + [lighting setup] +
[environment] + [technical specs] + [brand_injection]
```

### 예시 조립 결과
```
candid daily life photo, taken by friend or timer, iPhone 15 Pro 24mm f/1.9,
young Korean woman, early 20s, realistic skin texture natural pores,
wearing MLB casual everyday style, sitting casually on cafe chair legs crossed,
friend at eye-level 1-2 meters distance, mixed window light and indoor ambient,
cafe interior warm atmosphere, 2K resolution, smartphone natural bokeh,
in the style of MLB Marketing
```

## Step 4: 이미지 생성

```python
# Gemini API 호출
config = types.GenerateContentConfig(
    temperature=0.3,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="4:5",   # 일상컷 기본 (9:16도 가능)
        image_size="2K"
    )
)
```

| 설정 | 값 | 비고 |
|------|-----|------|
| 모델 | `gemini-3-pro-image-preview` | 필수 |
| temperature | 0.3 | 자연스러움 확보 |
| 비율 | 4:5 (기본) / 9:16 (세로) / 3:4 | 사용자 지정 가능 |
| 해상도 | 2K | 프로덕션 품질 |

## Step 5: 검증

생성된 이미지의 품질을 VLM으로 검증합니다.

### 일상컷 전용 검증 기준

| 기준 | 가중치 | 설명 |
|------|--------|------|
| 자연스러움 | 30% | 포즈, 표정이 자연스러운가? 모델 느낌이 아닌가? |
| 인물 보존 | 25% | 얼굴/체형이 원본과 일치하는가? |
| 카메라 리얼리즘 | 20% | 실제 폰/디카로 찍은 것처럼 보이는가? |
| 착장 반영 | 15% | 의상이 정확히 반영되었는가? |
| 배경 적합성 | 10% | 요청한 장소/분위기와 맞는가? |

### 실패 시 자동 재시도
- 자연스러움 < 80: 포즈/표정 프롬프트 보강
- 카메라 리얼리즘 < 80: 폰 카메라 특성 프롬프트 강화
- temperature 하향: 0.3 → 0.2 → 0.15


---

# 시딩UGC (Seeding UGC) 상세

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


---

**통합일**: 2026-02-03
**통합 출처**: brand-cut, background-swap, daily-casual, seeding-ugc
