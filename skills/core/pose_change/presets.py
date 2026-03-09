"""
포즈 변경 프리셋 모듈

SKILL.md의 포즈 프리셋 데이터를 기반으로 구성.
"""

# 포즈 프리셋 딕셔너리
# 키: 내부 식별자 / 값: API에 전달할 영문 포즈 설명
POSE_PRESETS = {
    "sit_floor": "sitting on the floor, legs crossed, relaxed posture",
    "sit_chair": "sitting on a chair, legs crossed, casual posture",
    "lean_wall": "leaning against the wall, one foot up, casual stance",
    "walking": "walking naturally, mid-stride, natural motion",
    "back_turn": "turned away from camera, looking back over shoulder",
    "arms_crossed": "standing with arms crossed, confident posture",
    "hand_pocket": "standing relaxed, one hand in pocket, casual stance",
}

# 사용자 노출용 라벨 매핑 (SKILL.md AskUserQuestion 옵션과 대응)
POSE_LABELS = {
    "sit_floor": "앉기 (바닥)",
    "sit_chair": "앉기 (의자)",
    "lean_wall": "기대기 (벽)",
    "walking": "걷는 중",
    "back_turn": "뒤돌기",
    "arms_crossed": "팔 꼬고 서기",
    "hand_pocket": "주머니에 손",
}


def get_pose_description(pose_key: str) -> str:
    """프리셋 키 또는 직접 입력된 설명에서 포즈 설명 반환.

    프리셋 키가 있으면 해당 영문 설명 반환.
    없으면 pose_key 자체를 커스텀 설명으로 취급하여 그대로 반환.

    Args:
        pose_key: 프리셋 키 (예: "lean_wall") 또는 직접 입력 포즈 설명

    Returns:
        str: API에 전달할 포즈 설명 문자열
    """
    return POSE_PRESETS.get(pose_key, pose_key)


def list_presets() -> list:
    """사용 가능한 포즈 프리셋 목록 반환 (레이블 포함).

    Returns:
        list: [{"key": ..., "label": ..., "description": ...}, ...] 형식의 목록
    """
    return [
        {
            "key": key,
            "label": POSE_LABELS.get(key, key),
            "description": description,
        }
        for key, description in POSE_PRESETS.items()
    ]
