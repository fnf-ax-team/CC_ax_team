"""
공유 유틸리티 - 이미지 처리 및 API 관리
"""

import os
import json
import threading
from io import BytesIO
from PIL import Image
from typing import Dict, Any, List

from google.genai import types


def pil_to_part(image_pil: Image.Image, max_size: int = 1024) -> types.Part:
    """
    PIL Image를 Gemini API Part로 변환.

    Args:
        image_pil: PIL Image 객체
        max_size: 최대 크기 (다운샘플링)

    Returns:
        types.Part(inline_data=types.Blob(...))
    """
    img = image_pil.copy().convert("RGB")
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


class ImageUtils:
    """공통 이미지 처리 유틸리티"""

    @staticmethod
    def load_image(path: str, max_size: int = 1024) -> bytes:
        """이미지 로드 및 리사이즈 후 PNG 바이트 반환"""
        img = Image.open(path).convert("RGB")

        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            img = img.resize(
                (int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS
            )

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def get_aspect_ratio(width: int, height: int) -> str:
        """이미지 크기에서 가장 가까운 표준 비율 반환"""
        ratio = width / height
        ratios = {
            "1:1": 1.0,
            "2:3": 0.667,
            "3:2": 1.5,
            "3:4": 0.75,
            "4:3": 1.333,
            "4:5": 0.8,
            "5:4": 1.25,
            "9:16": 0.5625,
            "16:9": 1.778,
            "21:9": 2.333,
        }
        return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))

    @staticmethod
    def parse_json(text: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 파싱 (마크다운 코드블록 처리)"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(text)
        except Exception:
            return {"error": "JSON parse error", "raw": text}

    @staticmethod
    def resize_output(
        img: Image.Image, orig_size: tuple, target: int = 2560
    ) -> Image.Image:
        """출력 이미지를 목표 해상도로 리사이즈"""
        w, h = orig_size
        if w > h:
            nw, nh = target, int(target * h / w)
        else:
            nh, nw = target, int(target * w / h)
        return img.resize((nw, nh), Image.LANCZOS)


class ApiKeyManager:
    """스레드 안전 API 키 로테이션 관리자"""

    def __init__(self, api_keys: List[str] = None):
        self._api_keys = api_keys or self._load_keys()
        self._lock = threading.Lock()
        self._index = 0

    def get_key(self) -> str:
        """다음 API 키 반환 (라운드 로빈)"""
        if not self._api_keys:
            raise ValueError("GEMINI_API_KEY 없음. .env 파일을 확인하세요.")
        with self._lock:
            key = self._api_keys[self._index % len(self._api_keys)]
            self._index += 1
            return key

    @property
    def key_count(self) -> int:
        return len(self._api_keys)

    @staticmethod
    def _load_keys() -> List[str]:
        """환경변수 또는 .env 파일에서 API 키 로드"""
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key:
            keys = [k.strip() for k in env_key.split(",") if k.strip()]
            if keys:
                return keys

        for path in [".env", "../.env", "../../.env", "../../../.env"]:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        for line in f:
                            if (
                                "GEMINI_API_KEY" in line
                                and "=" in line
                                and not line.startswith("#")
                            ):
                                _, v = line.strip().split("=", 1)
                                keys = [k.strip() for k in v.split(",") if k.strip()]
                                if keys:
                                    return keys
                except Exception:
                    continue
        return []
