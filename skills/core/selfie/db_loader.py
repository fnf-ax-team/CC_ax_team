"""
셀카 프리셋 DB 로더

db/presets/ 하위 폴더의 프리셋 JSON 파일들을 로드
- common/pose_presets.json (인플과 공용)
- common/expression_presets.json (인플과 공용)
- selfie/scene_presets.json (셀카 전용)

기능:
- 카테고리별 조회
- 랜덤 선택
- 태그 기반 필터링
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from core.storage import get_json, resolve_path

# DB 파일 경로 (로컬 폴백용)
DB_DIR = Path(__file__).parent.parent.parent / "db"
POSE_PRESETS_PATH = DB_DIR / "presets" / "common" / "pose_presets.json"
SCENE_PRESETS_PATH = DB_DIR / "presets" / "selfie" / "scene_presets.json"
EXPRESSION_PRESETS_PATH = DB_DIR / "presets" / "common" / "expression_presets.json"

# 캐시 (한 번 로드 후 재사용)
_pose_cache: Optional[Dict] = None
_scene_cache: Optional[Dict] = None
_expression_cache: Optional[Dict] = None


def _load_preset_json(relative_path: str, local_fallback: Path) -> Dict:
    """프리셋 JSON 로드 (storage 모듈 우선, 로컬 폴백)"""
    try:
        return get_json(relative_path)
    except FileNotFoundError:
        if local_fallback.exists():
            with open(local_fallback, "r", encoding="utf-8") as f:
                return json.load(f)
        raise


def _load_pose_presets() -> Dict:
    """포즈 프리셋 JSON 로드 (캐싱)"""
    global _pose_cache
    if _pose_cache is None:
        _pose_cache = _load_preset_json(
            "db/presets/common/pose_presets.json", POSE_PRESETS_PATH
        )
    return _pose_cache


def _load_scene_presets() -> Dict:
    """씬 프리셋 JSON 로드 (캐싱)"""
    global _scene_cache
    if _scene_cache is None:
        _scene_cache = _load_preset_json(
            "db/presets/selfie/scene_presets.json", SCENE_PRESETS_PATH
        )
    return _scene_cache


def _load_expression_presets() -> Dict:
    """표정 프리셋 JSON 로드 (캐싱)"""
    global _expression_cache
    if _expression_cache is None:
        _expression_cache = _load_preset_json(
            "db/presets/common/expression_presets.json", EXPRESSION_PRESETS_PATH
        )
    return _expression_cache


def get_pose_categories() -> List[str]:
    """
    포즈 카테고리 목록 반환

    Returns:
        ["전신", "상반신", "앉기", "거울셀피"]
    """
    data = _load_pose_presets()
    return list(data["categories"].keys())


def get_scene_categories() -> List[str]:
    """
    씬(배경) 카테고리 목록 반환

    Returns:
        ["핫플카페", "그래피티", "철문", ...]
    """
    data = _load_scene_presets()
    return list(data["categories"].keys())


def get_expression_categories() -> List[str]:
    """
    표정 카테고리 목록 반환

    Returns:
        ["시크", "러블리"]
    """
    data = _load_expression_presets()
    return list(data["categories"].keys())


def get_poses_by_category(category: str) -> List[Dict]:
    """
    특정 카테고리의 포즈 목록 반환

    Args:
        category: "전신", "상반신", "앉기", "거울셀피"

    Returns:
        포즈 dict 리스트
    """
    data = _load_pose_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown pose category: {category}")
    return data["categories"][category]["poses"]


def get_scenes_by_category(category: str) -> List[Dict]:
    """
    특정 카테고리의 씬 목록 반환

    Args:
        category: "핫플카페", "그래피티", ...

    Returns:
        씬 dict 리스트
    """
    data = _load_scene_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown scene category: {category}")
    return data["categories"][category]["scenes"]


def get_expressions_by_category(category: str) -> List[Dict]:
    """
    특정 카테고리의 표정 목록 반환

    Args:
        category: "시크", "러블리"

    Returns:
        표정 dict 리스트
    """
    data = _load_expression_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown expression category: {category}")
    return data["categories"][category]["expressions"]


def get_pose_by_id(pose_id: str) -> Optional[Dict]:
    """
    포즈 ID로 포즈 조회

    Args:
        pose_id: "전신_01", "거울셀피_03" 등

    Returns:
        포즈 dict 또는 None
    """
    data = _load_pose_presets()
    for category_data in data["categories"].values():
        for pose in category_data["poses"]:
            if pose["id"] == pose_id:
                return pose
    return None


def get_scene_by_id(scene_id: str) -> Optional[Dict]:
    """
    씬 ID로 씬 조회

    Args:
        scene_id: "scene_핫플카페_01" 등

    Returns:
        씬 dict 또는 None
    """
    data = _load_scene_presets()
    for category_data in data["categories"].values():
        for scene in category_data["scenes"]:
            if scene["id"] == scene_id:
                return scene
    return None


def get_expression_by_id(expression_id: str) -> Optional[Dict]:
    """
    표정 ID로 표정 조회

    Args:
        expression_id: "시크_01", "러블리_03" 등

    Returns:
        표정 dict 또는 None
    """
    data = _load_expression_presets()
    for category_data in data["categories"].values():
        for expression in category_data["expressions"]:
            if expression["id"] == expression_id:
                return expression
    return None


def get_pose_category_info(category: str) -> Dict:
    """
    포즈 카테고리 메타 정보 반환

    Returns:
        {
            "count": 21,
            "description": "전신 포즈 - ...",
            "requires": [],
            "supported_stances": ["stand", "walk", ...]
        }
    """
    data = _load_pose_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown pose category: {category}")

    cat_data = data["categories"][category]
    return {
        "count": cat_data["count"],
        "description": cat_data["description"],
        "requires": cat_data.get("requires", []),
        "supported_stances": cat_data.get("supported_stances", []),
    }


def get_scene_category_info(category: str) -> Dict:
    """
    씬 카테고리 메타 정보 반환

    Returns:
        {
            "count": 21,
            "compatible_pose_categories": ["전신", "상반신", ...],
            "blocked_pose_categories": [...],
            "note": "..."
        }
    """
    data = _load_scene_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown scene category: {category}")

    cat_data = data["categories"][category]
    return {
        "count": cat_data["count"],
        "compatible_pose_categories": cat_data.get("compatible_pose_categories", []),
        "blocked_pose_categories": cat_data.get("blocked_pose_categories", []),
        "note": cat_data.get("note", ""),
    }


def get_expression_category_info(category: str) -> Dict:
    """
    표정 카테고리 메타 정보 반환

    Returns:
        {
            "count": 5,
            "description": "시크 표정 - ..."
        }
    """
    data = _load_expression_presets()
    if category not in data["categories"]:
        raise ValueError(f"Unknown expression category: {category}")

    cat_data = data["categories"][category]
    return {
        "count": cat_data["count"],
        "description": cat_data["description"],
    }


def get_random_poses(category: str, count: int = 1) -> List[Dict]:
    """
    카테고리에서 랜덤 포즈 선택 (중복 없이)

    Args:
        category: 포즈 카테고리
        count: 선택할 개수

    Returns:
        포즈 dict 리스트
    """
    poses = get_poses_by_category(category)

    # 요청 개수가 포즈 수보다 많으면 순환
    if count <= len(poses):
        return random.sample(poses, count)
    else:
        result = []
        while len(result) < count:
            remaining = count - len(result)
            sample_size = min(remaining, len(poses))
            result.extend(random.sample(poses, sample_size))
        return result


def get_random_scenes(category: str, count: int = 1) -> List[Dict]:
    """
    카테고리에서 랜덤 씬 선택 (중복 없이)

    Args:
        category: 씬 카테고리
        count: 선택할 개수

    Returns:
        씬 dict 리스트
    """
    scenes = get_scenes_by_category(category)

    # 요청 개수가 씬 수보다 많으면 순환
    if count <= len(scenes):
        return random.sample(scenes, count)
    else:
        result = []
        while len(result) < count:
            remaining = count - len(result)
            sample_size = min(remaining, len(scenes))
            result.extend(random.sample(scenes, sample_size))
        return result


def get_random_expressions(
    category: str = None, count: int = 1, exclude_wink: bool = False
) -> List[Dict]:
    """
    카테고리에서 랜덤 표정 선택 (중복 없이)

    Args:
        category: 표정 카테고리 ("시크", "러블리"). None이면 전체에서 선택
        count: 선택할 개수
        exclude_wink: True면 윙크 표정 제외

    Returns:
        표정 dict 리스트
    """
    if category:
        expressions = get_expressions_by_category(category)
    else:
        # 전체 카테고리에서 선택
        data = _load_expression_presets()
        expressions = []
        for cat_data in data["categories"].values():
            expressions.extend(cat_data["expressions"])

    # 윙크 제외 옵션
    if exclude_wink:
        expressions = [e for e in expressions if not e.get("is_wink", False)]

    # 요청 개수가 표정 수보다 많으면 순환
    if count <= len(expressions):
        return random.sample(expressions, count)
    else:
        result = []
        while len(result) < count:
            remaining = count - len(result)
            sample_size = min(remaining, len(expressions))
            result.extend(random.sample(expressions, sample_size))
        return result


def get_wink_expressions() -> List[Dict]:
    """
    윙크 표정만 반환

    Returns:
        윙크 표정 dict 리스트 (is_wink=True, wink_eye 포함)
    """
    data = _load_expression_presets()
    winks = []
    for cat_data in data["categories"].values():
        for expression in cat_data["expressions"]:
            if expression.get("is_wink", False):
                winks.append(expression)
    return winks


def get_expression_reference_image_path(expression: Dict) -> Optional[str]:
    """
    표정의 레퍼런스 이미지 전체 경로 반환 (S3/로컬 자동 전환)

    Args:
        expression: 표정 dict

    Returns:
        이미지 전체 경로 또는 None
    """
    image_path = expression.get("image_path")
    if not image_path:
        return None

    try:
        resolved = resolve_path(image_path)
        return str(resolved)
    except FileNotFoundError:
        return None


def get_scenes_by_tags(tags: List[str], category: Optional[str] = None) -> List[Dict]:
    """
    태그로 씬 필터링

    Args:
        tags: 검색할 태그 리스트 (OR 조건)
        category: 특정 카테고리로 제한 (선택)

    Returns:
        매칭된 씬 리스트
    """
    data = _load_scene_presets()
    results = []

    categories = [category] if category else data["categories"].keys()

    for cat in categories:
        if cat not in data["categories"]:
            continue
        for scene in data["categories"][cat]["scenes"]:
            scene_tags = scene.get("tags", [])
            # OR 조건: 태그 중 하나라도 매칭되면
            if any(tag.lower() in [t.lower() for t in scene_tags] for tag in tags):
                results.append(scene)

    return results


def get_reference_image_path(scene: Dict) -> Optional[str]:
    """
    씬의 레퍼런스 이미지 전체 경로 반환 (S3/로컬 자동 전환)

    Args:
        scene: 씬 dict

    Returns:
        이미지 전체 경로 또는 None
    """
    ref_image = scene.get("reference_image")
    if not ref_image:
        return None

    # scene_presets.json의 reference_folder 기준
    data = _load_scene_presets()
    ref_folder = data.get("reference_folder", "4. 배경")

    # 1. reference_folder/이미지 경로로 시도
    try:
        resolved = resolve_path(f"{ref_folder}/{ref_image}")
        return str(resolved)
    except FileNotFoundError:
        pass

    # 2. 직접 경로로 시도
    try:
        resolved = resolve_path(ref_image)
        return str(resolved)
    except FileNotFoundError:
        return None


def get_category_summary() -> Dict[str, Dict]:
    """
    모든 카테고리 요약 정보 반환 (UI용)

    Returns:
        {
            "poses": {
                "전신": {"count": 21, "description": "..."},
                ...
            },
            "scenes": {
                "핫플카페": {"count": 21, "compatible_poses": [...]},
                ...
            },
            "expressions": {
                "시크": {"count": 5, "description": "..."},
                ...
            }
        }
    """
    pose_data = _load_pose_presets()
    scene_data = _load_scene_presets()
    expression_data = _load_expression_presets()

    poses_summary = {}
    for cat, data in pose_data["categories"].items():
        poses_summary[cat] = {
            "count": data["count"],
            "description": data["description"],
        }

    scenes_summary = {}
    for cat, data in scene_data["categories"].items():
        scenes_summary[cat] = {
            "count": data["count"],
            "compatible_poses": data.get("compatible_pose_categories", []),
        }

    expressions_summary = {}
    for cat, data in expression_data["categories"].items():
        expressions_summary[cat] = {
            "count": data["count"],
            "description": data["description"],
        }

    return {
        "poses": poses_summary,
        "scenes": scenes_summary,
        "expressions": expressions_summary,
    }


def clear_cache():
    """캐시 초기화 (DB 파일 수정 후 사용)"""
    global _pose_cache, _scene_cache, _expression_cache
    _pose_cache = None
    _scene_cache = None
    _expression_cache = None
