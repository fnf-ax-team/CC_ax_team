"""
브랜드컷 검증기 v2 - 14개 기준 (미감 + 브랜드 느낌 추가)

변경점 (v1 대비):
1. aesthetic_appeal (미감) 추가 - "예쁜가?"
2. brand_vibe (브랜드 느낌) 추가 - "MLB 느낌 나는가?"
3. 비중 재조정 (총 100%)

기준 구조:
- A. 기본품질 (22%): photorealism(6%), anatomy(7%), micro_detail(4%), aesthetic_appeal(5%)
- B. 인물보존 (23%): face_identity(13%), expression(6%), body_type(4%)
- C. 착장 (15%): outfit_accuracy(15%)
- D. 브랜드 (25%): brand_compliance(7%), brand_vibe(10%), environmental_integration(4%), lighting_mood(4%)
- E. 구도 (15%): composition(8%), pose_quality(7%)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, TYPE_CHECKING
from enum import Enum
from pathlib import Path
import json
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL

if TYPE_CHECKING:
    from core.outfit_analyzer import OutfitAnalysis


# ============================================================
# 한글 기준명 (14개)
# ============================================================

CRITERION_NAMES_KR = {
    # A. 기본품질
    "photorealism": "실사감",
    "anatomy": "해부학 정확도",
    "micro_detail": "미세 디테일",
    "aesthetic_appeal": "미감",  # NEW
    # B. 인물보존
    "face_identity": "얼굴 동일성",
    "expression": "표정",
    "body_type": "체형 일치",
    # C. 착장
    "outfit_accuracy": "착장 정확도",
    # D. 브랜드
    "brand_compliance": "브랜드 준수",
    "brand_vibe": "브랜드 느낌",  # NEW
    "environmental_integration": "환경 통합",
    "lighting_mood": "조명/무드",
    # E. 구도
    "composition": "구도",
    "pose_quality": "포즈 품질",
}


# ============================================================
# 비중 (Weights) - 총 100%
# ============================================================

WEIGHTS = {
    # A. 기본품질 (22%)
    "photorealism": 0.06,
    "anatomy": 0.07,
    "micro_detail": 0.04,
    "aesthetic_appeal": 0.05,  # NEW
    # B. 인물보존 (23%)
    "face_identity": 0.13,
    "expression": 0.06,
    "body_type": 0.04,
    # C. 착장 (15%)
    "outfit_accuracy": 0.15,
    # D. 브랜드 (25%)
    "brand_compliance": 0.07,
    "brand_vibe": 0.10,  # NEW
    "environmental_integration": 0.04,
    "lighting_mood": 0.04,
    # E. 구도 (15%)
    "composition": 0.08,
    "pose_quality": 0.07,
}


# ============================================================
# 임계값 (Thresholds)
# ============================================================

THRESHOLDS = {
    "photorealism": 85,
    "anatomy": 80,
    "micro_detail": 75,
    "aesthetic_appeal": 80,  # NEW - 예쁘지 않으면 탈락
    "face_identity": 90,
    "expression": 75,
    "body_type": 85,
    "outfit_accuracy": 80,
    "brand_compliance": 75,
    "brand_vibe": 75,  # NEW - 브랜드 느낌 없으면 탈락
    "environmental_integration": 70,
    "lighting_mood": 75,
    "composition": 80,
    "pose_quality": 75,
}


# ============================================================
# Auto-Fail 임계값
# ============================================================

AUTO_FAIL_THRESHOLDS = {
    "anatomy": 50,  # 손가락 기형
    "face_identity": 70,  # 다른 사람
    "outfit_accuracy": 50,  # 착장 누락
    "brand_vibe": 50,  # MLB 느낌 전혀 없음
    "lighting_mood": 50,  # 누런 톤
    "aesthetic_appeal": 50,  # 전혀 예쁘지 않음
}


# ============================================================
# VLM 검증 프롬프트 (14개 기준)
# ============================================================

VALIDATION_PROMPT = """
당신은 F&F 패션 브랜드의 화보 검수 전문가입니다.
생성된 이미지를 14개 기준으로 평가해주세요.

## 평가 기준 (14개)

### A. 기본품질 (22%)

1. **photorealism** (실사감) - 6%
   - 진짜 사진처럼 보이는가?
   - AI 생성 티가 나는가?
   - 질감, 조명, 그림자가 자연스러운가?

2. **anatomy** (해부학 정확도) - 7%
   - 손가락 5개인가? (6개 이상 = 0점)
   - 신체 비율이 자연스러운가?
   - 관절이 자연스러운가?

