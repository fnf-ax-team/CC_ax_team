"""
통합 프롬프트 빌더 (v2)

기존 prompt_builder.py + korean_prompt_builder.py 통합.
한국어 자연어 프롬프트를 기본으로 생성.

변경점:
- JSON 스키마 + 한국어 자연어를 하나의 프롬프트로 통합
- enhance_with_korean_layer() 불필요 → build_prompt()가 바로 한국어 프롬프트 포함
"""

from typing import Optional, List
import re
import random
from core.outfit_analyzer import OutfitAnalysis


# ============================================================
# 빈도 기반 랜덤 추출 (치트시트 빈도 데이터)
# ============================================================

EXPRESSION_FREQUENCIES = {
    "베이스": {"cool": 50, "natural": 25, "neutral": 15, "serious": 10},
    "바이브": {"mysterious": 40, "approachable": 25, "sophisticated": 35},
    "시선": {"direct": 50, "past": 30, "side": 20},
    "입": {"closed": 60, "parted": 30, "smile": 10},
}


def _weighted_random_choice(frequency_dict: dict) -> str:
    """빈도(가중치) 기반 랜덤 선택"""
    options = list(frequency_dict.keys())
    weights = list(frequency_dict.values())
    return random.choices(options, weights=weights, k=1)[0]


def get_random_expression() -> dict:
    """빈도 기반 랜덤 표정 조합 생성"""
    result = {}
    for field, frequencies in EXPRESSION_FREQUENCIES.items():
        result[field] = _weighted_random_choice(frequencies)

    # 금지 조합 수정
    if result["베이스"] == "dreamy" and result["시선"] == "direct":
        result["시선"] = "past"
    if result["베이스"] in ["serious", "cool"] and result["입"] == "smile":
        result["입"] = "closed"

    return result


# ============================================================
# K-Beauty 표정 프리셋 (상세 표정 요소)
# ============================================================

