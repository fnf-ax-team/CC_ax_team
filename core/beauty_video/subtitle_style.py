"""
숏폼/릴스 자막 스타일 모듈

2가지 프리셋:
  - thumbnail: 유튜브 썸네일 (G마켓 산스 볼드 + 기울기 + 테두리 + 이모지)
  - broadcast: 방송 자막 바 (흰 배경 바 + 검정 텍스트, 깔끔)

2가지 적용 방식:
  1. Gemini 프롬프트 방식: build_subtitle_prompt() → 이미지 생성 프롬프트에 합체
  2. PIL 오버레이 방식: apply_subtitle() → 기존 이미지에 자막 오버레이 (폴백)
"""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# Gemini 프롬프트 빌더 (메인 방식)
# 이미지 생성 시 프롬프트에 포함시켜 Gemini가 직접 자막을 렌더링
# ============================================================

# 스타일별 프롬프트 템플릿
_THUMBNAIL_STYLE_GUIDE = """[자막 스타일: 유튜브 뷰티 썸네일]
- 폰트: 한국어 고딕 볼드체 (G마켓 산스 볼드처럼 둥글고 굵은 서체)
- 기울기: 약간 이탤릭 (오른쪽으로 살짝 기울어진 느낌)
- 테두리: 모든 텍스트에 검정색 외곽선 3~5px
- 정렬: 모든 텍스트 가로 가운데 정렬
- 배경: 텍스트 뒤에 살짝 어두운 반투명 그라디언트 (가독성)

[텍스트 레이아웃 - 상단에서 하단 순서]
{text_layout}

[색상 규칙]
- 소제목: 흰색 텍스트 + 검정 테두리
- 메인 텍스트: 흰색 텍스트 + 검정 테두리 (가장 큰 글씨)
- 브랜드명/강조: {accent_desc}
- 가격/CTA: {accent_desc}
- 이모지: 소제목 줄에만 인라인으로 배치 (앞뒤에 1개씩)

[강조색 팔레트 참고 - 콘텐츠에 어울리는 은은한 색상 사용]
- 코랄 로즈 (#D4847A) — 뷰티, 스킨케어, 로맨틱
- 소프트 라임 (#A8C97A) — 프레시, 자연, 건강
- 머스타드 옐로 (#D4B86A) — 세일, 할인, 포인트
- 더스티 라벤더 (#9B8EC4) — 프리미엄, 고급, 트렌디
- 밀키 피치 (#E8A88A) — 따뜻한, 일상, 데일리

[절대 금지]
- 텍스트를 제품/인물 위에 겹치지 말 것
- 텍스트를 이미지 바깥으로 잘리게 하지 말 것
- 글자 간격이 너무 넓거나 좁지 않게"""

_BROADCAST_STYLE_GUIDE = """[자막 스타일: 방송 자막 바]
- 폰트: 한국어 고딕 볼드체 (깔끔하고 정자, 기울기 없음)
- 배경 바: 흰색 반투명 라운드 사각형 (opacity 85%, 모서리 라운드)
- 텍스트 색상: 검정색 (#000000)
- 정렬: 바 안에서 가운데 정렬
- 바 위치: {position_desc}
- 바 그림자: 살짝 드롭섀도우 (자연스러움)

[텍스트 내용]
{text_layout}

[절대 금지]
- 바 없이 텍스트만 띄우지 말 것
- 텍스트가 바 밖으로 나가지 말 것
- 바가 인물 얼굴을 가리지 말 것"""

_POSITION_DESC = {
    "top": "이미지 상단 5% 위치",
    "center": "이미지 세로 중앙",
    "bottom": "이미지 하단 20% 위치 (인스타 UI 가림 영역 위)",
}


