"""
이커머스 VLM 분석 모듈

착장 분석과 모델 얼굴 분석을 통해 이커머스 이미지 생성에 필요한
정보를 추출한다. 브랜드컷과 달리 상업적 디스플레이(상품 정확도)에 집중.
"""

from typing import Any
from PIL import Image
import json
import re

from core.config import VISION_MODEL
from .templates import OUTFIT_ANALYSIS_PROMPT


# ------------------------------------------------------------------
# 얼굴 분석용 내부 프롬프트
# ------------------------------------------------------------------
_FACE_ANALYSIS_PROMPT = """
얼굴 이미지를 분석하여 이커머스 모델 생성에 필요한 정보를 추출하세요.

JSON 형식으로 출력:
{
  "face_description": "얼굴 전체 설명 (형태, 특징)",
  "skin_tone": "피부톤 (예: fair, light, medium, olive, tan, dark)",
  "age_range": "나이대 (예: early_20s, mid_20s, late_20s, 30s)",
  "expression_style": "표정 스타일 (예: natural, approachable, neutral, friendly)"
}
"""


def _load_image(image: "Image.Image | str") -> "Image.Image | None":
    """이미지 로드 헬퍼. 경로(str) 또는 PIL 이미지 모두 처리."""
    if isinstance(image, str):
        try:
            return Image.open(image)
        except Exception as e:
            print(f"[EcommerceAnalyzer] 이미지 로드 실패: {image} → {e}")
            return None
    return image


def _parse_json(text: str) -> dict:
    """VLM 응답에서 JSON 파싱. 마크다운 코드 블록 제거 후 시도."""
    # 마크다운 코드 블록 제거
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # { ... } 범위 직접 추출 시도
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}


def analyze_outfit_for_ecommerce(
    outfit_images: "list[Image.Image | str]",
    client: Any,
) -> dict:
    """착장 이미지를 이커머스 디스플레이 관점에서 분석한다.

    브랜드컷 분석과 달리 상품 정확도(색상·로고·디테일·실루엣)와
    판매 포인트 추출에 집중한다.

    Args:
        outfit_images: 착장 이미지 리스트 (PIL.Image 또는 경로 문자열)
        client: Google GenAI client instance

    Returns:
        dict:
            - items (list[dict]): 아이템별 상세
                - type (str): 아이템 유형 (outer/top/bottom/shoes/accessories)
                - color (str): 정확한 색상 표현
                - material (str): 소재 질감
                - logo (str): 로고/그래픽 위치 및 내용
                - details (list[str]): AI가 놓치기 쉬운 디테일
            - overall_style (str): 전체 스타일 요약
            - recommended_pose (str): 착장 특성에 맞는 권장 포즈 키
            - key_selling_points (list[str]): 강조해야 할 판매 포인트
    """
    if not outfit_images:
        return _fallback_outfit_analysis()

    # 이미지 로드
    pil_images = []
    for img in outfit_images:
        loaded = _load_image(img)
        if loaded:
            pil_images.append(loaded)

    if not pil_images:
        return _fallback_outfit_analysis()

    # VLM 호출: 프롬프트 + 모든 착장 이미지 전달
    contents = [OUTFIT_ANALYSIS_PROMPT] + pil_images

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=contents,
        )
        raw = response.text.strip()
        data = _parse_json(raw)
    except Exception as e:
        print(f"[EcommerceAnalyzer] 착장 분석 VLM 호출 실패: {e}")
        return _fallback_outfit_analysis()

    if not data:
        return _fallback_outfit_analysis()

    # VLM 응답을 표준 반환 형식으로 변환
    items = []
    for category in ["outer", "top", "bottom", "shoes"]:
        item_data = data.get(category, {})
        if isinstance(item_data, dict) and item_data.get("item"):
            items.append(
                {
                    "type": category,
                    "color": item_data.get("color", ""),
                    "material": "",  # OUTFIT_ANALYSIS_PROMPT는 material 미반환, 후처리용
                    "logo": item_data.get("logo_position", ""),
                    "details": item_data.get("details", []),
                    "item": item_data.get("item", ""),
                }
            )

    # accessories 처리 (리스트 형태)
    accessories = data.get("accessories", [])
    if isinstance(accessories, list):
        for acc in accessories:
            if isinstance(acc, str) and acc.strip():
                items.append(
                    {
                        "type": "accessories",
                        "color": "",
                        "material": "",
                        "logo": "",
                        "details": [acc],
                        "item": acc,
                    }
                )

    overall_style = data.get("overall_style", "")
    key_details = data.get("key_details", [])

    # 전체 스타일에서 권장 포즈 추론
    recommended_pose = _infer_pose_from_style(overall_style, items)

    return {
        "items": items,
        "overall_style": overall_style,
        "recommended_pose": recommended_pose,
        "key_selling_points": key_details,
        # 하위 호환: 원본 VLM 응답도 보존
        "_raw": data,
    }


