"""
clip_validator.py

CLIP 기반 A급 이미지 유사도 검증기.
생성된 이미지가 A급 DB(db/mlb_style)와 얼마나 유사한지 측정.

Usage:
    from core.brandcut.clip_validator import CLIPValidator, get_clip_validator

    validator = get_clip_validator()
    score = validator.score_image(generated_image)
    # score: 0-100 (100에 가까울수록 A급 유사)
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Union
from PIL import Image
import warnings

# CLIP import (torch + transformers)
try:
    import torch
    from transformers import CLIPProcessor, CLIPModel

    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    warnings.warn("CLIP not available. Install with: pip install torch transformers")


# ============================================================
# PATHS & CONSTANTS
# ============================================================
DEFAULT_A_GRADE_DIR = Path("db/mlb_style")
DEFAULT_CACHE_PATH = Path("db/clip_a_grade_embeddings.npz")
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

# A급 유사도 기준
A_GRADE_THRESHOLD = 0.75  # 코사인 유사도 0.75 이상이면 A급 수준
B_GRADE_THRESHOLD = 0.65  # 0.65~0.75는 B급
# 0.65 미만은 C급


# ============================================================
# CLIP VALIDATOR CLASS
# ============================================================
class CLIPValidator:
    """CLIP 기반 A급 이미지 유사도 검증기"""

    def __init__(
        self,
        a_grade_dir: Union[str, Path] = DEFAULT_A_GRADE_DIR,
        cache_path: Union[str, Path] = DEFAULT_CACHE_PATH,
        device: Optional[str] = None,
    ):
        """
        Args:
            a_grade_dir: A급 이미지 폴더 경로
            cache_path: 임베딩 캐시 파일 경로
            device: 'cuda' or 'cpu' (None이면 자동 선택)
        """
        self.a_grade_dir = Path(a_grade_dir)
        self.cache_path = Path(cache_path)

        if not CLIP_AVAILABLE:
            raise ImportError(
                "CLIP not available. Install with: pip install torch transformers"
            )

        # Device 설정
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"[CLIP] Using device: {self.device}")

        # 모델 로드
        self._model = None
        self._processor = None
        self._a_grade_embeddings = None
        self._a_grade_paths = None

    @property
    def model(self):
        """Lazy load CLIP model"""
        if self._model is None:
            print(f"[CLIP] Loading model: {CLIP_MODEL_NAME}")
            self._model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(self.device)
            self._model.eval()
        return self._model

    @property
    def processor(self):
        """Lazy load CLIP processor"""
        if self._processor is None:
            self._processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
        return self._processor

    def _load_or_build_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """A급 이미지 임베딩 로드 또는 빌드"""
        # 캐시 확인
        if self.cache_path.exists():
            try:
                data = np.load(self.cache_path, allow_pickle=True)
                embeddings = data["embeddings"]
                paths = list(data["paths"])
                print(f"[CLIP] Loaded {len(paths)} A-grade embeddings from cache")
                return embeddings, paths
            except Exception as e:
                print(f"[CLIP] Cache load failed: {e}, rebuilding...")

        # 임베딩 빌드
        return self._build_embeddings()

    def _build_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """A급 이미지 임베딩 빌드"""
        if not self.a_grade_dir.exists():
            raise FileNotFoundError(f"A-grade directory not found: {self.a_grade_dir}")

        # 이미지 파일 수집
        image_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            image_files.extend(self.a_grade_dir.glob(ext))

        if not image_files:
            raise ValueError(f"No images found in {self.a_grade_dir}")

        print(f"[CLIP] Building embeddings for {len(image_files)} A-grade images...")

        embeddings = []
        paths = []

        with torch.no_grad():
            for i, img_path in enumerate(image_files):
                try:
                    img = Image.open(img_path).convert("RGB")
                    embedding = self._embed_image(img)
                    embeddings.append(embedding)
                    paths.append(str(img_path))

                    if (i + 1) % 20 == 0:
                        print(f"  Processed {i + 1}/{len(image_files)}...")

                except Exception as e:
                    print(f"  [WARN] Failed to process {img_path.name}: {e}")

        embeddings = np.vstack(embeddings)
        print(f"[CLIP] Built {len(embeddings)} embeddings (shape: {embeddings.shape})")

        # 캐시 저장
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self.cache_path,
            embeddings=embeddings,
            paths=np.array(paths, dtype=object),
        )
        print(f"[CLIP] Saved cache: {self.cache_path}")

        return embeddings, paths

    def _embed_image(self, image: Image.Image) -> np.ndarray:
        """단일 이미지 임베딩"""
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            features = self.model.get_image_features(**inputs)
            # L2 정규화
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy()

    def _ensure_embeddings(self):
        """임베딩이 로드되었는지 확인"""
        if self._a_grade_embeddings is None:
            self._a_grade_embeddings, self._a_grade_paths = (
                self._load_or_build_embeddings()
            )

    def score_image(
        self,
        image: Union[Image.Image, str, Path],
        top_k: int = 5,
    ) -> dict:
        """
        이미지의 A급 유사도 점수 계산

        Args:
            image: PIL Image 또는 이미지 경로
            top_k: 가장 유사한 상위 k개 이미지

        Returns:
            {
                "score": 0-100,
                "grade": "A" | "B" | "C",
                "similarity": 0.0-1.0 (코사인 유사도),
                "top_matches": [(path, similarity), ...],
                "recommendation": str
            }
        """
        self._ensure_embeddings()

        # 이미지 로드
        if isinstance(image, (str, Path)):
            image = Image.open(image).convert("RGB")

        # 임베딩
        query_embedding = self._embed_image(image)

        # 코사인 유사도 계산
        similarities = np.dot(self._a_grade_embeddings, query_embedding.T).flatten()

        # 상위 k개
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        top_matches = [
            (self._a_grade_paths[i], float(similarities[i])) for i in top_indices
        ]

        # 평균 유사도 (상위 k개)
        avg_similarity = float(np.mean([s for _, s in top_matches]))

        # 최고 유사도
        max_similarity = float(similarities.max())

        # 등급 판정
        if avg_similarity >= A_GRADE_THRESHOLD:
            grade = "A"
            recommendation = "A급 수준 달성. 품질 양호."
        elif avg_similarity >= B_GRADE_THRESHOLD:
            grade = "B"
            recommendation = "B급 수준. 앵글/포즈/표정 조정으로 개선 가능."
        else:
            grade = "C"
            recommendation = "C급 수준. 전체적인 스타일 재검토 필요."

        # 0-100 점수로 변환
        score = int(min(100, max(0, avg_similarity * 100)))

        return {
            "score": score,
            "grade": grade,
            "avg_similarity": avg_similarity,
            "max_similarity": max_similarity,
            "top_matches": top_matches,
            "recommendation": recommendation,
        }

    def compare_images(
        self,
        images: List[Union[Image.Image, str, Path]],
        labels: Optional[List[str]] = None,
    ) -> dict:
        """
        여러 이미지의 A급 유사도 비교

        Args:
            images: 이미지 리스트
            labels: 각 이미지 라벨 (선택)

        Returns:
            {
                "results": [{score, grade, ...}, ...],
                "best_index": int,
                "worst_index": int,
                "summary": str
            }
        """
        if labels is None:
            labels = [f"image_{i}" for i in range(len(images))]

        results = []
        for img, label in zip(images, labels):
            result = self.score_image(img)
            result["label"] = label
            results.append(result)

        # 정렬
        scores = [r["score"] for r in results]
        best_idx = int(np.argmax(scores))
        worst_idx = int(np.argmin(scores))

        # 요약
        grades = [r["grade"] for r in results]
        a_count = grades.count("A")
        b_count = grades.count("B")
        c_count = grades.count("C")

        summary = (
            f"총 {len(images)}장: A급 {a_count}장, B급 {b_count}장, C급 {c_count}장"
        )

        return {
            "results": results,
            "best_index": best_idx,
            "worst_index": worst_idx,
            "summary": summary,
        }

    def validate_batch(
        self,
        images: List[Union[Image.Image, str, Path]],
        min_a_grade_ratio: float = 0.7,
    ) -> dict:
        """
        배치 검증 (A급 비율 기반 Pass/Fail)

        Args:
            images: 이미지 리스트
            min_a_grade_ratio: 최소 A급 비율 (0.7 = 70%)

        Returns:
            {
                "passed": bool,
                "a_grade_ratio": float,
                "avg_score": float,
                "details": [...]
            }
        """
        comparison = self.compare_images(images)

        a_count = sum(1 for r in comparison["results"] if r["grade"] == "A")
        a_grade_ratio = a_count / len(images) if images else 0
        avg_score = sum(r["score"] for r in comparison["results"]) / len(images)

        passed = a_grade_ratio >= min_a_grade_ratio

        return {
            "passed": passed,
            "a_grade_ratio": a_grade_ratio,
            "avg_score": avg_score,
            "a_count": a_count,
            "total": len(images),
            "min_required_ratio": min_a_grade_ratio,
            "details": comparison["results"],
        }


# ============================================================
# SINGLETON INSTANCE
# ============================================================
_validator_instance: Optional[CLIPValidator] = None


def get_clip_validator() -> CLIPValidator:
    """싱글톤 CLIPValidator 반환"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = CLIPValidator()
    return _validator_instance


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================
def score_a_grade_similarity(
    image: Union[Image.Image, str, Path],
) -> dict:
    """
    이미지의 A급 유사도 점수 (편의 함수)

    Returns:
        {"score": 0-100, "grade": "A"|"B"|"C", ...}
    """
    validator = get_clip_validator()
    return validator.score_image(image)


