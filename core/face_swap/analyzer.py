"""
Face Swap 소스 이미지 분석 모듈

소스 이미지에서 보존해야 할 요소(포즈, 착장, 배경, 조명)를 추출하고,
얼굴 이미지 목록에서 AI 생성에 최적인 이미지를 선택한다.

V2: 카테고리 기반 분석 지원 (A/B 테스트용)
"""

import json
import re
from typing import Any, Optional

from google.genai import types
from PIL import Image

from core.config import VISION_MODEL
from .templates import SOURCE_ANALYSIS_PROMPT, FACE_SELECTION_PROMPT
from .templates_variants import SOURCE_ANALYSIS_PROMPT_V2, VALID_CATEGORIES


# ============================================================
# 내부 유틸 함수
# ============================================================


def _load_image(image: "Image.Image | str") -> Optional[Image.Image]:
    """이미지 로드 (경로 또는 PIL Image)"""
    if isinstance(image, str):
        try:
            return Image.open(image)
        except Exception as e:
            print(f"[FaceSwapAnalyzer] 이미지 로드 실패 {image}: {e}")
            return None
    return image


def _parse_json_response(response_text: str) -> dict:
    """JSON 응답 파싱 (마크다운 코드 블록 제거)"""
    # 마크다운 코드 블록에서 JSON 추출
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # JSON 파싱 시도
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[FaceSwapAnalyzer] JSON 파싱 에러: {e}")

        # JSON 객체 직접 추출 시도
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                return json.loads(response_text[start_idx : end_idx + 1])
            except json.JSONDecodeError:
                pass

        return {}


def _flatten_source_analysis(raw: dict) -> dict:
    """
    SOURCE_ANALYSIS_PROMPT의 중첩 JSON을 프롬프트 빌더가 사용하는
    flat dict로 변환한다.

    Returns:
        dict with keys:
        - face_position: str
        - face_angle: str
        - pose_description: str
        - outfit_description: str
        - background_description: str
        - lighting_description: str
    """
    face = raw.get("face", {})
    preserve = raw.get("preserve_elements", {})

    # 얼굴 위치 문자열 (x, y 좌표)
    pos = face.get("position", {})
    face_position = f"x={pos.get('x', 0.5):.2f}, y={pos.get('y', 0.3):.2f}"

    face_angle = face.get("angle", "frontal")

    # 포즈 설명 조합
    pose = preserve.get("pose", {})
    pose_parts = []
    if pose.get("body_position"):
        pose_parts.append(pose["body_position"])
    if pose.get("arm_left"):
        pose_parts.append(f"left arm: {pose['arm_left']}")
    if pose.get("arm_right"):
        pose_parts.append(f"right arm: {pose['arm_right']}")
    if pose.get("leg_position"):
        pose_parts.append(f"legs: {pose['leg_position']}")
    pose_description = ", ".join(pose_parts) if pose_parts else "standing naturally"

    # 착장 설명 조합
    outfit = preserve.get("outfit", {})
    outfit_parts = []
    if outfit.get("description"):
        outfit_parts.append(outfit["description"])
    if outfit.get("colors"):
        outfit_parts.append(f"colors: {', '.join(outfit['colors'])}")
    if outfit.get("style"):
        outfit_parts.append(f"style: {outfit['style']}")
    outfit_description = ", ".join(outfit_parts) if outfit_parts else "casual outfit"

    # 배경 설명 조합
    background = preserve.get("background", {})
    bg_parts = []
    if background.get("setting"):
        bg_parts.append(background["setting"])
    if background.get("color_tone"):
        bg_parts.append(f"tone: {background['color_tone']}")
    if background.get("lighting"):
        bg_parts.append(background["lighting"])
    background_description = ", ".join(bg_parts) if bg_parts else "neutral background"

    # 조명 설명 조합
    lighting = preserve.get("lighting", {})
    light_parts = []
    if lighting.get("direction"):
        light_parts.append(f"direction: {lighting['direction']}")
    if lighting.get("quality"):
        light_parts.append(f"quality: {lighting['quality']}")
    if lighting.get("face_lighting"):
        light_parts.append(f"face: {lighting['face_lighting']}")
    lighting_description = ", ".join(light_parts) if light_parts else "natural lighting"

    return {
        "face_position": face_position,
        "face_angle": face_angle,
        "pose_description": pose_description,
        "outfit_description": outfit_description,
        "background_description": background_description,
        "lighting_description": lighting_description,
    }


def _get_fallback_source_analysis() -> dict:
    """분석 실패 시 기본값"""
    return {
        "face_position": "x=0.50, y=0.30",
        "face_angle": "frontal",
        "pose_description": "standing naturally",
        "outfit_description": "casual outfit",
        "background_description": "neutral background",
        "lighting_description": "natural soft lighting",
    }


# ============================================================
# 공개 함수
# ============================================================


def analyze_source_image(
    source_image: "Image.Image | str",
    client: Any,
) -> dict:
    """
    소스 이미지 분석 — 얼굴 스왑 시 보존해야 할 요소 추출.

    Args:
        source_image: PIL.Image 또는 이미지 파일 경로
        client: Google GenAI client instance

    Returns:
        dict with keys:
        - face_position: str  (예: "x=0.50, y=0.30")
        - face_angle: str     (예: "3/4 left")
        - pose_description: str
        - outfit_description: str
        - background_description: str
        - lighting_description: str
    """
    pil_image = _load_image(source_image)
    if pil_image is None:
        print("[FaceSwapAnalyzer] 소스 이미지 로드 실패, 기본값 사용")
        return _get_fallback_source_analysis()

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[SOURCE_ANALYSIS_PROMPT, pil_image],
        )
        response_text = response.text.strip()
        raw = _parse_json_response(response_text)

        if not raw:
            print("[FaceSwapAnalyzer] 소스 분석 응답 파싱 실패, 기본값 사용")
            return _get_fallback_source_analysis()

        return _flatten_source_analysis(raw)

    except Exception as e:
        print(f"[FaceSwapAnalyzer] 소스 이미지 분석 실패: {e}")
        return _get_fallback_source_analysis()


