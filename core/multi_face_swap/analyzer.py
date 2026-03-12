"""
다중 얼굴 교체 분석 모듈

두 가지 분석을 담당한다:
1. analyze_group_photo  — 단체 사진의 장면/조명/포즈 컨텍스트 추출
2. analyze_replacement_faces — 각 교체 얼굴 세트의 특징 분석

VLM 모델: VISION_MODEL (gemini-3-flash-preview)
"""

import json
import logging
from io import BytesIO
from typing import Any, Union

from PIL import Image

from core.config import VISION_MODEL
from core.multi_face_swap.detector import (
    _load_image,
    _pil_to_part,
    _parse_json_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VLM 프롬프트 (단체 사진 장면 분석)
# =============================================================================

_GROUP_CONTEXT_PROMPT = """
이 단체 사진의 장면 컨텍스트를 분석하세요.

[STEP 1] 장면 설명
- 배경 환경: 실내/실외, 구체적 장소
- 전체 분위기: 캐주얼/포멀/아웃도어 등

[STEP 2] 조명 분석
- 주광원 방향: 왼쪽/오른쪽/상단/정면/역광
- 조명 강도: 강함/보통/약함
- 조명 색온도: 쿨(자연광/형광)/뉴트럴/웜(황색/할로겐)

[STEP 3] 포즈 컨텍스트
- 전체 그룹 포즈 패턴 (예: "group standing in a line", "seated around a table")
- 신체 방향 (카메라 기준): 정면/약간 옆/측면
- 촬영 각도: 아이레벨/로우앵글/하이앵글

[STEP 4] 인물 간 관계 (공간적)
- 접촉/근접 여부 (예: "person 1 has arm around person 2")
- 인물 간 간격

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "scene_description": "outdoor urban street, casual daytime",
  "lighting_description": "soft natural light from upper-left, cool temperature",
  "overall_pose_context": "group standing in horizontal line, facing camera",
  "person_relationships": [
    "person 1 and person 2 standing close together",
    "person 3 has slight separation from the group"
  ]
}
"""


# =============================================================================
# VLM 프롬프트 (단일 얼굴 세트 분석)
# =============================================================================

_FACE_ANALYSIS_PROMPT = """
이 얼굴 참조 이미지(들)를 분석하여 교체에 필요한 특징을 추출하세요.

[STEP 1] 얼굴 특징 분석
- 전반적 인상: 성별/나이대/피부톤
- 두드러진 얼굴 특징: 눈, 코, 입, 윤곽 등

[STEP 2] 최적 참조 각도
- 제공된 이미지 중 교체에 가장 적합한 앵글 (frontal 선호)
- frontal / 3/4 left / 3/4 right / profile

[STEP 3] 조명 특성
- 현재 참조 이미지의 조명 방향
- 피부톤 색온도 (쿨/뉴트럴/웜)

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "face_description": "young female, fair skin, almond-shaped eyes, defined jawline",
  "best_angle": "frontal",
  "skin_tone": "neutral",
  "lighting_in_reference": "soft frontal, neutral temperature",
  "distinguishing_features": "high cheekbones, thin eyebrows"
}
"""


# =============================================================================
# 공개 함수
# =============================================================================


def analyze_group_photo(
    source_image: Union[Image.Image, str],
    detected_faces: list[dict],
    client: Any,
) -> dict:
    """단체 사진의 장면/조명/포즈 컨텍스트 분석

    VLM(VISION_MODEL)으로 단체 사진의 전반적 컨텍스트를 추출한다.
    이 결과는 prompt_builder에서 교체 프롬프트에 반영된다.

    Args:
        source_image: 단체 사진 (PIL Image 또는 파일 경로)
        detected_faces: detect_faces()의 반환값 (인물 정보 리스트)
        client: 초기화된 Gemini API 클라이언트

    Returns:
        dict:
            - scene_description: str — 배경/장소/분위기 요약
            - lighting_description: str — 조명 방향/강도/색온도
            - overall_pose_context: str — 그룹 전체 포즈 패턴
            - person_relationships: list[str] — 인물 간 공간 관계

    Raises:
        ValueError: VLM 응답 파싱 실패 시
        TypeError: 지원하지 않는 이미지 타입 시
    """
    from google.genai import types

    img = _load_image(source_image)
    img_part = _pil_to_part(img)

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=_GROUP_CONTEXT_PROMPT),
                    img_part,
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"],
        ),
    )

    raw_text = response.candidates[0].content.parts[0].text
    result = _parse_json_response(raw_text)

    # 필수 키가 없으면 안전한 기본값 채우기
    result.setdefault("scene_description", "unknown scene")
    result.setdefault("lighting_description", "natural light")
    result.setdefault("overall_pose_context", "group photo")
    result.setdefault("person_relationships", [])

    logger.debug(
        "[MULTI_FACE_SWAP] 단체 사진 분석 완료 — 장면: %s, 조명: %s",
        result["scene_description"],
        result["lighting_description"],
    )

    return result


