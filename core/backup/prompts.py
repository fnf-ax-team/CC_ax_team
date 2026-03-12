"""
공유 프롬프트 - 검증된 이미지 생성 프롬프트 상수 및 빌더
"""


# 기본 모델 보존 프롬프트 (auto_retry_pipeline에서 검증됨)
BASE_PRESERVATION_PROMPT = """EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

MODEL PRESERVATION (100% IDENTICAL):
- FACE: identical to input - same features, expression, hair
- BODY: identical to input - same pose, proportions, position
- CLOTHING: identical to input - same garments, colors, logos, details
- SCALE: identical to input - person height ratio must match exactly
- SKIN TONE: preserve the model's natural skin color - DO NOT desaturate or grey-shift
- CLOTHING COLORS: preserve exact original colors - navy stays navy, brown stays brown

PHOTOREALISTIC INTEGRATION (BACKGROUND MUST MATCH THE MODEL - NOT THE OTHER WAY):
- DO NOT modify the model's lighting, color, or tone in any way
- The BACKGROUND must be generated to match the model's existing lighting condition
  - Analyze the model's light direction, intensity, and color temperature FIRST
  - Then generate a background where the light source matches what's already on the model
  - If model has soft diffused light from the left, background must have the same light source
- SHADOWS: Add a natural ground shadow under the model
  - Shadow direction must be consistent with the light already on the model
  - Shadow softness must match the model's existing lighting (soft light = soft shadow)
- COLOR HARMONY: The background color palette must complement the model's existing tones
  - DO NOT alter the model's skin tone, hair color, or clothing colors
  - Generate background colors that harmonize with the model AS-IS
- DEPTH: Generate the background with correct perspective matching the model's camera angle
- The result must look like a REAL photo taken on-location

COLOR TEMPERATURE POLICY (MANDATORY):
- Use ONLY neutral-cool daylight tones (5600K-6500K)
- NO warm/golden/amber/sunset color cast
- NO yellowing of skin or clothing
- The overall color grade must be clean, crisp daylight

SHADOW CASTING (MANDATORY):
- Cast a natural shadow from the model onto the ground
- Shadow direction must match the light source direction in the scene
- Shadow softness must match scene lighting (hard sun = hard shadow, overcast = soft shadow)
- The model's feet must appear firmly planted on the ground surface, not floating

OUTPUT: Real on-location fashion photography, model completely unchanged from input"""


# 라이팅 허용 프롬프트 - 커머스/룩북용 (스튜디오 조명 → 환경 조명 자연스러운 전환)
LIGHTING_HARMONIZATION_PROMPT = """EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

MODEL PRESERVATION (STRICT - EXCEPT LIGHTING):
- FACE: identical to input - same features, expression, hair
- BODY: identical to input - same pose, proportions, position
- CLOTHING: identical to input - same garments, colors, logos, details, patterns, textures
- SCALE: identical to input - person height ratio must match exactly

LIGHTING HARMONIZATION (ALLOWED - KEY DIFFERENCE):
- You ARE ALLOWED to adjust the model's lighting to match the background environment
- Re-light the model as if they were ACTUALLY STANDING in the new background location
- Match the light direction, intensity, color temperature to the background scene
- Add natural environment reflections on skin and clothing surfaces
- Cast realistic shadows FROM the model that match the scene lighting
- Adjust overall color grading so model and background feel like ONE unified photo
- The model's SKIN TONE must remain natural and healthy - no grey/green/unnatural tints
- CLOTHING COLORS must stay recognizable (navy stays navy, not black; brown stays brown, not grey)
  but natural environmental color cast is acceptable (warm sunlight tint, cool shadow tint)

PHOTOREALISTIC INTEGRATION:
- The model must look like they were ACTUALLY PHOTOGRAPHED in this location
- NO studio-lit flat look against an outdoor background
- Environment light wraps around the model naturally
- Ambient occlusion and bounce light from the ground/walls should be visible
- The overall image should have ONE unified color grade, not two separate ones
- SHADOWS: Natural ground shadow matching the scene's main light source
- DEPTH: Correct perspective matching the model's camera angle

COLOR TEMPERATURE POLICY (MANDATORY):
- Use ONLY neutral-cool daylight tones (5600K-6500K)
- NO warm/golden/amber/sunset color cast - this is company policy
- Natural environment color interaction allowed, but NO overall warm tint
- The overall color grade must be clean, crisp daylight

SHADOW CASTING (MANDATORY):
- Cast a natural shadow from the model onto the ground
- Shadow direction must be consistent with background light source
- Shadow connects seamlessly to model's feet/contact points
- Shadow proves the model is ACTUALLY in this location

OUTPUT: Real on-location fashion photography with unified lighting throughout"""


