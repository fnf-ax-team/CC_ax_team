"""
핏 베리에이션 검증기

색상 보존 auto-fail + 실루엣 정확도 + 소재/디테일/인물 보존 검증.
color_preservation < 70 이면 자동 탈락.
model_preservation < 70 이면 자동 탈락.
material_preservation < 50 이면 자동 탈락.
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
    2. material_preservation (auto-fail < 50)
    3. silhouette_change
    4. logo_preservation
    5. model_preservation (auto-fail < 70)
    """

    workflow_type = WorkflowType.FIT_VARIATION

    config = ValidationConfig(
        pass_total=80,
        weights={
            "color_preservation": 0.30,
            "material_preservation": 0.20,
            "silhouette_change": 0.25,
            "logo_preservation": 0.10,
            "model_preservation": 0.15,
        },
        auto_fail_thresholds={
            "color_preservation": 70,  # 색상 변경되면 auto-fail
            "material_preservation": 50,  # 소재 완전 변경이면 auto-fail
            "model_preservation": 70,  # 다른 사람으로 변경되면 auto-fail
        },
        priority_order=[
            "color_preservation",
            "material_preservation",
            "silhouette_change",
            "logo_preservation",
            "model_preservation",
        ],
        grade_thresholds={"S": 95, "A": 85, "B": 80, "C": 60},
    )

    ENHANCEMENT_RULES = {
        "color_preservation": [
            "CRITICAL: Color must be EXACTLY the same as reference",
            "Do NOT change any color — preserve exact shade and tone",
            "Match wash level and color saturation precisely",
        ],
        "material_preservation": [
            "Material type must match reference exactly (denim stays denim, etc.)",
            "Preserve fabric texture and surface finish",
            "Keep fabric weight and drape characteristics",
        ],
        "silhouette_change": [
            "Silhouette must match target fit description exactly",
            "Check thigh, knee, calf, and hem width against target",
            "Ensure proper leg shape transition",
        ],
        "logo_preservation": [
            "Keep ALL logos in same position and style",
            "Preserve waistband design exactly",
            "Maintain all hardware and brand markings",
        ],
        "model_preservation": [
            "CRITICAL: Person must be EXACTLY the same — same face, build, proportions",
            "Do NOT change pose, stance, or weight distribution",
            "Preserve upper body outfit and background",
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
        """검증 점수 → 결과 변환

        새 JSON 스키마: {"key": {"score": int, "reason": str}, ...}
        이전 스키마(평탄 구조)도 호환 처리.
        """

        # 새 중첩 스키마와 구 평탄 스키마 모두 지원
        def _get_score(key: str) -> int:
            val = scores.get(key, 0)
            if isinstance(val, dict):
                return int(val.get("score", 0))
            return int(val)

        def _get_reason(key: str) -> str:
            val = scores.get(key, {})
            if isinstance(val, dict):
                return val.get("reason", "")
            # 구 스키마: {key}_reason 패턴
            return scores.get(f"{key}_reason", "")

        criteria = {key: _get_score(key) for key in self.config.priority_order}

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

        # 프롬프트 수준 auto_fail 필드도 확인
        if scores.get("auto_fail", False):
            auto_fail = True
            reason_text = scores.get("auto_fail_reason", "")
            if reason_text and reason_text not in auto_fail_reasons:
                auto_fail_reasons.append(reason_text)

        # 등급 결정
        if auto_fail:
            grade = "F"
            tier = QualityTier.REGENERATE
            passed = False
        else:
            grade, tier = self._calculate_grade(total)
            passed = grade in ("S", "A", "B")

        # 이슈 수집
        issues = list(scores.get("issues", []))
        for key in self.config.priority_order:
            reason = _get_reason(key)
            if reason and criteria.get(key, 0) < 80:
                issue_line = f"{key}: {reason}"
                if issue_line not in issues:
                    issues.append(issue_line)

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
                    "reason": _get_reason(key),
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
