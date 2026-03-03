"""
Face Swap V3 - 배경교체 스타일 프롬프트

핵심:
- 짧고 직접적인 명령
- 반복 강조
- 수학적 요구사항
- 문제 직접 해결 (조명/경계/피부톤/머리카락/그림자)
"""

# ============================================================
# 조명 분석 프롬프트 (최소화)
# ============================================================

LIGHTING_ANALYSIS_PROMPT_V3 = """Analyze lighting ONLY. Return JSON:

{
  "light_direction": "left | right | front | above | below-left | below-right",
  "light_quality": "soft | hard | mixed",
  "color_temp": "warm | neutral | cool",
  "shadow_side": "left | right | minimal"
}

JSON only. No explanation."""


# ============================================================
# V3 메인 프롬프트 - 배경교체 스타일
# ============================================================

FACE_SWAP_PROMPT_V3 = """FACE SWAP - SEAMLESS INTEGRATION

IMAGE 1: SOURCE (body, pose, outfit, background) - DO NOT CHANGE
IMAGE 2-3: NEW FACE - USE THIS IDENTITY

## CRITICAL: NATURAL LIGHTING INTEGRATION

The face MUST look like it was photographed in the same scene.

1. LIGHT DIRECTION on new face = {light_direction}
   - Highlights appear on {highlight_side}
   - Shadows fall on {shadow_side}

2. LIGHT QUALITY = {light_quality}
   - Skin shows {light_quality} lighting
   - Edge transitions are {light_quality}

3. COLOR TEMPERATURE = {color_temp}
   - Skin adapts to {color_temp} environment
   - DO NOT add warm/golden tone if source is cool
   - DO NOT add blue/cool tone if source is warm

## CRITICAL: SEAMLESS EDGE BLENDING

NO visible seams. NO halo. NO color bleeding.

1. FACE-TO-NECK: Skin tone transitions smoothly
2. FACE-TO-HAIR: Natural hairline, no harsh edge
3. FACE-TO-BACKGROUND: Clean silhouette

Check points:
- Jawline blends with neck
- Hairline looks natural
- Ears connect naturally
- No glow around face

## CRITICAL: SHADOW MATCHING

Face shadows MUST match body shadows.

- Shadow direction = {shadow_side}
- If body has left-side shadows, face has left-side shadows
- Shadow softness matches source image

## PRESERVATION (ABSOLUTE - NO EXCEPTIONS)

1. POSE: 100% IDENTICAL to SOURCE. DO NOT CHANGE.
2. OUTFIT: 100% IDENTICAL. Same colors, logos, details.
3. BACKGROUND: 100% IDENTICAL. Not one pixel changed.
4. BODY: Same proportions, same position.

## WHAT TO CHANGE (ONLY THESE)

1. FACE IDENTITY: From IMAGE 2-3
2. HAIR: Adapt to new face (style/color can change)
3. SKIN TONE: New face's tone, adapted to scene lighting

## OUTPUT QUALITY

- Photorealistic, not AI-generated look
- Natural skin texture (no plastic/smooth)
- Sharp focus on face
- No artifacts, no glitches
"""


def build_face_swap_prompt_v3(lighting: dict) -> str:
    """V3 프롬프트 빌드 - 조명 정보 삽입"""

    # 조명 방향 -> 하이라이트/그림자 위치 매핑
    direction_mapping = {
        "left": ("left side", "right side"),
        "right": ("right side", "left side"),
        "front": ("center", "both sides equally"),
        "above": ("top/forehead", "under chin/nose"),
        "below-left": ("lower left", "upper right"),
        "below-right": ("lower right", "upper left"),
    }

    light_dir = lighting.get("light_direction", "left")
    highlight_side, shadow_side = direction_mapping.get(
        light_dir, ("left side", "right side")
    )

    return FACE_SWAP_PROMPT_V3.format(
        light_direction=light_dir,
        highlight_side=highlight_side,
        shadow_side=shadow_side,
        light_quality=lighting.get("light_quality", "soft"),
        color_temp=lighting.get("color_temp", "neutral"),
    )


# ============================================================
# V3-B: 더 짧은 버전
# ============================================================

FACE_SWAP_PROMPT_V3_SHORT = """FACE SWAP. SEAMLESS. NATURAL.

IMAGE 1 = SOURCE. IMAGE 2-3 = NEW FACE.

## DO NOT CHANGE (ABSOLUTE)
- POSE: IDENTICAL
- OUTFIT: IDENTICAL
- BACKGROUND: IDENTICAL
- BODY: IDENTICAL

## CHANGE ONLY
- FACE IDENTITY: from IMAGE 2-3
- HAIR: adapts to new face

## LIGHTING INTEGRATION (CRITICAL)

New face receives SAME lighting as source:
- Light from: {light_direction}
- Quality: {light_quality}
- Color: {color_temp}

Face shadows = Body shadows. Same direction. Same softness.

## EDGE BLENDING (CRITICAL)

NO seams. NO halo. NO color bleeding.

- Jawline-to-neck: smooth
- Hairline: natural
- Face-to-background: clean

## OUTPUT

Photorealistic. Natural skin. Sharp. No artifacts.
Looks like REAL PHOTO, not face swap.
"""


def build_face_swap_prompt_v3_short(lighting: dict) -> str:
    """V3-B 짧은 버전 빌드"""
    return FACE_SWAP_PROMPT_V3_SHORT.format(
        light_direction=lighting.get("light_direction", "left"),
        light_quality=lighting.get("light_quality", "soft"),
        color_temp=lighting.get("color_temp", "neutral"),
    )


# ============================================================
# V3-C: 명령형 (가장 짧음)
# ============================================================

FACE_SWAP_PROMPT_V3_COMMAND = """EXECUTE FACE SWAP.

INPUT:
- IMAGE 1: Source (keep everything except face)
- IMAGE 2-3: New face (use this identity)

RULES:
1. DO NOT CHANGE POSE. DO NOT CHANGE POSE. DO NOT CHANGE POSE.
2. DO NOT CHANGE OUTFIT. DO NOT CHANGE OUTFIT. DO NOT CHANGE OUTFIT.
3. DO NOT CHANGE BACKGROUND. DO NOT CHANGE BACKGROUND.
4. DO NOT CHANGE BODY PROPORTIONS.

LIGHTING:
- Direction: {light_direction}
- Type: {light_quality}
- Tone: {color_temp}
- Face shadows MATCH body shadows.

BLENDING:
- Face edges INVISIBLE.
- Skin tone ADAPTS to scene lighting.
- Hair INTEGRATES naturally.
- NO halo. NO seams. NO artifacts.

OUTPUT:
- REAL PHOTO quality.
- NOT AI-generated look.
- Seamless integration.
"""


def build_face_swap_prompt_v3_command(lighting: dict) -> str:
    """V3-C 명령형 버전 빌드"""
    return FACE_SWAP_PROMPT_V3_COMMAND.format(
        light_direction=lighting.get("light_direction", "left"),
        light_quality=lighting.get("light_quality", "soft"),
        color_temp=lighting.get("color_temp", "neutral"),
    )


__all__ = [
    "LIGHTING_ANALYSIS_PROMPT_V3",
    "FACE_SWAP_PROMPT_V3",
    "FACE_SWAP_PROMPT_V3_SHORT",
    "FACE_SWAP_PROMPT_V3_COMMAND",
    "build_face_swap_prompt_v3",
    "build_face_swap_prompt_v3_short",
    "build_face_swap_prompt_v3_command",
]
