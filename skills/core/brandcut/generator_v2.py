"""
이미지 생성 모듈 v2

변경점 (v1 대비):
1. expression_reference 추가 (K-Beauty 표정)
2. 이미지 전송 순서 최적화: 얼굴 → 착장 → 포즈
3. prompt_builder_v2의 korean_prompt 직접 사용
"""

import json
import time
from io import BytesIO
from typing import Optional, List, Union
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def generate_brandcut(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    pose_reference: Optional[Image.Image] = None,
    expression_reference: Optional[Image.Image] = None,  # K-Beauty 표정 레퍼런스
    style_reference: Optional[Image.Image] = None,  # 스타일 레퍼런스
    api_key: Optional[str] = None,
    num_images: int = 1,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    temperature: float = 0.7,
) -> Union[Optional[Image.Image], List[Optional[Image.Image]]]:
    """
    브랜드컷 이미지 생성 (v2)

    변경점:
    - expression_reference 추가 (K-Beauty 표정)
    - 전송 순서: 프롬프트 → 얼굴 → 착장 → 포즈

    Args:
        prompt_json: 프롬프트 JSON (korean_prompt 필드 포함)
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록
        pose_reference: 포즈 레퍼런스 (선택) - 포즈/앵글/프레이밍 복사
        expression_reference: 표정 레퍼런스 (선택) - K-Beauty 표정 복사
        style_reference: 스타일 레퍼런스 (선택) - 전체 스타일 참조
        api_key: Gemini API 키
        num_images: 생성할 이미지 수량
        aspect_ratio: 화면 비율
        resolution: 해상도
        temperature: 생성 온도

    Returns:
        PIL.Image 또는 List[PIL.Image]
    """
    # 배치 모드
    if num_images > 1:
        return _generate_batch(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            expression_reference=expression_reference,
            style_reference=style_reference,
            api_key=api_key,
            num_images=num_images,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )

    # API 키 처리
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # ============================================================
    # 프롬프트 텍스트 (korean_prompt 우선)
    # ============================================================
    if "korean_prompt" in prompt_json:
        prompt_text = prompt_json["korean_prompt"]
    elif "_korean_prompt" in prompt_json:  # 하위 호환
        prompt_text = prompt_json["_korean_prompt"]
    else:
        prompt_text = json.dumps(prompt_json, ensure_ascii=False)

    # 재시도 강화 텍스트 추가
    for key in [
        "_outfit_enhancement",
        "_face_enhancement",
        "_brand_enhancement",
        "_aesthetic_enhancement",
        "_pose_enhancement",
        "_RETRY_NOTES",
    ]:
        if key in prompt_json:
            prompt_text += f"\n\n{prompt_json[key]}"

    # ============================================================
    # API 파트 구성 - 순서 최적화!
    # 1. 프롬프트 텍스트
    # 2. 얼굴 이미지 (최우선 - 동일성 중요)
    # 3. 착장 이미지 (2순위 - 디테일 중요)
    # 4. 포즈 레퍼런스 (있으면)
    # ============================================================

    parts = []

    # ============================================================
    # 0. 표정 레퍼런스 - 가장 먼저! (있을 경우)
    # ============================================================
    if expression_reference is not None:
        expr_info = prompt_json.get("표정", {})
        expr_text = expr_info.get("prompt_text", "")
        is_warm = any(
            w in str(expr_info).lower()
            for w in ["warm", "lovely", "smile", "soft", "dreamy"]
        )

        # VLM 분석 없이 강제 지시
        anti_smile = "" if is_warm else "\n- DO NOT SMILE. NO TEETH."

        parts.append(
            types.Part(
                text=f"""
★★★★★ EXPRESSION REFERENCE - COPY THIS EXACTLY! ★★★★★

MOST IMPORTANT INSTRUCTION: Copy the EXACT expression from this reference image!

This reference shows the EXACT facial expression you must recreate:
- Copy the EXACT eye openness (how open/closed the eyes are)
- Copy the EXACT mouth state (parted, closed, etc.)
- Copy the EXACT gaze direction
- Copy the EXACT overall mood/vibe
{anti_smile}

{f'Target expression: {expr_text}' if expr_text else ''}

DO NOT change this expression! DO NOT make it more "pleasant" or "photogenic"!
The expression in this reference is EXACTLY what we want!

EXPRESSION REFERENCE IMAGE (copy this expression):
"""
            )
        )
        parts.append(pil_to_part(expression_reference))

    # 1. 프롬프트 텍스트
    parts.append(types.Part(text=prompt_text))

    # ============================================================
    # 2. 얼굴 이미지 (최우선)
    # ============================================================
    for i, img_input in enumerate(face_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(
                text=f"""
[얼굴 레퍼런스 {i+1}] - 이 얼굴을 100% 동일하게!

반드시 일치시킬 것:
- 눈 모양 (쌍꺼풀, 크기, 눈꼬리)
- 코 (콧대, 코끝, 콧볼)
- 입술 (두께, 인중)
- 턱선 (각도)
- 광대뼈

다른 사람 얼굴 = 자동 탈락!
"""
            )
        )
        parts.append(pil_to_part(img))

    # ============================================================
    # 3. 착장 이미지 (2순위)
    # ============================================================

    # 착장 상세 정보 추출
    outfit_details = prompt_json.get("착장", {})
    outfit_summary_lines = []
    for category, data in outfit_details.items():
        if isinstance(data, dict) and data.get("프롬프트"):
            outfit_summary_lines.append(f"- {category}: {data['프롬프트']}")

    outfit_summary = (
        "\n".join(outfit_summary_lines)
        if outfit_summary_lines
        else "(착장 이미지 참조)"
    )

    parts.append(
        types.Part(
            text=f"""
[착장 - 모든 아이템 필수!]

{outfit_summary}

착장 규칙:
1. 위 아이템 전부 포함 (하나도 빠지면 탈락)
2. 색상 정확히 일치 (brown ≠ black)
3. 로고 위치와 디자인 그대로
4. 옷의 핏/스타일링 유지

아래 착장 이미지를 정확히 따라하세요:
"""
        )
    )

    for i, img_input in enumerate(outfit_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(types.Part(text=f"[착장 이미지 {i+1}]"))
        parts.append(pil_to_part(img))

    # ============================================================
    # 4. 포즈 레퍼런스 (있으면)
    # ============================================================
    if pose_reference is not None:
        parts.append(
            types.Part(
                text="""
[포즈 레퍼런스] - 포즈만 따라하기!

이 이미지에서 따라할 것:
- 카메라 앵글 (로우/아이레벨/하이)
- 프레이밍 (전신/무릎/허리)
- 다리 위치와 간격
- 팔 위치
- 몸의 방향

따라하지 않을 것:
- 얼굴 (얼굴 레퍼런스 사용)
- 착장 (착장 레퍼런스 사용)
- 배경
- 조명/색감 (무드 레퍼런스 사용)

포즈 레퍼런스 이미지:
"""
            )
        )
        parts.append(pil_to_part(pose_reference))

    # (표정 레퍼런스는 맨 앞 section 0에서 처리됨)

    # ============================================================
    # 5. 마지막 강조
    # ============================================================
    # 표정 레퍼런스가 있으면 체크리스트에 포함
    expr_check = (
        "- [ ] 표정: 표정 레퍼런스와 100% 동일 (눈, 입, 분위기)"
        if expression_reference
        else ""
    )

    parts.append(
        types.Part(
            text=f"""
[최종 체크리스트]
- [ ] 얼굴: 레퍼런스와 100% 동일한 사람
- [ ] 착장: 모든 아이템 포함, 색상/로고 정확
{expr_check}
- [ ] 포즈: 레퍼런스와 동일한 앵글/프레이밍
- [ ] 품질: 실사 같은 패션 화보

위 항목 중 하나라도 틀리면 탈락입니다!
"""
        )
    )

    # ============================================================
    # API 호출
    # ============================================================
    max_retries = 3
    for attempt in range(max_retries):
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

            # 이미지 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            print("[Generator] No image in response")
            return None

        except Exception as e:
            error_str = str(e).lower()

            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            if not is_retryable:
                print(f"[Generator] Error: {e}")
                return None

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[Generator] Retry {attempt + 1}/{max_retries} - waiting {wait_time}s"
                )
                time.sleep(wait_time)
            else:
                print(f"[Generator] Max retries exceeded: {e}")

    return None


def _generate_batch(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    pose_reference: Optional[Image.Image],
    expression_reference: Optional[Image.Image],
    style_reference: Optional[Image.Image],
    api_key: Optional[str],
    num_images: int,
    aspect_ratio: str,
    resolution: str,
    temperature: float,
) -> List[Optional[Image.Image]]:
    """배치 이미지 생성"""
    print(f"\n[Generator] Batch: {num_images} images | {aspect_ratio} | {resolution}")

    images = []
    for i in range(num_images):
        print(f"[Generator] Generating {i + 1}/{num_images}...")

        img = generate_brandcut(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            expression_reference=expression_reference,
            style_reference=style_reference,
            api_key=api_key,
            num_images=1,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )
        images.append(img)

        if img:
            print(f"[Generator] {i + 1}/{num_images} OK")
        else:
            print(f"[Generator] {i + 1}/{num_images} FAILED")

        if i < num_images - 1:
            time.sleep(1)

    success = sum(1 for img in images if img is not None)
    print(f"[Generator] Batch complete: {success}/{num_images} success")

    return images


__all__ = ["generate_brandcut", "pil_to_part"]
