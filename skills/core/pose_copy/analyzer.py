"""
pose_copy VLM 분석 모듈

핵심 원칙:
- 레퍼런스 이미지 → API에 직접 전달 (포즈/구도/배경 추출)
- 소스 이미지 → VLM 텍스트 분석만 (얼굴/착장만, 포즈 혼동 방지)
"""

import json
import re
from typing import Any, Union, Optional

from PIL import Image

from core.config import VISION_MODEL
from .templates import REFERENCE_POSE_ANALYSIS_PROMPT, SOURCE_PERSON_ANALYSIS_PROMPT


# ============================================================================
# JSON 파싱 유틸리티
# ============================================================================


def _parse_json_response(
    response_text: str, module_name: str = "PoseCopyAnalyzer"
) -> dict:
    """VLM 응답에서 JSON 추출 (마크다운 코드 블록 처리)"""
    # 마크다운 코드 블록에서 JSON 추출
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # JSON 파싱 시도
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[{module_name}] JSON 파싱 에러: {e}")

    # JSON 객체 직접 추출 시도
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}")

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        try:
            return json.loads(response_text[start_idx : end_idx + 1])
        except json.JSONDecodeError:
            pass

    return {}


def _load_image(
    image: Union[str, Image.Image], module_name: str = "PoseCopyAnalyzer"
) -> Optional[Image.Image]:
    """이미지 로드 (경로 또는 PIL Image)"""
    if isinstance(image, str):
        try:
            return Image.open(image)
        except Exception as e:
            print(f"[{module_name}] 이미지 로드 실패 {image}: {e}")
            return None
    return image


# ============================================================================
# 레퍼런스 포즈 분석 폴백
# ============================================================================


def _get_fallback_reference_analysis() -> dict:
    """레퍼런스 분석 실패 시 기본값"""
    return {
        # flat 문자열 필드 (prompt_builder에서 직접 사용)
        "pose_description": "standing, relaxed posture, weight centered",
        "camera_angle": "eye-level",
        "framing": "full body",
        "composition": "framing: full body, camera: eye-level, distance: medium shot",
        "background": "neutral studio background, soft lighting",
        "expression": "neutral, confident, gaze: direct eye contact, mood: relaxed",
        # 원본 중첩 구조 (배경 옵션 처리용, _raw 접미사로 충돌 방지)
        "pose": {
            "body_position": "standing, weight centered",
            "torso_angle": "frontal",
            "head_position": "straight, neutral",
            "arm_left": "relaxed, hanging naturally",
            "arm_right": "relaxed, hanging naturally",
            "leg_left": "straight, weight-bearing",
            "leg_right": "slightly relaxed",
            "overall_vibe": "natural, confident",
        },
        "composition_raw": {
            "person_position": {"x": 0.5, "y": 0.6},
            "person_size_ratio": 0.7,
            "framing": "full body, centered",
            "camera_angle": "eye-level",
            "distance": "medium shot",
        },
        "background_raw": {
            "setting": "neutral studio",
            "color_tone": "neutral, cool",
            "depth": "shallow",
            "lighting": "soft, even, natural",
        },
        "expression_raw": {
            "face": "neutral, confident",
            "gaze_direction": "camera, direct eye contact",
            "mood": "relaxed, self-assured",
        },
    }


# ============================================================================
# 소스 인물 분석 폴백
# ============================================================================


def _get_fallback_source_analysis() -> dict:
    """소스 인물 분석 실패 시 기본값"""
    return {
        "face_description": "East Asian female, mid-20s, fair skin, oval face, almond eyes",
        "outfit_description": "casual streetwear outfit",
        "hair_description": "long dark hair, straight",
        "body_type": "slim, average height",
        # 원본 구조도 보존
        "face": {
            "age": "mid-20s",
            "gender": "female",
            "ethnicity": "East Asian",
            "skin_tone": "fair, cool undertone",
            "face_shape": "oval",
            "distinctive_features": "almond eyes, natural expression",
        },
        "outfit": {
            "description": "casual outfit",
            "colors": [],
            "style": "casual",
            "details": [],
            "fit": "regular",
        },
        "hair": {
            "length": "long",
            "color": "dark brown",
            "style": "straight, natural",
        },
    }


# ============================================================================
# 분석 결과 플래튼 (중첩 dict → 단순 문자열 필드)
# ============================================================================


