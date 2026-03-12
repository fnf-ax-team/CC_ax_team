"""
Face Swap 검증기

검증 기준 (5개):
1. face_identity (40%)      - 얼굴 동일성, threshold >= 95
2. pose_preservation (25%)  - 포즈 유지, threshold >= 95
3. outfit_preservation (20%)- 착장 유지, threshold >= 95
4. lighting_consistency (10%)- 조명 일관성, threshold >= 80
5. edge_quality (5%)        - 경계 품질, threshold >= 80

Pass 조건: total_score >= 95

Auto-Fail 조건:
- face_identity < 80 (완전히 다른 사람)
- 포즈/착장/배경 변경됨
- 손가락 6개 이상
- 누런 톤 (golden/amber cast)
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Union
from pathlib import Path

from PIL import Image
from google.genai import types

from core.config import VISION_MODEL
from core.api import _get_next_api_key
from core.utils import pil_to_part
from core.validators.base import (
    WorkflowValidator,
    WorkflowType,
    CommonValidationResult,
    ValidationConfig,
    QualityTier,
)
from core.validators.registry import ValidatorRegistry

from .templates import VALIDATION_PROMPT


# ============================================================
# 검증 결과 데이터클래스
# ============================================================


@dataclass
class FaceSwapValidationResult:
    """Face Swap 검증 결과"""

    # 5개 기준 점수 (0-100)
    face_identity: int = 0  # 40% - >= 95 필수
    pose_preservation: int = 0  # 25% - >= 95 필수
    outfit_preservation: int = 0  # 20% - >= 95 필수
    lighting_consistency: int = 0  # 10% - >= 80 필수
    edge_quality: int = 0  # 5%  - >= 80 필수

    # reason 필드 (VLM step-by-step 검수 근거)
    face_identity_reason: str = ""
    pose_preservation_reason: str = ""
    outfit_preservation_reason: str = ""
    lighting_consistency_reason: str = ""
    edge_quality_reason: str = ""

    # auto-fail
    auto_fail: bool = False
    auto_fail_reasons: List[str] = field(default_factory=list)

    # 메타
    issues: List[str] = field(default_factory=list)
    raw_response: str = ""

    @property
    def total_score(self) -> int:
        """가중치 적용 총점"""
        return int(
            self.face_identity * 0.40
            + self.pose_preservation * 0.25
            + self.outfit_preservation * 0.20
            + self.lighting_consistency * 0.10
            + self.edge_quality * 0.05
        )

    @property
    def passed(self) -> bool:
        """Pass 조건: 총점 >= 95 AND auto_fail 없음"""
        return self.total_score >= 95 and not self.auto_fail

    @property
    def grade(self) -> str:
        """등급 반환"""
        if self.passed and self.total_score >= 98:
            return "S"
        elif self.passed and self.total_score >= 95:
            return "A"
        elif self.total_score >= 85:
            return "B"
        elif self.total_score >= 75:
            return "C"
        else:
            return "F"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "face_identity": self.face_identity,
            "pose_preservation": self.pose_preservation,
            "outfit_preservation": self.outfit_preservation,
            "lighting_consistency": self.lighting_consistency,
            "edge_quality": self.edge_quality,
            "total_score": self.total_score,
            "passed": self.passed,
            "grade": self.grade,
            "auto_fail": self.auto_fail,
            "auto_fail_reasons": self.auto_fail_reasons,
            "issues": self.issues,
            "reasons": {
                "face_identity": self.face_identity_reason,
                "pose_preservation": self.pose_preservation_reason,
                "outfit_preservation": self.outfit_preservation_reason,
                "lighting_consistency": self.lighting_consistency_reason,
                "edge_quality": self.edge_quality_reason,
            },
        }

    def format_korean(self) -> str:
        """검수 결과 한국어 표 형식 출력 (CLAUDE.md 검수 결과 출력 규칙 준수)"""

        def check(score: int, threshold: int) -> str:
            return "O" if score >= threshold else "X"

        lines = [
            "## 검수 결과",
            "",
            "| 항목 | 가중치 | 임계값 | 점수 | 통과 |",
            "|------|--------|--------|------|------|",
            f"| 얼굴 동일성 | 40% | >= 95 | {self.face_identity} | {check(self.face_identity, 95)} |",
            f"| 포즈 유지 | 25% | >= 95 | {self.pose_preservation} | {check(self.pose_preservation, 95)} |",
            f"| 착장 유지 | 20% | >= 95 | {self.outfit_preservation} | {check(self.outfit_preservation, 95)} |",
            f"| 조명 일관성 | 10% | >= 80 | {self.lighting_consistency} | {check(self.lighting_consistency, 80)} |",
            f"| 경계 품질 | 5% | >= 80 | {self.edge_quality} | {check(self.edge_quality, 80)} |",
            "",
            f"**총점**: {self.total_score}/100 | **등급**: {self.grade} | **판정**: {'PASS' if self.passed else 'FAIL'}",
        ]

        if self.auto_fail:
            lines.append("")
            lines.append("### Auto-Fail 사유")
            for reason in self.auto_fail_reasons:
                lines.append(f"- {reason}")

        if self.issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in self.issues:
                lines.append(f"- {issue}")

        return "\n".join(lines)


# ============================================================
# 강화 규칙 (재시도 시 프롬프트 보강)
# ============================================================

ENHANCEMENT_RULES = {
    "face_identity": [
        "Face MUST match reference exactly - same person identity",
        "Preserve unique facial features: eye shape, nose, jawline",
        "Match skin tone from face reference image",
        "Keep consistent face proportions and structure",
    ],
    "pose_preservation": [
        "Pose from SOURCE image ONLY - DO NOT change body position",
        "Arm positions EXACT: left arm, right arm from source",
        "Leg positions EXACT from source",
        "Body weight distribution EXACT from source",
    ],
    "outfit_preservation": [
        "Outfit from SOURCE image ONLY - EXACT copy",
        "Colors EXACT match: no shade variation allowed",
        "All logos and branding MUST be preserved",
        "Fabric texture and style EXACT from source",
    ],
    "lighting_consistency": [
        "Face lighting MUST match source image lighting direction",
        "Shadow direction on face matches light source in source",
        "No harsh shadows added that weren't in source",
        "Natural skin texture under consistent lighting",
    ],
    "edge_quality": [
        "Face-to-background edge must be clean and natural",
        "No glow or halo artifacts around face",
        "Hair-to-background transition must be seamless",
        "No color bleeding at face boundary",
    ],
}


# ============================================================
# WorkflowValidator 구현
# ============================================================


@ValidatorRegistry.register(WorkflowType.FACE_SWAP)
class FaceSwapValidator(WorkflowValidator):
    """Face Swap 검증기

    face_identity, pose_preservation, outfit_preservation,
    lighting_consistency, edge_quality 5개 기준으로 검수.

    Attributes:
        workflow_type: FACE_SWAP
        config: Face Swap 전용 검증 설정
    """

    workflow_type = WorkflowType.FACE_SWAP

    config = ValidationConfig(
        pass_total=95,
        weights={
            "face_identity": 0.40,
            "pose_preservation": 0.25,
            "outfit_preservation": 0.20,
            "lighting_consistency": 0.10,
            "edge_quality": 0.05,
        },
        auto_fail_thresholds={
            "face_identity": 80,  # < 80 이면 완전히 다른 사람 → auto_fail
        },
        priority_order=[
            "face_identity",
            "pose_preservation",
            "outfit_preservation",
            "lighting_consistency",
            "edge_quality",
        ],
        grade_thresholds={"S": 98, "A": 95, "B": 85, "C": 75},
    )

    def __init__(self, client):
        """검증기 초기화

        Args:
            client: Gemini API 클라이언트 (google.genai.Client)
        """
        super().__init__(client)

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """Face Swap 이미지 검증

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "face": 얼굴 참조 이미지 리스트 (필수, 교체된 얼굴 원본)
                - "source": 소스 이미지 리스트 (필수, 원본 포즈/착장/배경)
            **kwargs: 추가 옵션

        Returns:
            CommonValidationResult: 공통 검증 결과
        """
        # 이미지 로드
        generated = self._load_image(generated_img)

        face_imgs = reference_images.get("face", [])
        source_imgs = reference_images.get("source", [])

        # 로우레벨 검수 실행
        raw_result = self._run_validation(generated, face_imgs, source_imgs)

        # Tier 결정
        if not raw_result.passed or raw_result.grade == "F":
            tier = QualityTier.REGENERATE
        elif raw_result.grade in ("S", "A"):
            tier = QualityTier.RELEASE_READY
        else:
            tier = QualityTier.NEEDS_MINOR_EDIT

        # Auto-fail 사유 수집
        auto_fail_reasons = list(raw_result.auto_fail_reasons)
        if raw_result.face_identity < self.config.auto_fail_thresholds.get(
            "face_identity", 80
        ):
            reason = f"얼굴 동일성 {raw_result.face_identity} < 80 (완전히 다른 사람)"
            if reason not in auto_fail_reasons:
                auto_fail_reasons.append(reason)

        # 이슈 수집
        issues = list(raw_result.issues)
        for criterion, threshold in [
            ("face_identity", 95),
            ("pose_preservation", 95),
            ("outfit_preservation", 95),
            ("lighting_consistency", 80),
            ("edge_quality", 80),
        ]:
            score = getattr(raw_result, criterion)
            if score < threshold:
                issues.append(f"{criterion}: {score} < {threshold}")

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=raw_result.total_score,
            tier=tier,
            grade=raw_result.grade,
            passed=raw_result.passed,
            auto_fail=raw_result.auto_fail or bool(auto_fail_reasons),
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            criteria_scores=raw_result.to_dict(),
            summary_kr=raw_result.format_korean(),
            raw_response=raw_result.raw_response,
        )

    def _run_validation(
        self,
        generated_img: Image.Image,
        face_imgs: List[Union[str, Path, Image.Image]],
        source_imgs: List[Union[str, Path, Image.Image]],
    ) -> FaceSwapValidationResult:
        """로우레벨 VLM 검수 실행

        Args:
            generated_img: 생성된 이미지
            face_imgs: 얼굴 참조 이미지 리스트
            source_imgs: 소스 이미지 리스트

        Returns:
            FaceSwapValidationResult
        """
        try:
            # Parts 조립: 프롬프트 + 얼굴 참조 + 소스 + 결과물
            parts = [types.Part(text=VALIDATION_PROMPT)]

            # 얼굴 참조 이미지 (Image 1)
            if face_imgs:
                face_ref = self._load_image(face_imgs[0])
                parts.append(
                    types.Part(
                        text="\n[Image 1 - 얼굴 참조 이미지 (교체된 얼굴 원본)]:"
                    )
                )
                parts.append(pil_to_part(face_ref, max_size=1024))

            # 소스 이미지 (Image 2)
            if source_imgs:
                source_ref = self._load_image(source_imgs[0])
                parts.append(
                    types.Part(text="\n[Image 2 - 소스 이미지 (원본 포즈/착장/배경)]:")
                )
                parts.append(pil_to_part(source_ref, max_size=1024))

            # 결과 이미지 (Image 3)
            parts.append(
                types.Part(text="\n[Image 3 - Face Swap 결과 이미지 (검수 대상)]:")
            )
            parts.append(pil_to_part(generated_img, max_size=1024))

            # VLM 호출
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            data = json.loads(response.text)

            # 각 기준 점수 추출
            face_identity = int(data.get("face_identity", {}).get("score", 0))
            pose_preservation = int(data.get("pose_preservation", {}).get("score", 0))
            outfit_preservation = int(
                data.get("outfit_preservation", {}).get("score", 0)
            )
            lighting_consistency = int(
                data.get("lighting_consistency", {}).get("score", 0)
            )
            edge_quality = int(data.get("edge_quality", {}).get("score", 0))

            auto_fail = bool(data.get("auto_fail", False))
            auto_fail_reasons = data.get("auto_fail_reasons", [])

            # face_identity < 80 이면 자동 auto_fail
            if face_identity < 80:
                auto_fail = True
                reason = f"얼굴 동일성 {face_identity} < 80"
                if reason not in auto_fail_reasons:
                    auto_fail_reasons.append(reason)

            return FaceSwapValidationResult(
                face_identity=face_identity,
                pose_preservation=pose_preservation,
                outfit_preservation=outfit_preservation,
                lighting_consistency=lighting_consistency,
                edge_quality=edge_quality,
                face_identity_reason=data.get("face_identity", {}).get("reason", ""),
                pose_preservation_reason=data.get("pose_preservation", {}).get(
                    "reason", ""
                ),
                outfit_preservation_reason=data.get("outfit_preservation", {}).get(
                    "reason", ""
                ),
                lighting_consistency_reason=data.get("lighting_consistency", {}).get(
                    "reason", ""
                ),
                edge_quality_reason=data.get("edge_quality", {}).get("reason", ""),
                auto_fail=auto_fail,
                auto_fail_reasons=auto_fail_reasons,
                raw_response=response.text,
            )

        except Exception as e:
            return FaceSwapValidationResult(
                issues=[f"검수 오류: {str(e)[:200]}"],
                auto_fail=True,
                auto_fail_reasons=[f"검수 실행 오류: {str(e)[:100]}"],
                raw_response=str(e),
            )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 프롬프트 강화 규칙 반환

        Args:
            failed_criteria: 실패한 기준 목록
                (예: ["face_identity", "pose_preservation"])

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트
        """
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in ENHANCEMENT_RULES:
                lines.extend(ENHANCEMENT_RULES[criterion])
        # 최대 10개 규칙으로 제한
        return "\n".join([f"- {line}" for line in lines[:10]])


# ============================================================
# 헬퍼 함수
# ============================================================


def validate_face_swap_result(
    generated_img: Union[str, Path, Image.Image],
    face_imgs: List[Union[str, Path, Image.Image]],
    source_imgs: List[Union[str, Path, Image.Image]],
) -> FaceSwapValidationResult:
    """Face Swap 결과 검수 헬퍼 함수

    Args:
        generated_img: 생성된 이미지
        face_imgs: 얼굴 참조 이미지 리스트
        source_imgs: 소스 이미지 리스트

    Returns:
        FaceSwapValidationResult
    """
    from google import genai

    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)

    validator = FaceSwapValidator(client)
    return validator._run_validation(generated_img, face_imgs, source_imgs)


__all__ = [
    "FaceSwapValidationResult",
    "FaceSwapValidator",
    "ENHANCEMENT_RULES",
    "validate_face_swap_result",
]
