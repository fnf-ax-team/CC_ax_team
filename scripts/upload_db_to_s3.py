"""
FNF Studio db/ 데이터를 S3에 업로드하는 스크립트.

IMPORTANT: S3 키는 로컬 상대 경로를 그대로 보존한다.
           core/storage.py가 동일한 상대 경로로 S3 URL을 생성하기 때문.

사용법:
  1. AWS credentials 설정: aws configure
  2. 실행: python scripts/upload_db_to_s3.py

S3 구조 (로컬 db/ 구조와 동일):
  s3://tmp-img-s3/LINN/fnf-studio/
  ├── db/presets/common/          # 공용 프리셋 (인플+셀카)
  │   ├── pose_presets.json
  │   ├── expression_presets.json
  │   └── background_presets.json
  ├── db/presets/influencer/      # 인플루언서 전용
  │   ├── camera_presets.json
  │   ├── styling_preset_db.json
  │   └── prompt_schema.json
  ├── db/presets/brandcut/mlb/    # MLB 브랜드컷 전용
  │   ├── mlb_pose_presets.json
  │   └── ...
  ├── db/presets/selfie/          # 셀카 전용
  │   └── scene_presets.json
  ├── db/mlb_style/               # MLB 스타일 레퍼런스 이미지
  ├── db/model/                   # 모델 얼굴 이미지
  ├── db/characters/              # AI 인플루언서 캐릭터
  ├── db/인플테스트/               # 프리셋 레퍼런스 이미지
  └── outputs/                    # 생성 결과물 (MCP 모드)
"""

import os
import sys
from pathlib import Path

# boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("[ERROR] boto3 not installed. Run: pip install boto3")
    sys.exit(1)


# ============================================================
# CONFIG
# ============================================================
S3_BUCKET = "tmp-img-s3"
S3_PREFIX = "LINN/fnf-studio"
REGION = "ap-northeast-2"

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "db"

# 업로드 대상 정의 — s3_key = local 경로 그대로 (core/storage.py 매칭 필수)
UPLOAD_TARGETS = [
    # JSON 프리셋 파일 (재편된 폴더 구조)
    {
        "local": "db/presets/common/pose_presets.json",
        "s3_key": "db/presets/common/pose_presets.json",
    },
    {
        "local": "db/presets/common/expression_presets.json",
        "s3_key": "db/presets/common/expression_presets.json",
    },
    {
        "local": "db/presets/common/background_presets.json",
        "s3_key": "db/presets/common/background_presets.json",
    },
    {
        "local": "db/presets/influencer/camera_presets.json",
        "s3_key": "db/presets/influencer/camera_presets.json",
    },
    {
        "local": "db/presets/influencer/styling_preset_db.json",
        "s3_key": "db/presets/influencer/styling_preset_db.json",
    },
    {
        "local": "db/presets/selfie/scene_presets.json",
        "s3_key": "db/presets/selfie/scene_presets.json",
    },
    {
        "local": "db/presets/influencer/prompt_schema.json",
        "s3_key": "db/presets/influencer/prompt_schema.json",
    },
]

# 폴더 단위 업로드 — s3_prefix = local 경로 그대로 (core/storage.py 매칭 필수)
UPLOAD_FOLDERS = [
    {
        "local": "db/mlb_style",
        "s3_prefix": "db/mlb_style",
        "desc": "MLB style references",
    },
    {
        "local": "db/results",
        "s3_prefix": "db/results",
        "desc": "Style analysis JSONs",
    },
    {"local": "db/presets_v2", "s3_prefix": "db/presets_v2", "desc": "V2 presets"},
]

# MLB 전용 프리셋 (db/presets/brandcut/mlb/ 내 JSON)
MLB_PRESET_DIR = "db/presets/brandcut/mlb"
MLB_PRESET_FILES = [
    "mlb_expression_presets.json",
    "mlb_pose_presets.json",
    "mlb_background_presets.json",
    "mlb_camera_presets.json",
    "mlb_styling_presets.json",
    "mlb_model_presets.json",
]

# CLIP 임베딩 — s3_key = local 경로 그대로
EMBEDDING_FILES = [
    {
        "local": "db/clip_a_grade_embeddings.npz",
        "s3_key": "db/clip_a_grade_embeddings.npz",
    },
]


# ============================================================
# UPLOAD FUNCTIONS
# ============================================================


def get_s3_client():
    """S3 클라이언트 생성."""
    return boto3.client("s3", region_name=REGION)