def analyze_replacement_faces(
    face_mapping: dict[int, list[Union[Image.Image, str]]],
    client: Any,
) -> dict[int, dict]:
    """각 교체 얼굴 세트를 VLM으로 분석

    person_id별로 제공된 참조 얼굴 이미지를 분석하여
    교체 프롬프트 조합에 필요한 특징 딕셔너리를 반환한다.

    얼굴 수 제한:
        - 5명 이하: 권장 범위 (정상 처리)
        - 6~10명: 경고 로그 출력 (처리 계속)
        - 11명 이상: ValueError 발생

    Args:
        face_mapping: {person_id: [face_image, ...]} 형태의 매핑
            person_id는 1-indexed int
            face_image는 PIL Image 또는 파일 경로 문자열
        client: 초기화된 Gemini API 클라이언트

    Returns:
        dict[int, dict] — person_id 키, 얼굴 분석 결과 값:
        {
            1: {
                "face_description": str,
                "best_angle": str,
                "skin_tone": str,
                "lighting_in_reference": str,
                "distinguishing_features": str,
            },
            2: {...},
        }

    Raises:
        ValueError: 얼굴 세트 11개 초과 시
    """
    from google.genai import types

    num_persons = len(face_mapping)

    # 인원 수 제한 체크
    if num_persons > 10:
        raise ValueError(
            f"교체 얼굴 세트({num_persons}명)가 최대 허용 인원(10명)을 초과합니다."
        )
    if num_persons > 5:
        logger.warning(
            "[MULTI_FACE_SWAP] 교체 얼굴 세트 %d명. 5명 초과 시 품질이 저하될 수 있습니다.",
            num_persons,
        )

    analyses: dict[int, dict] = {}

    for person_id, face_images_raw in face_mapping.items():
        if not face_images_raw:
            logger.warning(
                "[MULTI_FACE_SWAP] person_id=%d 얼굴 이미지 없음. 기본값 사용.",
                person_id,
            )
            analyses[person_id] = _default_face_analysis()
            continue

        # 이미지 파트 구성 (최대 3장만 사용 — VLM 부담 최소화)
        parts = [types.Part(text=_FACE_ANALYSIS_PROMPT)]
        for img_src in face_images_raw[:3]:
            try:
                img = _load_image(img_src)
                parts.append(_pil_to_part(img))
            except Exception as e:
                logger.warning(
                    "[MULTI_FACE_SWAP] person_id=%d 얼굴 이미지 로드 실패: %s",
                    person_id,
                    e,
                )

        if len(parts) == 1:
            # 이미지 로드 전부 실패
            logger.warning(
                "[MULTI_FACE_SWAP] person_id=%d 모든 얼굴 이미지 로드 실패. 기본값 사용.",
                person_id,
            )
            analyses[person_id] = _default_face_analysis()
            continue

        try:
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=parts,
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"],
                ),
            )
            raw_text = response.candidates[0].content.parts[0].text
            face_result = _parse_json_response(raw_text)
        except Exception as e:
            logger.warning(
                "[MULTI_FACE_SWAP] person_id=%d VLM 분석 실패: %s. 기본값 사용.",
                person_id,
                e,
            )
            face_result = _default_face_analysis()

        # 필수 키 기본값 채우기
        face_result.setdefault("face_description", "unknown")
        face_result.setdefault("best_angle", "frontal")
        face_result.setdefault("skin_tone", "neutral")
        face_result.setdefault("lighting_in_reference", "natural light")
        face_result.setdefault("distinguishing_features", "")

        analyses[person_id] = face_result
        logger.debug(
            "[MULTI_FACE_SWAP] person_id=%d 분석 완료 — 각도: %s, 피부톤: %s",
            person_id,
            face_result["best_angle"],
            face_result["skin_tone"],
        )

    return analyses


# =============================================================================
# 내부 헬퍼
# =============================================================================


def _default_face_analysis() -> dict:
    """얼굴 분석 실패 시 사용하는 안전한 기본값"""
    return {
        "face_description": "unknown",
        "best_angle": "frontal",
        "skin_tone": "neutral",
        "lighting_in_reference": "natural light",
        "distinguishing_features": "",
    }
