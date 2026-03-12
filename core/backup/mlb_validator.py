"""
MLB A-to-Z Generation Validator (v4.0 - Unified 12 Criteria)

통합 품질 검증 모듈:
- 12개 기준으로 통합 (기존 6개 파일 → 1개)
- Grade 시스템 (S/A/B/C/F)
- Auto-fail 조건
- validate_with_retry() 메서드
- 한국어 요약 지원
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Tuple, Callable
from enum import Enum
from pathlib import Path
import json
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL, IMAGE_MODEL


class QualityTier(Enum):
    """Quality classification tiers for generated images"""
    RELEASE_READY = "RELEASE_READY"          # S/A Grade: 즉시 납품 가능
    NEEDS_MINOR_EDIT = "NEEDS_MINOR_EDIT"    # B Grade: 소폭 보정 후 사용 가능
    REGENERATE = "REGENERATE"                # C/F Grade: 재생성 필요


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

    # AI 티 검사 결과 (선택적)
    ai_artifact_score: Optional[int] = None  # 0-100, 높을수록 AI스러움
    ai_artifact_grade: Optional[str] = None  # S/A/B/C/F
    ai_artifact_issues: List[str] = field(default_factory=list)

    # 게이트 결과 (NEW)
    gate_passed: bool = True
    gate_failed_reasons: List[str] = field(default_factory=list)
    gate_checked: bool = False  # 게이트 체크 수행 여부

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
            # AI 티 검사 결과
            "ai_artifact_score": self.ai_artifact_score,
            "ai_artifact_grade": self.ai_artifact_grade,
            "ai_artifact_issues": self.ai_artifact_issues,
            # 게이트 결과
            "gate_passed": self.gate_passed,
            "gate_failed_reasons": self.gate_failed_reasons,
            "gate_checked": self.gate_checked,
        }


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
    pass_face_identity: int = 85
    pass_expression: int = 75
    pass_outfit_accuracy: int = 80
    pass_brand_compliance: int = 75

    # Auto-fail thresholds
    auto_fail_thresholds: dict = field(default_factory=lambda: {
        "anatomy": 50,                    # 손가락 기형
        "micro_detail": 50,               # 플라스틱 피부
        "face_identity": 50,              # 다른 사람
        "expression": 50,                 # 반감은 눈/미소
        "body_type": 70,                  # 체형 불일치
        "outfit_accuracy": 50,            # 착장 누락
        "brand_compliance": 50,           # 지저분한 배경
        "environmental_integration": 50,  # 합성 느낌
        "lighting_mood": 50,              # 누런 톤
    })

    # Weights for total score calculation (총 100%)
    weights: dict = field(default_factory=lambda: {
        # A. 기본품질 (25%)
        "photorealism": 0.10,
        "anatomy": 0.08,
        "micro_detail": 0.07,
        # B. 인물보존 (25%)
        "face_identity": 0.10,
        "expression": 0.08,
        "body_type": 0.07,
        # C. 착장 (15%)
        "outfit_accuracy": 0.15,
        # D. 브랜드 (20%)
        "brand_compliance": 0.10,
        "environmental_integration": 0.05,
        "lighting_mood": 0.05,
        # E. 구도 (15%)
        "composition": 0.08,
        "pose_quality": 0.07,
    })


# Auto-fail 조건 설명 (한국어)
AUTO_FAIL_DESCRIPTIONS = {
    "anatomy": "손가락 기형 또는 해부학 오류",
    "micro_detail": "플라스틱/에어브러시 피부",
    "face_identity": "얼굴 다른 사람",
    "expression": "반감은 눈/미소/찡그림",
    "body_type": "체형 불일치",
    "outfit_accuracy": "핵심 착장 누락",
    "brand_compliance": "지저분한 배경 (간판/차량/행인)",
    "environmental_integration": "합성 느낌 배경",
    "lighting_mood": "누런 톤/골든아워",
}


# 프롬프트 보강 규칙 (재시도용)
ENHANCEMENT_RULES = {
    "photorealism": [
        "CRITICAL: Must look like REAL PHOTOGRAPH",
        "Natural skin texture with pores",
        "Realistic shadow gradients",
        "Shot on Canon EOS R5, 85mm f/1.4"
    ],
    "anatomy": [
        "CRITICAL: Perfect human anatomy",
        "Exactly 5 fingers per hand",
        "Correct body proportions",
        "Natural joint positions"
    ],
    "micro_detail": [
        "ENHANCE: Add visible skin pores (forehead high density, nose visible, cheeks scattered)",
        "Natural texture variance, subtle imperfections",
        "Hair strand detail, fabric weave texture",
        "NO airbrushed perfection"
    ],
    "face_identity": [
        "CRITICAL: Face must be IDENTICAL to reference",
        "Preserve exact eye shape, nose, jawline",
        "Match skin tone precisely",
        "100% recognizable as same person"
    ],
    "expression": [
        "EXPRESSION: Large, wide-open eyes (K-pop style)",
        "NO SMILE - absolutely forbidden",
        "Neutral or pouty lips",
        "Cold confidence / innocent chic"
    ],
    "body_type": [
        "CRITICAL: Body type must match reference exactly",
        "Same height, build, proportions",
        "No body modification"
    ],
    "outfit_accuracy": [
        "CRITICAL: ALL clothing must match exactly",
        "Preserve exact colors, logos, patterns",
        "All accessories present",
        "No color shifts allowed"
    ],
    "brand_compliance": [
        "BACKGROUND: Clean, premium, minimalist",
        "Brutalist concrete / minimal architecture / private gallery",
        "NO street clutter, signs, vehicles, pedestrians",
        "MLB 'Young & Rich' aesthetic"
    ],
    "environmental_integration": [
        "Model must appear ACTUALLY in the scene",
        "Natural ground contact shadows",
        "No composited/pasted look",
        "Seamless environment integration"
    ],
    "lighting_mood": [
        "LIGHTING: Neutral cool 5600K-6200K only",
        "ABSOLUTELY NO warm/golden/amber tones",
        "Directional soft lighting",
        "No yellow color cast"
    ],
    "composition": [
        "Editorial composition, creative framing",
        "Variety of angles (low, high, 3/4)",
        "Magazine cover quality",
        "Not just boring frontal shots"
    ],
    "pose_quality": [
        "Natural but styled pose",
        "Variety: leaning, sitting, walking, crouching",
        "Relaxed shoulders, natural hand position",
        "NO mannequin stiffness"
    ]
}


class MLBValidator:
    """Validator for MLB A-to-Z generation quality assessment (12 criteria)"""

    # Self-Critique Loop settings
    MAX_SELF_CRITIQUE_ITERATIONS = 3
    TARGET_SCORE = 90

    VALIDATION_PROMPT = '''## MLB KOREA 통합 품질 검증 (v4.0 - 13개 기준)

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

### 7. outfit_accuracy (15%)
착장이 참조와 100% 일치하는가?
- 모든 아이템 존재 여부
- 색상 정확도
- 로고/패턴 정확도
- 소재감 표현
- 90-100: 모든 아이템 완벽 일치
- 70-89: 1개 아이템 약간 차이
- 50-69: 2개 이상 불일치
- 0-49: 핵심 아이템 누락 → AUTO-FAIL

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

### 10. lighting_mood (5%)
조명이 브랜드 무드에 맞는가?
- 색온도: 5600K-6200K (neutral-cool)
- 방향성 있는 소프트 라이팅
- 0-49: 누런 톤 / 골든아워 → AUTO-FAIL

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

### 12. pose_quality (7%)
포즈가 다양하고 매력적인가?
- 기대기, 앉기, 워킹, 크라우치 등 다양
- 손/팔 자연스러운 배치
- 90-100: 프로 모델급 포즈
- 70-89: 자연스러운 포즈
- 50-69: 어색하거나 평범
- 0-49: 딱딱하고 부자연스러움

---

## RESPONSE FORMAT (JSON only)

```json
{{
  "photorealism": <0-100>,
  "anatomy": <0-100>,
  "micro_detail": <0-100>,
  "face_identity": <0-100>,
  "expression": <0-100>,
  "body_type": <0-100>,
  "outfit_accuracy": <0-100>,
  "brand_compliance": <0-100>,
  "environmental_integration": <0-100>,
  "lighting_mood": <0-100>,
  "composition": <0-100>,
  "pose_quality": <0-100>,
  "issues": ["<문제점1>", "<문제점2>"],
  "strengths": ["<장점1>", "<장점2>"],
  "summary_kr": "<한국어 1-2문장 요약>"
}}
```'''

    def __init__(
        self,
        client: genai.Client,
        thresholds: Optional[ValidationThresholds] = None
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
        shot_preset: dict = None,
        check_ai_artifacts: bool = False,
        check_gate: bool = True  # NEW: 게이트 체크 (기본 활성화)
    ) -> ValidationResult:
        """
        Run VLM validation and classify result into quality tier

        Args:
            generated_img: Generated image to validate (path or PIL Image)
            face_images: Reference face images (paths or PIL Images)
            outfit_images: Reference outfit images (paths or PIL Images)
            style_images: Reference style images (paths or PIL Images)
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

            if not gate_passed:
                # 게이트 실패 시 즉시 반환
                return ValidationResult(
                    # 모든 점수 0
                    photorealism=0, anatomy=0, micro_detail=0,
                    face_identity=0, expression=0, body_type=0,
                    outfit_accuracy=0, brand_compliance=0,
                    environmental_integration=0, lighting_mood=0,
                    composition=0, pose_quality=0,
                    total_score=0,
                    tier=QualityTier.REGENERATE,
                    grade="F",
                    passed=False,
                    auto_fail=True,
                    auto_fail_reasons=gate_failed_reasons,
                    issues=gate_failed_reasons,
                    summary_kr=f"합성티 게이트 실패: {', '.join(gate_failed_reasons)}",
                    gate_passed=False,
                    gate_failed_reasons=gate_failed_reasons,
                    gate_checked=True
                )

        # Step 1: 기존 12개 기준 채점 (게이트 통과 시에만 도달)

        # 필수 참조 이미지 검증
        if not face_images or len(face_images) == 0:
            raise ValueError("face_images is required for validation. Cannot evaluate face_identity/body_type without reference.")

        if not outfit_images or len(outfit_images) == 0:
            raise ValueError("outfit_images is required for validation. Cannot evaluate outfit_accuracy without reference.")

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
            content_parts.append(types.Part(text="\n\n[FACE REFERENCE - 얼굴/표정/체형 비교용]"))
            for face in faces[:3]:
                content_parts.append(self._pil_to_part(face))

        if outfits:
            content_parts.append(types.Part(text="\n\n[OUTFIT REFERENCE - 착장 비교용]"))
            for outfit in outfits[:5]:
                content_parts.append(self._pil_to_part(outfit))

        if styles:
            content_parts.append(types.Part(text="\n\n[MLB STYLE REFERENCE - 브랜드 톤앤매너 비교용]"))
            for style in styles[:3]:
                content_parts.append(self._pil_to_part(style))

        # Call VLM
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
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

        # Process result
        return self._process_result(result_dict, gen_img, check_ai_artifacts, check_gate)

    def _process_result(self, result_dict: dict, gen_img: Image.Image, check_ai_artifacts: bool, check_gate: bool) -> ValidationResult:
        """Process raw VLM result into ValidationResult"""
        # Calculate total score
        total_score = self._calculate_total_score(result_dict)

        # Check auto-fail conditions
        auto_fail, auto_fail_reasons = self._check_auto_fail(result_dict)

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
                    auto_fail_reasons.append(f"AI artifact score {ai_artifact_score} (F grade)")
            except Exception as e:
                print(f"[Validator] AI artifact check error: {e}")

        # Determine grade
        grade = self._determine_grade(total_score, auto_fail)

        # Determine tier
        tier = self._determine_tier(total_score, auto_fail, grade)

        # Check passed
        passed = self._check_passed(result_dict, total_score, auto_fail)

        # Extract issues and strengths
        issues = self._extract_issues(result_dict, total_score)
        strengths = self._extract_strengths(result_dict)

        # Get summary
        summary_kr = result_dict.get("summary_kr", "")

        return ValidationResult(
            # A. 기본품질
            photorealism=result_dict.get("photorealism", 0),
            anatomy=result_dict.get("anatomy", 0),
            micro_detail=result_dict.get("micro_detail", 0),
            # B. 인물보존
            face_identity=result_dict.get("face_identity", 0),
            expression=result_dict.get("expression", 0),
            body_type=result_dict.get("body_type", 0),
            # C. 착장
            outfit_accuracy=result_dict.get("outfit_accuracy", 0),
            # D. 브랜드
            brand_compliance=result_dict.get("brand_compliance", 0),
            environmental_integration=result_dict.get("environmental_integration", 0),
            lighting_mood=result_dict.get("lighting_mood", 0),
            # E. 구도
            composition=result_dict.get("composition", 0),
            pose_quality=result_dict.get("pose_quality", 0),
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
            # AI 티 검사 결과
            ai_artifact_score=ai_artifact_score,
            ai_artifact_grade=ai_artifact_grade,
            ai_artifact_issues=ai_artifact_issues,
            # 게이트 결과
            gate_passed=True,  # 여기 도달했으면 게이트 통과
            gate_failed_reasons=[],
            gate_checked=check_gate
        )

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
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))

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

