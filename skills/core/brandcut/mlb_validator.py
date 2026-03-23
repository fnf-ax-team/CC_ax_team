"""
MLB A-to-Z Generation Validator (v4.0 - Unified 12 Criteria)

통합 품질 검증 모듈:
- 12개 기준으로 통합 (기존 6개 파일 → 1개)
- Grade 시스템 (S/A/B/C/F)
- Auto-fail 조건
- 한국어 요약 지원

Note: 재시도 로직은 retry_generator.py에서 처리
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Tuple, TYPE_CHECKING
from enum import Enum
from pathlib import Path
import json
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL, IMAGE_MODEL

if TYPE_CHECKING:
    from core.outfit_analyzer import OutfitAnalysis


# ============================================================
# Standalone 출력 함수 (retry_generator.py에서 import 가능)
# ============================================================

# 한글 기준명 상수 (canonical)
CRITERION_NAMES_KR = {
    "photorealism": "실사감",
    "anatomy": "해부학 정확도",
    "micro_detail": "미세 디테일",
    "face_identity": "얼굴 동일성",
    "expression": "표정",
    "body_type": "체형 일치",
    "outfit_accuracy": "착장 정확도",
    "brand_compliance": "브랜드 준수",
    "environmental_integration": "환경 통합",
    "lighting_mood": "조명/무드",
    "composition": "구도",
    "pose_quality": "포즈 품질",
}


def format_validation_result(result, filename: str = "") -> str:
    """
    검수 결과를 CLAUDE.md 규격 표 형식으로 포맷

    이 함수는 canonical 출력 함수임.
    retry_generator.py에서 이 함수를 import하여 사용.

    Args:
        result: ValidationResult 객체
        filename: 파일명 또는 시도 번호 (선택)

    Returns:
        str: Markdown 표 형식 문자열
    """
    # 기준별 임계값
    thresholds = {
        "outfit_accuracy": 80,
        "face_identity": 90,
        "expression": 75,
        "anatomy": 80,
        "brand_compliance": 75,
        "lighting_mood": 75,
        "micro_detail": 75,
        "environmental_integration": 75,
        "body_type": 85,
        "photorealism": 85,
        "composition": 80,
        "pose_quality": 75,
    }

    # 표 생성
    lines = []
    if filename:
        lines.append(f"\n## 검수 결과 ({filename})\n")
    else:
        lines.append("\n## 검수 결과\n")

    lines.append("| 항목 | 점수 | 기준 | 통과 | 사유 |")
    lines.append("|------|------|------|------|------|")

    failed_items = []
    reasons = getattr(result, "reasons", {}) or {}

    for key, korean_name in CRITERION_NAMES_KR.items():
        score = getattr(result, key, 0)
        threshold = thresholds.get(key, 75)
        check_mark = "O" if score >= threshold else "X"
        reason = reasons.get(key, "-")

        # 사유가 너무 길면 자르기
        if len(reason) > 35:
            reason = reason[:32] + "..."

        lines.append(
            f"| {korean_name} | {score} | >={threshold} | {check_mark} | {reason} |"
        )

        if score < threshold:
            failed_items.append((korean_name, reasons.get(key, "")))

    # 총점 및 판정
    total_score = getattr(result, "total_score", 0)
    grade = getattr(result, "grade", "F")
    passed = getattr(result, "passed", False)

    lines.append(
        f"\n**총점**: {total_score}/100 | **등급**: {grade} | **판정**: {'통과' if passed else '재검토 필요'}"
    )

    # Gate 결과 (있으면)
    if hasattr(result, "gate_checked") and result.gate_checked:
        gate_status = "PASS" if result.gate_passed else "FAIL"
        lines.append(f"\n**Gate 체크**: {gate_status}")
        if hasattr(result, "gate_failed_reasons") and result.gate_failed_reasons:
            for reason in result.gate_failed_reasons:
                lines.append(f"  - {reason}")

    # 자동 탈락 사유
    auto_fail_reasons = getattr(result, "auto_fail_reasons", []) or []
    if auto_fail_reasons:
        lines.append("\n### 자동 탈락 사유")
        for reason in auto_fail_reasons:
            lines.append(f"- {reason}")

    # 탈락 사유 (점수 기반)
    if failed_items:
        lines.append("\n### 탈락 사유")
        for item_name, item_reason in failed_items:
            if item_reason:
                lines.append(f"- **{item_name}**: {item_reason}")
            else:
                lines.append(f"- **{item_name}**: 기준 미달")

    return "\n".join(lines)


class QualityTier(Enum):
    """Quality classification tiers for generated images"""

    RELEASE_READY = "RELEASE_READY"  # S/A Grade: 즉시 납품 가능
    NEEDS_MINOR_EDIT = "NEEDS_MINOR_EDIT"  # B Grade: 소폭 보정 후 사용 가능
    REGENERATE = "REGENERATE"  # C/F Grade: 재생성 필요


@dataclass
class ValidationResult:
    """Complete validation result with 13 quality metrics"""

    # A. 기본품질 (25%)
    photorealism: int
    anatomy: int
    micro_detail: int

    # B. 인물보존 (25%)
    face_identity: int
    expression: int
    body_type: int

    # C. 착장 (15%)
    outfit_accuracy: int

    # D. 브랜드 (20%)
    brand_compliance: int
    environmental_integration: int
    lighting_mood: int

    # E. 구도 (15%)
    composition: int
    pose_quality: int

    # 결과
    total_score: int
    tier: QualityTier
    grade: str  # S/A/B/C/F
    passed: bool
    auto_fail: bool
    auto_fail_reasons: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    summary_kr: str = ""  # 한국어 요약
    raw_response: Optional[dict] = None

    # 각 항목별 점수 사유 (한국어)
    reasons: dict = field(default_factory=dict)

    # AI 티 검사 결과 (선택적)
    ai_artifact_score: Optional[int] = None  # 0-100, 높을수록 AI스러움
    ai_artifact_grade: Optional[str] = None  # S/A/B/C/F
    ai_artifact_issues: List[str] = field(default_factory=list)

    # 게이트 결과 (NEW)
    gate_passed: bool = True
    gate_failed_reasons: List[str] = field(default_factory=list)
    gate_checked: bool = False  # 게이트 체크 수행 여부

    # 착장 구조적 검증 결과 (NEW: outfit_spec 기반)
    outfit_missing_items: List[str] = field(default_factory=list)
    outfit_mismatched_attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            # A. 기본품질
            "photorealism": self.photorealism,
            "anatomy": self.anatomy,
            "micro_detail": self.micro_detail,
            # B. 인물보존
            "face_identity": self.face_identity,
            "expression": self.expression,
            "body_type": self.body_type,
            # C. 착장
            "outfit_accuracy": self.outfit_accuracy,
            # D. 브랜드
            "brand_compliance": self.brand_compliance,
            "environmental_integration": self.environmental_integration,
            "lighting_mood": self.lighting_mood,
            # E. 구도
            "composition": self.composition,
            "pose_quality": self.pose_quality,
            # 결과
            "total_score": self.total_score,
            "tier": self.tier.value,
            "grade": self.grade,
            "passed": self.passed,
            "auto_fail": self.auto_fail,
            "auto_fail_reasons": self.auto_fail_reasons,
            "issues": self.issues,
            "strengths": self.strengths,
            "summary_kr": self.summary_kr,
            "raw_response": self.raw_response,
            # 각 항목별 점수 사유
            "reasons": self.reasons,
            # AI 티 검사 결과
            "ai_artifact_score": self.ai_artifact_score,
            "ai_artifact_grade": self.ai_artifact_grade,
            "ai_artifact_issues": self.ai_artifact_issues,
            # 게이트 결과
            "gate_passed": self.gate_passed,
            "gate_failed_reasons": self.gate_failed_reasons,
            "gate_checked": self.gate_checked,
            # 착장 구조적 검증 결과
            "outfit_missing_items": self.outfit_missing_items,
            "outfit_mismatched_attributes": self.outfit_mismatched_attributes,
        }

    def format_korean(self) -> str:
        """검수표 형식으로 출력 (브랜드컷 12-criteria)

        브랜드컷 검수 기준:
        - A. 기본품질 (25%): 실사감, 해부학, 마이크로 디테일
        - B. 인물보존 (25%): 얼굴 동일성, 표정, 체형 일치
        - C. 착장 (15%): 착장 정확도
        - D. 브랜드 (20%): 브랜드 톤, 환경 통합, 조명/무드
        - E. 구도 (15%): 구도, 포즈 품질
        """

        def check(score, threshold):
            return "O" if score >= threshold else "X"

        # 기준별 임계값 (thresholds)
        thresholds = {
            "photorealism": 85,
            "anatomy": 80,
            "micro_detail": 75,
            "face_identity": 90,
            "expression": 75,
            "body_type": 85,
            "outfit_accuracy": 80,
            "brand_compliance": 75,
            "environmental_integration": 75,
            "lighting_mood": 75,
            "composition": 80,
            "pose_quality": 75,
        }

        # 항목 순서 및 한글명
        criteria_order = [
            ("photorealism", "실사감", "8%"),
            ("anatomy", "해부학 정확도", "8%"),
            ("micro_detail", "마이크로 디테일", "7%"),
            ("face_identity", "얼굴 동일성", "15%"),
            ("expression", "표정", "8%"),
            ("body_type", "체형 일치", "7%"),
            ("outfit_accuracy", "착장 정확도", "15%"),
            ("brand_compliance", "브랜드 톤", "10%"),
            ("environmental_integration", "환경 통합", "5%"),
            ("lighting_mood", "조명/무드", "5%"),
            ("composition", "구도", "6%"),
            ("pose_quality", "포즈 품질", "6%"),
        ]

        lines = [
            "## 검수 결과",
            "",
            "| 기준 | 비중 | Pass 조건 | 점수 | 통과 |",
            "|------|------|-----------|------|------|",
        ]

        for key, name_kr, weight in criteria_order:
            score = getattr(self, key, 0)
            threshold = thresholds[key]
            passed_mark = check(score, threshold)
            lines.append(
                f"| {name_kr} | {weight} | >= {threshold} | {score} | {passed_mark} |"
            )

        # 총점 및 판정
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

        # 이슈 추가
        if self.issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in self.issues[:5]:
                lines.append(f"- {issue}")

        # 게이트 실패 사유
        if self.gate_checked and not self.gate_passed and self.gate_failed_reasons:
            lines.append("")
            lines.append("### 합성티 게이트 실패")
            for reason in self.gate_failed_reasons:
                lines.append(f"- {reason}")

        return "\n".join(lines)


@dataclass
class ValidationThresholds:
    """Configurable thresholds for quality classification"""

    # Overall score thresholds
    total_score_release: int = 90  # S/A grade
    total_score_minor_edit: int = 85  # B grade
    total_score_regenerate: int = 75  # C grade, below = F

    # PASS criteria
    pass_total: int = 85
    pass_anatomy: int = 80
    pass_face_identity: int = 90  # 더 엄격 (85 → 90)
    pass_expression: int = 75
    pass_outfit_accuracy: int = 80
    pass_brand_compliance: int = 75
    pass_pose_quality: int = 70  # 포즈 레퍼런스 제공 시 필수
    pass_lighting_mood: int = 70  # 무드 레퍼런스 제공 시 필수

    # Auto-fail thresholds
    auto_fail_thresholds: dict = field(
        default_factory=lambda: {
            "anatomy": 50,  # 손가락 기형
            "micro_detail": 50,  # 플라스틱 피부
            "face_identity": 70,  # 다른 사람 (더 엄격)
            "expression": 50,  # 반감은 눈/미소
            "body_type": 75,  # 체형 불일치 (더 엄격)
            "outfit_accuracy": 50,  # 착장 누락/로고 변형
            "brand_compliance": 50,  # 지저분한 배경
            "environmental_integration": 50,  # 합성 느낌
            "lighting_mood": 50,  # 누런 톤
            "pose_quality": 50,  # 포즈 레퍼런스와 완전히 다름
            "unintended_text": 50,  # 의도하지 않은 텍스트/워터마크
        }
    )

    # Weights for total score calculation (총 100%)
    weights: dict = field(
        default_factory=lambda: {
            # A. 기본품질 (25%)
            "photorealism": 0.08,  # 10% → 8%
            "anatomy": 0.08,
            "micro_detail": 0.07,
            # B. 인물보존 (25%)
            "face_identity": 0.15,  # 10% → 15% (더 중요)
            "expression": 0.08,
            "body_type": 0.07,
            # C. 착장 (15%)
            "outfit_accuracy": 0.15,
            # D. 브랜드 (20%)
            "brand_compliance": 0.10,
            "environmental_integration": 0.05,
            "lighting_mood": 0.05,
            # E. 구도 (15%)
            "composition": 0.06,  # 8% → 6%
            "pose_quality": 0.06,  # 7% → 6%
        }
    )


# Auto-fail 조건 설명 (한국어)
AUTO_FAIL_DESCRIPTIONS = {
    "anatomy": "손가락 기형 또는 해부학 오류",
    "micro_detail": "플라스틱/에어브러시 피부",
    "face_identity": "얼굴 다른 사람",
    "expression": "반감은 눈/미소/찡그림",
    "body_type": "체형 불일치",
    "outfit_accuracy": "핵심 착장/로고 누락 또는 변형",
    "brand_compliance": "지저분한 배경 (간판/차량/행인)",
    "environmental_integration": "합성 느낌 배경",
    "lighting_mood": "누런 톤/골든아워",
    "pose_quality": "포즈/앵글/구도 레퍼런스와 불일치",
    "unintended_text": "의도하지 않은 텍스트/워터마크",
}


# 프롬프트 보강 규칙 (재시도용)
ENHANCEMENT_RULES = {
    "photorealism": [
        "CRITICAL: Must look like REAL PHOTOGRAPH",
        "Natural skin texture with pores",
        "Realistic shadow gradients",
        "Shot on Canon EOS R5, 85mm f/1.4",
    ],
    "anatomy": [
        "CRITICAL: Perfect human anatomy",
        "Exactly 5 fingers per hand",
        "Correct body proportions",
        "Natural joint positions",
    ],
    "micro_detail": [
        "ENHANCE: Add visible skin pores (forehead high density, nose visible, cheeks scattered)",
        "Natural texture variance, subtle imperfections",
        "Hair strand detail, fabric weave texture",
        "NO airbrushed perfection",
    ],
    "face_identity": [
        "CRITICAL: Face must be IDENTICAL to reference",
        "Preserve exact eye shape, nose, jawline",
        "Match skin tone precisely",
        "100% recognizable as same person",
    ],
    "expression": [
        "EXPRESSION: Large, wide-open eyes (K-pop style)",
        "NO SMILE - absolutely forbidden",
        "Neutral or pouty lips",
        "Cold confidence / innocent chic",
    ],
    "body_type": [
        "CRITICAL: Body type must match reference exactly",
        "Same height, build, proportions",
        "No body modification",
    ],
    "outfit_accuracy": [
        "CRITICAL: ALL clothing must match exactly",
        "Preserve exact colors, logos, patterns",
        "All accessories present",
        "No color shifts allowed",
    ],
    "brand_compliance": [
        "BACKGROUND: Clean, premium, minimalist",
        "Brutalist concrete / minimal architecture / private gallery",
        "NO street clutter, signs, vehicles, pedestrians",
        "MLB 'Young & Rich' aesthetic",
    ],
    "environmental_integration": [
        "Model must appear ACTUALLY in the scene",
        "Natural ground contact shadows",
        "No composited/pasted look",
        "Seamless environment integration",
    ],
    "lighting_mood": [
        "LIGHTING: Neutral cool 5600K-6200K only",
        "ABSOLUTELY NO warm/golden/amber tones",
        "Directional soft lighting",
        "No yellow color cast",
    ],
    "composition": [
        "Editorial composition, creative framing",
        "Variety of angles (low, high, 3/4)",
        "Magazine cover quality",
        "Not just boring frontal shots",
    ],
    "pose_quality": [
        "CRITICAL: COPY POSE REFERENCE EXACTLY",
        "Match exact body position from reference",
        "Match exact camera angle (low/eye-level/high)",
        "Match exact leg and arm positions",
        "Match exact framing (full body/half body/close-up)",
    ],
    "unintended_text": [
        "CRITICAL: NO unintended text or watermarks",
        "Remove any AI-generated text artifacts",
        "No brand names unless on actual product",
        "No floating text or symbols",
    ],
}


class MLBValidator:
    """Validator for MLB A-to-Z generation quality assessment (12 criteria)"""

    # Self-Critique Loop settings
    MAX_SELF_CRITIQUE_ITERATIONS = 3
    TARGET_SCORE = 90

    VALIDATION_PROMPT = """## MLB KOREA 통합 품질 검증 (v4.0 - 13개 기준)

