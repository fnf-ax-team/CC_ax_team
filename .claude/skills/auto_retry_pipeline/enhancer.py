"""
프롬프트 보강기 - 진단 결과에 따라 프롬프트 동적 보강
"""

from typing import Dict, Any, List
from .config import BASE_PRESERVATION_PROMPT


# 이슈별 보강 템플릿
ENHANCEMENT_TEMPLATES = {
    "POSE_MISMATCH": """
=== CRITICAL: PRESERVE EXACT POSE ===
DO NOT CHANGE THE POSE. DO NOT CHANGE THE POSE. DO NOT CHANGE THE POSE.

CURRENT POSE (MUST KEEP EXACTLY):
{pose_description}

- DO NOT move the arms
- DO NOT change hand positions
- DO NOT alter body angle
- DO NOT modify leg stance
- The pose must be PIXEL-PERFECT identical to the input image
""",

    "FACE_CHANGED": """
=== CRITICAL: PRESERVE EXACT FACE ===
DO NOT CHANGE THE FACE. DO NOT CHANGE THE FACE. DO NOT CHANGE THE FACE.

FACE DETAILS (MUST KEEP EXACTLY):
{face_description}

- Same facial features
- Same expression
- Same mouth state (open/closed)
- Same eye direction
- Same face angle
- DO NOT modify the face in ANY way
""",

    "SCALE_SHRUNK": """
=== CRITICAL: PRESERVE SCALE ===
DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT ZOOM OUT. DO NOT ZOOM OUT. DO NOT ZOOM OUT.

FRAMING (MUST KEEP EXACTLY):
{frame_description}

- The person must be the SAME SIZE as in the input
- DO NOT show more of the body
- DO NOT crop differently
- Maintain IDENTICAL framing
- Frame fill ratio must match input exactly
""",

    "PHYSICS_ERROR": """
=== CRITICAL: PHYSICS CONSTRAINT ===
The background MUST support the model's pose physically.

PHYSICS REQUIREMENT:
{physics_requirement}

- If the model is leaning, provide a surface to lean on
- If the model is sitting, provide a seat
- Shadows must be consistent with the pose and lighting
- The scene must be physically plausible
""",

    "PHYSICS_INCOMPATIBLE": """
=== CRITICAL: POSE REQUIRES PHYSICAL SUPPORT ===
The model's pose is PHYSICALLY INCOMPATIBLE with the current background.
The model appears to be FLOATING or UNSUPPORTED.

PHYSICS REQUIREMENT:
{physics_requirement}

The background MUST include a visible support structure for this pose:
- If sitting: add concrete ledge, steps, bench, low wall, or curb
- If leaning: add wall, pillar, column, or railing
- If crouching: ensure ground surface is clearly visible

The model must NOT appear floating in air.
The support surface must match the muted neutral tone of the background.
""",

    "CLOTHING_CHANGED": """
=== CRITICAL: PRESERVE CLOTHING ===
DO NOT CHANGE CLOTHING. DO NOT CHANGE CLOTHING. DO NOT CHANGE CLOTHING.

CLOTHING DETAILS (MUST KEEP EXACTLY):
{clothing_description}

- Same garments
- Same colors (exact match)
- Same logos and text (preserve perfectly)
- Same patterns and textures
- Same fit and draping
""",

    "PROP_STYLE_MISMATCH": """
=== CRITICAL: PROP STYLE MUST MATCH BACKGROUND ===
The prop/furniture the model is using does NOT match the background style.

DETECTED PROP: {prop_description}
TARGET BACKGROUND STYLE: {background_style}

{prop_replacement_instruction}

RULES:
- The replacement prop must serve the SAME physical function (same height, same support type)
- The model's pose must remain IDENTICAL - only the prop's visual appearance changes
- The prop material, color, and style must blend naturally with the new background
- Maintain the same spatial relationship between model and prop
- The prop must look like it BELONGS in the new background environment
""",

    "LIGHTING_MISMATCH": """
=== CRITICAL: FIX LIGHTING TO ELIMINATE COMPOSITING LOOK ===
The model looks PASTED ONTO the background due to lighting mismatch.

LIGHTING ISSUE DETECTED:
{lighting_description}

MODEL'S ACTUAL LIGHTING (from original photo analysis):
{model_lighting_profile}

REQUIREMENTS:
- Generate the background with lighting that MATCHES the model's existing lighting above
- If model has soft diffused light → background MUST have overcast/soft ambient light
- If model has hard directional light from left → background MUST have matching light source from left
- SHADOW DIRECTION on the ground must match the model's existing shadow direction
- COLOR TEMPERATURE must match: warm model = warm background, cool model = cool background
- The model's SKIN TONE must remain natural - NOT greyed out, NOT desaturated, NOT color-shifted
- PRESERVE the model's natural skin warmth and clothing color vibrancy exactly as input
- The model must look like they were ACTUALLY PHOTOGRAPHED in this location
- DO NOT apply any color grading to the model to "match" the background
""",

    "GROUND_POOR": """
=== CRITICAL: FIX GROUND CONTACT - MODEL APPEARS TO FLOAT ===
The model does not appear naturally grounded in the scene.

GROUND CONTACT ISSUE DETECTED:
{ground_description}

MODEL'S ACTUAL LIGHTING (for shadow direction):
{model_lighting_profile}

REQUIREMENTS:
- The model MUST cast a realistic SHADOW on the ground
- Shadow DIRECTION must match the model's light direction described above
- Shadow SOFTNESS must match the lighting type (hard directional = hard shadow, soft diffused = soft shadow)
- There MUST be a dark CONTACT SHADOW directly under the model's feet/shoes
- Feet must make VISIBLE CONTACT with the ground surface - no gap or floating
- The ground surface TEXTURE must continue naturally under and around the model
- The model should look like they are STANDING IN the space, not placed on top of it
""",

    "EDGE_ARTIFACTS": """
=== CRITICAL: REMOVE COMPOSITING ARTIFACTS AT EDGES ===
The model's outline shows visible signs of compositing.

EDGE ISSUE DETECTED:
{edge_description}

REQUIREMENTS:
- NO halo, glow, or bright/dark fringe around the model's outline
- NO color bleeding between model and background at the boundary
- HAIR must blend naturally with the background - no hard cutout edges
- The transition between model and background must be INVISIBLE
- Edges should look identical to a real photograph taken on location
- Pay special attention to: hair strands, clothing edges, gaps between arms and body
""",

    "PERSPECTIVE_MISMATCH": """
=== CRITICAL: FIX SPATIAL INTEGRATION - MODEL LOOKS LIKE A FLAT CUTOUT ===
The model does not appear to exist within the 3D space of the background.

PERSPECTIVE ISSUE DETECTED:
{perspective_description}

REQUIREMENTS:
- Camera angle must be CONSISTENT between model and background
- The model must appear to EXIST INSIDE the 3D space, not pasted on a flat plane
- DEPTH must feel natural - the model's position in space must make sense
- Vanishing point and horizon line must ALIGN between model and background
- The model's SCALE relative to background architectural elements must be correct
- Apply appropriate ATMOSPHERIC perspective if the background has depth
"""
}


