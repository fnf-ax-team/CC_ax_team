"""
다중 얼굴 교체 (Multi-Face Swap) 워크플로 모듈

단체 사진에서 여러 얼굴을 동시에 교체한다.
VLM으로 각 인물 위치/특징 감지 → 얼굴 폴더 매핑 → 모든 얼굴 동시 스왑.

Usage:
    from core.multi_face_swap import generate_multi_swap, generate_with_validation
    from core.multi_face_swap.detector import detect_faces, map_faces
    from core.multi_face_swap.validator import MultiFaceSwapValidator
"""

from .generator import generate_multi_swap, generate_with_validation
from .detector import detect_faces, map_faces
from .validator import MultiFaceSwapValidator
from .templates import (
    FACE_DETECTION_PROMPT,
    build_multi_face_swap_prompt,
    VALIDATION_PROMPT,
)

__all__ = [
    # 생성 함수 (주요 API)
    "generate_multi_swap",
    "generate_with_validation",
    # 감지 및 매핑
    "detect_faces",
    "map_faces",
    # 검증기
    "MultiFaceSwapValidator",
    # 템플릿 (선택사항)
    "FACE_DETECTION_PROMPT",
    "build_multi_face_swap_prompt",
    "VALIDATION_PROMPT",
]