def build_subtitle_prompt(
    style: str,
    texts: dict,
    position: str = "bottom",
) -> str:
    """
    Gemini 이미지 생성용 자막 스타일 프롬프트 조각을 반환.

    이미지 생성 프롬프트 끝에 이 결과를 합체시키면
    Gemini가 해당 스타일로 자막이 포함된 이미지를 직접 생성한다.

    Args:
        style: "thumbnail" 또는 "broadcast"
        texts: 텍스트 딕셔너리
            thumbnail: {"subtitle": str, "main": [str], "brand": str, "price": str}
            broadcast: {"lines": [str]}
        position: broadcast 위치 ("top", "center", "bottom")

    Returns:
        str: 프롬프트에 합체할 자막 스타일 가이드 텍스트

    사용 예시:
        prompt = f"{image_prompt}\\n\\n{build_subtitle_prompt('thumbnail', texts)}"
    """
    if style == "thumbnail":
        return _build_thumbnail_prompt(texts)
    elif style == "broadcast":
        return _build_broadcast_prompt(texts, position)
    else:
        raise ValueError(f"Unknown style: {style}. Use 'thumbnail' or 'broadcast'.")


# 강조색 프리셋 (이름 → hex)
ACCENT_COLORS = {
    "coral": {"hex": "#D4847A", "name": "코랄 로즈", "desc": "뷰티/스킨케어/로맨틱"},
    "lime": {"hex": "#A8C97A", "name": "소프트 라임", "desc": "프레시/자연/건강"},
    "yellow": {"hex": "#D4B86A", "name": "머스타드 옐로", "desc": "세일/할인/포인트"},
    "lavender": {
        "hex": "#9B8EC4",
        "name": "더스티 라벤더",
        "desc": "프리미엄/고급/트렌디",
    },
    "peach": {"hex": "#E8A88A", "name": "밀키 피치", "desc": "따뜻한/일상/데일리"},
}
DEFAULT_ACCENT = "coral"


def _build_thumbnail_prompt(texts: dict) -> str:
    """thumbnail 스타일 프롬프트 생성"""
    lines = []

    # 강조색 결정 (texts에 accent_color 키가 있으면 사용, 없으면 기본값)
    accent_key = texts.get("accent_color", DEFAULT_ACCENT)
    accent = ACCENT_COLORS.get(accent_key, ACCENT_COLORS[DEFAULT_ACCENT])
    accent_label = f"{accent['name']}({accent['hex']})"

    subtitle = texts.get("subtitle", "")
    if subtitle:
        lines.append(f"1줄 (작은 글씨, 이모지 인라인): {subtitle}")

    main_lines = texts.get("main", [])
    for i, text in enumerate(main_lines):
        lines.append(f"{len(lines)+1}줄 (가장 큰 글씨, 흰색): {text}")

    brand = texts.get("brand", "")
    if brand:
        lines.append(f"{len(lines)+1}줄 (중간 글씨, {accent_label}): {brand}")

    price = texts.get("price", "")
    if price:
        lines.append(f"하단 ({accent_label}): {price}")

    text_layout = "\n".join(f"  - {l}" for l in lines)
    accent_desc = f"{accent_label} 텍스트 + 검정 테두리"
    return _THUMBNAIL_STYLE_GUIDE.format(
        text_layout=text_layout,
        accent_desc=accent_desc,
    )


def _build_broadcast_prompt(texts: dict, position: str = "bottom") -> str:
    """broadcast 스타일 프롬프트 생성"""
    lines = texts.get("lines", [])
    text_layout = "\n".join(f"  - {l}" for l in lines)
    position_desc = _POSITION_DESC.get(position, _POSITION_DESC["bottom"])
    return _BROADCAST_STYLE_GUIDE.format(
        text_layout=text_layout,
        position_desc=position_desc,
    )


# ============================================================
# PIL 오버레이 (폴백 방식)
# Gemini 텍스트 정확도가 낮을 때 사용
# ============================================================

try:
    from pilmoji import Pilmoji
    from pilmoji.source import AppleEmojiSource

    HAS_PILMOJI = True
except ImportError:
    HAS_PILMOJI = False


# ============================================================
# 폰트
# ============================================================
_FONT_PATHS = [
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts/GmarketSansBold.otf",
    Path("C:/Windows/Fonts/GmarketSansBold.otf"),
    Path("C:/Windows/Fonts/malgunbd.ttf"),  # 폴백
]

_font_path = None
for fp in _FONT_PATHS:
    if fp.exists():
        _font_path = str(fp)
        break


def _font(size: int) -> ImageFont.FreeTypeFont:
    if _font_path:
        return ImageFont.truetype(_font_path, size)
    return ImageFont.load_default()


