# -*- coding: utf-8 -*-
"""
Pose Format Ablation Test (A/B/C)
=================================

동일 인풋(인플테스트3)으로 3가지 포즈 프롬프트 포맷을 비교:

- Variant A: Baseline (현재 문장형 + 방향/기울기 서브섹션)
- Variant B: Structured (서브필드 분리, 다리 중복 제거)
- Variant C: Flat key-value (계층 없이 플랫, 한 줄에 하나)

각 variant별 3장 = 총 9장 생성.
VLM 분석은 1회만 수행 (공통), 프롬프트 포맷만 달라짐.

비용: 9장 x 190원 = 1,710원

Author: FNF AX Team
Date: 2026-02-27
"""

import sys
import json
import shutil
import time
import traceback
from pathlib import Path
from datetime import datetime

# Project root setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables BEFORE importing core modules
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.api import _get_next_api_key

# ============================================================
# TEST CONFIGURATION
# ============================================================
NUM_SAMPLES = 3  # variant 당 3장
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"
TEMPERATURE = 0.35

# 인풋 폴더 (인플테스트3)
INPUT_FOLDER = project_root / "tests" / "인플테스트3"

FACE_IMAGE = INPUT_FOLDER / "얼굴.png"
POSE_IMAGE = INPUT_FOLDER / "포즈.png"
EXPRESSION_IMAGE = INPUT_FOLDER / "표정.png"
BACKGROUND_IMAGE = INPUT_FOLDER / "배경.png"
OUTFIT_IMAGES = sorted(INPUT_FOLDER.glob("착장*.png"))

# 출력 베이스
OUTPUT_BASE = project_root / "Fnf_studio_outputs" / "ai_influencer"

# Variant 정의
VARIANTS = {
    "A_baseline": {
        "pose_format": "A",
        "description": "Baseline - 문장형 팔/다리 + 별도 방향/기울기 서브섹션",
    },
    "B_structured": {
        "pose_format": "B",
        "description": "Structured - 서브필드 분리, 다리 중복 제거",
    },
    "C_flat": {
        "pose_format": "C",
        "description": "Flat - 플랫 키-값, 한 줄에 하나",
    },
}


# ============================================================
# IMAGE -> GEMINI PART
# ============================================================
def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image -> Gemini Part"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


# ============================================================
# VLM ANALYSIS (1 PASS)
# ============================================================
def run_vlm_analysis(client):
    """
    VLM 분석 1회 실행 (모든 variant에서 공유)

    Returns:
        dict: {hair, expression, pose, background, outfit, compatibility}
    """
    from core.ai_influencer.hair_analyzer import analyze_hair
    from core.ai_influencer.expression_analyzer import analyze_expression
    from core.ai_influencer.pose_analyzer import analyze_pose
    from core.ai_influencer.background_analyzer import analyze_background
    from core.ai_influencer.compatibility import check_compatibility
    from core.outfit_analyzer import OutfitAnalyzer

    print("\n[VLM] Running VLM analysis (1 pass for all variants)...")

    # 1. Hair
    print("  [1/6] Analyzing hair...")
    hair_result = analyze_hair(FACE_IMAGE)
    print(f"    -> style={hair_result.style}, color={hair_result.color}")

    # 2. Expression
    print("  [2/6] Analyzing expression...")
    expression_result = analyze_expression(EXPRESSION_IMAGE)
    print(f"    -> base={expression_result.mood_base}")

    # 3. Pose
    print("  [3/6] Analyzing pose...")
    pose_result = analyze_pose(POSE_IMAGE)
    print(
        f"    -> stance={pose_result.stance}, framing={pose_result.framing}, leg_shape={pose_result.bent_leg_shape}"
    )

    # 4. Background
    print("  [4/6] Analyzing background...")
    background_result = analyze_background(BACKGROUND_IMAGE)
    print(
        f"    -> scene={background_result.scene_type}, time={background_result.time_of_day}"
    )

    # 5. Compatibility
    print("  [5/6] Checking compatibility...")
    compatibility_result = check_compatibility(pose_result, background_result)
    print(f"    -> compatible={compatibility_result.is_compatible()}")

    # 6. Outfit
    print("  [6/6] Analyzing outfit...")
    outfit_analyzer = OutfitAnalyzer(client)
    outfit_result = outfit_analyzer.analyze([str(p) for p in OUTFIT_IMAGES])
    print(f"    -> {len(outfit_result.items)} items detected")

    print("[VLM] Analysis complete.\n")

    return {
        "hair": hair_result,
        "expression": expression_result,
        "pose": pose_result,
        "background": background_result,
        "compatibility": compatibility_result,
        "outfit": outfit_result,
    }


