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
