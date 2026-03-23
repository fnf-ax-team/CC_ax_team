"""
배경 교체 분석 모듈 - VFX 물리 분석 및 소스 타입 감지

기존 core/background_analyzer.py 함수를 import/re-export하고,
VFX 물리 분석 및 소스 타입 감지 함수를 추가한다.
"""

import json
from PIL import Image
from typing import Dict, Any

from google import genai
from google.genai import types

from core.config import VISION_MODEL
from core.utils import pil_to_part

# ============================================================
# 기존 함수 IMPORT 및 RE-EXPORT (복사 아님!)
# ============================================================
from core.background_analyzer import (
    analyze_background,  # 배경 이미지 -> 텍스트 설명
    analyze_for_background_swap,  # 차량/바닥/색보정 분석
    build_swap_instructions,  # 분석 -> 프롬프트 지시문
)

from .templates import VFX_ANALYSIS_PROMPT, SOURCE_TYPE_PROMPT


# ============================================================
# 신규 함수 (이 파일에서 구현)
# ============================================================


def analyze_model_physics(
    image_pil: Image.Image, api_key: str, additional_context: str = ""
) -> Dict[str, Any]:
    """
    VFX 슈퍼바이저 관점의 물리 분석 (6대 영역).

    Args:
        image_pil: PIL Image 객체 (원본 인물 사진)
        api_key: Gemini API 키
        additional_context: 추가 컨텍스트 (선택)

    Returns:
        {
            "status": "success" | "error",
            "data": {
                "geometry": {...},
                "lighting": {...},
                "pose_dependency": {...},
                "installation_logic": {...},
                "physics_anchors": {...},
                "semantic_style": {...}
            },
            "generated_guideline": str
        }
    """
    try:
        client = genai.Client(api_key=api_key)

        # 1024px 다운샘플링 (공간 분석이므로 높은 해상도)
        image_part = pil_to_part(image_pil, max_size=1024)

        system_instruction = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한 물리적 제약 조건을 수치화된 데이터로 추출해야 합니다."""

        prompt = VFX_ANALYSIS_PROMPT
        if additional_context:
            prompt += f"\n\n추가 컨텍스트:\n{additional_context}"

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Content(role="user", parts=[types.Part(text=prompt), image_part])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                max_output_tokens=1200,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        guideline = build_background_guideline(result)

        return {"status": "success", "data": result, "generated_guideline": guideline}

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)[:200],
            "data": {},
            "generated_guideline": "",
        }


def build_background_guideline(analysis_data: Dict[str, Any]) -> str:
    """
    추출된 VFX 분석 결과를 배경 생성 프롬프트 가이드라인으로 조립.

    ★★★ 핵심 원칙: 원본의 구조물을 컨셉에 맞게 변형 (제거 금지) ★★★

    Args:
        analysis_data: analyze_model_physics()의 data 필드

    Returns:
        프롬프트에 추가할 가이드라인 텍스트
    """
    geom = analysis_data.get("geometry", {})
    light = analysis_data.get("lighting", {})
    pose = analysis_data.get("pose_dependency", {})
    logic = analysis_data.get("installation_logic", {})
    style = analysis_data.get("semantic_style", {})

    parts = []

    # ============================================================
    # 1. CAMERA ANGLE (가장 중요!) - 원근감 고정
    # ============================================================
    if geom:
        perspective = geom.get("perspective", "eye-level")
        horizon_y = geom.get("horizon_y", 0.5)

        # 카메라 앵글별 구체적 지시
        if perspective == "low-angle":
            parts.append(
                f"""★★★ CAMERA ANGLE: LOW-ANGLE (CRITICAL) ★★★
- Camera is positioned LOW, looking UP at the subject
- Horizon line is in the LOWER part of frame (y={horizon_y})
- Floor/ground should be BARELY VISIBLE or NOT visible
- Buildings/structures should appear to TOWER UPWARD
- Vanishing point should be ABOVE the subject
- DO NOT show flat ground stretching into distance"""
            )
        elif perspective == "high-angle":
            parts.append(
                f"""★★★ CAMERA ANGLE: HIGH-ANGLE (CRITICAL) ★★★
- Camera is positioned HIGH, looking DOWN at the subject
- Horizon line is in the UPPER part of frame (y={horizon_y})
- Ground/floor should be PROMINENTLY visible
- Subject should appear smaller, looking down at them
- Vanishing point should be BELOW the subject"""
            )
        else:  # eye-level
            parts.append(
                f"""CAMERA ANGLE: EYE-LEVEL
- Camera at subject's eye height
- Horizon at middle of frame (y={horizon_y})
- Natural perspective with moderate ground visibility"""
            )

        if geom.get("focal_length_vibe"):
            parts.append(f"Focal length vibe: {geom['focal_length_vibe']}")

    # ============================================================
    # 2. SUPPORT STRUCTURE (구조물 변형, 제거 금지!)
    # ============================================================
    if pose and pose.get("support_required"):
        pose_type = pose.get("pose_type", "standing")
        support_type = pose.get("support_type", "structure")
        support_direction = pose.get("support_direction", "behind")

        # 포즈별 구체적 지시
        if pose_type == "leaning":
            parts.append(
                f"""★★★ SUPPORT STRUCTURE: LEANING POSE (CRITICAL - DO NOT REMOVE) ★★★
