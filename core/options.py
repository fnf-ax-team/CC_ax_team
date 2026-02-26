"""
공유 옵션 - 이미지 생성 옵션의 Single Source of Truth

모든 워크플로에서 이 모듈의 상수를 import해서 사용한다.
하드코딩 금지! 이 파일만 수정하면 전체 반영.

사용법:
    from core.options import (
        ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,
        DEFAULT_ASPECT_RATIO, DEFAULT_RESOLUTION,
        get_cost, get_resolution_px
    )
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass


# ============================================================
# 비율 (Aspect Ratio)
# ============================================================
ASPECT_RATIOS: Dict[str, Dict] = {
    "1:1": {"용도": "정사각/프로필/SNS", "시각화": "□"},
    "2:3": {"용도": "세로 포트레이트", "시각화": "▯"},
    "3:2": {"용도": "가로 랜드스케이프", "시각화": "▭"},
    "3:4": {"용도": "세로 화보 (기본)", "시각화": "▯"},
    "4:3": {"용도": "가로 화보", "시각화": "▭"},
    "4:5": {"용도": "인스타 피드", "시각화": "▯"},
    "5:4": {"용도": "가로 피드", "시각화": "▭"},
    "9:16": {"용도": "스토리/릴스/숏폼", "시각화": "▯"},
    "16:9": {"용도": "유튜브/가로 영상", "시각화": "▭"},
    "21:9": {"용도": "시네마틱/울트라와이드", "시각화": "▭▭"},
}

# 허용된 비율 목록 (validation용)
ALLOWED_ASPECT_RATIOS: List[str] = list(ASPECT_RATIOS.keys())


# ============================================================
# 해상도 (Resolution)
# ============================================================
RESOLUTIONS: Dict[str, Dict] = {
    "1K": {"px": 1024, "용도": "테스트/미리보기", "cost_tier": "standard"},
    "2K": {"px": 2048, "용도": "기본값 (SNS/웹)", "cost_tier": "standard"},
    "4K": {"px": 4096, "용도": "최종 결과물/인쇄", "cost_tier": "premium"},
}

# 허용된 해상도 목록 (validation용)
ALLOWED_RESOLUTIONS: List[str] = list(RESOLUTIONS.keys())


# ============================================================
# 비용 (Cost) - 2026.02 Gemini API 기준
# ============================================================
COST_TABLE: Dict[str, int] = {
    "standard": 190,  # 1K, 2K (원/장)
    "premium": 380,  # 4K (원/장)
}

# 수량별 총 비용 계산 헬퍼
QUANTITY_PRESETS: List[int] = [1, 3, 5, 10]


# ============================================================
# 기본값 (Defaults)
# ============================================================
DEFAULT_ASPECT_RATIO: str = "3:4"
DEFAULT_RESOLUTION: str = "2K"
DEFAULT_QUANTITY: int = 1


# ============================================================
# 워크플로별 권장 설정
# ============================================================
@dataclass
class WorkflowDefaults:
    """워크플로별 기본 설정"""

    aspect_ratio: str
    temperature: float
    description: str


WORKFLOW_DEFAULTS: Dict[str, WorkflowDefaults] = {
    "brandcut": WorkflowDefaults("3:4", 0.25, "브랜드컷 (에디토리얼)"),
    "reference_brandcut": WorkflowDefaults("3:4", 0.2, "레퍼런스 브랜드컷"),
    "background_swap": WorkflowDefaults("original", 0.2, "배경 교체"),
    "influencer": WorkflowDefaults("9:16", 0.5, "인플루언서"),
    "selfie": WorkflowDefaults("9:16", 0.3, "셀피/UGC"),
    "daily_casual": WorkflowDefaults("4:5", 0.3, "데일리 캐주얼"),
    "seeding_ugc": WorkflowDefaults("9:16", 0.35, "시딩 UGC"),
    "product_shot": WorkflowDefaults("1:1", 0.2, "제품샷"),
    "free_generation": WorkflowDefaults("3:4", 0.4, "자유 생성"),
    "experimental": WorkflowDefaults("3:4", 0.8, "실험적/아트"),
}


# ============================================================
# 헬퍼 함수
# ============================================================
def get_resolution_px(resolution: str) -> int:
    """해상도 문자열을 픽셀 값으로 변환

    Args:
        resolution: "1K", "2K", "4K"

    Returns:
        픽셀 값 (1024, 2048, 4096)

    Raises:
        ValueError: 허용되지 않은 해상도
    """
    if resolution not in RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution: {resolution}. " f"Allowed: {ALLOWED_RESOLUTIONS}"
        )
    return RESOLUTIONS[resolution]["px"]


def get_cost(resolution: str, quantity: int = 1) -> int:
    """해상도와 수량에 따른 총 비용 계산

    Args:
        resolution: "1K", "2K", "4K"
        quantity: 이미지 수량

    Returns:
        총 비용 (원)
    """
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Invalid resolution: {resolution}")

    cost_tier = RESOLUTIONS[resolution]["cost_tier"]
    unit_cost = COST_TABLE[cost_tier]
    return unit_cost * quantity


def validate_aspect_ratio(aspect_ratio: str) -> bool:
    """비율 유효성 검사

    Args:
        aspect_ratio: 비율 문자열 (e.g., "3:4")

    Returns:
        유효 여부
    """
    return aspect_ratio in ALLOWED_ASPECT_RATIOS


def validate_resolution(resolution: str) -> bool:
    """해상도 유효성 검사

    Args:
        resolution: 해상도 문자열 (e.g., "2K")

    Returns:
        유효 여부
    """
    return resolution in ALLOWED_RESOLUTIONS


def get_workflow_defaults(workflow_type: str) -> WorkflowDefaults:
    """워크플로 타입에 맞는 기본 설정 반환

    Args:
        workflow_type: 워크플로 타입 (e.g., "brandcut")

    Returns:
        WorkflowDefaults 객체
    """
    return WORKFLOW_DEFAULTS.get(
        workflow_type.lower(),
        WorkflowDefaults(DEFAULT_ASPECT_RATIO, 0.3, "Unknown workflow"),
    )


def format_options_for_user() -> str:
    """사용자에게 보여줄 옵션 표 생성

    Returns:
        마크다운 형식의 옵션 표
    """
    lines = ["## 비율 (Aspect Ratio)", ""]
    lines.append("| 비율 | 용도 | 시각화 |")
    lines.append("|------|------|--------|")
    for ratio, info in ASPECT_RATIOS.items():
        lines.append(f"| `{ratio}` | {info['용도']} | {info['시각화']} |")

    lines.append("")
    lines.append("## 화질 (Resolution)")
    lines.append("")
    lines.append("| 화질 | 해상도 | 용도 | 장당 비용 |")
    lines.append("|------|--------|------|----------|")
    for res, info in RESOLUTIONS.items():
        cost = COST_TABLE[info["cost_tier"]]
        lines.append(f"| `{res}` | {info['px']}px | {info['용도']} | ₩{cost:,} |")

    lines.append("")
    lines.append("## 수량별 비용")
    lines.append("")
    lines.append("| 수량 | 1K~2K 비용 | 4K 비용 |")
    lines.append("|------|-----------|---------|")
    for qty in QUANTITY_PRESETS:
        std_cost = COST_TABLE["standard"] * qty
        prm_cost = COST_TABLE["premium"] * qty
        lines.append(f"| {qty}장 | ₩{std_cost:,} | ₩{prm_cost:,} |")

    return "\n".join(lines)


# ============================================================
# 옵션 하드코딩 감지용 패턴 (Hooks에서 사용)
# ============================================================
HARDCODED_PATTERNS = {
    "aspect_ratio": [
        r'aspect_ratio\s*=\s*["\'][\d:]+["\']',  # aspect_ratio = "3:4"
        r'["\'](1:1|2:3|3:2|3:4|4:3|4:5|5:4|9:16|16:9|21:9)["\']',  # 직접 문자열
    ],
    "resolution": [
        r'image_size\s*=\s*["\'][124]K["\']',  # image_size = "2K"
        r'resolution\s*=\s*["\'][124]K["\']',  # resolution = "2K"
    ],
    "cost": [
        r"cost\s*=\s*\d+",  # cost = 190
        r'["\']?\d{3}원["\']?',  # 190원
    ],
}


# ============================================================
# 모듈 직접 실행 시 옵션 표 출력
# ============================================================
if __name__ == "__main__":
    print(format_options_for_user())
