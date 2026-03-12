"""
4K 업스케일 모듈

기존 이미지의 내용을 변경하지 않고 해상도만 4K로 향상.
"""

from .generator import upscale_image, upscale_with_validation, upscale_batch
from .validator import UpscaleValidator

__all__ = [
    "upscale_image",
    "upscale_with_validation",
    "upscale_batch",
    "UpscaleValidator",
]