3. **micro_detail** (미세 디테일) - 4%
   - 피부 질감이 자연스러운가? (플라스틱 = 낮은 점수)
   - 머리카락 디테일이 좋은가?
   - 천의 주름이 자연스러운가?

4. **aesthetic_appeal** (미감) - 5% [NEW]
   - 패션 화보로서 예쁜가?
   - 보는 사람이 "와" 할 만한 비주얼인가?
   - 모델처럼 빛나는 아우라가 있는가?
   - 세련되고 고급스러운 느낌인가?

### B. 인물보존 (23%)

5. **face_identity** (얼굴 동일성) - 13%
   [FACE REFERENCE]와 비교!
   - 동일 인물인가? (다른 사람 = 0점)
   - 눈, 코, 입, 턱선이 일치하는가?
   - 피부톤이 비슷한가?

6. **expression** (표정) - 6%
   - 쿨하고 자신감 있는 표정인가?
   - 밝은 미소/이 보이면 감점
   - 약하거나 피곤해 보이면 감점

7. **body_type** (체형 일치) - 4%
   - 체형이 레퍼런스와 일치하는가?
   - 어깨 너비, 허리 라인 등

### C. 착장 (15%)

8. **outfit_accuracy** (착장 정확도) - 15%
   [OUTFIT REFERENCE]와 비교!

   [STEP 1] 레퍼런스 아이템 개수 세기
   [STEP 2] 생성 이미지 아이템 개수 세기
   [STEP 3] 누락 아이템 = 레퍼런스에만 있는 것
   → 누락 1개 이상 = 0점 FAIL!

   - 모든 아이템이 포함되었는가?
   - 색상이 정확한가?
   - 로고 위치와 디자인이 맞는가?
   - 핏과 스타일링이 맞는가?

### D. 브랜드 (25%)

9. **brand_compliance** (브랜드 준수) - 7%
   - 배경이 깔끔한가? (지저분 = 감점)
   - 금지 요소가 없는가? (밝은 미소, 웜톤 등)
   - 프롬프트 라이브러리 규칙을 따르는가?

10. **brand_vibe** (브랜드 느낌) - 10% [NEW]
    - MLB 브랜드 DNA가 느껴지는가?
    - "Young & Rich" 컨셉이 전달되는가?
    - 프리미엄하고 세련된 느낌인가?
    - 파워풀하고 자신감 있는 분위기인가?
    - 스트릿/캐주얼 + 고급스러움의 조합인가?

11. **environmental_integration** (환경 통합) - 4%
    - 인물과 배경이 자연스럽게 어우러지는가?
    - 합성 느낌이 나는가?

12. **lighting_mood** (조명/무드) - 4%
    [MOOD REFERENCE] 있으면 비교!
    - 쿨톤을 유지하는가? (누런톤 = 0점)
    - 조명이 자연스러운가?
    - 무드 레퍼런스와 비슷한 느낌인가?

### E. 구도 (15%)

13. **composition** (구도) - 8%
    - 구도가 안정적인가?
    - 여백이 적절한가?
    - 시선 유도가 좋은가?

14. **pose_quality** (포즈 품질) - 7%
    [POSE REFERENCE] 있으면 비교!

    [STEP 1] 레퍼런스 앵글/프레이밍 파악
    [STEP 2] 생성 이미지 앵글/프레이밍 파악
    [STEP 3] 비교 → 다르면 감점
    - 앵글 다름: -20
    - 프레이밍 다름: -15
    - 다리 위치 다름: -10

    - 파워포즈인가? (당당하고 자신감 있는)
    - 자연스러운 포즈인가?

---

## 출력 형식 (JSON)

```json
{
  "photorealism": {"score": 0-100, "reason": "..."},
  "anatomy": {"score": 0-100, "reason": "..."},
  "micro_detail": {"score": 0-100, "reason": "..."},
  "aesthetic_appeal": {"score": 0-100, "reason": "..."},
  "face_identity": {"score": 0-100, "reason": "..."},
  "expression": {"score": 0-100, "reason": "..."},
  "body_type": {"score": 0-100, "reason": "..."},
  "outfit_accuracy": {"score": 0-100, "reason": "...", "missing_items": [], "mismatched_attributes": {}},
  "brand_compliance": {"score": 0-100, "reason": "..."},
  "brand_vibe": {"score": 0-100, "reason": "..."},
  "environmental_integration": {"score": 0-100, "reason": "..."},
  "lighting_mood": {"score": 0-100, "reason": "..."},
  "composition": {"score": 0-100, "reason": "..."},
  "pose_quality": {"score": 0-100, "reason": "..."},
  "issues": ["이슈1", "이슈2"],
  "strengths": ["장점1", "장점2"],
  "summary_kr": "한국어 요약 (2-3문장)"
}
```

