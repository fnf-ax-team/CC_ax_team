"""
VLM 배치 분석 모듈 - 인플루언서 이미지에서 패션 속성 추출

인스타그램 인플루언서 이미지들을 VLM(Gemini Flash)으로 분석하여
착장, 컬러, 실루엣, 스타일링, 무드 등을 구조화된 JSON으로 추출한다.

사용법:
    from core.trend_analysis.analyzer import TrendAnalyzer

    analyzer = TrendAnalyzer(image_dir="path/to/images")
    analyzer.run(max_images=100, resume=True)
"""

import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


# ============================================================
# 상수
# ============================================================

# 지원 이미지 확장자
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# VLM 이미지 최대 크기 (리사이즈)
MAX_IMAGE_SIZE = 1024

# 재시도 대기 시간 (초) - exponential backoff
RETRY_DELAYS = [5, 10, 20]

# API 호출 최대 재시도 횟수
MAX_API_RETRIES = 3


# ============================================================
# VLM 분석 프롬프트
# ============================================================

FASHION_ANALYSIS_PROMPT = """You are a professional fashion analyst. Analyze this influencer photo and extract fashion attributes.

IMPORTANT RULES:
- Output ONLY valid JSON, no markdown, no explanation
- If an item is not visible or not present, use "none"
- Be specific about colors (e.g., "navy" not just "blue")
- Be specific about item types (e.g., "cargo_pants" not just "pants")

Output this exact JSON structure:
{
  "items": {
    "outer": "none / bomber, trench, padding, cardigan, blazer, denim_jacket, leather_jacket, fleece, vest, windbreaker",
    "top": "none / crop_tee, oversized_tee, tank_top, shirt, blouse, hoodie, sweatshirt, knit, polo, bustier",
    "bottom": "none / wide_pants, cargo_pants, straight_jeans, slim_jeans, mini_skirt, midi_skirt, long_skirt, shorts, jogger, leggings",
    "dress": "none / mini_dress, midi_dress, long_dress, jumpsuit",
    "shoes": "none / sneakers, boots, loafer, sandal, mule, heel, slipper, platform",
    "bag": "none / tote, crossbody, clutch, backpack, shoulder, bucket, mini_bag",
    "headwear": "none / cap, beanie, bucket_hat, beret, visor, headband",
    "accessories": "none / sunglasses, necklace, earrings, bracelet, watch, belt, scarf, ring"
  },
  "colors": {
    "main_color": "the single dominant color: black, white, cream, beige, gray, navy, blue, red, pink, green, brown, khaki, purple, yellow, orange, denim_blue, camel, burgundy, olive, lavender, charcoal",
    "sub_colors": ["up to 3 secondary colors from the same list"],
    "color_scheme": "monochrome / contrasting / pastel / earth_tone / vivid / neutral / denim_based"
  },
  "silhouette": {
    "top_fit": "oversized / regular / slim / crop",
    "bottom_fit": "wide / straight / slim / flare / none",
    "overall": "brief 1-sentence silhouette description in English"
  },
  "styling": {
    "layering": "none / light (2 layers) / heavy (3+ layers)",
    "tuck": "full_tuck / half_tuck / untucked / not_applicable",
    "details": "notable styling points in English (e.g., rolled sleeves, open buttons)"
  },
  "mood": {
    "primary": "clean_minimal / street_casual / sporty / romantic / gorpcore / y2k / preppy / grunge / classic / bohemian / athleisure",
    "secondary": "a secondary mood or none",
    "vibe": "one-line vibe summary in English"
  },
  "season": "spring / summer / fall / winter / transitional",
  "setting": "indoor / outdoor / cafe / street / studio / nature / gym / beach / office",
  "gender": "female / male",
  "quality_note": "ok / low_resolution / partial_body / face_only / group_photo / not_fashion"
}"""


# ============================================================
# API 키 관리 (thread-safe round-robin)
# ============================================================


