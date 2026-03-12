"""
핏 베리에이션 생성기

분석 → 프롬프트 → 생성 → 검증 → 재생성 루프.
"""

import time
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.options import get_workflow_defaults

from .analyzer import PantsAnalysis, PantsAnalyzer
from .fit_presets import load_fit_preset, get_display_mode, FitPreset, DisplayMode
from .prompt_builder import build_fit_variation_prompt
from .validator import FitVariationValidator


def generate_fit_variation(
    pants_image: Union[str, Path, Image.Image],
    target_fit: str,
    display_mode: str = "flatlay",
    client: Optional[genai.Client] = None,
    aspect_ratio: Optional[str] = None,
    resolution: str = "2K",
    temperature: Optional[float] = None,
    max_retries: int = 2,
    validate: bool = True,
    extra_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """핏 베리에이션 생성 (분석 → 생성 → 검증 → 재생성)

    Args:
        pants_image: 원본 바지 이미지
        target_fit: 목표 핏 ID (예: "wide", "skinny", "tapered")
        display_mode: 디스플레이 모드 ("flatlay", "hanger", "model_wearing")
        client: Gemini API 클라이언트
        aspect_ratio: 비율 (None이면 워크플로 기본값 사용)
        resolution: 해상도 ("1K", "2K", "4K")
        temperature: 생성 온도 (None이면 워크플로 기본값)
        max_retries: 최대 재시도 횟수
        validate: 검증 활성화 여부
        extra_instructions: 추가 지시사항

    Returns:
        {
            "image": PIL.Image or None,
            "prompt": str,
            "analysis": PantsAnalysis,
            "validation": dict or None,
            "history": list,
        }
    """
    # 클라이언트 초기화
    if client is None:
        from core.api import _get_next_api_key

        client = genai.Client(api_key=_get_next_api_key())

    # 기본값
    defaults = get_workflow_defaults("fit_variation")
    if aspect_ratio is None:
        aspect_ratio = defaults.aspect_ratio
    if temperature is None:
        temperature = defaults.temperature

    # 이미지 로드
    if isinstance(pants_image, (str, Path)):
        pants_img = Image.open(pants_image).convert("RGB")
    else:
        pants_img = pants_image.convert("RGB")

    # 프리셋 로드
    target_preset = load_fit_preset(target_fit)
    display = get_display_mode(display_mode)

    # =========================================================
    # STEP 1: VLM 바지 분석
    # =========================================================
    print(f"\n[1/4] Analyzing pants image...")
    analyzer = PantsAnalyzer(client)
    analysis = analyzer.analyze(pants_img)
    print(f"  Current fit: {analysis.current_fit}")
    print(f"  Color: {analysis.color_primary}")
    print(f"  Material: {analysis.material_type}")
    print(f"  Logos: {len(analysis.logos)}")
    print(f"  Confidence: {analysis.confidence}")

    # =========================================================
    # STEP 2: 프롬프트 생성
    # =========================================================
    print(f"\n[2/4] Building prompt (target: {target_preset.name_en})...")
    prompt = build_fit_variation_prompt(
        analysis=analysis,
        target_preset=target_preset,
        display_mode=display,
        extra_instructions=extra_instructions,
    )
    print(f"  Prompt lines: {len(prompt.splitlines())}")

    # =========================================================
    # STEP 3: 이미지 생성
    # =========================================================
    print(f"\n[3/4] Generating {target_preset.name_en} fit variation...")
    history = []

    image = _send_generation_request(
        client=client,
        prompt=prompt,
        pants_image=pants_img,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        temperature=temperature,
    )

    if image is None:
        print("  [FAIL] Generation failed")
        return {
            "image": None,
            "prompt": prompt,
            "analysis": analysis,
            "validation": None,
            "history": [{"attempt": 1, "status": "generation_failed"}],
        }

    print("  [OK] Image generated")

    # =========================================================
    # STEP 4: 검증 + 재생성 루프
    # =========================================================
    if not validate:
        return {
            "image": image,
            "prompt": prompt,
            "analysis": analysis,
            "validation": None,
            "history": [{"attempt": 1, "status": "success_no_validation"}],
        }

    print(f"\n[4/4] Validating (target: {target_fit})...")
    validator = FitVariationValidator(client)

    for attempt in range(1, max_retries + 2):  # +1 for first attempt, +1 for range
        result = validator.validate(
            generated_img=image,
            reference_images={"pants": [pants_img]},
            target_fit=target_fit,
        )

        attempt_record = {
            "attempt": attempt,
            "score": result.total_score,
            "grade": result.grade,
            "passed": result.passed,
            "auto_fail": result.auto_fail,
        }
        history.append(attempt_record)

        print(
            f"  Attempt {attempt}: {result.total_score}/100 ({result.grade}) "
            f"{'PASS' if result.passed else 'FAIL'}"
        )

        if result.passed:
            return {
                "image": image,
                "prompt": prompt,
                "analysis": analysis,
                "validation": result.to_dict(),
                "history": history,
            }

        # 재시도 가능한지 확인
        if attempt > max_retries:
            break

        # 프롬프트 강화 후 재생성
        failed_criteria = [
            k
            for k, v in result.criteria_scores.items()
            if isinstance(v, dict) and v.get("score", 0) < 80
        ]
        enhancement = validator.get_enhancement_rules(failed_criteria)

        print(f"  Retrying with enhanced prompt...")
        enhanced_prompt = (
            prompt + f"\n\n## [강화 규칙] (재시도 {attempt})\n{enhancement}"
        )

        # temperature 낮춰서 재시도
        retry_temp = max(0.1, temperature - 0.05 * attempt)
        image = _send_generation_request(
            client=client,
            prompt=enhanced_prompt,
            pants_image=pants_img,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=retry_temp,
        )

        if image is None:
            history.append({"attempt": attempt + 1, "status": "generation_failed"})
            break

        time.sleep(2)  # rate limit

    # 최종 실패 — 마지막 이미지라도 반환
    return {
        "image": image,
        "prompt": prompt,
        "analysis": analysis,
        "validation": result.to_dict() if result else None,
        "history": history,
    }


def _send_generation_request(
    client: genai.Client,
    prompt: str,
    pants_image: Image.Image,
    aspect_ratio: str = "1:1",
    resolution: str = "2K",
    temperature: float = 0.3,
) -> Optional[Image.Image]:
    """이미지 생성 API 호출

    Args:
        client: Gemini 클라이언트
        prompt: 프롬프트
        pants_image: 원본 바지 이미지
        aspect_ratio: 비율
        resolution: 해상도
        temperature: 생성 온도

    Returns:
        생성된 이미지 또는 None
    """
    # 이미지를 Part로 변환
    img_copy = pants_image.copy()
    if max(img_copy.size) > 1024:
        img_copy.thumbnail((1024, 1024), Image.LANCZOS)

    buffer = BytesIO()
    img_copy.save(buffer, format="PNG")
    pants_part = types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )

    # API 호출
    parts = [
        types.Part(text=prompt),
        types.Part(text="[REFERENCE] pants image:"),
        pants_part,
    ]

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                ),
            ),
        )

        # 이미지 추출
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    if part.inline_data.mime_type.startswith("image/"):
                        img_data = part.inline_data.data
                        return Image.open(BytesIO(img_data)).convert("RGB")

        print("  [WARN] No image in response")
        return None

    except Exception as e:
        print(f"  [ERROR] Generation failed: {e}")
        return None
