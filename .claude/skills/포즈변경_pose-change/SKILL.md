---
name: pose-change
description: 기존 이미지의 포즈만 변경 (얼굴, 착장, 배경 유지)
user-invocable: true
trigger-keywords: ["포즈 변경", "포즈 바꾸기", "자세 변경", "pose change"]
---

# 포즈 변경 (Pose Change)

> **핵심 개념**: 기존 이미지에서 포즈만 텍스트로 변경하고 나머지 모든 요소 유지
> 얼굴/착장/배경은 **EXACT 보존**, 포즈는 **텍스트 설명으로 변경**

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
│  Pose Change = 포즈만 변경                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  유지:                      변경:                            │
│  ├─ 얼굴 (EXACT)           └─ 포즈 → 텍스트 설명으로 변경     │
│  ├─ 착장 (EXACT)                                            │
│  ├─ 배경 (EXACT)                                            │
│  └─ 조명 (ADAPT)  ← 새 포즈에 맞게 자연스럽게                 │
│                                                             │
│  포즈 변경 예시:                                              │
│  - "서있기 → 앉기"                                           │
│  - "정면 → 뒤돌기"                                           │
│  - "팔 내리기 → 팔 올리기"                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 입력 구조

| 입력 | 필수 | 처리 방식 |
|------|------|----------|
| 소스 이미지 | ✅ | API에 직접 전달 (얼굴/착장/배경 보존 대상) |
| 새 포즈 설명 | ✅ | 텍스트 프롬프트로 전달 |

---

## 대화 플로우 (경로 질문 → 옵션 클릭)

> **원칙**: 경로 먼저 → 현재 포즈 분석 → 포즈 옵션 클릭 → 생성

### 플로우

```
1. 사용자: "포즈 변경"

2. Claude: "소스 이미지 경로?"
3. 사용자: D:\photo.jpg

4. Claude: [현재 포즈 분석]
   "현재 포즈: 서서 팔 내리고 있는 상태
    어떤 포즈로 바꿀까요?"

   [AskUserQuestion - 포즈 프리셋 클릭 선택]

5. 사용자: 벽에 기대기

6. Claude:
   - 소스 이미지 상세 분석 (얼굴/착장/배경 보존용)
   - 새 포즈로 이미지 생성
   - 검수 실행
   - 결과 저장 및 경로 안내
```

### 포즈 프리셋 옵션 (AskUserQuestion)

```python
AskUserQuestion(questions=[
    {
        "question": "어떤 포즈로 변경할까요?",
        "header": "포즈 프리셋",
        "options": [
            {"label": "앉기 (바닥)", "description": "sitting on floor, legs crossed"},
            {"label": "앉기 (의자)", "description": "sitting on chair, relaxed"},
            {"label": "기대기 (벽)", "description": "leaning against wall, one foot up"},
            {"label": "걷는 중", "description": "walking naturally, mid-stride"},
            {"label": "뒤돌기", "description": "turned away, looking over shoulder"},
            {"label": "팔 꼬고 서기", "description": "standing with arms crossed"},
            {"label": "주머니에 손", "description": "standing, one hand in pocket"},
            {"label": "직접 입력", "description": "원하는 포즈를 직접 설명하세요"}
        ],
        "multiSelect": False
    }
])
```

### 포즈 프리셋 데이터 (v3.0 통합)

**Single Source of Truth**: `db/presets/common/pose_presets.json` (75종)

```python
# v3.0: 통합 프리셋 로더 사용
from core.ai_influencer.presets import load_preset

# 프리셋 ID로 로드 (예: "전신_03")
pose = load_preset("pose", "전신_03")

# v3.0 필드 활용
print(pose["한줄요약"])  # "사이드 앵글에서 기둥에 기대고..."
print(pose["태그"])      # ["사이드앵글", "기대기", ...]
print(pose["stance"])   # "lean"

# 간단 프리셋 (하위 호환용)
POSE_PRESETS = {
    "sit_floor": "sitting on the floor, legs crossed, relaxed posture",
    "sit_chair": "sitting on a chair, legs crossed, casual posture",
    "lean_wall": "leaning against the wall, one foot up, casual stance",
    "walking": "walking naturally, mid-stride, natural motion",
    "back_turn": "turned away from camera, looking back over shoulder",
    "arms_crossed": "standing with arms crossed, confident posture",
    "hand_pocket": "standing relaxed, one hand in pocket, casual stance"
}
```

