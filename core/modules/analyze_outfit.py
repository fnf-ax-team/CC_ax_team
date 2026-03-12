"""
착장 분석 래퍼 모듈

원본: core.outfit_analyzer (OutfitAnalyzer, OutfitAnalysis, OutfitItem, LogoInfo)

래핑 범위:
- 데이터클래스 재export (OutfitAnalysis, OutfitItem, LogoInfo)
- analyze_outfit(): api_key와 client 모두 지원하는 통합 인터페이스
- detail_level 옵션: "full" (기본), "basic" (간소화), "commerce" (판매 포인트 추가)
"""

from pathlib import Path
from typing import List, Optional, Union

from google import genai

# 원본 분석기 import
from core.outfit_analyzer import (
    OutfitAnalyzer,
    OutfitAnalysis,
    OutfitItem,
    LogoInfo,
)

# 통합 VLM 유틸리티
from core.modules.vlm_utils import vlm_call


# ============================================================
# 커머스 확장용 프롬프트
# ============================================================

_COMMERCE_PROMPT = """이 착장 이미지에서 커머스(이커머스) 판매를 위한 핵심 셀링 포인트를 분석하세요.

JSON 형식으로 출력:
```json
{
    "key_selling_points": [
        "셀링포인트 1 (예: 유니크한 오버사이즈 실루엣)",
        "셀링포인트 2",
        "셀링포인트 3"
    ],
    "target_audience": "타겟 고객층 설명",
    "styling_tip": "스타일링 팁 한 줄"
}
```

JSON만 출력하세요."""


# ============================================================
# 메인 분석 함수
# ============================================================


def analyze_outfit(
    images: List[Union[str, Path]],
    api_key: Optional[str] = None,
    client=None,
    detail_level: str = "full",
    per_image: bool = False,
) -> Union[OutfitAnalysis, List[OutfitAnalysis]]:
    """
    착장 분석 (통합 인터페이스).

    api_key 또는 client 중 하나만 제공하면 된다.
    detail_level에 따라 분석 깊이가 달라진다.

    Args:
        images: 착장 이미지 경로 리스트
        api_key: Gemini API 키 (client가 없을 때 사용)
        client: genai.Client 인스턴스 (있으면 우선 사용)
        detail_level: 분석 상세도
            - "full": 기본 (OutfitAnalyzer.analyze 그대로)
            - "basic": 간소화 (blind_spot/details 생략)
            - "commerce": full + 셀링포인트/타겟고객 추가
        per_image: True면 이미지당 개별 분석 (착장스왑용).
            List[OutfitAnalysis]를 반환한다.

    Returns:
        per_image=False: OutfitAnalysis 객체
        per_image=True: List[OutfitAnalysis] (이미지당 1개)
    """
    # 클라이언트 초기화
    if client is None:
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    # per_image 모드: 이미지당 개별 분석
    if per_image:
        analyzer = OutfitAnalyzer(client)
        results = []
        for img in images:
            try:
                analysis = analyzer.analyze([img])
                if detail_level == "basic":
                    for item in analysis.items:
                        item.details = []
                results.append(analysis)
            except Exception as e:
                print(f"[analyze_outfit] 개별 분석 실패: {e}")
                # 빈 분석 결과로 폴백
                results.append(
                    OutfitAnalysis(
                        items=[],
                        overall_style="",
                        color_palette=[],
                        brand_detected=None,
                        style_era="contemporary",
                        formality="casual",
                        prompt_section="",
                    )
                )
        return results

    # 1) 기본 분석 (OutfitAnalyzer 사용)
    analyzer = OutfitAnalyzer(client)
    analysis = analyzer.analyze(images)

    # 2) detail_level별 후처리
    if detail_level == "basic":
        # 간소화: details(blind_spot) 제거
        for item in analysis.items:
            item.details = []
        return analysis

    if detail_level == "commerce":
        # 커머스 확장: 셀링포인트 추가 VLM 호출
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        commerce_data = vlm_call(
            api_key=api_key,
            prompt=_COMMERCE_PROMPT,
            images=images,
            temperature=0.2,
        )

        # 커머스 데이터를 prompt_section에 추가
        if "key_selling_points" in commerce_data:
            selling_lines = "\n".join(
                f"  - {sp}" for sp in commerce_data["key_selling_points"]
            )
            analysis.prompt_section += f"\n\n[KEY SELLING POINTS]\n{selling_lines}"
            if commerce_data.get("styling_tip"):
                analysis.prompt_section += (
                    f"\n[STYLING TIP] {commerce_data['styling_tip']}"
                )

        return analysis

    # detail_level == "full" (기본): 그대로 반환
    return analysis


# ============================================================
# 변환 함수: OutfitAnalysis → 워크플로별 dict
# ============================================================

# 이커머스 카테고리 매핑 (OutfitItem.category → ecommerce type)
_ECOMMERCE_CATEGORY_MAP = {
    "outerwear": "outer",
    "top": "top",
    "bottom": "bottom",
    "footwear": "shoes",
    "accessory": "accessories",
    "headwear": "accessories",
}


def _format_logo_text(logos: List[LogoInfo]) -> str:
    """LogoInfo 리스트 → 'position: brand type (color)' 텍스트."""
    if not logos:
        return ""
    parts = []
    for logo in logos:
        desc = f"{logo.position}: {logo.brand} {logo.type}"
        if logo.color:
            desc += f" ({logo.color})"
        parts.append(desc)
    return "; ".join(parts)


