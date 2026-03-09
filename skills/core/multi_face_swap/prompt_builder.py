"""
다중 얼굴 교체 프롬프트 빌더

templates.py의 build_multi_face_swap_prompt()를 래핑하고
analyzer.py의 분석 결과를 통합하여 완성된 교체 프롬프트를 생성한다.

인원 수 제한:
    - 5명 이하: 권장
    - 6~10명: 경고 (진행 가능)
    - 11명 이상: ValueError 발생
"""

import logging

from core.multi_face_swap.templates import build_multi_face_swap_prompt as _build_prompt

logger = logging.getLogger(__name__)


def build_multi_swap_prompt(
    group_analysis: dict,
    detected_faces: list[dict],
    face_analyses: dict[int, dict],
) -> str:
    """다중 얼굴 교체 최종 프롬프트 생성

    analyze_group_photo(), detect_faces(), analyze_replacement_faces()의
    결과를 통합하여 Gemini 이미지 생성 모델에 전달할 프롬프트를 조립한다.

    처리 로직:
    - 인물별 위치 참조 (position)로 교체 대상 명확히 지정
    - 그룹 조명/장면 컨텍스트를 보존 지시에 반영
    - 각 얼굴의 최적 앵글·피부톤 정보를 블렌딩 힌트로 추가
    - 착장·포즈·배경 완전 보존 규칙 포함

    인원 수 제한:
        - 5명 이하: 권장 (최적 품질)
        - 6~10명: 경고 로그 후 계속 진행
        - 11명 이상: ValueError 발생

    Args:
        group_analysis: analyze_group_photo() 반환값.
            - scene_description: str
            - lighting_description: str
            - overall_pose_context: str
            - person_relationships: list[str]
        detected_faces: detect_faces() 반환값 (인물 정보 리스트).
            각 항목에 id, position, clothing_hint 등 포함.
        face_analyses: analyze_replacement_faces() 반환값.
            {person_id: {"face_description": ..., "best_angle": ..., ...}}

    Returns:
        str: 완성된 다중 얼굴 교체 프롬프트

    Raises:
        ValueError: detected_faces 기준 인물 11명 이상 시
    """
    num_persons = len(detected_faces)

    # 인원 수 제한 체크
    if num_persons > 10:
        raise ValueError(
            f"감지된 인물 수({num_persons}명)가 최대 허용 인원(10명)을 초과합니다. "
            "10명 이하 단체 사진을 사용하세요."
        )
    if num_persons > 5:
        logger.warning(
            "[MULTI_FACE_SWAP] 인물 %d명. 5명 초과 시 품질이 저하될 수 있습니다. 최적 인원: 2~4명.",
            num_persons,
        )

    # persons_info 딕셔너리 구성 (templates의 build_multi_face_swap_prompt 입력 형식)
    persons_info = {
        "total_persons": num_persons,
        "persons": detected_faces,
    }

    # face_mappings: {person_id: face_folder_path} — 위치 주석용 (실제 이미지 전달은 API 레이어에서)
    face_mappings = {pid: f"person_{pid}_faces" for pid in face_analyses.keys()}

    # 기본 프롬프트 생성 (templates 위임)
    base_prompt = _build_prompt(
        persons_info=persons_info,
        face_mappings=face_mappings,
    )

    # 장면·조명 컨텍스트 보존 섹션 추가
    scene_section = _build_scene_section(group_analysis)

    # 인물별 얼굴 블렌딩 힌트 섹션 추가
    face_hint_section = _build_face_hints_section(detected_faces, face_analyses)

    return f"{base_prompt}\n\n{scene_section}\n\n{face_hint_section}".strip()


# =============================================================================
# 내부 헬퍼
# =============================================================================


def _build_scene_section(group_analysis: dict) -> str:
    """장면/조명/포즈 컨텍스트 보존 섹션 생성

    Args:
        group_analysis: analyze_group_photo() 반환값

    Returns:
        str: 프롬프트에 추가할 장면 컨텍스트 섹션
    """
    scene = group_analysis.get("scene_description", "")
    lighting = group_analysis.get("lighting_description", "")
    pose_context = group_analysis.get("overall_pose_context", "")
    relationships = group_analysis.get("person_relationships", [])

    lines = ["=== SCENE CONTEXT (PRESERVE EXACTLY) ==="]

    if scene:
        lines.append(f"Scene: {scene}")
    if lighting:
        lines.append(
            f"Lighting: {lighting} — apply consistent relight to ALL replaced faces"
        )
    if pose_context:
        lines.append(f"Group pose: {pose_context} — do NOT alter any pose")

    if relationships:
        lines.append("Spatial relationships (must be preserved):")
        for rel in relationships:
            lines.append(f"  - {rel}")

    return "\n".join(lines)


def _build_face_hints_section(
    detected_faces: list[dict],
    face_analyses: dict[int, dict],
) -> str:
    """인물별 얼굴 블렌딩 힌트 섹션 생성

    각 인물의 최적 참조 앵글과 피부톤 정보를 생성 모델에 전달하여
    자연스러운 블렌딩을 유도한다.

    Args:
        detected_faces: detect_faces() 반환값 (인물 정보 리스트)
        face_analyses: analyze_replacement_faces() 반환값

    Returns:
        str: 프롬프트에 추가할 얼굴 힌트 섹션
    """
    id_to_person = {p["id"]: p for p in detected_faces}

    lines = ["=== PER-PERSON FACE BLENDING HINTS ==="]

    for person_id, analysis in sorted(face_analyses.items()):
        person = id_to_person.get(person_id, {})
        position = person.get("position", f"position_{person_id}")
        face_angle_in_group = person.get("face_angle", "unknown")

        best_angle = analysis.get("best_angle", "frontal")
        skin_tone = analysis.get("skin_tone", "neutral")
        distinguishing = analysis.get("distinguishing_features", "")

        hint_parts = [
            f"PERSON_{person_id} ({position}):",
            f"  - Reference best angle: {best_angle}",
            f"  - Target face angle in photo: {face_angle_in_group}",
            f"  - Skin tone: {skin_tone} — match to group lighting",
        ]
        if distinguishing:
            hint_parts.append(f"  - Key features to preserve: {distinguishing}")

        lines.extend(hint_parts)

    lines.append(
        "\nApply consistent ambient lighting adaptation to ALL faces "
        "so they match the scene lighting described above."
    )

    return "\n".join(lines)
