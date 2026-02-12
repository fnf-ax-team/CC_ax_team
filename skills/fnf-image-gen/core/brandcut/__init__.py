"""
브랜드컷 생성 모듈

Usage:
    from core.brandcut import (
        analyze_outfit,
        analyze_pose_expression,
        analyze_mood,
        build_prompt,
        generate_brandcut,           # 순수 이미지 생성
        generate_with_validation,    # 생성 + 검증 + 재시도 루프
        OutfitAnalysis               # re-export for type hints
    )
"""

from .analyzer import (
    analyze_outfit,
    analyze_pose_expression,
    analyze_mood,
)
from .prompt_builder import build_prompt, validate_and_fix_combinations
from .generator import generate_brandcut
from .retry_generator import generate_with_validation
from .korean_prompt_builder import (
    build_korean_prompt,
    enhance_with_korean_layer,
    QUALITY_SECTION_TEMPLATE,
    MOMENT_TEMPLATES,
)

# MLB validator (12-criteria 검증)
from .mlb_validator import (
    MLBValidator,
    ValidationResult as MLBValidationResult,
    ENHANCEMENT_RULES,
    QualityTier as MLBQualityTier,
)

# Re-export OutfitAnalysis for external type hints
from core.outfit_analyzer import OutfitAnalysis

__all__ = [
    # Analyzer functions
    "analyze_outfit",
    "analyze_pose_expression",
    "analyze_mood",
    # Prompt builder functions
    "build_prompt",
    "validate_and_fix_combinations",
    # Korean prompt builder (품질 향상)
    "build_korean_prompt",
    "enhance_with_korean_layer",
    "QUALITY_SECTION_TEMPLATE",
    "MOMENT_TEMPLATES",
    # Generator functions
    "generate_brandcut",
    "generate_with_validation",
    # MLB Validator (12-criteria 검증)
    "MLBValidator",
    "MLBValidationResult",
    "ENHANCEMENT_RULES",
    "MLBQualityTier",
    # Type exports
    "OutfitAnalysis",
]
