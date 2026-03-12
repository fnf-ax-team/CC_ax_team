"""
뷰티 영상 설정 - KlingAI Video API 설정 + 비디오 옵션

core/config.py와 core/options.py에서 비디오 관련 설정을 통합.
"""

import os
from dataclasses import dataclass
from typing import Dict, List


# ============================================================
# KlingAI Video API 설정
# ============================================================
KLING_API_BASE = "https://api.klingai.com"
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")

# KlingAI 모델 상수
KLING_DEFAULT_MODEL = "kling-v2-0"  # 기본 모델 (최신 안정 버전)
KLING_MODELS = ["kling-v1-6", "kling-v2-0", "kling-v2-5"]


# KlingAI API 에러 코드
class KlingErrorCode:
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMIT = 429
    SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# KlingAI 폴링 설정 (비디오 생성은 오래 걸림)
KLING_POLL_TIMEOUT = 600  # 10분
KLING_POLL_INTERVAL = 10  # 10초마다
KLING_MAX_RETRIES = 3
KLING_JWT_TTL = 1800  # JWT 토큰 유효시간 30분


@dataclass
class VideoGenerationConfig:
    """비디오 생성 설정"""

    model_name: str = "kling-v2-0"
    mode: str = "std"  # "std" 또는 "pro"
    duration: str = "5"  # "5" 또는 "10" (초)
    cfg_scale: float = 0.5  # 0.0~1.0 (프롬프트 충실도)
    aspect_ratio: str = "16:9"  # "16:9", "9:16", "1:1"
    enable_audio: bool = False  # kling-v2-6 + pro 모드에서만 네이티브 오디오 생성
    poll_timeout: int = 600
    poll_interval: int = 10
    max_retries: int = 3


# ============================================================
# 비디오 비율 (Video Aspect Ratio) - KlingAI 지원
# ============================================================
VIDEO_ASPECT_RATIOS: Dict[str, Dict] = {
    "16:9": {"용도": "가로 영상 (기본)", "시각화": "▭"},
    "9:16": {"용도": "세로 숏폼/릴스", "시각화": "▯"},
    "1:1": {"용도": "정사각 SNS", "시각화": "□"},
}

ALLOWED_VIDEO_ASPECT_RATIOS: List[str] = list(VIDEO_ASPECT_RATIOS.keys())


# ============================================================
# 비디오 길이 (Video Duration)
# ============================================================
VIDEO_DURATIONS: Dict[str, Dict] = {
    "5": {"초": 5, "용도": "숏폼/SNS 클립", "cost_multiplier": 1.0},
    "10": {"초": 10, "용도": "일반 영상", "cost_multiplier": 2.0},
}


# ============================================================
# 비디오 모드 (Video Mode)
# ============================================================
VIDEO_MODES: Dict[str, Dict] = {
    "std": {"이름": "Standard", "용도": "일반 품질", "cost_multiplier": 1.0},
    "pro": {"이름": "Professional", "용도": "고품질", "cost_multiplier": 1.33},
}


# ============================================================
# 비디오 비용 (Cost) - KlingAI API 공식가격 기준 (원/건)
# 환율 기준: $1 = 1,450원 (2026.03)
# 공식 가격표: https://klingai.com/global/dev/pricing
# ============================================================
# Kling-V3 모델 기준 (2026.03 현재)
#   Standard 5s: $0.084 → 122원
#   Standard 10s: $0.126 → 183원
#   Pro 5s: $0.112 → 162원
#   Pro 10s: $0.168 → 244원
#   V2A 5s: $0.035 → 51원
#   V2A 10s: (동일 단가 추정) → 51원
# ============================================================
VIDEO_COST_TABLE: Dict[str, int] = {
    "std_5s": 122,  # $0.084/건
    "std_10s": 183,  # $0.126/건
    "pro_5s": 162,  # $0.112/건
    "pro_10s": 244,  # $0.168/건
    "v2a_5s": 51,  # $0.035/건 (Video-to-Audio)
    "v2a_10s": 51,  # $0.035/건 (Video-to-Audio)
}

# ElevenLabs TTS 비용 (원/200자)
# Pro plan 초과분: $0.24/1,000자 → 200자 ≈ 70원
# Scale plan 초과분: $0.18/1,000자 → 200자 ≈ 52원
# 공식: https://elevenlabs.io/pricing/api
TTS_COST_PER_200_CHARS: int = 70  # Pro plan 기준

# Suno BGM 비용 (원/곡)
# sunoapi.org 3rd-party API: 1회 12크레딧, 1000크레딧 = $5
# → $0.06/곡 × 1,450원/$ ≈ 87원
# 공식: https://sunoapi.org/
BGM_COST_PER_SONG: int = 87


def get_video_cost(mode: str, duration: str, quantity: int = 1) -> int:
    """비디오 생성 비용 계산

    Args:
        mode: "std" 또는 "pro"
        duration: "5" 또는 "10"
        quantity: 생성 수량

    Returns:
        총 비용 (원)
    """
    key = f"{mode}_{duration}s"
    unit_cost = VIDEO_COST_TABLE.get(key, 500)
    return unit_cost * quantity


def validate_video_aspect_ratio(aspect_ratio: str) -> bool:
    """비디오 비율 유효성 검사

    Args:
        aspect_ratio: 비율 문자열 (e.g., "16:9")

    Returns:
        유효 여부
    """
    return aspect_ratio in ALLOWED_VIDEO_ASPECT_RATIOS
