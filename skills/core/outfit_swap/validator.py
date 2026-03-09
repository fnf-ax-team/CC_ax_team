"""
Outfit Swap Validator

착장 스왑 결과 검증 모듈 - WorkflowValidator 기반

검수 기준 (SKILL.md 기준):
- outfit_accuracy:      35%, threshold >= 90
- face_identity:        25%, threshold >= 95
- pose_preservation:    25%, threshold >= 95
- outfit_draping:       10%, threshold >= 80
- background_preservation: 5%, threshold >= 90

Pass 조건: total_score >= 92 AND 각 필수 기준 통과
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from google import genai
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


# ============================================================
# 검수 기준 상수
# ============================================================

# 가중치 (합계 = 1.0)
WEIGHTS: Dict[str, float] = {
    "outfit_accuracy": 0.35,
    "face_identity": 0.25,
    "pose_preservation": 0.25,
    "outfit_draping": 0.10,
    "background_preservation": 0.05,
}

# 개별 기준 통과 임계값
THRESHOLDS: Dict[str, int] = {
    "outfit_accuracy": 90,
    "face_identity": 95,
    "pose_preservation": 95,
    "outfit_draping": 80,
    "background_preservation": 90,
}

# Auto-Fail 임계값 (이 이하면 즉시 탈락)
AUTO_FAIL_THRESHOLDS: Dict[str, int] = {
    "face_identity": 80,  # 다른 사람 - 즉시 탈락
    "pose_preservation": 90,  # 포즈 변경 심각 - 즉시 탈락
    "outfit_accuracy": 70,  # 착장 색상/로고 불일치 - 즉시 탈락
}

# 전체 통과 점수
PASS_TOTAL = 92

# 한국어 기준명
CRITERION_NAMES_KR: Dict[str, str] = {
    "outfit_accuracy": "착장 정확도",
    "face_identity": "얼굴 동일성",
    "pose_preservation": "포즈 유지",
    "outfit_draping": "착장 자연스러움",
    "background_preservation": "배경 유지",
}

# 재시도 강화 규칙 (실패 기준별)
ENHANCEMENT_RULES: Dict[str, List[str]] = {
    "outfit_accuracy": [
        "EXACT colors from outfit images - match PRECISELY",
        "ALL outfit items must be present - check each item",
        "Logo position, text, color must match EXACTLY",
        "Material texture must match (fuzzy=fuzzy, denim=denim)",
    ],
    "face_identity": [
        "Preserve the face EXACTLY from SOURCE IMAGE",
        "Same person, same facial features, same skin tone",
        "Do NOT alter face shape, eye shape, or skin tone",
    ],
    "pose_preservation": [
        "EXACT same pose as SOURCE IMAGE - do not change anything",
        "Arm positions must match SOURCE exactly",
        "Leg positions must match SOURCE exactly",
        "Head tilt and body angle must be identical to SOURCE",
    ],
    "outfit_draping": [
        "Natural fabric draping conforming to the pose",
        "Physics-based wrinkles and folds matching body position",
        "No floating or detached clothing",
    ],
    "background_preservation": [
        "Keep the background EXACTLY as in SOURCE IMAGE",
        "Same setting, same lighting direction, same color tone",
    ],
}


# ============================================================
# 검증기 클래스
# ============================================================


@ValidatorRegistry.register(WorkflowType.OUTFIT_SWAP)
class OutfitSwapValidator(WorkflowValidator):
    """
    착장 스왑 워크플로 검증기

    ValidatorRegistry에 OUTFIT_SWAP으로 등록됨.
    WorkflowValidator 추상 클래스를 구현.
    """

    workflow_type = WorkflowType.OUTFIT_SWAP
    config = ValidationConfig(
        pass_total=PASS_TOTAL,
        weights=WEIGHTS,
        auto_fail_thresholds=AUTO_FAIL_THRESHOLDS,
        priority_order=[
            "outfit_accuracy",
            "face_identity",
            "pose_preservation",
            "outfit_draping",
            "background_preservation",
        ],
    )

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """
        착장 스왑 이미지 검증 (5개 기준)

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: {
                "source": [Image] - 원본 소스 이미지 (얼굴/포즈/배경 기준)
                "outfit": [Image, ...] - 착장 레퍼런스 이미지들
            }
            **kwargs: 추가 옵션 (사용하지 않음)

        Returns:
            CommonValidationResult: 검증 결과
        """
        # 이미지 로드
        gen_img = self._load_image(generated_img)

        # 소스 이미지 (얼굴/포즈/배경 기준)
        source_list = reference_images.get("source", [])
        source_img: Optional[Image.Image] = None
        if source_list:
            source_img = self._load_image(source_list[0])

        # 착장 레퍼런스 이미지들
        outfit_imgs = self._load_images(reference_images.get("outfit", []))

        if source_img is None:
            # 소스 없으면 검증 불가
            return self._make_fallback_result("소스 이미지가 없어 검증 불가")

        # VLM Parts 조립
        parts = [types.Part(text=VALIDATION_PROMPT)]

        # IMAGE 1: SOURCE
        parts.append(types.Part(text="[IMAGE 1: SOURCE] - 얼굴/포즈/배경 보존 기준"))
        parts.append(self._pil_to_part(source_img))

        # IMAGE 2: RESULT (generated)
        parts.append(types.Part(text="[IMAGE 2: RESULT] - 검수 대상 (착장 스왑 결과)"))
        parts.append(self._pil_to_part(gen_img))

        # IMAGE 3+: OUTFIT REFERENCE
        for i, outfit_img in enumerate(outfit_imgs):
            parts.append(
                types.Part(
                    text=f"[IMAGE {3 + i}: OUTFIT REFERENCE {i + 1}] - 착장 정확도 판정 기준"
                )
            )
            parts.append(self._pil_to_part(outfit_img))

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"],
                ),
            )

            response_text = response.candidates[0].content.parts[0].text.strip()

            # JSON 블록 추출
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())

        except json.JSONDecodeError as e:
            print(f"[OutfitSwapValidator] JSON 파싱 실패: {e}")
            return self._make_fallback_result(f"JSON 파싱 실패: {e}")
        except Exception as e:
            print(f"[OutfitSwapValidator] VLM 호출 실패: {e}")
            return self._make_fallback_result(f"VLM 호출 실패: {e}")

        return self._build_result(data)

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """
        실패한 기준에 따른 프롬프트 강화 규칙 반환

        Args:
            failed_criteria: 실패한 검증 기준 키 목록

        Returns:
            강화 규칙 문자열 (프롬프트에 추가할 내용)
        """
        rules = []
        for criterion in failed_criteria:
            if criterion in ENHANCEMENT_RULES:
                rules.extend(ENHANCEMENT_RULES[criterion])

        if not rules:
            return ""

        lines = ["[ENHANCEMENT - 이전 시도 실패 원인 수정]"]
        for rule in rules:
            lines.append(f"- {rule}")
        return "\n".join(lines)

    def format_korean(self, result: CommonValidationResult) -> str:
        """
        검수 결과를 한국어 검수표 형식으로 출력

        Args:
            result: CommonValidationResult 객체

        Returns:
            한국어 검수표 문자열
        """
        criteria_order = [
            ("outfit_accuracy", "착장 정확도", "35%"),
            ("face_identity", "얼굴 동일성", "25%"),
            ("pose_preservation", "포즈 유지", "25%"),
            ("outfit_draping", "착장 자연스러움", "10%"),
            ("background_preservation", "배경 유지", "5%"),
        ]

        lines = [
            "## 검수 결과",
            "",
            "| 항목 | 비중 | Pass 기준 | 점수 | 통과 |",
            "|------|------|-----------|------|------|",
        ]

        for key, name_kr, weight in criteria_order:
            score = result.criteria_scores.get(key, 0)
            threshold = THRESHOLDS[key]
            passed_mark = "O" if score >= threshold else "X"
            lines.append(
                f"| {name_kr} | {weight} | >= {threshold} | {score} | {passed_mark} |"
            )

        # 등급/판정 한국어
        tier_kr = {
            "RELEASE_READY": "납품 가능",
            "NEEDS_MINOR_EDIT": "소폭 보정 필요",
            "REGENERATE": "재생성 필요",
        }
        tier_text = tier_kr.get(result.tier.value, result.tier.value)

        lines.append("")
        lines.append(
            f"**총점**: {result.total_score}/100 | **등급**: {result.grade} | **판정**: {tier_text}"
        )

        if result.auto_fail_reasons:
            lines.append("")
            lines.append("### 자동 탈락 사유")
            for reason in result.auto_fail_reasons:
                lines.append(f"- {reason}")

        if result.issues:
            lines.append("")
            lines.append("### 이슈 사항")
            for issue in result.issues[:5]:
                lines.append(f"- {issue}")

        if result.summary_kr:
            lines.append("")
            lines.append(f"### 종합 의견")
            lines.append(result.summary_kr)

        return "\n".join(lines)

    # --------------------------------------------------------
    # 내부 헬퍼 메서드
    # --------------------------------------------------------

    def _build_result(self, data: dict) -> CommonValidationResult:
        """VLM 응답 dict에서 CommonValidationResult 생성"""

        def get_score(key: str) -> int:
            """기준별 점수 추출 (dict or int 처리)"""
            val = data.get(key, {})
            if isinstance(val, dict):
                return int(val.get("score", 0))
            return int(val)

        # 점수 추출
        scores = {key: get_score(key) for key in WEIGHTS}

        # 가중치 적용 총점
        total_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
        total_score = round(total_score)

        # Auto-Fail 체크
        auto_fail = False
        auto_fail_reasons: List[str] = []

        # VLM이 auto_fail 응답 준 경우
        if data.get("auto_fail", False):
            auto_fail = True
            auto_fail_reasons.extend(data.get("auto_fail_reasons", []))

        # 기준별 Auto-Fail 임계값 체크
        for key, threshold in AUTO_FAIL_THRESHOLDS.items():
            if scores.get(key, 0) < threshold:
                auto_fail = True
                auto_fail_reasons.append(
                    f"{CRITERION_NAMES_KR.get(key, key)}: {scores[key]}점 < {threshold}점"
                )

        # 착장 누락 체크 (outfit_accuracy의 missing_items)
        outfit_data = data.get("outfit_accuracy", {})
        missing_items = []
        if isinstance(outfit_data, dict):
            missing_items = outfit_data.get("missing_items", [])
        if missing_items:
            auto_fail = True
            auto_fail_reasons.append(f"착장 누락: {', '.join(missing_items)}")

        # 등급 결정
        if auto_fail:
            grade = "F"
            tier = QualityTier.REGENERATE
        elif total_score >= 97:
            grade = "S"
            tier = QualityTier.RELEASE_READY
        elif total_score >= 92:
            grade = "A"
            tier = QualityTier.RELEASE_READY
        elif total_score >= 85:
            grade = "B"
            tier = QualityTier.NEEDS_MINOR_EDIT
        elif total_score >= 75:
            grade = "C"
            tier = QualityTier.REGENERATE
        else:
            grade = "F"
            tier = QualityTier.REGENERATE

        # 통과 여부: auto_fail 없고 총점 >= PASS_TOTAL 이고 필수 기준 통과
        passed = (
            not auto_fail
            and total_score >= PASS_TOTAL
            and all(
                scores.get(key, 0) >= THRESHOLDS[key]
                for key in ["outfit_accuracy", "face_identity", "pose_preservation"]
            )
        )

        return CommonValidationResult(
            workflow_type=WorkflowType.OUTFIT_SWAP,
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=data.get("issues", []),
            criteria_scores=scores,
            summary_kr=data.get("summary_kr", ""),
            raw_response=json.dumps(data, ensure_ascii=False),
        )

    def _make_fallback_result(self, reason: str) -> CommonValidationResult:
        """검증 실패 시 기본 결과"""
        return CommonValidationResult(
            workflow_type=WorkflowType.OUTFIT_SWAP,
            total_score=0,
            tier=QualityTier.REGENERATE,
            grade="F",
            passed=False,
            auto_fail=True,
            auto_fail_reasons=[f"검증 실패: {reason}"],
            issues=[reason],
            criteria_scores={key: 0 for key in WEIGHTS},
            summary_kr=f"검증 오류로 자동 탈락: {reason}",
        )

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini API Part로 변환"""
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )


# ============================================================
# 공개 인터페이스
# ============================================================

__all__ = [
    "OutfitSwapValidator",
    "WEIGHTS",
    "THRESHOLDS",
    "AUTO_FAIL_THRESHOLDS",
    "CRITERION_NAMES_KR",
    "ENHANCEMENT_RULES",
    "PASS_TOTAL",
]
