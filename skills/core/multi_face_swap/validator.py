"""
다중 얼굴 교체 검증기

MultiFaceSwapValidator — 단체 사진 다중 얼굴 교체 결과를 5개 기준으로 검증한다.

검증 기준 (총점 >= 92 통과):
    all_faces_identity  40%  >= 90 (모든 인물 얼굴 동일성 평균, 한 명이라도 < 80 = Auto-Fail)
    face_consistency    20%  >= 85 (얼굴들이 자연스럽게 어울리는가)
    pose_preservation   20%  >= 95 (각 인물 포즈 보존)
    outfit_preservation 15%  >= 95 (각 인물 착장 보존)
    edge_quality         5%  >= 80 (얼굴 경계 품질)

Auto-Fail 조건:
    - 인물 수 불일치 (원본 vs 결과)
    - 위치 뒤바뀜 (어느 한 명이라도)
    - 얼굴 동일성 < 80 (어느 한 명이라도)
    - 착장 변경됨 (어느 한 명이라도)
    - 체형 변경됨
"""

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Union

from PIL import Image

from core.config import VISION_MODEL
from core.multi_face_swap.templates import VALIDATION_PROMPT
from core.validators.base import (
    CommonValidationResult,
    QualityTier,
    ValidationConfig,
    WorkflowType,
    WorkflowValidator,
)
from core.validators.registry import ValidatorRegistry

logger = logging.getLogger(__name__)


def _pil_to_part(img: Image.Image, max_size: int = 1024):
    """PIL 이미지를 Gemini API Part로 변환"""
    from google.genai import types

    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _load_image(img: Union[str, Path, Image.Image]) -> Image.Image:
    """이미지 로드 헬퍼"""
    if isinstance(img, (str, Path)):
        return Image.open(img).convert("RGB")
    if hasattr(img, "convert"):
        return img.convert("RGB")
    raise TypeError(f"지원하지 않는 이미지 타입: {type(img)}")


def _parse_json_response(text: str) -> dict:
    """VLM 응답에서 JSON 파싱"""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"VLM 응답 JSON 파싱 실패: {e}\n텍스트:\n{text[:400]}")


def _compute_grade(score: int) -> str:
    """점수 → 등급 변환"""
    if score >= 95:
        return "S"
    if score >= 90:
        return "A"
    if score >= 85:
        return "B"
    if score >= 75:
        return "C"
    return "F"


def _compute_tier(grade: str, passed: bool) -> QualityTier:
    """등급 → QualityTier 변환"""
    if not passed:
        return QualityTier.REGENERATE
    if grade in ("S", "A"):
        return QualityTier.RELEASE_READY
    if grade == "B":
        return QualityTier.NEEDS_MINOR_EDIT
    return QualityTier.REGENERATE


