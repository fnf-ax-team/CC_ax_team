---
name: ecommerce
description: 이커머스용 모델 이미지 생성 - 상세페이지 및 룩북 전용
user-invocable: true
trigger-keywords: ["이커머스", "상세페이지", "룩북", "모델 이미지", "커머스"]
---

# 이커머스 (Ecommerce) - 상업용 모델 이미지 생성

> 얼굴 + 착장 이미지 → 이커머스 모델 이미지 생성

---

## 핵심 컨셉

```
┌─────────────────────────────────────────────────────────────────┐
│  이커머스 모델 이미지 = 착장 정확도 최우선 + 클린 배경          │
└─────────────────────────────────────────────────────────────────┘
```

### 목적

| 항목 | 설명 |
|------|------|
| **용도** | 온라인 쇼핑몰 상세페이지, 룩북 |
| **핵심** | 착장을 정확히 보여주는 것이 최우선 |
| **스타일** | 스튜디오 조명, 클린한 배경, 상업적 완성도 |

### 우선순위

| 순위 | 항목 | 설명 |
|------|------|------|
| **1 (최우선)** | **착장 정확도** | 색상, 디테일, 로고, 실루엣 완벽 재현 |
| **2** | **상업적 품질** | 프로페셔널한 조명, 포즈, 구도 |
| 3 | 얼굴 동일성 | 동일 모델 사용 (브랜드컷보다 낮음) |
| 4 | 배경 | 깔끔한 단색 또는 미니멀 배경 |

---

## 모델 설정

```python
from core.config import IMAGE_MODEL, VISION_MODEL

IMAGE_MODEL = "gemini-3-pro-image-preview"  # 이미지 생성
VISION_MODEL = "gemini-3-flash-preview"     # 착장 분석 및 검수
```

---

## 워크플로 (4단계)

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 입력 수집                                                │
│  1. 얼굴 폴더 경로                                                 │
│  2. 착장 이미지 폴더 경로                                          │
│  3. 포즈 프리셋 선택 (클릭)                                        │
│  4. 배경 프리셋 선택 (클릭)                                        │
│  5. 생성 장수: 1-10                                               │
│  6. 비율: 3:4(기본) / 1:1 / 4:5 / 9:16                           │
│  7. 화질: 2K(기본, 190원) / 1K / 4K(380원)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: 착장 분석 (VLM)                                           │
│  AI가 놓치기 쉬운 디테일 추출                                       │
│  - 변형된 실루엣, 미세 부자재, 로고 위치, 소재 질감                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 프롬프트 조립                                              │
│  포즈 프리셋 + 배경 프리셋 + 착장 분석 결과 → JSON 프롬프트        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: 생성 → 검증 → 재생성                                       │
│  ★ 얼굴 이미지 + 착장 이미지 전체 → API 전송 ★                    │
│  VLM 검증 (임계값 미달 시 재생성, 최대 2회)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: 입력 수집 (대화형)

### 대화 플로우

```
1. Claude: "얼굴 폴더 경로 알려주세요!"
   사용자: D:\사진\얼굴\

2. Claude: "착장 이미지 폴더 경로 알려주세요!"
   사용자: D:\사진\착장\

3. Claude: [AskUserQuestion - 포즈 프리셋 클릭 선택]
   옵션: front_standing / front_casual / side_profile / back_view / detail_closeup

4. Claude: [AskUserQuestion - 배경 프리셋 클릭 선택]
   옵션: white_studio / gray_studio / minimal_indoor / outdoor_urban

5. Claude: [AskUserQuestion - 수량/비율/화질 클릭 선택]
   수량: 1장 / 3장 / 5장 / 10장
   비율: 3:4 / 1:1 / 4:5 / 9:16
   화질: 2K / 1K / 4K

6. Claude: [일괄 생성]
```

---

## 포즈 프리셋

| 프리셋 | 설명 | 프레이밍 | 용도 |
|--------|------|----------|------|
| `front_standing` | 정면, 자연스러운 서있기 | 전신 (FS) | 기본 모델컷 |
| `front_casual` | 정면, 캐주얼한 포즈 (한 손 허리, 발 살짝 엇갈림) | 전신 (FS) | 룩북, 라이프스타일 |
| `side_profile` | 측면, 프로필 각도 | 전신 (FS) | 실루엣 강조 |
| `back_view` | 뒷모습, 뒤 디테일 보이기 | 전신 (FS) | 후면 디자인 표현 |
| `detail_closeup` | 상체 클로즈업, 디테일 보이기 | 미디엄샷 (MS) | 소재/로고/디테일 강조 |