class _APIKeyRotator:
    """Thread-safe API 키 로테이션"""

    def __init__(self):
        self._keys: List[str] = []
        self._index = 0
        self._lock = threading.Lock()
        self._loaded = False

    def _load_keys(self):
        """환경변수에서 API 키 로드"""
        if self._loaded:
            return
        api_key_str = os.getenv("GEMINI_API_KEY", "")
        self._keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
        if not self._keys:
            raise RuntimeError("GEMINI_API_KEY not found in environment")
        self._loaded = True

    def get_next(self) -> str:
        """다음 API 키 반환 (round-robin)"""
        with self._lock:
            self._load_keys()
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            return key

    @property
    def key_count(self) -> int:
        """사용 가능한 키 수"""
        with self._lock:
            self._load_keys()
            return len(self._keys)


_key_rotator = _APIKeyRotator()


# ============================================================
# 유틸리티 함수
# ============================================================


def _extract_influencer_name(filename: str) -> str:
    """
    파일명에서 인플루언서명 추출

    패턴: {인플루언서명}_{번호}_{포스트ID}_{이미지번호}.jpg
    예: Minha Kim_4_3616175565601804489_0.jpg -> Minha Kim
    예: joy_park_12_1234567890_2.jpg -> joy_park

    숫자로만 된 세그먼트가 연속 3개 나오기 전까지를 이름으로 간주
    """
    stem = Path(filename).stem

    # 언더스코어로 분리
    parts = stem.split("_")

    # 뒤에서부터 연속 숫자 세그먼트 카운트
    name_parts = []
    trailing_numbers = 0

    for part in reversed(parts):
        if part.isdigit() and trailing_numbers < 3:
            trailing_numbers += 1
        else:
            break

    # 숫자가 아닌 부분까지가 이름
    if trailing_numbers > 0:
        name_parts = parts[:-trailing_numbers]
    else:
        name_parts = parts

    if not name_parts:
        return stem

    return " ".join(name_parts)


def _pil_to_part(img: Image.Image) -> types.Part:
    """PIL Image를 Gemini Part로 변환 (리사이즈 포함)"""
    # 리사이즈
    if max(img.size) > MAX_IMAGE_SIZE:
        img = img.copy()
        img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)

    return types.Part(
        inline_data=types.Blob(mime_type="image/jpeg", data=buffer.getvalue())
    )


def _parse_json_response(text: str) -> Optional[Dict]:
    """
    VLM 응답에서 JSON 추출

    마크다운 코드블록, 앞뒤 텍스트 등을 제거하고 JSON만 파싱
    """
    if not text:
        return None

    cleaned = text.strip()

    # 마크다운 코드블록 제거
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

    # JSON 객체 추출 (첫 번째 { ~ 마지막 })
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ============================================================
# TrendAnalyzer 클래스
# ============================================================


