---
name: brand-cut
description: MLB 브랜드컷 생성. 얼굴+착장 → 화보 이미지 생성.
user-invocable: true
trigger-keywords: ["브랜드컷", "화보", "에디토리얼", "룩북", "마케팅컷"]
---

# 브랜드컷 (Brand Cut) - MLB 마케팅 화보 생성

> 모델 얼굴 + 착장 이미지 → AI 화보 생성

---

## 절대 규칙 (CRITICAL)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 착장 이미지 전체 사용 (1순위) - 절대 빠뜨리면 안됨              │
│  2. 얼굴 이미지 반드시 API에 전송 - 얼굴 동일성 보장                │
│  3. 앵글에 따른 착장 노출 규칙 준수                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 우선순위

| 순위 | 항목 | 설명 |
|------|------|------|
| **1 (최우선)** | **착장 보존** | 모든 착장 이미지를 API에 전송. 하나도 빠뜨리면 안됨 |
| **2** | **얼굴 보존** | 얼굴 이미지 반드시 API에 전송. 동일 인물 보장 |
| 3 | 컨셉/무드 | 컨셉 레퍼런스에 맞는 표정/포즈/분위기 |
| 4 | 배경/조명 | 브랜드 톤앤매너 |

### 앵글-착장 노출 규칙

| 프레이밍 | 보여야 하는 착장 | 안보여도 OK |
|----------|-----------------|-------------|
| CU (클로즈업) | 헤드웨어, 주얼리, 상의 일부 | 하의, 신발 |
| MCU (가슴위) | 헤드웨어, 주얼리, 상의, 아우터 | 하의, 신발 |
| MS (허리위) | 헤드웨어, 주얼리, 상의, 아우터 | 신발 |
| MFS (무릎위) | 헤드웨어, 주얼리, 상의, 아우터, 하의 | 신발 (일부) |
| FS (전신) | **모든 착장 필수** | 없음 |

**전신샷에서 헤드웨어(모자/비니) 빠뜨리면 재생성 필수!**

---

## MLB 브랜드 지침 (BRAND GUIDELINES)

```
┌─────────────────────────────────────────────────────────────────┐
│  ★ MLB 브랜드컷은 "Young & Rich" 컨셉 - 고급스러움 필수 ★        │
└─────────────────────────────────────────────────────────────────┘
```

### 차량 배경 규칙

| 항목 | 필수 조건 | 금지 |
|------|----------|------|
| 차량 종류 | **명품 SUV만** (G-Class, Range Rover, Porsche Cayenne, BMW X7 등) | 일반 세단, 경차, 오래된 차량 |
| 차량 상태 | 깨끗하고 광택 있는 상태, 프리미엄 컬러 (블랙, 화이트, 실버, 다크그레이) | 더럽거나 낡은 차량 |
| 주차 환경 | 모던한 공간 (깔끔한 주차장, 럭셔리 빌딩 앞, 미니멀 배경) | 가난한 차고지, 허름한 주차장, 복잡한 배경 |

### 배경 규칙

| 항목 | 필수 조건 | 금지 |
|------|----------|------|
| 전체 느낌 | **모던하고 클린** - 미니멀, 하이엔드 | 복잡하거나 지저분한 배경 |
| 차량 있음 | 럭셔리 SUV + 깔끔한 주변 환경 | 허름한 차고지, 공사장, 골목길 |
| 차량 없음 | 메탈 패널, 콘크리트 벽, 산업적 미니멀 | 너무 화려하거나 복잡한 배경 |
| 조명 | 자연광 또는 스튜디오 조명, 쿨톤 유지 | 누런 조명, 따뜻한 색감 |

### 배경 상세 프롬프트 예시

**차량 있음 (Good):**
```
"silver luxury SUV (Mercedes G-Class or Range Rover) parked in clean modern
parking structure, polished concrete floor, minimal architectural elements,
soft natural daylight, cool neutral tones, high-end editorial atmosphere"
```

**차량 없음 (Good):**
```
"clean industrial backdrop, brushed metal panels, modern architectural
concrete, minimalist setting, soft diffused daylight, cool neutral palette"
```

**금지 표현 (Bad):**
```
❌ "old garage", "worn concrete", "rusty", "dirty", "cheap"
❌ "warm lighting", "golden hour", "amber tones"
❌ "cluttered background", "busy street", "crowded"
```

---

## 필수 리소스

```
.claude/skills/brand-dna/mlb-prompt-cheatsheet.md  ← 이것만 로드
```

---

## 모델 설정

