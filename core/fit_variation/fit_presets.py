"""
핏 프리셋 로더

db/fit_presets.json에서 핏 프리셋 데이터를 로드한다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


# 프리셋 파일 경로
_PRESET_FILE = Path(__file__).parent.parent.parent / "db" / "fit_presets.json"

# 캐시
_cache: Optional[Dict] = None


def _load_presets() -> Dict:
    """프리셋 파일 로드 (캐싱)"""
    global _cache
    if _cache is None:
        with open(_PRESET_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


@dataclass
class FitPreset:
    """핏 프리셋 데이터"""

    id: str
    name_kr: str
    name_en: str
    silhouette: str
    thigh: str
    knee: str
    calf: str
    hem_width: str
    rise: str
    keywords: List[str]
    negative: List[str]


@dataclass
class DisplayMode:
    """디스플레이 모드 데이터"""

    id: str
    name_kr: str
    description: str
    prompt_hint: str


def load_fit_preset(preset_id: str) -> FitPreset:
    """핏 프리셋 로드

    Args:
        preset_id: 프리셋 ID (예: "skinny", "wide", "tapered")

    Returns:
        FitPreset 객체

    Raises:
        KeyError: 존재하지 않는 프리셋
    """
    data = _load_presets()
    presets = data["presets"]

    if preset_id not in presets:
        available = list(presets.keys())
        raise KeyError(f"Unknown fit preset: '{preset_id}'. Available: {available}")

    p = presets[preset_id]
    return FitPreset(
        id=preset_id,
        name_kr=p["name_kr"],
        name_en=p["name_en"],
        silhouette=p["silhouette"],
        thigh=p["thigh"],
        knee=p["knee"],
        calf=p["calf"],
        hem_width=p["hem_width"],
        rise=p["rise"],
        keywords=p["keywords"],
        negative=p["negative"],
    )


def list_fit_presets() -> List[Dict[str, str]]:
    """모든 핏 프리셋 목록 반환

    Returns:
        [{"id": "skinny", "name_kr": "스키니", "name_en": "Skinny"}, ...]
    """
    data = _load_presets()
    return [
        {"id": k, "name_kr": v["name_kr"], "name_en": v["name_en"]}
        for k, v in data["presets"].items()
    ]


def get_display_mode(mode_id: str) -> DisplayMode:
    """디스플레이 모드 로드

    Args:
        mode_id: 모드 ID ("flatlay", "hanger", "model_wearing")

    Returns:
        DisplayMode 객체

    Raises:
        KeyError: 존재하지 않는 모드
    """
    data = _load_presets()
    modes = data["display_modes"]

    if mode_id not in modes:
        available = list(modes.keys())
        raise KeyError(f"Unknown display mode: '{mode_id}'. Available: {available}")

    m = modes[mode_id]
    return DisplayMode(
        id=mode_id,
        name_kr=m["name_kr"],
        description=m["description"],
        prompt_hint=m["prompt_hint"],
    )


def list_display_modes() -> List[Dict[str, str]]:
    """모든 디스플레이 모드 목록 반환"""
    data = _load_presets()
    return [
        {"id": k, "name_kr": v["name_kr"], "description": v["description"]}
        for k, v in data["display_modes"].items()
    ]
