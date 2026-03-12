"""Gemini 스타트프레임 이미지 생성 모듈.

뷰티 영상 시나리오의 각 컷에 대해
Gemini gemini-3-pro-image-preview로 스타트프레임 이미지를 자동 생성한다.

사용법:
    from core.beauty_video.startframe import generate_startframes

    frames = await generate_startframes(
        scenario=scenario,
        source_images={"face": ["face.jpg"], "product": ["product.jpg"]},
        output_dir="outputs/startframes",
    )
    # frames = {"cut01_hook": "outputs/startframes/cut01_hook.jpg", ...}
"""

import io
import os
import asyncio
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from PIL import Image

from core.config import IMAGE_MODEL
from .presets import BEAUTY_CUT_TYPES


# ============================================================
# API Key Management (GEMINI_API_KEY 로테이션)
# ============================================================
_api_keys: Optional[List[str]] = None
_api_key_index = 0


def _get_next_api_key() -> str:
    """GEMINI_API_KEY에서 다음 API 키를 round-robin으로 반환한다."""
    global _api_keys, _api_key_index

    if _api_keys is None:
        api_key_str = os.getenv("GEMINI_API_KEY", "")
        _api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
        if not _api_keys:
            raise RuntimeError("GEMINI_API_KEY not found in environment")

    key = _api_keys[_api_key_index]
    _api_key_index = (_api_key_index + 1) % len(_api_keys)
    return key


# ============================================================
# 이미지 유틸리티
# ============================================================
def _load_image(path: Union[str, Path], max_size: int = 2048) -> Image.Image:
    """이미지 로드 + RGB 변환 + 리사이즈."""
    img = Image.open(path).convert("RGB")
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def _pil_to_part(img: Image.Image):
    """PIL Image를 Gemini Part로 변환한다."""
    from google.genai import types

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return types.Part(
        inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())
    )


def _extract_image_from_response(response) -> Optional[Image.Image]:
    """Gemini 응답에서 이미지를 추출한다."""
    if not response.candidates:
        return None
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            if part.inline_data.mime_type.startswith("image/"):
                return Image.open(BytesIO(part.inline_data.data)).convert("RGB")
    return None


# ============================================================
# 프롬프트 빌더
# ============================================================
def _build_startframe_prompt(
    cut: dict,
    scenario: dict,
) -> str:
    """컷 정보와 시나리오로 스타트프레임 생성 프롬프트를 조립한다.

    Args:
        cut: 컷 딕셔너리 (id, type, name, image_prompt 등)
        scenario: 시나리오 딕셔너리 (brand, product, description 등)

    Returns:
        프롬프트 문자열
    """
    # 커스텀 프롬프트가 있으면 그것을 우선 사용
    if cut.get("image_prompt"):
        return cut["image_prompt"]

    cut_type = cut.get("type", "hook")
    cut_name = cut.get("name", cut_type)
    brand = scenario.get("brand", "")
    product = scenario.get("product", "")
    description = scenario.get("description", "")

    # BEAUTY_CUT_TYPES에서 목적 가져오기
    cut_info = BEAUTY_CUT_TYPES.get(cut_type, BEAUTY_CUT_TYPES["hook"])
    purpose = cut_info["purpose"]

    # 시나리오 scene_description 가져오기 (있으면)
    scene_desc = cut.get("scene_description", "")

    prompt = f"""Create a high-quality beauty influencer photo for a short-form video (Reels/TikTok).

Brand: {brand}
Product: {product}
Cut: {cut_name} ({cut_type})
Purpose: {purpose}

Style Requirements:
- Korean beauty influencer aesthetic
- 9:16 vertical format, suitable as video start frame
- Natural, authentic selfie/vlog feel
- Soft, flattering lighting (ring light or natural window light)
- Clean, minimal background (bathroom mirror, vanity, bedroom)
- High-end beauty editorial quality with casual vibe

"""
    if scene_desc:
        prompt += f"Scene: {scene_desc}\n\n"

    # 컷 타입별 추가 지시
    type_instructions = {
        "hook": (
            "HOOK SHOT: Capture attention in first second. "
            "Close-up on face showing flawless skin with the product. "
            "Surprised/excited expression. Eye-catching composition."
        ),
        "apply": (
            "APPLICATION SHOT: Show the model applying the product. "
            "Close-up on hands and face. Natural, tutorial-style feel. "
            "Product clearly visible in hand or being applied."
        ),
        "proof": (
            "PROOF SHOT: Show lasting effect after hours. "
            "Mirror selfie or natural light. Dewy, glowing skin. "
            "Time-lapse feel - still looking fresh and beautiful."
        ),
        "cta": (
            "CTA/PRODUCT SHOT: Clean product lineup or product-in-hand. "
            "Product packaging clearly visible with brand name. "
            "Elegant, aspirational composition."
        ),
        "unboxing": (
            "UNBOXING SHOT: Fresh product packaging being opened. "
            "Clean background, hands visible. "
            "Excitement and anticipation feel."
        ),
        "swatch": (
            "SWATCH SHOT: Product swatch on skin (hand or arm). "
            "Close-up macro detail. Color accuracy important. "
            "Clean, bright lighting."
        ),
        "before_after": (
            "BEFORE/AFTER: Split or comparison composition. "
            "Same lighting, same angle. "
            "Clear difference visible (skin texture, glow, coverage)."
        ),
        "routine": (
            "ROUTINE/GRWM: Getting-ready scene. "
            "Bathroom or vanity setup with products visible. "
            "Morning routine feel, fresh and bright."
        ),
    }

    prompt += type_instructions.get(cut_type, type_instructions["hook"])

    prompt += """

CRITICAL:
- The person in ALL cuts must be the SAME person (preserve face identity from reference)
- Product must be clearly recognizable
- No text or watermark on the image
- Professional quality, sharp focus
- Skin texture must be natural (not plastic/AI-looking)
"""

    return prompt


