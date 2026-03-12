"""
프롬프트 조립 및 검증 모듈

MLB 치트시트 JSON 스키마 기반으로 프롬프트를 조립하고,
금지 조합을 검증하여 자동 수정한다.

Functions:
    build_prompt: 분석 결과를 치트시트 JSON으로 조립
    validate_and_fix_combinations: 금지 조합 검증 및 자동 수정
    apply_concept_mapping: 컨셉별 표정/시선/입 자동 매핑
"""

from typing import Optional
import re
import random
from core.outfit_analyzer import OutfitAnalysis
from .korean_prompt_builder import enhance_with_korean_layer


# ============================================================
# 빈도 기반 랜덤 추출 (치트시트 빈도 데이터)
# ============================================================

# 표정 빈도 테이블 (치트시트 기준)
EXPRESSION_FREQUENCIES = {
    "베이스": {
        "cool": 50,
        "natural": 25,
        "neutral": 15,
        "serious": 10,
        # dreamy는 빈도 없음 = 0%
    },
    "바이브": {
        "mysterious": 40,
        "approachable": 25,
        "sophisticated": 35,
    },
    "시선": {
        "direct": 50,
        "past": 30,
        "side": 20,
    },
    "입": {
        "closed": 60,
        "parted": 30,
        "smile": 10,
    },
}


# ============================================================
# K-뷰티 표정 프리셋 (세분화된 표정 요소)
# ============================================================

KBEAUTY_EXPRESSION_PRESETS = {
    "chic_confident": {
        "preset": "chic_confident",
        "intensity": 75,
        "eyes": {
            "openness": "half_lidded",
            "eye_corner": "upturned",
            "gaze_intensity": "intense_piercing",
            "eye_smile": "none",
            "eyebrows": "natural_relaxed",
        },
        "mouth": {
            "lip_state": "slightly_parted",
            "mouth_corner": "neutral",
            "lip_emphasis": "glossy_plump",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "raised",
            "jaw_tension": "relaxed",
        },
        "mood_keywords": ["chic", "confident", "cool", "slightly seductive"],
        "prompt": "Chic confident expression: half-lidded eyes with upturned corners, intense piercing gaze at camera, no eye smile. Lips slightly parted, neutral corners, glossy plump. Chin slightly raised. Cool, confident, seductive mood.",
    },
    "chic_mysterious": {
        "preset": "chic_mysterious",
        "intensity": 70,
        "eyes": {
            "openness": "half_lidded",
            "eye_corner": "neutral",
            "gaze_intensity": "smoldering",
            "eye_smile": "none",
            "eyebrows": "slightly_raised",
        },
        "mouth": {
            "lip_state": "slightly_parted",
            "mouth_corner": "neutral",
            "lip_emphasis": "glossy_plump",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "neutral",
            "jaw_tension": "relaxed",
        },
        "mood_keywords": ["chic", "mysterious", "languid", "smoldering"],
        "prompt": "Chic mysterious expression: half-lidded eyes with smoldering languid gaze, eyebrows slightly raised. Lips slightly parted, glossy. Neutral chin. Mysterious, languid mood.",
    },
    "lovely_warm": {
        "preset": "lovely_warm",
        "intensity": 65,
        "eyes": {
            "openness": "natural",
            "eye_corner": "downturned",
            "gaze_intensity": "soft_gentle",
            "eye_smile": "slight",
            "eyebrows": "natural_relaxed",
        },
        "mouth": {
            "lip_state": "smiling_closed",
            "mouth_corner": "upturned",
            "lip_emphasis": "natural",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "neutral",
            "jaw_tension": "soft",
        },
        "mood_keywords": ["lovely", "warm", "approachable", "charming"],
        "prompt": "Lovely warm expression: natural eyes with soft gentle gaze, slight eye smile, downturned corners. Warm closed-mouth smile, upturned corners. Approachable, charming mood.",
    },
    "lovely_dreamy": {
        "preset": "lovely_dreamy",
        "intensity": 55,
        "eyes": {
            "openness": "slightly_closed",
            "eye_corner": "downturned",
            "gaze_intensity": "dreamy_unfocused",
            "eye_smile": "none",
            "eyebrows": "natural_relaxed",
        },
        "mouth": {
            "lip_state": "slightly_parted",
            "mouth_corner": "neutral",
            "lip_emphasis": "natural",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "lowered",
            "jaw_tension": "soft",
        },
        "mood_keywords": ["lovely", "dreamy", "ethereal", "soft"],
        "prompt": "Lovely dreamy expression: slightly closed eyes with dreamy unfocused gaze. Lips slightly parted, relaxed. Chin lowered. Ethereal, soft, dreamy mood.",
    },
    "innocent_pure": {
        "preset": "innocent_pure",
        "intensity": 60,
        "eyes": {
            "openness": "wide_open",
            "eye_corner": "downturned",
            "gaze_intensity": "innocent_clear",
            "eye_smile": "none",
            "eyebrows": "slightly_raised",
        },
        "mouth": {
            "lip_state": "closed_neutral",
            "mouth_corner": "neutral",
            "lip_emphasis": "natural",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "neutral",
            "jaw_tension": "soft",
        },
        "mood_keywords": ["innocent", "pure", "fresh", "youthful"],
        "prompt": "Innocent pure expression: wide open eyes with clear innocent gaze, doe-eyed look. Eyebrows slightly raised. Closed neutral lips. Fresh, pure, youthful mood.",
    },
    "haughty_cool": {
        "preset": "haughty_cool",
        "intensity": 70,
        "eyes": {
            "openness": "natural",
            "eye_corner": "upturned",
            "gaze_intensity": "cool_detached",
            "eye_smile": "none",
            "eyebrows": "arched",
        },
        "mouth": {
            "lip_state": "closed_tense",
            "mouth_corner": "downturned",
            "lip_emphasis": "matte_defined",
            "lip_tension": "slightly_tense",
        },
        "chin": {
            "chin_position": "raised",
            "jaw_tension": "defined",
        },
        "mood_keywords": ["haughty", "cool", "aloof", "unreachable"],
        "prompt": "Haughty cool expression: upturned eyes with cool detached gaze, arched eyebrows. Closed tense lips, slightly downturned corners. Chin raised, defined jaw. Aloof, unreachable mood.",
    },
    "natural_effortless": {
        "preset": "natural_effortless",
        "intensity": 40,
        "eyes": {
            "openness": "natural",
            "eye_corner": "neutral",
            "gaze_intensity": "soft_gentle",
            "eye_smile": "slight",
            "eyebrows": "natural_relaxed",
        },
        "mouth": {
            "lip_state": "closed_neutral",
            "mouth_corner": "neutral",
            "lip_emphasis": "natural",
            "lip_tension": "relaxed",
        },
        "chin": {
            "chin_position": "neutral",
            "jaw_tension": "relaxed",
        },
        "mood_keywords": ["natural", "effortless", "relaxed", "everyday"],
        "prompt": "Natural effortless expression: natural eyes with soft gaze, slight eye smile. Closed neutral lips, relaxed. Neutral chin. Relaxed, everyday mood.",
    },
    "fierce_intense": {
        "preset": "fierce_intense",
        "intensity": 90,
        "eyes": {
            "openness": "squinting",
            "eye_corner": "upturned",
            "gaze_intensity": "intense_piercing",
            "eye_smile": "none",
            "eyebrows": "furrowed",
        },
        "mouth": {
            "lip_state": "closed_tense",
            "mouth_corner": "downturned",
            "lip_emphasis": "matte_defined",
            "lip_tension": "tense",
        },
        "chin": {
            "chin_position": "raised",
            "jaw_tension": "defined",
        },
        "mood_keywords": ["fierce", "intense", "powerful", "commanding"],
        "prompt": "Fierce intense expression: squinting eyes with intense piercing gaze, upturned corners, furrowed brows. Closed tense lips, downturned. Chin raised, jaw defined. Powerful, commanding mood.",
    },
}


def get_expression_preset(preset_name: str) -> dict:
    """
    K-뷰티 표정 프리셋 반환.

    Args:
        preset_name: 프리셋 이름 (예: "chic_confident", "lovely_warm")

    Returns:
        프리셋 딕셔너리

    Raises:
        ValueError: 프리셋을 찾을 수 없는 경우
    """
    if preset_name not in KBEAUTY_EXPRESSION_PRESETS:
        raise ValueError(f"Expression preset not found: {preset_name}")

    return KBEAUTY_EXPRESSION_PRESETS[preset_name]


def get_all_expression_presets() -> list:
    """
    모든 K-뷰티 표정 프리셋 목록 반환.

    Returns:
        프리셋 이름 리스트
    """
    return list(KBEAUTY_EXPRESSION_PRESETS.keys())


def _weighted_random_choice(frequency_dict: dict) -> str:
    """
    빈도(가중치) 기반 랜덤 선택.

    Args:
        frequency_dict: {"옵션": 빈도, ...} 형태

    Returns:
        선택된 옵션 ID
    """
    options = list(frequency_dict.keys())
    weights = list(frequency_dict.values())
    return random.choices(options, weights=weights, k=1)[0]


