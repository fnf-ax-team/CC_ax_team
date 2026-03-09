"""
배경 교체 프롬프트 템플릿 - VLM 분석 및 생성 프롬프트
"""

# ============================================================
# VFX 물리 분석 프롬프트 (6대 영역)
# ============================================================

VFX_ANALYSIS_PROMPT = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한
물리적 제약 조건을 수치화된 데이터로 추출해야 합니다.

## 분석 집중 대상:

### 1. Camera Geometry (카메라 지오메트리)
- 수평선 높이: 이미지 높이 기준 0.0~1.0 정규화 좌표
- 원근감: eye-level | high-angle | low-angle
- 초점 거리 느낌: 35mm | 50mm | 85mm

### 2. Lighting Physics (조명 물리)
- 광원 방향: 시계 방향 1~12시
- 고도: low | mid | high
- 부드러움: 0.0 (hard) ~ 1.0 (soft)
- 색온도: K 값 또는 warm/neutral/cool

### 3. Pose Dependency (포즈 의존성) - CRITICAL
- 포즈 타입: standing | sitting | leaning | crouching | lying
- 지지대 필요 여부:
  - leaning -> 반드시 기댈 수 있는 벽/기둥/난간 필요
  - sitting -> 반드시 앉을 수 있는 의자/벤치/바닥 필요
  - standing -> 지지대 불필요
- 지지대 방향: behind | left | right | below
- 지지대 거리: close(접촉) | near(30cm이내) | far(30cm이상)

### 4. Installation Logic (설치 논리) - CRITICAL
- 소품 감지: 모델이 사용 중인 소품 식별
- 고정형 여부: 고정형 vs 이동형 판별
- 배치 규칙: 상세한 공간 논리
- 금지 컨텍스트: 소품이 자연스럽게 존재할 수 없는 장소

### 5. Physics Anchors (물리적 앵커)
- 접촉점: [x, y] 정규화 좌표
- 그림자 방향: [x, y] 벡터

### 6. Semantic Style (의미적 스타일)
- 분위기: street_editorial | studio | indoor | outdoor
- 추천 위치: ["subway", "lounge", "shop_interior"] 등

## 출력 형식:
JSON 형식으로 정확히 출력하세요."""


# ============================================================
# 소스 타입 감지 프롬프트 (StudioRelight 라우팅용)
# ============================================================

SOURCE_TYPE_PROMPT = """Analyze this image and classify the background type.

Return ONLY one of these exact words:
- "outdoor" - outdoor location (street, park, beach, nature, urban exterior)
- "white_studio" - white/light studio background (cyclorama, seamless white)
- "colored_studio" - colored studio background (gray, black, colored backdrop)
- "indoor" - indoor location (room, cafe, office, interior space)

Return ONLY the classification word, nothing else."""


# ============================================================
# 기본 보존 프롬프트 (프레이밍 고정)
# ============================================================

BASE_PRESERVATION_PROMPT = """EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1
DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

## MATHEMATICAL REQUIREMENTS
- Person height / Frame height = 0.97
- Scale factor = 1.0
- Person center = Frame center (same position)

## MODEL PRESERVATION (ABSOLUTE - NO EXCEPTIONS)

1. PERSON SIZE: 100% IDENTICAL to input. NO shrinking/scaling.
2. PERSON POSITION: Same location in frame as input.
3. PERSON DETAILS: Face, body, clothing, hair, accessories - EXACT COPY."""


# ============================================================
# 구조물 스타일 변환 프롬프트 (위치/원근 고정, 스타일만 변경)
# ============================================================

STRUCTURE_STYLE_TRANSFORM = """
★★★ CRITICAL: STRUCTURE STYLE TRANSFORM (NOT REGENERATION) ★★★

This is NOT background replacement. This is STYLE TRANSFORMATION.

## ABSOLUTE RULE: KEEP ALL STRUCTURE POSITIONS

Every structure in the original image (railings, buildings, walls, floors, stairs, etc.)
MUST remain in the EXACT SAME POSITION, SIZE, and PERSPECTIVE.

