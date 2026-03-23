"""
Face Swap V4 - 기존 성공 패턴 기반

핵심 (Linn_face_swap_v2.py에서 추출):
1. 간결한 프롬프트
2. 레이블 이미지 태그
3. IDENTITY 변경 강조
4. temperature 0.5
"""

# ============================================================
# V4 프롬프트 - 기존 성공 패턴 기반
# ============================================================

FACE_SWAP_PROMPT_V4 = """Swap the face in SOURCE with FACE REFERENCE.

CRITICAL: The person's IDENTITY must change to FACE REFERENCE.
The output person must look like FACE REFERENCE, not SOURCE.

RULES:
- Face identity: REPLACE with FACE REFERENCE completely (ethnicity, features, everything)
- Expression & pose: keep from SOURCE
- Skin tone: use FACE REFERENCE skin tone, adjust to SOURCE lighting
- Lighting & shadow: analyze SOURCE light direction, apply to new face
- Edges: seamless blend at jawline, hairline, neck
- Quality: sharp, high-resolution, photorealistic

The final person must be recognizable as FACE REFERENCE, not SOURCE."""


# ============================================================
# V4-B: 더 간결한 버전
# ============================================================

FACE_SWAP_PROMPT_V4_MINIMAL = """Face swap: Replace face in SOURCE with FACE REFERENCE.

The resulting person must BE the person from FACE REFERENCE.
Not look "similar to" - but actually BE that person.

Keep from SOURCE:
- Pose, body position
- Clothes
- Background
- Lighting direction

Take from FACE REFERENCE:
- Face identity (who the person is)
- Skin tone (adapt to SOURCE lighting)

Blend naturally: jawline, hairline, neck - no visible edges."""


# ============================================================
# V4-C: IDENTITY 강조 버전
# ============================================================

FACE_SWAP_PROMPT_V4_IDENTITY = """IDENTITY SWAP.

SOURCE = scene, pose, clothes, background
FACE REFERENCE = who the person IS

The output person IS the person from FACE REFERENCE.
- Same face structure
- Same skin tone (adapted to lighting)
- Same ethnicity
- Same features

Everything else from SOURCE:
- Same pose exactly
- Same clothes exactly
- Same background exactly
- Same lighting direction

Face must blend seamlessly - no edges, no halo, no artifacts.
Photorealistic quality."""


# ============================================================
# 이미지 태그 포맷
# ============================================================


def get_image_tags():
    """레이블 이미지 태그 반환"""
    return {
        "source": "[SOURCE - scene to modify]:",
        "face": "[FACE REFERENCE - use this exact face]:",
        "face_multi": "[FACE REFERENCE {i}]:",  # {i}는 숫자로 대체
    }


__all__ = [
    "FACE_SWAP_PROMPT_V4",
    "FACE_SWAP_PROMPT_V4_MINIMAL",
    "FACE_SWAP_PROMPT_V4_IDENTITY",
    "get_image_tags",
]