def get_random_expression() -> dict:
    """
    빈도 기반으로 랜덤 표정 조합 생성.

    Returns:
        dict: {"베이스": "...", "바이브": "...", "시선": "...", "입": "..."}
    """
    result = {}
    for field, frequencies in EXPRESSION_FREQUENCIES.items():
        result[field] = _weighted_random_choice(frequencies)

    # 금지 조합 검증 및 수정
    # dreamy + direct → past로 수정
    if result["베이스"] == "dreamy" and result["시선"] == "direct":
        result["시선"] = "past"

    # serious/cool + smile → closed로 수정
    if result["베이스"] in ["serious", "cool"] and result["입"] == "smile":
        result["입"] = "closed"

    return result


# ============================================================
# Pose Preset Data (하드코딩 - 치트시트와 동기화)
# ============================================================

# 16개 검증된 포즈 프리셋 (147개 VLM 분석에서 추출)
# JSON 스키마 형식: stance, 왼팔, 오른팔, 왼손, 오른손, 왼다리, 오른다리, 힙
POSE_PRESETS = {
    "confident_standing_none_neutral": {
        "id": "confident_standing_none_neutral",
        "name_ko": "자신감스탠딩_중립",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 55% right 45%",
            "왼팔": "down, slightly bent at elbow",
            "오른팔": "down, slightly bent at elbow",
            "왼손": "relaxed",
            "오른손": "relaxed",
            "왼다리": "not visible",
            "오른다리": "not visible",
            "힙": "neutral",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: down, slightly bent at elbow, right arm: down, slightly bent at elbow, left leg: not visible, right leg: not visible",
    },
    "confident_standing_none_hand_on_hip": {
        "id": "confident_standing_none_hand_on_hip",
        "name_ko": "자신감스탠딩_허리손",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 55% right 45%",
            "왼팔": "bent at elbow, hand on hip",
            "오른팔": "holding bag strap",
            "왼손": "resting on hip, fingers spread",
            "오른손": "gripping bag strap",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: hand on hip, right arm: holding bag strap, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "confident_standing_none_arms_relaxed": {
        "id": "confident_standing_none_arms_relaxed",
        "name_ko": "자신감스탠딩_편안",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 55% right 45%",
            "왼팔": "relaxed at side, slightly bent",
            "오른팔": "relaxed at side, slightly bent",
            "왼손": "relaxed, fingers slightly curled",
            "오른손": "relaxed, fingers slightly curled",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "neutral",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: relaxed at side, slightly bent, right arm: relaxed at side, slightly bent, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "confident_standing_none_hand_in_pocket": {
        "id": "confident_standing_none_hand_in_pocket",
        "name_ko": "자신감스탠딩_주머니손",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 50% right 50%",
            "왼팔": "bent at elbow, hand in pocket",
            "오른팔": "bent at elbow, hand in pocket",
            "왼손": "in pocket",
            "오른손": "in pocket",
            "왼다리": "straight support leg",
            "오른다리": "straight support leg",
            "힙": "neutral",
        },
        "full_prompt": "confident standing, weight: left 50%, right 50%, left arm: hand in pocket, right arm: hand in pocket, left leg: straight support leg, right leg: straight support leg",
    },
    "confident_standing_none_holding_bag": {
        "id": "confident_standing_none_holding_bag",
        "name_ko": "자신감스탠딩_가방들기",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 55% right 45%",
            "왼팔": "holding bag strap, elbow bent 90 degrees",
            "오른팔": "bent at elbow, hand in pocket",
            "왼손": "gripping bag strap",
            "오른손": "in pocket",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: holding bag strap, elbow bent 90°, right arm: hand in pocket, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "confident_standing_none_hand_on_chin": {
        "id": "confident_standing_none_hand_on_chin",
        "name_ko": "자신감스탠딩_턱괴기",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 4,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 60% right 40%",
            "왼팔": "across chest, hand touching right shoulder",
            "오른팔": "holding bag strap, arm slightly bent",
            "왼손": "touching right shoulder, fingers relaxed",
            "오른손": "gripping bag strap",
            "왼다리": "slightly bent at knee 5 degrees",
            "오른다리": "slightly bent at knee 10 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "confident standing, weight: left 60%, right 40%, left arm: across chest, hand touching right shoulder, right arm: holding bag strap, arm slightly bent, left leg: slightly bent at knee 5°, right leg: slightly bent at knee 10°",
    },
    "confident_standing_none_hand_on_hat": {
        "id": "confident_standing_none_hand_on_hat",
        "name_ko": "자신감스탠딩_모자터치",
        "category": "confident_standing",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["메탈패널", "창고", "콘크리트", "도심"],
        "pose": {
            "stance": "confident standing, weight left 55% right 45%",
            "왼팔": "raised, hand touching hat brim",
            "오른팔": "hanging loosely at side, jacket draped over shoulder",
            "왼손": "touching hat brim, fingers spread",
            "오른손": "relaxed, holding jacket",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: hand touching hat brim, right arm: hanging loosely at side, jacket draped over shoulder, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "confident_standing_car_neutral": {
        "id": "confident_standing_car_neutral",
        "name_ko": "자신감스탠딩_차량_중립",
        "category": "confident_standing",
        "has_vehicle": True,
        "energy_level": 3,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "confident standing near car, weight left 55% right 45%",
            "왼팔": "extended, resting on car",
            "오른팔": "extended, slightly bent",
            "왼손": "resting on car surface, fingers relaxed",
            "오른손": "relaxed",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "neutral",
        },
        "full_prompt": "confident standing, weight: left 55%, right 45%, left arm: extended, resting on car, right arm: extended, slightly bent, hand relaxed, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "relaxed_lean_car_neutral": {
        "id": "relaxed_lean_car_neutral",
        "name_ko": "편안한기대기_차량_중립",
        "category": "relaxed_lean",
        "has_vehicle": True,
        "energy_level": 3,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "relaxed lean against car, weight left 30% right 70%",
            "왼팔": "resting on car hood, slightly bent",
            "오른팔": "resting on right thigh, slightly bent",
            "왼손": "resting on car hood, fingers relaxed",
            "오른손": "resting on thigh, fingers relaxed",
            "왼다리": "bent at knee 45 degrees, foot on ground",
            "오른다리": "bent at knee 30 degrees, resting on car tire",
            "힙": "leaning right",
        },
        "full_prompt": "relaxed lean, weight: left 30%, right 70%, left arm: resting on car hood, slightly bent, right arm: resting on right thigh, slightly bent, left leg: bent at knee 45°, foot on ground, right leg: bent at knee 30°, resting on car tire",
    },
    "relaxed_lean_car_hand_on_hip": {
        "id": "relaxed_lean_car_hand_on_hip",
        "name_ko": "편안한기대기_차량_허리손",
        "category": "relaxed_lean",
        "has_vehicle": True,
        "energy_level": 3,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "relaxed lean against car, weight left 60% right 40%",
            "왼팔": "straight, hand on hip",
            "오른팔": "bent, leaning on car",
            "왼손": "resting on hip, fingers spread",
            "오른손": "resting on car, fingers relaxed",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "relaxed lean, weight: left 60%, right 40%, left arm: straight, hand on hip, right arm: bent, leaning on car, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "relaxed_lean_car_hand_in_pocket": {
        "id": "relaxed_lean_car_hand_in_pocket",
        "name_ko": "편안한기대기_차량_주머니손",
        "category": "relaxed_lean",
        "has_vehicle": True,
        "energy_level": 3,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "relaxed lean against car, weight left 60% right 40%",
            "왼팔": "bent at elbow, hand in pocket",
            "오른팔": "resting on car",
            "왼손": "in pocket",
            "오른손": "resting on car, fingers relaxed",
            "왼다리": "straight support leg",
            "오른다리": "slightly bent at knee 5 degrees",
            "힙": "pop_left",
        },
        "full_prompt": "relaxed lean, weight: left 60%, right 40%, left arm: hand in pocket, right arm: resting on car, left leg: straight support leg, right leg: slightly bent at knee 5°",
    },
    "relaxed_lean_none_neutral": {
        "id": "relaxed_lean_none_neutral",
        "name_ko": "편안한기대기_중립",
        "category": "relaxed_lean",
        "has_vehicle": False,
        "energy_level": 3,
        "compatible_backgrounds": ["콘크리트", "창고", "메탈패널"],
        "pose": {
            "stance": "relaxed lean against wall or pole, weight left 60% right 40%",
            "왼팔": "extended, hand on pole",
            "오른팔": "holding bag, slightly bent",
            "왼손": "gripping pole",
            "오른손": "holding bag handle",
            "왼다리": "straight support leg",
            "오른다리": "bent at knee 20 degrees, foot slightly raised",
            "힙": "pop_left",
        },
        "full_prompt": "relaxed lean, weight: left 60%, right 40%, left arm: extended, hand on pole, right arm: holding bag, slightly bent, left leg: straight support leg, right leg: bent at knee 20°, foot slightly raised",
    },
    "seated_none_neutral": {
        "id": "seated_none_neutral",
        "name_ko": "앉기_중립",
        "category": "seated",
        "has_vehicle": False,
        "energy_level": 1,
        "compatible_backgrounds": ["창고", "콘크리트", "스튜디오"],
        "pose": {
            "stance": "seated on elevated surface, weight left 50% right 50%",
            "왼팔": "resting on chair arm",
            "오른팔": "resting on lap",
            "왼손": "resting on armrest, fingers relaxed",
            "오른손": "resting on lap, fingers relaxed",
            "왼다리": "slightly bent at knee 10 degrees",
            "오른다리": "slightly bent at knee 10 degrees",
            "힙": "neutral",
        },
        "full_prompt": "seated, weight: left 50%, right 50%, left arm: resting on chair arm, right arm: resting on lap, left leg: slightly bent at knee 10°, right leg: slightly bent at knee 10°",
    },
    "seated_none_hand_on_chin": {
        "id": "seated_none_hand_on_chin",
        "name_ko": "앉기_턱괴기",
        "category": "seated",
        "has_vehicle": False,
        "energy_level": 2,
        "compatible_backgrounds": ["창고", "콘크리트", "스튜디오"],
        "pose": {
            "stance": "seated contemplative, weight left 60% right 40%",
            "왼팔": "elbow resting on left knee",
            "오른팔": "bent at elbow, hand resting on right thigh",
            "왼손": "supporting chin, fingers relaxed",
            "오른손": "resting on thigh, fingers relaxed",
            "왼다리": "bent at knee 90 degrees, foot flat on ground",
            "오른다리": "bent at knee 120 degrees, foot resting on toes",
            "힙": "leaning left",
        },
        "full_prompt": "seated, weight: left 60%, right 40%, left arm: elbow resting on left knee, hand supporting chin, right arm: bent at elbow, hand resting on right thigh, left leg: bent at knee 90°, foot flat on ground, right leg: bent at knee 120°, foot resting on toes",
    },
    "seated_car_neutral": {
        "id": "seated_car_neutral",
        "name_ko": "앉기_차량_중립",
        "category": "seated",
        "has_vehicle": True,
        "energy_level": 2,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "seated on car hood or trunk, weight left 60% right 40%",
            "왼팔": "resting on bent left leg",
            "오른팔": "resting on ground, slightly bent",
            "왼손": "resting on knee, fingers relaxed",
            "오른손": "resting on car surface, fingers spread",
            "왼다리": "bent at knee 70 degrees, foot flat on ground",
            "오른다리": "extended, slightly bent at knee 10 degrees",
            "힙": "leaning left",
        },
        "full_prompt": "seated, weight: left 60%, right 40%, left arm: resting on bent left leg, right arm: resting on ground, slightly bent, left leg: bent at knee 70°, foot flat on ground, right leg: extended, slightly bent at knee 10°",
    },
    "static_car_neutral": {
        "id": "static_car_neutral",
        "name_ko": "정적서기_차량_중립",
        "category": "static",
        "has_vehicle": True,
        "energy_level": 1,
        "compatible_backgrounds": ["럭셔리SUV", "빈티지카", "지하주차장"],
        "pose": {
            "stance": "static standing near car, weight left 50% right 50%",
            "왼팔": "hanging naturally",
            "오른팔": "hanging naturally",
            "왼손": "relaxed",
            "오른손": "relaxed",
            "왼다리": "not visible",
            "오른다리": "not visible",
            "힙": "neutral",
        },
        "full_prompt": "static, weight: left 50%, right 50%, left arm: hanging naturally, right arm: hanging naturally, left leg: not visible, right leg: not visible",
    },
}


