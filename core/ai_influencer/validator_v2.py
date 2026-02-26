"""
AI 인플루언서 검증기 v2.0

개선 사항:
1. 포즈 필드별 비교 (왼팔, 오른팔, 왼손, 오른손, 왼다리, 오른다리, 힙)
2. 표정 필드별 비교 (눈, 입, 시선)
3. 포즈-배경 호환성 검증 통합
4. step-by-step 강제 비교 프롬프트
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL
from .character import Character
from .pose_analyzer import PoseAnalysisResult, PoseAnalyzer
from .background_analyzer import BackgroundAnalysisResult, BackgroundAnalyzer
from .compatibility import CompatibilityChecker, CompatibilityResult


@dataclass
class ValidationResultV2:
    """검증 결과 v2"""

    total_score: int
    passed: bool
    criteria: Dict[str, Dict[str, Any]]
    issues: List[str]
    grade: str

    # v2 추가
    pose_comparison: Dict[str, Any] = None  # 포즈 필드별 비교 결과
    expression_comparison: Dict[str, Any] = None  # 표정 필드별 비교 결과
    compatibility_result: CompatibilityResult = None  # 호환성 결과

    def format_korean(self) -> str:
        """한국어 검수 결과 표 포맷"""
        lines = []
        lines.append("## 검수 결과 (v2)\n")
        lines.append("| 항목 | 점수 | 기준 | 통과 |")
        lines.append("|------|------|------|------|")

        for name, data in self.criteria.items():
            score = data.get("score", 0)
            threshold = data.get("threshold", 0)
            passed_mark = "O" if data.get("passed", False) else "X"
            lines.append(f"| {name} | {score} | >={threshold} | {passed_mark} |")

        lines.append("")
        lines.append(
            f"**총점**: {self.total_score}/100 | **등급**: {self.grade} | **판정**: {'통과' if self.passed else '재생성 필요'}"
        )

        if self.issues:
            lines.append("\n### 이슈 사항")
            for issue in self.issues:
                lines.append(f"- {issue}")

        # 포즈 비교 상세
        if self.pose_comparison:
            lines.append("\n### 포즈 필드별 비교")
            for field, data in self.pose_comparison.items():
                ref = data.get("ref", "")
                gen = data.get("gen", "")
                match = "O" if data.get("match", False) else "X"
                lines.append(f"- {field}: REF[{ref}] vs GEN[{gen}] -> {match}")

        # 표정 비교 상세
        if self.expression_comparison:
            lines.append("\n### 표정 필드별 비교")
            for field, data in self.expression_comparison.items():
                ref = data.get("ref", "")
                gen = data.get("gen", "")
                match = "O" if data.get("match", False) else "X"
                lines.append(f"- {field}: REF[{ref}] vs GEN[{gen}] -> {match}")

        return "\n".join(lines)


# 검증 프롬프트 v2 - step-by-step 강제 비교
VALIDATION_PROMPT_V2 = """당신은 AI 인플루언서 이미지 품질 검수 전문가입니다.

## 검수 기준 (7개 항목)

### 1. face_identity (얼굴 동일성) - 35%
[STEP 1] FACE REFERENCE 분석:
- 얼굴형 = ?
- 눈 모양/크기 = ?
- 코 형태 = ?
- 입술 형태 = ?
- 피부톤 = ?

[STEP 2] GENERATED IMAGE 얼굴 분석:
- 얼굴형 = ?
- 눈 모양/크기 = ?
- 코 형태 = ?
- 입술 형태 = ?
- 피부톤 = ?

[STEP 3] 비교 및 감점:
- 얼굴형: 같음(0) / 다름(-15)
- 눈: 같음(0) / 다름(-15)
- 코: 같음(0) / 다름(-10)
- 입술: 같음(0) / 다름(-10)
- 피부톤: 같음(0) / 다름(-10)
- 완전히 다른 사람: -60

최종 점수 = 100 - 합계 감점
reason 필수 형식: "REF:계란형+큰눈+높은코, GEN:계란형+큰눈+높은코, 감점:0"

### 2. pose_accuracy (포즈 정확도) - 20% ★★★ 신규 강화 ★★★
[POSE REFERENCE]가 있으면 반드시 필드별로 비교!

[STEP 1] POSE REFERENCE 분석 (각 필드별):
- stance = ? (stand/sit/walk/lean_wall/lean/kneel)
- 왼팔 = ?
- 오른팔 = ?
- 왼손 = ?
- 오른손 = ?
- 왼다리 = ?
- 오른다리 = ?
- 힙(무게중심) = ?
- 프레이밍 = ? (FS/MFS/MS/MCU/CU)