```python
from core.config import IMAGE_MODEL, VISION_MODEL

IMAGE_MODEL = "gemini-3-pro-image-preview"  # 이미지 생성
VISION_MODEL = "gemini-3-flash-preview"     # 착장/컨셉 분석
```

---

## 워크플로 (4단계)

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 입력 수집                                                │
│  1. 얼굴 폴더 경로                                                 │
│  2. 착장 이미지 폴더 경로                                          │
│  3. 컨셉 레퍼런스 이미지 폴더 경로 (선택)                           │
│     → Claude가 분석해서 컨셉 정리                                  │
│  4. 배경 타입: 차량있음 / 차량없음                                  │
│  5. 생성 장수: 1-10                                               │
│  6. 비율: 3:4(기본) / 1:1 / 4:5 / 9:16 / 16:9 등                 │
│  7. 화질: 2K(기본, 190원) / 1K(190원) / 4K(380원)                 │
│  + 추가 요청사항 자유 입력 가능                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: 착장 분석 + 컨셉 분석 (VLM)                               │
│  [착장] AI가 놓치기 쉬운 디테일 추출                                │
│  [컨셉] 레퍼런스 이미지에서 무드/포즈/표정/앵글 추출                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 치트시트 기반 프롬프트 조립                                 │
│  1. 컨셉 분석 결과 → 표정/시선/입/포즈 매핑                         │
│  2. 배경 타입 → 포즈 호환성 검증                                     │
│  3. 금지 조합 검증 → 위반 시 대안 적용                               │
│  4. JSON 프롬프트 조립                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: 생성 → 검증 → 재생성                                       │
│  ★ 얼굴 이미지 + 착장 이미지 전체 + 프롬프트 → API 전송 ★           │
│  VLM 검증 (임계값 미달 시 재생성, 최대 2회)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: 입력 수집 (대화형)

### 질문 순서

```
1. 얼굴 폴더 경로?
2. 착장 이미지 폴더 경로?
3. 컨셉 레퍼런스 이미지 폴더? (없으면 스킵, 텍스트로 설명해도 OK)
4. 배경에 차량? (있음/없음)
5. 생성 장수? (1-10)
6. 비율? (3:4 기본)
7. 화질? (2K 기본)

+ "추가로 원하시는 것이 있으면 말씀해주세요" (자유 입력)
```

### 컨셉 레퍼런스 처리

사용자가 컨셉 이미지 폴더를 제공하면:
1. Claude가 이미지를 분석
2. 컨셉 요약을 정리해서 보여줌
3. 사용자 확인 후 진행

```python
CONCEPT_ANALYSIS_PROMPT = """
이 이미지들의 공통 스타일/무드를 분석하세요.

추출할 정보:
1. 전체 무드 (예: cool, dreamy, natural, edgy)
2. 표정 특징 (예: 무표정, 살짝 미소, 시크)
3. 포즈 특징 (예: 자연스러운 서있기, 기대기, 걷기)
4. 시선 방향 (예: 카메라 직시, 허공, 측면)
5. 앵글/프레이밍 (예: 전신, 허리위, 클로즈업)
6. 조명/색감 (예: 자연광, 스튜디오, 쿨톤)

JSON 출력:
{
  "mood": "",
  "expression": "",
  "pose_style": "",
  "gaze": "",
  "framing": "",
  "lighting": "",
  "summary": "한 문장 요약"
}
"""
```

---

## Step 2: 착장 분석 + 컨셉 분석

### 착장 분석 (모든 이미지 대상)

```python
OUTFIT_ANALYSIS_PROMPT = """
착장 이미지를 분석하여 AI가 놓치기 쉬운 디테일을 추출하세요.

반드시 포함:
1. 변형된 실루엣: 벌룬핏, 비대칭 커팅, 익스트림 크롭
2. 미세 부자재: 배색 스티치, 빈티지 워싱, 로고 각인 단추
3. 로고/그래픽 위치: 정확한 상대적 좌표 (예: "왼쪽 가슴 위, 어깨에서 10cm 아래")
4. 소재 질감: 시어, 슬러브, 헤어리, 코팅 가공

JSON 형식으로 출력:
{
  "outer": {"item": "", "color": "", "details": [], "logo_position": ""},
  "top": {"item": "", "color": "", "details": [], "logo_position": ""},
  "bottom": {"item": "", "color": "", "details": []},
  "shoes": {"item": "", "color": ""},
  "headwear": {"item": "", "color": "", "logo_position": ""},
  "accessories": []
}
"""
```

---

## Step 3: 컨셉 → 프롬프트 매핑

치트시트(`mlb-prompt-cheatsheet.md`)에서 컨셉 분석 결과에 맞게 조립.

