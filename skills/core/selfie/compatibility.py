"""
포즈-배경 호환성 검증 모듈

pose_presets.json과 scene_presets.json의 호환성 규칙 기반
- 거울셀피는 거울 있는 장소에서만
- 앉기는 횡단보도 불가
- 등등
"""

from typing import List, Dict, Tuple, Optional

from .db_loader import (
    get_pose_category_info,
    get_scene_category_info,
    get_scenes_by_category,
    _load_scene_presets,
)


# ============================================================
# 호환성 규칙 (scene_presets.json의 compatibility_rules 기반)
# ============================================================

# 포즈 카테고리별 차단 배경 카테고리
POSE_BLOCKED_BACKGROUNDS: Dict[str, List[str]] = {
    "거울셀피": ["횡단보도", "그래피티", "해외스트릿"],
    "앉기": ["횡단보도"],
}

# 포즈 카테고리별 허용 배경 카테고리 (명시적 허용)
POSE_ALLOWED_BACKGROUNDS: Dict[str, List[str]] = {
    "거울셀피": ["엘레베이터"],  # 힙라이프는 예외로 처리
    "전신": [],  # 비어있으면 ALL
    "상반신": [],
    "앉기": [],
}

# 특수 예외 (특정 씬만 허용)
SCENE_EXCEPTIONS: Dict[str, Dict[str, List[str]]] = {
    # 포즈 카테고리: {배경 카테고리: [허용되는 씬 ID]}
    "거울셀피": {
        # 지하철: 역사/승강장만 허용 (전동차 내부는 거울 없음)
        # - 허용: 지하철_02(승강장), 지하철_03(입구), 지하철_04(플랫폼),
        #         지하철_07(환승구역/거울), 지하철_09(역사 내부)
        # - 금지: 지하철_05(파리 내부), 지하철_06(일본 내부),
        #         지하철_08(일본 내부), 지하철_10(한국 내부)
        "지하철": [
            "scene_지하철_02",  # 한국 승강장 (역사)
            "scene_지하철_03",  # 뉴욕 역 입구 (역사)
            "scene_지하철_04",  # 뉴욕 승강장 (역사)
            "scene_지하철_07",  # 뉴욕 환승 구역 (역사)
            "scene_지하철_07_mirror",  # 거울 있는 버전
            "scene_지하철_09",  # 뉴욕 역사 내부
        ],
        "힙스트릿라이프스타일": ["scene_힙라이프_05", "scene_힙라이프_05_mirror"],
    }
}


def is_compatible(pose_category: str, scene_category: str) -> bool:
    """
    포즈 카테고리와 씬 카테고리가 호환되는지 확인

    Args:
        pose_category: "전신", "상반신", "앉기", "거울셀피"
        scene_category: "핫플카페", "그래피티", ...

    Returns:
        bool: 호환 여부
    """
    # 1. 차단 목록 확인
    blocked = POSE_BLOCKED_BACKGROUNDS.get(pose_category, [])
    if scene_category in blocked:
        # 예외 확인
        exceptions = SCENE_EXCEPTIONS.get(pose_category, {})
        if scene_category in exceptions:
            # 예외가 있으면 부분 호환 (특정 씬만)
            return True  # 씬 레벨에서 필터링
        return False

    # 2. 허용 목록 확인 (비어있으면 ALL)
    allowed = POSE_ALLOWED_BACKGROUNDS.get(pose_category, [])
    if allowed and scene_category not in allowed:
        # 예외 확인
        exceptions = SCENE_EXCEPTIONS.get(pose_category, {})
        if scene_category in exceptions:
            return True
        return False

    # 3. 씬 카테고리의 호환 포즈 확인
    try:
        scene_info = get_scene_category_info(scene_category)
        compatible_poses = scene_info.get("compatible_pose_categories", [])
        if compatible_poses and pose_category not in compatible_poses:
            return False
    except ValueError:
        pass

    return True


def get_compatible_scene_categories(pose_category: str) -> List[str]:
    """
    포즈 카테고리와 호환되는 씬 카테고리 목록 반환

    Args:
        pose_category: "전신", "상반신", "앉기", "거울셀피"

    Returns:
        호환되는 씬 카테고리 리스트
    """
    data = _load_scene_presets()
    all_categories = list(data["categories"].keys())

    compatible = []
    for scene_cat in all_categories:
        if is_compatible(pose_category, scene_cat):
            compatible.append(scene_cat)

    return compatible


