"""
셀피/인플루언서 프롬프트 조립 모듈

치트시트 기반 옵션 매핑 및 프롬프트 빌드 기능 제공
- PROMPT_OPTIONS: 모든 옵션의 ID → 프롬프트 텍스트 매핑
- build_selfie_prompt: 옵션 dict → 최종 프롬프트 문자열
- build_prompt_from_db: DB 프리셋 → 프롬프트 문자열 (v3)
- 금지 조합 검증
"""

from typing import Optional, List, Tuple, Dict


# ============================================================
# 프롬프트 옵션 매핑 (치트시트 기반)
# ============================================================

PROMPT_OPTIONS = {
    # 성별 매핑
    "gender": {
        "female": "예쁜 여자",
        "male": "잘생긴 남자",
    },
    # 촬영 스타일
    "shooting_style": {
        "selfie": "셀카 느낌, 카메라 응시, 손에 폰 없이",
        "mirror": "거울 앞에서 폰 셀카, 거울에 비친 모습",
        "candid": "자연스럽게 찍힌 듯, 누가 찍어준 사진, 폰카 느낌",
    },
    # 거리/구도
    "framing": {
        "close_up": "완전 얼빡, 얼굴 클로즈업",
        "upper_body": "상반신, 허리 위로",
        "full_body": "전신샷, 발끝까지",
        "lying": "누워서 찍은, 침대에 누워서",
        "sitting": "앉아서, 소파에 앉아서",
    },
    # 표정
    "expression": {
        "flirty": "끼부리는 표정",
        "natural": "자연스러운 표정, 대충 찍은 듯",
        "innocent": "청순한 눈빛",
        "chic": "도도한 표정",
        "smiling": "살짝 웃는",
        "sleepy": "졸린 표정, just woke up",
    },
    # 메이크업
    "makeup": {
        "bare": "bare face, no makeup, natural skin texture",
        "natural": "natural makeup, subtle enhancement, minimal foundation",
        "full": "full makeup, perfect skin, defined eyes, contoured face",
    },
    # 착장 - 실내복
    "outfit_indoor": {
        "pajama": "cozy pajama set, loungewear",
        "hoodie": "oversized hoodie, casual comfort",
        "sweatshirt": "crewneck sweatshirt, relaxed fit",
    },
    # 착장 - 데일리
    "outfit_daily": {
        "dress": "casual dress, one-piece",
        "jeans_tee": "jeans and t-shirt, casual denim look",
        "knit": "knit sweater, cozy knitwear",
    },
    # 착장 - 운동복
    "outfit_sports": {
        "gym_wear": "gym wear, sports bra and leggings",
        "tracksuit": "tracksuit, sporty casual",
    },
    # 착장 - 특수
    "outfit_special": {
        "lingerie": "satin slip dress, silk nightwear",
        "swimsuit": "swimsuit, bikini",
    },
    # 장소
    "location": {
        "bedroom": "cozy bedroom, soft bedding",
        "cafe": "cozy cafe interior, coffee shop",
        "car": "inside car, car interior, driver seat",
        "outdoor": "outdoor street, urban background",
        "gym": "gym interior, fitness center",
        "bathroom": "bathroom, bathroom mirror",
        "hotel": "hotel room, luxury hotel interior",
        "club": "nightclub, club lighting",
        "pool": "poolside, swimming pool",
    },
    # 시간대
    "time_of_day": {
        "day": "daylight, natural light",
        "night": "night time, evening lighting",
        "dawn": "early morning, soft dawn light",
    },
    # 조명/무드
    "lighting": {
        "natural_home": "natural indoor lighting, soft daylight from window",
        "flash_dark": "dark room, phone flash reflection in mirror, lens flare burst, low ambient light",
        "ring_light": "ring light catchlight in eyes, even soft lighting, influencer style",
        "golden_hour": "golden hour warm glow, sunset light through window",
        "club_neon": "neon club lighting, colorful ambient, party vibe",
        "bathroom_bright": "bright bathroom lighting, white fluorescent",
        "bedroom_mood": "dim bedroom lighting, mood lighting, cozy warm ambient, soft shadows",
    },
}


# ============================================================
# 금지 조합 테이블
# ============================================================