# ============================================================
# 단일 컷 생성 (재시도 포함)
# ============================================================
async def _generate_single_startframe(
    cut: dict,
    scenario: dict,
    source_images: Dict[str, List[str]],
    output_dir: str,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    max_retries: int = 3,
) -> Dict[str, Any]:
    """단일 컷의 스타트프레임을 생성한다.

    Args:
        cut: 컷 딕셔너리
        scenario: 시나리오 딕셔너리
        source_images: {"face": [...], "product": [...]}
        output_dir: 출력 디렉토리
        aspect_ratio: 비율 (기본 9:16)
        resolution: 해상도 (기본 2K)
        max_retries: 최대 재시도 (기본 3)

    Returns:
        {"cut_id": str, "success": bool, "image_path": str, "error": str}
    """
    from google import genai
    from google.genai import types

    cut_id = cut["id"]
    prompt = _build_startframe_prompt(cut, scenario)

    # parts 조립
    parts = [types.Part(text=prompt)]

    # 얼굴 참조 이미지
    face_images = source_images.get("face", [])
    if face_images:
        parts.append(
            types.Part(
                text="=== FACE REFERENCE (SAME PERSON - preserve face identity exactly) ==="
            )
        )
        for i, face_path in enumerate(face_images[:3]):
            parts.append(types.Part(text=f"[Face {i+1}]"))
            img = _load_image(face_path)
            parts.append(_pil_to_part(img))

    # 제품 참조 이미지
    product_images = source_images.get("product", [])
    if product_images:
        parts.append(
            types.Part(text="=== PRODUCT REFERENCE (product must be recognizable) ===")
        )
        for i, prod_path in enumerate(product_images[:3]):
            parts.append(types.Part(text=f"[Product {i+1}]"))
            img = _load_image(prod_path)
            parts.append(_pil_to_part(img))

    # 생성 시도 (재시도 포함)
    for attempt in range(max_retries):
        try:
            api_key = _get_next_api_key()
            client = genai.Client(api_key=api_key)

            # 동기 호출을 asyncio에서 실행
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=resolution,
                        ),
                    ),
                ),
            )

            # 이미지 추출
            result_img = _extract_image_from_response(response)
            if result_img is None:
                raise RuntimeError("No image in response")

            # 저장
            out_path = Path(output_dir) / f"{cut_id}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            result_img.save(str(out_path), quality=95)

            w, h = result_img.size
            print(f"  [OK] {cut_id}: {w}x{h} -> {out_path}")

            return {
                "cut_id": cut_id,
                "success": True,
                "image_path": str(out_path),
            }

        except Exception as e:
            err_str = str(e).lower()
            retryable = any(
                kw in err_str
                for kw in ["429", "rate", "503", "overload", "timeout", "resource"]
            )

            if retryable and attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                print(
                    f"  [RETRY] {cut_id}: {e} (attempt {attempt+1}/{max_retries}, "
                    f"waiting {wait}s...)"
                )
                await asyncio.sleep(wait)
            else:
                print(f"  [FAIL] {cut_id}: {e}")
                return {
                    "cut_id": cut_id,
                    "success": False,
                    "image_path": "",
                    "error": str(e),
                }

    return {
        "cut_id": cut_id,
        "success": False,
        "image_path": "",
        "error": "Max retries exceeded",
    }


# ============================================================
# 메인: 전체 스타트프레임 병렬 생성
# ============================================================
async def generate_startframes(
    scenario: dict,
    source_images: Dict[str, List[str]],
    output_dir: str,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    max_retries: int = 3,
) -> Dict[str, str]:
    """시나리오 기반 스타트프레임 이미지 병렬 생성.

    image_path가 없거나 파일이 존재하지 않는 컷에 대해서만 생성한다.

    Args:
        scenario: 시나리오 딕셔너리 (brand, product, cuts 등)
        source_images: 참조 이미지 {"face": [...], "product": [...]}
        output_dir: 출력 디렉토리
        aspect_ratio: 비율 (기본 9:16 = 릴스/숏폼)
        resolution: 해상도 (기본 2K)
        max_retries: 최대 재시도 (기본 3)

    Returns:
        {"cut01_hook": "path/to/image.jpg", ...}
        생성 실패한 컷은 포함되지 않는다.
    """
    cuts = scenario.get("cuts", [])

    # image_path가 없거나 파일이 없는 컷만 생성
    cuts_to_generate = [
        c for c in cuts if not c.get("image_path") or not Path(c["image_path"]).exists()
    ]

    if not cuts_to_generate:
        print("[Phase 1] All cuts already have images, skipping startframe generation")
        return {}

    print(
        f"[Phase 1] Generating {len(cuts_to_generate)} startframe images (PARALLEL)..."
    )
    print(f"  Model: {IMAGE_MODEL}")
    print(f"  Ratio: {aspect_ratio}, Resolution: {resolution}")
    print(f"  Face refs: {len(source_images.get('face', []))}")
    print(f"  Product refs: {len(source_images.get('product', []))}")

    # 병렬 생성
    tasks = [
        _generate_single_startframe(
            cut=cut,
            scenario=scenario,
            source_images=source_images,
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            max_retries=max_retries,
        )
        for cut in cuts_to_generate
    ]

    results = await asyncio.gather(*tasks)

    # 성공한 컷만 반환
    frame_paths = {}
    ok_count = 0
    for result in results:
        if result["success"]:
            frame_paths[result["cut_id"]] = result["image_path"]
            ok_count += 1

    print(f"\n  [Phase 1] {ok_count}/{len(cuts_to_generate)} startframes generated")
    return frame_paths
