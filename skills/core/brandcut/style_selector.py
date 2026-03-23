"""
MLB Style Reference Selector

프롬프트 JSON 기반으로 가장 적합한 스타일 레퍼런스 이미지 자동 선택.
"""

import random
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image

from .style_index import StyleIndex, get_style_index


# ============================================================
# DEFAULT PATHS
# ============================================================
DEFAULT_INDEX_PATH = "db/mlb_style_index.npz"
DEFAULT_ANALYSIS_PATH = "db/mlb_style_analysis.json"
DEFAULT_STYLE_DIR = "db/mlb_style"


# ============================================================
# STYLE SELECTOR
# ============================================================
class StyleSelector:
    """MLB 스타일 레퍼런스 선택기"""

    def __init__(
        self,
        index_path: str = DEFAULT_INDEX_PATH,
        analysis_path: str = DEFAULT_ANALYSIS_PATH,
        style_dir: str = DEFAULT_STYLE_DIR,
    ):
        """
        Args:
            index_path: 스타일 인덱스 파일 경로
            analysis_path: 분석 결과 JSON 경로
            style_dir: 스타일 이미지 폴더 경로
        """
        self.style_dir = Path(style_dir)
        self._index: Optional[StyleIndex] = None
        self._index_path = index_path
        self._analysis_path = analysis_path

    @property
    def index(self) -> StyleIndex:
        """인덱스 lazy 로드"""
        if self._index is None:
            self._index = get_style_index(self._index_path, self._analysis_path)
        return self._index

    def select(
        self,
        prompt_json: Dict[str, Any],
        top_k: int = 3,
        randomize: bool = True,
    ) -> Optional[Path]:
        """
        프롬프트 JSON에서 가장 적합한 스타일 레퍼런스 선택

        Args:
            prompt_json: 브랜드컷 프롬프트 JSON
            top_k: 후보 수
            randomize: 상위 k개 중 랜덤 선택 여부

        Returns:
            스타일 레퍼런스 이미지 경로 (없으면 None)
        """
        if self.index.vectors is None or len(self.index.vectors) == 0:
            return self._fallback_selection()

        # 유사도 기반 후보 선택
        results = self.index.find_similar_from_prompt(prompt_json, top_k=top_k)

        if not results:
            return self._fallback_selection()

        # 상위 k개 중 선택
        if randomize and len(results) > 1:
            # 유사도 가중 랜덤 선택
            weights = [r[1] for r in results]
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]
                idx = random.choices(range(len(results)), weights=weights, k=1)[0]
                selected = results[idx]
            else:
                selected = results[0]
        else:
            selected = results[0]

        # 경로 검증
        path = Path(selected[2])
        if path.exists():
            return path

        # 상대 경로로 재시도
        for candidate in results:
            path = Path(candidate[2])
            if path.exists():
                return path
            # style_dir 기준 상대 경로
            relative = self.style_dir / path.name
            if relative.exists():
                return relative

        return self._fallback_selection()

    def select_image(
        self,
        prompt_json: Dict[str, Any],
        top_k: int = 3,
    ) -> Optional[Image.Image]:
        """
        스타일 레퍼런스 이미지 반환

        Args:
            prompt_json: 브랜드컷 프롬프트 JSON
            top_k: 후보 수

        Returns:
            PIL.Image 또는 None
        """
        path = self.select(prompt_json, top_k=top_k)
        if path and path.exists():
            try:
                return Image.open(path).convert("RGB")
            except Exception as e:
                print(f"[WARN] Failed to load style reference {path}: {e}")
        return None

    def _fallback_selection(self) -> Optional[Path]:
        """인덱스 없을 때 폴백 - 랜덤 선택"""
        if not self.style_dir.exists():
            return None

        images = list(self.style_dir.glob("*.jpg"))
        images.extend(self.style_dir.glob("*.webp"))
        images.extend(self.style_dir.glob("*.png"))

        if images:
            return random.choice(images)
        return None


# ============================================================
# SINGLETON INSTANCE
# ============================================================
_selector_instance: Optional[StyleSelector] = None


def get_style_selector() -> StyleSelector:
    """싱글톤 StyleSelector 반환"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = StyleSelector()
    return _selector_instance


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================
def select_style_reference(
    prompt_json: Dict[str, Any],
    top_k: int = 3,
) -> Optional[Path]:
    """
    스타일 레퍼런스 선택 (편의 함수)

    Args:
        prompt_json: 브랜드컷 프롬프트 JSON
        top_k: 후보 수

    Returns:
        스타일 레퍼런스 이미지 경로
    """
    selector = get_style_selector()
    return selector.select(prompt_json, top_k=top_k)


def select_style_reference_image(
    prompt_json: Dict[str, Any],
    top_k: int = 3,
) -> Optional[Image.Image]:
    """
    스타일 레퍼런스 이미지 반환 (편의 함수)

    Args:
        prompt_json: 브랜드컷 프롬프트 JSON
        top_k: 후보 수

    Returns:
        PIL.Image 또는 None
    """
    selector = get_style_selector()
    return selector.select_image(prompt_json, top_k=top_k)


# ============================================================
# STYLE REFERENCE INSTRUCTION (T6용)
# ============================================================
STYLE_REFERENCE_INSTRUCTION = """
[STYLE REFERENCE] - MLB Brand Editorial Style:

COPY FROM THIS IMAGE:
- Overall mood and atmosphere (languid, cool, unbothered)
- Skin texture and finish (glossy, dewy, highlighted)
- Expression vibe (slightly parted lips, hooded eyes, intense gaze)
- Accessory styling (hoop earrings, chain necklace if present)
- Editorial fashion photography feel
- Body language and confidence level

DO NOT COPY:
- Face (use FACE REFERENCE instead)
- Outfit/clothing (use OUTFIT REFERENCE instead)
- Exact pose (use POSE REFERENCE if provided)
- Background

MATCH the "Young & Rich" attitude and premium street vibe.
Capture the languid chic aesthetic - bored rich kid energy.
"""
