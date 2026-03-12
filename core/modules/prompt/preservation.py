"""
보존 프롬프트 모듈 (배경 교체 워크플로용)

배경 교체 시 인물/소품/구조물 보존을 위한 프롬프트를 생성한다.

3단계 보존 레벨:
- BASIC: 인물 크기/위치 고정, 배경만 교체
- DETAILED: 인물+차량을 ONE UNIT으로 묶어 보존
- FULL: 전경 모든 요소를 절대 보존 (인물+차량+소품+그림자)

원본:
- core.background_swap.templates : BASE_PRESERVATION_PROMPT, ONE_UNIT_PROMPTS, STRUCTURE_STYLE_TRANSFORM
"""

from enum import Enum
from typing import Optional


# ============================================================
# 보존 레벨 열거형
# ============================================================


class PreservationLevel(Enum):
    """인물/전경 보존 강도 레벨"""

    BASIC = "BASIC"
    DETAILED = "DETAILED"
    FULL = "FULL"


# ============================================================
# 기본 보존 프롬프트 (프레이밍 고정)
# 원본: background_swap/templates.py BASE_PRESERVATION_PROMPT
# ============================================================

BASE_PRESERVATION_PROMPT = """EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1
DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

## MATHEMATICAL REQUIREMENTS
- Person height / Frame height = 0.97
- Scale factor = 1.0
- Person center = Frame center (same position)

## MODEL PRESERVATION (ABSOLUTE - NO EXCEPTIONS)

1. PERSON SIZE: 100% IDENTICAL to input. NO shrinking/scaling.
2. PERSON POSITION: Same location in frame as input.
3. PERSON DETAILS: Face, body, clothing, hair, accessories - EXACT COPY."""


# ============================================================
# ONE UNIT 보존 프롬프트 (3단계 레벨)
# 원본: background_swap/templates.py ONE_UNIT_PROMPTS
# ============================================================

ONE_UNIT_PROMPTS = {
    PreservationLevel.BASIC: """FRAMING: Model fills 90% of the frame height. KEEP THIS.
DO NOT make the model smaller. DO NOT zoom out.

The BLACK CAR (if exists) is a PROP, not background.

COPY EXACTLY FROM INPUT:
- Model size in frame (CRITICAL - must be same %)
- Model face, pose, clothes, hair
- Any vehicle/object near model (color, shape, position)

REPLACE: Background only""",
    PreservationLevel.DETAILED: """=== FOREGROUND SUBJECT PRESERVATION (CRITICAL) ===

SUBJECT = Person + Vehicle as ONE CONNECTED UNIT
Treat them as a SINGLE subject, NOT separate objects.

DO NOT MODIFY THE SUBJECT:
- Person: exact face, body, clothes, pose, hair
- Vehicle: exact color, model, wheels, reflections, position
- Their spatial relationship: distance, angle, contact points
- Combined shadows on ground

The person and vehicle are ONE COMPOSITION.
Moving, resizing, or modifying either one breaks the composition.

ONLY REPLACE: Background environment behind this unit""",
    PreservationLevel.FULL: """=== FOREGROUND SUBJECT = ONE UNIT (DO NOT SEPARATE) ===

Everything in foreground (person + vehicle + objects) = SINGLE SUBJECT
This is NOT "person" + "car". This is ONE connected unit.

ABSOLUTE PRESERVATION:
- Person: 100% identical (face, body, clothing, pose, expression)
- Vehicle (if exists): 100% identical (color, shape, wheels, reflections)
- Objects (if exist): 100% identical
- All contact points and spatial relationships: LOCKED
- All shadows: preserve direction and shape

NEVER:
- Separate person from vehicle
- Move person relative to vehicle
- Change vehicle color/shape/size
- Add new people, cars, or objects

ONLY CHANGE: Background behind the foreground subject""",
}


# ============================================================
# 구조물 스타일 변환 프롬프트
# 원본: background_swap/templates.py STRUCTURE_STYLE_TRANSFORM
# ============================================================

STRUCTURE_STYLE_TRANSFORM = """
*** CRITICAL: STRUCTURE STYLE TRANSFORM (NOT REGENERATION) ***

This is NOT background replacement. This is STYLE TRANSFORMATION.

## ABSOLUTE RULE: KEEP ALL STRUCTURE POSITIONS

Every structure in the original image (railings, buildings, walls, floors, stairs, etc.)
MUST remain in the EXACT SAME POSITION, SIZE, and PERSPECTIVE.

What to KEEP (DO NOT CHANGE):
- Structure positions (x, y coordinates)
- Structure sizes and proportions
- Perspective angles and vanishing points
- Depth relationships (what's in front/behind)
- Camera angle and horizon line

What to CHANGE (ONLY THESE):
- Textures and materials (e.g., wooden railing -> metal railing)
- Colors and finishes (e.g., brown wood -> silver metal)
- Style/aesthetic (e.g., rural -> urban modern)
- Lighting color temperature (to match new style)
- Sky/atmosphere (if visible)

## THINK OF IT AS:
"Reskinning" the existing scene, NOT rebuilding it.
Like applying a texture pack to a 3D model - geometry stays, appearance changes.
"""


