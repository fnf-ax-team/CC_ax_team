"""
포즈 변경 프롬프트 조립 모듈

소스 이미지 분석 결과와 목표 포즈를 받아 IMAGE_MODEL에 전달할
최종 생성 프롬프트를 조립한다.
"""

from .templates import build_pose_change_prompt as _build_prompt
from .presets import get_pose_description


def build_pose_change_prompt(
    source_analysis: dict,
    target_pose: str,
) -> str:
    """포즈 변경 이미지 생성 프롬프트를 조립한다.

    소스 이미지 분석 결과에서 얼굴/착장/배경/체형 보존 정보를 추출하고,
    목표 포즈를 프리셋 키 또는 커스텀 설명으로 해석하여
    IMAGE_MODEL에 전달할 최종 프롬프트를 반환한다.

    프리셋 키 (예: "lean_wall", "sit_floor")를 전달하면
    presets.py의 영문 포즈 설명으로 자동 변환된다.
    프리셋에 없는 문자열은 커스텀 포즈 설명으로 그대로 사용된다.

    Args:
        source_analysis: analyze_source_for_pose_change() 반환값.
            반드시 "preserve_elements"와 "physical_constraints" 키를 포함해야 한다.
        target_pose: 목표 포즈 (프리셋 키 또는 직접 입력 영문 설명).
            예시:
                - "lean_wall" → "leaning against the wall, one foot up, casual stance"
                - "sitting cross-legged on the floor, relaxed" → 그대로 사용

    Returns:
        str: IMAGE_MODEL에 전달할 생성 프롬프트 문자열.
            얼굴/착장/배경 보존 지시와 새 포즈 지시를 포함한다.

    Raises:
        KeyError: source_analysis에 필수 키가 없는 경우
    """
    # 프리셋 키이면 영문 설명으로 변환, 아니면 그대로 사용
    pose_description = get_pose_description(target_pose)

    # templates.py의 build_pose_change_prompt 위임
    return _build_prompt(
        source_analysis=source_analysis,
        target_pose=pose_description,
    )
