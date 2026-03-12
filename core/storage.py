"""
FNF Studio Storage Module

로컬 파일 / S3 URL 자동 전환 이미지 로더 + 아웃풋 저장.

=== 읽기 (인풋/프리셋) ===
    from core.storage import get_image, get_json, get_image_url

    img = get_image("db/model/MLB_KARINA/face_01.jpg")
    data = get_json("db/presets/common/pose_presets.json")
    url = get_image_url("db/model/MLB_KARINA/face_01.jpg")

=== 쓰기 (아웃풋) ===
    from core.storage import save_output_image, save_output_json

    # PIL Image 저장 → 로컬 경로 or S3 URL 반환
    result_url = save_output_image(pil_image, "brand_cut/20260312_143000_mlb/images/output_001.jpg")

    # JSON 저장
    save_output_json(data, "brand_cut/20260312_143000_mlb/prompt.json")

환경변수:
    FNF_STORAGE_MODE: "local" (기본) | "s3"
    FNF_S3_BASE_URL: S3 base URL (읽기용)
    FNF_OUTPUT_MODE: "local" (기본) | "s3" (아웃풋 저장 위치)
    FNF_S3_BUCKET: S3 버킷명 (쓰기용, 기본: tmp-img-s3)
    FNF_S3_PREFIX: S3 키 접두사 (쓰기용, 기본: LINN/fnf-studio)
    FNF_S3_REGION: AWS 리전 (쓰기용, 기본: ap-northeast-2)
"""

import os
import json
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Union

from PIL import Image

# S3 설정 (읽기)
_STORAGE_MODE = os.environ.get("FNF_STORAGE_MODE", "local")
_S3_BASE_URL = os.environ.get(
    "FNF_S3_BASE_URL",
    "https://tmp-img-s3.s3.ap-northeast-2.amazonaws.com/LINN/fnf-studio",
)

# S3 설정 (쓰기 - 아웃풋 업로드용)
_OUTPUT_MODE = os.environ.get("FNF_OUTPUT_MODE", "local")
_S3_BUCKET = os.environ.get("FNF_S3_BUCKET", "tmp-img-s3")
_S3_PREFIX = os.environ.get("FNF_S3_PREFIX", "LINN/fnf-studio")
_S3_REGION = os.environ.get("FNF_S3_REGION", "ap-northeast-2")

# 프로젝트 루트
_PROJECT_ROOT = Path(__file__).parent.parent

# 로컬 아웃풋 디렉토리
_OUTPUT_DIR = _PROJECT_ROOT / "Fnf_studio_outputs"

# 로컬 캐시 디렉토리 (S3에서 다운받은 파일 저장)
_CACHE_DIR = Path(tempfile.gettempdir()) / "fnf_studio_cache"


