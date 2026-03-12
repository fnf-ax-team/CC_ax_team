"""
포즈-배경 호환성 검사 모듈
VFX 분석 결과의 pose_dependency를 기반으로 배경 호환성 검증
"""

from typing import Dict, Any, List, Tuple

# 포즈별 필수 배경 요소 매칭 테이블
POSE_BACKGROUND_REQUIREMENTS = {
    "sitting": {
        "required_elements": ["bench", "stairs", "steps", "chair", "stool", "ledge", "wall edge", "curb", "platform"],
        "forbidden_elements": ["flat ground only", "empty plaza", "middle of road"],
        "prompt_addition": "Background MUST include a visible sitting surface (bench, stairs, ledge, or platform) at the exact height where the model is seated.",
    },
    "leaning": {
        "required_elements": ["wall", "pillar", "column", "railing", "fence", "car", "tree"],
        "forbidden_elements": ["open field", "empty space", "middle of street"],
        "prompt_addition": "Background MUST include a vertical surface (wall, pillar, or railing) for the model to lean against.",
    },
    "crouching": {
        "required_elements": ["ground", "floor", "surface"],
        "forbidden_elements": [],
        "prompt_addition": "Background ground surface must be clearly visible and connect naturally with model's crouching position.",
    },
    "lying": {
        "required_elements": ["ground", "grass", "beach", "bed", "sofa", "floor"],
        "forbidden_elements": ["standing area", "sidewalk", "street"],
        "prompt_addition": "Background MUST include a horizontal surface (grass, sand, floor) suitable for lying down.",
    },
    "standing": {
        "required_elements": [],  # 제약 없음
        "forbidden_elements": [],
        "prompt_addition": "",  # 추가 지시 불필요
    },
}

# 지지대 타입별 호환 배경
SUPPORT_TYPE_BACKGROUNDS = {
    "wall": ["urban street", "alley", "building exterior", "concrete wall", "brick wall"],
    "chair": ["cafe terrace", "park bench area", "indoor space", "restaurant"],
    "bench": ["park", "plaza", "street corner", "public space"],
    "steps": ["building entrance", "stairway", "amphitheater", "monument"],
    "railing": ["bridge", "balcony", "waterfront", "overlook"],
    "none": ["any"],  # 제약 없음
}


def validate_pose_background_compatibility(
    vfx_data: Dict[str, Any],
    background_prompt: str
) -> Tuple[bool, str, str]:
    """
    VFX 분석 데이터와 배경 프롬프트의 호환성 검증

    Args:
        vfx_data: analyze_model_physics()의 반환값 중 'data' 부분
        background_prompt: 사용자가 입력한 배경 설명

    Returns:
        Tuple[bool, str, str]: (is_compatible, warning_message, prompt_addition)
        - is_compatible: 호환 여부
        - warning_message: 비호환시 경고 메시지
        - prompt_addition: 프롬프트에 추가할 포즈 지지 요구사항
    """
    pose_dep = vfx_data.get("pose_dependency", {})
    pose_type = pose_dep.get("pose_type", "standing").lower()
    support_required = pose_dep.get("support_required", False)
    support_type = pose_dep.get("support_type", "none").lower()
    support_direction = pose_dep.get("support_direction", "none")
    prompt_requirement = pose_dep.get("prompt_requirement", "")

    # 포즈 요구사항 조회
    pose_req = POSE_BACKGROUND_REQUIREMENTS.get(pose_type, POSE_BACKGROUND_REQUIREMENTS["standing"])

    warnings = []
    prompt_additions = []

    # 1. 필수 요소 체크
    if pose_req["required_elements"]:
        bg_lower = background_prompt.lower()
        has_required = any(elem in bg_lower for elem in pose_req["required_elements"])

        if not has_required and support_required:
            warnings.append(
                f"POSE MISMATCH: '{pose_type}' pose requires {pose_req['required_elements']}, "
                f"but background '{background_prompt}' may not have suitable support."
            )
            # 자동으로 프롬프트 보강
            prompt_additions.append(pose_req["prompt_addition"])

    # 2. VFX에서 추출한 prompt_requirement 추가
    if prompt_requirement and prompt_requirement != "No support needed":
        prompt_additions.append(f"CRITICAL POSE SUPPORT: {prompt_requirement}")

    # 3. 지지대 타입 기반 추가 검증
    if support_type != "none" and support_required:
        compatible_bgs = SUPPORT_TYPE_BACKGROUNDS.get(support_type, [])
        if compatible_bgs and compatible_bgs != ["any"]:
            bg_lower = background_prompt.lower()
            is_compatible_bg = any(bg in bg_lower for bg in compatible_bgs)
            if not is_compatible_bg:
                prompt_additions.append(
                    f"Background must include {support_type} or similar support structure "
                    f"at {support_direction} of the model for physical plausibility."
                )

    # 결과 조립
    is_compatible = len(warnings) == 0
    warning_message = " | ".join(warnings) if warnings else ""
    prompt_addition = "\n".join(prompt_additions) if prompt_additions else ""

    return is_compatible, warning_message, prompt_addition