# ============================================================
# Pose Preset Functions
# ============================================================


def load_pose_presets(brand_id: str = "mlb") -> dict:
    """
    포즈 프리셋 반환 (하드코딩).

    Args:
        brand_id: 브랜드 ID (현재 "mlb"만 지원)

    Returns:
        프리셋 데이터 dict
    """
    return {
        "version": "1.0.0",
        "brand_id": brand_id,
        "total_presets": len(POSE_PRESETS),
        "presets": list(POSE_PRESETS.values()),
    }


def get_pose_preset(preset_id: str) -> dict:
    """
    프리셋 ID로 포즈 데이터 반환.

    Args:
        preset_id: 프리셋 ID (예: "confident_standing_none_hand_on_hip")

    Returns:
        프리셋 데이터 dict

    Raises:
        ValueError: 프리셋을 찾을 수 없는 경우
    """
    if preset_id not in POSE_PRESETS:
        raise ValueError(f"Pose preset not found: {preset_id}")

    return POSE_PRESETS[preset_id]


def get_pose_prompt(preset_id: str) -> str:
    """
    프리셋 ID로 full_prompt 반환.

    Args:
        preset_id: 프리셋 ID

    Returns:
        프롬프트 문자열

    Raises:
        ValueError: 프리셋을 찾을 수 없는 경우
    """
    preset = get_pose_preset(preset_id)
    return preset.get("full_prompt", "")


def is_preset_compatible_with_background(preset_id: str, background: str) -> bool:
    """
    프리셋-배경 호환성 검사.

    Args:
        preset_id: 프리셋 ID
        background: 배경 ID

    Returns:
        호환 여부
    """
    try:
        preset = get_pose_preset(preset_id)
        compatible = preset.get("compatible_backgrounds", [])
        return background in compatible
    except ValueError:
        return False


def get_all_preset_ids() -> list:
    """
    모든 프리셋 ID 목록 반환.

    Returns:
        프리셋 ID 리스트
    """
    return list(POSE_PRESETS.keys())


def get_presets_by_category(category: str) -> list:
    """
    카테고리별 프리셋 목록 반환.

    Args:
        category: 카테고리 (confident_standing, relaxed_lean, seated, static)

    Returns:
        해당 카테고리 프리셋 리스트
    """
    return [p for p in POSE_PRESETS.values() if p.get("category") == category]


def get_vehicle_presets() -> list:
    """
    차량 프리셋 목록 반환.

    Returns:
        has_vehicle=True인 프리셋 리스트
    """
    return [p for p in POSE_PRESETS.values() if p.get("has_vehicle")]


def get_non_vehicle_presets() -> list:
    """
    비차량 프리셋 목록 반환.

    Returns:
        has_vehicle=False인 프리셋 리스트
    """
    return [p for p in POSE_PRESETS.values() if not p.get("has_vehicle")]


# ============================================================
# Helper Functions
# ============================================================


def _format_critical_detail(detail: str) -> str:
    """
    디테일을 MUST/NEVER 형식으로 변환하여 이미지 생성 모델이 무시하지 못하게 강조

    Examples:
        "NO BRIM skull cap style" → "[MUST: NO BRIM skull cap style] [NEVER: add brim or visor]"
        "front_right logo position" → "[MUST: logo at front_right] [NEVER: center or left placement]"
        "fuzzy hairy texture" → "[MUST: visible fuzzy hairy texture]"
    """
    detail_upper = detail.upper()

    # NO / 없음 패턴 감지 → NEVER 추가
    if "NO " in detail_upper or "NO-" in detail_upper or "없" in detail:
        # "NO BRIM" → NEVER: add brim
        negation_match = re.search(r"NO[- ]?(\w+)", detail, re.IGNORECASE)
        if negation_match:
            negated_item = negation_match.group(1).lower()
            return f"[MUST: {detail}] [NEVER: add {negated_item} or similar]"
        return f"[MUST: {detail}] [NEVER: add the opposite]"

    # front_right, front_left 등 위치 패턴 감지
    if "front_right" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or left placement]"
    if "front_left" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or right placement]"
    if "front_center" in detail.lower():
        return f"[MUST: {detail}] [NEVER: off-center placement]"

    # 질감 키워드 감지 → 강조
    texture_keywords = [
        "fuzzy",
        "hairy",
        "mohair",
        "velvet",
        "satin",
        "matte",
        "glossy",
    ]
    if any(kw in detail.lower() for kw in texture_keywords):
        return f"[MUST: visible {detail}]"

    # 기타 디테일 → MUST만 추가
    return f"[MUST: {detail}]"


def _format_logo_detail(logo) -> str:
    """
    로고 정보를 MUST/NEVER 형식으로 변환

    Args:
        logo: LogoInfo object with brand, position, type

    Returns:
        Strongly formatted logo requirement string
    """
    brand = logo.brand
    position = logo.position
    logo_type = logo.type

    # 위치별 NEVER 설정
    position_never = {
        "front_right": "center or left",
        "front_left": "center or right",
        "front_center": "off-center",
        "left_chest": "center or right chest",
        "back_center": "front",
    }

    never_part = position_never.get(position, "wrong position")

    return (
        f"[MUST: {brand} logo at {position} ({logo_type})] "
        f"[NEVER: {never_part} placement]"
    )


