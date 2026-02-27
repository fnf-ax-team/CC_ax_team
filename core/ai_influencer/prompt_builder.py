"""
AI 인플루언서 프롬프트 빌더

스키마 + 프리셋 기반 프롬프트 조립
db/influencer_prompt_schema.json 구조를 따름

build_schema_prompt(): 풀 파이프라인용 (VLM 분석 결과 기반)
build_influencer_prompt(): 프리셋 기반 (레거시)
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any, Union

from .character import Character
from .presets import (
    load_preset,
    get_camera_preset_for_pose,
    format_visual_mood_for_prompt,
)


# 스키마 파일 경로
SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "db" / "influencer_prompt_schema.json"
)


def _load_schema() -> Dict:
    """스키마 로드"""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_influencer_prompt(
    character: Character,
    expression_preset: str = None,
    pose_preset: str = None,
    background_preset: str = None,
    styling_preset: str = None,
    outfit_text: str = None,
    outfit_analysis: Dict = None,
    custom_overrides: Dict = None,
) -> Dict[str, Any]:
    """
    AI 인플루언서 프롬프트 스키마 조립 (셀카 스타일 - 간결하게)

    Args:
        character: 캐릭터 객체
        expression_preset: 표정 프리셋 ID (예: "시크_02")
        pose_preset: 포즈 프리셋 ID (예: "전신_05")
        background_preset: 배경 프리셋 ID (예: "핫플카페_08")
        styling_preset: 스타일링 프리셋 ID (선택)
        outfit_text: 착장 텍스트 설명 (선택)
        outfit_analysis: VLM 착장 분석 결과 (선택)
        custom_overrides: 커스텀 오버라이드 값들 (선택)

    Returns:
        스키마 형식의 프롬프트 dict
    """
    schema = _load_schema()
    field_rules = schema.get("field_rules", {})

    # 기본 스키마 구조 복사 (셀카 스타일 - 간결하게)
    prompt_schema = {
        "모델": {},
        "헤어": {},
        "표정": {},
        "포즈": {},
        "배경": {},
        "스타일링": {"아이템": {}, "코디방법": {}},
        "네거티브": "",
    }

    # 1. 모델 정보 (캐릭터에서)
    prompt_schema["모델"] = character.get_model_info()

    # 2. 헤어 기본값
    hair_rules = field_rules.get("헤어", {})
    prompt_schema["헤어"] = {
        "스타일": hair_rules.get("스타일", {}).get("default", "straight_loose"),
        "컬러": hair_rules.get("컬러", {}).get("default", "dark_brown"),
        "질감": hair_rules.get("질감", {}).get("default", "sleek"),
    }

    # 3. 표정 프리셋
    if expression_preset:
        expr_data = load_preset("expression", expression_preset)
        if expr_data:
            prompt_schema["표정"] = {
                "preset_id": expression_preset,
                "베이스": expr_data.get("베이스", "cool"),
                "바이브": expr_data.get("바이브", ""),
                "눈": expr_data.get("눈", "큰 눈"),
                "시선": expr_data.get("시선", "direct"),
                "입": expr_data.get("입", "closed"),
            }
    else:
        # 기본값
        expr_rules = field_rules.get("표정", {})
        prompt_schema["표정"] = {
            "베이스": expr_rules.get("베이스", {}).get("default", "cool"),
            "눈": "큰 눈",  # 고정
            "시선": expr_rules.get("시선", {}).get("default", "direct"),
            "입": expr_rules.get("입", {}).get("default", "closed"),
        }

    # 4. 포즈 프리셋
    if pose_preset:
        pose_data = load_preset("pose", pose_preset)
        if pose_data:
            # vlm_analysis가 있으면 상세 방향 정보 사용
            vlm = pose_data.get("vlm_analysis", {})

            prompt_schema["포즈"] = {
                "preset_id": pose_preset,
                "stance": vlm.get("stance") or pose_data.get("stance", "stand"),
                # vlm_analysis의 상세 정보 우선 사용 (방향 정보 포함)
                "왼팔": vlm.get("left_arm") or pose_data.get("왼팔", ""),
                "오른팔": vlm.get("right_arm") or pose_data.get("오른팔", ""),
                "왼다리": vlm.get("left_leg") or pose_data.get("왼다리", ""),
                "오른다리": vlm.get("right_leg") or pose_data.get("오른다리", ""),
                "힙": vlm.get("hip") or pose_data.get("힙", ""),
                # 방향/기울기 정보 (vlm_analysis에서만 제공)
                "어깨_라인": vlm.get("shoulder_line", ""),
                "얼굴_방향": vlm.get("face_direction", ""),
            }

            # 촬영 세팅도 vlm_analysis에서 추출
            if vlm:
                prompt_schema["촬영_세팅"] = {
                    "프레이밍": vlm.get("framing", ""),
                    "앵글": vlm.get("camera_angle", ""),
                    "높이": vlm.get("camera_height", ""),
                }

    # 5. 배경 프리셋
    if background_preset:
        bg_data = load_preset("background", background_preset)
        if bg_data:
            prompt_schema["배경"] = {
                "preset_id": background_preset,
                "지역": bg_data.get("지역", ""),
                "시간대": bg_data.get("시간대", "주간"),
                "색감": bg_data.get("색감", ""),
                "장소": bg_data.get("장소", ""),
                "분위기": bg_data.get("분위기", ""),
            }

    # 6. 스타일링
    if styling_preset:
        styling_data = load_preset("styling", styling_preset)
        if styling_data:
            prompt_schema["스타일링"] = {
                "preset_id": styling_preset,
                "overall_vibe": styling_data.get("overall_vibe", ""),
                "아이템": styling_data.get("아이템", {}),
                "코디방법": styling_data.get("코디방법", {}),
            }
    elif outfit_analysis:
        # VLM 착장 분석 결과 사용
        prompt_schema["스타일링"]["아이템"] = outfit_analysis.get("아이템", {})
    elif outfit_text:
        # 텍스트 착장 파싱
        prompt_schema["스타일링"]["아이템"] = _parse_outfit_text(outfit_text)

    # 7. 네거티브 (기본 + 조건부)
    prompt_schema["네거티브"] = _build_negative_prompt(prompt_schema, field_rules)

    # 10. 커스텀 오버라이드 적용
    if custom_overrides:
        prompt_schema = _apply_overrides(prompt_schema, custom_overrides)

    return prompt_schema


def _parse_outfit_text(outfit_text: str) -> Dict[str, str]:
    """
    텍스트 착장 설명을 아이템 dict로 파싱

    예: "MLB 화이트 후드티, 청바지" -> {"상의": "MLB 화이트 후드티", "하의": "청바지"}
    """
    items = {}

    # 키워드 기반 간단 파싱
    keywords = {
        "상의": [
            "티셔츠",
            "후드티",
            "탱크탑",
            "셔츠",
            "블라우스",
            "크롭",
            "스웨터",
            "니트",
        ],
        "하의": ["바지", "데님", "청바지", "스커트", "레깅스", "쇼츠", "팬츠"],
        "아우터": ["자켓", "코트", "점퍼", "가디건", "패딩"],
        "신발": ["스니커즈", "운동화", "부츠", "힐", "슬리퍼"],
        "헤드웨어": ["모자", "캡", "볼캡", "비니", "버킷햇"],
    }

    parts = outfit_text.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 키워드 매칭
        matched = False
        for category, kws in keywords.items():
            for kw in kws:
                if kw in part:
                    items[category] = part
                    matched = True
                    break
            if matched:
                break

        # 매칭 안 됐으면 상의로 기본 처리
        if not matched and "상의" not in items:
            items["상의"] = part

    return items


def _build_negative_prompt(prompt_schema: Dict, field_rules: Dict) -> str:
    """네거티브 프롬프트 조립 (셀카 스타일)"""
    neg_rules = field_rules.get("네거티브", {})

    # 기본 네거티브 (AI스러움 배제 추가)
    base_negative = neg_rules.get(
        "default",
        "bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers, AI look, overprocessed",
    )
    negatives = [base_negative]

    # 조건부 추가
    conditional = neg_rules.get("conditional", {})

    # walk 포즈면 static pose 추가
    stance = prompt_schema.get("포즈", {}).get("stance", "")
    if stance == "walk":
        negatives.append(conditional.get("walk_포즈", "static pose, standing still"))

    return ", ".join(negatives)


def _apply_overrides(schema: Dict, overrides: Dict) -> Dict:
    """커스텀 오버라이드 적용 (중첩 dict 지원)"""
    for key, value in overrides.items():
        if isinstance(value, dict) and key in schema and isinstance(schema[key], dict):
            schema[key] = _apply_overrides(schema[key], value)
        else:
            schema[key] = value
    return schema


def schema_to_prompt_text(prompt_schema: Dict, character: Character = None) -> str:
    """
    스키마를 셀카 스타일 간결한 프롬프트로 변환

    Args:
        prompt_schema: 조립된 스키마 dict
        character: 캐릭터 (얼굴 특징 포함용)

    Returns:
        간결한 프롬프트 텍스트 (셀카 스타일)
    """
    # 핵심 요소만 간결하게 조합
    prompt_parts = []

    # 1. 얼굴 동일성 (캐릭터 있으면)
    if character:
        prompt_parts.append(character.get_face_prompt())

    # 2. 모델 기본 (간결하게)
    model = prompt_schema.get("모델", {})
    model_desc = f"{model.get('국적', '한국인')} {model.get('성별', '여성')}"
    prompt_parts.append(model_desc)

    # 3. 표정 (핵심만)
    expr = prompt_schema.get("표정", {})
    if expr:
        expr_desc = []
        if expr.get("베이스"):
            expr_desc.append(expr["베이스"])
        if expr.get("바이브"):
            expr_desc.append(expr["바이브"])
        if expr_desc:
            prompt_parts.append(" ".join(expr_desc) + " expression")

    # 4. 포즈 (상세하게 - 방향 정보 포함)
    pose = prompt_schema.get("포즈", {})
    if pose:
        pose_lines = []

        # stance
        if pose.get("stance"):
            pose_lines.append(f"stance: {pose['stance']}")

        # 팔 (상세 정보 포함)
        if pose.get("왼팔"):
            pose_lines.append(f"왼팔: {pose['왼팔']}")
        if pose.get("오른팔"):
            pose_lines.append(f"오른팔: {pose['오른팔']}")

        # 다리 (방향 정보 포함 - 핵심!)
        if pose.get("왼다리"):
            pose_lines.append(f"왼다리: {pose['왼다리']}")
        if pose.get("오른다리"):
            pose_lines.append(f"오른다리: {pose['오른다리']}")

        # 힙
        if pose.get("힙"):
            pose_lines.append(f"힙: {pose['힙']}")

        # 방향/기울기
        if pose.get("어깨_라인"):
            pose_lines.append(f"어깨_라인: {pose['어깨_라인']}")
        if pose.get("얼굴_방향"):
            pose_lines.append(f"얼굴_방향: {pose['얼굴_방향']}")

        if pose_lines:
            prompt_parts.append("\n[포즈]\n" + "\n".join(pose_lines))

    # 4.5 촬영 세팅 (vlm_analysis에서 추출)
    camera = prompt_schema.get("촬영_세팅", {})
    if camera and any(camera.values()):
        camera_lines = []
        if camera.get("프레이밍"):
            camera_lines.append(f"프레이밍: {camera['프레이밍']}")
        if camera.get("앵글"):
            camera_lines.append(f"앵글: {camera['앵글']}")
        if camera.get("높이"):
            camera_lines.append(f"높이: {camera['높이']}")
        if camera_lines:
            prompt_parts.append("\n[촬영]\n" + "\n".join(camera_lines))

    # 5. 착장 (아이템 나열)
    styling = prompt_schema.get("스타일링", {})
    if styling:
        items = styling.get("아이템", {})
        outfit_parts = []
        for key in ["헤드웨어", "상의", "하의", "신발"]:
            if items.get(key):
                outfit_parts.append(items[key])
        if outfit_parts:
            prompt_parts.append("wearing " + ", ".join(outfit_parts))

    # 6. 배경 (간결하게)
    bg = prompt_schema.get("배경", {})
    if bg:
        bg_desc = bg.get("장소", "") or bg.get("분위기", "")
        if bg_desc:
            prompt_parts.append(bg_desc)

    # 최종 조합 (쉼표로 연결, 셀카 스타일)
    main_prompt = ", ".join(prompt_parts)

    # 네거티브 추가
    negative = prompt_schema.get("네거티브", "")
    if negative:
        return f"{main_prompt}\n\nNegative: {negative}"

    return main_prompt


# ============================================================
# 풀 파이프라인용 스키마 프롬프트 빌더
# ============================================================

# state → 한국어 코디방법 매핑 (VLM이 반환하는 state 값 기반)
_STATE_TO_KOREAN = {
    "open": "지퍼 오픈",
    "draped": "어깨에 걸침",
    "one_arm": "한쪽 팔만 소매에 넣고 착용",
    "held": "손에 들고",
    "off_shoulder": "한쪽 어깨 흘러내림",
    "tucked": "넣어입기",
    "rolled": "밑단 롤업",
    "backwards": "뒤로 쓰기",
    "cropped": "크롭, 배꼽 노출",
    "loose_socks": "루즈삭스 함께",
    "crossbody_front": "크로스바디 앞으로",
    "crossbody_side": "크로스바디 옆으로",
    "layered": "레이어드 여러개",
}


def _build_styling_method_section(items) -> list:
    """
    착장 아이템의 state를 한국어 코디방법으로 변환

    state가 "normal"이면 생략 (불필요한 정보 배제)
    """
    lines = []
    for item in items:
        state = getattr(item, "state", "normal") or "normal"
        if state.lower() == "normal":
            continue
        korean = _STATE_TO_KOREAN.get(state.lower(), state)
        lines.append(f"- {item.category}: {korean}")
    return lines


def _select_visual_mood(background_result, pose_result) -> str:
    """
    배경/포즈 분석 결과 기반 비주얼 무드 프리셋 자동 선택

    Returns:
        비주얼 무드 프리셋 ID
    """
    scene = background_result.scene_type.lower()
    time = background_result.time_of_day

    # 실내 스튜디오 → STUDIO_EDITORIAL_001
    if "studio" in scene or "스튜디오" in scene:
        return "STUDIO_EDITORIAL_001"

    # 야간/플래시 → SUMMER_003 (Y2K flash)
    if time in ["야간", "night"]:
        return "SUMMER_003"

    # 카페/실내 → SPRING_006 (cozy cafe, indoor natural + artificial mix)
    if any(kw in scene for kw in ["cafe", "카페", "indoor", "실내"]) or time == "실내":
        return "SPRING_006"

    # 기본 (야외/주간) → OUTDOOR_CASUAL_001
    return "OUTDOOR_CASUAL_001"


def _detect_leg_lifted(pose_result) -> tuple:
    """특이 포즈 감지 (다리 들기)

    bent_leg_shape 필드가 있으면 우선 사용 (VLM이 직접 판단).
    없으면 키워드 기반 폴백.
    """
    leg_shape = getattr(pose_result, "bent_leg_shape", "")

    # bent_leg_shape가 있으면 이것으로 판단 (VLM이 4자/L자 직접 판별)
    if leg_shape and leg_shape != "직립":
        # 어느 쪽 다리가 구부러져 있는지 무릎 각도로 판별
        left_angle = getattr(pose_result, "left_knee_angle", "")
        right_angle = getattr(pose_result, "right_knee_angle", "")

        # 각도가 작을수록 구부러진 다리
        left_bent = (
            any(kw in left_angle for kw in ["45", "60", "80", "90", "접힘", "직각"])
            if left_angle
            else False
        )
        right_bent = (
            any(kw in right_angle for kw in ["45", "60", "80", "90", "접힘", "직각"])
            if right_angle
            else False
        )

        # 각도로 못 찾으면 다리 설명 텍스트에서 찾기
        if not left_bent and not right_bent:
            _bent_kws = ["구부", "접어", "올림", "들어올", "들어 올", "접힘"]
            left_bent = any(kw in pose_result.left_leg for kw in _bent_kws)
            right_bent = any(kw in pose_result.right_leg for kw in _bent_kws)

        return left_bent, right_bent

    # 폴백: 키워드 기반 감지 (확장된 키워드)
    _bent_kws = [
        "들어올",
        "들어 올",
        "구부",
        "접어",
        "올림",
        "45도",
        "60도",
        "80도",
        "90도",
        "배꼽 높이",
    ]
    left_leg_lifted = any(kw in pose_result.left_leg for kw in _bent_kws)
    right_leg_lifted = any(kw in pose_result.right_leg for kw in _bent_kws)
    return left_leg_lifted, right_leg_lifted


def _is_figure4(pose_result) -> bool:
    """4자 다리 포즈인지 확인"""
    return getattr(pose_result, "bent_leg_shape", "") == "4자"


def _build_unusual_pose_warning(pose_result, left_leg_lifted, right_leg_lifted) -> list:
    """특이 포즈 경고 라인 생성 (4자/L자 구분 포함)"""
    lines = []
    is_fig4 = _is_figure4(pose_result)

    warnings = []
    if left_leg_lifted:
        warnings.append(f"* LEFT LEG BENT: {pose_result.left_leg}")
    if right_leg_lifted:
        warnings.append(f"* RIGHT LEG BENT: {pose_result.right_leg}")

    if warnings:
        lines.append("### *** CRITICAL POSE WARNING ***")
        lines.extend(warnings)
        lines.append("")

        if is_fig4:
            # 4자 다리 전용 강제 지시
            lines.append("*** FIGURE-4 LEG SHAPE (4자 다리) ***")
            lines.append('The bent leg forms a NUMBER "4" shape:')
            lines.append("- Knee points SIDEWAYS / LATERALLY (to the SIDE of the body)")
            lines.append(
                "- Foot is pressed against the inner calf/thigh of the standing leg, or tucked BEHIND it"
            )
            lines.append(
                "- The thigh of the bent leg opens OUTWARD, creating a triangular gap between legs"
            )
            lines.append("")
            lines.append("*** DO NOT ***:")
            lines.append(
                "- DO NOT lift the knee FORWARD or UPWARD (that is L-shape, WRONG!)"
            )
            lines.append("- DO NOT have the foot dangling in front")
            lines.append("- DO NOT make a flamingo with knee pointing forward")
            lines.append("")
            lines.append(
                "Think: like crossing legs while standing, or resting sole of foot against inner calf"
            )
            lines.append("")
        else:
            # L자 또는 일반
            lines.append(
                "This is an UNUSUAL pose. DO NOT default to normal standing pose!"
            )
            lines.append("The model MUST have ONE LEG LIFTED as specified above.")
            lines.append("")

    return lines


def _build_pose_section_a(pose_result, background_result) -> tuple:
    """
    Variant A: Baseline (현재 그대로)

    문장형 팔 설명 + 문장형 다리 설명 + 별도 방향/기울기 서브섹션.
    Returns: (lines, left_leg_lifted, right_leg_lifted)
    """
    lines = []
    lines.append("## [포즈] *** MUST FOLLOW EXACTLY - DO NOT SIMPLIFY ***")
    lines.append(f"- stance: {pose_result.stance}")
    lines.append(f"- 왼팔: {pose_result.left_arm}")
    lines.append(f"- 오른팔: {pose_result.right_arm}")
    lines.append(f"- 왼손: {pose_result.left_hand}")
    lines.append(f"- 오른손: {pose_result.right_hand}")
    lines.append(f"- 왼다리: {pose_result.left_leg}")
    lines.append(f"- 오른다리: {pose_result.right_leg}")
    lines.append(f"- 힙: {pose_result.hip}")
    lines.append("")

    # 특이 포즈 감지
    left_leg_lifted, right_leg_lifted = _detect_leg_lifted(pose_result)
    lines.extend(
        _build_unusual_pose_warning(pose_result, left_leg_lifted, right_leg_lifted)
    )

    # 방향/기울기
    lines.append("### [방향/기울기] *** CRITICAL - EXACT DIRECTION ***")
    if pose_result.torso_tilt:
        lines.append(f"- 상체_기울기: {pose_result.torso_tilt}")

    if pose_result.left_knee_direction:
        lines.append(f"- 왼무릎_방향: {pose_result.left_knee_direction}")
    if pose_result.right_knee_direction:
        lines.append(f"- 오른무릎_방향: {pose_result.right_knee_direction}")

    if pose_result.left_foot_direction:
        lines.append(f"- 왼발_방향: {pose_result.left_foot_direction}")
    if pose_result.right_foot_direction:
        lines.append(f"- 오른발_방향: {pose_result.right_foot_direction}")

    if pose_result.left_knee_angle:
        lines.append(f"- 왼무릎_각도: {pose_result.left_knee_angle}")
    if pose_result.right_knee_angle:
        lines.append(f"- 오른무릎_각도: {pose_result.right_knee_angle}")
    if pose_result.left_knee_height:
        lines.append(f"- 왼무릎_높이: {pose_result.left_knee_height}")
    if pose_result.right_knee_height:
        lines.append(f"- 오른무릎_높이: {pose_result.right_knee_height}")
    if pose_result.left_foot_position:
        lines.append(f"- 왼발_위치: {pose_result.left_foot_position}")
    if pose_result.right_foot_position:
        lines.append(f"- 오른발_위치: {pose_result.right_foot_position}")

    if pose_result.shoulder_line:
        lines.append(f"- 어깨_라인: {pose_result.shoulder_line}")
    if pose_result.face_direction:
        lines.append(f"- 얼굴_방향: {pose_result.face_direction}")
    if pose_result.neck_tilt:
        lines.append(f"- 목_기울기: {pose_result.neck_tilt}")
    if pose_result.head_tilt:
        lines.append(f"- 고개_각도: {pose_result.head_tilt}")
    if pose_result.left_elbow_angle:
        lines.append(f"- 왼팔꿈치_각도: {pose_result.left_elbow_angle}")
    if pose_result.right_elbow_angle:
        lines.append(f"- 오른팔꿈치_각도: {pose_result.right_elbow_angle}")
    if pose_result.left_elbow_direction:
        lines.append(f"- 왼팔꿈치_방향: {pose_result.left_elbow_direction}")
    if pose_result.right_elbow_direction:
        lines.append(f"- 오른팔꿈치_방향: {pose_result.right_elbow_direction}")
    lines.append("")

    # sit 포즈일 때 앉는 위치 명시
    if pose_result.stance == "sit" and background_result.sit_on:
        lines.append(f"- 앉는_위치: {background_result.sit_on}")
        lines.append("")
        lines.append("*** IMPORTANT: 배경에 이미 있는 위치에 앉으세요! ***")
        lines.append(
            "새로운 의자/물체를 만들지 마세요. 배경 레퍼런스에 보이는 곳에 앉으세요."
        )
        lines.append("")

    return lines, left_leg_lifted, right_leg_lifted


def _build_pose_section_b(pose_result) -> tuple:
    """
    Variant B: Structured (서브필드 분리)

    문장형 제거. 모든 정보를 키-값 서브필드로 분리. 다리 중복 제거.
    Returns: (lines, left_leg_lifted, right_leg_lifted)
    """
    lines = []
    lines.append("## [포즈] *** MUST FOLLOW EXACTLY - DO NOT SIMPLIFY ***")
    lines.append(f"- stance: {pose_result.stance}")
    lines.append("")

    # 왼팔 (서브필드 분리)
    lines.append("### 왼팔:")
    if pose_result.left_arm:
        lines.append(f"  - 설명: {pose_result.left_arm}")
    if pose_result.left_elbow_angle:
        lines.append(f"  - 팔꿈치_각도: {pose_result.left_elbow_angle}")
    if pose_result.left_elbow_direction:
        lines.append(f"  - 팔꿈치_방향: {pose_result.left_elbow_direction}")
    lines.append("")

    # 왼손
    lines.append("### 왼손:")
    if pose_result.left_hand:
        lines.append(f"  - 동작: {pose_result.left_hand}")
    lines.append("")

    # 오른팔 (서브필드 분리)
    lines.append("### 오른팔:")
    if pose_result.right_arm:
        lines.append(f"  - 설명: {pose_result.right_arm}")
    if pose_result.right_elbow_angle:
        lines.append(f"  - 팔꿈치_각도: {pose_result.right_elbow_angle}")
    if pose_result.right_elbow_direction:
        lines.append(f"  - 팔꿈치_방향: {pose_result.right_elbow_direction}")
    lines.append("")

    # 오른손
    lines.append("### 오른손:")
    if pose_result.right_hand:
        lines.append(f"  - 동작: {pose_result.right_hand}")
    lines.append("")

    # 왼다리 (서브필드만, 문장형 제거)
    lines.append("### 왼다리:")
    if pose_result.left_knee_angle:
        lines.append(f"  - 무릎_각도: {pose_result.left_knee_angle}")
    if pose_result.left_knee_direction:
        lines.append(f"  - 무릎_방향: {pose_result.left_knee_direction}")
    if pose_result.left_knee_height:
        lines.append(f"  - 무릎_높이: {pose_result.left_knee_height}")
    if pose_result.left_foot_direction:
        lines.append(f"  - 발_방향: {pose_result.left_foot_direction}")
    if pose_result.left_foot_position:
        lines.append(f"  - 발_위치: {pose_result.left_foot_position}")
    lines.append("")

    # 오른다리 (서브필드만, 문장형 제거)
    lines.append("### 오른다리:")
    if pose_result.right_knee_angle:
        lines.append(f"  - 무릎_각도: {pose_result.right_knee_angle}")
    if pose_result.right_knee_direction:
        lines.append(f"  - 무릎_방향: {pose_result.right_knee_direction}")
    if pose_result.right_knee_height:
        lines.append(f"  - 무릎_높이: {pose_result.right_knee_height}")
    if pose_result.right_foot_direction:
        lines.append(f"  - 발_방향: {pose_result.right_foot_direction}")
    if pose_result.right_foot_position:
        lines.append(f"  - 발_위치: {pose_result.right_foot_position}")
    lines.append("")

    # 체중/방향
    lines.append("### 체중/방향:")
    if pose_result.hip:
        lines.append(f"  - 무게중심: {pose_result.hip}")
    if pose_result.torso_tilt:
        lines.append(f"  - 상체_기울기: {pose_result.torso_tilt}")
    if pose_result.shoulder_line:
        lines.append(f"  - 어깨: {pose_result.shoulder_line}")
    if pose_result.face_direction:
        lines.append(f"  - 얼굴: {pose_result.face_direction}")
    if pose_result.neck_tilt:
        lines.append(f"  - 목_기울기: {pose_result.neck_tilt}")
    if pose_result.head_tilt:
        lines.append(f"  - 고개_각도: {pose_result.head_tilt}")
    lines.append("")

    # 특이 포즈 감지
    left_leg_lifted, right_leg_lifted = _detect_leg_lifted(pose_result)
    lines.extend(
        _build_unusual_pose_warning(pose_result, left_leg_lifted, right_leg_lifted)
    )

    return lines, left_leg_lifted, right_leg_lifted


def _build_pose_section_c(pose_result) -> tuple:
    """
    Variant C: Flat key-value (플랫 하이브리드)

    계층 없이 플랫하게. 한 줄에 하나의 정보만.
    Returns: (lines, left_leg_lifted, right_leg_lifted)
    """
    lines = []
    lines.append("## [포즈] *** MUST FOLLOW EXACTLY - DO NOT SIMPLIFY ***")
    lines.append(f"- stance: {pose_result.stance}")

    # 팔 (플랫 키-값)
    if pose_result.left_arm:
        lines.append(f"- 왼팔_설명: {pose_result.left_arm}")
    if pose_result.left_elbow_angle:
        lines.append(f"- 왼팔꿈치_각도: {pose_result.left_elbow_angle}")
    if pose_result.left_elbow_direction:
        lines.append(f"- 왼팔꿈치_방향: {pose_result.left_elbow_direction}")
    if pose_result.left_hand:
        lines.append(f"- 왼손: {pose_result.left_hand}")
    if pose_result.right_arm:
        lines.append(f"- 오른팔_설명: {pose_result.right_arm}")
    if pose_result.right_elbow_angle:
        lines.append(f"- 오른팔꿈치_각도: {pose_result.right_elbow_angle}")
    if pose_result.right_elbow_direction:
        lines.append(f"- 오른팔꿈치_방향: {pose_result.right_elbow_direction}")
    if pose_result.right_hand:
        lines.append(f"- 오른손: {pose_result.right_hand}")

    # 왼다리 (플랫 키-값, 문장형 제거)
    if pose_result.left_knee_angle:
        lines.append(f"- 왼다리_무릎각도: {pose_result.left_knee_angle}")
    if pose_result.left_knee_direction:
        lines.append(f"- 왼다리_무릎방향: {pose_result.left_knee_direction}")
    if pose_result.left_knee_height:
        lines.append(f"- 왼다리_무릎높이: {pose_result.left_knee_height}")
    if pose_result.left_foot_direction:
        lines.append(f"- 왼다리_발방향: {pose_result.left_foot_direction}")
    if pose_result.left_foot_position:
        lines.append(f"- 왼다리_발위치: {pose_result.left_foot_position}")

    # 오른다리 (플랫 키-값, 문장형 제거)
    if pose_result.right_knee_angle:
        lines.append(f"- 오른다리_무릎각도: {pose_result.right_knee_angle}")
    if pose_result.right_knee_direction:
        lines.append(f"- 오른다리_무릎방향: {pose_result.right_knee_direction}")
    if pose_result.right_knee_height:
        lines.append(f"- 오른다리_무릎높이: {pose_result.right_knee_height}")
    if pose_result.right_foot_direction:
        lines.append(f"- 오른다리_발방향: {pose_result.right_foot_direction}")
    if pose_result.right_foot_position:
        lines.append(f"- 오른다리_발위치: {pose_result.right_foot_position}")

    # 체중/방향 (플랫)
    if pose_result.hip:
        lines.append(f"- 무게중심: {pose_result.hip}")
    if pose_result.torso_tilt:
        lines.append(f"- 상체기울기: {pose_result.torso_tilt}")
    if pose_result.shoulder_line:
        lines.append(f"- 어깨라인: {pose_result.shoulder_line}")
    if pose_result.face_direction:
        lines.append(f"- 얼굴방향: {pose_result.face_direction}")
    if pose_result.neck_tilt:
        lines.append(f"- 목기울기: {pose_result.neck_tilt}")
    if pose_result.head_tilt:
        lines.append(f"- 고개각도: {pose_result.head_tilt}")
    lines.append("")

    # 특이 포즈 감지
    left_leg_lifted, right_leg_lifted = _detect_leg_lifted(pose_result)
    lines.extend(
        _build_unusual_pose_warning(pose_result, left_leg_lifted, right_leg_lifted)
    )

    return lines, left_leg_lifted, right_leg_lifted


# 프레이밍 코드 → 설명 매핑
_FRAMING_DESCRIPTIONS = {
    "ECU": "Extreme Close-Up: eyes/lips only",
    "CU": "Close-Up: face and neck only, shoulders barely visible",
    "MCU": "Medium Close-Up: head to chest, cut at mid-chest",
    "MS": "Medium Shot: head to waist, cut at waist/belt line",
    "MFS": "Medium Full Shot: head to knees, cut at knee to mid-thigh. Feet NOT visible",
    "FS": "Full Shot: entire body from head to toe, feet fully visible on ground",
    "WS": "Wide Shot: full body plus surrounding environment",
}

# 프레이밍별 네거티브 프롬프트 (다른 프레이밍 금지)
_FRAMING_NEGATIVES = {
    "CU": ["full body visible", "legs visible", "waist visible"],
    "MCU": ["full body visible", "legs visible", "below waist visible"],
    "MS": ["full body visible", "feet visible", "legs below knee visible"],
    "MFS": [
        "feet visible",
        "shoes fully visible on ground",
        "full body head to toe",
        "ankles visible",
    ],
    "FS": ["cropped at waist", "cropped at knee", "legs cut off"],
    "WS": ["tight crop", "cropped body"],
}


def _get_framing_description(framing: str) -> str:
    """프레이밍 코드를 설명 텍스트로 변환"""
    return _FRAMING_DESCRIPTIONS.get(framing.upper(), framing)


def build_schema_prompt(
    hair_result,
    expression_result,
    pose_result,
    background_result,
    outfit_result,
    compatibility_result=None,
    model_info: Dict = None,
    pose_format: str = "A",
) -> str:
    """
    풀 파이프라인용 스키마 기반 프롬프트 생성

    모든 VLM 분석 결과를 텍스트로 포함하여
    이미지 레퍼런스와 함께 API에 전송할 프롬프트를 조립한다.

    Args:
        hair_result: HairAnalysisResult 또는 dict (헤어 분석 결과)
        expression_result: ExpressionAnalysisResult 또는 dict (표정 분석 결과)
        pose_result: PoseAnalysisResult (포즈 분석 결과)
        background_result: BackgroundAnalysisResult (배경 분석 결과)
        outfit_result: OutfitAnalysisResult (착장 분석 결과)
        compatibility_result: CompatibilityResult (호환성 검사 결과, 선택)
        model_info: 모델 정보 dict (선택). 예: {"국적": "한국인", "성별": "여성", "나이": "20대 초반"}
        pose_format: 포즈 프롬프트 포맷 ("A"=baseline, "B"=structured, "C"=flat)

    Returns:
        str: 스키마 프롬프트 텍스트
    """
    # hair_result가 dict인 경우 호환 (레거시)
    if isinstance(hair_result, dict):
        hair_dict = hair_result
    else:
        hair_dict = hair_result.to_schema_format()

    # expression_result가 dict인 경우 호환 (레거시)
    if isinstance(expression_result, dict):
        expr_dict = expression_result
    else:
        expr_dict = expression_result.to_schema_format()

    lines = []

    # 기본 설정
    lines.append("# AI Influencer Image Generation")
    lines.append("")
    lines.append("Generate a fashion editorial photo following this schema EXACTLY.")
    lines.append("")

    # =====================================================
    # 모델 정보
    # =====================================================
    _model = model_info or {}
    lines.append("## [모델]")
    lines.append(f"- 국적: {_model.get('국적', '한국인')}")
    lines.append(f"- 성별: {_model.get('성별', '여성')}")
    lines.append(f"- 나이: {_model.get('나이', '20대 초반')}")
    lines.append("")

    # =====================================================
    # 헤어 (CRITICAL - 변경 금지)
    # =====================================================
    lines.append("## [헤어] *** CRITICAL - DO NOT CHANGE ***")
    lines.append(f"- 스타일: {hair_dict.get('스타일', 'straight_loose')}")
    lines.append(f"- 컬러: {hair_dict.get('컬러', 'dark_brown')}")
    lines.append(f"- 질감: {hair_dict.get('질감', 'sleek')}")
    lines.append("")
    lines.append("IMPORTANT: 헤어 컬러와 스타일은 위에 명시된 대로 유지!")
    lines.append("다른 레퍼런스 이미지의 헤어를 복사하지 마세요!")
    lines.append("")

    # =====================================================
    # 표정
    # =====================================================
    lines.append("## [표정]")

    # ExpressionAnalysisResult (상세 버전) 감지
    if hasattr(expression_result, "to_prompt_text"):
        # 상세 버전 - prompt_text 사용
        lines.append(expression_result.to_prompt_text())
    else:
        # dict (간단 버전) - 호환
        lines.append(f"- 베이스: {expr_dict.get('베이스', 'cool')}")
        lines.append(f"- 바이브: {expr_dict.get('바이브', 'effortless')}")
        lines.append("- 눈: 큰 눈")
        lines.append(f"- 시선: {expr_dict.get('시선', 'direct')}")
        lines.append(f"- 입: {expr_dict.get('입', 'closed')}")
    lines.append("")

    # =====================================================
    # 포즈 (pose_format에 따라 A/B/C 분기)
    # =====================================================
    if pose_format == "B":
        pose_lines, left_leg_lifted, right_leg_lifted = _build_pose_section_b(
            pose_result
        )
    elif pose_format == "C":
        pose_lines, left_leg_lifted, right_leg_lifted = _build_pose_section_c(
            pose_result
        )
    else:
        pose_lines, left_leg_lifted, right_leg_lifted = _build_pose_section_a(
            pose_result, background_result
        )
    lines.extend(pose_lines)

    # =====================================================
    # 촬영 세팅 (프레이밍 강제)
    # =====================================================
    framing = pose_result.framing or "MFS"
    framing_desc = _get_framing_description(framing)
    lines.append("## [촬영_세팅] *** FRAMING IS CRITICAL ***")
    lines.append(f"- 프레이밍: {framing} ({framing_desc})")
    lines.append(f"  *** YOU MUST crop the image at {framing} level! ***")
    lines.append("- 렌즈: 50mm")
    lines.append(f"- 앵글: {pose_result.camera_angle}")
    lines.append(f"- 높이: {pose_result.camera_height}")
    lines.append("- 구도: 중앙")
    lines.append("- 조리개: f/2.8")
    lines.append("")

    # =====================================================
    # 배경
    # =====================================================
    lines.append("## [배경]")
    lines.append(f"- 지역: {background_result.region}")
    lines.append(f"- 시간대: {background_result.time_of_day}")
    lines.append(f"- 색감: {background_result.color_tone}")
    lines.append(f"- 장소: {background_result.scene_type}")
    lines.append(f"- 분위기: {background_result.mood}")
    lines.append("- 인물제외: 배경에 다른 사람 없음. 주인공 한 명만 등장.")
    lines.append("")

    # 호환성 경고
    if compatibility_result and not compatibility_result.is_compatible():
        lines.append("## [COMPATIBILITY WARNING]")
        for issue in compatibility_result.issues:
            lines.append(f"- {issue.description}")
        lines.append("")

    # =====================================================
    # 스타일링 (착장)
    # =====================================================
    lines.append("## [스타일링] - Match EXACTLY")
    lines.append(f"- overall_vibe: {outfit_result.overall_style}")
    lines.append("")
    lines.append("### 아이템:")
    for item in outfit_result.items:
        lines.append(f"- {item.category}: {item.name}")
        lines.append(f"  - 색상: {item.color}")
        lines.append(f"  - 핏: {item.fit}")
        if item.logos:
            for logo in item.logos:
                lines.append(f"  - 로고: {logo.brand} ({logo.type}) at {logo.position}")
        if item.details:
            lines.append(f"  - 디테일: {', '.join(item.details)}")
    lines.append("")

    # 코디방법 (state → 한국어 착용법)
    styling_lines = _build_styling_method_section(outfit_result.items)
    if styling_lines:
        lines.append("### 코디방법:")
        lines.extend(styling_lines)
        lines.append("")

    # =====================================================
    # 비주얼 무드 (배경 분석 기반 자동 선택)
    # =====================================================
    visual_mood_id = _select_visual_mood(background_result, pose_result)
    visual_mood_lines = format_visual_mood_for_prompt(visual_mood_id)
    lines.extend(visual_mood_lines)

    # =====================================================
    # 네거티브 (동적 추가 - 풀 스키마 조건부)
    # =====================================================
    lines.append("## [네거티브]")
    base_negative = "other people, crowd, bystanders, passersby, multiple people, random chair, random box, invented furniture, objects not in background reference, bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers, AI look, overprocessed"

    extra_negative = []

    # 조건부 1: 특이 포즈 (다리 들기)
    if left_leg_lifted or right_leg_lifted:
        extra_negative.append("both feet on ground")
        extra_negative.append("standing with both legs")
        extra_negative.append("flat-footed stance")
        extra_negative.append("symmetrical leg position")

        # 4자 다리일 때 L자 포즈 명시적 금지
        if _is_figure4(pose_result):
            extra_negative.append("knee pointing forward")
            extra_negative.append("knee lifted upward")
            extra_negative.append("L-shaped leg")
            extra_negative.append("foot dangling in front")

    # 조건부 2: 프레이밍별 네거티브 (프레이밍 강제)
    if pose_result.framing:
        framing_negs = _FRAMING_NEGATIVES.get(pose_result.framing.upper(), [])
        extra_negative.extend(framing_negs)

    # 조건부 3: walk 포즈 → static pose 금지
    if pose_result.stance == "walk":
        extra_negative.append("static pose")
        extra_negative.append("standing still")

    # 조건부 4: sit 포즈 → standing pose 금지
    if pose_result.stance == "sit":
        extra_negative.append("standing pose")
        extra_negative.append("both feet on ground")

    # 조건부 5: 차량 배경 → grille/license plate 금지
    scene_lower = background_result.scene_type.lower()
    if any(kw in scene_lower for kw in ["car", "vehicle", "차량", "자동차", "parking"]):
        extra_negative.append("front grille visible")
        extra_negative.append("license plate")

    if extra_negative:
        full_negative = base_negative + ", " + ", ".join(extra_negative)
    else:
        full_negative = base_negative

    lines.append(full_negative)
    lines.append("")

    # =====================================================
    # 이미지 역할 안내 (항상 모든 레퍼런스 포함)
    # =====================================================
    lines.append("=" * 50)
    lines.append("## [IMAGE REFERENCE ROLES]")
    lines.append("")
    lines.append("[FACE] images: Use this person's face identity")
    lines.append("  - KEEP hair color/style as specified in [헤어] section!")
    lines.append("")
    lines.append("[OUTFIT] images: Match outfit EXACTLY")
    lines.append("  - Copy all colors, logos, patterns, details")
    lines.append("")
    lines.append("[POSE REFERENCE]: Copy pose AND framing from this image")
    lines.append("  - Match body position EXACTLY")
    lines.append(f"  - Match framing EXACTLY: {framing} ({framing_desc})")
    lines.append("  - Ignore face/outfit/background from this image")
    lines.append("")
    lines.append("[EXPRESSION REFERENCE]: Copy expression only")
    lines.append("  - Copy eyes, mouth, facial expression")
    lines.append("  - DO NOT copy hair from this image!")
    lines.append("")
    lines.append("[BACKGROUND REFERENCE]: Use this background")
    lines.append("  - Ignore any person in background image")
    lines.append("  - Match lighting/mood of background")
    lines.append("")

    return "\n".join(lines)
