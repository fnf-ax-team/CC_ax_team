"""
다중 얼굴 감지 및 매핑 모듈

VLM(VISION_MODEL)을 사용하여 단체 사진에서 모든 인물을 감지하고
각 인물의 위치/특징을 추출한다.

주요 함수:
    detect_faces(source_image, client) -> list[dict]
    map_faces(detected_faces, face_mapping) -> dict
"""

import json
import logging
from io import BytesIO
from typing import Any, Union

from PIL import Image

from core.config import VISION_MODEL
from core.multi_face_swap.templates import FACE_DETECTION_PROMPT

logger = logging.getLogger(__name__)


def _pil_to_part(img: Image.Image, max_size: int = 1024):
    """PIL 이미지를 Gemini API Part로 변환

    Args:
        img: PIL 이미지
        max_size: 최대 픽셀 크기 (긴 변 기준)

    Returns:
        google.genai.types.Part 객체
    """
    from google.genai import types

    # 크기 제한 (VLM 분석용이므로 1024px 충분)
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _load_image(source: Union[Image.Image, str]) -> Image.Image:
    """이미지 로드 헬퍼

    Args:
        source: PIL 이미지 또는 파일 경로 문자열

    Returns:
        RGB PIL 이미지
    """
    if isinstance(source, str):
        return Image.open(source).convert("RGB")
    if hasattr(source, "convert"):
        return source.convert("RGB")
    raise TypeError(f"지원하지 않는 이미지 타입: {type(source)}")


def _parse_json_response(text: str) -> dict:
    """VLM 응답 텍스트에서 JSON 파싱

    Args:
        text: VLM 응답 텍스트

    Returns:
        파싱된 딕셔너리

    Raises:
        ValueError: JSON 파싱 실패 시
    """
    # 마크다운 코드블록 제거
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"VLM 응답 JSON 파싱 실패: {e}\n원본 텍스트:\n{text[:500]}")


def detect_faces(
    source_image: Union[Image.Image, str],
    client: Any,
) -> list[dict]:
    """단체 사진에서 모든 인물을 VLM으로 감지

    VISION_MODEL을 사용하여 단체 사진 내 각 인물의 위치, 얼굴 각도,
    착장 특징 등을 추출한다.

    인물 수 제한:
        - 6~10명: 경고 로그 출력 (진행은 계속)
        - 11명 이상: ValueError 발생 (처리 거부)

    Args:
        source_image: 단체 사진 (PIL Image 또는 파일 경로)
        client: 초기화된 Gemini API 클라이언트 (google.genai.Client)

    Returns:
        감지된 인물 정보 리스트. 각 항목:
        {
            "id": int,                     # 왼쪽부터 부여 (1-indexed)
            "position": str,               # "left", "center", "right" 등
            "bbox": {                      # 정규화 좌표 (0.0~1.0)
                "x1": float,
                "y1": float,
                "x2": float,
                "y2": float
            },
            "face_angle": str,             # "frontal", "3/4 left" 등
            "clothing_hint": str,          # 구분용 착장 특징
            "hair_hint": str,              # 머리 특징
            "distinguishing_features": str # 기타 구분 특징
        }

    Raises:
        ValueError: 인물 11명 초과 또는 감지 실패 시
        TypeError: 지원하지 않는 이미지 타입 시
    """
    from google.genai import types

    # 이미지 로드
    img = _load_image(source_image)
    img_part = _pil_to_part(img)

    # VLM 호출 (텍스트 응답만)
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=FACE_DETECTION_PROMPT),
                    img_part,
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,  # 감지 정확도를 위해 낮게 설정
            response_modalities=["TEXT"],
        ),
    )

    # 응답 텍스트 추출
    raw_text = response.candidates[0].content.parts[0].text
    result = _parse_json_response(raw_text)

    # 인물 수 검증
    total_persons = result.get("total_persons", 0)
    persons = result.get("persons", [])

    if total_persons == 0 or not persons:
        raise ValueError("단체 사진에서 인물을 감지하지 못했습니다.")

    # 11명 이상: 처리 거부
    if total_persons > 10:
        raise ValueError(
            f"감지된 인물 수({total_persons}명)가 최대 허용 인원(10명)을 초과합니다. "
            "10명 이하의 단체 사진을 사용하세요."
        )

    # 6~10명: 경고
    if total_persons > 5:
        logger.warning(
            "[MULTI_FACE_SWAP] 인물 %d명 감지됨. 5명 초과 시 정확도가 낮아질 수 있습니다. "
            "최적 인원: 2~4명.",
            total_persons,
        )

    # persons 리스트만 반환 (id, bbox, description 포함)
    return persons


def map_faces(
    detected_faces: list[dict],
    face_mapping: dict[int, list],
) -> dict:
    """감지된 인물 ID와 교체할 얼굴 이미지를 매핑

    detect_faces() 결과와 사용자가 지정한 얼굴 이미지 목록을 연결한다.
    매핑에 없는 인물은 결과에서 제외된다.

    Args:
        detected_faces: detect_faces() 반환값 (인물 정보 리스트)
        face_mapping: {person_id: [face_image, ...]} 형태의 매핑
            person_id는 1-indexed int
            face_image는 PIL Image 또는 파일 경로 문자열

    Returns:
        {
            person_id (int): {
                "person_info": dict,        # 원본 감지 정보
                "face_images": list[Image], # 교체할 얼굴 이미지 (PIL)
                "mapped": bool              # 매핑 완료 여부
            },
            ...
        }

    Example:
        detected = detect_faces(group_photo, client)
        result = map_faces(detected, {
            1: [Image.open("alice1.jpg"), Image.open("alice2.jpg")],
            2: [Image.open("bob1.jpg")],
        })
    """
    # id → person_info 딕셔너리 구성
    id_to_person = {p["id"]: p for p in detected_faces}

    result = {}
    for person_id, face_images_raw in face_mapping.items():
        person_info = id_to_person.get(person_id)
        if person_info is None:
            logger.warning(
                "[MULTI_FACE_SWAP] 매핑된 person_id=%d 가 감지 결과에 없습니다. "
                "감지된 ID 목록: %s",
                person_id,
                list(id_to_person.keys()),
            )
            mapped = False
            person_info = {"id": person_id, "position": "unknown"}
        else:
            mapped = True

        # 각 얼굴 이미지를 PIL 형식으로 로드
        loaded_images = []
        for img_src in face_images_raw:
            try:
                loaded_images.append(_load_image(img_src))
            except Exception as e:
                logger.warning(
                    "[MULTI_FACE_SWAP] person_id=%d 얼굴 이미지 로드 실패: %s",
                    person_id,
                    e,
                )

        result[person_id] = {
            "person_info": person_info,
            "face_images": loaded_images,
            "mapped": mapped and len(loaded_images) > 0,
        }

    return result