KBEAUTY_EXPRESSION_PRESETS = {
    # 시크 (Chic) 계열 - 도도하고 카리스마 있는
    "chic_confident": {
        "preset": "chic_confident",
        "베이스": "cool",
        "바이브": "confident chic",
        "시선": "direct",
        "입": "closed",
        "intensity": 75,
        "detailed": {
            "eyes": {
                "openness": "half_lidded",  # 반쯤 감은 눈
                "eye_corner": "upturned",  # 눈꼬리 올라감
                "gaze_intensity": "intense_piercing",  # 강렬한 눈빛
                "eye_smile": "none",
            },
            "mouth": {
                "state": "slightly_parted",  # 살짝 벌린 입술
                "corner": "neutral_slight_pout",  # 약간 삐죽
            },
            "chin": "raised",  # 턱 살짝 들기
        },
        "prompt_text": "half-lidded eyes with upturned corners, intense piercing gaze, lips slightly parted with subtle pout, chin raised confidently, chic and unapproachable",
    },
    "chic_mysterious": {
        "preset": "chic_mysterious",
        "베이스": "cool",
        "바이브": "mysterious",
        "시선": "past",
        "입": "closed",
        "intensity": 70,
        "detailed": {
            "eyes": {
                "openness": "half_lidded",
                "eye_corner": "neutral",
                "gaze_intensity": "distant_dreamy",
                "eye_smile": "none",
            },
            "mouth": {
                "state": "closed",
                "corner": "relaxed",
            },
            "chin": "neutral",
        },
        "prompt_text": "half-lidded dreamy eyes gazing into distance, closed relaxed lips, mysterious and enigmatic expression",
    },
    # 러블리 (Lovely) 계열 - 사랑스럽고 따뜻한
    "lovely_warm": {
        "preset": "lovely_warm",
        "베이스": "natural",
        "바이브": "warm approachable",
        "시선": "direct",
        "입": "smile",
        "intensity": 60,
        "detailed": {
            "eyes": {
                "openness": "natural",
                "eye_corner": "soft",
                "gaze_intensity": "soft_warm",
                "eye_smile": "present",  # 눈웃음
            },
            "mouth": {
                "state": "gentle_smile",
                "corner": "upturned",  # 입꼬리 올라감
            },
            "chin": "neutral_lowered",
        },
        "prompt_text": "natural soft eyes with warm gaze, gentle eye smile, soft genuine smile with upturned corners, warm and approachable",
    },
    "lovely_dreamy": {
        "preset": "lovely_dreamy",
        "베이스": "natural",
        "바이브": "dreamy soft",
        "시선": "past",
        "입": "parted",
        "intensity": 55,
        "detailed": {
            "eyes": {
                "openness": "slightly_wide",
                "eye_corner": "soft_round",
                "gaze_intensity": "soft_dreamy",
                "eye_smile": "slight",
            },
            "mouth": {
                "state": "slightly_open",
                "corner": "soft",
            },
            "chin": "lowered",
        },
        "prompt_text": "slightly wide dreamy eyes with soft round corners, soft distant gaze, lips slightly open, innocent dreamy expression",
    },
    # 청순 (Innocent/Pure) 계열
    "innocent_pure": {
        "preset": "innocent_pure",
        "베이스": "natural",
        "바이브": "innocent",
        "시선": "direct",
        "입": "closed",
        "intensity": 50,
        "detailed": {
            "eyes": {
                "openness": "wide",
                "eye_corner": "round_soft",
                "gaze_intensity": "clear_pure",
                "eye_smile": "slight",
            },
            "mouth": {
                "state": "closed",
                "corner": "soft_neutral",
            },
            "chin": "lowered",
        },
        "prompt_text": "wide clear eyes with round soft corners, pure innocent gaze, closed soft lips, youthful innocent expression",
    },
    # 도도 (Haughty/Cool) 계열
    "haughty_cool": {
        "preset": "haughty_cool",
        "베이스": "serious",
        "바이브": "haughty unapproachable",
        "시선": "direct",
        "입": "closed",
        "intensity": 80,
        "detailed": {
            "eyes": {
                "openness": "narrow",
                "eye_corner": "sharply_upturned",
                "gaze_intensity": "cold_piercing",
                "eye_smile": "none",
            },
            "mouth": {
                "state": "firmly_closed",
                "corner": "slight_downturn",
            },
            "chin": "raised_high",
        },
        "prompt_text": "narrow cold eyes with sharply upturned corners, piercing icy gaze, firmly closed lips with slight downturn, chin raised high, haughty unapproachable",
    },
    "haughty_elegant": {
        "preset": "haughty_elegant",
        "베이스": "cool",
        "바이브": "elegant superior",
        "시선": "side",
        "입": "closed",
        "intensity": 75,
        "detailed": {
            "eyes": {
                "openness": "half_lidded",
                "eye_corner": "upturned",
                "gaze_intensity": "superior_distant",
                "eye_smile": "none",
            },
            "mouth": {
                "state": "closed",
                "corner": "neutral",
            },
            "chin": "raised",
        },
        "prompt_text": "half-lidded eyes gazing sideways, upturned corners with superior distant look, closed neutral lips, elegant and untouchable",
    },
    # 내추럴 (Natural) 계열
    "natural_relaxed": {
        "preset": "natural_relaxed",
        "베이스": "natural",
        "바이브": "relaxed natural",
        "시선": "direct",
        "입": "parted",
        "intensity": 45,
        "detailed": {
            "eyes": {
                "openness": "natural",
                "eye_corner": "natural",
                "gaze_intensity": "soft_natural",
                "eye_smile": "none",
            },
            "mouth": {
                "state": "naturally_parted",
                "corner": "relaxed",
            },
            "chin": "neutral",
        },
        "prompt_text": "natural relaxed eyes with soft gaze, lips naturally parted, effortlessly natural expression",
    },
}


def get_expression_preset(preset_name: str) -> Optional[dict]:
    """프리셋 이름으로 표정 데이터 조회"""
    return KBEAUTY_EXPRESSION_PRESETS.get(preset_name)