# 스튜디오 → 야외 전환 프롬프트 (스튜디오 흰배경 소스 감지 시 추가)
STUDIO_TO_OUTDOOR_PROMPT = """
STUDIO-TO-OUTDOOR LIGHTING TRANSITION:
The source was shot on a white studio backdrop. Adjust ONLY the lighting/color cast - NOT the person.

LIGHTING ADJUSTMENTS (subtle, not drastic):
- Apply a gentle warm outdoor color cast (~5600K daylight) over the model
- COLOR TEMPERATURE: neutral-cool daylight (5600K-6200K) ONLY
- NO warm/golden/amber tones - company policy strictly prohibits warm color casts
- Add soft directional shadow consistent with the background's sun position
- Subtle ambient bounce from ground/walls onto the model's lower body
- The white studio floor must be completely replaced with the scene's ground surface

DO NOT CHANGE (even slightly):
- The model's face, features, expression - PIXEL-PERFECT preservation
- The model's body proportions, pose, hand positions
- Clothing details, logos, colors, textures, patterns
- Hair shape and style (only add subtle outdoor light interaction)

PERSPECTIVE & SPATIAL DEPTH (CRITICAL):
- The background MUST match the model's camera angle and focal length EXACTLY
- If the model is shot at eye-level with ~85mm lens, the background must have the same perspective
- The vanishing point of the background street/buildings must align with the model's horizon line
- Background depth of field must match the model's apparent focal length
- Objects in the background must be at correct relative scale to the model
- DO NOT create a wide-angle background for a telephoto-shot model (or vice versa)
"""


# === 스튜디오 리라이팅 전용 프롬프트 (studio-relight 스킬) ===

STUDIO_RELIGHT_PRESERVATION = """EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

MODEL PRESERVATION (STRICT - LIGHTING RE-MAPPING ALLOWED):
- FACE: identical features, expression, face shape, eye shape, nose, lips
  * LIGHTING on face IS ALLOWED TO CHANGE (shadows, highlights, color temperature)
  * But IDENTITY must remain 100% recognizable
- BODY: identical pose, proportions, position in frame
- CLOTHING: identical garments, patterns, logos, textures, design details
  * Natural light/shadow variation on fabric IS ALLOWED
  * But clothing COLORS must remain recognizable (navy stays navy, not black)
- SCALE: identical to input - person height ratio must match exactly
- HAIR: identical style and shape
  * Natural light interaction (backlight, sun highlights) IS ALLOWED

THIS IS A STUDIO-TO-OUTDOOR CONVERSION:
The person was photographed in a controlled studio environment.
Your job is to make them look like they were ACTUALLY PHOTOGRAPHED on location.
The studio lighting artifacts (flat illumination, no directional shadows, no environment interaction)
must be REPLACED with natural outdoor lighting that matches the background scene.

The result must look like a SINGLE photo taken on location, NOT a composite.
A viewer should NOT be able to tell this person was originally in a studio."""