def _ensure_cache_dir():
    """캐시 디렉토리 생성."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(relative_path: str) -> Path:
    """상대 경로에 대한 캐시 파일 경로 반환."""
    # 경로를 해시하여 캐시 파일명 생성 (한글 경로 대응)
    path_hash = hashlib.md5(relative_path.encode("utf-8")).hexdigest()
    ext = Path(relative_path).suffix or ".bin"
    return _CACHE_DIR / f"{path_hash}{ext}"


def _normalize_path(path: str) -> str:
    """경로 구분자 정규화 (Windows \\ -> /)."""
    return path.replace("\\", "/")


def _to_s3_url(relative_path: str) -> str:
    """상대 경로를 S3 URL로 변환."""
    normalized = _normalize_path(relative_path)
    # URL 인코딩 (한글 경로)
    from urllib.parse import quote

    encoded = quote(normalized, safe="/")
    return f"{_S3_BASE_URL}/{encoded}"


def _download_from_s3(relative_path: str) -> Path:
    """S3에서 파일 다운로드 후 캐시 경로 반환."""
    import httpx

    _ensure_cache_dir()
    cached = _cache_path(relative_path)

    # 이미 캐시에 있으면 재사용
    if cached.exists():
        return cached

    url = _to_s3_url(relative_path)
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        cached.write_bytes(response.content)
        return cached
    except Exception as e:
        raise FileNotFoundError(f"S3 다운로드 실패: {url} -> {e}") from e


def is_s3_mode() -> bool:
    """현재 S3 모드인지 확인."""
    return _STORAGE_MODE.lower() == "s3"


def get_storage_mode() -> str:
    """현재 스토리지 모드 반환."""
    return _STORAGE_MODE


def resolve_path(relative_path: str) -> Path:
    """상대 경로를 실제 파일 경로로 변환.

    - local 모드: 프로젝트 루트 기준 로컬 경로
    - s3 모드: S3에서 다운로드 후 캐시 경로

    Args:
        relative_path: 'db/presets/common/pose_presets.json' 같은 상대 경로

    Returns:
        실제 파일에 접근 가능한 Path
    """
    normalized = _normalize_path(relative_path)

    # 1. 로컬에 있으면 로컬 사용 (모드 무관)
    local_path = _PROJECT_ROOT / normalized
    if local_path.exists():
        return local_path

    # 2. S3 모드면 다운로드
    if is_s3_mode():
        return _download_from_s3(normalized)

    # 3. 로컬 모드인데 파일 없으면 에러
    raise FileNotFoundError(f"파일 없음: {local_path} (storage_mode={_STORAGE_MODE})")


def get_image(relative_path: str) -> Image.Image:
    """이미지 파일을 PIL Image로 로드.

    Args:
        relative_path: 'db/model/MLB_KARINA/face_01.jpg' 같은 상대 경로

    Returns:
        PIL.Image (RGB)
    """
    path = resolve_path(relative_path)
    return Image.open(path).convert("RGB")


def get_json(relative_path: str) -> Union[dict, list]:
    """JSON 파일 로드.

    Args:
        relative_path: 'db/presets/common/pose_presets.json' 같은 상대 경로

    Returns:
        파싱된 JSON (dict or list)
    """
    path = resolve_path(relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_image_url(relative_path: str) -> Optional[str]:
    """이미지의 S3 공개 URL 반환. 로컬 모드면 None.

    Gemini API에 URL로 직접 전달할 때 사용.

    Args:
        relative_path: 상대 경로

    Returns:
        S3 URL (s3 모드) 또는 None (local 모드)
    """
    if is_s3_mode():
        return _to_s3_url(_normalize_path(relative_path))
    return None


def list_files(relative_dir: str, extensions: list[str] = None) -> list[str]:
    """디렉토리 내 파일 목록 반환.

    Args:
        relative_dir: 'db/model/MLB_KARINA' 같은 상대 디렉토리 경로
        extensions: 필터링할 확장자 목록 ['.jpg', '.png']

    Returns:
        상대 경로 리스트
    """
    normalized = _normalize_path(relative_dir)
    local_dir = _PROJECT_ROOT / normalized

    if local_dir.exists():
        files = []
        for f in local_dir.iterdir():
            if f.is_file():
                if extensions is None or f.suffix.lower() in extensions:
                    files.append(f"{normalized}/{f.name}")
        return sorted(files)

    # S3 모드에서는 로컬 파일 목록을 제공할 수 없음
    # manifest.json을 사용해야 함
    if is_s3_mode():
        manifest_path = f"{normalized}/_manifest.json"
        try:
            manifest = get_json(manifest_path)
            if extensions:
                return [
                    f
                    for f in manifest
                    if any(f.lower().endswith(ext) for ext in extensions)
                ]
            return manifest
        except FileNotFoundError:
            return []

    return []


def resolve_image_for_api(relative_path: str) -> Union[str, Path]:
    """이미지를 Gemini API 전달에 최적화된 형태로 반환.

    - S3 모드: S3 URL 문자열 반환 (다운로드 없이 Gemini에 직접 전달)
    - 로컬 모드: 파일 경로 반환

    api.py의 image_to_part()와 함께 사용:
        from core.storage import resolve_image_for_api
        from core.api import image_to_part

        img_ref = resolve_image_for_api("db/presets/common/4. 배경/sunset.jpg")
        part = image_to_part(img_ref)  # URL이면 from_uri, 파일이면 inline_data

    Args:
        relative_path: 'db/model/MLB_KARINA/face_01.jpg' 같은 상대 경로

    Returns:
        S3 URL 문자열 (s3 모드) 또는 로컬 파일 Path (local 모드)
    """
    if is_s3_mode():
        return _to_s3_url(_normalize_path(relative_path))

    # 로컬 모드: 파일 존재 확인
    normalized = _normalize_path(relative_path)
    local_path = _PROJECT_ROOT / normalized
    if local_path.exists():
        return local_path

    raise FileNotFoundError(f"파일 없음: {local_path} (storage_mode={_STORAGE_MODE})")


def clear_cache():
    """로컬 캐시 전체 삭제."""
    import shutil

    if _CACHE_DIR.exists():
        shutil.rmtree(_CACHE_DIR)


# ============================================================
# 아웃풋 저장 (로컬 or S3)
# ============================================================


def is_output_s3() -> bool:
    """아웃풋을 S3에 저장하는 모드인지 확인."""
    return _OUTPUT_MODE.lower() == "s3"


def _get_s3_client():
    """boto3 S3 클라이언트 생성 (lazy import)."""
    import boto3

    return boto3.client("s3", region_name=_S3_REGION)


def _upload_bytes_to_s3(
    data: bytes, s3_key: str, content_type: str = "image/jpeg"
) -> str:
    """바이트 데이터를 S3에 업로드하고 공개 URL 반환."""
    client = _get_s3_client()
    full_key = f"{_S3_PREFIX}/{s3_key}"

    client.put_object(
        Bucket=_S3_BUCKET,
        Key=full_key,
        Body=data,
        ContentType=content_type,
    )

    return f"https://{_S3_BUCKET}.s3.{_S3_REGION}.amazonaws.com/{full_key}"


def save_output_image(image: Image.Image, relative_path: str, quality: int = 95) -> str:
    """생성된 이미지 저장.

    - local 모드: Fnf_studio_outputs/{relative_path}에 저장, 로컬 경로 반환
    - s3 모드: S3에 업로드, 공개 URL 반환

    Args:
        image: PIL Image 객체
        relative_path: 'brand_cut/20260312_143000_mlb/images/output_001.jpg'
        quality: JPEG 품질 (기본 95)

    Returns:
        로컬 경로 문자열 (local) 또는 S3 URL (s3)
    """
    import io

    normalized = _normalize_path(relative_path)

    if is_output_s3():
        # S3에 업로드
        buf = io.BytesIO()
        ext = Path(normalized).suffix.lower()
        fmt = "PNG" if ext == ".png" else "JPEG"
        content_type = "image/png" if ext == ".png" else "image/jpeg"
        image.save(buf, format=fmt, quality=quality)
        buf.seek(0)

        s3_key = f"outputs/{normalized}"
        url = _upload_bytes_to_s3(buf.read(), s3_key, content_type)
        return url
    else:
        # 로컬 저장
        local_path = _OUTPUT_DIR / normalized
        local_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(local_path), quality=quality)
        return str(local_path)


def save_output_json(data: Union[dict, list], relative_path: str) -> str:
    """JSON 데이터 저장 (prompt.json, config.json, validation.json 등).

    Args:
        data: JSON 데이터
        relative_path: 'brand_cut/20260312_143000_mlb/prompt.json'

    Returns:
        로컬 경로 문자열 (local) 또는 S3 URL (s3)
    """
    normalized = _normalize_path(relative_path)
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    if is_output_s3():
        s3_key = f"outputs/{normalized}"
        url = _upload_bytes_to_s3(content, s3_key, "application/json")
        return url
    else:
        local_path = _OUTPUT_DIR / normalized
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        return str(local_path)


def save_output_file(src_path: Union[str, Path], relative_path: str) -> str:
    """로컬 파일을 아웃풋 위치에 복사/업로드.

    인풋 이미지 복사용 (input_face_01.jpg 등).

    Args:
        src_path: 복사할 원본 파일 (로컬 경로 또는 S3 상대 경로)
        relative_path: 'brand_cut/20260312_143000_mlb/images/input_face_01.jpg'

    Returns:
        로컬 경로 문자열 (local) 또는 S3 URL (s3)
    """
    import shutil

    normalized = _normalize_path(relative_path)

    # 원본 파일 resolve (로컬 또는 S3에서 다운로드)
    if isinstance(src_path, str) and not Path(src_path).is_absolute():
        # 상대 경로 → core/storage로 resolve
        actual_path = resolve_path(src_path)
    else:
        actual_path = Path(src_path)

    if is_output_s3():
        content = actual_path.read_bytes()
        ext = Path(normalized).suffix.lower()
        ct_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".json": "application/json",
        }
        content_type = ct_map.get(ext, "application/octet-stream")

        s3_key = f"outputs/{normalized}"
        url = _upload_bytes_to_s3(content, s3_key, content_type)
        return url
    else:
        local_path = _OUTPUT_DIR / normalized
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(actual_path), str(local_path))
        return str(local_path)


def get_output_url(relative_path: str) -> str:
    """아웃풋의 접근 가능한 URL/경로 반환.

    - local 모드: '/outputs/{relative_path}' (API 서빙용)
    - s3 모드: S3 공개 URL

    Args:
        relative_path: 'brand_cut/.../output_001.jpg'

    Returns:
        URL 문자열
    """
    normalized = _normalize_path(relative_path)

    if is_output_s3():
        from urllib.parse import quote

        encoded = quote(f"outputs/{normalized}", safe="/")
        return (
            f"https://{_S3_BUCKET}.s3.{_S3_REGION}.amazonaws.com/{_S3_PREFIX}/{encoded}"
        )
    else:
        return f"/outputs/{normalized}"