@ValidatorRegistry.register(WorkflowType.MULTI_FACE_SWAP)
class MultiFaceSwapValidator(WorkflowValidator):
    """다중 얼굴 교체 검증기

    단체 사진에서 여러 얼굴을 교체한 결과를 5개 기준으로 평가한다.
    VALIDATION_PROMPT를 VISION_MODEL에 전달하여 단계별 검증 결과를 받는다.

    Attributes:
        workflow_type: MULTI_FACE_SWAP
        config: 다중 얼굴 교체 전용 검증 설정
    """

    workflow_type = WorkflowType.MULTI_FACE_SWAP

    # 검증 기준 및 가중치
    config = ValidationConfig(
        pass_total=92,  # 총점 92점 이상 통과
        weights={
            "all_faces_identity": 0.40,  # 모든 얼굴 동일성 (핵심)
            "face_consistency": 0.20,  # 얼굴들이 자연스럽게 어울림
            "pose_preservation": 0.20,  # 포즈 보존
            "outfit_preservation": 0.15,  # 착장 보존
            "edge_quality": 0.05,  # 얼굴 경계 품질
        },
        auto_fail_thresholds={
            "all_faces_identity": 90,  # 한 명이라도 80 미만 → Auto-Fail
            "pose_preservation": 95,
            "outfit_preservation": 95,
        },
        priority_order=[
            "all_faces_identity",
            "face_consistency",
            "pose_preservation",
            "outfit_preservation",
            "edge_quality",
        ],
    )

    # 실패 기준별 강화 규칙 (프롬프트 재생성 시 사용)
    ENHANCEMENT_RULES = {
        "all_faces_identity": [
            "Each face MUST match reference with identity >= 95%",
            "Use ONLY the provided reference faces for each person",
            "Preserve unique facial features: eyes, nose, mouth, jawline",
            "Never merge or mix facial features from different persons",
        ],
        "face_consistency": [
            "All replaced faces must look natural together in the group",
            "Apply consistent lighting to all faces matching background",
            "Ensure skin tone adjustments match ambient lighting",
            "Natural expressions appropriate for group setting",
        ],
        "pose_preservation": [
            "Keep EXACT body poses for EVERY person — zero changes",
            "Do NOT adjust or naturalize any body position",
            "Maintain exact head tilt and neck angle for each person",
            "Preserve exact hand and arm positions",
        ],
        "outfit_preservation": [
            "Preserve EXACT clothing for EVERY person — no color changes",
            "Keep all logos, patterns, textures identical to source",
            "Do NOT substitute or simplify any clothing item",
            "Maintain exact fit and silhouette of each outfit",
        ],
        "edge_quality": [
            "Clean, seamless face boundary blending for all persons",
            "No visible seams or hard edges at face-neck boundary",
            "Natural skin texture transition at face boundaries",
            "No color mismatch at face-neck junction",
        ],
    }

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """다중 얼굴 교체 결과 검증

        VISION_MODEL에 원본 사진 + 결과 이미지 + 각 인물 참조 얼굴을
        함께 전달하여 단계별 검증을 수행한다.

        Args:
            generated_img: 얼굴 교체 결과 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "source": [원본 단체 사진] (필수, 1장)
                - "face_N": [person_id=N의 참조 얼굴 이미지들] (선택)
                  예: "face_1", "face_2", "face_3", ...
            **kwargs: 추가 옵션 (현재 미사용)

        Returns:
            CommonValidationResult: 검증 결과

        Raises:
            ValueError: source 이미지 누락 시
        """
        from google.genai import types

        # 원본 이미지 확인
        source_list = reference_images.get("source", [])
        if not source_list:
            raise ValueError(
                "reference_images에 'source' (원본 단체 사진)가 필요합니다."
            )

        # 이미지 로드
        source_img = _load_image(source_list[0])
        result_img = _load_image(generated_img)

        # Parts 조립: 프롬프트 + 원본 + 결과 + 각 인물 참조 얼굴
        parts = [types.Part(text=VALIDATION_PROMPT)]
        parts.append(_pil_to_part(source_img))  # Image 1: SOURCE
        parts.append(_pil_to_part(result_img))  # Image 2: RESULT

        # Image 3+: 각 인물 참조 얼굴 (face_1, face_2, ...)
        person_keys = sorted(
            [k for k in reference_images if k.startswith("face_")],
            key=lambda k: int(k.split("_")[1]) if k.split("_")[1].isdigit() else 0,
        )
        for key in person_keys:
            for face_img_src in reference_images[key]:
                try:
                    face_img = _load_image(face_img_src)
                    parts.append(_pil_to_part(face_img))
                except Exception as e:
                    logger.warning(
                        "[MULTI_FACE_SWAP] 참조 얼굴 로드 실패 (%s): %s", key, e
                    )

        # VLM 검증 호출
        response = self.client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_modalities=["TEXT"],
            ),
        )

        raw_text = response.candidates[0].content.parts[0].text

        # 응답 파싱 및 결과 변환
        return self._parse_validation_response(raw_text)

    def _parse_validation_response(self, raw_text: str) -> CommonValidationResult:
        """VLM 검증 응답을 CommonValidationResult로 변환

        Args:
            raw_text: VLM 응답 텍스트

        Returns:
            CommonValidationResult
        """
        try:
            data = _parse_json_response(raw_text)
        except ValueError as e:
            logger.error("[MULTI_FACE_SWAP] 검증 응답 파싱 실패: %s", e)
            # 파싱 실패 시 최저점 반환
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=["VLM 검증 응답 파싱 실패"],
                issues=["검증 응답을 처리할 수 없습니다. 재생성을 시도하세요."],
                criteria_scores={},
                summary_kr="검증 실패: VLM 응답 파싱 오류",
                raw_response=raw_text,
            )

        # Auto-Fail 처리
        auto_fail_data = data.get("step6_auto_fail", {})
        auto_fail = auto_fail_data.get("auto_fail", False)
        auto_fail_reasons = auto_fail_data.get("reasons", [])

        # 각 기준 점수 추출
        scores_data = data.get("step5_scores", {})
        criteria_scores = {
            "all_faces_identity": scores_data.get("all_faces_identity", 0),
            "face_consistency": scores_data.get("face_consistency", 0),
            "pose_preservation": scores_data.get("pose_preservation", 0),
            "outfit_preservation": scores_data.get("outfit_preservation", 0),
            "edge_quality": scores_data.get("edge_quality", 0),
        }

        # 총점 계산 (가중 평균)
        total_score = int(
            criteria_scores["all_faces_identity"] * 0.40
            + criteria_scores["face_consistency"] * 0.20
            + criteria_scores["pose_preservation"] * 0.20
            + criteria_scores["outfit_preservation"] * 0.15
            + criteria_scores["edge_quality"] * 0.05
        )

        # 개별 얼굴 동일성 체크 — 한 명이라도 < 80 이면 Auto-Fail
        face_identities = data.get("step4_face_identities", [])
        for fi in face_identities:
            score = fi.get("score", 100)
            person_id = fi.get("person", "?")
            if score < 80:
                auto_fail = True
                reason = (
                    f"인물 {person_id} 얼굴 동일성 {score}점 (기준: 80점 이상 필수)"
                )
                if reason not in auto_fail_reasons:
                    auto_fail_reasons.append(reason)

        # 통과 여부 결정
        if auto_fail:
            passed = False
        else:
            passed = (
                total_score >= self.config.pass_total
                and criteria_scores["all_faces_identity"] >= 90
                and criteria_scores["face_consistency"] >= 85
                and criteria_scores["pose_preservation"] >= 95
                and criteria_scores["outfit_preservation"] >= 95
                and criteria_scores["edge_quality"] >= 80
            )

        # 등급 및 티어
        grade = _compute_grade(total_score)
        tier = _compute_tier(grade, passed)

        # 이슈 목록
        issues = list(data.get("issues", []))
        if auto_fail_reasons:
            for reason in auto_fail_reasons:
                if reason not in issues:
                    issues.append(f"[Auto-Fail] {reason}")

        # 한국어 요약 생성
        summary_kr = data.get("summary_kr", "")
        if not summary_kr:
            status = "통과" if passed else "탈락"
            summary_kr = (
                f"다중 얼굴 교체 검수 {status}. "
                f"총점: {total_score}점 (기준: {self.config.pass_total}점), "
                f"등급: {grade}"
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
            raw_response=raw_text,
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패한 검증 기준에 따른 프롬프트 강화 규칙 반환

        재생성 시 프롬프트에 추가할 규칙을 우선순위 순서로 반환한다.

        Args:
            failed_criteria: 실패한 기준 목록
                예: ["all_faces_identity", "pose_preservation"]

        Returns:
            강화 규칙 문자열 (각 줄 "- " 접두사, 최대 8개 규칙)
        """
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        # 최대 8개 규칙으로 제한
        return "\n".join([f"- {line}" for line in lines[:8]])