### 포즈 프리셋 JSON 구조

```python
POSE_PRESETS = {
    "front_standing": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "natural standing, arms relaxed at sides, neutral expression, looking at camera",
        "lens": "50mm",
        "height": "eye level"
    },
    "front_casual": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "casual standing, one hand on waist, slight hip shift, confident expression",
        "lens": "50mm",
        "height": "eye level"
    },
    "side_profile": {
        "framing": "FS",
        "angle": "side",
        "pose_desc": "side profile, standing straight, head turned slightly toward camera",
        "lens": "50mm",
        "height": "eye level"
    },
    "back_view": {
        "framing": "FS",
        "angle": "back",
        "pose_desc": "back view, standing naturally, showing back details of clothing",
        "lens": "50mm",
        "height": "eye level"
    },
    "detail_closeup": {
        "framing": "MS",
        "angle": "front",
        "pose_desc": "upper body shot, torso and face visible, showcasing clothing details",
        "lens": "85mm",
        "height": "chest level"
    }
}
```

---

## 배경 프리셋

| 프리셋 | 설명 | 용도 |
|--------|------|------|
| `white_studio` | 순백 스튜디오 배경 | 기본 모델컷, 상세페이지 |
| `gray_studio` | 회색 스튜디오 배경 | 룩북, 고급스러운 느낌 |
| `minimal_indoor` | 미니멀 실내 (흰 벽, 콘크리트) | 라이프스타일 룩북 |
| `outdoor_urban` | 도심 야외 (거리, 건물 앞) | 스트릿 룩북 |

### 배경 프리셋 JSON 구조

```python
BACKGROUND_PRESETS = {
    "white_studio": {
        "location": "white studio backdrop",
        "lighting": "professional studio lighting, soft diffused light, even illumination",
        "ambient": "clean white background, seamless paper backdrop",
        "mood": "commercial, professional, product-focused"
    },
    "gray_studio": {
        "location": "gray studio backdrop",
        "lighting": "studio lighting, slightly dramatic, soft shadows",
        "ambient": "neutral gray background, modern studio setting",
        "mood": "sophisticated, editorial, high-end"
    },
    "minimal_indoor": {
        "location": "minimal indoor space",
        "lighting": "natural window light, soft diffused daylight",
        "ambient": "white walls, concrete floor, architectural minimalism",
        "mood": "lifestyle, modern, relatable"
    },
    "outdoor_urban": {
        "location": "urban outdoor setting",
        "lighting": "natural daylight, soft ambient outdoor light",
        "ambient": "city street, modern building facade, clean urban environment",
        "mood": "streetwear, casual, authentic"
    }
}
```

---

## Step 2: 착장 분석 (VLM)

### 착장 분석 프롬프트

```python
ECOMMERCE_ANALYSIS_PROMPT = """
착장 이미지를 분석하여 AI가 놓치기 쉬운 디테일을 추출하세요.

이커머스 모델 이미지의 핵심은 **착장을 정확히 보여주는 것**입니다.

반드시 포함:
1. 변형된 실루엣: 벌룬핏, 비대칭 커팅, 익스트림 크롭, 오버사이즈, 슬림핏
2. 미세 부자재: 배색 스티치, 단추, 지퍼, 디테일 장식
3. 로고/그래픽 위치: 정확한 상대적 좌표 (예: "왼쪽 가슴, 어깨에서 10cm 아래")
4. 소재 질감: 코튼, 니트, 데님, 레더, 나일론, 실크 등
5. 색상: 정확한 색상 표현 (예: "다크 네이비", "크림 화이트", "머스타드 옐로우")
6. 착장 구성: 아우터 + 상의 + 하의 + 신발 + 액세서리 전체

JSON 형식으로 출력:
{
  "outer": {"item": "", "color": "", "details": [], "logo_position": ""},
  "top": {"item": "", "color": "", "details": [], "logo_position": ""},
  "bottom": {"item": "", "color": "", "details": []},
  "shoes": {"item": "", "color": ""},
  "accessories": [],
  "overall_style": "",
  "key_details": []
}
"""
```

---

## Step 3: 프롬프트 조립

### 이커머스 생성 프롬프트

