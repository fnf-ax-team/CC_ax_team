"""
뷰티 영상 릴스 워크플로 통합 모듈

시나리오 -> 스타트프레임(Gemini) -> 영상(Kling I2V, 무음)
-> 연결(moviepy) -> TTS(ElevenLabs) -> BGM(Suno) -> 싱크자막

사용법:
    # 뷰티 릴스 파이프라인 (End-to-End)
    from core.beauty_video import generate_beauty_reels

    # 비디오 생성 (T2V/I2V)
    from core.beauty_video import generate_text_to_video, generate_image_to_video

    # TTS 나레이션 (ElevenLabs)
    from core.beauty_video.tts import generate_tts, overlay_tts_on_video

    # BGM (Suno API)
    from core.beauty_video.bgm import generate_bgm, overlay_bgm_on_video

    # 영상 싱크 자막
    from core.beauty_video.video_subtitle import add_synced_subtitles, calculate_phrase_timings

    # 이미지 자막 (스타트프레임 베이킹용)
    from core.beauty_video import build_subtitle_prompt, apply_subtitle, apply_subtitle_to_image

    # 프리셋
    from core.beauty_video import BEAUTY_CAMERA_MOVES, BEAUTY_AUDIO_PROMPTS
"""

# 파이프라인
from .pipeline import generate_beauty_reels

# 프리셋
from .presets import (
    BEAUTY_CAMERA_MOVES,
    BEAUTY_AUDIO_PROMPTS,
    BEAUTY_NEGATIVE_PROMPT,
    BEAUTY_CUT_TYPES,
)

# 비디오 생성 (T2V/I2V)
from .client import KlingAIClient, KlingAPIError
from .generator import (
    generate_text_to_video,
    generate_image_to_video,
)

# 프롬프트 빌더
from .prompt_builder import (
    build_fashion_video_prompt,
    build_i2v_motion_prompt,
    FASHION_VIDEO_ACTIONS,
    CAMERA_MOVEMENTS,
    VIDEO_SETTINGS,
    DEFAULT_NEGATIVE_PROMPT,
)

# 이미지 자막 (스타트프레임 베이킹용)
from .subtitle_style import (
    build_subtitle_prompt,
    apply_subtitle,
    apply_subtitle_to_image,
    ACCENT_COLORS,
)

# 영상 싱크 자막
from .video_subtitle import (
    add_synced_subtitles,
    calculate_phrase_timings,
    SUBTITLE_STYLES,
)

# TTS (ElevenLabs)
from .tts import (
    generate_tts,
    generate_tts_for_voice_preset,
    overlay_tts_on_video,
    VOICE_PRESETS,
)

# BGM (Suno API)
from .bgm import (
    generate_bgm,
    generate_bgm_for_preset,
    overlay_bgm_on_video,
    BGM_PRESETS,
)

# 설정
from .config import (
    VideoGenerationConfig,
    VIDEO_COST_TABLE,
    get_video_cost,
    validate_video_aspect_ratio,
    VIDEO_ASPECT_RATIOS,
    VIDEO_DURATIONS,
    VIDEO_MODES,
    KLING_DEFAULT_MODEL,
    KLING_MODELS,
    TTS_COST_PER_200_CHARS,
    BGM_COST_PER_SONG,
)

__all__ = [
    # 파이프라인
    "generate_beauty_reels",
    # 프리셋
    "BEAUTY_CAMERA_MOVES",
    "BEAUTY_AUDIO_PROMPTS",
    "BEAUTY_NEGATIVE_PROMPT",
    "BEAUTY_CUT_TYPES",
    # 비디오 생성
    "KlingAIClient",
    "KlingAPIError",
    "generate_text_to_video",
    "generate_image_to_video",
    # 프롬프트 빌더
    "build_fashion_video_prompt",
    "build_i2v_motion_prompt",
    "FASHION_VIDEO_ACTIONS",
    "CAMERA_MOVEMENTS",
    "VIDEO_SETTINGS",
    "DEFAULT_NEGATIVE_PROMPT",
    # 이미지 자막
    "build_subtitle_prompt",
    "apply_subtitle",
    "apply_subtitle_to_image",
    "ACCENT_COLORS",
    # 영상 싱크 자막
    "add_synced_subtitles",
    "calculate_phrase_timings",
    "SUBTITLE_STYLES",
    # TTS
    "generate_tts",
    "generate_tts_for_voice_preset",
    "overlay_tts_on_video",
    "VOICE_PRESETS",
    # BGM
    "generate_bgm",
    "generate_bgm_for_preset",
    "overlay_bgm_on_video",
    "BGM_PRESETS",
    # 설정
    "VideoGenerationConfig",
    "VIDEO_COST_TABLE",
    "get_video_cost",
    "validate_video_aspect_ratio",
    "VIDEO_ASPECT_RATIOS",
    "VIDEO_DURATIONS",
    "VIDEO_MODES",
    "KLING_DEFAULT_MODEL",
    "KLING_MODELS",
    "TTS_COST_PER_200_CHARS",
    "BGM_COST_PER_SONG",
]
