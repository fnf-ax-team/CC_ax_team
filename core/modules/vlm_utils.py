"""
VLM 공통 유틸리티 (통합)

기존 5+ 파일에 분산된 _pil_to_part, _parse_json_response, _load_image를
한 곳으로 통합한다. 각 분석기에서 중복 구현하지 않고 이 모듈을 import.

통합 대상:
- core.utils.pil_to_part()
- core.api._pil_to_part()
- core.api._load_image()
- core.ai_influencer.pose_analyzer.PoseAnalyzer._pil_to_part()
- core.ai_influencer.face_analyzer.FaceAnalyzer._pil_to_part()
- core.ai_influencer.hair_analyzer.HairAnalyzer._pil_to_part()
- core.ai_influencer.expression_analyzer.ExpressionAnalyzer._pil_to_part()
- core.ai_influencer.background_analyzer.BackgroundAnalyzer._pil_to_part()
"""

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


# ============================================================
# 이미지 로드
# ============================================================


def load_image(
    image: Union[str, Path, Image.Image],
    max_size: Optional[int] = None,
) -> Optional[Image.Image]:
    """
    이미지 로드 통합 함수.

    str/Path이면 파일에서 로드, PIL.Image이면 그대로 반환.
    max_size 지정 시 긴 변 기준으로 축소.

    Args:
        image: 파일 경로 또는 PIL Image
        max_size: 최대 긴변 픽셀 (None이면 리사이즈 안 함)

    Returns:
        RGB 모드 PIL Image. 로드 실패 시 None.
    """
    try:
        if isinstance(image, Image.Image):
            img = image
        elif isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            print(f"[vlm_utils] 지원하지 않는 이미지 타입: {type(image)}")
            return None

        # RGB 변환
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 리사이즈
        if max_size and max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        return img

    except Exception as e:
        print(f"[vlm_utils] 이미지 로드 실패: {e}")
        return None


# ============================================================
# JSON 파싱 (마크다운 코드블록 제거)
# ============================================================


def parse_json_response(text: str) -> dict:
    """
    VLM 응답에서 JSON 추출 및 파싱.

    마크다운 코드블록(```json ... ```)을 자동 제거하고,
    여러 fallback 전략을 시도한다.

    Args:
        text: VLM 응답 텍스트

    Returns:
        파싱된 dict. 실패 시 {"error": ..., "raw": ...}
    """
    if not text:
        return {"error": "빈 응답", "raw": ""}

    text = text.strip()

    # 1) 마크다운 코드블록에서 JSON 추출
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2) 코드블록 시작 라인 제거 후 시도
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json)과 마지막 줄(```) 제거
        inner_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```json"):
                continue
            inner_lines.append(line)
        text = "\n".join(inner_lines).strip()

    # 3) 직접 JSON 파싱
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4) 텍스트 내에서 { ... } 최외곽 추출
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        try:
            return json.loads(text[start_idx : end_idx + 1])
        except json.JSONDecodeError:
            pass

    return {"error": "JSON 파싱 실패", "raw": text[:500]}


# ============================================================
# PIL -> Gemini Part 변환
# ============================================================


def pil_to_part(
    img: Image.Image,
    max_size: int = 1024,
    fmt: str = "PNG",
) -> types.Part:
    """
    PIL Image를 Gemini API Part(inline_data)로 변환.

    core.utils.pil_to_part()와 동일 로직이나,
    format 파라미터를 추가하여 JPEG도 지원.

    Args:
        img: PIL Image (RGB 권장)
        max_size: 긴변 최대 크기 (초과 시 축소)
        fmt: 이미지 포맷 ("PNG" 또는 "JPEG")

    Returns:
        types.Part with inline_data
    """
    img = img.copy()
    if img.mode != "RGB":
        img = img.convert("RGB")

    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    save_kwargs = {"format": fmt}
    if fmt.upper() == "JPEG":
        save_kwargs["quality"] = 90
    img.save(buffer, **save_kwargs)

    mime_type = f"image/{fmt.lower()}"
    if fmt.upper() == "PNG":
        mime_type = "image/png"

    return types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=buffer.getvalue())
    )


# ============================================================
# 통합 VLM 호출 패턴
# ============================================================


def vlm_call(
    api_key: str,
    prompt: str,
    images: Optional[List[Union[str, Path, Image.Image]]] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_image_size: int = 1024,
    response_mime_type: Optional[str] = "application/json",
) -> dict:
    """
    통합 VLM 호출 패턴.

    클라이언트 생성 -> 이미지 Part 변환 -> API 호출 -> JSON 파싱을
    하나의 함수로 묶는다.

    Args:
        api_key: Gemini API 키
        prompt: 분석 프롬프트 텍스트
        images: 이미지 리스트 (경로 또는 PIL Image)
        model: 사용 모델 (기본: VISION_MODEL)
        temperature: 생성 온도
        max_image_size: 이미지 최대 크기
        response_mime_type: 응답 MIME 타입 (None이면 텍스트)

    Returns:
        파싱된 dict. 실패 시 {"error": ...}
    """
    model = model or VISION_MODEL

    # 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # Parts 구성
    parts = [types.Part(text=prompt)]

    if images:
        for img_input in images:
            loaded = load_image(img_input, max_size=max_image_size)
            if loaded is not None:
                parts.append(pil_to_part(loaded, max_size=max_image_size))

    # API 호출
    try:
        config_kwargs = {"temperature": temperature}
        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(**config_kwargs),
        )

        result_text = response.text.strip() if response.text else ""
        return parse_json_response(result_text)

    except Exception as e:
        print(f"[vlm_call] API 호출 실패: {e}")
        return {"error": str(e)}


__all__ = [
    "load_image",
    "parse_json_response",
    "pil_to_part",
    "vlm_call",
]
