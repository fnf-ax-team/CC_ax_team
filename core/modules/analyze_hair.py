"""
헤어 분석 래퍼 모듈

원본: core.ai_influencer.hair_analyzer (HairAnalyzer, HairAnalysisResult)

래핑 범위:
- HairAnalysisResult 재export
- analyze_hair(): api_key 표준 인터페이스
"""

from pathlib import Path
from typing import Optional, Union

from PIL import Image

# 원본 분석기 import
from core.ai_influencer.hair_analyzer import (
    HairAnalyzer,
    HairAnalysisResult,
)


def analyze_hair(
    image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> HairAnalysisResult:
    """
    헤어 분석 (통합 인터페이스).

    이미지에서 인물의 헤어 스타일, 컬러, 질감을 분석한다.

    Args:
        image: 얼굴/헤어 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)

    Returns:
        HairAnalysisResult
    """
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    analyzer = HairAnalyzer(api_key=api_key)
    return analyzer.analyze(image)


__all__ = [
    "HairAnalysisResult",
    "analyze_hair",
]
