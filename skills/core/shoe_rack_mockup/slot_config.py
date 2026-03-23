# -*- coding: utf-8 -*-
"""
Slot Configuration - 색상별 슬롯 설정
=====================================
각 색상 마스크에 대한 신발 개수, 크기, 배치 패턴 정의
"""

from dataclasses import dataclass
from typing import Tuple, Dict, List


@dataclass
class SlotColor:
    """슬롯 색상 타입 정의"""

    name: str  # "mint", "coral", "white"
    rgb: Tuple[int, int, int]  # (130, 240, 210)
    shoes_per_slot: int  # 2, 1, 2
    shoe_size: str  # "small", "large", "medium"
    placement_pattern: str  # "side_by_side", "center"
    stage: int  # 처리 순서 (1, 2, 3)
    description: str  # 설명


# 기본 색상 설정 (테스트에서 검증됨)
DEFAULT_SLOT_COLORS: Dict[str, SlotColor] = {
    "mint": SlotColor(
        name="mint",
        rgb=(130, 240, 210),
        shoes_per_slot=2,
        shoe_size="small",
        placement_pattern="side_by_side",
        stage=1,
        description="민트/청록색 - 작은 신발 2개씩 나란히",
    ),
    "coral": SlotColor(
        name="coral",
        rgb=(240, 110, 110),
        shoes_per_slot=1,
        shoe_size="large",
        placement_pattern="center",
        stage=2,
        description="코랄/분홍색 - 큰 신발 1개 중앙",
    ),
    "white": SlotColor(
        name="white",
        rgb=(255, 255, 255),
        shoes_per_slot=2,
        shoe_size="medium",
        placement_pattern="side_by_side",
        stage=3,
        description="흰색 - 중간 신발 2개씩 (기존 유지 또는 교체)",
    ),
}

# 색상 감지 허용 오차
COLOR_TOLERANCE = 50

# 최소 픽셀 수 (노이즈 필터)
MIN_AREA = 500


@dataclass
class DetectedSlot:
    """감지된 슬롯"""

    id: str  # "mint_1", "coral_3"
    color_type: str  # "mint", "coral", "white"
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    center: Tuple[int, int]
    area: int
    position_id: str  # "r1_c1" (row_col)


def get_slot_color(name: str) -> SlotColor:
    """색상 이름으로 설정 가져오기"""
    if name not in DEFAULT_SLOT_COLORS:
        raise ValueError(
            f"Unknown slot color: {name}. Available: {list(DEFAULT_SLOT_COLORS.keys())}"
        )
    return DEFAULT_SLOT_COLORS[name]


def get_colors_by_stage() -> List[SlotColor]:
    """처리 순서대로 색상 목록 반환"""
    colors = list(DEFAULT_SLOT_COLORS.values())
    return sorted(colors, key=lambda x: x.stage)


def get_stage_prompt_hint(color: SlotColor) -> str:
    """색상별 프롬프트 힌트 반환"""
    if color.shoes_per_slot == 2:
        return f"TWO shoes side by side ({color.shoe_size} size, matching pair)"
    else:
        return f"ONE shoe centered ({color.shoe_size} size, single)"
