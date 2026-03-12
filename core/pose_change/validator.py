"""
포즈 변경 검증기

포즈 변경 워크플로의 결과 이미지를 소스 이미지와 비교하여 품질 판정.

검증 기준 및 가중치:
  face_identity       30%  (>= 90 필수)
  outfit_preservation 25%  (>= 90 필수)
  pose_correctness    25%  (>= 85 필수)
  physics_plausibility 15% (>= 80 필수)
  lighting_consistency  5% (>= 75 권장)

통과 기준: 총점 >= 88
"""

import json
from typing import Any, Dict, List, Union
from pathlib import Path

from PIL import Image
from google.genai import types

from core.config import VISION_MODEL
from core.validators.base import (
    CommonValidationResult,
    ValidationConfig,
    WorkflowType,
    WorkflowValidator,
)
from core.validators.registry import ValidatorRegistry
from core.pose_change.templates import VALIDATION_PROMPT


def _parse_json_response(text: str) -> dict:
    """VLM 응답에서 JSON 추출 및 파싱."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


def _compute_total_score(scores: Dict[str, int], weights: Dict[str, float]) -> int:
    """가중 평균 총점 계산."""
    total = sum(scores.get(k, 0) * w for k, w in weights.items())
    return round(total)


@ValidatorRegistry.register(WorkflowType.POSE_CHANGE)
class PoseChangeValidator(WorkflowValidator):
    """포즈 변경 검증기

    소스 이미지와 생성 이미지를 함께 VLM에 전달하여 5개 기준으로 비교 검수.

    검증 기준:
      face_identity       30%  >= 90
      outfit_preservation 25%  >= 90
      pose_correctness    25%  >= 85
      physics_plausibility 15% >= 80
      lighting_consistency  5% >= 75

    통과 기준: 총점 >= 88

    Auto-Fail 트리거:
      - face_identity < 80 (다른 사람)
      - outfit_preservation 색상/로고 불일치
      - 물리적으로 불가능한 포즈
      - 손가락 6개 이상
      - 체형 비율 크게 변경
    """

    workflow_type = WorkflowType.POSE_CHANGE

    config = ValidationConfig(
        pass_total=88,
        weights={
            "face_identity": 0.30,
            "outfit_preservation": 0.25,
            "pose_correctness": 0.25,
            "physics_plausibility": 0.15,
            "lighting_consistency": 0.05,
        },
        auto_fail_thresholds={
            "face_identity": 80,  # 80 미만이면 자동 탈락
            "outfit_preservation": 70,  # 70 미만이면 자동 탈락
            "physics_plausibility": 50,
        },
        priority_order=[
            "face_identity",
            "outfit_preservation",
            "pose_correctness",
            "physics_plausibility",
            "lighting_consistency",
        ],
        grade_thresholds={"S": 95, "A": 90, "B": 88, "C": 75},
    )

    # 재시도 프롬프트 강화 규칙 (실패 기준별)
    ENHANCEMENT_RULES: Dict[str, List[str]] = {
        "face_identity": [
            "CRITICAL: Preserve exact facial identity - same person as source image",
            "Match skin tone precisely: do not alter complexion",
            "Keep identical hair style, color, and length",
            "Maintain same facial structure and expression",
        ],
        "outfit_preservation": [
            "CRITICAL: All outfit elements must be EXACTLY reproduced",
            "Preserve exact colors - no saturation or hue shifts",
            "Keep all logos with correct text, position, and color",
            "Maintain garment fit and silhouette exactly",
        ],
        "pose_correctness": [
            "New pose must exactly match the target description",
            "Ensure natural weight distribution for the pose",
            "Physically plausible joints and limb angles only",
        ],
        "physics_plausibility": [
            "All fingers must look natural - exactly 5 fingers per hand",
            "Ground contact must be correct for the pose",
            "Center of gravity must be balanced",
        ],
        "lighting_consistency": [
            "Adapt lighting naturally to the new pose",
            "Ensure face is well-lit with no harsh shadows",
            "Avoid warm/yellow color cast on skin",
        ],
    }

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs: Any,
    ) -> CommonValidationResult:
        """포즈 변경 결과 이미지 검증.

        소스 이미지(IMAGE 1)와 생성 이미지(IMAGE 2)를 VLM에 전달하여
        5개 기준을 단계별로 비교 분석.

        Args:
            generated_img: 생성된 결과 이미지 (경로 또는 PIL Image)
            reference_images: 참조 이미지 딕셔너리
                - "source": 원본 소스 이미지 목록 (필수, 첫 번째 항목 사용)
            **kwargs: 추가 옵션
                - target_pose: 목표 포즈 설명 (검수 프롬프트 컨텍스트용)

        Returns:
            CommonValidationResult: 통합 검증 결과
        """
        # 이미지 로드
        result_img = self._load_image(generated_img)
        source_imgs = reference_images.get("source", [])
        if not source_imgs:
            raise ValueError("reference_images에 'source' 키가 필요합니다.")
        source_img = self._load_image(source_imgs[0])

        # VLM 검수 호출 (소스 + 결과 이미지 동시 전달)
        raw = self._call_vlm(source_img, result_img, kwargs.get("target_pose", ""))

        # 항목별 점수 추출
        criteria_scores = {
            "face_identity": raw.get("face_identity", {}).get("score", 0),
            "outfit_preservation": raw.get("outfit_preservation", {}).get("score", 0),
            "pose_correctness": raw.get("pose_correctness", {}).get("score", 0),
            "physics_plausibility": raw.get("physics_plausibility", {}).get("score", 0),
            "lighting_consistency": raw.get("lighting_consistency", {}).get("score", 0),
        }

        # 총점 계산
        total_score = _compute_total_score(criteria_scores, self.config.weights)

        # Auto-Fail 판정
        auto_fail_triggers: List[str] = raw.get("auto_fail_triggers", [])
        # 임계값 미달 항목 추가 체크
        for criterion, threshold in self.config.auto_fail_thresholds.items():
            if criteria_scores.get(criterion, 100) < threshold:
                trigger_key = f"{criterion}_below_{threshold}"
                if trigger_key not in auto_fail_triggers:
                    auto_fail_triggers.append(trigger_key)

        auto_fail = bool(auto_fail_triggers)

        # 이슈 목록 수집
        issues: List[str] = []
        for key in self.config.priority_order:
            section = raw.get(key, {})
            for issue in section.get("issues", []):
                issues.append(f"[{key}] {issue}")

        # 통과 판정 (auto_fail이면 무조건 탈락)
        passed = (not auto_fail) and (total_score >= self.config.pass_total)

        # 등급 및 티어
        grade, tier = self._calculate_grade(total_score)

        # 한국어 요약
        summary_kr = self._build_summary_kr(
            total_score=total_score,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_triggers=auto_fail_triggers,
            criteria_scores=criteria_scores,
        )

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_triggers,
            issues=issues,
            criteria_scores=criteria_scores,
            summary_kr=summary_kr,
            raw_response=json.dumps(raw, ensure_ascii=False),
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패한 검증 기준에 따른 프롬프트 강화 규칙 반환.

        우선순위 순서로 최대 8개 규칙 반환.

        Args:
            failed_criteria: 실패한 기준 목록 (예: ["face_identity", "outfit_preservation"])

        Returns:
            str: 프롬프트에 추가할 강화 규칙 텍스트 (줄 단위)
        """
        lines: List[str] = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in self.ENHANCEMENT_RULES:
                lines.extend(self.ENHANCEMENT_RULES[criterion])
        return "\n".join(f"- {line}" for line in lines[:8])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_vlm(
        self,
        source_img: Image.Image,
        result_img: Image.Image,
        target_pose: str,
    ) -> dict:
        """VLM에 소스+결과 이미지 전달하여 검수 결과 JSON 반환.

        Args:
            source_img: 원본 소스 이미지 (PIL Image)
            result_img: 생성된 결과 이미지 (PIL Image)
            target_pose: 목표 포즈 설명 (컨텍스트 보강용)

        Returns:
            dict: 파싱된 VLM 검수 결과
        """
        # 목표 포즈를 프롬프트에 삽입
        prompt = VALIDATION_PROMPT
        if target_pose:
            prompt = prompt.replace(
                "- Target = ? (describe expected pose)",
                f"- Target = {target_pose}",
            )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=prompt),
                    self._pil_to_part(source_img),  # IMAGE 1: SOURCE
                    self._pil_to_part(result_img),  # IMAGE 2: RESULT
                ],
            )
        ]

        response = self.client.models.generate_content(
            model=VISION_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_modalities=["TEXT"],
            ),
        )

        text = response.candidates[0].content.parts[0].text
        return _parse_json_response(text)

    def _build_summary_kr(
        self,
        total_score: int,
        grade: str,
        passed: bool,
        auto_fail: bool,
        auto_fail_triggers: List[str],
        criteria_scores: Dict[str, int],
    ) -> str:
        """검수 결과 한국어 요약 생성.

        CLAUDE.md 검수 결과 출력 규칙 준수 (표 형식).

        Args:
            total_score: 가중 합산 총점
            grade: 등급 문자 (S/A/B/C/F)
            passed: 통과 여부
            auto_fail: 자동 탈락 여부
            auto_fail_triggers: 자동 탈락 사유 목록
            criteria_scores: 항목별 점수 딕셔너리

        Returns:
            str: 마크다운 표 형식 한국어 요약
        """
        # 항목 한국어 매핑
        labels = {
            "face_identity": "얼굴 동일성",
            "outfit_preservation": "착장 보존",
            "pose_correctness": "포즈 정확도",
            "physics_plausibility": "물리 타당성",
            "lighting_consistency": "조명 일관성",
        }
        thresholds = {
            "face_identity": 90,
            "outfit_preservation": 90,
            "pose_correctness": 85,
            "physics_plausibility": 80,
            "lighting_consistency": 75,
        }

        rows = []
        for key in self.config.priority_order:
            score = criteria_scores.get(key, 0)
            thr = thresholds[key]
            ok = "O" if score >= thr else "X"
            rows.append(f"| {labels[key]} | {score} | >={thr} | {ok} |")

        table = "\n".join(rows)
        verdict = "통과" if passed else ("자동 탈락" if auto_fail else "재생성 필요")

        summary = (
            "## 검수 결과\n\n"
            "| 항목 | 점수 | 기준 | 통과 |\n"
            "|------|------|------|------|\n"
            f"{table}\n\n"
            f"**총점**: {total_score}/100 | **등급**: {grade} | **판정**: {verdict}"
        )

        if auto_fail_triggers:
            triggers_kr = "\n".join(f"- {t}" for t in auto_fail_triggers)
            summary += f"\n\n### 자동 탈락 사유\n{triggers_kr}"

        return summary
