# -*- coding: utf-8 -*-
"""
Slot Detector - 색상 마스크 기반 슬롯 감지
==========================================
OpenCV를 사용하여 신발장 이미지에서 색상 마스크 영역 감지
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import cv2
import numpy as np
from PIL import Image

from .slot_config import (
    SlotColor,
    DetectedSlot,
    DEFAULT_SLOT_COLORS,
    COLOR_TOLERANCE,
    MIN_AREA,
)


def detect_slots_from_image(
    image: Image.Image,
    target_colors: Optional[Dict[str, SlotColor]] = None,
    tolerance: int = COLOR_TOLERANCE,
    min_area: int = MIN_AREA,
) -> Dict[str, List[DetectedSlot]]:
    """
    이미지에서 색상 마스크 기반으로 슬롯 감지

    Args:
        image: PIL Image 객체
        target_colors: 감지할 색상 설정 (None이면 기본값 사용)
        tolerance: 색상 허용 오차
        min_area: 최소 픽셀 수

    Returns:
        색상별 감지된 슬롯 리스트 {"mint": [...], "coral": [...], ...}
    """
    if target_colors is None:
        target_colors = DEFAULT_SLOT_COLORS

    # PIL -> numpy (RGB)
    img_array = np.array(image.convert("RGB"))

    results: Dict[str, List[DetectedSlot]] = {}

    for color_name, color_config in target_colors.items():
        slots = _detect_color_regions(
            img_array,
            color_name,
            color_config.rgb,
            tolerance,
            min_area,
        )
        results[color_name] = slots

    # position_id 할당 (y좌표 기준 정렬 후)
    _assign_position_ids(results)

    return results


def _detect_color_regions(
    img_array: np.ndarray,
    color_name: str,
    target_rgb: Tuple[int, int, int],
    tolerance: int,
    min_area: int,
) -> List[DetectedSlot]:
    """특정 색상 영역 감지"""

    # 색상 범위 계산
    lower = np.array([max(0, c - tolerance) for c in target_rgb])
    upper = np.array([min(255, c + tolerance) for c in target_rgb])

    # 색상 마스크 생성
    mask = cv2.inRange(img_array, lower, upper)

    # 노이즈 제거
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # 컨투어 찾기
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    slots = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        center = (x + w // 2, y + h // 2)

        slot = DetectedSlot(
            id=f"{color_name}_{i+1}",
            color_type=color_name,
            bbox=(x, y, w, h),
            center=center,
            area=int(area),
            position_id="",  # 나중에 할당
        )
        slots.append(slot)

    return slots


def _assign_position_ids(results: Dict[str, List[DetectedSlot]]):
    """모든 슬롯에 position_id 할당 (행/열 기준)"""
    # 모든 슬롯을 하나의 리스트로
    all_slots = []
    for slots in results.values():
        all_slots.extend(slots)

    if not all_slots:
        return

    # y 좌표로 행 그룹화 (50px 이내는 같은 행)
    all_slots.sort(key=lambda s: s.center[1])

    row_threshold = 50
    rows: List[List[DetectedSlot]] = []
    current_row: List[DetectedSlot] = []
    last_y = -999

    for slot in all_slots:
        if slot.center[1] - last_y > row_threshold:
            if current_row:
                rows.append(current_row)
            current_row = [slot]
        else:
            current_row.append(slot)
        last_y = slot.center[1]

    if current_row:
        rows.append(current_row)

    # 각 행 내에서 x 좌표로 정렬하여 position_id 할당
    for row_idx, row in enumerate(rows, 1):
        row.sort(key=lambda s: s.center[0])
        for col_idx, slot in enumerate(row, 1):
            slot.position_id = f"r{row_idx}_c{col_idx}"


def slots_to_json(slots_by_color: Dict[str, List[DetectedSlot]]) -> dict:
    """슬롯 결과를 JSON 형식으로 변환"""
    all_slots = []
    for color_name, slots in slots_by_color.items():
        for slot in slots:
            all_slots.append(
                {
                    "id": slot.id,
                    "color_type": slot.color_type,
                    "bbox": list(slot.bbox),
                    "center": list(slot.center),
                    "area": slot.area,
                    "position_id": slot.position_id,
                }
            )

    # position_id로 정렬
    all_slots.sort(key=lambda x: x["position_id"])

    return {
        "detection_method": "color_mask",
        "slots": all_slots,
        "summary": {color: len(slots) for color, slots in slots_by_color.items()},
    }


def save_slots_json(
    slots_by_color: Dict[str, List[DetectedSlot]],
    output_path: Path,
    source_image_name: str = "",
):
    """슬롯 결과를 JSON 파일로 저장"""
    data = slots_to_json(slots_by_color)
    data["source_image"] = source_image_name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def visualize_slots(
    image: Image.Image,
    slots_by_color: Dict[str, List[DetectedSlot]],
    output_path: Optional[Path] = None,
) -> Image.Image:
    """슬롯 영역을 시각화"""
    img_array = np.array(image.convert("RGB"))

    # 색상별 시각화 색상
    vis_colors = {
        "mint": (0, 255, 0),  # 초록
        "coral": (255, 0, 0),  # 빨강
        "white": (128, 128, 128),  # 회색
    }

    for color_name, slots in slots_by_color.items():
        vis_color = vis_colors.get(color_name, (255, 255, 0))

        for slot in slots:
            x, y, w, h = slot.bbox

            # 바운딩 박스 그리기
            cv2.rectangle(img_array, (x, y), (x + w, y + h), vis_color, 2)

            # 라벨 그리기
            label = f"{slot.id} ({slot.position_id})"
            cv2.putText(
                img_array,
                label,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                vis_color,
                1,
            )

    result = Image.fromarray(img_array)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)

    return result


def get_slots_by_stage(
    slots_by_color: Dict[str, List[DetectedSlot]],
    stage: int,
) -> List[DetectedSlot]:
    """특정 스테이지의 슬롯만 반환"""
    stage_colors = {
        1: "mint",
        2: "coral",
        3: "white",
    }

    color_name = stage_colors.get(stage)
    if not color_name:
        return []

    return slots_by_color.get(color_name, [])