[STEP 2] GENERATED IMAGE 포즈 분석 (각 필드별):
- stance = ?
- 왼팔 = ?
- 오른팔 = ?
- 왼손 = ?
- 오른손 = ?
- 왼다리 = ?
- 오른다리 = ?
- 힙 = ?
- 프레이밍 = ?

[STEP 3] 필드별 비교 및 감점:
- stance 다름: -20
- 왼팔 다름: -10
- 오른팔 다름: -10
- 왼손 다름: -8
- 오른손 다름: -8
- 왼다리 다름: -10
- 오른다리 다름: -10
- 힙/무게중심 다름: -8
- 프레이밍 다름: -15

최종 점수 = 100 - 합계 감점 (최소 0)
reason 필수 형식: "stance:같음(0), 왼팔:다름(-10), 오른팔:같음(0), ... 합계:-20"

pose_field_comparison에 각 필드별 REF vs GEN 결과를 기록하세요.

### 3. expression_accuracy (표정 정확도) - 10% ★★★ 신규 ★★★
[EXPRESSION REFERENCE]가 있으면 반드시 비교!

[STEP 1] EXPRESSION REFERENCE 분석:
- 베이스 표정 = ? (cool/natural/dreamy/playful)
- 눈 상태 = ? (윙크/크게뜬눈/반감은눈 등)
- 입 상태 = ? (닫힘/살짝벌림/미소 등)
- 시선 = ? (정면/측면/아래 등)

[STEP 2] GENERATED IMAGE 표정 분석:
- 베이스 표정 = ?
- 눈 상태 = ?
- 입 상태 = ?
- 시선 = ?

[STEP 3] 비교 및 감점:
- 베이스 표정 다름: -25
- 눈 상태 다름: -25 (윙크 요청했는데 안함 = -25)
- 입 상태 다름: -15
- 시선 다름: -15

최종 점수 = 100 - 합계 감점
reason 필수 형식: "REF:시크+윙크+닫힘+정면, GEN:시크+크게뜬눈+닫힘+정면, 눈상태다름:-25"

expression_field_comparison에 각 필드별 REF vs GEN 결과를 기록하세요.

### 4. physical_plausibility (물리적 타당성) - 10% ★★★ 신규 ★★★
포즈와 배경의 물리적 호환성을 검증합니다.

- 횡단보도에서 앉기: -40 (비논리적)
- 벽 없는 곳에서 벽에 기대기: -30
- 좌석 없는 곳에서 앉기: -30
- 손가락 6개 이상 / 기형: -40
- 관절 각도 부자연스러움: -20
- 접지감 부족: -15

reason 필수 형식: "배경:횡단보도, 포즈:앉기, 물리적불가:-40"

### 5. realism (사실성) - 10%
- AI 특유 플라스틱 피부: -30
- 부자연스러운 조명: -15
- 비현실적 배경 합성: -15

### 6. outfit_fit (착장 적합성) - 10%
- 착장 누락/불일치: -30
- 옷 주름/질감 부자연스러움: -15

### 7. brand_tone (브랜드 톤) - 5%
- 누런 톤 (golden/amber/warm cast): -40
- 과도한 필터/보정: -15

## Auto-Fail 조건
다음 중 하나라도 해당하면 total_score = 0:
- 완전히 다른 사람 얼굴
- 손가락 6개 이상
- 누런 톤 (golden hour / warm amber)
- 횡단보도에서 앉기 (물리적 불가)

