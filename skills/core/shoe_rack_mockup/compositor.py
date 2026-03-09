# -*- coding: utf-8 -*-
"""
Compositor - Gemini 인페인팅 엔진
=================================
Gemini API를 사용하여 색상 마스크 영역을 실사 신발로 교체

v0.7 (2026-02-20):
- 실루엣 자동 분석 통합 (silhouette_analyzer)
  - VLM 기반 배치 패턴 자동 감지
  - depth-overlap / side-by-side / single 자동 대응
  - 분석 결과 기반 동적 프롬프트 생성

v0.6 (2026-02-20):
- Stage 2, 3 프롬프트 최적화 완료
  - 모든 스테이지 2켤레(PAIR) 통일
  - 이전 스테이지 결과물 보존 명시
  - 크기 기준 + 경계 오버플로우 방지

v0.5 (2026-02-20):
- Stage 1 프롬프트 최적화 (V4)
  - 2켤레(PAIR) 강조
  - 코랄/흰색 크기 기준 참조
  - 경계 오버플로우 방지

v0.4 (2026-02-20):
- 전체 이미지 인페인팅 방식으로 변경
- 개별 슬롯 생성+붙여넣기 방식 deprecated
- 신발 참조 정확도 개선 (EXACT COPY 강조)

핵심 함수:
- composite_single_stage(): 단일 스테이지 인페인팅
- composite_with_retry(): 재시도 로직 포함
- run_pipeline(): 전체 3단계 파이프라인 (자동 분석 포함)
"""

import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key as get_next_api_key

from .templates import (
    get_stage_prompt,
    get_retry_prompt,
    get_prompt_with_context,
    build_dynamic_prompt,
    build_single_pass_prompt,
    build_slot_inpaint_prompt,
)
from .slot_config import SlotColor, get_colors_by_stage
from .silhouette_analyzer import analyze_silhouette, SilhouetteAnalysis


# 지원되는 비율 목록
SUPPORTED_RATIOS = {
    "1:1": 1.0,
    "3:4": 0.75,
    "4:3": 1.333,
    "2:3": 0.667,
    "3:2": 1.5,
    "9:16": 0.5625,
    "16:9": 1.778,
}


def _get_closest_aspect_ratio(ratio: float) -> str:
    """원본 비율에 가장 가까운 지원 aspect_ratio 반환"""
    closest = "3:4"
    min_diff = float("inf")
    for name, val in SUPPORTED_RATIOS.items():
        diff = abs(ratio - val)
        if diff < min_diff:
            min_diff = diff
            closest = name
    return closest


# =============================================================================
# v3.0 슬롯별 파이프라인 유틸리티 (정면뷰 전용)
# =============================================================================


def _pad_to_supported_ratio(slot_crop: Image.Image, target_ratio: str = None) -> tuple:
    """
    슬롯 크롭 이미지를 API 지원 비율로 패딩

    Gemini API는 특정 비율만 지원 (1:1, 3:4, 4:3, 2:3, 3:2, 9:16, 16:9)
    슬롯 크롭이 지원되지 않는 비율이면 흰색 패딩 추가

    Args:
        slot_crop: 크롭된 슬롯 이미지 (PIL.Image)
        target_ratio: 강제 비율 (None이면 가장 가까운 비율 자동 선택)

    Returns:
        (padded_image, padding_info)
        padding_info = (pad_left, pad_top, pad_right, pad_bottom)
    """
    current_ratio = slot_crop.width / slot_crop.height

    # 가장 가까운 지원 비율 찾기
    if target_ratio is None:
        target_ratio = _get_closest_aspect_ratio(current_ratio)

    target_val = SUPPORTED_RATIOS[target_ratio]

    # 패딩 계산
    if current_ratio > target_val:
        # 너무 넓음 - 세로 패딩 추가
        new_height = int(slot_crop.width / target_val)
        pad_total = new_height - slot_crop.height
        pad_top = pad_total // 2
        pad_bottom = pad_total - pad_top
        pad_left = pad_right = 0
    else:
        # 너무 높음 - 가로 패딩 추가
        new_width = int(slot_crop.height * target_val)
        pad_total = new_width - slot_crop.width
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        pad_top = pad_bottom = 0

    # 패딩된 이미지 생성 (흰색 배경)
    new_size = (
        slot_crop.width + pad_left + pad_right,
        slot_crop.height + pad_top + pad_bottom,
    )
    padded = Image.new("RGB", new_size, (255, 255, 255))
    padded.paste(slot_crop, (pad_left, pad_top))

    return padded, (pad_left, pad_top, pad_right, pad_bottom)


def _unpad_from_result(
    result_img: Image.Image, original_size: tuple, padding_info: tuple
) -> Image.Image:
    """
    API 결과에서 패딩 제거하여 원본 슬롯 크기로 복원

    Args:
        result_img: API 생성 이미지 (패딩된 크기)
        original_size: 원본 슬롯 크기 (width, height)
        padding_info: 패딩 정보 (pad_left, pad_top, pad_right, pad_bottom)

    Returns:
        원본 슬롯 크기로 크롭된 이미지
    """
    pad_left, pad_top, pad_right, pad_bottom = padding_info
    orig_w, orig_h = original_size

    # 스케일 팩터 계산 (API가 다른 크기 반환할 수 있음)
    scale_x = result_img.width / (orig_w + pad_left + pad_right)
    scale_y = result_img.height / (orig_h + pad_top + pad_bottom)

    # 결과 이미지 좌표에서 크롭 박스 계산
    crop_left = int(pad_left * scale_x)
    crop_top = int(pad_top * scale_y)
    crop_right = int((orig_w + pad_left) * scale_x)
    crop_bottom = int((orig_h + pad_top) * scale_y)

    # 크롭 후 원본 크기로 리사이즈
    cropped = result_img.crop((crop_left, crop_top, crop_right, crop_bottom))
    return cropped.resize(original_size, Image.Resampling.LANCZOS)


