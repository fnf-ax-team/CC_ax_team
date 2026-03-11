"""
FNF Studio Storage Module

로컬 파일 / S3 URL 자동 전환 이미지 로더.

사용법:
    from core.storage import get_image, get_json, get_image_url

    # PIL Image로 로드 (로컬 or S3)
    img = get_image("db/model/MLB_KARINA/face_01.jpg")

    # JSON 파일 로드
    data = get_json("db/presets/common/pose_presets.json")

    # S3 공개 URL 반환 (Gemini API에 직접 전달용)
    url = get_image_url("db/model/MLB_KARINA/face_01.jpg")

환경변수:
    FNF_STORAGE_MODE: "local" (기본) | "s3"
    FNF_S3_BASE_URL: S3 base URL (예: https://tmp-img-s3.s3.ap-northeast-2.amazonaws.com/LINN/fnf-studio)
"""

import os
import json
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Union

from PIL import Image

# S3 설정
_STORAGE_MODE = os.environ.get("FNF_STORAGE_MODE", "local")
_S3_BASE_URL = os.environ.get(
    "FNF_S3_BASE_URL",
    "https://tmp-img-s3.s3.ap-northeast-2.amazonaws.com/LINN/fnf-studio",
)

# 프로젝트 루트
_PROJECT_ROOT = Path(__file__).parent.parent

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