class TrendAnalyzer:
    """
    인플루언서 이미지 VLM 배치 분석기

    이미지 폴더를 스캔하여 각 이미지의 패션 속성을
    VLM으로 추출하고 구조화된 JSON으로 저장한다.
    """

    def __init__(
        self,
        image_dir: str,
        output_dir: Optional[str] = None,
        max_workers: int = 3,
    ):
        """
        Args:
            image_dir: 분석할 이미지 폴더 경로
            output_dir: 결과 저장 경로 (기본: Fnf_studio_outputs/trend_analysis/{timestamp})
            max_workers: 동시 처리 스레드 수 (API rate limit 고려, 기본 3)
        """
        self.image_dir = Path(image_dir)
        if not self.image_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {image_dir}")

        # 출력 폴더 설정
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = (
                project_root / "Fnf_studio_outputs" / "trend_analysis" / timestamp
            )

        self.results_dir = self.output_dir / "results"
        self.max_workers = max_workers

        # 통계 카운터 (thread-safe)
        self._lock = threading.Lock()
        self._stats = {
            "total": 0,
            "ok": 0,
            "skip": 0,
            "error": 0,
            "processed": 0,
        }
        self._start_time: Optional[float] = None

    # ----------------------------------------------------------
    # 공개 메서드
    # ----------------------------------------------------------

    def run(
        self,
        max_images: Optional[int] = None,
        resume: bool = True,
    ) -> Path:
        """
        전체 이미지 배치 분석 실행

        Args:
            max_images: 분석할 최대 이미지 수 (None이면 전체)
            resume: True이면 이전 결과 이어서 진행

        Returns:
            결과 저장 디렉토리 경로
        """
        # 폴더 생성
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 이미지 목록 수집
        all_images = self._collect_images()
        if not all_images:
            print("[WARN] No images found in directory")
            return self.output_dir

        # resume 모드: 이미 분석된 파일 제외
        if resume:
            already_done = self._get_completed_files()
            pending = [p for p in all_images if p.stem not in already_done]
            skipped_count = len(all_images) - len(pending)
            if skipped_count > 0:
                print(f"[RESUME] Skipping {skipped_count} already analyzed images")
        else:
            pending = all_images

        # max_images 제한
        if max_images and len(pending) > max_images:
            pending = pending[:max_images]

        total = len(pending)
        if total == 0:
            print("[INFO] All images already analyzed")
            self._save_progress(len(all_images), len(all_images))
            return self.output_dir

        print(f"[START] Analyzing {total} images (workers={self.max_workers})")
        print(f"[OUTPUT] {self.output_dir}")

        # 통계 초기화
        self._stats = {"total": total, "ok": 0, "skip": 0, "error": 0, "processed": 0}
        self._start_time = time.time()

        # 병렬 실행
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._analyze_and_save, img_path): img_path
                for img_path in pending
            }

            for future in as_completed(futures):
                img_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"[ERROR] Unexpected: {img_path.name} - {e}")
                    with self._lock:
                        self._stats["error"] += 1
                        self._stats["processed"] += 1

                # 진행 상황 출력 (10건마다 또는 마지막)
                with self._lock:
                    processed = self._stats["processed"]
                if processed % 10 == 0 or processed == total:
                    self._print_progress()

        # 최종 진행 상황 저장
        self._save_progress(
            total_in_dir=len(all_images),
            total_analyzed=len(all_images) - len(pending) + self._stats["ok"],
        )

        # 완료 요약
        elapsed = time.time() - self._start_time
        print(f"\n[DONE] {self._stats['ok']}/{total} analyzed in {elapsed:.0f}s")
        print(
            f"  OK: {self._stats['ok']} | SKIP: {self._stats['skip']} | ERROR: {self._stats['error']}"
        )
        print(f"  Results: {self.results_dir}")

        return self.output_dir

    def analyze_single(self, image_path: str) -> Dict[str, Any]:
        """
        단일 이미지 VLM 분석

        Args:
            image_path: 이미지 파일 경로

        Returns:
            구조화된 패션 속성 dict
            실패 시 {"error": "...", "status": "error"} 반환
        """
        img_path = Path(image_path)

        # 이미지 로드
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            return {"error": f"Image load failed: {e}", "status": "error"}

        # 인플루언서명 추출
        influencer = _extract_influencer_name(img_path.name)

        # VLM 호출
        result = self._call_vlm(img)
        if result is None:
            return {
                "influencer": influencer,
                "filename": img_path.name,
                "error": "VLM analysis failed",
                "status": "error",
            }

        # 메타데이터 추가
        result["influencer"] = influencer
        result["filename"] = img_path.name
        result["analyzed_at"] = datetime.now().isoformat()
        result["status"] = "ok"

        return result

    # ----------------------------------------------------------
    # VLM 호출
    # ----------------------------------------------------------

    def _call_vlm(self, img: Image.Image) -> Optional[Dict]:
        """
        VLM API 호출 (재시도 포함)

        Args:
            img: 분석할 이미지 (PIL)

        Returns:
            파싱된 JSON dict, 실패 시 None
        """
        image_part = _pil_to_part(img)

        for attempt in range(MAX_API_RETRIES):
            try:
                api_key = _key_rotator.get_next()
                client = genai.Client(api_key=api_key)

                response = client.models.generate_content(
                    model=VISION_MODEL,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(text=FASHION_ANALYSIS_PROMPT),
                                image_part,
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(temperature=0.1),
                )

                # 응답 텍스트 추출
                text = ""
                if hasattr(response, "text") and response.text:
                    text = response.text
                else:
                    # candidates에서 텍스트 추출
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                text = part.text
                                break
                        if text:
                            break

                if not text:
                    if attempt < MAX_API_RETRIES - 1:
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    return None

                # JSON 파싱
                parsed = _parse_json_response(text)
                if parsed:
                    return parsed

                # 파싱 실패 시 재시도
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None

            except Exception as e:
                error_str = str(e).lower()

                # rate limit - backoff 후 재시도
                if "429" in error_str or "rate" in error_str or "quota" in error_str:
                    if attempt < MAX_API_RETRIES - 1:
                        wait = RETRY_DELAYS[attempt]
                        print(f"[RATE_LIMIT] Waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    return None

                # safety block - 스킵
                if "safety" in error_str or "blocked" in error_str:
                    return None

                # 인증 에러 - 즉시 종료
                if "401" in error_str or "auth" in error_str:
                    raise RuntimeError(f"API authentication failed: {e}")

                # 서버 에러 - 재시도
                if "503" in error_str or "overload" in error_str:
                    if attempt < MAX_API_RETRIES - 1:
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    return None

                # 기타 에러
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None

        return None

    # ----------------------------------------------------------
    # 내부 메서드
    # ----------------------------------------------------------

    def _analyze_and_save(self, img_path: Path):
        """단일 이미지 분석 후 결과 즉시 저장 (스레드에서 실행)"""
        result = self.analyze_single(str(img_path))

        with self._lock:
            self._stats["processed"] += 1

        status = result.get("status", "error")
        quality = result.get("quality_note", "ok")

        # 패션과 무관한 이미지는 스킵 처리
        if status == "ok" and quality in ("not_fashion", "face_only"):
            status = "skip"
            result["status"] = "skip"

        # 결과 저장 (상태와 무관하게 항상 저장 - resume 지원)
        result_path = self.results_dir / f"{img_path.stem}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 카운터 업데이트
        with self._lock:
            if status == "ok":
                self._stats["ok"] += 1
            elif status == "skip":
                self._stats["skip"] += 1
            else:
                self._stats["error"] += 1

    def _collect_images(self) -> List[Path]:
        """이미지 폴더에서 지원 확장자 파일 수집 (정렬)"""
        images = []
        for f in sorted(self.image_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                images.append(f)
        return images

    def _get_completed_files(self) -> set:
        """이미 분석 완료된 파일명 (확장자 제외) 집합"""
        completed = set()
        if not self.results_dir.exists():
            return completed

        for f in self.results_dir.iterdir():
            if f.suffix == ".json" and f.name != "progress.json":
                completed.add(f.stem)

        return completed

    def _print_progress(self):
        """진행 상황 출력"""
        with self._lock:
            processed = self._stats["processed"]
            total = self._stats["total"]
            ok = self._stats["ok"]
            skip = self._stats["skip"]
            error = self._stats["error"]

        pct = (processed / total * 100) if total > 0 else 0

        # ETA 계산
        elapsed = time.time() - self._start_time if self._start_time else 0
        if processed > 0 and elapsed > 0:
            per_item = elapsed / processed
            remaining = (total - processed) * per_item
            eta_min = remaining / 60
            eta_str = f"ETA: {eta_min:.0f}min"
        else:
            eta_str = "ETA: --"

        print(
            f"[PROGRESS] {processed}/{total} ({pct:.1f}%) | "
            f"OK: {ok} | SKIP: {skip} | ERR: {error} | {eta_str}"
        )

    def _save_progress(self, total_in_dir: int, total_analyzed: int):
        """진행 상황 파일 저장 (resume용)"""
        progress = {
            "image_dir": str(self.image_dir),
            "output_dir": str(self.output_dir),
            "total_images": total_in_dir,
            "total_analyzed": total_analyzed,
            "last_updated": datetime.now().isoformat(),
            "stats": dict(self._stats),
        }
        progress_path = self.output_dir / "progress.json"
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    # 프롬프트 (외부 커스터마이징용)
    # ----------------------------------------------------------

    def _build_analysis_prompt(self) -> str:
        """VLM 분석 프롬프트 반환 (서브클래스에서 오버라이드 가능)"""
        return FASHION_ANALYSIS_PROMPT