FORBIDDEN_COMBINATIONS: List[dict] = [
    {
        "rule": "전신 + 얼빡",
        "reason": "물리적 모순",
        "condition": lambda opts: opts.get("framing") == "full_body"
        and "close_up" in str(opts),
        "fix": {"framing": "upper_body"},
    },
    {
        "rule": "거울셀카 + 누워서",
        "reason": "거울 앞에서 눕기 어려움",
        "condition": lambda opts: opts.get("shooting_style") == "mirror"
        and opts.get("framing") == "lying",
        "fix": {"shooting_style": "selfie"},
    },
    {
        "rule": "헬스장 + 파자마",
        "reason": "상황 부적합",
        "condition": lambda opts: opts.get("location") == "gym"
        and opts.get("outfit") == "pajama",
        "fix": {"outfit": "gym_wear"},
    },
    {
        "rule": "수영복 + 카페",
        "reason": "상황 부적합",
        "condition": lambda opts: opts.get("location") == "cafe"
        and opts.get("outfit") == "swimsuit",
        "fix": {"location": "pool"},
    },
    {
        "rule": "남찍 + 거울셀카",
        "reason": "촬영 방식 충돌",
        "condition": lambda opts: opts.get("shooting_style") == "candid"
        and "mirror" in str(opts),
        "fix": {"shooting_style": "candid"},
    },
    # 조명 관련 금지 조합
    {
        "rule": "클럽/네온 + 집/방",
        "reason": "조명-장소 불일치",
        "condition": lambda opts: opts.get("lighting") == "club_neon"
        and opts.get("location") == "bedroom",
        "fix": {"location": "club"},
    },
    {
        "rule": "골든아워 + 욕실",
        "reason": "조명-장소 불일치",
        "condition": lambda opts: opts.get("lighting") == "golden_hour"
        and opts.get("location") == "bathroom",
        "fix": {"lighting": "bathroom_bright"},
    },
    {
        "rule": "플래시 + 야외",
        "reason": "낮에 플래시 부자연스러움",
        "condition": lambda opts: opts.get("lighting") == "flash_dark"
        and opts.get("location") == "outdoor",
        "fix": {"lighting": "natural_home"},
    },
    {
        "rule": "링라이트 + 캔디드",
        "reason": "링라이트는 정면 셀카용",
        "condition": lambda opts: opts.get("lighting") == "ring_light"
        and opts.get("shooting_style") == "candid",
        "fix": {"lighting": "natural_home"},
    },
]


# ============================================================
# 프롬프트 빌드 함수
# ============================================================


