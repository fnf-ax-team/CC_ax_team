"""
착장(스타일링) 섹션 포매터

3대 워크플로의 착장 프롬프트 빌드 로직을 통합:
- korean_detailed: 브랜드컷 방식 (한글 카테고리 + MUST/NEVER 로고 + 코디방법)
- image_first: 인플루언서 방식 (이미지가 주역, hard detail만 텍스트 보조)
- basic: 셀카/이커머스 방식 (간결한 영문 설명)

원본:
- core.brandcut.prompt_builder_v2 : 착장 섹션 빌드 로직 (라인 584-635)
- core.ai_influencer.prompt_builder : _build_outfit_section_image_first()
"""

from typing import List, Optional

from core.outfit_analyzer import OutfitItem, LogoInfo
from core.modules.prompt.mappings import (
    STATE_TO_KOREAN,
    STATE_TO_STYLING_ID,
    infer_category,
    format_logo_detail,
    format_critical_detail,
)


# ============================================================
# 코디방법 영문 프롬프트 매핑
# brandcut prompt_builder_v2.STYLING_PROMPT_MAP 통합
# ============================================================

STYLING_PROMPT_MAP = {
    "정상착용": "worn normally",
    "어깨걸침": "jacket draped over shoulder",
    "한쪽만착용": "worn on one arm only",
    "지퍼오픈": "zipper open",
    "지퍼클로즈": "zipper closed",
    "손에들고": "held in hand",
    "크롭": "cropped above waist",
    "넣어입기": "tucked into pants",
    "한쪽어깨노출": "off-shoulder on one side",
    "오버사이즈": "oversized fit",
    "롤업": "cuffed at ankle",
    "뒤로쓰기": "cap worn backwards",
}


# ============================================================
# 이미지 모델이 놓치기 쉬운 "hard detail" 패턴
# 인플루언서 prompt_builder._HARD_DETAIL_PATTERNS 통합
# ============================================================

_HARD_DETAIL_PATTERNS = [
    # 구조적 특이사항
    "no brim",
    "no fold",
    "asymmetric",
    "deconstructed",
    "double",
    "reversed",
    "backwards",
    "inside out",
    "skull cap",
    # 특이 네크라인/착용 방식
    "off-shoulder",
    "off_shoulder",
    "one-shoulder",
    "crop",
    "cutout",
    "slit",
    # 소재/질감 (이미지에서 미묘한 차이)
    "sheer",
    "mesh",
    "fuzzy",
    "mohair",
    "patent",
    "latex",
    "vinyl",
    "transparent",
    "translucent",
    "velvet",
    "corduroy",
    # 착용 상태
    "draped",
    "tied",
    "knotted",
    "layered",
    # 텍스트/그래픽 (VLM 오독 방지)
    "cursive",
    "필기체",
    "script",
    "handwritten",
]


def _is_hard_detail(text: str) -> bool:
    """이 디테일이 이미지만으로 재현하기 어려운 hard detail인지 판단"""
    text_lower = text.lower()
    return any(p in text_lower for p in _HARD_DETAIL_PATTERNS)


# ============================================================
# 하체 디테일 필터링 (프레이밍 기반)
# 인플루언서 prompt_builder._LOWER_LEG_KEYWORDS 통합
# ============================================================

_LOWER_LEG_KEYWORDS = [
    "on the left leg",
    "on the right leg",
    "on the leg",
    "on left leg",
    "on right leg",
    "lower leg",
    "calf",
    "ankle",
    "hem",
    "covering shoes",
    "covering feet",
    "extra-long length",
    "extra long length",
    "종아리",
    "발목",
    "밑단",
]


def _filter_bottom_details_for_framing(details: list, show_legs: bool) -> list:
    """프레이밍에 따라 bottom 아이템의 하단 위치 디테일 필터링.

    MFS 등 하체가 안 보이는 프레이밍에서는 종아리/발목 위치 디테일을 제거.
    """
    if show_legs or not details:
        return details
    return [
        d for d in details if not any(kw in d.lower() for kw in _LOWER_LEG_KEYWORDS)
    ]


# ============================================================
# 메인 함수
# ============================================================


def format_outfit_section(
    items: List[OutfitItem],
    mode: str = "korean_detailed",
    show_legs: bool = True,
) -> str:
    """
    착장 아이템 리스트를 프롬프트 텍스트로 변환.

    Args:
        items: OutfitItem 리스트 (core.outfit_analyzer 참조)
        mode: 포맷 모드
            - "korean_detailed": 한글 카테고리 + MUST/NEVER 로고 + 코디방법 (브랜드컷)
            - "image_first": 이미지 주도, hard detail만 텍스트 보조 (인플루언서)
            - "basic": 간결한 영문 설명 (셀카/이커머스)
        show_legs: 하체(무릎 이하) 표시 여부 (프레이밍 기반 필터링)

    Returns:
        포매팅된 착장 섹션 텍스트
    """
    if not items:
        return "(착장 이미지 참조)"

    if mode == "korean_detailed":
        return _format_korean_detailed(items)
    elif mode == "image_first":
        return _format_image_first(items, show_legs)
    elif mode == "basic":
        return _format_basic(items)
    else:
        raise ValueError(
            f"지원하지 않는 mode: {mode}. 사용 가능: korean_detailed, image_first, basic"
        )


