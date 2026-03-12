"""
FNF Studio 통합 검증기 기본 모듈

이 모듈은 모든 워크플로 검증기의 기반 인터페이스를 제공합니다.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
from google.genai import types


class WorkflowType(Enum):
    """워크플로 타입 열거형 - workflow-invariants.json과 1:1 매핑"""

    # Person 카테고리 (11개)
    BRANDCUT = "brand_cut"
    REFERENCE_BRANDCUT = "reference_brandcut"
    BACKGROUND_SWAP = "background_swap"
    FACE_SWAP = "face_swap"
    MULTI_FACE_SWAP = "multi_face_swap"
    POSE_CHANGE = "pose_change"
    POSE_COPY = "pose_copy"
    OUTFIT_SWAP = "outfit_swap"
    SELFIE = "selfie"
    UGC = "seeding_ugc"
    ECOMMERCE = "ecommerce"
    AI_INFLUENCER = "ai_influencer"

    # Product 카테고리 (4개)
    PRODUCT_DESIGN = "product_design"
    FABRIC_GENERATION = "fabric_generation"
    PRODUCT_STYLED = "product_styled"
    SHOES_3D = "shoes_3d"

    # Design 카테고리
    FIT_VARIATION = "fit_variation"

    # Video 카테고리
    VIDEO_GENERATION = "video_generation"

    # Post-processing 카테고리
    UPSCALE = "upscale"


class QualityTier(Enum):
    """품질 분류 등급 - MLBValidator의 QualityTier와 값 호환"""

    RELEASE_READY = "RELEASE_READY"  # S/A Grade: 즉시 납품 가능
    NEEDS_MINOR_EDIT = "NEEDS_MINOR_EDIT"  # B Grade: 소폭 보정 후 사용 가능
    REGENERATE = "REGENERATE"  # C/F Grade: 재생성 필요


@dataclass
class ValidationConfig:
    """검증 설정"""

    pass_total: int = 85
    weights: Dict[str, float] = field(default_factory=dict)
    auto_fail_thresholds: Dict[str, int] = field(default_factory=dict)
    priority_order: List[str] = field(default_factory=list)
    # 워크플로별 등급 임계값 — {"S": 95, "A": 85, "B": 70, "C": 50}
    grade_thresholds: Dict[str, int] = field(default_factory=dict)


@dataclass
class CommonValidationResult:
    """통합 검증 결과"""

    workflow_type: WorkflowType
    total_score: int
    tier: QualityTier
    grade: str  # S/A/B/C/F
    passed: bool
    auto_fail: bool = False
    auto_fail_reasons: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    criteria_scores: Dict[str, Any] = field(default_factory=dict)
    summary_kr: str = ""
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "workflow_type": self.workflow_type.value,
            "total_score": self.total_score,
            "tier": self.tier.value,
            "grade": self.grade,
            "passed": self.passed,
            "auto_fail": self.auto_fail,
            "auto_fail_reasons": self.auto_fail_reasons,
            "issues": self.issues,
            "criteria_scores": self.criteria_scores,
            "summary_kr": self.summary_kr,
        }


class WorkflowValidator(ABC):
    """워크플로 검증기 추상 클래스

    모든 워크플로별 검증기는 이 클래스를 상속받아야 합니다.
    """

    workflow_type: WorkflowType
    config: ValidationConfig

    def __init__(self, client):
        """검증기 초기화

        Args:
            client: Gemini API 클라이언트
        """
        self.client = client

    @abstractmethod
    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """이미지 검증 수행

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "face": 얼굴 이미지 리스트
                - "outfit": 착장 이미지 리스트
                - "background": 배경 이미지 리스트
                - etc.
            **kwargs: 추가 옵션

        Returns:
            CommonValidationResult: 검증 결과
        """
        pass

    @abstractmethod
    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 프롬프트 강화 규칙 반환

        Args:
            failed_criteria: 실패한 검증 기준 목록

        Returns:
            강화 규칙 문자열
        """
        pass

    def should_retry(self, result: CommonValidationResult) -> bool:
        """재시도 여부 판단

        Args:
            result: 검증 결과

        Returns:
            재시도 필요 여부
        """
        # 통과했거나 자동 실패인 경우 재시도 안함
        if result.passed or result.auto_fail:
            return False
        # 점수가 너무 낮으면 재시도
        return result.total_score < self.config.pass_total

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드 헬퍼

        Args:
            img: 이미지 경로 또는 PIL Image

        Returns:
            PIL Image 객체
        """
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _load_images(
        self, images: List[Union[str, Path, Image.Image]]
    ) -> List[Image.Image]:
        """여러 이미지 로드 헬퍼

        Args:
            images: 이미지 경로 또는 PIL Image 리스트

        Returns:
            PIL Image 객체 리스트
        """
        return [self._load_image(img) for img in images]

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image → Gemini API Part 변환 (공통)

        Args:
            img: PIL Image 객체
            max_size: 최대 크기 (다운샘플링)

        Returns:
            types.Part(inline_data=types.Blob(...))
        """
        converted = img.copy().convert("RGB")
        if max(converted.size) > max_size:
            converted.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        converted.save(buf, format="PNG")
        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
        )

    def _parse_vlm_json(self, text: str) -> dict:
        """VLM 응답에서 JSON 추출 — 3단계 폴백

        Args:
            text: VLM 응답 텍스트

        Returns:
            파싱된 JSON dict
        """
        # 1. ```json ... ``` 블록 추출
        json_match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 2. { ... } 직접 추출 (가장 바깥 중괄호)
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 3. 전체를 json.loads 시도
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _calculate_grade(self, score: int) -> Tuple[str, "QualityTier"]:
        """점수 → 등급/티어 변환 (공통)

        config.grade_thresholds가 있으면 워크플로별 임계값 사용,
        없으면 기본값(S≥95, A≥85, B≥70, C≥50) 사용.

        Args:
            score: 총점 (0-100)

        Returns:
            (grade, tier) 튜플
        """
        t = (
            self.config.grade_thresholds
            if self.config.grade_thresholds
            else {
                "S": 95,
                "A": 85,
                "B": 70,
                "C": 50,
            }
        )
        if score >= t.get("S", 95):
            return "S", QualityTier.RELEASE_READY
        if score >= t.get("A", 85):
            return "A", QualityTier.RELEASE_READY
        if score >= t.get("B", 70):
            return "B", QualityTier.NEEDS_MINOR_EDIT
        if score >= t.get("C", 50):
            return "C", QualityTier.REGENERATE
        return "F", QualityTier.REGENERATE