The person is LEANING on something. You MUST:
1. KEEP a {support_type} at the SAME position ({support_direction} the subject)
2. TRANSFORM the {support_type} to match the new background style
   - Original: {support_type}
   - Transform to: matching style {support_type} (e.g., modern metal railing, concrete barrier, urban fence)
3. NEVER remove the support structure - the pose requires it
4. The person's body angle and contact points must align with the structure"""
            )
        elif pose_type == "sitting":
            parts.append(
                f"""★★★ SUPPORT STRUCTURE: SITTING POSE (CRITICAL - DO NOT REMOVE) ★★★
The person is SITTING. You MUST:
1. KEEP a {support_type} at the SAME position (below/behind the subject)
2. TRANSFORM the {support_type} to match the new background style
   - Original: {support_type}
   - Transform to: matching style seating (e.g., urban bench, ledge, steps)
3. NEVER leave the person floating - they need something to sit on
4. The sitting surface must be at the correct height and angle"""
            )
        else:
            parts.append(
                f"""SUPPORT STRUCTURE REQUIRED:
- Type: {support_type}
- Direction: {support_direction}
- Transform to match new background style while keeping position"""
            )

    # ============================================================
    # 3. LIGHTING (조명 방향 고정)
    # ============================================================
    if light:
        parts.append(
            f"""LIGHTING MATCH:
- Light source from {light.get('direction_clock', '12')} o'clock direction
- Elevation: {light.get('elevation', 'mid')}
- Softness: {light.get('softness', 0.5)}
- Color temperature: {light.get('color_temp', 'neutral')}
- Background lighting must match subject lighting direction"""
        )

    # ============================================================
    # 4. FORBIDDEN CONTEXTS (금지 컨텍스트)
    # ============================================================
    if logic:
        if logic.get("forbidden_contexts"):
            forbidden = logic["forbidden_contexts"]
            if isinstance(forbidden, list):
                parts.append(
                    f"AVOID these contexts (physically impossible): {', '.join(forbidden)}"
                )
            else:
                parts.append(f"AVOID: {forbidden}")

    # ============================================================
    # 5. STYLE VIBE
    # ============================================================
    if style and style.get("vibe"):
        parts.append(f"Overall style vibe: {style['vibe']}")

    if not parts:
        return "Create a professional background that matches the subject's pose, camera angle, and lighting."

    return "\n\n".join(parts)


def detect_source_type(image_pil: Image.Image, api_key: str) -> str:
    """
    스튜디오/야외 자동 감지 (StudioRelight 라우팅용).

    ============================================================
    CRITICAL: 이 함수는 VFX analysis와 완전히 독립적인 별도 VLM 호출!
    ============================================================

    - VFX analysis JSON 스키마에는 background_type 필드가 없음
    - 따라서 이 함수는 독립적인 간단한 VLM 호출로 배경 유형만 판별
    - 목적: StudioRelightValidator 라우팅 결정

    API 호출 상세:
    - Model: gemini-3-flash-preview (VLM 분석용)
    - Resolution: 512px 다운샘플링 (빠른 분류용)
    - Temperature: 0.1 (일관된 분류)
    - Prompt: SOURCE_TYPE_PROMPT

    Args:
        image_pil: PIL Image 객체
        api_key: Gemini API 키

    Returns:
        "outdoor" | "white_studio" | "colored_studio" | "indoor"
    """
    try:
        client = genai.Client(api_key=api_key)

        # 512px 다운샘플링 (분류용이므로 저해상도)
        image_part = pil_to_part(image_pil, max_size=512)

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Content(
                    role="user", parts=[types.Part(text=SOURCE_TYPE_PROMPT), image_part]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=20,  # 단일 단어만 반환
            ),
        )

        # None 체크
        if response is None or response.text is None:
            return "outdoor"

        result = response.text.strip().lower()

        # 유효한 값인지 확인
        valid_types = ["outdoor", "white_studio", "colored_studio", "indoor"]
        if result not in valid_types:
            # 부분 매칭 시도
            for vt in valid_types:
                if vt in result:
                    return vt
            # 기본값: outdoor (안전한 선택)
            return "outdoor"

        return result

    except Exception as e:
        # 에러 시 기본값
        print(f"[detect_source_type] Error: {e}")
        return "outdoor"


__all__ = [
    # Re-exported from core.background_analyzer
    "analyze_background",
    "analyze_for_background_swap",
    "build_swap_instructions",
    # New functions defined in this file
    "analyze_model_physics",
    "build_background_guideline",
    "detect_source_type",
]
