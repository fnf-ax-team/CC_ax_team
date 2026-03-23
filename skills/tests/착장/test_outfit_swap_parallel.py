"""
Outfit Swap Parallel Test - Sergio Tacchini 4 Sets x 3 Images

4개 테스트셋을 병렬로 실행, 각 3장씩 생성
검수 없이 빠른 테스트 (generate_outfit_swap 사용)
"""

import sys
import os
import json
import shutil
import time
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from PIL import Image
from google import genai
from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key
from core.outfit_swap import (
    generate_outfit_swap,
    analyze_source_for_swap,
    analyze_outfit_items,
    build_outfit_swap_prompt,
    pil_to_part,
)
from core.options import detect_aspect_ratio

# ============================================================
# TEST CONFIG
# ============================================================
NUM_IMAGES = 3
ASPECT_RATIO = "auto"  # "auto" = 소스 이미지 비율 자동 매칭 (포즈 보존 핵심!)
RESOLUTION = "2K"
TEMPERATURE = 0.2

# 테스트셋 정의
TEST_SETS = {
    "test1_tennis_dress": {
        "source": r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트1\20260120 SERGIO TACCHINI152659.jpg",
        "outfits": [
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트1\STS26W51424-108_4268.jpg",
        ],
        "description": "st_white_bra_skirt_to_tennis_dress",
    },
    "test2_teal_set": {
        "source": r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트2\20260120 SERGIO TACCHINI152733.jpg",
        "outfits": [
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트2\STS26W51418-303_4260.jpg",
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트2\STS26W51419-303_4266.jpg",
        ],
        "description": "st_white_jacket_to_teal_pullover_skirt",
    },
    "test3_cream_jacket_set": {
        "source": r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트3\20260120 SERGIO TACCHINI152874.jpg",
        "outfits": [
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트3\9FBB6435EFED4BA4A0A57FE2B5A151E1.jpg",
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트3\STS26W51440-108_4281.jpg",
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트3\STS26W51441-108_4286.jpg",
        ],
        "description": "st_poolside_to_cream_jacket_bra_skirt",
    },
    "test4_navy_jacket_set": {
        "source": r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트4\20260120-SERGIO-TACCHINI152257.jpg",
        "outfits": [
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트4\STS26W51451-412.jpg",
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트4\STS26W51443-050_4278.jpg",
            r"d:\FNF_Studio_TEST\New-fnf-studio\tests\착장테스트4\W 마시멜로우 브라탑.jpeg",
        ],
        "description": "st_black_set_to_navy_jacket_white_skirt_bra",
    },
}


