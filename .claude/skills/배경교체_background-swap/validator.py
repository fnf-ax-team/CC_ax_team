"""
배경 교체 검증기 - 통합 검증기

검증 모드:
- 7-criteria: outdoor → outdoor 배경교체
- 9-criteria: studio/indoor → outdoor 배경교체 (리라이팅 포함)
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
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
    """
    배경교체 검증 결과.

    validation_mode에 따라 7-criteria 또는 9-criteria 사용.

    7-criteria Pass 조건:
    - model_preservation = 100 (필수)
    - physics_plausibility >= 50 (필수)
    - total_score >= 95

    9-criteria Pass 조건:
    - model_preservation = 100 (필수)
    - physics_plausibility >= 50 (필수)
    - color_temperature_compliance >= 80 (필수)
    - total_score >= 90
    """

    # 기본 7개 기준 점수 (0-100)
    model_preservation: int = 0  # 7: 30%, 9: 25% - =100 필수
    physics_plausibility: int = 0  # 7: 15%, 9: 10% - >=50 필수
    ground_contact: int = 0  # 7: 13%, 9: 12%
    lighting_match: int = 0  # 7: 12%, 9: 12%
    prop_style_consistency: int = 0  # 7: 12%, 9: 8%
    edge_quality: int = 0  # 7: 10%, 9: 8%
    perspective_match: int = 0  # 7: 8%, 9: 5%

    # 스튜디오 추가 2개 (9-criteria 모드에서만 사용)
    relight_naturalness: int = 0  # 9: 15%
    color_temperature_compliance: int = 0  # 9: 5%

    # 모드 표시
    validation_mode: str = "7-criteria"  # "7-criteria" | "9-criteria"

    # 결과
    issues: List[str] = field(default_factory=list)
    raw_response: str = ""

    @property
    def total_score(self) -> int:
        """가중치 적용 총점 계산"""
        if self.validation_mode == "9-criteria":
            return int(
                self.model_preservation * 0.25
                + self.relight_naturalness * 0.15
                + self.lighting_match * 0.12
                + self.ground_contact * 0.12
                + self.edge_quality * 0.08
                + self.physics_plausibility * 0.10
                + self.prop_style_consistency * 0.08
                + self.color_temperature_compliance * 0.05
                + self.perspective_match * 0.05
            )
        else:
            return int(
                self.model_preservation * 0.30
                + self.physics_plausibility * 0.15
                + self.ground_contact * 0.13
                + self.lighting_match * 0.12
                + self.prop_style_consistency * 0.12
                + self.edge_quality * 0.10
                + self.perspective_match * 0.08
            )

    @property
    def passed(self) -> bool:
        """Pass 조건 확인"""
        if self.validation_mode == "9-criteria":
            return (
                self.model_preservation == 100
                and self.physics_plausibility >= 50
                and self.color_temperature_compliance >= 80
                and self.total_score >= 90
            )
        else:
            return (
                self.model_preservation == 100
                and self.physics_plausibility >= 50
                and self.total_score >= 95
            )

    @property
    def grade(self) -> str:
        """등급 반환"""
        if self.validation_mode == "9-criteria":
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
        else:
            if self.passed and self.total_score >= 98:
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
        result = {
            "model_preservation": self.model_preservation,
            "physics_plausibility": self.physics_plausibility,
            "ground_contact": self.ground_contact,
            "lighting_match": self.lighting_match,
            "prop_style_consistency": self.prop_style_consistency,
            "edge_quality": self.edge_quality,
            "perspective_match": self.perspective_match,
            "validation_mode": self.validation_mode,
            "total_score": self.total_score,
            "passed": self.passed,
            "grade": self.grade,
            "issues": self.issues,
        }
        if self.validation_mode == "9-criteria":
            result["relight_naturalness"] = self.relight_naturalness
            result["color_temperature_compliance"] = self.color_temperature_compliance
        return result


# ============================================================
# 검증 프롬프트
# ============================================================

VALIDATION_7_PROMPT = """You are a professional VFX quality inspector. Evaluate this background swap result.

Score each criterion 0-100:

