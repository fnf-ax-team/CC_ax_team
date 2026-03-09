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
from core.outfit_analyzer import OutfitAnalysis
from .korean_prompt_builder import enhance_with_korean_layer


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
    포즈 섹션 빌드 - pose_analysis["pose"]에서 추출

    pose_analysis 구조:
    {
        "pose": {
            "stance": "leaning against car wheel",
            "weight": "on left leg",
            "body_direction": "facing camera at 30 degrees right",
            "left_leg": "bent, knee pointing outward, foot resting on car wheel",
            "right_leg": "straight, extended forward, foot flat on ground",
            "leg_spacing": "wide apart",
            "left_arm": "bent at elbow, hand resting on left thigh",
            "left_hand": "relaxed, fingers slightly curved",
            "right_arm": "relaxed, hanging by side",
            "right_hand": "relaxed",
            "shoulders": "left shoulder slightly higher, relaxed",
            "torso": "leaning back slightly against car",
            "head": "tilted slightly left, facing camera"
        }
    }
    """
    pose = pose_analysis.get("pose", {}) if pose_analysis else {}

    return {
        "stance": pose.get("stance", user_options.get("포즈.stance", "stand")),
        "체중분배": pose.get("weight", "균등"),
        "몸방향": pose.get("body_direction", "정면"),
        "왼팔": pose.get("left_arm", user_options.get("포즈.왼팔", "natural")),
        "오른팔": pose.get("right_arm", user_options.get("포즈.오른팔", "relaxed")),
        "왼손": pose.get("left_hand", user_options.get("포즈.왼손", "relaxed")),
        "오른손": pose.get("right_hand", user_options.get("포즈.오른손", "relaxed")),
        "왼다리": pose.get("left_leg", user_options.get("포즈.왼다리", "support")),
        "오른다리": pose.get("right_leg", user_options.get("포즈.오른다리", "knee_10")),
        "다리간격": pose.get("leg_spacing", "어깨너비"),
        "어깨": pose.get("shoulders", "수평"),
        "상체": pose.get("torso", "똑바로"),
        "머리": pose.get("head", "정면"),
        "힙": pose.get("hip", user_options.get("포즈.힙", "neutral")),
    }


def _build_expression_section(
    pose_analysis: Optional[dict], user_options: dict
) -> dict:
    """
    표정 섹션 빌드 - pose_analysis["expression"]에서 추출

    pose_analysis 구조:
    {
        "expression": {
            "eyes": "large, wide open, confident gaze",
            "eyebrows": "natural, slightly raised",
            "mouth": "closed, neutral, slight pout",
            "mood": "cool, confident, chic"
        }
    }
    """
    expression = pose_analysis.get("expression", {}) if pose_analysis else {}

    # 무드에서 베이스 추출
    mood_raw = expression.get("mood", "")
    if "cool" in mood_raw.lower() or "confident" in mood_raw.lower():
        base = "cool"
    elif "dreamy" in mood_raw.lower():
        base = "dreamy"
    elif "natural" in mood_raw.lower():
        base = "natural"
    elif "serious" in mood_raw.lower():
        base = "serious"
    else:
        base = user_options.get("표정.베이스", "cool")

    # 입 상태 추출
    mouth_raw = expression.get("mouth", "")
    if "open" in mouth_raw.lower() or "parted" in mouth_raw.lower():
        mouth = "parted"
    elif "smile" in mouth_raw.lower():
        mouth = "smile"
    else:
        mouth = "closed"

    # 시선 추출 (eyes에서)
    eyes_raw = expression.get("eyes", "")
    if "direct" in eyes_raw.lower() or "camera" in eyes_raw.lower():
        gaze = "direct"
    elif "past" in eyes_raw.lower() or "away" in eyes_raw.lower():
        gaze = "past"
    else:
        gaze = user_options.get("표정.시선", "direct")

    return {
        "베이스": base,
        "바이브": expression.get("mood", user_options.get("표정.바이브", "mysterious")),
        "시선": gaze,
        "입": mouth,
        "눈": expression.get("eyes", "natural"),
        "눈썹": expression.get("eyebrows", "natural"),
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
        "네거티브": "bright smile, teeth showing, golden hour, warm amber",
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

                item_desc = ", ".join(item_desc_parts)

                # 착장 중첩 구조에 아이템 정보 채우기
                prompt_json["착장"][kor_category]["아이템"] = item_desc

                # 코디방법: 사용자 옵션 > 기본값
                styling_id = user_options.get(
                    f"코디방법.{kor_category}",
                    prompt_json["착장"][kor_category]["코디방법"],
                )
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
