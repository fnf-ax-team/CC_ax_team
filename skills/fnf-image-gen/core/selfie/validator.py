"""
셀피 검증기 - 리얼리즘 + 자연스러움

SelfieValidator를 래핑하여 WorkflowValidator 인터페이스 구현.
기존 5개 검증 기준을 사용하되, UGC보다는 약간 덜 엄격한 기준 적용.

우선순위:
1. 리얼리즘 (realism)
2. 인물 보존 (person_preservation)
3. 피부 상태 (skin_condition)
4. 시나리오 적합성 (scenario_fit)
5. 자연스러움 (natural_feel)
"""

from typing import List, Dict, Union
from pathlib import Path
from PIL import Image

from core.selfie_validator import (
    SelfieValidator,
    SelfieValidationResult,
    SelfieQualityTier,
)
from core.validators.base import (
    WorkflowValidator, WorkflowType, CommonValidationResult,
    ValidationConfig, QualityTier
)
from core.validators.registry import ValidatorRegistry


@ValidatorRegistry.register(WorkflowType.SELFIE)
class SelfieWorkflowValidator(WorkflowValidator):
    """셀피 검증기 - 리얼리즘 + 자연스러움

    SelfieValidator를 래핑하여 통합 인터페이스 제공.
    UGC보다는 약간 덜 엄격하지만, 자연스러움은 유지.

    Attributes:
        workflow_type: SELFIE
        config: 셀피 전용 검증 설정
    """

    workflow_type = WorkflowType.SELFIE

    # 셀피 우선순위: 리얼리즘 > 인물 > 피부 > 시나리오 > 자연스러움
    config = ValidationConfig(
        pass_total=80,  # UGC(75)보다 약간 높음
        weights={
            "realism": 0.30,
            "person_preservation": 0.30,  # 인물 보존 더 중요
            "scenario_fit": 0.15,
            "skin_condition": 0.15,
            "natural_feel": 0.10,
        },
        auto_fail_thresholds={
            "realism": 50,
            "person_preservation": 60,
            "skin_condition": 50,
        },
        priority_order=[
            "realism",
            "person_preservation",
            "skin_condition",
            "scenario_fit",
            "natural_feel",
        ]
    )

    # 셀피 전용 강화 규칙
    ENHANCEMENT_RULES = {
        "realism": [
            "Must look like REAL smartphone selfie",
            "Natural lighting preferred over studio",
            "Avoid overly processed/filtered look",
            "Natural framing and composition",
        ],
        "person_preservation": [
            "Face must match reference EXACTLY - same person",
            "Preserve unique facial features and characteristics",
            "Maintain natural skin texture from reference",
            "Keep consistent face proportions",
        ],
        "skin_condition": [
            "Natural skin texture with pores visible",
            "NO plastic/waxy skin appearance",
            "Avoid over-smoothing or airbrushing",
            "Allow natural imperfections",
        ],
        "scenario_fit": [
            "Setting must match selfie context naturally",
            "Clothing and environment must be coherent",
            "Expression appropriate for selfie mood",
        ],
        "natural_feel": [
            "Natural, casual selfie aesthetic",
            "Avoid perfect studio composition",
            "Natural lighting variations OK",
            "Authentic, relatable feel",
        ],
    }

    def __init__(self, client):
        """
        Args:
            client: Initialized Gemini API client (google.genai.Client)
        """
        super().__init__(client)
        self._selfie_validator = SelfieValidator(client)

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs
    ) -> CommonValidationResult:
        """셀피 이미지 검증

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "face": 얼굴 이미지 목록 (필수)
                - "outfit": 착장 이미지 목록 (선택)
            **kwargs: 추가 옵션
                - scenario_options: 시나리오 옵션 (장소, 분위기 등)

        Returns:
            CommonValidationResult: 공통 검증 결과
        """
        # SelfieValidator 호출
        result: SelfieValidationResult = self._selfie_validator.validate(
            generated_img=generated_img,
            face_images=reference_images.get("face", []),
            outfit_images=reference_images.get("outfit", []),
            scenario_options=kwargs.get("scenario_options"),
        )

        # SelfieQualityTier → QualityTier 변환
        tier_map = {
            SelfieQualityTier.RELEASE_READY: QualityTier.RELEASE_READY,
            SelfieQualityTier.NEEDS_MINOR_EDIT: QualityTier.NEEDS_MINOR_EDIT,
            SelfieQualityTier.REGENERATE: QualityTier.REGENERATE,
        }

        # natural_feel은 anti_polish의 역수 개념 (너무 완벽하면 감점)
        natural_feel = 100 if not result.too_polished_penalty else 60

        # CommonValidationResult로 변환
        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=result.total_score,
            tier=tier_map.get(result.tier, QualityTier.REGENERATE),
            grade=result.grade,
            passed=result.passed,
            auto_fail=result.auto_fail,
            auto_fail_reasons=result.auto_fail_reasons,
            issues=result.issues,
            criteria_scores={
                "realism": result.realism,
                "person_preservation": result.person_preservation,
                "scenario_fit": result.scenario_fit,
                "skin_condition": result.skin_condition,
                "natural_feel": natural_feel,
            },
            summary_kr=result.summary_kr,
            raw_response=result.raw_response,
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """셀피 프롬프트 강화 규칙

        실패한 기준에 따라 우선순위 순서로 강화 규칙 반환.

        Args:
            failed_criteria: 실패한 기준 목록

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트
        """
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        # 최대 8개 규칙으로 제한
        return "\n".join([f"- {line}" for line in lines[:8]])
