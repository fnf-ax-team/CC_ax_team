"""
MLB Style Analyzer - VLM 기반 스타일 분석

db/mlb_style/ 이미지들을 분석하여 스타일 DNA 프로파일 생성.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from google import genai

from core.config import VISION_MODEL


# ============================================================
# STYLE ANALYSIS SCHEMA (T1 - 플랜 기반)
# ============================================================
STYLE_ANALYSIS_SCHEMA = {
    "pose": {
        "arm_position": [
            "hand_on_hip",
            "hand_on_hat",
            "arms_relaxed",
            "holding_bag",
            "arms_crossed",
            "hand_in_pocket",
            "touching_hair",
        ],
        "stance": ["confident", "relaxed", "lean", "seated"],
        "energy_level": "1-5 scale",  # 1=calm, 5=dynamic
    },
    "expression": {
        "mouth": ["closed", "parted", "subtle_smile"],
        "eyes": ["direct", "past", "side", "hooded"],
        "intensity": "1-7 scale",  # 1=soft, 7=intense
    },
    "skin": {
        "finish": ["matte", "dewy", "glossy"],
        "highlight": ["none", "subtle", "prominent"],
    },
    "accessories": {
        "earrings": ["none", "stud", "hoop_small", "hoop_large"],
        "necklace": ["none", "chain", "layered"],
        "rings": "0-5 count",
    },
    "camera": {
        "angle": ["low", "eye_level", "high"],
        "framing": ["CU", "MCU", "MS", "MFS", "FS"],
    },
    "vibe_keywords": "list of 3-5 keywords",
}


# ============================================================
# VLM PROMPT FOR STYLE ANALYSIS
# ============================================================
STYLE_ANALYSIS_PROMPT = """
Analyze this MLB style fashion image and extract style attributes.

Return ONLY valid JSON (no markdown, no explanation):

{
    "pose": {
        "arm_position": "hand_on_hip|hand_on_hat|arms_relaxed|holding_bag|arms_crossed|hand_in_pocket|touching_hair",
        "stance": "confident|relaxed|lean|seated",
        "energy_level": 1-5
    },
    "expression": {
        "mouth": "closed|parted|subtle_smile",
        "eyes": "direct|past|side|hooded",
        "intensity": 1-7
    },
    "skin": {
        "finish": "matte|dewy|glossy",
        "highlight": "none|subtle|prominent"
    },
    "accessories": {
        "earrings": "none|stud|hoop_small|hoop_large",
        "necklace": "none|chain|layered",
        "rings": 0-5
    },
    "camera": {
        "angle": "low|eye_level|high",
        "framing": "CU|MCU|MS|MFS|FS"
    },
    "vibe_keywords": ["keyword1", "keyword2", "keyword3"]
}

