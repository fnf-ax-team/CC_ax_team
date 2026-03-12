"""
4K 업스케일 검증기

원본과 업스케일 결과를 비교하여 내용 변경 여부를 확인.
모든 요소(구도, 인물, 착장, 색감)가 보존되었는지 검증.
"""

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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


# 검증 기준 (한국어)
CRITERION_NAMES_KR = {
    "composition_preservation": "구도 보존",
    "person_preservation": "인물 보존",
    "outfit_preservation": "착장 보존",
    "color_fidelity": "색감 보존",
    "detail_enhancement": "디테일 향상",
}

# 가중치
WEIGHTS = {
    "composition_preservation": 0.25,
    "person_preservation": 0.25,
    "outfit_preservation": 0.20,
    "color_fidelity": 0.15,
    "detail_enhancement": 0.15,
}

# 프롬프트 강화 규칙
ENHANCEMENT_RULES = {
    "composition_preservation": "DO NOT crop or reframe. Keep EXACT same composition and framing.",
    "person_preservation": "Keep EXACT same face, expression, pose, body type. Do NOT change the person.",
    "outfit_preservation": "Keep EXACT same clothing colors, logos, details, fit. Do NOT change outfits.",
    "color_fidelity": "Keep EXACT same color temperature, lighting, color grading. No warm/cool shift.",
    "detail_enhancement": "Enhance sharpness and fine detail. Improve texture clarity.",
}

# VLM 검증 프롬프트 (step-by-step 강제 — VLM 검수 프롬프트 작성 원칙 준수)
VALIDATION_PROMPT = """You are comparing an ORIGINAL image with its 4K UPSCALED version.
The upscaled version should be IDENTICAL to the original, only with higher resolution.

Compare these two images and score each criterion (0-100).

### 1. composition_preservation (구도 보존)

[STEP 1] ORIGINAL 분석: 프레이밍=?, 크롭=?, 카메라 앵글=?
[STEP 2] UPSCALED 분석: 프레이밍=?, 크롭=?, 카메라 앵글=?
[STEP 3] 비교 및 감점:
- 프레이밍: 같음(0) / 다름(-30)
- 크롭: 같음(0) / 다름(-30)
- 앵글: 같음(0) / 다름(-20)
- 요소 추가/삭제: 없음(0) / 있음(-20)
[STEP 4] 최종 = 100 - 감점합계

reason 필수 형식: "ORIG:전신+아이레벨, UP:전신+아이레벨, 감점:0"

### 2. person_preservation (인물 보존)

[STEP 1] ORIGINAL 분석: 얼굴 특징=?, 표정=?, 포즈=?, 체형=?
[STEP 2] UPSCALED 분석: 얼굴 특징=?, 표정=?, 포즈=?, 체형=?
[STEP 3] 비교 및 감점:
- 얼굴 동일: 같음(0) / 미세 차이(-15) / 다름(-50)
- 표정: 같음(0) / 다름(-20)
- 포즈: 같음(0) / 다름(-20)
- 체형: 같음(0) / 다름(-15)
[STEP 4] 최종 = 100 - 감점합계

reason 필수 형식: "ORIG:여성+미소+서있음, UP:여성+미소+서있음, 감점:0"

### 3. outfit_preservation (착장 보존)

[STEP 1] ORIGINAL 분석: 아이템=?, 색상=?, 로고=?, 핏=?
[STEP 2] UPSCALED 분석: 아이템=?, 색상=?, 로고=?, 핏=?
[STEP 3] 비교 및 감점:
- 아이템 누락/추가: 없음(0) / 있음(-40)
- 색상 불일치: 없음(0) / 있음(-25)
- 로고 변경: 없음(0) / 있음(-25)
- 핏 변경: 없음(0) / 있음(-10)
[STEP 4] 최종 = 100 - 감점합계

reason 필수 형식: "ORIG:흰티+청바지, UP:흰티+청바지, 감점:0"

### 4. color_fidelity (색감 보존)

[STEP 1] ORIGINAL 분석: 색온도=?, 밝기=?, 대비=?, 채도=?
[STEP 2] UPSCALED 분석: 색온도=?, 밝기=?, 대비=?, 채도=?
[STEP 3] 비교 및 감점:
- 색온도 변화: 없음(0) / 미세(-10) / 큰 변화(-30)
- 밝기 변화: 없음(0) / 미세(-10) / 큰 변화(-25)
- 채도 변화: 없음(0) / 미세(-10) / 큰 변화(-20)
[STEP 4] 최종 = 100 - 감점합계

reason 필수 형식: "ORIG:쿨톤+자연광, UP:쿨톤+자연광, 감점:0"

### 5. detail_enhancement (디테일 향상)

Score how much the resolution/detail actually improved:
- 100: 선명도 크게 향상, 미세 디테일 살아남
- 80: 선명도 약간 향상
- 60: 변화 거의 없음 (원본과 비슷)
- 40: 오히려 흐려짐 or 아티팩트 발생

reason 필수 형식: "선명도:향상/유지/저하, 디테일:향상/유지/저하"

---

OUTPUT FORMAT (JSON only, no markdown):
{
  "composition_preservation": {"score": 0-100, "reason": "..."},
  "person_preservation": {"score": 0-100, "reason": "..."},
  "outfit_preservation": {"score": 0-100, "reason": "..."},
  "color_fidelity": {"score": 0-100, "reason": "..."},
  "detail_enhancement": {"score": 0-100, "reason": "..."}
}
"""


