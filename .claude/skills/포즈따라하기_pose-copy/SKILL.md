---
name: pose-copy
description: 레퍼런스 이미지의 포즈를 소스 인물에 적용 (얼굴, 착장 유지)
user-invocable: true
trigger-keywords: ["포즈 따라하기", "포즈 복제", "포즈 카피", "pose copy", "copy pose"]
---

# 포즈 따라하기 (Pose Copy)

> **핵심 개념**: 레퍼런스 이미지의 포즈와 구도를 복제, 소스 인물의 얼굴과 착장은 유지

---

## 모델 필수 확인

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ 이미지 생성: IMAGE_MODEL (gemini-3-pro-image-preview)   │
│  ✅ VLM 분석: VISION_MODEL (gemini-3-flash-preview)         │
│                                                             │
│  ⚠️  반드시 core/config.py 에서 import 해서 사용!           │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 컨셉

```
┌─────────────────────────────────────────────────────────────┐
│  Pose Copy = 레퍼런스 포즈 복제                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FROM SOURCE:                FROM REFERENCE:                │
│  ├─ 얼굴 (EXACT)             ├─ 포즈 (EXACT)                │
│  └─ 착장 (EXACT)             ├─ 표정 (ADAPT)                │
│                              ├─ 구도 (EXACT)                │
│                              └─ 카메라 앵글 (EXACT)          │
│                                                             │
│  BACKGROUND:                                                │
│  ├─ reference (레퍼런스 배경 사용)                           │
│  ├─ source (소스 배경 사용)                                  │
│  └─ custom (새로운 배경 지정)                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**주의사항:**
- 레퍼런스는 포즈, 구도, 카메라 앵글만 참조
- 레퍼런스의 얼굴/착장은 절대 사용 안 함
- 소스의 얼굴/착장을 레퍼런스 포즈에 적용

---

## 입력 구조

| 입력 | 필수 | 수량 | 처리 방식 |
|------|------|------|----------|
| 레퍼런스 이미지 | ✅ | 1장 | API에 직접 전달 (포즈/구도 보존 대상) |
| 소스 이미지 | ✅ | 1장 | VLM 분석 → 텍스트 변환 (얼굴/착장) |
| 배경 옵션 | ✅ | 선택 | reference / source / custom |

---

## 대화 플로우 (경로 순차 → 옵션 클릭 → 일괄 생성)

> **원칙**: 경로 하나씩 질문 → 옵션 클릭 선택 → 마지막에 한번에 생성

### 플로우

```
1. 사용자: "포즈 따라하기" 또는 "pose copy"

2. Claude: "레퍼런스 이미지 경로?" (포즈/구도 복제 대상)
3. 사용자: D:\reference.jpg

4. Claude: "소스 이미지 경로?" (얼굴/착장 유지 대상)
5. 사용자: D:\source.jpg

6. Claude: [AskUserQuestion - 배경/수량/화질 클릭 선택]

7. 사용자: 클릭으로 선택

8. Claude:
   - 레퍼런스 포즈 분석
   - 소스 얼굴/착장 분석
   - 이미지 생성
   - 포즈 비교 검수
   - 결과 저장 및 경로 안내
