"""
배경 교체 모듈 - Public API

============================================================
사용법:
    from core.background_swap import swap
    result = swap(source_image, "urban street")
    if result.success:
        result.image.save("output.png")

고급 사용법:
    from core.background_swap import (
        swap,
        analyze_model_physics,
        build_background_prompt,
        BatchProcessor,
    )
============================================================
"""

# ============================================================
# 메인 엔트리포인트
# ============================================================
from .generator import (
    swap,
    generate_background_swap,
    generate_with_validation,
    SwapResult,
    BatchResult,
    BatchProcessor,
)

# ============================================================
# 분석 함수 (VFX + 기존)
# ============================================================
from .analyzer import (
    # Re-exported from core.background_analyzer
    analyze_background,
    analyze_for_background_swap,
    build_swap_instructions,
    # New functions
    analyze_model_physics,
    build_background_guideline,
    detect_source_type,
)

# ============================================================
# 프롬프트 빌더
# ============================================================
from .prompt_builder import (
    build_background_prompt,
    build_reference_prompt,
    build_one_unit_instructions,
    build_vehicle_instructions,
    build_ground_instructions,
    build_color_matching_instructions,
    build_swap_analysis_instructions,
)

# ============================================================
# 템플릿 & 프리셋
# ============================================================
from .templates import (
    VFX_ANALYSIS_PROMPT,
    SOURCE_TYPE_PROMPT,
    BASE_PRESERVATION_PROMPT,
    ONE_UNIT_PROMPTS,
    REFERENCE_PROMPTS,
    VFX_JSON_SCHEMA,
)

from .presets import (
    CONCRETE_STYLES,
    CITY_STYLES,
    STUDIO_STYLES,
    get_style_preset,
    list_all_styles,
)

# ============================================================
# 유틸리티 (core.utils에서 re-export)
# ============================================================
from core.utils import pil_to_part

# ============================================================
# 검증기 (WorkflowValidator 인터페이스)
# ============================================================
from .workflow_validator import BackgroundSwapWorkflowValidator

# 검증기 (로컬 모듈에서 import - 9-criteria)
from .validator import (
    BackgroundSwapValidator,
    BackgroundSwapValidationResult,
    validate_result,
    get_validator,
    ENHANCEMENT_RULES,
)


__all__ = [
    # 메인 엔트리포인트
    "swap",
    "generate_background_swap",
    "generate_with_validation",
    "SwapResult",
    "BatchResult",
    "BatchProcessor",
    # 분석 함수
    "analyze_background",
    "analyze_for_background_swap",
    "build_swap_instructions",
    "analyze_model_physics",
    "build_background_guideline",
    "detect_source_type",
    # 프롬프트 빌더
    "build_background_prompt",
    "build_reference_prompt",
    "build_one_unit_instructions",
    "build_vehicle_instructions",
    "build_ground_instructions",
    "build_color_matching_instructions",
    "build_swap_analysis_instructions",
    # 템플릿 & 프리셋
    "VFX_ANALYSIS_PROMPT",
    "SOURCE_TYPE_PROMPT",
    "BASE_PRESERVATION_PROMPT",
    "ONE_UNIT_PROMPTS",
    "REFERENCE_PROMPTS",
    "VFX_JSON_SCHEMA",
    "CONCRETE_STYLES",
    "CITY_STYLES",
    "STUDIO_STYLES",
    "get_style_preset",
    "list_all_styles",
    # 유틸리티
    "pil_to_part",
    # 워크플로 검증기 (ValidatorRegistry 인터페이스)
    "BackgroundSwapWorkflowValidator",
    # 검증기 (9-criteria)
    "BackgroundSwapValidator",
    "BackgroundSwapValidationResult",
    "validate_result",
    "ENHANCEMENT_RULES",
]