def build_selfie_prompt(
    options: dict,
    outfit_analysis: Optional[dict] = None,
) -> str:
    """
    옵션 dict → 최종 한국어 프롬프트 문자열 생성

    Args:
        options: 선택된 옵션들
            - gender: "female" | "male"
            - shooting_style: "selfie" | "mirror" | "candid"
            - framing: "close_up" | "upper_body" | "full_body" | "lying" | "sitting"
            - expression: "flirty" | "natural" | "innocent" | "chic" | "smiling" | "sleepy"
            - makeup: "bare" | "natural" | "full"
            - outfit: 착장 ID 또는 None (outfit_analysis 사용)
            - location: 장소 ID
            - time_of_day: "day" | "night" | "dawn"
        outfit_analysis: VLM 착장 분석 결과 (선택)

    Returns:
        str: 조립된 프롬프트 문자열

    Example:
        >>> options = {
        ...     "gender": "female",
        ...     "shooting_style": "selfie",
        ...     "framing": "close_up",
        ...     "expression": "flirty",
        ...     "location": "bedroom",
        ... }
        >>> prompt = build_selfie_prompt(options)
        >>> print(prompt)
        이 얼굴로 예쁜 여자, 셀카 느낌, 카메라 응시, 손에 폰 없이, 완전 얼빡, 끼부리는 표정, cozy bedroom
    """
    # 금지 조합 검증 및 수정
    options = validate_and_fix_combinations(options)

    parts = ["이 얼굴로"]

    # 1. 성별
    gender = options.get("gender", "female")
    gender_text = PROMPT_OPTIONS["gender"].get(gender, "예쁜 여자")
    parts.append(gender_text)

    # 2. 촬영 스타일
    shooting_style = options.get("shooting_style")
    if shooting_style and shooting_style in PROMPT_OPTIONS["shooting_style"]:
        parts.append(PROMPT_OPTIONS["shooting_style"][shooting_style])

    # 3. 거리/구도
    framing = options.get("framing")
    if framing and framing in PROMPT_OPTIONS["framing"]:
        parts.append(PROMPT_OPTIONS["framing"][framing])

    # 4. 표정
    expression = options.get("expression")
    if expression and expression in PROMPT_OPTIONS["expression"]:
        parts.append(PROMPT_OPTIONS["expression"][expression])

    # 5. 메이크업
    makeup = options.get("makeup")
    if makeup and makeup in PROMPT_OPTIONS["makeup"]:
        parts.append(PROMPT_OPTIONS["makeup"][makeup])

    # 6. 착장 (outfit_analysis 우선, 없으면 옵션에서)
    if outfit_analysis and outfit_analysis.get("prompt_text"):
        parts.append(outfit_analysis["prompt_text"])
    else:
        outfit = options.get("outfit")
        if outfit:
            # 착장 카테고리별 검색
            for category in [
                "outfit_indoor",
                "outfit_daily",
                "outfit_sports",
                "outfit_special",
            ]:
                if outfit in PROMPT_OPTIONS.get(category, {}):
                    parts.append(PROMPT_OPTIONS[category][outfit])
                    break

    # 7. 장소
    location = options.get("location")
    if location and location in PROMPT_OPTIONS["location"]:
        parts.append(PROMPT_OPTIONS["location"][location])

    # 8. 시간대
    time_of_day = options.get("time_of_day")
    if time_of_day and time_of_day in PROMPT_OPTIONS["time_of_day"]:
        parts.append(PROMPT_OPTIONS["time_of_day"][time_of_day])

    # 9. 조명
    lighting = options.get("lighting")
    if lighting and lighting in PROMPT_OPTIONS["lighting"]:
        parts.append(PROMPT_OPTIONS["lighting"][lighting])

    # 프롬프트 조립
    prompt = ", ".join(parts)

    return prompt


def validate_and_fix_combinations(options: dict) -> dict:
    """
    금지 조합 검증 및 자동 수정

    Args:
        options: 옵션 dict

    Returns:
        dict: 수정된 옵션 dict
    """
    options = options.copy()

    for rule in FORBIDDEN_COMBINATIONS:
        try:
            if rule["condition"](options):
                # 금지 조합 감지 시 자동 수정
                for key, value in rule["fix"].items():
                    options[key] = value
                print(f"[PromptBuilder] 금지 조합 수정: {rule['rule']} → {rule['fix']}")
        except Exception:
            # 조건 평가 실패 시 무시
            pass

    return options


def get_negative_prompt(options: dict) -> str:
    """
    네거티브 프롬프트 생성

    Args:
        options: 옵션 dict

    Returns:
        str: 네거티브 프롬프트
    """
    # 기본 네거티브 (항상 적용)
    negatives = ["AI look", "plastic skin", "overprocessed", "golden hour warm cast"]

    # 조건부 추가
    shooting_style = options.get("shooting_style")
    if shooting_style == "selfie":
        negatives.append("professional studio lighting")

    # UGC 스타일이면 완벽함 배제
    if options.get("ugc_style"):
        negatives.extend(["perfect skin", "magazine quality"])

    # 자연스러움 원하면
    if options.get("natural_look"):
        negatives.extend(["posed", "staged", "artificial"])

    return ", ".join(negatives)


def get_available_options() -> dict:
    """
    사용 가능한 모든 옵션 목록 반환 (UI/대화용)

    Returns:
        dict: 카테고리별 옵션 목록
    """
    return {category: list(opts.keys()) for category, opts in PROMPT_OPTIONS.items()}


# ============================================================
# DB 기반 프롬프트 빌더 (v3)
# ============================================================

