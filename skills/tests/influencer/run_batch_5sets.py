"""
AI Influencer Batch Runner - 5 Test Sets Sequential Execution

5개 테스트 세트를 순차적으로 실행하고 결과를 표준 폴더 구조로 저장한다.

Usage:
  python tests/influencer/run_batch_5sets.py

Test Sets:
  - tests/인플테스트1
  - tests/인플테스트2
  - tests/인플테스트3
  - tests/인플테스트4
  - tests/인플테스트5

Settings:
  - aspect_ratio: 4:5
  - resolution: 2K
  - num_images: 3
  - temperature: 0.5
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import time
import shutil

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드 - core 모듈 import 전에 반드시 실행
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from google import genai

from core.config import IMAGE_MODEL
from core.api import _get_next_api_key
from core.ai_influencer.pipeline import generate_full_pipeline, send_image_request


# ============================================================
# OPTIONS (change these values)
# ============================================================
# aspect_ratio: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
# resolution: "1K", "2K", "4K"
# num_images: 1, 3, 5, 10
# cost: 1K~2K = 190won/image, 4K = 380won/image
# ============================================================
NUM_IMAGES = 3
ASPECT_RATIO = "4:5"
RESOLUTION = "2K"
TEMPERATURE = 0.5

# 5개 테스트 세트 목록
TEST_SETS = [
    "인플테스트1",
    "인플테스트2",
    "인플테스트3",
    "인플테스트4",
    "인플테스트5",
]


# ============================================================
# SINGLE TEST RUNNER
# ============================================================


def run_test(test_name: str, test_folder: Path):
    """
    AI 인플루언서 이미지 생성 - 단일 테스트 세트 실행

    core/ai_influencer/pipeline.py의 generate_full_pipeline()을 호출하고
    결과를 표준 폴더 구조로 저장한다.

    Returns:
        dict: validation 결과 (성공 시), None (실패 시)
    """

    print(f"\n{'#' * 60}")
    print(f"# AI INFLUENCER - FULL PIPELINE TEST: {test_name}")
    print(f"# Folder: {test_folder}")
    print(f"{'#' * 60}")

    if not test_folder.exists():
        print(f"[ERROR] Test folder not found: {test_folder}")
        return None

    # API 클라이언트 (세트마다 로테이션)
    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)

    # 출력 디렉토리
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        project_root
        / "Fnf_studio_outputs"
        / "ai_influencer"
        / f"{test_name}_{timestamp}"
    )
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # 이미지 경로 탐색
    # =========================================================
    face_images = [test_folder / "얼굴.png"]
    outfit_images = sorted(list(test_folder.glob("착장*.png")))
    pose_image = test_folder / "포즈.png"

    expression_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        expr_path = test_folder / f"표정{ext}"
        if expr_path.exists():
            expression_image = expr_path
            break

    background_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        bg_path = test_folder / f"배경{ext}"
        if bg_path.exists():
            background_image = bg_path
            break

    # 필수 이미지 확인
    missing = []
    if not face_images[0].exists():
        missing.append("얼굴.png")
    if not pose_image.exists():
        missing.append("포즈.png")
    if not expression_image:
        missing.append("표정.png/jpeg/jpg")
    if not background_image:
        missing.append("배경.png/jpeg/jpg")
    if not outfit_images:
        missing.append("착장*.png")

    if missing:
        print(f"[ERROR] Missing required images: {', '.join(missing)}")
        return None

    # 인풋 이미지 복사 (input_ 접두사로 구분)
    for face_path in face_images:
        shutil.copy(face_path, images_dir / "input_face.png")
    for i, outfit_path in enumerate(outfit_images):
        shutil.copy(outfit_path, images_dir / f"input_outfit_{i+1:02d}.png")
    shutil.copy(pose_image, images_dir / "input_pose.png")
    shutil.copy(
        expression_image, images_dir / f"input_expression{expression_image.suffix}"
    )
    shutil.copy(
        background_image, images_dir / f"input_background{background_image.suffix}"
    )

    input_count = 3 + len(outfit_images) + len(face_images)
    print(f"[OK] {input_count} input images copied")

    # =========================================================
    # STEP 1-7: core 파이프라인 호출 (분석 + 프롬프트 조립 + 첫 이미지 생성)
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 1-7: Running core pipeline (analysis + prompt)")
    print("=" * 60)

    pipeline_result = generate_full_pipeline(
        face_images=face_images,
        outfit_images=outfit_images,
        pose_image=pose_image,
        expression_image=expression_image,
        background_image=background_image,
        aspect_ratio=ASPECT_RATIO,
        resolution=RESOLUTION,
        temperature=TEMPERATURE,
        client=client,
    )

    prompt = pipeline_result["prompt"]
    analysis = pipeline_result["analysis"]

    # 분석 결과 저장
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    with open(analysis_dir / "hair_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis["hair"].to_schema_format(), f, ensure_ascii=False, indent=2)

    with open(analysis_dir / "expression_analysis.json", "w", encoding="utf-8") as f:
        expr = analysis["expression"]
        if hasattr(expr, "to_schema_format"):
            expr_data = expr.to_schema_format()
        elif hasattr(expr, "to_preset_format"):
            expr_data = expr.to_preset_format()
        else:
            expr_data = {"raw": str(expr)}
        json.dump(expr_data, f, ensure_ascii=False, indent=2)

    # 얼굴 특징 분석 저장
    if "face" in analysis and analysis["face"] is not None:
        with open(analysis_dir / "face_analysis.json", "w", encoding="utf-8") as f:
            json.dump(
                analysis["face"].to_schema_format(), f, ensure_ascii=False, indent=2
            )

    with open(analysis_dir / "pose_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis["pose"].to_preset_format(), f, ensure_ascii=False, indent=2)

    with open(analysis_dir / "background_analysis.json", "w", encoding="utf-8") as f:
        json.dump(
            analysis["background"].to_preset_format(), f, ensure_ascii=False, indent=2
        )

    with open(analysis_dir / "compatibility.json", "w", encoding="utf-8") as f:
        compat = analysis["compatibility"]
        json.dump(
            {
                "level": compat.level.value,
                "score": compat.score,
                "issues": [
                    {"type": i.issue_type, "description": i.description}
                    for i in compat.issues
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # 프롬프트 저장 (텍스트, 가독용)
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"  Saved: prompt.txt")

    # prompt.json 저장 (구조화된 원본)
    prompt_json = {
        "module": "core.ai_influencer.pipeline",
        "pipeline": [
            "analyze_hair",
            "analyze_expression",
            "analyze_pose",
            "analyze_background",
            "check_compatibility",
            "OutfitAnalyzer.analyze",
            "build_schema_prompt",
            "send_image_request",
        ],
        "analysis": {
            "hair": analysis["hair"].to_schema_format(),
            "expression": analysis["expression"].to_preset_format()
            if hasattr(analysis["expression"], "to_preset_format")
            else {"raw": str(analysis["expression"])},
            "pose": analysis["pose"].to_preset_format(),
            "background": analysis["background"].to_preset_format(),
            "outfit": {
                "style": analysis["outfit"].overall_style,
                "brand": analysis["outfit"].brand_detected,
                "items": [
                    {
                        "category": item.category,
                        "name": item.name,
                        "color": item.color,
                        "fit": item.fit,
                        "logos": [
                            {"brand": l.brand, "type": l.type, "position": l.position}
                            for l in (item.logos or [])
                        ],
                        "details": item.details,
                        "state": item.state,
                    }
                    for item in analysis["outfit"].items
                ],
            },
        },
        "references": {
            "pose_image": str(pose_image),
            "expression_image": str(expression_image),
            "background_image": str(background_image),
            "face_images": [str(p) for p in face_images],
            "outfit_images": [str(p) for p in outfit_images],
        },
    }
    with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_json, f, ensure_ascii=False, indent=2)

    # =========================================================
    # STEP 8: 이미지 생성
    # 첫 번째는 generate_full_pipeline()에서 이미 생성됨
    # 나머지는 send_image_request()로 추가 생성
    # =========================================================
    print("\n" + "=" * 60)
    print(f"STEP 8: Generating {NUM_IMAGES} images (all references included)")
    print("=" * 60)

    results = []

    # 첫 번째 이미지는 pipeline 결과 사용
    first_image = pipeline_result["image"]
    if first_image:
        first_image.save(images_dir / "output_001.jpg", quality=95)
        results.append({"index": 1, "status": "success"})
        print(f"  [OK] Saved output_001.jpg (from pipeline)")
    else:
        results.append({"index": 1, "status": "failed"})
        print(f"  [FAIL] Pipeline generation failed")

    # 나머지 이미지 추가 생성 (send_image_request 사용)
    for i in range(1, NUM_IMAGES):
        print(f"\n[Generating] Image {i+1}/{NUM_IMAGES}...")
        time.sleep(2)  # rate limiting

        image = send_image_request(
            client=client,
            prompt=prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            aspect_ratio=ASPECT_RATIO,
            resolution=RESOLUTION,
            temperature=TEMPERATURE,
        )

        if image:
            image.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)
            results.append({"index": i + 1, "status": "success"})
            print(f"  [OK] Saved output_{i+1:03d}.jpg")
        else:
            results.append({"index": i + 1, "status": "failed"})
            print(f"  [FAIL] Generation failed")

    # =========================================================
    # 결과 저장 (config.json, validation.json)
    # =========================================================
    success_count = sum(1 for r in results if r["status"] == "success")

    # config.json
    config = {
        "workflow": "ai_influencer",
        "module": "core.ai_influencer.pipeline",
        "description": test_name,
        "timestamp": datetime.now().isoformat(),
        "model": IMAGE_MODEL,
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "temperature": TEMPERATURE,
        "num_images": NUM_IMAGES,
        "cost_per_image": 190,
        "total_cost": NUM_IMAGES * 190,
        "input_summary": {
            "face": len(face_images),
            "outfits": len(outfit_images),
            "pose_reference": True,
            "expression_reference": True,
            "background_reference": True,
        },
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # validation.json
    compat = analysis["compatibility"]
    outfit = analysis["outfit"]
    validation = {
        "workflow": "ai_influencer",
        "results": results,
        "total_generated": success_count,
        "total_failed": NUM_IMAGES - success_count,
        "success_rate": success_count / NUM_IMAGES * 100 if NUM_IMAGES > 0 else 0,
        "analysis": {
            "hair": analysis["hair"].to_schema_format(),
            "expression": analysis["expression"].to_preset_format()
            if hasattr(analysis["expression"], "to_preset_format")
            else {"raw": str(analysis["expression"])},
            "pose": analysis["pose"].to_preset_format(),
            "background": analysis["background"].to_preset_format(),
            "compatibility": {
                "level": compat.level.value,
                "score": compat.score,
            },
            "outfit": {
                "style": outfit.overall_style,
                "brand": outfit.brand_detected,
                "item_count": len(outfit.items),
            },
        },
    }
    with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)

    # 단일 세트 결과 출력
    print(f"\n{'=' * 60}")
    print(f"TEST COMPLETE: {test_name}")
    print(f"{'=' * 60}")
    print(f"Output: {output_dir}")
    print(f"Results: {success_count}/{NUM_IMAGES} success")
    print(f"Cost: {NUM_IMAGES * 190} won ({NUM_IMAGES} x 190)")

    return {
        "test_name": test_name,
        "output_dir": str(output_dir),
        "success_count": success_count,
        "total": NUM_IMAGES,
        "validation": validation,
    }


# ============================================================
# BATCH RUNNER
# ============================================================


def run_batch():
    """
    5개 테스트 세트를 순차적으로 실행하고 전체 요약을 출력한다.
    """

    print("=" * 60)
    print("AI INFLUENCER BATCH RUNNER - 5 TEST SETS")
    print("=" * 60)
    print(f"Settings:")
    print(f"  aspect_ratio : {ASPECT_RATIO}")
    print(f"  resolution   : {RESOLUTION}")
    print(f"  num_images   : {NUM_IMAGES}")
    print(f"  temperature  : {TEMPERATURE}")
    print(f"  test_sets    : {len(TEST_SETS)}")
    print(f"  total_images : {len(TEST_SETS) * NUM_IMAGES}")
    print(f"  total_cost   : {len(TEST_SETS) * NUM_IMAGES * 190} won")
    print("=" * 60)

    batch_start = datetime.now()
    batch_results = []

    for idx, test_name in enumerate(TEST_SETS):
        test_folder = project_root / "tests" / test_name

        print(f"\n[BATCH {idx+1}/{len(TEST_SETS)}] Starting: {test_name}")
        print(f"  Path: {test_folder}")

        set_start = datetime.now()

        try:
            result = run_test(test_name, test_folder)
            elapsed = (datetime.now() - set_start).total_seconds()

            if result is not None:
                result["elapsed_sec"] = elapsed
                batch_results.append(result)
                print(
                    f"\n[BATCH {idx+1}/{len(TEST_SETS)}] Done: {test_name} ({elapsed:.1f}s)"
                )
            else:
                batch_results.append(
                    {
                        "test_name": test_name,
                        "output_dir": None,
                        "success_count": 0,
                        "total": NUM_IMAGES,
                        "elapsed_sec": elapsed,
                        "error": "Test returned None (check missing images or errors above)",
                    }
                )
                print(f"\n[BATCH {idx+1}/{len(TEST_SETS)}] Failed: {test_name}")

        except Exception as e:
            elapsed = (datetime.now() - set_start).total_seconds()
            batch_results.append(
                {
                    "test_name": test_name,
                    "output_dir": None,
                    "success_count": 0,
                    "total": NUM_IMAGES,
                    "elapsed_sec": elapsed,
                    "error": str(e),
                }
            )
            print(f"\n[BATCH {idx+1}/{len(TEST_SETS)}] ERROR: {test_name}")
            print(f"  Exception: {e}")

        # 세트 간 대기 (마지막 세트는 대기 없음)
        if idx < len(TEST_SETS) - 1:
            print(f"\n[WAIT] Sleeping 5s before next set...")
            time.sleep(5)

    # =========================================================
    # 전체 배치 요약 출력
    # =========================================================
    total_elapsed = (datetime.now() - batch_start).total_seconds()
    total_success = sum(r.get("success_count", 0) for r in batch_results)
    total_generated = sum(r.get("total", 0) for r in batch_results)
    total_sets_ok = sum(1 for r in batch_results if r.get("success_count", 0) > 0)

    print(f"\n{'=' * 60}")
    print(f"BATCH SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total elapsed  : {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  Sets completed : {total_sets_ok}/{len(TEST_SETS)}")
    print(f"  Images success : {total_success}/{total_generated}")
    print(f"  Total cost     : {total_success * 190} won")
    print(f"")
    print(f"  {'SET':<20} {'SUCCESS':>8} {'ELAPSED':>10} {'OUTPUT'}")
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*30}")

    for r in batch_results:
        success_str = f"{r.get('success_count', 0)}/{r.get('total', NUM_IMAGES)}"
        elapsed_str = f"{r.get('elapsed_sec', 0):.1f}s"
        output_str = r.get("output_dir") or r.get("error", "N/A")
        # 출력 경로가 길면 끝만 표시
        if output_str and len(output_str) > 45:
            output_str = "..." + output_str[-42:]
        print(
            f"  {r['test_name']:<20} {success_str:>8} {elapsed_str:>10}  {output_str}"
        )

    print(f"{'=' * 60}")
    print(f"BATCH DONE")
    print(f"{'=' * 60}")

    return batch_results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_batch()
