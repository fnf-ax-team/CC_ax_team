"""
핏 베리에이션 프롬프트 빌더

3x 보존 전략: 색상/소재/로고를 프롬프트에 3번 반복 강조하여
핏만 변경하고 나머지 속성은 100% 보존하도록 유도한다.

구조:
1. [절대 보존] 섹션 — 색상/소재/로고 1차 명시
2. [모델 보존] 섹션 — 인물/포즈/상체 착장 보존 (model_wearing 모드 필수)
3. [핏 변형] 섹션 — 목표 핏 실루엣 상세
4. [디테일 보존] 섹션 — 포켓/허리/밑단/스티칭 + 색상/소재 2차 반복
5. [디스플레이] 섹션 — 촬영 모드
6. [네거티브] 섹션 — 금지 요소 + 색상/소재/모델 변경 3차 금지
"""

from typing import Optional
from .analyzer import PantsAnalysis
from .fit_presets import FitPreset, DisplayMode


def build_fit_variation_prompt(
    analysis: PantsAnalysis,
    target_preset: FitPreset,
    display_mode: DisplayMode,
    extra_instructions: Optional[str] = None,
) -> str:
    """핏 베리에이션 프롬프트 생성

    Args:
        analysis: VLM 바지 분석 결과
        target_preset: 목표 핏 프리셋
        display_mode: 디스플레이 모드 (flatlay/hanger/model_wearing)
        extra_instructions: 추가 지시사항

    Returns:
        str: 생성용 프롬프트
    """
    lines = []

    # 헤더
    lines.append("# Pants Fit Variation")
    lines.append(
        f"Change ONLY the silhouette/fit to [{target_preset.name_en} ({target_preset.name_kr})]. "
        f"Preserve EVERYTHING else from the [REFERENCE] image."
    )
    lines.append("")

    # ============================================================
    # 1차 보존: [절대 보존] — 색상/소재/로고 명시
    # ============================================================
    lines.append("## [절대 보존] *** DO NOT CHANGE ***")

    # 색상
    color_text = analysis.color_primary
    if analysis.color_secondary:
        color_text += f" with {analysis.color_secondary}"
    if analysis.color_wash and analysis.color_wash != "none":
        color_text += f", {analysis.color_wash} wash"
    lines.append(f"- COLOR: {color_text} (EXACT match required)")

    # 소재
    material_text = analysis.material_type
    if analysis.material_texture:
        material_text += f", {analysis.material_texture} texture"
    if analysis.material_weight:
        material_text += f", {analysis.material_weight} weight"
    if analysis.material_finish and analysis.material_finish != "none":
        material_text += f", {analysis.material_finish} finish"
    lines.append(f"- MATERIAL: {material_text} (EXACT match required)")

    # 로고
    for logo in analysis.logos:
        lines.append(
            f"- LOGO: {logo.brand} {logo.type} at {logo.position} (MUST preserve)"
        )

    # 패턴
    if analysis.pattern_type and analysis.pattern_type not in ("solid", "none"):
        lines.append(
            f"- PATTERN: {analysis.pattern_type} — {analysis.pattern_description}"
        )

    lines.append("")

    # ============================================================
    # [모델/인물 보존] — 인물이 있는 경우 필수 잠금
    # ============================================================
    lines.append("## [MODEL/PERSON PRESERVATION — DO NOT CHANGE]")
    lines.append("★★★ This is a PANTS FIT VARIATION, not image generation ★★★")
    lines.append("Think of it as Photoshop: the person is a LOCKED LAYER.")
    lines.append("You are ONLY modifying the pants silhouette/fit.")
    lines.append("")
    lines.append("- Face: EXACT same person, same expression, same skin tone")
    lines.append("- Body: EXACT same proportions, height, build, shoulder width")
    lines.append("- Pose: EXACT same stance, weight distribution, position in frame")
    lines.append("- Upper body outfit: EXACT same top/outer/accessories (if visible)")
    lines.append("- Background: EXACT same environment (if visible)")
    lines.append("- Scale: Person height / Frame height = IDENTICAL to source")
    lines.append("- DO NOT change anything except the pants fit/silhouette")
    lines.append("")

    # ============================================================
    # [핏 변형] — 목표 실루엣
    # ============================================================
    lines.append(f"## [핏 변형] Target: {target_preset.name_en}")
    lines.append(f"- silhouette: {target_preset.silhouette}")
    lines.append(f"- thigh: {target_preset.thigh}")
    lines.append(f"- knee: {target_preset.knee}")
    lines.append(f"- calf: {target_preset.calf}")
    lines.append(f"- hem width: {target_preset.hem_width}")
    lines.append(f"- rise: {target_preset.rise}")
    lines.append(f"- keywords: {', '.join(target_preset.keywords)}")
    lines.append("")

    # ============================================================
    # 2차 보존: [디테일 보존] — 포켓/허리/밑단 + 색상/소재 반복
    # ============================================================
    lines.append("## [디테일 보존] Keep ALL details from reference")

    # 허리
    waist_desc = analysis.waist_type
    if analysis.waist_details:
        waist_desc += f" ({analysis.waist_details})"
    lines.append(f"- waist: {waist_desc}")

    # 포켓
    pocket_parts = []
    if analysis.pockets_front and analysis.pockets_front != "none":
        pocket_parts.append(f"front {analysis.pockets_front}")
    if analysis.pockets_back and analysis.pockets_back != "none":
        pocket_parts.append(f"back {analysis.pockets_back}")
    if analysis.pockets_cargo and analysis.pockets_cargo != "none":
        pocket_parts.append(f"cargo at {analysis.pockets_cargo}")
    if pocket_parts:
        lines.append(f"- pockets: {', '.join(pocket_parts)}")

    # 밑단
    hem_desc = analysis.hem_type
    if analysis.hem_details:
        hem_desc += f" ({analysis.hem_details})"
    lines.append(f"- hem: {hem_desc}")

    # 스티칭
    if analysis.stitching_color != "tonal" or analysis.stitching_type != "single":
        lines.append(
            f"- stitching: {analysis.stitching_color} {analysis.stitching_type}"
        )

    # 특이사항
    for detail in analysis.special_details:
        lines.append(f"- detail: {detail}")

    # 색상/소재 2차 반복
    lines.append(f"- REMINDER — color: {color_text}")
    lines.append(f"- REMINDER — material: {material_text}")
    lines.append("")

    # ============================================================
    # [디스플레이] — 촬영 모드
    # ============================================================
    lines.append(f"## [디스플레이] {display_mode.name_kr}")
    lines.append(f"- {display_mode.prompt_hint}")
    lines.append("")

    # ============================================================
    # 추가 지시사항
    # ============================================================
    if extra_instructions:
        lines.append("## [추가 지시]")
        lines.append(f"- {extra_instructions}")
        lines.append("")

    # ============================================================
    # 3차 보존: [네거티브] — 금지 요소 + 색상 변경 금지
    # ============================================================
    lines.append("## [네거티브]")

    # 핏 프리셋의 네거티브
    neg_items = list(target_preset.negative)

    # 색상/소재 변경 금지 (3차)
    neg_items.append("color change")
    neg_items.append("different color")
    neg_items.append("wrong material")
    neg_items.append("missing logos")
    neg_items.append("added logos")
    neg_items.append("different texture")
    neg_items.append("wrong stitching color")
    neg_items.append("material change")
    neg_items.append("different fabric")
    neg_items.append("fabric texture change")

    # 모델/인물 변경 금지 (3차)
    neg_items.append("face change")
    neg_items.append("different person")
    neg_items.append("body proportion change")
    neg_items.append("pose change")
    neg_items.append("upper body outfit change")

    lines.append(", ".join(neg_items))
    lines.append("")

    # ============================================================
    # [이미지 역할]
    # ============================================================
    lines.append("## [IMAGE REFERENCE ROLES]")
    lines.append(
        "[REFERENCE]: 이 바지의 색상/소재/패턴/로고/디테일을 100% 보존. "
        "실루엣(핏)만 변경."
    )

    return "\n".join(lines)
