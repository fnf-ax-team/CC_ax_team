"""
VLM 바지 분석기

바지 이미지에서 색상, 소재, 패턴, 로고, 디테일을 추출한다.
핏 변형 시 보존해야 할 속성을 정확히 파악하는 것이 목적.
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
from .templates import PANTS_ANALYSIS_PROMPT


@dataclass
class LogoInfo:
    """로고 정보"""

    brand: str
    type: str  # embroidered, printed, patch, etc.
    position: str  # back_waist, front_pocket, etc.
    description: str = ""


@dataclass
class PantsAnalysis:
    """바지 분석 결과

    핏 변형 시 반드시 보존해야 할 모든 속성을 담는다.
    """

    # 현재 핏
    current_fit: str  # skinny, slim, regular, relaxed, wide, etc.

    # 색상 (3x 보존 대상)
    color_primary: str  # 메인 색상
    color_secondary: str  # 보조 색상
    color_wash: str  # 워싱 정도

    # 소재 (3x 보존 대상)
    material_type: str  # denim, cotton, polyester, etc.
    material_texture: str  # smooth, rough, soft, etc.
    material_weight: str  # light, medium, heavy
    material_finish: str  # raw, washed, coated, etc.

    # 패턴
    pattern_type: str  # solid, striped, plaid, etc.
    pattern_description: str

    # 허리
    waist_type: str  # belt_loop, elastic, drawstring, etc.
    waist_details: str

    # 포켓
    pockets_front: str  # slant, on-seam, patch, etc.
    pockets_back: str  # patch, welt, flap, etc.
    pockets_cargo: str  # none, side_thigh, etc.

    # 밑단
    hem_type: str  # plain, cuffed, raw, etc.
    hem_details: str

    # 로고 (3x 보존 대상)
    logos: List[LogoInfo] = field(default_factory=list)

    # 스티칭
    stitching_color: str = "tonal"
    stitching_type: str = "single"

    # 특이사항
    special_details: List[str] = field(default_factory=list)

    # 메타
    confidence: float = 0.5
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_preservation_text(self) -> str:
        """보존해야 할 속성을 텍스트로 변환 (프롬프트용)"""
        parts = []

        # 색상 (최우선 보존)
        color_desc = self.color_primary
        if self.color_secondary:
            color_desc += f" with {self.color_secondary}"
        if self.color_wash and self.color_wash != "none":
            color_desc += f", {self.color_wash} wash"
        parts.append(f"COLOR: {color_desc}")

        # 소재
        material_desc = self.material_type
        if self.material_texture:
            material_desc += f", {self.material_texture}"
        if self.material_weight:
            material_desc += f", {self.material_weight} weight"
        if self.material_finish and self.material_finish != "none":
            material_desc += f", {self.material_finish} finish"
        parts.append(f"MATERIAL: {material_desc}")

        # 패턴
        if self.pattern_type and self.pattern_type != "solid":
            parts.append(f"PATTERN: {self.pattern_type} - {self.pattern_description}")

        # 허리
        parts.append(
            f"WAIST: {self.waist_type}"
            + (f" ({self.waist_details})" if self.waist_details else "")
        )

        # 포켓
        pocket_parts = []
        if self.pockets_front and self.pockets_front != "none":
            pocket_parts.append(f"front: {self.pockets_front}")
        if self.pockets_back and self.pockets_back != "none":
            pocket_parts.append(f"back: {self.pockets_back}")
        if self.pockets_cargo and self.pockets_cargo != "none":
            pocket_parts.append(f"cargo: {self.pockets_cargo}")
        if pocket_parts:
            parts.append(f"POCKETS: {', '.join(pocket_parts)}")

        # 밑단
        parts.append(
            f"HEM: {self.hem_type}"
            + (f" ({self.hem_details})" if self.hem_details else "")
        )

        # 로고
        for logo in self.logos:
            parts.append(f"LOGO: {logo.brand} {logo.type} at {logo.position}")

        # 스티칭
        if self.stitching_color != "tonal":
            parts.append(f"STITCHING: {self.stitching_color} {self.stitching_type}")

        # 특이사항
        for detail in self.special_details:
            parts.append(f"DETAIL: {detail}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "current_fit": self.current_fit,
            "color": {
                "primary": self.color_primary,
                "secondary": self.color_secondary,
                "wash": self.color_wash,
            },
            "material": {
                "type": self.material_type,
                "texture": self.material_texture,
                "weight": self.material_weight,
                "finish": self.material_finish,
            },
            "pattern": {
                "type": self.pattern_type,
                "description": self.pattern_description,
            },
            "waist": {"type": self.waist_type, "details": self.waist_details},
            "pockets": {
                "front": self.pockets_front,
                "back": self.pockets_back,
                "cargo": self.pockets_cargo,
            },
            "hem": {"type": self.hem_type, "details": self.hem_details},
            "logos": [
                {
                    "brand": l.brand,
                    "type": l.type,
                    "position": l.position,
                    "description": l.description,
                }
                for l in self.logos
            ],
            "stitching": {"color": self.stitching_color, "type": self.stitching_type},
            "special_details": self.special_details,
            "confidence": self.confidence,
        }


class PantsAnalyzer:
    """VLM 바지 분석기"""

    def __init__(self, client: genai.Client):
        self.client = client

    def analyze(self, pants_image: Union[str, Path, Image.Image]) -> PantsAnalysis:
        """바지 이미지에서 속성 추출

        Args:
            pants_image: 바지 이미지 (경로 또는 PIL Image)

        Returns:
            PantsAnalysis: 분석 결과
        """
        # 이미지 로드
        if isinstance(pants_image, (str, Path)):
            img = Image.open(pants_image).convert("RGB")
        else:
            img = pants_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=PANTS_ANALYSIS_PROMPT),
            self._pil_to_part(img),
        ]

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
            data = json.loads(result_text)

        except Exception as e:
            print(f"[PantsAnalyzer] API error: {e}")
            return self._fallback_result(str(e))

        return self._parse_result(data)

    def _parse_result(self, data: Dict[str, Any]) -> PantsAnalysis:
        """API 응답을 PantsAnalysis로 변환"""
        color = data.get("color", {})
        material = data.get("material", {})
        pattern = data.get("pattern", {})
        waist = data.get("waist", {})
        pockets = data.get("pockets", {})
        hem = data.get("hem", {})
        stitching = data.get("stitching", {})

        logos = []
        for logo_data in data.get("logos", []):
            logos.append(
                LogoInfo(
                    brand=logo_data.get("brand", ""),
                    type=logo_data.get("type", ""),
                    position=logo_data.get("position", ""),
                    description=logo_data.get("description", ""),
                )
            )

        return PantsAnalysis(
            current_fit=data.get("current_fit", "regular"),
            color_primary=color.get("primary", ""),
            color_secondary=color.get("secondary", ""),
            color_wash=color.get("wash", "none"),
            material_type=material.get("type", ""),
            material_texture=material.get("texture", ""),
            material_weight=material.get("weight", "medium"),
            material_finish=material.get("finish", "none"),
            pattern_type=pattern.get("type", "solid"),
            pattern_description=pattern.get("description", ""),
            waist_type=waist.get("type", "belt_loop"),
            waist_details=waist.get("details", ""),
            pockets_front=pockets.get("front", "slant"),
            pockets_back=pockets.get("back", "patch"),
            pockets_cargo=pockets.get("cargo", "none"),
            hem_type=hem.get("type", "plain"),
            hem_details=hem.get("details", ""),
            logos=logos,
            stitching_color=stitching.get("color", "tonal"),
            stitching_type=stitching.get("type", "single"),
            special_details=data.get("special_details", []),
            confidence=data.get("confidence", 0.5),
            raw_response=data,
        )

    def _fallback_result(self, error: str) -> PantsAnalysis:
        """분석 실패 시 기본값"""
        return PantsAnalysis(
            current_fit="regular",
            color_primary="unknown",
            color_secondary="",
            color_wash="none",
            material_type="unknown",
            material_texture="",
            material_weight="medium",
            material_finish="none",
            pattern_type="solid",
            pattern_description="",
            waist_type="belt_loop",
            waist_details="",
            pockets_front="slant",
            pockets_back="patch",
            pockets_cargo="none",
            hem_type="plain",
            hem_details="",
            confidence=0.0,
            raw_response={"error": error},
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


def analyze_pants(
    pants_image: Union[str, Path, Image.Image],
    client: Optional[genai.Client] = None,
) -> PantsAnalysis:
    """바지 분석 편의 함수

    Args:
        pants_image: 바지 이미지
        client: Gemini API 클라이언트 (없으면 자동 생성)

    Returns:
        PantsAnalysis: 분석 결과
    """
    if client is None:
        from core.api import _get_next_api_key

        client = genai.Client(api_key=_get_next_api_key())

    analyzer = PantsAnalyzer(client)
    return analyzer.analyze(pants_image)