## 출력 형식 (JSON)
```json
{
    "face_identity": {"score": 0-100, "reason": "REF:~, GEN:~, 감점:~"},
    "pose_accuracy": {
        "score": 0-100,
        "reason": "stance:같음(0), 왼팔:다름(-10)...",
        "pose_field_comparison": {
            "stance": {"ref": "sit", "gen": "sit", "match": true},
            "left_arm": {"ref": "무릎에 올림", "gen": "무릎에 올림", "match": true},
            "right_arm": {"ref": "~", "gen": "~", "match": true/false},
            "left_hand": {"ref": "~", "gen": "~", "match": true/false},
            "right_hand": {"ref": "~", "gen": "~", "match": true/false},
            "left_leg": {"ref": "~", "gen": "~", "match": true/false},
            "right_leg": {"ref": "~", "gen": "~", "match": true/false},
            "hip": {"ref": "~", "gen": "~", "match": true/false},
            "framing": {"ref": "FS", "gen": "FS", "match": true}
        }
    },
    "expression_accuracy": {
        "score": 0-100,
        "reason": "REF:시크+윙크, GEN:시크+크게뜬눈, 눈다름:-25",
        "expression_field_comparison": {
            "base": {"ref": "cool", "gen": "cool", "match": true},
            "eyes": {"ref": "윙크", "gen": "크게뜬눈", "match": false},
            "mouth": {"ref": "닫힘", "gen": "닫힘", "match": true},
            "gaze": {"ref": "정면", "gen": "정면", "match": true}
        }
    },
    "physical_plausibility": {"score": 0-100, "reason": ""},
    "realism": {"score": 0-100, "reason": ""},
    "outfit_fit": {"score": 0-100, "reason": ""},
    "brand_tone": {"score": 0-100, "reason": ""},
    "auto_fail": {"triggered": false, "reason": ""},
    "issues": []
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class AIInfluencerValidatorV2:
    """AI 인플루언서 이미지 검증기 v2"""

    # 가중치 (v2: 포즈/표정/물리적타당성 추가)
    WEIGHTS = {
        "face_identity": 0.35,
        "pose_accuracy": 0.20,  # 신규 강화
        "expression_accuracy": 0.10,  # 신규
        "physical_plausibility": 0.10,  # 신규
        "realism": 0.10,
        "outfit_fit": 0.10,
        "brand_tone": 0.05,
    }

    # 통과 기준
    THRESHOLDS = {
        "face_identity": 70,
        "pose_accuracy": 60,  # 포즈 정확도
        "expression_accuracy": 50,  # 표정 정확도
        "physical_plausibility": 70,  # 물리적 타당성 필수!
        "realism": 60,
        "outfit_fit": 50,
        "brand_tone": 60,
    }

    PASS_SCORE = 70  # 총점 70점 이상 통과

    def __init__(self, api_key: Optional[str] = None):
        """검증기 초기화"""
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)
        self.api_key = api_key
        self.pose_analyzer = PoseAnalyzer(api_key=api_key)
        self.background_analyzer = BackgroundAnalyzer(api_key=api_key)
        self.compatibility_checker = CompatibilityChecker()

    def validate(
        self,
        generated_img: Image.Image,
        character: Character,
        pose_reference: Optional[Union[str, Path, Image.Image]] = None,
        expression_reference: Optional[Union[str, Path, Image.Image]] = None,
        background_reference: Optional[Union[str, Path, Image.Image]] = None,
        outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    ) -> ValidationResultV2:
        """
        생성된 이미지 검증 (v2)

        Args:
            generated_img: 생성된 이미지
            character: 캐릭터 객체
            pose_reference: 포즈 레퍼런스 이미지
            expression_reference: 표정 레퍼런스 이미지
            background_reference: 배경 레퍼런스 이미지
            outfit_images: 착장 참조 이미지

        Returns:
            ValidationResultV2: 검증 결과
        """
        # 1. 사전 분석 (포즈-배경 호환성)
        compatibility_result = None
        if pose_reference and background_reference:
            try:
                pose_analysis = self.pose_analyzer.analyze(pose_reference)
                bg_analysis = self.background_analyzer.analyze(background_reference)
                compatibility_result = self.compatibility_checker.check(
                    pose_analysis, bg_analysis
                )
            except Exception as e:
                print(f"[ValidatorV2] 호환성 분석 실패: {e}")

        # 2. API 파트 구성
        parts = [types.Part(text=VALIDATION_PROMPT_V2)]

        # 얼굴 참조 이미지
        face_images = character.face_images
        for i, face_path in enumerate(face_images[:3]):
            img = Image.open(face_path).convert("RGB")
            parts.append(types.Part(text=f"[FACE REFERENCE {i+1}]:"))
            parts.append(self._pil_to_part(img))

        # 포즈 참조 이미지
        if pose_reference:
            if isinstance(pose_reference, (str, Path)):
                pose_img = Image.open(pose_reference).convert("RGB")
            else:
                pose_img = pose_reference.convert("RGB")
            parts.append(types.Part(text="[POSE REFERENCE]:"))
            parts.append(self._pil_to_part(pose_img))

        # 표정 참조 이미지
        if expression_reference:
            if isinstance(expression_reference, (str, Path)):
                expr_img = Image.open(expression_reference).convert("RGB")
            else:
                expr_img = expression_reference.convert("RGB")
            parts.append(types.Part(text="[EXPRESSION REFERENCE]:"))
            parts.append(self._pil_to_part(expr_img))

        # 배경 참조 이미지
        if background_reference:
            if isinstance(background_reference, (str, Path)):
                bg_img = Image.open(background_reference).convert("RGB")
            else:
                bg_img = background_reference.convert("RGB")
            parts.append(types.Part(text="[BACKGROUND REFERENCE]:"))
            parts.append(self._pil_to_part(bg_img))

        # 착장 참조 이미지
        if outfit_images:
            for i, outfit_input in enumerate(outfit_images[:2]):
                if isinstance(outfit_input, (str, Path)):
                    outfit_img = Image.open(outfit_input).convert("RGB")
                else:
                    outfit_img = outfit_input.convert("RGB")
                parts.append(types.Part(text=f"[OUTFIT REFERENCE {i+1}]:"))
                parts.append(self._pil_to_part(outfit_img))

        # 생성된 이미지
        parts.append(types.Part(text="[GENERATED IMAGE]:"))
        parts.append(self._pil_to_part(generated_img))

        # 3. API 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_json = json.loads(result_text)

        except Exception as e:
            print(f"[ValidatorV2] API 호출 실패: {e}")
            return ValidationResultV2(
                total_score=0,
                passed=False,
                criteria={
                    k: {"score": 0, "threshold": v, "passed": False}
                    for k, v in self.THRESHOLDS.items()
                },
                issues=[f"검증 API 호출 실패: {e}"],
                grade="F",
            )

        # 4. 결과 처리
        return self._process_result(result_json, compatibility_result)

    def _process_result(
        self,
        result_json: Dict,
        compatibility_result: Optional[CompatibilityResult] = None,
    ) -> ValidationResultV2:
        """검증 결과 처리"""
        criteria = {}
        issues = []
        weighted_sum = 0

        # Auto-fail 체크
        auto_fail = result_json.get("auto_fail", {})
        if auto_fail.get("triggered", False):
            return ValidationResultV2(
                total_score=0,
                passed=False,
                criteria={
                    k: {"score": 0, "threshold": v, "passed": False}
                    for k, v in self.THRESHOLDS.items()
                },
                issues=[f"Auto-Fail: {auto_fail.get('reason', '알 수 없음')}"],
                grade="F",
            )

        # 호환성 결과를 physical_plausibility에 반영
        if compatibility_result and not compatibility_result.is_compatible():
            # 호환성 점수를 반영
            phys_score = result_json.get("physical_plausibility", {}).get("score", 100)
            phys_score = min(phys_score, compatibility_result.score)
            result_json.setdefault("physical_plausibility", {})["score"] = phys_score

            # 이슈 추가
            for issue in compatibility_result.issues:
                issues.append(f"[호환성] {issue.description}")

        # 각 기준별 점수 계산
        for criterion, weight in self.WEIGHTS.items():
            data = result_json.get(criterion, {})
            score = data.get("score", 0)
            reason = data.get("reason", "")
            threshold = self.THRESHOLDS[criterion]
            passed = score >= threshold

            criteria[criterion] = {
                "score": score,
                "threshold": threshold,
                "passed": passed,
                "reason": reason,
            }

            weighted_sum += score * weight

            if not passed:
                issues.append(f"{criterion}: {score}점 (기준 {threshold}점 미달)")

        # 이슈 목록 추가
        if result_json.get("issues"):
            issues.extend(result_json["issues"])

        # 총점 계산
        total_score = int(weighted_sum)

        # 등급 결정
        if total_score >= 90:
            grade = "S"
        elif total_score >= 80:
            grade = "A"
        elif total_score >= 70:
            grade = "B"
        elif total_score >= 60:
            grade = "C"
        else:
            grade = "F"

        # 통과 여부
        face_passed = criteria.get("face_identity", {}).get("passed", False)
        phys_passed = criteria.get("physical_plausibility", {}).get("passed", True)
        passed = total_score >= self.PASS_SCORE and face_passed and phys_passed

        # 포즈/표정 필드별 비교 결과 추출
        pose_comparison = result_json.get("pose_accuracy", {}).get(
            "pose_field_comparison", None
        )
        expression_comparison = result_json.get("expression_accuracy", {}).get(
            "expression_field_comparison", None
        )

        return ValidationResultV2(
            total_score=total_score,
            passed=passed,
            criteria=criteria,
            issues=issues,
            grade=grade,
            pose_comparison=pose_comparison,
            expression_comparison=expression_comparison,
            compatibility_result=compatibility_result,
        )

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


def validate_ai_influencer_v2(
    generated_img: Image.Image,
    character: Character,
    pose_reference: Optional[Union[str, Path, Image.Image]] = None,
    expression_reference: Optional[Union[str, Path, Image.Image]] = None,
    background_reference: Optional[Union[str, Path, Image.Image]] = None,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    api_key: Optional[str] = None,
) -> ValidationResultV2:
    """
    AI 인플루언서 이미지 검증 v2 (편의 함수)
    """
    validator = AIInfluencerValidatorV2(api_key=api_key)
    return validator.validate(
        generated_img,
        character,
        pose_reference,
        expression_reference,
        background_reference,
        outfit_images,
    )