# ============================================================
# BUILD PROMPT FOR VARIANT
# ============================================================
def build_prompt_for_variant(analysis, pose_format: str) -> str:
    """variant별 프롬프트 생성 (pose_format만 다름)"""
    from core.ai_influencer.prompt_builder import build_schema_prompt

    return build_schema_prompt(
        hair_result=analysis["hair"],
        expression_result=analysis["expression"],
        pose_result=analysis["pose"],
        background_result=analysis["background"],
        outfit_result=analysis["outfit"],
        compatibility_result=analysis["compatibility"],
        pose_format=pose_format,
    )


# ============================================================
# GENERATE SINGLE IMAGE
# ============================================================
def generate_single_image(
    prompt: str,
    max_retries: int = 3,
) -> Image.Image:
    """단일 이미지 생성 (프롬프트 + 모든 레퍼런스 이미지)"""

    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)

    # API 파트 구성
    parts = []

    # 1. 프롬프트
    parts.append(types.Part(text=prompt))

    # 2. 포즈 레퍼런스
    parts.append(types.Part(text="[POSE REFERENCE]"))
    parts.append(pil_to_part(Image.open(POSE_IMAGE).convert("RGB")))

    # 3. 표정 레퍼런스
    parts.append(types.Part(text="[EXPRESSION REFERENCE]"))
    parts.append(pil_to_part(Image.open(EXPRESSION_IMAGE).convert("RGB")))

    # 4. 얼굴
    parts.append(types.Part(text="[FACE 1]"))
    parts.append(pil_to_part(Image.open(FACE_IMAGE).convert("RGB")))

    # 5. 착장
    for i, outfit_path in enumerate(OUTFIT_IMAGES):
        parts.append(types.Part(text=f"[OUTFIT {i+1}]"))
        parts.append(pil_to_part(Image.open(outfit_path).convert("RGB")))

    # 6. 배경 레퍼런스
    parts.append(types.Part(text="[BACKGROUND REFERENCE]"))
    parts.append(pil_to_part(Image.open(BACKGROUND_IMAGE).convert("RGB")))

    # 7. 포즈 재강조 (마지막에 다시 포즈 이미지 전송)
    parts.append(
        types.Part(
            text="[POSE REMINDER] *** CRITICAL: Copy this EXACT pose! "
            "Pay attention to leg shape: if knee points SIDEWAYS (figure-4), "
            "do NOT lift it FORWARD. Match the exact direction! ***"
        )
    )
    parts.append(pil_to_part(Image.open(POSE_IMAGE).convert("RGB")))

    # API 호출
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=ASPECT_RATIO,
                        image_size=RESOLUTION,
                    ),
                ),
            )

            # 이미지 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            print(f"    [!] No image in response")
            return None

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(
                x in error_str for x in ["429", "rate", "503", "overload", "timeout"]
            )

            if not is_retryable:
                print(f"    [X] Non-retryable error: {e}")
                return None

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"    [!] Retry {attempt + 1}/{max_retries} - waiting {wait_time}s..."
                )
                time.sleep(wait_time)

    return None


