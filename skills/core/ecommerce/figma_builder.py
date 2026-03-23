"""
Figma 상세페이지 빌더 모듈.
Figma MCP (TalkToFigma) 도구 호출 시퀀스를 생성한다.

NOTE: 이 모듈은 직접 Figma MCP를 호출하지 않는다.
대신 Claude가 실행할 MCP 도구 호출 시퀀스를 구조화된 형태로 반환한다.
Claude가 이 시퀀스를 받아 Figma MCP 도구를 순차 호출한다.

사용법:
    from core.ecommerce.figma_builder import DetailPageFigmaBuilder

    builder = DetailPageFigmaBuilder(template_id="mlb_standard")
    actions = builder.build_sequence(
        product_name="MLB NY 탱크탑",
        model_spec={"height": "175", "fitting_size": "S / 240mm"},
        fabric_info={"icon": "SPAN", "description": "모달 원사로..."},
        image_urls={"model_1": "http://...", "product_front": "http://..."},
    )

    # Claude가 actions를 순회하며 Figma MCP 호출 실행
    for action in actions:
        print(f"[{action.tool}] {action.description}")
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.ecommerce.template_presets import (
    TemplateConfig,
    SectionConfig,
    SlotConfig,
    get_template,
    get_all_slots,
    get_model_spec_format,
)


@dataclass
class FigmaAction:
    """Figma MCP 도구 호출 액션

    Attributes:
        tool: MCP 도구 이름 (예: create_frame, create_text, set_node_image_fill)
        params: 도구 파라미터 딕셔너리
        description: 액션 설명 (한국어)
        slot_id: 연결된 슬롯 ID (이미지 슬롯과 매핑 시 사용)
        node_ref: 생성 후 참조할 노드 변수명 (후속 액션에서 parentId로 사용)
        depends_on: 이 액션이 의존하는 node_ref (parentId 주입 필요)
    """

    tool: str
    params: dict
    description: str
    slot_id: Optional[str] = None
    node_ref: Optional[str] = None
    depends_on: Optional[str] = None


class DetailPageFigmaBuilder:
    """상세페이지 Figma 빌드 시퀀스 생성기

    템플릿 설정(ecommerce_templates.json)을 기반으로
    Figma MCP 도구 호출 시퀀스를 생성한다.
    Claude가 이 시퀀스를 순차 실행하여 Figma에 상세페이지를 구축한다.
    """

    def __init__(self, template_id: str = "mlb_standard"):
        """초기화

        Args:
            template_id: 템플릿 ID (기본: mlb_standard)
        """
        self.template_id = template_id
        self.template: TemplateConfig = get_template(template_id)
        self.model_spec_format: dict = get_model_spec_format(self.template.brand)
        self.actions: list[FigmaAction] = []

    def build_sequence(
        self,
        product_name: str,
        model_spec: Optional[dict] = None,
        fabric_info: Optional[dict] = None,
        image_urls: Optional[dict] = None,
        start_x: int = 0,
        start_y: int = 0,
    ) -> list[FigmaAction]:
        """상세페이지 전체 빌드 시퀀스 생성

        Args:
            product_name: 상품명 (예: "MLB NY 빅로고 반팔티")
            model_spec: 모델 스펙 {"height": "175", "fitting_size": "S / 240mm"}
            fabric_info: 소재 정보 {"icon": "SPAN", "description": "모달 원사로..."}
            image_urls: 슬롯별 이미지 URL {"model_1": "http://...", "product_front": "http://..."}
            start_x: 시작 X 좌표
            start_y: 시작 Y 좌표

        Returns:
            list[FigmaAction]: 순차 실행할 Figma MCP 도구 호출 목록
        """
        self.actions = []
        page_w = self.template.page_width

        # 1. 메인 프레임 생성 (VERTICAL auto-layout, HUG 높이)
        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": start_x,
                    "y": start_y,
                    "width": page_w,
                    "height": 100,  # HUG 모드에서 자동 조절
                    "name": f"Detail Page - {product_name}",
                    "layoutMode": "VERTICAL",
                    "layoutSizingHorizontal": "FIXED",
                    "layoutSizingVertical": "HUG",
                    "itemSpacing": 0,
                    "paddingTop": 0,
                    "paddingBottom": 0,
                    "paddingLeft": 0,
                    "paddingRight": 0,
                    "fillColor": self._hex_to_figma_color(
                        self.template.background_color
                    ),
                },
                description=f"메인 프레임 생성: {product_name} ({page_w}px 폭)",
                node_ref="main_frame",
            )
        )

        # 2. 섹션별 빌드
        for section in self.template.sections:
            if section.type == "image_grid":
                self._build_image_grid_section(section, page_w, image_urls)
            elif section.type == "info_section":
                self._build_info_section(section, page_w, model_spec, fabric_info)

        return self.actions

    def _build_image_grid_section(
        self,
        section: SectionConfig,
        page_w: int,
        image_urls: Optional[dict] = None,
    ):
        """이미지 그리드 섹션 빌드

        섹션 프레임 -> 각 슬롯 프레임 -> 이미지 적용 -> 오버레이 순서로 생성
        """
        section_ref = f"section_{section.id}"

        # 섹션 컨테이너 프레임
        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": 0,
                    "y": 0,
                    "width": page_w,
                    "height": 100,  # HUG 모드에서 자동 조절
                    "name": f"Section - {section.label}",
                    "layoutMode": "VERTICAL",
                    "layoutSizingHorizontal": "FIXED",
                    "layoutSizingVertical": "HUG",
                    "itemSpacing": section.gap,
                    "paddingTop": 0,
                    "paddingBottom": 0,
                    "paddingLeft": 0,
                    "paddingRight": 0,
                    "fillColor": {"r": 1, "g": 1, "b": 1},
                },
                description=f"섹션 프레임: {section.label} (gap={section.gap}px)",
                node_ref=section_ref,
                depends_on="main_frame",
            )
        )

        # 각 슬롯 생성
        for slot in section.slots:
            self._build_slot(slot, section_ref, image_urls)

    def _build_slot(
        self,
        slot: SlotConfig,
        parent_ref: str,
        image_urls: Optional[dict] = None,
    ):
        """단일 이미지 슬롯 빌드"""
        slot_ref = f"slot_{slot.id}"

        # 슬롯 배경색 결정
        bg_color = self._hex_to_figma_color(slot.background or "#FFFFFF")

        # 슬롯 프레임 생성
        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": 0,
                    "y": 0,
                    "width": slot.width,
                    "height": slot.height,
                    "name": f"Slot - {slot.label} ({slot.id})",
                    "fillColor": bg_color,
                },
                description=(
                    f"이미지 슬롯: {slot.label} "
                    f"({slot.width}x{slot.height}, {slot.aspect_ratio})"
                ),
                slot_id=slot.id,
                node_ref=slot_ref,
                depends_on=parent_ref,
            )
        )

        # 이미지 채우기 (URL 제공 시)
        if image_urls and slot.id in image_urls:
            self._add_action(
                FigmaAction(
                    tool="set_node_image_fill",
                    params={
                        "imageUrl": image_urls[slot.id],
                        "scaleMode": "FILL",
                        # nodeId는 실행 시 slot_ref의 실제 ID로 대체
                    },
                    description=f"이미지 적용: {slot.label}",
                    slot_id=slot.id,
                    depends_on=slot_ref,
                )
            )

        # MODEL SPEC 오버레이 (슬롯에 overlay 설정 있을 때)
        if slot.overlay and slot.overlay.get("type") == "model_spec":
            self._build_model_spec_overlay(slot, slot_ref)

    def _build_model_spec_overlay(self, slot: SlotConfig, parent_ref: str):
        """MODEL SPEC 텍스트 오버레이 생성

        첫 번째 모델컷 하단에 모델 키/피팅 사이즈 표시.
        model_spec_defaults 포맷 사용.
        """
        spec_format = self.model_spec_format
        font_size = spec_format.get("title_font_size", 11)
        color_hex = spec_format.get("color", "#666666")
        text_template = spec_format.get(
            "format",
            "MODEL SPEC\nHeight : {height}cm\nFitting Size : {fitting_size}",
        )

        # 오버레이 위치 (bottom_left 기본)
        position = slot.overlay.get("position", "bottom_left")
        if position == "bottom_left":
            text_x = 30
            text_y = slot.height - 120
        elif position == "bottom_right":
            text_x = slot.width - 200
            text_y = slot.height - 120
        else:
            text_x = 30
            text_y = slot.height - 120

        # 오버레이 배경 (반투명 프레임)
        overlay_ref = f"overlay_{slot.id}"
        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": text_x - 15,
                    "y": text_y - 15,
                    "width": 220,
                    "height": 100,
                    "name": "Model Spec Overlay",
                    "fillColor": {"r": 1, "g": 1, "b": 1, "a": 0.7},
                    "paddingTop": 15,
                    "paddingBottom": 15,
                    "paddingLeft": 15,
                    "paddingRight": 15,
                    "layoutMode": "VERTICAL",
                    "layoutSizingHorizontal": "HUG",
                    "layoutSizingVertical": "HUG",
                    "itemSpacing": 4,
                },
                description="MODEL SPEC 오버레이 배경",
                node_ref=overlay_ref,
                depends_on=parent_ref,
            )
        )

        # 텍스트 (placeholder - 실제 값은 Claude가 치환)
        self._add_action(
            FigmaAction(
                tool="create_text",
                params={
                    "x": 0,
                    "y": 0,
                    "text": text_template,
                    "fontSize": font_size,
                    "fontColor": self._hex_to_figma_color(color_hex),
                    "name": "Model Spec Text",
                },
                description="MODEL SPEC 텍스트 (height/fitting_size 치환 필요)",
                slot_id=slot.id,
                depends_on=overlay_ref,
            )
        )

    def _build_info_section(
        self,
        section: SectionConfig,
        page_w: int,
        model_spec: Optional[dict] = None,
        fabric_info: Optional[dict] = None,
    ):
        """정보 섹션 빌드 (FABRIC 등)

        구조: 섹션 프레임 -> 타이틀 -> 아이콘 라벨 -> 설명 텍스트
        """
        bg_color = self._hex_to_figma_color(section.background or "#FFFFFF")
        section_height = section.height or 500
        section_ref = f"section_{section.id}"

        # 섹션 프레임 (고정 높이 - 정보 섹션은 HUG 대신 FIXED 사용)
        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": 0,
                    "y": 0,
                    "width": page_w,
                    "height": section_height,
                    "name": f"Section - {section.label}",
                    "fillColor": bg_color,
                },
                description=f"정보 섹션: {section.label} ({page_w}x{section_height})",
                node_ref=section_ref,
                depends_on="main_frame",
            )
        )

        # 섹션 내 요소들 순차 생성
        for elem in section.elements:
            self._build_info_element(elem, section_ref, page_w, fabric_info)

    def _build_info_element(
        self,
        elem: dict,
        parent_ref: str,
        page_w: int,
        fabric_info: Optional[dict] = None,
    ):
        """정보 섹션 내 개별 요소 빌드"""
        elem_type = elem.get("type")

        if elem_type == "title":
            self._build_title_element(elem, parent_ref, page_w)
        elif elem_type == "icon":
            self._build_icon_element(elem, parent_ref, page_w)
        elif elem_type == "icon_label":
            self._build_icon_label_element(elem, parent_ref, page_w, fabric_info)
        elif elem_type == "description":
            self._build_description_element(elem, parent_ref, page_w, fabric_info)

    def _build_title_element(self, elem: dict, parent_ref: str, page_w: int):
        """타이틀 텍스트 생성"""
        text = elem.get("text", "")
        font_size = elem.get("font_size", 24)
        font_weight = elem.get("font_weight", 700)
        color = elem.get("color", "#000000")
        y_offset = elem.get("y_offset", 40)

        # 중앙 정렬 계산 (대략적 - Figma auto-layout 미사용 시)
        # 글자 폭 추정: font_size * 0.6 * len(text)
        est_text_width = font_size * 0.6 * len(text)
        x_pos = max(0, int((page_w - est_text_width) / 2))

        self._add_action(
            FigmaAction(
                tool="create_text",
                params={
                    "x": x_pos,
                    "y": y_offset,
                    "text": text,
                    "fontSize": font_size,
                    "fontWeight": font_weight,
                    "fontColor": self._hex_to_figma_color(color),
                    "name": f"Title - {text}",
                },
                description=f"타이틀: {text}",
                depends_on=parent_ref,
            )
        )

    def _build_icon_element(self, elem: dict, parent_ref: str, page_w: int):
        """아이콘 placeholder 생성 (원형 프레임)"""
        icon_w = elem.get("width", 60)
        icon_h = elem.get("height", 60)
        y_offset = elem.get("y_offset", 100)
        x_pos = (page_w - icon_w) // 2

        icon_ref = f"icon_{elem.get('id', 'default')}"

        self._add_action(
            FigmaAction(
                tool="create_frame",
                params={
                    "x": x_pos,
                    "y": y_offset,
                    "width": icon_w,
                    "height": icon_h,
                    "name": f"Icon - {elem.get('id', 'fabric')}",
                    "fillColor": {"r": 0.95, "g": 0.95, "b": 0.95},
                },
                description=f"아이콘 placeholder ({icon_w}x{icon_h})",
                node_ref=icon_ref,
                depends_on=parent_ref,
            )
        )

        # 아이콘을 원형으로 (corner radius = 반지름)
        self._add_action(
            FigmaAction(
                tool="set_corner_radius",
                params={
                    "radius": icon_w // 2,
                    # nodeId는 실행 시 icon_ref 실제 ID로 대체
                },
                description="아이콘 원형 처리",
                depends_on=icon_ref,
            )
        )

    def _build_icon_label_element(
        self,
        elem: dict,
        parent_ref: str,
        page_w: int,
        fabric_info: Optional[dict] = None,
    ):
        """아이콘 하단 라벨 텍스트"""
        icon_label = "SPAN"  # 기본값
        if fabric_info:
            icon_label = fabric_info.get("icon", "SPAN")

        font_size = elem.get("font_size", 12)
        color = elem.get("color", "#666666")
        y_offset = elem.get("y_offset", 170)

        est_text_width = font_size * 0.7 * len(icon_label)
        x_pos = max(0, int((page_w - est_text_width) / 2))

        self._add_action(
            FigmaAction(
                tool="create_text",
                params={
                    "x": x_pos,
                    "y": y_offset,
                    "text": icon_label,
                    "fontSize": font_size,
                    "fontColor": self._hex_to_figma_color(color),
                    "name": f"Icon Label - {icon_label}",
                },
                description=f"소재 아이콘 라벨: {icon_label}",
                depends_on=parent_ref,
            )
        )

    def _build_description_element(
        self,
        elem: dict,
        parent_ref: str,
        page_w: int,
        fabric_info: Optional[dict] = None,
    ):
        """설명 텍스트 생성"""
        desc_text = ""
        if fabric_info:
            desc_text = fabric_info.get("description", "")

        if not desc_text:
            # 데이터 없으면 placeholder
            desc_text = "(소재 설명 텍스트)"

        font_size = elem.get("font_size", 14)
        color = elem.get("color", "#333333")
        max_width = elem.get("max_width", 700)
        y_offset = elem.get("y_offset", 220)

        x_pos = (page_w - max_width) // 2

        self._add_action(
            FigmaAction(
                tool="create_text",
                params={
                    "x": x_pos,
                    "y": y_offset,
                    "text": desc_text,
                    "fontSize": font_size,
                    "fontColor": self._hex_to_figma_color(color),
                    "name": "Fabric Description",
                },
                description="소재 설명 텍스트",
                depends_on=parent_ref,
            )
        )

    # ------------------------------------------------------------------
    # 유틸리티 메서드
    # ------------------------------------------------------------------

    def _add_action(self, action: FigmaAction):
        """액션을 시퀀스에 추가"""
        self.actions.append(action)

    def to_json(self) -> str:
        """빌드 시퀀스를 JSON 문자열로 반환

        Claude가 파싱하여 Figma MCP 호출에 사용.
        """
        return json.dumps(
            [
                {
                    "tool": a.tool,
                    "params": a.params,
                    "description": a.description,
                    "slot_id": a.slot_id,
                    "node_ref": a.node_ref,
                    "depends_on": a.depends_on,
                }
                for a in self.actions
            ],
            ensure_ascii=False,
            indent=2,
        )

    def get_slot_image_map(self) -> dict:
        """슬롯 ID -> 이미지 소스 맵 반환

        어떤 이미지가 어디에 들어가는지 매핑 정보를 제공한다.
        Claude가 이미지 생성 결과를 슬롯에 매핑할 때 사용.

        Returns:
            dict: {slot_id: {"source": str, "pose": str|None, "crop": str|None}}
        """
        slots = get_all_slots(self.template_id)
        return {
            s.id: {
                "label": s.label,
                "source": s.source,
                "pose": s.pose_preset,
                "crop": s.crop_target,
                "size": f"{s.width}x{s.height}",
                "aspect_ratio": s.aspect_ratio,
            }
            for s in slots
        }

    def get_dependency_graph(self) -> dict:
        """액션 의존성 그래프 반환

        각 node_ref가 어떤 하위 액션에 의존하는지 표시.
        Claude가 parentId를 올바르게 주입하는 데 사용.

        Returns:
            dict: {node_ref: [depends_on_node_ref, ...]}
        """
        graph = {}
        for action in self.actions:
            if action.node_ref:
                graph[action.node_ref] = {
                    "tool": action.tool,
                    "depends_on": action.depends_on,
                    "description": action.description,
                }
        return graph

    def get_execution_instructions(self) -> str:
        """Claude용 실행 가이드 텍스트 생성

        Claude가 이 시퀀스를 Figma MCP로 실행할 때 참조하는 지침.
        """
        lines = [
            f"# Figma 상세페이지 빌드 시퀀스",
            f"",
            f"## 템플릿: {self.template.name}",
            f"## 브랜드: {self.template.brand}",
            f"## 페이지 폭: {self.template.page_width}px",
            f"## 총 액션 수: {len(self.actions)}",
            f"",
            f"## 실행 규칙",
            f"1. 액션을 순서대로 실행한다.",
            f"2. node_ref가 있는 액션은 생성된 노드 ID를 기록한다.",
            f"3. depends_on이 있는 액션은 해당 node_ref의 실제 노드 ID를",
            f"   parentId (create_frame/create_text) 또는 nodeId (set_node_image_fill, set_corner_radius) 파라미터에 주입한다.",
            f"4. model_spec 텍스트의 {{height}}, {{fitting_size}}는 실제 값으로 치환한다.",
            f"",
            f"## 액션 시퀀스",
        ]

        for i, action in enumerate(self.actions):
            dep_info = f" (parent: {action.depends_on})" if action.depends_on else ""
            ref_info = f" -> {action.node_ref}" if action.node_ref else ""
            slot_info = f" [slot: {action.slot_id}]" if action.slot_id else ""
            lines.append(
                f"  {i+1}. [{action.tool}] {action.description}"
                f"{dep_info}{ref_info}{slot_info}"
            )

        return "\n".join(lines)

    def print_summary(self):
        """빌드 시퀀스 요약 출력"""
        print(f"[Figma Builder] Template: {self.template.name}")
        print(f"[Figma Builder] Brand: {self.template.brand}")
        print(f"[Figma Builder] Page width: {self.template.page_width}px")
        print(f"[Figma Builder] Total actions: {len(self.actions)}")
        print(f"[Figma Builder] Sections:")
        for section in self.template.sections:
            slot_count = len(section.slots)
            if slot_count:
                print(f"  - {section.label}: {slot_count} slots ({section.type})")
            else:
                elem_count = len(section.elements)
                print(f"  - {section.label}: {elem_count} elements ({section.type})")

        # 슬롯 이미지 소스 요약
        slot_map = self.get_slot_image_map()
        if slot_map:
            print(f"[Figma Builder] Slot image map:")
            for slot_id, info in slot_map.items():
                print(f"  - {slot_id}: {info['source']} ({info['size']})")

    def format_model_spec_text(self, model_spec: dict) -> str:
        """모델 스펙 텍스트 포맷팅

        Args:
            model_spec: {"height": "175", "fitting_size": "S / 240mm"}

        Returns:
            포맷팅된 문자열 (예: "MODEL SPEC\nHeight : 175cm\nFitting Size : S / 240mm")
        """
        text_template = self.model_spec_format.get(
            "format",
            "MODEL SPEC\nHeight : {height}cm\nFitting Size : {fitting_size}",
        )
        height = model_spec.get("height", "175")
        fitting_size = model_spec.get("fitting_size", "FREE")
        return text_template.format(height=height, fitting_size=fitting_size)

    # ------------------------------------------------------------------
    # 컬러 유틸리티
    # ------------------------------------------------------------------

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """HEX -> RGB (0-1 범위)

        Args:
            hex_color: "#FFFFFF" 또는 "FFFFFF"

        Returns:
            (r, g, b) 각 0.0~1.0
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (1.0, 1.0, 1.0)  # 파싱 실패 시 흰색 기본값
        return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    @staticmethod
    def _hex_to_figma_color(hex_color: str) -> dict:
        """HEX -> Figma 컬러 dict {"r": float, "g": float, "b": float}"""
        r, g, b = DetailPageFigmaBuilder._hex_to_rgb(hex_color)
        return {"r": round(r, 4), "g": round(g, 4), "b": round(b, 4)}


# ------------------------------------------------------------------
# 편의 함수
# ------------------------------------------------------------------


def build_figma_detail_page(
    template_id: str = "mlb_standard",
    product_name: str = "Product",
    model_spec: Optional[dict] = None,
    fabric_info: Optional[dict] = None,
    image_urls: Optional[dict] = None,
    start_x: int = 0,
    start_y: int = 0,
) -> list[FigmaAction]:
    """상세페이지 Figma 빌드 시퀀스를 한 줄로 생성하는 편의 함수

    Args:
        template_id: 템플릿 ID
        product_name: 상품명
        model_spec: 모델 스펙
        fabric_info: 소재 정보
        image_urls: 슬롯별 이미지 URL
        start_x: 시작 X 좌표
        start_y: 시작 Y 좌표

    Returns:
        list[FigmaAction]: Figma MCP 도구 호출 시퀀스
    """
    builder = DetailPageFigmaBuilder(template_id=template_id)
    return builder.build_sequence(
        product_name=product_name,
        model_spec=model_spec,
        fabric_info=fabric_info,
        image_urls=image_urls,
        start_x=start_x,
        start_y=start_y,
    )


__all__ = [
    "FigmaAction",
    "DetailPageFigmaBuilder",
    "build_figma_detail_page",
]