> 참고: `core/pose_change/presets.py`의 간단 영어 프리셋은 하위 호환용.
> 상세 포즈 데이터가 필요하면 `db/presets/common/pose_presets.json`에서 로드.

---

## API 전송 순서

```
1. 프롬프트 (텍스트) - 포즈 변경 지시 + 새 포즈 설명 + 보존 요소 명시
2. 소스 이미지 - 얼굴/착장/배경 보존 대상
```

---

## VLM 분석 프롬프트

### 소스 이미지 분석 (보존 대상 추출)

```python
SOURCE_POSE_ANALYSIS_PROMPT = """
이 이미지를 분석해서 포즈 변경 시 보존해야 할 모든 요소를 추출하세요.

JSON 출력:
{
  "current_pose": {
    "body_position": "standing",
    "torso_angle": "straight, facing forward",
    "head_position": "straight, looking at camera",
    "arm_left": "hanging naturally by side",
    "arm_right": "hanging naturally by side",
    "leg_left": "straight, bearing weight",
    "leg_right": "straight, bearing weight",
    "weight_distribution": "evenly distributed",
    "overall_description": "standing upright, arms by sides"
  },
  "preserve_elements": {
    "face": {
      "identity": "Korean female, 20s, natural makeup",
      "expression": "slight smile, neutral",
      "skin_tone": "fair, natural",
      "hair": "long black hair, straight, shoulder length",
      "facial_structure": "oval face, defined features"
    },
    "outfit": {
      "top": {
        "type": "oversized hoodie",
        "color": "dark charcoal gray",
        "material": "cotton fleece",
        "details": ["front pocket", "drawstring hood", "ribbed cuffs"],
        "logo": {
          "exists": true,
          "text": "NY",
          "position": "center chest",
          "color": "white",
          "size": "large"
        },
        "fit": "oversized, drop shoulder"
      },
      "bottom": {
        "type": "wide leg jeans",
        "color": "light wash blue",
        "material": "denim",
        "details": ["high waist", "cargo pockets on sides"],
        "fit": "wide leg, ankle length"
      }
    },
    "background": {
      "setting": "concrete wall background",
      "description": "minimalist urban setting, neutral gray concrete wall",
      "lighting": "soft natural light from left side",
      "atmosphere": "clean, modern, industrial-minimal"
    },
    "body_type": {
      "height_proportion": "model proportions, 8-head ratio",
      "build": "slim, athletic",
      "leg_length": "long legs"
    }
  },
  "physical_constraints": {
    "ground_type": "flat floor",
    "nearby_objects": ["concrete wall on background"],
    "space_available": "indoor studio space"
  }
}

**중요**:
- 얼굴 특징을 매우 구체적으로 (피부톤, 헤어스타일, 표정)
- 착장의 모든 디테일 (색상, 로고, 소재, 핏)
- 배경 환경 정확히 설명
- 물리적 제약 사항 명시
"""
```

---

## 이미지 생성 프롬프트 조립

