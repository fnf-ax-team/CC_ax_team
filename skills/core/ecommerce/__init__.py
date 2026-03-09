"""
이커머스 모델 이미지 생성 모듈

온라인 쇼핑몰 상세페이지 및 룩북용 모델 이미지를 생성합니다.
착장 정확도를 최우선으로 하며, 클린한 배경과 상업적 품질을 유지합니다.

Usage:
    from core.ecommerce import generate_ecommerce_image, generate_with_validation
    from core.ecommerce import POSE_PRESETS, BACKGROUND_PRESETS
    from core.ecommerce.validator import EcommerceValidator
"""

from .presets import POSE_PRESETS, BACKGROUND_PRESETS, VALID_ECOMMERCE_BACKGROUNDS
from .templates import (
    OUTFIT_ANALYSIS_PROMPT,
    ECOMMERCE_GENERATION_PROMPT,
    VALIDATION_PROMPT,
)
from .validator import EcommerceValidator
from .analyzer import analyze_outfit_for_ecommerce, analyze_face_for_model
from .prompt_builder import build_ecommerce_prompt
from .generator import generate_ecommerce_image, generate_with_validation

__all__ = [
    # 생성 함수 (주요 API)
    "generate_ecommerce_image",
    "generate_with_validation",
    # 프리셋
    "POSE_PRESETS",
    "BACKGROUND_PRESETS",
    "VALID_ECOMMERCE_BACKGROUNDS",
    # 분석
    "analyze_outfit_for_ecommerce",
    "analyze_face_for_model",
    # 프롬프트 빌더
    "build_ecommerce_prompt",
    # 검증기
    "EcommerceValidator",
    # 템플릿 (선택사항)
    "OUTFIT_ANALYSIS_PROMPT",
    "ECOMMERCE_GENERATION_PROMPT",
    "VALIDATION_PROMPT",
]
