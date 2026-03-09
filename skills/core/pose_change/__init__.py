"""
포즈 변경 워크플로 모듈

기존 이미지의 포즈만 변경하고 얼굴/착장/배경은 유지.

Usage:
    from core.pose_change import generate_pose_change, generate_with_validation
    from core.pose_change import POSE_PRESETS, get_pose_description
    from core.pose_change.validator import PoseChangeValidator
"""

from .presets import POSE_PRESETS, get_pose_description
from .analyzer import analyze_source_for_pose_change, validate_target_pose
from .prompt_builder import build_pose_change_prompt
from .generator import generate_pose_change, generate_with_validation
from .validator import PoseChangeValidator
from .templates import (
    SOURCE_ANALYSIS_PROMPT,
    VALIDATION_PROMPT,
)

__all__ = [
    # 생성 함수 (주요 API)
    "generate_pose_change",
    "generate_with_validation",
    # 프리셋 및 유틸
    "POSE_PRESETS",
    "get_pose_description",
    # 분석
    "analyze_source_for_pose_change",
    "validate_target_pose",
    # 프롬프트 빌더
    "build_pose_change_prompt",
    # 검증기
    "PoseChangeValidator",
    # 템플릿 (선택사항)
    "SOURCE_ANALYSIS_PROMPT",
    "VALIDATION_PROMPT",
]
