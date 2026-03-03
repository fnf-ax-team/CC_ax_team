"""
Face Swap 프롬프트 조립 모듈

소스 이미지 분석 결과(analyze_source_image 출력)를 받아
IMAGE_MODEL에 전달할 최종 생성 프롬프트를 조립한다.
"""

from typing import Optional

from .templates import FACE_SWAP_PROMPT


def build_face_swap_prompt(
    source_analysis: dict,
    face_description: Optional[str] = None,
) -> str:
    """
    Face Swap 생성 프롬프트 조립.

    Args:
        source_analysis: analyze_source_image()의 반환값.
            필요 키:
            - pose_description: str
            - outfit_description: str
            - background_description: str
            - lighting_description: str
            - face_angle: str
            - face_position: str
        face_description: 교체할 얼굴에 대한 부가 설명 (선택).
            예: "Korean female, mid-20s, oval face, fair skin"
            None이면 템플릿 기본 설명만 사용.

    Returns:
        IMAGE_MODEL에 전달할 완성된 프롬프트 문자열.
    """
    pose_description = source_analysis.get("pose_description", "standing naturally")
    outfit_description = source_analysis.get("outfit_description", "casual outfit")
    background_description = source_analysis.get(
        "background_description", "neutral background"
    )
    lighting_description = source_analysis.get(
        "lighting_description", "natural soft lighting"
    )
    face_angle = source_analysis.get("face_angle", "frontal")
    face_position = source_analysis.get("face_position", "x=0.50, y=0.30")

    prompt = FACE_SWAP_PROMPT.format(
        pose_description=pose_description,
        outfit_description=outfit_description,
        background_description=background_description,
        lighting_description=lighting_description,
        face_angle=face_angle,
        face_position=face_position,
    )

    # 얼굴 부가 설명이 제공된 경우 프롬프트 끝에 추가
    if face_description:
        prompt = prompt.rstrip() + f"\n\n[TARGET FACE DESCRIPTION]\n{face_description}"

    return prompt
