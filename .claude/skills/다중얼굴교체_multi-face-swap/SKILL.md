---
name: multi-face-swap
description: 단체 사진에서 여러 얼굴을 동시에 교체
user-invocable: true
trigger-keywords: ["다중 얼굴 교체", "단체 사진 얼굴", "multi face swap", "여러 얼굴", "그룹 사진 얼굴"]
---

# 다중 얼굴 교체 (Multi-Face Swap)

> **핵심 개념**: 단체 사진에서 여러 얼굴을 동시에 교체
> VLM으로 각 인물 위치/특징 감지 → 얼굴 폴더 매핑 → 모든 얼굴 동시 스왑
> 다른 모든 요소(포즈, 착장, 배경, 구도)는 정확히 유지

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
│  Multi-Face Swap = 단체사진 다중 얼굴 교체                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  입력:                                                       │
│  1. 단체 사진 (N명, 2~10명 권장)                             │
│  2. 각 인물별 얼굴 폴더 매핑:                                 │
│     - 인물1 → faces/person1/                                │
│     - 인물2 → faces/person2/                                │
│     - 인물3 → faces/person3/                                │
│     - 인물N → faces/personN/                                │
│                                                             │
│  처리:                                                       │
│  1. VLM으로 사진 내 인물 위치/특징 감지                       │
│  2. 사용자에게 각 인물 얼굴 폴더 매핑 요청                     │
│  3. 모든 얼굴 동시 스왑 (한번에 처리)                          │
│                                                             │
│  유지:                                                       │
│  ├─ 각 인물 포즈 (EXACT)                                     │
│  ├─ 각 인물 착장 (EXACT)                                     │
│  ├─ 각 인물 체형 (EXACT)                                     │
│  ├─ 그룹 구도 (EXACT)                                        │
│  ├─ 배경 (EXACT)                                            │
│  ├─ 조명 (EXACT)                                            │
│  └─ 상대 위치 (EXACT)                                        │
│                                                             │
│  변경:                                                       │
│  └─ 모든 인물 얼굴 → 제공된 얼굴로 교체                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 대화 플로우 (경로 순차 → 옵션 클릭 → 일괄 생성)

> **원칙**: 사진 분석 → 인물 감지 결과 출력 → 각 인물별 얼굴 폴더 매핑 → 옵션 클릭 선택 → 생성

### 플로우

```
1. 사용자: "다중 얼굴 교체"

2. Claude: "단체 사진 경로를 알려주세요."

3. 사용자: D:\group_photo.jpg

4. Claude: [VLM 분석 시작]
   "단체 사진 분석 중..."
   [detect_faces() 함수 호출 - core/person_utils.py]

5. Claude: [분석 결과 테이블 출력]
   "4명의 인물이 감지되었습니다.

   | # | 위치 | 얼굴 각도 | 구분 특징 |
   |---|------|----------|----------|
   | 1 | 왼쪽 | frontal | 빨간 재킷 착용 |
   | 2 | 왼쪽-중앙 | 3/4 left | 흰색 티셔츠 |
   | 3 | 오른쪽-중앙 | frontal | 검은 후드 |
   | 4 | 오른쪽 | 3/4 right | 청색 재킷 |

   각 인물에 적용할 얼굴 폴더를 순서대로 알려주세요."

6. Claude: "Person 1 (왼쪽, 빨간 재킷)의 얼굴 이미지 폴더 경로?"
   사용자: D:\faces\alice

7. Claude: "Person 2 (왼쪽-중앙, 흰 티셔츠)의 얼굴 이미지 폴더 경로?"
   사용자: D:\faces\bob

8. Claude: "Person 3 (오른쪽-중앙, 검은 후드)의 얼굴 이미지 폴더 경로?"
   사용자: D:\faces\charlie

9. Claude: "Person 4 (오른쪽, 청색 재킷)의 얼굴 이미지 폴더 경로?"
   사용자: D:\faces\diana

10. Claude: [매핑 확인 테이블 출력]
    "얼굴 매핑:

    | 인물 | 원본 특징 | 적용할 얼굴 폴더 |
    |------|----------|-----------------|
    | 1 (왼쪽) | 빨간 재킷 | D:\faces\alice |
    | 2 (왼쪽-중앙) | 흰 티셔츠 | D:\faces\bob |
    | 3 (오른쪽-중앙) | 검은 후드 | D:\faces\charlie |
    | 4 (오른쪽) | 청색 재킷 | D:\faces\diana |"

11. Claude: [AskUserQuestion - 수량/화질 클릭 선택]

12. 사용자: 클릭으로 선택

13. Claude: [얼굴 이미지 선택 + 생성]
    "각 폴더에서 얼굴 이미지 선택 중..."
    "다중 얼굴 교체 이미지 생성 중..."
    [MULTI_FACE_SWAP_PROMPT + API 호출]

14. Claude: [검수]
    "검수 중..."
    [MULTI_FACE_VALIDATION_PROMPT로 검증]

15. Claude: [결과]
    "✅ 다중 얼굴 교체 완료!

    검수 결과:
    - 인물1 얼굴 동일성: 96
    - 인물2 얼굴 동일성: 94
    - 인물3 얼굴 동일성: 95
    - 인물4 얼굴 동일성: 97
    - 상대 위치 유지: ✓
    - 그룹 구도 유지: ✓

    저장 경로: Fnf_studio_outputs/multi_face_swap/20260210_153045/result_01.png"
```

