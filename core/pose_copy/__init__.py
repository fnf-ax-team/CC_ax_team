"""
포즈 따라하기 워크플로 모듈

레퍼런스 이미지의 포즈를 소스 인물에게 적용.
얼굴/착장/배경을 소스에서 유지.

Usage:
    from core.pose_copy import generate_pose_copy, generate_with_validation
    from core.pose_copy.analyzer import analyze_reference_pose, analyze_source_person
    from core.pose_copy.validator import PoseCopyValidator
"""

from .analyzer import analyze_reference_pose, analyze_source_person
from .prompt_builder import build_pose_copy_prompt
from .generator import generate_pose_copy, generate_with_validation
from .validator import PoseCopyValidator
from .templates import (
    REFERENCE_POSE_ANALYSIS_PROMPT,
    SOURCE_PERSON_ANALYSIS_PROMPT,
    POSE_COPY_PROMPT,
    VALIDATION_PROMPT,
)

__all__ = [
    # 생성 함수 (주요 API)
    "generate_pose_copy",
    "generate_with_validation",
    # 분석
    "analyze_reference_pose",
    "analyze_source_person",
    # 프롬프트 빌더
    "build_pose_copy_prompt",
    # 검증기
    "PoseCopyValidator",
    # 템플릿 (선택사항)
    "REFERENCE_POSE_ANALYSIS_PROMPT",
    "SOURCE_PERSON_ANALYSIS_PROMPT",
    "POSE_COPY_PROMPT",
    "VALIDATION_PROMPT",
]
