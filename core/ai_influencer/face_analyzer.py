"""
VLM 얼굴 특징 분석기

얼굴 레퍼런스 이미지에서 얼굴형, 이목구비, 피부톤 등을
추출하여 프롬프트에 텍스트 앵커로 사용한다.

목적: Gemini가 온도(temperature)가 높아도 얼굴 동일성을
유지하도록, 이미지 레퍼런스 + 텍스트 설명의 이중 앵커링.

HairAnalyzer와 동일한 패턴.
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class FaceAnalysisResult:
    """얼굴 특징 분석 결과"""

    # 얼굴형
    face_shape: str  # 계란형, 둥근형, 각진형, 하트형, 긴형
    # 눈
    eye_shape: str  # 아몬드눈, 둥근눈, 고양이눈, 처진눈, 쌍커풀큰눈
    eye_size: str  # 크다, 보통, 작다
    eye_spacing: str  # 넓다, 보통, 좁다
    # 코
    nose_shape: str  # 오똑한, 넓적한, 매부리, 자연스러운, 콧대높은
    # 입술
    lip_shape: str  # 도톰한, 얇은, 윗입술도톰, 아랫입술도톰, 하트형
    # 턱선
    jawline: str  # 갸름한, 둥근, 각진, V라인, 자연스러운
    # 광대뼈
    cheekbones: str  # 높은, 평평한, 자연스러운
    # 피부톤
    skin_tone: str  # 밝은, 중간, 어두운, 아이보리, 웜톤, 쿨톤
    # 특징적 요소
    distinctive: str = ""  # 보조개, 점, 주근깨 등

    # 메타
    confidence: float = 0.5
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트 (한국어)"""
        parts = [
            f"얼굴형 {self.face_shape}",
            f"{self.eye_shape} ({self.eye_size})",
            f"코 {self.nose_shape}",
            f"입술 {self.lip_shape}",
            f"턱선 {self.jawline}",
            f"광대 {self.cheekbones}",
            f"피부 {self.skin_tone}",
        ]
        if self.distinctive:
            parts.append(self.distinctive)
        return ", ".join(parts)

    def to_schema_format(self) -> Dict[str, str]:
        """스키마 형식"""
        return {
            "얼굴형": self.face_shape,
            "눈_형태": self.eye_shape,
            "눈_크기": self.eye_size,
            "눈_간격": self.eye_spacing,
            "코": self.nose_shape,
            "입술": self.lip_shape,
            "턱선": self.jawline,
            "광대뼈": self.cheekbones,
            "피부톤": self.skin_tone,
            "특징": self.distinctive,
        }


# VLM 얼굴 분석 프롬프트
FACE_ANALYSIS_PROMPT = """이 이미지에서 인물의 얼굴 특징을 상세히 분석하세요.
다른 사진에서 동일 인물을 재현할 수 있도록 구별되는 특징에 집중하세요.

JSON 형식으로 출력:
```json
{
    "face_shape": "계란형/둥근형/각진형/하트형/긴형 중 하나",
    "eye_shape": "아몬드눈/둥근눈/고양이눈/처진눈/쌍커풀큰눈 중 하나",
    "eye_size": "크다/보통/작다 중 하나",
    "eye_spacing": "넓다/보통/좁다 중 하나",
    "nose_shape": "오똑한/넓적한/매부리/자연스러운/콧대높은 중 하나",
    "lip_shape": "도톰한/얇은/윗입술도톰/아랫입술도톰/하트형 중 하나",
    "jawline": "갸름한/둥근/각진/V라인/자연스러운 중 하나",
    "cheekbones": "높은/평평한/자연스러운 중 하나",
    "skin_tone": "밝은/중간/어두운/아이보리/웜톤/쿨톤 중 하나",
    "distinctive": "보조개, 점, 주근깨, 쌍커풀 등 특이사항 (없으면 빈 문자열)",
    "confidence": 0.0~1.0
}
```

JSON만 출력하세요."""


class FaceAnalyzer:
    """VLM 얼굴 특징 분석기"""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)

    def analyze(
        self,
        face_image: Union[str, Path, Image.Image],
    ) -> FaceAnalysisResult:
        """
        얼굴 이미지에서 특징 분석

        Args:
            face_image: 얼굴 레퍼런스 이미지

        Returns:
            FaceAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(face_image, (str, Path)):
            img = Image.open(face_image).convert("RGB")
        else:
            img = face_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=FACE_ANALYSIS_PROMPT),
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
            print(f"[FaceAnalyzer] API error: {e}")
            return FaceAnalysisResult(
                face_shape="계란형",
                eye_shape="아몬드눈",
                eye_size="보통",
                eye_spacing="보통",
                nose_shape="자연스러운",
                lip_shape="자연스러운",
                jawline="자연스러운",
                cheekbones="자연스러운",
                skin_tone="밝은",
                distinctive="",
                confidence=0.0,
                raw_response={"error": str(e)},
            )

        return FaceAnalysisResult(
            face_shape=result_json.get("face_shape", "계란형"),
            eye_shape=result_json.get("eye_shape", "아몬드눈"),
            eye_size=result_json.get("eye_size", "보통"),
            eye_spacing=result_json.get("eye_spacing", "보통"),
            nose_shape=result_json.get("nose_shape", "자연스러운"),
            lip_shape=result_json.get("lip_shape", "자연스러운"),
            jawline=result_json.get("jawline", "자연스러운"),
            cheekbones=result_json.get("cheekbones", "자연스러운"),
            skin_tone=result_json.get("skin_tone", "밝은"),
            distinctive=result_json.get("distinctive", ""),
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


def analyze_face(
    face_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> FaceAnalysisResult:
    """
    얼굴 특징 분석 (편의 함수)

    Args:
        face_image: 얼굴 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        FaceAnalysisResult: 분석 결과
    """
    analyzer = FaceAnalyzer(api_key=api_key)
    return analyzer.analyze(face_image)