class PromptEnhancer:
    """프롬프트 보강기"""

    def enhance(self, base_prompt: str, diagnosis: Dict[str, Any], background_prompt: str) -> str:
        """진단 결과에 따라 프롬프트 보강"""

        issues = diagnosis.get("issues", [])
        enhancements = []

        for issue in issues:
            if issue in ENHANCEMENT_TEMPLATES:
                template = ENHANCEMENT_TEMPLATES[issue]
                enhancement = self._fill_template(template, issue, diagnosis)
                enhancements.append(enhancement)

        # 보강 프롬프트 조합
        if enhancements:
            enhanced_prompt = "\n".join(enhancements) + "\n\n" + base_prompt
        else:
            enhanced_prompt = base_prompt

        # 배경 프롬프트 추가
        final_prompt = enhanced_prompt + "\n\n" + background_prompt

        return final_prompt

    def build_full_prompt(self, diagnosis: Dict[str, Any], background_prompt: str) -> str:
        """진단 정보로 전체 프롬프트 생성"""

        # 기본 보존 프롬프트에 진단 정보 추가
        enhanced = self.enhance(BASE_PRESERVATION_PROMPT, diagnosis, background_prompt)

        return enhanced

    def build_preemptive_prompt(self, original_analysis: Dict[str, Any], background_prompt: str) -> str:
        """원본 분석 결과로 선제적 프롬프트 생성 (재시도가 아닌 1차 생성에서 복잡한 포즈 감지 시)"""

        prompt = f"""EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.
DO NOT CHANGE THE POSE. KEEP EXACT SAME POSE.

=== CURRENT POSE (PRESERVE EXACTLY) ===
{original_analysis.get('pose_description', 'Keep pose identical to input')}

=== FACE DETAILS (PRESERVE EXACTLY) ===
{original_analysis.get('face_description', 'Keep face identical to input')}

=== CLOTHING DETAILS (PRESERVE EXACTLY) ===
{original_analysis.get('clothing_description', 'Keep clothing identical to input')}

=== FRAMING (PRESERVE EXACTLY) ===
{original_analysis.get('frame_description', 'Keep framing identical to input')}

=== PHYSICS CONSTRAINT ===
{original_analysis.get('physics_requirement', 'Background must be physically plausible for the pose')}

MODEL PRESERVATION (100% IDENTICAL):
- FACE: identical to input
- BODY: identical to input
- CLOTHING: identical to input
- SCALE: identical to input

{background_prompt}

OUTPUT: Professional fashion photography, seamless compositing, no artifacts"""

        return prompt

    def build_prop_style_prompt(self, prop_analysis: Dict[str, Any], background_prompt: str) -> str:
        """소품 스타일 매칭 프롬프트 생성 (Stage 0에서 사전 주입용)"""

        props = prop_analysis.get("props", [])
        if not props:
            return ""

        replaceable_props = [p for p in props if p.get("is_removable", False)]
        if not replaceable_props:
            return ""

        # 스타일 매치 판정 확인
        verdict = prop_analysis.get("style_match_verdict", "neutral")
        if verdict == "match":
            return ""

        # 소품별 교체 지시문 생성
        instructions = []
        for prop in replaceable_props:
            recommended = prop_analysis.get("recommended_replacement", "")
            snippet = prop_analysis.get("replacement_prompt_snippet", "")

            if snippet:
                instructions.append(snippet)
            elif recommended:
                instructions.append(
                    f"Replace the {prop.get('prop_type', 'prop')} with {recommended} "
                    f"that fits the new background style."
                )
            else:
                instructions.append(
                    f"The {prop.get('prop_type', 'prop')} ({prop.get('prop_style', 'unknown style')}) "
                    f"should be replaced with a version that matches the background environment. "
                    f"Constraint: {prop.get('swap_constraints', 'must serve same physical function')}."
                )

        prop_prompt = f"""=== PROP STYLE MATCHING ===
The model is interacting with props that need to match the new background.

PROP REPLACEMENT INSTRUCTIONS:
{chr(10).join(f"- {inst}" for inst in instructions)}

CRITICAL CONSTRAINTS:
- Model's POSE must remain 100% identical
- Only change the prop's VISUAL APPEARANCE (style, material, color)
- The replacement prop must have the SAME physical dimensions and support capability
- The prop must look natural and belong in the new background environment
"""
        return prop_prompt

    def _fill_template(self, template: str, issue: str, diagnosis: Dict[str, Any]) -> str:
        """템플릿 변수 치환"""

        replacements = {
            "pose_description": diagnosis.get("pose_description", "Keep pose identical to input"),
            "face_description": diagnosis.get("face_description", "Keep face identical to input"),
            "frame_description": diagnosis.get("frame_description", "Keep framing identical to input"),
            "physics_requirement": diagnosis.get("physics_requirement", "Background must support the pose"),
            "clothing_description": diagnosis.get("clothing_description", "Keep clothing identical to input"),
            "prop_description": diagnosis.get("prop_description", "furniture/prop near the model"),
            "background_style": diagnosis.get("background_style", "the target background"),
            "prop_replacement_instruction": diagnosis.get("prop_replacement_instruction",
                "Replace the prop with one that matches the background style while maintaining the same physical support for the model's pose."),
            "lighting_description": diagnosis.get("lighting_description", "Ensure lighting direction and color temperature match the background"),
            "ground_description": diagnosis.get("ground_description", "Ensure natural ground contact with realistic shadows"),
            "edge_description": diagnosis.get("edge_description", "Ensure clean edges with no halo or artifacts"),
            "perspective_description": diagnosis.get("perspective_description", "Ensure camera angle and horizon line match the background"),
            "model_lighting_profile": self._build_lighting_profile_text(diagnosis),
        }

        result = template
        for key, value in replacements.items():
            result = result.replace("{" + key + "}", value)

        return result

    def _build_lighting_profile_text(self, diagnosis: Dict[str, Any]) -> str:
        """조명 프로필 텍스트 구성"""
        profile = diagnosis.get("_lighting_profile")
        if not profile or profile.get("error"):
            return "Analyze the model's existing lighting and match the background to it."

        parts = []
        if profile.get("light_direction"):
            parts.append(f"- Light Direction: {profile['light_direction']}")
        if profile.get("light_type"):
            parts.append(f"- Light Type: {profile['light_type']}")
        if profile.get("color_temperature"):
            parts.append(f"- Color Temperature: {profile['color_temperature']}")
        if profile.get("shadow_characteristics"):
            parts.append(f"- Shadows on Model: {profile['shadow_characteristics']}")
        if profile.get("intensity"):
            parts.append(f"- Intensity: {profile['intensity']}")
        if profile.get("background_lighting_recommendation"):
            parts.append(f"- RECOMMENDATION: {profile['background_lighting_recommendation']}")

        return "\n".join(parts) if parts else "Analyze the model's existing lighting and match the background to it."
