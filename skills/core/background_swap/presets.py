"""
배경 스타일 프리셋 - 콘크리트, 도시, 스튜디오 스타일
"""

# ============================================================
# 콘크리트 스타일 (4종)
# ============================================================

CONCRETE_STYLES = {
    "1_raw": """Raw exposed concrete wall with visible texture and form marks.
Industrial, authentic, slightly weathered. Like a construction site or parking garage.""",
    "2_smooth": """Smooth polished concrete wall, minimalist and clean.
Modern architectural finish, subtle gray tones. Like a contemporary museum exterior.""",
    "3_metal": """Concrete wall with metal elements - steel beams, industrial fixtures.
Urban industrial aesthetic, mixed materials. Like a modern warehouse district.""",
    "4_brutalist": """Brutalist architecture style - massive concrete forms, geometric shapes.
Bold, monumental, dramatic shadows. Like a 70s government building or university.""",
}


# ============================================================
# 도시 스타일 (7종)
# ============================================================

CITY_STYLES = {
    "california_affluent": """Sunny California affluent neighborhood.
Warm golden light, palm trees, clean sidewalks, upscale residential area.
Beverly Hills / Malibu / Bel Air aesthetic.""",
    "california_retro": """1970s California retro aesthetic.
Warm film tones, vintage signage, retro architecture.
Palm Springs / Venice Beach vintage vibe.""",
    "london_affluent": """Upscale London neighborhood.
Classic Georgian townhouses, brick facades, manicured gardens.
Mayfair / Kensington / Chelsea aesthetic.""",
    "london_mayfair": """London Mayfair district.
Elegant storefronts, wrought iron railings, cobblestone details.
Luxury retail and residential mix.""",
    "hollywood_simple": """Clean Hollywood urban setting.
Modern American commercial buildings, clean lines.
Subtle urban backdrop, not distracting.""",
    "tokyo_shibuya": """Tokyo Shibuya crossing area.
Neon lights, dense urban, modern Japanese architecture.
Dynamic, energetic atmosphere.""",
    "paris_marais": """Paris Le Marais district.
Historic stone buildings, ornate balconies, charming streets.
Artistic, bohemian atmosphere.""",
}


# ============================================================
# 스튜디오 스타일 (4종)
# ============================================================

STUDIO_STYLES = {
    "white_cyclorama": """Pure white studio cyclorama background.
Seamless white curve, soft even lighting.
Clean, professional fashion photography setup.""",
    "gray_seamless": """Medium gray seamless paper background.
Neutral, versatile, professional.
Classic editorial photography setup.""",
    "black_dramatic": """Black studio background with dramatic lighting.
High contrast, moody, editorial.
Fashion magazine cover aesthetic.""",
    "natural_window": """Studio with large natural window light.
Soft directional light, subtle shadows.
Bright, airy, lifestyle photography feel.""",
}


def get_style_preset(style_key: str) -> str:
    """
    스타일 키로 프리셋 조회.

    Args:
        style_key: 스타일 키 (예: '1_raw', 'california_affluent', 'white_cyclorama')

    Returns:
        스타일 설명 텍스트, 없으면 빈 문자열
    """
    all_styles = {**CONCRETE_STYLES, **CITY_STYLES, **STUDIO_STYLES}
    return all_styles.get(style_key, "")


def list_all_styles() -> dict:
    """
    모든 스타일 프리셋 목록 반환.

    Returns:
        {"concrete": [...], "city": [...], "studio": [...]}
    """
    return {
        "concrete": list(CONCRETE_STYLES.keys()),
        "city": list(CITY_STYLES.keys()),
        "studio": list(STUDIO_STYLES.keys()),
    }


__all__ = [
    "CONCRETE_STYLES",
    "CITY_STYLES",
    "STUDIO_STYLES",
    "get_style_preset",
    "list_all_styles",
]