### 경로 질문 (순차, 일반 텍스트)

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "단체 소스 이미지 경로?" | ✅ |
| 2 | "Person 1의 얼굴 이미지 폴더 경로?" | ✅ |
| 3 | "Person 2의 얼굴 이미지 폴더 경로?" | ✅ |
| ... | (인물 수만큼 반복) | ✅ |

### 옵션 선택 (AskUserQuestion 클릭)

```python
AskUserQuestion(questions=[
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
| 수량 | 3장 |
| 화질 | 2K |

---

## API 전송 순서 (중요!)

```
1. 프롬프트 (텍스트)
   - 다중 얼굴 교체 지시
   - 각 인물 위치 및 매핑 정보 명시

2. 소스 이미지 (단체 사진)
   - 첫 번째 이미지
   - 포즈/착장/배경/구도 보존 대상

3. 인물1 얼굴 이미지들 (라벨: PERSON_1)
   - 1~2장 자동 선택

4. 인물2 얼굴 이미지들 (라벨: PERSON_2)
   - 1~2장 자동 선택

5. 인물3 얼굴 이미지들 (라벨: PERSON_3)
   - 1~2장 자동 선택

... 인물N까지 반복
```

**핵심 원칙:**
- 소스 이미지 항상 첫 번째 전송
- 각 인물 얼굴은 명확히 라벨링 (PERSON_1, PERSON_2, ...)
- 위치 순서대로 전송 (왼쪽 → 오른쪽)

---

## VLM 분석 프롬프트

### 1. 인물 감지 (detect_faces() from core/person_utils.py)

**핵심**: `core/person_utils.py`의 `detect_faces()` 함수 활용

```python
from core.config import VISION_MODEL
from core.person_utils import detect_faces

# 단체 사진 분석 시 detect_faces() 호출
persons_info = detect_faces(group_image_path)

