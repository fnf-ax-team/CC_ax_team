"""
착장 분석 래퍼 모듈

원본: core.outfit_analyzer (OutfitAnalyzer, OutfitAnalysis, OutfitItem, LogoInfo)

래핑 범위:
- 데이터클래스 재export (OutfitAnalysis, OutfitItem, LogoInfo)
- analyze_outfit(): api_key와 client 모두 지원하는 통합 인터페이스
- detail_level 옵션: "full" (기본), "basic" (간소화), "commerce" (판매 포인트 추가)
"""

from pathlib import Path
from typing import List, Optional, Union

from google import genai

# 원본 분석기 import
from core.outfit_analyzer import (
    OutfitAnalyzer,
    OutfitAnalysis,
    OutfitItem,
    LogoInfo,
)

# 통합 VLM 유틸리티
from core.modules.vlm_utils import vlm_call


# ============================================================
# 커머스 확장용 프롬프트
# ============================================================

_COMMERCE_PROMPT = """이 착장 이미지에서 커머스(이커머스) 판매를 위한 핵심 셀링 포인트를 분석하세요.

JSON 형식으로 출력:
```json
{
    "key_selling_points": [
        "셀링포인트 1 (예: 유니크한 오버사이즈 실루엣)",
        "셀링포인트 2",
        "셀링포인트 3"
    ],
    "target_audience": "타겟 고객층 설명",
    "styling_tip": "스타일링 팁 한 줄"
}
```

JSON만 출력하세요."""


# ============================================================
# 메인 분석 함수
# ============================================================


def analyze_outfit(
    images: List[Union[str, Path]],
    api_key: Optional[str] = None,
    client=None,
    detail_level: str = "full",
) -> OutfitAnalysis:
    """
    착장 분석 (통합 인터페이스).

    api_key 또는 client 중 하나만 제공하면 된다.
    detail_level에 따라 분석 깊이가 달라진다.

    Args:
        images: 착장 이미지 경로 리스트
        api_key: Gemini API 키 (client가 없을 때 사용)
        client: genai.Client 인스턴스 (있으면 우선 사용)
        detail_level: 분석 상세도
            - "full": 기본 (OutfitAnalyzer.analyze 그대로)
            - "basic": 간소화 (blind_spot/details 생략)
            - "commerce": full + 셀링포인트/타겟고객 추가

    Returns:
        OutfitAnalysis 객체
    """
    # 클라이언트 초기화
    if client is None:
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    # 1) 기본 분석 (OutfitAnalyzer 사용)
    analyzer = OutfitAnalyzer(client)
    analysis = analyzer.analyze(images)

    # 2) detail_level별 후처리
    if detail_level == "basic":
        # 간소화: details(blind_spot) 제거
        for item in analysis.items:
            item.details = []
        return analysis

    if detail_level == "commerce":
        # 커머스 확장: 셀링포인트 추가 VLM 호출
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        commerce_data = vlm_call(
            api_key=api_key,
            prompt=_COMMERCE_PROMPT,
            images=images,
            temperature=0.2,
        )

        # 커머스 데이터를 prompt_section에 추가
        if "key_selling_points" in commerce_data:
            selling_lines = "\n".join(
                f"  - {sp}" for sp in commerce_data["key_selling_points"]
            )
            analysis.prompt_section += f"\n\n[KEY SELLING POINTS]\n{selling_lines}"
            if commerce_data.get("styling_tip"):
                analysis.prompt_section += (
                    f"\n[STYLING TIP] {commerce_data['styling_tip']}"
                )

        return analysis

    # detail_level == "full" (기본): 그대로 반환
    return analysis


__all__ = [
    "OutfitAnalysis",
    "OutfitItem",
    "LogoInfo",
    "analyze_outfit",
]
