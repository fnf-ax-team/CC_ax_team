"""
배경 교체 생성기 - swap(), generate_with_validation(), BatchProcessor
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from google import genai
from google.genai import types

from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key as get_next_api_key
from core.utils import pil_to_part


# ============================================================
# 결과 데이터클래스
# ============================================================


@dataclass
class SwapResult:
    """단일 배경 교체 결과"""

    success: bool = False
    image: Optional[Image.Image] = None
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환 (image 제외)"""
        return {
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BatchResult:
    """배치 처리 결과"""

    total: int = 0
    success: int = 0
    failed: int = 0
    results: List[Any] = field(default_factory=list)
    duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "duration_sec": self.duration_sec,
        }


from .analyzer import (
    analyze_model_physics,
    analyze_for_background_swap,
    analyze_background,
    detect_source_type,
    build_background_guideline,
)
from .prompt_builder import (
    build_background_prompt,
    build_one_unit_instructions,
)
from .templates import BASE_PRESERVATION_PROMPT


# ============================================================
# 메인 진입점
# ============================================================


def swap(
    source: Union[str, Path, Image.Image],
    background_style: str,
    output_dir: str = None,
    variations: int = 1,
    enable_retry: bool = False,
    max_retries: int = 2,
    enable_sweep: bool = False,
    max_sweep_rounds: int = 2,
    image_size: str = "2K",
) -> Dict[str, Any]:
    """
    통합 진입점 - Fast/Quality/Sweep 모드 자동 선택.

    Args:
        source: 이미지 파일 경로, 폴더 경로, 또는 PIL Image
        background_style: 배경 스타일 설명 (예: "캘리포니아 해변 석양")
        output_dir: 출력 폴더 (기본: Fnf_studio_outputs/background_swap/{timestamp})
        variations: 생성할 이미지 수 (기본: 1)
        enable_retry: Quality 모드 활성화 (생성+검증+재시도)
        max_retries: 최대 재시도 횟수 (기본: 2)
        enable_sweep: Sweep 모드 활성화 (배치 생성+일괄 검증)
        max_sweep_rounds: Sweep 라운드 수 (기본: 2)
        image_size: 해상도 "1K" | "2K" | "4K"

    Returns:
        {
            "mode": "fast" | "quality" | "sweep",
            "total": int,
            "success": int,
            "failed": int,
            "results": List[dict],
            "output_dir": str
        }
    """
    # 출력 폴더 설정
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        style_slug = background_style[:20].replace(" ", "_")
        output_dir = f"Fnf_studio_outputs/background_swap/{style_slug}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # 소스 이미지 로드
    images = _load_source_images(source)

    # 모드 결정
    if enable_sweep:
        mode = "sweep"
    elif enable_retry:
        mode = "quality"
    else:
        mode = "fast"

    print(
        f"[BG-SWAP] Mode: {mode.upper()}, Images: {len(images)}, Variations: {variations}"
    )

    results = []
    success_count = 0
    fail_count = 0

    for i, img in enumerate(images):
        for v in range(variations):
            api_key = get_next_api_key()

            if mode == "fast":
                # Fast 모드: 단일 생성 + 점수 리포트
                result = _fast_generate(img, background_style, api_key, image_size)
            elif mode == "quality":
                # Quality 모드: 생성 + 검증 + 재시도
                result = generate_with_validation(
                    img, background_style, api_key, max_retries, 0.2, image_size
                )
            else:
                # Sweep 모드: Fast 생성 후 일괄 검증
                result = _fast_generate(img, background_style, api_key, image_size)

            # 결과 저장
            if result.get("image"):
                output_path = os.path.join(
                    output_dir,
                    f"result_{i:03d}_v{v:02d}_{datetime.now().strftime('%H%M%S')}.png",
                )
                result["image"].save(output_path, "PNG")
                result["output_path"] = output_path
                del result["image"]  # PIL 객체 제거
                success_count += 1
            else:
                fail_count += 1

            results.append(result)

    # Sweep 모드: 일괄 검증 + 실패분 재생성
    if mode == "sweep" and max_sweep_rounds > 0:
        results = _sweep_validate_and_retry(
            results, images, background_style, max_sweep_rounds, image_size, output_dir
        )

    return {
        "mode": mode,
        "total": len(results),
        "success": success_count,
        "failed": fail_count,
        "results": results,
        "output_dir": output_dir,
    }


# ============================================================
# 단일 이미지 생성
# ============================================================