# 표정 옵션 매핑 (텍스트 기반 - 레거시)
EXPRESSION_OPTIONS = {
    "시크": "도도하고 쿨한 표정, 무표정에 가까운 자신감 있는 눈빛",
    "러블리": "사랑스럽고 부드러운 미소, 청순한 눈빛",
    "자연스러움": "힘 뺀 편안한 표정, 일상적인 느낌",
    "도발적": "끼 있는 표정, 살짝 도발적인 눈빛",
}


def build_expression_text_from_preset(expression_preset: Dict) -> str:
    """
    표정 프리셋으로부터 상세 표정 텍스트 생성

    Args:
        expression_preset: expression_presets.json의 표정 dict

    Returns:
        str: 상세 표정 설명 텍스트
    """
    parts = []

    # 기본 베이스 + 바이브
    base = expression_preset.get("베이스", "natural")
    vibe = expression_preset.get("바이브", "")
    if base:
        parts.append(f"기본 무드: {base}")
    if vibe:
        parts.append(f"분위기: {vibe}")

    # 눈/시선
    eye_desc = expression_preset.get("눈", "")
    gaze = expression_preset.get("시선", "")
    if eye_desc:
        parts.append(f"눈: {eye_desc}")
    if gaze:
        parts.append(f"시선: {gaze}")

    # 입
    mouth = expression_preset.get("입", "")
    if mouth:
        parts.append(f"입: {mouth}")

    # VLM 분석 결과 활용 (있으면)
    vlm = expression_preset.get("vlm_analysis", {})
    if vlm:
        # 눈 상세
        eye_emotion = vlm.get("eye_emotion", "")
        if eye_emotion:
            parts.append(f"눈빛 감정: {eye_emotion}")

        # 입술 상세
        lip_shape = vlm.get("lip_shape", "")
        if lip_shape:
            parts.append(f"입술: {lip_shape}")

        # 얼굴 각도
        face_angle = vlm.get("face_angle", "")
        if face_angle:
            parts.append(f"얼굴 각도: {face_angle}")

        # 특수 특징
        special = vlm.get("special_features", [])
        if special:
            parts.append(f"특징: {', '.join(special)}")

    # 윙크 여부
    if expression_preset.get("is_wink"):
        wink_eye = expression_preset.get("wink_eye", "left")
        eye_kr = "왼쪽" if wink_eye == "left" else "오른쪽"
        parts.append(f"★ {eye_kr} 눈 윙크!")

    return ", ".join(parts) if parts else "자연스러운 표정"


def get_expression_text(expression_input) -> str:
    """
    표정 입력(str 또는 Dict)에서 프롬프트용 텍스트 추출

    Args:
        expression_input: 카테고리 문자열("시크") 또는 프리셋 Dict

    Returns:
        str: 표정 설명 텍스트
    """
    # Dict면 프리셋에서 상세 텍스트 생성
    if isinstance(expression_input, dict):
        return build_expression_text_from_preset(expression_input)

    # str면 기존 매핑 사용
    return EXPRESSION_OPTIONS.get(
        expression_input, EXPRESSION_OPTIONS.get("시크", "자연스러운 표정")
    )


