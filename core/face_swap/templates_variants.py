"""
Face Swap 프롬프트 변형 A/B/C

A/B 테스트를 위한 3가지 프롬프트 전략:
- 변형 A (Minimal): VLM 분석 의존도 최소화, 고정 템플릿
- 변형 B (Category): 카테고리 enum만 사용, 자유 텍스트 제거
- 변형 C (Hybrid): 카테고리 + 짧은 요약 (20자 이내)
"""

# ============================================================
# 카테고리 기반 SOURCE_ANALYSIS_PROMPT (공통)
# ============================================================

SOURCE_ANALYSIS_PROMPT_V2 = """이미지를 분석하고 다음 카테고리에서 **정확히 하나씩** 선택하세요.

## 카테고리 선택 (필수)

face_angle_category: 다음 중 하나 선택
- "frontal" (정면)
- "3/4-left" (왼쪽 3/4)
- "3/4-right" (오른쪽 3/4)
- "profile-left" (왼쪽 측면)
- "profile-right" (오른쪽 측면)

pose_category: 다음 중 하나 선택
- "standing" (서있음)
- "sitting" (앉아있음)
- "dynamic" (동적 포즈)
- "casual" (편안한 포즈)

lighting_category: 다음 중 하나 선택
- "front" (정면)
- "front-left" (왼쪽 앞)
- "front-right" (오른쪽 앞)
- "back" (역광)
- "side-left" (왼쪽 측면)
- "side-right" (오른쪽 측면)

background_category: 다음 중 하나 선택
- "studio" (스튜디오)
- "outdoor-urban" (도시 야외)
- "outdoor-nature" (자연 야외)
- "indoor" (실내)
- "abstract" (추상/단색)

## JSON 출력 (반드시 이 형식)
{
  "face_angle_category": "선택값",
  "pose_category": "선택값",
  "lighting_category": "선택값",
  "background_category": "선택값",
  "face_position": {"x": 0.0-1.0, "y": 0.0-1.0},
  "pose_brief": "20자 이내 설명",
  "outfit_brief": "20자 이내 설명"
}

JSON만 반환, 설명 없이.
"""


# ============================================================
# 변형 A - Minimal VLM (고정 템플릿, VLM 분석 없음)
# ============================================================

FACE_SWAP_PROMPT_A = """[IMAGE ROLE ASSIGNMENT]
IMAGE 1: SOURCE - PRESERVE EVERYTHING EXCEPT FACE
IMAGE 2-3: FACE REFERENCE - USE THIS FACE ONLY

[FACE SWAP INSTRUCTIONS]
- Replace ONLY the face with the provided face reference
- Preserve EXACT pose from source (body position, arm position, leg position)
- Preserve EXACT outfit from source (all colors, logos, patterns, details)
- Preserve EXACT background from source
- Match lighting on face to source lighting direction and quality
- Adapt hair naturally to the new face

[OUTPUT QUALITY]
- Natural skin texture (no plastic/overly smooth appearance)
- Neutral cool white balance (NO golden/warm/sepia tones)
- Clean edge between face and surrounding area, no artifacts
- Natural hair transition
- Sharp focus on face
- 8K professional photography quality

CRITICAL: Only change who the person is. Everything else stays EXACTLY the same.
Do NOT change pose, outfit, background, body proportions, or lighting direction.
"""


# ============================================================
# 변형 B - Category Only (카테고리만, 자유 텍스트 제거)
# ============================================================

FACE_SWAP_PROMPT_B = """[IMAGE ROLE ASSIGNMENT]
IMAGE 1: SOURCE - PRESERVE EVERYTHING EXCEPT FACE
IMAGE 2-3: FACE REFERENCE - USE THIS FACE ONLY

[SOURCE IMAGE PROPERTIES]
- Face angle: {face_angle_category}
- Pose type: {pose_category}
- Lighting: {lighting_category}
- Background: {background_category}

[FACE SWAP INSTRUCTIONS]
- Replace ONLY the face with the provided face reference
- Match face angle exactly: {face_angle_category}
- Preserve EXACT pose from source ({pose_category})
- Preserve EXACT outfit from source (all colors, logos, details)
- Preserve EXACT background from source ({background_category})
- Match lighting on face to source: {lighting_category}
- Adapt hair naturally to the new face

[OUTPUT QUALITY]
- Natural skin texture (no plastic/overly smooth appearance)
- Neutral cool white balance (NO golden/warm/sepia tones)
- Clean edge between face and surrounding area, no artifacts
- Natural hair transition
- Sharp focus on face
- 8K professional photography quality

CRITICAL: Only change who the person is. Everything else stays EXACTLY the same.
"""


# ============================================================
# 변형 C - Hybrid (카테고리 + 짧은 요약)
# ============================================================

FACE_SWAP_PROMPT_C = """[IMAGE ROLE ASSIGNMENT]
IMAGE 1: SOURCE - PRESERVE EVERYTHING EXCEPT FACE
IMAGE 2-3: FACE REFERENCE - USE THIS FACE ONLY

[SOURCE IMAGE ANALYSIS]
Face: {face_angle_category} angle, position {face_position}
Pose: {pose_category} - {pose_brief}
Outfit: {outfit_brief}
Lighting: {lighting_category}
Background: {background_category}

[FACE SWAP INSTRUCTIONS]
- Replace ONLY the face with the provided face reference
- Match face angle exactly: {face_angle_category}
- Preserve pose: {pose_brief}
- Preserve outfit: {outfit_brief}
- Match lighting direction: {lighting_category}
- Adapt hair naturally to the new face

[OUTPUT QUALITY]
- Natural skin texture (no plastic/overly smooth appearance)
- Neutral cool white balance (NO golden/warm/sepia tones)
- Clean edge between face and surrounding area, no artifacts
- Natural hair transition
- Sharp focus on face
- 8K professional photography quality

CRITICAL: Only change who the person is. Everything else stays EXACTLY the same.
"""


# ============================================================
# 카테고리 정의 (검증용)
# ============================================================

VALID_CATEGORIES = {
    "face_angle_category": [
        "frontal",
        "3/4-left",
        "3/4-right",
        "profile-left",
        "profile-right",
    ],
    "pose_category": ["standing", "sitting", "dynamic", "casual"],
    "lighting_category": [
        "front",
        "front-left",
        "front-right",
        "back",
        "side-left",
        "side-right",
    ],
    "background_category": [
        "studio",
        "outdoor-urban",
        "outdoor-nature",
        "indoor",
        "abstract",
    ],
}


def validate_category(key: str, value: str) -> bool:
    """카테고리 값 검증"""
    if key not in VALID_CATEGORIES:
        return False
    return value in VALID_CATEGORIES[key]


def get_variant_prompt(variant: str) -> str:
    """변형 ID로 프롬프트 템플릿 반환"""
    variants = {
        "A": FACE_SWAP_PROMPT_A,
        "B": FACE_SWAP_PROMPT_B,
        "C": FACE_SWAP_PROMPT_C,
    }
    return variants.get(variant.upper(), FACE_SWAP_PROMPT_A)
