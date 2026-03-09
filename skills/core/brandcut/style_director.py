"""
style_director.py

StyleSelector + DirectorAnalysis 통합 모듈.
스타일 레퍼런스 선택 시 해당 director_analysis JSON의 micro-instruction도 함께 반환.
"""

import json
import random
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from .style_selector import StyleSelector, get_style_selector
from .director_to_prompt import (
    director_to_full_prompt,
    convert_camera_to_prompt,
    convert_pose_to_prompt,
    convert_expression_to_prompt,
    convert_composition_to_prompt,
    convert_brand_vibe_to_prompt,
)


# ============================================================
# PATHS
# ============================================================
DEFAULT_DIRECTOR_DIR = Path("db/results/director_analysis")
DEFAULT_STYLE_DIR = Path("db/mlb_style")


# ============================================================
# ANGLE DISTRIBUTION (사용자 피드백 반영)
# ============================================================
# "다양한 앵글 필요. 로우앵글이 주력이지만 100%는 아님"
ANGLE_DISTRIBUTION = {
    "low_angle": 0.65,  # 60-70%
    "eye_level": 0.30,  # 25-35%
    "high_angle": 0.05,  # 5-10%
}

# "풀바디샷(FS)은 10장 중 1장 정도로 제한"
FRAMING_DISTRIBUTION = {
    "MS": 0.45,  # Medium Shot - 허리 위 (가장 많음)
    "MFS": 0.28,  # Medium Full Shot - 무릎 위
    "MCU": 0.17,  # Medium Close-Up - 가슴 위
    "FS": 0.10,  # Full Shot - 전신 (제한적)
}


