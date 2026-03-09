"""
이커머스 포즈 및 배경 프리셋

SKILL.md 정의 기반 프리셋 상수 모음.
이커머스는 브랜드컷과 달리 중립적 배경(스튜디오/미니멀)을 사용한다.
"""

# 포즈 프리셋 - 이커머스 모델 촬영용 10종
POSE_PRESETS = {
    # === 기본 스탠딩 (5종) ===
    "front_standing": {
        "framing": "FS",  # Full Shot (전신)
        "angle": "front",
        "pose_desc": "natural standing, arms relaxed at sides, neutral expression, looking at camera",
        "lens": "50mm",
        "height": "eye level",
    },
    "front_casual": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "casual standing, one hand on waist, slight hip shift, confident expression",
        "lens": "50mm",
        "height": "eye level",
    },
    "side_profile": {
        "framing": "FS",
        "angle": "side",
        "pose_desc": "side profile, standing straight, head turned slightly toward camera",
        "lens": "50mm",
        "height": "eye level",
    },
    "back_view": {
        "framing": "FS",
        "angle": "back",
        "pose_desc": "back view, standing naturally, showing back details of clothing",
        "lens": "50mm",
        "height": "eye level",
    },
    "detail_closeup": {
        "framing": "MS",  # Medium Shot (미디엄샷)
        "angle": "front",
        "pose_desc": "upper body shot, torso and face visible, showcasing clothing details",
        "lens": "85mm",
        "height": "chest level",
    },
    # === 추가 포즈 (5종) ===
    "three_quarter": {
        "framing": "FS",
        "angle": "three-quarter",
        "pose_desc": "45-degree angle view, body slightly turned, one shoulder toward camera, natural stance",
        "lens": "50mm",
        "height": "eye level",
    },
    "walking": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "mid-stride walking pose, one foot forward, arms in natural swing, dynamic movement",
        "lens": "50mm",
        "height": "eye level",
    },
    "crossed_arms": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "standing with arms crossed over chest, confident stance, slight smile",
        "lens": "50mm",
        "height": "eye level",
    },
    "hands_in_pockets": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "relaxed standing, both hands in pockets, casual confident posture",
        "lens": "50mm",
        "height": "eye level",
    },
    "sitting_casual": {
        "framing": "FS",
        "angle": "front",
        "pose_desc": "sitting on stool or box, relaxed posture, legs slightly apart, hands on knees",
        "lens": "50mm",
        "height": "eye level",
    },
}

# 배경 프리셋 - 이커머스 전용 4종 (중립적 배경만 허용)
BACKGROUND_PRESETS = {
    "white_studio": {
        "location": "white studio backdrop",
        "lighting": "professional studio lighting, soft diffused light, even illumination",
        "ambient": "clean white background, seamless paper backdrop",
        "mood": "commercial, professional, product-focused",
    },
    "gray_studio": {
        "location": "gray studio backdrop",
        "lighting": "studio lighting, slightly dramatic, soft shadows",
        "ambient": "neutral gray background, modern studio setting",
        "mood": "sophisticated, editorial, high-end",
    },
    "minimal_indoor": {
        "location": "minimal indoor space",
        "lighting": "natural window light, soft diffused daylight",
        "ambient": "white walls, concrete floor, architectural minimalism",
        "mood": "lifestyle, modern, relatable",
    },
    "outdoor_urban": {
        "location": "urban outdoor setting",
        "lighting": "natural daylight, soft ambient outdoor light",
        "ambient": "city street, modern building facade, clean urban environment",
        "mood": "streetwear, casual, authentic",
    },
}

# 이커머스 유효 배경 목록 (브랜드컷처럼 브랜드 특화 배경 사용 불가)
VALID_ECOMMERCE_BACKGROUNDS = [
    "white_studio",
    "gray_studio",
    "minimal_indoor",
    "outdoor_urban",
]

__all__ = [
    "POSE_PRESETS",
    "BACKGROUND_PRESETS",
    "VALID_ECOMMERCE_BACKGROUNDS",
]