```python
def build_pose_change_prompt(source_analysis, target_pose):
    """
    소스 분석 결과 + 목표 포즈로 프롬프트 조립

    핵심:
    - 얼굴/착장/배경은 소스 분석 결과 그대로 사용
    - 포즈만 target_pose로 변경
    - 조명은 새 포즈에 맞게 자연스럽게 적응
    """

    preserve = source_analysis["preserve_elements"]
    current_pose = source_analysis["current_pose"]
    constraints = source_analysis["physical_constraints"]

    # 착장 설명 조립
    top = preserve["outfit"]["top"]
    bottom = preserve["outfit"]["bottom"]

    outfit_desc = f"""
[TOP - EXACT REPRODUCTION]
- {top['type']}: {top['color']} color
- Material: {top['material']}
- Details: {', '.join(top['details'])}
"""

    if top["logo"]["exists"]:
        outfit_desc += f"""- Logo: "{top['logo']['text']}" in {top['logo']['color']} on {top['logo']['position']}
"""

    outfit_desc += f"""- Fit: {top['fit']}

[BOTTOM - EXACT REPRODUCTION]
- {bottom['type']}: {bottom['color']} color
- Material: {bottom['material']}
- Details: {', '.join(bottom['details'])}
- Fit: {bottom['fit']}
"""

    # 전체 프롬프트
    prompt = f"""
Generate a high-quality fashion photo with EXACT preservation of all elements except pose.

[CRITICAL - PRESERVE EXACTLY]

FACE (DO NOT CHANGE):
- Identity: {preserve['face']['identity']}
- Expression: {preserve['face']['expression']}
- Skin tone: {preserve['face']['skin_tone']}
- Hair: {preserve['face']['hair']}
- Facial structure: {preserve['face']['facial_structure']}

OUTFIT (DO NOT CHANGE):
{outfit_desc}

BACKGROUND (DO NOT CHANGE):
- Setting: {preserve['background']['setting']}
- Description: {preserve['background']['description']}
- Atmosphere: {preserve['background']['atmosphere']}

BODY TYPE (DO NOT CHANGE):
- Proportions: {preserve['body_type']['height_proportion']}
- Build: {preserve['body_type']['build']}
- Leg length: {preserve['body_type']['leg_length']}

[CHANGE - NEW POSE ONLY]

POSE (CHANGE TO THIS):
{target_pose}

Physical constraints:
- Ground type: {constraints['ground_type']}
- Available space: {constraints['space_available']}
- Must be physically plausible and natural

[LIGHTING ADAPTATION]
- Adapt lighting naturally to new pose
- Maintain soft, natural quality
- Ensure face is well-lit
- Shadows should match new body position

[QUALITY REQUIREMENTS]
- High-end fashion editorial quality
- Natural skin texture (not overly polished)
- Sharp focus throughout
- Physically correct pose (no impossible angles)
- Proper weight distribution
- Natural hand/finger positions

DO NOT:
- Change facial features or identity
- Alter outfit colors, logos, or details
- Modify background setting
- Change body proportions
- Create unnatural or impossible poses
- Add yellow/golden cast to skin
"""

    return prompt.strip()
```

---

## API 호출 코드

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import json

# Config에서 모델 상수 로드 (절대 하드코딩 금지!)
from core.config import IMAGE_MODEL, VISION_MODEL

# ============ API 키 로드 ============
def load_api_keys():
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

def get_next_api_key():
    global key_index
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ============ 이미지 변환 ============
def pil_to_part(img, max_size=1024):
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

# ============ VLM 분석 ============
def analyze_with_vlm(image_path, prompt):
    """이미지를 VLM으로 분석해서 텍스트(JSON) 응답 받기"""
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

    # JSON 파싱
    text = response.candidates[0].content.parts[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

# ============ 소스 이미지 분석 ============
def analyze_source_for_pose_change(source_path):
    """소스 이미지에서 보존할 요소 추출"""
    return analyze_with_vlm(source_path, SOURCE_POSE_ANALYSIS_PROMPT)

# ============ 이미지 생성 ============
def generate_pose_change(
    source_path,
    target_pose,
    aspect_ratio="3:4",
    count=1
):
    """
    포즈 변경 이미지 생성

    Args:
        source_path: 소스 이미지 경로
        target_pose: 목표 포즈 설명 (영어)
        aspect_ratio: 비율 ("3:4", "4:5", "9:16", "1:1")
        count: 생성 수량

    Returns:
        List[PIL.Image]
    """

    # 1. 소스 이미지 분석
    print("📷 소스 이미지 분석 중...")
    source_analysis = analyze_source_for_pose_change(source_path)
    current_pose = source_analysis["current_pose"]["overall_description"]
    print(f"  - 현재 포즈: {current_pose}")
    print(f"  - 목표 포즈: {target_pose}")

    # 2. 프롬프트 조립
    prompt = build_pose_change_prompt(source_analysis, target_pose)
    print(f"\n📝 최종 프롬프트:\n{prompt[:300]}...")

    # 3. 소스 이미지 로드
    source_img = Image.open(source_path).convert("RGB")

    # 4. 이미지 생성
    results = []
    for i in range(count):
        print(f"\n🎨 이미지 생성 중... ({i+1}/{count})")

        client = genai.Client(api_key=get_next_api_key())

        # 프롬프트 + 소스 이미지
        parts = [
            types.Part(text=prompt),
            pil_to_part(source_img)
        ]

        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,  # gemini-3-pro-image-preview
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.25,  # 포즈 변경은 약간 높게
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="2K"
                    )
                )
            )

            # 결과 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    results.append(img)
                    print(f"  ✅ 생성 완료!")
                    break

        except Exception as e:
            print(f"  ❌ 생성 실패: {e}")
            continue

    return results
