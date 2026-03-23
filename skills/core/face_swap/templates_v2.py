"""
Face Swap V2 - 배경교체 스타일 프롬프트

핵심 컨셉:
- 인물 전체를 그대로 유지 (배경교체처럼)
- 얼굴 ID만 교체
- 조명 정보만 VLM에서 분석하여 얼굴에 적용
"""

# ============================================================
# 1. 조명 분석 프롬프트 (최소화)
# ============================================================

LIGHTING_ANALYSIS_PROMPT = """이미지의 조명만 분석하세요.

다음 형식으로만 응답:
```json
{
  "direction": "front-left",
  "quality": "soft",
  "color_temp": "neutral"
}
```

direction 옵션: front, front-left, front-right, side-left, side-right, back
quality 옵션: soft, hard, mixed
color_temp 옵션: warm, neutral, cool

JSON만 반환.
"""


# ============================================================
# 2. 메인 생성 프롬프트 (배경교체 스타일)
# ============================================================

FACE_SWAP_PROMPT_V2 = """## CRITICAL RULES

FACE SWAP ONLY - EVERYTHING ELSE IDENTICAL
DO NOT CHANGE POSE. DO NOT CHANGE OUTFIT. DO NOT CHANGE BACKGROUND.
The person's pose, outfit, background must be IDENTICAL to SOURCE.

## MATHEMATICAL REQUIREMENTS
- Person size / Frame = IDENTICAL to SOURCE
- Person position = IDENTICAL to SOURCE
- Scale factor = 1.0 (NO shrinking, NO enlarging)

## IMAGE ROLES

IMAGE 1 (SOURCE): PRESERVE EVERYTHING EXCEPT FACE
- Pose: EXACT COPY
- Outfit: EXACT COPY (colors, logos, textures, all details)
- Background: EXACT COPY
- Body proportions: EXACT COPY
- Hair style: ADAPT to new face naturally

IMAGE 2-3 (FACE REFERENCE): USE THIS FACE IDENTITY ONLY
- Face structure: FROM FACE REFERENCE
- Eyes, nose, lips: FROM FACE REFERENCE
- Skin tone: FROM FACE REFERENCE
- But adapt to SOURCE lighting direction

## FACE INTEGRATION RULES

1. FACE ANGLE: Match SOURCE image exactly
2. FACE POSITION: Same location as SOURCE
3. LIGHTING ON FACE: {lighting_direction}, {lighting_quality}
4. SKIN TONE: From FACE REFERENCE, adapted to {color_temp} lighting
5. EDGE BLENDING: Seamless transition, no halo/glow artifacts

## ABSOLUTE CONSTRAINTS (VIOLATION = FAILURE)

- Pose changed → FAILURE
- Outfit color changed → FAILURE
- Background changed → FAILURE
- Person size changed → FAILURE
- Different person body → FAILURE

## OUTPUT QUALITY

- Natural skin texture (NO plastic/smooth appearance)
- Clean face edge (NO glow, NO color bleeding)
- Consistent lighting across entire image
- Hair transition natural and seamless
- 8K professional photography quality

ONLY CHANGE: WHO the person is (face identity).
EVERYTHING ELSE: PIXEL-PERFECT IDENTICAL to SOURCE.
"""


# ============================================================
# 3. 검수 프롬프트 (간소화)
# ============================================================

VALIDATION_PROMPT_V2 = """Face Swap 결과를 검수하세요.

이미지:
- Image 1: 얼굴 참조 (교체된 얼굴 원본)
- Image 2: 소스 (원본 포즈/착장/배경)
- Image 3: 결과물 (검수 대상)

## 검수 기준

### 1. identity_match (40%)
결과물 얼굴이 얼굴 참조(Image 1)와 동일 인물인가?
- 100: 동일 인물
- 80: 비슷하지만 약간 다름
- 50: 다른 사람

### 2. pose_preserved (25%)
결과물 포즈가 소스(Image 2)와 동일한가?
- 100: 완전 동일
- 80: 약간 다름
- 50: 크게 다름

### 3. outfit_preserved (20%)
결과물 착장이 소스(Image 2)와 동일한가?
- 100: 완전 동일 (색상, 로고, 디테일)
- 80: 약간 다름
- 50: 크게 다름

### 4. quality (15%)
전체 품질 (조명 일관성, 경계 품질, 자연스러움)
- 100: 프로 사진 수준
- 80: 양호
- 50: 문제 있음

## JSON 출력
```json
{
  "identity_match": {"score": 100, "reason": "동일 인물"},
  "pose_preserved": {"score": 100, "reason": "포즈 완전 동일"},
  "outfit_preserved": {"score": 100, "reason": "착장 완전 동일"},
  "quality": {"score": 95, "reason": "자연스러운 결과"},
  "auto_fail": false,
  "auto_fail_reasons": []
}
```

Auto-Fail 조건:
- 다른 사람 얼굴 (identity_match < 70)
- 포즈 변경됨 (pose_preserved < 80)
- 착장 변경됨 (outfit_preserved < 80)
- 인물 크기 변경됨
- 손가락 6개 이상

JSON만 반환.
"""


def build_face_swap_prompt_v2(lighting_analysis: dict) -> str:
    """V2 프롬프트 조립 (조명 정보만 삽입)"""
    return FACE_SWAP_PROMPT_V2.format(
        lighting_direction=lighting_analysis.get("direction", "front"),
        lighting_quality=lighting_analysis.get("quality", "soft"),
        color_temp=lighting_analysis.get("color_temp", "neutral"),
    )
