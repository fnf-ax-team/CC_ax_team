"""
Figma 배너 빌더 모듈.
채널별 배너를 Figma MCP 도구 호출 시퀀스로 생성한다.

NOTE: 이 모듈은 직접 Figma MCP를 호출하지 않는다.
Claude가 실행할 MCP 도구 호출 시퀀스를 구조화된 형태로 반환한다.
"""

import json
from dataclasses import dataclass
from typing import Optional

from core.banner.layout_engine import (
    BannerLayoutEngine,
    BannerLayout,
    BannerZone,
    get_channel_specs,
    get_all_channels,
    load_channel_specs,
)


@dataclass
class FigmaAction:
    """Figma MCP 도구 호출 액션"""

    tool: str
    params: dict
    description: str
    zone_id: Optional[str] = None
    node_ref: Optional[str] = None


class BannerFigmaBuilder:
    """배너 Figma 빌드 시퀀스 생성기"""

    def __init__(self, brand: str = "MLB"):
        self.engine = BannerLayoutEngine()
        self.brand = brand
        self.actions: list[FigmaAction] = []

        # 브랜드 컬러 로드
        specs = load_channel_specs()
        self.brand_colors = specs.get("brand_colors", {}).get(
            brand,
            {
                "primary": "#000000",
                "secondary": "#FFFFFF",
                "accent": "#C41E3A",
                "background": "#FFFFFF",
                "text": "#000000",
            },
        )

    def build_channel_banners(
        self,
        channel: str,
        product_name: str,
        product_image_url: str,
        price: Optional[str] = None,
        cta_text: str = "자세히 보기",
        discount: Optional[str] = None,
        start_x: int = 0,
        start_y: int = 0,
        gap: int = 40,
    ) -> list[FigmaAction]:
        """특정 채널의 모든 배너 빌드 시퀀스 생성"""
        self.actions = []
        layouts = self.engine.calculate_channel_layouts(channel)
        ch_specs = get_channel_specs(channel)

        current_y = start_y

        # 채널 제목 프레임
        self.actions.append(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": start_x,
                    "y": current_y,
                    "width": 1400,
                    "height": 60,
                    "name": f"Channel - {ch_specs.get('name', channel)}",
                    "fillColor": {"r": 0.96, "g": 0.96, "b": 0.96},
                },
                description=f"채널 헤더: {ch_specs.get('name', channel)}",
                node_ref=f"channel_{channel}_header",
            )
        )

        self.actions.append(
            FigmaAction(
                tool="create_text",
                params={
                    "x": start_x + 20,
                    "y": current_y + 15,
                    "text": f"{ch_specs.get('name', channel)} Banners ({len(layouts)} sizes)",
                    "fontSize": 24,
                    "fontWeight": 700,
                    "fontColor": {"r": 0, "g": 0, "b": 0},
                },
                description="채널 제목 텍스트",
            )
        )

        current_y += 60 + gap

        # 각 배너 사이즈별 빌드
        for layout in layouts:
            banner_actions = self._build_single_banner(
                layout=layout,
                product_name=product_name,
                product_image_url=product_image_url,
                price=price,
                cta_text=cta_text,
                discount=discount,
                x=start_x,
                y=current_y,
            )
            self.actions.extend(banner_actions)

            # 라벨 텍스트 (배너 위)
            self.actions.append(
                FigmaAction(
                    tool="create_text",
                    params={
                        "x": start_x,
                        "y": current_y - 20,
                        "text": f"{layout.label} ({layout.width}x{layout.height})",
                        "fontSize": 12,
                        "fontColor": {"r": 0.5, "g": 0.5, "b": 0.5},
                    },
                    description=f"배너 라벨: {layout.label}",
                )
            )

            current_y += layout.height + gap + 20

        return self.actions

    def build_all_channels(
        self,
        product_name: str,
        product_image_url: str,
        price: Optional[str] = None,
        cta_text: str = "자세히 보기",
        discount: Optional[str] = None,
    ) -> list[FigmaAction]:
        """전 채널 배너 빌드 시퀀스"""
        self.actions = []
        start_x = 0
        channel_gap = 100

        for channel in get_all_channels():
            ch_actions = self.build_channel_banners(
                channel=channel,
                product_name=product_name,
                product_image_url=product_image_url,
                price=price,
                cta_text=cta_text,
                discount=discount,
                start_x=start_x,
                start_y=0,
            )
            # 다음 채널은 오른쪽에 배치
            max_w = max(
                (a.params.get("width", 0) for a in ch_actions if "width" in a.params),
                default=0,
            )
            start_x += max_w + channel_gap

        return self.actions

    def _build_single_banner(
        self,
        layout: BannerLayout,
        product_name: str,
        product_image_url: str,
        price: Optional[str] = None,
        cta_text: str = "자세히 보기",
        discount: Optional[str] = None,
        x: int = 0,
        y: int = 0,
    ) -> list[FigmaAction]:
        """단일 배너 빌드"""
        actions = []
        bg = self.brand_colors.get("background", "#FFFFFF")
        r, g, b = self._hex_to_rgb(bg)

        # 배너 메인 프레임
        actions.append(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": x,
                    "y": y,
                    "width": layout.width,
                    "height": layout.height,
                    "name": f"Banner - {layout.label}",
                    "fillColor": {"r": r, "g": g, "b": b},
                },
                description=f"배너 프레임: {layout.label} ({layout.width}x{layout.height})",
                node_ref=f"banner_{layout.channel}_{layout.banner_id}",
            )
        )

        # 각 영역별 요소 생성
        for zone in layout.zones:
            zone_x = x + zone.x + zone.padding
            zone_y = y + zone.y + zone.padding
            zone_w = zone.width - zone.padding * 2
            zone_h = zone.height - zone.padding * 2

            if zone_w <= 0 or zone_h <= 0:
                continue

            if zone.content == "product_image":
                # 이미지 영역
                actions.append(
                    FigmaAction(
                        tool="create_rectangle",
                        params={
                            "x": zone_x,
                            "y": zone_y,
                            "width": zone_w,
                            "height": zone_h,
                            "name": "Product Image",
                        },
                        description="제품 이미지 영역",
                        zone_id=zone.id,
                        node_ref=f"img_{layout.banner_id}",
                    )
                )
                actions.append(
                    FigmaAction(
                        tool="set_node_image_fill",
                        params={
                            "imageUrl": product_image_url,
                            "scaleMode": zone.scale_mode or "FILL",
                        },
                        description="제품 이미지 적용",
                        zone_id=zone.id,
                    )
                )

            elif zone.content == "product_name_price":
                # 텍스트 영역 (상품명 + 가격)
                text_parts = [product_name]
                if price:
                    text_parts.append(price)
                if discount:
                    text_parts.append(f"{discount} OFF")

                text_color = self._hex_to_figma_color(
                    zone.color or self.brand_colors.get("text", "#000000")
                )

                # 사이즈에 따른 폰트 크기 자동 조절
                font_size = self._auto_font_size(zone_w, zone_h, len(product_name))

                actions.append(
                    FigmaAction(
                        tool="create_text",
                        params={
                            "x": zone_x,
                            "y": zone_y,
                            "text": "\n".join(text_parts),
                            "fontSize": font_size,
                            "fontWeight": 700,
                            "fontColor": text_color,
                        },
                        description=f"상품명/가격: {product_name}",
                        zone_id=zone.id,
                    )
                )

            elif zone.content == "brand_logo":
                # 브랜드 로고 (텍스트로 대체, 실제 로고는 이미지로 교체 가능)
                actions.append(
                    FigmaAction(
                        tool="create_text",
                        params={
                            "x": zone_x,
                            "y": zone_y,
                            "text": self.brand,
                            "fontSize": min(zone_h - 4, 20),
                            "fontWeight": 800,
                            "fontColor": self._hex_to_figma_color(
                                self.brand_colors.get("primary", "#000000")
                            ),
                        },
                        description=f"브랜드 로고: {self.brand}",
                        zone_id=zone.id,
                    )
                )

            elif zone.content == "cta_button":
                # CTA 버튼
                btn_bg = self.brand_colors.get("primary", "#000000")
                btn_r, btn_g, btn_b = self._hex_to_rgb(btn_bg)

                actions.append(
                    FigmaAction(
                        tool="create_frame",
                        params={
                            "x": zone_x,
                            "y": zone_y,
                            "width": zone_w,
                            "height": zone_h,
                            "name": "CTA Button",
                            "fillColor": {"r": btn_r, "g": btn_g, "b": btn_b},
                        },
                        description="CTA 버튼 배경",
                        zone_id=zone.id,
                    )
                )
                actions.append(
                    FigmaAction(
                        tool="set_corner_radius",
                        params={"radius": 4},
                        description="CTA 버튼 라운딩",
                        zone_id=zone.id,
                    )
                )
                actions.append(
                    FigmaAction(
                        tool="create_text",
                        params={
                            "x": zone_x + 8,
                            "y": zone_y + max(2, (zone_h - 14) // 2),
                            "text": cta_text,
                            "fontSize": min(zone_h - 8, 14),
                            "fontWeight": 600,
                            "fontColor": {"r": 1, "g": 1, "b": 1},
                        },
                        description=f"CTA 텍스트: {cta_text}",
                        zone_id=zone.id,
                    )
                )

            elif zone.content == "gradient_overlay":
                # 그라데이션 오버레이 (스토리/릴스용)
                actions.append(
                    FigmaAction(
                        tool="create_rectangle",
                        params={
                            "x": zone_x,
                            "y": zone_y,
                            "width": zone_w,
                            "height": zone_h,
                            "name": "Gradient Overlay",
                        },
                        description="그라데이션 오버레이",
                        zone_id=zone.id,
                    )
                )
                actions.append(
                    FigmaAction(
                        tool="set_fill_color",
                        params={"r": 0, "g": 0, "b": 0, "a": 0.5},
                        description="오버레이 색상 (반투명 검정)",
                        zone_id=zone.id,
                    )
                )

        return actions

    def _auto_font_size(self, zone_w: int, zone_h: int, text_len: int) -> int:
        """영역 크기와 텍스트 길이에 따른 폰트 크기 자동 계산"""
        area = zone_w * zone_h
        if area < 5000:
            return max(8, min(zone_h - 4, 10))
        elif area < 20000:
            return max(10, min(zone_h // 2, 14))
        elif area < 80000:
            return max(12, min(zone_h // 3, 20))
        else:
            return max(16, min(zone_h // 4, 32))

    def to_json(self) -> str:
        """빌드 시퀀스를 JSON으로 반환"""
        return json.dumps(
            [
                {
                    "tool": a.tool,
                    "params": a.params,
                    "description": a.description,
                    "zone_id": a.zone_id,
                    "node_ref": a.node_ref,
                }
                for a in self.actions
            ],
            ensure_ascii=False,
            indent=2,
        )

    def get_summary(self, channel: str = None) -> str:
        """채널 배너 요약"""
        return self.engine.get_summary(channel)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    @staticmethod
    def _hex_to_figma_color(hex_color: str) -> dict:
        r, g, b = BannerFigmaBuilder._hex_to_rgb(hex_color)
        return {"r": r, "g": g, "b": b}
