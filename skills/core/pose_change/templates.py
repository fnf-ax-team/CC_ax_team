"""
포즈 변경 VLM 프롬프트 템플릿 모듈

SKILL.md의 VLM 프롬프트를 기반으로 구성.

포함 프롬프트:
  1. SOURCE_ANALYSIS_PROMPT  - 소스 이미지 분석 (얼굴/착장/배경 보존 요소 추출)
  2. POSE_CHANGE_PROMPT      - 이미지 생성 프롬프트 조립 함수
  3. VALIDATION_PROMPT       - 단계별 강제 검수 프롬프트 (VLM 규칙 준수)
"""

# =============================================================================
# 1. 소스 이미지 분석 프롬프트
#    VLM(VISION_MODEL)에 소스 이미지와 함께 전달하여 보존 요소 추출
# =============================================================================
SOURCE_ANALYSIS_PROMPT = """
이 이미지를 분석해서 포즈 변경 시 보존해야 할 모든 요소를 추출하세요.

JSON 출력:
{
  "current_pose": {
    "body_position": "standing",
    "torso_angle": "straight, facing forward",
    "head_position": "straight, looking at camera",
    "arm_left": "hanging naturally by side",
    "arm_right": "hanging naturally by side",
    "leg_left": "straight, bearing weight",
    "leg_right": "straight, bearing weight",
    "weight_distribution": "evenly distributed",
    "overall_description": "standing upright, arms by sides"
  },
  "preserve_elements": {
    "face": {
      "identity": "Korean female, 20s, natural makeup",
      "expression": "slight smile, neutral",
      "skin_tone": "fair, natural",
      "hair": "long black hair, straight, shoulder length",
      "facial_structure": "oval face, defined features"
    },
    "outfit": {
      "top": {
        "type": "oversized hoodie",
        "color": "dark charcoal gray",
        "material": "cotton fleece",
        "details": ["front pocket", "drawstring hood", "ribbed cuffs"],
        "logo": {
          "exists": true,
          "text": "NY",
          "position": "center chest",
          "color": "white",
          "size": "large"
        },
        "fit": "oversized, drop shoulder"
      },
      "bottom": {
        "type": "wide leg jeans",
        "color": "light wash blue",
        "material": "denim",
        "details": ["high waist", "cargo pockets on sides"],
        "fit": "wide leg, ankle length"
      }
    },
    "background": {
      "setting": "concrete wall background",
      "description": "minimalist urban setting, neutral gray concrete wall",
      "lighting": "soft natural light from left side",
      "atmosphere": "clean, modern, industrial-minimal"
    },
    "body_type": {
      "height_proportion": "model proportions, 8-head ratio",
      "build": "slim, athletic",
      "leg_length": "long legs"
    }
  },
  "physical_constraints": {
    "ground_type": "flat floor",
    "nearby_objects": ["concrete wall on background"],
    "space_available": "indoor studio space"
  }
}

중요:
- 얼굴 특징을 매우 구체적으로 (피부톤, 헤어스타일, 표정)
- 착장의 모든 디테일 (색상, 로고, 소재, 핏)
- 배경 환경 정확히 설명
- 물리적 제약 사항 명시
""".strip()