```

### 경로 질문 (순차, 일반 텍스트)

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "레퍼런스 이미지 경로?" | ✅ |
| 2 | "소스 이미지 경로?" | ✅ |

### 옵션 선택 (AskUserQuestion 클릭)

```python
AskUserQuestion(questions=[
    {
        "question": "배경을 어떻게 할까요?",
        "header": "배경 옵션",
        "options": [
            {"label": "reference (Recommended)", "description": "레퍼런스 이미지 배경 사용"},
            {"label": "source", "description": "소스 이미지 배경 사용"},
            {"label": "custom", "description": "새로운 배경 지정"}
        ],
        "multiSelect": False
    },
    {
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "1장", "description": "테스트용"},
            {"label": "3장 (Recommended)", "description": "다양한 결과 비교"},
            {"label": "5장", "description": "충분한 선택지"}
        ],
        "multiSelect": False
    },
    {
        "question": "화질을 선택해주세요",
        "header": "해상도",
        "options": [
            {"label": "1K", "description": "테스트용"},
            {"label": "2K (Recommended)", "description": "일반 사용"},
            {"label": "4K", "description": "최종 출력"}
        ],
        "multiSelect": False
    }
])
```

### 기본값

| 항목 | 기본값 |
|------|--------|
| 배경 | reference |
| 수량 | 3장 |
| 화질 | 2K |

---

## API 전송 순서 (CRITICAL)

```
1. 프롬프트 (텍스트) - 포즈 복제 지시
2. 레퍼런스 이미지 (첫 번째) - 포즈/구도 보존 대상 (API 직접 전달)
3. 소스 얼굴/착장 정보 (텍스트) - VLM 분석 결과
```

**핵심 원칙:**
- 레퍼런스 이미지를 API에 첫 번째 이미지로 직접 전달 (포즈/구도 보존)
- 소스는 VLM으로 분석해서 얼굴/착장만 텍스트로 전달 (이미지 전달 X)
- 배경 옵션에 따라 프롬프트 조정

**왜 레퍼런스를 이미지로, 소스를 텍스트로?**
- API가 첫 번째 이미지의 포즈/구도를 강하게 보존
- 소스 이미지를 직접 전달하면 포즈가 섞이는 문제 발생
- 얼굴/착장은 텍스트 묘사로 충분히 전달 가능

---

## Workflow Pattern (5 Steps)

```
1. analyze_reference()  → VLM 분석 (레퍼런스 포즈/구도/배경)
2. analyze_source()     → VLM 분석 (소스 얼굴/착장)
3. build_prompt()       → 프롬프트 조립
4. generate_image()     → Gemini API 호출
5. validate()           → 포즈 비교 검수
```

---

## VLM 분석 프롬프트

### 레퍼런스 포즈 분석

```python
POSE_REFERENCE_ANALYSIS_PROMPT = """
레퍼런스 이미지를 분석해서 포즈, 구도, 카메라 앵글을 추출하세요.

JSON 출력:
{
  "pose": {
    "body_position": "standing, weight on right leg, slight hip tilt",
    "torso_angle": "3/4 left, slight lean forward",
    "head_position": "turned slightly left, chin up",
    "arm_left": "bent at elbow 90°, hand on hip",
    "arm_right": "relaxed, hanging naturally, fingers spread",
    "leg_left": "straight, weight-bearing",
    "leg_right": "slightly bent, relaxed",
    "overall_vibe": "confident, casual stance"
  },
  "composition": {
    "person_position": {"x": 0.5, "y": 0.6},  // 정규화 좌표 (0.0~1.0)
    "person_size_ratio": 0.7,  // 인물이 화면에서 차지하는 비율
    "framing": "full body, centered",
    "camera_angle": "eye-level, slightly from below",
    "distance": "medium shot"
  },
  "background": {
    "setting": "concrete wall, industrial",
    "color_tone": "cool gray, muted",
    "depth": "shallow, simple",
    "lighting": "soft natural light from left, diffused"
  },
  "expression": {
    "face": "neutral, confident",
    "gaze_direction": "camera, direct eye contact",
    "mood": "relaxed, self-assured"
  }
}
"""
```

### 소스 얼굴/착장 분석

```python
SOURCE_PERSON_ANALYSIS_PROMPT = """
소스 이미지를 분석해서 얼굴과 착장 정보를 추출하세요.

JSON 출력:
{
  "face": {
    "age": "mid-20s",
    "gender": "female",
    "ethnicity": "East Asian",
    "skin_tone": "fair, cool undertone",
    "face_shape": "oval",
    "distinctive_features": "high cheekbones, almond eyes, thin eyebrows"
  },
  "outfit": {
    "description": "black oversized hoodie with white MLB logo, light blue wide leg jeans",
    "colors": ["black", "white", "light blue"],
    "style": "streetwear, casual",
    "details": [
      "hoodie: drawstrings, kangaroo pocket",
      "jeans: wide leg, high waist, slightly distressed"
    ],
    "fit": "oversized top, relaxed bottom"
  },
  "hair": {
    "length": "long, past shoulders",
    "color": "dark brown",
    "style": "straight, center part, loose"
  }
}
"""
```

---

## 프롬프트 조립 로직

```python
from core.config import IMAGE_MODEL, VISION_MODEL

