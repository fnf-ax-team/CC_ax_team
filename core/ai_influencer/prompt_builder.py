"""
AI 인플루언서 프롬프트 빌더

스키마 + 프리셋 기반 프롬프트 조립
db/influencer_prompt_schema.json 구조를 따름
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any

from .character import Character
from .presets import load_preset, get_camera_preset_for_pose


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
