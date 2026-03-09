"""
브랜드컷 편집 모드 Generator

기존 A컷 이미지를 기반으로 착장/배경만 변경.
얼굴, 표정, 포즈는 최대한 유지.

Usage:
    from core.brandcut import edit_brandcut, edit_with_validation

    # 단순 편집
    result = edit_brandcut(
        source_image=pil_image,
        outfit_description="아이스블루 패딩, 블랙 크롭탑...",
        background_description="차고, 험머 SUV",
        api_key=api_key
    )

    # 편집 + 검증 + 재시도
    result = edit_with_validation(
        source_image=pil_image,
        outfit_description="...",
        background_description="...",
        api_key=api_key,
        max_retries=2
    )
"""

import time
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL


def pil_to_part(img: Image.Image, max_size: int = 1200) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def build_edit_prompt(
    outfit_description: str,
    background_description: str,
    style_notes: str = "",
    strict_preservation: bool = True,
) -> str:
    """편집 모드 프롬프트 생성

    Note: 표정은 언급 안함 - 언급하면 오히려 딱딱해짐.
          살짝 변형되도 괜찮음.
    """

    preserve_section = (
        """
[절대 변경 금지]
- 얼굴 (눈, 코, 입, 턱선, 피부 전부 그대로)
- 헤어스타일
- 포즈
- 신체 비율
"""
        if strict_preservation
        else """
[유지할 것]
- 얼굴 (동일 인물)
- 신체 비율
"""
    )

    prompt = f"""
이 이미지를 편집해줘.

{preserve_section}

[변경할 것 - 착장]
현재 입고 있는 옷을 다음으로 교체:
{outfit_description}

[변경할 것 - 배경]
현재 배경을 다음으로 교체:
{background_description}

[스타일]
{style_notes if style_notes else "한국 패션 매거진 화보 느낌. 피부는 촉촉하고 자연스럽게."}

[금지]
- 얼굴 변형 (다른 사람으로 바뀌면 안됨)
- AI look, plastic skin
- 시골 정비소, 지저분한 배경, 잡동사니

얼굴은 1픽셀도 바꾸지 마. 100% 동일 인물 유지.
착장과 배경만 자연스럽게 합성해.
"""
    return prompt


def edit_brandcut(
    source_image: Image.Image,
    outfit_description: str,
    background_description: str,
    api_key: str,
    style_notes: str = "",
    strict_preservation: bool = True,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    temperature: float = 0.5,
) -> Image.Image | None:
    """
    기존 이미지를 편집하여 착장/배경만 변경

    Args:
        source_image: 원본 A컷 이미지 (PIL Image)
        outfit_description: 변경할 착장 설명
        background_description: 변경할 배경 설명
        api_key: Gemini API 키
        style_notes: 추가 스타일 지시 (선택)
        strict_preservation: 얼굴/포즈 엄격 보존 (기본 True). 표정은 자연스럽게 변할 수 있음.
        aspect_ratio: 출력 비율
        resolution: 출력 해상도
        temperature: 생성 온도 (편집은 낮게 권장)

    Returns:
        편집된 이미지 또는 None
    """
    client = genai.Client(api_key=api_key)

    parts = []

    # 원본 이미지
    parts.append(types.Part(text="[원본 이미지]"))
    parts.append(pil_to_part(source_image))

    # 편집 프롬프트
    prompt = build_edit_prompt(
        outfit_description=outfit_description,
        background_description=background_description,
        style_notes=style_notes,
        strict_preservation=strict_preservation,
    )
    parts.append(types.Part(text=prompt))

    max_retries = 3
    for retry in range(max_retries):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio, image_size=resolution
                    ),
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))
            return None

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "503" in error_str:
                if retry < max_retries - 1:
                    wait = (retry + 1) * 5
                    print(f"[edit_brandcut] Rate limit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
            print(f"[edit_brandcut] Error: {e}")
            return None

    return None


def edit_with_validation(
    source_image: Image.Image,
    outfit_description: str,
    background_description: str,
    api_key: str,
    outfit_images: list[Image.Image] | None = None,
    style_notes: str = "",
    strict_preservation: bool = True,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    temperature: float = 0.5,
    max_retries: int = 2,
) -> dict:
    """
    편집 + 검증 + 재시도 루프

    Args:
        source_image: 원본 A컷 이미지
        outfit_description: 착장 설명
        background_description: 배경 설명
        api_key: API 키
        outfit_images: 착장 참조 이미지 (검증용)
        style_notes: 스타일 노트
        strict_preservation: 얼굴/포즈 엄격 보존 (표정은 자연스럽게 변할 수 있음)
        aspect_ratio: 비율
        resolution: 해상도
        temperature: 온도
        max_retries: 최대 재시도 횟수

    Returns:
        {
            "image": PIL.Image or None,
            "passed": bool,
            "score": int,
            "attempts": int,
            "history": list
        }
    """
    from .validator_v2 import BrandcutValidator

    history = []
    best_image = None
    best_score = 0

    client = genai.Client(api_key=api_key)
    validator = BrandcutValidator(client)

    for attempt in range(max_retries + 1):
        print(f"[edit_with_validation] Attempt {attempt + 1}/{max_retries + 1}")

        # 편집 실행
        image = edit_brandcut(
            source_image=source_image,
            outfit_description=outfit_description,
            background_description=background_description,
            api_key=api_key,
            style_notes=style_notes,
            strict_preservation=strict_preservation,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )

        if image is None:
            history.append({"attempt": attempt + 1, "error": "Generation failed"})
            continue

        # 검증 (outfit_images가 있으면 사용)
        reference_images = {
            "face": [source_image],  # 원본 이미지를 얼굴 참조로
        }
        if outfit_images:
            reference_images["outfit"] = outfit_images

        try:
            result = validator.validate(image, reference_images)
            score = result.total_score

            history.append(
                {
                    "attempt": attempt + 1,
                    "score": score,
                    "passed": result.passed,
                    "criteria": result.criteria_scores,
                }
            )

            if score > best_score:
                best_score = score
                best_image = image

            if result.passed:
                print(f"[edit_with_validation] Passed with score {score}")
                return {
                    "image": image,
                    "passed": True,
                    "score": score,
                    "attempts": attempt + 1,
                    "history": history,
                }

            print(f"[edit_with_validation] Score {score}, retrying...")

        except Exception as e:
            print(f"[edit_with_validation] Validation error: {e}")
            history.append({"attempt": attempt + 1, "error": str(e)})
            # 검증 실패해도 이미지는 저장
            if best_image is None:
                best_image = image
                best_score = 0

        if attempt < max_retries:
            time.sleep(2)

    # 모든 시도 실패 시 최고 점수 이미지 반환
    return {
        "image": best_image,
        "passed": False,
        "score": best_score,
        "attempts": max_retries + 1,
        "history": history,
    }


# 편의 함수: 착장 설명 빌더
def build_outfit_description(
    outer: str = "",
    top: str = "",
    bottom: str = "",
    headwear: str = "",
    accessories: list[str] | None = None,
) -> str:
    """착장 설명 문자열 생성"""
    parts = []
    if outer:
        parts.append(f"- 아우터: {outer}")
    if top:
        parts.append(f"- 상의: {top}")
    if bottom:
        parts.append(f"- 하의: {bottom}")
    if headwear:
        parts.append(f"- 모자: {headwear}")
    if accessories:
        for acc in accessories:
            parts.append(f"- 액세서리: {acc}")
    return "\n".join(parts)