def analyze_face_for_model(
    face_images: "list[Image.Image | str]",
    client: Any,
) -> dict:
    """얼굴 이미지를 분석하여 모델 생성에 필요한 정보를 추출한다.

    이커머스에서 얼굴 동일성은 착장 정확도보다 낮은 우선순위(20%)이지만,
    생성 프롬프트에 얼굴 특징을 명시하면 일치율이 높아진다.

    Args:
        face_images: 얼굴 이미지 리스트 (PIL.Image 또는 경로 문자열)
        client: Google GenAI client instance

    Returns:
        dict:
            - face_description (str): 얼굴 형태 및 특징 설명
            - skin_tone (str): 피부톤
            - age_range (str): 나이대
            - expression_style (str): 권장 표정 스타일
    """
    if not face_images:
        return _fallback_face_analysis()

    # 첫 번째 얼굴 이미지만 사용 (복수 제공 시 대표 이미지)
    pil_image = _load_image(face_images[0])
    if pil_image is None:
        return _fallback_face_analysis()

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[_FACE_ANALYSIS_PROMPT, pil_image],
        )
        raw = response.text.strip()
        data = _parse_json(raw)
    except Exception as e:
        print(f"[EcommerceAnalyzer] 얼굴 분석 VLM 호출 실패: {e}")
        return _fallback_face_analysis()

    if not data:
        return _fallback_face_analysis()

    return {
        "face_description": data.get("face_description", ""),
        "skin_tone": data.get("skin_tone", "light"),
        "age_range": data.get("age_range", "early_20s"),
        "expression_style": data.get("expression_style", "natural"),
    }


# ------------------------------------------------------------------
# 내부 헬퍼
# ------------------------------------------------------------------


def _infer_pose_from_style(overall_style: str, items: list) -> str:
    """착장 스타일에서 권장 이커머스 포즈 키를 추론한다."""
    style_lower = overall_style.lower()

    # 후면 디테일이 중요한 아이템 감지 (백프린트, 후드)
    for item in items:
        for detail in item.get("details", []):
            if any(kw in detail.lower() for kw in ["back print", "hood", "후드", "백"]):
                return "back_view"

    # 상의 중심 스타일 → 클로즈업 권장
    has_outer = any(item["type"] == "outer" for item in items)
    has_shoes = any(item["type"] == "shoes" for item in items)

    if has_outer and has_shoes:
        return "front_standing"  # 전신 필요
    if not has_shoes:
        return "detail_closeup"  # 신발 없으면 상반신 클로즈업

    # 기본값
    return "front_standing"


def _fallback_outfit_analysis() -> dict:
    """착장 분석 실패 시 폴백 반환값."""
    return {
        "items": [],
        "overall_style": "casual streetwear",
        "recommended_pose": "front_standing",
        "key_selling_points": [],
        "_raw": {},
    }


def _fallback_face_analysis() -> dict:
    """얼굴 분석 실패 시 폴백 반환값."""
    return {
        "face_description": "natural features, balanced proportions",
        "skin_tone": "light",
        "age_range": "early_20s",
        "expression_style": "natural",
    }
