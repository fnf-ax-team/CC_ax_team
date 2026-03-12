"""
네거티브 프롬프트 빌더

3대 워크플로의 네거티브 프롬프트를 통합:
- 기본 AI 공통 네거티브 (손가락 변형, 플라스틱 피부, 텍스트/워터마크)
- 브랜드별 네거티브 (MLB: 골든아워/웜앰버/밝은미소, Discovery 등)
- 프레이밍별 자동 네거티브 (인플루언서 _FRAMING_NEGATIVES)
- 포즈 기반 조건부 네거티브 (특이 포즈 경고)
- 조건부 추가 (walk/sit/vehicle 배경 등)

원본:
- core.brandcut.prompt_builder_v2.MLB_BRAND_DNA["negative"]
- core.ai_influencer.prompt_builder._build_negative_prompt() + _FRAMING_NEGATIVES
- core.ai_influencer.prompt_builder.build_schema_prompt() 조건부 네거티브 로직
"""

from typing import List, Optional


# ============================================================
# 기본 네거티브 (모든 워크플로 공통)
# ============================================================

BASE_NEGATIVES = [
    "deformed fingers",
    "extra fingers",
    "missing fingers",
    "plastic skin",
    "AI look",
    "overprocessed",
    "text",
    "watermark",
    "signature",
    "cartoon style",
    "illustration style",
]


# ============================================================
# 브랜드별 네거티브
#
# MLB: brandcut prompt_builder_v2.MLB_BRAND_DNA["negative"]
# Discovery/Duvetica 등은 향후 치트시트 기반 확장
# ============================================================

BRAND_NEGATIVES = {
    "MLB": [
        "bright smile",
        "teeth showing",
        "golden hour",
        "warm amber",
        "yellow cast",
        "weak posture",
        "messy background",
    ],
    "Discovery": [
        "indoor studio",
        "formal wear",
        "weak posture",
    ],
    "Duvetica": [
        "cheap fabric",
        "sportswear aesthetic",
    ],
    "Sergio Tacchini": [
        "modern minimalist",
        "luxury aesthetic",
    ],
    "Banila Co": [
        "harsh lighting",
        "heavy makeup",
    ],
}


# ============================================================
# 프레이밍별 자동 네거티브
# 원본: influencer prompt_builder._FRAMING_NEGATIVES
#
# 해당 프레이밍에서 보이면 안 되는 것들:
# MFS(허벅지에서 끊김) -> 무릎/종아리/발 보이면 안됨
# FS(발끝까지 보임) -> 허리/무릎에서 잘리면 안됨
# ============================================================

FRAMING_NEGATIVES = {
    "CU": ["full body visible", "legs visible", "waist visible"],
    "MCU": ["full body visible", "legs visible", "below waist visible"],
    "MS": ["full body visible", "feet visible", "legs below knee visible"],
    "MFS": [
        "feet visible",
        "shoes visible",
        "ankles visible",
        "calves visible",
        "shins visible",
        "knees visible",
        "full body head to toe",
        "legs below knee",
        "lower legs showing",
    ],
    "FS": ["cropped at waist", "cropped at knee", "legs cut off"],
    "WS": ["tight crop", "cropped body"],
}


# ============================================================
# 포즈 기반 네거티브 (특이 포즈 경고용)
# 원본: influencer prompt_builder.build_schema_prompt() 조건부 로직
# ============================================================

_LIFTED_LEG_NEGATIVES = [
    "both feet on ground",
    "standing with both legs",
    "flat-footed stance",
    "symmetrical leg position",
]

_FIGURE4_NEGATIVES = [
    "knee pointing forward",
    "knee lifted upward",
    "L-shaped leg",
    "foot dangling in front",
    "foot pointing outward",
    "foot pointing backward",
    "foot sole facing outward",
]


# ============================================================
# NegativePromptBuilder (플루언트 API)
# ============================================================