POSE_COPY_PROMPT = """
[CRITICAL - IMAGE ROLE ASSIGNMENT]

You are receiving ONE reference image. Use it for POSE and COMPOSITION ONLY.

🎯 REFERENCE IMAGE (FIRST IMAGE): POSE AND COMPOSITION SOURCE
- This is your PRIMARY reference for pose and framing
- COPY the exact pose (body position, limbs, head angle)
- COPY the exact composition (person size, position, camera angle)
- COPY the expression and gaze direction
- Do NOT use the face or outfit from this image

[FROM REFERENCE IMAGE - COPY EXACTLY]
POSE:
{pose_description}

COMPOSITION:
{composition_description}

EXPRESSION:
{expression_description}

[FROM SOURCE (TEXT ONLY) - APPLY TO POSE]
FACE:
{face_description}
- Apply this face to the person in the reference pose
- Match the face angle and gaze direction from reference
- Ensure natural integration with the pose

OUTFIT:
{outfit_description}
- Dress the person in this exact outfit
- Ensure outfit fits naturally with the pose
- Preserve all colors, logos, and details

HAIR:
{hair_description}

[BACKGROUND]
{background_instruction}

[CRITICAL CONSTRAINTS]
- COPY pose from reference image EXACTLY
- COPY composition from reference EXACTLY
- USE face from source description ONLY
- USE outfit from source description ONLY
- Do NOT mix reference person's face/outfit
- Ensure natural lighting on face and outfit
- Match expression and gaze from reference

[OUTPUT QUALITY]
- High-end professional quality
- Natural skin texture (no plastic/overly smooth)
- Sharp focus throughout
- Consistent lighting
- Clean edges, no artifacts
- Pose should look natural and effortless

⚠️ CRITICAL REMINDERS:
1. Pose/composition from REFERENCE IMAGE
2. Face/outfit from SOURCE TEXT DESCRIPTION
3. Do NOT use reference person's identity
4. Ensure seamless integration
"""
```

### 배경 옵션별 지시

```python
def get_background_instruction(bg_option: str, ref_bg: dict, source_bg: dict, custom_bg: str = None) -> str:
    """배경 옵션별 프롬프트 생성"""

    if bg_option == "reference":
        return f"""
BACKGROUND (from reference):
Setting: {ref_bg['setting']}
Color tone: {ref_bg['color_tone']}
Depth: {ref_bg['depth']}
Lighting: {ref_bg['lighting']}

Use the exact background from the reference image.
"""

    elif bg_option == "source":
        return f"""
BACKGROUND (from source):
Setting: {source_bg['setting']}
Color tone: {source_bg['color_tone']}
Depth: {source_bg['depth']}
Lighting: {source_bg['lighting']}

Use the background from the source image, but adjust lighting to match the reference pose.
"""

    elif bg_option == "custom":
        return f"""
BACKGROUND (custom):
{custom_bg}

Create this custom background while ensuring:
- Lighting matches the pose naturally
- Depth appropriate for the framing
- Style cohesive with the overall image
"""

    return ""
```

---

## 검수 기준

### 검수 항목

| 항목 | 가중치 | Pass 기준 |
|------|--------|----------|
| pose_similarity | 50% | >= 90 |
| face_preservation | 20% | >= 95 |
| outfit_preservation | 20% | >= 95 |
| composition_match | 10% | >= 85 |

**총점 계산:**
```
total_score = (
    pose_similarity * 0.5 +
    face_preservation * 0.2 +
    outfit_preservation * 0.2 +
    composition_match * 0.1
)
```

**Pass 조건:** `total_score >= 92`

### Auto-Fail Conditions

- 포즈 유사도 < 70 (완전히 다른 포즈)
- 얼굴 다른 사람 (소스와 불일치)
- 착장 변경됨 (색상/로고/스타일 다름)
- 손가락 6개 이상
- 누런 톤 (golden/amber cast)

### 포즈 비교 (core/person_utils.py)

```python
from core.person_utils import compare_poses

# 포즈 비교
pose_comparison = compare_poses(
    source_path=result_img_path,  # 생성된 이미지
    reference_path=reference_path,  # 레퍼런스 이미지
    threshold=90.0
)