당신은 MLB Korea 브랜드컷의 품질을 평가하는 전문가입니다.
아래 13개 기준으로 이미지를 평가하세요.

---

## CATEGORY A: 기본 품질 (25%)

### 1. photorealism (10%)
실제 사진처럼 보이는가?
- 90-100: 실제 패션 매거진 수준
- 70-89: 좋지만 약간 AI 느낌
- 50-69: AI 생성 티가 남
- 0-49: 명백히 AI/CG

### 2. anatomy (8%)
해부학적으로 정확한가?
- 90-100: 완벽 (손가락 5개, 비율 정확)
- 70-89: 사소한 문제
- 50-69: 눈에 띄는 오류
- 0-49: 심각한 기형 (손가락 6개 등) → AUTO-FAIL

### 3. micro_detail (7%)
마이크로 디테일이 살아있는가?
- 피부 질감 (모공, 잔털)
- 머리카락 디테일 (잔머리, 광택)
- 옷감 텍스처 (직조, 주름)
- 0-49: 플라스틱/에어브러시 피부 → AUTO-FAIL

---

## CATEGORY B: 인물 보존 (25%)

### 4. face_identity (10%) ★ 매우 엄격하게 평가
[FACE REFERENCE] 이미지의 인물과 [GENERATED IMAGE]의 인물이 **정확히 같은 사람**인가?