class NegativePromptBuilder:
    """
    네거티브 프롬프트를 단계적으로 조립하는 빌더.

    사용법:
        negative = (
            NegativePromptBuilder()
            .add_base()
            .add_brand("MLB")
            .add_framing("MFS")
            .add_if(is_walking, ["static pose", "standing still"])
            .build()
        )
    """

    def __init__(self):
        self._items: List[str] = []

    def add_base(self) -> "NegativePromptBuilder":
        """기본 AI 공통 네거티브 추가 (손가락, 피부, 텍스트 등)"""
        self._items.extend(BASE_NEGATIVES)
        return self

    def add_brand(self, brand: str) -> "NegativePromptBuilder":
        """브랜드별 네거티브 추가.

        Args:
            brand: 브랜드명 (예: "MLB", "Discovery")
        """
        brand_negs = BRAND_NEGATIVES.get(brand, [])
        self._items.extend(brand_negs)
        return self

    def add_if(self, condition: bool, items: List[str]) -> "NegativePromptBuilder":
        """조건부 네거티브 추가.

        Args:
            condition: True일 때만 추가
            items: 추가할 네거티브 항목 리스트
        """
        if condition:
            self._items.extend(items)
        return self

    def add_framing(self, framing: Optional[str]) -> "NegativePromptBuilder":
        """프레이밍 기반 네거티브 자동 추가.

        프레이밍 코드(CU~WS)에 따라 해당 프레이밍에서 보이면 안 되는 것들을 추가.

        Args:
            framing: 프레이밍 코드 (예: "MFS", "FS", "CU")
        """
        if framing:
            negs = FRAMING_NEGATIVES.get(framing.upper(), [])
            self._items.extend(negs)
        return self

    def add_pose(
        self, pose_tags: Optional[List[str]] = None
    ) -> "NegativePromptBuilder":
        """포즈 기반 네거티브 추가.

        특이 포즈(다리 들기, 4자 다리 등)에 대한 경고 네거티브.

        Args:
            pose_tags: 포즈 태그 리스트. 지원 태그:
                - "leg_lifted": 다리 들기 포즈
                - "figure4": 4자 다리 포즈
                - "walk": 걷기 포즈
                - "sit": 앉기 포즈
        """
        if not pose_tags:
            return self

        for tag in pose_tags:
            tag_lower = tag.lower()

            if tag_lower == "leg_lifted":
                self._items.extend(_LIFTED_LEG_NEGATIVES)

            elif tag_lower == "figure4":
                self._items.extend(_FIGURE4_NEGATIVES)

            elif tag_lower == "walk":
                self._items.extend(["static pose", "standing still"])

            elif tag_lower == "sit":
                self._items.extend(["standing pose", "both feet on ground"])

        return self

    def add_items(self, items: List[str]) -> "NegativePromptBuilder":
        """임의의 네거티브 항목 직접 추가.

        Args:
            items: 네거티브 문자열 리스트
        """
        self._items.extend(items)
        return self

    def build(self) -> str:
        """조립된 네거티브 프롬프트를 쉼표로 연결하여 반환.

        중복 제거 후 반환한다 (삽입 순서 유지).

        Returns:
            네거티브 프롬프트 문자열
        """
        # 중복 제거 (삽입 순서 유지)
        seen = set()
        unique = []
        for item in self._items:
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(item.strip())

        return ", ".join(unique)


# ============================================================
# 편의 함수
# ============================================================


def build_default_negative(brand: Optional[str] = None) -> str:
    """기본 + 브랜드 네거티브를 한번에 빌드하는 편의 함수.

    Args:
        brand: 브랜드명 (None이면 기본만)

    Returns:
        네거티브 프롬프트 문자열
    """
    builder = NegativePromptBuilder().add_base()
    if brand:
        builder.add_brand(brand)
    return builder.build()


__all__ = [
    "NegativePromptBuilder",
    "BASE_NEGATIVES",
    "BRAND_NEGATIVES",
    "FRAMING_NEGATIVES",
    "build_default_negative",
]
