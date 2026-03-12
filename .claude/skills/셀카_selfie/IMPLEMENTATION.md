# 셀카 v2.0 구현 가이드

> core/selfie/ 모듈에 추가해야 할 함수들

---

## 필요한 새 함수들

### 1. 프리셋 로더 (presets.py)

```python
"""
셀카 프리셋 로더 모듈

pose-presets.md, background-presets.md에서 프리셋 텍스트 추출
"""

from pathlib import Path
from typing import Dict, Optional
import re

# 프리셋 파일 경로
SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / "셀카_selfie"
POSE_PRESETS_FILE = SKILL_DIR / "pose-presets.md"
BACKGROUND_PRESETS_FILE = SKILL_DIR / "background-presets.md"

# 캐시
_pose_cache: Dict[str, dict] = {}
_bg_cache: Dict[str, dict] = {}


def load_pose_preset(preset_id: str) -> Optional[dict]:
    """
    포즈 프리셋 로드

    Args:
        preset_id: 프리셋 ID (예: "squat_chin_rest")

    Returns:
        {
            "id": str,
            "category": str,  # fullbody, upperbody, sitting, mirror
            "prompt": str     # 프롬프트 텍스트
        }
        또는 None (프리셋 없음)
    """
    global _pose_cache

    if not _pose_cache:
        _pose_cache = _parse_presets_file(POSE_PRESETS_FILE)

    return _pose_cache.get(preset_id)


def load_background_preset(preset_id: str) -> Optional[dict]:
    """
    배경 프리셋 로드

    Args:
        preset_id: 프리셋 ID (예: "graffiti_character_metal")

    Returns:
        {
            "id": str,
            "category": str,  # cafe, graffiti, shutter, door, street, subway, elevator
            "prompt": str     # 프롬프트 텍스트
        }
        또는 None (프리셋 없음)
    """
    global _bg_cache

    if not _bg_cache:
        _bg_cache = _parse_presets_file(BACKGROUND_PRESETS_FILE)

    return _bg_cache.get(preset_id)


def list_pose_presets() -> Dict[str, list]:
    """
    모든 포즈 프리셋 목록 반환 (카테고리별)

    Returns:
        {"fullbody": ["walk_side_dynamic", ...], "sitting": [...], ...}
    """
    global _pose_cache

    if not _pose_cache:
        _pose_cache = _parse_presets_file(POSE_PRESETS_FILE)

    result = {}
    for preset_id, preset in _pose_cache.items():
        category = preset.get("category", "other")
        if category not in result:
            result[category] = []
        result[category].append(preset_id)

    return result


def list_background_presets() -> Dict[str, list]:
    """
    모든 배경 프리셋 목록 반환 (카테고리별)

    Returns:
        {"cafe": ["cafe_parisian_terrace", ...], "graffiti": [...], ...}
    """
    global _bg_cache

    if not _bg_cache:
        _bg_cache = _parse_presets_file(BACKGROUND_PRESETS_FILE)

    result = {}
    for preset_id, preset in _bg_cache.items():
        category = preset.get("category", "other")
        if category not in result:
            result[category] = []
        result[category].append(preset_id)

    return result


def _parse_presets_file(filepath: Path) -> Dict[str, dict]:
    """
    프리셋 마크다운 파일 파싱

    형식:
    #### preset_id
    > 설명
    ```
    프롬프트 텍스트
    ```
    """
    if not filepath.exists():
        return {}

    content = filepath.read_text(encoding="utf-8")
    presets = {}

    # 현재 카테고리 추적
    current_category = ""

    # 섹션 파싱 (## N. 카테고리명)
    for line in content.split("\n"):
        if line.startswith("## ") and ". " in line:
            # 예: "## 1. 전신 (Fullbody) - 21종"
            match = re.search(r"## \d+\. (.+?) \((\w+)\)", line)
            if match:
                current_category = match.group(2).lower()  # fullbody, sitting 등

    # 프리셋 파싱 (#### preset_id)
    pattern = r"#### (\w+)\n(?:> .+\n)?```\n(.+?)```"
    matches = re.findall(pattern, content, re.DOTALL)

    for preset_id, prompt_text in matches:
        # 카테고리 추론 (프리셋 ID 접두사 기반)
        category = _infer_category(preset_id)

        presets[preset_id] = {
            "id": preset_id,
            "category": category,
            "prompt": prompt_text.strip()
        }

    return presets


def _infer_category(preset_id: str) -> str:
    """프리셋 ID에서 카테고리 추론"""
    if preset_id.startswith("walk_") or preset_id.startswith("lean_") or preset_id.startswith("hip_") or preset_id.startswith("leg_lift_"):
        return "fullbody"
    elif preset_id.startswith("arms_") or preset_id.startswith("props_"):
        return "upperbody"
    elif preset_id.startswith("squat_") or preset_id.startswith("stairs_") or preset_id.startswith("floor_") or preset_id.startswith("bench_"):
        return "sitting"
    elif preset_id.startswith("mirror_"):
        return "mirror"
    elif preset_id.startswith("cafe_"):
        return "cafe"
    elif preset_id.startswith("graffiti_"):
        return "graffiti"
    elif preset_id.startswith("shutter_"):
        return "shutter"
    elif preset_id.startswith("door_"):
        return "door"
    elif preset_id.startswith("street_"):
        return "street"
    elif preset_id.startswith("lifestyle_"):
        return "lifestyle"
    elif preset_id.startswith("subway_"):
        return "subway"
    elif preset_id.startswith("elevator_"):
        return "elevator"
    elif preset_id.startswith("crosswalk_"):
        return "crosswalk"
    else:
        return "other"
```