def generate_background_swap(
    source_image: Image.Image,
    background_prompt: str,
    api_key: str,
    temperature: float = 0.2,
    image_size: str = "2K",
) -> Optional[Image.Image]:
    """
    단일 이미지 생성.

    Args:
        source_image: 소스 이미지
        background_prompt: 조립된 최종 프롬프트
        api_key: Gemini API 키
        temperature: 생성 온도 (기본: 0.2)
        image_size: 해상도

    Returns:
        생성된 PIL Image 또는 None
    """
    try:
        client = genai.Client(api_key=api_key)

        # 원본 비율 계산 및 가장 가까운 aspect_ratio 선택
        aspect_ratio = _get_closest_aspect_ratio(source_image)

        # 소스 이미지 준비
        source_part = pil_to_part(source_image, max_size=2048)

        parts = [
            types.Part(text=background_prompt),
            types.Part(text="\n\n[Source Image - preserve this person exactly]:"),
            source_part,
        ]

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )

        # 이미지 추출
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                from io import BytesIO

                return Image.open(BytesIO(part.inline_data.data))

        return None

    except Exception as e:
        print(f"[BG-SWAP] Generation error: {str(e)[:100]}")
        return None


# ============================================================
# 생성 + 검증 루프
# ============================================================


def generate_with_validation(
    source_image: Image.Image,
    background_style: str,
    api_key: str,
    max_retries: int = 2,
    initial_temperature: float = 0.2,
    image_size: str = "2K",
) -> Dict[str, Any]:
    """
    생성 + 7-criteria 검증 + 자동 재시도.

    Args:
        source_image: 소스 이미지
        background_style: 배경 스타일 설명
        api_key: API 키
        max_retries: 최대 재시도 횟수
        initial_temperature: 초기 온도
        image_size: 해상도

    Returns:
        {
            "image": PIL.Image | None,
            "score": int,
            "passed": bool,
            "grade": str,
            "issues": List[str],
            "attempts": int,
            "history": List[dict]
        }
    """
    from .validator import get_validator, BackgroundSwapValidator

    # 분석 수행
    physics_analysis = analyze_model_physics(source_image, api_key)
    swap_analysis = analyze_for_background_swap(source_image, api_key)
    source_type = detect_source_type(source_image, api_key)

    # 검증기 선택 및 VFX 분석 결과 전달
    validator, validator_name = get_validator(source_type, api_key)
    validator.set_vfx_analysis(physics_analysis)  # 원근감/포즈 정보 전달

    # Temperature 감소 스케줄: 0.2 -> 0.1 -> 0.05
    temps = [initial_temperature, 0.1, 0.05]

    history = []
    best_result = None
    best_score = 0

    for attempt in range(max_retries + 1):
        temp = temps[min(attempt, len(temps) - 1)]

        # 프롬프트 조립
        prompt = build_background_prompt(
            background_style=background_style,
            physics_analysis=physics_analysis.get("data", {}),
            swap_analysis=swap_analysis,
            preservation_level="DETAILED"
            if swap_analysis.get("has_vehicle")
            else "BASIC",
        )

        # 재시도 시 보강 프롬프트 추가
        if attempt > 0 and best_result:
            enhancement, _ = validator.get_enhancement_prompt(best_result)
            if enhancement:
                prompt = enhancement + "\n\n" + prompt

        # 생성
        image = generate_background_swap(
            source_image, prompt, api_key, temp, image_size
        )

        if image is None:
            history.append({"attempt": attempt + 1, "status": "generation_failed"})
            continue

        # 검증
        result = validator.validate(image, source_image)

        # 검증 결과 출력
        print(f"\n{'=' * 60}")
        print(f"검증 결과 (시도 {attempt + 1})")
        print(f"{'=' * 60}")
        print(f"| 항목                  | 점수 | 기준    | 통과 |")
        print(f"|----------------------|------|---------|------|")
        print(
            f"| 인물 보존            | {result.model_preservation:4d} | = 100   | {'O' if result.model_preservation == 100 else 'X'} |"
        )
        print(
            f"| 리라이트 자연스러움   | {result.relight_naturalness:4d} | -       | - |"
        )
        print(f"| 조명 일치            | {result.lighting_match:4d} | -       | - |")
        print(f"| 접지감               | {result.ground_contact:4d} | -       | - |")
        print(
            f"| 물리 타당성          | {result.physics_plausibility:4d} | >= 50   | {'O' if result.physics_plausibility >= 50 else 'X'} |"
        )
        print(f"| 경계 품질            | {result.edge_quality:4d} | -       | - |")
        print(
            f"| 스타일 일치          | {result.prop_style_consistency:4d} | -       | - |"
        )
        print(
            f"| 색온도 준수          | {result.color_temperature_compliance:4d} | >= 80   | {'O' if result.color_temperature_compliance >= 80 else 'X'} |"
        )
        print(f"| 원근 일치            | {result.perspective_match:4d} | -       | - |")
        print(f"|----------------------|------|---------|------|")
        print(
            f"| 총점                 | {result.total_score:4d} | >= 90   | {'O' if result.total_score >= 90 else 'X'} |"
        )
        print(f"{'=' * 60}")
        print(f"등급: {result.grade} | 판정: {'PASS' if result.passed else 'FAIL'}")
        if result.issues:
            print(f"이슈: {', '.join(result.issues)}")
        print(f"{'=' * 60}\n")

        history.append(
            {
                "attempt": attempt + 1,
                "temperature": temp,
                "score": result.total_score,
                "passed": result.passed,
                "grade": result.grade,
                "issues": result.issues,
            }
        )

        # 최고 점수 업데이트
        if result.total_score > best_score:
            best_score = result.total_score
            best_result = result
            best_image = image

        # Pass 시 종료
        if result.passed:
            return {
                "image": image,
                "score": result.total_score,
                "passed": True,
                "grade": result.grade,
                "issues": result.issues,
                "attempts": attempt + 1,
                "history": history,
                "validator": validator_name,
            }

    # 모든 시도 실패 - 최고 점수 이미지 반환
    return {
        "image": best_image if best_score > 0 else None,
        "score": best_score,
        "passed": False,
        "grade": best_result.grade if best_result else "F",
        "issues": best_result.issues if best_result else ["All attempts failed"],
        "attempts": max_retries + 1,
        "history": history,
        "validator": validator_name,
    }