What to KEEP (DO NOT CHANGE):
- Structure positions (x, y coordinates)
- Structure sizes and proportions
- Perspective angles and vanishing points
- Depth relationships (what's in front/behind)
- Camera angle and horizon line

What to CHANGE (ONLY THESE):
- Textures and materials (e.g., wooden railing → metal railing)
- Colors and finishes (e.g., brown wood → silver metal)
- Style/aesthetic (e.g., rural → urban modern)
- Lighting color temperature (to match new style)
- Sky/atmosphere (if visible)

## EXAMPLE:
Original: Person leaning on wooden fence, small house behind
Target style: LA downtown

CORRECT:
- Fence stays at SAME position → becomes modern metal railing
- House behind stays at SAME position/size → becomes glass building
- Ground stays at SAME angle → becomes urban concrete

WRONG:
- Moving the fence
- Removing the house and adding distant skyline
- Changing the ground angle/perspective
- Adding new structures that weren't there

## THINK OF IT AS:
"Reskinning" the existing scene, NOT rebuilding it.
Like applying a texture pack to a 3D model - geometry stays, appearance changes.
"""


# ============================================================
# ONE UNIT 보존 프롬프트 (3단계 레벨)
# ============================================================

ONE_UNIT_PROMPTS = {
    "BASIC": """FRAMING: Model fills 90% of the frame height. KEEP THIS.
DO NOT make the model smaller. DO NOT zoom out.

The BLACK CAR (if exists) is a PROP, not background.

COPY EXACTLY FROM INPUT:
- Model size in frame (CRITICAL - must be same %)
- Model face, pose, clothes, hair
- Any vehicle/object near model (color, shape, position)

REPLACE: Background only""",
    "DETAILED": """=== FOREGROUND SUBJECT PRESERVATION (CRITICAL) ===

SUBJECT = Person + Vehicle as ONE CONNECTED UNIT
Treat them as a SINGLE subject, NOT separate objects.

DO NOT MODIFY THE SUBJECT:
- Person: exact face, body, clothes, pose, hair
- Vehicle: exact color, model, wheels, reflections, position
- Their spatial relationship: distance, angle, contact points
- Combined shadows on ground

The person and vehicle are ONE COMPOSITION.
Moving, resizing, or modifying either one breaks the composition.

ONLY REPLACE: Background environment behind this unit""",
    "FULL": """=== FOREGROUND SUBJECT = ONE UNIT (DO NOT SEPARATE) ===

Everything in foreground (person + vehicle + objects) = SINGLE SUBJECT
This is NOT "person" + "car". This is ONE connected unit.

ABSOLUTE PRESERVATION:
- Person: 100% identical (face, body, clothing, pose, expression)
- Vehicle (if exists): 100% identical (color, shape, wheels, reflections)
- Objects (if exist): 100% identical
- All contact points and spatial relationships: LOCKED
- All shadows: preserve direction and shape

NEVER:
- Separate person from vehicle
- Move person relative to vehicle
- Change vehicle color/shape/size
- Add new people, cars, or objects

ONLY CHANGE: Background behind the foreground subject""",
}


# ============================================================
# 참조 이미지 유형별 프롬프트
# ============================================================

REFERENCE_PROMPTS = {
    "style": """Based on the reference image, generate with:
- Similar lighting style and quality
- Same color palette and tonal range
- Matching mood and atmosphere""",
    "pose": """Based on the reference image, generate with:
- Same pose and body position
- Similar framing and composition
- Matching camera angle""",
    "background": """Based on the reference image, generate with:
- Same background environment
- Similar depth and spatial arrangement
- Matching ambient lighting""",
    "clothing": """Based on the reference garment image, the model wears this EXACT garment.

CRITICAL - Preserve EXACTLY:
- Garment shape and silhouette (DO NOT change)
- All colors including primary and secondary
- Logo/branding placement and design (DO NOT modify or remove)
- All features: hood, zipper, pockets, buttons
- Fabric texture and material appearance
- Fit style (oversized/regular/slim) and length

The garment must be IDENTICAL to reference.""",
    "all": """Based on the reference image, generate a new image that closely follows:
- Lighting: Match the light direction, quality, and shadows
- Colors: Use the same color palette and tonal balance
- Composition: Follow the framing and subject placement
- Mood: Capture the same atmosphere and feeling
- Style: Replicate the overall photographic style""",
}


# ============================================================
# VFX 분석 JSON 스키마 (참조용)
# ============================================================

VFX_JSON_SCHEMA = {
    "geometry": {
        "horizon_y": "float 0.0-1.0",
        "perspective": "eye-level | high-angle | low-angle",
        "camera_height": "eye-level | high | low",
        "viewing_angle": "3/4 | frontal | profile",
        "focal_length_vibe": "35mm | 50mm | 85mm",
    },
    "lighting": {
        "direction_clock": "1-12",
        "elevation": "low | mid | high",
        "softness": "float 0.0-1.0",
        "color_temp": "warm | neutral | cool | K value",
    },
    "pose_dependency": {
        "pose_type": "standing | sitting | leaning | crouching | lying",
        "support_required": "bool",
        "support_type": "wall | pillar | chair | bench | ground",
        "support_direction": "behind | left | right | below",
        "support_distance": "close | near | far",
        "prompt_requirement": "string",
    },
    "installation_logic": {
        "prop_detected": "string",
        "is_fixed_prop": "bool",
        "placement_rule": "string",
        "forbidden_contexts": "list[string]",
    },
    "physics_anchors": {
        "contact_points": "list[{label, coord: [x, y]}]",
        "shadow_casting_direction": "[x, y]",
    },
    "semantic_style": {
        "vibe": "street_editorial | studio | indoor | outdoor",
        "recommended_locations": "list[string]",
    },
}


__all__ = [
    "VFX_ANALYSIS_PROMPT",
    "SOURCE_TYPE_PROMPT",
    "BASE_PRESERVATION_PROMPT",
    "STRUCTURE_STYLE_TRANSFORM",
    "ONE_UNIT_PROMPTS",
    "REFERENCE_PROMPTS",
    "VFX_JSON_SCHEMA",
]