def blend_slot_edges(
    base_img: Image.Image,
    slot_img: Image.Image,
    bbox: Tuple[int, int, int, int],
    blend_width: int = 5,
) -> Image.Image:
    """
    슬롯 이미지를 베이스 이미지에 페더링 엣지로 블렌딩

    그라디언트 마스크를 사용하여 슬롯 경계의 하드 엣지 방지

    Args:
        base_img: 원본 전체 이미지 (PIL.Image)
        slot_img: 생성된 슬롯 이미지 (PIL.Image)
        bbox: 슬롯 위치 (x, y, w, h)
        blend_width: 블렌딩할 엣지 픽셀 수 (기본: 5)

    Returns:
        블렌딩된 결과 이미지
    """
    x, y, w, h = bbox

    # 슬롯 이미지 크기 확인 및 리사이즈
    if slot_img.size != (w, h):
        slot_img = slot_img.resize((w, h), Image.Resampling.LANCZOS)

    # 너무 작은 슬롯은 블렌딩 없이 직접 붙여넣기
    if w < 3 or h < 3:
        result = base_img.copy()
        result.paste(slot_img, (x, y))
        return result

    # 블렌드 너비가 슬롯 크기의 절반을 넘지 않도록 조정
    actual_blend_w = min(blend_width, w // 2 - 1, h // 2 - 1)
    actual_blend_w = max(1, actual_blend_w)  # 최소 1px

    # 그라디언트 마스크 생성
    mask = np.ones((h, w), dtype=np.float32)

    # 가로 그라디언트 (왼쪽/오른쪽 엣지)
    for i in range(actual_blend_w):
        alpha = i / actual_blend_w
        if i < w:
            mask[:, i] = alpha  # 왼쪽 엣지
        if w - 1 - i >= 0:
            mask[:, w - 1 - i] = alpha  # 오른쪽 엣지

    # 세로 그라디언트 (위/아래 엣지)
    for i in range(actual_blend_w):
        alpha = i / actual_blend_w
        if i < h:
            mask[i, :] = np.minimum(mask[i, :], alpha)  # 위쪽 엣지
        if h - 1 - i >= 0:
            mask[h - 1 - i, :] = np.minimum(mask[h - 1 - i, :], alpha)  # 아래쪽 엣지

    # RGB 블렌딩을 위한 3채널 마스크
    mask_3ch = np.stack([mask] * 3, axis=-1)

    # 알파 블렌딩
    slot_arr = np.array(slot_img.convert("RGB")).astype(np.float32)
    base_crop = np.array(base_img.crop((x, y, x + w, y + h))).astype(np.float32)

    blended = slot_arr * mask_3ch + base_crop * (1 - mask_3ch)
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    # 결과를 베이스 이미지에 붙여넣기
    result = base_img.copy()
    result.paste(Image.fromarray(blended), (x, y))

    return result


def _sample_shelf_color(
    image: Image.Image, bbox: Tuple[int, int, int, int]
) -> Tuple[int, int, int]:
    """
    슬롯 아래 선반 영역의 평균 색상 샘플링

    조명 조화를 위해 신발 색상 조정에 사용

    Args:
        image: 전체 이미지
        bbox: 슬롯 위치 (x, y, w, h)

    Returns:
        평균 색상 (r, g, b)
    """
    x, y, w, h = bbox
    # 슬롯 아래 10px 영역 샘플링
    shelf_y_start = y + h
    shelf_y_end = min(y + h + 10, image.height)

    if shelf_y_end <= shelf_y_start:
        return (255, 255, 255)  # 기본값: 흰색

    shelf_region = image.crop((x, shelf_y_start, x + w, shelf_y_end))
    avg_color = np.array(shelf_region).mean(axis=(0, 1))
    return tuple(avg_color.astype(int))


@dataclass
class CompositeResult:
    """합성 결과"""

    image: Optional[Image.Image]
    success: bool
    stage: int
    attempt: int
    error: Optional[str] = None
    response_text: Optional[str] = None


@dataclass
class PipelineResult:
    """전체 파이프라인 결과"""

    final_image: Optional[Image.Image]
    success: bool
    stages_completed: List[int]
    stage_results: Dict[int, CompositeResult]
    total_attempts: int


def _preprocess_reference_shoes(
    shoe_images: List[Image.Image],
    stage: int,
    scale_ratio: float = 0.65,
) -> List[Image.Image]:
    """
    참조 신발 이미지 전처리 (v1.5)

    Gemini가 프롬프트 지시를 무시하는 문제 해결을 위해:
    1. 크기 축소: 원본의 65%로 리사이즈 (신발이 너무 크게 생성되는 문제)
    2. 방향 조정: stage별로 pre-flip (방향이 틀리는 문제)
    3. 중앙 배치: 흰색 배경 위에 중앙 배치

    Args:
        shoe_images: 원본 참조 신발 이미지 목록
        stage: 처리 스테이지 (1=mint, 2=coral, 3=white)
        scale_ratio: 축소 비율 (기본 0.65 = 65%)

    Returns:
        전처리된 신발 이미지 목록
    """
    processed = []

    for i, img in enumerate(shoe_images):
        # 원본 크기
        orig_w, orig_h = img.size

        # 1. 크기 축소
        new_w = int(orig_w * scale_ratio)
        new_h = int(orig_h * scale_ratio)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 2. Stage별 방향 조정 (mint=left-toe, coral/white=right-toe)
        # 원본 신발 이미지는 left-toe-forward라고 가정
        if stage in [2, 3]:  # coral, white = right-toe (flip)
            resized = resized.transpose(Image.FLIP_LEFT_RIGHT)

        # 3. 흰색 배경 위에 중앙 배치 (패딩 추가)
        # Gemini가 신발을 더 작게 인식하도록 여백 추가
        padding = int(min(new_w, new_h) * 0.2)  # 20% 패딩
        canvas_w = new_w + padding * 2
        canvas_h = new_h + padding * 2
        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

        # RGBA 처리 (투명 배경 있는 경우)
        if resized.mode == "RGBA":
            canvas.paste(resized, (padding, padding), resized)
        else:
            canvas.paste(resized, (padding, padding))

        processed.append(canvas)

    direction = "left-toe" if stage == 1 else "right-toe"
    print(f"  [PREPROCESS] Stage {stage}: {len(processed)} shoes")
    print(f"    Scale: {scale_ratio:.0%}, Direction: {direction}, Padding: 20%")

    return processed


def _flip_shoes_if_needed(
    shoe_images: List[Image.Image],
    direction: str,
    stage: int = None,
) -> List[Image.Image]:
    """
    실루엣 방향에 맞게 신발 이미지 좌우반전

    v1.5: _preprocess_reference_shoes()로 대체 권장
    - 이 함수는 하위 호환성을 위해 유지
    - 새 코드는 _preprocess_reference_shoes() 사용

    v1.4 변경: stage별 방향 적용
    - stage 1 (mint): 항상 left-toe (플립 안함)
    - stage 2 (coral): 항상 right-toe (플립)
    - stage 3 (white): 항상 right-toe (플립)

    Args:
        shoe_images: 참조 신발 이미지 목록
        direction: 실루엣 방향 (legacy, stage 우선)
        stage: 처리 스테이지 (1=mint, 2=coral, 3=white)

    Returns:
        방향 보정된 신발 이미지 목록
    """
    # v1.4: stage별 방향 고정 (열별로 다른 방향)
    # 참조 신발은 left-toe-forward라고 가정
    if stage is not None:
        if stage == 1:  # mint = left-toe (no flip)
            print(f"  [DIRECTION] Stage {stage} (mint): left-toe, no flip")
            return shoe_images
        elif stage in [2, 3]:  # coral, white = right-toe (flip)
            print(f"  [DIRECTION] Stage {stage}: right-toe, flipping shoes")
            return [img.transpose(Image.FLIP_LEFT_RIGHT) for img in shoe_images]

    # Legacy: stage 없으면 direction 기반 (하위 호환)
    if "right" in direction.lower():
        print(f"  [FLIP] Flipping shoes for right-toe-forward direction")
        return [img.transpose(Image.FLIP_LEFT_RIGHT) for img in shoe_images]
    return shoe_images


def composite_single_stage(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    stage: int,
    api_key: Optional[str] = None,
    temperature: float = 0.3,
    previous_stages: Optional[List[int]] = None,
    custom_instructions: str = "",
    silhouette_analysis: Optional[SilhouetteAnalysis] = None,
) -> CompositeResult:
    """
    단일 스테이지 전체 이미지 인페인팅

    방식: 전체 이미지를 Gemini에 보내고 특정 색상 영역만 신발로 교체
    - Gemini가 색상 영역을 인식하고 해당 영역만 인페인팅
    - 슬롯 경계 준수, 배경 100% 보존
    - 실루엣 분석 결과 기반 동적 프롬프트 생성 (v0.7)

    Args:
        input_image: 입력 이미지
        shoe_images: 참조 신발 이미지 목록
        stage: 처리할 스테이지 (1=mint, 2=coral, 3=white)
        api_key: Gemini API 키
        temperature: 생성 온도
        previous_stages: 이전에 완료된 스테이지 목록
        custom_instructions: 추가 지시사항
        silhouette_analysis: 실루엣 분석 결과 (None이면 정적 프롬프트 사용)

    Returns:
        CompositeResult
    """
    if api_key is None:
        api_key = get_next_api_key()

    # 스테이지별 색상 매핑
    stage_colors = {1: "mint", 2: "coral", 3: "white"}
    target_color = stage_colors.get(stage, "mint")

    # 신발 개수 (민트/화이트=2개, 코랄=1개)
    shoes_per_slot = 2 if stage in [1, 3] else 1

    print(f"[STAGE {stage}] Full-image inpainting")
    print(f"  Target color: {target_color}")
    print(f"  Shoes per slot: {shoes_per_slot}")

    # 프롬프트 가져오기 (실루엣 분석 결과 기반 동적 프롬프트 또는 정적 프롬프트)
    if silhouette_analysis:
        print(
            f"  Using dynamic prompt (arrangement: {silhouette_analysis.arrangement})"
        )
        prompt = build_dynamic_prompt(
            stage=stage,
            arrangement=silhouette_analysis.arrangement,
            arrangement_description=silhouette_analysis.arrangement_description,
            shoes_per_slot=silhouette_analysis.shoes_per_slot,
            direction=silhouette_analysis.direction,
            previous_stages_done=previous_stages,
        )
        if custom_instructions:
            prompt += f"\n\n{custom_instructions}"
    else:
        prompt = get_prompt_with_context(
            stage=stage,
            previous_stages_done=previous_stages,
            custom_instructions=custom_instructions,
        )

    # Gemini 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # 원본 이미지 비율 계산
    original_ratio = input_image.width / input_image.height
    aspect_ratio = _get_closest_aspect_ratio(original_ratio)

    print(f"  Original size: {input_image.width}x{input_image.height}")
    print(f"  Aspect ratio: {aspect_ratio}")

    # v1.5: 참조 신발 전처리 (크기 축소 + 방향 조정 + 패딩)
    # Gemini가 프롬프트를 무시하는 문제 해결: 이미지 자체를 사전 조정
    processed_shoes = _preprocess_reference_shoes(
        shoe_images=shoe_images,
        stage=stage,
        scale_ratio=0.65,  # 65% 크기로 축소
    )

    # 컨텐츠 구성: 프롬프트 + 원본 이미지 + 참조 신발 이미지들
    contents = [prompt, input_image]

    # 참조 신발 이미지 추가 (최대 6개)
    for i, shoe in enumerate(processed_shoes[:6]):
        contents.append(f"Reference Shoe {i+1}:")
        contents.append(shoe)

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size="2K",
                ),
            ),
        )

        # 응답에서 이미지 추출
        response_text = None
        result_image = None

        for part in response.candidates[0].content.parts:
            if part.text:
                response_text = part.text
            if part.inline_data is not None:
                image_data = part.inline_data.data
                result_image = Image.open(io.BytesIO(image_data))

        if result_image:
            print(f"[STAGE {stage}] SUCCESS - Inpainting complete")
            print(f"  Result size: {result_image.width}x{result_image.height}")
            return CompositeResult(
                image=result_image,
                success=True,
                stage=stage,
                attempt=1,
                response_text=response_text,
            )
        else:
            print(f"[STAGE {stage}] FAILED - No image in response")
            return CompositeResult(
                image=None,
                success=False,
                stage=stage,
                attempt=1,
                error="No image generated",
                response_text=response_text,
            )

    except Exception as e:
        print(f"[STAGE {stage}] ERROR: {e}")
        return CompositeResult(
            image=None,
            success=False,
            stage=stage,
            attempt=1,
            error=str(e),
        )


