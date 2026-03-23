"""
배경 교체 프롬프트 빌더 - 프롬프트 조립 및 참조 이미지 처리
"""

from typing import Dict, Any, Optional

from .templates import (
    BASE_PRESERVATION_PROMPT,
    STRUCTURE_STYLE_TRANSFORM,
    ONE_UNIT_PROMPTS,
    REFERENCE_PROMPTS,
)
from .presets import get_style_preset


def build_background_prompt(
    background_style: str,
    physics_analysis: Dict[str, Any] = None,
    swap_analysis: Dict[str, Any] = None,
    background_analysis: str = None,
    preservation_level: str = "BASIC",
) -> str:
    """
    최종 배경 교체 프롬프트 조립.

    조립 순서 (위에서 아래로 누적):
    1. [기본] BASE_PRESERVATION_PROMPT - 인물 보존
    2. [기본] STRUCTURE_STYLE_TRANSFORM - 구조물 위치 고정, 스타일만 변경
    3. [감지시] ONE UNIT 보존
    4. [감지시] VFX 물리 가이드라인
    5. [감지시] 배경 분석 결과
    6. [감지시] 차량/바닥/색보정 지시문
    7. [기본] 사용자 입력 배경 스타일

    Args:
        background_style: 배경 스타일 설명 또는 프리셋 키
        physics_analysis: analyze_model_physics() 결과
        swap_analysis: analyze_for_background_swap() 결과
        background_analysis: analyze_background() 결과 (텍스트)
        preservation_level: ONE UNIT 보존 레벨 (BASIC/DETAILED/FULL)

    Returns:
        조립된 프롬프트 텍스트
    """
    parts = []

    # 1. 기본 보존 프롬프트
    parts.append(BASE_PRESERVATION_PROMPT)

    # 2. 구조물 스타일 변환 프롬프트 (위치/원근 고정, 스타일만 변경)
    parts.append(STRUCTURE_STYLE_TRANSFORM)

    # 3. ONE UNIT 보존 (차량/오브젝트 감지 시)
    if swap_analysis and swap_analysis.get("has_vehicle"):
        # 차량 감지 시 자동으로 DETAILED 이상 적용
        level = (
            preservation_level
            if preservation_level in ["DETAILED", "FULL"]
            else "DETAILED"
        )
        parts.append(ONE_UNIT_PROMPTS.get(level, ONE_UNIT_PROMPTS["DETAILED"]))
    elif preservation_level != "BASIC":
        parts.append(
            ONE_UNIT_PROMPTS.get(preservation_level, ONE_UNIT_PROMPTS["BASIC"])
        )

    # 4. VFX 물리 가이드라인 (지지대 필요 시)
    if physics_analysis and physics_analysis.get("status") == "success":
        guideline = physics_analysis.get("generated_guideline", "")
        if guideline:
            parts.append(f"\n=== VFX PHYSICAL CONSTRAINTS ===\n{guideline}")

        # 설치 논리 - 금지 컨텍스트
        data = physics_analysis.get("data", {})
        logic = data.get("installation_logic", {})
        if logic.get("forbidden_contexts"):
            forbidden = logic["forbidden_contexts"]
            if isinstance(forbidden, list):
                parts.append(f"AVOID these contexts: {', '.join(forbidden)}")
            else:
                parts.append(f"AVOID: {forbidden}")

    # 5. 배경 분석 결과 (VLM)
    if background_analysis and not background_analysis.startswith("Error"):
        parts.append(f"\n=== REFERENCE BACKGROUND ANALYSIS ===\n{background_analysis}")

    # 6. 차량/바닥/색보정 지시문
    if swap_analysis:
        swap_instructions = build_swap_analysis_instructions(swap_analysis)
        if swap_instructions:
            parts.append(swap_instructions)

    # 7. 사용자 입력 배경 스타일
    # 프리셋 키인지 확인
    preset_style = get_style_preset(background_style)
    style_desc = preset_style if preset_style else background_style

    parts.append(f"\n=== TARGET BACKGROUND ===\n{style_desc}")

    return "\n\n".join(parts)


def build_reference_prompt(base_prompt: str, reference_type: str = "style") -> str:
    """
    참조 이미지용 프롬프트 생성.

    ============================================================
    SKILL.md 라인 225-228 기반 구현
    ============================================================

    Args:
        base_prompt: 기본 프롬프트
        reference_type: 참조 유형
            - "style": 조명/색상/분위기 스타일
            - "pose": 포즈/프레이밍/카메라 앵글
            - "background": 배경 환경/깊이/조명
            - "clothing": 착장 보존 (가장 상세)
            - "all": 전체 요소 참조

    Returns:
        REFERENCE_PROMPTS[reference_type] + "\\n\\nNow generate:\\n" + base_prompt

    Example:
        >>> build_reference_prompt("Model in urban setting", "style")
        "Based on the reference image, generate with:
        - Similar lighting style and quality
        - Same color palette and tonal range
        - Matching mood and atmosphere

        Now generate:
        Model in urban setting"
    """
    instruction = REFERENCE_PROMPTS.get(reference_type, REFERENCE_PROMPTS["style"])
    return f"{instruction}\n\nNow generate:\n{base_prompt}"