def validate_a_grade_batch(
    images: List[Union[Image.Image, str, Path]],
    min_a_grade_ratio: float = 0.7,
) -> dict:
    """
    배치 A급 검증 (편의 함수)

    Returns:
        {"passed": bool, "a_grade_ratio": float, ...}
    """
    validator = get_clip_validator()
    return validator.validate_batch(images, min_a_grade_ratio)


# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    import sys

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    print("[TEST] CLIP A-Grade Validator")
    print("=" * 60)

    # 검증기 초기화
    validator = CLIPValidator(
        a_grade_dir=project_root / "db" / "mlb_style",
        cache_path=project_root / "db" / "clip_a_grade_embeddings.npz",
    )

    # 테스트: A급 이미지 자체 검증 (높은 점수 예상)
    a_grade_images = list((project_root / "db" / "mlb_style").glob("*.webp"))[:3]

    if a_grade_images:
        print("\n[1] Testing A-grade images (should score high):")
        for img_path in a_grade_images:
            result = validator.score_image(img_path)
            print(
                f"  {img_path.name}: score={result['score']}, grade={result['grade']}"
            )

    # 파일럿 실험 이미지 테스트
    pilot_dir = project_root / "Fnf_studio_outputs" / "pilot_experiment"
    if pilot_dir.exists():
        latest_dir = (
            sorted(pilot_dir.iterdir())[-1] if any(pilot_dir.iterdir()) else None
        )
        if latest_dir:
            print(f"\n[2] Testing pilot experiment images ({latest_dir.name}):")

            micro_images = list(latest_dir.glob("micro_*.png"))
            baseline_images = list(latest_dir.glob("baseline_*.png"))

            if micro_images:
                print("\n  [Micro-instruction images]:")
                for img_path in micro_images:
                    result = validator.score_image(img_path)
                    print(
                        f"    {img_path.name}: score={result['score']}, grade={result['grade']}"
                    )

            if baseline_images:
                print("\n  [Baseline images]:")
                for img_path in baseline_images:
                    result = validator.score_image(img_path)
                    print(
                        f"    {img_path.name}: score={result['score']}, grade={result['grade']}"
                    )
