"""
배경 교체 검증기 - 9-criteria 단일 검증

검증 기준 (9개):
1. model_preservation (25%) - 인물 보존 (필수 100)
2. relight_naturalness (15%) - 리라이트 자연스러움
3. lighting_match (12%) - 조명 일치
4. ground_contact (12%) - 접지감
5. physics_plausibility (10%) - 물리 타당성 (필수 50 이상)
6. edge_quality (8%) - 경계 품질
7. prop_style_consistency (8%) - 소품 스타일
8. color_temperature_compliance (5%) - 색온도 (필수 80 이상)
9. perspective_match (5%) - 원근 일치

Pass 조건:
- model_preservation = 100 (필수)
- physics_plausibility >= 50 (필수)
- color_temperature_compliance >= 80 (필수)
- total_score >= 90
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Union
from pathlib import Path
from PIL import Image

from google import genai
from google.genai import types

from core.config import VISION_MODEL
from core.utils import pil_to_part


# ============================================================
# 검증 결과 데이터클래스
# ============================================================


@dataclass
class BackgroundSwapValidationResult:
    """배경교체 검증 결과 (9-criteria)"""

    # 9개 기준 점수 (0-100)
    model_preservation: int = 0  # 25% - =100 필수
    relight_naturalness: int = 0  # 15%
    lighting_match: int = 0  # 12%
    ground_contact: int = 0  # 10%
    physics_plausibility: int = 0  # 10% - >=50 필수
    edge_quality: int = 0  # 8%
    prop_style_consistency: int = 0  # 5%
    color_temperature_compliance: int = 0  # 5% - >=80 필수
    perspective_match: int = 0  # 10% - >=70 필수 (NEW!)

    # 추가 정보
    perspective_reason: str = ""  # 원근감 비교 근거
    issues: List[str] = field(default_factory=list)
    raw_response: str = ""

    @property
    def total_score(self) -> int:
        """가중치 적용 총점 (perspective_match 10%로 상향)"""
        return int(
            self.model_preservation * 0.25
            + self.relight_naturalness * 0.15
            + self.lighting_match * 0.12
            + self.ground_contact * 0.10
            + self.physics_plausibility * 0.10
            + self.edge_quality * 0.08
            + self.prop_style_consistency * 0.05
            + self.color_temperature_compliance * 0.05
            + self.perspective_match * 0.10  # 5% → 10%
        )

    @property
    def passed(self) -> bool:
        """Pass 조건 확인 - 총점 95점 이상 + 필수 항목 충족"""
        return (
            self.model_preservation == 100
            and self.physics_plausibility >= 50
            and self.color_temperature_compliance >= 80
            and self.perspective_match >= 70
            and self.total_score >= 95  # 90 → 95 (릴리즈 기준)
        )

    @property
    def grade(self) -> str:
        """등급 반환"""
        if self.passed and self.total_score >= 95:
            return "S"
        elif self.passed:
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
            "model_preservation": self.model_preservation,
            "relight_naturalness": self.relight_naturalness,
            "lighting_match": self.lighting_match,
            "ground_contact": self.ground_contact,
            "physics_plausibility": self.physics_plausibility,
            "edge_quality": self.edge_quality,
            "prop_style_consistency": self.prop_style_consistency,
            "color_temperature_compliance": self.color_temperature_compliance,
            "perspective_match": self.perspective_match,
            "perspective_reason": self.perspective_reason,
            "total_score": self.total_score,
            "passed": self.passed,
            "grade": self.grade,
            "issues": self.issues,
        }

    def format_korean(self) -> str:
        """검수표 템플릿 형식으로 출력 (skills/fnf-image-gen/배경교체_background-swap/검수표_템플릿.md 참조)"""

        def check(score, threshold, is_equal=False):
            if is_equal:
                return "O" if score == threshold else "X"
            return "O" if score >= threshold else "X"

        lines = [
            "## 검수 결과",
            "",
            "| 기준 | 비중 | Pass 조건 | 점수 | 통과 |",
            "|------|------|-----------|------|------|",
            f"| 인물 보존 | 25% | = 100 | {self.model_preservation} | {check(self.model_preservation, 100, True)} |",
            f"| 리라이트 자연스러움 | 15% | - | {self.relight_naturalness} | - |",
            f"| 조명 일치 | 12% | - | {self.lighting_match} | - |",
            f"| 접지감 | 10% | - | {self.ground_contact} | - |",
            f"| 물리 타당성 | 10% | >= 50 | {self.physics_plausibility} | {check(self.physics_plausibility, 50)} |",
            f"| 경계 품질 | 8% | - | {self.edge_quality} | - |",
            f"| 스타일 일치 | 5% | - | {self.prop_style_consistency} | - |",
            f"| 색온도 준수 | 5% | >= 80 | {self.color_temperature_compliance} | {check(self.color_temperature_compliance, 80)} |",
            f"| 원근 일치 | 10% | >= 70 | {self.perspective_match} | {check(self.perspective_match, 70)} |",
            "",
            f"**총점**: {self.total_score}/100 | **등급**: {self.grade} | **판정**: {'PASS' if self.passed else 'FAIL'}",
        ]

        if self.issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in self.issues:
                lines.append(f"- {issue}")

        return "\n".join(lines)


# ============================================================
# 검증 프롬프트
# ============================================================

VALIDATION_PROMPT_BASE = """배경 교체 품질 검수. 9개 항목 0-100점.

