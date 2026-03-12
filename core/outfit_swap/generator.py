"""
Outfit Swap Generator

착장 스왑 이미지 생성 모듈 (생성 + 검증 루프 포함)

4단계 패턴:
1. 소스 분석 (VLM) - 얼굴/포즈/배경 추출
2. 착장 분석 (VLM) - 착장 아이템 정보 추출
3. 생성 (IMAGE) - gemini-3-pro-image-preview 사용
4. 검수+재생성 루프 - 탈락 시 재생성 (최대 max_retries회)

Pass 기준: total_score >= 92
착장 이미지 최대: 10개
"""

import time
from io import BytesIO
from typing import Any, Optional

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.api import _get_next_api_key
from core.options import detect_aspect_ratio
from .analyzer import analyze_source_for_swap, analyze_outfit_items, pil_to_part
from .prompt_builder import build_outfit_swap_prompt
from .validator import OutfitSwapValidator, PASS_TOTAL, ENHANCEMENT_RULES


# ============================================================
# 최대 착장 이미지 수
# ============================================================
MAX_OUTFIT_IMAGES = 10

# ============================================================
# 내부 헬퍼
# ============================================================


def _load_image(img_input: "Image.Image | str") -> Image.Image:
    """PIL Image 또는 경로를 PIL Image로 변환"""
    if isinstance(img_input, str):
        return Image.open(img_input).convert("RGB")
    return img_input


def _resolve_aspect_ratio(aspect_ratio: str, source_image: Image.Image) -> str:
    """aspect_ratio 값 해석: "auto"면 소스 이미지 비율 자동 감지"""
    if aspect_ratio.lower() in ("auto", "original"):
        detected = detect_aspect_ratio(source_image)
        print(
            f"[outfit_swap] 비율 자동 감지: {source_image.size[0]}x{source_image.size[1]} -> {detected}"
        )
        return detected
    return aspect_ratio


def _generate_single(
    source_image: Image.Image,
    outfit_images: list,
    prompt: str,
    client: Any,
    temperature: float,
    aspect_ratio: str,
    resolution: str,
) -> Optional[Image.Image]:
    """
    단일 이미지 생성 (내부 함수)

    소스 이미지 + 착장 이미지들을 API에 전달하여 생성한다.

    Returns:
        생성된 PIL Image, 실패 시 None
    """
    # 비율 자동 감지
    resolved_ratio = _resolve_aspect_ratio(aspect_ratio, source_image)

    # Parts 조립: 프롬프트 텍스트 + 소스 이미지 + 착장 이미지들
    parts = [types.Part(text=prompt)]
    parts.append(
        types.Part(
            text="[SOURCE IMAGE - EDITING CANVAS] Preserve EVERYTHING (face, pose, background, scale). Change ONLY clothing."
        )
    )
    parts.append(pil_to_part(source_image))

    for i, outfit_img in enumerate(outfit_images):
        parts.append(
            types.Part(
                text=f"[OUTFIT REFERENCE {i + 1}] Extract garment ONLY. IGNORE pose/face/background in this image."
            )
        )
        parts.append(pil_to_part(outfit_img))

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=resolved_ratio,
                    image_size=resolution,
                ),
            ),
        )

        # 이미지 파트 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data))

    except Exception as e:
        print(f"[outfit_swap] 생성 실패: {e}")

    return None


def _build_enhanced_prompt(
    base_prompt: str,
    failed_criteria: list,
) -> str:
    """
    이전 시도 실패 기준에 따른 강화 프롬프트 생성

    Args:
        base_prompt: 기본 프롬프트
        failed_criteria: 실패한 기준 키 목록

    Returns:
        강화된 프롬프트 문자열
    """
    if not failed_criteria:
        return base_prompt

    enhancement_lines = ["[ENHANCEMENT - 이전 시도 실패 원인 수정]"]
    for criterion in failed_criteria:
        rules = ENHANCEMENT_RULES.get(criterion, [])
        for rule in rules:
            enhancement_lines.append(f"- {rule}")

    enhancement_section = "\n".join(enhancement_lines)
    return f"{base_prompt}\n\n{enhancement_section}"


# ============================================================
# 공개 인터페이스
# ============================================================


