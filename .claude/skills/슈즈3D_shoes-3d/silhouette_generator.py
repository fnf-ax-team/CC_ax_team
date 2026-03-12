"""
실루엣 생성기 - Tripo API가 정확한 형태를 생성하도록 참조 이미지 생성
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import google.generativeai as genai
from google.generativeai import types

from core.config import IMAGE_MODEL

logger = logging.getLogger(__name__)


async def generate_silhouette_views(
    shoe_analysis: Dict[str, Any],
    angles: List[str],
    api_key: str,
    output_dir: Path
) -> List[str]:
    """
    신발 분석 결과를 바탕으로 실루엣 참조 이미지 생성

    Args:
        shoe_analysis: 신발 분석 결과 (analyze_shoe 반환값)
        angles: 생성할 각도 리스트 (front, side, back, top)
        api_key: Gemini API 키
        output_dir: 출력 디렉토리

    Returns:
        list[str]: 생성된 이미지 경로 리스트
    """
    # Gemini 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(IMAGE_MODEL)

    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 각도별 설명
    angle_descriptions = {
        "front": "front view, showing laces and toe box clearly",
        "side": "side profile view, showing full silhouette and sole height",
        "back": "back view, showing heel tab and branding",
        "top": "top-down view, showing insole and opening"
    }

    generated_images = []

    for angle in angles:
        try:
            # 프롬프트 생성
            prompt = f"""High-quality product photography of {shoe_analysis['shoe_type']},
clean white background, studio lighting, {shoe_analysis['silhouette']} design,
showing {', '.join(shoe_analysis['features'])},
shot from {angle_descriptions[angle]},
professional e-commerce style, 8K resolution, sharp focus"""

            # 이미지 생성
            config = types.GenerateContentConfig(
                temperature=0.2,
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                    image_size="2K"
                )
            )

            response = model.generate_content(prompt, generation_config=config)

            # 이미지 저장
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        output_path = output_dir / f"{angle}_view.png"
                        with open(output_path, 'wb') as f:
                            f.write(part.inline_data.data)

                        generated_images.append(str(output_path))
                        logger.info(f"실루엣 이미지 생성 완료: {angle} -> {output_path}")
                        break
            else:
                logger.warning(f"이미지 생성 실패: {angle}")

        except Exception as e:
            logger.error(f"실루엣 생성 에러 ({angle}): {e}")
            raise

    return generated_images
