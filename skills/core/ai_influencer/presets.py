"""
AI 인플루언서 프리셋 로더

db/ 폴더의 프리셋 JSON 파일들을 로드
- expression_presets.json (표정)
- pose_presets.json (포즈)
- camera_presets.json (촬영 세팅)
- background_presets.json (배경)
- styling_preset_db.json (스타일링)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

# 프리셋 데이터 기본 경로
PRESET_BASE_PATH = Path(__file__).parent.parent.parent / "db"

# 프리셋 파일 매핑
PRESET_FILES = {
    "expression": "expression_presets.json",
    "pose": "pose_presets.json",
    "camera": "camera_presets.json",
    "background": "background_presets.json",
    "styling": "styling_preset_db.json",
}


@lru_cache(maxsize=10)
def _load_preset_file(preset_type: str) -> Dict:
    """
    프리셋 파일 로드 (캐싱)

    Args:
        preset_type: 프리셋 타입 (expression, pose, camera, background, styling)

    Returns:
        프리셋 JSON 데이터
    """
    if preset_type not in PRESET_FILES:
        raise ValueError(
            f"알 수 없는 프리셋 타입: {preset_type}. 가능한 값: {list(PRESET_FILES.keys())}"
        )

    file_path = PRESET_BASE_PATH / PRESET_FILES[preset_type]
    if not file_path.exists():
        raise FileNotFoundError(f"프리셋 파일 없음: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_preset_categories(preset_type: str) -> List[str]:
    """
    프리셋 카테고리 목록 반환

    Args:
        preset_type: 프리셋 타입

    Returns:
        카테고리 이름 목록
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    return list(categories.keys())


def list_presets(preset_type: str, category: str = None) -> List[str]:
    """
    프리셋 ID 목록 반환

    Args:
        preset_type: 프리셋 타입
        category: 카테고리 (None이면 전체)

    Returns:
        프리셋 ID 목록
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})

    preset_ids = []

    # 카테고리 내 프리셋 키 결정 (파일마다 다름)
    preset_key = _get_preset_key(preset_type)

    if category:
        # 특정 카테고리만
        if category not in categories:
            return []
        items = categories[category].get(preset_key, [])
        for item in items:
            preset_ids.append(item.get("id", ""))
    else:
        # 전체 카테고리
        for cat_name, cat_data in categories.items():
            items = cat_data.get(preset_key, [])
            for item in items:
                preset_ids.append(item.get("id", ""))

    return [pid for pid in preset_ids if pid]


def _get_preset_key(preset_type: str) -> str:
    """프리셋 타입별 아이템 키 반환"""
    key_mapping = {
        "expression": "expressions",
        "pose": "poses",
        "camera": "settings",
        "background": "backgrounds",
        "styling": "styles",
    }
    return key_mapping.get(preset_type, "items")


def load_preset(preset_type: str, preset_id: str) -> Optional[Dict[str, Any]]:
    """
    특정 프리셋 로드

    Args:
        preset_type: 프리셋 타입
        preset_id: 프리셋 ID (예: "시크_02", "전신_05")

    Returns:
        프리셋 데이터 dict (없으면 None)
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    for cat_name, cat_data in categories.items():
        items = cat_data.get(preset_key, [])
        for item in items:
            if item.get("id") == preset_id:
                # 카테고리 정보 추가
                result = item.copy()
                result["_category"] = cat_name
                return result

    return None


def get_preset_with_description(preset_type: str, preset_id: str) -> Dict[str, Any]:
    """
    프리셋 데이터 + 카테고리 설명 포함

    Args:
        preset_type: 프리셋 타입
        preset_id: 프리셋 ID

    Returns:
        프리셋 데이터 + 카테고리 정보
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    for cat_name, cat_data in categories.items():
        items = cat_data.get(preset_key, [])
        for item in items:
            if item.get("id") == preset_id:
                return {
                    "preset": item,
                    "category": cat_name,
                    "category_description": cat_data.get("description", ""),
                }

    return {"preset": None, "category": None, "category_description": None}


def get_camera_preset_for_pose(pose_preset_id: str) -> Optional[Dict[str, Any]]:
    """
    포즈 프리셋과 매칭되는 카메라 프리셋 로드

    스키마에 따르면 촬영_세팅.preset_id는 포즈 preset_id와 1:1 매칭

    Args:
        pose_preset_id: 포즈 프리셋 ID

    Returns:
        카메라 프리셋 데이터
    """
    return load_preset("camera", pose_preset_id)


def format_preset_options(preset_type: str, category: str = None) -> str:
    """
    사용자에게 보여줄 프리셋 옵션 포맷

    Args:
        preset_type: 프리셋 타입
        category: 카테고리 (None이면 전체)

    Returns:
        포맷된 문자열
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    lines = []

    if category:
        cats_to_show = {category: categories.get(category, {})}
    else:
        cats_to_show = categories

    for cat_name, cat_data in cats_to_show.items():
        lines.append(f"\n## {cat_name}")
        if cat_data.get("description"):
            lines.append(f"_{cat_data['description']}_")
        lines.append("")

        items = cat_data.get(preset_key, [])
        for item in items:
            item_id = item.get("id", "")
            note = item.get("note", "")
            if note:
                lines.append(f"- **{item_id}**: {note}")
            else:
                lines.append(f"- **{item_id}**")

    return "\n".join(lines)


