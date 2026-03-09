"""
셀피/인플루언서 스타일 이미지 생성 모듈

Usage (v2 - 기존):
    from core.selfie import (
        analyze_face,
        build_selfie_prompt,
        generate_selfie,
        generate_with_validation,
    )

Usage (v3 - DB 기반):
    from core.selfie import (
        # DB 로더
        get_pose_categories,
        get_scene_categories,
        get_poses_by_category,
        get_scenes_by_category,
        get_random_poses,
        get_random_scenes,
        # 호환성
        is_compatible,
        get_compatible_scene_categories,
        get_compatible_scenes,
        # 프롬프트
        build_prompt_from_db,
        # 생성
        generate_selfie_v3,
        generate_batch_v3,
        get_random_combinations,
    )
"""

# Analyzer
from .analyzer import analyze_face, SelfieAnalyzer

# Prompt builder (v2)
from .prompt_builder import build_selfie_prompt, PROMPT_OPTIONS

# Prompt builder (v3 - DB 기반)
from .prompt_builder import (
    build_prompt_from_db,
    build_prompt_from_db_simple,
    get_db_based_negative_prompt,
    EXPRESSION_OPTIONS,
)

# Generator (v2)
from .generator import generate_selfie, generate_with_validation

# Generator (v3 - DB 기반)
from .generator import (
    generate_selfie_v3,
    generate_batch_v3,
    get_random_combinations,
)

# Validator
from .validator import SelfieWorkflowValidator

# Templates
from .templates import FACE_ANALYSIS_PROMPT, OUTFIT_ANALYSIS_PROMPT

# DB Loader (v3)
from .db_loader import (
    get_pose_categories,
    get_scene_categories,
    get_poses_by_category,
    get_scenes_by_category,
    get_pose_by_id,
    get_scene_by_id,
    get_pose_category_info,
    get_scene_category_info,
    get_random_poses,
    get_random_scenes,
    get_scenes_by_tags,
    get_reference_image_path,
    get_category_summary,
    clear_cache,
)

# Compatibility (v3)
from .compatibility import (
    is_compatible,
    get_compatible_scene_categories,
    get_compatible_scenes,
    filter_compatible_combinations,
    validate_combination,
    get_compatibility_summary,
    format_compatibility_for_user,
)


__all__ = [
    # Analyzer
    "analyze_face",
    "SelfieAnalyzer",
    # Prompt builder (v2)
    "build_selfie_prompt",
    "PROMPT_OPTIONS",
    # Prompt builder (v3)
    "build_prompt_from_db",
    "build_prompt_from_db_simple",
    "get_db_based_negative_prompt",
    "EXPRESSION_OPTIONS",
    # Generator (v2)
    "generate_selfie",
    "generate_with_validation",
    # Generator (v3)
    "generate_selfie_v3",
    "generate_batch_v3",
    "get_random_combinations",
    # Validator
    "SelfieWorkflowValidator",
    # Templates
    "FACE_ANALYSIS_PROMPT",
    "OUTFIT_ANALYSIS_PROMPT",
    # DB Loader (v3)
    "get_pose_categories",
    "get_scene_categories",
    "get_poses_by_category",
    "get_scenes_by_category",
    "get_pose_by_id",
    "get_scene_by_id",
    "get_pose_category_info",
    "get_scene_category_info",
    "get_random_poses",
    "get_random_scenes",
    "get_scenes_by_tags",
    "get_reference_image_path",
    "get_category_summary",
    "clear_cache",
    # Compatibility (v3)
    "is_compatible",
    "get_compatible_scene_categories",
    "get_compatible_scenes",
    "filter_compatible_combinations",
    "validate_combination",
    "get_compatibility_summary",
    "format_compatibility_for_user",
]
