---
name: image-gen-reference
description: 이미지 생성 워크플로 구축 시 참조하는 범용 레퍼런스. Gemini API 사용법, 프롬프트 패턴, 배경 스타일, 유틸리티 함수 등 워크플로 비종속적인 기초 지식을 담고 있습니다.
---

# 이미지 생성 레퍼런스 (Image Generation Reference)

> 이 스킬은 **특정 워크플로에 종속되지 않는 범용 기초 지식**입니다.
> 새 워크플로를 만들 때 반드시 이 파일을 먼저 참조하세요.
>
> 워크플로별 스킬:
> - 브랜드 패션 화보: `브랜드컷_brand-cut/SKILL.md`
> - 배경 교체: `배경교체_background-swap/SKILL.md`

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Section 1: Gemini 모델 & 절대 규칙                             ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 모델 선택 (절대 규칙)

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

## Temperature 가이드

| 용도 | Temperature | 설명 |
|------|-------------|------|
| 참조 이미지 보존 (착장/얼굴) | `0.2 ~ 0.3` | 착장 충실도 유지 |
| 브랜드컷 자유 생성 | `0.3 ~ 0.5` | 창의적 다양성 |
| 실험적/아트 | `0.7 ~ 0.9` | 다양한 결과 |

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Section 2: API 코드 패턴                                      ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## Quick Start (최소 생성 코드)

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
# ║   Section 3: 프롬프트 패턴 (Hybrid DX+JSON)                    ║
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

## 하이브리드 프롬프트 템플릿 (HYBRID_TEMPLATE)

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

## 필수 DX 키워드 (보존 필요 시)

```
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1
DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
PERSON PRESERVATION (100% IDENTICAL)
```

## 배경 스타일 라이브러리 (BACKGROUND_STYLES)

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
```

## 프롬프트 생성 함수

```python
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

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Section 4: 에디토리얼 프롬프트 구조                            ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 9섹션 JSON 구조

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

## 화보 스타일별 특징

| 스타일 | 조명 | 포즈 | 무드 |
|--------|------|------|------|
| 하이패션 에디토리얼 | 드라마틱 스튜디오, 강한 대비 | 역동적, 예술적 | 초연함, 강렬함 |
| 뷰티 에디토리얼 | 부드럽고 균일한 뷰티 라이팅 | 클로즈업, 얼굴 강조 | 빛나는, 완벽한 |
| 라이프스타일/럭셔리 | 자연광, 영화적 조명 | 우아한, 여유로운 | 세련됨, 여유로움 |
| 야외 로케이션 | 골든아워, 자연광 | 여행/모험 컨셉 | 자연스러운 |

## 카메라 & 렌즈 추천

| 촬영 유형 | 추천 카메라 | 추천 렌즈 |
|----------|------------|----------|
| 스튜디오 인물 | Hasselblad H6D | 85mm f/1.8, 100mm f/2.2 |
| 패션 풀샷 | Phase One | 50mm f/1.4, 35mm f/1.4 |
| 뷰티 클로즈업 | Canon EOS R5 | 100mm macro, 85mm f/1.2 |
| 야외 로케이션 | Sony A7R IV | 70-200mm f/2.8, 24-70mm f/2.8 |

## 조명 셋업 가이드

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
# ║   Section 5: 브랜드 DNA 프롬프트 주입                            ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 브랜드별 DNA 키워드

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
```

## DNA 프롬프트 적용 함수

```python
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

## 전체 프롬프트 조합 함수

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

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Section 6: 파일 저장 & 출력 규칙                               ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

## 출력 디렉토리 구조

```
output/
├── release/           # 품질 검증 통과
├── review/            # 검토 필요
├── manual_review/     # 수동 검토
│   └── diagnosis/     # 진단 파일
└── logs/              # 파이프라인 리포트
```

## 파일 저장 함수

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

---

<br/>

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   Section 7: 배경 스타일 프리셋                                  ║
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
# ║   Section 8: 참조 이미지 처리                                    ║
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

# 이 레퍼런스를 참조하는 스킬들

| 스킬 | 용도 | 이 레퍼런스 활용 부분 |
|------|------|---------------------|
| `브랜드컷_brand-cut` | 브랜드 패션 화보 | 전체 |
| `배경교체_background-swap` | 배경 교체 | Section 1-3, 7-8 |
| (향후 추가 워크플로) | - | Section 1-2 (최소) |