def get_pose_compatible_backgrounds(pose_type: str, support_type: str = "none") -> List[str]:
    """
    특정 포즈에 호환되는 배경 유형 목록 반환

    Args:
        pose_type: sitting, standing, leaning, crouching, lying
        support_type: wall, chair, bench, steps, railing, none

    Returns:
        호환 가능한 배경 유형 리스트
    """
    compatible = []

    # 지지대 타입 기반
    if support_type in SUPPORT_TYPE_BACKGROUNDS:
        compatible.extend(SUPPORT_TYPE_BACKGROUNDS[support_type])

    # 포즈 타입 기반 추가 권장
    pose_recommendations = {
        "sitting": ["park with benches", "cafe terrace", "stairs", "urban steps", "plaza with seating"],
        "leaning": ["urban wall", "graffiti alley", "brick building", "industrial exterior"],
        "standing": ["street", "sidewalk", "plaza", "park path", "urban landscape"],
        "crouching": ["urban ground", "graffiti wall base", "street corner"],
        "lying": ["grass field", "beach", "park lawn"],
    }

    if pose_type in pose_recommendations:
        compatible.extend(pose_recommendations[pose_type])

    return list(set(compatible))  # 중복 제거


def build_pose_aware_prompt_addition(vfx_data: Dict[str, Any]) -> str:
    """
    VFX 데이터를 기반으로 포즈 인식 프롬프트 블록 생성

    Args:
        vfx_data: analyze_model_physics()의 반환값 중 'data' 부분

    Returns:
        프롬프트에 추가할 포즈 관련 지시문
    """
    pose_dep = vfx_data.get("pose_dependency", {})
    pose_type = pose_dep.get("pose_type", "standing")
    support_required = pose_dep.get("support_required", False)
    support_type = pose_dep.get("support_type", "none")
    support_direction = pose_dep.get("support_direction", "none")

    if not support_required or pose_type == "standing":
        return ""

    lines = [
        "=== POSE PHYSICS REQUIREMENT (CRITICAL) ===",
        f"Detected pose: {pose_type}",
        f"Support required: {support_type} at {support_direction}",
        "",
    ]

    if pose_type == "sitting":
        lines.extend([
            "The model is SITTING. The background MUST include:",
            "- A visible sitting surface (bench, stairs, ledge, platform) at the EXACT height of the model's seated position",
            "- The surface must connect naturally with the model's body",
            "- DO NOT place the model on flat ground - they will appear to be floating",
            "",
        ])
    elif pose_type == "leaning":
        lines.extend([
            "The model is LEANING. The background MUST include:",
            f"- A vertical support surface ({support_type}) at the {support_direction} of the model",
            "- The surface must be at the correct position to support the lean angle",
            "- DO NOT leave empty space where the model is leaning",
            "",
        ])

    lines.append("Failure to provide appropriate support will result in physically impossible composition.")

    return "\n".join(lines)
