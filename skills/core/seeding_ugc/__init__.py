"""
시딩 UGC 워크플로 모듈

UGC(User Generated Content) 스타일 이미지 생성.
핵심 철학: "너무 잘 나오면 실패" - 진짜 폰카처럼 보여야 함.

사용법:
    from core.seeding_ugc import UGCValidator
    from core.seeding_ugc.validator import UGCValidator
"""

from .validator import UGCValidator

__all__ = [
    "UGCValidator",
]