STUDIO_RELIGHT_AGGRESSIVE = """
=== STUDIO-TO-OUTDOOR LIGHTING TRANSFORMATION ===

SOURCE: Studio flat diffused lighting (multi-softbox, ~5200K, no directional shadows)
TARGET: Natural outdoor lighting matching the background scene
COLOR POLICY: NO warm golden tones, NO sunset glow, NO amber cast. Use neutral-cool daylight (5600K-6200K).

STEP 1 - DIRECTIONAL SUNLIGHT:
- Main light source: {sun_direction} o'clock direction, {sun_elevation} elevation
- Sun color temperature: {color_temp} (MUST be neutral-cool, NOT warm/golden)
- Apply directional light to model: sun-facing surfaces brighter, opposite side darker
- Face should show natural light/shadow modeling (NOT the flat studio look)
- Hair should catch sunlight naturally on the sun-facing side
- IMPORTANT: Sunlight must be crisp white-blue daylight, NOT warm amber

STEP 2 - GROUND SHADOW (CRITICAL):
- The model MUST cast a visible shadow on the ground
- Shadow falls OPPOSITE to the {sun_direction} o'clock light source
- Shadow must connect seamlessly to the model's feet/contact points
- The shadow proves the model is ACTUALLY in this location

STEP 3 - ENVIRONMENT INTERACTION:
- Ground bounce: {bounce_color} reflected light on model's lower body and under-chin area
- Building/wall reflection: subtle fill light on the side facing nearby structures
- Sky fill: cool blue ambient light in shadow areas (opposite to sun)

STEP 4 - SKIN & FABRIC RESPONSE:
- Skin on sun-facing side: bright neutral highlight, natural specular on forehead/nose (NO warm/amber cast)
- Skin on shadow side: cooler tone, ambient fill (NOT pure black shadow)
- Fabric: sun-facing surfaces slightly brighter, shadow surfaces slightly darker
- Maintain fabric color identity (navy must still read as navy, no yellowing)

STEP 5 - OVERALL COLOR GRADE:
- Apply ONE unified color grade to entire image (model + background)
- Color grade MUST be neutral-cool (NO warm/golden/amber tint, NO sunset look)
- The overall tone should be crisp, clean daylight - like 2PM bright sun
- The model should look like they belong in this light, not pasted from another photo
- NO yellowing of the image. If anything, lean slightly cool rather than warm

ABSOLUTE PRESERVATION (NO CHANGE EVEN WITH RE-LIGHTING):
- Person's face identity (bone structure, features, expression)
- Body proportions and pose
- Clothing design, logos, patterns, textures
- Hair style and volume (only light interaction changes)
"""


STUDIO_RELIGHT_CONSERVATIVE = """
=== SUBTLE STUDIO-TO-OUTDOOR ADJUSTMENT ===

SOURCE: Studio lighting with some existing directionality
TARGET: Gentle blend into outdoor environment

MINIMAL ADJUSTMENTS:
1. Shift overall color temperature toward {color_temp} (neutral-cool outdoor daylight)
2. Add soft ground shadow matching ambient outdoor light
3. Subtle {bounce_color} bounce from ground on lower body
4. Very slight neutral-cool tint on sun-exposed surfaces (NO warm/golden cast)
5. Match exposure/brightness to background scene levels

PRESERVATION PRIORITY: Maximum. Only add the minimum needed for integration.
"""


