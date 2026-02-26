"""
AI 인플루언서 검증기

얼굴 동일성 40% 비중으로 강화 검증
- 셀카 스킬(25%)보다 높은 비중
- 동일 캐릭터 유지가 핵심
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


@dataclass
class ValidationResult:
    """검증 결과"""

    total_score: int
    passed: bool
    criteria: Dict[str, Dict[str, Any]]
    issues: List[str]
    grade: str

    def format_korean(self) -> str:
        """한국어 검수 결과 표 포맷"""
        lines = []
        lines.append("## 검수 결과\n")
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

        return "\n".join(lines)


# 검증 프롬프트 템플릿
VALIDATION_PROMPT = """당신은 AI 인플루언서 이미지 품질 검수 전문가입니다.

## 검수 기준 (5개 항목)

### 1. face_identity (얼굴 동일성) - 40%
[FACE REFERENCE]와 생성 이미지의 얼굴을 비교합니다.

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

### 2. realism (사실성) - 25%
실제 사진처럼 보이는가?
- AI 특유 플라스틱 피부: -30
- 부자연스러운 조명: -15
- 비현실적 배경 합성: -15
- 신체 비율 이상: -20

### 3. outfit_fit (착장 적합성) - 15%
착장이 자연스럽게 입혀졌는가?
- 착장 누락/불일치: -30
- 옷 주름/질감 부자연스러움: -15
- 사이즈 불일치: -10

### 4. pose_natural (포즈 자연스러움) - 10%
- 손가락 이상 (6개+, 기형): -40
- 관절 각도 부자연스러움: -20
- 접지감 부족: -15

### 5. brand_tone (브랜드 톤) - 10%
- 누런 톤 (golden/amber/warm cast): -40
- 과도한 필터/보정: -15
- 브랜드 톤 불일치: -15

## Auto-Fail 조건
다음 중 하나라도 해당하면 total_score = 0:
- 완전히 다른 사람 얼굴
- 손가락 6개 이상
- 누런 톤 (golden hour / warm amber)
- 의도하지 않은 텍스트/워터마크

## 출력 형식 (JSON)
```json
{
    "face_identity": {"score": 0-100, "reason": "REF:~, GEN:~, 감점:~"},
    "realism": {"score": 0-100, "reason": ""},
    "outfit_fit": {"score": 0-100, "reason": ""},
    "pose_natural": {"score": 0-100, "reason": ""},
    "brand_tone": {"score": 0-100, "reason": ""},
    "auto_fail": {"triggered": false, "reason": ""},
    "issues": []
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class AIInfluencerValidator:
    """AI 인플루언서 이미지 검증기"""

    # 가중치 (face_identity 40%로 강화)
    WEIGHTS = {
        "face_identity": 0.40,
        "realism": 0.25,
        "outfit_fit": 0.15,
        "pose_natural": 0.10,
        "brand_tone": 0.10,
    }

    # 통과 기준
    THRESHOLDS = {
        "face_identity": 70,  # 얼굴 동일성 필수 70점 이상
        "realism": 60,
        "outfit_fit": 50,
        "pose_natural": 50,
        "brand_tone": 60,
    }

    PASS_SCORE = 75  # 총점 75점 이상 통과

    def __init__(self, api_key: Optional[str] = None):
        """
        검증기 초기화

        Args:
            api_key: Gemini API 키 (None이면 자동 로드)
        """
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)

    def validate(
        self,
        generated_img: Image.Image,
        character: Character,
        outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    ) -> ValidationResult:
        """
        생성된 이미지 검증

        Args:
            generated_img: 생성된 이미지
            character: 캐릭터 객체 (얼굴 참조 이미지 포함)
            outfit_images: 착장 참조 이미지 (선택)

        Returns:
            ValidationResult: 검증 결과
        """
        # API 파트 구성
        parts = [types.Part(text=VALIDATION_PROMPT)]

        # 얼굴 참조 이미지 전송
        face_images = character.face_images
        for i, face_path in enumerate(face_images[:3]):  # 최대 3장
            img = Image.open(face_path).convert("RGB")
            parts.append(types.Part(text=f"[FACE REFERENCE {i+1}]:"))
            parts.append(self._pil_to_part(img))

        # 착장 참조 이미지 전송 (있으면)
        if outfit_images:
            for i, outfit_input in enumerate(outfit_images[:2]):  # 최대 2장
                if isinstance(outfit_input, (str, Path)):
                    outfit_img = Image.open(outfit_input).convert("RGB")
                else:
                    outfit_img = outfit_input.convert("RGB")
                parts.append(types.Part(text=f"[OUTFIT REFERENCE {i+1}]:"))
                parts.append(self._pil_to_part(outfit_img))

        # 생성된 이미지 전송
        parts.append(types.Part(text="[GENERATED IMAGE]:"))
        parts.append(self._pil_to_part(generated_img))

        # API 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            # JSON 파싱
            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_json = json.loads(result_text)

        except Exception as e:
            print(f"[Validator] API 호출 실패: {e}")
            # 기본 결과 반환
            return ValidationResult(
                total_score=0,
                passed=False,
                criteria={
                    k: {"score": 0, "threshold": v, "passed": False}
                    for k, v in self.THRESHOLDS.items()
                },
                issues=[f"검증 API 호출 실패: {e}"],
                grade="F",
            )

        # 결과 처리
        return self._process_result(result_json)

    def _process_result(self, result_json: Dict) -> ValidationResult:
        """검증 결과 처리"""
        criteria = {}
        issues = []
        weighted_sum = 0

        # Auto-fail 체크
        auto_fail = result_json.get("auto_fail", {})
        if auto_fail.get("triggered", False):
            return ValidationResult(
                total_score=0,
                passed=False,
                criteria={
                    k: {"score": 0, "threshold": v, "passed": False}
                    for k, v in self.THRESHOLDS.items()
                },
                issues=[f"Auto-Fail: {auto_fail.get('reason', '알 수 없음')}"],
                grade="F",
            )

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

        # 통과 여부 (총점 + face_identity 필수 통과)
        face_passed = criteria.get("face_identity", {}).get("passed", False)
        passed = total_score >= self.PASS_SCORE and face_passed

        return ValidationResult(
            total_score=total_score,
            passed=passed,
            criteria=criteria,
            issues=issues,
            grade=grade,
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


def validate_ai_influencer(
    generated_img: Image.Image,
    character: Character,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    api_key: Optional[str] = None,
) -> ValidationResult:
    """
    AI 인플루언서 이미지 검증 (편의 함수)

    Args:
        generated_img: 생성된 이미지
        character: 캐릭터 객체
        outfit_images: 착장 참조 이미지 (선택)
        api_key: Gemini API 키

    Returns:
        ValidationResult: 검증 결과
    """
    validator = AIInfluencerValidator(api_key=api_key)
    return validator.validate(generated_img, character, outfit_images)
