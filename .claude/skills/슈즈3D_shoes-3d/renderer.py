"""
렌더링 엔진 - 7개 각도 렌더링 및 품질 검증
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import json
import google.generativeai as genai

from core.config import VISION_MODEL

logger = logging.getLogger(__name__)


# 7가지 렌더링 각도 (yaw, pitch, roll)
RENDER_ANGLES = {
    "front": {"yaw": 0, "pitch": 0, "roll": 0},
    "back": {"yaw": 180, "pitch": 0, "roll": 0},
    "left": {"yaw": 90, "pitch": 0, "roll": 0},
    "right": {"yaw": 270, "pitch": 0, "roll": 0},
    "top": {"yaw": 0, "pitch": 90, "roll": 0},
    "bottom": {"yaw": 0, "pitch": -90, "roll": 0},
    "three_quarter": {"yaw": 45, "pitch": 30, "roll": 0}
}


# 렌더링 설정
render_config = {
    "resolution": [1920, 1080],
    "samples": 128,  # 레이트레이싱 샘플
    "hdri": "studio_neutral_4k",
    "background": "transparent",
    "format": "png",
    "lighting": "studio_3point"
}


async def validate_3d_quality(
    original_image: str,
    render_images: List[str],
    api_key: str
) -> Dict[str, Any]:
    """
    VLM으로 3D 렌더링 품질 평가

    Args:
        original_image: 원본 신발 이미지 경로
        render_images: 렌더링된 이미지 경로 리스트
        api_key: Gemini API 키

    Returns:
        dict: 품질 평가 결과
            - shape_accuracy: 형태 정확도 (0-100)
            - material_fidelity: 소재 충실도 (0-100)
            - color_match: 색상 일치도 (0-100)
            - detail_preservation: 디테일 보존도 (0-100)
            - lighting_quality: 조명 품질 (0-100)
            - overall_score: 총점 (0-100)
    """
    # Gemini 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(VISION_MODEL)

    # VLM 품질 평가 프롬프트
    prompt = """Compare the generated 3D render with the original shoe image.
Rate these aspects from 0-100:

1. shape_accuracy: How well does the 3D model match the original silhouette?
2. material_fidelity: Are textures (leather, mesh, rubber) realistic?
3. color_match: Do colors match the reference image?
4. detail_preservation: Are logos, stitching, perforations visible?
5. lighting_quality: Is the render professionally lit?

Return JSON with scores:
{
  "shape_accuracy": 0-100,
  "material_fidelity": 0-100,
  "color_match": 0-100,
  "detail_preservation": 0-100,
  "lighting_quality": 0-100,
  "overall_score": 0-100
}
"""

    try:
        # 원본 이미지 로드
        with open(original_image, 'rb') as f:
            original_data = f.read()

        # 대표 렌더 이미지 선택 (정면 또는 3/4 뷰)
        render_path = render_images[0] if render_images else None
        if not render_path or not Path(render_path).exists():
            logger.error("렌더링 이미지를 찾을 수 없음")
            return {
                "shape_accuracy": 0,
                "material_fidelity": 0,
                "color_match": 0,
                "detail_preservation": 0,
                "lighting_quality": 0,
                "overall_score": 0
            }

        with open(render_path, 'rb') as f:
            render_data = f.read()

        # VLM 실행
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": original_data},
            {"mime_type": "image/png", "data": render_data}
        ])

        # JSON 파싱
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()

        validation = json.loads(result_text)

        # 총점 계산 (없으면 평균)
        if "overall_score" not in validation:
            scores = [v for k, v in validation.items() if k != "overall_score"]
            validation["overall_score"] = sum(scores) / len(scores) if scores else 0

        logger.info(f"품질 검증 완료: 총점 {validation['overall_score']:.1f}")
        return validation

    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.error(f"응답: {response.text}")
        raise

    except Exception as e:
        logger.error(f"품질 검증 에러: {e}")
        raise


def check_quality_thresholds(validation: Dict[str, float]) -> bool:
    """
    품질 검증 통과 여부 확인

    Args:
        validation: 품질 평가 결과

    Returns:
        bool: 합격 여부
    """
    # 필수 조건
    required = [
        ("shape_accuracy", 80),
        ("material_fidelity", 70),
        ("color_match", 75),
        ("detail_preservation", 65)
    ]

    for metric, threshold in required:
        if validation.get(metric, 0) < threshold:
            logger.warning(f"품질 기준 미달: {metric} = {validation.get(metric, 0)} < {threshold}")
            return False

    logger.info("품질 검증 통과")
    return True