```

---

## 검수 기준 (Validation)

### VLM 검수 프롬프트

```python
POSE_CHANGE_VALIDATION_PROMPT = """
Compare the RESULT image against the SOURCE image to verify pose change quality.

SOURCE: Original image (all elements should be preserved except pose)
RESULT: Generated image with new pose

Verify these criteria:

1. FACE IDENTITY (CRITICAL - must be same person)
   - Facial structure match
   - Skin tone consistency
   - Hair style/color match
   - Expression similarity

2. OUTFIT PRESERVATION (CRITICAL - must be exact)
   - All garment types match
   - Colors exactly preserved
   - Logos/text exactly preserved (position, color, text)
   - Material appearance match
   - Fit/silhouette match

3. POSE CORRECTNESS
   - New pose matches target description
   - Physically plausible (no impossible angles)
   - Natural weight distribution
   - Hands/fingers look natural (no extra fingers)
   - Feet properly grounded

4. BACKGROUND PRESERVATION
   - Setting matches source
   - Environment consistency
   - No unwanted changes

5. LIGHTING ADAPTATION
   - Lighting naturally adapted to new pose
   - Face well-lit
   - Shadows consistent with pose
   - No harsh artifacts

Return JSON:
{
  "face_identity": {
    "score": 95,  // 0-100
    "same_person": true,
    "issues": []
  },
  "outfit_preservation": {
    "score": 90,  // 0-100
    "all_preserved": true,
    "issues": ["slight color saturation difference in top"]
  },
  "pose_correctness": {
    "score": 92,  // 0-100
    "matches_target": true,
    "physically_plausible": true,
    "issues": []
  },
  "physics_plausibility": {
    "score": 85,  // 0-100
    "grounding_correct": true,
    "weight_distribution_natural": true,
    "hand_fingers_normal": true,
    "issues": []
  },
  "background_preservation": {
    "score": 95,  // 0-100
    "preserved": true,
    "issues": []
  },
  "lighting_adaptation": {
    "score": 88,  // 0-100
    "natural": true,
    "face_well_lit": true,
    "issues": []
  },
  "overall_pass": true,
  "auto_fail_triggers": [],  // 치명적 오류 목록
  "recommendation": "PASS"  // PASS / RETRY / FAIL
}

AUTO-FAIL TRIGGERS:
- Different person (face_identity < 80)
- Outfit changed (colors/logos wrong)
- Physically impossible pose
- 6+ fingers or deformed hands
- Body proportions drastically changed
"""

