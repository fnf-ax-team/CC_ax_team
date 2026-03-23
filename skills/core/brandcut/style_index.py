"""
MLB Style Index - VLM Categorical Encoding 기반 유사도 인덱스

numpy + scipy만 사용 (FAISS 미사용 - 176개 이미지는 소규모)
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from scipy.spatial.distance import cosine


# ============================================================
# CATEGORICAL ENCODING CONSTANTS
# ============================================================
# 플랜 T3 기반: VLM Categorical Encoding → one-hot 벡터 (~50차원)

ARM_POSITIONS = [
    "hand_on_hip",
    "hand_on_hat",
    "arms_relaxed",
    "holding_bag",
    "arms_crossed",
    "hand_in_pocket",
    "touching_hair",
]

STANCES = ["confident", "relaxed", "lean", "seated"]

MOUTH_TYPES = ["closed", "parted", "subtle_smile"]

EYE_TYPES = ["direct", "past", "side", "hooded"]

SKIN_FINISHES = ["matte", "dewy", "glossy"]

HIGHLIGHTS = ["none", "subtle", "prominent"]

EARRING_TYPES = ["none", "stud", "hoop_small", "hoop_large"]

NECKLACE_TYPES = ["none", "chain", "layered"]

CAMERA_ANGLES = ["low", "eye_level", "high"]

FRAMINGS = ["CU", "MCU", "MS", "MFS", "FS"]

VIBE_KEYWORDS = [
    "languid",
    "cool",
    "mysterious",
    "confident",
    "chic",
    "unbothered",
    "sexy",
    "playful",
    "fierce",
    "dreamy",
]

# 총 차원 계산:
# arm_position(7) + stance(4) + energy(1) +
# mouth(3) + eyes(4) + intensity(1) +
# finish(3) + highlight(3) +
# earrings(4) + necklace(3) + rings(1) +
# angle(3) + framing(5) +
# vibe_keywords(10) = 52차원
TOTAL_DIMENSIONS = 52


# ============================================================
# ENCODING FUNCTIONS
# ============================================================
def one_hot(value: str, categories: List[str]) -> List[float]:
    """카테고리 값을 one-hot 벡터로 변환"""
    vector = [0.0] * len(categories)
    value_lower = str(value).lower().strip()

    for i, cat in enumerate(categories):
        if cat.lower() == value_lower:
            vector[i] = 1.0
            break

    return vector


def multi_hot(values: List[str], categories: List[str]) -> List[float]:
    """다중 카테고리 값을 multi-hot 벡터로 변환"""
    vector = [0.0] * len(categories)

    for value in values:
        value_lower = str(value).lower().strip()
        for i, cat in enumerate(categories):
            if cat.lower() == value_lower:
                vector[i] = 1.0
                break

    return vector


def normalize(value: float, min_val: float, max_val: float) -> float:
    """숫자 값을 0-1 범위로 정규화"""
    if max_val <= min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


# ============================================================
# FEATURE VECTOR CONVERSION
# ============================================================
def analysis_to_feature_vector(analysis: Dict[str, Any]) -> np.ndarray:
    """
    VLM 분석 결과 → 고정 길이 특징 벡터 (52차원)

    Args:
        analysis: StyleAnalyzer.analyze_single() 결과

    Returns:
        np.ndarray (52,)
    """
    vector = []

    # 1. Pose encoding (12 dims)
    pose = analysis.get("pose", {})
    vector.extend(one_hot(pose.get("arm_position", "arms_relaxed"), ARM_POSITIONS))  # 7
    vector.extend(one_hot(pose.get("stance", "confident"), STANCES))  # 4
    vector.append(normalize(pose.get("energy_level", 3), 1, 5))  # 1

    # 2. Expression encoding (8 dims)
    expr = analysis.get("expression", {})
    vector.extend(one_hot(expr.get("mouth", "closed"), MOUTH_TYPES))  # 3
    vector.extend(one_hot(expr.get("eyes", "direct"), EYE_TYPES))  # 4
    vector.append(normalize(expr.get("intensity", 4), 1, 7))  # 1

    # 3. Skin encoding (6 dims)
    skin = analysis.get("skin", {})
    vector.extend(one_hot(skin.get("finish", "dewy"), SKIN_FINISHES))  # 3
    vector.extend(one_hot(skin.get("highlight", "subtle"), HIGHLIGHTS))  # 3

    # 4. Accessories encoding (8 dims)
    acc = analysis.get("accessories", {})
    vector.extend(one_hot(acc.get("earrings", "none"), EARRING_TYPES))  # 4
    vector.extend(one_hot(acc.get("necklace", "none"), NECKLACE_TYPES))  # 3
    vector.append(normalize(acc.get("rings", 0), 0, 5))  # 1

    # 5. Camera encoding (8 dims)
    cam = analysis.get("camera", {})
    vector.extend(one_hot(cam.get("angle", "eye_level"), CAMERA_ANGLES))  # 3
    vector.extend(one_hot(cam.get("framing", "MFS"), FRAMINGS))  # 5

    # 6. Vibe keywords encoding (10 dims)
    vibe = analysis.get("vibe_keywords", [])
    if isinstance(vibe, list):
        vector.extend(multi_hot(vibe, VIBE_KEYWORDS))  # 10
    else:
        vector.extend([0.0] * len(VIBE_KEYWORDS))

    return np.array(vector, dtype=np.float32)


# ============================================================
# STYLE INDEX CLASS
# ============================================================
class StyleIndex:
    """MLB 스타일 유사도 인덱스"""

    def __init__(self):
        """인덱스 초기화"""
        self.vectors: Optional[np.ndarray] = None  # (N, 52)
        self.sources: List[str] = []  # 이미지 경로 리스트
        self.analyses: List[Dict[str, Any]] = []  # 원본 분석 결과

    def build_from_analyses(self, analyses: List[Dict[str, Any]]) -> None:
        """
        분석 결과로 인덱스 구축

        Args:
            analyses: StyleAnalyzer.analyze_batch() 결과
        """
        vectors = []
        sources = []
        valid_analyses = []

        for analysis in analyses:
            if analysis.get("_fallback"):
                continue

            vector = analysis_to_feature_vector(analysis)
            vectors.append(vector)
            sources.append(analysis.get("_source", ""))
            valid_analyses.append(analysis)

        if vectors:
            self.vectors = np.vstack(vectors)
            self.sources = sources
            self.analyses = valid_analyses
            print(
                f"[INDEX] Built index with {len(vectors)} vectors ({TOTAL_DIMENSIONS} dims)"
            )
        else:
            print("[WARN] No valid analyses to build index")

    def save(self, path: str) -> None:
        """
        인덱스 저장 (numpy 압축 포맷)

        Args:
            path: 저장 경로 (.npz)
        """
        if self.vectors is None:
            print("[WARN] No index to save")
            return

        np.savez_compressed(
            path,
            vectors=self.vectors,
            sources=np.array(self.sources, dtype=object),
        )
        print(f"[SAVED] Index: {path}")

    def load(self, path: str) -> bool:
        """
        인덱스 로드

        Args:
            path: 로드 경로 (.npz)

        Returns:
            성공 여부
        """
        try:
            data = np.load(path, allow_pickle=True)
            self.vectors = data["vectors"]
            self.sources = list(data["sources"])
            print(f"[LOADED] Index: {len(self.sources)} vectors from {path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load index: {e}")
            return False

    def find_similar(
        self,
        query_vector: np.ndarray,
        top_k: int = 3,
    ) -> List[Tuple[int, float, str]]:
        """
        가장 유사한 스타일 찾기

        Args:
            query_vector: 쿼리 특징 벡터 (52,)
            top_k: 반환할 결과 수

        Returns:
            [(index, similarity, source_path), ...]
        """
        if self.vectors is None or len(self.vectors) == 0:
            return []

        # 코사인 유사도 계산
        similarities = np.array([1 - cosine(query_vector, sv) for sv in self.vectors])

        # 상위 k개
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        return [
            (int(idx), float(similarities[idx]), self.sources[idx])
            for idx in top_indices
        ]

    def find_similar_from_analysis(
        self,
        analysis: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Tuple[int, float, str]]:
        """
        분석 결과로 유사한 스타일 찾기

        Args:
            analysis: VLM 분석 결과 dict
            top_k: 반환할 결과 수

        Returns:
            [(index, similarity, source_path), ...]
        """
        query_vector = analysis_to_feature_vector(analysis)
        return self.find_similar(query_vector, top_k)

    def find_similar_from_prompt(
        self,
        prompt_json: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Tuple[int, float, str]]:
        """
        프롬프트 JSON으로 유사한 스타일 찾기

        Args:
            prompt_json: 브랜드컷 프롬프트 JSON
            top_k: 반환할 결과 수

        Returns:
            [(index, similarity, source_path), ...]
        """
        # 프롬프트 JSON → 분석 포맷 변환
        analysis = self._prompt_to_analysis(prompt_json)
        return self.find_similar_from_analysis(analysis, top_k)

    def _prompt_to_analysis(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """프롬프트 JSON → 분석 포맷 변환"""
        # 포즈 정보 추출
        pose_data = prompt_json.get("포즈", prompt_json.get("pose", {}))
        if isinstance(pose_data, str):
            pose_data = {"stance": pose_data}

        # 표정 정보 추출
        expr_data = prompt_json.get("표정", prompt_json.get("expression", {}))
        if isinstance(expr_data, str):
            expr_data = {"mood": expr_data}

        # 촬영 정보 추출
        camera_data = prompt_json.get("촬영", prompt_json.get("camera", {}))

        return {
            "pose": {
                "arm_position": pose_data.get(
                    "arms", pose_data.get("왼팔", "arms_relaxed")
                ),
                "stance": pose_data.get("stance", "confident"),
                "energy_level": 3,
            },
            "expression": {
                "mouth": expr_data.get("입", expr_data.get("mouth", "closed")),
                "eyes": expr_data.get("시선", expr_data.get("eyes", "direct")),
                "intensity": 4,
            },
            "skin": {
                "finish": "dewy",  # MLB 기본값
                "highlight": "subtle",
            },
            "accessories": {
                "earrings": "hoop_small",  # MLB 기본값
                "necklace": "chain",
                "rings": 0,
            },
            "camera": {
                "angle": camera_data.get("높이", camera_data.get("angle", "eye_level")),
                "framing": camera_data.get(
                    "프레이밍", camera_data.get("framing", "MFS")
                ),
            },
            "vibe_keywords": ["cool", "confident", "chic"],
        }


# ============================================================
# INDEX BUILDER
# ============================================================
def build_style_index(
    analysis_json: str = "db/mlb_style_analysis.json",
    output_index: str = "db/mlb_style_index.npz",
) -> StyleIndex:
    """
    분석 JSON으로 스타일 인덱스 구축

    Args:
        analysis_json: 분석 결과 JSON 경로
        output_index: 인덱스 출력 경로 (.npz)

    Returns:
        StyleIndex 인스턴스
    """
    # 분석 결과 로드
    with open(analysis_json, "r", encoding="utf-8") as f:
        analyses = json.load(f)

    print(f"[LOAD] {len(analyses)} analyses from {analysis_json}")

    # 인덱스 구축
    index = StyleIndex()
    index.build_from_analyses(analyses)

    # 저장
    index.save(output_index)

    return index


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================
def get_style_index(
    index_path: str = "db/mlb_style_index.npz",
    analysis_path: str = "db/mlb_style_analysis.json",
) -> StyleIndex:
    """
    스타일 인덱스 로드 (없으면 생성)

    Args:
        index_path: 인덱스 파일 경로
        analysis_path: 분석 결과 JSON 경로

    Returns:
        StyleIndex 인스턴스
    """
    index = StyleIndex()

    if Path(index_path).exists():
        if index.load(index_path):
            return index

    # 인덱스 파일이 없거나 로드 실패 시 재생성
    if Path(analysis_path).exists():
        return build_style_index(analysis_path, index_path)

    print(f"[ERROR] No analysis file: {analysis_path}")
    print("[HINT] Run style_analyzer.py first to generate analysis")
    return index


# ============================================================
# CLI ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent

    # 인덱스 구축
    index = build_style_index(
        analysis_json=str(project_root / "db" / "mlb_style_analysis.json"),
        output_index=str(project_root / "db" / "mlb_style_index.npz"),
    )

    # 테스트 쿼리
    if index.vectors is not None:
        print("\n[TEST] Sample query...")

        test_analysis = {
            "pose": {
                "arm_position": "hand_on_hip",
                "stance": "confident",
                "energy_level": 4,
            },
            "expression": {"mouth": "parted", "eyes": "direct", "intensity": 5},
            "skin": {"finish": "glossy", "highlight": "prominent"},
            "accessories": {"earrings": "hoop_large", "necklace": "chain", "rings": 1},
            "camera": {"angle": "low", "framing": "MFS"},
            "vibe_keywords": ["languid", "cool", "sexy"],
        }

        results = index.find_similar_from_analysis(test_analysis, top_k=5)

        print("\nTop 5 similar styles:")
        for i, (idx, sim, path) in enumerate(results, 1):
            print(f"  {i}. similarity={sim:.3f} - {Path(path).name}")
