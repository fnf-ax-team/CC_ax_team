"""
제품 분석기 - VLM을 사용한 제품 특성 추출
"""

import json
from typing import Dict
from core.config import VISION_MODEL
from google import genai
from google.genai import types


def analyze_product(image_path: str, api_key: str) -> Dict:
    """
    VLM으로 제품 특성 추출

    Args:
        image_path: 제품 이미지 경로
        api_key: Gemini API 키

    Returns:
        {
            "product_type": str,  # "sneakers", "bag", "watch" 등
            "dominant_colors": list[str],  # ["white", "navy blue"]
            "material": str,  # "leather", "canvas", "metal"
            "key_features": list[str],  # ["logo on tongue", "metal buckle"]
        }
    """
    client = genai.Client(api_key=api_key)

    # 이미지 로드
    with open(image_path, 'rb') as f:
        image_data = f.read()

    vlm_prompt = """
    Analyze this product image and extract:
    1. Product type (be specific: e.g., "high-top sneakers", "crossbody bag")
    2. Dominant colors (list top 2-3 colors in order of prominence)
    3. Primary material (leather, canvas, metal, plastic, etc.)
    4. Key visual features (logo placement, hardware, patterns, textures)

    Return in JSON format:
    {
        "product_type": "...",
        "dominant_colors": ["color1", "color2"],
        "material": "...",
        "key_features": ["feature1", "feature2"]
    }
    """

    # VLM 호출
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=image_data, mime_type="image/png"),
            vlm_prompt
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"]
        )
    )

    # JSON 파싱
    text = response.text.strip()

    # 코드 블록 제거
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    result = json.loads(text.strip())

    return result