def _text_bbox(text: str, fnt: ImageFont.FreeTypeFont, sw: int = 0) -> tuple:
    temp = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(temp).textbbox(
        (0, 0), text, font=fnt, anchor="lt", stroke_width=sw
    )
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ============================================================
# Style A: 유튜브 썸네일 (thumbnail)
# ============================================================
def _draw_italic_stroke(
    img,
    xy,
    text,
    fnt,
    fill="#FFFFFF",
    stroke_fill="#000000",
    stroke_width=4,
    shear=0.18,
    anchor="mm",
):
    """기울기 + 테두리 텍스트"""
    bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox(
        (0, 0), text, font=fnt, anchor="lt", stroke_width=stroke_width
    )
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = stroke_width + 10
    shear_extra = int(th * abs(shear)) + 20
    lw = tw + shear_extra + pad * 2
    lh = th + pad * 2

    layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(
        (pad + shear_extra // 2, pad),
        text,
        font=fnt,
        fill=fill,
        anchor="lt",
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    layer = layer.transform(
        layer.size,
        Image.AFFINE,
        (1, shear, -shear * lh / 2, 0, 1, 0),
        resample=Image.BICUBIC,
    )

    x, y = xy
    if anchor == "mm":
        px, py = x - lw // 2, y - lh // 2
    else:
        px, py = x, y
    img.paste(layer, (px, py), layer)


def _get_aspect_scale(w: int, h: int) -> float:
    """이미지 비율에 따라 폰트 스케일 반환.

    가로형(16:9)=1.0 기준, 세로형(9:16)은 살짝만 축소.
    """
    ratio = w / h  # 가로/세로 비율
    if ratio >= 0.9:
        # 가로형/정사각/약간 세로 → 기본 크기
        return 1.0
    else:
        # 세로형 → 살짝 축소 (최소 0.75)
        return max(0.75, 0.55 + ratio * 0.5)


def _add_local_shadow(overlay_draw, cx, y_center, text_h, w, alpha_max=35, spread=1.5):
    """자막 줄 주변에만 좁은 그라디언트 그림자 추가 (전체 어둡게 X)."""
    half = int(text_h * spread)
    y_top = max(0, y_center - half)
    y_bot = y_center + half
    for i in range(y_bot - y_top):
        t = i / max(1, y_bot - y_top)
        # 가운데가 가장 짙고 양끝으로 사라지는 bell curve
        alpha = int(alpha_max * (1 - abs(2 * t - 1) ** 2))
        overlay_draw.line([(0, y_top + i), (w, y_top + i)], fill=(0, 0, 0, alpha))


def _apply_thumbnail(
    img: Image.Image,
    texts: dict,
) -> Image.Image:
    """
    Style A: 유튜브 썸네일 스타일

    texts = {
        "subtitle": "압도적 빔력;;",           # 소제목 (이모지 인라인)
        "main": ["하이라이터", "5종 비교"],     # 메인 텍스트 (줄 단위)
        "brand": "BANILA CO",                   # 브랜드 (강조색)
        "price": "16,000원",                    # 가격 (하단)
        "accent_color": "coral",                # 강조색 키 (ACCENT_COLORS 참조)
    }

    비율 자동 대응:
        가로형(16:9) → 기본 크기 (유튜브 썸네일)
        세로형(9:16) → 자동 축소 (~55%)
    """
    result = img.copy().convert("RGBA")
    w, h = result.size
    cx = w // 2
    shear = 0.18

    # 강조색 결정
    accent_key = texts.get("accent_color", DEFAULT_ACCENT)
    accent_hex = ACCENT_COLORS.get(accent_key, ACCENT_COLORS[DEFAULT_ACCENT])["hex"]

    # 비율 기반 자동 스케일
    asc = _get_aspect_scale(w, h)

    # 폰트 크기 (비율 반영)
    sz_sub = int(w * 0.06 * asc)
    sz_main = int(w * 0.19 * asc)
    sz_brand = int(w * 0.105 * asc)
    sz_price = int(w * 0.115 * asc)

    f_sub = _font(sz_sub)
    f_main = _font(sz_main)
    f_brand = _font(sz_brand)
    f_price = _font(sz_price)

    # 테두리 (비율 반영)
    sc = w / 1536 * asc
    sw3 = max(2, int(3 * sc))
    sw4 = max(2, int(4 * sc))
    sw5 = max(3, int(5 * sc))

    # 줄 높이 계산
    _, h_sub = _text_bbox("가", f_sub, sw3)
    _, h_main = _text_bbox("가", f_main, sw5)
    _, h_brand = _text_bbox("A", f_brand, sw4)

    gap_sub_main = int(h_sub * 0.4)
    gap_main = int(h_main * 0.08)
    gap_main_brand = int(h_brand * 0.2)

    main_lines = texts.get("main", [])
    n_main = len(main_lines)

    # 블록 y 좌표 계산 (상단 3% 시작)
    y = int(h * 0.03)

    # subtitle
    y_sub = y + h_sub // 2
    y += h_sub + gap_sub_main

    # main lines
    y_mains = []
    for i in range(n_main):
        y_mains.append(y + h_main // 2)
        y += h_main + (gap_main if i < n_main - 1 else gap_main_brand)

    # brand
    y_brand = y + h_brand // 2

    # 그림자 없음 — 텍스트 테두리(stroke)만으로 가독성 확보

    # ---- LINE 1: 소제목 (이모지: pilmoji 있으면 렌더, 없으면 텍스트만) ----
    subtitle = texts.get("subtitle", "")
    if subtitle:
        if HAS_PILMOJI:
            # pilmoji 설치됨 → 이모지 포함
            line1 = f"\U0001f496 {subtitle} \u2728"
            _, h1 = _text_bbox(line1, f_sub, sw3)
            pad = sw3 + 10
            shear_extra = int((h1 + pad * 2) * abs(shear)) + 20
            lw1 = int(w * 0.9)
            lh1 = h1 + pad * 2 + 20
            layer1 = Image.new("RGBA", (lw1, lh1), (0, 0, 0, 0))
            with Pilmoji(layer1, source=AppleEmojiSource) as pm:
                tw1, _ = _text_bbox(line1, f_sub, sw3)
                tx = (lw1 - tw1) // 2
                pm.text(
                    (tx, pad),
                    line1,
                    font=f_sub,
                    fill="#FFFFFF",
                    stroke_width=sw3,
                    stroke_fill="#000000",
                    emoji_scale_factor=1.0,
                )
            layer1 = layer1.transform(
                layer1.size,
                Image.AFFINE,
                (1, shear, -shear * lh1 / 2, 0, 1, 0),
                resample=Image.BICUBIC,
            )
            result.paste(layer1, (cx - lw1 // 2, y_sub - lh1 // 2), layer1)
        else:
            # pilmoji 없음 → 이모지 없이 텍스트만 렌더
            _draw_italic_stroke(
                result,
                (cx, y_sub),
                subtitle,
                f_sub,
                fill="#FFFFFF",
                stroke_fill="#000000",
                stroke_width=sw3,
                shear=shear,
            )

    # ---- MAIN LINES (흰색) ----
    for i, line in enumerate(main_lines):
        _draw_italic_stroke(
            result,
            (cx, y_mains[i]),
            line,
            f_main,
            fill="#FFFFFF",
            stroke_fill="#000000",
            stroke_width=sw5,
            shear=shear,
        )

    # ---- BRAND (강조색) ----
    brand = texts.get("brand", "")
    if brand:
        _draw_italic_stroke(
            result,
            (cx, y_brand),
            brand,
            f_brand,
            fill=accent_hex,
            stroke_fill="#000000",
            stroke_width=sw4,
            shear=shear,
        )

    # ---- PRICE (강조색, 통일) ----
    price = texts.get("price", "")
    if price:
        y_price = int(h * 0.925)
        _draw_italic_stroke(
            result,
            (cx, y_price),
            price,
            f_price,
            fill=accent_hex,
            stroke_fill="#000000",
            stroke_width=sw4,
            shear=shear,
        )

    return result.convert("RGB")


# ============================================================
# Style B: 방송 자막 바 (broadcast)
# ============================================================
def _apply_broadcast(
    img: Image.Image,
    texts: dict,
    position: str = "bottom",
) -> Image.Image:
    """
    Style B: 방송 자막 바

    texts = {
        "lines": ["이렇게 뭐 용량이 많을 필요도", "없을 것 같긴 해요"],
    }
    position = "top" | "center" | "bottom"
    """
    result = img.copy().convert("RGBA")
    w, h = result.size
    cx = w // 2

    lines = texts.get("lines", [])
    if not lines:
        return result.convert("RGB")

    # 폰트 (기울기 없음)
    sz = int(w * 0.055)
    fnt = _font(sz)

    # 줄 높이 계산
    line_heights = []
    line_widths = []
    for line in lines:
        tw, th = _text_bbox(line, fnt)
        line_widths.append(tw)
        line_heights.append(th)

    max_tw = max(line_widths)
    total_th = sum(line_heights)
    line_gap = int(sz * 0.35)
    total_th += line_gap * (len(lines) - 1)

    # 바 크기
    pad_x = int(w * 0.06)
    pad_y = int(sz * 0.55)
    bar_w = max_tw + pad_x * 2
    bar_h = total_th + pad_y * 2
    bar_x = cx - bar_w // 2
    radius = int(sz * 0.4)

    # 위치
    if position == "top":
        bar_y = int(h * 0.05)
    elif position == "center":
        bar_y = (h - bar_h) // 2
    else:  # bottom
        bar_y = int(h * 0.82) - bar_h // 2

    # 바 레이어 (흰색 반투명 + 라운드)
    bar_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_layer)

    # 그림자
    shadow_off = int(sz * 0.08)
    bar_draw.rounded_rectangle(
        [
            bar_x + shadow_off,
            bar_y + shadow_off,
            bar_x + bar_w + shadow_off,
            bar_y + bar_h + shadow_off,
        ],
        radius=radius,
        fill=(0, 0, 0, 30),
    )

    # 흰색 바
    bar_draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=radius,
        fill=(255, 255, 255, 220),
    )

    result = Image.alpha_composite(result, bar_layer)

    # 텍스트 (가운데 정렬, 검정)
    draw = ImageDraw.Draw(result)
    ty = bar_y + pad_y
    for i, line in enumerate(lines):
        draw.text(
            (cx, ty + line_heights[i] // 2),
            line,
            font=fnt,
            fill="#000000",
            anchor="mm",
        )
        ty += line_heights[i] + line_gap

    return result.convert("RGB")


# ============================================================
# 통합 인터페이스
# ============================================================
def apply_subtitle(
    image_path: str,
    style: str,
    texts: dict,
    position: str = "bottom",
    remove_existing_text: bool = False,
) -> Image.Image:
    """
    숏폼/릴스 자막 스타일 적용 (파일 경로 기반)

    Args:
        image_path: 입력 이미지 경로
        style: "thumbnail" 또는 "broadcast"
        texts: 텍스트 딕셔너리 (스타일별 구조 다름)
        position: 텍스트 위치 (broadcast만 적용)
        remove_existing_text: True면 Gemini로 기존 텍스트 제거 후 적용

    Returns:
        PIL Image (자막 오버레이 적용됨)
    """
    img = Image.open(image_path).convert("RGB")
    return apply_subtitle_to_image(img, style, texts, position)


def apply_subtitle_to_image(
    img: Image.Image,
    style: str,
    texts: dict,
    position: str = "bottom",
) -> Image.Image:
    """
    숏폼/릴스 자막 스타일 적용 (PIL Image 직접 입력)

    파이프라인 내부에서 이미 로드된 이미지에 자막을 적용할 때 사용.
    generate_beauty_reels() 등에서 I2V 전 스타트프레임에 자막 베이킹용.

    Args:
        img: PIL Image 객체
        style: "thumbnail" 또는 "broadcast"
        texts: 텍스트 딕셔너리 (스타일별 구조 다름)
            thumbnail: {"subtitle": str, "main": [str], "brand": str, "price": str}
            broadcast: {"lines": [str]}
        position: 텍스트 위치 (broadcast만 적용) - "top", "center", "bottom"

    Returns:
        PIL Image (자막 오버레이 적용됨)
    """
    img = img.convert("RGB")

    if style == "thumbnail":
        return _apply_thumbnail(img, texts)
    elif style == "broadcast":
        return _apply_broadcast(img, texts, position)
    else:
        raise ValueError(f"Unknown style: {style}. Use 'thumbnail' or 'broadcast'.")
