"""
워크플로 카테고리 선언적 설정

CLAUDE.md의 워크플로 카테고리 테이블을 코드로 표현:
- 인물-정규: 얼굴필수, 착장필수, 브랜드톤필수
- 인물-자유: 얼굴필수, 착장선택, 브랜드톤중요
- 스왑:     preserve/change 선언
- 배경:     인물유지, 착장유지, 배경변경
- 제품:     얼굴X, 착장X, 브랜드톤필수
- VMD:      얼굴X, 착장필수, 브랜드톤중요

사용법:
    from core.modules.workflow_config import WORKFLOW_REGISTRY, get_workflow_config

    config = get_workflow_config("brandcut")
    # config.category, config.analyzers, config.prompt_mode, ...
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# 카테고리 enum
# ============================================================


class WorkflowCategory(Enum):
    """CLAUDE.md 카테고리 테이블 기반"""

    PERSON_FORMAL = "인물-정규"  # 화보컷, 이커머스, 브랜드컷
    PERSON_FREE = "인물-자유"  # 인플루언서, UGC, 셀카
    SWAP = "스왑"  # 얼굴교체, 착장스왑, 포즈변경, 포즈카피
    BACKGROUND = "배경"  # 배경 교체, 배경 합성
    PRODUCT = "제품"  # 제품 디자인, 제품 연출, 슈즈 3D
    GRAPHIC = "그래픽"  # 그래픽 생성, 소재 생성
    VMD = "VMD"  # 마네킹 착장, 마네킹 포즈
    EDIT = "수정"  # 후보정, 인페인팅, 재질 조절


# ============================================================
# 분석 슬롯
# ============================================================


class AnalyzerSlot(Enum):
    """모듈화된 분석기 슬롯"""

    FACE = "face"
    OUTFIT = "outfit"
    POSE = "pose"
    EXPRESSION = "expression"
    HAIR = "hair"
    BACKGROUND = "background"
    PRESERVATION = "preservation"  # 스왑 전용


# ============================================================
# 워크플로 설정 데이터클래스
# ============================================================


@dataclass
class WorkflowConfig:
    """단일 워크플로의 전체 설정"""

    # 기본 정보
    name: str  # 워크플로 영문명 (예: "brandcut")
    name_kr: str  # 한국어명 (예: "브랜드컷")
    category: WorkflowCategory

    # 분석 설정
    analyzers: List[AnalyzerSlot] = field(default_factory=list)
    outfit_detail: str = "full"  # "full" | "basic" | "commerce"

    # 프롬프트 설정
    prompt_mode: str = "korean_detailed"  # outfit_section 모드
    brand_tone: bool = True  # 브랜드톤 섹션 포함 여부
    negative_base: bool = True  # 기본 네거티브 포함

    # 이미지 역할 (API 전송 시 역할 명시)
    image_roles: Dict[str, str] = field(default_factory=dict)

    # 카메라 기본값
    default_framing: Optional[str] = None  # None이면 프리셋/분석에서 결정
    default_aspect_ratio: str = "3:4"
    default_temperature: float = 0.7

    # 보존 (스왑 카테고리 전용)
    preserve: Optional[List[str]] = None
    change: Optional[List[str]] = None
    include_physical_constraints: bool = False

    # 워크플로 고유 확장
    extra: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 카테고리 기본 설정 (공통 베이스)
# ============================================================


def _person_formal_base() -> dict:
    """인물-정규 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.PERSON_FORMAL,
        analyzers=[
            AnalyzerSlot.FACE,
            AnalyzerSlot.OUTFIT,
            AnalyzerSlot.POSE,
            AnalyzerSlot.EXPRESSION,
            AnalyzerSlot.HAIR,
        ],
        outfit_detail="full",
        prompt_mode="korean_detailed",
        brand_tone=True,
        negative_base=True,
        image_roles={
            "FACE": "이 사람의 얼굴을 정확히 재현하세요",
            "OUTFIT": "이 착장의 모든 디테일을 정확히 재현하세요",
        },
    )