def select_best_face_images(
    face_images: "list[Image.Image | str]",
    client: Any,
    max_faces: int = 2,
) -> list:
    """
    얼굴 이미지 목록에서 AI 생성에 최적인 이미지를 선택한다.

    Args:
        face_images: PIL.Image 또는 파일 경로 목록 (최대 5장 처리)
        client: Google GenAI client instance
        max_faces: 반환할 최대 이미지 수 (기본값 2)

    Returns:
        선택된 PIL.Image 목록 (최대 max_faces장)
        분석 실패 시 입력 목록의 앞 max_faces장 반환
    """
    if not face_images:
        return []

    # 최대 5장만 처리
    limited = face_images[:5]

    # PIL Image로 변환
    pil_images: list[Image.Image] = []
    for img in limited:
        loaded = _load_image(img)
        if loaded is not None:
            pil_images.append(loaded)

    if not pil_images:
        print("[FaceSwapAnalyzer] 유효한 얼굴 이미지 없음")
        return []

    # 이미지 1장이면 바로 반환
    if len(pil_images) == 1:
        return pil_images[:max_faces]

    # VLM에 이미지 + 프롬프트 전달하여 최적 이미지 선택
    try:
        contents = [FACE_SELECTION_PROMPT] + pil_images
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=contents,
        )
        response_text = response.text.strip()
        data = _parse_json_response(response_text)

        selected_indices = []
        selected_info = data.get("selected_images", [])

        for item in selected_info:
            filename = item.get("filename", "")
            # 파일명 기반 인덱스 매칭 시도
            for idx, original in enumerate(limited):
                if isinstance(original, str) and (
                    filename in original or original.endswith(filename)
                ):
                    if idx not in selected_indices:
                        selected_indices.append(idx)
                    break

        if selected_indices:
            result = [pil_images[i] for i in selected_indices if i < len(pil_images)]
            return result[:max_faces]

        # 파일명 매칭 실패 시 선택된 수만큼 앞에서 반환
        count = min(len(selected_info), max_faces, len(pil_images))
        if count > 0:
            print("[FaceSwapAnalyzer] 파일명 매칭 실패, 앞에서 선택")
            return pil_images[:count]

    except Exception as e:
        print(f"[FaceSwapAnalyzer] 얼굴 이미지 선택 실패: {e}")

    # 폴백: 앞 max_faces장 반환
    return pil_images[:max_faces]


# ============================================================
# V2: 카테고리 기반 분석 (A/B 테스트용)
# ============================================================


def _get_fallback_category_analysis() -> dict:
    """카테고리 분석 실패 시 기본값"""
    return {
        "face_angle_category": "frontal",
        "pose_category": "standing",
        "lighting_category": "front",
        "background_category": "studio",
        "face_position": {"x": 0.5, "y": 0.3},
        "pose_brief": "standing naturally",
        "outfit_brief": "casual outfit",
    }


def _validate_categories(analysis: dict) -> dict:
    """카테고리 값 검증 및 보정"""
    result = analysis.copy()

    for key, valid_values in VALID_CATEGORIES.items():
        value = result.get(key, "")
        if value not in valid_values:
            # 기본값으로 폴백
            result[key] = valid_values[0]
            print(
                f"[FaceSwapAnalyzer] 카테고리 보정: {key}={value} -> {valid_values[0]}"
            )

    return result


def analyze_source_image_v2(
    source_image: "Image.Image | str",
    client: Any,
) -> dict:
    """
    소스 이미지 분석 V2 - 카테고리 기반 분석.

    Args:
        source_image: PIL.Image 또는 이미지 파일 경로
        client: Google GenAI client instance

    Returns:
        dict with keys:
        - face_angle_category: str (enum)
        - pose_category: str (enum)
        - lighting_category: str (enum)
        - background_category: str (enum)
        - face_position: dict {"x": float, "y": float}
        - pose_brief: str (20자 이내)
        - outfit_brief: str (20자 이내)
    """
    pil_image = _load_image(source_image)
    if pil_image is None:
        print("[FaceSwapAnalyzer] 소스 이미지 로드 실패, 기본값 사용")
        return _get_fallback_category_analysis()

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[SOURCE_ANALYSIS_PROMPT_V2, pil_image],
            config=types.GenerateContentConfig(
                temperature=1,  # 기본값 사용
                response_mime_type="application/json",
            ),
        )
        response_text = response.text.strip()
        raw = _parse_json_response(response_text)

        if not raw:
            print("[FaceSwapAnalyzer] V2 분석 응답 파싱 실패, 기본값 사용")
            return _get_fallback_category_analysis()

        # 카테고리 검증 및 보정
        validated = _validate_categories(raw)

        # face_position 기본값 처리
        if "face_position" not in validated:
            validated["face_position"] = {"x": 0.5, "y": 0.3}

        # brief 기본값 처리
        if "pose_brief" not in validated:
            validated["pose_brief"] = "natural pose"
        if "outfit_brief" not in validated:
            validated["outfit_brief"] = "casual outfit"

        return validated

    except Exception as e:
        print(f"[FaceSwapAnalyzer] V2 소스 이미지 분석 실패: {e}")
        return _get_fallback_category_analysis()