reason 형식: "REF:~, GEN:~, 감점:~" (비교 항목의 경우)

반드시 JSON만 출력하세요. 설명 없이!
"""


# ============================================================
# 결과 데이터 클래스
# ============================================================


class QualityTier(Enum):
    RELEASE_READY = "RELEASE_READY"
    NEEDS_MINOR_EDIT = "NEEDS_MINOR_EDIT"
    REGENERATE = "REGENERATE"


@dataclass
class ValidationResult:
    """14개 기준 검증 결과"""

    # A. 기본품질
    photorealism: int
    anatomy: int
    micro_detail: int
    aesthetic_appeal: int  # NEW

    # B. 인물보존
    face_identity: int
    expression: int
    body_type: int

    # C. 착장
    outfit_accuracy: int

    # D. 브랜드
    brand_compliance: int
    brand_vibe: int  # NEW
    environmental_integration: int
    lighting_mood: int

    # E. 구도
    composition: int
    pose_quality: int

    # 결과
    total_score: int
    tier: QualityTier
    grade: str
    passed: bool
    auto_fail: bool
    auto_fail_reasons: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    summary_kr: str = ""
    reasons: dict = field(default_factory=dict)

    # 착장 구조적 검증 결과
    outfit_missing_items: List[str] = field(default_factory=list)
    outfit_mismatched_attributes: dict = field(default_factory=dict)

    def format_korean(self) -> str:
        """검수표 형식으로 출력"""

        def check(score, threshold):
            return "O" if score >= threshold else "X"

        criteria_order = [
            ("photorealism", "실사감", "6%"),
            ("anatomy", "해부학 정확도", "7%"),
            ("micro_detail", "미세 디테일", "4%"),
            ("aesthetic_appeal", "미감", "5%"),  # NEW
            ("face_identity", "얼굴 동일성", "13%"),
            ("expression", "표정", "6%"),
            ("body_type", "체형 일치", "4%"),
            ("outfit_accuracy", "착장 정확도", "15%"),
            ("brand_compliance", "브랜드 준수", "7%"),
            ("brand_vibe", "브랜드 느낌", "10%"),  # NEW
            ("environmental_integration", "환경 통합", "4%"),
            ("lighting_mood", "조명/무드", "4%"),
            ("composition", "구도", "8%"),
            ("pose_quality", "포즈 품질", "7%"),
        ]

        lines = [
            "## 검수 결과",
            "",
            "| 기준 | 비중 | Pass 조건 | 점수 | 통과 |",
            "|------|------|-----------|------|------|",
        ]

        for key, name_kr, weight in criteria_order:
            score = getattr(self, key, 0)
            threshold = THRESHOLDS[key]
            passed_mark = check(score, threshold)
            lines.append(
                f"| {name_kr} | {weight} | >= {threshold} | {score} | {passed_mark} |"
            )

        tier_kr = {
            "RELEASE_READY": "납품 가능",
            "NEEDS_MINOR_EDIT": "소폭 보정 필요",
            "REGENERATE": "재생성 필요",
        }
        tier_text = tier_kr.get(self.tier.value, self.tier.value)

        lines.append("")
        lines.append(
            f"**총점**: {self.total_score}/100 | **등급**: {self.grade} | **판정**: {tier_text}"
        )

        if self.auto_fail_reasons:
            lines.append("")
            lines.append("### 자동 탈락 사유")
            for reason in self.auto_fail_reasons:
                lines.append(f"- {reason}")

        if self.issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in self.issues[:5]:
                lines.append(f"- {issue}")

        return "\n".join(lines)


# ============================================================
# 검증기 클래스
# ============================================================


class BrandcutValidator:
    """브랜드컷 14개 기준 검증기 v2"""

    def __init__(self, client: genai.Client):
        self.client = client

    def validate(
        self,
        generated_img: Image.Image,
        face_images: List[Union[str, Path, Image.Image]],
        outfit_images: List[Union[str, Path, Image.Image]],
        pose_reference: Optional[Image.Image] = None,
        outfit_spec: Optional["OutfitAnalysis"] = None,
    ) -> ValidationResult:
        """
        브랜드컷 이미지 검증 (14개 기준)

        Args:
            generated_img: 생성된 이미지
            face_images: 얼굴 레퍼런스
            outfit_images: 착장 레퍼런스
            pose_reference: 포즈 레퍼런스 (선택)
            outfit_spec: 착장 스펙 (선택)

        Returns:
            ValidationResult
        """
        # API 파트 구성
        parts = [types.Part(text=VALIDATION_PROMPT)]

        # 생성 이미지
        parts.append(types.Part(text="[GENERATED IMAGE] - 평가 대상"))
        parts.append(self._pil_to_part(generated_img))

        # 얼굴 레퍼런스
        for i, img in enumerate(face_images):
            parts.append(types.Part(text=f"[FACE REFERENCE {i+1}]"))
            parts.append(self._pil_to_part(self._load_image(img)))

        # 착장 레퍼런스
        for i, img in enumerate(outfit_images):
            parts.append(types.Part(text=f"[OUTFIT REFERENCE {i+1}]"))
            parts.append(self._pil_to_part(self._load_image(img)))

        # 포즈 레퍼런스
        if pose_reference:
            parts.append(types.Part(text="[POSE REFERENCE]"))
            parts.append(self._pil_to_part(pose_reference))

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.1),
            )

            # JSON 파싱
            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            scores = json.loads(response_text)

        except Exception as e:
            print(f"[Validator] Error: {e}")
            # 실패 시 기본값
            scores = {
                k: {"score": 50, "reason": "평가 실패"} for k in CRITERION_NAMES_KR
            }
            scores["issues"] = [str(e)]
            scores["strengths"] = []
            scores["summary_kr"] = "검증 실패"

        # 결과 생성
        return self._build_result(scores)

    def _build_result(self, scores: dict) -> ValidationResult:
        """점수 dict로 ValidationResult 생성"""

        def get_score(key):
            val = scores.get(key, {})
            if isinstance(val, dict):
                return val.get("score", 0)
            return val

        def get_reason(key):
            val = scores.get(key, {})
            if isinstance(val, dict):
                return val.get("reason", "")
            return ""

        # 점수 추출
        criterion_scores = {key: get_score(key) for key in CRITERION_NAMES_KR}

        # 총점 계산 (가중합)
        total_score = sum(
            criterion_scores[key] * WEIGHTS[key] for key in CRITERION_NAMES_KR
        )
        total_score = round(total_score)

        # Auto-fail 체크
        auto_fail = False
        auto_fail_reasons = []

        for key, threshold in AUTO_FAIL_THRESHOLDS.items():
            if criterion_scores[key] < threshold:
                auto_fail = True
                auto_fail_reasons.append(
                    f"{CRITERION_NAMES_KR[key]}: {criterion_scores[key]}점 < {threshold}점"
                )

        # 착장 누락 체크
        outfit_data = scores.get("outfit_accuracy", {})
        missing_items = (
            outfit_data.get("missing_items", [])
            if isinstance(outfit_data, dict)
            else []
        )
        if missing_items:
            auto_fail = True
            auto_fail_reasons.append(f"착장 누락: {', '.join(missing_items)}")

        # 등급 결정
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
        elif total_score >= 75:
            grade = "C"
            tier = QualityTier.REGENERATE
        else:
            grade = "F"
            tier = QualityTier.REGENERATE

        # Pass 판정
        passed = (
            not auto_fail
            and total_score >= 85
            and all(
                criterion_scores[key] >= THRESHOLDS[key]
                for key in ["face_identity", "outfit_accuracy"]
            )
        )

        # reasons dict 생성
        reasons = {key: get_reason(key) for key in CRITERION_NAMES_KR}

        return ValidationResult(
            photorealism=criterion_scores["photorealism"],
            anatomy=criterion_scores["anatomy"],
            micro_detail=criterion_scores["micro_detail"],
            aesthetic_appeal=criterion_scores["aesthetic_appeal"],
            face_identity=criterion_scores["face_identity"],
            expression=criterion_scores["expression"],
            body_type=criterion_scores["body_type"],
            outfit_accuracy=criterion_scores["outfit_accuracy"],
            brand_compliance=criterion_scores["brand_compliance"],
            brand_vibe=criterion_scores["brand_vibe"],
            environmental_integration=criterion_scores["environmental_integration"],
            lighting_mood=criterion_scores["lighting_mood"],
            composition=criterion_scores["composition"],
            pose_quality=criterion_scores["pose_quality"],
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=scores.get("issues", []),
            strengths=scores.get("strengths", []),
            summary_kr=scores.get("summary_kr", ""),
            reasons=reasons,
            outfit_missing_items=missing_items,
            outfit_mismatched_attributes=outfit_data.get("mismatched_attributes", {})
            if isinstance(outfit_data, dict)
            else {},
        )

    def _load_image(self, img_input: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드"""
        if isinstance(img_input, (str, Path)):
            return Image.open(img_input).convert("RGB")
        return img_input.convert("RGB") if img_input.mode != "RGB" else img_input

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )


# ============================================================
# 재시도 강화 규칙
# ============================================================

ENHANCEMENT_RULES = {
    "outfit_accuracy": [
        "모든 착장 아이템을 빠짐없이 포함하세요",
        "색상을 정확히 일치시키세요",
        "로고 위치와 디자인을 그대로 재현하세요",
    ],
    "face_identity": [
        "얼굴을 100% 동일하게 유지하세요",
        "눈, 코, 입, 턱선을 정확히 일치시키세요",
    ],
    "aesthetic_appeal": [  # NEW
        "패션 화보처럼 예쁘게 만드세요",
        "모델처럼 빛나는 아우라를 표현하세요",
        "세련되고 고급스러운 느낌을 주세요",
    ],
    "brand_vibe": [  # NEW
        "MLB 브랜드 DNA를 강하게 표현하세요",
        "'Young & Rich' 컨셉을 살리세요",
        "파워풀하고 자신감 있는 분위기로",
    ],
    "brand_compliance": [
        "배경을 깔끔하게 유지하세요",
        "쿨톤 색감을 유지하세요",
    ],
    "lighting_mood": [
        "절대 누런 톤 금지",
        "쿨톤 조명을 유지하세요",
    ],
    "pose_quality": [
        "포즈 레퍼런스와 동일한 앵글로",
        "프레이밍을 정확히 맞추세요",
    ],
    "anatomy": [
        "손가락 정확히 5개",
        "신체 비율을 자연스럽게",
    ],
}