def _build_camera_section(pose_analysis: Optional[dict], user_options: dict) -> dict:
    """
    촬영 섹션 빌드 - pose_analysis["camera"]에서 추출

    pose_analysis 구조:
    {
        "camera": {
            "camera_height": "low angle (shooting from below)",
            "framing": "FS (full shot, head to toe)",
            "gaze_direction": "directly at camera",
            "camera_distance": "medium"
        }
    }
    """
    camera = pose_analysis.get("camera", {}) if pose_analysis else {}

    # 앵글 매핑: low angle → 로우앵글, eye level → 눈높이, high angle → 하이앵글
    height_raw = camera.get("camera_height", "")
    if "low" in height_raw.lower():
        height = "로우앵글"
    elif "high" in height_raw.lower():
        height = "하이앵글"
    else:
        height = "눈높이"

    # 프레이밍 매핑: FS → FS, MFS → MFS, MS → MS, MCU → MCU, CU → CU
    framing_raw = camera.get("framing", "")
    if "full" in framing_raw.lower() or "FS" in framing_raw:
        framing = "FS"
    elif "knee" in framing_raw.lower() or "MFS" in framing_raw:
        framing = "MFS"
    elif "waist" in framing_raw.lower() or "MS" in framing_raw:
        framing = "MS"
    elif "close" in framing_raw.lower() or "CU" in framing_raw:
        framing = "CU"
    else:
        framing = user_options.get("촬영.프레이밍", "MS")

    return {
        "프레이밍": framing,
        "렌즈": user_options.get("촬영.렌즈", "50mm"),
        "앵글": user_options.get("촬영.앵글", "3/4측면"),
        "높이": height,
        "구도": user_options.get("촬영.구도", "중앙"),
        "조리개": "f/2.8",
    }


def _build_pose_section(pose_analysis: Optional[dict], user_options: dict) -> dict:
    """
    포즈 섹션 빌드. 프리셋 모드와 커스텀 모드 지원.

    Args:
        pose_analysis: 포즈 데이터 (선택)
            - preset_id가 있으면 프리셋 모드
            - custom_mode=True면 커스텀 모드
            - 둘 다 없으면 기존 방식 (하위 호환)
        user_options: 사용자 옵션

    Returns:
        dict: 포즈 섹션 데이터

    프리셋 모드 반환 형식:
    {
        "stance": "confident_standing",
        "full_prompt": "...",
        "preset_used": "confident_standing_none_hand_on_hip",
        "has_vehicle": False,
        "context_prop": None,
        "energy_level": 3
    }

    기존 방식 반환 형식:
    {
        "stance": "...",
        "왼팔": "...",
        "오른팔": "...",
        ...
    }
    """
    pose = pose_analysis if pose_analysis else {}

    # 1. 프리셋 모드 체크
    preset_id = pose.get("preset_id") or user_options.get("포즈.preset_id")
    if preset_id:
        try:
            preset = get_pose_preset(preset_id)
            return {
                "stance": preset.get("category", "confident_standing"),
                "full_prompt": preset.get("full_prompt", ""),
                "preset_used": preset_id,
                "has_vehicle": preset.get("has_vehicle", False),
                "context_prop": preset.get("context_prop"),
                "energy_level": preset.get("energy_level", 3),
            }
        except ValueError as e:
            # 프리셋을 찾을 수 없으면 기존 방식으로 폴백
            print(f"⚠️  Preset not found: {preset_id}, falling back to default pose")

    # 2. 커스텀 모드 체크
    if pose.get("custom_mode") and pose.get("custom"):
        pose = pose["custom"]

    # 3. 기존 방식 (하위 호환)
    pose_data = pose.get("pose", {}) if "pose" in pose else pose

    # MLB DNA 기본값 (레퍼런스 없을 때 적용)
    # - 파워포즈: 공간 지배, 다리 벌림, 당당함, 자신감
    MLB_POSE_DEFAULTS = {
        "stance": "power stance, standing tall with confident posture, weight on one leg",
        "왼팔": "hand on hip, elbow pointing outward, assertive",
        "오른팔": "relaxed at side, natural hang",
        "왼손": "resting on hip, fingers spread confidently",
        "오른손": "relaxed, natural position",
        "왼다리": "straight, supporting weight, firmly planted",
        "오른다리": "relaxed, spread apart for wide power stance",
        "힙": "weight shifted to one side, S-curve silhouette",
    }

    return {
        "stance": pose_data.get(
            "stance", user_options.get("포즈.stance", MLB_POSE_DEFAULTS["stance"])
        ),
        "왼팔": pose_data.get(
            "left_arm", user_options.get("포즈.왼팔", MLB_POSE_DEFAULTS["왼팔"])
        ),
        "오른팔": pose_data.get(
            "right_arm", user_options.get("포즈.오른팔", MLB_POSE_DEFAULTS["오른팔"])
        ),
        "왼손": pose_data.get(
            "left_hand", user_options.get("포즈.왼손", MLB_POSE_DEFAULTS["왼손"])
        ),
        "오른손": pose_data.get(
            "right_hand", user_options.get("포즈.오른손", MLB_POSE_DEFAULTS["오른손"])
        ),
        "왼다리": pose_data.get(
            "left_leg", user_options.get("포즈.왼다리", MLB_POSE_DEFAULTS["왼다리"])
        ),
        "오른다리": pose_data.get(
            "right_leg",
            user_options.get("포즈.오른다리", MLB_POSE_DEFAULTS["오른다리"]),
        ),
        "힙": pose_data.get(
            "hip", user_options.get("포즈.힙", MLB_POSE_DEFAULTS["힙"])
        ),
    }


def _build_expression_section(
    pose_analysis: Optional[dict], user_options: dict
) -> dict:
    """
    표정 섹션 빌드 - pose_analysis["expression"]에서 추출

    ★ K-뷰티 세분화 표정 지원 ★

    pose_analysis 신규 구조 (세분화된 표정):
    {
        "expression": {
            "preset": "chic_confident",
            "intensity": 75,
            "eyes": {
                "openness": "half_lidded",
                "eye_corner": "upturned",
                "gaze_intensity": "intense_piercing",
                "eye_smile": "none",
                "eyebrows": "natural_relaxed"
            },
            "mouth": {
                "lip_state": "slightly_parted",
                "mouth_corner": "neutral",
                "lip_emphasis": "glossy_plump",
                "lip_tension": "relaxed"
            },
            "chin": {
                "chin_position": "raised",
                "jaw_tension": "relaxed"
            },
            "mood_keywords": ["chic", "confident", "cool"]
        }
    }

    기존 구조 (하위 호환):
    {
        "expression": {
            "eyes": "large, wide open, confident gaze",
            "eyebrows": "natural, slightly raised",
            "mouth": "closed, neutral, slight pout",
            "mood": "cool, confident, chic"
        }
    }

    레퍼런스 없을 때: 빈도 기반 랜덤 추출 또는 프리셋 사용
    """
    expression = pose_analysis.get("expression", {}) if pose_analysis else {}

    # ============================================================
    # 1. 사용자가 프리셋을 직접 지정한 경우
    # ============================================================
    user_preset = user_options.get("표정.프리셋") or user_options.get("표정.preset")
    if user_preset and user_preset in KBEAUTY_EXPRESSION_PRESETS:
        preset = KBEAUTY_EXPRESSION_PRESETS[user_preset]
        return _build_expression_from_preset(preset, user_options)

    # ============================================================
    # 2. VLM 분석 결과에 세분화된 표정 데이터가 있는 경우
    # ============================================================
    if expression and isinstance(expression.get("eyes"), dict):
        # 신규 세분화 구조 감지
        return _build_expression_from_detailed(expression, user_options)

    # ============================================================
    # 3. 레퍼런스 없거나 기존 구조인 경우
    # ============================================================
    if not expression:
        # 사용자가 직접 지정한 옵션이 있으면 사용, 없으면 랜덤
        random_expr = get_random_expression()

        return {
            "베이스": user_options.get("표정.베이스", random_expr["베이스"]),
            "바이브": user_options.get("표정.바이브", random_expr["바이브"]),
            "시선": user_options.get("표정.시선", random_expr["시선"]),
            "입": user_options.get("표정.입", random_expr["입"]),
            "눈": user_options.get("표정.눈", "wide_open"),
            "눈썹": user_options.get("표정.눈썹", "natural_arched"),
            # 세분화 필드 기본값
            "세분화": None,
            "프롬프트": None,
        }

    # ============================================================
    # 4. 기존 구조 (하위 호환) - 텍스트 기반 분석 결과
    # ============================================================
    mood_raw = expression.get("mood", "")
    if "fierce" in mood_raw.lower() or "intense" in mood_raw.lower():
        base = "fierce"
    elif "cool" in mood_raw.lower() or "confident" in mood_raw.lower():
        base = "cool"
    elif "dreamy" in mood_raw.lower():
        base = "dreamy"
    elif "natural" in mood_raw.lower():
        base = "natural"
    elif "serious" in mood_raw.lower():
        base = "serious"
    else:
        base = "cool"  # 분석 결과 매칭 안되면 cool

    # 입 상태 추출
    mouth_raw = expression.get("mouth", "")
    if "open" in mouth_raw.lower() or "parted" in mouth_raw.lower():
        mouth = "parted"
    elif "smile" in mouth_raw.lower():
        mouth = "smile"
    else:
        mouth = "closed"

    # 시선 추출
    eyes_raw = expression.get("eyes", "")
    if "intense" in eyes_raw.lower():
        gaze = "direct"
    elif "direct" in eyes_raw.lower() or "camera" in eyes_raw.lower():
        gaze = "direct"
    elif "past" in eyes_raw.lower() or "away" in eyes_raw.lower():
        gaze = "past"
    elif "side" in eyes_raw.lower():
        gaze = "side"
    else:
        gaze = "direct"

    return {
        "베이스": base,
        "바이브": expression.get("mood", "mysterious"),
        "시선": gaze,
        "입": mouth,
        "눈": expression.get("eyes", "wide_open"),
        "눈썹": expression.get("eyebrows", "natural_arched"),
        # 세분화 필드 (기존 구조에서는 None)
        "세분화": None,
        "프롬프트": None,
    }


def _build_expression_from_preset(preset: dict, user_options: dict) -> dict:
    """
    K-뷰티 프리셋에서 표정 섹션 빌드.

    Args:
        preset: KBEAUTY_EXPRESSION_PRESETS에서 가져온 프리셋
        user_options: 사용자 옵션 (일부 override 가능)

    Returns:
        표정 섹션 딕셔너리
    """
    # 프리셋에서 베이스/바이브 추론
    preset_name = preset.get("preset", "natural_effortless")
    mood_keywords = preset.get("mood_keywords", [])

    # 프리셋 이름에서 베이스 추출
    if "chic" in preset_name:
        base = "cool"
    elif "lovely" in preset_name:
        base = "natural"
    elif "innocent" in preset_name:
        base = "natural"
    elif "haughty" in preset_name:
        base = "serious"
    elif "fierce" in preset_name:
        base = "fierce"
    else:
        base = "natural"

    # 바이브 추출
    if "mysterious" in mood_keywords:
        vibe = "mysterious"
    elif "warm" in mood_keywords or "approachable" in mood_keywords:
        vibe = "approachable"
    elif "cool" in mood_keywords or "aloof" in mood_keywords:
        vibe = "sophisticated"
    else:
        vibe = "sophisticated"

    # 눈/입/시선 추출
    eyes_data = preset.get("eyes", {})
    mouth_data = preset.get("mouth", {})

    # 시선 (gaze_intensity → 시선 매핑)
    gaze_intensity = eyes_data.get("gaze_intensity", "")
    if "direct" in gaze_intensity or "piercing" in gaze_intensity:
        gaze = "direct"
    elif "unfocused" in gaze_intensity or "dreamy" in gaze_intensity:
        gaze = "past"
    elif "detached" in gaze_intensity:
        gaze = "side"
    else:
        gaze = "direct"

    # 입 (lip_state → 입 매핑)
    lip_state = mouth_data.get("lip_state", "")
    if "parted" in lip_state:
        mouth = "parted"
    elif "smile" in lip_state:
        mouth = "smile"
    else:
        mouth = "closed"

    return {
        "베이스": user_options.get("표정.베이스", base),
        "바이브": user_options.get("표정.바이브", vibe),
        "시선": user_options.get("표정.시선", gaze),
        "입": user_options.get("표정.입", mouth),
        "눈": eyes_data.get("openness", "natural"),
        "눈썹": eyes_data.get("eyebrows", "natural_relaxed"),
        # ★ 세분화 표정 데이터 (generator에서 활용)
        "프리셋": preset_name,
        "강도": preset.get("intensity", 60),
        "세분화": {
            "eyes": eyes_data,
            "mouth": mouth_data,
            "chin": preset.get("chin", {}),
        },
        "키워드": mood_keywords,
        "프롬프트": preset.get("prompt", ""),
    }


def _build_expression_from_detailed(expression: dict, user_options: dict) -> dict:
    """
    VLM 세분화 분석 결과에서 표정 섹션 빌드.

    Args:
        expression: VLM 분석 결과 (세분화 구조)
        user_options: 사용자 옵션

    Returns:
        표정 섹션 딕셔너리
    """
    preset_name = expression.get("preset", "natural_effortless")
    mood_keywords = expression.get("mood_keywords", [])
    eyes_data = expression.get("eyes", {})
    mouth_data = expression.get("mouth", {})
    chin_data = expression.get("chin", {})

    # 프리셋 이름에서 베이스 추출
    if "chic" in preset_name:
        base = "cool"
    elif "lovely" in preset_name:
        base = "natural"
    elif "innocent" in preset_name:
        base = "natural"
    elif "haughty" in preset_name:
        base = "serious"
    elif "fierce" in preset_name:
        base = "fierce"
    else:
        base = "natural"

    # 바이브 추출
    if any(kw in mood_keywords for kw in ["mysterious", "languid"]):
        vibe = "mysterious"
    elif any(kw in mood_keywords for kw in ["warm", "approachable", "charming"]):
        vibe = "approachable"
    else:
        vibe = "sophisticated"

    # 시선 매핑
    gaze_intensity = eyes_data.get("gaze_intensity", "")
    if "direct" in gaze_intensity or "piercing" in gaze_intensity:
        gaze = "direct"
    elif "unfocused" in gaze_intensity or "dreamy" in gaze_intensity:
        gaze = "past"
    else:
        gaze = "direct"

    # 입 매핑
    lip_state = mouth_data.get("lip_state", "")
    if "parted" in lip_state:
        mouth = "parted"
    elif "smile" in lip_state:
        mouth = "smile"
    else:
        mouth = "closed"

    return {
        "베이스": user_options.get("표정.베이스", base),
        "바이브": user_options.get("표정.바이브", vibe),
        "시선": user_options.get("표정.시선", gaze),
        "입": user_options.get("표정.입", mouth),
        "눈": eyes_data.get("openness", "natural"),
        "눈썹": eyes_data.get("eyebrows", "natural_relaxed"),
        # ★ 세분화 표정 데이터
        "프리셋": preset_name,
        "강도": expression.get("intensity", 60),
        "세분화": {
            "eyes": eyes_data,
            "mouth": mouth_data,
            "chin": chin_data,
        },
        "키워드": mood_keywords,
        "프롬프트": expression.get("expression_prompt", ""),
    }


# 금지 조합 테이블 (mlb-prompt-cheatsheet.md 484-498줄 기반)
FORBIDDEN_COMBINATIONS = [
    {
        "rule": "85mm + MFS",
        "reason": "과도한 배경 압축",
        "fix": {"촬영.렌즈": "50mm"},
        "condition": lambda p: p.get("촬영", {}).get("렌즈") == "85mm"
        and p.get("촬영", {}).get("프레이밍") == "MFS",
    },
    {
        "rule": "35mm + CU",
        "reason": "광각 왜곡으로 얼굴 변형",
        "fix": {"촬영.렌즈": "85mm"},
        "condition": lambda p: p.get("촬영", {}).get("렌즈") == "35mm"
        and p.get("촬영", {}).get("프레이밍") == "CU",
    },
    {
        "rule": "cool + smile",
        "reason": "쿨한데 미소는 모순",
        "fix": {"표정.입": "closed"},
        "condition": lambda p: p.get("표정", {}).get("베이스") == "cool"
        and p.get("표정", {}).get("입") == "smile",
    },
    {
        "rule": "serious + smile",
        "reason": "컨셉 충돌",
        "fix": {"표정.입": "closed"},
        "condition": lambda p: p.get("표정", {}).get("베이스") == "serious"
        and p.get("표정", {}).get("입") == "smile",
    },
    {
        "rule": "dreamy + direct",
        "reason": "컨셉 충돌",
        "fix": {"표정.시선": "past"},
        "condition": lambda p: p.get("표정", {}).get("베이스") == "dreamy"
        and p.get("표정", {}).get("시선") == "direct",
    },
]


# 코디방법 기본값 (mlb-prompt-cheatsheet.md 기본값 섹션 기반)
STYLING_DEFAULTS = {
    "아우터": {"id": "정상착용", "prompt": "worn normally"},
    "상의": {"id": "한쪽어깨노출", "prompt": "off-shoulder on one side"},
    "하의": {"id": "정상착용", "prompt": "worn normally"},
    "신발": {"id": "정상착용", "prompt": "worn normally"},
    "헤드웨어": {"id": "정상착용", "prompt": "worn normally"},
    "주얼리": {"id": "정상착용", "prompt": "worn normally"},
    "가방": {"id": "정상착용", "prompt": "worn normally"},
    "벨트": {"id": "장식용", "prompt": "decorative styling"},
}


# ============================================================
# State → 코디방법 ID 매핑 (OutfitAnalyzer state 필드 연결)
# ============================================================

# OutfitItem.state에서 코디방법 ID를 추론하는 테이블
# VLM이 반환하는 state 값 → 치트시트 코디방법 ID
STATE_TO_STYLING_MAP = {
    # 아우터/상의 공통
    "open": "지퍼오픈",
    "closed": "지퍼클로즈",
    "zipper_open": "지퍼오픈",
    "zipper_closed": "지퍼클로즈",
    "draped": "어깨걸침",
    "draped_over_shoulder": "어깨걸침",
    "one_arm": "한쪽만착용",
    "one_arm_only": "한쪽만착용",
    "held": "손에들고",
    "held_in_hand": "손에들고",
    "buttons_open": "버튼오픈",
    # 상의 전용
    "off_shoulder": "한쪽어깨노출",
    "off-shoulder": "한쪽어깨노출",
    "cropped": "크롭",
    "tucked": "넣어입기",
    "tucked_in": "넣어입기",
    "oversized": "오버사이즈",
    # 하의 전용
    "high_waist": "하이웨이스트",
    "high-waist": "하이웨이스트",
    "low_waist": "로우웨이스트",
    "low-waist": "로우웨이스트",
    "low_rise": "로우웨이스트",
    "rolled": "롤업",
    "cuffed": "롤업",
    "one_leg_cuffed": "원레그롤업",
    "one_cuff": "원레그롤업",
    # 신발 전용
    "untied": "끈풀림",
    "laces_untied": "끈풀림",
    "heel_down": "뒤꿈치밟기",
    "heel_stepped": "뒤꿈치밟기",
    # 헤드웨어 전용
    "backwards": "뒤로쓰기",
    "backward": "뒤로쓰기",
    "sideways": "옆으로쓰기",
    "tilted": "살짝올려쓰기",
    "lifted": "살짝올려쓰기",
    # 주얼리 전용
    "layered": "레이어드",
    "asymmetric": "언발런스",
    "unbalanced": "언발런스",
    # 가방 전용
    "crossbody": "크로스바디",
    "cross_body": "크로스바디",
    "shoulder": "숄더",
    "on_ground": "바닥에놓기",
    "placed_down": "바닥에놓기",
    # 벨트 전용
    "loose": "느슨하게",
    "loosely": "느슨하게",
    "decorative": "장식용",
    # 기본값 (매핑 안되면)
    "normal": "정상착용",
    "default": "정상착용",
}


def infer_styling_from_state(state: str, category: str) -> str:
    """
    OutfitItem.state에서 코디방법 ID 추론.

    Args:
        state: OutfitItem.state 값 (예: "open", "draped", "rolled")
        category: 한글 카테고리 (예: "아우터", "상의")

    Returns:
        코디방법 ID (예: "지퍼오픈", "어깨걸침")
    """
    if not state or state.lower() in ["normal", ""]:
        # 기본값 반환
        return STYLING_DEFAULTS.get(category, {"id": "정상착용"})["id"]

    # state 정규화 (소문자, 공백→언더스코어)
    normalized = state.lower().strip().replace(" ", "_").replace("-", "_")

    # 매핑 테이블에서 찾기
    if normalized in STATE_TO_STYLING_MAP:
        return STATE_TO_STYLING_MAP[normalized]

    # 부분 매칭 시도
    for key, value in STATE_TO_STYLING_MAP.items():
        if key in normalized or normalized in key:
            return value

    # 매핑 실패 시 기본값
    return STYLING_DEFAULTS.get(category, {"id": "정상착용"})["id"]


def infer_styling_from_spec(spec: dict, category: str) -> str:
    """
    OutfitItem의 spec(structure/finishing)에서 코디방법 ID 추론.

    Args:
        spec: {"fit": "...", "structure": "...", "finishing": "..."}
        category: 한글 카테고리

    Returns:
        코디방법 ID (추론 성공 시) 또는 None (추론 실패 시)
    """
    if not spec:
        return None

    structure = spec.get("structure", "").lower()
    finishing = spec.get("finishing", "").lower()
    fit = spec.get("fit", "").lower()

    # structure에서 코디방법 추론
    structure_patterns = [
        ("off shoulder", "한쪽어깨노출"),
        ("one shoulder", "한쪽어깨노출"),
        ("cropped", "크롭"),
        ("tucked", "넣어입기"),
        ("open front", "지퍼오픈"),
        ("zip open", "지퍼오픈"),
        ("draped", "어깨걸침"),
    ]
    for pattern, styling_id in structure_patterns:
        if pattern in structure:
            return styling_id

    # finishing에서 코디방법 추론
    finishing_patterns = [
        ("cuffed", "롤업"),
        ("rolled", "롤업"),
        ("untied", "끈풀림"),
    ]
    for pattern, styling_id in finishing_patterns:
        if pattern in finishing:
            return styling_id

    # fit에서 코디방법 추론
    if "oversized" in fit or "over" in fit:
        return "오버사이즈"

    return None


# ============================================================
# Blind Spot → 네거티브 프롬프트 변환
# ============================================================

# blind_spot에서 감지해야 할 패턴 → 네거티브 프롬프트
# "NO X" 패턴 → "add X, X visible" 형태로 네거티브에 추가
BLIND_SPOT_NEGATIVE_PATTERNS = {
    # 구조적 특징 (있으면 안되는 것들)
    "no brim": "brim, visor, cap brim visible",
    "no fold": "folded, fold visible",
    "no cuff": "cuff, cuffed",
    "no logo": "logo visible, brand logo",
    "seamless": "visible seams, stitching lines",
    "no buttons": "buttons, button closure",
    "no zipper": "zipper, zip closure",
    # 질감/소재 관련 (반대 질감 방지)
    "matte": "shiny, glossy, reflective",
    "glossy": "matte, flat finish",
    "fuzzy": "smooth, sleek",
    "smooth": "fuzzy, textured",
    # 핏 관련
    "slim fit": "baggy, oversized, loose",
    "oversized": "fitted, slim, tight",
    "cropped": "full length, long",
}


def extract_negatives_from_blind_spots(items: list) -> list:
    """
    OutfitItem들의 blind_spot에서 네거티브 프롬프트 추출.

    Args:
        items: OutfitItem 리스트

    Returns:
        네거티브 프롬프트에 추가할 문자열 리스트
    """
    negatives = []

    for item in items:
        # details 필드에 blind_spot이 저장됨
        details = getattr(item, "details", []) or []

        for detail in details:
            detail_lower = detail.lower()

            # "NO X" 패턴 감지 → 네거티브 생성
            if detail_lower.startswith("no "):
                negated_item = detail_lower[3:].strip()
                # "no brim" → "brim, visor, add brim"
                negatives.append(f"{negated_item}, add {negated_item}")

            # 패턴 테이블에서 매칭
            for pattern, negative in BLIND_SPOT_NEGATIVE_PATTERNS.items():
                if pattern in detail_lower:
                    negatives.append(negative)
                    break

    # 중복 제거
    return list(set(negatives))


def build_negative_from_outfit(outfit_analysis) -> str:
    """
    OutfitAnalysis에서 네거티브 프롬프트 확장.

    기본 네거티브 + blind_spot 기반 네거티브 결합.

    Args:
        outfit_analysis: OutfitAnalysis 객체

    Returns:
        확장된 네거티브 프롬프트 문자열
    """
    # 기본 네거티브 (MLB DNA)
    base_negative = "bright smile, teeth showing, golden hour, warm amber"

    if not outfit_analysis or not hasattr(outfit_analysis, "items"):
        return base_negative

    # blind_spot에서 네거티브 추출
    additional_negatives = extract_negatives_from_blind_spots(outfit_analysis.items)

    if additional_negatives:
        return f"{base_negative}, {', '.join(additional_negatives)}"

    return base_negative


# 코디방법 ID → 프롬프트 매핑 (mlb-prompt-cheatsheet.md 360-400줄 기반)
STYLING_PROMPT_MAP = {
    # 아우터
    "정상착용": "worn normally",
    "어깨걸침": "jacket draped over shoulder",
    "한쪽만착용": "worn on one arm only",
    "지퍼오픈": "zipper open",
    "지퍼클로즈": "zipper closed",
    "손에들고": "held in hand",
    # 상의
    "크롭": "cropped above waist",
    "넣어입기": "tucked into pants",
    "한쪽어깨노출": "off-shoulder on one side",
    "버튼오픈": "buttons open",
    "오버사이즈": "oversized fit, 2-3 sizes up",
    # 하의
    "하이웨이스트": "high-waisted fit",
    "로우웨이스트": "low-rise fit",
    "롤업": "cuffed at ankle",
    "원레그롤업": "one leg cuffed",
    # 신발
    "끈풀림": "laces untied",
    "뒤꿈치밟기": "heel stepped down",
    # 헤드웨어
    "뒤로쓰기": "cap worn backwards",
    "옆으로쓰기": "cap worn sideways",
    "살짝올려쓰기": "cap slightly lifted",
    # 주얼리
    "레이어드": "layered jewelry",
    "언발런스": "asymmetric styling",
    # 가방
    "크로스바디": "crossbody wear",
    "숄더": "shoulder wear",
    "바닥에놓기": "placed on ground",
    # 벨트
    "느슨하게": "worn loosely",
    "장식용": "decorative styling",
}


# 컨셉별 표정 매핑 (mlb-prompt-cheatsheet.md 446-465줄 기반)
CONCEPT_MAPPING = {
    "cool": {
        "입_허용": ["closed", "parted"],
        "시선_허용": ["direct", "past", "side"],
        "기본_입": "closed",
        "기본_시선": "direct",
    },
    "natural": {
        "입_허용": ["closed", "parted"],
        "시선_허용": ["direct", "past"],
        "기본_입": "closed",
        "기본_시선": "direct",
    },
    "dreamy": {
        "입_허용": ["parted", "closed"],
        "시선_허용": ["past", "side"],
        "기본_입": "parted",
        "기본_시선": "past",
    },
    "neutral": {
        "입_허용": ["closed"],
        "시선_허용": ["direct"],
        "기본_입": "closed",
        "기본_시선": "direct",
    },
    "serious": {
        "입_허용": ["closed"],
        "시선_허용": ["direct"],
        "기본_입": "closed",
        "기본_시선": "direct",
    },
}


def _infer_category(category: str, name: str) -> str:
    """
    아이템 카테고리/이름에서 표준 한글 카테고리 추론

    Args:
        category: OutfitItem.category (표준 카테고리 또는 아이템 이름)
        name: OutfitItem.name (아이템 이름)

    Returns:
        str: 한글 카테고리 ("아우터", "상의", "하의" 등)
    """
    # 표준 영어 카테고리 매핑
    category_map = {
        "outer": "아우터",
        "top": "상의",
        "bottom": "하의",
        "shoes": "신발",
        "headwear": "헤드웨어",
        "jewelry": "주얼리",
        "bag": "가방",
        "belt": "벨트",
    }

    # 먼저 표준 카테고리인지 확인
    if category.lower() in category_map:
        return category_map[category.lower()]

    # 아이템 이름에서 카테고리 추론
    text = f"{category} {name}".lower()

    # 아우터 키워드
    if any(
        kw in text
        for kw in [
            "jacket",
            "coat",
            "hoodie",
            "blazer",
            "cardigan",
            "parka",
            "bomber",
            "varsity",
            "windbreaker",
            "outer",
        ]
    ):
        return "아우터"

    # 상의 키워드
    if any(
        kw in text
        for kw in [
            "top",
            "shirt",
            "blouse",
            "tee",
            "t-shirt",
            "tank",
            "sweater",
            "sweatshirt",
            "crop",
            "vest",
        ]
    ):
        return "상의"

    # 하의 키워드
    if any(
        kw in text
        for kw in [
            "pants",
            "jeans",
            "denim",
            "skirt",
            "shorts",
            "trousers",
            "legging",
            "bottom",
            "cargo",
        ]
    ):
        return "하의"

    # 신발 키워드
    if any(
        kw in text
        for kw in [
            "shoes",
            "sneaker",
            "boot",
            "sandal",
            "loafer",
            "heel",
            "slipper",
            "footwear",
        ]
    ):
        return "신발"

    # 헤드웨어 키워드
    if any(
        kw in text for kw in ["cap", "hat", "beanie", "beret", "headwear", "headband"]
    ):
        return "헤드웨어"

    # 주얼리 키워드
    if any(
        kw in text
        for kw in [
            "necklace",
            "earring",
            "ring",
            "bracelet",
            "chain",
            "jewelry",
            "jewellery",
            "pendant",
        ]
    ):
        return "주얼리"

    # 가방 키워드
    if any(
        kw in text
        for kw in ["bag", "purse", "clutch", "tote", "backpack", "hobo", "crossbody"]
    ):
        return "가방"

    # 벨트 키워드
    if "belt" in text:
        return "벨트"

    # 추론 실패 시 원본 반환
    return category


def _build_outfit_prompt_section(outfit: dict, styling: dict) -> dict:
    """
    착장 설명과 코디방법을 결합하여 프롬프트 텍스트 생성

    Args:
        outfit: 착장 딕셔너리 {"아우터": "varsity jacket, brown...", ...}
        styling: 코디방법 딕셔너리 {"아우터": "정상착용", ...}

    Returns:
        dict: 카테고리별 결합된 프롬프트 텍스트
              {"아우터": "varsity jacket, brown, worn normally", ...}
              (빈 착장은 제외됨)
    """
    result = {}

    for category, item_desc in outfit.items():
        # 빈 착장은 제외
        if not item_desc or not item_desc.strip():
            continue

        # 코디방법 ID 가져오기
        styling_id = styling.get(category, "정상착용")

        # 코디방법 ID → 프롬프트 텍스트 변환
        styling_prompt = STYLING_PROMPT_MAP.get(styling_id, "worn normally")

        # 착장 설명 + 코디방법 결합
        result[category] = f"{item_desc}, {styling_prompt}"

    return result


# 기본 배경 설정 (사용자 미입력 시)
DEFAULT_BACKGROUND = "깔끔한 콘크리트, 메탈 포인트"
DEFAULT_BACKGROUND_DETAIL = "clean concrete floor with metallic accents, industrial minimalist, cool neutral tones"


def _build_background_section(user_options: dict) -> dict:
    """
    배경 섹션 빌드

    우선순위:
    1. user_options["background_description"] - 사용자가 제공한 배경 설명 (VLM 분석 결과)
    2. user_options["배경.장소"] - 직접 지정한 장소
    3. 기본값 - 깔끔한 콘크리트, 메탈 포인트

    Args:
        user_options: 사용자 옵션 dict

    Returns:
        dict: {"장소": str, "배경상세": str}
    """
    # 사용자가 배경 설명을 제공했는지 확인
    bg_desc = user_options.get("background_description", "")
    bg_place = user_options.get("배경.장소", "")
    bg_detail = user_options.get("배경.배경상세", "")

    if bg_desc:
        # VLM 분석 결과가 있으면 장소와 상세 모두 채움
        # 장소는 상세 설명에서 핵심 키워드 추출 (첫 20자 정도)
        place = bg_desc[:50].split(",")[0].strip() if bg_desc else DEFAULT_BACKGROUND
        return {
            "장소": place,
            "배경상세": bg_desc,
        }
    elif bg_place:
        # 사용자가 직접 장소 지정
        return {
            "장소": bg_place,
            "배경상세": bg_detail,
        }
    else:
        # 기본값
        return {
            "장소": DEFAULT_BACKGROUND,
            "배경상세": DEFAULT_BACKGROUND_DETAIL,
        }


def build_prompt(
    outfit_analysis: OutfitAnalysis,
    pose_analysis: Optional[dict] = None,
    mood_analysis: Optional[dict] = None,
    background_type: str = "without_car",
    user_options: Optional[dict] = None,
) -> dict:
    """
    치트시트 기반 프롬프트 JSON 조립

    Args:
        outfit_analysis: OutfitAnalysis 객체 (core.outfit_analyzer.OutfitAnalysis)
        pose_analysis: 포즈/표정 분석 결과 (선택)
        mood_analysis: 무드/분위기 분석 결과 (선택)
        background_type: "with_car" | "without_car"
        user_options: 사용자 추가 옵션 (count, aspect_ratio, resolution 등)

    Returns:
        dict: MLB 치트시트 JSON 스키마 형식의 프롬프트
    """
    user_options = user_options or {}

    # 기본 프롬프트 JSON 구조 (mlb-prompt-cheatsheet.md 12-87줄)
    prompt_json = {
        "주제": {
            "character": "필름 그레인 질감, 에디토리얼 패션 사진 스타일",
            "mood": mood_analysis.get("mood", "") if mood_analysis else "",
        },
        "모델": {
            "민족": user_options.get("민족", "korean"),
            "성별": user_options.get("성별", "female"),
            "나이": user_options.get("나이", "early_20s"),
        },
        "헤어": {
            "스타일": user_options.get("헤어.스타일", "straight_loose"),
            "컬러": user_options.get("헤어.컬러", "black"),
            "질감": user_options.get("헤어.질감", "sleek"),
        },
        "메이크업": {
            "베이스": user_options.get("메이크업.베이스", "natural"),
            "블러셔": user_options.get("메이크업.블러셔", "none"),
            "립": user_options.get("메이크업.립", "mlbb"),
            "아이": user_options.get("메이크업.아이", "natural"),
        },
        "촬영": _build_camera_section(pose_analysis, user_options),
        "포즈": _build_pose_section(pose_analysis, user_options),
        "표정": _build_expression_section(pose_analysis, user_options),
        # 착장: 모든 카테고리 (중첩 구조)
        # 각 카테고리 = {"아이템": "...", "코디방법": "...", "프롬프트": "..."}
        "착장": {
            "아우터": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["아우터"]["id"],
                "프롬프트": "",
            },
            "상의": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["상의"]["id"],
                "프롬프트": "",
            },
            "하의": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["하의"]["id"],
                "프롬프트": "",
            },
            "신발": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["신발"]["id"],
                "프롬프트": "",
            },
            "헤드웨어": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["헤드웨어"]["id"],
                "프롬프트": "",
            },
            "주얼리": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["주얼리"]["id"],
                "프롬프트": "",
            },
            "가방": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["가방"]["id"],
                "프롬프트": "",
            },
            "벨트": {
                "아이템": "",
                "코디방법": STYLING_DEFAULTS["벨트"]["id"],
                "프롬프트": "",
            },
        },
        "배경": _build_background_section(user_options),
        "조명색감": {
            "조명": mood_analysis.get("조명", "자연광흐림")
            if mood_analysis
            else user_options.get("조명색감.조명", "자연광흐림"),
            "색보정": mood_analysis.get("색보정", "뉴트럴쿨")
            if mood_analysis
            else user_options.get("조명색감.색보정", "뉴트럴쿨"),
        },
        "출력품질": "professional fashion photography, high-end editorial, sharp focus, 8K quality",
        # ★ 네거티브: blind_spot에서 자동 추출된 항목 포함
        "네거티브": build_negative_from_outfit(outfit_analysis),
    }

    # OutfitAnalysis에서 착장 정보 채우기 (중첩 구조)
    if outfit_analysis and hasattr(outfit_analysis, "items"):
        for item in outfit_analysis.items:
            # 아이템 이름/카테고리에서 표준 카테고리 추론
            kor_category = _infer_category(item.category, item.name)
            if kor_category and kor_category in prompt_json["착장"]:
                # OutfitItem 필드에서 설명 조합: name, color, fit, material_appearance
                item_desc_parts = [item.name]
                if item.color:
                    item_desc_parts.append(item.color)
                if item.fit and item.fit != "regular":
                    item_desc_parts.append(f"{item.fit} fit")
                if item.material_appearance:
                    item_desc_parts.append(item.material_appearance)

                # ★ 로고 정보 추가 (MUST/NEVER 강조 - 위치 무시 방지)
                if hasattr(item, "logos") and item.logos:
                    for logo in item.logos:
                        logo_desc = _format_logo_detail(logo)
                        item_desc_parts.append(logo_desc)

                # ★ 디테일 정보 추가 (MUST/NEVER 강조 - NO BRIM 등 무시 방지)
                if hasattr(item, "details") and item.details:
                    for detail in item.details:
                        formatted_detail = _format_critical_detail(detail)
                        item_desc_parts.append(formatted_detail)

                item_desc = ", ".join(item_desc_parts)

                # 착장 중첩 구조에 아이템 정보 채우기
                prompt_json["착장"][kor_category]["아이템"] = item_desc

                # ★ 코디방법 추론 우선순위:
                # 1. 사용자 옵션 (직접 지정)
                # 2. state에서 추론
                # 3. spec.structure/finishing에서 추론
                # 4. 기본값
                styling_id = None

                # 1. 사용자 옵션 확인
                user_styling = user_options.get(f"코디방법.{kor_category}")
                if user_styling:
                    styling_id = user_styling
                else:
                    # 2. state에서 추론 시도
                    if hasattr(item, "state") and item.state:
                        inferred = infer_styling_from_state(item.state, kor_category)
                        if inferred and inferred != "정상착용":
                            styling_id = inferred
                            print(
                                f"[Adapter] state '{item.state}' → 코디방법 '{styling_id}' (카테고리: {kor_category})"
                            )

                    # 3. spec에서 추론 시도 (state에서 추론 못했으면)
                    if not styling_id:
                        # OutfitAnalyzer의 spec은 별도 필드로 저장되지 않으므로
                        # details(blind_spot)에서 구조 정보 찾아서 추론
                        spec_dict = {}
                        if hasattr(item, "fit"):
                            spec_dict["fit"] = item.fit
                        if hasattr(item, "details") and item.details:
                            # details에서 structure/finishing 관련 키워드 찾기
                            for d in item.details:
                                d_lower = d.lower()
                                if any(
                                    kw in d_lower
                                    for kw in [
                                        "off shoulder",
                                        "cropped",
                                        "tucked",
                                        "open",
                                    ]
                                ):
                                    spec_dict["structure"] = d
                                if any(
                                    kw in d_lower
                                    for kw in ["cuffed", "rolled", "untied"]
                                ):
                                    spec_dict["finishing"] = d
                        inferred = infer_styling_from_spec(spec_dict, kor_category)
                        if inferred:
                            styling_id = inferred
                            print(
                                f"[Adapter] spec 추론 → 코디방법 '{styling_id}' (카테고리: {kor_category})"
                            )

                # 4. 기본값 폴백
                if not styling_id:
                    styling_id = prompt_json["착장"][kor_category]["코디방법"]

                prompt_json["착장"][kor_category]["코디방법"] = styling_id

                # 프롬프트: 아이템 + 코디방법 결합
                styling_prompt = STYLING_PROMPT_MAP.get(styling_id, "worn normally")
                prompt_json["착장"][kor_category]["프롬프트"] = (
                    f"{item_desc}, {styling_prompt}"
                )

    # 사용자 옵션으로 착장 override
    for key, value in user_options.items():
        if key.startswith("착장."):
            parts = key.split(".")
            if len(parts) >= 2:
                category = parts[1]
                if category in prompt_json["착장"]:
                    if len(parts) == 2:
                        # "착장.상의" = "crop top" 형태
                        prompt_json["착장"][category]["아이템"] = value
                    elif len(parts) == 3:
                        # "착장.상의.코디방법" = "한쪽어깨노출" 형태
                        field = parts[2]
                        if field in ["아이템", "코디방법"]:
                            prompt_json["착장"][category][field] = value

    # 프롬프트 필드 재생성 (사용자 옵션 반영 후)
    for category, data in prompt_json["착장"].items():
        if data["아이템"]:
            styling_prompt = STYLING_PROMPT_MAP.get(data["코디방법"], "worn normally")
            data["프롬프트"] = f"{data['아이템']}, {styling_prompt}"

    # 컨셉 매핑 적용
    concept = prompt_json["표정"]["베이스"]
    prompt_json = apply_concept_mapping(concept, prompt_json)

    # 금지 조합 검증 및 수정
    prompt_json = validate_and_fix_combinations(prompt_json)

    # 한국어 자연어 레이어 추가 (품질 향상)
    prompt_json = enhance_with_korean_layer(
        prompt_json,
        include_moment=user_options.get("include_moment", True),
        moment_type=user_options.get("moment_type", None),
    )

    return prompt_json


def validate_and_fix_combinations(prompt_json: dict) -> dict:
    """
    금지 조합 검증 및 자동 수정

    SKILL.md 386-411줄의 로직을 테이블 기반으로 확장.

    검증 규칙:
    - 렌즈-프레이밍 검증 (85mm+MFS → 50mm, 35mm+CU → 85mm)
    - 표정-입 검증 (cool/serious + smile → closed)
    - 표정-시선 검증 (dreamy + direct → past)

    Args:
        prompt_json: 프롬프트 JSON

    Returns:
        dict: 수정된 프롬프트 JSON
    """
    # 각 금지 조합 규칙 검증
    for rule in FORBIDDEN_COMBINATIONS:
        if rule["condition"](prompt_json):
            # 금지 조합 감지 시 자동 수정
            for path, value in rule["fix"].items():
                keys = path.split(".")
                current = prompt_json
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = value

            print(f"⚠️  금지 조합 감지 및 수정: {rule['rule']} → {rule['fix']}")

    return prompt_json


def apply_concept_mapping(concept: str, prompt_json: dict) -> dict:
    """
    컨셉별 표정/시선/입 자동 매핑

    mlb-prompt-cheatsheet.md 446-465줄의 표정-입, 표정-시선 호환 규칙 적용.

    Args:
        concept: 표정 베이스 ("cool", "natural", "dreamy", "neutral", "serious")
        prompt_json: 프롬프트 JSON

    Returns:
        dict: 매핑 적용된 프롬프트 JSON
    """
    if concept not in CONCEPT_MAPPING:
        return prompt_json

    mapping = CONCEPT_MAPPING[concept]

    # 현재 입/시선 값
    current_mouth = prompt_json.get("표정", {}).get("입", "")
    current_gaze = prompt_json.get("표정", {}).get("시선", "")

    # 입 검증: 허용되지 않는 값이면 기본값으로 변경
    if current_mouth not in mapping["입_허용"]:
        prompt_json["표정"]["입"] = mapping["기본_입"]
        print(
            f"⚠️  컨셉 '{concept}'에서 입 '{current_mouth}' 불가 → '{mapping['기본_입']}'로 변경"
        )

    # 시선 검증: 허용되지 않는 값이면 기본값으로 변경
    if current_gaze not in mapping["시선_허용"]:
        prompt_json["표정"]["시선"] = mapping["기본_시선"]
        print(
            f"⚠️  컨셉 '{concept}'에서 시선 '{current_gaze}' 불가 → '{mapping['기본_시선']}'로 변경"
        )

    return prompt_json
