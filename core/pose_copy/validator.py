"""
Pose Copy 검증기

포즈 복제 결과의 품질을 검수합니다.
- 레퍼런스 포즈와 생성 결과의 포즈 유사도 비교
- 소스 인물의 얼굴/착장 보존 여부 확인
- 구도 일치 여부 확인

검수 기준:
  pose_similarity    : 50% 가중치, >= 85 필수 (핵심 지표)
  face_preservation  : 20% 가중치, >= 90 필수
  outfit_preservation: 20% 가중치, >= 90 필수
  composition_match  : 10% 가중치, >= 80 필수

통과 기준: total_score >= 92
"""

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Union

from PIL import Image

from core.validators.base import (
    CommonValidationResult,
    QualityTier,
    ValidationConfig,
    WorkflowType,
    WorkflowValidator,
)
from core.validators.registry import ValidatorRegistry
from core.pose_copy.templates import VALIDATION_PROMPT

logger = logging.getLogger(__name__)


# 검수 가중치 및 기준값 (단일 소스, 하드코딩 금지)
_WEIGHTS = {
    "pose_similarity": 0.50,  # 핵심 지표 - 가장 높은 가중치
    "face_preservation": 0.20,
    "outfit_preservation": 0.20,
    "composition_match": 0.10,
}

_PASS_THRESHOLDS = {
    "pose_similarity": 85,  # 포즈 유사도 최소 기준
    "face_preservation": 90,  # 얼굴 보존 최소 기준
    "outfit_preservation": 90,  # 착장 보존 최소 기준
    "composition_match": 80,  # 구도 일치 최소 기준
}

_AUTO_FAIL_THRESHOLDS = {
    "pose_similarity": 70,  # 완전히 다른 포즈
    "face_preservation": 80,  # 다른 사람 얼굴
    "outfit_preservation": 80,  # 착장 완전 변경
}

_PASS_TOTAL = 92  # 통과 최소 총점


