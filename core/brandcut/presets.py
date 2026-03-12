"""
MLB 브랜드 전용 프리셋 로더

db/presets/brandcut/mlb/ 폴더의 프리셋 JSON 파일들을 로드
- mlb_expression_presets.json (표정)
- mlb_pose_presets.json (포즈)
- mlb_background_presets.json (배경)
- mlb_camera_presets.json (카메라)
- mlb_styling_presets.json (스타일링)
- mlb_model_presets.json (모델)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

from core.storage import get_json, get_image, resolve_path, resolve_image_for_api

# 프리셋 데이터 기본 경로 (로컬 폴백용)
PRESET_BASE_PATH = (
    Path(__file__).parent.parent.parent / "db" / "presets" / "brandcut" / "mlb"
)

# MLB 프리셋 파일 매핑
MLB_PRESET_FILES = {
    "expression": "mlb_expression_presets.json",
    "pose": "mlb_pose_presets.json",
    "background": "mlb_background_presets.json",
    "camera": "mlb_camera_presets.json",
    "styling": "mlb_styling_presets.json",
    "model": "mlb_model_presets.json",
}

# 하위 호환: 이전 경로 상수
MLB_PRESET_BASE_PATH = PRESET_BASE_PATH


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


@lru_cache(maxsize=10)
def _load_mlb_preset_file(preset_type: str) -> Dict:
    """
    MLB 프리셋 파일 로드 (캐싱)

    Args:
        preset_type: 프리셋 타입 (expression, pose, background, camera, styling, model)

    Returns:
        MLB 프리셋 JSON 데이터
    """
    if preset_type not in MLB_PRESET_FILES:
        raise ValueError(
            f"알 수 없는 MLB 프리셋 타입: {preset_type}. "
            f"가능한 값: {list(MLB_PRESET_FILES.keys())}"
        )

    relative = f"db/presets/brandcut/mlb/{MLB_PRESET_FILES[preset_type]}"
    try:
        return get_json(relative)
    except FileNotFoundError:
        file_path = PRESET_BASE_PATH / MLB_PRESET_FILES[preset_type]
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


def get_mlb_preset_image_path(preset_type: str, preset_id: str) -> Optional[str]:
    """
    MLB 프리셋의 레퍼런스 이미지 경로 반환

    Args:
        preset_type: 프리셋 타입 (expression, pose, background)
        preset_id: 프리셋 ID (예: "MLB스탠딩_주머니_01")

    Returns:
        이미지 절대 경로 (없으면 None)
    """
    preset = load_mlb_preset(preset_type, preset_id)
    if not preset:
        return None

    image_path = preset.get("image_path", "")
    if not image_path:
        return None

    # storage 모듈로 이미지 참조 (S3면 URL, 로컬이면 경로)
    relative = image_path.replace("\\", "/")
    try:
        resolved = resolve_image_for_api(relative)
        return str(resolved)
    except FileNotFoundError:
        # 로컬 폴백 (프로젝트 루트 기준)
        project_root = Path(__file__).parent.parent.parent
        abs_path = project_root / relative
        if abs_path.exists():
            return str(abs_path)
        return None


def load_mlb_preset_with_image(preset_type: str, preset_id: str) -> Dict[str, Any]:
    """
    MLB 프리셋 데이터 + PIL 이미지를 함께 반환

    브랜드컷 파이프라인에서 프리셋 ID로 데이터+이미지를 한번에 로드할 때 사용.

    Args:
        preset_type: 프리셋 타입 (pose, expression, background)
        preset_id: 프리셋 ID (예: "MLB스탠딩_주머니_01")

    Returns:
        {"preset": dict, "image": PIL.Image|None, "image_path": str|None}
    """
    from PIL import Image

    preset = load_mlb_preset(preset_type, preset_id)
    if not preset:
        return {"preset": None, "image": None, "image_path": None}

    image_path = get_mlb_preset_image_path(preset_type, preset_id)
    image = None
    if image_path:
        try:
            image = (
                get_image(image_path)
                if image_path.startswith("db")
                else Image.open(image_path).convert("RGB")
            )
        except Exception:
            pass

    return {"preset": preset, "image": image, "image_path": image_path}


def mlb_pose_preset_to_analysis(preset: dict) -> "PoseAnalysisResult":
    """
    MLB 포즈 프리셋 dict -> PoseAnalysisResult 변환

    프리셋 JSON의 중첩 구조(왼팔.설명, 왼팔.팔꿈치각도)를
    PoseAnalysisResult의 flat 필드로 매핑한다.

    Args:
        preset: load_mlb_preset('pose', id)로 얻은 dict

    Returns:
        PoseAnalysisResult 객체 (build_prompt()의 pose_analysis로 전달 가능)
    """
    from core.ai_influencer.pose_analyzer import PoseAnalysisResult

    def _arm(key: str) -> dict:
        v = preset.get(key, {})
        if isinstance(v, str):
            return {"설명": v, "손": "", "팔꿈치각도": "", "팔꿈치방향": ""}
        return v

    def _leg(key: str) -> dict:
        v = preset.get(key, {})
        if isinstance(v, str):
            return {
                "설명": v,
                "무릎각도": "",
                "무릎방향": "",
                "무릎높이": "",
                "발방향": "",
                "발위치": "",
            }
        return v

    def _hip() -> dict:
        v = preset.get("힙", {})
        if isinstance(v, str):
            return {"설명": v, "상체기울기": ""}
        return v

    la = _arm("왼팔")
    ra = _arm("오른팔")
    ll = _leg("왼다리")
    rl = _leg("오른다리")
    hip = _hip()
    camera = preset.get("촬영", {})

    return PoseAnalysisResult(
        stance=preset.get("stance", "stand"),
        # 팔
        left_arm=la.get("설명", ""),
        right_arm=ra.get("설명", ""),
        left_hand=la.get("손", ""),
        right_hand=ra.get("손", ""),
        left_elbow_angle=la.get("팔꿈치각도", ""),
        left_elbow_direction=la.get("팔꿈치방향", ""),
        right_elbow_angle=ra.get("팔꿈치각도", ""),
        right_elbow_direction=ra.get("팔꿈치방향", ""),
        # 다리
        left_leg=ll.get("설명", ""),
        right_leg=rl.get("설명", ""),
        left_knee_angle=ll.get("무릎각도", ""),
        left_knee_direction=ll.get("무릎방향", ""),
        left_knee_height=ll.get("무릎높이", ""),
        left_foot_direction=ll.get("발방향", ""),
        left_foot_position=ll.get("발위치", ""),
        right_knee_angle=rl.get("무릎각도", ""),
        right_knee_direction=rl.get("무릎방향", ""),
        right_knee_height=rl.get("무릎높이", ""),
        right_foot_direction=rl.get("발방향", ""),
        right_foot_position=rl.get("발위치", ""),
        # 힙/상체
        hip=hip.get("설명", ""),
        torso_tilt=hip.get("상체기울기", ""),
        shoulder_line=preset.get("어깨라인", ""),
        # 얼굴/목
        face_direction=preset.get("얼굴방향", ""),
        neck_tilt=preset.get("목기울기", ""),
        head_tilt=preset.get("고개각도", ""),
        # 다리 형태
        bent_leg_shape=preset.get("다리형태", ""),
        # 촬영
        camera_angle=camera.get("앵글", ""),
        camera_height=camera.get("높이", ""),
        framing=camera.get("프레이밍", ""),
        # 메타
        summary=preset.get("한줄요약", ""),
        tags=preset.get("태그", []),
        confidence=0.9,
    )


def reload_mlb_presets():
    """MLB 프리셋 캐시 무효화 (파일 갱신 후 호출)"""
    _load_mlb_preset_file.cache_clear()


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
