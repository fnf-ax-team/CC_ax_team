"""
공유 설정 - 파이프라인 설정 데이터클래스
"""

import os
from dataclasses import dataclass
from typing import Tuple

# ============================================================
# 모델 상수 (여기만 바꾸면 전체 반영)
# ============================================================
IMAGE_MODEL = "gemini-3-pro-image-preview"
VISION_MODEL = "gemini-3-flash-preview"  # Vision analysis (text + image input)

# ============================================================
# 출력 경로 (여기만 바꾸면 전체 반영)
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "Fnf_studio_outputs")


@dataclass
class PipelineConfig:
    """파이프라인 설정"""

    # 생성 설정
    max_workers: int = 3
    image_model: str = "gemini-3-pro-image-preview"
    vision_model: str = "gemini-3-flash-preview"  # Vision analysis model
    image_size: str = "2K"

    # 검수 기준
    model_preservation_threshold: int = 100
    total_score_threshold: int = 95

    # 재시도 설정
    max_retries: int = 2
    temperature_schedule: Tuple[float, ...] = (0.15, 0.1, 0.05)  # First attempt 0.15 for better preservation
    enable_retry: bool = True

    # 진단 기준
    pose_match_threshold: int = 90
    face_match_threshold: int = 95
    scale_match_threshold: int = 85
    physics_threshold: int = 80
    physics_plausibility_threshold: int = 50
    clothing_match_threshold: int = 90
    prop_style_threshold: int = 70
    lighting_match_threshold: int = 80
    ground_contact_threshold: int = 80
    edge_quality_threshold: int = 85
    perspective_match_threshold: int = 80
    lighting_harmonization: bool = False  # 라이팅 허용 모드 (커머스/룩북용)

    # 이미지 설정
    max_image_size: int = 2048

    # API 설정
    api_retry_count: int = 3
    api_retry_delay: int = 10

# ============================================================
# Tripo 3D API 설정
# ============================================================
TRIPO_API_BASE = "https://api.tripo3d.ai/v2"
TRIPO_API_KEY = os.getenv("TRIPO_API_KEY", "")


# Tripo API 에러 코드
class TripoErrorCode:
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMIT = 429
    SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# Tripo Rate Limit 설정
TRIPO_RATE_LIMIT_DELAY = 60
TRIPO_MAX_RETRIES = 3

# Tripo 폴링 설정
TRIPO_POLL_TIMEOUT = 300
TRIPO_POLL_INTERVAL = 5


@dataclass
class ProductRetryConfig:
    """제품 이미지 생성 재시도 설정"""
    max_retries: int = 2
    temperature_schedule: Tuple[float, ...] = (0.2, 0.15, 0.1)
    tripo_poll_timeout: int = 300
    temp_reduction_on_fail: float = 0.05

    def get_temperature(self, attempt: int) -> float:
        """재시도 횟수에 따른 temperature 반환"""
        if attempt < len(self.temperature_schedule):
            return self.temperature_schedule[attempt]
        return self.temperature_schedule[-1]


PRODUCT_RETRY_CONFIG = ProductRetryConfig()


@dataclass
class ProductPipelineConfig(PipelineConfig):
    """제품 이미지 파이프라인 설정 (PipelineConfig 확장)"""

    # 3D 생성 설정
    tripo_poll_timeout: int = 300
    tripo_poll_interval: int = 5
    tripo_max_retries: int = 3

    # 제품 이미지 검수 기준
    product_match_threshold: int = 90
    material_fidelity_threshold: int = 85
    detail_preservation_threshold: int = 80

    # 제품 이미지 재시도 설정
    product_retry_config: ProductRetryConfig = None

    def __post_init__(self):
        """초기화 후 기본값 설정"""
        if self.product_retry_config is None:
            self.product_retry_config = PRODUCT_RETRY_CONFIG
