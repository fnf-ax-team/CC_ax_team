# -*- coding: utf-8 -*-
"""
Mirror Processor - 거울 반사 처리
=================================
이미지 8번처럼 왼쪽/오른쪽에 거울이 있는 경우 후처리

v1.0 (2026-02-24):
- 거울 반사 후처리 기능 추가
- blur + mirror flip 적용
- 거울 영역 자동 감지 또는 수동 지정
"""

from PIL import Image, ImageFilter
from typing import Tuple, Optional


def process_mirror_reflection(
    result_image: Image.Image,
    mirror_side: str = "left",
    blur_radius: float = 4.0,
    mirror_ratio: float = 0.5,
) -> Image.Image:
    """
    거울 반사 후처리

    이미지의 한 쪽이 거울인 경우:
    1. 실제 캐비닛 영역에서 거울과 인접한 부분 추출
    2. 좌우 반전 (mirror flip)
    3. blur 적용 (거울 느낌)
    4. 거울 영역에 합성

    v1.2 수정:
    - 거울 영역 크기만큼만 캐비닛에서 추출 (비율 유지)
    - 기존: 전체 캐비닛 추출 후 리사이즈 (비율 왜곡)
    - 수정: 거울 영역과 동일한 너비만 추출 (1:1 비율)

    Args:
        result_image: 처리할 이미지 (3 stage 완료 후)
        mirror_side: 거울 위치 ("left" 또는 "right")
        blur_radius: 거울 블러 강도 (기본 4.0)
        mirror_ratio: 거울 영역 비율 (기본 0.5 = 절반)

    Returns:
        거울 처리된 이미지
    """
    width, height = result_image.size
    mirror_width = int(width * mirror_ratio)

    result = result_image.copy()

    if mirror_side == "left":
        # 오른쪽 캐비닛에서 거울 영역과 동일한 너비만큼 추출
        # (거울 바로 옆 영역을 반사시켜야 자연스러움)
        cabinet_start = mirror_width
        cabinet_end = mirror_width + mirror_width  # 거울 너비만큼만 추출
        if cabinet_end > width:
            cabinet_end = width

        cabinet = result_image.crop((cabinet_start, 0, cabinet_end, height))

        # 좌우 반전
        mirrored = cabinet.transpose(Image.FLIP_LEFT_RIGHT)

        # 거울 영역 크기에 맞게 리사이즈 (추출 영역이 작을 경우)
        if mirrored.width != mirror_width:
            mirrored = mirrored.resize((mirror_width, height), Image.LANCZOS)

        # blur 적용 (거울 느낌)
        blurred = mirrored.filter(ImageFilter.GaussianBlur(blur_radius))

        # 왼쪽 거울 영역에 합성
        result.paste(blurred, (0, 0))

    else:  # mirror_side == "right"
        # 왼쪽 캐비닛에서 거울 영역과 동일한 너비만큼 추출
        cabinet_end = width - mirror_width
        cabinet_start = cabinet_end - mirror_width
        if cabinet_start < 0:
            cabinet_start = 0

        cabinet = result_image.crop((cabinet_start, 0, cabinet_end, height))

        # 좌우 반전
        mirrored = cabinet.transpose(Image.FLIP_LEFT_RIGHT)

        # 거울 영역 크기에 맞게 리사이즈
        if mirrored.width != mirror_width:
            mirrored = mirrored.resize((mirror_width, height), Image.LANCZOS)

        # blur 적용 (거울 느낌)
        blurred = mirrored.filter(ImageFilter.GaussianBlur(blur_radius))

        # 오른쪽 거울 영역에 합성
        result.paste(blurred, (width - mirror_width, 0))

    return result