def generate_outfit_swap(
    source_image: "Image.Image | str",
    outfit_images: "list[Image.Image | str]",
    client: Any,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> Image.Image:
    """
    착장 스왑 이미지 생성 (검증 없음)

    1단계: 소스 이미지 분석 (얼굴/포즈/배경)
    2단계: 착장 아이템 분석 (색상/소재/로고/디테일)
    3단계: 드레이핑 고려 프롬프트 조립
    4단계: IMAGE_MODEL로 생성

    Args:
        source_image: 소스 이미지 (PIL Image 또는 파일 경로)
                      얼굴/포즈/배경이 보존될 기준 이미지
        outfit_images: 착장 이미지 목록 (PIL Image 또는 파일 경로, 최대 10개)
        client: Gemini API 클라이언트 (genai.Client)
        temperature: 생성 온도 (0.0~1.0, 기본값 0.2)
        aspect_ratio: 이미지 비율 (기본값 "3:4")
        resolution: 해상도 (기본값 "2K")

    Returns:
        생성된 PIL Image

    Raises:
        ValueError: 착장 이미지가 없거나 생성 실패 시
    """
    # 착장 이미지 최대 10개 제한
    if len(outfit_images) > MAX_OUTFIT_IMAGES:
        print(
            f"[outfit_swap] 착장 이미지 수 초과 ({len(outfit_images)}개 -> {MAX_OUTFIT_IMAGES}개로 제한)"
        )
        outfit_images = outfit_images[:MAX_OUTFIT_IMAGES]

    if not outfit_images:
        raise ValueError(
            "[outfit_swap] 착장 이미지가 없습니다. 최소 1개 이상 필요합니다."
        )

    # 소스 이미지 로드
    source_pil = _load_image(source_image)

    # 착장 이미지 로드
    outfit_pils = [_load_image(img) for img in outfit_images]

    # 1. 소스 분석 (VLM)
    print("[outfit_swap] 소스 이미지 분석 중...")
    source_analysis = analyze_source_for_swap(source_pil, client)
    print(f"  - 얼굴: {source_analysis.get('face_description', 'N/A')}")
    print(f"  - 포즈: {source_analysis.get('pose_description', 'N/A')}")

    # 2. 착장 분석 (VLM)
    print(f"[outfit_swap] 착장 이미지 {len(outfit_pils)}개 분석 중...")
    outfit_analyses = analyze_outfit_items(outfit_pils, client)
    for i, item in enumerate(outfit_analyses):
        logo_info = f" (로고: {item['logo']})" if item.get("logo") else ""
        print(
            f"  - 착장 {i + 1}: {item.get('item_type', 'N/A')} / {item.get('color', 'N/A')}{logo_info}"
        )

    # 3. 프롬프트 조립 (드레이핑 고려)
    prompt = build_outfit_swap_prompt(
        source_analysis=source_analysis,
        outfit_analyses=outfit_analyses,
    )
    print(f"[outfit_swap] 프롬프트 완성 ({len(prompt)}자)")

    # 4. 생성
    print("[outfit_swap] 이미지 생성 중...")
    generated = _generate_single(
        source_image=source_pil,
        outfit_images=outfit_pils,
        prompt=prompt,
        client=client,
        temperature=temperature,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )

    if generated is None:
        raise ValueError("[outfit_swap] 이미지 생성에 실패했습니다.")

    return generated


def generate_with_validation(
    source_image: "Image.Image | str",
    outfit_images: "list[Image.Image | str]",
    client: Any | None = None,
    api_key: str | None = None,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """
    착장 스왑 이미지 생성 + 검증 루프 (공개 API)

    4단계 패턴:
    1. 소스 분석 - 얼굴/포즈/배경
    2. 착장 분석 - 아이템 정보
    3. 생성
    4. 검수 + 재생성 (최대 max_retries회)

    Pass 기준: total_score >= 92

    Args:
        source_image: 소스 이미지 (PIL Image 또는 파일 경로)
        outfit_images: 착장 이미지 목록 (최대 10개)
        client: Gemini API 클라이언트 (없으면 api_key로 생성)
        api_key: API 키 (없으면 자동 로테이션)
        max_retries: 최대 재시도 횟수 (기본값 2)
        temperature: 생성 온도 (기본값 0.2)
        aspect_ratio: 이미지 비율 (기본값 "3:4")
        resolution: 해상도 (기본값 "2K")

    Returns:
        dict with keys:
            image (PIL.Image): 생성된 이미지 (실패 시 마지막 생성 이미지 또는 None)
            score (int): 검수 총점 (0~100)
            passed (bool): 통과 여부 (total_score >= 92)
            criteria (dict): 기준별 점수 {outfit_accuracy, face_identity, ...}
            history (list): 시도별 이력 [{attempt, score, passed, criteria, issues}, ...]
    """
    # 착장 이미지 최대 10개 제한
    if len(outfit_images) > MAX_OUTFIT_IMAGES:
        print(
            f"[outfit_swap] 착장 이미지 수 초과 ({len(outfit_images)}개 -> {MAX_OUTFIT_IMAGES}개로 제한)"
        )
        outfit_images = outfit_images[:MAX_OUTFIT_IMAGES]

    if not outfit_images:
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "history": [
                {"attempt": 0, "status": "error", "issues": ["착장 이미지가 없습니다."]}
            ],
        }

    # 클라이언트 초기화
    if client is None:
        key = api_key or _get_next_api_key()
        client = genai.Client(api_key=key)

    # 소스/착장 이미지 로드
    source_pil = _load_image(source_image)
    outfit_pils = [_load_image(img) for img in outfit_images]

    history = []
    last_generated: Optional[Image.Image] = None
    last_score = 0
    last_criteria: dict = {}

    # 1. 소스 분석
    print("[outfit_swap] 소스 이미지 분석 중...")
    source_analysis = analyze_source_for_swap(source_pil, client)

    # 2. 착장 분석
    print(f"[outfit_swap] 착장 이미지 {len(outfit_pils)}개 분석 중...")
    outfit_analyses = analyze_outfit_items(outfit_pils, client)

    # 3. 기본 프롬프트 조립
    base_prompt = build_outfit_swap_prompt(
        source_analysis=source_analysis,
        outfit_analyses=outfit_analyses,
    )
    print(f"[outfit_swap] 프롬프트 완성 ({len(base_prompt)}자)")

    # 검증기 초기화
    validator = OutfitSwapValidator(client)

    # 4. 생성 + 검수 루프
    current_prompt = base_prompt
    current_temperature = temperature
    failed_criteria: list = []

    for attempt in range(max_retries + 1):
        print(f"\n[outfit_swap] 시도 {attempt + 1}/{max_retries + 1}...")

        # 키 로테이션 (1회 이상 재시도 시)
        if attempt > 0:
            client = genai.Client(api_key=_get_next_api_key())
            validator = OutfitSwapValidator(client)
            # 실패 기준 기반 프롬프트 강화
            current_prompt = _build_enhanced_prompt(base_prompt, failed_criteria)
            # 온도 미세 조정 (너무 높지 않게)
            current_temperature = min(current_temperature + 0.05, 0.4)

        # 생성
        generated = _generate_single(
            source_image=source_pil,
            outfit_images=outfit_pils,
            prompt=current_prompt,
            client=client,
            temperature=current_temperature,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

        if generated is None:
            history.append({"attempt": attempt + 1, "status": "generation_failed"})
            print(f"  [FAIL] 생성 실패")
            # 재시도 전 대기
            if attempt < max_retries:
                wait = (attempt + 1) * 5
                print(f"  {wait}초 대기 후 재시도...")
                time.sleep(wait)
            continue

        last_generated = generated

        # 검수
        print("[outfit_swap] 검수 중...")
        try:
            from pathlib import Path as _Path

            validation_result = validator.validate(
                generated_img=generated,
                reference_images={
                    "source": [source_pil],
                    "outfit": outfit_pils,
                },
            )

            score = validation_result.total_score
            passed = validation_result.passed
            criteria = validation_result.criteria_scores
            issues = validation_result.issues
            auto_fail_reasons = validation_result.auto_fail_reasons

            last_score = score
            last_criteria = criteria

            # 실패한 기준 수집 (다음 재시도 프롬프트 강화용)
            failed_criteria = [
                key
                for key, val in criteria.items()
                if val < validator.config.auto_fail_thresholds.get(key, 0)
            ]
            if not failed_criteria and not passed:
                # Auto-fail 기준 아래는 아니지만 임계값 미달인 기준 수집
                from .validator import THRESHOLDS

                failed_criteria = [
                    key for key, val in criteria.items() if val < THRESHOLDS.get(key, 0)
                ]

            history.append(
                {
                    "attempt": attempt + 1,
                    "score": score,
                    "passed": passed,
                    "criteria": criteria,
                    "issues": issues + auto_fail_reasons,
                }
            )

            print(f"  - 총점: {score}/100 | 통과: {passed}")
            for key, val in criteria.items():
                print(f"    {key}: {val}")

            if passed:
                print(f"[outfit_swap] 검수 통과 (시도 {attempt + 1})")
                return {
                    "image": generated,
                    "score": score,
                    "passed": True,
                    "criteria": criteria,
                    "history": history,
                }

            print(f"  [FAIL] 검수 탈락 - 재시도 예정")

        except Exception as e:
            print(f"  [ERROR] 검수 중 오류: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "status": "validation_error",
                    "issues": [str(e)],
                }
            )

        # 재시도 전 대기
        if attempt < max_retries:
            wait = (attempt + 1) * 5
            print(f"  {wait}초 대기 후 재시도...")
            time.sleep(wait)

    # 최대 재시도 후에도 미통과 - 마지막 결과 반환
    print(f"[outfit_swap] 최대 재시도 초과. 마지막 이미지 반환.")
    return {
        "image": last_generated,
        "score": last_score,
        "passed": False,
        "criteria": last_criteria,
        "history": history,
    }


# ============================================================
# 공개 인터페이스
# ============================================================

__all__ = [
    "generate_outfit_swap",
    "generate_with_validation",
    "MAX_OUTFIT_IMAGES",
]
