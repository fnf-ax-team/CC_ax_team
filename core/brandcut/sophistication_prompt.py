"""
sophistication_prompt.py

A급 이미지 분석에서 추출한 "세련됨" 프롬프트 템플릿.
추상적 키워드가 아닌, 구체적이고 측정 가능한 지시사항.
"""


# ============================================================
# A급 세련됨 프롬프트 블록
# ============================================================

SOPHISTICATION_LIGHTING = """
=== LIGHTING (A-GRADE STANDARD) ===
- Main light: front-center to front-left 30 degrees, elevated 15-20 degrees
- Light quality: soft diffused beauty dish style
- Shadow intensity: 15-35% (NOT flat, subtle shadows under jawline and neck)
- Highlight areas: bridge of nose, cheekbones, forehead
- Catchlight position: 11 o'clock in both eyes
- AVOID: completely flat lighting, harsh direct flash, no shadows
"""

SOPHISTICATION_COLOR = """
=== COLOR GRADING (A-GRADE STANDARD) ===
- Color temperature: 6000-6500K cool daylight (NEVER warm/yellow)
- Saturation: 40-55% (low to medium, NEVER over-saturated)
- Contrast: medium to medium-high
- Black point: deep blacks OR slightly lifted for matte finish
- Skin tone: natural with cool undertones, slight dewy glow on high points
- AVOID: over-saturated colors, warm/golden cast, flat muddy tones
"""

SOPHISTICATION_STYLING = """
=== STYLING (A-GRADE STANDARD) ===
Intentional "undone" styling that looks editorial, not catalog:

JACKET/OUTERWEAR:
- Off one shoulder, draped asymmetrically (preferred)
- OR: unzipped from bottom to show midriff
- OR: sleeves pushed up to forearm
- AVOID: worn perfectly straight and symmetrical

CAP:
- Pulled LOW to just above eyebrows (creates shadow on face)
- Straight or tilted 5 degrees forward
- AVOID: cap sitting high on head

INTENTIONAL IMPERFECTIONS (pick 1-2):
- Fabric bunching at elbow or waist
- Stray hair strands over shoulder
- One sleeve slightly higher than other
- Collar slightly uneven

ACCESSORIES:
- Minimal: thin silver chain necklace OR layered fine chains
- Dark manicured nails visible
- AVOID: over-accessorizing, chunky loud jewelry
"""

SOPHISTICATION_POSE = """
=== POSE (A-GRADE STANDARD) ===
Natural "candid moment" energy, NOT stiff catalog pose:

SHOULDER LINE (CRITICAL):
- One shoulder dropped 5-10cm lower than the other
- OR: one shoulder raised toward head
- Creates asymmetry and movement
- AVOID: perfectly level shoulders

SPINE & WEIGHT:
- Slight S-curve in spine
- Weight shifted to one leg
- Natural lean (against wall/car/etc) if applicable
- AVOID: rigid straight spine, centered weight

HEAD & CHIN:
- Head tilted 5-10 degrees to one side
- Chin slightly down or level (NEVER chin up)
- Creates approachable, confident energy
- AVOID: chin raised high (looks arrogant)

HANDS:
- Relaxed, slightly spread or loosely curled
- Natural positions: on hip, touching cap, in pocket, holding jacket
- AVOID: stiff fingers, awkward hand placement
"""

SOPHISTICATION_EXPRESSION = """
=== EXPRESSION (MLB KARINA STANDARD) ===
Based on actual model photo analysis - "cool girl" look:

EYES (CRITICAL):
- Intensity: PIERCING (not soft, not dreamy)
- Openness: naturally open (not wide, not narrow)
- Squint: micro-squint or none
- Gaze: DIRECT to camera (70%)
- Eye smile: NONE (no crow's feet, no warmth in eyes)

EYEBROWS:
- Position: NEUTRAL (not raised, not furrowed)
- Shape: straight or natural
- AVOID: expressive or arched eyebrows

MOUTH (CRITICAL - 100% of model photos):
- State: BARELY PARTED (lips slightly open, 2-3mm gap)
- Corners: NEUTRAL (not up, not down)
- Lip tension: SOFT and relaxed
- Teeth: NOT visible
- AVOID: closed lips, smile, pout, pressed lips

JAW:
- Tension: SOFT (not clenched, not jutting)
- Chin: neutral position

OVERALL VIBE:
- Cool (60%) or Mysterious (20%) or Confident (20%)
- Calm intensity, effortless poise
- NOT friendly, NOT playful, NOT warm
- "Cool girl who doesn't try too hard"
"""

SOPHISTICATION_AVOID = """
=== MUST AVOID (촌스러운 요소) ===
These elements make images look cheap/catalog/AI-generated:

LIGHTING:
- Flat shadowless lighting (looks like phone selfie)
- Harsh direct flash (looks amateur)

COLOR:
- Over-saturated vibrant colors (looks cheap)
- Warm/golden/yellow cast (looks dated)
- Low contrast muddy tones (looks unprocessed)

POSE:
- Perfectly symmetrical stance (looks robotic/AI)
- Rigid straight spine (looks catalog)
- Chin raised high (looks arrogant)
- Stiff catalog pose (looks fake)

STYLING:
- Clothes worn too perfectly (looks catalog)
- Symmetrical accessories (looks staged)
- Everything matching too well (looks try-hard)

EXPRESSION:
- Forced commercial smile (looks catalog)
- Dead emotionless eyes (looks AI)
- Overly intense aggressive stare (looks snake-like)
- Perfect symmetrical features (looks AI-generated)
"""


def get_full_sophistication_prompt() -> str:
    """전체 세련됨 프롬프트 반환"""
    return "\n".join(
        [
            SOPHISTICATION_LIGHTING,
            SOPHISTICATION_COLOR,
            SOPHISTICATION_STYLING,
            SOPHISTICATION_POSE,
            SOPHISTICATION_EXPRESSION,
            SOPHISTICATION_AVOID,
        ]
    )


def get_sophistication_summary() -> str:
    """핵심 요약 프롬프트 (짧은 버전)"""
    return """
=== EDITORIAL SOPHISTICATION (KEY POINTS) ===

EXPRESSION (MLB KARINA STYLE - CRITICAL):
- Eyes: PIERCING intensity, direct to camera, NO eye smile
- Mouth: BARELY PARTED (2-3mm gap), neutral corners, NO smile
- Eyebrows: NEUTRAL position, straight shape
- Vibe: Cool/mysterious, calm intensity, NOT friendly/warm

ASYMMETRY IS KEY:
- One shoulder dropped lower
- Head tilted 5-10 degrees
- Weight shifted to one leg
- Jacket off one shoulder or draped

LIGHTING & COLOR:
- 6000-6500K cool tone (NOT warm)
- 40-55% saturation (NOT over-saturated)
- Soft diffused light with 15-35% shadows

STYLING IMPERFECTIONS:
- Fabric bunching, stray hair
- Cap pulled low to eyebrows
- Minimal silver jewelry

AVOID:
- Flat lighting, over-saturation
- Symmetrical stiff pose
- Smile or warm expression
- Closed lips (must be barely parted)
- Perfect catalog styling
"""