def validate_pose_change(source_path, result_img, target_pose):
    """포즈 변경 결과 검수"""
    # 결과 이미지 임시 저장
    temp_result = "temp_result.png"
    result_img.save(temp_result)

    # VLM으로 SOURCE와 RESULT 동시 분석
    client = genai.Client(api_key=get_next_api_key())

    source_img = Image.open(source_path).convert("RGB")

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part(text=POSE_CHANGE_VALIDATION_PROMPT),
            pil_to_part(source_img),  # SOURCE
            pil_to_part(result_img)   # RESULT
        ])],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"]
        )
    )

    # JSON 파싱
    text = response.candidates[0].content.parts[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    result = json.loads(text.strip())

    # 임시 파일 삭제
    if os.path.exists(temp_result):
        os.remove(temp_result)

    return result
```

### 검수 가중치

| 항목 | 가중치 | Pass 기준 |
|------|--------|----------|
| face_identity | 30% | >= 95 |
| outfit_preservation | 25% | >= 90 |
| pose_correctness | 25% | 요청 포즈와 일치 |
| physics_plausibility | 15% | >= 80 |
| lighting_adaptation | 5% | >= 85 |

### Auto-Fail 조건

- 얼굴 다른 사람 (face_identity < 80)
- 착장 변경됨 (색상/로고 불일치)
- 물리적으로 불가능한 포즈
- 손가락 6개 이상
- 체형 비율 크게 변경

---

## 재시도 전략

```python
def generate_with_retry(source_path, target_pose, max_retries=2):
    """재시도 로직 포함 생성"""

    temperatures = [0.25, 0.15, 0.1]  # 포즈는 약간 높게 시작

    for attempt in range(max_retries + 1):
        temp = temperatures[attempt]
        print(f"\n🔄 시도 {attempt + 1}/{max_retries + 1} (temperature={temp})")

        # 생성
        results = generate_pose_change(
            source_path,
            target_pose,
            aspect_ratio="3:4",
            count=1
        )

        if not results:
            continue

        result_img = results[0]

        # 검수
        validation = validate_pose_change(source_path, result_img, target_pose)

        # Auto-Fail 체크
        if validation["auto_fail_triggers"]:
            print(f"  ❌ Auto-Fail: {validation['auto_fail_triggers']}")
            continue

        # Pass 판정
        if validation["recommendation"] == "PASS":
            print(f"  ✅ 검수 통과!")
            return result_img, validation

        # Retry 판정
        print(f"  ⚠️  재시도 필요: {validation['recommendation']}")
        if validation["outfit_preservation"]["issues"]:
            print(f"     - 착장: {validation['outfit_preservation']['issues']}")
        if validation["pose_correctness"]["issues"]:
            print(f"     - 포즈: {validation['pose_correctness']['issues']}")

    # 최대 재시도 도달
    print(f"\n❌ 최대 재시도 횟수 도달. 마지막 결과 반환.")
    return result_img, validation
```

---

## 전체 사용 예시

```python
from datetime import datetime
import os

# 1. 경로 설정
source_path = r"D:\사진\person.jpg"

# 2. 출력 폴더
output_dir = f"Fnf_studio_outputs/pose_change/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(output_dir, exist_ok=True)

# 3. 포즈 프리셋 선택
pose_preset = POSE_PRESETS["lean_wall"]  # "leaning against the wall, one foot up, casual stance"

# 4. 생성 (재시도 포함)
result_img, validation = generate_with_retry(
    source_path=source_path,
    target_pose=pose_preset,
    max_retries=2
)

# 5. 저장
output_path = f"{output_dir}/result.png"
result_img.save(output_path)
print(f"\n💾 저장: {output_path}")

# 6. 검수 결과 저장
validation_path = f"{output_dir}/validation.json"
with open(validation_path, 'w', encoding='utf-8') as f:
    json.dump(validation, f, indent=2, ensure_ascii=False)
print(f"💾 검수 결과: {validation_path}")
```

---

## 출력 폴더

```
Fnf_studio_outputs/
└── pose_change/
    └── 20260211_143045/
        ├── result.png
        └── validation.json
```

---

## 파일 구조

```
.claude/skills/포즈변경_pose-change/
├── SKILL.md          # 이 문서
└── examples/         # 예시 이미지 (선택)
```

---

## 핵심 원칙

| 항목 | 처리 방식 |
|------|----------|
| 소스 이미지 | **API에 직접 전달** (얼굴/착장/배경 보존) |
| 새 포즈 | **텍스트로만 전달** (프롬프트 설명) |
| 조명 | 새 포즈에 맞게 자연스럽게 적응 |

**왜 소스를 직접 전달?**
- 얼굴/착장/배경의 정확한 보존을 위해
- VLM 분석은 보조용 (프롬프트에 상세 설명 추가)
- API가 이미지를 직접 참조하면 더 정확

**왜 포즈는 텍스트로?**
- 레퍼런스 포즈 이미지가 없을 때 유연하게 대응
- 텍스트 설명만으로도 AI가 자연스러운 포즈 생성 가능
- 물리적 제약 조건도 함께 명시 가능

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 얼굴 바뀜 | temperature 너무 높음 | 0.1로 낮추기 |
| 착장 색상 변경 | 착장 설명 부족 | VLM 분석 강화, 프롬프트 "EXACT" 강조 |
| 포즈 부자연스러움 | 물리 제약 미명시 | 물리적 제약 조건 프롬프트에 추가 |
| 손가락 오류 | 포즈가 너무 복잡 | 단순한 포즈로 변경 또는 재생성 |
| 배경 바뀜 | 배경 설명 부족 | 배경 상세 설명 강화 |

---

## 개발 예정 기능

- [ ] 포즈 프리셋 확장 (30+ 포즈)
- [ ] 포즈 레퍼런스 이미지 지원 (pose-copy 스킬)
- [ ] 멀티 샷 생성 (3가지 포즈 동시)
- [ ] 포즈 물리 엔진 검증 강화