# 반환 형식:
# {
#   "total_persons": 4,
#   "persons": [
#     {
#       "id": 1,
#       "position": "left",
#       "bbox": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.8},
#       "face_angle": "frontal",
#       "clothing_hint": "빨간 재킷",
#       "hair_hint": "긴 검은 머리",
#       "distinguishing_features": "안경 착용"
#     },
#     ...
#   ]
# }
```

### MULTI_FACE_DETECTION_PROMPT (detect_faces() 내부 사용)

```python
MULTI_FACE_DETECTION_PROMPT = """
이 단체 사진에서 모든 인물을 감지하고 각 인물의 위치와 특징을 분석하세요.

JSON 출력:
{
  "total_persons": 4,
  "persons": [
    {
      "id": 1,
      "position": "left",  // left, center-left, center, center-right, right
      "bbox": {
        "x1": 0.1,  // normalized coordinates (0.0 ~ 1.0)
        "y1": 0.2,
        "x2": 0.3,
        "y2": 0.8
      },
      "face_angle": "frontal",  // frontal, 3/4 left, 3/4 right, profile left, profile right
      "clothing_hint": "빨간 재킷",  // 구분용 특징
      "hair_hint": "긴 검은 머리",
      "distinguishing_features": "안경 착용"
    },
    {
      "id": 2,
      "position": "center-left",
      "bbox": {"x1": 0.3, "y1": 0.15, "x2": 0.5, "y2": 0.85},
      "face_angle": "3/4 left",
      "clothing_hint": "흰색 티셔츠",
      "hair_hint": "짧은 갈색 머리",
      "distinguishing_features": "턱수염"
    },
    {
      "id": 3,
      "position": "center-right",
      "bbox": {"x1": 0.5, "y1": 0.18, "x2": 0.7, "y2": 0.82},
      "face_angle": "frontal",
      "clothing_hint": "검은 후드",
      "hair_hint": "중간 길이 금발",
      "distinguishing_features": "없음"
    },
    {
      "id": 4,
      "position": "right",
      "bbox": {"x1": 0.7, "y1": 0.2, "x2": 0.9, "y2": 0.8},
      "face_angle": "3/4 right",
      "clothing_hint": "청색 재킷",
      "hair_hint": "긴 웨이브 머리",
      "distinguishing_features": "목걸이"
    }
  ],
  "group_arrangement": "horizontal line",  // horizontal line, staggered, clustered
  "overall_composition": "casual group shot, outdoor setting"
}

규칙:
1. 모든 인물을 **왼쪽에서 오른쪽 순서로** ID 부여
2. bbox는 정규화된 좌표 (0.0 ~ 1.0)
3. clothing_hint는 사용자가 인물을 구분할 수 있는 특징
4. face_angle은 정확히 파악 (각 얼굴마다 다를 수 있음)
5. 부분적으로 가려진 인물도 포함
"""
```

---

## 프롬프트 조립 로직

### 2. 다중 얼굴 교체 프롬프트 (MULTI_FACE_SWAP_PROMPT)

```python
def build_multi_face_swap_prompt(persons_info, face_mappings):
    """
    다중 얼굴 교체 프롬프트 생성

    Args:
        persons_info: VLM 분석 결과 (MULTI_FACE_DETECTION_PROMPT)
        face_mappings: {person_id: face_folder_path} 매핑

    Returns:
        str: 다중 얼굴 교체 프롬프트
    """

    # 인물별 매핑 정보 생성
    person_mappings = []
    for person in persons_info["persons"]:
        person_id = person["id"]
        position = person["position"]
        clothing = person["clothing_hint"]

        person_mappings.append(
            f"PERSON {person_id} ({position}, {clothing}): "
            f"Use face from PERSON_{person_id} reference images"
        )

    mappings_text = "\n".join(person_mappings)

    prompt = f"""
[CRITICAL - MULTI-FACE SWAP INSTRUCTION]

You are receiving a GROUP PHOTO with {persons_info["total_persons"]} people.
Each person will have their face SWAPPED with provided reference faces.

📷 IMAGE 1 (SOURCE): Group photo
   - This is the SOURCE image to preserve
   - PRESERVE EXACTLY:
     * All body poses
     * All clothing
     * All body proportions
     * Group composition
     * Background
     * Lighting
     * Relative positions
   - CHANGE ONLY: All faces

👥 FACE MAPPINGS:
{mappings_text}

⚠️ CRITICAL RULES:

1. PRESERVE ALL NON-FACE ELEMENTS:
   - Keep exact poses for each person
   - Keep exact clothing for each person
   - Keep exact body types
   - Keep group arrangement (spacing, positions)
   - Keep background EXACTLY
   - Keep lighting EXACTLY

2. FACE SWAP ACCURACY:
   - Use PERSON_1 reference for person in position "{persons_info["persons"][0]["position"]}"
   - Use PERSON_2 reference for person in position "{persons_info["persons"][1]["position"]}" if exists
   - Use PERSON_3 reference for person in position "{persons_info["persons"][2]["position"]}" if exists
   - ... and so on for all persons
   - Each face MUST match the corresponding reference EXACTLY

3. NO POSITION SWAPS:
   - Do NOT swap people's positions
   - Each person stays in their EXACT location
   - Maintain LEFT-TO-RIGHT order

4. CONSISTENCY:
   - Face identity >= 95% match for each person
   - Natural neck/face blending
   - Consistent lighting on all faces
   - Match skin tones appropriately

5. QUALITY:
   - Natural group photo appearance
   - No AI artifacts on any face
   - Clean face boundaries
   - Appropriate facial expressions for group setting

OUTPUT:
- High-quality group photo
- All faces swapped accurately
- Everything else preserved EXACTLY
- Natural and cohesive result

🚫 DO NOT:
- Change any clothing
- Change any poses
- Move people to different positions
- Alter background
- Mix up face assignments
- Add or remove people
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

# ============================================================================
# API 키 로드
# ============================================================================
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

# ============================================================================
# 이미지 변환
# ============================================================================
def pil_to_part(img, max_size=1024):
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

# ============================================================================
# VLM 분석 (텍스트 응답)
# ============================================================================
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
            temperature=0.3,
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

# ============================================================================
# 인물 감지
# ============================================================================
def detect_persons(group_image_path):
    """단체 사진에서 모든 인물 감지"""
    return analyze_with_vlm(group_image_path, MULTI_FACE_DETECTION_PROMPT)

# ============================================================================
# 얼굴 이미지 선택
# ============================================================================
def select_face_images(face_folder):
    """폴더에서 가장 적합한 얼굴 이미지 1~2장 선택"""
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = [f for f in os.listdir(face_folder)
              if os.path.splitext(f)[1].lower() in extensions]

    if not images:
        raise ValueError(f"폴더에 이미지가 없습니다: {face_folder}")

    if len(images) <= 2:
        return [os.path.join(face_folder, img) for img in images]

    # 간단한 품질 체크로 선택
    selected = []
    for img_name in images[:5]:
        img_path = os.path.join(face_folder, img_name)
        try:
            img = Image.open(img_path)
            if img.size[0] >= 512 and img.size[1] >= 512:
                selected.append(img_path)
                if len(selected) >= 2:
                    break
        except:
            continue

    return selected if selected else [os.path.join(face_folder, images[0])]

# ============================================================================
# 다중 얼굴 교체 생성
# ============================================================================
def generate_multi_face_swap(
    group_image_path,
    face_mappings,  # {person_id: face_folder_path}
    output_dir=None,
    count=1
):
    """
    다중 얼굴 교체 생성

    Args:
        group_image_path: 단체 사진 경로
        face_mappings: {1: "D:\\faces\\alice", 2: "D:\\faces\\bob", ...}
        output_dir: 출력 폴더 (None이면 자동 생성)
        count: 생성 수량

    Returns:
        List[PIL.Image]
    """
    from datetime import datetime

    # 1. 단체 사진 분석
    print("📷 단체 사진 분석 중...")
    persons_info = detect_persons(group_image_path)
    total_persons = persons_info["total_persons"]
    print(f"  - 감지된 인물: {total_persons}명")

    # 2. 각 인물별 얼굴 이미지 선택
    print("\n👤 각 인물 얼굴 이미지 선택 중...")
    all_face_images = {}
    for person_id, face_folder in face_mappings.items():
        face_paths = select_face_images(face_folder)
        all_face_images[person_id] = face_paths
        print(f"  - 인물 {person_id}: {[os.path.basename(p) for p in face_paths]}")

    # 3. 프롬프트 조립
    prompt = build_multi_face_swap_prompt(persons_info, face_mappings)
    print(f"\n📝 프롬프트 생성 완료")

    # 4. 출력 폴더
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f"Fnf_studio_outputs/multi_face_swap/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # 5. 이미지 생성
    results = []
    for i in range(count):
        print(f"\n🎨 이미지 생성 중... ({i+1}/{count})")

        client = genai.Client(api_key=get_next_api_key())

        # Parts 조립: 프롬프트 + 소스 이미지 + 각 인물 얼굴 이미지들
        parts = [types.Part(text=prompt)]

        # 소스 이미지 (단체 사진)
        group_img = Image.open(group_image_path).convert("RGB")
        parts.append(pil_to_part(group_img))

        # 각 인물 얼굴 이미지 (순서대로)
        for person_id in sorted(all_face_images.keys()):
            for face_path in all_face_images[person_id]:
                face_img = Image.open(face_path).convert("RGB")
                parts.append(pil_to_part(face_img))

        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,  # gemini-3-pro-image-preview
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.15,  # 낮게 시작 (일관성 중요)
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio="original",  # 원본 비율 유지
                        image_size="2K"
                    )
                )
            )

            # 결과 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    results.append(img)

                    # 저장
                    output_path = f"{output_dir}/result_{i+1:02d}.png"
                    img.save(output_path)
                    print(f"  ✅ 생성 완료: {output_path}")
                    break

        except Exception as e:
            print(f"  ❌ 생성 실패: {e}")
            continue

    return results
```

---

## 검수 기준

| 항목 | 가중치 | Pass 기준 |
|------|--------|----------|
| all_faces_identity | 50% | 모든 얼굴 >= 90 |
| relative_positions | 20% | 위치 변경 없음 |
| group_composition | 15% | 그룹 구도 유지 |
| individual_preservation | 15% | 각 인물 체형/착장 유지 |

### Auto-Fail 조건

- 인물 누락 (감지된 인물 수와 결과 인물 수 불일치)
- 위치 뒤바뀜 (왼쪽 사람이 오른쪽으로 이동 등)
- 얼굴 동일성 < 80 (어느 한 명이라도)
- 착장 변경됨
- 체형 변경됨

---

## 검수 VLM 프롬프트

### MULTI_FACE_VALIDATION_PROMPT

```python
MULTI_FACE_VALIDATION_PROMPT = """
이 두 이미지를 비교해서 다중 얼굴 교체가 정확히 수행되었는지 검증하세요.

