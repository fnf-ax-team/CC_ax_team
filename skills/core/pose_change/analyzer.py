"""
포즈 변경 VLM 분석 모듈

소스 이미지에서 포즈 변경 시 보존해야 할 요소를 추출하고
목표 포즈의 물리적 타당성을 검증한다.
"""

import json
import re
from io import BytesIO
from typing import Any, Union

from PIL import Image
from google.genai import types

from core.config import VISION_MODEL
from .templates import SOURCE_ANALYSIS_PROMPT


# =============================================================================
# 내부 헬퍼 함수
# =============================================================================


def _pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL 이미지를 Gemini API Part로 변환 (크기 제한 포함)."""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _load_image(image: Union[str, Image.Image]) -> Image.Image:
    """경로 또는 PIL Image를 PIL Image로 반환."""
    if isinstance(image, str):
        return Image.open(image)
    return image


def _parse_json_response(text: str) -> dict:
    """VLM 응답에서 JSON 추출 및 파싱."""
    # 마크다운 코드 블록 제거
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    elif "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON 객체 직접 추출 시도
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return json.loads(text[start_idx : end_idx + 1])
        raise


# =============================================================================
# 소스 이미지 분석
# =============================================================================


def analyze_source_for_pose_change(
    source_image: Union[Image.Image, str],
    client: Any,
) -> dict:
    """소스 이미지를 분석하여 포즈 변경 시 보존해야 할 요소를 추출한다.

    VLM(VISION_MODEL)에 소스 이미지와 SOURCE_ANALYSIS_PROMPT를 전달하여
    얼굴/착장/배경/체형 정보를 구조화된 JSON으로 반환한다.

    Args:
        source_image: 분석할 소스 이미지 (PIL Image 또는 파일 경로)
        client: Google GenAI client 인스턴스

    Returns:
        dict: VLM 분석 결과.
            - current_pose (dict): 현재 포즈 상세 정보
                - body_position, torso_angle, head_position
                - arm_left, arm_right, leg_left, leg_right
                - weight_distribution, overall_description
            - preserve_elements (dict): 보존 요소
                - face (dict): identity, expression, skin_tone, hair, facial_structure
                - outfit (dict): top, bottom 디테일 및 로고 정보
                - background (dict): setting, description, lighting, atmosphere
                - body_type (dict): height_proportion, build, leg_length
            - physical_constraints (dict): 물리적 환경 정보
                - ground_type, nearby_objects, space_available

    Raises:
        ValueError: VLM 응답이 유효한 JSON이 아닌 경우
        Exception: API 호출 실패 시
    """
    pil_image = _load_image(source_image)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=SOURCE_ANALYSIS_PROMPT),
                _pil_to_part(pil_image),
            ],
        )
    ]

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"],
        ),
    )

    text = response.candidates[0].content.parts[0].text
    result = _parse_json_response(text)

    # 필수 키 존재 여부 확인 후 기본값 보완
    if "preserve_elements" not in result:
        raise ValueError(
            f"VLM 응답에 'preserve_elements' 키가 없습니다. 응답: {text[:200]}"
        )

    return result


# =============================================================================
# 목표 포즈 타당성 검증
# =============================================================================

# 물리적으로 불가능하거나 위험한 포즈 키워드
_IMPOSSIBLE_POSE_KEYWORDS = [
    "floating",
    "levitating",
    "flying",
    "upside down",
    "head on ground",
    "neck broken",
    "spine twisted 180",
]

# 체형 제약과 충돌할 수 있는 포즈 키워드 (경고 수준)
_CONSTRAINT_SENSITIVE_KEYWORDS = [
    "split",
    "backbend",
    "extreme flex",
    "contortion",
    "handstand",
    "cartwheel",
]

_POSE_VALIDATION_PROMPT_TEMPLATE = """
You are a physics and anatomy expert reviewing a fashion photography pose request.

Body constraints of the model:
{body_constraints}

Requested pose:
{target_pose}

Assess if this pose is:
1. Physically possible for a human body
2. Achievable given the model's body constraints
3. Safe and natural for fashion photography

Respond in JSON only:
{{
  "is_valid": true,
  "reason": "brief explanation in Korean",
  "risk_level": "none"
}}

risk_level options: "none" / "low" / "medium" / "high"
If risk_level is "high" or the pose is physically impossible, set is_valid to false.
""".strip()


def validate_target_pose(
    target_pose: str,
    body_constraints: str,
    client: Any,
) -> tuple:
    """목표 포즈가 물리적으로 가능한지 검증한다.

    1단계: 키워드 기반 빠른 사전 검사 (명백히 불가능한 포즈 차단)
    2단계: VLM 기반 심층 검증 (체형 제약과의 호환성 판단)

    Args:
        target_pose: 목표 포즈 설명 (프리셋 설명 또는 커스텀 텍스트)
        body_constraints: 소스 분석에서 추출한 체형/물리 제약 문자열
        client: Google GenAI client 인스턴스

    Returns:
        tuple[bool, str]: (is_valid, reason)
            - is_valid: True면 포즈 사용 가능, False면 재검토 필요
            - reason: 한국어 판정 사유
    """
    pose_lower = target_pose.lower()

    # 1단계: 명백히 불가능한 포즈 키워드 검사
    for keyword in _IMPOSSIBLE_POSE_KEYWORDS:
        if keyword in pose_lower:
            return (
                False,
                f"물리적으로 불가능한 포즈입니다: '{keyword}' 감지. 다른 포즈를 선택해주세요.",
            )

    # 2단계: VLM 심층 검증
    prompt = _POSE_VALIDATION_PROMPT_TEMPLATE.format(
        body_constraints=body_constraints or "일반 성인 모델 체형",
        target_pose=target_pose,
    )

    try:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )
        ]

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_modalities=["TEXT"],
            ),
        )

        text = response.candidates[0].content.parts[0].text
        result = _parse_json_response(text)

        is_valid = bool(result.get("is_valid", True))
        reason = result.get("reason", "검증 완료")
        return (is_valid, reason)

    except Exception as e:
        # VLM 검증 실패 시 키워드 기반 경고만 확인하고 통과 허용
        has_warning = any(kw in pose_lower for kw in _CONSTRAINT_SENSITIVE_KEYWORDS)
        if has_warning:
            return (
                True,
                f"VLM 검증 불가 (에러: {e}). 포즈에 주의 필요한 키워드가 포함되어 있습니다: {target_pose}",
            )
        return (True, f"VLM 검증 불가 (에러: {e}). 키워드 검사 통과.")
