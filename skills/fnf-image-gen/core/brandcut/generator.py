"""
이미지 생성 모듈 - 순수 브랜드컷 생성만 담당

역할: 프롬프트 + 참조 이미지 → 이미지 생성
검증/재시도 로직은 retry_generator.py에서 처리
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
    style_reference: Optional[Image.Image] = None,
    api_key: Optional[str] = None,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    temperature: float = 0.25,
) -> Union[Optional[Image.Image], List[Optional[Image.Image]]]:
    """
    브랜드컷 이미지 생성 (단일 또는 배치)

    순수 생성만 담당. 검증/재시도는 retry_generator.py에서 처리.

    Args:
        prompt_json: 프롬프트 JSON 객체 (치트시트 기반)
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록 (최우선)
        pose_reference: 포즈 레퍼런스 이미지 (선택)
        style_reference: 스타일 레퍼런스 이미지 (선택) - 무드/조명/분위기 복사
        api_key: Gemini API 키
        num_images: 생성할 이미지 수량 (기본 1)
        aspect_ratio: 화면 비율 (기본 3:4)
        resolution: 해상도 (1K/2K/4K)
        temperature: 생성 온도 (기본 0.25)

    Returns:
        num_images == 1: PIL.Image (실패 시 None)
        num_images > 1: List[PIL.Image] (각 이미지, 실패 시 None 포함)
    """
    # 배치 모드
    if num_images > 1:
        return _generate_batch(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            style_reference=style_reference,
            api_key=api_key,
            num_images=num_images,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )

    # 단일 모드
    # API 키 처리
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # 프롬프트 텍스트 (한국어 레이어 우선)
    if "_korean_prompt" in prompt_json:
        prompt_text = prompt_json["_korean_prompt"]
        # JSON도 함께 전송 (착장 정확도용)
        prompt_text += (
            f"\n\n[JSON Reference]\n{json.dumps(prompt_json, ensure_ascii=False)}"
        )
    else:
        prompt_text = json.dumps(prompt_json, ensure_ascii=False)

    # API 파트 구성 - 순서 중요!
    # 1. 포즈 레퍼런스 (최우선, 맨 앞에 배치)
    # 2. 프롬프트 텍스트
    # 3. 포즈 상세 정보
    # 4. 얼굴 이미지
    # 5. 착장 이미지

    parts = []

    # ============================================================
    # 1. 포즈 레퍼런스 (최우선 - 맨 앞에 배치!)
    # ============================================================
    if pose_reference is not None:
        parts.append(
            types.Part(
                text="""★★★★★ POSE REFERENCE - COPY THIS EXACTLY! ★★★★★

⚠️⚠️⚠️ THIS IMAGE IS THE MOST IMPORTANT INPUT! ⚠️⚠️⚠️

YOU MUST MATCH EXACTLY:

1. CAMERA ANGLE (카메라 앵글) - CRITICAL!
   - LOW ANGLE (로우앵글) = 아래에서 위로 올려다봄
   - EYE LEVEL (아이레벨) = 눈높이
   - HIGH ANGLE (하이앵글) = 위에서 아래로 내려다봄
   → IF REFERENCE IS LOW ANGLE, YOURS MUST BE LOW ANGLE!

2. FRAMING (구도) - CRITICAL!
   - FULL BODY (전신) = 머리부터 발끝까지
   - KNEE-UP (무릎위) = 머리부터 무릎까지
   - WAIST-UP (허리위) = 머리부터 허리까지
   → IF REFERENCE SHOWS FULL BODY, YOURS MUST SHOW FULL BODY!

3. LEG POSITION (다리) - CRITICAL!
   - SPREAD APART (벌림) = 다리를 넓게 벌림
   - TOGETHER (모음) = 다리를 모음
   - ONE BENT (한쪽 구부림) = 한쪽만 구부림
   → COPY THE EXACT LEG POSITION FROM REFERENCE!