# ============================================================
# MLB 브랜드 DNA (한 곳에서 관리)
# ============================================================

MLB_BRAND_DNA = {
    # 포즈 DNA
    "pose": {
        "stance": "power stance, standing tall with confident posture, weight on one leg",
        "default_arms": "hand on hip or relaxed at side",
        "default_legs": "legs spread apart for wide power stance",
        "energy": "dominating the space, assertive",
    },
    # 표정 DNA
    "expression": {
        "default_base": "cool",
        "default_eyes": "intense, confident gaze",
        "default_mouth": "closed, slight pout",
        "vibe": "chic, mysterious, unapproachable beauty",
    },
    # 색감 DNA
    "color": {
        "tone": "cool tones only",
        "never": "golden hour, warm amber, yellow cast",
        "temperature": "neutral to slightly cool",
    },
    # 배경 DNA
    "background": {
        "default": "clean concrete, metallic accents, industrial minimalist",
        "style": "premium, high-end, editorial",
    },
    # 네거티브 프롬프트
    "negative": "bright smile, teeth showing, golden hour, warm amber, yellow cast, plastic skin, cartoon style, weak posture, messy background",
}


# ============================================================
# 코디방법 매핑 테이블
# ============================================================

STATE_TO_STYLING_MAP = {
    "open": "지퍼오픈",
    "closed": "지퍼클로즈",
    "draped": "어깨걸침",
    "one_arm": "한쪽만착용",
    "held": "손에들고",
    "off_shoulder": "한쪽어깨노출",
    "tucked": "넣어입기",
    "oversized": "오버사이즈",
    "rolled": "롤업",
    "backwards": "뒤로쓰기",
    "normal": "정상착용",
}

STYLING_PROMPT_MAP = {
    "정상착용": "worn normally",
    "어깨걸침": "jacket draped over shoulder",
    "한쪽만착용": "worn on one arm only",
    "지퍼오픈": "zipper open",
    "지퍼클로즈": "zipper closed",
    "손에들고": "held in hand",
    "크롭": "cropped above waist",
    "넣어입기": "tucked into pants",
    "한쪽어깨노출": "off-shoulder on one side",
    "오버사이즈": "oversized fit",
    "롤업": "cuffed at ankle",
    "뒤로쓰기": "cap worn backwards",
}


# ============================================================
# 헬퍼 함수
# ============================================================


def _format_critical_detail(detail: str) -> str:
    """디테일을 MUST/NEVER 형식으로 변환"""
    detail_upper = detail.upper()

    if "NO " in detail_upper or "NO-" in detail_upper:
        negation_match = re.search(r"NO[- ]?(\w+)", detail, re.IGNORECASE)
        if negation_match:
            negated_item = negation_match.group(1).lower()
            return f"[MUST: {detail}] [NEVER: add {negated_item}]"
        return f"[MUST: {detail}]"

    if "front_right" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or left]"
    if "front_left" in detail.lower():
        return f"[MUST: {detail}] [NEVER: center or right]"

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

    return f"[MUST: {detail}]"


def _format_logo_detail(logo) -> str:
    """로고 정보를 MUST/NEVER 형식으로 변환"""
    brand = logo.brand
    position = logo.position
    logo_type = logo.type

    position_never = {
        "front_right": "center or left",
        "front_left": "center or right",
        "front_center": "off-center",
    }
    never_part = position_never.get(position, "wrong position")

    return f"[MUST: {brand} logo at {position} ({logo_type})] [NEVER: {never_part}]"


def _infer_category(category: str, name: str) -> str:
    """아이템에서 표준 한글 카테고리 추론"""
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

    if category.lower() in category_map:
        return category_map[category.lower()]

    text = f"{category} {name}".lower()

    if any(
        kw in text for kw in ["jacket", "coat", "hoodie", "blazer", "varsity", "outer"]
    ):
        return "아우터"
    if any(kw in text for kw in ["top", "shirt", "tee", "tank", "sweater"]):
        return "상의"
    if any(kw in text for kw in ["pants", "jeans", "skirt", "shorts", "bottom"]):
        return "하의"
    if any(kw in text for kw in ["shoes", "sneaker", "boot"]):
        return "신발"
    if any(kw in text for kw in ["cap", "hat", "beanie"]):
        return "헤드웨어"
    if any(kw in text for kw in ["bag", "purse", "backpack"]):
        return "가방"

    return category