IMPORTANT:
- Pick exactly ONE option for each categorical field
- energy_level: 1=calm/static, 5=dynamic/energetic
- intensity: 1=soft/gentle, 7=intense/piercing
- vibe_keywords: Choose from [languid, cool, mysterious, confident, chic, unbothered, sexy, playful, fierce, dreamy, edgy, premium, street]
- Return ONLY the JSON object, no other text
"""


class StyleAnalyzer:
    """MLB 스타일 이미지 분석기"""

    def __init__(self, client):
        """
        Args:
            client: Google GenAI client instance
        """
        self.client = client

    def analyze_single(self, image_path: str) -> Dict[str, Any]:
        """
        단일 이미지 스타일 분석

        Args:
            image_path: 이미지 파일 경로

        Returns:
            스타일 분석 결과 dict
        """
        try:
            pil_image = Image.open(image_path)

            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[STYLE_ANALYSIS_PROMPT, pil_image],
            )

            result = self._parse_json_response(response.text.strip())

            # 필수 키 검증
            if not self._validate_result(result):
                print(f"[WARN] Invalid result for {image_path}, using fallback")
                return self._get_fallback()

            result["_source"] = str(image_path)
            return result

        except Exception as e:
            print(f"[ERROR] Failed to analyze {image_path}: {e}")
            return self._get_fallback(str(image_path))

    def analyze_batch(
        self,
        image_paths: List[str],
        max_workers: int = 5,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """
        배치 이미지 분석 (병렬 처리)

        Args:
            image_paths: 이미지 경로 리스트
            max_workers: 병렬 워커 수
            progress_callback: 진행률 콜백 (current, total)

        Returns:
            분석 결과 리스트
        """
        results = []
        total = len(image_paths)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.analyze_single, path): path for path in image_paths
            }

            for i, future in enumerate(as_completed(futures), 1):
                path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"[ERROR] {path}: {e}")
                    results.append(self._get_fallback(str(path)))

                if progress_callback:
                    progress_callback(i, total)

        return results

    def _parse_json_response(self, response_text: str) -> dict:
        """JSON 응답 파싱 (마크다운 코드 블록 제거)"""
        # markdown code block 제거
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            response_text = json_match.group(1)

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # JSON 객체 찾기
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                try:
                    return json.loads(response_text[start_idx : end_idx + 1])
                except json.JSONDecodeError:
                    pass

            return {}

    def _validate_result(self, result: dict) -> bool:
        """결과 유효성 검증"""
        required_keys = ["pose", "expression", "skin", "accessories", "camera"]
        return all(k in result for k in required_keys)

    def _get_fallback(self, source: str = "") -> dict:
        """폴백 결과"""
        return {
            "pose": {
                "arm_position": "arms_relaxed",
                "stance": "confident",
                "energy_level": 3,
            },
            "expression": {
                "mouth": "closed",
                "eyes": "direct",
                "intensity": 4,
            },
            "skin": {
                "finish": "dewy",
                "highlight": "subtle",
            },
            "accessories": {
                "earrings": "none",
                "necklace": "none",
                "rings": 0,
            },
            "camera": {
                "angle": "eye_level",
                "framing": "MFS",
            },
            "vibe_keywords": ["cool", "confident"],
            "_source": source,
            "_fallback": True,
        }


# ============================================================
# PROFILE AGGREGATOR (T2)
# ============================================================
class StyleProfileAggregator:
    """스타일 분석 결과를 프로파일로 집계"""

    def __init__(self, analyses: List[Dict[str, Any]]):
        """
        Args:
            analyses: StyleAnalyzer.analyze_batch() 결과
        """
        self.analyses = [a for a in analyses if not a.get("_fallback")]
        self.total_count = len(self.analyses)

    def generate_profile(self) -> Dict[str, Any]:
        """
        MLB 스타일 프로파일 생성

        Returns:
            스타일 프로파일 dict
        """
        if not self.analyses:
            return {"error": "No valid analyses"}

        return {
            "version": "1.0.0",
            "sample_count": self.total_count,
            "pose_distribution": self._aggregate_pose(),
            "expression_distribution": self._aggregate_expression(),
            "skin_distribution": self._aggregate_skin(),
            "accessories_distribution": self._aggregate_accessories(),
            "camera_distribution": self._aggregate_camera(),
            "top_vibe_keywords": self._aggregate_vibe_keywords(),
        }

    def _count_values(self, key_path: str) -> Dict[str, int]:
        """특정 경로의 값 빈도 카운트"""
        counts = {}
        keys = key_path.split(".")

        for analysis in self.analyses:
            value = analysis
            for k in keys:
                value = value.get(k, {}) if isinstance(value, dict) else None
                if value is None:
                    break

            if value is not None:
                value_str = str(value)
                counts[value_str] = counts.get(value_str, 0) + 1

        return counts

    def _to_distribution(self, counts: Dict[str, int]) -> Dict[str, float]:
        """빈도 → 비율 변환"""
        total = sum(counts.values())
        if total == 0:
            return {}
        return {k: round(v / total, 3) for k, v in counts.items()}

    def _aggregate_pose(self) -> Dict[str, Any]:
        """포즈 분포 집계"""
        arm_counts = self._count_values("pose.arm_position")
        stance_counts = self._count_values("pose.stance")
        energy_counts = self._count_values("pose.energy_level")

        return {
            "arm_position": self._to_distribution(arm_counts),
            "stance": self._to_distribution(stance_counts),
            "energy_level": self._to_distribution(energy_counts),
            "energy_level_avg": self._calc_avg("pose.energy_level"),
        }

    def _aggregate_expression(self) -> Dict[str, Any]:
        """표정 분포 집계"""
        mouth_counts = self._count_values("expression.mouth")
        eyes_counts = self._count_values("expression.eyes")
        intensity_counts = self._count_values("expression.intensity")

        return {
            "mouth": self._to_distribution(mouth_counts),
            "eyes": self._to_distribution(eyes_counts),
            "intensity": self._to_distribution(intensity_counts),
            "intensity_avg": self._calc_avg("expression.intensity"),
        }

    def _aggregate_skin(self) -> Dict[str, Any]:
        """피부 분포 집계"""
        finish_counts = self._count_values("skin.finish")
        highlight_counts = self._count_values("skin.highlight")

        return {
            "finish": self._to_distribution(finish_counts),
            "highlight": self._to_distribution(highlight_counts),
        }

    def _aggregate_accessories(self) -> Dict[str, Any]:
        """악세서리 분포 집계"""
        earrings_counts = self._count_values("accessories.earrings")
        necklace_counts = self._count_values("accessories.necklace")
        rings_counts = self._count_values("accessories.rings")

        # 비율 계산
        hoop_rate = sum(
            earrings_counts.get(k, 0) for k in ["hoop_small", "hoop_large"]
        ) / max(sum(earrings_counts.values()), 1)

        chain_rate = sum(necklace_counts.get(k, 0) for k in ["chain", "layered"]) / max(
            sum(necklace_counts.values()), 1
        )

        return {
            "earrings": self._to_distribution(earrings_counts),
            "necklace": self._to_distribution(necklace_counts),
            "rings": self._to_distribution(rings_counts),
            "hoop_earring_rate": round(hoop_rate, 3),
            "chain_necklace_rate": round(chain_rate, 3),
        }

    def _aggregate_camera(self) -> Dict[str, Any]:
        """카메라 분포 집계"""
        angle_counts = self._count_values("camera.angle")
        framing_counts = self._count_values("camera.framing")

        return {
            "angle": self._to_distribution(angle_counts),
            "framing": self._to_distribution(framing_counts),
            "low_angle_rate": angle_counts.get("low", 0) / max(self.total_count, 1),
        }

    def _aggregate_vibe_keywords(self) -> List[str]:
        """바이브 키워드 집계 (상위 10개)"""
        keyword_counts = {}

        for analysis in self.analyses:
            keywords = analysis.get("vibe_keywords", [])
            if isinstance(keywords, list):
                for kw in keywords:
                    kw_lower = str(kw).lower().strip()
                    keyword_counts[kw_lower] = keyword_counts.get(kw_lower, 0) + 1

        # 상위 10개
        sorted_kw = sorted(keyword_counts.items(), key=lambda x: -x[1])
        return [kw for kw, _ in sorted_kw[:10]]

    def _calc_avg(self, key_path: str) -> float:
        """숫자 필드 평균 계산"""
        values = []
        keys = key_path.split(".")

        for analysis in self.analyses:
            value = analysis
            for k in keys:
                value = value.get(k, {}) if isinstance(value, dict) else None
                if value is None:
                    break

            if isinstance(value, (int, float)):
                values.append(value)

        return round(sum(values) / max(len(values), 1), 2)


# ============================================================
# BATCH ANALYSIS RUNNER
# ============================================================
def run_batch_analysis(
    style_dir: str = "db/mlb_style",
    output_analysis: str = "db/mlb_style_analysis.json",
    output_profile: str = "db/mlb_style_profile.json",
    api_key: Optional[str] = None,
    max_workers: int = 5,
) -> Dict[str, Any]:
    """
    MLB 스타일 이미지 배치 분석 실행

    Args:
        style_dir: 스타일 이미지 폴더
        output_analysis: 분석 결과 JSON 경로
        output_profile: 프로파일 JSON 경로
        api_key: Gemini API 키 (없으면 환경변수에서)
        max_workers: 병렬 워커 수

    Returns:
        {"analyses": [...], "profile": {...}}
    """
    from core.api import _get_next_api_key

    # API 클라이언트 생성
    if api_key is None:
        api_key = _get_next_api_key()

    client = genai.Client(api_key=api_key)

    # 이미지 파일 수집
    style_path = Path(style_dir)
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_files.extend(style_path.glob(ext))

    image_files = [str(f) for f in sorted(image_files)]
    total = len(image_files)

    print(f"[START] Analyzing {total} MLB style images...")
    print(f"[CONFIG] max_workers={max_workers}, model={VISION_MODEL}")

    # 분석 실행
    analyzer = StyleAnalyzer(client)

    def progress_cb(current, total):
        if current % 10 == 0 or current == total:
            print(f"  Progress: {current}/{total} ({current*100//total}%)")

    analyses = analyzer.analyze_batch(
        image_files, max_workers=max_workers, progress_callback=progress_cb
    )

    # 분석 결과 저장
    with open(output_analysis, "w", encoding="utf-8") as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Analysis: {output_analysis}")

    # 프로파일 생성
    aggregator = StyleProfileAggregator(analyses)
    profile = aggregator.generate_profile()

    # 프로파일 저장
    with open(output_profile, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Profile: {output_profile}")

    # 요약 출력
    print("\n" + "=" * 50)
    print("MLB STYLE PROFILE SUMMARY")
    print("=" * 50)
    print(f"Total samples: {profile.get('sample_count', 0)}")
    print(f"Top vibe keywords: {profile.get('top_vibe_keywords', [])}")

    skin = profile.get("skin_distribution", {})
    print(f"Skin finish: {skin.get('finish', {})}")

    acc = profile.get("accessories_distribution", {})
    print(f"Hoop earring rate: {acc.get('hoop_earring_rate', 0):.1%}")
    print(f"Chain necklace rate: {acc.get('chain_necklace_rate', 0):.1%}")

    expr = profile.get("expression_distribution", {})
    print(f"Mouth parted rate: {expr.get('mouth', {}).get('parted', 0):.1%}")

    return {"analyses": analyses, "profile": profile}


# ============================================================
# CLI ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 프로젝트 루트 추가
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")

    # 배치 분석 실행
    result = run_batch_analysis(
        style_dir=str(project_root / "db" / "mlb_style"),
        output_analysis=str(project_root / "db" / "mlb_style_analysis.json"),
        output_profile=str(project_root / "db" / "mlb_style_profile.json"),
        max_workers=5,
    )

    print(f"\n[COMPLETE] Analyzed {len(result['analyses'])} images")