def _person_free_base() -> dict:
    """인물-자유 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.PERSON_FREE,
        analyzers=[
            AnalyzerSlot.FACE,
            AnalyzerSlot.POSE,
            AnalyzerSlot.EXPRESSION,
            AnalyzerSlot.HAIR,
            AnalyzerSlot.BACKGROUND,
        ],
        outfit_detail="basic",
        prompt_mode="image_first",
        brand_tone=True,
        negative_base=True,
        image_roles={
            "FACE": "이 사람의 얼굴을 정확히 재현하세요",
        },
    )


def _swap_base() -> dict:
    """스왑 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.SWAP,
        analyzers=[AnalyzerSlot.PRESERVATION],
        outfit_detail="full",
        prompt_mode="korean_detailed",
        brand_tone=True,
        negative_base=True,
    )


def _background_base() -> dict:
    """배경 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.BACKGROUND,
        analyzers=[AnalyzerSlot.PRESERVATION],
        outfit_detail="full",
        prompt_mode="korean_detailed",
        brand_tone=True,
        negative_base=True,
        preserve=["face", "pose", "outfit", "lighting", "hair", "body_type"],
        change=["background"],
    )


def _product_base() -> dict:
    """제품 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.PRODUCT,
        analyzers=[],
        outfit_detail="basic",
        prompt_mode="basic",
        brand_tone=True,
        negative_base=True,
        default_aspect_ratio="1:1",
    )


def _vmd_base() -> dict:
    """VMD 카테고리 공통 설정"""
    return dict(
        category=WorkflowCategory.VMD,
        analyzers=[
            AnalyzerSlot.OUTFIT,
            AnalyzerSlot.POSE,
        ],
        outfit_detail="full",
        prompt_mode="korean_detailed",
        brand_tone=True,
        negative_base=True,
    )


# ============================================================
# 워크플로 레지스트리 (모든 워크플로 선언)
# ============================================================


WORKFLOW_REGISTRY: Dict[str, WorkflowConfig] = {}


def _register(name: str, name_kr: str, base_func, **overrides):
    """워크플로 등록 헬퍼"""
    base = base_func()
    base.update(overrides)
    config = WorkflowConfig(name=name, name_kr=name_kr, **base)
    WORKFLOW_REGISTRY[name] = config
    return config


# ── 인물-정규 ─────────────────────────────────────

_register(
    "brandcut",
    "브랜드컷",
    _person_formal_base,
    default_framing="FS",
    default_aspect_ratio="3:4",
)

_register(
    "reference_brandcut",
    "레퍼런스 브랜드컷",
    _person_formal_base,
    default_framing="FS",
    default_aspect_ratio="3:4",
    image_roles={
        "REFERENCE": "이 이미지의 포즈/표정/구도를 그대로 유지하세요",
        "FACE": "이 사람의 얼굴로 교체하세요",
        "OUTFIT": "이 착장으로 교체하세요",
        "BACKGROUND": "이 배경을 참고하세요",
    },
)

_register(
    "ecommerce",
    "이커머스",
    _person_formal_base,
    default_framing="FS",
    default_aspect_ratio="3:4",
    outfit_detail="commerce",
    extra={
        "background": "깨끗한 화이트 스튜디오 배경, 부드러운 스튜디오 조명",
        "camera_angle": "front",
    },
)

# ── 인물-자유 ─────────────────────────────────────

_register(
    "influencer",
    "인플루언서",
    _person_free_base,
    default_aspect_ratio="9:16",
    analyzers=[
        AnalyzerSlot.FACE,
        AnalyzerSlot.OUTFIT,
        AnalyzerSlot.POSE,
        AnalyzerSlot.EXPRESSION,
        AnalyzerSlot.HAIR,
        AnalyzerSlot.BACKGROUND,
    ],
)

_register(
    "selfie",
    "셀카",
    _person_free_base,
    default_aspect_ratio="9:16",
    prompt_mode="basic",
)

_register(
    "seeding_ugc",
    "시딩UGC",
    _person_free_base,
    default_aspect_ratio="9:16",
    prompt_mode="basic",
)

# ── 스왑 ──────────────────────────────────────────

