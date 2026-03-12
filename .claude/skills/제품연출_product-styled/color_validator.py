"""
색상 검증기 - VLM을 사용한 제품 색상 정확도 검증
"""

import json
from typing import Dict, List
from core.config import VISION_MODEL
from google import genai
from google.genai import types


def validate_color_accuracy(
    original_product: str,
    generated_image: bytes,
    expected_colors: List[str],
    api_key: str
) -> Dict:
    """
    생성된 이미지의 제품 색상이 원본과 일치하는지 VLM으로 검증

    Args:
        original_product: 원본 제품 이미지 경로
        generated_image: 생성된 이미지 바이트
        expected_colors: 예상 색상 리스트
        api_key: Gemini API 키

    Returns:
        {
            "accuracy_score": float,  # 0-100
            "color_match": bool,  # True if >= 90
            "detected_colors": list[str],
            "issues": list[str]  # 발견된 문제점
        }
    """
    client = genai.Client(api_key=api_key)

    # 원본 이미지 로드
    with open(original_product, 'rb') as f:
        original_data = f.read()

    vlm_prompt = f"""
    Compare the product colors in these two images:
    Image 1 (original product): Reference
    Image 2 (generated styled shot): To validate

    Expected product colors: {", ".join(expected_colors)}

    Evaluate:
    1. Color accuracy score (0-100): How well do the product colors match?
    2. Are all expected colors present and accurate?
    3. Any color shifts, saturation issues, or incorrect tones?

    Return in JSON format:
    {{
        "accuracy_score": <number 0-100>,
        "detected_colors": ["color1", "color2"],
        "issues": ["issue1 if any", "issue2 if any"]
    }}

    Focus ONLY on the product itself, ignore background/lighting differences.
    """

    # VLM 호출 (2개 이미지 비교)
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=original_data, mime_type="image/png"),
            types.Part.from_bytes(data=generated_image, mime_type="image/png"),
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

    # color_match 플래그 추가
    result["color_match"] = result["accuracy_score"] >= 90

    return result


def should_regenerate(validation: Dict) -> bool:
    """
    재생성 필요 여부 판단

    Args:
        validation: validate_color_accuracy()의 반환값

    Returns:
        True if 재생성 필요, False otherwise
    """
    # 색상 정확도 90% 미만이면 재생성
    if validation["accuracy_score"] < 90:
        return True

    # 치명적 이슈 목록
    critical_issues = [
        "wrong product color",
        "color shift",
        "product deformation",
        "missing key features"
    ]

    # 이슈 중 하나라도 치명적이면 재생성
    for issue in validation.get("issues", []):
        if any(crit in issue.lower() for crit in critical_issues):
            return True

    return False
