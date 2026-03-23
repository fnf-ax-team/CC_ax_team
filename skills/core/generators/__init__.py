"""
통합 이미지 생성 모듈

워크플로별 검증을 포함한 이미지 생성 함수를 제공한다.

사용법:
    from core.generators import generate_with_workflow_validation
    from core.validators import WorkflowType

    result = generate_with_workflow_validation(
        workflow_type=WorkflowType.BRANDCUT,
        generate_func=my_generate_func,
        prompt=prompt_json,
        reference_images={"face": [...], "outfit": [...]},
        config={"temperature": 0.25},
    )
"""

from .unified import generate_with_workflow_validation

__all__ = [
    "generate_with_workflow_validation",
]
