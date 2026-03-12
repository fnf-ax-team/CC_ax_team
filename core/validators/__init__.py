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

# 검증기 자동 등록 (eager import)
# 각 모듈의 @ValidatorRegistry.register 데코레이터가 import 시점에 실행됨
_VALIDATOR_MODULES = [
    "core.background_swap.validator",
    "core.ai_influencer.validator",
    "core.selfie.validator",
    "core.seeding_ugc.validator",
    "core.face_swap.validator",
    "core.outfit_swap.validator",
    "core.multi_face_swap.validator",
    "core.pose_change.validator",
    "core.pose_copy.validator",
    "core.fit_variation.validator",
    "core.ecommerce.validator",
    "core.upscale.validator",
    "core.brandcut.validator_v2",
]

import importlib as _importlib

for _mod in _VALIDATOR_MODULES:
    try:
        _importlib.import_module(_mod)
    except (ImportError, ModuleNotFoundError):
        pass  # 미구현 모듈은 무시

__all__ = [
    "WorkflowType",
    "QualityTier",
    "ValidationConfig",
    "CommonValidationResult",
    "WorkflowValidator",
    "ValidatorRegistry",
]