def get_compatible_scenes(pose_category: str, scene_category: str) -> List[Dict]:
    """
    포즈 카테고리와 호환되는 씬 목록 반환 (예외 처리 포함)

    Args:
        pose_category: 포즈 카테고리
        scene_category: 씬 카테고리

    Returns:
        호환되는 씬 리스트
    """
    if not is_compatible(pose_category, scene_category):
        return []

    all_scenes = get_scenes_by_category(scene_category)

    # 예외 확인
    exceptions = SCENE_EXCEPTIONS.get(pose_category, {})
    if scene_category in exceptions:
        # 예외 씬만 반환
        allowed_ids = exceptions[scene_category]
        return [s for s in all_scenes if s["id"] in allowed_ids]

    return all_scenes


def filter_compatible_combinations(
    pose_category: str,
    scene_category: str,
    poses: List[Dict],
    scenes: List[Dict],
) -> List[Tuple[Dict, Dict]]:
    """
    포즈와 씬의 호환되는 조합만 필터링

    Args:
        pose_category: 포즈 카테고리
        scene_category: 씬 카테고리
        poses: 포즈 리스트
        scenes: 씬 리스트

    Returns:
        (pose, scene) 튜플 리스트
    """
    compatible_scenes = get_compatible_scenes(pose_category, scene_category)

    if not compatible_scenes:
        return []

    combinations = []
    for pose in poses:
        for scene in compatible_scenes:
            # 씬의 suggested_stance와 포즈의 stance 매칭 확인
            scene_stance = scene.get("suggested_stance")
            pose_stance = pose.get("stance")

            # stance 매칭 (선택적 - 엄격하게 하려면 주석 해제)
            # if scene_stance and pose_stance and scene_stance != pose_stance:
            #     continue

            combinations.append((pose, scene))

    return combinations


def validate_combination(pose: Dict, scene: Dict) -> Tuple[bool, str]:
    """
    단일 포즈-씬 조합 검증

    Args:
        pose: 포즈 dict
        scene: 씬 dict

    Returns:
        (valid, reason)
    """
    pose_id = pose.get("id", "")
    scene_id = scene.get("id", "")

    # 포즈 카테고리 추출 (전신_01 -> 전신)
    pose_category = pose_id.split("_")[0] if "_" in pose_id else ""

    # 씬 카테고리 추출 (scene_핫플카페_01 -> 핫플카페)
    scene_parts = scene_id.split("_")
    scene_category = scene_parts[1] if len(scene_parts) > 1 else ""

    # 기본 호환성 확인
    if not is_compatible(pose_category, scene_category):
        return False, f"{pose_category} 포즈는 {scene_category} 배경에서 사용 불가"

    # 거울셀피 + 거울 없는 장소
    if pose_category == "거울셀피":
        scene_provides = scene.get("provides", [])
        if "mirror" not in scene_provides and scene_category not in ["엘레베이터"]:
            # 예외 확인
            exceptions = SCENE_EXCEPTIONS.get("거울셀피", {})
            allowed_scenes = exceptions.get(scene_category, [])
            if scene_id not in allowed_scenes:
                return False, "거울셀피는 거울이 있는 장소에서만 가능"

    # stance 불일치 (경고만)
    scene_stance = scene.get("suggested_stance")
    pose_stance = pose.get("stance")
    if scene_stance and pose_stance and scene_stance != pose_stance:
        # 경고만 (실패는 아님)
        pass

    return True, "OK"


def get_compatibility_summary() -> Dict:
    """
    전체 호환성 요약 정보 (UI용)

    Returns:
        {
            "전신": ["핫플카페", "그래피티", ...],
            "거울셀피": ["엘레베이터", ...],
            ...
        }
    """
    pose_categories = ["전신", "상반신", "앉기", "거울셀피"]

    summary = {}
    for pose_cat in pose_categories:
        compatible = get_compatible_scene_categories(pose_cat)
        summary[pose_cat] = {
            "compatible_backgrounds": compatible,
            "count": len(compatible),
        }

    return summary


def format_compatibility_for_user(pose_category: str) -> str:
    """
    사용자에게 보여줄 호환성 정보 포맷팅

    Args:
        pose_category: 포즈 카테고리

    Returns:
        포맷팅된 문자열
    """
    compatible = get_compatible_scene_categories(pose_category)

    lines = [f"[{pose_category}] 호환 배경 카테고리:"]
    for cat in compatible:
        try:
            info = get_scene_category_info(cat)
            count = info.get("count", "?")
            lines.append(f"  - {cat} ({count}개)")
        except ValueError:
            lines.append(f"  - {cat}")

    # 특수 예외 안내
    exceptions = SCENE_EXCEPTIONS.get(pose_category, {})
    if exceptions:
        lines.append("\n[예외]")
        for scene_cat, scene_ids in exceptions.items():
            lines.append(f"  - {scene_cat}: {len(scene_ids)}개 씬만 가능")

    return "\n".join(lines)
