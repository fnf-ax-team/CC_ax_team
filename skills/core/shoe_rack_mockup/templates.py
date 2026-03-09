# -*- coding: utf-8 -*-
"""
Prompt Templates - 스테이지별 프롬프트 템플릿
=============================================
Gemini 인페인팅에 사용할 프롬프트 정의

v1.3 (2026-02-24):
- **신발 크기 제어 강화**
  - "원본 실루엣 크기와 동일하게" 지시 추가
  - 컴팩트한 매장 디스플레이 크기 강조
  - 오버사이즈 청키 스니커즈 생성 방지
- **신발 다양성 강화**
  - 각 행별 다른 디자인 필수 명시
  - 참조 신발 색상/스타일 복사 강조
  - 중복 검증 체크리스트 추가

v1.2 (2026-02-24):
- COLOR_REMOVAL_SECTION 추가 (코랄 마스크 잔여 문제 해결)
- 신발 방향 반전 지원 (right-toe-forward)

v0.7 (2026-02-20):
- **원근감 배치(Depth Perspective) 도입**
  - 모든 스테이지에 원근감 있는 2켤레 배치 적용
  - "side by side" → "depth perspective (front overlapping back)"
  - 원본 실루엣과 동일한 배치 패턴 명시

v0.6 (2026-02-20):
- Stage 2, 3 프롬프트 최적화 완료
  - 모든 스테이지 2켤레(PAIR) 통일
  - 이전 스테이지 결과물 보존 명시
  - 크기 기준 + 경계 오버플로우 방지

v0.5 (2026-02-20):
- Stage 1 프롬프트 최적화 (V4)
  - 크기 기준: 코랄/흰색 실루엣과 동일 크기
  - 2켤레(PAIR) 강조: "2 shoes side by side"
  - 경계 오버플로우 방지: "must NOT overflow"

v0.4 (2026-02-20):
- Stage 1 프롬프트 대폭 강화
  - 색상 영역 명시 (LEFT=민트, CENTER=코랄, RIGHT=흰색)
  - 보존 영역 강조 (ABSOLUTE PRESERVATION RULES)
  - 신발 정확도 강조 (EXACT COPY, 로고/색상/스타일 복제)
"""

from typing import Dict, List
from .slot_config import SlotColor, get_slot_color


# Stage 1: 민트/청록색 영역 - 신발 2켤레(PAIR)씩 원근감 배치
STAGE1_MINT_PROMPT = """[SHOE RACK - MINT TO REALISTIC SHOES]

This shoe rack has 3 COLUMNS of shoe silhouettes:
- LEFT: MINT/CYAN colored (6 rows)
- CENTER: CORAL/PINK colored (6 rows)
- RIGHT: WHITE colored (6 rows)

ALL THREE COLUMNS have the SAME shoe size.
Look at CORAL and WHITE silhouettes - that is the CORRECT SIZE and ARRANGEMENT.

★★★ YOUR TASK ★★★
Replace ONLY the MINT colored areas with realistic sneakers.

★★★ CRITICAL: DEPTH PERSPECTIVE ARRANGEMENT ★★★
Each slot has 2 SHOES (a PAIR) arranged with DEPTH PERSPECTIVE:
- BACK SHOE: Mostly hidden behind the front shoe
- FRONT SHOE: Overlapping the back shoe, toe slightly covering back shoe's toe
- This creates a realistic 3D depth effect, NOT side-by-side flat arrangement

Look at the coral/white silhouettes - they show this exact arrangement!
The front shoe partially overlaps and hides the back shoe.

★★★ CRITICAL SIZE RULE ★★★
The mint shoes must be the SAME SIZE as coral/white silhouettes.
DO NOT make mint shoes LARGER than coral/white shoes.
Shoes must NOT overflow outside the mint boundary.

★★★ EACH SLOT = 2 SHOES (PAIR) WITH DEPTH ★★★
Row 1: 2 shoes with depth perspective (Reference Shoe 1 design)
Row 2: 2 shoes with depth perspective (Reference Shoe 2 design)
Row 3: 2 shoes with depth perspective (Reference Shoe 3 design)
Row 4: 2 shoes with depth perspective (Reference Shoe 4 design)
Row 5: 2 shoes with depth perspective (Reference Shoe 5 design)
Row 6: 2 shoes with depth perspective (Reference Shoe 6 design)

★★★ DESIGN COPY ★★★
Copy EXACT design from each reference shoe:
- Color (white, black, gray)
- Logo (MLB NY logo)
- Material texture
- Details (stitching, patterns)

★★★ PRESERVATION ★★★
- CORAL areas: Keep as flat pink. NO changes.
- WHITE areas: Keep exactly as white shapes. NO changes.
- Shelves, mesh, wall: Keep identical.

RESULT: 6 rows of realistic shoe PAIRS with depth perspective in mint slots.
Same size and arrangement as coral/white silhouettes. Zero mint color remaining."""


# Stage 2: 코랄/분홍색 영역 - 신발 2켤레(PAIR)씩 원근감 배치
STAGE2_CORAL_PROMPT = """[SHOE RACK - CORAL TO REALISTIC SHOES]

This shoe rack now has:
- LEFT: Realistic sneakers (already replaced, DO NOT TOUCH)
- CENTER: CORAL/PINK colored placeholders (6 rows) ← CHANGE THIS ONLY
- RIGHT: WHITE colored silhouettes (DO NOT TOUCH)

★★★ YOUR TASK ★★★
Replace ONLY the CORAL/PINK colored areas with realistic sneakers.

★★★ CRITICAL: DEPTH PERSPECTIVE ARRANGEMENT ★★★
Each slot has 2 SHOES (a PAIR) arranged with DEPTH PERSPECTIVE:
- BACK SHOE: Mostly hidden behind the front shoe
- FRONT SHOE: Overlapping the back shoe, toe slightly covering back shoe's toe
- This creates a realistic 3D depth effect, NOT side-by-side flat arrangement

Look at the LEFT column shoes - match their depth perspective arrangement!

★★★ CRITICAL SIZE RULE ★★★
Look at the LEFT column shoes - coral shoes should be SAME SIZE.
Shoes must NOT overflow outside the coral boundary.

★★★ EACH SLOT = 2 SHOES (PAIR) WITH DEPTH ★★★
Row 1: 2 shoes with depth perspective (Reference Shoe 7 design)
Row 2: 2 shoes with depth perspective (Reference Shoe 8 design)
Row 3: 2 shoes with depth perspective (Reference Shoe 9 design)
Row 4: 2 shoes with depth perspective (Reference Shoe 10 design)
Row 5: 2 shoes with depth perspective (Reference Shoe 11 design)
Row 6: 2 shoes with depth perspective (Reference Shoe 12 design)

★★★ DESIGN COPY ★★★
Copy EXACT design from each reference shoe:
- Color (white, black, gray)
- Logo (MLB NY logo)
- Material texture
- Details (stitching, patterns)

★★★ PRESERVATION (CRITICAL) ★★★
- LEFT column shoes: Already replaced. Keep EXACTLY as they are.
- WHITE areas on right: Keep exactly as white shapes. NO changes.
- Shelves, mesh, wall: Keep identical.

RESULT: 6 rows of realistic shoe PAIRS with depth perspective in coral slots.
Zero coral color remaining. Left column shoes unchanged."""