@ValidatorRegistry.register(WorkflowType.UPSCALE)
class UpscaleValidator(WorkflowValidator):
    """4K 업스케일 검증기

    원본과 업스케일 결과를 VLM으로 비교하여
    내용 변경 여부를 확인.
    """

    workflow_type = WorkflowType.UPSCALE
    config = ValidationConfig(
        pass_total=90,
        weights=WEIGHTS,
        auto_fail_thresholds={
            "person_preservation": 90,
            "outfit_preservation": 85,
            "composition_preservation": 90,
        },
        priority_order=[
            "person_preservation",
            "outfit_preservation",
            "composition_preservation",
            "color_fidelity",
            "detail_enhancement",
        ],
    )

    def _image_to_part(self, img: Image.Image) -> types.Part:
        """이미지를 Gemini Part로 변환"""
        buf = BytesIO()
        # 검증용이므로 적절한 크기로 리사이즈
        max_size = 1024
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        img.save(buf, format="JPEG", quality=90)
        return types.Part(
            inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())
        )

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """업스케일 결과 검증

        Args:
            generated_img: 업스케일된 이미지
            reference_images: {"source": [원본 이미지]}

        Returns:
            CommonValidationResult
        """
        upscaled = self._load_image(generated_img)

        # 원본 이미지 가져오기
        source_list = reference_images.get("source", [])
        if not source_list:
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=["원본 이미지 없음"],
                summary_kr="원본 이미지가 제공되지 않아 검증 불가",
            )

        original = self._load_image(source_list[0])

        # VLM 비교 요청
        try:
            original_part = self._image_to_part(original)
            upscaled_part = self._image_to_part(upscaled)

            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="[ORIGINAL IMAGE]"),
                            original_part,
                            types.Part(text="[UPSCALED IMAGE]"),
                            upscaled_part,
                            types.Part(text=VALIDATION_PROMPT),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(temperature=0.1),
            )

            raw_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    raw_text += part.text

            return self._parse_response(raw_text)

        except Exception as e:
            print(f"  [VALIDATION_ERROR] {e}")
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=[f"검증 실패: {str(e)}"],
                summary_kr=f"VLM 검증 중 오류 발생: {str(e)}",
            )

    def _parse_response(self, raw_text: str) -> CommonValidationResult:
        """VLM 응답 파싱"""
        # JSON 추출
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if not json_match:
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=["VLM 응답 파싱 실패"],
                raw_response=raw_text,
                summary_kr="VLM 응답에서 JSON을 추출할 수 없음",
            )

        try:
            scores_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return CommonValidationResult(
                workflow_type=self.workflow_type,
                total_score=0,
                tier=QualityTier.REGENERATE,
                grade="F",
                passed=False,
                auto_fail=True,
                auto_fail_reasons=["JSON 파싱 실패"],
                raw_response=raw_text,
                summary_kr="VLM 응답 JSON 파싱 실패",
            )

        # 점수 추출
        criteria_scores = {}
        for key in WEIGHTS:
            entry = scores_data.get(key, {})
            if isinstance(entry, dict):
                score = entry.get("score", 0)
                reason = entry.get("reason", "")
            else:
                score = int(entry) if entry else 0
                reason = ""
            criteria_scores[key] = {
                "score": int(score),
                "reason": reason,
                "name_kr": CRITERION_NAMES_KR.get(key, key),
            }

        # 가중 평균 총점
        total_score = sum(criteria_scores[k]["score"] * WEIGHTS[k] for k in WEIGHTS)
        total_score = round(total_score)

        # Auto-fail 확인
        auto_fail = False
        auto_fail_reasons = []
        issues = []
        for key, threshold in self.config.auto_fail_thresholds.items():
            score = criteria_scores.get(key, {}).get("score", 0)
            if score < threshold:
                auto_fail = True
                name_kr = CRITERION_NAMES_KR.get(key, key)
                auto_fail_reasons.append(f"{name_kr}: {score} < {threshold}")
                issues.append(f"{name_kr} 미달 ({score}/{threshold})")

        # 등급 산정
        passed = total_score >= self.config.pass_total and not auto_fail
        if auto_fail:
            grade = "F"
            tier = QualityTier.REGENERATE
        elif total_score >= 95:
            grade = "S"
            tier = QualityTier.RELEASE_READY
        elif total_score >= 90:
            grade = "A"
            tier = QualityTier.RELEASE_READY
        elif total_score >= 85:
            grade = "B"
            tier = QualityTier.NEEDS_MINOR_EDIT
        elif total_score >= 70:
            grade = "C"
            tier = QualityTier.REGENERATE
        else:
            grade = "F"
            tier = QualityTier.REGENERATE

        # 한국어 요약
        criteria_summary = ", ".join(
            f"{v['name_kr']}={v['score']}" for v in criteria_scores.values()
        )
        summary_kr = f"총점: {total_score} | 등급: {grade} | {criteria_summary}"

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
        """실패 기준에 따른 프롬프트 강화 규칙"""
        rules = []
        for criterion in failed_criteria:
            rule = ENHANCEMENT_RULES.get(criterion)
            if rule:
                rules.append(f"- {rule}")
        return "\n".join(rules) if rules else ""

    def should_retry(self, result: CommonValidationResult) -> bool:
        """재시도 여부 — auto_fail이 아닌 경우만 재시도"""
        if result.passed:
            return False
        if result.auto_fail:
            return (
                True  # 업스케일은 auto_fail도 재시도 (원본 변경은 재생성으로 해결 가능)
            )
        return result.total_score < self.config.pass_total