# ============================================================
# SAVE RESULTS
# ============================================================
def save_variant_results(
    variant_id: str,
    variant_dir: Path,
    prompt_text: str,
    images: list,
    config: dict,
    analysis_summary: dict,
):
    """variant별 결과 저장"""
    images_dir = variant_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 인풋 이미지 복사 (첫 variant만)
    if not (images_dir / f"input_face_01{FACE_IMAGE.suffix}").exists():
        shutil.copy(FACE_IMAGE, images_dir / f"input_face_01{FACE_IMAGE.suffix}")
        shutil.copy(POSE_IMAGE, images_dir / f"input_pose_ref{POSE_IMAGE.suffix}")
        shutil.copy(
            EXPRESSION_IMAGE,
            images_dir / f"input_expression_ref{EXPRESSION_IMAGE.suffix}",
        )
        shutil.copy(
            BACKGROUND_IMAGE,
            images_dir / f"input_background_ref{BACKGROUND_IMAGE.suffix}",
        )
        for i, outfit_path in enumerate(OUTFIT_IMAGES):
            shutil.copy(
                outfit_path, images_dir / f"input_outfit_{i+1:02d}{outfit_path.suffix}"
            )

    # 결과 이미지 저장
    for i, img in enumerate(images):
        if img:
            img.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)

    # prompt.txt
    with open(variant_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(f"=== POSE FORMAT ABLATION ===\n")
        f.write(f"Variant: {variant_id}\n")
        f.write(f"Description: {config.get('description', '')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Pose Format: {config.get('pose_format', 'A')}\n\n")
        f.write(f"=== INPUTS ===\n")
        f.write(f"Face: {FACE_IMAGE.name}\n")
        f.write(f"Pose: {POSE_IMAGE.name}\n")
        f.write(f"Expression: {EXPRESSION_IMAGE.name}\n")
        f.write(f"Background: {BACKGROUND_IMAGE.name}\n")
        f.write(f"Outfits: {[p.name for p in OUTFIT_IMAGES]}\n\n")
        f.write(f"=== PROMPT ===\n")
        f.write(prompt_text)

    # prompt.json
    with open(variant_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "variant": variant_id,
                "pose_format": config.get("pose_format", "A"),
                "prompt_text": prompt_text,
                "analysis_summary": analysis_summary,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # config.json
    with open(variant_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2, default=str)


# ============================================================
# MAIN
# ============================================================
def main(variants_to_run: list = None):
    """
    A/B/C 실험 실행

    Args:
        variants_to_run: 실행할 variant ID 목록 (None이면 전체)
    """
    print("=" * 60)
    print("POSE FORMAT ABLATION TEST (A/B/C)")
    print("=" * 60)
    print(f"Input: {INPUT_FOLDER}")
    print(f"Variants: {list(VARIANTS.keys())}")
    print(f"Samples per variant: {NUM_SAMPLES}")
    print(f"Total images: {len(VARIANTS) * NUM_SAMPLES}")
    print(f"Estimated cost: {len(VARIANTS) * NUM_SAMPLES * 190} won")
    print("=" * 60)

    # 인풋 검증
    print("\n[CHECK] Verifying inputs...")
    for label, path in [
        ("Face", FACE_IMAGE),
        ("Pose", POSE_IMAGE),
        ("Expression", EXPRESSION_IMAGE),
        ("Background", BACKGROUND_IMAGE),
    ]:
        if not path.exists():
            print(f"[ERROR] {label} not found: {path}")
            return None
        print(f"  [OK] {label}: {path.name}")

    if not OUTFIT_IMAGES:
        print("[ERROR] No outfit images found")
        return None
    print(f"  [OK] Outfits: {len(OUTFIT_IMAGES)} items")

    # 출력 폴더 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_BASE / f"pose_ablation_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[OUTPUT] {output_dir}")

    # VLM 분석 (1 pass)
    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)
    analysis = run_vlm_analysis(client)

    # 분석 요약 (로깅용)
    analysis_summary = {
        "pose": analysis["pose"].to_schema_format(),
        "background_scene": analysis["background"].scene_type,
        "background_time": analysis["background"].time_of_day,
        "outfit_items": len(analysis["outfit"].items),
        "compatible": analysis["compatibility"].is_compatible(),
    }

    # 분석 결과 저장
    with open(output_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, ensure_ascii=False, indent=2)

    # variant 필터
    active_variants = VARIANTS
    if variants_to_run:
        active_variants = {k: v for k, v in VARIANTS.items() if k in variants_to_run}

    # 각 variant 실행
    all_results = {}

    for variant_id, variant_config in active_variants.items():
        print(f"\n{'=' * 60}")
        print(f"[VARIANT] {variant_id}: {variant_config['description']}")
        print(f"{'=' * 60}")

        pose_format = variant_config["pose_format"]
        variant_dir = output_dir / variant_id

        # 프롬프트 생성
        prompt_text = build_prompt_for_variant(analysis, pose_format)
        print(f"  Prompt: {len(prompt_text.splitlines())} lines")

        # 이미지 생성
        images = []
        success_count = 0

        for i in range(NUM_SAMPLES):
            print(f"\n  [{i+1}/{NUM_SAMPLES}] Generating...", end=" ", flush=True)

            try:
                img = generate_single_image(prompt_text)
                if img:
                    images.append(img)
                    success_count += 1
                    print(f"OK ({img.size[0]}x{img.size[1]})")
                else:
                    images.append(None)
                    print("FAILED (no image)")
            except Exception as e:
                images.append(None)
                print(f"ERROR: {e}")
                traceback.print_exc()

            # Rate limit
            if i < NUM_SAMPLES - 1:
                time.sleep(3)

        # 결과 저장
        config_data = {
            "variant": variant_id,
            "pose_format": pose_format,
            "description": variant_config["description"],
            "workflow": "ai_influencer",
            "timestamp": datetime.now().isoformat(),
            "model": IMAGE_MODEL,
            "aspect_ratio": ASPECT_RATIO,
            "resolution": RESOLUTION,
            "temperature": TEMPERATURE,
            "num_images": NUM_SAMPLES,
            "success_count": success_count,
            "cost_per_image": 190,
            "total_cost": success_count * 190,
        }

        save_variant_results(
            variant_id=variant_id,
            variant_dir=variant_dir,
            prompt_text=prompt_text,
            images=images,
            config=config_data,
            analysis_summary=analysis_summary,
        )

        all_results[variant_id] = {
            "success": success_count,
            "total": NUM_SAMPLES,
            "pose_format": pose_format,
        }

        print(f"\n  -> {variant_id}: {success_count}/{NUM_SAMPLES} success")

        # variant 간 대기
        time.sleep(5)

    # 전체 요약
    print(f"\n{'=' * 60}")
    print("ABLATION TEST COMPLETE")
    print(f"{'=' * 60}")

    total_success = sum(r["success"] for r in all_results.values())
    total_count = sum(r["total"] for r in all_results.values())

    for vid, r in all_results.items():
        print(f"  {vid}: {r['success']}/{r['total']}")

    print(f"\n  Total: {total_success}/{total_count}")
    print(f"  Cost: {total_success * 190} won")
    print(f"  Output: {output_dir}")

    # summary.json
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "variants": list(active_variants.keys()),
                "num_samples": NUM_SAMPLES,
                "results": all_results,
                "analysis_summary": analysis_summary,
                "config": {
                    "aspect_ratio": ASPECT_RATIO,
                    "resolution": RESOLUTION,
                    "temperature": TEMPERATURE,
                    "model": IMAGE_MODEL,
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return output_dir


if __name__ == "__main__":
    # 전체 실행 (A/B/C x 3장 = 9장)
    # 특정 variant만: main(["A_baseline", "B_structured"])
    main()
