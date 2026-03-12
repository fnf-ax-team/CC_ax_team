"""
프롬프트 매핑 통합 모듈

기존에 분산되어 있던 매핑 데이터를 한 곳으로 통합한다.

통합 대상:
- core.brandcut.prompt_builder_v2.STATE_TO_STYLING_MAP (영문 state -> 한글 코디방법 ID)
- core.ai_influencer.prompt_builder._STATE_TO_KOREAN (영문 state -> 한글 설명)
- core.brandcut.prompt_builder_v2._infer_category()
- core.brandcut.prompt_builder_v2._format_logo_detail()
- core.brandcut.prompt_builder_v2._format_critical_detail()
"""

import re
from typing import Optional


# ============================================================
# STATE -> 한국어 매핑 (통합)
#
# brandcut의 STATE_TO_STYLING_MAP와 influencer의 _STATE_TO_KOREAN을
# 하나로 합침. 동일 키는 더 자세한 influencer 설명을 기본으로 사용하되,
# brandcut 전용 값(코디방법 ID)은 별도 dict로 유지.
# ============================================================

STATE_TO_KOREAN = {
    # brandcut + influencer 공통 (influencer 설명 우선)
    "open": "지퍼 오픈",
    "closed": "지퍼 클로즈",
    "draped": "어깨에 걸침",
    "one_arm": "한쪽 팔만 소매에 넣고 착용",
    "held": "손에 들고",
    "off_shoulder": "한쪽 어깨 흘러내림",
    "tucked": "넣어입기",
    "oversized": "오버사이즈",
    "rolled": "밑단 롤업",
    "backwards": "뒤로 쓰기",
    "normal": "정상착용",
    "cropped": "크롭, 배꼽 노출",
    # influencer 전용
    "loose_socks": "루즈삭스 함께",
    "crossbody_front": "크로스바디 앞으로",
    "crossbody_side": "크로스바디 옆으로",
    "layered": "레이어드 여러개",
}

# brandcut 전용: state -> 코디방법 ID (프롬프트 빌더에서 STYLING_PROMPT_MAP 키로 사용)
STATE_TO_STYLING_ID = {
    "open": "지퍼오픈",
    "closed": "지퍼클로즈",
    "draped": "어깨걸침",
    "one_arm": "한쪽만착용",
    "held": "손에들고",
    "off_shoulder": "한쪽어깨노출",
    "tucked": "넣어입기",
    "oversized": "오버사이즈",
    "rolled": "롤업",
    "backwards": "뒤로쓰기",
    "normal": "정상착용",
}


# ============================================================
# 성별 매핑
# ============================================================

GENDER_MAP = {
    "female": "여성",
    "male": "남성",
    "f": "여성",
    "m": "남성",
    "여성": "여성",
    "남성": "남성",
}


# ============================================================
# 카테고리 추론
# ============================================================


def infer_category(category: str, name: str = "") -> str:
    """
    OutfitItem의 category/name에서 표준 한글 카테고리를 추론한다.

    원본: core.brandcut.prompt_builder_v2._infer_category()

    Args:
        category: 아이템 카테고리 (영문 또는 한글)
        name: 아이템 이름 (보조 추론용)

    Returns:
        한글 카테고리 (아우터, 상의, 하의, 신발, 헤드웨어, 주얼리, 가방, 벨트)
    """
    # 직접 매핑
    category_map = {
        "outer": "아우터",
        "outerwear": "아우터",
        "top": "상의",
        "bottom": "하의",
        "shoes": "신발",
        "footwear": "신발",
        "headwear": "헤드웨어",
        "jewelry": "주얼리",
        "bag": "가방",
        "belt": "벨트",
        "accessory": "액세서리",
    }

    lower = category.lower()
    if lower in category_map:
        return category_map[lower]

    # 키워드 기반 추론
    text = f"{category} {name}".lower()

    if any(
        kw in text
        for kw in [
            "jacket",
            "coat",
            "hoodie",
            "blazer",
            "varsity",
            "outer",
            "cardigan",
            "parka",
        ]
    ):
        return "아우터"
    if any(
        kw in text
        for kw in ["top", "shirt", "tee", "tank", "sweater", "blouse", "knit"]
    ):
        return "상의"
    if any(
        kw in text
        for kw in ["pants", "jeans", "skirt", "shorts", "bottom", "trouser", "legging"]
    ):
        return "하의"
    if any(
        kw in text for kw in ["shoes", "sneaker", "boot", "sandal", "slipper", "loafer"]
    ):
        return "신발"
    if any(kw in text for kw in ["cap", "hat", "beanie", "bucket", "headband"]):
        return "헤드웨어"
    if any(
        kw in text for kw in ["bag", "purse", "backpack", "tote", "clutch", "pouch"]
    ):
        return "가방"
    if any(kw in text for kw in ["necklace", "bracelet", "ring", "earring", "chain"]):
        return "주얼리"
    if any(kw in text for kw in ["belt", "strap"]):
        return "벨트"

    return category


# ============================================================
# 로고/디테일 포맷
# ============================================================


def format_logo_detail(logo) -> str:
    """
    LogoInfo 객체를 MUST/NEVER 프롬프트 형식으로 변환.

    원본: core.brandcut.prompt_builder_v2._format_logo_detail()

    Args:
        logo: LogoInfo 또는 brand/position/type 속성을 가진 객체

    Returns:
        "[MUST: ... logo at ...] [NEVER: ...]" 형식 문자열
    """
    brand = getattr(logo, "brand", "unknown")
    position = getattr(logo, "position", "front_center")
    logo_type = getattr(logo, "type", "printed")

    position_never = {
        "front_right": "center or left",
        "front_left": "center or right",
        "front_center": "off-center",
    }
    never_part = position_never.get(position, "wrong position")

    return f"[MUST: {brand} logo at {position} ({logo_type})] [NEVER: {never_part}]"


def format_critical_detail(detail: str) -> str:
    """
    착장 디테일을 MUST/NEVER 프롬프트 형식으로 변환.

    원본: core.brandcut.prompt_builder_v2._format_critical_detail()

    Args:
        detail: 디테일 문자열 (예: "NO BRIM skull cap style")

    Returns:
        "[MUST: ...] [NEVER: ...]" 형식 문자열
    """
    detail_upper = detail.upper()

    # "NO ..." 패턴 -> 부정 강조
    if "NO " in detail_upper or "NO-" in detail_upper:
        negation_match = re.search(r"NO[- ]?(\w+)", detail, re.IGNORECASE)
        if negation_match:
            negated_item = negation_match.group(1).lower()
            return f"[MUST: {detail}] [NEVER: add {negated_item}]"
        return f"[MUST: {detail}]"

    # 로고 위치 강조
    if "front_right" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or left]"
    if "front_left" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or right]"

    # 텍스처 키워드 강조
    texture_keywords = [
        "fuzzy",
        "hairy",
        "mohair",
        "velvet",
        "satin",
        "matte",
        "glossy",
    ]
    if any(kw in detail.lower() for kw in texture_keywords):
        return f"[MUST: visible {detail}]"

    return f"[MUST: {detail}]"


__all__ = [
    "STATE_TO_KOREAN",
    "STATE_TO_STYLING_ID",
    "GENDER_MAP",
    "infer_category",
    "format_logo_detail",
    "format_critical_detail",
]
