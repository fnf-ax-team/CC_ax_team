"""
셀피/인플루언서 프롬프트 조립 모듈

치트시트 기반 옵션 매핑 및 프롬프트 빌드 기능 제공
- PROMPT_OPTIONS: 모든 옵션의 ID → 프롬프트 텍스트 매핑
- build_selfie_prompt: 옵션 dict → 최종 프롬프트 문자열
- 금지 조합 검증
"""

from typing import Optional, List, Tuple


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
