"""
Outfit Swap Module

착장만 교체하고 얼굴/포즈/배경을 유지하는 워크플로 모듈

카테고리: 스왑
- 얼굴: 유지
- 착장: 변경
- 포즈: 유지
- 배경: 유지

사용법:
    from core.outfit_swap import generate_with_validation

    # PIL 이미지 직접 사용
    result = generate_with_validation(
        source_image=source_pil,
        outfit_images=[outfit1_pil, outfit2_pil],
        aspect_ratio="3:4",
        max_retries=2,
    )

    if result["passed"]:
        result["image"].save("output.png")
"""

# 분석
from .analyzer import (
    analyze_source,
    analyze_source_from_path,
    analyze_source_for_swap,
    analyze_outfit_items,
    SourceAnalysisResult,
    pil_to_part,
)

# 프롬프트 빌더
from .prompt_builder import (
    build_outfit_swap_prompt,
    build_prompt_from_dict,
)

# 비율 자동 감지
from core.options import detect_aspect_ratio

# 생성
from .generator import (
    generate_outfit_swap,
    generate_with_validation,
    MAX_OUTFIT_IMAGES,
)

# 검증 (WorkflowValidator 기반 새 인터페이스)
from .validator import (
    OutfitSwapValidator,
    WEIGHTS as VALIDATION_WEIGHTS,
    THRESHOLDS,
    AUTO_FAIL_THRESHOLDS,
    CRITERION_NAMES_KR,
    ENHANCEMENT_RULES,
    PASS_TOTAL as PASS_THRESHOLD,
)

# 템플릿
from .templates import (
    SOURCE_ANALYSIS_PROMPT,
    OUTFIT_ANALYSIS_PROMPT,
    OUTFIT_SWAP_PROMPT_TEMPLATE,
    VALIDATION_PROMPT,
    build_outfit_swap_prompt as build_outfit_swap_prompt_from_analysis,
)


__all__ = [
    # 생성 함수 (주요 API)
    "generate_outfit_swap",
    "generate_with_validation",
    # 분석
    "analyze_source",
    "analyze_source_from_path",
    "analyze_source_for_swap",
    "analyze_outfit_items",
    "SourceAnalysisResult",
    "pil_to_part",
    # 프롬프트 빌더
    "build_outfit_swap_prompt",
    "build_prompt_from_dict",
    # 비율 자동 감지
    "detect_aspect_ratio",
    # 생성 설정
    "MAX_OUTFIT_IMAGES",
    # 검증
    "OutfitSwapValidator",
    "VALIDATION_WEIGHTS",
    "THRESHOLDS",
    "AUTO_FAIL_THRESHOLDS",
    "CRITERION_NAMES_KR",
    "ENHANCEMENT_RULES",
    "PASS_THRESHOLD",
    # 템플릿 (선택사항)
    "SOURCE_ANALYSIS_PROMPT",
    "OUTFIT_ANALYSIS_PROMPT",
    "OUTFIT_SWAP_PROMPT_TEMPLATE",
    "VALIDATION_PROMPT",
    "build_outfit_swap_prompt_from_analysis",
]
