"""
AI 인플루언서 Mode 2: 랜덤 프리셋 선택기

카테고리 기반으로 포즈, 표정, 배경 프리셋을 랜덤 선택
- "핫플 카페에서 알아서 해줘" → 해당 배경 카테고리에서 랜덤 선택
"""

import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from .presets import (
    _load_preset_file,
    _get_preset_key,
    load_preset,
    get_preset_categories,
)


# ============================================================
# 카테고리 별칭 매핑 (사용자 입력 → 실제 카테고리명)
# ============================================================

BACKGROUND_ALIASES = {
    # 핫플카페
    "핫플": "핫플카페",
    "카페": "핫플카페",
    "핫플카페": "핫플카페",
    "브런치": "핫플카페",
    "커피숍": "핫플카페",
    # 그래피티
    "그래피티": "그래피티",
    "벽화": "그래피티",
    "스트릿아트": "그래피티",
    # 철문
    "철문": "철문",
    "셔터": "철문",
    "인더스트리얼": "철문",
    # 기타문
    "문": "기타문",
    "기타문": "기타문",
    "유럽문": "기타문",
    "빈티지문": "기타문",
    # 해외스트릿
    "해외": "해외스트릿",
    "해외스트릿": "해외스트릿",
    "런던": "해외스트릿",
    "파리": "해외스트릿",
    "뉴욕": "해외스트릿",
    # 힙스트릿라이프스타일
    "힙": "힙스트릿라이프스타일",
    "힙스트릿": "힙스트릿라이프스타일",
    "힙라이프": "힙스트릿라이프스타일",
    "레코드샵": "힙스트릿라이프스타일",
    "서점": "힙스트릿라이프스타일",
    # 지하철
    "지하철": "지하철",
    "메트로": "지하철",
    "서브웨이": "지하철",
    # 엘레베이터
    "엘레베이터": "엘레베이터",
    "엘베": "엘레베이터",
    "미러셀카": "엘레베이터",
    # 횡단보도
    "횡단보도": "횡단보도",
    "거리": "횡단보도",
}

POSE_ALIASES = {
    # 전신
    "전신": "전신",
    "풀샷": "전신",
    "풀바디": "전신",
    # 상반신
    "상반신": "상반신",
    "버스트샷": "상반신",
    "상체": "상반신",
    # 앉기
    "앉기": "앉기",
    "앉은": "앉기",
    "시팅": "앉기",
    # 거울셀피
    "거울셀피": "거울셀피",
    "미러셀피": "거울셀피",
    "셀피": "거울셀피",
}

EXPRESSION_ALIASES = {
    # 시크
    "시크": "시크",
    "쿨": "시크",
    "도도": "시크",
    "차가운": "시크",
    # 러블리
    "러블리": "러블리",
    "사랑스러운": "러블리",
    "귀여운": "러블리",
    "발랄": "러블리",
}


# ============================================================
# 랜덤 선택 함수
# ============================================================


def resolve_category(
    alias: str, alias_map: Dict[str, str], preset_type: str
) -> Optional[str]:
    """
    사용자 입력(별칭)을 실제 카테고리명으로 변환

    Args:
        alias: 사용자 입력 (예: "핫플", "카페")
        alias_map: 별칭 → 카테고리 매핑
        preset_type: 프리셋 타입 (확인용)

    Returns:
        실제 카테고리명 또는 None
    """
    # 정확히 매칭
    if alias in alias_map:
        return alias_map[alias]

    # 부분 매칭 (포함 검색)
    alias_lower = alias.lower()
    for key, value in alias_map.items():
        if alias_lower in key.lower() or key.lower() in alias_lower:
            return value

    # 카테고리 목록에서 직접 검색
    categories = get_preset_categories(preset_type)
    for cat in categories:
        if alias_lower in cat.lower() or cat.lower() in alias_lower:
            return cat

    return None