# Stage 3: 흰색 영역 - 신발 2켤레(PAIR)씩 원근감 배치
STAGE3_WHITE_PROMPT = """[SHOE RACK - WHITE TO REALISTIC SHOES]

This shoe rack now has:
- LEFT: Realistic sneakers (already replaced, DO NOT TOUCH)
- CENTER: Realistic sneakers (already replaced, DO NOT TOUCH)
- RIGHT: WHITE colored placeholders (6 rows) ← CHANGE THIS ONLY

★★★ YOUR TASK ★★★
Replace ONLY the WHITE colored areas on the RIGHT column with realistic sneakers.

★★★ CRITICAL: DEPTH PERSPECTIVE ARRANGEMENT ★★★
Each slot has 2 SHOES (a PAIR) arranged with DEPTH PERSPECTIVE:
- BACK SHOE: Mostly hidden behind the front shoe
- FRONT SHOE: Overlapping the back shoe, toe slightly covering back shoe's toe
- This creates a realistic 3D depth effect, NOT side-by-side flat arrangement

Look at the LEFT and CENTER column shoes - match their depth perspective arrangement!

★★★ CRITICAL SIZE RULE ★★★
Look at the LEFT and CENTER column shoes - white shoes should be SAME SIZE.
Shoes must NOT overflow outside the white boundary.

★★★ EACH SLOT = 2 SHOES (PAIR) WITH DEPTH ★★★
Row 1: 2 shoes with depth perspective (Reference Shoe 13 design)
Row 2: 2 shoes with depth perspective (Reference Shoe 14 design)
Row 3: 2 shoes with depth perspective (Reference Shoe 15 design)
Row 4: 2 shoes with depth perspective (Reference Shoe 16 design)
Row 5: 2 shoes with depth perspective (Reference Shoe 17 design)
Row 6: 2 shoes with depth perspective (Reference Shoe 18 design)

★★★ DESIGN COPY ★★★
Copy EXACT design from each reference shoe:
- Color (white, black, gray)
- Logo (MLB NY logo)
- Material texture
- Details (stitching, patterns)

★★★ PRESERVATION (CRITICAL) ★★★
- LEFT column shoes: Already replaced. Keep EXACTLY as they are.
- CENTER column shoes: Already replaced. Keep EXACTLY as they are.
- Shelves, mesh, wall: Keep identical.

RESULT: 6 rows of realistic shoe PAIRS with depth perspective in white slots.
Zero white placeholder remaining. Left and Center column shoes unchanged."""


# 템플릿 매핑
STAGE_PROMPTS: Dict[int, str] = {
    1: STAGE1_MINT_PROMPT,
    2: STAGE2_CORAL_PROMPT,
    3: STAGE3_WHITE_PROMPT,
}


def get_stage_prompt(stage: int) -> str:
    """스테이지별 프롬프트 반환"""
    if stage not in STAGE_PROMPTS:
        raise ValueError(f"Unknown stage: {stage}. Available: 1, 2, 3")
    return STAGE_PROMPTS[stage]


def get_prompt_with_context(
    stage: int,
    previous_stages_done: List[int] = None,
    custom_instructions: str = "",
) -> str:
    """이전 스테이지 완료 상태를 고려한 프롬프트 생성"""
    base_prompt = get_stage_prompt(stage)

    # 이전 스테이지 완료 정보 추가
    if previous_stages_done:
        context = "\n\nPREVIOUS STAGES COMPLETED:\n"
        stage_info = {
            1: "- Stage 1 (MINT): Now contains realistic sneakers (2 per slot, shoes 1-6)",
            2: "- Stage 2 (CORAL): Now contains realistic sneakers (2 per slot, shoes 7-12)",
            3: "- Stage 3 (WHITE): Now contains realistic sneakers (2 per slot, shoes 13-18)",
        }
        for prev_stage in previous_stages_done:
            if prev_stage in stage_info:
                context += stage_info[prev_stage] + "\n"
        base_prompt = context + "\n" + base_prompt

    # 커스텀 지시 추가
    if custom_instructions:
        base_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    return base_prompt


def get_verification_prompt(stage: int) -> str:
    """검증용 프롬프트 반환"""
    color_info = {
        1: ("mint/cyan", "2 shoes per slot (pair)", "shoes 1-6"),
        2: ("coral/pink", "2 shoes per slot (pair)", "shoes 7-12"),
        3: ("white", "2 shoes per slot (pair)", "shoes 13-18"),
    }

    if stage not in color_info:
        raise ValueError(f"Unknown stage: {stage}")

    color, count, shoe_range = color_info[stage]

    return f"""Analyze this shoe rack image and verify Stage {stage} completion.

CHECK THE {color.upper()} AREAS:
1. Is there any {color} color remaining? (Should be 0% remaining)
2. Are there {count} in each area?
3. Do the shoes match reference {shoe_range}?
4. Do the shoes fit naturally on the shelf?

SCORING:
- slot_coverage: 0-100 (100 = all {color} replaced)
- shoe_count_accuracy: 0-100 (100 = correct number per slot)
- realism: 0-100 (100 = photorealistic)
- background_preservation: 0-100 (100 = shelves/mesh unchanged)

Return JSON format:
{{
  "stage": {stage},
  "color_remaining_percent": <0-100>,
  "scores": {{
    "slot_coverage": <0-100>,
    "shoe_count_accuracy": <0-100>,
    "realism": <0-100>,
    "background_preservation": <0-100>
  }},
  "issues": ["issue1", "issue2"],
  "passed": <true/false>
}}"""


def get_retry_prompt(
    stage: int,
    issues: List[str],
    attempt: int,
) -> str:
    """재시도 프롬프트 생성"""
    base_prompt = get_stage_prompt(stage)

    issue_text = "\n".join(f"- {issue}" for issue in issues)

    retry_instructions = f"""
RETRY ATTEMPT {attempt + 1} - FIXING PREVIOUS ISSUES:
{issue_text}

IMPORTANT CORRECTIONS:
"""

    # 이슈별 대응
    for issue in issues:
        issue_lower = issue.lower()
        if "color" in issue_lower or "remaining" in issue_lower:
            retry_instructions += "- COMPLETELY replace ALL colored pixels. Zero original color remaining.\n"
        if "count" in issue_lower or "number" in issue_lower:
            retry_instructions += "- Ensure EXACT shoe count per slot as specified.\n"
        if "background" in issue_lower or "shelf" in issue_lower:
            retry_instructions += "- DO NOT modify shelves, mesh, or walls AT ALL.\n"
        if "realistic" in issue_lower or "artificial" in issue_lower:
            retry_instructions += (
                "- Make shoes look PHOTOREALISTIC with proper shadows and lighting.\n"
            )

    return base_prompt + retry_instructions