```python
ECOMMERCE_GENERATION_PROMPT = """
이커머스 상품 상세페이지용 모델 이미지를 생성하세요.

## 우선순위 (반드시 준수)

1. **착장 정확도 (최우선)**
   - 색상, 로고, 디테일, 실루엣 완벽 재현
   - 착장 이미지의 모든 요소 정확히 복사

2. **상업적 품질**
   - 프로페셔널한 스튜디오 조명
   - 클린하고 깔끔한 배경
   - 완벽한 포즈와 구도

3. **얼굴 동일성**
   - 얼굴 참조 이미지와 유사한 얼굴
   - (브랜드컷보다 낮은 우선순위)

## 프롬프트 구조

{
  "모델": {
    "얼굴": "참조 이미지와 유사한 얼굴",
    "표정": "자연스럽고 친근한, 카메라 직시",
    "피부": "깨끗하고 자연스러운 피부톤"
  },
  "착장": {
    "outer": "{{착장_분석_결과.outer}}",
    "top": "{{착장_분석_결과.top}}",
    "bottom": "{{착장_분석_결과.bottom}}",
    "shoes": "{{착장_분석_결과.shoes}}",
    "accessories": "{{착장_분석_결과.accessories}}",
    "instruction": "CRITICAL: 착장 이미지의 모든 요소를 정확히 복사. 색상, 로고, 디테일 누락 금지!"
  },
  "포즈": {
    "stance": "{{포즈_프리셋.pose_desc}}",
    "framing": "{{포즈_프리셋.framing}}",
    "angle": "{{포즈_프리셋.angle}}"
  },
  "촬영": {
    "렌즈": "{{포즈_프리셋.lens}}",
    "높이": "{{포즈_프리셋.height}}",
    "조명": "{{배경_프리셋.lighting}}"
  },
  "배경": {
    "location": "{{배경_프리셋.location}}",
    "ambient": "{{배경_프리셋.ambient}}",
    "mood": "{{배경_프리셋.mood}}"
  },
  "금지": [
    "AI 특유의 플라스틱 피부",
    "과도한 보정",
    "착장 색상 변경",
    "착장 디테일 누락",
    "로고 변형",
    "손가락 6개 이상",
    "의도하지 않은 텍스트/워터마크"
  ]
}
"""
```

---

## Step 4: 이미지 생성

### API 전송 순서

```
1. 프롬프트 (JSON 텍스트)
2. 얼굴 이미지 (전체 전송)
3. 착장 이미지 (전체 전송 - CRITICAL)
```

### 이미지 생성 코드

```python
from google import genai
from google.genai import types
from core.config import IMAGE_MODEL
from io import BytesIO
from PIL import Image
import json

def pil_to_part(img, max_size=1024):
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(
        mime_type="image/png", data=buf.getvalue()
    ))

def generate_ecommerce_image(
    prompt_json: dict,
    face_images: list,    # 얼굴 이미지 (전체 전송)
    outfit_images: list,  # 착장 이미지 (전체 전송 - CRITICAL)
    api_key: str,
    aspect_ratio: str = "3:4",
    resolution: str = "2K"
):
    """이커머스 모델 이미지 생성"""
    client = genai.Client(api_key=api_key)

    # 프롬프트 텍스트
    prompt_text = json.dumps(prompt_json, ensure_ascii=False)

    # API 파트 구성
    parts = [types.Part(text=prompt_text)]

    # 얼굴 이미지 전송
    for i, img in enumerate(face_images):
        parts.append(types.Part(text=f"[FACE REFERENCE {i+1}] - 이 얼굴과 유사한 모델:"))
        parts.append(pil_to_part(img))

    # ★ 착장 이미지 전체 전송 (CRITICAL - 최우선)
    for i, img in enumerate(outfit_images):
        parts.append(types.Part(text=f"[OUTFIT REFERENCE {i+1}] - 이 착장을 정확히 복사하세요 (색상, 디테일, 로고 모두):"))
        parts.append(pil_to_part(img))

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.2,  # 착장 정확도 위해 낮은 온도
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution
            )
        )
    )

    # 이미지 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))

    return None
```

---

## VLM 검증

### 검증 프롬프트

```python
ECOMMERCE_VALIDATION_PROMPT = """
이커머스 모델 이미지를 평가하세요.

평가 기준:
1. outfit_accuracy (0-100): 착장 재현도 (색상, 로고, 디테일) - **최우선**
2. commercial_quality (0-100): 상업적 품질 (조명, 배경, 포즈)
3. face_identity (0-100): 얼굴 동일성
4. photorealism (0-100): 실제 사진처럼 보이는지
5. anatomy (0-100): 해부학적 정확성 (손가락, 비율)

JSON 출력:
{
  "outfit_accuracy": 0,
  "commercial_quality": 0,
  "face_identity": 0,
  "photorealism": 0,
  "anatomy": 0,
  "pass": true/false,
  "issues": []
}

Pass 조건 (AND 조건):
- outfit_accuracy ≥ 90 (최우선)
- commercial_quality ≥ 85
- face_identity ≥ 70 (브랜드컷보다 낮음)
- photorealism ≥ 85
- anatomy ≥ 90

Fail 조건 (즉시 재생성):
- 착장 색상 불일치
- 로고 누락/변형
- 착장 디테일 누락
- 손가락 6개 이상 / 기형적 손가락
- AI 특유의 플라스틱 피부
- 과도한 보정
"""
```