**반드시 비교할 특징:**
- 눈 모양 (쌍꺼풀 유무, 눈꼬리 각도, 눈 크기)
- 코 (콧대 높이, 코끝 모양, 콧볼 너비)
- 입 (입술 두께, 인중 길이, 입꼬리 모양)
- 턱선 (각진/둥근, V라인 여부)
- 광대뼈 (높이, 돌출 정도)
- 이마 (넓이, 헤어라인)

**점수 기준 (엄격하게!):**
- 95-100: 100% 동일인. 모든 특징 완벽 일치.
- 85-94: 동일인이지만 조명/각도로 약간 달라 보임
- 70-84: 비슷해 보이지만 확신 불가. 일부 특징 불일치.
- 50-69: 다른 사람. 눈/코/입 중 2개 이상 다름.
- 0-49: 완전히 다른 사람. 전혀 닮지 않음. → AUTO-FAIL

**중요:**
- "분위기가 비슷하다" ≠ 같은 사람
- 머리 스타일, 메이크업, 의상은 무시하고 **골격 구조만** 비교
- 조금이라도 다른 사람 같으면 70점 이하
- 확실히 다른 사람이면 50점 이하

### 5. expression (8%)
표정이 MLB 기준에 맞는가?
- **눈 크기**: LARGE, FULLY OPEN (K-pop 스타일)
- **입**: 중립, 파우팅, 또는 살짝 벌림 (미소/치아 금지)
- 90-100: 큰 눈 + 시크한 표정
- 70-89: 눈 약간 작거나 표정 애매
- 50-69: 눈 작음 또는 부적절한 표정
- 0-49: 반감은 눈 / 미소 / 찡그림 → AUTO-FAIL

### 6. body_type (7%)
체형이 참조와 일치하는가?
- 90-100: 완벽히 동일한 체형
- 70-89: 약간 차이
- 0-69: 체형 불일치 (날씬→뚱뚱 등) → AUTO-FAIL

---

## CATEGORY C: 착장 (15%)

### 7. outfit_accuracy (15%) ★★★ [OUTFIT REFERENCE]와 반드시 비교! ★★★

⚠️⚠️⚠️ 경고: [OUTFIT REFERENCE] 이미지들이 제공되었습니다! 반드시 비교해야 합니다! ⚠️⚠️⚠️

**[STEP 0] 먼저 [GENERATED IMAGE]의 샷 타입 판단:**

| 샷 타입 | 프레이밍 | 물리적으로 보이는 범위 |
|---------|----------|----------------------|
| 전신샷 (Full Body) | 머리~발끝 | 모든 아이템 보임 |
| 무릎샷 (Knee Shot) | 머리~무릎 | 신발 안 보임 (OK) |
| 허리샷 (Waist Shot) | 머리~허리 | 하의 일부만, 신발 안 보임 (OK) |
| 상반신 (Upper Body) | 머리~가슴 | 상의/모자만, 하의/신발 안 보임 (OK) |
| 얼굴 클로즈업 (Face Closeup) | 얼굴~어깨 | 상의 목선/어깨만, 모자 있으면 보임 |
| 익스트림 클로즈업 (Extreme CU) | 얼굴만 | 얼굴만 보임 |

**[STEP 0.5] 레퍼런스 아이템 총 개수 카운트:**

[OUTFIT REFERENCE] 이미지들에서 제공된 아이템을 모두 세어서 기록하세요.

- REF 아우터 있음? (O / X)
- REF 이너 있음? (O / X)
- REF 헤드웨어 있음? (O / X)
- REF 하의 있음? (O / X)
- REF 신발 있음? (O / X)
- REF 악세서리1 있음? (O / X) - 종류: ___
- REF 악세서리2 있음? (O / X) - 종류: ___

**REF 총 아이템 수 = ___ 개**

⚠️ 이 숫자를 반드시 기억하고, STEP 2.5에서 GEN 이미지와 비교! ⚠️

**[STEP 1] [OUTFIT REFERENCE] 이미지들을 상세 분석:**
각 아이템별로 다음 정보를 정확히 기록:

- REF 아우터(점퍼/자켓) = ?
  - 종류: (바시티, 블루종, 봄버 등)
  - 색상: (정확한 색상)
  - 로고 위치: (왼가슴, 오른팔, 등판 등)
  - 로고 종류: (NY, LA, Red Sox 등)
  - 재질: (새틴, 가죽, 울 등)
  - 특징: (화이트 소매, 리브 배색 등)

- REF 이너(티셔츠/탱크탑) = ?
  - 종류/색상/로고위치/로고종류/재질/특징

- REF 헤드웨어(모자/비니) = ?
  - 종류/색상/로고위치/로고종류/재질/특징

- REF 하의 = ?
  - 종류/색상/로고위치/재질/특징

- REF 신발 = ?
  - 종류/색상/특징

- REF 악세서리(가방/백팩/시계/주얼리/스카프) = ?
  - 종류: (크로스백, 백팩, 토트백, 숄더백 등)
  - 색상: (정확한 색상)
  - 로고 위치: (전면, 스트랩, 지퍼탭 등)
  - 로고 종류: (NY, LA, 모노그램 등)
  - 재질: (가죽, 캔버스, 나일론 등)
  - 특징: (체인, 키링, 패치 등)

**[STEP 2] [GENERATED IMAGE]에서 착용 아이템 동일하게 분석:**
- GEN 아우터 = ? (종류/색상/로고위치/로고종류/재질/특징)
- GEN 이너 = ? (종류/색상/로고위치/로고종류/재질/특징)
- GEN 헤드웨어 = ? (종류/색상/로고위치/로고종류/재질/특징)
- GEN 하의 = ? (종류/색상/로고위치/재질/특징)
- GEN 신발 = ? (종류/색상/특징)
- GEN 악세서리 = ? (종류/색상/로고위치/로고종류/재질/특징)

**[STEP 2.5] 1:1 매칭 카운트 (CRITICAL):**

REF와 GEN을 1:1로 비교하여 누락 아이템 카운트:

- REF 총 아이템: ___ 개 (STEP 0.5에서 카운트한 숫자)
- GEN 확인된 아이템: ___ 개
- 누락 아이템: ___ 개

**누락 아이템 목록:**
- (누락된 아이템 이름 나열)

예시:
- REF 총 아이템: 5개 (점퍼, 탱크탑, 비니, 데님, 가방)
- GEN 확인된 아이템: 3개 (탱크탑, 데님, 스니커즈)
- 누락: 2개 (점퍼, 가방)

**⚠️⚠️⚠️ 누락이 1개 이상이면 → 즉시 0점 (FAIL) ⚠️⚠️⚠️**

**[STEP 3] 샷 타입별 물리적 노출 규칙:**

핵심 원칙: 물리적으로 프레임에 찍힐 수 없으면 없어도 OK, 찍혀야 하는데 없으면 FAIL

| 아이템 | 전신샷 | 무릎샷 | 허리샷 | 상반신 | 얼굴CU | 누락 시 |
|--------|--------|--------|--------|--------|--------|---------|
| 아우터 | 필수 | 필수 | 필수 | 필수 | 일부OK | → 0점 FAIL |
| 이너 | 필수 | 필수 | 필수 | 필수 | 일부OK | → 0점 FAIL |
| 헤드웨어 | 필수 | 필수 | 필수 | 필수 | 필수* | → 0점 FAIL |
| 하의 | 필수 | 필수 | 일부OK | 불가 | 불가 | -30 (전신/무릎) |
| 신발 | 필수 | 불가 | 불가 | 불가 | 불가 | -20 (전신만) |
| 악세서리(가방/비니) | 필수 | 필수 | 필수 | 필수 | 불가 | → 0점 FAIL |

* 헤드웨어: 레퍼런스에 있으면 모든 샷에서 반드시 보여야 함!
* 악세서리(가방/비니): 얼굴CU 제외 모든 샷에서 반드시 보여야 함!
* "불가" = 물리적으로 프레임 밖이라 안 보여도 감점 없음
* "일부OK" = 일부만 보여도 OK (잘려도 감점 없음)

**[STEP 4] 디테일 일치 검사 (CRITICAL):**

아이템이 존재해도 디테일이 다르면 감점!

| 불일치 항목 | 감점 |
|------------|------|
| 색상 완전 다름 | **-50점 (심각)** |
| 색상 톤 다름 (명도/채도) | -20점 |
| 로고 위치 다름 | **-30점** |
| 로고 종류 다름 (NY→LA 등) | **-50점 (심각)** |
| 로고 왜곡/변형 | -25점 |
| 로고 누락 (있어야 하는데 없음) | **-40점** |
| 재질 다름 (새틴→면 등) | -20점 |
| 형태/실루엣 다름 | -25점 |
| 특징 누락 (화이트소매 없음 등) | -20점 |

**[STEP 5] 최종 점수 계산:**

1. 먼저 필수 아이템 누락 체크:
   - 물리적으로 보여야 하는데 없음 → **즉시 0점 (FAIL)**

2. 디테일 감점 합산:
   - 모든 불일치 항목 감점 합계 계산
   - 최종 점수 = 100 - 합계 감점 (최소 0점)

**검증 예시 1 (전신샷에서 점퍼 누락):**
- 샷타입: 전신샷
- REF: 바시티점퍼(브라운/RedSox/왼가슴) + 탱크탑(블랙/NY) + 데님(다크그레이/NY) + 스니커즈
- GEN: 탱크탑(블랙/NY) + 데님(다크그레이) + 스니커즈 [점퍼 없음!]
- 판정: 아우터 필수인데 누락 → **0점 (FAIL)**

**검증 예시 2 (상반신에서 로고 위치 다름):**
- 샷타입: 상반신
- REF: 바시티점퍼(브라운/RedSox로고 왼가슴/화이트소매)
- GEN: 바시티점퍼(브라운/RedSox로고 등판/화이트소매)
- 판정: 로고 위치 다름(-30) → **70점**

**검증 예시 3 (무릎샷에서 신발 안 보임):**
- 샷타입: 무릎샷 (무릎까지만 프레임)
- REF: 점퍼 + 탱크탑 + 데님 + 스니커즈
- GEN: 점퍼 + 탱크탑 + 데님 [신발 프레임 밖]
- 판정: 무릎샷에서 신발은 물리적으로 안 보임 → **감점 없음 (100점)**

**검증 예시 4 (전신샷에서 가방 누락 - 단순 카운팅):**
- 샷타입: 전신샷
- REF 총 아이템: 5개 (점퍼, 탱크탑, 비니, 데님, 가방)
- GEN 확인된 아이템: 4개 (점퍼, 탱크탑, 비니, 데님)
- 누락: 1개 (가방)
- 판정: 누락 1개 이상 → **0점 (FAIL)**

**검증 예시 5 (무릎샷에서 비니 누락 - 단순 카운팅):**
- 샷타입: 무릎샷
- REF 총 아이템: 5개 (점퍼, 탱크탑, 비니, 데님, 가방)
- GEN 확인된 아이템: 4개 (점퍼, 탱크탑, 데님, 가방)
- 누락: 1개 (비니)
- 판정: 누락 1개 이상 → **0점 (FAIL)**

**검증 예시 6 (다중 누락 - 단순 카운팅):**
- 샷타입: 전신샷
- REF 총 아이템: 5개 (점퍼, 탱크탑, 비니, 데님, 가방)
- GEN 확인된 아이템: 2개 (탱크탑, 데님)
- 누락: 3개 (점퍼, 비니, 가방)
- 판정: 누락 3개 → **0점 (FAIL)**

**⚠️⚠️⚠️ 핵심: REF에 있는 아이템이 GEN에 없으면 누락! 누락 1개 이상이면 0점! ⚠️⚠️⚠️**

**중요: reason에 반드시 다음 형식으로 기재:**
"샷타입:X, REF총:N개, GEN총:M개, 누락:[아이템목록], 감점:-N"

예시:
- "샷타입:전신샷, REF총:5개, GEN총:3개, 누락:[점퍼,가방], 감점:-100(FAIL)"
- "샷타입:무릎샷, REF총:5개, GEN총:4개, 누락:[비니], 감점:-100(FAIL)"
- "샷타입:전신샷, REF총:5개, GEN총:5개, 누락:[], 감점:0"

---

## CATEGORY D: 브랜드 톤앤매너 (20%)

### 8. brand_compliance (10%)
배경이 MLB "Young & Rich" 컨셉에 맞는가?
- **MUST**: 깨끗하고 모던한 배경
  - 브루탈리즘 콘크리트
  - 미니멀 건축
  - 프라이빗 갤러리
  - 럭셔리 공간
- **PROHIBITED**: 지저분한 배경
  - 복잡한 거리 (간판, 차량, 행인)
  - 그래피티, 쓰레기
- 0-49: 지저분한 거리/간판/차량 → AUTO-FAIL

### 9. environmental_integration (5%)
모델이 환경과 자연스럽게 어우러지는가?
- 합성 느낌 없이 일체감
- 그림자/반사 자연스러움
- 0-49: 명백한 합성 느낌 → AUTO-FAIL

### 10. lighting_mood (5%) ★★★ [MOOD REFERENCE]와 반드시 비교! ★★★

⚠️ [MOOD REFERENCE] 이미지가 제공되었습니다! 반드시 비교해야 합니다!

**[STEP 1] [MOOD REFERENCE] 이미지 분석:**
- REF 색온도 = ? (쿨톤/뉴트럴/웜톤)
- REF 조명방향 = ? (정면광/측광/역광/탑라이트)
- REF 그림자 = ? (소프트/하드)
- REF 분위기 = ? (밝음/어두움/드라마틱)

**[STEP 2] [GENERATED IMAGE] 분석:**
- GEN 색온도 = ?
- GEN 조명방향 = ?
- GEN 그림자 = ?
- GEN 분위기 = ?

**[STEP 3] 비교 및 점수:**
- 색온도: 같음(0) / 다름(-15)
- 조명방향: 같음(0) / 다름(-10)
- 그림자: 같음(0) / 다름(-10)
- 분위기: 같음(0) / 다름(-15)
- 누런톤 있으면: -50 (AUTO-FAIL)

**reason 필수 형식:** "REF:쿨톤+측광+소프트, GEN:웜톤+정면광+소프트, 감점:-25"

**[MOOD REFERENCE] 없는 경우만:** MLB 쿨톤 기준으로 평가

---

## CATEGORY E: 구도/프레이밍 (15%)

### 11. composition (8%)
구도와 프레이밍이 흥미로운가?
- 다양한 앵글 (로우, 하이, 3/4)
- 창의적 프레이밍 (크롭, 레이어)
- 90-100: 매거진 커버급 구도
- 70-89: 괜찮은 구도
- 50-69: 평범하고 재미없음
- 0-49: 아마추어 스냅샷 수준

### 12. pose_quality (7%) ★★★ [POSE REFERENCE]와 반드시 비교! ★★★

⚠️⚠️⚠️ 경고: [POSE REFERENCE] 이미지가 제공되었습니다! 반드시 비교해야 합니다! ⚠️⚠️⚠️

**[STEP 1] 먼저 [POSE REFERENCE] 이미지를 분석하세요:**
- REF 기본자세 = ? (서있음/앉음/기대어앉음/눕기)
- REF 카메라앵글 = ? (로우앵글/아이레벨/하이앵글)
- REF 프레이밍 = ? (전신/무릎위/허리위/클로즈업)
- REF 다리배치 = ? (벌림/모음/한쪽구부림)

**[STEP 2] 그 다음 [GENERATED IMAGE]를 분석하세요:**
- GEN 기본자세 = ?
- GEN 카메라앵글 = ?
- GEN 프레이밍 = ?
- GEN 다리배치 = ?

**[STEP 3] 하나씩 비교하고 점수 계산하세요:**
- 기본자세: REF vs GEN → 같음(0) / 다름(-30)
- 앵글: REF vs GEN → 같음(0) / 다름(-20)
- 프레이밍: REF vs GEN → 같음(0) / 다름(-15)
- 다리배치: REF vs GEN → 같음(0) / 다름(-15)
- 합계 감점 = ?점

**[STEP 4] 최종 점수 = 100 - 합계 감점**

**예시 (반드시 이 방식으로 계산!):**
- REF: 차에 앉음 + 로우앵글 + 전신 + 다리벌림
- GEN: 차에 앉음 + 아이레벨 + 무릎위 + 다리모음
- 감점: 자세(0) + 앵글(-20) + 프레이밍(-15) + 다리(-15) = -50점
- **최종: 100-50 = 50점**

**중요: reason에 반드시 "REF:~, GEN:~, 감점:~" 형식으로 비교 내용 기재!**