# =============================================================================
# 동적 프롬프트 생성 (v1.0) - 실루엣 분석 결과 기반
# =============================================================================

# =============================================================================
# v2.0 단일 패스 프롬프트 (모든 색상 한 번에 처리)
# =============================================================================


def build_single_pass_prompt(
    arrangement: str,
    arrangement_description: str,
    shoes_per_slot: int,
    direction: str,
    colors_present: list = None,
    num_columns: int = 3,
    column_layout: list = None,
    has_mirror: bool = False,
    mirror_side: str = "left",
    view_type: str = "side",  # "front" or "side"
    slot_shoe_mapping: list = None,  # v3.1: 슬롯별 신발 매핑
    num_rows: int = 6,  # v3.1: 행 개수
) -> str:
    """
    모든 색상 실루엣을 한 번에 교체하는 단일 패스 프롬프트

    v2.3: 거울 영역 지원
    - has_mirror=True면 한쪽은 거울 반사 영역으로 처리
    - 실제 신발장 영역만 신발 교체
    - 거울 영역은 반사상으로 표현

    v2.2: 신발 쌍 로직 수정
    - 각 슬롯 = 2쌍 (4개 신발)
    - 쌍 A (2개 동일) ≠ 쌍 B (2개 동일)
    - 각 행마다 다른 신발 조합

    v2.1: 동적 색상 열 지원
    - VLM 분석 결과에서 실제 색상 열 정보 사용
    - 2열/3열 자동 대응
    """

    # 방향 텍스트
    direction_text = direction.replace("-", " ").replace("_", " ")

    # 기본값 설정
    if colors_present is None:
        colors_present = ["mint", "coral", "white"]

    # 색상별 레이블 매핑
    color_labels = {"mint": "MINT/CYAN", "coral": "CORAL/PINK", "white": "WHITE"}

    # 거울 모드일 때 - 거울 영역 제외
    if has_mirror:
        # 거울이 아닌 쪽의 색상만 추출
        if mirror_side == "left" and len(colors_present) >= 2:
            # 왼쪽이 거울 → 오른쪽 색상만 사용
            actual_colors = [colors_present[-1]]  # 마지막 색상 (오른쪽)
            mirror_color = colors_present[0]  # 첫 번째 색상 (왼쪽 거울)
        elif mirror_side == "right" and len(colors_present) >= 2:
            # 오른쪽이 거울 → 왼쪽 색상만 사용
            actual_colors = [colors_present[0]]  # 첫 번째 색상 (왼쪽)
            mirror_color = colors_present[-1]  # 마지막 색상 (오른쪽 거울)
        else:
            actual_colors = colors_present
            mirror_color = None
    else:
        actual_colors = colors_present
        mirror_color = None

    # 동적 열 설명 생성
    if column_layout:
        column_desc = "\n".join(
            [
                f"- {col['position'].upper()} column (6 slots): {color_labels.get(col['color'], col['color'].upper())} colored shapes"
                for col in column_layout
            ]
        )
    else:
        # column_layout이 없으면 colors_present 기반으로 생성
        positions = ["LEFT", "CENTER", "RIGHT"][: len(colors_present)]
        column_desc = "\n".join(
            [
                f"- {pos} column (6 slots): {color_labels.get(color, color.upper())} colored shapes"
                for pos, color in zip(positions, colors_present)
            ]
        )

    # 동적 교체 규칙 생성
    replacement_rules = "\n".join(
        [
            f"- {color_labels.get(color, color.upper())} silhouettes → realistic shoes"
            for color in colors_present
        ]
    )

    # 동적 결과 규칙 (미리 생성)
    result_rules = "\n".join(
        [
            f"- ALL {color_labels.get(color, color.upper())} areas → realistic shoes"
            for color in colors_present
        ]
    )

    # 동적 열 개수 텍스트
    columns_text = f"all {num_columns} columns" if num_columns > 1 else "the column"

    # 거울 모드 프롬프트 분기
    if has_mirror and mirror_color:
        return _build_mirror_prompt(
            direction_text=direction_text,
            mirror_side=mirror_side,
            mirror_color=mirror_color,
            actual_colors=actual_colors,
            color_labels=color_labels,
            arrangement=arrangement,
            arrangement_description=arrangement_description,
        )

    # 정면 뷰 프롬프트 분기 (3~7번 이미지)
    if view_type == "front":
        return _build_front_view_prompt(
            direction_text=direction_text,
            colors_present=colors_present,
            num_columns=num_columns,
            color_labels=color_labels,
            column_layout=column_layout,
        )

    # v3.1: 측면 뷰 간소화 프롬프트 사용 (슬롯별 매핑 포함)
    if view_type == "side":
        total_slots = num_columns * num_rows
        return _build_side_view_simple_prompt(
            colors_present=colors_present,
            num_columns=num_columns,
            direction=direction,
            total_slots=total_slots,
            color_labels=color_labels,
            slot_shoe_mapping=slot_shoe_mapping,
            num_rows=num_rows,
        )

    # v1.5: 프롬프트 대폭 간소화 - 핵심 지시만 포함
    # 이전 버전의 긴 프롬프트는 Gemini가 무시하는 부분이 많았음
    prompt = f"""[REPLACE COLORED SHAPES WITH SHOES]

TASK: Replace colored silhouettes with realistic MLB sneakers.

LAYOUT:
{column_desc}

RULES:
1. REPLACE ALL colored shapes with shoes (NO colored pixels remaining!)
2. SHOES SAME SIZE as the colored silhouettes (NOT bigger!)
3. Each colored shape = 1 pair (2 shoes with depth overlap)
4. COPY EXACT design from reference images (color, logo, style)
5. Keep background UNCHANGED (shelves, mesh, walls)

DIRECTION BY COLOR:
- MINT (left column): Toes point LEFT ←
- CORAL (center): Toes point RIGHT →
- WHITE (right column): Toes point RIGHT →

The reference images are already adjusted for direction. Just copy them.

SHOE ASSIGNMENT:
Row 1 = Reference 1, Row 2 = Reference 2, etc.
Each row uses a DIFFERENT reference shoe.

CRITICAL - WILL FAIL IF:
- Any colored pixels remain (must be 100% replaced)
- Shoes bigger than silhouettes
- Wrong direction (check: MINT=left, CORAL/WHITE=right)
- Background changed
- Generic shoes instead of MLB BigBall style"""

    return prompt