def run_single_test(test_name, test_config):
    """단일 테스트셋 실행 (3장 생성)"""
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    description = test_config["description"]

    # 출력 폴더 생성
    output_dir = project_root / f"Fnf_studio_outputs/outfit_swap/{timestamp}_{description}"
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[{test_name}] START - {description}")
    print(f"{'='*60}")

    source_path = test_config["source"]
    outfit_paths = test_config["outfits"]

    # 인풋 이미지 복사
    src_ext = Path(source_path).suffix
    shutil.copy(source_path, images_dir / f"input_source_01{src_ext}")
    for i, op in enumerate(outfit_paths):
        ext = Path(op).suffix
        shutil.copy(op, images_dir / f"input_outfit_{i+1:02d}{ext}")

    # 소스/착장 이미지 로드
    source_pil = Image.open(source_path).convert("RGB")
    outfit_pils = [Image.open(p).convert("RGB") for p in outfit_paths]

    # 비율 자동 감지: 소스 이미지 비율과 동일한 Gemini 비율 사용
    if ASPECT_RATIO.lower() in ("auto", "original"):
        actual_ratio = detect_aspect_ratio(source_pil)
        print(f"[{test_name}] Aspect ratio auto-detected: {source_pil.size[0]}x{source_pil.size[1]} -> {actual_ratio}")
    else:
        actual_ratio = ASPECT_RATIO

    # VLM 분석 (1회만 수행, 3장 공유)
    client = genai.Client(api_key=_get_next_api_key())

    print(f"[{test_name}] Source VLM analysis...")
    source_analysis = analyze_source_for_swap(source_pil, client)
    print(f"[{test_name}] Source analysis done")

    print(f"[{test_name}] Outfit VLM analysis ({len(outfit_pils)} items)...")
    outfit_analyses = analyze_outfit_items(outfit_pils, client)
    print(f"[{test_name}] Outfit analysis done")

    # 프롬프트 조립
    prompt = build_outfit_swap_prompt(
        source_analysis=source_analysis,
        outfit_analyses=outfit_analyses,
    )
    print(f"[{test_name}] Prompt built ({len(prompt)} chars)")

    # prompt.json 저장
    prompt_data = {
        "test_name": test_name,
        "prompt_text": prompt,
        "source_analysis": source_analysis,
        "outfit_analyses": outfit_analyses,
    }
    with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2, default=str)

    # prompt.txt 저장
    prompt_txt = f"""=== TEST INFO ===
Test Name: {test_name}
Description: {description}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

=== INPUTS ===
Source: {source_path} ({source_pil.size[0]}x{source_pil.size[1]})
Outfits: {', '.join(outfit_paths)}

=== PROMPT ===
{prompt}

=== CONFIG ===
Aspect Ratio: {actual_ratio} (auto-detected from source)
Resolution: {RESOLUTION}
Temperature: {TEMPERATURE}
Num Images: {NUM_IMAGES}
"""
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    # config.json 저장
    config = {
        "workflow": "outfit_swap",
        "test_name": test_name,
        "description": description,
        "timestamp": datetime.now().isoformat(),
        "model": IMAGE_MODEL,
        "aspect_ratio": actual_ratio,
        "aspect_ratio_mode": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "temperature": TEMPERATURE,
        "num_images": NUM_IMAGES,
        "cost_per_image": 190,
        "total_cost": NUM_IMAGES * 190,
        "brand": "Sergio Tacchini",
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 3장 생성 (순차 - API rate limit 고려)
    from google.genai import types as gtypes

    for i in range(NUM_IMAGES):
        print(f"[{test_name}] Generating image {i+1}/{NUM_IMAGES}...")
        start_time = time.time()

        try:
            gen_client = genai.Client(api_key=_get_next_api_key())

            # Parts 조립 (generator.py와 동일한 라벨 사용)
            parts = [gtypes.Part(text=prompt)]
            parts.append(gtypes.Part(text="[SOURCE IMAGE - EDITING CANVAS] Preserve EVERYTHING (face, pose, background, scale). Change ONLY clothing."))
            parts.append(pil_to_part(source_pil))

            for j, outfit_img in enumerate(outfit_pils):
                parts.append(gtypes.Part(text=f"[OUTFIT REFERENCE {j+1}] Extract garment ONLY. IGNORE pose/face/background in this image."))
                parts.append(pil_to_part(outfit_img))

            response = gen_client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[gtypes.Content(role="user", parts=parts)],
                config=gtypes.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=gtypes.ImageConfig(
                        aspect_ratio=actual_ratio,
                        image_size=RESOLUTION,
                    ),
                ),
            )

            # 이미지 추출
            from io import BytesIO
            generated_img = None
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    generated_img = Image.open(BytesIO(part.inline_data.data))
                    break

            if generated_img:
                save_path = images_dir / f"output_{i+1:03d}.jpg"
                generated_img.save(str(save_path), quality=95)
                elapsed = time.time() - start_time
                print(f"[{test_name}] Image {i+1} saved ({elapsed:.1f}s) -> {save_path.name}")
                results.append({"index": i+1, "status": "ok", "path": str(save_path), "time": elapsed})
            else:
                print(f"[{test_name}] Image {i+1} - no image in response")
                results.append({"index": i+1, "status": "no_image"})

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            print(f"[{test_name}] Image {i+1} FAILED ({elapsed:.1f}s): {error_msg[:100]}")
            results.append({"index": i+1, "status": "error", "error": error_msg, "time": elapsed})

            # Rate limit 대기
            if "429" in error_msg or "rate" in error_msg.lower():
                wait = (i + 1) * 5
                print(f"[{test_name}] Rate limit, waiting {wait}s...")
                time.sleep(wait)

    # 결과 요약
    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"\n[{test_name}] DONE: {ok_count}/{NUM_IMAGES} generated -> {output_dir}")

    # results.json 저장
    with open(output_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump({"test_name": test_name, "results": results, "total": NUM_IMAGES, "success": ok_count}, f, ensure_ascii=False, indent=2, default=str)

    return test_name, ok_count, str(output_dir)


def main():
    print("=" * 60)
    print("Outfit Swap Parallel Test - Sergio Tacchini")
    print(f"4 sets x {NUM_IMAGES} images = {4 * NUM_IMAGES} total")
    print(f"Model: {IMAGE_MODEL}")
    print(f"Resolution: {RESOLUTION} | Ratio: {ASPECT_RATIO} | Temp: {TEMPERATURE}")
    print("=" * 60)

    start_total = time.time()

    # 4개 병렬 실행
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for test_name, test_config in TEST_SETS.items():
            future = executor.submit(run_single_test, test_name, test_config)
            futures[future] = test_name

        # 결과 수집
        summary = []
        for future in as_completed(futures):
            test_name = futures[future]
            try:
                name, ok_count, output_dir = future.result()
                summary.append((name, ok_count, output_dir))
            except Exception as e:
                print(f"[{test_name}] CRITICAL ERROR: {e}")
                traceback.print_exc()
                summary.append((test_name, 0, "ERROR"))

    elapsed_total = time.time() - start_total

    # 최종 요약
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    total_ok = 0
    for name, ok_count, output_dir in summary:
        status = "OK" if ok_count == NUM_IMAGES else f"PARTIAL ({ok_count}/{NUM_IMAGES})" if ok_count > 0 else "FAIL"
        print(f"  [{status}] {name}: {ok_count}/{NUM_IMAGES} -> {output_dir}")
        total_ok += ok_count

    print(f"\nTotal: {total_ok}/{4 * NUM_IMAGES} images generated")
    print(f"Time: {elapsed_total:.1f}s ({elapsed_total/60:.1f}min)")
    print(f"Cost: {total_ok * 190} won (@ 190 won/image)")


if __name__ == "__main__":
    main()
