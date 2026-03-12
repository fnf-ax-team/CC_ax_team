"""
이커머스 프롬프트 조립 모듈

착장 분석 결과와 얼굴 분석 결과를 결합하여
이커머스 이미지 생성용 프롬프트를 구성한다.

브랜드컷 대비 차이점:
- 착장 정확도(40%) 최우선 — 브랜드 무드보다 상품 재현이 핵심
- 중립 배경(스튜디오/미니멀)만 사용 — 브랜드 특화 배경 금지
- 상업적 완성도 중시 — 판매 전환율에 직결
"""

from .templates import ECOMMERCE_GENERATION_PROMPT
from .presets import POSE_PRESETS, BACKGROUND_PRESETS, VALID_ECOMMERCE_BACKGROUNDS


def build_ecommerce_prompt(
    outfit_analysis: dict,
    face_analysis: dict,
    pose: str = "front_standing",
    background: str = "white_studio",
) -> str:
    """이커머스 모델 이미지 생성 프롬프트를 조립한다.

    ECOMMERCE_GENERATION_PROMPT 템플릿의 {{플레이스홀더}}를
    분석 결과와 프리셋 데이터로 치환하여 완성된 프롬프트를 반환한다.

    착장 정확도(40%)를 최우선으로 구성하며,
    각 착장 아이템의 디테일·색상·로고를 MUST/NEVER 형식으로 강조한다.

    Args:
        outfit_analysis: analyze_outfit_for_ecommerce() 반환 dict
        face_analysis: analyze_face_for_model() 반환 dict
        pose: POSE_PRESETS 키 또는 커스텀 포즈 설명 문자열.
              기본값 "front_standing".
        background: BACKGROUND_PRESETS 키 또는 커스텀 배경 설명 문자열.
                    이커머스는 중립 배경만 허용. 기본값 "white_studio".

    Returns:
        str: 완성된 이커머스 생성 프롬프트 (텍스트)
    """
    # 포즈 프리셋 해석
    pose_preset = _resolve_pose(pose, outfit_analysis)

    # 배경 프리셋 해석 (이커머스는 중립 배경만 허용)
    background_preset = _resolve_background(background)

    # 착장 텍스트 조립 (우선순위 최상, MUST/NEVER 강조)
    outfit_text = _build_outfit_text(outfit_analysis)

    # 얼굴 설명 텍스트 조립
    face_text = _build_face_text(face_analysis)

    # 판매 포인트 텍스트 조립
    selling_points = outfit_analysis.get("key_selling_points", [])
    selling_points_text = (
        "\n".join(f"  - {pt}" for pt in selling_points)
        if selling_points
        else "  - (분석된 판매 포인트 없음)"
    )

    # 템플릿 플레이스홀더 치환
    prompt = ECOMMERCE_GENERATION_PROMPT

    # 착장 플레이스홀더 치환
    prompt = prompt.replace('"{{outfit_analysis.outer}}"', outfit_text["outer"])
    prompt = prompt.replace('"{{outfit_analysis.top}}"', outfit_text["top"])
    prompt = prompt.replace('"{{outfit_analysis.bottom}}"', outfit_text["bottom"])
    prompt = prompt.replace('"{{outfit_analysis.shoes}}"', outfit_text["shoes"])
    prompt = prompt.replace(
        '"{{outfit_analysis.accessories}}"', outfit_text["accessories"]
    )

    # 포즈 플레이스홀더 치환
    prompt = prompt.replace(
        '"{{pose_preset.pose_desc}}"', f'"{pose_preset["pose_desc"]}"'
    )
    prompt = prompt.replace('"{{pose_preset.framing}}"', f'"{pose_preset["framing"]}"')
    prompt = prompt.replace('"{{pose_preset.angle}}"', f'"{pose_preset["angle"]}"')
    prompt = prompt.replace('"{{pose_preset.lens}}"', f'"{pose_preset["lens"]}"')
    prompt = prompt.replace('"{{pose_preset.height}}"', f'"{pose_preset["height"]}"')

    # 배경 플레이스홀더 치환
    prompt = prompt.replace(
        '"{{background_preset.location}}"', f'"{background_preset["location"]}"'
    )
    prompt = prompt.replace(
        '"{{background_preset.ambient}}"', f'"{background_preset["ambient"]}"'
    )
    prompt = prompt.replace(
        '"{{background_preset.mood}}"', f'"{background_preset["mood"]}"'
    )
    prompt = prompt.replace(
        '"{{background_preset.lighting}}"', f'"{background_preset["lighting"]}"'
    )

    # 얼굴 설명 및 판매 포인트 추가 (프롬프트 말미에 보강)
    supplement = _build_supplement_section(face_text, selling_points_text)

    return prompt + supplement


# ------------------------------------------------------------------
# 내부 헬퍼 함수
# ------------------------------------------------------------------


def _resolve_pose(pose: str, outfit_analysis: dict) -> dict:
    """포즈 키 또는 커스텀 문자열을 POSE_PRESETS dict로 변환."""
    if pose in POSE_PRESETS:
        return POSE_PRESETS[pose]

    # 착장 분석에서 권장 포즈 사용 시도
    recommended = outfit_analysis.get("recommended_pose", "front_standing")
    if recommended in POSE_PRESETS:
        return POSE_PRESETS[recommended]

    # 커스텀 포즈 문자열이면 기본 카메라 설정과 결합
    return {
        "framing": "FS",
        "angle": "front",
        "pose_desc": pose,
        "lens": "50mm",
        "height": "eye level",
    }


def _resolve_background(background: str) -> dict:
    """배경 키 또는 커스텀 문자열을 BACKGROUND_PRESETS dict로 변환.

    이커머스는 중립 배경만 허용. 유효하지 않은 키는 white_studio로 폴백.
    """
    if background in BACKGROUND_PRESETS:
        return BACKGROUND_PRESETS[background]

    # 이커머스 유효 배경이 아닌 경우 경고 후 기본값
    print(
        f"[EcommercePromptBuilder] 경고: '{background}'는 유효한 이커머스 배경이 아닙니다. "
        f"허용 배경: {VALID_ECOMMERCE_BACKGROUNDS}. white_studio로 폴백."
    )
    return BACKGROUND_PRESETS["white_studio"]


def _format_item_detail(item: dict) -> str:
    """단일 아이템 dict를 MUST/NEVER 강조 프롬프트 텍스트로 변환."""
    parts = []

    item_name = item.get("item", "")
    color = item.get("color", "")
    logo = item.get("logo", "")
    details = item.get("details", [])

    if item_name:
        parts.append(item_name)
    if color:
        parts.append(f"[MUST: color={color}]")
    if logo:
        parts.append(f"[MUST: logo at {logo}] [NEVER: logo omission or distortion]")
    for detail in details:
        if detail:
            parts.append(f"[MUST: {detail}]")

    return ", ".join(parts) if parts else "not applicable"


def _build_outfit_text(outfit_analysis: dict) -> dict:
    """outfit_analysis.items를 카테고리별 프롬프트 텍스트 dict로 변환."""
    result = {
        "outer": '"not applicable"',
        "top": '"not applicable"',
        "bottom": '"not applicable"',
        "shoes": '"not applicable"',
        "accessories": '"not applicable"',
    }

    items = outfit_analysis.get("items", [])
    # 카테고리별 첫 번째 아이템만 대표로 사용 (복수 아이템이면 합산)
    category_texts: dict[str, list] = {}

    for item in items:
        item_type = item.get("type", "")
        text = _format_item_detail(item)
        if item_type in result:
            category_texts.setdefault(item_type, []).append(text)

    for category, texts in category_texts.items():
        combined = " | ".join(texts)
        result[category] = f'"{combined}"'

    return result


def _build_face_text(face_analysis: dict) -> str:
    """face_analysis를 생성 프롬프트용 텍스트로 변환."""
    desc = face_analysis.get("face_description", "")
    skin = face_analysis.get("skin_tone", "")
    age = face_analysis.get("age_range", "")
    expr = face_analysis.get("expression_style", "natural")

    parts = []
    if desc:
        parts.append(desc)
    if skin:
        parts.append(f"skin tone: {skin}")
    if age:
        parts.append(f"age range: {age}")
    if expr:
        parts.append(f"expression: {expr}, approachable, looking at camera")

    return ", ".join(parts) if parts else "natural features, approachable expression"


def _build_supplement_section(face_text: str, selling_points_text: str) -> str:
    """프롬프트 말미에 추가되는 보강 섹션 (얼굴 설명 + 판매 포인트)."""
    return f"""

## 모델 얼굴 특징 (참조 이미지 기반)
{face_text}

## 핵심 판매 포인트 (생성 시 강조)
{selling_points_text}

## 이커머스 품질 기준
- 스튜디오급 조명 필수 (그림자 최소화)
- 배경은 중립적으로 유지 (브랜드 특화 요소 금지)
- 착장 색상·로고·디테일은 참조 이미지와 pixel-perfect 일치
- AI 특유 플라스틱 피부 금지, 자연스러운 피부 텍스처
"""