def build_studio_relight_prompt(
    background: str,
    strategy: str = "aggressive",
    sun_direction: str = "10",
    sun_elevation: str = "mid",
    color_temp: str = "6000K crisp neutral-cool daylight",
    bounce_color: str = "neutral cool gray",
    vfx_guideline: str = "",
    has_personal_props: bool = False,
    environmental_props: list = None,
) -> str:
    """스튜디오→야외 리라이팅 전용 프롬프트 조립.

    Args:
        background: 원하는 배경 설명
        strategy: "aggressive" 또는 "conservative"
        sun_direction: 태양 방향 (시계 1-12)
        sun_elevation: 태양 높이 (low/mid/high)
        color_temp: 색온도
        bounce_color: 바운스 라이트 색상
        vfx_guideline: VFX 물리 가이드라인
        has_personal_props: 개인 소품 감지 여부
        environmental_props: 환경 소품 목록

    Returns:
        완전한 생성 프롬프트
    """
    parts = [STUDIO_RELIGHT_PRESERVATION]

    # 소품 보존
    if has_personal_props:
        parts.append(ONE_UNIT_PRESERVATION)

    if environmental_props:
        env_list = ", ".join(environmental_props)
        parts.append(f"""
ENVIRONMENTAL PROPS ADAPTATION:
The following furniture/environmental objects may be adapted to match the new background style: {env_list}
Keep their FUNCTION but adapt their APPEARANCE to match the background concept.""")

    # VFX 물리 가이드라인
    if vfx_guideline:
        parts.append(f"\n{vfx_guideline}")

    # 리라이팅 전략 블록
    if strategy == "aggressive":
        relight_block = STUDIO_RELIGHT_AGGRESSIVE.format(
            sun_direction=sun_direction,
            sun_elevation=sun_elevation,
            color_temp=color_temp,
            bounce_color=bounce_color,
        )
    else:
        relight_block = STUDIO_RELIGHT_CONSERVATIVE.format(
            color_temp=color_temp,
            bounce_color=bounce_color,
        )
    parts.append(relight_block)

    # 배경 설명
    bg_section = f"""
BACKGROUND CHANGE:
{background}

- Re-light the model to match this background environment naturally
- Ground surface must continue naturally under the model with appropriate shadow
- The model and background must share ONE unified lighting and color grade
- Make the model look like they were photographed ON LOCATION in this scene
- COLOR TEMPERATURE: neutral-cool daylight (5600K-6200K). NO warm golden cast. NO sunset tones.

NO Korean text. NO Korean signage."""

    parts.append(bg_section)

    return "\n".join(parts)


# 기본 배경 프롬프트
DEFAULT_BACKGROUND_PROMPT = """
BACKGROUND SPECIFICATION:
- Location: Modern industrial space
- Materials: Polished concrete, brushed steel accents
- Colors: Cool gray, metallic silver tones
- Atmosphere: Minimal, clean, architectural
- Lighting: Soft natural light matching original direction
"""


def build_generation_prompt(background: str, preservation_prompt: str = None, lighting_harmonization: bool = False) -> str:
    """배경 설명으로 완전한 생성 프롬프트 구성

    Args:
        background: 원하는 배경 설명 텍스트
        preservation_prompt: 커스텀 보존 프롬프트 (None이면 BASE_PRESERVATION_PROMPT 사용)
        lighting_harmonization: True이면 라이팅 허용 프롬프트 사용

    Returns:
        완전한 생성 프롬프트 문자열
    """
    if preservation_prompt:
        base = preservation_prompt
    elif lighting_harmonization:
        base = LIGHTING_HARMONIZATION_PROMPT
    else:
        base = BASE_PRESERVATION_PROMPT

    if lighting_harmonization:
        bg_section = f"""BACKGROUND CHANGE:
{background}

- Re-light the model to match this background environment naturally
- Ground surface must continue naturally under the model with appropriate shadow
- The model and background must share ONE unified lighting and color grade
- Make the model look like they were photographed ON LOCATION in this scene

NO Korean text. NO Korean signage."""
    else:
        bg_section = f"""BACKGROUND CHANGE:
{background}

- Generate the background to match the model's EXISTING lighting and perspective
- Ground surface must continue naturally under the model with appropriate shadow
- DO NOT change the model - only generate a matching background around them
- The background lighting must match what is already on the model

NO Korean text. NO Korean signage."""

    return base + "\n\n" + bg_section