def infer_styling_from_state(state: str, category: str) -> str:
    """OutfitItem.state에서 코디방법 ID 추론"""
    if not state or state.lower() in ["normal", ""]:
        return "정상착용"

    normalized = state.lower().strip().replace(" ", "_").replace("-", "_")

    if normalized in STATE_TO_STYLING_MAP:
        return STATE_TO_STYLING_MAP[normalized]

    for key, value in STATE_TO_STYLING_MAP.items():
        if key in normalized or normalized in key:
            return value

    return "정상착용"


# ============================================================
# 한국어 프롬프트 템플릿
# ============================================================

KOREAN_PROMPT_TEMPLATE = """
{model_desc}

[착장] - 반드시 모든 아이템 포함!
{outfit_section}

[분위기]
{mood_section}

[품질]
초사실적 패션 화보. 진짜 사진과 구분 안 되게.
자연스러운 피부 질감, 모공까지 보이게.
손가락 정확히 5개.
천의 자연스러운 주름과 무게감.
진짜 카메라로 찍은 것 같은 얕은 심도와 보케.

[브랜드 톤 - MLB]
강렬한 눈빛으로 카메라 응시.
도도하고 자신감 있는 표정.
파워포즈 - 공간을 지배하는 당당함.
클린한 배경 - 단색 스튜디오 또는 럭셔리 차량.
쿨톤 색감 유지.
프리미엄하고 세련된 느낌.

[예쁘게]
에디토리얼 패션 매거진 화보 수준의 미감.
모델처럼 빛나는 아우라.
세련되고 고급스러운 무드.
보는 사람이 '와' 하는 비주얼.

절대 안 됨: {negative}
"""

MOMENT_TEMPLATES = {
    "stand": "서 있는 자연스러운 순간. 포즈가 아니라 쉬는 느낌.",
    "walk": "걷다가 멈춘 찰나. 자연스러운 움직임 포착.",
    "lean": "기대어 쉬고 있는 순간. 여유로운 분위기.",
    "sit": "앉아서 생각에 잠긴 순간. 자연스러운 휴식.",
}


# ============================================================
# 메인 함수
# ============================================================


