"""
핏 베리에이션 검증기

색상 보존 auto-fail + 실루엣 정확도 + 소재/디테일 보존 검증.
color_preservation < 70 이면 자동 탈락.
"""

import json
from io import BytesIO
from typing import List, Dict, Union, Optional
from pathlib import Path

from PIL import Image
from google.genai import types

from core.config import VISION_MODEL
from core.validators.base import (
    WorkflowValidator,
    WorkflowType,
    CommonValidationResult,
    ValidationConfig,
    QualityTier,
)
from core.validators.registry import ValidatorRegistry
from .templates import FIT_VALIDATION_PROMPT


@ValidatorRegistry.register(WorkflowType.FIT_VARIATION)
class FitVariationValidator(WorkflowValidator):
    """핏 베리에이션 검증기

    우선순위:
    1. color_preservation (auto-fail < 70)
    2. silhouette_accuracy
    3. material_fidelity
    4. detail_preservation
    5. overall_quality
    """

    workflow_type = WorkflowType.FIT_VARIATION

    config = ValidationConfig(
        pass_total=80,
        weights={
            "color_preservation": 0.30,
            "silhouette_accuracy": 0.25,
            "material_fidelity": 0.20,
            "detail_preservation": 0.15,
            "overall_quality": 0.10,
        },
        auto_fail_thresholds={
            "color_preservation": 70,  # 색상 변경되면 auto-fail
        },
        priority_order=[
            "color_preservation",
            "silhouette_accuracy",
            "material_fidelity",
            "detail_preservation",
            "overall_quality",
        ],
    )

    ENHANCEMENT_RULES = {
        "color_preservation": [
            "CRITICAL: Color must be EXACTLY the same as reference",
            "Do NOT change any color — preserve exact shade and tone",
            "Match wash level and color saturation precisely",
        ],
        "silhouette_accuracy": [
            "Silhouette must match target fit description exactly",
            "Check thigh, knee, calf, and hem width against target",
            "Ensure proper leg shape transition",
        ],
        "material_fidelity": [
            "Material texture must match reference exactly",
            "Preserve fabric weight and drape characteristics",
            "Keep surface finish (matte/shiny/coated) the same",
        ],
        "detail_preservation": [
            "Keep ALL pockets in same position and style",
            "Preserve waistband design exactly",
            "Keep stitching color and pattern",
            "Maintain all logos and hardware",
        ],
        "overall_quality": [
            "Clean, professional product photography",
            "No artifacts or distortions",
            "Natural fabric drape for the target fit",
        ],
    }

    def __init__(self, client):
        super().__init__(client)

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """핏 베리에이션 검증

        Args:
            generated_img: 생성된 이미지
            reference_images: {"pants": [원본 바지 이미지]}
            **kwargs:
                target_fit: 목표 핏 이름 (예: "wide")

        Returns:
            CommonValidationResult
        """
        target_fit = kwargs.get("target_fit", "unknown")

        # 이미지 로드
        gen_img = self._load_image(generated_img)
        ref_imgs = self._load_images(reference_images.get("pants", []))

        if not ref_imgs:
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=["No reference pants image provided"],
                summary_kr="참조 바지 이미지 없음",
            )

        # VLM 검증 프롬프트 (target_fit 주입)
        prompt = FIT_VALIDATION_PROMPT.replace("{target_fit}", target_fit)

        # API 파트 구성: 텍스트 + 원본(ref) + 생성(gen)
        parts = [
            types.Part(text=prompt),
            self._pil_to_part(ref_imgs[0]),  # IMAGE 1: 원본
            self._pil_to_part(gen_img),  # IMAGE 2: 생성 결과
        ]

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            scores = json.loads(result_text)

        except Exception as e:
            print(f"[FitVariationValidator] API error: {e}")
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=[f"Validation API error: {e}"],
                summary_kr=f"검증 API 오류: {e}",
            )

        return self._build_result(scores, target_fit)

    def _build_result(self, scores: Dict, target_fit: str) -> CommonValidationResult:
        """검증 점수 → 결과 변환"""
        criteria = {}
        for key in self.config.priority_order:
            criteria[key] = scores.get(key, 0)

        # 가중 총점
        total = 0
        for key, weight in self.config.weights.items():
            total += criteria.get(key, 0) * weight
        total = round(total)

        # Auto-fail 체크
        auto_fail = False
        auto_fail_reasons = []
        for key, threshold in self.config.auto_fail_thresholds.items():
            if criteria.get(key, 0) < threshold:
                auto_fail = True
                auto_fail_reasons.append(f"{key}: {criteria.get(key, 0)} < {threshold}")

        # 등급 결정
        if auto_fail:
            grade = "F"
            tier = QualityTier.REGENERATE
            passed = False
        elif total >= 95:
            grade = "S"
            tier = QualityTier.RELEASE_READY
            passed = True
        elif total >= 85:
            grade = "A"
            tier = QualityTier.RELEASE_READY
            passed = True
        elif total >= self.config.pass_total:
            grade = "B"
            tier = QualityTier.NEEDS_MINOR_EDIT
            passed = True
        elif total >= 60:
            grade = "C"
            tier = QualityTier.REGENERATE
            passed = False
        else:
            grade = "F"
            tier = QualityTier.REGENERATE
            passed = False

        # 이슈 수집
        issues = []
        for key in self.config.priority_order:
            reason_key = f"{key}_reason"
            if reason_key in scores and scores[reason_key]:
                if criteria.get(key, 0) < 80:
                    issues.append(f"{key}: {scores[reason_key]}")

        # 한국어 요약
        summary_parts = [f"목표 핏: {target_fit}"]
        summary_parts.append(f"총점: {total}/100 ({grade})")
        if auto_fail:
            summary_parts.append(f"자동 탈락: {', '.join(auto_fail_reasons)}")
        summary_kr = " | ".join(summary_parts)

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=total,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            criteria_scores={
                key: {
                    "score": criteria.get(key, 0),
                    "reason": scores.get(f"{key}_reason", ""),
                }
                for key in self.config.priority_order
            },
            summary_kr=summary_kr,
            raw_response=json.dumps(scores, ensure_ascii=False),
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 강화 규칙"""
        rules = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                rules.extend(self.ENHANCEMENT_RULES[criterion])
        return "\n".join([f"- {r}" for r in rules[:8]])

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )
