"""
이커머스 상세페이지 템플릿 프리셋 모듈.
db/ecommerce_templates.json을 로드하고 관리한다.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# DB 경로
TEMPLATES_DB = Path(__file__).parent.parent.parent / "db" / "ecommerce_templates.json"


@dataclass
class SlotConfig:
    """이미지 슬롯 설정"""

    id: str
    label: str
    width: int
    height: int
    aspect_ratio: str
    source: str  # ai_generate, product_image, crop_detail
    pose_preset: Optional[str] = None
    background: Optional[str] = None
    crop_target: Optional[str] = None
    overlay: Optional[dict] = None


@dataclass
class SectionConfig:
    """섹션 설정"""

    id: str
    type: str  # image_grid, info_section
    label: str
    slots: list = field(default_factory=list)
    elements: list = field(default_factory=list)
    width: int = 860
    height: Optional[int] = None
    gap: int = 0
    layout: str = "vertical"
    background: Optional[str] = None


@dataclass
class TemplateConfig:
    """상세페이지 템플릿 설정"""

    name: str
    brand: str
    page_width: int
    background_color: str
    sections: list  # list[SectionConfig]


def load_templates() -> dict:
    """템플릿 DB 로드 (S3/로컬 자동 전환)"""
    from core.storage import get_json

    try:
        return get_json("db/ecommerce_templates.json")
    except FileNotFoundError:
        # 로컬 폴백
        with open(TEMPLATES_DB, "r", encoding="utf-8") as f:
            return json.load(f)


def get_template(template_id: str = "mlb_standard") -> TemplateConfig:
    """특정 템플릿 가져오기"""
    data = load_templates()
    tpl = data["templates"][template_id]

    sections = []
    for sec in tpl["sections"]:
        slots = [SlotConfig(**s) for s in sec.get("slots", [])]
        sections.append(
            SectionConfig(
                id=sec["id"],
                type=sec["type"],
                label=sec["label"],
                slots=slots,
                elements=sec.get("elements", []),
                width=sec.get("width", tpl["page_width"]),
                height=sec.get("height"),
                gap=sec.get("gap", 0),
                layout=sec.get("layout", "vertical"),
                background=sec.get("background"),
            )
        )

    return TemplateConfig(
        name=tpl["name"],
        brand=tpl["brand"],
        page_width=tpl["page_width"],
        background_color=tpl["background_color"],
        sections=sections,
    )


def get_all_slots(template_id: str = "mlb_standard") -> list:
    """모든 이미지 슬롯 목록"""
    tpl = get_template(template_id)
    all_slots = []
    for section in tpl.sections:
        all_slots.extend(section.slots)
    return all_slots


def get_slots_by_source(
    template_id: str = "mlb_standard", source: str = "ai_generate"
) -> list:
    """소스 타입별 슬롯 필터"""
    return [s for s in get_all_slots(template_id) if s.source == source]


def get_model_spec_format(brand: str = "MLB") -> dict:
    """모델 스펙 텍스트 포맷"""
    data = load_templates()
    return data.get("model_spec_defaults", {}).get(brand, {})