# ============================================================
# STYLE DIRECTOR CLASS
# ============================================================
class StyleDirector:
    """스타일 레퍼런스 + Director Analysis 통합 매니저"""

    def __init__(
        self,
        style_dir: str | Path = DEFAULT_STYLE_DIR,
        director_dir: str | Path = DEFAULT_DIRECTOR_DIR,
    ):
        """
        Args:
            style_dir: 스타일 이미지 폴더
            director_dir: director_analysis JSON 폴더
        """
        self.style_dir = Path(style_dir)
        self.director_dir = Path(director_dir)
        self._selector = get_style_selector()
        self._director_cache: Dict[str, dict] = {}

    def get_director_for_style(self, style_path: Path) -> Optional[dict]:
        """
        스타일 이미지에 대응하는 director_analysis JSON 로드

        Args:
            style_path: 스타일 이미지 경로 (예: MLB_STYLE_50.webp)

        Returns:
            director_analysis JSON dict 또는 None
        """
        # 캐시 확인
        cache_key = str(style_path)
        if cache_key in self._director_cache:
            return self._director_cache[cache_key]

        # 파일명에서 이미지 번호 추출
        # MLB_STYLE_50.webp -> MLB_STYLE_50.json
        stem = style_path.stem  # MLB_STYLE_50
        json_path = self.director_dir / f"{stem}.json"

        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._director_cache[cache_key] = data
                    return data
            except Exception as e:
                print(f"[WARN] Failed to load director JSON {json_path}: {e}")

        return None

    def select_with_director(
        self,
        prompt_json: Dict[str, Any],
        top_k: int = 5,
        apply_distribution: bool = True,
    ) -> Tuple[Optional[Path], Optional[dict], str]:
        """
        스타일 레퍼런스 선택 + director_analysis + micro-instruction 프롬프트 반환

        Args:
            prompt_json: 브랜드컷 프롬프트 JSON
            top_k: 후보 수
            apply_distribution: 앵글/프레이밍 분포 적용 여부

        Returns:
            (스타일 이미지 경로, director JSON, micro-instruction 프롬프트)
        """
        style_path = self._selector.select(prompt_json, top_k=top_k)

        if style_path is None:
            return None, None, ""

        # director_analysis 로드
        director_json = self.get_director_for_style(style_path)

        if director_json is None:
            # director 없으면 랜덤 선택
            director_json = self._select_random_director(apply_distribution)

        # director JSON이 있으면 micro-instruction 생성
        if director_json:
            # 분포 조정 적용
            if apply_distribution:
                director_json = self._adjust_for_distribution(director_json)

            micro_prompt = self._build_micro_instructions(director_json)
            return style_path, director_json, micro_prompt

        return style_path, None, ""

    def select_diverse_directors(
        self,
        count: int = 5,
        ensure_variety: bool = True,
    ) -> List[Tuple[Optional[Path], dict, str]]:
        """
        다양한 director_analysis 선택 (다양성 보장)

        Args:
            count: 선택할 개수
            ensure_variety: 표정/포즈/앵글 다양성 보장 여부

        Returns:
            [(스타일 경로, director JSON, micro-instruction), ...]
        """
        results = []
        used_expressions = set()
        used_framings = set()

        all_jsons = self._load_all_directors()

        if not all_jsons:
            return results

        # 다양성 보장 선택
        if ensure_variety:
            # 다른 표정/프레이밍 우선 선택
            remaining = list(all_jsons)
            random.shuffle(remaining)

            for director_json in remaining:
                if len(results) >= count:
                    break

                expr = director_json.get("expression", {}).get(
                    "overall_expression", "cool"
                )
                framing = director_json.get("composition", {}).get("framing_type", "MS")

                # 다양성 체크
                if ensure_variety and len(results) > 0:
                    # 이미 같은 표정이 있으면 스킵 (처음 2개까지만 체크)
                    if expr in used_expressions and len(used_expressions) < 3:
                        continue

                used_expressions.add(expr)
                used_framings.add(framing)

                # 분포 조정
                adjusted = self._adjust_for_distribution(director_json)
                micro_prompt = self._build_micro_instructions(adjusted)

                # 스타일 이미지 찾기
                style_path = self._find_style_for_director(director_json)

                results.append((style_path, adjusted, micro_prompt))
        else:
            # 랜덤 선택
            selected = random.sample(all_jsons, min(count, len(all_jsons)))
            for director_json in selected:
                adjusted = self._adjust_for_distribution(director_json)
                micro_prompt = self._build_micro_instructions(adjusted)
                style_path = self._find_style_for_director(director_json)
                results.append((style_path, adjusted, micro_prompt))

        return results

    def _select_random_director(
        self, apply_distribution: bool = True
    ) -> Optional[dict]:
        """분포에 맞는 랜덤 director_analysis 선택"""
        all_jsons = self._load_all_directors()

        if not all_jsons:
            return None

        # 분포 적용 시 필터링
        if apply_distribution:
            # 앵글 분포에 따라 필터
            angle_type = self._sample_from_distribution(ANGLE_DISTRIBUTION)

            filtered = []
            for dj in all_jsons:
                height = dj.get("camera", {}).get("camera_height_cm", 100)
                if angle_type == "low_angle" and height < 50:
                    filtered.append(dj)
                elif angle_type == "eye_level" and 50 <= height <= 150:
                    filtered.append(dj)
                elif angle_type == "high_angle" and height > 150:
                    filtered.append(dj)

            if filtered:
                return random.choice(filtered)

        return random.choice(all_jsons) if all_jsons else None

    def _adjust_for_distribution(self, director_json: dict) -> dict:
        """director_json을 분포 규칙에 맞게 조정"""
        adjusted = director_json.copy()

        # 프레이밍 분포 적용 (풀바디샷 10% 제한)
        if "composition" in adjusted:
            current_framing = adjusted["composition"].get("framing_type", "MS")

            # FS(풀바디샷)인 경우 10% 확률로만 유지
            if current_framing == "FS":
                if random.random() > FRAMING_DISTRIBUTION["FS"]:
                    # 다른 프레이밍으로 변경
                    adjusted["composition"]["framing_type"] = (
                        self._sample_from_distribution(
                            {"MS": 0.50, "MFS": 0.30, "MCU": 0.20}
                        )
                    )

        return adjusted

    def _sample_from_distribution(self, distribution: Dict[str, float]) -> str:
        """분포에서 샘플링"""
        items = list(distribution.keys())
        weights = list(distribution.values())
        return random.choices(items, weights=weights, k=1)[0]

    def _build_micro_instructions(self, director_json: dict) -> str:
        """director JSON에서 micro-instruction 프롬프트 생성"""
        parts = []

        # 카메라/앵글
        camera = director_json.get("camera", {})
        if camera:
            parts.append(convert_camera_to_prompt(camera))

        # 포즈
        pose = director_json.get("pose", {})
        if pose:
            parts.append(convert_pose_to_prompt(pose))

        # 표정
        expression = director_json.get("expression", {})
        if expression:
            parts.append(convert_expression_to_prompt(expression))

        # 구도
        composition = director_json.get("composition", {})
        if composition:
            parts.append(convert_composition_to_prompt(composition))

        return "\n\n".join(parts)

    def _load_all_directors(self) -> List[dict]:
        """모든 director_analysis JSON 로드"""
        all_jsons = []

        if not self.director_dir.exists():
            return all_jsons

        for json_file in self.director_dir.glob("MLB_STYLE_*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_source"] = str(json_file)
                    all_jsons.append(data)
            except Exception as e:
                print(f"[WARN] Failed to load {json_file}: {e}")

        return all_jsons

    def _find_style_for_director(self, director_json: dict) -> Optional[Path]:
        """director JSON에 대응하는 스타일 이미지 찾기"""
        source = director_json.get("_source", "")
        if source:
            # MLB_STYLE_50.json -> MLB_STYLE_50.webp
            stem = Path(source).stem
            for ext in [".webp", ".jpg", ".png"]:
                style_path = self.style_dir / f"{stem}{ext}"
                if style_path.exists():
                    return style_path
        return None