def build_one_unit_instructions(
    swap_analysis: Dict[str, Any], level: str = "BASIC"
) -> str:
    """
    ONE UNIT 보존 지시문 생성.

    Args:
        swap_analysis: analyze_for_background_swap() 결과
        level: 보존 레벨 (BASIC/DETAILED/FULL)

    Returns:
        ONE UNIT 보존 지시문
    """
    base = ONE_UNIT_PROMPTS.get(level, ONE_UNIT_PROMPTS["BASIC"])

    # 차량 정보 추가
    if swap_analysis and swap_analysis.get("has_vehicle"):
        vehicle_desc = swap_analysis.get("vehicle_description", "vehicle")
        vehicle_note = f"\n\nVEHICLE DETECTED: {vehicle_desc}\nThis vehicle is part of the FOREGROUND SUBJECT."
        return base + vehicle_note

    return base


def build_vehicle_instructions(swap_analysis: Dict[str, Any]) -> str:
    """
    차량 보존 지시문 생성.

    Args:
        swap_analysis: analyze_for_background_swap() 결과

    Returns:
        차량 보존 지시문 (차량 없으면 빈 문자열)
    """
    if not swap_analysis or not swap_analysis.get("has_vehicle"):
        return ""

    vehicle_desc = swap_analysis.get("vehicle_description", "vehicle")

    return f"""=== CRITICAL: VEHICLE PRESERVATION ===
THERE IS A VEHICLE IN THIS IMAGE: {vehicle_desc}
YOU MUST KEEP THIS VEHICLE EXACTLY AS IT IS.
DO NOT REMOVE, HIDE, OR MODIFY THE VEHICLE IN ANY WAY.
The vehicle is part of the original composition and MUST remain visible."""


def build_ground_instructions(swap_analysis: Dict[str, Any]) -> str:
    """
    바닥 연속성 지시문 생성.

    Args:
        swap_analysis: analyze_for_background_swap() 결과

    Returns:
        바닥 연속성 지시문
    """
    if not swap_analysis:
        return ""

    ground = swap_analysis.get("ground", {})
    if not ground:
        return ""

    material = ground.get("material", "concrete")
    color = ground.get("color", "gray")
    tone = ground.get("tone", "neutral")

    return f"""=== GROUND CONTINUITY ===
- Ground material: {material}
- Ground color: {color} ({tone} tone)
- The ground MUST continue seamlessly from foreground to background"""


def build_color_matching_instructions(swap_analysis: Dict[str, Any]) -> str:
    """
    색보정 매칭 지시문 생성.

    Args:
        swap_analysis: analyze_for_background_swap() 결과

    Returns:
        색보정 매칭 지시문
    """
    if not swap_analysis:
        return ""

    color = swap_analysis.get("color_grading", {})
    if not color:
        return ""

    warmth = color.get("overall_warmth", "neutral")
    saturation = color.get("saturation", "medium")

    return f"""=== COLOR MATCHING (MOST IMPORTANT) ===
The background MUST match the original image's color grading:
- Overall warmth: {warmth}
- Saturation: {saturation}

Apply the SAME color grading to the background as the person has.
The entire image must look like ONE photo, not a composite."""


def build_swap_analysis_instructions(swap_analysis: Dict[str, Any]) -> str:
    """
    배경교체 분석 결과를 종합 지시문으로 변환.

    Args:
        swap_analysis: analyze_for_background_swap() 결과

    Returns:
        종합 지시문 텍스트
    """
    parts = []

    # 차량 보존
    vehicle_instr = build_vehicle_instructions(swap_analysis)
    if vehicle_instr:
        parts.append(vehicle_instr)

    # 바닥 연속성
    ground_instr = build_ground_instructions(swap_analysis)
    if ground_instr:
        parts.append(ground_instr)

    # 색보정 매칭
    color_instr = build_color_matching_instructions(swap_analysis)
    if color_instr:
        parts.append(color_instr)

    # 조명 매칭
    lighting = swap_analysis.get("lighting", {})
    if lighting:
        parts.append(f"""=== LIGHTING MATCH ===
- Direction: {lighting.get('direction', 'front')}
- Intensity: {lighting.get('intensity', 'soft')}
- Color temperature: {lighting.get('color_temp', 'neutral')}""")

    if not parts:
        return ""

    return "\n\n".join(parts)


__all__ = [
    "build_background_prompt",
    "build_reference_prompt",
    "build_one_unit_instructions",
    "build_vehicle_instructions",
    "build_ground_instructions",
    "build_color_matching_instructions",
    "build_swap_analysis_instructions",
]