def _build_mirror_prompt(
    direction_text: str,
    mirror_side: str,
    mirror_color: str,
    actual_colors: list,
    color_labels: dict,
    arrangement: str,
    arrangement_description: str,
) -> str:
    """
    거울이 있는 이미지용 프롬프트 생성 (측면 뷰)
    v3.0: 정면 뷰처럼 간소화 - 복잡한 pair 개념 제거
    """
    mirror_label = color_labels.get(mirror_color, mirror_color.upper())
    actual_label = (
        color_labels.get(actual_colors[0], actual_colors[0].upper())
        if actual_colors
        else "WHITE"
    )

    if mirror_side == "left":
        mirror_pos = "LEFT"
        actual_pos = "RIGHT"
    else:
        mirror_pos = "RIGHT"
        actual_pos = "LEFT"

    # v3.0: 간소화된 프롬프트 - 정면 뷰 스타일
    prompt = f"""[REPLACE COLORED SILHOUETTES WITH SHOES - SIDE VIEW]

⚠️ EDIT TASK - Keep background EXACTLY as is! ⚠️

This is a SIDE VIEW of a shoe rack with a mirror on the {mirror_pos} side.

★★★ SIMPLE RULE: REPLACE ALL {actual_label} SILHOUETTES! ★★★

The {actual_pos} side has {actual_label} colored shoe silhouettes.
Replace EACH silhouette with a REALISTIC sneaker.

★★★ CRITICAL: EVERY SLOT = 1 PAIR (2 SHOES) ★★★

Each colored silhouette = 2 shoes with depth overlap:
- FRONT shoe: visible, toes pointing {direction_text}
- BACK shoe: partially hidden behind front shoe

The reference images are ALREADY FLIPPED for correct direction!
Just COPY them exactly as provided.

★★★ 6 ROWS = 6 DIFFERENT SHOE DESIGNS! ★★★

I am providing reference shoes. Each row must use a DIFFERENT reference:
- Row 1: Reference 1 design
- Row 2: Reference 2 design
- Row 3: Reference 3 design
- Row 4: Reference 4 design
- Row 5: Reference 5 design
- Row 6: Reference 6 design

NO TWO ROWS should have the same shoe design!

★★★ COPY REFERENCE EXACTLY! ★★★
- EXACT COLOR (pink, blue, white, black, beige, etc.)
- EXACT LOGO (NY, LA, B)
- EXACT STYLE (MLB BigBall chunky sneaker)

★★★ SIZE RULE - VERY IMPORTANT! ★★★
- Shoes must be SAME SIZE as the colored silhouettes
- Shoes must NOT be bigger than silhouettes
- Shoes must NOT overflow outside silhouette boundary
- Keep shoes COMPACT - these are display models, not oversized

★★★ MIRROR SIDE ({mirror_pos}) ★★★
The {mirror_label} area on {mirror_pos} = MIRROR surface
- Show BLURRED reflection of the shoes from {actual_pos}
- Reflections should be FADED and SOFT
- Do NOT put different shoes on mirror side

★★★ BACKGROUND PRESERVATION ★★★
- Metal shelves: NO change
- Mesh/grid: NO change
- Walls: NO change
- Mirror frame: NO change

★★★ RESULT ★★★
- {actual_pos} side: 6 pairs of shoes (all DIFFERENT designs)
- {mirror_pos} side: Blurred reflections
- ZERO {actual_label} color remaining
- Background 100% preserved"""

    return prompt


def _build_side_view_simple_prompt(
    colors_present: list,
    num_columns: int,
    direction: str,
    total_slots: int,
    color_labels: dict = None,
    slot_shoe_mapping: list = None,
    num_rows: int = 6,
) -> str:
    """
    측면 뷰 간소화 프롬프트 (v3.1)
    정면 뷰처럼 단순하게: N개 슬롯 = N개 다른 신발
    v3.1: 슬롯별 신발 매핑 명시 (중복 방지)

    Args:
        colors_present: 존재하는 색상 목록 ["coral", "mint", "white"]
        num_columns: 열 개수
        direction: 신발 방향
        total_slots: 전체 슬롯 수
        color_labels: 색상 레이블 매핑
        slot_shoe_mapping: 슬롯별 신발 매핑 리스트 [{"slot": 1, "row": 1, "col": 1, "ref": 1}, ...]
        num_rows: 행 개수 (기본 6)
    """
    if color_labels is None:
        color_labels = {"mint": "MINT/CYAN", "coral": "CORAL/PINK", "white": "WHITE"}

    # 색상별 설명 생성
    color_desc = ", ".join([color_labels.get(c, c.upper()) for c in colors_present])

    # v3.1: 슬롯별 신발 매핑 테이블 생성
    if slot_shoe_mapping:
        # 명시적 매핑이 제공된 경우
        mapping_lines = []
        for m in slot_shoe_mapping:
            mapping_lines.append(
                f"SLOT {m['slot']:2d} (Row {m['row']}, Col {m['col']}): Reference Shoe #{m['ref']}"
            )
        mapping_table = "\n".join(mapping_lines)
    else:
        # 기본 매핑 생성 (행 우선 순서)
        mapping_lines = []
        slot_num = 1
        for col in range(1, num_columns + 1):
            for row in range(1, num_rows + 1):
                mapping_lines.append(
                    f"SLOT {slot_num:2d} (Row {row}, Col {col}): Reference Shoe #{slot_num}"
                )
                slot_num += 1
        mapping_table = "\n".join(mapping_lines)

    prompt = f"""[REPLACE COLORED SILHOUETTES WITH SHOES - SIDE VIEW]

⚠️ EDIT TASK - Keep background EXACTLY as is! ⚠️

This shoe rack has {num_columns} columns × {num_rows} rows with colored silhouettes:
{color_desc}

★★★ CRITICAL: {total_slots} SLOTS = {total_slots} UNIQUE SHOES! ★★★

I am providing {total_slots} DIFFERENT reference shoe images.
Each slot MUST use its assigned reference - NO DUPLICATES ALLOWED!

★★★ EXACT SLOT-TO-SHOE ASSIGNMENT (FOLLOW EXACTLY!) ★★★
{mapping_table}

⚠️ THIS IS MANDATORY - DO NOT MIX UP THE ASSIGNMENTS!
⚠️ SLOT 1 gets Reference #1, SLOT 2 gets Reference #2, etc.
⚠️ NO TWO SLOTS should have the same shoe!

★★★ SHOE DIRECTION ★★★
All shoes: toes pointing {direction.replace("-", " ").replace("_", " ")}
The reference images are ALREADY FLIPPED for correct direction!
Just COPY them exactly as provided.

★★★ COPY EACH REFERENCE EXACTLY! ★★★
For each slot, copy the assigned reference shoe:
- EXACT COLOR (pink, blue, white, black, beige, red, green, etc.)
- EXACT LOGO (NY, LA, B - copy the letters!)
- EXACT STYLE (MLB BigBall chunky sneaker)

⚠️ DO NOT generate generic white sneakers!
⚠️ COPY the exact colors from each reference image!
⚠️ Reference #1 color ≠ Reference #2 color ≠ Reference #3 color...

★★★ EACH SLOT = 1 PAIR (2 SHOES) ★★★
- Each colored silhouette = 2 shoes with depth overlap
- Front shoe partially hides back shoe
- BOTH shoes in the pair are the SAME design (from assigned reference)

★★★ SIZE RULE - CRITICAL! ★★★
- Shoes must be SAME SIZE as colored silhouettes
- Shoes must NOT be bigger than silhouettes
- Shoes must NOT overflow outside silhouette boundary

★★★ COMPLETE COLOR REMOVAL ★★★
- ALL {color_desc} pixels must be REPLACED with shoes
- ZERO colored silhouette remaining after edit
- If any colored pixels remain = FAILURE

★★★ BACKGROUND PRESERVATION ★★★
- Metal shelves: NO change
- Mesh/grid pattern: NO change
- Walls: NO change
- Lighting: NO change

★★★ VERIFICATION CHECKLIST ★★★
Before finishing, verify:
[ ] SLOT 1 has Reference #1 shoe (not #2 or #3!)
[ ] SLOT 2 has Reference #2 shoe (not #1 or #3!)
[ ] ... (each slot has its UNIQUE assigned reference)
[ ] NO duplicate shoes anywhere in the image
[ ] ALL {total_slots} slots filled with DIFFERENT shoes

★★★ RESULT ★★★
- {total_slots} shoe pairs (2 shoes each, all DIFFERENT designs)
- Each slot matches its assigned reference number
- ZERO colored silhouettes remaining
- Background 100% preserved"""

    return prompt


