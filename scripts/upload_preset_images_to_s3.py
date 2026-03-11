"""
프리셋 이미지 + 캐릭터 얼굴 + MLB 스타일을 S3에 업로드.
+ 각 디렉토리에 _manifest.json 생성 (S3 모드에서 파일 목록 조회용)

프리셋 구조 (2026.03 재편):
  db/presets/
  ├── common/          (인플+셀카 공용: pose, expression, background)
  ├── influencer/      (인플루언서 전용: camera, styling, prompt_schema)
  ├── brandcut/mlb/    (MLB 브랜드컷 전용)
  └── selfie/          (셀카 전용: scene)

사용법:
    python scripts/upload_preset_images_to_s3.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
S3_BUCKET = "tmp-img-s3"
S3_PREFIX = "LINN/fnf-studio"
AWS_PROFILE = "Restricted-Developer-760196398155"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
JSON_EXTS = {".json"}
DATA_EXTS = {".npz"}


def collect_preset_image_paths():
    """프리셋 JSON에서 참조하는 이미지 경로 수집."""
    # 새 프리셋 구조
    preset_files = [
        # common (인플+셀카 공용)
        "db/presets/common/pose_presets.json",
        "db/presets/common/expression_presets.json",
        "db/presets/common/background_presets.json",
        # influencer 전용
        "db/presets/influencer/camera_presets.json",
        "db/presets/influencer/styling_preset_db.json",
        "db/presets/influencer/prompt_schema.json",
        # brandcut/mlb 전용
        "db/presets/brandcut/mlb/mlb_pose_presets.json",
        "db/presets/brandcut/mlb/mlb_expression_presets.json",
        "db/presets/brandcut/mlb/mlb_background_presets.json",
        "db/presets/brandcut/mlb/mlb_camera_presets.json",
        "db/presets/brandcut/mlb/mlb_model_presets.json",
        "db/presets/brandcut/mlb/mlb_styling_presets.json",
        # selfie 전용
        "db/presets/selfie/scene_presets.json",
    ]

    paths = set()
    for f in preset_files:
        full = PROJECT_ROOT / f
        if not full.exists():
            print(f"[SKIP] {f} not found")
            continue

        with open(full, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        def find_image_paths(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if any(kw in k.lower() for kw in ["image", "path", "reference"]):
                        if isinstance(v, str) and any(
                            v.lower().endswith(ext) for ext in IMAGE_EXTS
                        ):
                            paths.add(v)
                    find_image_paths(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_image_paths(item)

        find_image_paths(data)

    return paths


def collect_directory_files(relative_dir, extensions=IMAGE_EXTS):
    """디렉토리의 모든 파일 수집."""
    full_dir = PROJECT_ROOT / relative_dir
    if not full_dir.exists():
        return []

    files = []
    for root, _, filenames in os.walk(full_dir):
        for fname in filenames:
            if Path(fname).suffix.lower() in extensions:
                full_path = Path(root) / fname
                rel = full_path.relative_to(PROJECT_ROOT)
                files.append(str(rel).replace("\\", "/"))
    return files


def s3_upload(local_path, s3_key):
    """단일 파일 S3 업로드."""
    cmd = [
        "aws",
        "s3",
        "cp",
        str(local_path),
        f"s3://{S3_BUCKET}/{S3_PREFIX}/{s3_key}",
        "--profile",
        AWS_PROFILE,
        "--quiet",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [FAIL] {s3_key}: {result.stderr.strip()}")
        return False
    return True


def create_manifest(relative_dir, files):
    """디렉토리에 _manifest.json 생성 및 업로드."""
    manifest_path = PROJECT_ROOT / relative_dir / "_manifest.json"
    # 상대 경로만 저장
    relative_files = []
    for f in files:
        name = Path(f).name
        relative_files.append(f"{relative_dir}/{name}")

    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(sorted(relative_files), fp, ensure_ascii=False, indent=2)

    s3_key = f"{relative_dir}/_manifest.json"
    s3_upload(manifest_path, s3_key)
    print(f"  [MANIFEST] {s3_key} ({len(relative_files)} files)")


def main():
    print("=== FNF Studio Preset Image S3 Uploader ===\n")

    all_files = []

    # 1. 프리셋 JSON 파일 (새 구조)
    preset_jsons = collect_directory_files("db/presets", JSON_EXTS)
    all_files.extend(preset_jsons)
    print(f"[1] Preset JSONs (db/presets/): {len(preset_jsons)} files")

    # 2. 프리셋에서 참조하는 이미지
    preset_images = collect_preset_image_paths()
    existing_preset_images = []
    for p in preset_images:
        full = PROJECT_ROOT / p
        if full.exists():
            existing_preset_images.append(p.replace("\\", "/"))
    all_files.extend(existing_preset_images)
    print(f"[2] Preset reference images: {len(existing_preset_images)} files")

    # 3. 캐릭터(모델) 얼굴 이미지
    model_files = collect_directory_files("db/model", IMAGE_EXTS)
    all_files.extend(model_files)
    print(f"[3] Character face images: {len(model_files)} files")

    # 4. AI 인플루언서 캐릭터 데이터
    influencer_files = collect_directory_files(
        "db/ai_influencer", IMAGE_EXTS | JSON_EXTS
    )
    all_files.extend(influencer_files)
    print(f"[4] AI Influencer character files: {len(influencer_files)} files")

    # 5. MLB 스타일 이미지 + JSON
    mlb_files = collect_directory_files(
        "db/mlb_style", IMAGE_EXTS | JSON_EXTS | DATA_EXTS
    )
    all_files.extend(mlb_files)
    print(f"[5] MLB style files: {len(mlb_files)} files")

    # 6. 이커머스 템플릿
    ecom_files = ["db/ecommerce_templates.json"]
    for f in ecom_files:
        if (PROJECT_ROOT / f).exists():
            all_files.append(f)
    ecom_count = len([f for f in ecom_files if (PROJECT_ROOT / f).exists()])
    print(f"[6] Ecommerce templates: {ecom_count} files")

    # 중복 제거
    all_files = sorted(set(all_files))
    print(f"\n=== Total files to upload: {len(all_files)} ===\n")

    # 업로드
    success = 0
    fail = 0
    for i, f in enumerate(all_files):
        local_path = PROJECT_ROOT / f.replace("/", os.sep)
        if not local_path.exists():
            print(f"  [{i+1}/{len(all_files)}] SKIP (not found): {f}")
            fail += 1
            continue

        s3_key = f.replace("\\", "/")
        ok = s3_upload(local_path, s3_key)
        if ok:
            success += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(all_files)}] uploaded...")
        else:
            fail += 1

    print(f"\n=== Upload complete: {success} OK, {fail} failed ===")

    # manifest 생성
    print("\n=== Creating manifests ===")

    # 캐릭터별 manifest
    model_dir = PROJECT_ROOT / "db" / "model"
    if model_dir.exists():
        for char_dir in model_dir.iterdir():
            if char_dir.is_dir():
                char_files = [
                    f for f in model_files if f.startswith(f"db/model/{char_dir.name}/")
                ]
                if char_files:
                    create_manifest(f"db/model/{char_dir.name}", char_files)

    # AI 인플루언서 캐릭터별 manifest
    infl_dir = PROJECT_ROOT / "db" / "ai_influencer"
    if infl_dir.exists():
        for char_dir in infl_dir.iterdir():
            if char_dir.is_dir():
                # face 폴더 manifest
                face_dir = char_dir / "face"
                if face_dir.exists():
                    face_files = [
                        f
                        for f in influencer_files
                        if f.startswith(f"db/ai_influencer/{char_dir.name}/face/")
                    ]
                    if face_files:
                        create_manifest(
                            f"db/ai_influencer/{char_dir.name}/face", face_files
                        )

    print("\n[DONE]")

    # S3 base URL 안내
    print(
        f"\nS3 Base URL: https://{S3_BUCKET}.s3.ap-northeast-2.amazonaws.com/{S3_PREFIX}"
    )
    print("Set environment: FNF_STORAGE_MODE=s3")
    print(
        f"Set environment: FNF_S3_BASE_URL=https://{S3_BUCKET}.s3.ap-northeast-2.amazonaws.com/{S3_PREFIX}"
    )


if __name__ == "__main__":
    main()
