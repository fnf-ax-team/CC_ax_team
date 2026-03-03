# -*- coding: utf-8 -*-
"""
Silhouette Analyzer - VLM 기반 실루엣 배치 패턴 자동 분석
=========================================================
원본 신발장 이미지의 실루엣을 분석하여 배치 패턴, 방향, 크기 등을 추출

v0.1 (2026-02-20):
- 초기 구현
- VLM 기반 실루엣 배치 분석
- 분석 결과를 프롬프트 빌더에 전달
"""

import sys
from pathlib import Path

# 모듈 실행 시 경로 추가
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class SilhouetteAnalysis:
    """실루엣 분석 결과"""

    # 배치 패턴
    arrangement: str  # "depth-overlap", "side-by-side", "single"

    # 신발 방향
    direction: str  # "left-toe-forward", "right-toe-forward", "front-facing"

    # 슬롯당 신발 수
    shoes_per_slot: int  # 1, 2, or 4

    # 원근감 설명 (프롬프트에 사용)
    arrangement_description: str

    # v2.1: 색상 열 정보
    colors_present: List[str] = None  # ["mint", "white"] or ["mint", "coral", "white"]
    num_columns: int = 3  # 2 or 3
    column_layout: List[Dict[str, str]] = (
        None  # [{"position": "left", "color": "mint"}, ...]
    )

    # v2.2: 쌍 구조 정보
    num_pairs_per_slot: int = 1  # 1 or 2 (슬롯당 몇 쌍인지)
    pairs_are_different: bool = True  # 쌍끼리 다른 디자인인지

    # 원본 VLM 응답
    raw_response: Optional[str] = None


ANALYSIS_PROMPT = """Analyze the shoe silhouettes in this shoe rack image.

*** STEP 1: COLOR DETECTION (CRITICAL!) ***
Look carefully at the COLORED SILHOUETTE areas. What colors do you see?

Possible colors:
- MINT/CYAN (bright turquoise-green color)
- CORAL/PINK (salmon-pink color)
- WHITE (pure white or off-white)

Count HOW MANY color columns exist:
- 2 columns = only 2 colors present (e.g., mint + white)
- 3 columns = all 3 colors present (mint + coral + white)

*** STEP 2: VIEW TYPE (CRITICAL!) ***
Determine the camera angle/view:

A. **FRONT VIEW (정면)**:
   - Shoes are facing the camera head-on
   - You see the FRONT of the shoes (toe box facing you)
   - Back shoes are HIDDEN behind front shoes
   - Silhouette looks like 2 shoes side by side (left + right)
   - VISUAL CUE: Compact silhouette, looks like only 2 shoes per slot

B. **SIDE VIEW (측면)**:
   - Shoes are viewed from the side
   - You see the SIDE PROFILE of the shoes
   - ALL 4 shoes are visible (front pair + back pair with depth)
   - Silhouette shows depth arrangement
   - VISUAL CUE: You can see multiple layers of shoes front-to-back

*** STEP 3: VISIBLE SHOES COUNT ***
Based on view type:
- FRONT VIEW: Only 2 shoes VISIBLE per slot (back pair hidden)
- SIDE VIEW: All 4 shoes VISIBLE per slot (2 pairs with depth)

*** STEP 4: DIRECTION DETECTION ***
- "left-toe-forward": Toes pointing to the LEFT side of image
- "right-toe-forward": Toes pointing to the RIGHT side of image
- "front-facing": Toes pointing toward viewer (camera) - indicates FRONT VIEW

*** STEP 5: SHOE VARIETY RULE ***
- FRONT VIEW: The 2 visible shoes (left + right) must be DIFFERENT designs
- SIDE VIEW: Front pair (2 same) must be DIFFERENT from back pair (2 same)

Return ONLY valid JSON:
{
  "colors_present": ["mint", "white"] or ["mint", "coral", "white"],
  "num_columns": 2 or 3,
  "column_layout": [
    {"position": "left", "color": "mint"},
    {"position": "right", "color": "white"}
  ],
  "view_type": "front" or "side",
  "visible_shoes_per_slot": 2 or 4,
  "total_shoes_per_slot": 4,
  "direction": "left-toe-forward" or "right-toe-forward" or "front-facing",
  "arrangement_description": "detailed description of view and shoe arrangement"
}"""