# ============================================================
# 메인 함수
# ============================================================


def build_preservation_prompt(
    level: PreservationLevel = PreservationLevel.BASIC,
    physics_analysis: Optional[dict] = None,
    swap_analysis: Optional[dict] = None,
    include_base: bool = True,
    include_structure_transform: bool = False,
) -> str:
    """
    보존 프롬프트를 레벨에 따라 조립.

    Args:
        level: 보존 강도 (BASIC/DETAILED/FULL)
        physics_analysis: VFX 물리 분석 결과 dict (선택)
            - geometry.perspective, lighting.direction_clock 등
        swap_analysis: 스왑 분석 결과 dict (선택)
            - vehicle_detected, ground_type 등
        include_base: 기본 보존 프롬프트(BASE_PRESERVATION_PROMPT) 포함 여부
        include_structure_transform: 구조물 스타일 변환 프롬프트 포함 여부

    Returns:
        조립된 보존 프롬프트 텍스트
    """
    sections = []

    # 기본 보존 프롬프트
    if include_base:
        sections.append(BASE_PRESERVATION_PROMPT)

    # ONE UNIT 보존 프롬프트 (레벨별)
    one_unit = ONE_UNIT_PROMPTS.get(level, ONE_UNIT_PROMPTS[PreservationLevel.BASIC])
    sections.append(one_unit)

    # 물리 분석 기반 추가 지시
    if physics_analysis:
        physics_section = _build_physics_section(physics_analysis)
        if physics_section:
            sections.append(physics_section)

    # 스왑 분석 기반 추가 지시
    if swap_analysis:
        swap_section = build_swap_instructions(swap_analysis)
        if swap_section:
            sections.append(swap_section)

    # 구조물 스타일 변환 (배경 구조물 유지 모드)
    if include_structure_transform:
        sections.append(STRUCTURE_STYLE_TRANSFORM)

    return "\n\n".join(sections)


def _build_physics_section(physics_analysis: dict) -> str:
    """VFX 물리 분석 결과를 프롬프트 보조 텍스트로 변환.

    Args:
        physics_analysis: VFX 분석 JSON (geometry, lighting, pose_dependency 등)

    Returns:
        물리 조건 프롬프트 텍스트
    """
    lines = ["## PHYSICS CONSTRAINTS (from VFX analysis)"]

    # 카메라 지오메트리
    geometry = physics_analysis.get("geometry", {})
    if geometry:
        perspective = geometry.get("perspective", "")
        horizon = geometry.get("horizon_y", "")
        if perspective:
            lines.append(f"- Camera perspective: {perspective}")
        if horizon:
            lines.append(f"- Horizon line at y={horizon}")

    # 조명
    lighting = physics_analysis.get("lighting", {})
    if lighting:
        direction = lighting.get("direction_clock", "")
        color_temp = lighting.get("color_temp", "")
        if direction:
            lines.append(f"- Light direction: {direction} o'clock")
        if color_temp:
            lines.append(f"- Color temperature: {color_temp}")

    # 포즈 의존성
    pose_dep = physics_analysis.get("pose_dependency", {})
    if pose_dep:
        support_required = pose_dep.get("support_required", False)
        if support_required:
            support_type = pose_dep.get("support_type", "surface")
            support_dir = pose_dep.get("support_direction", "")
            lines.append(
                f"- CRITICAL: Model needs {support_type} support "
                f"({support_dir}) - background MUST include this"
            )

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def build_swap_instructions(swap_analysis: dict) -> str:
    """스왑 분석 결과를 배경 교체 지시 프롬프트로 변환.

    Args:
        swap_analysis: 스왑 분석 결과 dict
            - vehicle_detected (bool): 차량 감지 여부
            - vehicle_color (str): 차량 색상
            - ground_type (str): 바닥 타입
            - color_temperature (str): 색온도 유지 요구
            - lighting_direction (str): 광원 방향 유지 요구

    Returns:
        스왑 지시 프롬프트 텍스트
    """
    lines = ["## SWAP MATCHING REQUIREMENTS"]

    # 차량 보존
    vehicle = swap_analysis.get("vehicle_detected", False)
    if vehicle:
        color = swap_analysis.get("vehicle_color", "")
        lines.append(f"- Vehicle: KEEP as-is ({color}). Part of foreground unit.")

    # 바닥 매칭
    ground = swap_analysis.get("ground_type", "")
    if ground:
        lines.append(f"- Ground type to match: {ground}")

    # 색온도 유지
    color_temp = swap_analysis.get("color_temperature", "")
    if color_temp:
        lines.append(f"- Color temperature: MUST maintain {color_temp}")

    # 광원 방향 유지
    lighting = swap_analysis.get("lighting_direction", "")
    if lighting:
        lines.append(f"- Lighting direction: MUST match {lighting}")

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


__all__ = [
    "PreservationLevel",
    "BASE_PRESERVATION_PROMPT",
    "ONE_UNIT_PROMPTS",
    "STRUCTURE_STYLE_TRANSFORM",
    "build_preservation_prompt",
    "build_swap_instructions",
]