---

### 2. 프롬프트 빌더 v2 (prompt_builder.py에 추가)

```python
def build_selfie_prompt_v2(
    pose_preset_id: str,
    background_preset_id: str,
    gender: str = "female",
    makeup: str = "natural",
    outfit_analysis: Optional[dict] = None,
    expression: Optional[str] = None,
) -> str:
    """
    프리셋 기반 셀카 프롬프트 생성 (v2.0)

    Args:
        pose_preset_id: 포즈 프리셋 ID
        background_preset_id: 배경 프리셋 ID
        gender: "female" | "male"
        makeup: "bare" | "natural" | "full"
        outfit_analysis: 착장 분석 결과 (선택)
        expression: 표정 (선택) "flirty" | "natural" | "innocent" | "chic"

    Returns:
        조립된 프롬프트 문자열
    """
    from .presets import load_pose_preset, load_background_preset

    parts = ["이 얼굴로"]

    # 1. 성별
    gender_text = PROMPT_OPTIONS["gender"].get(gender, "예쁜 여자")
    parts.append(f"예쁜 한국 {gender_text}")

    # 2. 포즈 프리셋
    pose = load_pose_preset(pose_preset_id)
    if pose:
        parts.append(pose["prompt"])
    else:
        raise ValueError(f"포즈 프리셋을 찾을 수 없음: {pose_preset_id}")

    # 3. 배경 프리셋
    bg = load_background_preset(background_preset_id)
    if bg:
        parts.append(bg["prompt"])
    else:
        raise ValueError(f"배경 프리셋을 찾을 수 없음: {background_preset_id}")

    # 4. 표정 (선택)
    if expression and expression in PROMPT_OPTIONS.get("expression", {}):
        parts.append(PROMPT_OPTIONS["expression"][expression])

    # 5. 메이크업
    if makeup and makeup in PROMPT_OPTIONS.get("makeup", {}):
        parts.append(PROMPT_OPTIONS["makeup"][makeup])

    # 6. 착장 (outfit_analysis 있으면 사용)
    if outfit_analysis and outfit_analysis.get("prompt_text"):
        parts.append(outfit_analysis["prompt_text"])

    # 조립 (포즈/배경은 줄바꿈으로 구분)
    prompt = parts[0] + " " + parts[1] + "\n"
    prompt += parts[2] + "\n"  # 포즈
    prompt += parts[3]         # 배경

    # 나머지는 콤마로 연결
    if len(parts) > 4:
        prompt += "\n" + ", ".join(parts[4:])

    return prompt
```

---

### 3. 생성기 업데이트 (generator.py에 추가)

```python
def generate_with_validation(
    prompt: str,
    face_images: List[str],
    outfit_images: Optional[List[str]] = None,
    pose_reference: Optional[str] = None,      # NEW: 포즈 레퍼런스
    bg_reference: Optional[str] = None,        # NEW: 배경 레퍼런스
    api_key: str = None,
    max_retries: int = 2,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.7,
) -> dict:
    """
    셀카 이미지 생성 + 검증 + 재시도

    Args:
        prompt: 프롬프트 텍스트
        face_images: 얼굴 이미지 경로 리스트
        outfit_images: 착장 이미지 경로 리스트 (선택)
        pose_reference: 포즈 레퍼런스 이미지 경로 (선택)
        bg_reference: 배경 레퍼런스 이미지 경로 (선택)
        api_key: Gemini API 키
        max_retries: 최대 재시도 횟수
        aspect_ratio: 화면 비율
        resolution: 해상도
        temperature: 온도

    Returns:
        {
            "image": PIL.Image,
            "score": float,
            "passed": bool,
            "criteria": dict,
            "attempts": int,
            "history": list
        }
    """
    # ... 기존 로직 + pose_reference, bg_reference 처리 추가
```

