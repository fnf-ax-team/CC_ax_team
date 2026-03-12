"""
배너 레이아웃 엔진.
배너 사이즈에 따라 적절한 레이아웃 패턴을 자동 선택하고
각 요소(이미지, 텍스트, CTA)의 위치를 계산한다.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# DB 경로
CHANNEL_SPECS_DB = Path(__file__).parent.parent.parent / "db" / "channel_specs.json"
BANNER_TEMPLATES_DB = (
    Path(__file__).parent.parent.parent / "db" / "banner_templates.json"
)


@dataclass
class BannerZone:
    """배너 내 요소 영역"""

    id: str
    x: int
    y: int
    width: int
    height: int
    content: str
    style: Optional[str] = None
    scale_mode: Optional[str] = None
    color: Optional[str] = None
    align: Optional[str] = None
    gradient: Optional[str] = None
    padding: int = 0


@dataclass
class BannerLayout:
    """계산된 배너 레이아웃"""

    channel: str
    banner_id: str
    label: str
    width: int
    height: int
    category: str
    pattern: str
    zones: list  # list[BannerZone]


def load_channel_specs() -> dict:
    """채널 스펙 DB 로드"""
    with open(CHANNEL_SPECS_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def load_banner_templates() -> dict:
    """배너 템플릿 DB 로드"""
    with open(BANNER_TEMPLATES_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def get_channel_specs(channel: str = None) -> dict:
    """채널 스펙 조회 (채널 미지정시 전체)"""
    data = load_channel_specs()
    if channel:
        return data["channels"].get(channel, {})
    return data["channels"]


def get_banner_sizes(channel: str) -> dict:
    """특정 채널의 배너 사이즈 목록"""
    specs = get_channel_specs(channel)
    return specs.get("banners", {})


def get_all_channels() -> list:
    """모든 채널 목록"""
    data = load_channel_specs()
    return list(data["channels"].keys())


class BannerLayoutEngine:
    """배너 레이아웃 자동 계산 엔진"""

    def __init__(self):
        self.channel_specs = load_channel_specs()
        self.banner_templates = load_banner_templates()
        self.layout_patterns = self.banner_templates.get("layout_patterns", {})

    def calculate_layout(
        self,
        channel: str,
        banner_id: str,
    ) -> BannerLayout:
        """특정 배너의 레이아웃 계산

        Args:
            channel: 채널 ID (naver, google, kakao, meta, youtube)
            banner_id: 배너 ID (shopping_main, leaderboard 등)

        Returns:
            BannerLayout: 계산된 레이아웃 (영역 좌표 포함)
        """
        ch = self.channel_specs["channels"][channel]
        banner = ch["banners"][banner_id]
        w, h = banner["w"], banner["h"]
        category = banner["category"]

        # 카테고리 -> 레이아웃 패턴
        cat_info = self.channel_specs.get("layout_categories", {}).get(category, {})
        pattern_name = cat_info.get("pattern", "image_text_split")

        # 패턴에서 영역 좌표 계산
        pattern = self.layout_patterns.get(pattern_name, {})
        zones = []

        for zone_def in pattern.get("zones", []):
            zone = BannerZone(
                id=zone_def["id"],
                x=int(zone_def["x_ratio"] * w),
                y=int(zone_def["y_ratio"] * h),
                width=int(zone_def["w_ratio"] * w),
                height=int(zone_def["h_ratio"] * h),
                content=zone_def["content"],
                style=zone_def.get("style"),
                scale_mode=zone_def.get("scale_mode"),
                color=zone_def.get("color"),
                align=zone_def.get("align"),
                gradient=zone_def.get("gradient"),
                padding=zone_def.get("padding", 0),
            )
            zones.append(zone)

        return BannerLayout(
            channel=channel,
            banner_id=banner_id,
            label=banner["label"],
            width=w,
            height=h,
            category=category,
            pattern=pattern_name,
            zones=zones,
        )

    def calculate_channel_layouts(self, channel: str) -> list:
        """한 채널의 모든 배너 레이아웃 계산"""
        banners = get_banner_sizes(channel)
        return [self.calculate_layout(channel, bid) for bid in banners]

    def calculate_all_layouts(self) -> dict:
        """전 채널의 모든 배너 레이아웃 계산"""
        result = {}
        for channel in get_all_channels():
            result[channel] = self.calculate_channel_layouts(channel)
        return result

    def get_summary(self, channel: str = None) -> str:
        """채널/배너 요약 문자열"""
        lines = []
        channels = [channel] if channel else get_all_channels()

        for ch in channels:
            specs = get_channel_specs(ch)
            banners = specs.get("banners", {})
            lines.append(f"\n[{specs.get('name', ch)}] ({len(banners)} sizes)")
            for bid, info in banners.items():
                lines.append(
                    f"  - {info['label']}: {info['w']}x{info['h']} ({info['category']})"
                )

        return "\n".join(lines)