@ValidatorRegistry.register(WorkflowType.POSE_COPY)
class PoseCopyValidator(WorkflowValidator):
    """Pose Copy 검증기

    레퍼런스 이미지의 포즈를 소스 인물에 적용한 결과를 검수합니다.

    검수 항목:
    1. pose_similarity (50%): 레퍼런스 포즈와 생성 결과 포즈 일치도
    2. face_preservation (20%): 소스 얼굴 보존 여부
    3. outfit_preservation (20%): 소스 착장 보존 여부
    4. composition_match (10%): 레퍼런스 구도 일치 여부

    통과 기준: total_score >= 92

    Attributes:
        workflow_type: POSE_COPY
        config: 검증 설정
    """

    workflow_type = WorkflowType.POSE_COPY

    config = ValidationConfig(
        pass_total=_PASS_TOTAL,
        weights=_WEIGHTS,
        auto_fail_thresholds=_AUTO_FAIL_THRESHOLDS,
        priority_order=[
            "pose_similarity",  # 1순위: 핵심 목표
            "face_preservation",  # 2순위: 동일 인물
            "outfit_preservation",  # 3순위: 착장 유지
            "composition_match",  # 4순위: 구도 일치
        ],
        grade_thresholds={"S": 98, "A": 95, "B": 92, "C": 85},
    )

    # 실패 시 프롬프트 강화 규칙
    ENHANCEMENT_RULES = {
        "pose_similarity": [
            "CRITICAL: Copy pose from reference image EXACTLY - every limb position must match",
            "Pay close attention to arm positions - left arm and right arm separately",
            "Head angle and direction must precisely mirror the reference",
            "Body weight distribution and torso tilt must match reference",
            "Leg positions and stance width must replicate reference exactly",
        ],
        "face_preservation": [
            "The face MUST be the same person as described in source text",
            "Preserve all distinctive facial features: cheekbones, eye shape, nose, lips",
            "Maintain exact skin tone and undertone from source description",
            "Natural skin texture - avoid plastic or overly smooth finish",
            "Face angle should follow the pose naturally, not distort identity",
        ],
        "outfit_preservation": [
            "Outfit must exactly match source description - no substitutions",
            "Preserve ALL logo details, colors, and brand markings",
            "Maintain exact color palette - no color shifts allowed",
            "Preserve garment fit and silhouette as described",
            "All outfit items must be present - check for missing pieces",
        ],
        "composition_match": [
            "Person position in frame must match reference exactly",
            "Camera angle (eye-level/low/high) must replicate reference",
            "Framing (full body/half/close-up) must match reference",
            "Person size ratio in frame must be consistent with reference",
        ],
    }

    def __init__(self, client):
        """검증기 초기화

        Args:
            client: 초기화된 Gemini API 클라이언트 (google.genai.Client)
        """
        super().__init__(client)

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """Pose Copy 결과 검수

        Args:
            generated_img: 생성된 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "reference": 레퍼런스 이미지 목록 (포즈/구도 ground truth, 필수)
                - "source": 소스 이미지 목록 (얼굴/착장 ground truth, 필수)
            **kwargs: 추가 옵션 (현재 미사용)

        Returns:
            CommonValidationResult: 공통 검증 결과

        Raises:
            ValueError: reference 또는 source 이미지 누락 시
        """
        # 필수 이미지 확인
        reference_list = reference_images.get("reference", [])
        source_list = reference_images.get("source", [])

        if not reference_list:
            raise ValueError(
                "reference 이미지가 필요합니다 (reference_images['reference'])"
            )
        if not source_list:
            raise ValueError("source 이미지가 필요합니다 (reference_images['source'])")

        # 이미지 로드
        ref_img = self._load_image(reference_list[0])
        src_img = self._load_image(source_list[0])
        gen_img = self._load_image(generated_img)

        # VLM 검수 실행
        raw_result = self._run_vlm_validation(ref_img, src_img, gen_img)

        # 점수 추출 및 계산
        criteria_scores = self._extract_scores(raw_result)
        total_score = self._calculate_total_score(criteria_scores)

        # Auto-fail 체크
        auto_fail, auto_fail_reasons = self._check_auto_fail(
            raw_result, criteria_scores
        )

        # 개별 기준 통과 여부 체크
        issues = self._check_threshold_issues(criteria_scores)

        # 통과 판정
        passed = (
            not auto_fail
            and total_score >= _PASS_TOTAL
            and not issues  # 개별 기준 미달 없어야 통과
        )

        # 등급 산정
        grade, tier = self._calculate_grade(int(total_score))

        # 한국어 요약
        summary_kr = self._build_summary_kr(
            criteria_scores, total_score, passed, issues, auto_fail_reasons
        )

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=int(total_score),
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            criteria_scores=criteria_scores,
            summary_kr=summary_kr,
            raw_response=json.dumps(raw_result, ensure_ascii=False)
            if raw_result
            else "",
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 프롬프트 강화 규칙 반환

        Args:
            failed_criteria: 실패한 기준 목록

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트
        """
        lines = []
        # 우선순위 순서로 강화 규칙 수집
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        # 최대 10개 규칙으로 제한
        return "\n".join([f"- {line}" for line in lines[:10]])

    # =========================================================================
    # private methods
    # =========================================================================

    def _run_vlm_validation(
        self,
        ref_img: Image.Image,
        src_img: Image.Image,
        gen_img: Image.Image,
    ) -> dict:
        """VLM 검수 실행

        세 이미지를 VLM에 전달하여 step-by-step 비교 검수.

        Args:
            ref_img: 레퍼런스 이미지 (포즈/구도 ground truth)
            src_img: 소스 이미지 (얼굴/착장 ground truth)
            gen_img: 생성 결과 이미지

        Returns:
            dict: VLM 응답 파싱 결과
        """
        from google.genai import types
        from core.config import VISION_MODEL

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=VALIDATION_PROMPT),
                            self._pil_to_part(ref_img),  # Image 1: 레퍼런스
                            self._pil_to_part(src_img),  # Image 2: 소스
                            self._pil_to_part(gen_img),  # Image 3: 생성결과
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # 검수는 일관성 최우선
                    response_modalities=["TEXT"],
                ),
            )
            raw_text = response.candidates[0].content.parts[0].text
            return self._parse_json_response(raw_text)

        except Exception as e:
            logger.error(f"VLM 검수 실패: {e}")
            # VLM 호출 실패 시 재시도 유도를 위한 최저점 반환
            return self._fallback_result(str(e))

    def _parse_json_response(self, text: str) -> dict:
        """VLM 응답에서 JSON 파싱

        Args:
            text: VLM 응답 텍스트

        Returns:
            dict: 파싱된 결과
        """
        # JSON 블록 추출 시도
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {e}. 원문 응답으로 폴백")
            return self._fallback_result(f"JSON 파싱 실패: {e}")

    def _fallback_result(self, error_msg: str) -> dict:
        """VLM 실패 시 폴백 결과 (재생성 유도)

        Args:
            error_msg: 에러 메시지

        Returns:
            dict: 최저점 결과 dict
        """
        return {
            "pose_similarity": {
                "score": 0,
                "matching_elements": [],
                "differing_elements": ["VLM 분석 실패"],
                "issues": [error_msg],
                "reason": "VLM 분석 실패",
            },
            "face_preservation": {
                "score": 0,
                "same_person": False,
                "issues": [error_msg],
                "reason": "VLM 분석 실패",
            },
            "outfit_preservation": {
                "score": 0,
                "changed_elements": ["VLM 분석 실패"],
                "issues": [error_msg],
                "reason": "VLM 분석 실패",
            },
            "composition_match": {
                "score": 0,
                "person_position_match": False,
                "framing_match": False,
                "camera_angle_match": False,
                "issues": [error_msg],
                "reason": "VLM 분석 실패",
            },
            "auto_fail": True,
            "auto_fail_reasons": [f"VLM 검수 오류: {error_msg}"],
            "pass": False,
        }

    def _extract_scores(self, raw_result: dict) -> Dict[str, int]:
        """검수 결과에서 점수 추출

        Args:
            raw_result: VLM 응답 파싱 결과

        Returns:
            dict: 기준별 점수 (0~100)
        """
        scores = {}
        for key in _WEIGHTS:
            section = raw_result.get(key, {})
            if isinstance(section, dict):
                scores[key] = int(section.get("score", 0))
            else:
                scores[key] = 0
        return scores

    def _calculate_total_score(self, criteria_scores: Dict[str, int]) -> float:
        """가중 평균 총점 계산

        Args:
            criteria_scores: 기준별 점수

        Returns:
            float: 가중 평균 총점 (0.0~100.0)
        """
        total = 0.0
        for key, weight in _WEIGHTS.items():
            total += criteria_scores.get(key, 0) * weight
        return total

    def _check_auto_fail(
        self, raw_result: dict, criteria_scores: Dict[str, int]
    ) -> tuple:
        """Auto-fail 조건 체크

        Args:
            raw_result: VLM 응답 파싱 결과
            criteria_scores: 기준별 점수

        Returns:
            tuple: (auto_fail: bool, auto_fail_reasons: List[str])
        """
        reasons = []

        # VLM이 직접 판정한 auto_fail
        if raw_result.get("auto_fail", False):
            reasons.extend(raw_result.get("auto_fail_reasons", []))

        # 점수 기반 auto_fail 체크
        for key, threshold in _AUTO_FAIL_THRESHOLDS.items():
            score = criteria_scores.get(key, 0)
            if score < threshold:
                label_map = {
                    "pose_similarity": f"포즈 유사도 너무 낮음 ({score} < {threshold})",
                    "face_preservation": f"다른 사람 얼굴 ({score} < {threshold})",
                    "outfit_preservation": f"착장 완전 변경 ({score} < {threshold})",
                }
                reasons.append(
                    label_map.get(key, f"{key} 자동 탈락 ({score} < {threshold})")
                )

        return bool(reasons), reasons

    def _check_threshold_issues(self, criteria_scores: Dict[str, int]) -> List[str]:
        """개별 기준 통과 여부 체크 (auto_fail 제외)

        Args:
            criteria_scores: 기준별 점수

        Returns:
            List[str]: 기준 미달 항목 메시지 목록
        """
        issues = []
        label_map = {
            "pose_similarity": "포즈 유사도",
            "face_preservation": "얼굴 보존",
            "outfit_preservation": "착장 보존",
            "composition_match": "구도 일치",
        }
        for key, threshold in _PASS_THRESHOLDS.items():
            score = criteria_scores.get(key, 0)
            if score < threshold:
                issues.append(
                    f"{label_map.get(key, key)}: {score} (기준 {threshold} 미달)"
                )
        return issues

    def _build_summary_kr(
        self,
        criteria_scores: Dict[str, int],
        total_score: float,
        passed: bool,
        issues: List[str],
        auto_fail_reasons: List[str],
    ) -> str:
        """한국어 검수 요약 생성

        Args:
            criteria_scores: 기준별 점수
            total_score: 총점
            passed: 통과 여부
            issues: 기준 미달 항목
            auto_fail_reasons: auto_fail 사유

        Returns:
            str: 한국어 검수 요약 텍스트
        """
        판정 = "통과" if passed else "재생성 필요"
        lines = [
            "## 포즈 따라하기 검수 결과",
            "",
            "| 항목 | 점수 | 기준 | 통과 |",
            "|------|------|------|------|",
            f"| 포즈 유사도 | {criteria_scores.get('pose_similarity', 0)} | >= {_PASS_THRESHOLDS['pose_similarity']} | {'O' if criteria_scores.get('pose_similarity', 0) >= _PASS_THRESHOLDS['pose_similarity'] else 'X'} |",
            f"| 얼굴 보존 | {criteria_scores.get('face_preservation', 0)} | >= {_PASS_THRESHOLDS['face_preservation']} | {'O' if criteria_scores.get('face_preservation', 0) >= _PASS_THRESHOLDS['face_preservation'] else 'X'} |",
            f"| 착장 보존 | {criteria_scores.get('outfit_preservation', 0)} | >= {_PASS_THRESHOLDS['outfit_preservation']} | {'O' if criteria_scores.get('outfit_preservation', 0) >= _PASS_THRESHOLDS['outfit_preservation'] else 'X'} |",
            f"| 구도 일치 | {criteria_scores.get('composition_match', 0)} | >= {_PASS_THRESHOLDS['composition_match']} | {'O' if criteria_scores.get('composition_match', 0) >= _PASS_THRESHOLDS['composition_match'] else 'X'} |",
            "",
            f"**총점**: {total_score:.1f}/100 | **판정**: {판정}",
        ]

        if auto_fail_reasons:
            lines.append("\n### 자동 탈락 사유")
            for reason in auto_fail_reasons:
                lines.append(f"- {reason}")
        elif issues:
            lines.append("\n### 기준 미달 항목")
            for issue in issues:
                lines.append(f"- {issue}")

        return "\n".join(lines)