❌ WRONG (이렇게 하면 REJECTED):
- Reference: LOW ANGLE → Generated: EYE LEVEL
- Reference: FULL BODY → Generated: HALF BODY
- Reference: LEGS SPREAD → Generated: LEGS TOGETHER

✅ RIGHT (이렇게 해야 함):
- Reference: LOW ANGLE → Generated: LOW ANGLE ✓
- Reference: FULL BODY → Generated: FULL BODY ✓
- Reference: LEGS SPREAD → Generated: LEGS SPREAD ✓

NOW STUDY THIS REFERENCE IMAGE:"""
            )
        )
        parts.append(pil_to_part(pose_reference))
        parts.append(
            types.Part(
                text="""
★★★ REMINDER: COPY THE ABOVE IMAGE'S ANGLE, FRAMING, AND LEG POSITION! ★★★
"""
            )
        )

    # ============================================================
    # 2. 프롬프트 텍스트
    # ============================================================
    parts.append(types.Part(text=prompt_text))

    # ============================================================
    # 2.5. 스타일 레퍼런스 (프롬프트 다음, 얼굴 이미지 전)
    #      인플루언서 패턴: prompt -> style -> face -> outfit
    # ============================================================
    if style_reference is not None:
        parts.append(
            types.Part(
                text="""[STYLE REFERENCE] - MLB Brand Editorial Style:

COPY FROM THIS IMAGE:
- Overall mood and atmosphere
- Lighting quality and color temperature (cool tones only)
- Editorial fashion photography style
- Premium, high-end feel

DO NOT COPY:
- Face (use FACE REFERENCE instead)
- Outfit (use OUTFIT REFERENCE instead)
- Exact pose (use POSE REFERENCE if provided)

MATCH the photographic quality and fashion magazine aesthetic."""
            )
        )
        parts.append(pil_to_part(style_reference))

    # 포즈/촬영/표정 정보를 별도로 강조 (JSON에서 추출)
    pose_info = prompt_json.get("포즈", {})
    camera_info = prompt_json.get("촬영", {})
    expression_info = prompt_json.get("표정", {})

    if pose_info or camera_info or expression_info:
        pose_emphasis = f"""
[★★★ POSE/CAMERA/EXPRESSION DETAILS - MUST FOLLOW EXACTLY ★★★]

## 촬영 (CAMERA) - 반드시 따라하세요!
- 높이/앵글: {camera_info.get("높이", "눈높이")}
- 프레이밍: {camera_info.get("프레이밍", "MS")}

## 포즈 (POSE) - 각 부위별로 정확히 따라하세요!
- 기본자세(stance): {pose_info.get("stance", "stand")}
- 체중분배: {pose_info.get("체중분배", "균등")}
- 몸방향: {pose_info.get("몸방향", "정면")}
- 왼팔: {pose_info.get("왼팔", "natural")}
- 오른팔: {pose_info.get("오른팔", "relaxed")}
- 왼손: {pose_info.get("왼손", "relaxed")}
- 오른손: {pose_info.get("오른손", "relaxed")}
- 왼다리: {pose_info.get("왼다리", "support")}
- 오른다리: {pose_info.get("오른다리", "knee_10")}
- 다리간격: {pose_info.get("다리간격", "어깨너비")}
- 어깨: {pose_info.get("어깨", "수평")}
- 상체: {pose_info.get("상체", "똑바로")}
- 머리: {pose_info.get("머리", "정면")}
- 힙: {pose_info.get("힙", "neutral")}

## 표정 (EXPRESSION) - 레퍼런스와 동일하게!
- 베이스무드: {expression_info.get("베이스", "cool")}
- 바이브: {expression_info.get("바이브", "mysterious")}
- 시선: {expression_info.get("시선", "direct")}
- 입: {expression_info.get("입", "closed")}
- 눈: {expression_info.get("눈", "natural")}
- 눈썹: {expression_info.get("눈썹", "natural")}