**[POSE REFERENCE] 없는 경우만:** 일반 포즈 품질로 평가 (기본 90점 시작)

---

## RESPONSE FORMAT (JSON only)

**중요: 각 항목에 점수와 함께 반드시 한국어 사유(reason)를 작성하세요.**

```json
{{
  "photorealism": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "anatomy": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "micro_detail": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "face_identity": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "expression": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "body_type": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "outfit_accuracy": {{
    "score": <0-100>,
    "reason": "<한국어 사유>",
    "missing_items": ["<누락 아이템1>", "<누락 아이템2>"],
    "mismatched_attributes": {{
      "<아이템명>": ["<불일치1: 색상 RED→BLUE>", "<불일치2: 로고 누락>"]
    }}
  }},
  "brand_compliance": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "environmental_integration": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "lighting_mood": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "composition": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "pose_quality": {{"score": <0-100>, "reason": "<한국어 사유>"}},
  "issues": ["<문제점1>", "<문제점2>"],
  "strengths": ["<장점1>", "<장점2>"],
  "summary_kr": "<한국어 1-2문장 요약>"
}}
```

**⚠️ outfit_accuracy 필수 필드:**
- `missing_items`: 누락된 아이템 목록 (비어있으면 [] 반환)
- `mismatched_attributes`: 아이템별 불일치 속성 (비어있으면 {{}} 반환)
- **missing_items가 1개 이상이면 → score는 반드시 0점!**
- **mismatched_attributes에 "로고", "색상" 불일치가 있으면 → score 50점 이하!**

**reason 예시:**
- "피부 질감과 조명이 실제 사진과 구분 불가"
- "손가락 5개, 관절 자연스러움"
- "레퍼런스와 눈/코/턱 형태 일치, 동일인"
- "레퍼런스 대비 머리카락 색상 살짝 다름"

**⚠️ pose_quality reason 필수 형식 (POSE REFERENCE 있을 때):**
- "REF:기대어앉음+로우앵글+전신+다리벌림, GEN:앉음+아이레벨+무릎위+다리모음, 감점:-50 (앵글-20,프레이밍-15,다리-15)"

