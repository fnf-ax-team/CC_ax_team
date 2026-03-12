"""
표정 분석 래퍼 모듈

원본: core.ai_influencer.expression_analyzer (ExpressionAnalyzer, ExpressionAnalysisResult)

래핑 범위:
- ExpressionAnalysisResult 재export
- analyze_expression(): api_key 표준 인터페이스
"""

from pathlib import Path
from typing import Optional, Union

from PIL import Image

# 원본 분석기 import
from core.ai_influencer.expression_analyzer import (
    ExpressionAnalyzer,
    ExpressionAnalysisResult,
)


def analyze_expression(
    image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> ExpressionAnalysisResult:
    """
    표정 분석 (통합 인터페이스).

    이미지에서 모델의 표정을 분석한다.
    베이스 무드, 눈, 시선, 입, 얼굴각도, 윙크 여부 등을 반환.

    Args:
        image: 표정/얼굴 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)

    Returns:
        ExpressionAnalysisResult
    """
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    analyzer = ExpressionAnalyzer(api_key=api_key)
    return analyzer.analyze(image)


__all__ = [
    "ExpressionAnalysisResult",
    "analyze_expression",
]