## 필수 항목 (이것 중 하나라도 기준 미달이면 FAIL)
1. model_preservation (25%): 인물이 원본과 100% 동일한가?
   - 얼굴, 포즈, 의상, 스케일 모두 일치해야 100점
   - 조금이라도 다르면 0점

2. physics_plausibility (10%): 물리적으로 타당한가?
   - 앉아있으면 의자/벤치 있어야 함
   - 기대고 있으면 벽/기둥 있어야 함
   - 지지대 없이 앉기/기대기 = 0점

3. color_temperature_compliance (5%): 누런 톤 없는가?
   - 쿨/뉴트럴 톤 = 100점
   - 약간 따뜻함 = 50점
   - 골든/앰버 톤 = 0점 (FAIL)

4. perspective_match (10%): ★★★ 필수 - 원본과 카메라 앵글/원근감 일치 ★★★
   - >= 70점 필수 (미달 시 FAIL)
   - 반드시 아래 STEP을 따라 비교할 것

## 일반 항목
5. relight_naturalness (15%): 인물에 배경 조명이 자연스럽게 반영되었는가?
6. lighting_match (12%): 광원 방향이 인물과 배경 간에 일치하는가?
7. ground_contact (10%): 발/바닥 접촉과 그림자가 자연스러운가?
8. edge_quality (8%): 인물 외곽선이 깔끔한가? (달무리/글로우 없음)
9. prop_style_consistency (5%): 소품과 배경 스타일이 조화로운가?

## ★★★ perspective_match 필수 비교 절차 ★★★

[STEP 1] 원본(ORIGINAL) 분석:
- 카메라 앵글 = ? (low-angle/eye-level/high-angle)
- 수평선 위치 = ? (상단/중앙/하단)
- 바닥 보임 정도 = ? (안보임/조금/많이)

[STEP 2] 결과물(GENERATED) 분석:
- 카메라 앵글 = ?
- 수평선 위치 = ?
- 바닥 보임 정도 = ?

[STEP 3] 비교 및 감점:
- 앵글 불일치: low→eye(-30), low→high(-50), eye→high(-20)
- 수평선 위치 불일치: 1단계(-15), 2단계(-30)
- 바닥 보임 불일치: 원본은 안보이는데 결과물은 많이 보임(-40)

[STEP 4] 최종 점수 = 100 - 감점 합계

perspective_reason 필수 형식: "ORIG:low-angle+바닥안보임, GEN:eye-level+바닥많이보임, 감점:-70"

## 점수 기준
- 100: 완벽
- 90~99: 우수
- 80~89: 양호
- 70~79: 미흡
- 50~69: 불량
- 0~49: 실패