# ============================================================
# mode="korean_detailed" (브랜드컷)
#
# 원본: brandcut prompt_builder_v2 라인 584-635
# 한글 카테고리명 + 아이템 설명 + MUST/NEVER 로고 + 코디방법
# ============================================================


def _format_korean_detailed(items: List[OutfitItem]) -> str:
    """브랜드컷 방식: 한글 카테고리 + MUST/NEVER 로고 래퍼 + 코디방법"""
    lines = []

    for item in items:
        # 한글 카테고리 추론
        kor_category = infer_category(item.category, item.name)

        # 아이템 설명 조합
        item_parts = [item.name]
        if item.color:
            item_parts.append(item.color)
        if item.fit and item.fit != "regular":
            item_parts.append(f"{item.fit} fit")
        if item.material_appearance:
            item_parts.append(item.material_appearance)

        # 로고 강조 (MUST/NEVER 형식)
        if item.logos:
            for logo in item.logos:
                item_parts.append(format_logo_detail(logo))

        # 디테일 강조 (MUST/NEVER 형식)
        if item.details:
            for detail in item.details:
                item_parts.append(format_critical_detail(detail))

        item_desc = ", ".join(item_parts)

        # 코디방법 추론 (state -> 코디방법 ID -> 영문 프롬프트)
        styling_id = _infer_styling_from_state(item.state, kor_category)
        styling_prompt = STYLING_PROMPT_MAP.get(styling_id, "worn normally")
        full_prompt = f"{item_desc}, {styling_prompt}"

        lines.append(f"- {kor_category}: {full_prompt}")

    return "\n".join(lines) if lines else "(착장 이미지 참조)"


# ============================================================
# mode="image_first" (인플루언서)
#
# 원본: influencer prompt_builder._build_outfit_section_image_first()
# 이미지가 주역, 텍스트에는 놓치기 쉬운 hard detail만 포함
# ============================================================


def _format_image_first(items: List[OutfitItem], show_legs: bool) -> str:
    """인플루언서 방식: 이미지 주도, hard detail만 텍스트 보조"""
    lines = []
    lines.append("## [스타일링] -- Match [OUTFIT] images EXACTLY")

    for item in items:
        # 프레이밍에 따라 신발/양말 필터링
        if item.category in ("shoes", "socks", "footwear") and not show_legs:
            continue

        # 1줄 요약: 색상 + 핏 + 이름 + 착용상태
        parts = []
        if item.color:
            parts.append(item.color)
        if item.fit:
            parts.append(item.fit)
        if item.name:
            parts.append(item.name)

        state = item.state or "normal"
        if state.lower() != "normal":
            korean = STATE_TO_KOREAN.get(state.lower(), state)
            parts.append(f"({korean})")

        if parts:
            lines.append(f"- {item.category}: {' '.join(parts)}")

        # 디테일 (bottom은 프레이밍 필터 적용)
        details = item.details or []
        if item.category == "bottom":
            details = _filter_bottom_details_for_framing(details, show_legs)
        for detail in details:
            lines.append(f"  - {detail}")

        # 로고 (브랜드가 유효한 경우만)
        if item.logos:
            for logo in item.logos:
                if logo.brand and logo.brand.lower() not in ("unknown", "none", ""):
                    lines.append(
                        f"  - logo: {logo.brand} ({logo.type}) at {logo.position}"
                    )

    # 특수 착용 상태 강조
    special_notes = []
    for item in items:
        if item.category in ("shoes", "socks", "footwear") and not show_legs:
            continue
        state = item.state or "normal"
        if state.lower() != "normal":
            korean = STATE_TO_KOREAN.get(state.lower(), state)
            special_notes.append(f"- {item.category}: {korean} 착용")

    if special_notes:
        lines.append("주의:")
        lines.extend(special_notes)

    return "\n".join(lines)


# ============================================================
# mode="basic" (셀카/이커머스)
#
# 간결한 영문 설명. 카테고리 + 이름 + 색상만.
# ============================================================


def _format_basic(items: List[OutfitItem]) -> str:
    """기본 방식: 간결한 영문 설명"""
    parts = []
    for item in items:
        desc = item.name
        if item.color:
            desc = f"{item.color} {desc}"
        parts.append(desc)

    if not parts:
        return "(see outfit images)"

    return "wearing " + ", ".join(parts)


# ============================================================
# 헬퍼: state -> 코디방법 ID 추론
# 원본: brandcut prompt_builder_v2.infer_styling_from_state()
# ============================================================


def _infer_styling_from_state(state: Optional[str], category: str) -> str:
    """OutfitItem.state에서 코디방법 ID를 추론한다.

    Args:
        state: 아이템 착용 상태 (예: "open", "draped")
        category: 한글 카테고리

    Returns:
        코디방법 ID (예: "지퍼오픈", "어깨걸침", "정상착용")
    """
    if not state or state.lower() in ("normal", ""):
        return "정상착용"

    normalized = state.lower().strip().replace(" ", "_").replace("-", "_")

    # 정확 매핑
    if normalized in STATE_TO_STYLING_ID:
        return STATE_TO_STYLING_ID[normalized]

    # 부분 매칭
    for key, value in STATE_TO_STYLING_ID.items():
        if key in normalized or normalized in key:
            return value

    return "정상착용"


__all__ = [
    "format_outfit_section",
    "STYLING_PROMPT_MAP",
]