if pose_comparison.overall_match:
    print(f"✅ 포즈 매칭: {pose_comparison.similarity_score:.1f}")
else:
    print(f"❌ 포즈 불일치: {pose_comparison.differing_elements}")
```

### VLM 검수 프롬프트

```python
POSE_COPY_VALIDATION_PROMPT = """
세 이미지를 비교해서 Pose Copy 결과를 검수하세요.

Image 1: 레퍼런스 이미지 (포즈/구도 ground truth)
Image 2: 소스 이미지 (얼굴/착장 ground truth)
Image 3: 생성 결과

JSON 출력:
{
  "pose_similarity": {
    "score": 92,  // 0-100, 레퍼런스 포즈와 유사도
    "matching_elements": ["body_position", "arm_left", "leg_right"],
    "differing_elements": ["head_angle slightly off"],
    "issues": []
  },
  "face_preservation": {
    "score": 96,  // 0-100, 소스 얼굴과 동일성
    "same_person": true,
    "issues": []
  },
  "outfit_preservation": {
    "score": 98,  // 0-100, 소스 착장과 동일성
    "changed_elements": [],
    "issues": []
  },
  "composition_match": {
    "score": 88,  // 0-100, 레퍼런스 구도와 일치
    "person_position_match": true,
    "framing_match": true,
    "camera_angle_match": true,
    "issues": []
  },
  "auto_fail": false,
  "auto_fail_reasons": [],
  "pass": true
}

Auto-Fail 조건:
- pose_similarity < 70
- face_preservation < 80 (다른 사람)
- outfit_preservation < 80 (착장 변경됨)
- 손가락 6개 이상
"""
```

---

## 재시도 전략

### Temperature Sequence

| 시도 | Temperature | 설명 |
|------|-------------|------|
| 1차 | 0.2 | 기본값 |
| 2차 | 0.1 | 더 일관성 있게 |
| 3차 | 0.05 | 최대한 보수적으로 |

### 최대 재시도

- 최대 2회 재생성
- 실패 진단: `pose_mismatch`, `face_mismatch`, `outfit_changed`
- 2회 실패 시: 사용자에게 레퍼런스/소스 이미지 품질 확인 요청

---

## Python 모듈 구조

```python
# core/pose_copy.py

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

# Config에서 모델 상수 로드 (절대 하드코딩 금지!)
from core.config import IMAGE_MODEL, VISION_MODEL
from core.person_utils import compare_poses

# ============================================================================
# API 키 관리
# ============================================================================

def load_api_keys() -> List[str]:
    """프로젝트 루트의 .env에서 API 키 로드"""
    env_path = ".env"
    api_keys = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                    _, value = line.strip().split('=', 1)
                    api_keys.extend([k.strip() for k in value.split(',')])
    return api_keys or [os.environ.get("GEMINI_API_KEY", "")]

API_KEYS = load_api_keys()
key_index = 0

def get_next_api_key() -> str:
    """Thread-safe API 키 로테이션"""
    global key_index
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ============================================================================
# 이미지 유틸리티
# ============================================================================

def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

def extract_json(response_text: str) -> dict:
    """VLM 응답에서 JSON 추출"""
    text = response_text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())

# ============================================================================
# VLM 분석
# ============================================================================

def analyze_with_vlm(image_path: str, prompt: str) -> dict:
    """이미지를 VLM으로 분석"""
    client = genai.Client(api_key=get_next_api_key())

    img = Image.open(image_path).convert("RGB")

    response = client.models.generate_content(
        model=VISION_MODEL,  # gemini-3-flash-preview
        contents=[types.Content(role="user", parts=[
            types.Part(text=prompt),
            pil_to_part(img)
        ])],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_modalities=["TEXT"]
        )
    )

    return extract_json(response.candidates[0].content.parts[0].text)

def analyze_reference_pose(ref_path: str) -> dict:
    """레퍼런스 포즈/구도 분석"""
    return analyze_with_vlm(ref_path, POSE_REFERENCE_ANALYSIS_PROMPT)

def analyze_source_person(source_path: str) -> dict:
    """소스 얼굴/착장 분석"""
    return analyze_with_vlm(source_path, SOURCE_PERSON_ANALYSIS_PROMPT)

