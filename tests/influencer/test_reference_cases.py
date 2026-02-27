"""
AI Influencer Image Generation - Full Pipeline Test

테스트 래퍼: 입력 준비 + core 파이프라인 호출 + 결과 저장만 담당.

모든 비즈니스 로직은 core/ai_influencer/ 모듈에 위치:
- core/ai_influencer/hair_analyzer.py    -- 헤어 분석
- core/ai_influencer/expression_analyzer.py -- 표정 분석 (상세)
- core/ai_influencer/pose_analyzer.py    -- 포즈 분석
- core/ai_influencer/background_analyzer.py -- 배경 분석
- core/ai_influencer/compatibility.py    -- 포즈-배경 호환성
- core/ai_influencer/prompt_builder.py   -- 스키마 프롬프트 조립
- core/ai_influencer/pipeline.py         -- 풀 파이프라인 오케스트레이터

사용법:
  python tests/influencer/test_reference_cases.py --test-dir tests/인플테스트3 --num-images 5
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

# .env 로드
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from PIL import Image
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
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"


# ============================================================
# TEST RUNNER
# ============================================================


def run_test(test_name: str, test_folder: Path):
    """
    AI 인플루언서 이미지 생성 테스트

    core/ai_influencer/pipeline.py의 generate_full_pipeline()을 호출하고
    결과를 표준 폴더 구조로 저장한다.
    """

    print(f"\n{'#' * 60}")
    print(f"# AI INFLUENCER - FULL PIPELINE TEST: {test_name}")
    print(f"# Folder: {test_folder}")
    print(f"{'#' * 60}")

    if not test_folder.exists():
        print(f"[ERROR] Test folder not found: {test_folder}")
        return

    # API 클라이언트
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
        return

    # 인풋 이미지 복사
    for face_path in face_images:
        shutil.copy(face_path, images_dir / f"input_face.png")
    for i, outfit_path in enumerate(outfit_images):
        shutil.copy(outfit_path, images_dir / f"input_outfit_{i+1:02d}.png")
    shutil.copy(pose_image, images_dir / "input_pose.png")
    shutil.copy(
        expression_image, images_dir / f"input_expression{expression_image.suffix}"
    )
    shutil.copy(
        background_image, images_dir / f"input_background{background_image.suffix}"
    )
    print(f"[OK] {3 + len(outfit_images) + len(face_images)} input images copied")

    # =========================================================
    # STEP 1-7: core 파이프라인 호출 (분석 + 프롬프트 조립)
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
        temperature=0.35,
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
        json.dump(
            analysis["expression"].to_schema_format(), f, ensure_ascii=False, indent=2
        )
    with open(analysis_dir / "pose_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis["pose"].to_schema_format(), f, ensure_ascii=False, indent=2)
    with open(analysis_dir / "background_analysis.json", "w", encoding="utf-8") as f:
        json.dump(
            analysis["background"].to_schema_format(), f, ensure_ascii=False, indent=2
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

    # 프롬프트 저장
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"  Saved: prompt.txt")

    # prompt.json 저장
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
            "expression": analysis["expression"].to_schema_format(),
            "pose": analysis["pose"].to_schema_format(),
            "background": analysis["background"].to_schema_format(),
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
    # STEP 8: 이미지 생성 (첫 번째는 pipeline에서 이미 생성됨)
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

    # 나머지 이미지 추가 생성
    for i in range(1, NUM_IMAGES):
        print(f"\n[Generating] Image {i+1}/{NUM_IMAGES}...")

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
            temperature=0.35,
        )

        if image:
            image.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)
            results.append({"index": i + 1, "status": "success"})
            print(f"  [OK] Saved output_{i+1:03d}.jpg")
        else:
            results.append({"index": i + 1, "status": "failed"})
            print(f"  [FAIL] Generation failed")

        if i < NUM_IMAGES - 1:
            time.sleep(2)  # Rate limit

    # =========================================================
    # 결과 저장
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
        "temperature": 0.35,
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
            "expression": analysis["expression"].to_schema_format(),
            "pose": analysis["pose"].to_schema_format(),
            "background": analysis["background"].to_schema_format(),
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

    # 결과 출력
    print(f"\n{'=' * 60}")
    print(f"TEST COMPLETE: {test_name}")
    print(f"{'=' * 60}")
    print(f"Output: {output_dir}")
    print(f"Results: {success_count}/{NUM_IMAGES} success")
    print(f"Cost: {NUM_IMAGES * 190} won ({NUM_IMAGES} x 190)")

    return validation


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Influencer Full Pipeline Test")
    parser.add_argument(
        "--test-dir",
        type=str,
        required=True,
        help="Test folder path (e.g., tests/인플테스트3)",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=3,
        help="Number of images (default: 3)",
    )

    args = parser.parse_args()

    # Override NUM_IMAGES
    NUM_IMAGES = args.num_images

    # Resolve test folder
    test_folder = Path(args.test_dir)
    if not test_folder.is_absolute():
        test_folder = project_root / args.test_dir

    test_name = test_folder.name
    run_test(test_name, test_folder)
