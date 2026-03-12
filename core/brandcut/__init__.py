"""
브랜드컷 생성 모듈 v2

변경점 (v1 대비):
1. prompt_builder_v2: 한국어 프롬프트 통합
2. validator_v2: 14개 기준 (aesthetic_appeal, brand_vibe 추가)
3. retry_generator_v2: 실패 항목별 타겟 강화
4. edit_generator: 편집 모드 (기존 A컷 이미지 기반 착장/배경 변경)

Usage:
    from core.brandcut import (
        # 분석
        analyze_outfit,
        analyze_pose_expression,
        # 프롬프트 빌드
        build_prompt,
        # 생성 모드 (새 이미지 생성)
        generate_brandcut,           # 순수 이미지 생성
        generate_with_validation,    # 생성 + 검증 + 재시도 루프
        # 편집 모드 (기존 이미지 수정) - NEW!
        edit_brandcut,               # 순수 이미지 편집
        edit_with_validation,        # 편집 + 검증 + 재시도 루프
        build_outfit_description,    # 착장 설명 헬퍼
        # 검증
        BrandcutValidator,           # 14-criteria 검증기
        OutfitAnalysis               # re-export for type hints
    )
"""

# Analyzer functions
from .analyzer import (
    analyze_outfit,
    analyze_pose_expression,
    analyze_pose,
    analyze_expression,
)

# 인플루언서 분석 타입 re-export (type hints 용)
from core.ai_influencer.pose_analyzer import PoseAnalysisResult
from core.ai_influencer.expression_analyzer import ExpressionAnalysisResult

# Prompt builder v2 (unified Korean prompt builder)
from .prompt_builder_v2 import (
    build_prompt,
    build_prompt_with_director,
    enhance_prompt_for_retry,
    MLB_BRAND_DNA,
    get_random_expression,
    # K-Beauty 표정 프리셋
    KBEAUTY_EXPRESSION_PRESETS,
    get_expression_preset,
)

# Keep validate_and_fix_combinations from old prompt_builder for backwards compatibility
from .prompt_builder import validate_and_fix_combinations

# Generator v2 (mood image direct transmission)
from .generator_v2 import generate_brandcut, pil_to_part

# Retry generator v2 (targeted enhancement)
from .retry_generator_v2 import generate_with_validation

# Edit generator (편집 모드 - 기존 이미지 기반)
from .edit_generator import (
    edit_brandcut,
    edit_with_validation,
    build_outfit_description,
    build_edit_prompt,
)

# Validator v2 (14 criteria)
from .validator_v2 import (
    BrandcutValidator,
    ValidationResult,
    CRITERION_NAMES_KR,
    THRESHOLDS,
    WEIGHTS,
    ENHANCEMENT_RULES,
)

# Backwards compatibility aliases for MLBValidator
MLBValidator = BrandcutValidator
MLBValidationResult = ValidationResult

# Re-export OutfitAnalysis for external type hints
from core.outfit_analyzer import OutfitAnalysis

# Style Director (style_selector + director_analysis 통합)
from .style_director import (
    StyleDirector,
    get_style_director,
    select_style_with_director,
    get_diverse_micro_instructions,
    ANGLE_DISTRIBUTION,
    FRAMING_DISTRIBUTION,
)

# Director to Prompt converter
from .director_to_prompt import (
    director_to_full_prompt,
    convert_camera_to_prompt,
    convert_pose_to_prompt,
    convert_expression_to_prompt,
    load_director_json,
)

# CLIP A-Grade Validator
try:
    from .clip_validator import (
        CLIPValidator,
        get_clip_validator,
        score_a_grade_similarity,
        validate_a_grade_batch,
        A_GRADE_THRESHOLD,
        B_GRADE_THRESHOLD,
    )

    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

__all__ = [
    # Analyzer functions
    "analyze_outfit",
    "analyze_pose_expression",
    "analyze_pose",
    "analyze_expression",
    # 인플루언서 분석 타입
    "PoseAnalysisResult",
    "ExpressionAnalysisResult",
    # Prompt builder functions
    "build_prompt",
    "build_prompt_with_director",
    "enhance_prompt_for_retry",
    "validate_and_fix_combinations",
    "MLB_BRAND_DNA",
    "get_random_expression",
    # K-Beauty 표정 프리셋
    "KBEAUTY_EXPRESSION_PRESETS",
    "get_expression_preset",
    # Generator functions (생성 모드)
    "generate_brandcut",
    "generate_with_validation",
    "pil_to_part",
    # Edit functions (편집 모드)
    "edit_brandcut",
    "edit_with_validation",
    "build_outfit_description",
    "build_edit_prompt",
    # Validator (14-criteria)
    "BrandcutValidator",
    "ValidationResult",
    "CRITERION_NAMES_KR",
    "THRESHOLDS",
    "WEIGHTS",
    "ENHANCEMENT_RULES",
    # Backwards compatibility aliases
    "MLBValidator",
    "MLBValidationResult",
    # Type exports
    "OutfitAnalysis",
    # Style Director (style_selector + director 통합)
    "StyleDirector",
    "get_style_director",
    "select_style_with_director",
    "get_diverse_micro_instructions",
    "ANGLE_DISTRIBUTION",
    "FRAMING_DISTRIBUTION",
    # Director to Prompt
    "director_to_full_prompt",
    "convert_camera_to_prompt",
    "convert_pose_to_prompt",
    "convert_expression_to_prompt",
    "load_director_json",
    # CLIP Validator (optional)
    "CLIP_AVAILABLE",
    "CLIPValidator",
    "get_clip_validator",
    "score_a_grade_similarity",
    "validate_a_grade_batch",
    "A_GRADE_THRESHOLD",
    "B_GRADE_THRESHOLD",
]