**⚠️ outfit_accuracy reason 필수 형식:**
- "REF:바시티점퍼+탱크탑+카고데님, GEN:탱크탑+카고데님, 누락:점퍼, 감점:-50"
"""

    def __init__(
        self, client: genai.Client, thresholds: Optional[ValidationThresholds] = None
    ):
        """
        Initialize validator

        Args:
            client: Initialized Gemini API client
            thresholds: Optional custom thresholds (uses defaults if not provided)
        """
        self.client = client
        self.thresholds = thresholds or ValidationThresholds()

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        face_images: List[Union[str, Path, Image.Image]] = None,
        outfit_images: List[Union[str, Path, Image.Image]] = None,
        style_images: List[Union[str, Path, Image.Image]] = None,
        pose_reference: Optional[Union[str, Path, Image.Image]] = None,
        mood_reference: Optional[Union[str, Path, Image.Image]] = None,
        outfit_spec: Optional["OutfitAnalysis"] = None,  # NEW: 정답 스펙 기반 검증
        shot_preset: dict = None,
        check_ai_artifacts: bool = False,
        check_gate: bool = False,  # 게이트 체크 (기본 비활성화)
    ) -> ValidationResult:
        """
        Run VLM validation and classify result into quality tier

        Args:
            generated_img: Generated image to validate (path or PIL Image)
            face_images: Reference face images (paths or PIL Images)
            outfit_images: Reference outfit images (paths or PIL Images)
            style_images: Reference style images (paths or PIL Images)
            pose_reference: Reference pose image for pose comparison (path or PIL Image)
            mood_reference: Reference mood image for lighting/mood comparison (path or PIL Image)
            outfit_spec: OutfitAnalysis from analyze_outfit() - 정답 스펙 기반 검증 (권장)
            shot_preset: Optional shot preset dict
            check_ai_artifacts: If True, run AI artifact detection (default: False)
            check_gate: If True, run synthesis gate check first (default: True)

        Returns:
            ValidationResult with all metrics and quality tier classification
        """
        # Step 0: 합성티 게이트 (check_gate=True일 때)
        gate_passed = True
        gate_failed_reasons = []

        if check_gate:
            # 게이트 체크는 이미지만 필요
            gen_img_pil = self._load_image(generated_img)
            gate_result = self._check_synthesis_gate(gen_img_pil)
            gate_passed = gate_result["passed"]
            gate_failed_reasons = gate_result.get("failed_reasons", [])

            # [CHANGED] Gate 실패해도 VLM 채점은 계속 진행
            # gate_passed 변수에 결과 저장만 하고 early return 제거
            # Step 6에서 gate 결과 반영

        # Step 1: 기존 12개 기준 채점 (Gate 실패 여부와 무관하게 항상 수행)

        # 필수 참조 이미지 검증
        if not face_images or len(face_images) == 0:
            raise ValueError(
                "face_images is required for validation. Cannot evaluate face_identity/body_type without reference."
            )

        if not outfit_images or len(outfit_images) == 0:
            raise ValueError(
                "outfit_images is required for validation. Cannot evaluate outfit_accuracy without reference."
            )

        # Load images
        gen_img = self._load_image(generated_img)
        faces = [self._load_image(f) for f in (face_images or [])]
        outfits = [self._load_image(o) for o in (outfit_images or [])]
        styles = [self._load_image(s) for s in (style_images or [])]

        # Prepare content for VLM
        content_parts = [types.Part(text=self.VALIDATION_PROMPT)]

        content_parts.append(types.Part(text="\n\n[GENERATED IMAGE TO EVALUATE]"))
        content_parts.append(self._pil_to_part(gen_img))

        if faces:
            content_parts.append(
                types.Part(text="\n\n[FACE REFERENCE - 얼굴/표정/체형 비교용]")
            )
            for face in faces[:3]:
                content_parts.append(self._pil_to_part(face))

        if outfits:
            content_parts.append(
                types.Part(text="\n\n[OUTFIT REFERENCE - 착장 비교용]")
            )
            for outfit in outfits[:5]:
                content_parts.append(self._pil_to_part(outfit))

        # NEW: 정답 스펙 기반 검증 (outfit_spec이 있으면 추가)
        if outfit_spec is not None:
            spec_text = self._build_outfit_spec_section(outfit_spec)
            content_parts.append(types.Part(text=spec_text))

        if styles:
            content_parts.append(
                types.Part(text="\n\n[MLB STYLE REFERENCE - 브랜드 톤앤매너 비교용]")
            )
            for style in styles[:3]:
                content_parts.append(self._pil_to_part(style))

        # 포즈 레퍼런스 추가 (pose_quality 비교용)
        if pose_reference is not None:
            pose_img = self._load_image(pose_reference)
            content_parts.append(
                types.Part(
                    text="\n\n[POSE REFERENCE - 포즈/앵글/구도 비교용 ★ 필수 비교]"
                )
            )
            content_parts.append(self._pil_to_part(pose_img))

        # 무드 레퍼런스 추가 (lighting_mood 비교용)
        if mood_reference is not None:
            mood_img = self._load_image(mood_reference)
            content_parts.append(
                types.Part(
                    text="\n\n[MOOD REFERENCE - 조명/색감/분위기 비교용 ★ 필수 비교]"
                )
            )
            content_parts.append(self._pil_to_part(mood_img))

        # Call VLM
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_modalities=["TEXT"]
                ),
            )

            # Parse JSON response
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)

        except json.JSONDecodeError as e:
            print(f"[Validator] JSON parse error: {e}")
            return self._create_error_result(f"JSON parse error: {e}")
        except Exception as e:
            print(f"[Validator] VLM validation error: {e}")
            return self._create_error_result(f"VLM error: {e}")

        # Process result (레퍼런스 제공 여부 및 게이트 결과 전달)
        return self._process_result(
            result_dict,
            gen_img,
            check_ai_artifacts,
            check_gate,
            has_pose_ref=(pose_reference is not None),
            has_mood_ref=(mood_reference is not None),
            gate_passed=gate_passed,
            gate_failed_reasons=gate_failed_reasons,
        )

    def _extract_score_and_reason(self, value) -> tuple:
        """
        점수와 사유를 추출 (새 형식/구 형식 모두 지원)

        새 형식: {"score": 85, "reason": "사유"}
        구 형식: 85

        Returns:
            (score: int, reason: str)
        """
        if isinstance(value, dict):
            return value.get("score", 0), value.get("reason", "")
        elif isinstance(value, (int, float)):
            return int(value), ""
        return 0, ""

    def _normalize_result_dict(self, result_dict: dict) -> tuple:
        """
        VLM 응답을 정규화하여 점수 dict, 사유 dict, 착장 구조적 결과로 분리

        Returns:
            (scores: dict, reasons: dict, outfit_structural: dict)
        """
        score_keys = [
            "photorealism",
            "anatomy",
            "micro_detail",
            "face_identity",
            "expression",
            "body_type",
            "outfit_accuracy",
            "brand_compliance",
            "environmental_integration",
            "lighting_mood",
            "composition",
            "pose_quality",
        ]

        scores = {}
        reasons = {}
        outfit_structural = {
            "missing_items": [],
            "mismatched_attributes": {},
        }

        for key in score_keys:
            value = result_dict.get(key, 0)
            score, reason = self._extract_score_and_reason(value)
            scores[key] = score
            reasons[key] = reason

            # outfit_accuracy의 구조적 필드 추출
            if key == "outfit_accuracy" and isinstance(value, dict):
                outfit_structural["missing_items"] = value.get("missing_items", [])
                outfit_structural["mismatched_attributes"] = value.get(
                    "mismatched_attributes", {}
                )

        return scores, reasons, outfit_structural

    def _process_result(
        self,
        result_dict: dict,
        gen_img: Image.Image,
        check_ai_artifacts: bool,
        check_gate: bool,
        has_pose_ref: bool = False,
        has_mood_ref: bool = False,
        gate_passed: bool = True,
        gate_failed_reasons: List[str] = None,
    ) -> ValidationResult:
        """Process raw VLM result into ValidationResult"""
        # 새 형식(점수+사유+착장구조) 파싱
        scores, reasons, outfit_structural = self._normalize_result_dict(result_dict)

        # NEW: 착장 구조적 검증 - missing_items가 있으면 outfit_accuracy 자동 0점
        missing_items = outfit_structural.get("missing_items", [])
        mismatched_attrs = outfit_structural.get("mismatched_attributes", {})

        if missing_items:
            scores["outfit_accuracy"] = 0
            reasons["outfit_accuracy"] = f"누락 아이템: {', '.join(missing_items)}"

        # NEW: 심각한 불일치(로고/색상)가 있으면 50점 이하로 제한
        if mismatched_attrs:
            critical_mismatch = False
            for item_name, mismatches in mismatched_attrs.items():
                for mismatch in mismatches:
                    if (
                        "로고" in mismatch
                        or "색상" in mismatch
                        or "logo" in mismatch.lower()
                        or "color" in mismatch.lower()
                    ):
                        critical_mismatch = True
                        break
            if critical_mismatch and scores["outfit_accuracy"] > 50:
                scores["outfit_accuracy"] = 50
                reasons["outfit_accuracy"] = f"심각한 불일치: {mismatched_attrs}"

        # Calculate total score
        total_score = self._calculate_total_score(scores)

        # Check auto-fail conditions
        auto_fail, auto_fail_reasons = self._check_auto_fail(scores)

        # AI 티 체크 (선택적)
        ai_artifact_score = None
        ai_artifact_grade = None
        ai_artifact_issues = []

        if check_ai_artifacts:
            try:
                from core.ai_artifact_detector import AIArtifactDetector

                detector = AIArtifactDetector(self.client)
                artifact_result = detector.detect(gen_img)
                ai_artifact_score = artifact_result.total_ai_score
                ai_artifact_grade = artifact_result.naturalness_grade
                ai_artifact_issues = artifact_result.critical_issues

                # AI 티 심각 시 auto_fail에 추가
                if artifact_result.total_ai_score >= 70:  # F등급
                    auto_fail = True
                    auto_fail_reasons.append(
                        f"AI artifact score {ai_artifact_score} (F grade)"
                    )
            except Exception as e:
                print(f"[Validator] AI artifact check error: {e}")

        # Determine grade
        grade = self._determine_grade(total_score, auto_fail)

        # Determine tier
        tier = self._determine_tier(total_score, auto_fail, grade)

        # Check passed (레퍼런스 제공 여부에 따라 조건 적용)
        passed = self._check_passed(
            scores,
            total_score,
            auto_fail,
            has_pose_ref=has_pose_ref,
            has_mood_ref=has_mood_ref,
        )

        # Extract issues and strengths
        issues = self._extract_issues(scores, total_score)
        strengths = self._extract_strengths(scores)

        # Get summary
        summary_kr = result_dict.get("summary_kr", "")

        # Create result with 12-criteria scores
        result = ValidationResult(
            # A. 기본품질
            photorealism=scores.get("photorealism", 0),
            anatomy=scores.get("anatomy", 0),
            micro_detail=scores.get("micro_detail", 0),
            # B. 인물보존
            face_identity=scores.get("face_identity", 0),
            expression=scores.get("expression", 0),
            body_type=scores.get("body_type", 0),
            # C. 착장
            outfit_accuracy=scores.get("outfit_accuracy", 0),
            # D. 브랜드
            brand_compliance=scores.get("brand_compliance", 0),
            environmental_integration=scores.get("environmental_integration", 0),
            lighting_mood=scores.get("lighting_mood", 0),
            # E. 구도
            composition=scores.get("composition", 0),
            pose_quality=scores.get("pose_quality", 0),
            # 결과
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            strengths=strengths,
            summary_kr=summary_kr,
            raw_response=result_dict,
            # 각 항목별 점수 사유
            reasons=reasons,
            # AI 티 검사 결과
            ai_artifact_score=ai_artifact_score,
            ai_artifact_grade=ai_artifact_grade,
            ai_artifact_issues=ai_artifact_issues,
            # 게이트 결과 (기본값)
            gate_passed=True,
            gate_failed_reasons=[],
            gate_checked=check_gate,
            # 착장 구조적 검증 결과 (NEW)
            outfit_missing_items=missing_items,
            outfit_mismatched_attributes=mismatched_attrs,
        )

        # Step 6: Gate 결과 반영 [NEW - gate 실패해도 12개 기준 점수 유지]
        if check_gate:
            result.gate_checked = True
            result.gate_passed = gate_passed
            result.gate_failed_reasons = gate_failed_reasons or []

            if not gate_passed:
                # 게이트 실패 시: 점수는 유지, 통과만 불가
                result.auto_fail = True
                if gate_failed_reasons:
                    result.auto_fail_reasons = (gate_failed_reasons or []) + (
                        result.auto_fail_reasons or []
                    )
                result.passed = False
                result.tier = QualityTier.REGENERATE
                result.summary_kr = f"[GATE FAIL] {', '.join(gate_failed_reasons or [])} | Score: {result.total_score}"

        return result

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """Load image from path or return PIL Image"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """Convert PIL Image to Gemini Part"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )

    def _build_outfit_spec_section(self, outfit_spec: "OutfitAnalysis") -> str:
        """
        OutfitAnalysis를 VLM 프롬프트용 정답 스펙 텍스트로 변환

        Args:
            outfit_spec: analyze_outfit()에서 반환된 OutfitAnalysis

        Returns:
            VLM 프롬프트에 추가할 정답 스펙 섹션
        """
        lines = [
            "\n\n[OUTFIT SPEC (Ground Truth) - 정답 스펙 기반 검증]",
            "⚠️⚠️⚠️ 이 스펙이 정답입니다! GENERATED IMAGE와 1:1 비교하세요! ⚠️⚠️⚠️",
            "",
            f"총 아이템 개수: {len(outfit_spec.items)}개",
            "",
            "**필수 아이템 목록:**",
        ]

        for i, item in enumerate(outfit_spec.items, 1):
            # 기본 정보
            item_line = f"{i}. [{item.category.upper()}] {item.name}"
            item_line += f" | 색상: {item.color} | 핏: {item.fit}"

            # 로고 정보
            if item.logos:
                for logo in item.logos:
                    item_line += (
                        f"\n   - LOGO: {logo.brand} @ {logo.position} ({logo.type})"
                    )

            # 핵심 디테일 (blind_spot)
            if item.details:
                item_line += f"\n   - CRITICAL: {', '.join(item.details)}"

            lines.append(item_line)

        lines.extend(
            [
                "",
                "**검증 지침:**",
                "1. 위 아이템이 GENERATED IMAGE에 모두 있는지 확인",
                "2. 누락된 아이템이 있으면 missing_items에 기록",
                "3. 색상/로고/핏이 다르면 mismatched_attributes에 기록",
                "4. missing_items 또는 mismatched_attributes가 있으면 → outfit_accuracy 자동 0점",
            ]
        )

        return "\n".join(lines)

    def _check_synthesis_gate(self, image: Image.Image) -> dict:
        """합성티 게이트 체크

        AI 아티팩트가 하나라도 있으면 FAIL.

        Returns:
            {"passed": bool, "failed_reasons": List[str]}
        """
        img_part = self._pil_to_part(image)

        gate_prompt = """
## 합성티 게이트 검사

이 이미지에서 AI 합성 아티팩트를 검사합니다.
아래 항목 중 하나라도 해당되면 FAIL입니다.

### 체크 항목

1. 눈/시선 인공감
   - ring catchlight (도넛 모양 반사광)
   - white sclera (공막이 너무 하얗고 균일)
   - gaze mismatch (양 눈 시선 방향 불일치)

2. 피부 플라스틱/과샤픈
   - 모공 완전 부재
   - 경계가 과도하게 날카로움
   - 밀랍/도자기 표면

3. 손/입/귀/헤어라인 아티팩트
   - 손가락 5개 아님
   - 기형적 손가락/관절
   - 입술/치아 왜곡
   - 귀 형태 이상
   - 헤어라인 부자연스러움

4. 조명 물리 위반
   - 그림자 방향 불일치
   - 발/손 아래 그림자 없음
   - 다중 광원 하이라이트

5. 로고/텍스트 오류
   - 로고 번짐/왜곡
   - 읽을 수 없는 텍스트
   - 의도하지 않은 텍스트/워터마크 (AI가 임의 생성한 글자)

### 응답 (JSON)
{
  "passed": true/false,
  "failed_reasons": ["피부 모공 부재", "로고 왜곡"]
}

명백한 오류만 FAIL 처리하세요. 경미한 문제는 PASS 후 점수에서 감점합니다.
"""

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Content(
                        role="user", parts=[types.Part(text=gate_prompt), img_part]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_modalities=["TEXT"]
                ),
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result = json.loads(raw_text)
            return {
                "passed": result.get("passed", False),
                "failed_reasons": result.get("failed_reasons", []),
            }
        except json.JSONDecodeError as e:
            # 파싱 실패 시 FAIL 처리
            print(f"[Gate] JSON parse error: {e}")
            return {"passed": False, "failed_reasons": ["게이트 응답 파싱 실패"]}
        except Exception as e:
            # 기타 에러 시 FAIL 처리
            print(f"[Gate] VLM error: {e}")
            return {"passed": False, "failed_reasons": [f"게이트 체크 에러: {str(e)}"]}

    def _calculate_total_score(self, result: dict) -> int:
        """Calculate weighted total score"""
        weights = self.thresholds.weights
        total = 0.0

        for metric, weight in weights.items():
            score = result.get(metric, 0)
            total += score * weight

        return round(total)

    def _check_auto_fail(self, result: dict) -> Tuple[bool, List[str]]:
        """Check auto-fail conditions (현재 비활성화 - 경고만 기록)"""
        # auto_fail 비활성화: 항상 False 반환, 이슈만 기록
        reasons = []

        for criterion, threshold in self.thresholds.auto_fail_thresholds.items():
            score = result.get(criterion, 100)
            if score < threshold:
                # auto_fail = True  # 비활성화
                desc = AUTO_FAIL_DESCRIPTIONS.get(criterion, criterion)
                reasons.append(f"{desc} ({criterion}: {score})")

        return False, reasons  # 항상 False 반환

    def _determine_grade(self, total_score: int, auto_fail: bool) -> str:
        """Determine grade (S/A/B/C/F)"""
        if auto_fail:
            return "F"
        elif total_score >= 95:
            return "S"
        elif total_score >= 90:
            return "A"
        elif total_score >= 85:
            return "B"
        elif total_score >= 75:
            return "C"
        else:
            return "F"

    def _determine_tier(
        self, total_score: int, auto_fail: bool, grade: str
    ) -> QualityTier:
        """Determine quality tier"""
        if auto_fail or grade == "F":
            return QualityTier.REGENERATE
        elif grade in ("S", "A"):
            return QualityTier.RELEASE_READY
        elif grade == "B":
            return QualityTier.NEEDS_MINOR_EDIT
        else:  # C
            return QualityTier.REGENERATE

    def _check_passed(
        self,
        result: dict,
        total_score: int,
        auto_fail: bool,
        has_pose_ref: bool = False,
        has_mood_ref: bool = False,
    ) -> bool:
        """Check if validation passed

        모든 12개 기준이 95점 이상이어야 PASS. 하나라도 미달이면 FAIL.

        - 레퍼런스 있을 때: 레퍼런스와 비교
        - 레퍼런스 없을 때: MLB 프롬프트 치트시트 기준으로 평가

        Args:
            result: 점수 dict
            total_score: 총점
            auto_fail: auto-fail 여부
            has_pose_ref: 포즈 레퍼런스 제공 여부 (unused, 항상 체크)
            has_mood_ref: 무드 레퍼런스 제공 여부 (unused, 항상 체크)
        """
        if auto_fail:
            return False

        PASS_THRESHOLD = 95  # 모든 기준 95점 이상

        # 모든 12개 항목 체크 (레퍼런스 유무 관계없이)
        all_criteria = [
            "photorealism",
            "anatomy",
            "micro_detail",
            "face_identity",
            "expression",
            "body_type",
            "outfit_accuracy",
            "brand_compliance",
            "environmental_integration",
            "lighting_mood",
            "composition",
            "pose_quality",
        ]

        # 하나라도 95 미만이면 FAIL
        for criterion in all_criteria:
            if result.get(criterion, 0) < PASS_THRESHOLD:
                return False

        return True

    def _extract_issues(self, result: dict, total_score: int) -> List[str]:
        """Extract actionable issues"""
        issues = result.get("issues", [])
        extracted = []

        # Ensure issues is a list of strings
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, str):
                    extracted.append(issue)
                elif isinstance(issue, dict):
                    extracted.append(str(issue))

        # Add auto-detected issues based on scores
        score_thresholds = {
            ("photorealism", 85, "실사감 부족"),
            ("anatomy", 80, "해부학 오류"),
            ("micro_detail", 75, "디테일 부족 (피부/옷감)"),
            ("face_identity", 85, "얼굴 불일치"),
            ("expression", 75, "표정 부적절"),
            ("body_type", 85, "체형 불일치"),
            ("outfit_accuracy", 80, "착장 불일치"),
            ("brand_compliance", 75, "배경 부적절"),
            ("environmental_integration", 75, "합성 느낌"),
            ("lighting_mood", 75, "색온도 문제"),
            ("composition", 80, "구도 평범"),
            ("pose_quality", 75, "포즈 어색"),
        }

        for criterion, threshold, desc in score_thresholds:
            score = result.get(criterion, 0)
            if score < threshold:
                issue_str = f"{desc} ({criterion}: {score})"
                if issue_str not in extracted:
                    extracted.append(issue_str)

        return extracted

    def _extract_strengths(self, result: dict) -> List[str]:
        """Extract strengths"""
        strengths = result.get("strengths", [])
        extracted = []

        # Ensure strengths is a list of strings
        if isinstance(strengths, list):
            for strength in strengths:
                if isinstance(strength, str):
                    extracted.append(strength)
                elif isinstance(strength, dict):
                    extracted.append(str(strength))

        # Add auto-detected strengths
        if result.get("photorealism", 0) >= 95:
            extracted.append("뛰어난 실사감")
        if result.get("face_identity", 0) >= 95:
            extracted.append("완벽한 얼굴 일치")
        if result.get("outfit_accuracy", 0) >= 95:
            extracted.append("착장 완벽 재현")
        if result.get("expression", 0) >= 95:
            extracted.append("이상적인 표정")
        if result.get("brand_compliance", 0) >= 95:
            extracted.append("프리미엄 배경")
        if result.get("composition", 0) >= 95:
            extracted.append("매거진급 구도")

        return list(set(extracted))  # Remove duplicates

    def _create_error_result(self, error_msg: str) -> ValidationResult:
        """Create error result with REGENERATE tier"""
        return ValidationResult(
            photorealism=0,
            anatomy=0,
            micro_detail=0,
            face_identity=0,
            expression=0,
            body_type=0,
            outfit_accuracy=0,
            brand_compliance=0,
            environmental_integration=0,
            lighting_mood=0,
            composition=0,
            pose_quality=0,
            total_score=0,
            tier=QualityTier.REGENERATE,
            grade="F",
            passed=False,
            auto_fail=True,
            auto_fail_reasons=[f"Validation error: {error_msg}"],
            issues=[f"Validation error: {error_msg}"],
            strengths=[],
            summary_kr=f"검증 오류: {error_msg}",
            reasons={},  # 오류 시 사유 없음
        )

    def generate_report(
        self, results: List[ValidationResult], shot_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Generate batch validation report with statistics

        Args:
            results: List of ValidationResult objects
            shot_ids: Optional list of shot IDs corresponding to results

        Returns:
            Report dict with statistics and tier breakdown
        """
        if not results:
            return {"error": "No results to report"}

        total = len(results)

        # Grade counts
        grade_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "F": 0}
        tier_counts = {"RELEASE_READY": 0, "NEEDS_MINOR_EDIT": 0, "REGENERATE": 0}

        avg_scores = {
            "total_score": 0,
            "photorealism": 0,
            "anatomy": 0,
            "face_identity": 0,
            "expression": 0,
            "outfit_accuracy": 0,
            "brand_compliance": 0,
        }

        auto_fail_count = 0

        for result in results:
            grade_counts[result.grade] += 1
            tier_counts[result.tier.value] += 1

            avg_scores["total_score"] += result.total_score
            avg_scores["photorealism"] += result.photorealism
            avg_scores["anatomy"] += result.anatomy
            avg_scores["face_identity"] += result.face_identity
            avg_scores["expression"] += result.expression
            avg_scores["outfit_accuracy"] += result.outfit_accuracy
            avg_scores["brand_compliance"] += result.brand_compliance

            if result.auto_fail:
                auto_fail_count += 1

        # Calculate averages
        for key in avg_scores:
            avg_scores[key] = round(avg_scores[key] / total, 1)

        # Pass rate
        passed_count = sum(1 for r in results if r.passed)
        pass_rate = round(passed_count / total * 100, 1)

        # Usable rate (RELEASE_READY + NEEDS_MINOR_EDIT)
        usable_count = tier_counts["RELEASE_READY"] + tier_counts["NEEDS_MINOR_EDIT"]
        usable_rate = round(usable_count / total * 100, 1)

        # Build report
        report = {
            "summary": {
                "total_images": total,
                "passed": passed_count,
                "pass_rate": pass_rate,
                "usable_rate": usable_rate,
                "auto_fail_count": auto_fail_count,
            },
            "grades": grade_counts,
            "tiers": tier_counts,
            "average_scores": avg_scores,
            "details": [],
        }

        # Add per-image breakdown
        for i, result in enumerate(results):
            shot_id = shot_ids[i] if shot_ids and i < len(shot_ids) else f"Image_{i+1}"
            report["details"].append(
                {
                    "shot_id": shot_id,
                    "total_score": result.total_score,
                    "grade": result.grade,
                    "tier": result.tier.value,
                    "passed": result.passed,
                    "auto_fail": result.auto_fail,
                    "auto_fail_reasons": result.auto_fail_reasons,
                    "issues": result.issues[:3],  # Top 3 issues
                    "summary_kr": result.summary_kr,
                }
            )

        return report

    # 항목 한글명 매핑
    CRITERION_NAMES_KR = {
        "photorealism": "실사감",
        "anatomy": "해부학 정확도",
        "micro_detail": "마이크로 디테일",
        "face_identity": "얼굴 동일성",
        "expression": "표정",
        "body_type": "체형 일치",
        "outfit_accuracy": "착장 정확도",
        "brand_compliance": "브랜드 톤",
        "environmental_integration": "환경 통합",
        "lighting_mood": "조명/무드",
        "composition": "구도",
        "pose_quality": "포즈 품질",
    }

    def print_result(self, result: ValidationResult, filename: str = "") -> None:
        """검수 결과를 CLAUDE.md 규격 표 형식으로 출력"""
        print(f"\n## 검수 결과")
        if filename:
            print(f"\n**파일**: {filename}")
        print()

        # 표 헤더
        print("| 항목 | 점수 | 기준 | 통과 | 사유 |")
        print("|------|------|------|------|------|")

        # 카테고리별 기준점
        criteria_thresholds = {
            # A. 기본품질 (25%)
            "photorealism": ("실사감", result.photorealism, 85),
            "anatomy": ("해부학 정확도", result.anatomy, 80),
            "micro_detail": ("마이크로 디테일", result.micro_detail, 75),
            # B. 인물보존 (25%)
            "face_identity": ("얼굴 동일성", result.face_identity, 90),
            "expression": ("표정", result.expression, 75),
            "body_type": ("체형 일치", result.body_type, 85),
            # C. 착장 (15%)
            "outfit_accuracy": ("착장 정확도", result.outfit_accuracy, 80),
            # D. 브랜드 (20%)
            "brand_compliance": ("브랜드 톤", result.brand_compliance, 75),
            "environmental_integration": (
                "환경 통합",
                result.environmental_integration,
                75,
            ),
            "lighting_mood": ("조명/무드", result.lighting_mood, 75),
            # E. 구도 (15%)
            "composition": ("구도", result.composition, 80),
            "pose_quality": ("포즈 품질", result.pose_quality, 75),
        }

        # 항목 순서
        order = [
            "photorealism",
            "anatomy",
            "micro_detail",
            "face_identity",
            "expression",
            "body_type",
            "outfit_accuracy",
            "brand_compliance",
            "environmental_integration",
            "lighting_mood",
            "composition",
            "pose_quality",
        ]

        for key in order:
            name_kr, score, threshold = criteria_thresholds[key]
            passed_mark = "V" if score >= threshold else "X"
            reason = result.reasons.get(key, "-") if result.reasons else "-"
            # 사유가 너무 길면 자르기
            if len(reason) > 40:
                reason = reason[:37] + "..."
            print(f"| {name_kr} | {score} | >={threshold} | {passed_mark} | {reason} |")

        # 총점 및 판정
        tier_kr = {
            "RELEASE_READY": "납품 가능",
            "NEEDS_MINOR_EDIT": "소폭 보정 필요",
            "REGENERATE": "재생성 필요",
        }
        tier_text = tier_kr.get(result.tier.value, result.tier.value)

        print()
        print(
            f"**총점**: {result.total_score}/100 | **등급**: {result.grade} | **판정**: {tier_text}"
        )

        # Auto-fail 사유
        if result.auto_fail and result.auto_fail_reasons:
            print(f"\n### Auto-Fail 사유")
            for reason in result.auto_fail_reasons:
                print(f"- {reason}")

        # 게이트 실패
        if not result.gate_passed and result.gate_failed_reasons:
            print(f"\n### 합성티 게이트 실패")
            for reason in result.gate_failed_reasons:
                print(f"- {reason}")

        # 탈락 사유 (점수 기반)
        fail_items = []
        for key in order:
            name_kr, score, threshold = criteria_thresholds[key]
            if score < threshold:
                reason = result.reasons.get(key, "") if result.reasons else ""
                fail_items.append((name_kr, score, threshold, reason))

        if fail_items:
            print(f"\n### 탈락 사유")
            for name_kr, score, threshold, reason in fail_items:
                if reason:
                    print(f"- **{name_kr}** ({score}<{threshold}): {reason}")
                else:
                    print(f"- **{name_kr}** ({score}<{threshold})")

        # 장점
        if result.strengths:
            print(f"\n### 장점")
            for strength in result.strengths[:5]:
                print(f"- {strength}")

        # 요약
        if result.summary_kr:
            print(f"\n### 요약")
            print(f"{result.summary_kr}")

    def print_report(self, report: dict) -> None:
        """Pretty-print batch validation report"""
        print("\n" + "=" * 70)
        print("MLB UNIFIED VALIDATION REPORT (13 Criteria)")
        print("=" * 70)

        summary = report["summary"]
        print(f"\n[SUMMARY]")
        print(f"  Total Images: {summary['total_images']}")
        print(f"  Passed: {summary['passed']} ({summary['pass_rate']}%)")
        print(f"  Usable Rate: {summary['usable_rate']}%")
        print(f"  Auto-Fail: {summary['auto_fail_count']}")

        grades = report["grades"]
        print(f"\n[GRADE DISTRIBUTION]")
        print(
            f"  S: {grades['S']} | A: {grades['A']} | B: {grades['B']} | C: {grades['C']} | F: {grades['F']}"
        )

        tiers = report["tiers"]
        print(f"\n[TIER BREAKDOWN]")
        print(f"  RELEASE_READY: {tiers['RELEASE_READY']}")
        print(f"  NEEDS_MINOR_EDIT: {tiers['NEEDS_MINOR_EDIT']}")
        print(f"  REGENERATE: {tiers['REGENERATE']}")

        avg = report["average_scores"]
        print(f"\n[AVERAGE SCORES]")
        print(f"  Total: {avg['total_score']}")
        print(f"  Photorealism: {avg['photorealism']}")
        print(f"  Face Identity: {avg['face_identity']}")
        print(f"  Expression: {avg['expression']}")
        print(f"  Outfit Accuracy: {avg['outfit_accuracy']}")
        print(f"  Brand Compliance: {avg['brand_compliance']}")

        print("\n" + "=" * 70)
        print(
            "| {:^40} | {:^5} | {:^5} | {:^6} |".format(
                "Shot ID", "Score", "Grade", "Status"
            )
        )
        print("|" + "-" * 42 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 8 + "|")

        for detail in report["details"]:
            status = "PASS" if detail["passed"] else "FAIL"
            print(
                "| {:<40} | {:>5} | {:^5} | {:^6} |".format(
                    detail["shot_id"][:40],
                    detail["total_score"],
                    detail["grade"],
                    status,
                )
            )

        print("=" * 70)