⚠️ 위 정보와 다르게 생성하면 REJECTED됩니다!
"""
        parts.append(types.Part(text=pose_emphasis))

    # ============================================================
    # 3. 착장 정보 강조 (prompt_json에서 동적 추출)
    # ============================================================
    outfit_info = prompt_json.get("착장", {})
    if outfit_info:
        # 프롬프트가 있는 아이템만 추출
        outfit_lines = []
        for category, data in outfit_info.items():
            if isinstance(data, dict) and data.get("프롬프트"):
                outfit_lines.append(f"- {category}: {data['프롬프트']}")

        if outfit_lines:
            outfit_emphasis = f"""
[★★★ OUTFIT DETAILS - MUST MATCH EXACTLY ★★★]

## 착장 아이템 (반드시 모두 포함!)
{chr(10).join(outfit_lines)}

⚠️ CRITICAL OUTFIT RULES:
1. EVERY item above MUST appear in the generated image
2. COLORS must match exactly (e.g., "brown with cream" = brown + cream)
3. LOGOS and PATTERNS must be preserved
4. FIT must match (oversized, cropped, wide, etc.)
5. STYLING must match (off-shoulder, worn normally, etc.)

❌ WRONG: Missing any item, wrong color, missing logo
✅ RIGHT: All items visible with correct colors and details
"""
            parts.append(types.Part(text=outfit_emphasis))

    # 얼굴 이미지 전체 전송
    for i, img_input in enumerate(face_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(
                text=f"""
[CRITICAL] [FACE REFERENCE {i+1}] - COPY THIS FACE EXACTLY! [CRITICAL]

[!][!][!] THIS PERSON'S FACE MUST BE PRESERVED 100% [!][!][!]

YOU MUST MATCH:
- Eye shape (double eyelid, eye size, eye corners)
- Nose (bridge, tip, nostrils)
- Lips (thickness, philtrum)
- Jawline (chin line)
- Cheekbones (prominence)

[X] WRONG: Different person's face
[OK] RIGHT: 100% same person, recognizable immediately

FACE IDENTITY FAILURE = AUTOMATIC REJECTION
"""
            )
        )
        parts.append(pil_to_part(img))

    # 착장 이미지 전체 전송 (1순위)
    for i, img_input in enumerate(outfit_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(text=f"[OUTFIT REFERENCE {i+1}] - Copy this outfit exactly:")
        )
        parts.append(pil_to_part(img))

    # 최대 3회 재시도 (API 에러용)
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

            # 재시도 가능 에러 판별
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
    style_reference: Optional[Image.Image],
    api_key: Optional[str],
    num_images: int,
    aspect_ratio: str,
    resolution: str,
    temperature: float,
) -> List[Optional[Image.Image]]:
    """
    배치 이미지 생성 (순수 생성만, 검증 없음)

    Args:
        num_images: 생성할 이미지 수량

    Returns:
        List[PIL.Image]: 생성된 이미지 목록 (실패한 이미지는 None)
    """
    print(f"\n[Generator] Batch: {num_images} images | {aspect_ratio} | {resolution}")

    images = []
    for i in range(num_images):
        print(f"[Generator] Generating {i + 1}/{num_images}...")

        # 단일 이미지 생성 (재귀 호출)
        img = generate_brandcut(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            style_reference=style_reference,
            api_key=api_key,
            num_images=1,  # 단일 모드로 호출
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )
        images.append(img)

        if img:
            print(f"[Generator] {i + 1}/{num_images} OK")
        else:
            print(f"[Generator] {i + 1}/{num_images} FAILED")

        # Rate limit 방지 (마지막 제외)
        if i < num_images - 1:
            time.sleep(1)

    success = sum(1 for img in images if img is not None)
    print(f"[Generator] Batch complete: {success}/{num_images} success")

    return images