def process_mirror_with_mask(
    result_image: Image.Image,
    mirror_mask: Image.Image,
    source_region: Tuple[int, int, int, int],
    blur_radius: float = 4.0,
) -> Image.Image:
    """
    마스크 기반 거울 반사 처리

    Args:
        result_image: 처리할 이미지
        mirror_mask: 거울 영역 마스크 (흰색 = 거울, 검정 = 실제)
        source_region: 실제 캐비닛 영역 (x1, y1, x2, y2)
        blur_radius: 거울 블러 강도

    Returns:
        거울 처리된 이미지
    """
    # 실제 캐비닛 영역 추출
    cabinet = result_image.crop(source_region)

    # 좌우 반전
    mirrored = cabinet.transpose(Image.FLIP_LEFT_RIGHT)

    # blur 적용
    blurred = mirrored.filter(ImageFilter.GaussianBlur(blur_radius))

    # 거울 마스크를 사용해 합성
    result = result_image.copy()

    # 거울 영역에만 합성 (마스크가 흰색인 부분)
    # 거울 영역 크기에 맞게 리사이즈
    mirror_bbox = mirror_mask.getbbox()
    if mirror_bbox:
        mirror_width = mirror_bbox[2] - mirror_bbox[0]
        mirror_height = mirror_bbox[3] - mirror_bbox[1]
        blurred_resized = blurred.resize((mirror_width, mirror_height), Image.LANCZOS)

        # 마스크를 사용해 합성
        mirror_region = mirror_mask.crop(mirror_bbox)
        result.paste(blurred_resized, (mirror_bbox[0], mirror_bbox[1]), mirror_region)

    return result


def detect_mirror_side(image: Image.Image) -> Optional[str]:
    """
    이미지에서 거울 위치 자동 감지 (간단한 휴리스틱)

    거울은 보통 반사로 인해 대칭 패턴을 가짐.
    왼쪽 절반과 오른쪽 절반의 유사도를 비교.

    Args:
        image: 분석할 이미지

    Returns:
        "left", "right", 또는 None (거울 없음)
    """
    import numpy as np

    # 이미지를 numpy 배열로 변환
    img_array = np.array(image)
    width = img_array.shape[1]
    half = width // 2

    # 왼쪽/오른쪽 절반 추출
    left_half = img_array[:, :half]
    right_half = img_array[:, half:]

    # 오른쪽 절반을 뒤집어서 비교
    right_flipped = np.flip(right_half, axis=1)

    # 왼쪽 절반과 뒤집은 오른쪽 절반의 유사도 계산
    # MSE (Mean Squared Error) 사용
    # 크기가 다를 수 있으므로 최소 크기로 맞춤
    min_width = min(left_half.shape[1], right_flipped.shape[1])
    left_cropped = left_half[:, :min_width]
    right_cropped = right_flipped[:, :min_width]

    mse = np.mean((left_cropped.astype(float) - right_cropped.astype(float)) ** 2)

    # 임계값 기반 판단 (낮을수록 유사함)
    # 거울이 있으면 매우 유사해야 함
    if mse < 500:  # 임계값은 조정 가능
        # 어느 쪽이 거울인지 추가 분석 필요
        # 보통 거울 쪽이 약간 더 밝거나 흐릿함
        left_brightness = np.mean(left_half)
        right_brightness = np.mean(right_half)

        # 더 밝은 쪽이 거울일 가능성 높음 (반사광)
        if left_brightness > right_brightness * 1.05:
            return "left"
        elif right_brightness > left_brightness * 1.05:
            return "right"

    return None


def apply_mirror_effect_to_image8(
    result_image: Image.Image,
    blur_radius: float = 5.0,
) -> Image.Image:
    """
    이미지 8번 전용 거울 처리

    이미지 8번은 왼쪽에 거울이 있어서 오른쪽 캐비닛이 반사됨.
    오른쪽 캐비닛을 복사 -> 좌우반전 -> blur -> 왼쪽에 합성

    v1.2 수정:
    - mirror_ratio: 0.5 → 0.35 (원본 이미지 기준 약 35%가 거울)
    - blur_radius: 4.0 → 5.0 (더 흐릿하게)

    Args:
        result_image: 3 stage 완료된 이미지
        blur_radius: 거울 블러 강도

    Returns:
        거울 처리된 최종 이미지
    """
    return process_mirror_reflection(
        result_image=result_image,
        mirror_side="left",
        blur_radius=blur_radius,
        mirror_ratio=0.35,  # 왼쪽 약 35%가 거울 (원본 기준)
    )