# ONE UNIT 보존 프롬프트 (인물+차량+오브젝트를 하나의 덩어리로)
ONE_UNIT_PRESERVATION = """
=== FOREGROUND SUBJECT PRESERVATION (CRITICAL) ===
SUBJECT = Person + Vehicle + Objects as ONE CONNECTED UNIT.
Treat them as a SINGLE subject, NOT separate objects.

DO NOT MODIFY THE SUBJECT:
- Person: exact face, body, clothes, pose, hair
- Vehicle (if exists): exact color, model, wheels, reflections, position
- Objects (if exist): exact appearance and position
- Their spatial relationship: distance, angle, contact points
- Combined shadows on ground

ONLY REPLACE: Background environment behind this unit.
"""


# 환경 소품 키워드 (배경 컨셉에 맞게 수정 허용)
ENVIRONMENTAL_PROPS = {
    "chair", "table", "bench", "stool", "sofa", "couch", "desk",
    "shelf", "cabinet", "counter", "railing", "fence", "ladder",
    "의자", "테이블", "벤치", "스툴", "소파", "책상", "선반",
}


# === MLB 리얼리즘 강화 프롬프트 (한국 패션 화보 스타일) ===

MLB_SKIN_MICRODETAIL = """SKIN MICRO-DETAIL PROTOCOL:
- Pore visibility: forehead(high density), nose(visible blackheads), cheeks(scattered)
- Texture layers: epidermis grain, fine peach fuzz, natural oil sheen zones
- Imperfections allowed: minor redness, barely visible fine lines, natural skin variance
- Color undertone: cool-neutral Korean skin tone, not uniform

FORBIDDEN SKIN PATTERNS:
- Airbrushed perfection
- Uniform matte texture
- Porcelain/plastic appearance
- Over-smooth gradients"""


MLB_SHADOW_SYSTEM = """SHADOW MASTERY SYSTEM:
Layer 1 - CONTACT: hairline shadow on forehead, collar shadow on neck,
         fabric fold shadows, all in blue-violet undertone
Layer 2 - FORM: soft gradients defining facial structure,
         nose bridge shadow, under-eye socket definition
Layer 3 - CAST: directional shadows matching 45° key light,
         environmental shadows from props/architecture

All shadows maintain cool undertone (no warm/amber cast)
Shadow intensity: 30-40% (not too harsh, not absent)"""


MLB_FABRIC_TEXTURE = """FABRIC TEXTURE PROTOCOL:
- Material visible at macro level: thread weave pattern, surface nap direction
- Light interaction: specular highlights on synthetic, matte absorption on cotton
- Fold behavior: natural drape weight, crease patterns matching fabric type
- Surface detail: visible stitching, label edges, zipper teeth reflection

FABRIC REALISM MARKERS:
- Nylon/polyester: slight sheen, smooth surface tension
- Denim: indigo depth variation, white thread contrast at seams
- Knit: ribbing visible, slight stretch deformation
- Fleece: surface pile direction, light-catching texture"""


MLB_EYE_EXPRESSION = """EYE AND EXPRESSION PROTOCOL:
- Eye size: LARGE, WIDE OPEN (K-pop idol style)
- Iris detail: visible fiber texture, natural catchlight position (10-2 o'clock)
- Eyelash: natural separation, slight clumping, mascara texture
- Gaze: confident, direct or 15-30° offset, NOT vacant

EXPRESSION TYPES (allowed):
- innocent_chic: soft gaze, slight head tilt, neutral lips
- cool_confidence: direct stare, minimal expression, chin slightly up
- relaxed_cool: half-smile (no teeth), natural blink position
- provocative_chic: intense gaze, pouty lips, arched brow
- thoughtful_cool: looking slightly away, contemplative mood

FORBIDDEN:
- Squinting, half-lidded, sleepy eyes
- Bright smile showing teeth
- Surprised/wide-eyed expression
- Blank vacant stare"""