# =============================================================================
# DEPRECATED FUNCTIONS (v0.3 이전 방식 - 개별 슬롯 생성+붙여넣기)
# 참고용으로 남겨둠. 새 코드에서는 composite_single_stage() 사용
# =============================================================================


def _generate_shoes_for_slot(
    client,
    shoe_reference: Image.Image,
    slot_width: int,
    slot_height: int,
    num_shoes: int,
    temperature: float,
) -> Optional[Image.Image]:
    """[DEPRECATED] 슬롯에 맞는 신발 이미지 생성 (투명 배경)

    Note: v0.3부터 사용 안 함. composite_single_stage()가 전체 이미지 인페인팅 방식으로 대체.
    """

    prompt = f"""Generate {num_shoes} realistic sneaker(s) based on the reference shoe.

REQUIREMENTS:
- Output: {num_shoes} shoe(s) {"side by side (left + right of a pair)" if num_shoes == 2 else "(single shoe, angled view)"}
- Background: Pure white (#FFFFFF) or transparent
- View: 3/4 perspective, showing the shoe from slightly above
- Style: Photorealistic product shot with soft shadows
- Size: Fit within {slot_width}x{slot_height} pixels area

Copy the EXACT design from the reference shoe (colors, logo, style)."""

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[prompt, shoe_reference],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1" if num_shoes == 1 else "3:2",
                    image_size="1K",
                ),
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                return Image.open(io.BytesIO(image_data))

    except Exception as e:
        print(f"    [ERROR] Shoe generation failed: {e}")

    return None


def _paste_shoes_on_slot(
    base_image: Image.Image,
    shoes_image: Image.Image,
    slot_bbox: tuple,
) -> Image.Image:
    """[DEPRECATED] 신발 이미지를 슬롯 위치에 합성

    Note: v0.3부터 사용 안 함.
    """
    x, y, w, h = slot_bbox

    # 슬롯 크기에 맞게 리사이즈
    shoes_resized = shoes_image.resize((w, h), Image.Resampling.LANCZOS)

    # RGBA 변환 (투명도 처리)
    if shoes_resized.mode != "RGBA":
        shoes_resized = shoes_resized.convert("RGBA")

    # 흰색 배경을 투명으로 변환
    shoes_resized = _remove_white_background(shoes_resized)

    # 합성
    result = base_image.copy()
    if result.mode != "RGBA":
        result = result.convert("RGBA")

    result.paste(shoes_resized, (x, y), shoes_resized)

    return result.convert("RGB")


def _remove_white_background(image: Image.Image, threshold: int = 240) -> Image.Image:
    """[DEPRECATED] 흰색 배경을 투명으로 변환

    Note: v0.3부터 사용 안 함.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    data = image.getdata()
    new_data = []

    for item in data:
        # 흰색에 가까우면 투명으로
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    image.putdata(new_data)
    return image


def composite_with_retry(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    stage: int,
    max_retries: int = 2,
    api_key: Optional[str] = None,
    previous_stages: Optional[List[int]] = None,
    silhouette_analysis: Optional[SilhouetteAnalysis] = None,
) -> CompositeResult:
    """
    재시도 로직 포함 인페인팅

    Args:
        input_image: 입력 이미지
        shoe_images: 참조 신발 이미지 목록
        stage: 처리할 스테이지
        max_retries: 최대 재시도 횟수
        api_key: API 키
        previous_stages: 이전 완료 스테이지
        silhouette_analysis: 실루엣 분석 결과 (v0.7)

    Returns:
        CompositeResult
    """
    last_result = None
    temperatures = [0.3, 0.25, 0.2]  # 재시도 시 온도 낮춤

    for attempt in range(max_retries + 1):
        temp = temperatures[min(attempt, len(temperatures) - 1)]

        if attempt == 0:
            # 첫 시도
            result = composite_single_stage(
                input_image=input_image,
                shoe_images=shoe_images,
                stage=stage,
                api_key=api_key,
                temperature=temp,
                previous_stages=previous_stages,
                silhouette_analysis=silhouette_analysis,
            )
        else:
            # 재시도 - 이전 실패 사유 기반 프롬프트 강화
            issues = []
            if last_result and last_result.error:
                issues.append(last_result.error)

            # 재시도 대기
            wait_time = (attempt + 1) * 5
            print(f"[RETRY] Waiting {wait_time}s before retry {attempt + 1}...")
            time.sleep(wait_time)

            result = composite_single_stage(
                input_image=input_image,
                shoe_images=shoe_images,
                stage=stage,
                api_key=api_key,
                temperature=temp,
                previous_stages=previous_stages,
                custom_instructions=f"Previous attempt failed. Please ensure complete replacement.",
                silhouette_analysis=silhouette_analysis,
            )

        result.attempt = attempt + 1

        if result.success:
            return result

        last_result = result
        print(f"[STAGE {stage}] Attempt {attempt + 1} failed")

    # 모든 재시도 실패
    return last_result or CompositeResult(
        image=None,
        success=False,
        stage=stage,
        attempt=max_retries + 1,
        error="All retries exhausted",
    )


def run_pipeline(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    stages: List[int] = None,
    max_retries_per_stage: int = 2,
    api_key: Optional[str] = None,
    auto_analyze: bool = True,
) -> PipelineResult:
    """
    전체 3단계 파이프라인 실행

    Args:
        input_image: 원본 신발장 이미지
        shoe_images: 참조 신발 이미지 목록
        stages: 실행할 스테이지 목록 (기본: [1, 2, 3])
        max_retries_per_stage: 스테이지별 최대 재시도
        api_key: API 키
        auto_analyze: VLM으로 실루엣 자동 분석 여부 (기본: True)

    Returns:
        PipelineResult
    """
    if stages is None:
        stages = [1, 2, 3]

    current_image = input_image.copy()
    completed_stages: List[int] = []
    stage_results: Dict[int, CompositeResult] = {}
    total_attempts = 0

    print("=" * 60)
    print("SHOE RACK MOCKUP PIPELINE")
    print(f"Stages to process: {stages}")
    print("=" * 60)

    # 실루엣 자동 분석 (v0.7)
    silhouette_analysis = None
    if auto_analyze:
        print("\n--- STEP 0: Silhouette Analysis ---")
        try:
            silhouette_analysis = analyze_silhouette(input_image, api_key=api_key)
            print(f"  Arrangement: {silhouette_analysis.arrangement}")
            print(f"  Direction: {silhouette_analysis.direction}")
            print(f"  Shoes per slot: {silhouette_analysis.shoes_per_slot}")
            print(f"  Description: {silhouette_analysis.arrangement_description}")
        except Exception as e:
            print(f"  [WARNING] Silhouette analysis failed: {e}")
            print("  Using default static prompts")

    for stage in stages:
        print(f"\n--- STAGE {stage} ---")

        result = composite_with_retry(
            input_image=current_image,
            shoe_images=shoe_images,
            stage=stage,
            max_retries=max_retries_per_stage,
            api_key=api_key,
            previous_stages=completed_stages.copy(),
            silhouette_analysis=silhouette_analysis,
        )

        stage_results[stage] = result
        total_attempts += result.attempt

        if result.success and result.image:
            current_image = result.image
            completed_stages.append(stage)
            print(f"[STAGE {stage}] COMPLETED (attempts: {result.attempt})")
        else:
            print(f"[STAGE {stage}] FAILED after {result.attempt} attempts")
            # 실패 시 파이프라인 중단
            return PipelineResult(
                final_image=current_image if completed_stages else None,
                success=False,
                stages_completed=completed_stages,
                stage_results=stage_results,
                total_attempts=total_attempts,
            )

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Stages completed: {completed_stages}")
    print(f"Total attempts: {total_attempts}")
    print("=" * 60)

    return PipelineResult(
        final_image=current_image,
        success=True,
        stages_completed=completed_stages,
        stage_results=stage_results,
        total_attempts=total_attempts,
    )


# =============================================================================
# v2.0 단일 패스 파이프라인 (모든 색상 한 번에 처리)
# =============================================================================


def composite_single_pass(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    api_key: Optional[str] = None,
    temperature: float = 0.3,
    silhouette_analysis: Optional[SilhouetteAnalysis] = None,
    has_mirror: bool = False,
    mirror_side: str = "left",
    view_type: str = "side",
    num_columns_override: Optional[int] = None,  # v3.2: VLM 감지 대신 수동 지정
) -> CompositeResult:
    """
    단일 패스 전체 이미지 인페인팅 (v2.0)

    모든 색상 실루엣(민트, 코랄, 흰색)을 한 번에 신발로 교체
    - 3단계 방식의 "이전 스테이지 보존 실패" 문제 해결
    - 한 번의 API 호출로 전체 교체

    Args:
        input_image: 원본 신발장 이미지 (색상 실루엣 포함)
        shoe_images: 참조 신발 이미지 목록 (최대 18개)
        api_key: Gemini API 키
        temperature: 생성 온도
        silhouette_analysis: 실루엣 분석 결과

    Returns:
        CompositeResult
    """
    if api_key is None:
        api_key = get_next_api_key()

    print("[SINGLE PASS] Full-image inpainting - all colors at once")

    # 기본 분석 결과 (없으면 기본값 사용)
    if silhouette_analysis is None:
        arrangement = "depth-overlap"
        arrangement_description = "2 shoes with depth perspective"
        shoes_per_slot = 2
        direction = "left-toe-forward"
    else:
        arrangement = silhouette_analysis.arrangement
        arrangement_description = silhouette_analysis.arrangement_description
        shoes_per_slot = silhouette_analysis.shoes_per_slot
        direction = silhouette_analysis.direction

    print(f"  Arrangement: {arrangement}")
    print(f"  Direction: {direction}")
    print(f"  Shoes per slot: {shoes_per_slot}")
    if silhouette_analysis:
        print(f"  Colors present: {silhouette_analysis.colors_present}")
        print(f"  Num columns: {silhouette_analysis.num_columns}")

    # v2.1: 색상 열 정보 추출
    colors_present = None
    num_columns = 3
    column_layout = None
    if silhouette_analysis:
        colors_present = silhouette_analysis.colors_present
        num_columns = silhouette_analysis.num_columns
        column_layout = silhouette_analysis.column_layout

    # v3.2: num_columns_override가 있으면 VLM 감지 대신 수동 지정값 사용
    # (기둥에 가린 신발이 있어 VLM이 잘못 감지하는 경우 대응)
    if num_columns_override is not None:
        print(f"  [OVERRIDE] num_columns: {num_columns} -> {num_columns_override}")
        num_columns = num_columns_override

    # v3.1: 슬롯-신발 매핑 생성 (중복 방지)
    # 열 우선 순서: Col1의 Row1~6 → Col2의 Row1~6 → ...
    num_rows = 6  # 고정값
    total_slots = num_columns * num_rows
    slot_shoe_mapping = []

    # 사용 가능한 신발 수에 맞춰 순환 할당
    num_shoes = len(shoe_images)

    slot_num = 1
    for col in range(1, num_columns + 1):
        for row in range(1, num_rows + 1):
            # 신발 번호: 1부터 시작, 순환
            ref_num = ((slot_num - 1) % num_shoes) + 1
            slot_shoe_mapping.append(
                {
                    "slot": slot_num,
                    "row": row,
                    "col": col,
                    "ref": ref_num,
                }
            )
            slot_num += 1

    print(f"  [MAPPING] {total_slots} slots → {num_shoes} unique shoes (cycled)")

    # 단일 패스 프롬프트 생성 (동적 색상 열 지원 + 거울 모드 + 뷰 타입 + 슬롯 매핑)
    prompt = build_single_pass_prompt(
        arrangement=arrangement,
        arrangement_description=arrangement_description,
        shoes_per_slot=shoes_per_slot,
        direction=direction,
        colors_present=colors_present,
        num_columns=num_columns,
        column_layout=column_layout,
        has_mirror=has_mirror,
        mirror_side=mirror_side,
        view_type=view_type,
        slot_shoe_mapping=slot_shoe_mapping,
        num_rows=num_rows,
    )

    if has_mirror:
        print(f"  Mirror mode: {mirror_side} side is mirror")
    print(f"  View type: {view_type}")

    # Gemini 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # 원본 이미지 비율 계산
    original_ratio = input_image.width / input_image.height
    aspect_ratio = _get_closest_aspect_ratio(original_ratio)

    print(f"  Original size: {input_image.width}x{input_image.height}")
    print(f"  Aspect ratio: {aspect_ratio}")

    # v3.0: 참조 신발 전처리 - 측면 뷰는 방향 미리 플립 + 더 많은 참조 전송
    # 측면 뷰에서 중복 신발 문제 해결을 위해 참조 수 늘림 (6개 → 18개)
    processed_shoes = []

    # v3.2: 측면 뷰 방향 결정
    # 참조 신발 이미지 폴더: side_view_left_toe (발끝이 왼쪽)
    # - 실루엣이 left-toe-forward면: 플립 불필요 (참조와 동일)
    # - 실루엣이 right-toe-forward면: 플립 필요 (참조 반전)
    should_flip = False
    if view_type == "side":
        if silhouette_analysis and "right" in silhouette_analysis.direction.lower():
            should_flip = True  # right-toe 실루엣 → 참조 신발 플립 필요
        # left-toe 또는 분석 없으면 플립 안함 (참조가 이미 left-toe)

    for i, shoe in enumerate(shoe_images):
        # 크기만 축소 (65%)
        orig_w, orig_h = shoe.size
        scale_ratio = 0.65
        new_w = int(orig_w * scale_ratio)
        new_h = int(orig_h * scale_ratio)
        resized = shoe.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # v3.0: 측면 뷰는 방향 미리 플립 (프롬프트 의존하지 않음)
        if view_type == "side" and should_flip:
            resized = resized.transpose(Image.FLIP_LEFT_RIGHT)

        # 패딩 추가
        padding = int(min(new_w, new_h) * 0.2)
        canvas = Image.new(
            "RGB", (new_w + padding * 2, new_h + padding * 2), (255, 255, 255)
        )
        if resized.mode == "RGBA":
            canvas.paste(resized, (padding, padding), resized)
        else:
            canvas.paste(resized, (padding, padding))
        processed_shoes.append(canvas)

    flip_status = "FLIPPED" if (view_type == "side" and should_flip) else "NO FLIP"
    print(f"  [PREPROCESS] Single pass: {len(processed_shoes)} shoes, {flip_status}")

    # 컨텐츠 구성: 프롬프트 + 원본 이미지 + 참조 신발 이미지들
    contents = [prompt, input_image]

    # v3.0: 참조 신발 수 늘림 - 측면 뷰는 18개, 정면 뷰는 12개
    # 중복 신발 문제 해결
    if view_type == "side":
        max_refs = min(18, len(processed_shoes))  # 측면: 최대 18개
    else:
        max_refs = min(12, len(processed_shoes))  # 정면: 최대 12개

    for i, shoe in enumerate(processed_shoes[:max_refs]):
        contents.append(f"Reference {i+1}:")
        contents.append(shoe)

    print(f"  [REFS] Sending {max_refs} reference shoes to API")

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size="2K",
                ),
            ),
        )

        # 응답에서 이미지 추출
        response_text = None
        result_image = None

        for part in response.candidates[0].content.parts:
            if part.text:
                response_text = part.text
            if part.inline_data is not None:
                image_data = part.inline_data.data
                result_image = Image.open(io.BytesIO(image_data))

        if result_image:
            print("[SINGLE PASS] SUCCESS - All silhouettes replaced")
            print(f"  Result size: {result_image.width}x{result_image.height}")
            return CompositeResult(
                image=result_image,
                success=True,
                stage=0,  # 단일 패스는 스테이지 0으로 표시
                attempt=1,
                response_text=response_text,
            )
        else:
            print("[SINGLE PASS] FAILED - No image in response")
            return CompositeResult(
                image=None,
                success=False,
                stage=0,
                attempt=1,
                error="No image generated",
                response_text=response_text,
            )

    except Exception as e:
        print(f"[SINGLE PASS] ERROR: {e}")
        return CompositeResult(
            image=None,
            success=False,
            stage=0,
            attempt=1,
            error=str(e),
        )


def run_single_pass_pipeline(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    max_retries: int = 2,
    api_key: Optional[str] = None,
    auto_analyze: bool = True,
    has_mirror: bool = False,
    mirror_side: str = "left",
    view_type: str = "side",  # "front" (3~7번) or "side" (2, 8번)
    num_columns_override: Optional[int] = None,  # v3.2: VLM 감지 대신 수동 지정
) -> PipelineResult:
    """
    단일 패스 파이프라인 실행 (v2.0)

    3단계 방식 대신 한 번에 모든 색상 실루엣을 교체
    - 이전 스테이지 결과 보존 문제 없음
    - 더 일관된 결과물

    Args:
        input_image: 원본 신발장 이미지
        shoe_images: 참조 신발 이미지 목록 (18개 권장)
        max_retries: 최대 재시도 횟수
        api_key: API 키
        auto_analyze: VLM으로 실루엣 자동 분석 여부

    Returns:
        PipelineResult
    """
    print("=" * 60)
    print("SHOE RACK MOCKUP - SINGLE PASS PIPELINE (v2.0)")
    print("=" * 60)

    # 실루엣 자동 분석
    silhouette_analysis = None
    if auto_analyze:
        print("\n--- STEP 0: Silhouette Analysis ---")
        try:
            silhouette_analysis = analyze_silhouette(input_image, api_key=api_key)
            print(f"  Arrangement: {silhouette_analysis.arrangement}")
            print(f"  Direction: {silhouette_analysis.direction}")
            print(f"  Shoes per slot: {silhouette_analysis.shoes_per_slot}")
            print(f"  Description: {silhouette_analysis.arrangement_description}")
        except Exception as e:
            print(f"  [WARNING] Silhouette analysis failed: {e}")
            print("  Using default settings")

    # v3.0: 정면 뷰는 슬롯별 파이프라인으로 라우팅
    if view_type == "front":
        print("\n--- FRONT VIEW DETECTED: Using Slot-by-Slot Pipeline (v3.0) ---")
        try:
            from .slot_detector import detect_slots_from_image

            # 슬롯 감지
            slots_dict = detect_slots_from_image(input_image)

            # 딕셔너리를 리스트로 변환 (mint + white)
            # 노이즈 필터 적용하여 유효한 슬롯만 추출
            all_slots = []
            for color, slots in slots_dict.items():
                if color == "mint":
                    # 민트는 비교적 정확하게 감지됨
                    for slot in slots:
                        x, y, w, h = slot.bbox
                        if w >= 50 and h >= 30:
                            all_slots.append(slot)
                elif color == "white":
                    # 흰색은 선반 노이즈 때문에 더 엄격한 필터 적용
                    # 실제 신발 실루엣은 큰 영역 (200+ width, 50+ height)
                    for slot in slots:
                        x, y, w, h = slot.bbox
                        if w >= 200 and h >= 50:  # 큰 슬롯만
                            all_slots.append(slot)

            # 위치 순 정렬
            all_slots.sort(
                key=lambda s: (s.position_id if hasattr(s, "position_id") else str(s))
            )

            print(f"  Detected {len(all_slots)} slots for front view")

            if all_slots:
                return run_slot_by_slot_pipeline(
                    input_image=input_image,
                    shoe_images=shoe_images,
                    detected_slots=all_slots,
                    api_key=api_key,
                    max_retries=max_retries,
                    parallel=True,
                    max_workers=4,
                )
            else:
                print("  [WARNING] No slots detected, falling back to single-pass")
        except Exception as e:
            print(f"  [ERROR] Slot-by-slot failed: {e}")
            print("  Falling back to single-pass pipeline")

    # 단일 패스 실행 (측면 뷰 또는 폴백)
    last_result = None
    temperatures = [0.3, 0.25, 0.2]

    for attempt in range(max_retries + 1):
        print(f"\n--- SINGLE PASS (Attempt {attempt + 1}/{max_retries + 1}) ---")

        temp = temperatures[min(attempt, len(temperatures) - 1)]

        result = composite_single_pass(
            input_image=input_image,
            shoe_images=shoe_images,
            api_key=api_key,
            temperature=temp,
            silhouette_analysis=silhouette_analysis,
            has_mirror=has_mirror,
            mirror_side=mirror_side,
            view_type=view_type,
            num_columns_override=num_columns_override,  # v3.2: VLM 우회
        )

        result.attempt = attempt + 1

        if result.success:
            print("\n" + "=" * 60)
            print("SINGLE PASS PIPELINE COMPLETED SUCCESSFULLY")
            print(f"Total attempts: {attempt + 1}")
            print("=" * 60)

            return PipelineResult(
                final_image=result.image,
                success=True,
                stages_completed=[0],  # 단일 패스는 [0]
                stage_results={0: result},
                total_attempts=attempt + 1,
            )

        last_result = result
        print(f"[SINGLE PASS] Attempt {attempt + 1} failed")

        if attempt < max_retries:
            wait_time = (attempt + 1) * 5
            print(f"  Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

    # 모든 재시도 실패
    print("\n" + "=" * 60)
    print("SINGLE PASS PIPELINE FAILED")
    print(f"Total attempts: {max_retries + 1}")
    print("=" * 60)

    return PipelineResult(
        final_image=None,
        success=False,
        stages_completed=[],
        stage_results={0: last_result} if last_result else {},
        total_attempts=max_retries + 1,
    )


def save_pipeline_results(
    result: PipelineResult,
    output_dir: Path,
    original_image: Image.Image,
    prefix: str = "",
):
    """파이프라인 결과 저장 (v0.9: comparison 이미지 제거)"""
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    # 최종 이미지 저장
    if result.final_image:
        final_path = output_dir / f"{prefix}final_mockup.png"
        result.final_image.save(final_path)
        saved_files.append(final_path)
        print(f"[SAVED] Final: {final_path}")

    # 스테이지별 결과 저장
    for stage, stage_result in result.stage_results.items():
        if stage_result.image:
            stage_path = output_dir / f"{prefix}stage{stage}_result.png"
            stage_result.image.save(stage_path)
            saved_files.append(stage_path)
            print(f"[SAVED] Stage {stage}: {stage_path}")

    return saved_files


# =============================================================================
# v3.0 슬롯별 파이프라인 (정면뷰 전용 - 겹침 문제 해결)
# =============================================================================


def composite_single_slot(
    slot_crop: Image.Image,
    left_ref: Image.Image,
    right_ref: Image.Image,
    slot_color: str = "mint",
    api_key: Optional[str] = None,
    temperature: float = 0.25,
) -> CompositeResult:
    """
    단일 슬롯에 2개 신발 생성 (정면뷰용)

    API 비율 제약을 내부에서 처리 (패딩/언패딩)

    Args:
        slot_crop: 크롭된 슬롯 이미지
        left_ref: 왼쪽 신발 참조 이미지
        right_ref: 오른쪽 신발 참조 이미지
        slot_color: 슬롯 색상 ("mint", "coral", "white")
        api_key: API 키
        temperature: 생성 온도

    Returns:
        CompositeResult
    """
    if api_key is None:
        api_key = get_next_api_key()

    # 1. 원본 크기 저장
    original_size = (slot_crop.width, slot_crop.height)

    # 2. API 지원 비율로 패딩
    padded_crop, padding_info = _pad_to_supported_ratio(slot_crop)

    # 3. 비율 계산
    padded_ratio = padded_crop.width / padded_crop.height
    aspect_ratio = _get_closest_aspect_ratio(padded_ratio)

    print(f"  [SLOT] Original: {original_size}, Padded: {padded_crop.size}")
    print(f"  [SLOT] Aspect ratio: {aspect_ratio}")

    # 4. 프롬프트 생성
    prompt = build_slot_inpaint_prompt(
        left_ref_desc="MLB chunky sneaker from Reference 1",
        right_ref_desc="MLB chunky sneaker from Reference 2 (DIFFERENT color!)",
        slot_color=slot_color,
    )

    # 5. API 호출
    client = genai.Client(api_key=api_key)
    contents = [
        prompt,
        padded_crop,
        "Reference 1:",
        left_ref,
        "Reference 2:",
        right_ref,
    ]

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size="1K",  # 슬롯 수준은 1K로 충분
                ),
            ),
        )

        # 6. 응답에서 이미지 추출
        result_image = None
        response_text = None

        for part in response.candidates[0].content.parts:
            if part.text:
                response_text = part.text
            if part.inline_data is not None:
                image_data = part.inline_data.data
                result_image = Image.open(io.BytesIO(image_data))
                break

        if result_image:
            # 7. 패딩 제거하여 원본 크기로 복원
            result_image = _unpad_from_result(result_image, original_size, padding_info)
            print(f"  [SLOT] SUCCESS - Generated and unpadded to {result_image.size}")
            return CompositeResult(
                image=result_image,
                success=True,
                stage=0,
                attempt=1,
                response_text=response_text,
            )
        else:
            print("  [SLOT] FAILED - No image in response")
            return CompositeResult(
                image=None,
                success=False,
                stage=0,
                attempt=1,
                error="No image generated",
                response_text=response_text,
            )

    except Exception as e:
        print(f"  [SLOT] ERROR: {e}")
        return CompositeResult(
            image=None,
            success=False,
            stage=0,
            attempt=1,
            error=str(e),
        )


def run_slot_by_slot_pipeline(
    input_image: Image.Image,
    shoe_images: List[Image.Image],
    detected_slots: List[Any],  # List[DetectedSlot]
    api_key: Optional[str] = None,
    max_retries: int = 2,
    parallel: bool = True,
    max_workers: int = 4,
) -> PipelineResult:
    """
    슬롯별 개별 처리 파이프라인 (정면뷰 전용)

    각 슬롯을 독립적으로 처리하여 2개 신발 나란히 배치 보장

    Args:
        input_image: 전체 신발장 이미지
        shoe_images: 참조 신발 이미지 목록 (6개)
        detected_slots: 감지된 슬롯 목록
        api_key: API 키
        max_retries: 슬롯당 최대 재시도
        parallel: 병렬 처리 여부
        max_workers: 최대 동시 작업 수

    Returns:
        PipelineResult
    """
    print("=" * 60)
    print("SHOE RACK MOCKUP - SLOT-BY-SLOT PIPELINE (v3.0)")
    print(f"  Total slots: {len(detected_slots)}")
    print(f"  Parallel: {parallel}, Workers: {max_workers}")
    print("=" * 60)

    result_image = input_image.copy()
    slot_results: Dict[str, CompositeResult] = {}
    total_attempts = 0

    # 참조 신발 쌍 할당 함수 (행 기반)
    def get_refs_for_slot(slot) -> Tuple[Image.Image, Image.Image]:
        """슬롯 위치에 따라 참조 신발 쌍 반환"""
        # position_id가 "r1_c1" 형식이라고 가정
        try:
            row_str = slot.position_id.split("_")[0].replace("r", "")
            row = int(row_str) - 1
        except (AttributeError, ValueError, IndexError):
            row = 0

        # 행 번호에 따라 순환 할당
        # 왼쪽: 0, 1, 2 순환 / 오른쪽: 3, 4, 5 순환
        left_idx = row % min(3, len(shoe_images))
        right_idx = min(3, len(shoe_images)) + (row % max(1, len(shoe_images) - 3))

        if right_idx >= len(shoe_images):
            right_idx = (left_idx + 1) % len(shoe_images)

        return shoe_images[left_idx], shoe_images[right_idx]

    def process_slot_with_retry(slot) -> Tuple[Any, CompositeResult]:
        """슬롯 처리 (재시도 포함)"""
        x, y, w, h = slot.bbox
        slot_crop = input_image.crop((x, y, x + w, y + h))
        left_ref, right_ref = get_refs_for_slot(slot)

        print(f"\n[SLOT {slot.position_id}] Processing ({w}x{h})...")

        last_result = None
        temperatures = [0.25, 0.2, 0.15]

        for attempt in range(max_retries + 1):
            temp = temperatures[min(attempt, len(temperatures) - 1)]

            result = composite_single_slot(
                slot_crop=slot_crop,
                left_ref=left_ref,
                right_ref=right_ref,
                slot_color=slot.color_type if hasattr(slot, "color_type") else "mint",
                api_key=api_key,
                temperature=temp,
            )

            result.attempt = attempt + 1

            if result.success:
                print(f"[SLOT {slot.position_id}] SUCCESS (attempt {attempt + 1})")
                return slot, result

            last_result = result
            print(f"[SLOT {slot.position_id}] Attempt {attempt + 1} failed")

            if attempt < max_retries:
                wait_time = (attempt + 1) * 3
                print(f"  Waiting {wait_time}s...")
                time.sleep(wait_time)

        return slot, last_result or CompositeResult(
            image=None,
            success=False,
            stage=0,
            attempt=max_retries + 1,
            error="All retries exhausted",
        )

    # 슬롯 처리 (병렬 또는 순차)
    if parallel and len(detected_slots) > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print(
            f"\n[PARALLEL] Processing {len(detected_slots)} slots with {max_workers} workers..."
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_slot_with_retry, slot): slot
                for slot in detected_slots
            }

            for future in as_completed(futures):
                slot, result = future.result()
                slot_id = (
                    slot.position_id if hasattr(slot, "position_id") else str(slot)
                )
                slot_results[slot_id] = result
                total_attempts += result.attempt
    else:
        print(f"\n[SEQUENTIAL] Processing {len(detected_slots)} slots...")

        for slot in detected_slots:
            slot, result = process_slot_with_retry(slot)
            slot_id = slot.position_id if hasattr(slot, "position_id") else str(slot)
            slot_results[slot_id] = result
            total_attempts += result.attempt

    # 결과 합성 (블렌딩)
    print("\n[COMPOSITE] Blending slot results...")
    success_count = 0

    for slot in detected_slots:
        slot_id = slot.position_id if hasattr(slot, "position_id") else str(slot)
        result = slot_results.get(slot_id)

        if result and result.success and result.image:
            result_image = blend_slot_edges(
                base_img=result_image,
                slot_img=result.image,
                bbox=slot.bbox,
                blend_width=5,
            )
            success_count += 1
            print(f"  [OK] Slot {slot_id} blended")
        else:
            print(f"  [FAIL] Slot {slot_id} skipped")

    success = success_count == len(detected_slots)

    print("\n" + "=" * 60)
    print("SLOT-BY-SLOT PIPELINE " + ("COMPLETED" if success else "PARTIAL"))
    print(f"  Success: {success_count}/{len(detected_slots)}")
    print(f"  Total attempts: {total_attempts}")
    print("=" * 60)

    return PipelineResult(
        final_image=result_image,
        success=success,
        stages_completed=[0] if success else [],
        stage_results=slot_results,
        total_attempts=total_attempts,
    )