---

### 4. __init__.py 업데이트

```python
from .presets import (
    load_pose_preset,
    load_background_preset,
    list_pose_presets,
    list_background_presets,
)
from .prompt_builder import build_selfie_prompt_v2

__all__ = [
    # ... 기존 export
    # Presets (NEW)
    "load_pose_preset",
    "load_background_preset",
    "list_pose_presets",
    "list_background_presets",
    # Prompt builder v2 (NEW)
    "build_selfie_prompt_v2",
]
```

---

## 금지 조합 검증 로직

```python
FORBIDDEN_POSE_BACKGROUND_COMBINATIONS = [
    {
        "pose_pattern": "mirror_*",
        "bg_pattern": ["street_*", "cafe_*", "graffiti_*", "crosswalk_*"],
        "reason": "거울샷은 실내 전용",
        "fix": {"bg": "elevator_mirror_metal"}
    },
    {
        "pose_pattern": "lying_*",
        "bg_pattern": ["street_*", "subway_*", "crosswalk_*"],
        "reason": "눕기 부적합 장소",
        "fix": {"bg": "lifestyle_bookstore"}
    },
    {
        "pose_pattern": "squat_*",
        "bg_pattern": ["elevator_*"],
        "reason": "엘리베이터에서 쪼그리기 부적합",
        "fix": {"bg": "graffiti_character_metal"}
    },
]


def validate_preset_combination(pose_id: str, bg_id: str) -> tuple:
    """
    포즈/배경 프리셋 조합 검증

    Returns:
        (is_valid: bool, fixed_bg_id: Optional[str], reason: Optional[str])
    """
    import fnmatch

    for rule in FORBIDDEN_POSE_BACKGROUND_COMBINATIONS:
        pose_match = fnmatch.fnmatch(pose_id, rule["pose_pattern"])
        bg_match = any(fnmatch.fnmatch(bg_id, p) for p in rule["bg_pattern"])

        if pose_match and bg_match:
            return (False, rule["fix"]["bg"], rule["reason"])

    return (True, None, None)
```

---

## 테스트 코드 예시

```python
# tests/selfie/test_preset_v2.py

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from core.selfie import (
    load_pose_preset,
    load_background_preset,
    build_selfie_prompt_v2,
    generate_with_validation,
)

def test_preset_loading():
    """프리셋 로딩 테스트"""
    pose = load_pose_preset("squat_chin_rest")
    assert pose is not None
    assert "prompt" in pose
    print(f"[OK] Pose preset: {pose['id']}")

    bg = load_background_preset("graffiti_character_metal")
    assert bg is not None
    assert "prompt" in bg
    print(f"[OK] Background preset: {bg['id']}")


def test_prompt_building():
    """프롬프트 빌드 테스트"""
    prompt = build_selfie_prompt_v2(
        pose_preset_id="squat_chin_rest",
        background_preset_id="graffiti_character_metal",
        gender="female",
        makeup="natural",
    )

    assert "이 얼굴로" in prompt
    assert "쪼그려" in prompt  # 포즈 키워드
    assert "철문" in prompt    # 배경 키워드
    print(f"[OK] Generated prompt:\n{prompt}")


if __name__ == "__main__":
    test_preset_loading()
    test_prompt_building()
```

---

## 구현 체크리스트

- [ ] `core/selfie/presets.py` 생성
  - [ ] `load_pose_preset()`
  - [ ] `load_background_preset()`
  - [ ] `list_pose_presets()`
  - [ ] `list_background_presets()`
  - [ ] `_parse_presets_file()`

- [ ] `core/selfie/prompt_builder.py` 업데이트
  - [ ] `build_selfie_prompt_v2()` 추가
  - [ ] `validate_preset_combination()` 추가

- [ ] `core/selfie/generator.py` 업데이트
  - [ ] `pose_reference` 파라미터 추가
  - [ ] `bg_reference` 파라미터 추가

- [ ] `core/selfie/__init__.py` 업데이트
  - [ ] 새 함수들 export

- [ ] 테스트
  - [ ] 프리셋 로딩 테스트
  - [ ] 프롬프트 빌드 테스트
  - [ ] 생성+검증 테스트

---

**버전**: 1.0.0
**작성일**: 2026-02-20