def get_random_presets_from_category(
    preset_type: str, category: str, count: int = 1
) -> List[Dict[str, Any]]:
    """
    특정 카테고리에서 랜덤으로 프리셋 선택

    Args:
        preset_type: "pose", "expression", "background"
        category: 카테고리명
        count: 선택할 개수

    Returns:
        선택된 프리셋 목록 (image_path 포함)
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    if category not in categories:
        return []

    items = categories[category].get(preset_key, [])
    if not items:
        return []

    # 이미지 경로가 있는 프리셋만 필터링
    valid_items = [item for item in items if item.get("image_path")]

    if not valid_items:
        # 이미지 없어도 반환 (프롬프트 생성용)
        valid_items = items

    # 랜덤 선택 (중복 없이)
    count = min(count, len(valid_items))
    selected = random.sample(valid_items, count)

    # 카테고리 정보 추가
    for item in selected:
        item["_category"] = category

    return selected


def select_random_combination(
    background_category: str,
    pose_category: Optional[str] = None,
    expression_category: Optional[str] = None,
    count: int = 1,
) -> List[Dict[str, Any]]:
    """
    배경 카테고리 기반으로 호환되는 포즈/표정 조합 선택

    Args:
        background_category: 배경 카테고리 (필수)
        pose_category: 포즈 카테고리 (None이면 호환되는 것 중 랜덤)
        expression_category: 표정 카테고리 (None이면 랜덤)
        count: 생성할 조합 수

    Returns:
        조합 목록 [{"pose": {...}, "expression": {...}, "background": {...}}, ...]
    """
    # 1. 배경 카테고리 해석
    bg_cat = resolve_category(background_category, BACKGROUND_ALIASES, "background")
    if not bg_cat:
        raise ValueError(f"알 수 없는 배경 카테고리: {background_category}")

    # 2. 배경 정보에서 지원 포즈 확인
    data = _load_preset_file("background")
    bg_category_data = data["categories"].get(bg_cat, {})
    supported_stances = bg_category_data.get("supported_stances", [])
    provides = bg_category_data.get("provides", [])

    # 3. 포즈 카테고리 결정
    if pose_category:
        pose_cat = resolve_category(pose_category, POSE_ALIASES, "pose")
    else:
        # 호환되는 포즈 카테고리 자동 선택
        pose_cat = _select_compatible_pose_category(supported_stances, provides)

    # 4. 표정 카테고리 결정
    if expression_category:
        expr_cat = resolve_category(
            expression_category, EXPRESSION_ALIASES, "expression"
        )
    else:
        # 랜덤 선택
        expr_categories = get_preset_categories("expression")
        expr_cat = random.choice(expr_categories)

    # 5. 랜덤 선택 (중복 조합 허용)
    combinations = []
    for _ in range(count):
        bg = get_random_presets_from_category("background", bg_cat, 1)[0]
        pose = get_random_presets_from_category("pose", pose_cat, 1)[0]
        expr = get_random_presets_from_category("expression", expr_cat, 1)[0]

        combinations.append(
            {
                "background": bg,
                "pose": pose,
                "expression": expr,
            }
        )

    return combinations


def _select_compatible_pose_category(
    supported_stances: List[str], provides: List[str]
) -> str:
    """배경의 지원 stance/provides에 맞는 포즈 카테고리 선택"""

    # stance → 포즈 카테고리 매핑
    stance_to_pose = {
        "stand": ["전신", "상반신"],
        "walk": ["전신"],
        "sit": ["앉기"],
        "lean_wall": ["전신", "상반신"],
        "lean": ["전신", "상반신"],
        "kneel": ["거울셀피"],
    }

    # provides → 포즈 카테고리 매핑
    provides_to_pose = {
        "mirror": ["거울셀피"],
        "seating": ["앉기", "전신"],
        "rail": ["전신", "상반신"],
    }

    candidates = set()

    # stance 기반 후보
    for stance in supported_stances:
        if stance in stance_to_pose:
            candidates.update(stance_to_pose[stance])

    # provides 기반 가중치
    for provide in provides:
        if provide in provides_to_pose:
            # mirror가 있으면 거울셀피 우선
            if provide == "mirror":
                return "거울셀피"
            candidates.update(provides_to_pose[provide])

    # 후보가 없으면 기본값
    if not candidates:
        candidates = {"전신", "상반신"}

    return random.choice(list(candidates))


# ============================================================
# 카테고리 안내 함수
# ============================================================


def get_available_categories() -> Dict[str, List[str]]:
    """사용 가능한 모든 카테고리 목록 반환"""
    return {
        "background": get_preset_categories("background"),
        "pose": get_preset_categories("pose"),
        "expression": get_preset_categories("expression"),
    }


def format_category_options() -> str:
    """사용자에게 보여줄 카테고리 옵션 포맷"""
    cats = get_available_categories()

    lines = [
        "## 사용 가능한 카테고리",
        "",
        "### 배경 (필수 선택)",
    ]

    # 배경 카테고리와 설명
    bg_data = _load_preset_file("background")
    for cat_name, cat_data in bg_data["categories"].items():
        desc = cat_data.get("description", "")
        count = cat_data.get("count", 0)
        lines.append(f"- **{cat_name}** ({count}개): {desc}")

    lines.append("")
    lines.append("### 포즈 (선택 - 미선택시 호환되는 것 자동 선택)")

    pose_data = _load_preset_file("pose")
    for cat_name, cat_data in pose_data["categories"].items():
        desc = cat_data.get("description", "")
        count = cat_data.get("count", 0)
        lines.append(f"- **{cat_name}** ({count}개): {desc}")

    lines.append("")
    lines.append("### 표정 (선택 - 미선택시 랜덤)")

    expr_data = _load_preset_file("expression")
    for cat_name, cat_data in expr_data["categories"].items():
        desc = cat_data.get("description", "")
        count = cat_data.get("count", 0)
        lines.append(f"- **{cat_name}** ({count}개): {desc}")

    return "\n".join(lines)


# ============================================================
# Mode 2 메인 함수
# ============================================================


def generate_mode2_selections(
    user_request: str,
    count: int = 1,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    사용자 요청에서 카테고리를 파싱하고 랜덤 조합 생성

    Args:
        user_request: 사용자 요청 (예: "핫플 카페에서 시크하게")
        count: 생성할 이미지 수

    Returns:
        (조합 목록, 파싱 결과)
    """
    # 카테고리 파싱
    parsed = _parse_user_request(user_request)

    if not parsed.get("background"):
        raise ValueError(
            f"배경 카테고리를 인식할 수 없습니다: '{user_request}'\n"
            f"사용 가능한 배경: {', '.join(get_preset_categories('background'))}"
        )

    combinations = select_random_combination(
        background_category=parsed["background"],
        pose_category=parsed.get("pose"),
        expression_category=parsed.get("expression"),
        count=count,
    )

    return combinations, parsed


def _parse_user_request(user_request: str) -> Dict[str, Optional[str]]:
    """사용자 요청에서 카테고리 키워드 추출"""
    result = {
        "background": None,
        "pose": None,
        "expression": None,
    }

    request_lower = user_request.lower()

    # 배경 키워드 검색
    for keyword, category in BACKGROUND_ALIASES.items():
        if keyword in user_request:
            result["background"] = category
            break

    # 포즈 키워드 검색
    for keyword, category in POSE_ALIASES.items():
        if keyword in user_request:
            result["pose"] = category
            break

    # 표정 키워드 검색
    for keyword, category in EXPRESSION_ALIASES.items():
        if keyword in user_request:
            result["expression"] = category
            break

    return result