# =============================================================================
# 2. 이미지 생성 프롬프트 조립 함수
#    소스 분석 결과 + 목표 포즈로 IMAGE_MODEL에 전달할 프롬프트 생성
# =============================================================================
def build_pose_change_prompt(source_analysis: dict, target_pose: str) -> str:
    """소스 분석 결과와 목표 포즈로 이미지 생성 프롬프트 조립.

    얼굴/착장/배경은 소스 분석 결과 그대로 유지하고
    포즈만 target_pose 설명으로 변경한다.
    조명은 새 포즈에 맞게 자연스럽게 적응.

    Args:
        source_analysis: SOURCE_ANALYSIS_PROMPT 결과 JSON (dict)
        target_pose: 목표 포즈 설명 영문 텍스트 (예: "sitting on floor, legs crossed")

    Returns:
        str: IMAGE_MODEL에 전달할 생성 프롬프트
    """
    preserve = source_analysis["preserve_elements"]
    constraints = source_analysis["physical_constraints"]

    face = preserve["face"]
    top = preserve["outfit"]["top"]
    bottom = preserve["outfit"]["bottom"]
    background = preserve["background"]
    body_type = preserve["body_type"]

    # 착장 설명 조립
    outfit_desc = (
        f"[TOP - EXACT REPRODUCTION]\n"
        f"- {top['type']}: {top['color']} color\n"
        f"- Material: {top['material']}\n"
        f"- Details: {', '.join(top['details'])}\n"
    )
    if top.get("logo", {}).get("exists"):
        logo = top["logo"]
        outfit_desc += (
            f"- Logo: \"{logo['text']}\" in {logo['color']} on {logo['position']}\n"
        )
    outfit_desc += (
        f"- Fit: {top['fit']}\n\n"
        f"[BOTTOM - EXACT REPRODUCTION]\n"
        f"- {bottom['type']}: {bottom['color']} color\n"
        f"- Material: {bottom['material']}\n"
        f"- Details: {', '.join(bottom['details'])}\n"
        f"- Fit: {bottom['fit']}"
    )

    prompt = f"""Generate a high-quality fashion photo with EXACT preservation of all elements except pose.

[CRITICAL - PRESERVE EXACTLY]

FACE (DO NOT CHANGE):
- Identity: {face['identity']}
- Expression: {face['expression']}
- Skin tone: {face['skin_tone']}
- Hair: {face['hair']}
- Facial structure: {face['facial_structure']}

OUTFIT (DO NOT CHANGE):
{outfit_desc}

BACKGROUND (DO NOT CHANGE):
- Setting: {background['setting']}
- Description: {background['description']}
- Atmosphere: {background['atmosphere']}

BODY TYPE (DO NOT CHANGE):
- Proportions: {body_type['height_proportion']}
- Build: {body_type['build']}
- Leg length: {body_type['leg_length']}

[CHANGE - NEW POSE ONLY]

POSE (CHANGE TO THIS):
{target_pose}

Physical constraints:
- Ground type: {constraints['ground_type']}
- Available space: {constraints['space_available']}
- Must be physically plausible and natural

[LIGHTING ADAPTATION]
- Adapt lighting naturally to new pose
- Maintain soft, natural quality
- Ensure face is well-lit
- Shadows should match new body position

[QUALITY REQUIREMENTS]
- High-end fashion editorial quality
- Natural skin texture (not overly polished)
- Sharp focus throughout
- Physically correct pose (no impossible angles)
- Proper weight distribution
- Natural hand/finger positions

DO NOT:
- Change facial features or identity
- Alter outfit colors, logos, or details
- Modify background setting
- Change body proportions
- Create unnatural or impossible poses
- Add yellow/golden cast to skin"""

    return prompt.strip()


