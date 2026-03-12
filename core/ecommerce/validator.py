"""
이커머스 검증기

EcommerceValidator - 착장 정확도 최우선 + 중립 배경 필수

검증 기준 (5개):
- outfit_accuracy:       40%, >= 85 (최우선 - 착장 색상/로고/디테일)
- face_identity:         20%, >= 70 (이커머스 완화 기준, 브랜드컷보다 낮음)
- background_compliance: 15%, >= 90 (중립 배경 필수)
- pose_correctness:      15%, >= 80
- commercial_quality:    10%, >= 85

Pass 조건:
- 위 5개 기준 모두 통과 AND total_score >= 85

총점 계산:
total_score = outfit_accuracy * 0.40 + face_identity * 0.20
            + background_compliance * 0.15 + pose_correctness * 0.15
            + commercial_quality * 0.10
"""

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Union

from PIL import Image
from google.genai import types

from core.config import VISION_MODEL
from core.validators.base import (
    CommonValidationResult,
    QualityTier,
    ValidationConfig,
    WorkflowType,
    WorkflowValidator,
)
from core.validators.registry import ValidatorRegistry

from .templates import VALIDATION_PROMPT


@ValidatorRegistry.register(WorkflowType.ECOMMERCE)
class EcommerceValidator(WorkflowValidator):
    """이커머스 검증기 - 착장 정확도 최우선

    이커머스 모델 이미지의 핵심 요구사항:
    1. 착장을 정확히 보여줄 것 (색상, 로고, 디테일 완벽 재현)
    2. 클린한 중립 배경 (브랜드 특화 배경 금지)
    3. 상업적 품질 (프로페셔널 조명, 포즈)
    4. 얼굴 동일성 (브랜드컷보다 완화된 기준)

    Attributes:
        workflow_type: ECOMMERCE
        config: 이커머스 전용 검증 설정
    """

    workflow_type = WorkflowType.ECOMMERCE

    # 이커머스 검증 설정
    config = ValidationConfig(
        pass_total=85,
        weights={
            "outfit_accuracy": 0.40,  # 최우선 - 착장 정확도
            "face_identity": 0.20,  # 완화 기준 (브랜드컷 < 이커머스)
            "background_compliance": 0.15,  # 중립 배경 필수
            "pose_correctness": 0.15,  # 포즈 정확도
            "commercial_quality": 0.10,  # 상업적 완성도
        },
        auto_fail_thresholds={
            "outfit_accuracy": 70,  # 착장 심각 불일치 → 즉시 재생성
            "face_identity": 40,  # 완전히 다른 사람 → 즉시 재생성
            "background_compliance": 60,  # 부적절한 배경 → 즉시 재생성
        },
        priority_order=[
            "outfit_accuracy",
            "face_identity",
            "background_compliance",
            "pose_correctness",
            "commercial_quality",
        ],
        grade_thresholds={"S": 95, "A": 85, "B": 78, "C": 70},
    )

    # 개별 기준 Pass 임계값
    PASS_THRESHOLDS = {
        "outfit_accuracy": 85,
        "face_identity": 70,
        "background_compliance": 90,
        "pose_correctness": 80,
        "commercial_quality": 85,
    }

    # 재생성 프롬프트 강화 규칙
    ENHANCEMENT_RULES = {
        "outfit_accuracy": [
            "ULTRA CRITICAL: Copy ALL outfit elements from reference images pixel-perfect",
            "Do NOT change any color of any clothing item",
            "Include EVERY logo, graphic, text exactly as shown",
            "Preserve all silhouette details (cropped, balloon, oversized, etc.)",
            "Include ALL accessories and layering items without omission",
        ],
        "face_identity": [
            "Face must closely resemble the provided face reference image",
            "Preserve facial features, proportions, and skin tone",
            "Avoid over-smoothing or changing face shape",
        ],
        "background_compliance": [
            "Use ONLY neutral backgrounds: white studio, gray studio, minimal indoor, or outdoor urban",
            "NO brand-specific conceptual backgrounds",
            "Professional studio lighting with even illumination",
            "Clean, uncluttered background without props",
        ],
        "pose_correctness": [
            "Match the requested framing exactly (FS=full shot, MS=medium shot)",
            "Match the requested camera angle (front/side/back)",
            "Natural, anatomically correct body positioning",
            "No deformed hands or fingers (5 fingers only)",
        ],
        "commercial_quality": [
            "Professional studio lighting - soft, even, no harsh shadows",
            "Commercial photography aesthetics",
            "Clean, photo-realistic skin without AI plastic appearance",
            "Sharp focus on clothing details",
        ],
    }

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """이커머스 이미지 검증

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "face": 얼굴 이미지 목록 (필수)
                - "outfit": 착장 이미지 목록 (필수 - 최우선 비교 대상)
            **kwargs: 추가 옵션
                - pose_preset: 요청된 포즈 프리셋 키 (str)
                - background_preset: 요청된 배경 프리셋 키 (str)

        Returns:
            CommonValidationResult: 공통 검증 결과
        """
        # 이미지 로드
        gen_img = self._load_image(generated_img)
        face_imgs = self._load_images(reference_images.get("face", []))
        outfit_imgs = self._load_images(reference_images.get("outfit", []))

        pose_preset = kwargs.get("pose_preset", "front_standing")
        background_preset = kwargs.get("background_preset", "white_studio")

        # VLM 검수 수행
        raw_response = self._run_vlm_validation(
            gen_img, face_imgs, outfit_imgs, pose_preset, background_preset
        )

        # 응답 파싱
        parsed = self._parse_response(raw_response)

        # 점수 추출
        criteria_scores = {
            "outfit_accuracy": parsed.get("outfit_accuracy", 0),
            "face_identity": parsed.get("face_identity", 0),
            "background_compliance": parsed.get("background_compliance", 0),
            "pose_correctness": parsed.get("pose_correctness", 0),
            "commercial_quality": parsed.get("commercial_quality", 0),
        }

        # 총점 계산 (가중 평균)
        total_score = int(
            criteria_scores["outfit_accuracy"] * 0.40
            + criteria_scores["face_identity"] * 0.20
            + criteria_scores["background_compliance"] * 0.15
            + criteria_scores["pose_correctness"] * 0.15
            + criteria_scores["commercial_quality"] * 0.10
        )

        # Auto-Fail 판정
        auto_fail = parsed.get("auto_fail", False)
        auto_fail_reasons = []
        if auto_fail:
            reason = parsed.get("auto_fail_reason", "")
            if reason:
                auto_fail_reasons.append(reason)

        # 개별 기준 임계값 Auto-Fail 추가 검사
        for criterion, threshold in self.config.auto_fail_thresholds.items():
            score = criteria_scores.get(criterion, 0)
            if score < threshold:
                auto_fail = True
                auto_fail_reasons.append(
                    f"{criterion} 점수 {score} < Auto-Fail 기준 {threshold}"
                )

        # Pass 판정: 5개 기준 모두 통과 AND 총점 >= 85 AND auto_fail == False
        criteria_passed = all(
            criteria_scores.get(k, 0) >= v for k, v in self.PASS_THRESHOLDS.items()
        )
        passed = (
            not auto_fail and criteria_passed and total_score >= self.config.pass_total
        )

        # 이슈 수집
        issues = list(parsed.get("issues", []))
        for criterion, threshold in self.PASS_THRESHOLDS.items():
            score = criteria_scores.get(criterion, 0)
            if score < threshold:
                issues.append(f"{criterion}: {score}점 (기준 {threshold}점 미달)")

        # 등급 및 Tier 결정
        if auto_fail:
            grade, tier = "F", QualityTier.REGENERATE
        else:
            grade, tier = self._calculate_grade(total_score)

        # 한국어 요약
        summary_kr = self._build_summary_kr(
            criteria_scores, total_score, grade, passed, auto_fail_reasons, issues
        )

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            criteria_scores=criteria_scores,
            summary_kr=summary_kr,
            raw_response=raw_response,
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 프롬프트 강화 규칙 반환

        우선순위 순서(priority_order)에 따라 강화 규칙을 최대 8개 반환.

        Args:
            failed_criteria: 실패한 검증 기준 목록

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트
        """
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        return "\n".join([f"- {line}" for line in lines[:8]])

    # ------------------------------------------------------------------
    # 내부 헬퍼 메서드
    # ------------------------------------------------------------------

    def _run_vlm_validation(
        self,
        gen_img: Image.Image,
        face_imgs: List[Image.Image],
        outfit_imgs: List[Image.Image],
        pose_preset: str,
        background_preset: str,
    ) -> str:
        """VLM 검수 실행

        Args:
            gen_img: 생성된 이미지
            face_imgs: 얼굴 참조 이미지 목록
            outfit_imgs: 착장 참조 이미지 목록
            pose_preset: 요청된 포즈 프리셋 키
            background_preset: 요청된 배경 프리셋 키

        Returns:
            str: VLM 응답 텍스트
        """
        # 검수 프롬프트에 포즈/배경 프리셋 정보 추가
        prompt_text = (
            VALIDATION_PROMPT
            + f"\n\n## 요청 포즈 프리셋: {pose_preset}"
            + f"\n## 요청 배경 프리셋: {background_preset}"
        )

        # API 파트 구성
        parts = [types.Part(text=prompt_text)]

        # 생성된 이미지 [GENERATED IMAGE]
        parts.append(types.Part(text="[GENERATED IMAGE] - 검수 대상 이미지:"))
        parts.append(self._pil_to_part(gen_img))

        # 얼굴 참조 이미지
        for i, img in enumerate(face_imgs):
            parts.append(types.Part(text=f"[FACE REFERENCE {i+1}] - 얼굴 참조:"))
            parts.append(self._pil_to_part(img))

        # 착장 참조 이미지 (최우선 비교 대상)
        for i, img in enumerate(outfit_imgs):
            parts.append(
                types.Part(
                    text=f"[OUTFIT REFERENCE {i+1}] - 착장 참조 (최우선 비교 대상):"
                )
            )
            parts.append(self._pil_to_part(img))

        # VLM 호출
        response = self.client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=parts)],
        )

        return response.candidates[0].content.parts[0].text

    def _parse_response(self, raw_response: str) -> dict:
        """VLM 응답에서 JSON 파싱

        Args:
            raw_response: VLM 응답 텍스트

        Returns:
            dict: 파싱된 결과 (파싱 실패 시 빈 dict)
        """
        # JSON 블록 추출 시도
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not json_match:
            return {}

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return {}

    def _build_summary_kr(
        self,
        criteria_scores: dict,
        total_score: int,
        grade: str,
        passed: bool,
        auto_fail_reasons: List[str],
        issues: List[str],
    ) -> str:
        """한국어 검수 결과 요약 생성 (CLAUDE.md 표 형식)

        Args:
            criteria_scores: 기준별 점수
            total_score: 총점
            grade: 등급
            passed: 통과 여부
            auto_fail_reasons: Auto-Fail 사유 목록
            issues: 이슈 목록

        Returns:
            str: Markdown 형식 검수 결과 문자열
        """
        # 한국어 기준명 매핑
        kr_names = {
            "outfit_accuracy": "착장 정확도",
            "face_identity": "얼굴 동일성",
            "background_compliance": "배경 준수",
            "pose_correctness": "포즈 정확도",
            "commercial_quality": "상업적 품질",
        }

        판정 = "통과" if passed else "재생성 필요"

        lines = [
            "## 검수 결과",
            "",
            "| 항목 | 점수 | 기준 | 통과 |",
            "|------|------|------|------|",
        ]

        for criterion, kr_name in kr_names.items():
            score = criteria_scores.get(criterion, 0)
            threshold = self.PASS_THRESHOLDS[criterion]
            ok = "O" if score >= threshold else "X"
            lines.append(f"| {kr_name} | {score} | >={threshold} | {ok} |")

        lines.append("")
        lines.append(
            f"**총점**: {total_score}/100 | **등급**: {grade} | **판정**: {판정}"
        )

        if auto_fail_reasons:
            lines.append("")
            lines.append("### Auto-Fail 사유")
            for r in auto_fail_reasons:
                lines.append(f"- {r}")

        if issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in issues:
                lines.append(f"- {issue}")

        return "\n".join(lines)
