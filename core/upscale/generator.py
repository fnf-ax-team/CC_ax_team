"""
4K 업스케일 생성기

원본 이미지를 Gemini에 전달하고 동일 이미지를 4K 해상도로 재생성.
내용 변경 최소화를 위해 temperature=0.05 사용.
"""

import time
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.options import detect_aspect_ratio


# 업스케일 프롬프트 — 원본 완전 복제 지시
UPSCALE_PROMPT = """Reproduce this EXACT image at maximum 4K resolution.

CRITICAL RULES:
- DO NOT change ANYTHING: same composition, same people, same poses, same outfits, same colors, same background, same lighting, same expressions, same camera angle, same framing.
- This is a professional photo that needs to be reproduced IDENTICALLY at higher resolution.
- Enhance sharpness, fine details, and texture clarity.
- Maintain exact color temperature and grading.
- Do NOT add, remove, or modify any element.

Output the exact same image with enhanced resolution and detail."""


def _load_image(img: Union[str, Path, Image.Image]) -> Image.Image:
    """이미지 로드 헬퍼"""
    if isinstance(img, (str, Path)):
        return Image.open(img).convert("RGB")
    return img.convert("RGB") if img.mode != "RGB" else img


def _image_to_part(img: Image.Image) -> types.Part:
    """PIL Image를 Gemini Part로 변환 (원본 크기 유지)"""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return types.Part(
        inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())
    )


def _get_api_key(api_key: Optional[str] = None) -> str:
    """API 키 가져오기"""
    if api_key:
        return api_key
    from core.api import get_next_api_key

    return get_next_api_key()