def build_prompt(
    outfit_analysis: OutfitAnalysis,
    pose_analysis: Optional[dict] = None,
    mood_analysis: Optional[dict] = None,
    user_options: Optional[dict] = None,
) -> dict:
    """
    통합 프롬프트 빌더 (v2)

    JSON 스키마 + 한국어 자연어를 모두 포함하는 프롬프트 생성.

    Args:
        outfit_analysis: OutfitAnalysis 객체
        pose_analysis: 포즈/표정 분석 결과 (선택)
        mood_analysis: 무드/분위기 분석 결과 (선택)
        user_options: 사용자 추가 옵션

    Returns:
        dict: 프롬프트 JSON (korean_prompt 필드 포함)
    """
    user_options = user_options or {}

    # 1. 착장 섹션 빌드
    outfit_section_lines = []
    outfit_dict = {}  # JSON용

    if outfit_analysis and hasattr(outfit_analysis, "items"):
        for item in outfit_analysis.items:
            kor_category = _infer_category(item.category, item.name)

            # 아이템 설명 조합
            item_parts = [item.name]
            if item.color:
                item_parts.append(item.color)
            if item.fit and item.fit != "regular":
                item_parts.append(f"{item.fit} fit")
            if item.material_appearance:
                item_parts.append(item.material_appearance)

            # 로고 강조
            if hasattr(item, "logos") and item.logos:
                for logo in item.logos:
                    item_parts.append(_format_logo_detail(logo))

            # 디테일 강조
            if hasattr(item, "details") and item.details:
                for detail in item.details:
                    item_parts.append(_format_critical_detail(detail))

            item_desc = ", ".join(item_parts)

            # 코디방법 추론
            styling_id = "정상착용"
            if hasattr(item, "state") and item.state:
                styling_id = infer_styling_from_state(item.state, kor_category)

            styling_prompt = STYLING_PROMPT_MAP.get(styling_id, "worn normally")
            full_prompt = f"{item_desc}, {styling_prompt}"

            # 한국어 섹션용
            outfit_section_lines.append(f"- {kor_category}: {full_prompt}")

            # JSON용
            outfit_dict[kor_category] = {
                "아이템": item_desc,
                "코디방법": styling_id,
                "프롬프트": full_prompt,
            }

    outfit_section = (
        "\n".join(outfit_section_lines)
        if outfit_section_lines
        else "(착장 이미지 참조)"
    )

    # 2. 분위기 섹션 빌드
    mood_parts = []

    # 포즈 정보
    if pose_analysis:
        stance = pose_analysis.get("pose", {}).get("stance", "")
        if stance:
            mood_parts.append(f"자세: {stance}")

    # 무드 정보
    if mood_analysis:
        mood_desc = mood_analysis.get("mood", "")
        lighting = mood_analysis.get("조명", "자연광흐림")
        color_temp = mood_analysis.get("색보정", "뉴트럴쿨")
        if mood_desc:
            mood_parts.append(f"분위기: {mood_desc}")
        mood_parts.append(f"조명: {lighting}")
        mood_parts.append(f"색감: {color_temp}")
    else:
        mood_parts.append("조명: 자연광흐림")
        mood_parts.append("색감: 뉴트럴쿨 (쿨톤 유지)")

    # stance에서 순간 템플릿 선택
    moment_type = "stand"
    if pose_analysis:
        stance = pose_analysis.get("pose", {}).get("stance", "").lower()
        if "lean" in stance:
            moment_type = "lean"
        elif "sit" in stance:
            moment_type = "sit"
        elif "walk" in stance:
            moment_type = "walk"

    mood_parts.append(MOMENT_TEMPLATES.get(moment_type, MOMENT_TEMPLATES["stand"]))

    mood_section = "\n".join(mood_parts)

    # 3. 모델 정보
    gender = user_options.get("성별", "female")
    model_desc = f"이 얼굴의 한국인 {'여성' if gender == 'female' else '남성'} 모델."

    # 4. 네거티브 프롬프트 조정 (표정 프리셋에 따라)
    # 러블리/따뜻한 표정 프리셋은 smile 금지를 제거해야 함
    preset_name = user_options.get("표정.프리셋") or user_options.get("표정.preset")
    negative_prompt = MLB_BRAND_DNA["negative"]

    # 따뜻한 표정 프리셋 목록 (smile이 필요한 표정들)
    WARM_EXPRESSION_PRESETS = [
        "lovely_warm",
        "lovely_dreamy",
        "innocent_pure",
        "natural_relaxed",
    ]

    if preset_name in WARM_EXPRESSION_PRESETS:
        # smile 관련 금지 제거
        negative_prompt = negative_prompt.replace("bright smile, ", "")
        negative_prompt = negative_prompt.replace("teeth showing, ", "")
        print(
            f"[PROMPT] Warm expression preset '{preset_name}' - smile restriction removed"
        )

    # 5. 한국어 프롬프트 생성
    korean_prompt = KOREAN_PROMPT_TEMPLATE.format(
        model_desc=model_desc,
        outfit_section=outfit_section,
        mood_section=mood_section,
        negative=negative_prompt,
    )

    # 6. JSON 구조 빌드
    prompt_json = {
        # 한국어 프롬프트 (최우선 사용)
        "korean_prompt": korean_prompt,
        # JSON 구조 (보조/디버깅용)
        "착장": outfit_dict,
        "모델": {
            "민족": user_options.get("민족", "korean"),
            "성별": gender,
        },
        "조명색감": {
            "조명": mood_analysis.get("조명", "자연광흐림")
            if mood_analysis
            else "자연광흐림",
            "색보정": mood_analysis.get("색보정", "뉴트럴쿨")
            if mood_analysis
            else "뉴트럴쿨",
        },
        "네거티브": negative_prompt,
        # 브랜드 DNA (참조용)
        "_brand_dna": MLB_BRAND_DNA,
    }

    # 표정 정보 추가 (프리셋 우선, pose_analysis 그 다음, 마지막으로 랜덤)
    # user_options에 프리셋이 있거나 pose_analysis에 expression이 있으면 빌드
    has_preset = user_options.get("표정.프리셋") or user_options.get("표정.preset")
    has_pose_expr = pose_analysis and "expression" in pose_analysis
    if has_preset or has_pose_expr:
        prompt_json["표정"] = _build_expression_section(pose_analysis, user_options)
    else:
        random_expr = get_random_expression()
        prompt_json["표정"] = random_expr

    # 포즈 정보 추가
    if pose_analysis:
        prompt_json["포즈"] = pose_analysis.get("pose", {})
        prompt_json["촬영"] = _build_camera_section(pose_analysis, user_options)

    return prompt_json


def _build_camera_section(pose_analysis: Optional[dict], user_options: dict) -> dict:
    """촬영 섹션 빌드"""
    camera = pose_analysis.get("camera", {}) if pose_analysis else {}

    height_raw = camera.get("camera_height", "")
    if "low" in height_raw.lower():
        height = "로우앵글"
    elif "high" in height_raw.lower():
        height = "하이앵글"
    else:
        height = "눈높이"

    framing_raw = camera.get("framing", "")
    if "full" in framing_raw.lower() or "FS" in framing_raw:
        framing = "FS"
    elif "knee" in framing_raw.lower() or "MFS" in framing_raw:
        framing = "MFS"
    else:
        framing = user_options.get("촬영.프레이밍", "MS")

    return {
        "프레이밍": framing,
        "렌즈": user_options.get("촬영.렌즈", "50mm"),
        "앵글": user_options.get("촬영.앵글", "3/4측면"),
        "높이": height,
    }


def _build_expression_section(
    pose_analysis: Optional[dict], user_options: dict
) -> dict:
    """표정 섹션 빌드 (K-Beauty 프리셋 지원)"""

    # 1. 먼저 user_options에서 프리셋 확인
    preset_name = user_options.get("표정.프리셋") or user_options.get("표정.preset")
    if preset_name:
        preset = get_expression_preset(preset_name)
        if preset:
            # 프리셋 기반 표정 반환
            result = {
                "베이스": preset.get("베이스", "cool"),
                "바이브": preset.get("바이브", "mysterious"),
                "시선": preset.get("시선", "direct"),
                "입": preset.get("입", "closed"),
            }
            # 상세 정보가 있으면 추가
            if preset.get("detailed"):
                result["detailed"] = preset["detailed"]
            if preset.get("prompt_text"):
                result["prompt_text"] = preset["prompt_text"]
            if preset.get("intensity"):
                result["intensity"] = preset["intensity"]
            return result

    # 2. pose_analysis에서 표정 정보 확인
    expression = pose_analysis.get("expression", {}) if pose_analysis else {}

    if not expression:
        return get_random_expression()

    mood_raw = expression.get("mood", "")
    if "cool" in mood_raw.lower() or "confident" in mood_raw.lower():
        base = "cool"
    elif "dreamy" in mood_raw.lower():
        base = "dreamy"
    elif "natural" in mood_raw.lower():
        base = "natural"
    else:
        base = "cool"

    mouth_raw = expression.get("mouth", "")
    if "open" in mouth_raw.lower() or "parted" in mouth_raw.lower():
        mouth = "parted"
    else:
        mouth = "closed"

    return {
        "베이스": base,
        "바이브": expression.get("mood", "mysterious"),
        "시선": "direct",
        "입": mouth,
    }


# ============================================================
# 재시도용 프롬프트 강화 (타겟팅)
# ============================================================


def enhance_prompt_for_retry(
    original_prompt: dict,
    failed_criteria: List[str],
    reasons: dict,
) -> dict:
    """
    실패 항목별 타겟 프롬프트 강화

    Args:
        original_prompt: 원본 프롬프트
        failed_criteria: 실패한 기준 리스트
        reasons: 실패 사유 딕셔너리

    Returns:
        dict: 강화된 프롬프트
    """
    enhanced = original_prompt.copy()

    # 착장 실패 → 착장 프롬프트만 강화
    if "outfit_accuracy" in failed_criteria:
        outfit_reason = reasons.get("outfit_accuracy", "")
        outfit_fix = f"""
[착장 수정 필수!]
이전 시도 실패 사유: {outfit_reason}

착장 아이템을 100% 정확하게 재현해야 합니다:
- 모든 아이템 누락 없이 포함
- 색상 정확히 일치
- 로고 위치와 디자인 정확히
- 옷의 핏과 스타일링 그대로
"""
        enhanced["_outfit_enhancement"] = outfit_fix

    # 얼굴 실패 → 얼굴 프롬프트만 강화
    if "face_identity" in failed_criteria:
        face_reason = reasons.get("face_identity", "")
        face_fix = f"""
[얼굴 동일성 수정 필수!]
이전 시도 실패 사유: {face_reason}

얼굴을 100% 동일하게 재현해야 합니다:
- 눈 모양 (쌍꺼풀, 크기, 눈꼬리)
- 코 (콧대, 코끝)
- 입술 (두께, 인중)
- 턱선 (각도, 길이)
- 광대뼈 (돌출 정도)
"""
        enhanced["_face_enhancement"] = face_fix

    # 브랜드 톤 실패 → 브랜드 프롬프트만 강화
    if "brand_compliance" in failed_criteria or "brand_vibe" in failed_criteria:
        brand_reason = reasons.get("brand_compliance", "") or reasons.get(
            "brand_vibe", ""
        )
        brand_fix = f"""
[브랜드 톤 수정 필수!]
이전 시도 실패 사유: {brand_reason}

MLB 브랜드 DNA를 정확히 반영:
- 쿨톤 색감 (절대 누런톤 금지)
- 프리미엄하고 세련된 느낌
- 파워풀하고 자신감 있는 분위기
- 깔끔한 배경
"""
        enhanced["_brand_enhancement"] = brand_fix

    # 미감 실패 → 미감 프롬프트만 강화
    if "aesthetic_appeal" in failed_criteria:
        aesthetic_reason = reasons.get("aesthetic_appeal", "")
        aesthetic_fix = f"""
[미감 수정 필수!]
이전 시도 실패 사유: {aesthetic_reason}

패션 매거진 에디토리얼 수준의 아름다움:
- 모델처럼 빛나는 아우라
- 세련되고 고급스러운 무드
- 보는 사람이 '예쁘다' 느끼는 비주얼
- 화보 같은 구도와 조명
"""
        enhanced["_aesthetic_enhancement"] = aesthetic_fix

    # 포즈 실패 → 포즈 프롬프트만 강화
    if "pose_quality" in failed_criteria:
        pose_reason = reasons.get("pose_quality", "")
        pose_fix = f"""
[포즈 수정 필수!]
이전 시도 실패 사유: {pose_reason}

포즈 레퍼런스와 정확히 일치:
- 카메라 앵글 (로우/아이/하이)
- 프레이밍 (전신/무릎/허리)
- 다리 위치와 간격
- 팔 위치
"""
        enhanced["_pose_enhancement"] = pose_fix

    return enhanced


# ============================================================
# Director 기반 프롬프트 빌더 (A급 품질 향상)
# ============================================================