_register(
    "face_swap",
    "얼굴교체",
    _swap_base,
    preserve=["pose", "outfit", "background", "lighting"],
    change=["face"],
    image_roles={
        "SOURCE": "이 이미지에서 얼굴만 교체합니다 (나머지 완벽 유지)",
        "FACE": "이 사람의 얼굴로 교체하세요",
    },
)

_register(
    "multi_face_swap",
    "다중얼굴교체",
    _swap_base,
    preserve=["pose", "outfit", "background", "lighting"],
    change=["face"],
    image_roles={
        "SOURCE": "이 단체 사진에서 지정된 얼굴들만 교체합니다",
    },
)

_register(
    "outfit_swap",
    "착장스왑",
    _swap_base,
    preserve=["face", "pose", "background"],
    change=["outfit"],
    analyzers=[AnalyzerSlot.PRESERVATION, AnalyzerSlot.OUTFIT],
    image_roles={
        "SOURCE": "이 이미지에서 착장만 교체합니다 (얼굴/포즈 완벽 유지)",
        "OUTFIT": "이 착장으로 교체하세요",
    },
)

_register(
    "pose_change",
    "포즈변경",
    _swap_base,
    preserve=["face", "outfit", "background"],
    change=["pose"],
    include_physical_constraints=True,
    image_roles={
        "SOURCE": "이 이미지에서 포즈만 변경합니다 (얼굴/착장/배경 완벽 유지)",
    },
)

_register(
    "pose_copy",
    "포즈따라하기",
    _swap_base,
    preserve=["face", "outfit", "hair"],
    change=["pose", "background"],
    image_roles={
        "SOURCE": "이 인물의 얼굴과 착장을 유지하세요",
        "REFERENCE": "이 이미지의 포즈를 그대로 따라하세요",
    },
)

# ── 배경 ──────────────────────────────────────────

_register(
    "background_swap",
    "배경교체",
    _background_base,
    default_aspect_ratio="original",
    image_roles={
        "SOURCE": "이 인물을 완벽하게 보존하세요 (ONE_UNIT 원칙)",
    },
)

# ── 제품 ──────────────────────────────────────────

_register(
    "product_design",
    "제품디자인",
    _product_base,
)

_register(
    "product_styled",
    "제품연출",
    _product_base,
    default_aspect_ratio="3:4",
)

_register(
    "shoes_3d",
    "슈즈3D",
    _product_base,
)

_register(
    "fabric_generation",
    "소재생성",
    _product_base,
)

# ── VMD ───────────────────────────────────────────

_register(
    "mannequin_outfit",
    "마네킹착장",
    _vmd_base,
    extra={"model_type": "mannequin"},
    image_roles={
        "OUTFIT": "이 착장을 마네킹에 정확히 입히세요",
    },
)

_register(
    "mannequin_pose",
    "마네킹포즈",
    _vmd_base,
    extra={"model_type": "mannequin"},
    analyzers=[AnalyzerSlot.OUTFIT, AnalyzerSlot.POSE, AnalyzerSlot.PRESERVATION],
    preserve=["outfit"],
    change=["pose"],
)


# ============================================================
# 조회 API
# ============================================================


def get_workflow_config(name: str) -> WorkflowConfig:
    """워크플로 설정 조회.

    Args:
        name: 워크플로 영문명 (예: "brandcut", "face_swap")

    Returns:
        WorkflowConfig 객체

    Raises:
        KeyError: 미등록 워크플로
    """
    if name not in WORKFLOW_REGISTRY:
        available = sorted(WORKFLOW_REGISTRY.keys())
        raise KeyError(f"미등록 워크플로: '{name}'. " f"사용 가능: {available}")
    return WORKFLOW_REGISTRY[name]


def list_workflows() -> List[str]:
    """등록된 워크플로 목록 반환"""
    return sorted(WORKFLOW_REGISTRY.keys())


def list_by_category(category: WorkflowCategory) -> List[WorkflowConfig]:
    """카테고리별 워크플로 목록 반환"""
    return [cfg for cfg in WORKFLOW_REGISTRY.values() if cfg.category == category]


__all__ = [
    "WorkflowCategory",
    "AnalyzerSlot",
    "WorkflowConfig",
    "WORKFLOW_REGISTRY",
    "get_workflow_config",
    "list_workflows",
    "list_by_category",
]