# ============================================================
# 배치 프로세서
# ============================================================


class BatchProcessor:
    """대량 이미지 배치 처리"""

    def __init__(
        self, max_workers: int = 5, retry_count: int = 3, delay_between: float = 0.5
    ):
        """
        Args:
            max_workers: 병렬 워커 수 (API 키 개수에 맞춰 조정)
            retry_count: 실패 시 재시도 횟수
            delay_between: 요청 간 딜레이 (초)
        """
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.delay_between = delay_between
        self.results = []
        self.errors = []
        self._completed = 0
        self._total = 0
        # config 속성 - 테스트 호환성용
        self.config = {
            "max_workers": max_workers,
            "retry_count": retry_count,
            "delay_between": delay_between,
        }

    def get_progress(self) -> Dict[str, int]:
        """현재 진행 상황 반환"""
        return {"completed": self._completed, "total": self._total}

    def process(
        self, items: List[Any], process_func, output_dir: str = None
    ) -> Dict[str, Any]:
        """
        배치 처리 실행.

        Args:
            items: 처리할 아이템 리스트
            process_func: 각 아이템에 적용할 함수 (item) -> result
            output_dir: 출력 폴더 (선택)

        Returns:
            {
                "total": int,
                "success": int,
                "failed": int,
                "duration_sec": float,
                "results": List[dict],
                "errors": List[dict]
            }
        """
        start_time = datetime.now()
        self.results = []
        self.errors = []

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        total = len(items)
        print(f"[BATCH] Starting: {total} items, {self.max_workers} workers")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_with_retry, item, process_func, idx, output_dir
                ): idx
                for idx, item in enumerate(items)
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.errors.append({"index": idx, "error": str(e)})
                time.sleep(self.delay_between)

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "total": total,
            "success": len(self.results),
            "failed": len(self.errors),
            "duration_sec": round(duration, 2),
            "results": self.results,
            "errors": self.errors,
        }

    def _process_with_retry(self, item, process_func, idx, output_dir):
        """재시도 로직 포함 단일 아이템 처리"""
        last_error = None

        for attempt in range(self.retry_count):
            try:
                result_image = process_func(item)

                if output_dir and result_image:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
                    filepath = os.path.join(
                        output_dir, f"result_{idx:04d}_{timestamp}.png"
                    )
                    result_image.save(filepath, "PNG")
                    return {"index": idx, "filepath": filepath, "status": "success"}

                return {"index": idx, "status": "success"}

            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep((attempt + 1) * 3)

        raise last_error