# ============================================================================
# 배경 지시 생성
# ============================================================================

def get_background_instruction(
    bg_option: str,
    ref_bg: dict,
    source_bg: dict = None,
    custom_bg: str = None
) -> str:
    """배경 옵션별 프롬프트 생성"""

    if bg_option == "reference":
        return f"""
BACKGROUND (from reference):
Setting: {ref_bg['setting']}
Color tone: {ref_bg['color_tone']}
Depth: {ref_bg['depth']}
Lighting: {ref_bg['lighting']}

Use the exact background from the reference image.
"""

    elif bg_option == "source":
        if not source_bg:
            raise ValueError("source background info required")
        return f"""
BACKGROUND (from source):
Setting: {source_bg['setting']}
Color tone: {source_bg['color_tone']}
Depth: {source_bg['depth']}
Lighting: {source_bg['lighting']}

Use the background from the source image, but adjust lighting to match the reference pose.
"""

    elif bg_option == "custom":
        if not custom_bg:
            raise ValueError("custom background description required")
        return f"""
BACKGROUND (custom):
{custom_bg}

Create this custom background while ensuring:
- Lighting matches the pose naturally
- Depth appropriate for the framing
- Style cohesive with the overall image
"""

    return ""

# ============================================================================
# 프롬프트 조립
# ============================================================================

def build_pose_copy_prompt(
    ref_analysis: dict,
    source_analysis: dict,
    bg_option: str,
    custom_bg: str = None
) -> str:
    """Pose Copy 프롬프트 조립"""

    # 포즈 설명
    pose = ref_analysis["pose"]
    pose_desc = ", ".join([
        pose["body_position"],
        f"torso: {pose['torso_angle']}",
        f"head: {pose['head_position']}",
        f"left arm: {pose['arm_left']}",
        f"right arm: {pose['arm_right']}",
        f"left leg: {pose['leg_left']}",
        f"right leg: {pose['leg_right']}"
    ])

    # 구도 설명
    comp = ref_analysis["composition"]
    comp_desc = f"{comp['framing']}, person at x={comp['person_position']['x']:.2f} y={comp['person_position']['y']:.2f}, size ratio={comp['person_size_ratio']:.2f}, {comp['camera_angle']}, {comp['distance']}"

    # 표정 설명
    expr = ref_analysis["expression"]
    expr_desc = f"{expr['face']}, gaze: {expr['gaze_direction']}, mood: {expr['mood']}"

    # 얼굴 설명
    face = source_analysis["face"]
    face_desc = f"{face['age']} {face['gender']}, {face['ethnicity']}, {face['skin_tone']}, {face['face_shape']} face shape, distinctive: {', '.join(face['distinctive_features'])}"

    # 착장 설명
    outfit = source_analysis["outfit"]
    outfit_desc = f"{outfit['description']}, colors: {', '.join(outfit['colors'])}, style: {outfit['style']}, fit: {outfit['fit']}"

    # 헤어 설명
    hair = source_analysis["hair"]
    hair_desc = f"{hair['length']}, {hair['color']}, {hair['style']}"

    # 배경 지시
    bg_instruction = get_background_instruction(
        bg_option,
        ref_analysis["background"],
        source_analysis.get("background"),
        custom_bg
    )

    return POSE_COPY_PROMPT.format(
        pose_description=pose_desc,
        composition_description=comp_desc,
        expression_description=expr_desc,
        face_description=face_desc,
        outfit_description=outfit_desc,
        hair_description=hair_desc,
        background_instruction=bg_instruction
    )

# ============================================================================
# 이미지 생성
# ============================================================================

def generate_pose_copy(
    ref_path: str,
    prompt: str,
    temperature: float = 0.2,
    image_size: str = "2K"
) -> Image.Image:
    """Pose Copy 이미지 생성"""
    client = genai.Client(api_key=get_next_api_key())

    # Parts 조립: 프롬프트 + 레퍼런스 이미지
    parts = [types.Part(text=prompt)]

    # 레퍼런스 이미지 (포즈/구도 보존)
    ref_img = Image.open(ref_path).convert("RGB")
    parts.append(pil_to_part(ref_img))

    # 생성
    response = client.models.generate_content(
        model=IMAGE_MODEL,  # gemini-3-pro-image-preview
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                image_size=image_size
            )
        )
    )

    # 이미지 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))

    raise ValueError("No image in response")