def _flatten_reference_analysis(raw: dict) -> dict:
    """VLM 응답 중첩 dict를 prompt_builder가 쓸 수 있는 flat dict로 변환"""
    pose = raw.get("pose", {})
    composition = raw.get("composition", {})
    background = raw.get("background", {})
    expression = raw.get("expression", {})

    # 포즈 설명 조합
    pose_parts = []
    if pose.get("body_position"):
        pose_parts.append(pose["body_position"])
    if pose.get("torso_angle"):
        pose_parts.append(f"torso: {pose['torso_angle']}")
    if pose.get("head_position"):
        pose_parts.append(f"head: {pose['head_position']}")
    if pose.get("arm_left"):
        pose_parts.append(f"left arm: {pose['arm_left']}")
    if pose.get("arm_right"):
        pose_parts.append(f"right arm: {pose['arm_right']}")
    if pose.get("leg_left"):
        pose_parts.append(f"left leg: {pose['leg_left']}")
    if pose.get("leg_right"):
        pose_parts.append(f"right leg: {pose['leg_right']}")
    if pose.get("overall_vibe"):
        pose_parts.append(f"vibe: {pose['overall_vibe']}")

    # 구도 설명 조합
    comp_parts = []
    if composition.get("framing"):
        comp_parts.append(f"framing: {composition['framing']}")
    if composition.get("camera_angle"):
        comp_parts.append(f"camera: {composition['camera_angle']}")
    if composition.get("distance"):
        comp_parts.append(f"distance: {composition['distance']}")
    pos = composition.get("person_position", {})
    if pos:
        comp_parts.append(
            f"person position: x={pos.get('x', 0.5):.1f} y={pos.get('y', 0.6):.1f}"
        )
    if composition.get("person_size_ratio"):
        comp_parts.append(
            f"size ratio: {composition['person_size_ratio']:.0%} of frame"
        )

    # 배경 설명 조합
    bg_parts = []
    if background.get("setting"):
        bg_parts.append(background["setting"])
    if background.get("color_tone"):
        bg_parts.append(f"tone: {background['color_tone']}")
    if background.get("lighting"):
        bg_parts.append(f"lighting: {background['lighting']}")

    # 표정 설명 조합
    expr_parts = []
    if expression.get("face"):
        expr_parts.append(expression["face"])
    if expression.get("gaze_direction"):
        expr_parts.append(f"gaze: {expression['gaze_direction']}")
    if expression.get("mood"):
        expr_parts.append(f"mood: {expression['mood']}")

    return {
        # flat 문자열 필드
        "pose_description": ", ".join(pose_parts)
        if pose_parts
        else "natural standing pose",
        "camera_angle": composition.get("camera_angle", "eye-level"),
        "framing": composition.get("framing", "full body"),
        "composition": ", ".join(comp_parts) if comp_parts else "centered composition",
        "background": ", ".join(bg_parts) if bg_parts else "neutral background",
        "expression": ", ".join(expr_parts) if expr_parts else "neutral expression",
        # 원본 중첩 구조도 유지 (배경 옵션 처리용)
        "pose": pose,
        "composition_raw": composition,
        "background_raw": background,
        "expression_raw": expression,
    }


def _flatten_source_analysis(raw: dict) -> dict:
    """VLM 응답 중첩 dict를 prompt_builder가 쓸 수 있는 flat dict로 변환"""
    face = raw.get("face", {})
    outfit = raw.get("outfit", {})
    hair = raw.get("hair", {})

    # 얼굴 설명 조합
    face_parts = []
    if face.get("gender") and face.get("age"):
        face_parts.append(f"{face['age']} {face['gender']}")
    if face.get("ethnicity"):
        face_parts.append(face["ethnicity"])
    if face.get("skin_tone"):
        face_parts.append(f"skin: {face['skin_tone']}")
    if face.get("face_shape"):
        face_parts.append(f"{face['face_shape']} face shape")
    if face.get("distinctive_features"):
        face_parts.append(face["distinctive_features"])

    # 착장 설명 조합
    outfit_parts = []
    if outfit.get("description"):
        outfit_parts.append(outfit["description"])
    if outfit.get("details"):
        outfit_parts.extend(outfit["details"])
    if outfit.get("fit"):
        outfit_parts.append(f"fit: {outfit['fit']}")

    # 헤어 설명 조합
    hair_parts = []
    if hair.get("length"):
        hair_parts.append(hair["length"])
    if hair.get("color"):
        hair_parts.append(hair["color"])
    if hair.get("style"):
        hair_parts.append(hair["style"])

    return {
        # flat 문자열 필드
        "face_description": ", ".join(face_parts)
        if face_parts
        else "young Asian female, natural look",
        "outfit_description": "; ".join(outfit_parts)
        if outfit_parts
        else "casual outfit",
        "hair_description": ", ".join(hair_parts) if hair_parts else "natural hair",
        "body_type": raw.get("body_type", "average build"),
        # 원본 중첩 구조도 유지
        "face": face,
        "outfit": outfit,
        "hair": hair,
    }