Image 1: SOURCE (원본 단체 사진)
Image 2: RESULT (얼굴 교체 결과)

검증 항목:

1. 인물 수 일치
   - 원본과 결과의 인물 수가 동일한가?

2. 각 인물별 얼굴 동일성 (Face Identity)
   - 인물1 얼굴: 참조 얼굴과 동일 인물인가? (0-100 점수)
   - 인물2 얼굴: 참조 얼굴과 동일 인물인가? (0-100 점수)
   - 인물3 얼굴: 참조 얼굴과 동일 인물인가? (0-100 점수)
   - ... 모든 인물 평가

3. 상대 위치 유지 (Relative Positions)
   - 각 인물의 위치가 원본과 동일한가?
   - 왼쪽 사람이 여전히 왼쪽에 있는가?
   - 인물 간 간격이 유지되었는가?

4. 그룹 구도 유지 (Group Composition)
   - 전체 그룹 배치가 원본과 동일한가?
   - 프레이밍이 유지되었는가?

5. 개별 인물 보존 (Individual Preservation)
   - 각 인물의 포즈가 유지되었는가?
   - 각 인물의 착장이 유지되었는가?
   - 각 인물의 체형이 유지되었는가?

JSON 출력:
{
  "person_count_match": true,
  "face_identities": [
    {"person": 1, "position": "left", "score": 96, "match": true},
    {"person": 2, "position": "center-left", "score": 94, "match": true},
    {"person": 3, "position": "center-right", "score": 95, "match": true},
    {"person": 4, "position": "right", "score": 97, "match": true}
  ],
  "relative_positions_preserved": true,
  "position_issues": [],  // 예: ["person 2 moved to right"]
  "group_composition_score": 98,
  "individual_preservation": {
    "poses_preserved": true,
    "clothing_preserved": true,
    "body_types_preserved": true
  },
  "overall_score": 95,
  "pass": true,
  "issues": []  // 문제점 리스트
}

