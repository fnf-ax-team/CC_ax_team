"""
MCP 서버 헬퍼 유틸리티

- stdout 보호 (stdio 전송 시 core/ 모듈의 print() 오염 방지)
- 이미지 로드/저장 함수
"""

import sys
import json
import shutil
import contextlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

from PIL import Image


# ============================================================
# stdout 보호
# ============================================================


@contextlib.contextmanager
def protect_stdout():
    """
    core 모듈 호출 시 stdout -> stderr 리다이렉트.

    MCP stdio 전송에서는 stdout이 JSON-RPC 메시지 전용이므로,
    core/ 모듈의 print() 호출이 프로토콜을 오염시키지 않도록 보호한다.
    """
    original = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original


# ============================================================
# 이미지 로드
# ============================================================


def load_image(path: str) -> Image.Image:
    """파일 경로에서 PIL Image 로드. 파일 없으면 FileNotFoundError."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(p).convert("RGB")


def load_images(paths: list[str]) -> list[Image.Image]:
    """여러 이미지 경로를 PIL Image 리스트로 로드."""
    images = []
    for path in paths:
        images.append(load_image(path))
    return images


# ============================================================
# 결과 저장 (Fnf_studio_outputs/ 표준 구조)
# ============================================================


def get_output_dir(workflow: str, description: str = "mcp") -> Path:
    """타임스탬프 기반 출력 디렉토리 생성."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("Fnf_studio_outputs") / workflow / f"{timestamp}_{description}"
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_generation_result(
    workflow: str,
    image: Image.Image,
    prompt_json: Optional[dict] = None,
    config: Optional[dict] = None,
    validation: Optional[dict] = None,
    input_images: Optional[dict[str, list[str]]] = None,
    description: str = "mcp",
) -> str:
    """
    생성 결과를 표준 폴더 구조로 저장.

    Returns:
        출력 이미지 경로 (str)
    """
    output_dir = get_output_dir(workflow, description)
    images_dir = output_dir / "images"

    # 인풋 이미지 복사
    if input_images:
        for category, paths in input_images.items():
            for i, img_path in enumerate(paths):
                src = Path(img_path)
                if src.exists():
                    dest = images_dir / f"input_{category}_{i+1:02d}{src.suffix}"
                    shutil.copy(str(src), str(dest))

    # 결과 이미지 저장
    output_path = images_dir / "output_001.jpg"
    image.save(str(output_path), quality=95)

    # prompt.json 저장
    if prompt_json:
        with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
            json.dump(prompt_json, f, ensure_ascii=False, indent=2)

    # config.json 저장
    if config:
        config_data = {
            "workflow": workflow,
            "timestamp": datetime.now().isoformat(),
            **config,
        }
        with open(output_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

    # validation.json 저장
    if validation:
        with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
            json.dump(validation, f, ensure_ascii=False, indent=2)

    return str(output_path)