### 컨셉별 표정 매핑

| 컨셉 | 표정 베이스 | 가능 시선 | 가능 입 |
|------|------------|----------|--------|
| cool | cool | direct, past, side | closed, parted |
| natural | natural | direct, past | closed, parted |
| dreamy | dreamy | past, side | parted, closed |
| neutral | neutral | direct | closed |
| serious | serious | direct | closed |

### 배경 타입 → 포즈 매핑

**차량 없음:**
| 배경 | 가능 포즈 |
|------|----------|
| 메탈패널 | stand, lean_wall, walk, back_look |
| 창고 | stand, lean_wall, sit, sit_crouch, lean_railing, walk, back_look |
| 콘크리트 | stand, lean_wall, sit_crouch, walk, back_look |

**차량 있음:**
| 배경 | 가능 포즈 |
|------|----------|
| 럭셔리SUV | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 빈티지카 | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 지하주차장 | lean_car, door_lean |

### 금지 조합 검증

```python
def validate_and_fix(prompt_json: dict) -> dict:
    """금지 조합 검증 및 자동 수정"""

    lens = prompt_json.get("촬영", {}).get("렌즈", "")
    framing = prompt_json.get("촬영", {}).get("프레이밍", "")
    expression = prompt_json.get("표정", {}).get("베이스", "")
    mouth = prompt_json.get("표정", {}).get("입", "")
    gaze = prompt_json.get("표정", {}).get("시선", "")

    # 렌즈-프레이밍 검증
    if lens == "85mm" and framing == "MFS":
        prompt_json["촬영"]["렌즈"] = "50mm"
    if lens == "35mm" and framing == "CU":
        prompt_json["촬영"]["렌즈"] = "85mm"

    # 표정-입 검증
    if expression in ["cool", "serious"] and mouth == "smile":
        prompt_json["표정"]["입"] = "closed"

    # 표정-시선 검증
    if expression == "dreamy" and gaze == "direct":
        prompt_json["표정"]["시선"] = "past"

    return prompt_json
```

---

## Step 4: 이미지 생성 (CRITICAL)

### API 전송 필수 항목

```
┌─────────────────────────────────────────────────────────────────┐
│  ★★★ 반드시 API에 전송해야 하는 이미지 ★★★                        │
│                                                                 │
│  1. 얼굴 이미지 (전체) - 얼굴 동일성 보장                          │
│  2. 착장 이미지 (전체) - 착장 정확도 보장                          │
│  3. 컨셉 레퍼런스 (있는 경우) - 무드/스타일 참조                   │
│                                                                 │
│  ❌ 얼굴 이미지 빠뜨리면: 다른 사람 얼굴 생성됨                    │
│  ❌ 착장 이미지 빠뜨리면: 착장 누락/변형됨                         │
└─────────────────────────────────────────────────────────────────┘
```

### 이미지 생성 코드