def _build_front_view_prompt(
    direction_text: str,
    colors_present: list,
    num_columns: int,
    color_labels: dict,
    column_layout: list = None,
) -> str:
    """
    정면 뷰용 프롬프트 (이미지 3~7번) - v2.0 단순화

    핵심: 이미지 전체에 12개 신발, 전부 다르면 됨!
    - 6행 × 2열 = 12개 슬롯
    - 레퍼런스 6장 → 각각 2번씩 사용 (12개)
    - 복잡한 depth/overlap 설명 제거
    """
    # 열 설명 생성
    if column_layout:
        column_desc = "\n".join(
            [
                f"- {col['position'].upper()} column: {color_labels.get(col['color'], col['color'].upper())} silhouettes"
                for col in column_layout
            ]
        )
    else:
        positions = ["LEFT", "CENTER", "RIGHT"][: len(colors_present)]
        column_desc = "\n".join(
            [
                f"- {pos} column: {color_labels.get(color, color.upper())} silhouettes"
                for pos, color in zip(positions, colors_present)
            ]
        )

    prompt = f"""[EDIT IMAGE - REPLACE COLORED SILHOUETTES WITH SHOES]

⚠️ EDIT TASK - Keep background EXACTLY as is! ⚠️

This rack has {num_columns} columns × 6 rows:
{column_desc}

★★★ SIMPLE RULE: 12 DIFFERENT SHOES! ★★★

This image has 12 shoe slots total (6 rows × 2 columns).
EVERY SINGLE SHOE must look DIFFERENT from every other shoe!

12 shoes = 12 DIFFERENT designs!
NO TWO SHOES should look the same!

★★★ 12 REFERENCE IMAGES = 12 UNIQUE SHOES! ★★★

I'm giving you 12 DIFFERENT reference shoe photos!
Each reference = 1 unique shoe. Use each EXACTLY ONCE!

ROW 1: Reference 1 (left) + Reference 2 (right)
ROW 2: Reference 3 (left) + Reference 4 (right)
ROW 3: Reference 5 (left) + Reference 6 (right)
ROW 4: Reference 7 (left) + Reference 8 (right)
ROW 5: Reference 9 (left) + Reference 10 (right)
ROW 6: Reference 11 (left) + Reference 12 (right)

CRITICAL RULES:
- ALL 12 shoes must be VISUALLY DIFFERENT!
- NO shoe appears twice in this image!
- Each reference used EXACTLY ONCE!

★★★ COPY REFERENCE IMAGES EXACTLY! ★★★

For each reference image, COPY:
- EXACT COLOR (pink, blue, white, black, beige, etc.)
- EXACT LOGO (NY, LA, B - whatever is shown!)
- EXACT STYLE (chunky MLB BigBall sneaker)

⚠️ DO NOT generate generic white sneakers!
⚠️ DO NOT ignore the reference colors!

EXAMPLE:
- If Reference 1 = PINK shoe → that slot = PINK shoe
- If Reference 2 = BLUE shoe → that slot = BLUE shoe
- If Reference 3 = WHITE shoe → that slot = WHITE shoe

★★★ SHOE PLACEMENT ★★★

Each colored silhouette → replace with 1 realistic shoe
- Toes point LEFT ←
- Side profile view (you see the side of the shoe)
- Sits flat on shelf

★★★ ABSOLUTE SIZE RULE - READ CAREFULLY! ★★★

THE SHOES MUST BE TINY! MINIATURE! VERY SMALL!

Look at the colored silhouettes - they are TINY shapes!
Each silhouette is a SMALL blob, NOT a full-size shoe!

CRITICAL MEASUREMENTS:
- Each shoe width = LESS THAN 20% of shelf width
- Each shoe height = LESS THAN 50% of shelf height
- 2 shoes together = LESS THAN 50% of shelf width
- MORE THAN HALF the shelf should be EMPTY SPACE!

SCALE REFERENCE:
- Think "miniature collectible shoes" not "real shoes"
- Think "dollhouse size" not "human size"
- The shelf should look mostly EMPTY with small shoes

FORBIDDEN - INSTANT FAILURE:
- Shoes wider than the colored silhouette = WRONG
- Shoes touching each other = WRONG (need gap!)
- Shoes filling the shelf = WRONG
- Normal-sized shoes = WRONG (must be TINY!)

IMAGINE: These are THUMBNAIL-sized display shoes!
The shelf should be 70% EMPTY SPACE, 30% tiny shoes!

★★★ BACKGROUND PRESERVATION ★★★

- Metal shelves: Keep EXACT same
- Mesh/grid: Keep EXACT same
- Walls: Keep EXACT same
- ONLY change the colored silhouette areas!

★★★ RESULT ★★★

- 12 total shoes (6 rows × 2 columns)
- ALL 12 shoes look DIFFERENT from each other
- Colors match the 6 reference images
- ZERO colored silhouettes remaining
- Background 100% preserved"""

    return prompt