def upload_file(s3_client, local_path: Path, s3_key: str, dry_run: bool = False):
    """단일 파일 업로드."""
    full_key = f"{S3_PREFIX}/{s3_key}"

    if not local_path.exists():
        print(f"  [SKIP] Not found: {local_path}")
        return False

    size_mb = local_path.stat().st_size / (1024 * 1024)

    if dry_run:
        print(f"  [DRY] {local_path} -> s3://{S3_BUCKET}/{full_key} ({size_mb:.1f}MB)")
        return True

    try:
        # Content type 설정
        content_type = "application/json"
        ext = local_path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif ext in (".png",):
            content_type = "image/png"
        elif ext in (".webp",):
            content_type = "image/webp"
        elif ext in (".npz",):
            content_type = "application/octet-stream"

        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            full_key,
            ExtraArgs={"ContentType": content_type},
        )
        print(
            f"  [OK] {local_path.name} -> s3://{S3_BUCKET}/{full_key} ({size_mb:.1f}MB)"
        )
        return True
    except ClientError as e:
        print(f"  [ERROR] {local_path.name}: {e}")
        return False


def upload_folder(
    s3_client,
    local_folder: Path,
    s3_prefix: str,
    extensions: set = None,
    dry_run: bool = False,
):
    """폴더 내 모든 파일 업로드."""
    if not local_folder.exists():
        print(f"  [SKIP] Folder not found: {local_folder}")
        return 0

    if extensions is None:
        extensions = {".jpg", ".jpeg", ".png", ".webp", ".json", ".npz", ".md"}

    count = 0
    for file_path in sorted(local_folder.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        # 상대 경로 계산
        rel_path = file_path.relative_to(local_folder)
        s3_key = f"{s3_prefix}/{rel_path.as_posix()}"

        if upload_file(s3_client, file_path, s3_key, dry_run):
            count += 1

    return count


def upload_characters(s3_client, dry_run: bool = False):
    """AI 인플루언서 캐릭터 폴더 업로드.

    S3 키는 로컬 상대 경로를 그대로 보존.
    예: db/인플테스트/3. 포즈/전신 (1).jpeg
      → s3://tmp-img-s3/LINN/fnf-studio/db/인플테스트/3. 포즈/전신 (1).jpeg
    """
    # db/ 하위 폴더 중 캐릭터/프리셋 레퍼런스 이미지 포함 폴더
    char_dirs = [
        ("db/ai_influencer", DB_DIR / "ai_influencer"),
        ("db/인플테스트", DB_DIR / "인플테스트"),
        ("db/characters", DB_DIR / "characters"),
        ("db/model", DB_DIR / "model"),
    ]

    count = 0
    for s3_base, char_dir in char_dirs:
        if not char_dir.exists():
            continue

        print(f"\n  [CHARS] Scanning {char_dir.name}/")
        # 폴더 전체를 db/ prefix 보존하여 업로드
        n = upload_folder(s3_client, char_dir, s3_base, dry_run=dry_run)
        count += n

    return count


# ============================================================
# MAIN
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Upload FNF Studio db/ to S3")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without uploading"
    )
    args = parser.parse_args()

    dry_run = args.dry_run

    print("=" * 60)
    print(f"FNF Studio DB -> S3 Upload")
    print(f"Bucket: s3://{S3_BUCKET}/{S3_PREFIX}/")
    print(f"Region: {REGION}")
    print(f"Mode:   {'DRY RUN (no upload)' if dry_run else 'UPLOAD'}")
    print("=" * 60)

    s3_client = get_s3_client()
    total = 0

    # 1. JSON 프리셋 파일
    print("\n[1/6] JSON Presets")
    for target in UPLOAD_TARGETS:
        local = PROJECT_ROOT / target["local"]
        if upload_file(s3_client, local, target["s3_key"], dry_run):
            total += 1

    # 2. MLB 전용 프리셋 (db/presets/brandcut/mlb/)
    print("\n[2/6] MLB Presets")
    mlb_dir = PROJECT_ROOT / MLB_PRESET_DIR
    for fname in MLB_PRESET_FILES:
        local = mlb_dir / fname
        s3_key = f"{MLB_PRESET_DIR}/{fname}"
        if upload_file(s3_client, local, s3_key, dry_run):
            total += 1

    # 3. 폴더 단위 업로드
    print("\n[3/6] Folders (mlb_style, results, presets_v2)")
    for folder_target in UPLOAD_FOLDERS:
        local = PROJECT_ROOT / folder_target["local"]
        print(f"\n  --- {folder_target['desc']} ---")
        n = upload_folder(s3_client, local, folder_target["s3_prefix"], dry_run=dry_run)
        total += n

    # 4. 캐릭터 데이터
    print("\n[4/6] Characters (AI Influencer)")
    total += upload_characters(s3_client, dry_run)

    # 5. CLIP 임베딩
    print("\n[5/6] Embeddings")
    for target in EMBEDDING_FILES:
        local = PROJECT_ROOT / target["local"]
        if upload_file(s3_client, local, target["s3_key"], dry_run):
            total += 1

    # 6. 요약
    print("\n" + "=" * 60)
    print(f"[DONE] Total files: {total}")
    print(f"S3 location: s3://{S3_BUCKET}/{S3_PREFIX}/")

    if dry_run:
        print("\n[INFO] This was a DRY RUN. Run without --dry-run to upload.")
    else:
        print("\n[INFO] Upload complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