# ============================================================
# 내부 헬퍼 함수
# ============================================================


def _get_closest_aspect_ratio(image: Image.Image) -> str:
    """
    원본 이미지의 비율에 가장 가까운 지원 aspect_ratio 반환.

    지원 비율: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
    """
    w, h = image.size
    ratio = w / h

    # 지원되는 비율들 (ratio 값, 문자열)
    supported = [
        (1 / 1, "1:1"),  # 1.0
        (2 / 3, "2:3"),  # 0.667
        (3 / 2, "3:2"),  # 1.5
        (3 / 4, "3:4"),  # 0.75
        (4 / 3, "4:3"),  # 1.333
        (4 / 5, "4:5"),  # 0.8
        (5 / 4, "5:4"),  # 1.25
        (9 / 16, "9:16"),  # 0.5625
        (16 / 9, "16:9"),  # 1.778
        (21 / 9, "21:9"),  # 2.333
    ]

    # 가장 가까운 비율 찾기
    closest = min(supported, key=lambda x: abs(x[0] - ratio))
    return closest[1]


def _load_source_images(source: Union[str, Path, Image.Image]) -> List[Image.Image]:
    """소스에서 이미지 로드"""
    if isinstance(source, Image.Image):
        return [source]

    source_path = Path(source)

    if source_path.is_file():
        return [Image.open(source_path)]

    if source_path.is_dir():
        images = []
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            for f in source_path.glob(ext):
                images.append(Image.open(f))
        return images

    raise ValueError(f"Invalid source: {source}")


def _fast_generate(
    source_image: Image.Image,
    background_style: str,
    api_key: str,
    image_size: str,
) -> Dict[str, Any]:
    """Fast 모드 생성 (검증 없음)"""
    # 간단한 분석
    try:
        swap_analysis = analyze_for_background_swap(source_image, api_key)
    except:
        swap_analysis = {}

    # 프롬프트 조립
    prompt = build_background_prompt(
        background_style=background_style,
        physics_analysis={},
        swap_analysis=swap_analysis,
        preservation_level="BASIC",
    )

    # 생성
    image = generate_background_swap(source_image, prompt, api_key, 0.2, image_size)

    return {
        "image": image,
        "score": None,  # Fast 모드는 검증 없음
        "passed": None,
        "mode": "fast",
    }


def _sweep_validate_and_retry(
    results: List[Dict],
    images: List[Image.Image],
    background_style: str,
    max_rounds: int,
    image_size: str,
    output_dir: str,
) -> List[Dict]:
    """Sweep 모드: 일괄 검증 + 실패분 재생성"""
    from .validator import get_validator

    # 일괄 검증
    api_key = get_next_api_key()

    for round_num in range(max_rounds):
        failed_indices = []

        for i, result in enumerate(results):
            if result.get("passed") is None or not result.get("passed"):
                # 검증 수행
                if result.get("image"):
                    source_type = detect_source_type(images[i % len(images)], api_key)
                    validator, _ = get_validator(source_type, api_key)
                    val_result = validator.validate(
                        result["image"], images[i % len(images)]
                    )
                    result["score"] = val_result.total_score
                    result["passed"] = val_result.passed
                    result["grade"] = val_result.grade
                    result["issues"] = val_result.issues

                    if not val_result.passed:
                        failed_indices.append(i)

        if not failed_indices:
            print(f"[SWEEP] Round {round_num + 1}: All passed!")
            break

        print(
            f"[SWEEP] Round {round_num + 1}: {len(failed_indices)} failed, retrying..."
        )

        # 실패분 재생성 (Quality 모드로)
        for idx in failed_indices:
            api_key = get_next_api_key()
            new_result = generate_with_validation(
                images[idx % len(images)],
                background_style,
                api_key,
                max_retries=1,
                initial_temperature=0.1,
                image_size=image_size,
            )

            if new_result.get("image"):
                output_path = os.path.join(
                    output_dir,
                    f"result_{idx:03d}_sweep{round_num}_{datetime.now().strftime('%H%M%S')}.png",
                )
                new_result["image"].save(output_path, "PNG")
                new_result["output_path"] = output_path
                del new_result["image"]

            results[idx] = new_result

    return results


__all__ = [
    "swap",
    "generate_background_swap",
    "generate_with_validation",
    "SwapResult",
    "BatchResult",
    "BatchProcessor",
]
