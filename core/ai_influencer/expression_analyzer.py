"""
VLM 표정 분석기

표정 레퍼런스 이미지에서 핵심 표정 정보를 추출하여
프롬프트 스키마 형식으로 반환합니다.

분석 항목 (v2.0 - 한글 통일):
- 베이스: 표정 무드
- 눈: 눈 형태/분위기
- 시선: 시선 방향
- 입: 입 상태 + 표정
- 얼굴각도: 얼굴 방향
- 턱: 턱 위치
- is_wink: 윙크 여부
- wink_eye: 어느 눈 윙크
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class ExpressionAnalysisResult:
    """표정 분석 결과"""

    베이스: str  # cool, natural, dreamy, playful, cute
    눈: str  # 큰 눈, 자연스러운 눈 등 (형태+분위기)
    시선: str  # 정면, 왼쪽, 오른쪽, 아래, 3/4 측면
    입: str  # 다문, 살짝 벌림(3mm), 살짝 미소, 살짝 삐죽
    얼굴각도: str  # 정면, 3/4 오른쪽, 3/4 왼쪽, 측면
    턱: str  # 자연스러운, 들어올린, 내린
    is_wink: bool
    wink_eye: str  # left, right, ""

    def to_preset_format(self) -> Dict[str, Any]:
        """expression_presets.json 형식으로 변환"""
        result = {
            "베이스": self.베이스,
            "눈": self.눈,
            "시선": self.시선,
            "입": self.입,
            "얼굴각도": self.얼굴각도,
            "턱": self.턱,
            "is_wink": self.is_wink,
        }
        if self.is_wink:
            result["wink_eye"] = self.wink_eye
        return result

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트로 변환 (한글 문장형)"""
        lines = []
        lines.append(f"- 베이스: {self.베이스}")
        lines.append(f"- 눈: {self.눈}")
        lines.append(f"- 시선: {self.시선}")

        if self.is_wink:
            wink_side = "왼쪽" if self.wink_eye == "left" else "오른쪽"
            lines.append(f"- 윙크: {wink_side} 눈")

        lines.append(f"- 입: {self.입}")
        lines.append(f"- 얼굴각도: {self.얼굴각도}")
        lines.append(f"- 턱: {self.턱}")

        return "\n".join(lines)


# VLM 표정 분석 프롬프트
EXPRESSION_ANALYSIS_PROMPT = """당신은 패션 화보 표정 분석 전문가입니다.

## 작업
이미지에서 모델의 표정을 분석하여 아래 JSON 형식으로 출력하세요.

## 분석 항목

### 1. 베이스 (표정 무드)
다음 중 선택:
- "cool": 쿨하고 도도함
- "natural": 자연스럽고 편안함
- "dreamy": 몽환적, 나른함
- "playful": 장난스럽고 발랄함
- "cute": 귀엽고 사랑스러움

### 2. 눈 (눈 형태 + 분위기)
눈의 생김새와 분위기를 간결하게 서술.
예: "큰 눈, 무심한 쿨 눈빛", "자연스러운 눈, 게으른 듯한 눈빛", "한쪽 윙크, 장난스러운 눈빛"

### 3. 시선 (시선 방향)
양쪽 눈이 어디를 보고 있는지:
- "정면", "왼쪽", "오른쪽", "아래", "3/4 측면"

### 4. 입 (입 상태 + 표정)
입의 벌림 정도 또는 표정:
- "다문": 완전히 다문 상태
- "살짝 벌림": 벌림 정도 불명확
- "살짝 벌림(2mm)": 거의 안 벌림
- "살짝 벌림(3mm)": 약간 벌림
- "살짝 벌림(5mm)": 숨쉬는 정도
- "살짝 미소": 부드러운 미소
- "살짝 삐죽": 삐죽 내민 입술
- "벌림": 크게 벌림

### 5. 얼굴각도 (얼굴 방향)
- "정면", "3/4 오른쪽", "3/4 왼쪽", "측면"

### 6. 턱 (턱 위치)
- "자연스러운": 평소
- "들어올린": 턱을 올림
- "내린": 턱을 당김

### 7. is_wink (윙크 여부)
한쪽 눈만 감거나 거의 감은 상태인지:
- true / false

### 8. wink_eye (윙크한 눈)
is_wink가 true일 때만:
- "left": 왼쪽 눈 윙크 (이미지 기준)
- "right": 오른쪽 눈 윙크 (이미지 기준)
- "": is_wink가 false일 때

## 출력 형식 (JSON만 출력!)
```json
{
    "베이스": "cool",
    "눈": "큰 눈, 무심한 쿨 눈빛",
    "시선": "정면",
    "입": "살짝 벌림(3mm)",
    "얼굴각도": "3/4 왼쪽",
    "턱": "자연스러운",
    "is_wink": false,
    "wink_eye": ""
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class ExpressionAnalyzer:
    """VLM 표정 분석기"""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)

    def analyze(
        self,
        expression_image: Union[str, Path, Image.Image],
    ) -> ExpressionAnalysisResult:
        """
        표정 이미지 분석

        Args:
            expression_image: 표정 레퍼런스 이미지

        Returns:
            ExpressionAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(expression_image, (str, Path)):
            img = Image.open(expression_image).convert("RGB")
        else:
            img = expression_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=EXPRESSION_ANALYSIS_PROMPT),
            types.Part(text="[EXPRESSION IMAGE]:"),
            self._pil_to_part(img),
        ]

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
            print(f"[ExpressionAnalyzer] API error: {e}")
            return ExpressionAnalysisResult(
                베이스="natural",
                눈="자연스러운 눈",
                시선="정면",
                입="다문",
                얼굴각도="정면",
                턱="자연스러운",
                is_wink=False,
                wink_eye="",
            )

        return ExpressionAnalysisResult(
            베이스=result_json.get("베이스", "natural"),
            눈=result_json.get("눈", "자연스러운 눈"),
            시선=result_json.get("시선", "정면"),
            입=result_json.get("입", "다문"),
            얼굴각도=result_json.get("얼굴각도", "정면"),
            턱=result_json.get("턱", "자연스러운"),
            is_wink=result_json.get("is_wink", False),
            wink_eye=result_json.get("wink_eye", ""),
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


def analyze_expression(
    expression_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> ExpressionAnalysisResult:
    """
    표정 분석 (편의 함수)

    Args:
        expression_image: 표정 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        ExpressionAnalysisResult: 분석 결과
    """
    analyzer = ExpressionAnalyzer(api_key=api_key)
    return analyzer.analyze(expression_image)