def analyze_silhouette(
    image: Image.Image,
    client: Optional[genai.Client] = None,
    api_key: Optional[str] = None,
) -> SilhouetteAnalysis:
    """
    원본 신발장 이미지의 실루엣 배치 패턴 분석

    Args:
        image: 신발장 원본 이미지
        client: Gemini 클라이언트 (없으면 생성)
        api_key: API 키 (client 없을 때 사용)

    Returns:
        SilhouetteAnalysis: 분석 결과
    """
    if client is None:
        if api_key is None:
            from core.api import _get_next_api_key as get_next_api_key

            api_key = get_next_api_key()
        client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[ANALYSIS_PROMPT, image],
            config=types.GenerateContentConfig(
                temperature=0.1,  # 분석이므로 낮은 온도
                response_mime_type="application/json",
            ),
        )

        response_text = response.text.strip()

        # JSON 파싱
        try:
            data = json.loads(response_text)
            # list로 파싱된 경우 첫 번째 요소 사용
            if isinstance(data, list):
                data = data[0] if data else {}
        except json.JSONDecodeError:
            # JSON 블록 추출 시도
            import re

            json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse JSON from response: {response_text}")

        return SilhouetteAnalysis(
            arrangement=data.get("arrangement", "depth-overlap"),
            direction=data.get("direction", "left-toe-forward"),
            shoes_per_slot=data.get("shoes_per_slot", 4),  # v2.2: 기본값 4 (2쌍)
            arrangement_description=data.get(
                "arrangement_description", "4 shoes (2 pairs) with depth perspective"
            ),
            # v2.1: 색상 열 정보
            colors_present=data.get("colors_present", ["mint", "coral", "white"]),
            num_columns=data.get("num_columns", 3),
            column_layout=data.get("column_layout", None),
            # v2.2: 쌍 구조 정보
            num_pairs_per_slot=data.get("num_pairs_per_slot", 2),  # 기본값 2쌍
            pairs_are_different=data.get(
                "pairs_are_different", True
            ),  # 쌍끼리 다른 디자인
            raw_response=response_text,
        )

    except Exception as e:
        print(f"[WARNING] Silhouette analysis failed: {e}")
        # 기본값 반환 (depth-overlap이 가장 일반적)
        return SilhouetteAnalysis(
            arrangement="depth-overlap",
            direction="left-toe-forward",
            shoes_per_slot=2,
            arrangement_description="2 shoes with depth perspective - back shoe mostly hidden behind front shoe, front shoe partially overlapping",
            colors_present=["mint", "coral", "white"],
            num_columns=3,
            column_layout=None,
            raw_response=str(e),
        )


def get_arrangement_prompt_section(analysis: SilhouetteAnalysis) -> str:
    """
    분석 결과를 프롬프트 섹션으로 변환

    Args:
        analysis: 실루엣 분석 결과

    Returns:
        str: 프롬프트에 삽입할 배치 규칙 섹션
    """
    if analysis.arrangement == "depth-overlap":
        return f"""*** CRITICAL: SHOE ARRANGEMENT ***
Each slot has {analysis.shoes_per_slot} SHOES arranged with DEPTH PERSPECTIVE:
{analysis.arrangement_description}

- BACK SHOE: Mostly hidden behind the front shoe
- FRONT SHOE: Overlapping the back shoe, toe area covering back shoe
- Direction: {analysis.direction.replace("-", " ").replace("_", " ")}

This creates a realistic 3D depth effect. Do NOT place shoes flat side-by-side."""

    elif analysis.arrangement == "side-by-side":
        return f"""*** CRITICAL: SHOE ARRANGEMENT ***
Each slot has {analysis.shoes_per_slot} SHOES arranged SIDE BY SIDE:
{analysis.arrangement_description}

- Two shoes placed horizontally next to each other
- Both shoes fully visible
- Direction: {analysis.direction.replace("-", " ").replace("_", " ")}

Place shoes flat side-by-side, NOT overlapping."""

    else:  # single
        return f"""*** CRITICAL: SHOE ARRANGEMENT ***
Each slot has {analysis.shoes_per_slot} SHOE (SINGLE):
{analysis.arrangement_description}

- One shoe per slot
- Direction: {analysis.direction.replace("-", " ").replace("_", " ")}"""


# 테스트용
if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")

    # 테스트 이미지
    test_image_path = project_root / "vlm_테스트용" / "매장" / "2.png"

    if test_image_path.exists():
        img = Image.open(test_image_path).convert("RGB")
        print("[ANALYZING] Silhouette arrangement...")

        result = analyze_silhouette(img)

        print("\n[RESULT]")
        print(f"  Arrangement: {result.arrangement}")
        print(f"  Direction: {result.direction}")
        print(f"  Shoes per slot: {result.shoes_per_slot}")
        print(f"  Description: {result.arrangement_description}")
        print("\n[PROMPT SECTION]")
        print(get_arrangement_prompt_section(result))
    else:
        print(f"[ERROR] Test image not found: {test_image_path}")