### 검증 기준표

| 항목 | 비중 | Pass 기준 | 비고 |
|------|------|----------|------|
| **outfit_accuracy** | 40% | ≥ 90 | **최우선** - 색상, 로고, 디테일 정확도 |
| **commercial_quality** | 20% | ≥ 85 | 조명, 배경, 포즈 전문성 |
| **face_identity** | 20% | ≥ 70 | 브랜드컷보다 낮은 기준 (착장이 더 중요) |
| **photorealism** | 10% | ≥ 85 | 실사 품질 |
| **anatomy** | 10% | ≥ 90 | 손, 비율 정확성 |

**총점 계산:**
```
총점 = outfit_accuracy * 0.4 + commercial_quality * 0.2 + face_identity * 0.2 + photorealism * 0.1 + anatomy * 0.1
```

**Pass 조건 (AND):**
- `outfit_accuracy ≥ 90` (필수)
- `commercial_quality ≥ 85` (필수)
- `face_identity ≥ 70`
- `photorealism ≥ 85`
- `anatomy ≥ 90`

---

## Auto-Fail 조건 (즉시 재생성)

- 착장 색상 불일치 (outfit_accuracy < 80)
- 로고 누락/변형
- 착장 디테일 누락
- 손가락 6개 이상 / 기형적 손가락
- AI 특유의 플라스틱 피부
- 과도한 보정 (너무 인위적)
- 배경에 의도하지 않은 요소
- 의도하지 않은 텍스트/워터마크

---

## 재생성 전략

### 재생성 로직

```python
def generate_with_validation(
    prompt_json: dict,
    face_images: list,
    outfit_images: list,
    api_key: str,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2
):
    """생성-검증-재생성 루프"""
    for attempt in range(max_retries + 1):
        # 생성
        image = generate_ecommerce_image(
            prompt_json, face_images, outfit_images, api_key,
            aspect_ratio=aspect_ratio, resolution=resolution
        )

        # 검증
        result = validate_image(image, outfit_images, api_key)

        if result["pass"]:
            return {"image": image, "validation": result, "attempts": attempt + 1}

        # 재생성 전 프롬프트 강화
        if result["outfit_accuracy"] < 90:
            prompt_json["착장"]["instruction"] = "ULTRA CRITICAL: 착장 이미지의 모든 요소를 pixel-perfect로 복사. 색상, 로고, 디테일 단 하나도 빠뜨리지 말 것!"
        if result["commercial_quality"] < 85:
            prompt_json["촬영"]["조명"] = "professional studio lighting, perfect even illumination, no harsh shadows"
        if result["face_identity"] < 70:
            prompt_json["모델"]["instruction"] = "얼굴 참조 이미지와 유사한 얼굴"

        # 온도 낮춤 (착장 정확도 향상)
        temperature = max(0.1, 0.2 - attempt * 0.05)

    return {"image": image, "validation": result, "attempts": max_retries + 1, "warning": "검증 실패"}
```

---

## 에러 핸들링

| 에러 타입 | 감지 방법 | 복구 액션 |
|-----------|-----------|-----------|
| API Timeout | 30초 초과 | 최대 3회 재시도 (5s, 10s, 15s) |
| Rate Limit (429) | status_code == 429 | 60초 대기 후 재시도 |
| VLM Failure | response 비어있음 | 프롬프트 간소화 후 재시도 |
| File Not Found | FileNotFoundError | 사용자에게 경로 재입력 요청 |
| Validation Fail | pass == false | 프롬프트 강화 후 재생성 (최대 2회) |

---

## 사용법

### CLI

```
/이커머스
```

Claude가 순차적으로 질문:
1. 얼굴 폴더 경로?
2. 착장 이미지 폴더 경로?
3. 포즈 프리셋? (클릭 선택: front_standing / front_casual / side_profile / back_view / detail_closeup)
4. 배경 프리셋? (클릭 선택: white_studio / gray_studio / minimal_indoor / outdoor_urban)
5. 생성 장수? (1-10)
6. 비율? (3:4 기본)
7. 화질? (2K 기본)