def build_prompt_with_director(
    outfit_analysis: OutfitAnalysis,
    director_json: Optional[dict] = None,
    micro_instructions: Optional[str] = None,
    mood_analysis: Optional[dict] = None,
    user_options: Optional[dict] = None,
) -> dict:
    """
    Director Analysis 기반 프롬프트 빌더 (A급 품질 향상용)

    director_json 또는 micro_instructions가 제공되면
    해당 micro-instruction을 프롬프트에 포함하여 A급 수준 달성.

    Args:
        outfit_analysis: OutfitAnalysis 객체
        director_json: director_analysis JSON (선택, 직접 전달)
        micro_instructions: 미리 변환된 micro-instruction 문자열 (선택)
        mood_analysis: 무드/분위기 분석 결과 (선택)
        user_options: 사용자 추가 옵션

    Returns:
        dict: 프롬프트 JSON (micro_instructions 필드 포함)
    """
    # director_json이 있으면 pose_analysis 형태로 변환
    pose_analysis = None
    if director_json:
        pose_analysis = _director_to_pose_analysis(director_json)

    # 기본 프롬프트 빌드
    prompt_json = build_prompt(
        outfit_analysis=outfit_analysis,
        pose_analysis=pose_analysis,
        mood_analysis=mood_analysis,
        user_options=user_options,
    )

    # micro_instructions가 직접 제공되면 사용, 아니면 director_json에서 생성
    if micro_instructions:
        prompt_json["micro_instructions"] = micro_instructions
    elif director_json:
        from .director_to_prompt import (
            convert_camera_to_prompt,
            convert_pose_to_prompt,
            convert_expression_to_prompt,
            convert_composition_to_prompt,
        )

        micro_parts = []

        camera = director_json.get("camera", {})
        if camera:
            micro_parts.append(convert_camera_to_prompt(camera))

        pose = director_json.get("pose", {})
        if pose:
            micro_parts.append(convert_pose_to_prompt(pose))

        expression = director_json.get("expression", {})
        if expression:
            micro_parts.append(convert_expression_to_prompt(expression))

        composition = director_json.get("composition", {})
        if composition:
            micro_parts.append(convert_composition_to_prompt(composition))

        prompt_json["micro_instructions"] = "\n\n".join(micro_parts)

    # director_json 원본도 저장 (디버깅/검증용)
    if director_json:
        prompt_json["_director_json"] = director_json

    return prompt_json


def _director_to_pose_analysis(director_json: dict) -> dict:
    """director_json을 pose_analysis 형태로 변환 (기존 코드 호환)"""
    camera = director_json.get("camera", {})
    pose = director_json.get("pose", {})
    expression = director_json.get("expression", {})

    # 카메라 높이 → 앵글
    height_cm = camera.get("camera_height_cm", 100)
    if height_cm < 50:
        camera_height = "low angle"
    elif height_cm > 150:
        camera_height = "high angle"
    else:
        camera_height = "eye level"

    # 프레이밍
    composition = director_json.get("composition", {})
    framing = composition.get("framing_type", "MS")

    return {
        "pose": {
            "stance": pose.get("overall_pose_category", "confident_standing"),
            "left_arm": pose.get("left_arm_position", "relaxed at side"),
            "right_arm": pose.get("right_arm_position", "relaxed at side"),
            "torso_rotation": pose.get("torso_rotation_deg", 0),
            "shoulder_tilt": pose.get("shoulder_tilt_deg", 0),
            "energy_level": pose.get("pose_energy_level", 3),
        },
        "expression": {
            "mood": expression.get("overall_expression", "cool"),
            "mouth": expression.get("mouth_state", "closed_neutral"),
            "eyes": f"{expression.get('eye_openness_percent', 80)}% open",
            "intensity": expression.get("expression_intensity", 4),
            "vibe": expression.get("attractiveness_vibe", "mysterious"),
        },
        "camera": {
            "camera_height": camera_height,
            "framing": framing,
            "lens_mm": camera.get("lens_mm", "50"),
            "tilt_deg": camera.get("tilt_deg", 0),
        },
    }


__all__ = [
    "build_prompt",
    "build_prompt_with_director",
    "enhance_prompt_for_retry",
    "MLB_BRAND_DNA",
    "get_random_expression",
    # K-Beauty 표정 프리셋
    "KBEAUTY_EXPRESSION_PRESETS",
    "get_expression_preset",
]