from core.validators.base import (
    WorkflowValidator,
    WorkflowType,
    CommonValidationResult,
    ValidationConfig,
    QualityTier as CommonQualityTier,
)
from core.validators.registry import ValidatorRegistry


@ValidatorRegistry.register(WorkflowType.BRANDCUT)
class BrandcutWorkflowValidator(WorkflowValidator):
    """브랜드컷 통합 검증기 — BrandcutValidator 래핑

    ValidatorRegistry를 통해 WorkflowType.BRANDCUT으로 접근 가능.
    """

    workflow_type = WorkflowType.BRANDCUT
    config = ValidationConfig(
        pass_total=85,
        weights=WEIGHTS,
        auto_fail_thresholds=AUTO_FAIL_THRESHOLDS,
        priority_order=[
            "outfit_accuracy",
            "face_identity",
            "brand_vibe",
            "aesthetic_appeal",
            "anatomy",
            "brand_compliance",
            "lighting_mood",
        ],
        grade_thresholds={"S": 95, "A": 90, "B": 85, "C": 75},
    )

    def __init__(self, client):
        super().__init__(client)
        self._inner = BrandcutValidator(client)

    def validate(
        self,
        generated_img,
        reference_images,
        **kwargs,
    ) -> CommonValidationResult:
        """브랜드컷 검증 — CommonValidationResult 반환"""
        result = self._inner.validate(
            generated_img=generated_img,
            face_images=reference_images.get("face", []),
            outfit_images=reference_images.get("outfit", []),
            pose_reference=kwargs.get("pose_reference"),
            outfit_spec=kwargs.get("outfit_spec"),
        )

        # 로컬 QualityTier → 공통 QualityTier
        tier_map = {
            QualityTier.RELEASE_READY: CommonQualityTier.RELEASE_READY,
            QualityTier.NEEDS_MINOR_EDIT: CommonQualityTier.NEEDS_MINOR_EDIT,
            QualityTier.REGENERATE: CommonQualityTier.REGENERATE,
        }

        return CommonValidationResult(
            workflow_type=self.workflow_type,
            total_score=result.total_score,
            tier=tier_map.get(result.tier, CommonQualityTier.REGENERATE),
            grade=result.grade,
            passed=result.passed,
            auto_fail=result.auto_fail,
            auto_fail_reasons=result.auto_fail_reasons,
            issues=result.issues,
            criteria_scores={
                key: getattr(result, key, 0) for key in CRITERION_NAMES_KR
            },
            summary_kr=result.summary_kr,
        )

    def get_enhancement_rules(self, failed_criteria):
        """실패 기준에 따른 강화 규칙"""
        lines = []
        for criterion in self.config.priority_order:
            if criterion in failed_criteria and criterion in ENHANCEMENT_RULES:
                lines.extend(ENHANCEMENT_RULES[criterion])
        return "\n".join([f"- {line}" for line in lines[:10]])


__all__ = [
    "BrandcutValidator",
    "BrandcutWorkflowValidator",
    "ValidationResult",
    "CRITERION_NAMES_KR",
    "THRESHOLDS",
    "WEIGHTS",
    "ENHANCEMENT_RULES",
]