# ============================================================================
# 메인 분석 함수
# ============================================================================


def analyze_reference_pose(
    reference_image: Union[Image.Image, str],
    client: Any,
) -> dict:
    """레퍼런스 이미지의 포즈/구도/배경을 상세 분석한다.

    레퍼런스 이미지는 API에 직접 전달되므로, 이 함수는
    검수 및 프롬프트 조립에 사용할 구조화된 텍스트 데이터를 반환한다.

    Args:
        reference_image: 레퍼런스 이미지 (PIL.Image 또는 파일 경로)
        client: Google GenAI client instance

    Returns:
        dict with keys:
            - pose_description: str  (전신 포즈 상세 설명)
            - camera_angle: str      (카메라 앵글)
            - framing: str           (프레이밍)
            - composition: str       (구도 전체 설명)
            - background: str        (배경 설명)
            - expression: str        (표정/시선/무드)
            - pose: dict             (원본 중첩 구조)
            - composition_raw: dict
            - background_raw: dict
            - expression_raw: dict
    """
    pil_image = _load_image(reference_image, "PoseCopyAnalyzer[reference]")
    if pil_image is None:
        print("[PoseCopyAnalyzer] 레퍼런스 이미지 로드 실패, 폴백 사용")
        return _get_fallback_reference_analysis()

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[REFERENCE_POSE_ANALYSIS_PROMPT, pil_image],
        )
        response_text = response.text.strip()
        raw = _parse_json_response(response_text, "PoseCopyAnalyzer[reference]")

        if not raw or "pose" not in raw:
            print("[PoseCopyAnalyzer] 레퍼런스 분석 응답 불완전, 폴백 사용")
            return _get_fallback_reference_analysis()

        return _flatten_reference_analysis(raw)

    except Exception as e:
        print(f"[PoseCopyAnalyzer] 레퍼런스 포즈 분석 실패: {e}")
        return _get_fallback_reference_analysis()


def analyze_source_person(
    source_image: Union[Image.Image, str],
    client: Any,
) -> dict:
    """소스 인물의 얼굴과 착장을 텍스트로 분석한다.

    중요: 소스 이미지는 API에 직접 전달하지 않는다.
    이 함수에서 텍스트로 변환하여 포즈 혼동을 방지한다.

    Args:
        source_image: 소스 인물 이미지 (PIL.Image 또는 파일 경로)
        client: Google GenAI client instance

    Returns:
        dict with keys:
            - face_description: str   (얼굴 상세 설명)
            - outfit_description: str (착장 상세 설명)
            - hair_description: str   (헤어 설명)
            - body_type: str          (체형)
            - face: dict              (원본 중첩 구조)
            - outfit: dict
            - hair: dict

    Note:
        포즈/자세 정보는 의도적으로 추출하지 않는다.
        SOURCE_PERSON_ANALYSIS_PROMPT가 포즈 분석을 명시적으로 제외한다.
    """
    pil_image = _load_image(source_image, "PoseCopyAnalyzer[source]")
    if pil_image is None:
        print("[PoseCopyAnalyzer] 소스 이미지 로드 실패, 폴백 사용")
        return _get_fallback_source_analysis()

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[SOURCE_PERSON_ANALYSIS_PROMPT, pil_image],
        )
        response_text = response.text.strip()
        raw = _parse_json_response(response_text, "PoseCopyAnalyzer[source]")

        if not raw or "face" not in raw:
            print("[PoseCopyAnalyzer] 소스 분석 응답 불완전, 폴백 사용")
            return _get_fallback_source_analysis()

        return _flatten_source_analysis(raw)

    except Exception as e:
        print(f"[PoseCopyAnalyzer] 소스 인물 분석 실패: {e}")
        return _get_fallback_source_analysis()
