"""
배경 분석 래퍼 모듈

원본: core.ai_influencer.background_analyzer (BackgroundAnalyzer, BackgroundAnalysisResult)

래핑 범위:
- BackgroundAnalysisResult 재export
- analyze_background(): api_key 표준 인터페이스
"""

from pathlib import Path
from typing import Optional, Union

from PIL import Image

# 원본 분석기 import
from core.ai_influencer.background_analyzer import (
    BackgroundAnalyzer,
    BackgroundAnalysisResult,
)


def analyze_background(
    image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> BackgroundAnalysisResult:
    """
    배경 분석 (통합 인터페이스).

    이미지에서 배경 환경을 분석한다.
    배경 유형, 제공 요소, 가능한 포즈, 앉을 수 있는 위치 등을 반환.

    Args:
        image: 배경 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)

    Returns:
        BackgroundAnalysisResult
    """
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    analyzer = BackgroundAnalyzer(api_key=api_key)
    return analyzer.analyze(image)


__all__ = [
    "BackgroundAnalysisResult",
    "analyze_background",
]