# ============================================================================
# 검수
# ============================================================================

def validate_pose_copy(
    ref_path: str,
    source_path: str,
    result_img: Image.Image
) -> dict:
    """Pose Copy 결과 검수"""
    # 결과 이미지 임시 저장
    temp_path = "temp_result.png"
    result_img.save(temp_path)

    # VLM 검수 (레퍼런스 + 소스 + 결과)
    client = genai.Client(api_key=get_next_api_key())

    ref_img = Image.open(ref_path).convert("RGB")
    source_img = Image.open(source_path).convert("RGB")
    result_img_for_vlm = Image.open(temp_path).convert("RGB")

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part(text=POSE_COPY_VALIDATION_PROMPT),
            pil_to_part(ref_img),
            pil_to_part(source_img),
            pil_to_part(result_img_for_vlm)
        ])],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_modalities=["TEXT"]
        )
    )

    validation = extract_json(response.candidates[0].content.parts[0].text)

    # 총점 계산
    total_score = (
        validation["pose_similarity"]["score"] * 0.5 +
        validation["face_preservation"]["score"] * 0.2 +
        validation["outfit_preservation"]["score"] * 0.2 +
        validation["composition_match"]["score"] * 0.1
    )

    validation["total_score"] = total_score
    validation["pass"] = (total_score >= 92 and not validation["auto_fail"])

    # 포즈 비교 (core/person_utils.py)
    pose_comparison = compare_poses(
        source_path=temp_path,
        reference_path=ref_path,
        threshold=90.0
    )
    validation["pose_comparison"] = {
        "similarity_score": pose_comparison.similarity_score,
        "overall_match": pose_comparison.overall_match,
        "differing_elements": pose_comparison.differing_elements
    }

    # 임시 파일 삭제
    os.remove(temp_path)

    return validation

# ============================================================================
# 메인 워크플로
# ============================================================================

def pose_copy(
    reference_path: str,
    source_path: str,
    background_option: str = "reference",
    custom_background: str = None,
    output_dir: str = None,
    count: int = 1,
    image_size: str = "2K"
) -> List[Image.Image]:
    """
    Pose Copy 워크플로

    Args:
        reference_path: 레퍼런스 이미지 경로 (포즈/구도)
        source_path: 소스 이미지 경로 (얼굴/착장)
        background_option: 배경 옵션 ("reference", "source", "custom")
        custom_background: 커스텀 배경 설명 (bg_option="custom" 시)
        output_dir: 출력 폴더 (None이면 자동 생성)
        count: 생성 수량
        image_size: 화질 ("1K", "2K", "4K")

    Returns:
        List[Image.Image]: 생성된 이미지 목록
    """

    # 1. 레퍼런스 포즈 분석
    print("📷 레퍼런스 포즈/구도 분석 중...")
    ref_analysis = analyze_reference_pose(reference_path)
    print(f"  - 포즈: {ref_analysis['pose']['body_position']}")
    print(f"  - 구도: {ref_analysis['composition']['framing']}")
    print(f"  - 배경: {ref_analysis['background']['setting']}")

    # 2. 소스 얼굴/착장 분석
    print("\n👤 소스 얼굴/착장 분석 중...")
    source_analysis = analyze_source_person(source_path)
    print(f"  - 얼굴: {source_analysis['face']['age']} {source_analysis['face']['gender']}")
    print(f"  - 착장: {source_analysis['outfit']['description']}")

    # 3. 프롬프트 조립
    prompt = build_pose_copy_prompt(
        ref_analysis,
        source_analysis,
        background_option,
        custom_background
    )
    print(f"\n📝 프롬프트:\n{prompt[:200]}...")

    # 4. 출력 폴더
    if output_dir is None:
        output_dir = f"Fnf_studio_outputs/pose_copy/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)

    # 5. 생성 & 검수 루프
    results = []
    temperature_sequence = [0.2, 0.1, 0.05]

    for i in range(count):
        print(f"\n🎨 이미지 생성 중... ({i+1}/{count})")

        for attempt, temp in enumerate(temperature_sequence):
            if attempt > 0:
                print(f"  재시도 {attempt}회 (temperature={temp})")

            # 생성
            result_img = generate_pose_copy(
                reference_path,
                prompt,
                temperature=temp,
                image_size=image_size
            )

            # 검수
            validation = validate_pose_copy(
                reference_path,
                source_path,
                result_img
            )

            print(f"  검수 결과: {validation['total_score']:.1f}/100")
            print(f"  포즈 유사도: {validation['pose_comparison']['similarity_score']:.1f}")

            if validation["pass"]:
                # 성공
                results.append(result_img)
                output_path = f"{output_dir}/result_{i+1:02d}.png"
                result_img.save(output_path)
                print(f"  ✅ 저장: {output_path}")
                break
            else:
                # 실패
                issues = validation.get("auto_fail_reasons", [])
                if not issues:
                    issues = validation["pose_similarity"].get("issues", [])
                print(f"  ❌ 실패: {issues}")

                if attempt >= 2:
                    # 최대 재시도 초과
                    print(f"  ⚠️  최대 재시도 초과, 다음 이미지로...")
                    break

    return results