## 출력 (JSON만 반환)
```json
{
  "model_preservation": 점수,
  "relight_naturalness": 점수,
  "lighting_match": 점수,
  "ground_contact": 점수,
  "physics_plausibility": 점수,
  "edge_quality": 점수,
  "prop_style_consistency": 점수,
  "color_temperature_compliance": 점수,
  "perspective_match": 점수,
  "perspective_reason": "ORIG:..., GEN:..., 감점:...",
  "issues": ["이슈1", "이슈2"]
}
```"""


# VFX 분석 결과를 포함한 동적 프롬프트 생성
def build_validation_prompt(vfx_analysis: dict = None) -> str:
    """VFX 분석 결과를 포함한 검증 프롬프트 생성"""
    prompt = VALIDATION_PROMPT_BASE

    if vfx_analysis and vfx_analysis.get("data"):
        data = vfx_analysis["data"]
        geom = data.get("geometry", {})
        pose = data.get("pose_dependency", {})

        vfx_context = "\n\n## ★★★ 원본 VFX 분석 결과 (검증 기준으로 사용) ★★★\n"

        # 카메라 지오메트리
        if geom:
            perspective = geom.get("perspective", "eye-level")
            horizon_y = geom.get("horizon_y", 0.5)
            vfx_context += f"""
### 원본 카메라 정보:
- 카메라 앵글: {perspective}
- 수평선 위치: {horizon_y} (0=상단, 0.5=중앙, 1=하단)
- low-angle이면 바닥이 거의 안 보이고 건물이 위로 솟아보여야 함
- high-angle이면 바닥이 많이 보이고 위에서 내려다보는 구도
"""

        # 포즈 의존성
        if pose:
            pose_type = pose.get("pose_type", "standing")
            support_required = pose.get("support_required", False)
            support_type = pose.get("support_type", "")
            vfx_context += f"""