def _infer_pose_from_items(items: List[OutfitItem]) -> str:
    """착장 아이템에서 이커머스 권장 포즈 추론."""
    has_outer = any(item.category == "outerwear" for item in items)
    has_shoes = any(item.category == "footwear" for item in items)

    # 후면 디테일 감지
    for item in items:
        for detail in item.details:
            if any(kw in detail.lower() for kw in ["back print", "hood", "후드", "백"]):
                return "back_view"

    if has_outer and has_shoes:
        return "front_standing"
    if not has_shoes:
        return "detail_closeup"
    return "front_standing"


def to_ecommerce_dict(
    analysis: OutfitAnalysis,
    selling_points: Optional[List[str]] = None,
) -> dict:
    """OutfitAnalysis → 이커머스 포맷 dict.

    반환 키: items[], overall_style, recommended_pose, key_selling_points, _raw

    Args:
        analysis: OutfitAnalysis 객체
        selling_points: 셀링포인트 리스트 (commerce 모드에서 추출)
    """
    items = []
    for outfit_item in analysis.items:
        ecom_type = _ECOMMERCE_CATEGORY_MAP.get(outfit_item.category, "accessories")
        items.append(
            {
                "type": ecom_type,
                "color": outfit_item.color,
                "material": outfit_item.material_appearance,
                "logo": _format_logo_text(outfit_item.logos),
                "details": outfit_item.details,
                "item": outfit_item.name,
            }
        )

    return {
        "items": items,
        "overall_style": analysis.overall_style,
        "recommended_pose": _infer_pose_from_items(analysis.items),
        "key_selling_points": selling_points or [],
        "_raw": {
            "brand_detected": analysis.brand_detected,
            "style_era": analysis.style_era,
            "formality": analysis.formality,
            "color_palette": analysis.color_palette,
        },
    }


def to_outfit_swap_dict(analysis: OutfitAnalysis) -> dict:
    """OutfitAnalysis → 착장스왑 포맷 dict (단일 아이템 기준).

    반환 키: item_type, color, material, logo, details, prompt_description

    분석 결과의 첫 번째 아이템을 기준으로 변환한다.
    아이템이 없으면 폴백값을 반환한다.
    """
    if not analysis.items:
        return {
            "item_type": "garment",
            "color": "unknown",
            "material": "fabric",
            "logo": None,
            "details": [],
            "prompt_description": "outfit item",
        }

    item = analysis.items[0]

    # 로고 텍스트 추출
    logo_text = None
    if item.logos:
        logo = item.logos[0]
        logo_text = f"{logo.brand} {logo.type}"

    # prompt_description 합성
    parts = [item.color, item.material_appearance, item.name]
    if item.fit and item.fit != "regular":
        parts.insert(0, item.fit)
    if logo_text:
        parts.append(f"with {logo_text}")
    prompt_desc = " ".join(p for p in parts if p)

    return {
        "item_type": item.name or item.category,
        "color": item.color,
        "material": item.material_appearance,
        "logo": logo_text,
        "details": item.details,
        "prompt_description": prompt_desc,
    }


# 셀카 카테고리 추론용 키워드
_SELFIE_CATEGORY_KEYWORDS = {
    "pajama": "pajama",
    "sleepwear": "pajama",
    "hoodie": "hoodie",
    "sweatshirt": "hoodie",
    "dress": "dress",
    "one-piece": "dress",
    "suit": "formal",
    "blazer": "formal",
    "coat": "outerwear",
    "jacket": "outerwear",
    "cardigan": "outerwear",
    "athleisure": "athleisure",
    "sportswear": "athleisure",
    "gym": "athleisure",
}


def to_selfie_dict(analysis: OutfitAnalysis) -> dict:
    """OutfitAnalysis → 셀카 포맷 dict.

    반환 키: category, top{}, bottom{}, style, prompt_text
    """
    # 카테고리 추론
    category = "casual"
    all_names = " ".join(item.name.lower() for item in analysis.items)
    for keyword, cat in _SELFIE_CATEGORY_KEYWORDS.items():
        if keyword in all_names:
            category = cat
            break

    # top/bottom 분리
    top_data = {"item": "", "color": "", "fit": "regular", "details": []}
    bottom_data = {"item": "", "color": "", "details": []}

    for item in analysis.items:
        if item.category in ("top", "outerwear"):
            top_data = {
                "item": item.name,
                "color": item.color,
                "fit": item.fit,
                "details": item.details,
            }
        elif item.category == "bottom":
            bottom_data = {
                "item": item.name,
                "color": item.color,
                "details": item.details,
            }

    # prompt_text 합성
    prompt_parts = []
    if top_data["item"]:
        prompt_parts.append(f"{top_data['color']} {top_data['item']}".strip())
    if bottom_data["item"]:
        prompt_parts.append(f"{bottom_data['color']} {bottom_data['item']}".strip())
    prompt_text = (
        f"{category} outfit: {', '.join(prompt_parts)}"
        if prompt_parts
        else f"{category} everyday outfit"
    )

    return {
        "category": category,
        "top": top_data,
        "bottom": bottom_data,
        "style": analysis.overall_style or f"{category} everyday",
        "prompt_text": prompt_text,
    }


def _extract_selling_points_from_prompt_section(prompt_section: str) -> List[str]:
    """prompt_section에서 [KEY SELLING POINTS] 섹션을 파싱하여 리스트로 반환."""
    selling_points = []
    in_section = False
    for line in prompt_section.split("\n"):
        line = line.strip()
        if "[KEY SELLING POINTS]" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("["):
                break  # 다음 섹션 시작
            if line.startswith("- "):
                selling_points.append(line[2:].strip())
    return selling_points


__all__ = [
    "OutfitAnalysis",
    "OutfitItem",
    "LogoInfo",
    "analyze_outfit",
    "to_ecommerce_dict",
    "to_outfit_swap_dict",
    "to_selfie_dict",
]
