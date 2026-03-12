"""
Outfit Analyzer for MLB Brandcut Generation

Extracts detailed outfit information for accurate reproduction in generated images.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from PIL import Image
from google import genai
from google.genai import types
from core.config import VISION_MODEL
import json
import re


@dataclass
class LogoInfo:
    """Information about a logo/graphic on clothing"""
    brand: str
    type: str  # "text", "graphic", "embroidered", "printed"
    position: str  # "front_center", "left_chest", "back", etc.
    size: str  # "small", "medium", "large"
    color: str


@dataclass
class OutfitItem:
    """Single outfit item details"""
    category: str  # "top", "bottom", "outerwear", "accessory", "footwear"
    name: str
    color: str
    fit: str  # "regular", "oversized", "slim", etc.
    material_appearance: str  # "cotton", "denim", "leather", etc.
    details: List[str] = field(default_factory=list)  # Special features
    logos: List[LogoInfo] = field(default_factory=list)
    state: str = "normal"  # "open", "closed", "rolled", etc.


@dataclass
class OutfitAnalysis:
    """Complete outfit analysis result"""
    items: List[OutfitItem]
    overall_style: str
    color_palette: List[str]
    brand_detected: Optional[str]
    style_era: str  # "contemporary", "y2k", "90s", etc.
    formality: str  # "casual", "streetwear", "athletic", etc.
    prompt_section: str  # Ready-to-use prompt text


class OutfitAnalyzer:
    """Analyzes outfit images for accurate reproduction in generated images"""

    def __init__(self, client):
        """
        Initialize the outfit analyzer.

        Args:
            client: Google GenAI client instance
        """
        self.client = client
        self._analysis_prompt = self._build_analysis_prompt()

    def _build_analysis_prompt(self) -> str:
        """Build the VLM analysis prompt"""
        return '''당신은 패션 제품의 '차별적 디테일'만 찾아내는 선별적 분석가입니다.

아이템 제외 필터 (Strict Exclusion):
- 기본 무지 아이템: 로고, 그래픽, 특수 마감, 독특한 핏이 없는 평범한 아이템은 분석 생략
- 특이사항 없음: 브랜드 로고가 보이지 않고, 일반적인 레귤러 핏이며, 부자재 디테일이 전무한 경우

분석 집중 대상 (High Priority):
1. 변형된 실루엣: 벌룬핏, 가오리핏, 비대칭 커팅, 익스트림 크롭, NO BRIM 등
2. 미세 부자재: 배색 스티치, 빈티지 워싱, 2-way 지퍼, 로고 각인 단추
3. 로고/그래픽 좌표: 정확한 위치 (front_center, front_left, front_right, left_chest, back_center 등)
4. 소재의 질감: 시어, 슬러브, 헤어리(fuzzy), 코팅 가공 등 시각적 특성
5. 구조적 특이사항: 립 없음(no brim), 턴업, 지퍼 마감 등

출력 포맷 (JSON):
{
    "detected_items": [
        {
            "category": "아이템명 (예: fuzzy beanie, cargo jeans, varsity jacket)",
            "brand": {
                "name": "브랜드명 (예: NY Yankees, Red Sox)",
                "logo_pos": "정확한 위치 (front_center/front_left/front_right/left_chest/back_center)",
                "type": "형태 (embroidered/printed/intarsia_knit/chenille_patch/metal_hardware)"
            },
            "blind_spot": [
                "놓치기 쉬운 디테일 2~4개 (예: NO BRIM skull cap style, fuzzy mohair texture)"
            ],
            "spec": {
                "fit": "실루엣 (slim/regular/oversized/wide/cropped)",
                "structure": "구조적 특성 (예: no fold, raglan sleeves, snap buttons)",
                "finishing": "마감 (예: raw hem, ribbed cuffs)"
            },
            "color": {
                "primary": "주 색상",
                "secondary": "보조 색상 (있으면)"
            },
            "texture": "시각적 재질 특성 (예: fuzzy mohair, washed denim, satin polyester)"
        }
    ],
    "overall_style": "전체 스타일 (예: sporty streetwear)",
    "color_palette": ["색상 목록"],
    "brand_detected": "주요 브랜드"
}

CRITICAL:
- 로고 위치는 정확하게: front_center vs front_left vs front_right 구분 필수
- 구조적 디테일 필수: 비니의 "립 없음(no brim)", 팬츠의 "와이드핏" 등
- blind_spot에 AI가 놓치기 쉬운 핵심 특징 반드시 포함
'''

    def analyze(self, outfit_images: List[str]) -> OutfitAnalysis:
        """
        Analyze outfit images and return structured result.

        Args:
            outfit_images: List of paths to outfit images

        Returns:
            OutfitAnalysis with all extracted information
        """
        if not outfit_images:
            raise ValueError("At least one outfit image is required")

        # Limit to 5 images to avoid token limits
        images_to_analyze = outfit_images[:5]

        # Load images
        pil_images = []
        for img_path in images_to_analyze:
            try:
                pil_images.append(Image.open(img_path))
            except Exception as e:
                print(f"Warning: Could not load image {img_path}: {e}")

        if not pil_images:
            raise ValueError("No valid images could be loaded")

        # Call VLM
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    self._analysis_prompt,
                    *pil_images
                ]
            )

            response_text = response.text.strip()

            # Parse response
            data = self._parse_response(response_text)

            # Create OutfitAnalysis
            analysis = self._create_analysis_from_dict(data)

            # Build prompt section
            analysis.prompt_section = self.build_prompt_section(analysis)

            return analysis

        except Exception as e:
            print(f"Error during VLM analysis: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis()

    def build_prompt_section(self, analysis: OutfitAnalysis) -> str:
        """
        Build a prompt section for image generation.

        Args:
            analysis: OutfitAnalysis from analyze()

        Returns:
            Ready-to-use prompt text for outfit specification
        """
        lines = ["---OUTFIT (MANDATORY - REPRODUCE EXACTLY)---"]

        for i, item in enumerate(analysis.items, 1):
            # 기본 정보
            item_desc = f"{i}. [REQUIRED] {item.name}"
            item_desc += f" - {item.color}, {item.fit} fit"

            # 로고 정보
            if item.logos:
                for logo in item.logos:
                    item_desc += f"\n   LOGO: {logo.brand} at {logo.position} ({logo.type})"

            # CRITICAL: blind_spot 디테일 (AI가 놓치기 쉬운 것)
            if item.details:  # blind_spot이 여기에 저장됨
                item_desc += "\n   CRITICAL DETAILS:"
                for d in item.details:
                    item_desc += f"\n   - {d}"

            lines.append(item_desc)

        lines.append(f"\nOVERALL: {analysis.overall_style}")
        lines.append(f"COLORS: {', '.join(analysis.color_palette)}")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> dict:
        """Parse VLM JSON response with error handling"""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

        # Try to parse JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {response_text[:500]}")

            # Try to find JSON object in text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                try:
                    return json.loads(response_text[start_idx:end_idx+1])
                except json.JSONDecodeError:
                    pass

            # Return minimal valid structure
            return {
                "items": [],
                "overall_style": "unknown",
                "color_palette": [],
                "brand_detected": None,
                "style_era": "contemporary",
                "formality": "casual"
            }

    def _create_analysis_from_dict(self, data: dict) -> OutfitAnalysis:
        """Convert dict to OutfitAnalysis dataclass"""
        items = []

        # 새 포맷(detected_items) 또는 구 포맷(items) 모두 지원
        items_data = data.get("detected_items", data.get("items", []))

        for item_data in items_data:
            # Parse logos (새 포맷: brand 객체 / 구 포맷: logos 배열)
            logos = []
            if "brand" in item_data and item_data["brand"]:
                brand_info = item_data["brand"]
                logos.append(LogoInfo(
                    brand=brand_info.get("name", "unknown"),
                    type=brand_info.get("type", "printed"),
                    position=brand_info.get("logo_pos", "front_center"),
                    size="medium",  # 새 포맷엔 size 없음
                    color="unknown"  # 새 포맷엔 color 없음
                ))
            elif "logos" in item_data:
                for logo_data in item_data.get("logos", []):
                    logos.append(LogoInfo(
                        brand=logo_data.get("brand", "unknown"),
                        type=logo_data.get("type", "printed"),
                        position=logo_data.get("position", "front_center"),
                        size=logo_data.get("size", "medium"),
                        color=logo_data.get("color", "black")
                    ))

            # Parse fit/color (새 포맷: spec/color 객체 / 구 포맷: fit/color 문자열)
            fit = "regular"
            color = "unknown color"
            material = "cotton"

            if "spec" in item_data:
                spec = item_data["spec"]
                fit = spec.get("fit", "regular")
            elif "fit" in item_data:
                fit = item_data.get("fit", "regular")

            if "color" in item_data:
                if isinstance(item_data["color"], dict):
                    primary = item_data["color"].get("primary", "unknown")
                    secondary = item_data["color"].get("secondary")
                    color = f"{primary}" + (f" with {secondary}" if secondary else "")
                else:
                    color = item_data.get("color", "unknown color")

            if "texture" in item_data:
                material = item_data.get("texture", "cotton")
            elif "material_appearance" in item_data:
                material = item_data.get("material_appearance", "cotton")

            # Parse blind_spot (새 포맷) 또는 details (구 포맷)
            details = item_data.get("blind_spot", item_data.get("details", []))

            # Create OutfitItem
            items.append(OutfitItem(
                category=item_data.get("category", "top"),
                name=item_data.get("category", "unknown item"),  # 새 포맷에선 category가 아이템명
                color=color,
                fit=fit,
                material_appearance=material,
                details=details,
                logos=logos,
                state=item_data.get("state", "normal")
            ))

        return OutfitAnalysis(
            items=items,
            overall_style=data.get("overall_style", "casual streetwear"),
            color_palette=data.get("color_palette", []),
            brand_detected=data.get("brand_detected"),
            style_era=data.get("style_era", "contemporary"),
            formality=data.get("formality", "casual"),
            prompt_section=""  # Will be built separately
        )

    def _create_fallback_analysis(self) -> OutfitAnalysis:
        """Create a fallback analysis when VLM fails"""
        fallback_item = OutfitItem(
            category="top",
            name="casual shirt",
            color="neutral",
            fit="regular",
            material_appearance="cotton",
            details=[],
            logos=[],
            state="normal"
        )

        analysis = OutfitAnalysis(
            items=[fallback_item],
            overall_style="casual streetwear",
            color_palette=["neutral tones"],
            brand_detected=None,
            style_era="contemporary",
            formality="casual",
            prompt_section=""
        )

        analysis.prompt_section = self.build_prompt_section(analysis)
        return analysis


# Convenience function for quick analysis
def analyze_outfit(client, outfit_images: List[str]) -> OutfitAnalysis:
    """
    Convenience function to analyze outfit images.

    Args:
        client: Google GenAI client instance
        outfit_images: List of paths to outfit images

    Returns:
        OutfitAnalysis with all extracted information
    """
    analyzer = OutfitAnalyzer(client)
    return analyzer.analyze(outfit_images)
