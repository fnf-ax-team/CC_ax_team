"""
pose_copy 생성 프롬프트 조립 모듈

핵심 원칙:
- reference_analysis: 레퍼런스 이미지 VLM 분석 결과 (포즈/구도/배경)
- source_analysis: 소스 인물 VLM 분석 결과 (얼굴/착장만, 포즈 제외)
- 레퍼런스 이미지는 API에 직접 전달되므로, 이 프롬프트는 텍스트 보조 역할
"""

from typing import Optional

from .templates import POSE_COPY_PROMPT, get_background_instruction


def build_pose_copy_prompt(
    reference_analysis: dict,
    source_analysis: dict,
    background_mode: str = "reference",
    custom_background: Optional[str] = None,
) -> str:
    """포즈 복제 생성 프롬프트를 조립한다.

    레퍼런스 이미지가 API에 직접 전달되는 구조이므로,
    이 프롬프트는 포즈/구도 재확인과 소스 인물 정보 제공에 집중한다.

    Args:
        reference_analysis: analyze_reference_pose() 반환값
            - pose_description: str
            - camera_angle: str
            - framing: str
            - composition: str
            - background: str (또는 background_raw: dict)
            - expression: str
        source_analysis: analyze_source_person() 반환값
            - face_description: str
            - outfit_description: str
            - hair_description: str
        background_mode: 배경 처리 방식
            - "reference": 레퍼런스 이미지 배경 재현 (기본값)
            - "source": 소스 이미지 배경 컨텍스트 사용
            - "custom": custom_background 문자열 사용
        custom_background: background_mode="custom" 시 배경 설명 문자열

    Returns:
        str: API에 전달할 완성된 프롬프트 텍스트

    Note:
        source_analysis에는 포즈 정보가 없어야 한다.
        analyze_source_person()은 얼굴/착장만 추출하도록 설계되어 있다.
    """
    # 1. 포즈 설명 (레퍼런스 분석 결과)
    pose_description = reference_analysis.get(
        "pose_description", "natural standing pose"
    )

    # 2. 구도 설명 (레퍼런스 분석 결과)
    composition_description = _build_composition_description(reference_analysis)

    # 3. 표정 설명 (레퍼런스 분석 결과)
    expression_description = reference_analysis.get(
        "expression", "neutral, confident, direct gaze"
    )

    # 4. 얼굴 설명 (소스 인물 분석 결과)
    face_description = source_analysis.get("face_description", "natural looking person")

    # 5. 착장 설명 (소스 인물 분석 결과)
    outfit_description = source_analysis.get("outfit_description", "casual outfit")

    # 6. 헤어 설명 (소스 인물 분석 결과)
    hair_description = source_analysis.get("hair_description", "natural hair")

    # 7. 배경 지시문 생성
    background_instruction = _build_background_instruction(
        background_mode=background_mode,
        reference_analysis=reference_analysis,
        source_analysis=source_analysis,
        custom_background=custom_background,
    )

    # 8. 최종 프롬프트 조립
    prompt = POSE_COPY_PROMPT.format(
        pose_description=pose_description,
        composition_description=composition_description,
        expression_description=expression_description,
        face_description=face_description,
        outfit_description=outfit_description,
        hair_description=hair_description,
        background_instruction=background_instruction,
    )

    return prompt.strip()


# ============================================================================
# 내부 유틸리티
# ============================================================================


def _build_composition_description(reference_analysis: dict) -> str:
    """레퍼런스 분석에서 구도 설명 문자열 조립"""
    # flat 문자열이 이미 있으면 사용
    if reference_analysis.get("composition"):
        composition = reference_analysis["composition"]
        # flat 문자열인지 확인 (dict가 아닌 경우)
        if isinstance(composition, str):
            return composition

    # 개별 필드로 조립
    parts = []

    framing = reference_analysis.get("framing")
    if framing:
        parts.append(f"framing: {framing}")

    camera_angle = reference_analysis.get("camera_angle")
    if camera_angle:
        parts.append(f"camera angle: {camera_angle}")

    # composition_raw가 있으면 추가 정보 추출
    comp_raw = reference_analysis.get("composition_raw", {})
    if comp_raw:
        distance = comp_raw.get("distance")
        if distance:
            parts.append(f"distance: {distance}")

        pos = comp_raw.get("person_position", {})
        if pos:
            parts.append(
                f"person position: x={pos.get('x', 0.5):.1f} y={pos.get('y', 0.6):.1f}"
            )

        size_ratio = comp_raw.get("person_size_ratio")
        if size_ratio:
            parts.append(f"size ratio: {size_ratio:.0%} of frame")

    return ", ".join(parts) if parts else "centered, full body, eye-level"


def _build_background_instruction(
    background_mode: str,
    reference_analysis: dict,
    source_analysis: dict,
    custom_background: Optional[str],
) -> str:
    """배경 모드에 따른 지시문 생성"""
    # 레퍼런스 배경 dict 추출
    ref_bg_raw = reference_analysis.get("background_raw", {})

    # flat 문자열만 있는 경우 dict로 변환
    if not ref_bg_raw:
        bg_str = reference_analysis.get("background", "")
        ref_bg_raw = {"setting": bg_str} if bg_str else {}

    # 소스 배경 dict (source 모드 시 사용)
    # source_analysis는 배경 정보를 포함하지 않으므로 빈 dict 기본값
    source_bg_raw = source_analysis.get("background_raw", {})

    try:
        return get_background_instruction(
            bg_option=background_mode,
            ref_bg=ref_bg_raw,
            source_bg=source_bg_raw if background_mode == "source" else None,
            custom_bg=custom_background if background_mode == "custom" else None,
        )
    except ValueError as e:
        print(f"[PoseCopyPromptBuilder] 배경 지시문 생성 실패: {e}, 기본값 사용")
        return "BACKGROUND: Clean, neutral studio background. Simple and minimal."