1. model_preservation (30%): Person EXACTLY preserved? Face, body, pose, clothing, scale - all identical to original?
   - 100 = perfect, 0 = changed

2. physics_plausibility (15%): Does the pose make physical sense in this environment?
   - Sitting person has chair/bench?
   - Leaning person has wall/pillar?
   - Standing is always OK

3. ground_contact (13%): Natural foot placement and shadows on ground?

4. lighting_match (12%): Light direction, intensity, color temperature consistent?

5. prop_style_consistency (12%): Do props (vehicle, objects) match the new background style?

6. edge_quality (10%): Clean edges around person? No halo, glow, or artifacts?

7. perspective_match (8%): Camera angle and vanishing point consistent?

List any issues found.

Return JSON only:
{
  "model_preservation": 0-100,
  "physics_plausibility": 0-100,
  "ground_contact": 0-100,
  "lighting_match": 0-100,
  "prop_style_consistency": 0-100,
  "edge_quality": 0-100,
  "perspective_match": 0-100,
  "issues": ["issue1", "issue2"]
}"""


VALIDATION_9_PROMPT = """You are a professional VFX quality inspector. Evaluate this STUDIO-TO-OUTDOOR relight result.

This image was originally shot in a studio with flat lighting. It has been composited into an outdoor scene.
The key challenge is making the studio subject look natural in outdoor lighting.

Score each criterion 0-100:

1. model_preservation (25%): Person EXACTLY preserved? Face, body, pose, clothing - all identical?

2. relight_naturalness (15%): Does the person look naturally lit by outdoor light?
   - Are there appropriate shadows on the person?
   - Does the person NOT look flat/studio-lit?

3. lighting_match (12%): Light direction consistent between person and background?

4. ground_contact (12%): Natural foot placement and shadows?

5. edge_quality (8%): Clean edges, no halo or glow?

6. physics_plausibility (10%): Pose makes sense in this environment?

7. prop_style_consistency (8%): Objects match the scene?

8. color_temperature_compliance (5%): NO warm/golden cast? Cool neutral tones?
   - 100 = cool/neutral
   - 50 = slightly warm
   - 0 = golden/amber (FAIL)

9. perspective_match (5%): Camera angle consistent?

