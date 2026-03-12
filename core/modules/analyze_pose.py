"""
포즈 분석 래퍼 모듈

원본: core.ai_influencer.pose_analyzer (PoseAnalyzer, PoseAnalysisResult)

래핑 범위:
- PoseAnalysisResult 재export
- analyze_pose(): api_key 표준 인터페이스
"""

from pathlib import Path
from typing import Optional, Union

from PIL import Image

# 원본 분석기 import
from core.ai_influencer.pose_analyzer import (
    PoseAnalyzer,
    PoseAnalysisResult,
)


def analyze_pose(
    image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PoseAnalysisResult:
    """
    포즈 분석 (통합 인터페이스).

    이미지에서 모델의 포즈를 상세 분석한다.
    stance, 신체 부위별 설명, 카메라 앵글, 프레이밍 등을 반환.

    Args:
        image: 포즈 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)

    Returns:
        PoseAnalysisResult
    """
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    analyzer = PoseAnalyzer(api_key=api_key)
    return analyzer.analyze(image)


__all__ = [
    "PoseAnalysisResult",
    "analyze_pose",
]
