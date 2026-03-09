"""
FNF Studio 검증기 레지스트리

워크플로 타입별 검증기를 등록하고 관리합니다.
"""

from typing import Dict, List, Type

from .base import WorkflowType, WorkflowValidator


class ValidatorRegistry:
    """검증기 레지스트리 - 워크플로 타입별 검증기 관리

    Usage:
        # 검증기 등록
        @ValidatorRegistry.register(WorkflowType.BACKGROUND_SWAP)
        class BackgroundSwapWorkflowValidator(WorkflowValidator):
            ...

        # 검증기 가져오기
        validator = ValidatorRegistry.get(WorkflowType.BACKGROUND_SWAP, client)
    """

    _validators: Dict[WorkflowType, Type[WorkflowValidator]] = {}

    @classmethod
    def register(cls, workflow_type: WorkflowType):
        """데코레이터로 검증기 등록

        Args:
            workflow_type: 워크플로 타입

        Returns:
            데코레이터 함수

        Usage:
            @ValidatorRegistry.register(WorkflowType.BACKGROUND_SWAP)
            class BackgroundSwapWorkflowValidator(WorkflowValidator):
                ...
        """

        def decorator(validator_cls: Type[WorkflowValidator]):
            cls._validators[workflow_type] = validator_cls
            return validator_cls

        return decorator

    @classmethod
    def get(cls, workflow_type: WorkflowType, client) -> WorkflowValidator:
        """검증기 인스턴스 반환

        Args:
            workflow_type: 워크플로 타입
            client: Gemini API 클라이언트

        Returns:
            검증기 인스턴스

        Raises:
            KeyError: 등록되지 않은 워크플로 타입
        """
        if workflow_type not in cls._validators:
            registered = [wt.value for wt in cls._validators.keys()]
            raise KeyError(
                f"Validator not registered for {workflow_type.value}. "
                f"Registered validators: {registered}"
            )
        return cls._validators[workflow_type](client)

    @classmethod
    def list_registered(cls) -> List[WorkflowType]:
        """등록된 워크플로 타입 목록 반환

        Returns:
            등록된 WorkflowType 리스트
        """
        return list(cls._validators.keys())

    @classmethod
    def is_registered(cls, workflow_type: WorkflowType) -> bool:
        """워크플로 타입이 등록되어 있는지 확인

        Args:
            workflow_type: 워크플로 타입

        Returns:
            등록 여부
        """
        return workflow_type in cls._validators

    @classmethod
    def clear(cls) -> None:
        """레지스트리 초기화 (테스트용)"""
        cls._validators.clear()