# v1.6 추가 규칙 섹션 (중복 방지 최대 강화)
NO_DUPLICATE_SECTION = """★★★ ZERO DUPLICATE SHOES - EVERY SHOE MUST BE UNIQUE! ★★★
⚠️ THIS IS THE #1 PRIORITY RULE! ⚠️

MANDATORY: Count the reference shoe images (#{start} to #{start_plus_5}).
Each reference image shows a DIFFERENT colored shoe. USE THEM ALL!

STRICT COLOR ASSIGNMENT (NO EXCEPTIONS!):
- Row 1: Reference #{start} color (e.g., WHITE)
- Row 2: Reference #{start_plus_1} color (e.g., BLACK) ← DIFFERENT from Row 1!
- Row 3: Reference #{start_plus_2} color (e.g., GRAY) ← DIFFERENT from Row 1,2!
- Row 4: Reference #{start_plus_3} color (e.g., WHITE with BLACK accents)
- Row 5: Reference #{start_plus_4} color (e.g., BLACK with WHITE sole)
- Row 6: Reference #{start_plus_5} color (e.g., GRAY with colored accents)

⚠️ DUPLICATE CHECK - FAIL CONDITIONS:
✗ Row 1 and Row 2 same color → FAILURE!
✗ Row 3 looks like Row 1 → FAILURE!
✗ More than 2 white shoes total → TOO MANY DUPLICATES!
✗ More than 2 black shoes total → TOO MANY DUPLICATES!
✗ All 6 rows look similar → COMPLETE FAILURE!

COLOR VARIETY TARGET:
- At least 3 DIFFERENT main colors across 6 rows
- Example: 2 white, 2 black, 2 gray = GOOD
- Example: 6 white shoes = BAD (no variety!)

VISUAL DISTINCTION TEST:
If someone looks at your result, can they immediately see:
"Row 1 is white, Row 2 is black, Row 3 is gray..."?
If all rows look the same → YOU FAILED!"""

SIZE_CONTROL_SECTION = """★★★ ABSOLUTE SIZE RULE - SHOES MUST BE TINY! ★★★
⚠️ THIS IS THE #1 FAILURE REASON - READ CAREFULLY! ⚠️

THE SHOES ARE TOO BIG IF:
- Shoe width > 80% of silhouette width → TOO BIG!
- Shoe height > 80% of silhouette height → TOO BIG!
- Shoes touch the silhouette boundary → TOO BIG!
- Shoes look "full size" → TOO BIG!

CORRECT SIZE:
- Each shoe = 70-80% of silhouette size
- VISIBLE GAP between shoe edge and silhouette boundary
- Shoes look COMPACT, like miniature display models
- Think "collectible figurine shoes" not "real wearable shoes"

★★★ PIXEL MEASUREMENT CHECK ★★★
If silhouette is 100 pixels wide:
- Each shoe width = 35-40 pixels MAX (not 50+!)
- Gap between shoes = at least 10 pixels
- Gap to boundary = at least 5 pixels on each side

★★★ SCALE DOWN COMMAND ★★★
IMAGINE: Shrink the reference shoes to 70% of their apparent size!
The shelves should have EMPTY SPACE around the shoes!

FORBIDDEN:
✗ Shoes filling the entire silhouette area
✗ Shoes touching or overlapping silhouette boundary
✗ Oversized chunky appearance
✗ Shoes that look "zoomed in"

★★★ SELF-CHECK ★★★
Look at your output: Is there EMPTY SPACE around shoes?
If NO empty space → WRONG! Make shoes SMALLER!
If shoes touch boundary → WRONG! Make shoes SMALLER!"""

STRAIGHT_PLACEMENT_SECTION = """★★★ STRAIGHT PLACEMENT (NO ANGLED) ★★★
- Shoes must face STRAIGHT forward, parallel to shelf edge
- NO angled, tilted, or artistic diagonal placement
- Shoes sit FLAT on shelf surface
- This is a RETAIL DISPLAY, not artistic arrangement
- Toe direction: {direction}"""

BACKGROUND_PRESERVATION_SECTION = """★★★ ABSOLUTE BACKGROUND PRESERVATION ★★★
- ONLY change the {color} colored silhouette pixels
- Metal shelves: DO NOT CHANGE COLOR (no coral, no mint, no gradients!)
- Mesh/grid: Keep EXACT same pattern and color
- Wall: Keep EXACT same color (no bleeding!)
- ⚠️ ANY change to non-{color} areas = COMPLETE FAILURE"""

# v1.3: 색상 완전 제거 최강화 섹션
COLOR_REMOVAL_SECTION = """★★★ #1 PRIORITY: COMPLETE {color} REMOVAL ★★★
⚠️⚠️⚠️ THIS IS THE MOST IMPORTANT RULE! ⚠️⚠️⚠️

BEFORE ANYTHING ELSE - REMOVE ALL {color}!

{color} silhouettes = DELETE ZONES
- Every {color} pixel MUST become part of a realistic shoe
- {color} is a placeholder - it must 100% DISAPPEAR
- After your edit: ZERO {color} pixels visible ANYWHERE

★★★ PIXEL-BY-PIXEL CHECK ★★★
Scan the image for {color} colored pixels:
- Top row silhouettes: {color} gone?
- Middle row silhouettes: {color} gone?
- Bottom row silhouettes: {color} gone?
ALL must be YES. ANY {color} remaining = COMPLETE FAILURE!

★★★ COMMON MISTAKES TO AVOID ★★★
✗ Shoes placed ON TOP of {color} (wrong - {color} still visible behind!)
✗ {color} outline visible around shoes (wrong - must be completely replaced!)
✗ {color} tint bleeding into shoe color (wrong - clean replacement!)
✗ Some {color} areas unchanged (wrong - ALL {color} must be shoes!)

★★★ CORRECT APPROACH ★★★
✓ {color} area becomes shoe leather/fabric texture
✓ {color} area becomes shoe shadow
✓ {color} area becomes shoe details
✓ ZERO {color} hue remaining in any pixel

FINAL CHECK: Can you find ANY {color} color in your output?
If YES → FAILURE, you must redo with complete removal!"""


