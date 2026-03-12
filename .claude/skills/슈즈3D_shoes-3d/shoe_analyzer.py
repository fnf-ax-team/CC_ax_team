"""
신발 분석기 - VLM으로 신발 특성 추출
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path
import google.generativeai as genai

from core.config import VISION_MODEL

logger = logging.getLogger(__name__)


async def analyze_shoe(image_path: str, api_key: str) -> Dict[str, Any]:
    """
    신발 이미지를 VLM으로 분석하여 특성 추출

    Args:
        image_path: 신발 이미지 경로
        api_key: Gemini API 키

    Returns:
        dict: 신발 분석 결과
            - shoe_type: 신발 종류 (sneaker, boot, sandal, heel 등)
            - materials: 소재 리스트 (leather, mesh, rubber, canvas 등)
            - colors: 색상 리스트 (hex codes)
            - features: 주요 특징 (laces, buckles, straps, logo 등)
            - silhouette: 실루엣 (low-top, mid-top, high-top)
            - textures: 텍스처 패턴 (smooth, perforated, woven 등)
    """
    # Gemini 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(VISION_MODEL)

    # 이미지 로드
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없음: {image_path}")

    # VLM 분석 프롬프트
    prompt = """Analyze this shoe image and extract:
1. Shoe type (sneaker, boot, sandal, heel, etc.)
2. Material types visible (leather, mesh, rubber, canvas, etc.)
3. Dominant colors (hex codes if possible)
4. Key structural features (laces, buckles, straps, logo placement)
5. Overall silhouette shape (low-top, mid-top, high-top)
6. Texture patterns (smooth, perforated, woven, etc.)

Return structured JSON with these fields:
{
  "shoe_type": "string",
  "materials": ["string"],
  "colors": ["#hex"],
  "features": ["string"],
  "silhouette": "string",
  "textures": ["string"]
}
"""

    try:
        # VLM 실행
        with open(image_path, 'rb') as f:
            image_data = f.read()

        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_data}
        ])

        # JSON 파싱
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()

        analysis = json.loads(result_text)

        logger.info(f"신발 분석 완료: {analysis['shoe_type']}")
        return analysis

    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.error(f"응답: {response.text}")
        raise

    except Exception as e:
        logger.error(f"신발 분석 에러: {e}")
        raise