# ============================================================
# SINGLETON INSTANCE
# ============================================================
_director_instance: Optional[StyleDirector] = None


def get_style_director() -> StyleDirector:
    """싱글톤 StyleDirector 반환"""
    global _director_instance
    if _director_instance is None:
        _director_instance = StyleDirector()
    return _director_instance


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================
def select_style_with_director(
    prompt_json: Dict[str, Any],
    top_k: int = 5,
) -> Tuple[Optional[Path], Optional[dict], str]:
    """
    스타일 + director 선택 (편의 함수)

    Returns:
        (스타일 이미지 경로, director JSON, micro-instruction 프롬프트)
    """
    director = get_style_director()
    return director.select_with_director(prompt_json, top_k=top_k)


def get_diverse_micro_instructions(
    count: int = 5,
) -> List[Tuple[Optional[Path], dict, str]]:
    """
    다양한 micro-instruction 세트 반환

    Args:
        count: 필요한 개수

    Returns:
        [(스타일 경로, director JSON, micro-instruction), ...]
    """
    director = get_style_director()
    return director.select_diverse_directors(count=count, ensure_variety=True)


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    import sys

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    print("[TEST] StyleDirector")
    print("=" * 60)

    director = StyleDirector(
        style_dir=project_root / "db" / "mlb_style",
        director_dir=project_root / "db" / "results" / "director_analysis",
    )

    # 테스트 1: 다양한 director 선택
    print("\n[1] Diverse directors selection:")
    results = director.select_diverse_directors(count=5, ensure_variety=True)

    for i, (style_path, dj, micro) in enumerate(results, 1):
        expr = dj.get("expression", {}).get("overall_expression", "?")
        framing = dj.get("composition", {}).get("framing_type", "?")
        height = dj.get("camera", {}).get("camera_height_cm", 0)

        print(f"\n  [{i}] Expression: {expr}, Framing: {framing}, Height: {height}cm")
        print(f"      Style: {style_path.name if style_path else 'None'}")
        print(f"      Micro (first 100 chars): {micro[:100]}...")

    # 테스트 2: 프롬프트 기반 선택
    print("\n\n[2] Prompt-based selection:")
    test_prompt = {
        "pose": {"stance": "confident", "arms": "hand_on_hip"},
        "expression": {"mood": "cool"},
        "camera": {"angle": "low", "framing": "MFS"},
    }

    style_path, dj, micro = director.select_with_director(test_prompt)
    print(f"  Style: {style_path}")
    print(f"  Director keys: {list(dj.keys()) if dj else None}")
    print(f"  Micro length: {len(micro)} chars")