def build_dynamic_prompt(
    stage: int,
    arrangement: str,
    arrangement_description: str,
    shoes_per_slot: int,
    direction: str,
    previous_stages_done: list = None,
) -> str:
    """
    실루엣 분석 결과를 기반으로 동적 프롬프트 생성

    v0.9 변경사항:
    - LEFT 열과 RIGHT 열이 **다른 신발**임을 명시
    - 정면 뷰에서 2개가 겹쳐 1개로 보이지만 실제로 다른 디자인
    - 신발 할당: Row 1 LEFT = Shoe 1, Row 1 RIGHT = Shoe 2 방식

    Args:
        stage: 스테이지 번호 (1, 2, 3)
        arrangement: 배치 패턴 ("depth-overlap", "side-by-side", "single")
        arrangement_description: 배치 설명 (VLM 분석 결과)
        shoes_per_slot: 슬롯당 신발 수 (VLM 분석 결과, 정면뷰에서 감지된 수)
        direction: 신발 방향
        previous_stages_done: 이전 완료 스테이지 목록

    Returns:
        str: 동적 생성된 프롬프트
    """
    # 스테이지별 색상 정보
    stage_config = {
        1: {
            "color": "MINT/CYAN",
            "column": "LEFT",
            "shoe_range": "1-6",
            "preserve": [
                "CORAL areas: Keep as flat pink. NO changes.",
                "WHITE areas: Keep exactly as white shapes. NO changes.",
            ],
        },
        2: {
            "color": "CORAL/PINK",
            "column": "CENTER",
            "shoe_range": "7-12",
            "preserve": [
                "LEFT column shoes: Already replaced. Keep EXACTLY as they are.",
                "WHITE areas on right: Keep exactly as white shapes. NO changes.",
            ],
        },
        3: {
            "color": "WHITE",
            "column": "RIGHT",
            "shoe_range": "13-18",
            "preserve": [
                "LEFT column shoes: Already replaced. Keep EXACTLY as they are.",
                "CENTER column shoes: Already replaced. Keep EXACTLY as they are.",
            ],
        },
    }

    if stage not in stage_config:
        raise ValueError(f"Unknown stage: {stage}")

    cfg = stage_config[stage]
    color = cfg["color"]
    column = cfg["column"]
    shoe_start = int(cfg["shoe_range"].split("-")[0])

    # 배치 규칙 섹션 생성 (v0.9: LEFT/RIGHT 열 다른 신발 명시)
    # 정면 뷰에서는 1개로 보이지만 실제로 LEFT 열과 RIGHT 열이 다른 신발
    if arrangement in ("depth-overlap", "single"):
        # "single"로 감지되어도 실제로는 LEFT/RIGHT 열이 다른 신발
        arrangement_section = f"""*** CRITICAL: SHOE ARRANGEMENT (FRONT VIEW) ***
IMPORTANT: This is a FRONT VIEW of the shoe rack.
What looks like 1 silhouette per row is actually 2 DIFFERENT shoes overlapping:
- LEFT COLUMN shoe: Front (closer to viewer)
- RIGHT COLUMN shoe: Back (partially hidden behind left shoe)

{arrangement_description}

*** CRITICAL: LEFT and RIGHT columns = DIFFERENT SHOE DESIGNS ***
Each ROW has TWO shoes from DIFFERENT reference images:
- LEFT column = Reference Shoe A
- RIGHT column = Reference Shoe B (different design!)

Direction: {direction.replace("-", " ").replace("_", " ")}

The front shoe (LEFT column) overlaps and partially hides the back shoe (RIGHT column).
This creates a depth perspective effect in the front view."""
    else:  # side-by-side
        arrangement_section = f"""*** CRITICAL: SHOE ARRANGEMENT (SIDE BY SIDE) ***
Each row has 2 DIFFERENT shoes placed side by side:
{arrangement_description}

*** CRITICAL: LEFT and RIGHT = DIFFERENT SHOE DESIGNS ***
- LEFT shoe = Reference Shoe A
- RIGHT shoe = Reference Shoe B (different design!)

Both shoes fully visible, placed horizontally next to each other.
Direction: {direction.replace("-", " ").replace("_", " ")}"""

    # 슬롯별 신발 할당 (v0.9: LEFT/RIGHT 열에 다른 신발 할당)
    # 예: Stage 1 (shoes 1-6): Row 1 LEFT = Shoe 1, Row 1 RIGHT = Shoe 2, ...
    shoe_assignments_lines = []
    for i in range(6):
        left_shoe = shoe_start + i  # odd indices
        right_shoe = (
            shoe_start + i
        )  # 같은 row에서 다른 참조 이미지 사용하도록 API에서 처리
        shoe_assignments_lines.append(
            f"Row {i+1}: LEFT column = Reference Shoe {shoe_start + i} design, "
            f"RIGHT column = DIFFERENT design (use variety)"
        )
    shoe_assignments = "\n".join(shoe_assignments_lines)

    # 보존 규칙
    preserve_rules = "\n".join([f"- {rule}" for rule in cfg["preserve"]])
    preserve_rules += "\n- Shelves, mesh, wall: Keep identical."

    # 이전 스테이지 컨텍스트
    context = ""
    if previous_stages_done:
        context = "\nPREVIOUS STAGES COMPLETED:\n"
        stage_info = {
            1: f"- Stage 1 (MINT): Now contains realistic sneakers (LEFT + RIGHT different shoes per row)",
            2: f"- Stage 2 (CORAL): Now contains realistic sneakers (LEFT + RIGHT different shoes per row)",
            3: f"- Stage 3 (WHITE): Now contains realistic sneakers (LEFT + RIGHT different shoes per row)",
        }
        for prev_stage in previous_stages_done:
            if prev_stage in stage_info:
                context += stage_info[prev_stage] + "\n"

    # v1.1: 강화된 규칙 섹션 생성 (신발 번호 동적 삽입)
    no_duplicate = NO_DUPLICATE_SECTION.format(
        start=shoe_start,
        start_plus_1=shoe_start + 1,
        start_plus_2=shoe_start + 2,
        start_plus_3=shoe_start + 3,
        start_plus_4=shoe_start + 4,
        start_plus_5=shoe_start + 5,
    )
    size_control = SIZE_CONTROL_SECTION
    straight_placement = STRAIGHT_PLACEMENT_SECTION.format(
        direction=direction.replace("-", " ").replace("_", " ")
    )
    background_preserve = BACKGROUND_PRESERVATION_SECTION.format(color=color)
    # v1.2: 색상 완전 제거 강화 (Image 7 코랄 마스크 잔여 문제)
    color_removal = COLOR_REMOVAL_SECTION.format(color=color)

    # 최종 프롬프트 조립 (v1.2 - 색상 완전 제거 강화)
    prompt = f"""[SHOE RACK - {color} TO REALISTIC SHOES]
{context}
This shoe rack has colored silhouette placeholders.
Target: {column} column - {color} colored areas (6 rows)

*** YOUR TASK ***
Replace ONLY the {color} colored areas with realistic sneakers.
CRITICAL: Each row must have 2 DIFFERENT shoe designs (LEFT column != RIGHT column)!

{color_removal}

{arrangement_section}

{no_duplicate}

{size_control}

{straight_placement}

*** SHOE ASSIGNMENTS (LEFT != RIGHT) ***
{shoe_assignments}

*** CRITICAL: MLB BIGBALL CHUNKY SNEAKER STYLE ONLY! ***
⚠️ COPY THE EXACT SHOE STYLE FROM REFERENCE IMAGES! ⚠️

The reference shoes are "MLB BigBall Chunky" sneakers with these EXACT features:
1. CHUNKY THICK SOLE - Very thick, bulky midsole (3-4cm height)
2. BULKY SILHOUETTE - Round, puffy upper shape (NOT slim or flat!)
3. MLB NY LOGO - Large "NY" interlocking letters on the side
4. PANEL CONSTRUCTION - Multiple leather/mesh panels with visible stitching
5. RETRO ATHLETIC STYLE - 90s dad-shoe aesthetic

CRITICAL STYLE RULES:
✓ CHUNKY, BULKY shape (like the reference images)
✓ THICK platform sole
✓ Large NY logo on side panel
✓ Round, puffy toe box
✗ NO slim/flat sneakers (like Converse, Vans)
✗ NO high-tops (like Jordan 1)
✗ NO low-profile shoes
✗ NO running shoe style

FORBIDDEN BRANDS:
✗ Nike swoosh
✗ Adidas stripes
✗ Converse star
✗ Jordan jumpman
✗ Puma, Reebok, New Balance

COLOR PALETTE (from reference images):
- White with gray accents
- Black with white accents
- Gray/silver tones
Copy the EXACT colors shown in each reference image!

*** DESIGN COPY FROM REFERENCE ***
For each row, copy the corresponding reference shoe EXACTLY:
- CHUNKY BULKY shape (mandatory!)
- Thick sole height
- NY logo size and placement
- Panel layout and stitching
- Color exactly as shown in reference

*** CRITICAL: LEFT vs RIGHT MUST BE DIFFERENT! ***
⚠️ THIS IS MANDATORY - SAME DESIGN ON BOTH SIDES = FAILURE! ⚠️

For EACH ROW, the two shoes MUST be VISUALLY DIFFERENT:
- LEFT shoe: One color/design (e.g., WHITE sneaker)
- RIGHT shoe: DIFFERENT color/design (e.g., BLACK sneaker, or GRAY, or BLUE)

EXAMPLES OF CORRECT:
✓ Row 1: LEFT=white shoe, RIGHT=black shoe
✓ Row 2: LEFT=gray shoe, RIGHT=blue shoe
✓ Row 3: LEFT=black shoe, RIGHT=white shoe

EXAMPLES OF WRONG (FAILURE):
✗ Row 1: LEFT=white shoe, RIGHT=white shoe (SAME COLOR = WRONG!)
✗ Row 2: LEFT=NY white, RIGHT=NY white (IDENTICAL = WRONG!)

SELF-CHECK: Look at each row - can you tell LEFT from RIGHT by COLOR?
If both sides look the same → YOU FAILED, make them different!

{background_preserve}

*** PRESERVATION (CRITICAL) ***
{preserve_rules}

RESULT: 6 rows with 2 DIFFERENT shoes each (LEFT != RIGHT) in {color.lower()} slots.
⚠️ ZERO {color.lower()} color remaining - completely replaced with shoes!
Background 100% preserved."""

    return prompt


