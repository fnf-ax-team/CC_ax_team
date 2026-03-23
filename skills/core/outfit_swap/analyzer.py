"""
Outfit Swap Source Analyzer

소스 이미지에서 얼굴/포즈/배경 정보를 추출하는 VLM 분석 모듈
"""

import json
from io import BytesIO
from typing import Any, Optional

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL
from .templates import SOURCE_ANALYSIS_PROMPT, OUTFIT_ANALYSIS_PROMPT


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


class SourceAnalysisResult:
    """소스 이미지 분석 결과"""

    def __init__(self, data: dict):
        self.face = data.get("face", {})
        self.pose = data.get("pose", {})
        self.background = data.get("background", {})
        self.composition = data.get("composition", {})
        self._raw = data

    @property
    def face_position(self) -> str:
        return self.face.get("position", "center")

    @property
    def face_angle(self) -> str:
        return self.face.get("angle", "frontal")

    @property
    def face_expression(self) -> str:
        return self.face.get("expression", "neutral")

    @property
    def pose_body(self) -> str:
        return self.pose.get("body_position", "standing")

    @property
    def pose_torso(self) -> str:
        return self.pose.get("torso_angle", "frontal")

    @property
    def pose_head(self) -> str:
        return self.pose.get("head_position", "straight")

    @property
    def pose_arm_left(self) -> str:
        return self.pose.get("arm_left", "natural")

    @property
    def pose_arm_right(self) -> str:
        return self.pose.get("arm_right", "natural")

    @property
    def pose_leg_left(self) -> str:
        return self.pose.get("leg_left", "standing")

    @property
    def pose_leg_right(self) -> str:
        return self.pose.get("leg_right", "standing")

    @property
    def bg_setting(self) -> str:
        return self.background.get("setting", "studio")

    @property
    def bg_tone(self) -> str:
        return self.background.get("color_tone", "neutral")

    @property
    def bg_lighting(self) -> str:
        return self.background.get("lighting", "soft")

    @property
    def comp_framing(self) -> str:
        return self.composition.get("framing", "full body")

    @property
    def comp_angle(self) -> str:
        return self.composition.get("camera_angle", "eye level")

    @property
    def comp_position(self) -> str:
        return self.composition.get("subject_position", "center")

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return self._raw


def analyze_source(
    client: genai.Client,
    source_image: Image.Image,
    prompt: Optional[str] = None,
) -> SourceAnalysisResult:
    """
    소스 이미지에서 얼굴/포즈/배경 추출

    Args:
        client: Gemini API 클라이언트
        source_image: 소스 이미지 (PIL Image)
        prompt: 커스텀 프롬프트 (없으면 기본 템플릿 사용)

    Returns:
        SourceAnalysisResult: 분석 결과 객체
    """
    analysis_prompt = prompt or SOURCE_ANALYSIS_PROMPT

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=analysis_prompt),
                    pil_to_part(source_image),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"],
        ),
    )

    text = response.candidates[0].content.parts[0].text

    # JSON 파싱
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        # 기본값 반환
        data = {
            "face": {"position": "center", "angle": "frontal", "expression": "neutral"},
            "pose": {"body_position": "standing", "torso_angle": "frontal"},
            "background": {"setting": "studio", "color_tone": "neutral"},
            "composition": {"framing": "full body", "camera_angle": "eye level"},
        }

    return SourceAnalysisResult(data)


def analyze_source_from_path(
    client: genai.Client,
    source_path: str,
    prompt: Optional[str] = None,
) -> SourceAnalysisResult:
    """
    소스 이미지 경로에서 얼굴/포즈/배경 추출

    Args:
        client: Gemini API 클라이언트
        source_path: 소스 이미지 경로
        prompt: 커스텀 프롬프트 (없으면 기본 템플릿 사용)

    Returns:
        SourceAnalysisResult: 분석 결과 객체
    """
    img = Image.open(source_path).convert("RGB")
    return analyze_source(client, img, prompt)


# ============================================================
# 태스크 요구 인터페이스 - 단순 dict 반환 버전
# ============================================================