### 원본 포즈 정보:
- 포즈 타입: {pose_type}
- 지지대 필요: {support_required}
- 지지대 종류: {support_type}
- 기대는 포즈면 기댈 대상(난간/벽/기둥)이 결과물에도 있어야 함
"""

        prompt = vfx_context + "\n" + prompt

    return prompt


# 기존 호환성을 위한 기본 프롬프트
VALIDATION_PROMPT = VALIDATION_PROMPT_BASE


# ============================================================
# 재시도 프롬프트 보강 테이블
# ============================================================

ENHANCEMENT_RULES = {
    "FACE_CHANGED": {
        "key": "model_preservation",
        "threshold": 95,
        "fix": "얼굴 고정: 이목구비, 표정, 시선 방향 원본 복사. EXACT SAME FACE.",
    },
    "POSE_MISMATCH": {
        "key": "model_preservation",
        "threshold": 90,
        "fix": "포즈 고정: 팔, 다리 각도 픽셀 단위 일치. DO NOT change pose.",
    },
    "SCALE_SHRUNK": {
        "key": "model_preservation",
        "threshold": 85,
        "fix": "스케일 고정: 줌아웃 금지, 인물 크기 비율 유지. DO NOT SHRINK.",
    },
    "CLOTHING_CHANGED": {
        "key": "model_preservation",
        "threshold": 90,
        "fix": "의상 보존: 의상 디테일, 로고, 텍스처 유지.",
    },
    "RELIGHT_FLAT": {
        "key": "relight_naturalness",
        "threshold": 70,
        "fix": "리라이트: 인물에 배경 조명 반영, 적절한 그림자 추가.",
    },
    "LIGHTING_MISMATCH": {
        "key": "lighting_match",
        "threshold": 80,
        "fix": "조명 동기화: 광원 방향, 그림자 일치.",
    },
    "GROUND_POOR": {
        "key": "ground_contact",
        "threshold": 80,
        "fix": "접지 강화: 발밑 그림자 생성, 바닥 안착.",
    },
    "PHYSICS_INCOMPATIBLE": {
        "key": "physics_plausibility",
        "threshold": 50,
        "fix": "지지대 강제: 앉기/기대기 포즈에 구조물 생성. MUST add support.",
    },
    "EDGE_ARTIFACTS": {
        "key": "edge_quality",
        "threshold": 85,
        "fix": "경계 최적화: 글로우, 달무리 제거.",
    },
    "WARM_CAST": {
        "key": "color_temperature_compliance",
        "threshold": 80,
        "fix": "색온도: 누런 톤 제거, 쿨/뉴트럴 유지. NO golden/amber cast.",
    },
    "PERSPECTIVE_MISMATCH": {
        "key": "perspective_match",
        "threshold": 80,
        "fix": "원근 동기화: 카메라 앵글, 소실점 일치.",
    },
}


# ============================================================
# 검증기 클래스
# ============================================================


class BackgroundSwapValidator:
    """배경교체 검증기 (9-criteria)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self._vfx_analysis = None  # VFX 분석 결과 저장

    def set_vfx_analysis(self, vfx_analysis: dict):
        """VFX 분석 결과 설정 (검증 시 원근감 비교에 사용)"""
        self._vfx_analysis = vfx_analysis

    def validate(
        self, generated_image: Image.Image, source_image: Image.Image = None
    ) -> BackgroundSwapValidationResult:
        """생성된 이미지 검증 (VFX 분석 결과 포함)"""
        try:
            # VFX 분석 결과가 있으면 동적 프롬프트 사용
            prompt = build_validation_prompt(self._vfx_analysis)

            parts = [types.Part(text=prompt)]

            parts.append(types.Part(text="\n\n[Generated Image - 검증 대상]:"))
            parts.append(pil_to_part(generated_image, max_size=1024))

            if source_image:
                parts.append(
                    types.Part(
                        text="\n\n[Original Image - 원본 (카메라 앵글/포즈 비교 기준)]:"
                    )
                )
                parts.append(
                    pil_to_part(source_image, max_size=1024)
                )  # 512→1024로 상향 (원근감 비교용)

            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_mime_type="application/json"
                ),
            )

            data = json.loads(response.text)

            return BackgroundSwapValidationResult(
                model_preservation=data.get("model_preservation", 0),
                relight_naturalness=data.get("relight_naturalness", 0),
                lighting_match=data.get("lighting_match", 0),
                ground_contact=data.get("ground_contact", 0),
                physics_plausibility=data.get("physics_plausibility", 0),
                edge_quality=data.get("edge_quality", 0),
                prop_style_consistency=data.get("prop_style_consistency", 0),
                color_temperature_compliance=data.get(
                    "color_temperature_compliance", 0
                ),
                perspective_match=data.get("perspective_match", 0),
                perspective_reason=data.get("perspective_reason", ""),
                issues=data.get("issues", []),
                raw_response=response.text,
            )

        except Exception as e:
            return BackgroundSwapValidationResult(
                issues=[f"Validation error: {str(e)[:100]}"],
                raw_response=str(e),
            )

    def get_enhancement_prompt(
        self, result: BackgroundSwapValidationResult
    ) -> Tuple[str, List[str]]:
        """검증 실패 시 프롬프트 보강"""
        scores = result.to_dict()
        enhancements = []
        applied = []

        for rule_name, rule in ENHANCEMENT_RULES.items():
            if scores.get(rule["key"], 100) < rule["threshold"]:
                enhancements.append(rule["fix"])
                applied.append(rule_name)

        if not enhancements:
            return "", []

        text = f"""
=== RETRY (Score: {result.total_score}/100, Grade: {result.grade}) ===
MUST FIX:
""" + "\n".join(f"- {e}" for e in enhancements)

        return text, applied


# ============================================================
# 헬퍼 함수
# ============================================================


def validate_result(
    generated_image: Image.Image,
    source_image: Image.Image,
    api_key: str,
) -> Dict[str, Any]:
    """검증 수행"""
    validator = BackgroundSwapValidator(api_key)
    result = validator.validate(generated_image, source_image)

    return {
        "result": result,
        "passed": result.passed,
        "score": result.total_score,
        "grade": result.grade,
    }


def get_validator(source_type: str, api_key: str):
    """
    소스 타입에 따른 검증기 반환.

    Args:
        source_type: "outdoor" | "white_studio" | "colored_studio" | "indoor"
        api_key: API 키

    Returns:
        (validator, validator_name) 튜플
    """
    # 현재는 모든 타입에 BackgroundSwapValidator 사용
    validator = BackgroundSwapValidator(api_key)
    return validator, "BackgroundSwapValidator"