# =============================================================================
# v3.0 슬롯별 인페인팅 프롬프트 (정면뷰 전용)
# =============================================================================


def build_slot_inpaint_prompt(
    left_ref_desc: str = "MLB chunky sneaker from Reference 1",
    right_ref_desc: str = "MLB chunky sneaker from Reference 2",
    slot_color: str = "mint",
) -> str:
    """
    단일 슬롯 인페인팅용 프롬프트 (정면뷰에서 2개 신발 나란히)

    "rack", "shelf", "display" 용어를 피해서 depth 패턴 트리거 방지.
    슬롯 단위로 처리하므로 간결한 프롬프트.

    Args:
        left_ref_desc: 왼쪽 신발 설명 (참조 이미지 기반)
        right_ref_desc: 오른쪽 신발 설명 (참조 이미지 기반)
        slot_color: 교체할 색상 ("mint", "coral", "white")

    Returns:
        str: 슬롯 인페인팅용 프롬프트
    """
    color_labels = {
        "mint": "MINT/CYAN",
        "coral": "CORAL/PINK",
        "white": "WHITE",
    }
    color_label = color_labels.get(slot_color, slot_color.upper())

    return f"""[INPAINT: REPLACE {color_label} AREA WITH 2 SNEAKERS]

★★★ CRITICAL: COMPLETE COLOR REMOVAL ★★★
The {color_label} colored area MUST be COMPLETELY REPLACED.
- ZERO {color_label} pixels should remain in the output
- The entire colored region becomes 2 realistic sneakers
- If you see any {color_label} tint in your output, you have FAILED

The {color_label} colored area shows where to place shoes.
Replace it with EXACTLY 2 sneakers in SIDE PROFILE VIEW, placed SIDE BY SIDE.

★★★ SIDE PROFILE VIEW ★★★
Show the LATERAL SIDE of each shoe - as if looking at the shoe from its side.
You should see: the side silhouette, heel on one side, toe on the other.
You should NOT see: the front of the shoe pointing at the camera.

┌───────────────────────────────┐
│   ╭──────╮    ╭──────╮       │
│  ╱        ╲  ╱        ╲      │  ← SIDE PROFILE: heel-to-toe visible
│ ╱──────────╲╱──────────╲     │  ← Toes pointing LEFT
│ ▔▔▔▔▔▔▔▔▔▔▔ ▔▔▔▔▔▔▔▔▔▔▔     │
│   [SHOE A]     [SHOE B]      │  ← 2 shoes SIDE BY SIDE
└───────────────────────────────┘

SHOE A (LEFT POSITION):
{left_ref_desc}
- Show SIDE PROFILE (lateral view of the shoe)
- Copy EXACT color from Reference Image 1
- Copy EXACT logo (NY, LA, or B) from Reference 1

SHOE B (RIGHT POSITION):
{right_ref_desc}
- Show SIDE PROFILE (lateral view of the shoe)
- Copy EXACT color from Reference Image 2
- MUST be DIFFERENT color from Shoe A!

★★★ MANDATORY VIEW ANGLE ★★★
1. SIDE PROFILE VIEW of each shoe (see the side, not front)
2. Toes pointing to the LEFT ←
3. Heel visible on the right side of each shoe
4. You can see the full length from heel to toe
5. This is how shoes are displayed on store shelves

★★★ MANDATORY LAYOUT ★★★
1. EXACTLY 2 shoes only, NOT 4
2. Placed SIDE BY SIDE horizontally
3. Both shoes FULLY visible, NO overlapping
4. Same size as the colored area
5. ZERO {color_label} pixels remaining - COMPLETE REPLACEMENT

★★★ FORBIDDEN ★★★
✗ FRONT VIEW of shoes (toes pointing at camera) - WRONG!
✗ 4 shoes (only 2!)
✗ Depth arrangement (front/back)
✗ One shoe hiding another
✗ Generic white/black shoes
✗ ANY {color_label} color remaining in output - THIS IS A FAILURE

★★★ COPY FROM REFERENCES ★★★
Look at Reference 1 and Reference 2 - they show SIDE PROFILE view!
Copy the exact colors and designs as shown from the side angle.

★★★ FINAL CHECK ★★★
Before outputting, verify:
[ ] Is ALL {color_label} color gone? (must be YES)
[ ] Are there exactly 2 shoes? (must be YES)
[ ] Are shoes in SIDE PROFILE view? (must be YES)

OUTPUT: 2 MLB BigBall sneakers in SIDE PROFILE VIEW, side by side, toes pointing left. NO {color_label} COLOR."""
