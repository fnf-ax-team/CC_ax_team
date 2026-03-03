"""
Face Swap 워크플로 모듈

얼굴만 교체 (포즈, 착장, 배경 유지)

Usage:
    from core.face_swap import generate_face_swap, generate_with_validation
    from core.face_swap import analyze_source_image, select_best_face_images
    from core.face_swap.validator import FaceSwapValidator
"""

from .templates import (
    SOURCE_ANALYSIS_PROMPT,
    FACE_SELECTION_PROMPT,
    FACE_SWAP_PROMPT,
    VALIDATION_PROMPT,
)
from .validator import FaceSwapValidator, FaceSwapValidationResult
from .analyzer import analyze_source_image, select_best_face_images
from .prompt_builder import build_face_swap_prompt
from .generator import generate_face_swap, generate_with_validation

__all__ = [
    # 생성 함수 (주요 API)
    "generate_face_swap",
    "generate_with_validation",
    # 분석
    "analyze_source_image",
    "select_best_face_images",
    # 프롬프트 빌더
    "build_face_swap_prompt",
    # 검증기
    "FaceSwapValidator",
    "FaceSwapValidationResult",
    # 템플릿 (선택사항)
    "SOURCE_ANALYSIS_PROMPT",
    "FACE_SELECTION_PROMPT",
    "FACE_SWAP_PROMPT",
    "VALIDATION_PROMPT",
]
