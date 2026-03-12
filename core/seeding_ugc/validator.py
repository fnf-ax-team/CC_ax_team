"""
시딩 UGC 검증기 - 리얼리즘 + 역검증 (너무 완벽하면 실패)

SelfieValidator를 래핑하여 WorkflowValidator 인터페이스 구현.
기존 5개 검증 기준과 "너무 완벽" 페널티 로직을 그대로 사용.

핵심 원칙: "너무 잘 나오면 실패"
- 진짜 UGC 사진은 약간의 결점이 있다
- 너무 완벽한 사진은 AI스럽게 보인다
- 폰카 특유의 왜곡/노이즈/압축 아티팩트 필수

우선순위:
1. 리얼리즘 (realism)
2. 인물 보존 (person_preservation)
3. 피부 상태 (skin_condition)
4. 시나리오 적합성 (scenario_fit)
5. 역검증 (anti_polish_factor)
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
    WorkflowValidator,
    WorkflowType,
    CommonValidationResult,
    ValidationConfig,
    QualityTier,
)
from core.validators.registry import ValidatorRegistry


@ValidatorRegistry.register(WorkflowType.UGC)
class UGCValidator(WorkflowValidator):
    """시딩 UGC 검증기 - 리얼리즘 + 역검증(너무 완벽하면 실패)

    SelfieValidator를 래핑하여 통합 인터페이스 제공.
    "너무 잘 나오면 실패" 원칙을 반영.

    Attributes:
        workflow_type: UGC
        config: UGC 전용 검증 설정
    """

    workflow_type = WorkflowType.UGC

    # UGC 우선순위: 리얼리즘 > 인물 > 시나리오 > 상품노출 > 피부 > 역검증
    config = ValidationConfig(
        pass_total=75,
        weights={
            "realism": 0.30,
            "person_preservation": 0.25,
            "scenario_fit": 0.20,
            "skin_condition": 0.15,
            "anti_polish_factor": 0.10,
            # product_visibility 제거: VLM 프롬프트에 해당 항목 없어 항상 0점 반환
        },
        auto_fail_thresholds={
            "realism": 40,
            "person_preservation": 50,
            "skin_condition": 40,
        },
        priority_order=[
            "realism",
            "person_preservation",
            "scenario_fit",
            "skin_condition",
            "anti_polish_factor",
        ],
    )

    # UGC 전용 강화 규칙 - "너무 완벽" 방지 + 상품 자연스러운 노출
    ENHANCEMENT_RULES = {
        "realism": [
            "Must look like REAL smartphone photo, NOT studio shot",
            "Natural imperfections allowed (slight blur, uneven lighting)",
            "NO airbrushed perfection - this is UGC, not editorial",
            "Avoid perfect symmetry and composition",
            "Add natural barrel distortion from wide-angle selfie lens",
            "Include slight JPEG compression artifacts",
        ],
        "person_preservation": [
            "Face must match reference EXACTLY - same person",
            "Preserve unique facial features and characteristics",
            "Maintain natural skin texture from reference",
        ],
        "scenario_fit": [
            "Setting must match UGC context naturally",
            "Clothing and environment must be coherent",
            "Avoid overly styled or curated looks",
            "Expression appropriate for scenario",
        ],
        "product_visibility": [
            "Product should be naturally visible, NOT prominently displayed",
            "NO product logo close-ups or unnatural focus on brand",
            "Product placement should feel incidental, not intentional",
            "Avoid holding product toward camera or pointing at it",
            "Product in background or casually held is ideal",
            "If wearing product, it should not dominate the frame",
        ],
        "skin_condition": [
            "Natural skin texture with pores visible",
            "NO plastic/waxy skin appearance",
            "Avoid over-smoothing or airbrushing",
            "Allow natural imperfections (small blemishes OK)",
            "Show requested skin state (oily, dry, etc.)",
        ],
        "anti_polish_factor": [
            "Add natural imperfections: stray hairs, slight shadows",
            "Avoid perfect studio lighting - use natural/ambient light",
            "UGC aesthetic - NOT editorial/magazine quality",
            "Some blur, slight noise, uneven lighting is GOOD",
            "NO ring light catchlight in eyes",
            "NO perfect centered composition",
        ],
    }

    # UGC 전용 Auto-Fail 조건
    UGC_AUTO_FAIL_CONDITIONS = [
        "studio_background",  # 스튜디오 배경
        "professional_pose",  # 전문 모델 포즈
        "product_closeup",  # 상품 로고 클로즈업
        "advertisement_text",  # 명백한 광고 문구
    ]

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
        **kwargs,
    ) -> CommonValidationResult:
        """UGC 이미지 검증

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

        # "너무 완벽" 페널티 반영
        # too_polished_penalty=True이면 anti_polish_factor를 50점으로 (감점)
        anti_polish = 100 if not result.too_polished_penalty else 50

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
                "anti_polish_factor": anti_polish,
            },
            summary_kr=result.summary_kr,
            raw_response=result.raw_response,
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """UGC 프롬프트 강화 규칙

        실패한 기준에 따라 우선순위 순서로 강화 규칙 반환.
        UGC 특성상 "너무 완벽" 방지에 초점.

        Args:
            failed_criteria: 실패한 기준 목록

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트
        """
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        # 최대 10개 규칙으로 제한 (UGC는 간결하게)
        return "\n".join([f"- {line}" for line in lines[:10]])