def search_presets(preset_type: str, keyword: str) -> List[Dict[str, Any]]:
    """
    키워드로 프리셋 검색

    Args:
        preset_type: 프리셋 타입
        keyword: 검색 키워드

    Returns:
        매칭된 프리셋 목록
    """
    data = _load_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    results = []
    keyword_lower = keyword.lower()

    for cat_name, cat_data in categories.items():
        items = cat_data.get(preset_key, [])
        for item in items:
            # ID, note, 또는 다른 필드에서 검색
            item_str = json.dumps(item, ensure_ascii=False).lower()
            if keyword_lower in item_str:
                result = item.copy()
                result["_category"] = cat_name
                results.append(result)

    return results


# ============================================================
# MLB 브랜드 전용 프리셋 로더
# ============================================================

MLB_PRESET_BASE_PATH = PRESET_BASE_PATH / "mlb_style"

MLB_PRESET_FILES = {
    "expression": "mlb_expression_presets.json",
    "pose": "mlb_pose_presets.json",
    "background": "mlb_background_presets.json",
    "camera": "mlb_camera_presets.json",
}


@lru_cache(maxsize=10)
def _load_mlb_preset_file(preset_type: str) -> Dict:
    """
    MLB 프리셋 파일 로드 (캐싱)

    Args:
        preset_type: 프리셋 타입 (expression, pose, background, camera)

    Returns:
        MLB 프리셋 JSON 데이터
    """
    if preset_type not in MLB_PRESET_FILES:
        raise ValueError(
            f"알 수 없는 MLB 프리셋 타입: {preset_type}. "
            f"가능한 값: {list(MLB_PRESET_FILES.keys())}"
        )

    file_path = MLB_PRESET_BASE_PATH / MLB_PRESET_FILES[preset_type]
    if not file_path.exists():
        raise FileNotFoundError(f"MLB 프리셋 파일 없음: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_mlb_preset(preset_type: str, preset_id: str) -> Optional[Dict[str, Any]]:
    """
    MLB 특정 프리셋 로드

    Args:
        preset_type: 프리셋 타입 (expression, pose, background, camera)
        preset_id: 프리셋 ID (예: "MLB시크_01")

    Returns:
        프리셋 데이터 dict (없으면 None)
    """
    data = _load_mlb_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    for cat_name, cat_data in categories.items():
        items = cat_data.get(preset_key, [])
        for item in items:
            if item.get("id") == preset_id:
                result = item.copy()
                result["_category"] = cat_name
                return result

    return None


def list_mlb_presets(preset_type: str, category: str = None) -> List[str]:
    """
    MLB 프리셋 ID 목록 반환

    Args:
        preset_type: 프리셋 타입
        category: 카테고리 (None이면 전체)

    Returns:
        프리셋 ID 목록
    """
    data = _load_mlb_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    preset_ids = []

    if category:
        if category not in categories:
            return []
        items = categories[category].get(preset_key, [])
        for item in items:
            preset_ids.append(item.get("id", ""))
    else:
        for cat_name, cat_data in categories.items():
            items = cat_data.get(preset_key, [])
            for item in items:
                preset_ids.append(item.get("id", ""))

    return [pid for pid in preset_ids if pid]


def search_mlb_presets(preset_type: str, keyword: str) -> List[Dict[str, Any]]:
    """
    MLB 프리셋 키워드 검색

    Args:
        preset_type: 프리셋 타입
        keyword: 검색 키워드

    Returns:
        매칭된 프리셋 목록
    """
    data = _load_mlb_preset_file(preset_type)
    categories = data.get("categories", {})
    preset_key = _get_preset_key(preset_type)

    results = []
    keyword_lower = keyword.lower()

    for cat_name, cat_data in categories.items():
        items = cat_data.get(preset_key, [])
        for item in items:
            item_str = json.dumps(item, ensure_ascii=False).lower()
            if keyword_lower in item_str:
                result = item.copy()
                result["_category"] = cat_name
                results.append(result)

    return results
