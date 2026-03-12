"""
비디오 프롬프트 빌더

패션 비디오용 프롬프트 조립 헬퍼 + 프리셋
"""

from typing import Optional


# ============================================================
# 패션 비디오 액션 프리셋
# ============================================================
FASHION_VIDEO_ACTIONS = {
    "walk": "walking confidently toward camera",
    "turn": "turning 360 degrees to show outfit details",
    "pose_shift": "shifting between poses naturally",
    "runway": "walking a runway with confident stride",
    "casual": "casually walking down the street",
    "dynamic": "moving dynamically with energy",
    "seated": "sitting elegantly and turning head toward camera",
    "lean": "leaning against wall and adjusting clothes naturally",
}


# ============================================================
# 카메라 무브먼트 프리셋
# ============================================================
CAMERA_MOVEMENTS = {
    "static": "static medium shot",
    "tracking": "smooth tracking shot following model",
    "orbit": "slow orbiting shot around model",
    "dolly_in": "slow dolly-in from full body to upper body",
    "dolly_out": "slow dolly-out from close-up to full body",
    "low_angle": "low angle tracking shot",
    "crane": "slow crane shot from ground to eye level",
    "handheld": "slight handheld movement for natural feel",
}


# ============================================================
# 배경/세팅 프리셋
# ============================================================
VIDEO_SETTINGS = {
    "urban_street": "urban city street with modern buildings",
    "studio_white": "clean white studio with professional lighting",
    "studio_dark": "dark moody studio with dramatic spotlight",
    "outdoor_park": "lush green park with natural sunlight",
    "rooftop": "rooftop with city skyline in background",
    "cafe": "trendy modern cafe interior",
    "beach": "sandy beach with ocean waves",
    "neon_alley": "neon-lit alley at night with colorful reflections",
    "minimal_concrete": "minimal concrete space with indirect lighting",
}


# ============================================================
# 기본 네거티브 프롬프트
# ============================================================
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, distorted face, deformed hands, extra fingers, "
    "unnatural movement, jittery, low quality, watermark, text overlay, "
    "morphing artifacts, flickering, temporal inconsistency"
)


def build_fashion_video_prompt(
    subject: str,
    action: str = "walking confidently",
    setting: str = "urban street",
    mood: str = "cinematic editorial",
    camera: str = "smooth tracking shot",
    brand: Optional[str] = None,
    extra: Optional[str] = None,
) -> str:
    """
    패션 비디오 프롬프트 조립

    Args:
        subject: 착장 설명 (e.g., "MLB white tank top with NY logo")
        action: 모델 동작 (프리셋 키 또는 직접 입력)
        setting: 배경/장소 (프리셋 키 또는 직접 입력)
        mood: 분위기/스타일
        camera: 카메라 무브먼트 (프리셋 키 또는 직접 입력)
        brand: 브랜드명 (선택)
        extra: 추가 지시사항 (선택)

    Returns:
        str: 조립된 프롬프트
    """
    # 프리셋 키면 값으로 변환
    action_desc = FASHION_VIDEO_ACTIONS.get(action, action)
    setting_desc = VIDEO_SETTINGS.get(setting, setting)
    camera_desc = CAMERA_MOVEMENTS.get(camera, camera)

    parts = [
        f"Professional fashion video, {mood} style.",
        f"A model {action_desc} in {setting_desc}.",
        f"Wearing {subject}.",
        f"Camera: {camera_desc}.",
        "High-end production quality, natural lighting, 4K cinematic look.",
    ]

    if brand:
        parts.append(f"Brand aesthetic: {brand}.")
    if extra:
        parts.append(extra)

    return " ".join(parts)


def build_i2v_motion_prompt(
    action: str = "walk",
    camera: str = "static",
    extra: Optional[str] = None,
) -> str:
    """
    이미지-투-비디오(I2V) 모션 프롬프트 조립

    I2V는 이미지가 있으므로 모션/카메라만 지시.

    Args:
        action: 모델 동작 (프리셋 키 또는 직접 입력)
        camera: 카메라 무브먼트 (프리셋 키 또는 직접 입력)
        extra: 추가 지시사항 (선택)

    Returns:
        str: 모션 프롬프트
    """
    action_desc = FASHION_VIDEO_ACTIONS.get(action, action)
    camera_desc = CAMERA_MOVEMENTS.get(camera, camera)

    parts = [
        f"The person in the image starts {action_desc}.",
        f"Camera: {camera_desc}.",
        "Smooth natural movement, high quality.",
    ]

    if extra:
        parts.append(extra)

    return " ".join(parts)