def build_prompt_from_db(
    pose: Dict,
    scene: Dict,
    gender: str = "female",
    expression="시크",  # str 또는 Dict (표정 프리셋)
    makeup: str = "natural",
    outfit_analysis: Optional[Dict] = None,
) -> str:
    """
    DB 프리셋 데이터로 프롬프트 생성 (v3)

    Args:
        pose: pose_presets.json의 포즈 dict
        scene: scene_presets.json의 씬 dict
        gender: "female" | "male"
        expression: 카테고리 문자열("시크") 또는 expression_presets.json의 프리셋 Dict
        makeup: "bare" | "natural" | "full"
        outfit_analysis: VLM 착장 분석 결과 (선택)

    Returns:
        str: 조립된 프롬프트 문자열
    """
    # 성별 텍스트
    gender_text = "예쁜 한국 여자" if gender == "female" else "잘생긴 한국 남자"

    # 표정 텍스트 (str 또는 Dict 둘 다 처리)
    expression_text = get_expression_text(expression)

    # 메이크업 텍스트
    makeup_map = {
        "bare": "노메이크업, 자연스러운 피부 텍스처",
        "natural": "내추럴 메이크업, 은은한 강조",
        "full": "풀 메이크업, 또렷한 눈매",
    }
    makeup_text = makeup_map.get(makeup, makeup_map["natural"])

    # 포즈 텍스트 조립
    pose_parts = []
    pose_stance = pose.get("stance", "stand")
    stance_map = {
        "stand": "서있는 자세",
        "sit": "앉은 자세",
        "walk": "걷는 자세",
        "lean_wall": "구조물에 기댄 자세",
        "lean": "기댄 자세",
        "kneel": "무릎 꿇은 자세",
    }
    pose_parts.append(stance_map.get(pose_stance, pose_stance))

    # 팔/다리 상세 (있으면 추가)
    if pose.get("왼팔"):
        pose_parts.append(f"왼팔: {pose['왼팔']}")
    if pose.get("오른팔"):
        pose_parts.append(f"오른팔: {pose['오른팔']}")
    if pose.get("왼손"):
        pose_parts.append(f"왼손: {pose['왼손']}")
    if pose.get("오른손"):
        pose_parts.append(f"오른손: {pose['오른손']}")
    if pose.get("왼다리") and pose.get("왼다리") != "보이지 않음":
        pose_parts.append(f"왼다리: {pose['왼다리']}")
    if pose.get("오른다리") and pose.get("오른다리") != "보이지 않음":
        pose_parts.append(f"오른다리: {pose['오른다리']}")
    if pose.get("힙") and pose.get("힙") != "보이지 않음":
        pose_parts.append(f"무게중심: {pose['힙']}")

    pose_text = ", ".join(pose_parts)

    # 배경 텍스트 (태그 기반)
    scene_tags = scene.get("tags", [])
    background_text = ", ".join(scene_tags) if scene_tags else "도시 거리"

    # 착장 텍스트
    outfit_text = ""
    if outfit_analysis and outfit_analysis.get("prompt_text"):
        outfit_text = f"\n\n[착장]\n{outfit_analysis['prompt_text']}"

    # 최종 프롬프트 조립
    prompt = f"""이 얼굴로 {gender_text} 인플루언서 사진

[인물]
- 표정: {expression_text}
- 메이크업: {makeup_text}

[포즈]
{pose_text}

[배경]
- 장소: {background_text}
- 분위기: 인스타그램 인플루언서 감성, 자연스러운 일상 셀카{outfit_text}

[스타일 지시]
- 실제 폰카로 찍은 듯한 자연스러운 느낌
- 약간의 결점이 있는 리얼한 피부
- AI처럼 완벽하게 만들지 말 것
- 쿨톤 유지, 누런 톤 금지"""

    return prompt


def build_prompt_from_db_simple(
    pose: Dict,
    scene: Dict,
    gender: str = "female",
    expression="시크",  # str 또는 Dict (표정 프리셋)
) -> str:
    """
    간단한 DB 기반 프롬프트 (레퍼런스 이미지 사용 시)

    레퍼런스 이미지가 있으면 상세 포즈 설명 불필요.

    Args:
        pose: pose_presets.json의 포즈 dict
        scene: scene_presets.json의 씬 dict
        gender: "female" | "male"
        expression: 카테고리 문자열("시크") 또는 expression_presets.json의 프리셋 Dict

    Returns:
        str: 간단한 프롬프트
    """
    gender_text = "예쁜 한국 여자" if gender == "female" else "잘생긴 한국 남자"
    expression_text = get_expression_text(expression)
    scene_tags = scene.get("tags", [])
    background_text = ", ".join(scene_tags[:3]) if scene_tags else "도시"

    prompt = f"""이 얼굴로 {gender_text} 인플루언서 사진

표정: {expression_text}
배경: {background_text}

실제 폰카로 찍은 듯한 자연스러운 느낌
쿨톤 유지, 누런 톤 금지"""

    return prompt


def get_db_based_negative_prompt() -> str:
    """
    DB 기반 생성용 네거티브 프롬프트

    Returns:
        str: 네거티브 프롬프트
    """
    negatives = [
        "AI look",
        "plastic skin",
        "overprocessed",
        "golden hour warm cast",
        "amber tint",
        "perfect skin",
        "magazine quality",
        "professional studio lighting",
        "posed",
        "staged",
    ]
    return ", ".join(negatives)