def analyze_source_for_swap(
    source_image: "Image.Image | str",
    client: Any,
) -> dict:
    """
    소스 이미지를 분석하여 착장 스왑 시 보존해야 할 요소를 추출

    SOURCE_ANALYSIS_PROMPT를 사용하여 얼굴/포즈/배경 정보를 추출한다.
    착장(옷)은 분석에서 제외하고 보존 대상 요소만 반환한다.

    Args:
        source_image: PIL 이미지 객체 또는 이미지 파일 경로
        client: Gemini API 클라이언트 (genai.Client)

    Returns:
        dict with keys:
            face_description (str): 얼굴 위치/각도/표정/피부톤 요약
            pose_description (str): 전체 포즈 상세 설명
            body_type (str): 체형 및 프레이밍 요약
            background_description (str): 배경 설정/색조/조명 설명
    """
    # 이미지 로드
    if isinstance(source_image, str):
        pil_img = Image.open(source_image).convert("RGB")
    else:
        pil_img = source_image

    # VLM 호출 — SOURCE_ANALYSIS_PROMPT 사용
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=SOURCE_ANALYSIS_PROMPT),
                    pil_to_part(pil_img),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_modalities=["TEXT"],
        ),
    )

    text = response.candidates[0].content.parts[0].text

    # JSON 파싱
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        raw = json.loads(text.strip())
    except json.JSONDecodeError:
        raw = {}

    face = raw.get("face", {})
    pose = raw.get("pose", {})
    bg = raw.get("background", {})
    comp = raw.get("composition", {})

    # 사람이 읽기 쉬운 요약 문자열로 변환
    face_description = (
        f"position={face.get('position', 'center')}, "
        f"angle={face.get('angle', 'frontal')}, "
        f"expression={face.get('expression', 'neutral')}, "
        f"skin_tone={face.get('skin_tone', 'medium')}"
    )

    pose_parts = [
        f"body={pose.get('body_position', 'standing')}",
        f"torso={pose.get('torso_angle', 'frontal')}",
        f"head={pose.get('head_position', 'straight')}",
        f"arm_left={pose.get('arm_left', 'hanging naturally')}",
        f"arm_right={pose.get('arm_right', 'hanging naturally')}",
        f"leg_left={pose.get('leg_left', 'straight')}",
        f"leg_right={pose.get('leg_right', 'straight')}",
    ]
    pose_description = ", ".join(pose_parts)

    body_type = (
        f"framing={comp.get('framing', 'full body')}, "
        f"camera_angle={comp.get('camera_angle', 'eye level')}, "
        f"subject_position={comp.get('subject_position', 'center')}"
    )

    background_description = (
        f"setting={bg.get('setting', 'studio backdrop')}, "
        f"color_tone={bg.get('color_tone', 'neutral')}, "
        f"lighting={bg.get('lighting', 'soft diffused daylight')}, "
        f"direction={bg.get('lighting_direction', 'frontal')}"
    )

    return {
        "face_description": face_description,
        "pose_description": pose_description,
        "body_type": body_type,
        "background_description": background_description,
        # 원본 구조화 데이터도 포함 (prompt_builder에서 활용 가능)
        "_raw": raw,
    }


def analyze_outfit_items(
    outfit_images: "list[Image.Image | str]",
    client: Any,
) -> list[dict]:
    """
    착장 이미지 목록을 개별 분석하여 아이템 정보를 반환

    OUTFIT_ANALYSIS_PROMPT를 사용하여 각 아이템의 타입/색상/소재/로고/디테일을 추출한다.
    최대 10개 아이템까지 처리한다.

    Args:
        outfit_images: PIL 이미지 또는 파일 경로 목록 (최대 10개)
        client: Gemini API 클라이언트 (genai.Client)

    Returns:
        list of dicts, each with keys:
            item_type (str): 의류 타입 (e.g. "hoodie", "pants", "cap")
            color (str): 색상 + 톤 설명 (e.g. "dark charcoal gray")
            material (str): 소재 텍스처 설명 (e.g. "cotton fleece")
            logo (str | None): 로고 텍스트 (없으면 None)
            details (list[str]): 디자인 디테일 목록
            prompt_description (str): AI 생성용 영어 one-liner 설명
    """
    # 최대 10개 제한
    images_to_process = outfit_images[:10]
    results = []

    for idx, img_input in enumerate(images_to_process):
        # 이미지 로드
        if isinstance(img_input, str):
            try:
                pil_img = Image.open(img_input).convert("RGB")
            except Exception as e:
                print(f"[outfit_swap] 착장 이미지 {idx + 1} 로드 실패: {e}")
                # 폴백 값 추가
                results.append(_fallback_outfit_item(idx))
                continue
        else:
            pil_img = img_input

        # VLM 호출 — OUTFIT_ANALYSIS_PROMPT 사용
        try:
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=OUTFIT_ANALYSIS_PROMPT),
                            pil_to_part(pil_img),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"],
                ),
            )

            text = response.candidates[0].content.parts[0].text

            # JSON 파싱
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            raw = json.loads(text.strip())

        except json.JSONDecodeError:
            print(f"[outfit_swap] 착장 {idx + 1} JSON 파싱 실패, 폴백 사용")
            results.append(_fallback_outfit_item(idx))
            continue
        except Exception as e:
            print(f"[outfit_swap] 착장 {idx + 1} VLM 호출 실패: {e}")
            results.append(_fallback_outfit_item(idx))
            continue

        # 로고 정보 정규화
        logo_data = raw.get("logo", {})
        if isinstance(logo_data, dict):
            logo_text = (
                logo_data.get("text") if logo_data.get("exists", False) else None
            )
        else:
            logo_text = None

        # details 정규화 — 문자열이면 리스트로 분리
        details_raw = raw.get("details", "")
        if isinstance(details_raw, list):
            details = details_raw
        elif isinstance(details_raw, str) and details_raw:
            details = [d.strip() for d in details_raw.split(",") if d.strip()]
        else:
            details = []

        results.append(
            {
                "item_type": raw.get("item_type", "garment"),
                "color": raw.get("color", "unknown color"),
                "material": raw.get("material", "fabric"),
                "logo": logo_text,
                "details": details,
                "prompt_description": raw.get("prompt_description", ""),
            }
        )

    return results


def _fallback_outfit_item(idx: int) -> dict:
    """착장 분석 실패 시 폴백 아이템"""
    return {
        "item_type": f"garment_{idx + 1}",
        "color": "unknown",
        "material": "fabric",
        "logo": None,
        "details": [],
        "prompt_description": f"outfit item {idx + 1}",
    }