```

---

## 사용 예시

```python
from datetime import datetime
import os

# 1. 경로 설정
reference_path = r"D:\photos\reference.jpg"  # 포즈/구도 복제 대상
source_path = r"D:\photos\source.jpg"  # 얼굴/착장 유지 대상

# 2. 출력 폴더
output_dir = f"Fnf_studio_outputs/pose_copy/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(output_dir, exist_ok=True)

# 3. Pose Copy 실행
from core.pose_copy import pose_copy

results = pose_copy(
    reference_path=reference_path,
    source_path=source_path,
    background_option="reference",  # 레퍼런스 배경 사용
    output_dir=output_dir,
    count=3,
    image_size="2K"
)

print(f"\n✅ {len(results)}장 생성 완료!")
```

---

## 출력 폴더 구조

```
Fnf_studio_outputs/
└── pose_copy/
    └── 20260211_103045/
        ├── result_01.png
        ├── result_02.png
        └── result_03.png
```

---

## 파일 구조

```
.claude/skills/포즈따라하기_pose-copy/
├── SKILL.md          # 이 문서
└── examples/         # 예시 이미지 (선택)
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 포즈가 다름 | 레퍼런스 복잡한 포즈 | 단순한 포즈 레퍼런스 선택 |
| 얼굴이 안 닮음 | 소스 분석 약함 | 정면, 고해상도 소스 이미지 사용 |
| 착장 변경됨 | 소스 분석 실패 | 착장 명확한 소스 이미지 선택 |
| 구도가 다름 | 프롬프트 약함 | composition 강조 추가 |
| 배경이 어색함 | 배경 옵션 불일치 | background_option 재선택 |

---

## 핵심 원칙

| 항목 | 처리 방식 |
|------|----------|
| 레퍼런스 이미지 | API에 직접 전달 (포즈/구도 보존) |
| 소스 이미지 | VLM 분석 → 텍스트로만 전달 (얼굴/착장) |
| 포즈 | 레퍼런스에서 복제 (절대 변경 금지) |
| 얼굴 | 소스에서 유지 (절대 변경 금지) |
| 착장 | 소스에서 유지 (절대 변경 금지) |
| 구도 | 레퍼런스에서 복제 |
| 배경 | 옵션에 따라 선택 (reference/source/custom) |

**왜 이렇게 설계했는가?**
- 레퍼런스를 이미지로 전달 → API가 포즈/구도를 강하게 보존
- 소스를 텍스트로 전달 → 포즈 혼동 방지, 얼굴/착장 명확 전달
- 배경 옵션 → 유연한 활용 (화보/커머스/인플루언서 등)

---

## 활용 사례

| 용도 | 설정 |
|------|------|
| 브랜드 화보 | bg_option="reference", 전문 모델 포즈 복제 |
| 커머스 룩북 | bg_option="custom", 스튜디오 배경 지정 |
| 인플루언서 컨텐츠 | bg_option="reference", 트렌디한 포즈 복제 |
| 패션 매거진 | bg_option="reference", 에디토리얼 포즈 |
| 소셜 미디어 | bg_option="source", 개인 배경 유지 |