```python
from google import genai
from google.genai import types
from core.config import IMAGE_MODEL
from io import BytesIO
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

def generate_brandcut(
    prompt_json: dict,
    face_images: list,    # ★ 전체 전송 (빠뜨리면 안됨)
    outfit_images: list,  # ★ 전체 전송 (빠뜨리면 안됨)
    concept_images: list = None,  # 컨셉 레퍼런스 (선택)
    api_key: str,
    aspect_ratio: str = "3:4",
    resolution: str = "2K"
):
    client = genai.Client(api_key=api_key)

    # 프롬프트 텍스트
    prompt_text = json.dumps(prompt_json, ensure_ascii=False)

    # API 파트 구성
    parts = [types.Part(text=prompt_text)]

    # ★ 얼굴 이미지 전체 전송 (CRITICAL)
    for i, img in enumerate(face_images):
        parts.append(types.Part(text=f"[FACE REFERENCE {i+1}] - 이 얼굴을 정확히 복사하세요:"))
        parts.append(pil_to_part(img))

    # ★ 착장 이미지 전체 전송 (CRITICAL - 1순위)
    for i, img in enumerate(outfit_images):
        parts.append(types.Part(text=f"[OUTFIT REFERENCE {i+1}] - 이 착장을 정확히 복사하세요:"))
        parts.append(pil_to_part(img))

    # 컨셉 레퍼런스 (있는 경우)
    if concept_images:
        for i, img in enumerate(concept_images[:3]):
            parts.append(types.Part(text=f"[CONCEPT REFERENCE {i+1}] - 이 무드/포즈/앵글 참조:"))
            parts.append(pil_to_part(img))

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.25,
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

### VLM 검증

```python
VALIDATION_PROMPT = """
생성된 이미지를 평가하세요.

평가 기준:
1. photorealism (0-100): 실제 사진처럼 보이는지
2. anatomy (0-100): 해부학적 정확성 (손가락, 비율)
3. face_identity (0-100): 얼굴 동일성
4. outfit_accuracy (0-100): 착장 재현도 (색상, 로고, 디테일)
5. outfit_completeness (0-100): 착장 누락 여부 (헤드웨어, 액세서리 포함)

JSON 출력:
{
  "photorealism": 0,
  "anatomy": 0,
  "face_identity": 0,
  "outfit_accuracy": 0,
  "outfit_completeness": 0,
  "pass": true/false,
  "missing_items": [],
  "issues": []
}

Pass 조건:
- photorealism ≥ 85
- anatomy ≥ 90
- face_identity ≥ 90
- outfit_accuracy ≥ 85
- outfit_completeness ≥ 90 (전신샷의 경우)
"""
```

### 생성-검증-재생성 루프

```python
def generate_with_validation(
    prompt_json: dict,
    face_images: list,
    outfit_images: list,
    concept_images: list,
    api_key: str,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2
):
    for attempt in range(max_retries + 1):
        # 생성
        image = generate_brandcut(
            prompt_json, face_images, outfit_images, concept_images, api_key,
            aspect_ratio=aspect_ratio, resolution=resolution
        )

        # 검증
        result = validate_image(image, face_images[0], outfit_images, api_key)

        if result["pass"]:
            return {"image": image, "validation": result, "attempts": attempt + 1}

        # 재생성 전 프롬프트 강화
        if result["outfit_accuracy"] < 85 or result.get("missing_items"):
            prompt_json["착장"]["instruction"] = "CRITICAL: 모든 착장 아이템 정확히 복사. 누락 금지!"
        if result["face_identity"] < 90:
            prompt_json["모델"]["instruction"] = "CRITICAL: 얼굴을 참조 이미지와 정확히 일치시키세요"

    return {"image": image, "validation": result, "attempts": max_retries + 1, "warning": "검증 실패"}
```

---

## Auto-Fail 조건 (즉시 재생성)

- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람 (face_identity < 70)
- 착장 색상/로고 불일치 (outfit_accuracy < 70)
- **착장 아이템 누락** (전신샷에서 헤드웨어 없음 등)
- 누런 톤 (golden/amber/warm cast)
- 의도하지 않은 텍스트/워터마크

---

## 에러 핸들링

| 에러 타입 | 감지 방법 | 복구 액션 |
|-----------|-----------|-----------|
| API Timeout | 30초 초과 | 최대 3회 재시도 (2s, 4s, 8s) |
| Rate Limit (429) | status_code == 429 | 60초 대기 후 재시도 |
| VLM Failure | response 비어있음 | 프롬프트 간소화 후 재시도 |
| File Not Found | FileNotFoundError | 사용자에게 경로 재입력 요청 |

---

## 사용법

### CLI

```
/브랜드컷
```

Claude가 순차적으로 질문:
1. 얼굴 폴더 경로?
2. 착장 이미지 폴더 경로?
3. 컨셉 레퍼런스 이미지 폴더? (없으면 스킵 가능)
   → 이미지 분석 후 "이런 컨셉이네요: [요약]" 확인
4. 배경에 차량? (있음/없음)
5. 생성 장수? (1-10)
6. 비율? (3:4 기본)
7. 화질? (2K 기본)
8. 추가 요청사항? (자유 입력)

### 비율 옵션

| 비율 | 용도 |
|------|------|
| 3:4 | 에디토리얼 기본 (권장) |
| 4:5 | 인스타그램 피드 |
| 1:1 | 정방형 |
| 9:16 | 스토리/릴스 |
| 16:9 | 와이드 배너 |

### 화질 및 비용

| 화질 | 해상도 | 비용/장 |
|------|--------|---------|
| 1K | 1024px | 190원 |
| 2K | 2048px | 190원 (권장) |
| 4K | 4096px | 380원 |

---

## 파일 구조

```
.claude/skills/브랜드컷_brand-cut/
└── SKILL.md                   # 이 문서

.claude/skills/brand-dna/
└── mlb-prompt-cheatsheet.md   # MLB 치트시트
```

---

**버전**: 2.2.0
**작성일**: 2026-02-10
**변경사항**:
- **MLB 브랜드 지침 추가**: 명품 SUV 필수, 모던/클린 배경
- 컨셉 이미지 폴더 입력 추가
- 착장/얼굴 이미지 API 전송 필수 강조
- 앵글-착장 노출 규칙 추가
- 추가 요청사항 자유 입력 추가
