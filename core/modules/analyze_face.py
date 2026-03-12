"""
얼굴 분석 래퍼 모듈

원본: core.ai_influencer.face_analyzer (FaceAnalyzer, FaceAnalysisResult)

래핑 범위:
- FaceAnalysisResult 재export
- ExtendedFaceAnalysisResult: 성별/나이/민족/표정 스타일 확장
- analyze_face(): api_key 표준 인터페이스 + 인구통계 옵션
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

from PIL import Image

# 원본 분석기 import
from core.ai_influencer.face_analyzer import (
    FaceAnalyzer,
    FaceAnalysisResult,
)

# 통합 VLM 유틸리티
from core.modules.vlm_utils import vlm_call


# ============================================================
# 확장 결과 데이터클래스
# ============================================================


@dataclass
class ExtendedFaceAnalysisResult(FaceAnalysisResult):
    """
    확장 얼굴 분석 결과.

    FaceAnalysisResult의 모든 필드를 상속하고,
    인구통계(성별/나이/민족) 및 표정 스타일 필드를 추가.

    include_demographics=True일 때만 추가 VLM 호출로 채워진다.
    """

    gender: Optional[str] = None  # female, male
    age_range: Optional[str] = None  # early_20s, mid_20s, late_20s 등
    ethnicity: Optional[str] = None  # korean, japanese, chinese, western 등
    expression_style: Optional[str] = None  # cool, warm, natural 등


# 인구통계 분석용 VLM 프롬프트
_DEMOGRAPHICS_PROMPT = """이 인물의 인구통계 정보를 분석하세요.

JSON 형식으로 출력:
```json
{
    "gender": "female 또는 male",
    "age_range": "early_20s / mid_20s / late_20s / early_30s / mid_30s 중 하나",
    "ethnicity": "korean / japanese / chinese / southeast_asian / western / mixed 중 하나",
    "expression_style": "cool / warm / natural / dreamy / playful 중 하나"
}
```

JSON만 출력하세요."""


# ============================================================
# 메인 분석 함수
# ============================================================


def analyze_face(
    image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
    include_demographics: bool = False,
) -> Union[FaceAnalysisResult, ExtendedFaceAnalysisResult]:
    """
    얼굴 특징 분석 (통합 인터페이스).

    기본적으로 원본 FaceAnalyzer를 사용하여 얼굴형/눈/코/입술/턱선 등을 분석.
    include_demographics=True이면 추가 VLM 호출로 성별/나이/민족/표정스타일도 분석.

    Args:
        image: 얼굴 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)
        include_demographics: 인구통계 확장 분석 여부

    Returns:
        FaceAnalysisResult (기본) 또는 ExtendedFaceAnalysisResult (확장)
    """
    # API 키 자동 로드
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # 1) 기본 얼굴 분석 (원본 분석기 사용)
    analyzer = FaceAnalyzer(api_key=api_key)
    base_result = analyzer.analyze(image)

    if not include_demographics:
        return base_result

    # 2) 인구통계 확장 분석 (추가 VLM 호출)
    demo_data = vlm_call(
        api_key=api_key,
        prompt=_DEMOGRAPHICS_PROMPT,
        images=[image],
        temperature=0.1,
    )

    # 확장 결과 생성 (기본 결과 필드 복사 + 인구통계 추가)
    return ExtendedFaceAnalysisResult(
        # 기본 FaceAnalysisResult 필드
        face_shape=base_result.face_shape,
        eye_shape=base_result.eye_shape,
        eye_size=base_result.eye_size,
        eye_spacing=base_result.eye_spacing,
        nose_shape=base_result.nose_shape,
        lip_shape=base_result.lip_shape,
        jawline=base_result.jawline,
        cheekbones=base_result.cheekbones,
        skin_tone=base_result.skin_tone,
        distinctive=base_result.distinctive,
        confidence=base_result.confidence,
        raw_response=base_result.raw_response,
        # 확장 필드
        gender=demo_data.get("gender"),
        age_range=demo_data.get("age_range"),
        ethnicity=demo_data.get("ethnicity"),
        expression_style=demo_data.get("expression_style"),
    )


__all__ = [
    "FaceAnalysisResult",
    "ExtendedFaceAnalysisResult",
    "analyze_face",
]