Pass 기준:
- all_faces_identity: 모든 얼굴 >= 90
- relative_positions_preserved: true
- group_composition_score: >= 90
- individual_preservation: 모든 항목 true
- overall_score: >= 95
"""
```

---

## 재시도 전략

### Fallback Strategy

실패 시 전략:

1. **Temperature 조정**: 0.15 → 0.1 → 0.05
2. **최대 재시도**: 3회 (복잡도 고려)
3. **Fallback**: 모든 재시도 실패 시 → 단일 얼굴씩 순차 스왑
   ```python
   # 다중 스왑 3회 실패 시
   # → face-swap을 각 인물에 순차 적용
   # → 결과 이미지를 다음 소스로 사용
   # 예: result1 = face_swap(source, person1_face)
   #     result2 = face_swap(result1, person2_face)
   #     result3 = face_swap(result2, person3_face)
   #     ...
   ```

### 재생성 트리거

| 실패 원인 | 재생성 전략 |
|----------|------------|
| 얼굴 동일성 < 80 (1명 이상) | Temperature 낮추기 |
| 위치 뒤바뀜 | 프롬프트에 위치 정보 강화 |
| 인물 누락 | Fallback: 순차 스왑 |
| 착장 변경 | 프롬프트에 "PRESERVE clothing EXACTLY" 추가 |

---

## 전체 사용 예시

```python
from datetime import datetime
import os

# 1. 단체 사진 경로
group_image_path = r"D:\photos\group_photo.jpg"

# 2. 각 인물별 얼굴 폴더 매핑
# (사용자가 VLM 분석 결과 보고 지정)
face_mappings = {
    1: r"D:\faces\alice",    # 왼쪽 (빨간 재킷)
    2: r"D:\faces\bob",      # 왼쪽-중앙 (흰 티셔츠)
    3: r"D:\faces\charlie",  # 오른쪽-중앙 (검은 후드)
    4: r"D:\faces\diana"     # 오른쪽 (청색 재킷)
}

# 3. 생성
results = generate_multi_face_swap(
    group_image_path=group_image_path,
    face_mappings=face_mappings,
    count=1
)

# 4. 결과 확인
print(f"\n✅ 다중 얼굴 교체 완료! {len(results)}장 생성됨.")
```

---

## 핵심 원칙

| 항목 | 처리 방식 |
|------|----------|
| 단체 사진 | **API에 직접 전달** (포즈/착장/구도 보존 핵심!) |
| 각 얼굴 이미지 | **이미지로 직접 전달** (Face Swap) + 명확한 라벨링 |
| 위치 매핑 | **텍스트로 명시** (PERSON_1, PERSON_2, ...) |
| 순서 | **왼쪽 → 오른쪽** 순서 엄수 |

**왜 복잡한가?**
- 여러 얼굴을 동시에 교체하면서 각각 정확히 매핑해야 함
- 인물 간 위치/구도 유지 필요
- 한 명이라도 실패하면 전체 재생성

**왜 순차 스왑을 Fallback으로?**
- 다중 스왑이 실패할 경우 안전한 대안
- 한 번에 하나씩 처리하면 정확도 높아짐
- 시간은 더 걸리지만 신뢰성 보장

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 얼굴 뒤바뀜 | 위치 매핑 혼동 | 프롬프트에 위치 정보 명확히 강화 |
| 인물 누락 | 너무 많은 인물 | 5명 이하 권장, 또는 Fallback 사용 |
| 착장 변경 | 프롬프트 과부하 | "PRESERVE clothing EXACTLY" 강조 |
| 포즈 변경 | 다중 작업 복잡도 | Temperature 낮추기, Fallback 사용 |
| 전체 실패 | 너무 복잡한 구도 | Fallback: 순차 스왑으로 전환 |

---

## 출력 폴더

```
Fnf_studio_outputs/
└── multi_face_swap/
    └── 20260210_153045/
        ├── result_01.png
        ├── result_02.png
        └── analysis_log.json  # 분석 결과 기록
```

---

## 파일 구조

```
.claude/skills/다중얼굴교체_multi-face-swap/
├── SKILL.md          # 이 문서
└── examples/         # 예시 이미지 (선택)
```

---

## 한계점 및 권장사항

### 권장 인원
- **최적**: 2~4명
- **가능**: 5~6명
- **비권장**: 7명 이상 (Fallback 자동 전환)

### 권장 구도
- ✅ 수평 일렬
- ✅ 약간 엇갈린 배치
- ⚠️ 겹쳐진 인물 (일부 가능)
- ❌ 복잡한 3D 배치

### 권장 사진 품질
- 해상도: 최소 1920x1080
- 각 얼굴 크기: 최소 200px
- 조명: 균일한 조명
- 각도: 정면 또는 3/4 뷰 권장

---

## 성공률 향상 팁

1. **사전 분석 결과 확인**: VLM이 감지한 인물 수/위치가 정확한지 확인
2. **고품질 얼굴 이미지**: 각 인물의 얼굴 이미지는 정면, 고해상도 사용
3. **명확한 매핑**: 사용자가 각 인물을 명확히 구분할 수 있도록 특징 제공
4. **Fallback 활용**: 3회 실패 시 자동으로 순차 스왑으로 전환
5. **적은 인원부터**: 처음엔 2~3명으로 테스트 후 점진적으로 증가
