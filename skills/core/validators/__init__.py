"""
FNF Studio 통합 검증기 모듈

Usage:
    from core.validators import WorkflowType, ValidatorRegistry, QualityTier

    # 검증기 가져오기
    validator = ValidatorRegistry.get(WorkflowType.BACKGROUND_SWAP, client)
    result = validator.validate(generated_img, reference_images)
"""

from .base import (
    WorkflowType,
    QualityTier,
    ValidationConfig,
    CommonValidationResult,
    WorkflowValidator,
)
from .registry import ValidatorRegistry

# Note: Workflow validators are registered via @ValidatorRegistry.register decorator
# when their respective modules are imported. Import from workflow modules directly:
#   from core.face_swap import FaceSwapValidator
#   from core.outfit_swap import OutfitSwapValidator
#   from core.ai_influencer.validator import AIInfluencerWorkflowValidator
#   etc.
#
# Or use ValidatorRegistry.get(WorkflowType.FACE_SWAP, client) after importing the workflow module.
# For AI_INFLUENCER: import core.ai_influencer.validator to trigger registration.

__all__ = [
    "WorkflowType",
    "QualityTier",
    "ValidationConfig",
    "CommonValidationResult",
    "WorkflowValidator",
    "ValidatorRegistry",
]
