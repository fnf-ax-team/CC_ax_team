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
from .templates import SOURCE_ANALYSIS_PROMPT


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

    공통 OutfitAnalyzer를 통해 이미지당 개별 분석 후 착장스왑 포맷으로 변환한다.
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
    from core.modules.analyze_outfit import analyze_outfit, to_outfit_swap_dict

    analyses = analyze_outfit(
        images=outfit_images[:10],
        client=client,
        detail_level="full",
        per_image=True,
    )

    return [to_outfit_swap_dict(a) for a in analyses]