### 비율 옵션

| 비율 | 용도 |
|------|------|
| 3:4 | 상세페이지 기본 (권장) |
| 1:1 | 정방형 (인스타그램) |
| 4:5 | 세로형 (피드) |
| 9:16 | 세로 풀스크린 (스토리) |

### 화질 및 비용

| 화질 | 해상도 | 비용/장 |
|------|--------|---------|
| 1K | 1024px | 190원 |
| 2K | 2048px | 190원 (권장) |
| 4K | 4096px | 380원 |

---

## Python 코드 예시

### EcommerceGenerator 클래스

```python
from google import genai
from google.genai import types
from core.config import IMAGE_MODEL, VISION_MODEL
from PIL import Image
from io import BytesIO
import json
import os

class EcommerceGenerator:
    """이커머스 모델 이미지 생성기"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    def analyze_outfit(self, outfit_images: list) -> dict:
        """착장 분석"""
        prompt = ECOMMERCE_ANALYSIS_PROMPT
        parts = [types.Part(text=prompt)]
        for img in outfit_images:
            parts.append(self.pil_to_part(img))

        response = self.client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=parts)]
        )

        result_text = response.candidates[0].content.parts[0].text
        return json.loads(result_text)

    def generate(
        self,
        face_images: list,
        outfit_images: list,
        pose_preset: str = "front_standing",
        background_preset: str = "white_studio",
        aspect_ratio: str = "3:4",
        resolution: str = "2K"
    ) -> Image.Image:
        """이커머스 이미지 생성"""
        # 착장 분석
        outfit_analysis = self.analyze_outfit(outfit_images)

        # 프롬프트 조립
        prompt_json = self.build_prompt(
            outfit_analysis, pose_preset, background_preset
        )

        # 생성
        return generate_ecommerce_image(
            prompt_json, face_images, outfit_images, self.api_key,
            aspect_ratio=aspect_ratio, resolution=resolution
        )

    def build_prompt(self, outfit_analysis, pose_preset, background_preset):
        """프롬프트 조립"""
        return {
            "모델": {
                "얼굴": "참조 이미지와 유사한 얼굴",
                "표정": "자연스럽고 친근한, 카메라 직시",
                "피부": "깨끗하고 자연스러운 피부톤"
            },
            "착장": outfit_analysis,
            "포즈": POSE_PRESETS[pose_preset],
            "촬영": {
                "렌즈": POSE_PRESETS[pose_preset]["lens"],
                "높이": POSE_PRESETS[pose_preset]["height"],
                "조명": BACKGROUND_PRESETS[background_preset]["lighting"]
            },
            "배경": BACKGROUND_PRESETS[background_preset],
            "금지": [
                "AI 특유의 플라스틱 피부",
                "과도한 보정",
                "착장 색상 변경",
                "착장 디테일 누락",
                "로고 변형",
                "손가락 6개 이상"
            ]
        }

    @staticmethod
    def pil_to_part(img, max_size=1024):
        """PIL Image를 Gemini Part로 변환"""
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png", data=buf.getvalue()
        ))


# ============ 사용 예시 ============

if __name__ == "__main__":
    # 1. API 키 로드
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    # 2. Generator 초기화
    gen = EcommerceGenerator(api_key)

    # 3. 이미지 로드
    face_images = [Image.open(f"faces/{i}.jpg") for i in range(1, 4)]
    outfit_images = [Image.open(f"outfits/{i}.jpg") for i in range(1, 6)]

    # 4. 생성
    result = gen.generate(
        face_images=face_images,
        outfit_images=outfit_images,
        pose_preset="front_standing",
        background_preset="white_studio",
        aspect_ratio="3:4",
        resolution="2K"
    )

    # 5. 저장
    result.save("output/ecommerce_model.png")
    print("Success!")
```

---

## 파일 구조

```
.claude/skills/이커머스_ecommerce/
└── SKILL.md              # 이 문서

Fnf_studio_outputs/
└── ecommerce/
    └── {timestamp}/
        ├── ecommerce_01.png
        ├── ecommerce_02.png
        └── ...
```

---

**버전**: 1.0.0
**작성일**: 2026-02-11
**변경사항**:
- 초기 버전 작성
- 포즈 프리셋 5종 추가 (front_standing, front_casual, side_profile, back_view, detail_closeup)
- 배경 프리셋 4종 추가 (white_studio, gray_studio, minimal_indoor, outdoor_urban)
- 착장 정확도 최우선 검증 기준 (40%)
- 얼굴 동일성 기준 완화 (20%, ≥70)