### 응답 (JSON)
{
  "passed": true/false,
  "failed_reasons": ["피부 모공 부재", "로고 왜곡"]
}

엄격하게 판단하세요. 의심되면 FAIL입니다.
"""

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=gate_prompt),
                    img_part
                ])],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
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
                "failed_reasons": result.get("failed_reasons", [])
            }
        except json.JSONDecodeError as e:
            # 파싱 실패 시 FAIL 처리
            print(f"[Gate] JSON parse error: {e}")
            return {
                "passed": False,
                "failed_reasons": ["게이트 응답 파싱 실패"]
            }
        except Exception as e:
            # 기타 에러 시 FAIL 처리
            print(f"[Gate] VLM error: {e}")
            return {
                "passed": False,
                "failed_reasons": [f"게이트 체크 에러: {str(e)}"]
            }

    def _calculate_total_score(self, result: dict) -> int:
        """Calculate weighted total score"""
        weights = self.thresholds.weights
        total = 0.0

        for metric, weight in weights.items():
            score = result.get(metric, 0)
            total += score * weight

        return round(total)

    def _check_auto_fail(self, result: dict) -> Tuple[bool, List[str]]:
        """Check auto-fail conditions"""
        auto_fail = False
        reasons = []

        for criterion, threshold in self.thresholds.auto_fail_thresholds.items():
            score = result.get(criterion, 100)
            if score < threshold:
                auto_fail = True
                desc = AUTO_FAIL_DESCRIPTIONS.get(criterion, criterion)
                reasons.append(f"{desc} ({criterion}: {score})")

        return auto_fail, reasons

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

    def _determine_tier(self, total_score: int, auto_fail: bool, grade: str) -> QualityTier:
        """Determine quality tier"""
        if auto_fail or grade == "F":
            return QualityTier.REGENERATE
        elif grade in ("S", "A"):
            return QualityTier.RELEASE_READY
        elif grade == "B":
            return QualityTier.NEEDS_MINOR_EDIT
        else:  # C
            return QualityTier.REGENERATE

    def _check_passed(self, result: dict, total_score: int, auto_fail: bool) -> bool:
        """Check if validation passed"""
        if auto_fail:
            return False

        t = self.thresholds
        return (
            total_score >= t.pass_total and
            result.get("anatomy", 0) >= t.pass_anatomy and
            result.get("face_identity", 0) >= t.pass_face_identity and
            result.get("expression", 0) >= t.pass_expression and
            result.get("outfit_accuracy", 0) >= t.pass_outfit_accuracy and
            result.get("brand_compliance", 0) >= t.pass_brand_compliance
        )

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
            summary_kr=f"검증 오류: {error_msg}"
        )

    def validate_with_retry(
        self,
        generate_func: Callable,
        prompt: str,
        reference_images: dict,
        config: dict,
        max_retries: int = 3,
        output_dir: str = None
    ) -> Tuple[Optional[Image.Image], ValidationResult, List[dict]]:
        """
        Generate-Validate-Retry loop with prompt enhancement

        Args:
            generate_func: Callable that takes (prompt, refs, config) and returns Image
            prompt: Base generation prompt
            reference_images: Dict with 'face', 'outfit', 'style' image lists
            config: Generation config dict (must include 'temperature')
            max_retries: Maximum retry attempts (default: 3)
            output_dir: Optional directory to save intermediate results

        Returns:
            Tuple of (best_image, best_validation_result, history)
        """
        # 필수 참조 이미지 검증
        if not reference_images.get("face") or len(reference_images.get("face", [])) == 0:
            raise ValueError("reference_images['face'] is required for validation. Cannot evaluate face_identity/body_type without reference.")

        if not reference_images.get("outfit") or len(reference_images.get("outfit", [])) == 0:
            raise ValueError("reference_images['outfit'] is required for validation. Cannot evaluate outfit_accuracy without reference.")

        best_image = None
        best_result = None
        best_score = 0
        history = []

        current_prompt = prompt
        current_config = config.copy()
        initial_temp = current_config.get("temperature", 0.25)
        current_temp = initial_temp

        for attempt in range(max_retries + 1):
            print(f"\n{'#'*60}")
            print(f"# ATTEMPT {attempt + 1}/{max_retries + 1} | Temperature: {current_temp:.2f}")
            print(f"{'#'*60}")

            try:
                # 1. Generate image
                current_config["temperature"] = current_temp
                image = generate_func(current_prompt, reference_images, current_config)

                if image is None:
                    print(f"[Retry] No image generated in attempt {attempt + 1}")
                    history.append({
                        "attempt": attempt + 1,
                        "temperature": current_temp,
                        "error": "No image generated"
                    })
                    continue

                # Save intermediate result
                if output_dir:
                    import os
                    os.makedirs(output_dir, exist_ok=True)
                    image.save(os.path.join(output_dir, f"attempt_{attempt + 1}.png"))

                # 2. Validate
                result = self.validate(
                    generated_img=image,
                    face_images=reference_images.get("face", []),
                    outfit_images=reference_images.get("outfit", []),
                    style_images=reference_images.get("style", [])
                )

                print(f"[Retry] Score: {result.total_score}/100 | Grade: {result.grade} | {'PASS' if result.passed else 'FAIL'}")

                # Record history
                history.append({
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "total_score": result.total_score,
                    "grade": result.grade,
                    "passed": result.passed,
                    "auto_fail": result.auto_fail,
                    "issues": result.issues[:5],  # Limit for readability
                })

                # 3. Track best
                if result.total_score > best_score:
                    best_image = image
                    best_result = result
                    best_score = result.total_score
                    print(f"[Retry] New best score: {best_score}")

                # 4. Check pass condition
                if result.passed:
                    print(f"[Retry] PASSED at attempt {attempt + 1}!")
                    return image, result, history

                # 5. Enhance prompt for next attempt
                if attempt < max_retries:
                    enhancement = self._build_enhancement_from_result(result, attempt)
                    if enhancement:
                        current_prompt = prompt + "\n\n" + enhancement
                        print(f"[Retry] Added enhancement for {len(result.issues)} issues")

                    # Reduce temperature slightly
                    current_temp = max(0.15, current_temp - 0.03)

            except Exception as e:
                print(f"[Retry] Error in attempt {attempt + 1}: {e}")
                history.append({
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": str(e)
                })
                continue

        print(f"\n[Retry] Max retries reached. Best score: {best_score}")
        return best_image, best_result, history

    def _build_enhancement_from_result(self, result: ValidationResult, retry: int) -> str:
        """Build prompt enhancements based on validation result"""
        # Find failed criteria
        failed_criteria = []

        criteria_scores = {
            "photorealism": (result.photorealism, 85),
            "anatomy": (result.anatomy, 80),
            "micro_detail": (result.micro_detail, 75),
            "face_identity": (result.face_identity, 85),
            "expression": (result.expression, 75),
            "body_type": (result.body_type, 85),
            "outfit_accuracy": (result.outfit_accuracy, 80),
            "brand_compliance": (result.brand_compliance, 75),
            "environmental_integration": (result.environmental_integration, 75),
            "lighting_mood": (result.lighting_mood, 75),
            "composition": (result.composition, 80),
            "pose_quality": (result.pose_quality, 75),
        }

        for criterion, (score, threshold) in criteria_scores.items():
            if score < threshold:
                failed_criteria.append(criterion)

        if not failed_criteria:
            return ""

        # Build enhancement text
        enhancements = []

        # Priority order for enhancements (most critical first)
        priority_order = [
            "face_identity", "expression", "anatomy", "outfit_accuracy",
            "brand_compliance", "lighting_mood", "micro_detail",
            "environmental_integration", "body_type", "photorealism",
            "composition", "pose_quality"
        ]

        for criterion in priority_order:
            if criterion in failed_criteria and criterion in ENHANCEMENT_RULES:
                enhancements.extend(ENHANCEMENT_RULES[criterion])

        # Add retry header
        enhancement_block = "\n".join([f"- {e}" for e in enhancements[:12]])  # Limit to 12 items

        return f"""=== RETRY ENHANCEMENT (Attempt #{retry + 2}) ===
Previous score: {result.total_score}/100 | Grade: {result.grade}
Failed on: {', '.join(failed_criteria[:6])}

MUST FIX:
{enhancement_block}
================================================"""

    def generate_report(
        self,
        results: List[ValidationResult],
        shot_ids: Optional[List[str]] = None
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
        tier_counts = {
            "RELEASE_READY": 0,
            "NEEDS_MINOR_EDIT": 0,
            "REGENERATE": 0
        }

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
                "auto_fail_count": auto_fail_count
            },
            "grades": grade_counts,
            "tiers": tier_counts,
            "average_scores": avg_scores,
            "details": []
        }

        # Add per-image breakdown
        for i, result in enumerate(results):
            shot_id = shot_ids[i] if shot_ids and i < len(shot_ids) else f"Image_{i+1}"
            report["details"].append({
                "shot_id": shot_id,
                "total_score": result.total_score,
                "grade": result.grade,
                "tier": result.tier.value,
                "passed": result.passed,
                "auto_fail": result.auto_fail,
                "auto_fail_reasons": result.auto_fail_reasons,
                "issues": result.issues[:3],  # Top 3 issues
                "summary_kr": result.summary_kr
            })

        return report

    def print_result(self, result: ValidationResult, filename: str = "") -> None:
        """Pretty-print single validation result"""
        print(f"\n{'='*70}")
        if filename:
            print(f"File: {filename}")
        print(f"{'='*70}")

        # Category breakdown
        categories = {
            "A. 기본품질 (25%)": [
                ("photorealism", result.photorealism, 85),
                ("anatomy", result.anatomy, 80),
                ("micro_detail", result.micro_detail, 75),
            ],
            "B. 인물보존 (25%)": [
                ("face_identity", result.face_identity, 85),
                ("expression", result.expression, 75),
                ("body_type", result.body_type, 85),
            ],
            "C. 착장 (15%)": [
                ("outfit_accuracy", result.outfit_accuracy, 80),
            ],
            "D. 브랜드 (20%)": [
                ("brand_compliance", result.brand_compliance, 75),
                ("environmental_integration", result.environmental_integration, 75),
                ("lighting_mood", result.lighting_mood, 75),
            ],
            "E. 구도 (15%)": [
                ("composition", result.composition, 80),
                ("pose_quality", result.pose_quality, 75),
            ],
        }

        for cat_name, criteria in categories.items():
            print(f"\n{cat_name}:")
            for criterion, score, threshold in criteria:
                status = "[O]" if score >= threshold else "[X]"
                print(f"  {criterion:<28} {score:>3}  {status}")

        # Total
        print(f"\n{'='*70}")
        print(f"TOTAL: {result.total_score}  |  GRADE: {result.grade}  |  TIER: {result.tier.value}  |  {'PASS' if result.passed else 'FAIL'}")
        print(f"{'='*70}")

        # Auto-fail
        if result.auto_fail:
            print(f"\n[AUTO-FAIL] {', '.join(result.auto_fail_reasons)}")

        # Issues
        if result.issues:
            print(f"\nIssues ({len(result.issues)}):")
            for issue in result.issues[:5]:
                print(f"  - {issue}")

        # Strengths
        if result.strengths:
            print(f"\nStrengths:")
            for strength in result.strengths[:3]:
                print(f"  + {strength}")

        # Summary
        if result.summary_kr:
            print(f"\n요약: {result.summary_kr}")

    def print_report(self, report: dict) -> None:
        """Pretty-print batch validation report"""
        print("\n" + "="*70)
        print("MLB UNIFIED VALIDATION REPORT (13 Criteria)")
        print("="*70)

        summary = report["summary"]
        print(f"\n[SUMMARY]")
        print(f"  Total Images: {summary['total_images']}")
        print(f"  Passed: {summary['passed']} ({summary['pass_rate']}%)")
        print(f"  Usable Rate: {summary['usable_rate']}%")
        print(f"  Auto-Fail: {summary['auto_fail_count']}")

        grades = report["grades"]
        print(f"\n[GRADE DISTRIBUTION]")
        print(f"  S: {grades['S']} | A: {grades['A']} | B: {grades['B']} | C: {grades['C']} | F: {grades['F']}")

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

        print("\n" + "="*70)
        print("| {:^40} | {:^5} | {:^5} | {:^6} |".format("Shot ID", "Score", "Grade", "Status"))
        print("|" + "-"*42 + "|" + "-"*7 + "|" + "-"*7 + "|" + "-"*8 + "|")

        for detail in report["details"]:
            status = "PASS" if detail["passed"] else "FAIL"
            print("| {:<40} | {:>5} | {:^5} | {:^6} |".format(
                detail["shot_id"][:40],
                detail["total_score"],
                detail["grade"],
                status
            ))

        print("="*70)