# ============================================================
# WorkflowValidator 인터페이스
# ============================================================

from core.validators.base import (
    WorkflowValidator,
    WorkflowType,
    CommonValidationResult,
    ValidationConfig,
    QualityTier,
)
from core.validators.registry import ValidatorRegistry
from core.api import _get_next_api_key


@ValidatorRegistry.register(WorkflowType.BACKGROUND_SWAP)
class BackgroundSwapWorkflowValidator(WorkflowValidator):
    """배경교체 워크플로 검증기"""

    workflow_type = WorkflowType.BACKGROUND_SWAP

    config = ValidationConfig(
        pass_total=95,  # 릴리즈 기준 95점
        weights={
            "model_preservation": 0.25,
            "relight_naturalness": 0.15,
            "lighting_match": 0.12,
            "ground_contact": 0.10,
            "physics_plausibility": 0.10,
            "edge_quality": 0.08,
            "prop_style_consistency": 0.05,
            "color_temperature_compliance": 0.05,
            "perspective_match": 0.10,  # 5% → 10%
        },
        auto_fail_thresholds={
            "model_preservation": 100,
            "physics_plausibility": 50,
            "color_temperature_compliance": 80,
            "perspective_match": 70,  # NEW! 필수 조건
        },
        priority_order=[
            "model_preservation",
            "perspective_match",  # 우선순위 상향
            "physics_plausibility",
            "color_temperature_compliance",
            "relight_naturalness",
            "lighting_match",
            "ground_contact",
            "edge_quality",
            "prop_style_consistency",
        ],
    )

    def __init__(self, client):
        super().__init__(client)
        self._api_key = _get_next_api_key()
        self._validator = BackgroundSwapValidator(self._api_key)

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
        **kwargs,
    ) -> CommonValidationResult:
        """배경교체 이미지 검증"""
        generated = self._load_image(generated_img)

        original = None
        if original_images := reference_images.get("original", []):
            original = self._load_image(original_images[0])

        result = self._validator.validate(generated, original)

        # Tier 결정
        if not result.passed or result.grade == "F":
            tier = QualityTier.REGENERATE
        elif result.grade in ("S", "A"):
            tier = QualityTier.RELEASE_READY
        else:
            tier = QualityTier.NEEDS_MINOR_EDIT

        # Auto-fail 체크
        auto_fail_reasons = []
        if result.model_preservation < 100:
            auto_fail_reasons.append(
                f"model_preservation {result.model_preservation} < 100"
            )
        if result.physics_plausibility < 50:
            auto_fail_reasons.append(
                f"physics_plausibility {result.physics_plausibility} < 50"
            )
        if result.color_temperature_compliance < 80:
            auto_fail_reasons.append(
                f"color_temperature_compliance {result.color_temperature_compliance} < 80"
            )
        if result.perspective_match < 70:
            auto_fail_reasons.append(
                f"perspective_match {result.perspective_match} < 70 ({result.perspective_reason})"
            )

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=result.total_score,
            tier=tier,
            grade=result.grade,
            passed=result.passed,
            auto_fail=bool(auto_fail_reasons),
            auto_fail_reasons=auto_fail_reasons,
            issues=result.issues,
            criteria_scores=result.to_dict(),
            summary_kr="; ".join(result.issues) if result.issues else "",
            raw_response=result.raw_response,
        )

    def get_enhancement_rules(self, failed_criteria: List[str]) -> str:
        """실패 기준에 따른 프롬프트 강화"""
        lines = []
        for criterion in failed_criteria:
            for rule in ENHANCEMENT_RULES.values():
                if rule["key"] == criterion:
                    lines.append(rule["fix"])
        return "\n".join([f"- {line}" for line in lines[:10]])


__all__ = [
    "BackgroundSwapValidationResult",
    "BackgroundSwapValidator",
    "BackgroundSwapWorkflowValidator",
    "ENHANCEMENT_RULES",
    "VALIDATION_PROMPT",
    "validate_result",
    "get_validator",
]