Return JSON only:
{
  "model_preservation": 0-100,
  "relight_naturalness": 0-100,
  "lighting_match": 0-100,
  "ground_contact": 0-100,
  "edge_quality": 0-100,
  "physics_plausibility": 0-100,
  "prop_style_consistency": 0-100,
  "color_temperature_compliance": 0-100,
  "perspective_match": 0-100,
  "issues": ["issue1", "issue2"]
}"""


# ============================================================
# 재시도 프롬프트 보강 테이블
# ============================================================

ENHANCEMENT_RULES = {
    "POSE_MISMATCH": {
        "threshold_key": "model_preservation",
        "threshold": 90,
        "enhancement": "포즈 고정: 팔, 다리 각도 및 신체 각도 픽셀 단위 일치 강제. DO NOT change pose.",
    },
    "FACE_CHANGED": {
        "threshold_key": "model_preservation",
        "threshold": 95,
        "enhancement": "얼굴 고정: 이목구비, 표정, 시선 방향 및 입 모양 원본 복사. EXACT SAME FACE.",
    },
    "SCALE_SHRUNK": {
        "threshold_key": "model_preservation",
        "threshold": 85,
        "enhancement": "스케일 고정: 줌아웃 금지, 화면 대비 인물 크기 비율 유지. DO NOT SHRINK.",
    },
    "CLOTHING_CHANGED": {
        "threshold_key": "model_preservation",
        "threshold": 90,
        "enhancement": "의상 보존: 의상 디테일, 로고, 텍스처 및 드레이핑 유지.",
    },
    "PHYSICS_ERROR": {
        "threshold_key": "physics_plausibility",
        "threshold": 80,
        "enhancement": "물리 제약: 조명과 포즈에 맞는 물리적 타당성 및 그림자 정합.",
    },
    "PHYSICS_INCOMPATIBLE": {
        "threshold_key": "physics_plausibility",
        "threshold": 50,
        "enhancement": "지지대 강제: 앉기/기대기 포즈에 맞는 구조물(벽, 벤치 등) 생성. MUST add support structure.",
    },
    "PROP_STYLE_MISMATCH": {
        "threshold_key": "prop_style_consistency",
        "threshold": 70,
        "enhancement": "소품 적응: 배경 스타일과 조화로운 재질/색상으로 소품 유지.",
    },
    "LIGHTING_MISMATCH": {
        "threshold_key": "lighting_match",
        "threshold": 80,
        "enhancement": "조명 동기화: 광원 방향, 그림자 일치 및 색온도 매칭.",
    },
    "GROUND_POOR": {
        "threshold_key": "ground_contact",
        "threshold": 80,
        "enhancement": "접지 강화: 발밑 그림자 생성 및 원근에 맞는 바닥 안착.",
    },
    "EDGE_ARTIFACTS": {
        "threshold_key": "edge_quality",
        "threshold": 85,
        "enhancement": "경계 최적화: 외곽선 글로우, 달무리 현상 제거 및 매끄러운 합성.",
    },
    "PERSPECTIVE_MISMATCH": {
        "threshold_key": "perspective_match",
        "threshold": 80,
        "enhancement": "원근 동기화: 카메라 앵글, 수평선 및 소실점 일치.",
    },
}


# ============================================================
# 통합 검증기 클래스
# ============================================================


class BackgroundSwapValidator:
    """
    배경교체 통합 검증기.

    validation_mode:
    - "7-criteria": outdoor → outdoor (기본값)
    - "9-criteria": studio/indoor → outdoor (리라이팅)

    Usage:
        validator = BackgroundSwapValidator(api_key)
        result = validator.validate(generated_image, source_image)

        # 또는 모드 지정
        validator = BackgroundSwapValidator(api_key, validation_mode="9-criteria")
    """

    def __init__(self, api_key: str, validation_mode: str = "7-criteria"):
        """
        Args:
            api_key: Gemini API 키
            validation_mode: "7-criteria" | "9-criteria"
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.validation_mode = validation_mode

    def validate(
        self, generated_image: Image.Image, source_image: Image.Image = None
    ) -> BackgroundSwapValidationResult:
        """
        생성된 이미지 검증.

        Args:
            generated_image: 생성된 이미지
            source_image: 원본 소스 이미지 (선택, 비교용)

        Returns:
            BackgroundSwapValidationResult
        """
        try:
            # 모드에 따른 프롬프트 선택
            if self.validation_mode == "9-criteria":
                prompt = VALIDATION_9_PROMPT
            else:
                prompt = VALIDATION_7_PROMPT

            parts = [types.Part(text=prompt)]

            # 생성된 이미지
            if self.validation_mode == "9-criteria":
                parts.append(
                    types.Part(
                        text="\n\n[Generated Image (studio subject in outdoor scene)]:"
                    )
                )
            else:
                parts.append(types.Part(text="\n\n[Generated Image]:"))
            parts.append(pil_to_part(generated_image, max_size=1024))

            # 원본 이미지 (있으면 추가)
            if source_image:
                if self.validation_mode == "9-criteria":
                    parts.append(
                        types.Part(text="\n\n[Original Studio Image for comparison]:")
                    )
                else:
                    parts.append(
                        types.Part(text="\n\n[Original Source Image for comparison]:")
                    )
                parts.append(pil_to_part(source_image, max_size=512))

            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_mime_type="application/json"
                ),
            )

            data = json.loads(response.text)

            # 결과 생성
            result = BackgroundSwapValidationResult(
                model_preservation=data.get("model_preservation", 0),
                physics_plausibility=data.get("physics_plausibility", 0),
                ground_contact=data.get("ground_contact", 0),
                lighting_match=data.get("lighting_match", 0),
                prop_style_consistency=data.get("prop_style_consistency", 0),
                edge_quality=data.get("edge_quality", 0),
                perspective_match=data.get("perspective_match", 0),
                validation_mode=self.validation_mode,
                issues=data.get("issues", []),
                raw_response=response.text,
            )

            # 9-criteria 추가 필드
            if self.validation_mode == "9-criteria":
                result.relight_naturalness = data.get("relight_naturalness", 0)
                result.color_temperature_compliance = data.get(
                    "color_temperature_compliance", 0
                )

            return result

        except Exception as e:
            return BackgroundSwapValidationResult(
                validation_mode=self.validation_mode,
                issues=[f"Validation error: {str(e)[:100]}"],
                raw_response=str(e),
            )

    def get_enhancement_prompt(
        self, result: BackgroundSwapValidationResult
    ) -> Tuple[str, List[str]]:
        """
        검증 실패 시 프롬프트 보강 내용 생성.

        Args:
            result: 검증 결과

        Returns:
            (보강 프롬프트 텍스트, 적용된 규칙 목록)
        """
        enhancements = []
        applied_rules = []

        scores = {
            "model_preservation": result.model_preservation,
            "physics_plausibility": result.physics_plausibility,
            "ground_contact": result.ground_contact,
            "lighting_match": result.lighting_match,
            "prop_style_consistency": result.prop_style_consistency,
            "edge_quality": result.edge_quality,
            "perspective_match": result.perspective_match,
        }

        # 우선순위 순서로 규칙 적용
        priority_order = [
            "FACE_CHANGED",
            "POSE_MISMATCH",
            "SCALE_SHRUNK",
            "CLOTHING_CHANGED",
            "PHYSICS_INCOMPATIBLE",
            "PHYSICS_ERROR",
            "LIGHTING_MISMATCH",
            "GROUND_POOR",
            "EDGE_ARTIFACTS",
            "PROP_STYLE_MISMATCH",
            "PERSPECTIVE_MISMATCH",
        ]

        for rule_name in priority_order:
            rule = ENHANCEMENT_RULES.get(rule_name)
            if not rule:
                continue

            score = scores.get(rule["threshold_key"], 100)
            if score < rule["threshold"]:
                enhancements.append(rule["enhancement"])
                applied_rules.append(rule_name)

        if not enhancements:
            return "", []

        enhancement_text = (
            f"""
=== RETRY ENHANCEMENT (Score: {result.total_score}/100, Grade: {result.grade}) ===
Failed criteria: {', '.join(applied_rules)}

MUST FIX:
"""
            + "\n".join(f"- {e}" for e in enhancements)
            + "\n================================================"
        )

        return enhancement_text, applied_rules


