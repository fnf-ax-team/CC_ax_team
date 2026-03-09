"""
VLM 헤어 분석기

얼굴 레퍼런스 이미지에서 헤어 정보를 추출하여
프롬프트 스키마 형식으로 반환합니다.

ExpressionAnalyzer와 동일한 패턴.
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class HairAnalysisResult:
    """헤어 분석 결과"""

    # 기본 정보
    style: str  # straight_loose, wavy, ponytail, bun, braids, short_bob
    color: str  # black, dark_brown, brown, blonde, red, ash_gray
    texture: str  # sleek, voluminous, textured, messy

    # 신뢰도
    confidence: float = 0.5
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_schema_format(self) -> Dict[str, str]:
        """프롬프트 스키마 형식으로 변환 (한국어 키)"""
        return {
            "스타일": self.style,
            "컬러": self.color,
            "질감": self.texture,
        }

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트로 변환"""
        return f"[헤어]: 스타일 {self.style}, 컬러 {self.color}, 질감 {self.texture}"


# VLM 헤어 분석 프롬프트
HAIR_ANALYSIS_PROMPT = """이 이미지에서 인물의 헤어 정보를 분석하세요.

JSON 형식으로 출력:
```json
{
    "style": "straight_loose/wavy/ponytail/bun/braids/short_bob 중 하나",
    "color": "black/dark_brown/brown/blonde/red/ash_gray 중 하나",
    "texture": "sleek/voluminous/textured/messy 중 하나",
    "confidence": 0.0~1.0
}
```

JSON만 출력하세요."""


class HairAnalyzer:
    """VLM 헤어 분석기"""

    def __init__(self, api_key: Optional[str] = None):
        """
        분석기 초기화

        Args:
            api_key: Gemini API 키 (None이면 자동 로드)
        """
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)

    def analyze(
        self,
        face_image: Union[str, Path, Image.Image],
    ) -> HairAnalysisResult:
        """
        얼굴 이미지에서 헤어 정보 분석

        Args:
            face_image: 얼굴 레퍼런스 이미지

        Returns:
            HairAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(face_image, (str, Path)):
            img = Image.open(face_image).convert("RGB")
        else:
            img = face_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=HAIR_ANALYSIS_PROMPT),
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
            print(f"[HairAnalyzer] API error: {e}")
            # 기본 결과 반환
            return HairAnalysisResult(
                style="straight_loose",
                color="dark_brown",
                texture="sleek",
                confidence=0.0,
                raw_response={"error": str(e)},
            )

        # 결과 변환
        return HairAnalysisResult(
            style=result_json.get("style", "straight_loose"),
            color=result_json.get("color", "dark_brown"),
            texture=result_json.get("texture", "sleek"),
            confidence=result_json.get("confidence", 0.5),
            raw_response=result_json,
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


def analyze_hair(
    face_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> HairAnalysisResult:
    """
    헤어 분석 (편의 함수)

    Args:
        face_image: 얼굴 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        HairAnalysisResult: 분석 결과
    """
    analyzer = HairAnalyzer(api_key=api_key)
    return analyzer.analyze(face_image)
