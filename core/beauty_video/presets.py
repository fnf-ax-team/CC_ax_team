"""
뷰티 영상 프리셋

카메라 무브먼트, 오디오 프롬프트, 네거티브 프롬프트 등
뷰티 인플루언서 릴스에 최적화된 프리셋 모음.
"""

from typing import Dict


# ============================================================
# 카메라 무브먼트 프리셋 (뷰티 전용)
# ============================================================
BEAUTY_CAMERA_MOVES: Dict[str, str] = {
    "selfie_zoom": (
        "very slight slow zoom in, beauty vlog selfie feel, "
        "natural handheld micro-movements"
    ),
    "product_pan": (
        "slow smooth downward pan across products, "
        "clean product photography feel, soft natural lighting"
    ),
    "mirror_static": (
        "very slight drift, almost static, "
        "warm cafe restroom lighting, natural mirror selfie feel"
    ),
    "handheld_beauty": (
        "subtle handheld sway, static with very slight movement, "
        "beauty tutorial feel"
    ),
    "slow_orbit": (
        "slow orbiting shot around product, " "gentle light shimmer on surfaces"
    ),
    "close_up_static": (
        "static close-up shot, very slight focus breathing, "
        "skin texture detail visible"
    ),
}


# ============================================================
# 오디오 프리셋 (V2A 프롬프트, 영어)
# ============================================================
BEAUTY_AUDIO_PROMPTS: Dict[str, Dict[str, str]] = {
    "hook": {
        "sfx": "excited gasp, cosmetic compact clicking open, subtle fabric rustling",
        "bgm": "trendy lo-fi bedroom pop, soft beat, warm synth pads",
    },
    "apply": {
        "sfx": "soft brush stroking on skin, powder puff dabbing, gentle tapping",
        "bgm": "gentle lo-fi background music, calm and focused vibe",
    },
    "proof": {
        "sfx": "cafe ambient sounds, soft chatter in distance, coffee machine hum",
        "bgm": "warm cafe jazz, acoustic guitar, relaxing afternoon vibe",
    },
    "cta": {
        "sfx": "product placement click, satisfying snap, subtle whoosh transition",
        "bgm": "upbeat trendy pop music, energetic and promotional feel",
    },
    "unboxing": {
        "sfx": "box opening, tissue paper rustling, product revealing",
        "bgm": "anticipation building music, gentle crescendo",
    },
    "swatch": {
        "sfx": "finger swiping on skin, cream spreading, gentle tap",
        "bgm": "soft ambient electronic, minimal and clean",
    },
    "before_after": {
        "sfx": "camera shutter click, transition whoosh",
        "bgm": "dramatic reveal music, building anticipation then resolution",
    },
    "routine": {
        "sfx": "morning alarm softly, water splashing, skincare pump dispenser",
        "bgm": "morning routine lo-fi, fresh and bright melody",
    },
}


# ============================================================
# 컷 타입 정의 (시나리오 구성용)
# ============================================================
BEAUTY_CUT_TYPES: Dict[str, Dict[str, str]] = {
    "hook": {
        "name": "Hook",
        "purpose": "첫 1초 주목도, 놀라움/궁금증 유발",
        "default_camera": "selfie_zoom",
        "default_audio": "hook",
    },
    "apply": {
        "name": "Application",
        "purpose": "제품 사용 과정 보여주기",
        "default_camera": "handheld_beauty",
        "default_audio": "apply",
    },
    "proof": {
        "name": "Proof",
        "purpose": "효과 증명, 시간 경과 후 지속력",
        "default_camera": "mirror_static",
        "default_audio": "proof",
    },
    "cta": {
        "name": "CTA",
        "purpose": "제품 라인업, 가격, 구매 유도",
        "default_camera": "product_pan",
        "default_audio": "cta",
    },
    "unboxing": {
        "name": "Unboxing",
        "purpose": "제품 언박싱, 첫인상",
        "default_camera": "close_up_static",
        "default_audio": "unboxing",
    },
    "swatch": {
        "name": "Swatch",
        "purpose": "발색, 텍스처 클로즈업",
        "default_camera": "close_up_static",
        "default_audio": "swatch",
    },
    "before_after": {
        "name": "Before/After",
        "purpose": "비포/애프터 비교",
        "default_camera": "selfie_zoom",
        "default_audio": "before_after",
    },
    "routine": {
        "name": "Routine",
        "purpose": "데일리 루틴, GRWM",
        "default_camera": "handheld_beauty",
        "default_audio": "routine",
    },
}


# ============================================================
# 네거티브 프롬프트 (뷰티 영상 공통)
# ============================================================
BEAUTY_NEGATIVE_PROMPT: str = (
    "blurry, distorted face, deformed hands, extra fingers, "
    "unnatural movement, jittery, low quality, watermark, text overlay, "
    "morphing artifacts, flickering, temporal inconsistency, "
    "face morphing, identity change, sudden jump cuts"
)