MLB_NEGATIVE_AI_TELLS = """ABSOLUTE FORBIDDEN (AI TELLS):
plastic smooth skin, porcelain doll appearance, airbrushed perfection,
uniform texture across all skin areas, missing pores,
doll-like eyes, uncanny valley expression, frozen smile,
stiff mannequin pose, T-pose arms, unnatural weight distribution,
flat lighting without shadows, missing contact shadows,
floating subject not grounded to environment,
too-clean background without atmospheric dust or grain,
perfect symmetry in face or body,
over-saturated colors without tonal variation,
missing fabric texture and fold detail,
cartoon skin coloring, anime influence"""


def classify_props(props_list: list) -> tuple:
    """소품을 개인/환경으로 분류.

    Returns:
        (personal_props: list, environmental_props: list)
    """
    personal = []
    environmental = []
    for prop in props_list:
        prop_lower = prop.lower()
        if any(env_kw in prop_lower for env_kw in ENVIRONMENTAL_PROPS):
            environmental.append(prop)
        else:
            personal.append(prop)
    return personal, environmental


def build_enhanced_prompt(
    background: str,
    vfx_guideline: str = "",
    swap_instructions: str = "",
    has_personal_props: bool = False,
    environmental_props: list = None,
    lighting_harmonization: bool = False,
    is_studio_source: bool = False,
) -> str:
    """분석 결과를 통합한 강화 프롬프트 구성.

    Args:
        background: 원하는 배경 설명 텍스트
        vfx_guideline: VFX 분석에서 생성된 물리 가이드라인
        swap_instructions: 배경교체 분석 지시문 (바닥/색보정/차량)
        has_personal_props: 개인 소품 감지 여부 (ONE UNIT 프롬프트 포함 여부)
        environmental_props: 환경 소품 목록 (배경에 맞게 수정 허용)
        lighting_harmonization: True이면 라이팅 허용 프롬프트 사용

    Returns:
        완전한 생성 프롬프트 문자열
    """
    parts = [LIGHTING_HARMONIZATION_PROMPT if lighting_harmonization else BASE_PRESERVATION_PROMPT]

    # Studio-to-outdoor transition block (only when studio source + lighting harmonization)
    if is_studio_source and lighting_harmonization:
        parts.append(STUDIO_TO_OUTDOOR_PROMPT)

    # ONE UNIT 보존 (개인 소품 감지 시)
    if has_personal_props:
        parts.append(ONE_UNIT_PRESERVATION)

    # 환경 소품 적응 (배경 컨셉에 맞게 수정 허용)
    if environmental_props:
        env_list = ", ".join(environmental_props)
        parts.append(f"""
ENVIRONMENTAL PROPS ADAPTATION:
The following furniture/environmental objects may be adapted to match the new background style: {env_list}
Keep their FUNCTION (something to sit on, lean against, etc.) but adapt their APPEARANCE to match the background concept.""")

    # VFX 물리 가이드라인 (카메라, 조명, 포즈 지지대)
    if vfx_guideline:
        parts.append(f"\n{vfx_guideline}")

    # 배경교체 분석 지시문 (바닥 연속성, 색보정)
    if swap_instructions:
        parts.append(f"\n{swap_instructions}")

    # 배경 설명
    if lighting_harmonization:
        bg_section = f"""
BACKGROUND CHANGE:
{background}

- Re-light the model to match this background environment naturally
- Ground surface must continue naturally under the model with appropriate shadow
- The model and background must share ONE unified lighting and color grade
- Make the model look like they were photographed ON LOCATION in this scene

NO Korean text. NO Korean signage."""
    else:
        bg_section = f"""
BACKGROUND CHANGE:
{background}

- Generate the background to match the model's EXISTING lighting and perspective
- Ground surface must continue naturally under the model with appropriate shadow
- DO NOT change the model - only generate a matching background around them
- The background lighting must match what is already on the model

NO Korean text. NO Korean signage."""

    parts.append(bg_section)

    return "\n".join(parts)