# =============================================================================
# 3. 검수 프롬프트
#    CLAUDE.md VLM 검수 프롬프트 작성 원칙 준수:
#    - 단계별 출력 강제 (STEP 1~4)
#    - 출력 형식 명시
#    - 감점 계산 공식 명시
#
#    소스 이미지(IMAGE 1)와 생성 이미지(IMAGE 2)를 함께 전달하여 비교 검수
# =============================================================================
VALIDATION_PROMPT = """
Compare IMAGE 1 (SOURCE) and IMAGE 2 (RESULT) to verify pose change quality.

IMAGE 1 = SOURCE: Original image (reference for preservation)
IMAGE 2 = RESULT: Generated image with new pose

Evaluate each criterion using MANDATORY step-by-step analysis.
Do NOT skip any step. Output each step explicitly.

---

### 1. face_identity [CRITICAL]

[STEP 1] SOURCE face analysis:
- SRC identity = ?
- SRC skin tone = ?
- SRC hair = ?
- SRC expression = ?

[STEP 2] RESULT face analysis:
- RES identity = ?
- RES skin tone = ?
- RES hair = ?
- RES expression = ?

[STEP 3] Comparison and deduction:
- Same person: yes(0) / no(-40)
- Skin tone match: yes(0) / slight diff(-5) / different(-15)
- Hair match: yes(0) / slight diff(-5) / different(-10)
- Total deduction = ?

[STEP 4] face_identity score = 100 - total deduction
reason format: "SRC:fair+black-hair, RES:same-person, deduction:-0"

---

### 2. outfit_preservation [CRITICAL]

[STEP 1] SOURCE outfit analysis:
- SRC top = ?
- SRC bottom = ?
- SRC logo = ?
- SRC colors = ?

[STEP 2] RESULT outfit analysis:
- RES top = ?
- RES bottom = ?
- RES logo = ?
- RES colors = ?

[STEP 3] Comparison and deduction:
- Top type match: yes(0) / different(-20)
- Top color match: yes(0) / slight diff(-5) / different(-20)
- Logo preserved: yes(0) / missing(-30) / altered(-20)
- Bottom match: yes(0) / different(-20)
- Total deduction = ?

[STEP 4] outfit_preservation score = 100 - total deduction
reason format: "SRC:gray-hoodie+NY-logo+jeans, RES:same, deduction:-0"

---

### 3. pose_correctness

[STEP 1] Target pose description (from context):
- Target = ? (describe expected pose)

[STEP 2] RESULT pose analysis:
- RES body position = ?
- RES weight distribution = ?
- RES arm position = ?
- RES leg position = ?

[STEP 3] Comparison and deduction:
- Pose matches target: yes(0) / partial(-15) / no(-30)
- Physically plausible: yes(0) / minor issue(-10) / impossible(-40)
- Natural weight distribution: yes(0) / awkward(-10)
- Total deduction = ?

[STEP 4] pose_correctness score = 100 - total deduction
reason format: "target:lean-wall, RES:leaning-naturally, deduction:-0"

---

### 4. physics_plausibility

[STEP 1] Assess physical realism of RESULT:
- Ground contact = ?
- Center of gravity = ?
- Limb angles = ?

[STEP 2] Check for abnormalities:
- Finger count normal: yes(0) / 6+fingers(-30)
- Joints natural: yes(0) / unnatural(-20)
- Grounding correct: yes(0) / floating(-20)
- Total deduction = ?

[STEP 3] physics_plausibility score = 100 - total deduction
reason format: "grounding:ok, joints:ok, fingers:normal, deduction:-0"

---

### 5. lighting_consistency

[STEP 1] SOURCE lighting analysis:
- SRC light direction = ?
- SRC shadow style = ?

[STEP 2] RESULT lighting analysis:
- RES light direction = ?
- RES shadow style = ?
- RES face well-lit = ?

[STEP 3] Comparison and deduction:
- Light direction adapted naturally: yes(0) / harsh artifact(-15)
- Face well-lit: yes(0) / shadowed(-10)
- Warm/yellow cast present: no(0) / yes(-20)
- Total deduction = ?

[STEP 4] lighting_consistency score = 100 - total deduction
reason format: "SRC:soft-left, RES:adapted-naturally, deduction:-0"

---

Return ONLY the following JSON (no extra text):
{
  "face_identity": {
    "score": 0,
    "same_person": true,
    "issues": [],
    "reason": ""
  },
  "outfit_preservation": {
    "score": 0,
    "all_preserved": true,
    "issues": [],
    "reason": ""
  },
  "pose_correctness": {
    "score": 0,
    "matches_target": true,
    "physically_plausible": true,
    "issues": [],
    "reason": ""
  },
  "physics_plausibility": {
    "score": 0,
    "grounding_correct": true,
    "hand_fingers_normal": true,
    "issues": [],
    "reason": ""
  },
  "lighting_consistency": {
    "score": 0,
    "natural": true,
    "face_well_lit": true,
    "issues": [],
    "reason": ""
  },
  "auto_fail_triggers": [],
  "recommendation": "PASS"
}

AUTO-FAIL triggers (add to auto_fail_triggers list if any apply):
- "different_person" if face_identity < 80
- "outfit_changed" if outfit colors or logos altered
- "impossible_pose" if pose is physically impossible
- "six_plus_fingers" if 6+ fingers detected
- "body_proportion_changed" if body shape drastically altered

recommendation values: "PASS" / "RETRY" / "FAIL"
""".strip()