def upscale_image(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
    max_retries: int = 3,
) -> Optional[Image.Image]:
    """단일 이미지를 4K로 업스케일

    원본 이미지를 Gemini에 전달하여 동일 이미지를 4K 해상도로 재생성.

    Args:
        source_image: 원본 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)
        max_retries: 최대 재시도 횟수

    Returns:
        4K 업스케일된 PIL Image 또는 None (실패 시)
    """
    img = _load_image(source_image)
    aspect_ratio = detect_aspect_ratio(img)
    w, h = img.size
    print(f"  [UPSCALE] Original: {w}x{h} | Ratio: {aspect_ratio} | Target: 4K")

    image_part = _image_to_part(img)

    for attempt in range(max_retries):
        try:
            key = _get_api_key(api_key)
            client = genai.Client(api_key=key)

            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[image_part, types.Part(text=UPSCALE_PROMPT)],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.05,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="4K",
                    ),
                ),
            )

            # 이미지 추출
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        result = Image.open(BytesIO(part.inline_data.data))
                        rw, rh = result.size
                        print(f"  [UPSCALE] Result: {rw}x{rh}")
                        return result

            print(
                f"  [WARN] No image in response (attempt {attempt + 1}/{max_retries})"
            )

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                wait = (attempt + 1) * 5
                print(f"  [RATE_LIMIT] Waiting {wait}s...")
                time.sleep(wait)
            elif "safety" in error_str or "blocked" in error_str:
                print(f"  [BLOCKED] Safety filter - skipping")
                return None
            else:
                print(f"  [ERROR] {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 5)

    print(f"  [FAIL] All {max_retries} attempts failed")
    return None


def upscale_with_validation(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
    max_retries: int = 2,
) -> dict:
    """업스케일 + 검증 + 재시도

    업스케일 후 원본과 비교 검증하여 내용 변경 여부를 확인.
    검증 실패 시 재시도.

    Args:
        source_image: 원본 이미지
        api_key: API 키
        max_retries: 검증 재시도 횟수

    Returns:
        {
            "image": PIL.Image (최고 품질 결과),
            "score": int (총점),
            "passed": bool,
            "criteria": dict (항목별 점수),
            "attempts": int,
            "history": list,
        }
    """
    from core.upscale.validator import UpscaleValidator

    img = _load_image(source_image)
    key = _get_api_key(api_key)
    client = genai.Client(api_key=key)

    validator = UpscaleValidator(client)

    best_result = None
    best_score = -1
    history = []

    for attempt in range(max_retries + 1):
        print(f"\n  [ATTEMPT {attempt + 1}/{max_retries + 1}]")

        # 업스케일 생성
        result_img = upscale_image(img, api_key=api_key)
        if result_img is None:
            history.append({"attempt": attempt + 1, "status": "generation_failed"})
            continue

        # 검증 (원본 vs 결과 비교)
        validation = validator.validate(
            generated_img=result_img,
            reference_images={"source": [img]},
        )

        attempt_info = {
            "attempt": attempt + 1,
            "score": validation.total_score,
            "passed": validation.passed,
            "grade": validation.grade,
            "criteria": validation.criteria_scores,
        }
        history.append(attempt_info)

        # 최고 점수 갱신
        if validation.total_score > best_score:
            best_score = validation.total_score
            best_result = {
                "image": result_img,
                "score": validation.total_score,
                "passed": validation.passed,
                "grade": validation.grade,
                "criteria": validation.criteria_scores,
                "attempts": attempt + 1,
                "history": history,
                "validation_result": validation,
            }

        if validation.passed:
            print(
                f"  [PASS] Score: {validation.total_score} | Grade: {validation.grade}"
            )
            break
        else:
            print(
                f"  [FAIL] Score: {validation.total_score} | Issues: {validation.issues}"
            )

    if best_result is None:
        best_result = {
            "image": None,
            "score": 0,
            "passed": False,
            "grade": "F",
            "criteria": {},
            "attempts": max_retries + 1,
            "history": history,
            "validation_result": None,
        }

    return best_result


def upscale_batch(
    input_dir: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    api_key: Optional[str] = None,
    max_retries: int = 3,
    delay: float = 2.0,
    skip_existing: bool = True,
) -> dict:
    """폴더 내 이미지 일괄 4K 업스케일

    Args:
        input_dir: 입력 이미지 폴더
        output_dir: 출력 폴더 (None이면 input_dir/4K)
        api_key: API 키
        max_retries: 이미지당 최대 재시도
        delay: 이미지 간 딜레이 (초, rate limit 방지)
        skip_existing: 이미 존재하는 결과 스킵

    Returns:
        {"success": int, "failed": int, "skipped": int, "results": list}
    """
    input_path = Path(input_dir)
    if output_dir is None:
        output_path = input_path / "4K"
    else:
        output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 이미지 파일 수집
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(
        f
        for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    )

    print("=" * 60)
    print("  4K Upscale Batch")
    print("=" * 60)
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Images: {len(images)}")
    print("=" * 60)

    success = 0
    failed = 0
    skipped = 0
    results = []

    for i, img_path in enumerate(images):
        out_name = img_path.stem + "_4K.jpg"
        out_path = output_path / out_name

        print(f"\n[{i + 1}/{len(images)}] {img_path.name}")

        # 이미 존재하면 스킵
        if skip_existing and out_path.exists():
            print(f"  [SKIP] Already exists")
            skipped += 1
            results.append({"file": img_path.name, "status": "skipped"})
            continue

        result_img = upscale_image(
            str(img_path), api_key=api_key, max_retries=max_retries
        )

        if result_img is not None:
            result_img.save(str(out_path), quality=95)
            success += 1
            rw, rh = result_img.size
            results.append(
                {"file": img_path.name, "status": "success", "size": f"{rw}x{rh}"}
            )
        else:
            failed += 1
            results.append({"file": img_path.name, "status": "failed"})

        # rate limit 방지 딜레이
        if i < len(images) - 1:
            time.sleep(delay)

    print(f"\n{'=' * 60}")
    print(f"  DONE! Success: {success} | Failed: {failed} | Skipped: {skipped}")
    print(f"  Output: {output_path}")
    print(f"{'=' * 60}")

    return {
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }
