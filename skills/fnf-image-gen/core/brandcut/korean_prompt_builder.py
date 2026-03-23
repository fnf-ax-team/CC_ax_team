"""
한국어 자연어 프롬프트 생성기

JSON 프롬프트를 인플루언서 스타일 한국어 자연어로 변환.
인플루언서 스킬에서 검증된 품질 향상 패턴 적용.

Functions:
    build_korean_prompt: JSON 프롬프트를 한국어 자연어로 변환
    enhance_with_korean_layer: 기존 JSON 프롬프트에 한국어 레이어 추가
"""

from typing import Optional


# 품질 지시 템플릿 (인플루언서에서 검증됨)
QUALITY_SECTION_TEMPLATE = """
[품질]
초사실적 패션 화보. 진짜 사진과 구분 안 되게.
자연스러운 피부 질감, 모공까지 보이게.
손가락 정확히 5개.
천의 자연스러운 주름과 무게감.
진짜 카메라로 찍은 것 같은 얕은 심도와 보케.

절대 안 됨: 밝은 미소, 인위적인 포즈, 다른 사람들, 만화 느낌, 플라스틱 피부, 누런 톤
"""

# 순간 묘사 템플릿 (동작/상황 기반)
MOMENT_TEMPLATES = {
    "stand": "서 있는 자연스러운 순간. 포즈가 아니라 쉬는 느낌.",
    "walk": "걷다가 멈춘 찰나. 자연스러운 움직임 포착.",
    "lean": "기대어 쉬고 있는 순간. 여유로운 분위기.",
    "sit": "앉아서 생각에 잠긴 순간. 자연스러운 휴식.",
    "turn": "뒤돌아보는 찰나. '뭐?' 하는 표정.",
}


def build_korean_prompt(
    prompt_json: dict,
    include_moment: bool = True,
    moment_type: Optional[str] = None,
) -> str:
    """
    JSON 프롬프트를 한국어 자연어로 변환

    Args:
        prompt_json: 기존 JSON 프롬프트 (prompt_builder.py에서 생성)
        include_moment: [순간] 섹션 포함 여부
        moment_type: 순간 타입 ("stand", "walk", "lean", "sit", "turn")

    Returns:
        str: 한국어 자연어 프롬프트
    """
    sections = []

    # 1. 모델 정보
    model_info = prompt_json.get("모델", {})
    gender = model_info.get("성별", "female")

    model_desc = f"이 얼굴의 한국인 {'여성' if gender == 'female' else '남성'} 모델."
    sections.append(model_desc)

    # 2. [착장] 섹션 - 가장 중요!
    outfit_section = _build_outfit_section(prompt_json.get("착장", {}))
    if outfit_section:
        sections.append(f"\n[착장]\n{outfit_section}")
    else:
        # 빈 착장 분석 결과 에러 핸들링
        sections.append("\n[착장]\n(착장 정보 없음 - 착장 이미지 참조)")

    # 3. [순간] 섹션 - 자연스러운 동작 묘사
    if include_moment:
        moment_section = _build_moment_section(prompt_json, moment_type)
        sections.append(f"\n[순간]\n{moment_section}")

    # 4. [품질] 섹션 - 인플루언서에서 검증된 품질 지시
    sections.append(QUALITY_SECTION_TEMPLATE)

    return "\n".join(sections)


def _build_outfit_section(outfit_dict: dict) -> str:
    """착장 정보를 한국어 설명으로 변환"""
    if not outfit_dict:
        return ""

    lines = []

    # 카테고리 순서 (시각적 중요도)
    category_order = [
        "아우터",
        "상의",
        "하의",
        "신발",
        "헤드웨어",
        "가방",
        "주얼리",
        "벨트",
    ]

    for category in category_order:
        item_data = outfit_dict.get(category, {})
        if isinstance(item_data, dict):
            prompt_text = item_data.get("프롬프트", "")
            if prompt_text:
                lines.append(f"{prompt_text}.")

    return "\n".join(lines) if lines else ""


def _build_moment_section(prompt_json: dict, moment_type: Optional[str] = None) -> str:
    """순간/동작 묘사 섹션 생성"""
    # 포즈 정보에서 stance 추출
    pose_info = prompt_json.get("포즈", {})
    stance = pose_info.get("stance", "stand")

    # moment_type이 지정되지 않았으면 stance에서 추론
    if moment_type is None:
        if "lean" in stance.lower():
            moment_type = "lean"
        elif "sit" in stance.lower():
            moment_type = "sit"
        elif "walk" in stance.lower():
            moment_type = "walk"
        else:
            moment_type = "stand"

    # 기본 템플릿
    moment_desc = MOMENT_TEMPLATES.get(moment_type, MOMENT_TEMPLATES["stand"])

    # 배경 정보 추가
    background = prompt_json.get("배경", {})
    place = background.get("장소", "")
    if place:
        moment_desc = f"{place}에서 {moment_desc}"

    # 표정 정보 추가
    expression = prompt_json.get("표정", {})
    vibe = expression.get("바이브", "")
    if vibe:
        moment_desc += f"\n{vibe} 분위기의 표정."

    # 브랜드 톤 추가 (MLB 필수)
    moment_desc += "\n패션 매거진 에디토리얼 화보 같은 분위기."
    moment_desc += "\nMLB 'Young & Rich' 컨셉 - 프리미엄하고 자신감 있는 느낌."

    return moment_desc


def enhance_with_korean_layer(
    original_prompt_json: dict,
    include_moment: bool = True,
    moment_type: Optional[str] = None,
) -> dict:
    """
    기존 JSON 프롬프트에 한국어 자연어 레이어 추가

    기존 JSON 구조를 유지하면서 _korean_prompt 필드 추가.
    generator.py에서 이 필드를 우선 사용.

    Args:
        original_prompt_json: 기존 JSON 프롬프트
        include_moment: [순간] 섹션 포함 여부
        moment_type: 순간 타입

    Returns:
        dict: _korean_prompt 필드가 추가된 프롬프트 JSON
    """
    if not original_prompt_json:
        raise ValueError("prompt_json cannot be empty")

    enhanced = original_prompt_json.copy()

    # 한국어 프롬프트 생성
    korean_prompt = build_korean_prompt(
        original_prompt_json,
        include_moment=include_moment,
        moment_type=moment_type,
    )

    # _korean_prompt 필드 추가 (generator.py에서 우선 사용)
    enhanced["_korean_prompt"] = korean_prompt

    return enhanced


__all__ = [
    "build_korean_prompt",
    "enhance_with_korean_layer",
    "QUALITY_SECTION_TEMPLATE",
    "MOMENT_TEMPLATES",
]
