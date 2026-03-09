# core/test_agent/__init__.py
"""
테스트 에이전트 유틸리티 패키지.

테스트 실행 전 db/ 폴더에서 적절한 이미지를 자동으로 선택하는 유틸리티.

Usage:
    from core.test_agent import get_test_images, WorkflowType

    images = get_test_images(WorkflowType.BRANDCUT, model_name="카리나")
    print(images["face"])    # 얼굴 이미지 경로
    print(images["outfit"])  # 착장 이미지 경로 (VLM 자동 분류)
"""

from core.validators import WorkflowType
from core.test_agent.test_utils import (
    # Constants
    MAX_IMAGES,
    DEFAULT_COUNTS,
    VLM_CALL_DELAY,
    DB_ROOT,
    # Types
    ImageSet,
    OutfitCategory,
    # Core functions
    list_images,
    select_images,
    validate_image_count,
    get_model_list,
    get_image_count,
    get_default_counts,
    # VLM classification
    classify_outfit,
    classify_outfit_batch,
    classify_outfit_batch_fallback,
    auto_coordinate,
    get_coordinated_outfit,
    # Workflow-specific
    get_test_images,
    get_brandcut_images,
    get_background_swap_images,
    get_ugc_images,
)

__all__ = [
    # Constants
    "MAX_IMAGES",
    "DEFAULT_COUNTS",
    "VLM_CALL_DELAY",
    "DB_ROOT",
    # Types
    "WorkflowType",
    "ImageSet",
    "OutfitCategory",
    # Core functions
    "list_images",
    "select_images",
    "validate_image_count",
    "get_model_list",
    "get_image_count",
    "get_default_counts",
    # VLM classification
    "classify_outfit",
    "classify_outfit_batch",
    "classify_outfit_batch_fallback",
    "auto_coordinate",
    "get_coordinated_outfit",
    # Workflow-specific
    "get_test_images",
    "get_brandcut_images",
    "get_background_swap_images",
    "get_ugc_images",
]