# ============================================================
# 헬퍼 함수
# ============================================================


def get_validator(
    source_type: str, api_key: str
) -> Tuple[BackgroundSwapValidator, str]:
    """
    소스 타입에 따라 적절한 모드의 검증기 반환.

    Args:
        source_type: "outdoor" | "white_studio" | "colored_studio" | "indoor"
        api_key: Gemini API 키

    Returns:
        (validator_instance, validation_mode)

    라우팅 로직:
    - outdoor → 7-criteria
    - studio/indoor → 9-criteria
    """
    if source_type == "outdoor":
        return BackgroundSwapValidator(api_key, "7-criteria"), "7-criteria"
    else:
        return BackgroundSwapValidator(api_key, "9-criteria"), "9-criteria"


def validate_result(
    generated_image: Image.Image,
    source_image: Image.Image,
    source_type: str,
    api_key: str,
) -> Dict[str, Any]:
    """
    자동 라우팅으로 검증 수행.

    Args:
        generated_image: 생성된 이미지
        source_image: 원본 소스 이미지
        source_type: 소스 타입
        api_key: API 키

    Returns:
        {
            "validation_mode": str,
            "result": BackgroundSwapValidationResult,
            "passed": bool,
            "score": int,
            "grade": str
        }
    """
    validator, validation_mode = get_validator(source_type, api_key)
    result = validator.validate(generated_image, source_image)

    return {
        "validation_mode": validation_mode,
        "result": result,
        "passed": result.passed,
        "score": result.total_score,
        "grade": result.grade,
    }


__all__ = [
    "BackgroundSwapValidationResult",
    "BackgroundSwapValidator",
    "ENHANCEMENT_RULES",
    "VALIDATION_7_PROMPT",
    "VALIDATION_9_PROMPT",
    "get_validator",
    "validate_result",
]
