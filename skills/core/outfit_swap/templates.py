"""
Outfit Swap VLM Prompt Templates

착장 스왑 워크플로의 VLM 프롬프트 모음.

VLM 검수 프롬프트 작성 원칙 (CLAUDE.md 준수):
1. 지시만 하지 말고 STEP-BY-STEP으로 강제
2. 출력 형식 명시 강제 (reason: "REF:~, GEN:~, 감점:~")
3. 계산 공식 명시 강제 (100 - 합계 감점)
"""

# ============================================================
# 1. 소스 이미지 분석 프롬프트
#    얼굴/포즈/배경 추출 -> 착장 스왑 시 보존 정보로 사용
# ============================================================

SOURCE_ANALYSIS_PROMPT = """
이 소스 이미지를 분석해서 착장 스왑 시 보존해야 할 요소를 추출하세요.
착장(옷)은 분석에서 제외하고, 얼굴/포즈/배경/구도만 추출합니다.

아래 JSON 형식으로만 응답하세요. 설명 없이 JSON만 출력:

{
  "face": {
    "position": "center / left / right",
    "angle": "frontal / 3-4 left / 3-4 right / profile left / profile right",
    "expression": "neutral / slight smile / serious / confident",
    "skin_tone": "fair / medium / tan / dark"
  },
  "pose": {
    "body_position": "standing straight / standing relaxed / sitting / leaning / crouching",
    "torso_angle": "frontal / slight left / slight right / side",
    "head_position": "straight / tilted left / tilted right / looking up / looking down",
    "arm_left": "hanging naturally / bent at elbow / hand on hip / raised / crossed",
    "arm_right": "hanging naturally / bent at elbow / hand on hip / raised / crossed",
    "leg_left": "straight / slightly bent / crossed / step forward / weight bearing",
    "leg_right": "straight / slightly bent / crossed / step back / relaxed"
  },
  "background": {
    "setting": "detailed environment description (e.g. concrete wall, street, studio white backdrop)",
    "color_tone": "cool gray / warm beige / neutral / dark / bright",
    "lighting": "soft diffused daylight / hard directional / studio flash / natural window",
    "lighting_direction": "from left / from right / frontal / overhead"
  },
  "composition": {
    "framing": "full body / 3-4 shot (thigh up) / upper body / close up",
    "camera_angle": "eye level / low angle / high angle / bird eye",
    "subject_position": "center / left / right / off-center"
  }
}
"""

# ============================================================
# 2. 착장 이미지 분석 프롬프트
#    각 착장 아이템의 상세 특징 추출 -> 생성 프롬프트에 포함
# ============================================================

OUTFIT_ANALYSIS_PROMPT = """
이 이미지의 의류/액세서리를 분석해서 AI 이미지 생성 프롬프트용으로 상세하게 설명하세요.
패션 화보 수준의 정확도가 필요합니다.

아래 JSON 형식으로만 응답하세요. 설명 없이 JSON만 출력:

{
  "item_type": "garment type (e.g. hoodie, jacket, pants, t-shirt, shorts, cap, bag)",
  "category": "top / bottom / outer / accessory / footwear",
  "color": "specific color with tone (e.g. dark charcoal gray, ivory cream, washed black, light blue)",
  "material": "texture description (e.g. fuzzy mohair, washed denim, smooth leather, cotton fleece)",
  "fit": "silhouette (e.g. oversized, drop shoulder, wide leg, high waist, slim, boxy)",
  "logo": {
    "exists": true,
    "text": "exact logo text (e.g. NY, MLB, Red Sox, DODGERS)",
    "position": "center chest / right chest / left chest / back / sleeve / cap front / waistband",
    "color": "logo color (e.g. white, red, navy, gold)",
    "size": "small / medium / large / oversized"
  },
  "details": "specific design details (e.g. cargo pockets, ribbed cuffs, drawstring hood, front zipper, button placket)",
  "length": "length description (e.g. cropped, regular, longline, ankle-length)",
  "prompt_description": "one-line English description for AI image generation, very specific"
}

**중요 주의사항**:
- logo.exists가 false이면 logo.text, logo.position, logo.color, logo.size 는 null로 설정
- 색상은 일반 색 이름 + 구체적 톤 (예: 그냥 "검정" 대신 "washed black" 또는 "charcoal black")
- prompt_description은 영어로, 소재/색상/핏/로고 모두 포함해서 한 문장에
"""

# ============================================================
# 3. 착장 스왑 생성 프롬프트 템플릿
#    소스 분석 결과 + 착장 분석 결과를 조합해서 사용
# ============================================================

OUTFIT_SWAP_PROMPT_TEMPLATE = """
★★★ OUTFIT EDITING MODE - NOT IMAGE GENERATION ★★★

This is a CLOTHING LAYER SWAP on an existing photograph.
Think of it as Photoshop: the person, pose, and background are LOCKED layers.
You are ONLY replacing the clothing layer.

## MATHEMATICAL PRESERVATION REQUIREMENTS (ABSOLUTE)
- Person height / Frame height = IDENTICAL to SOURCE IMAGE
- Person position in frame = IDENTICAL to SOURCE IMAGE
- Scale factor = 1.0 (NO resizing, NO repositioning)
- Body angle, joint positions, weight distribution = PIXEL-LOCKED to SOURCE
- Face identity, expression, skin = PIXEL-LOCKED to SOURCE
- Background, lighting, color grade = PIXEL-LOCKED to SOURCE

DO NOT MOVE THE PERSON. DO NOT CHANGE THE POSE. DO NOT CHANGE THE SCALE.
DO NOT MOVE THE PERSON. DO NOT CHANGE THE POSE. DO NOT CHANGE THE SCALE.

## IMAGE ROLES
- IMAGE 1 (FIRST IMAGE): SOURCE - Your editing canvas. PRESERVE EVERYTHING except clothing.
- IMAGE 2+: OUTFIT REFERENCE - Use ONLY the garments from these images.

## WHAT TO PRESERVE FROM SOURCE (IMAGE 1) - EVERYTHING EXCEPT CLOTHING
- Face: exact same person, exact features, exact expression, exact skin tone
- Pose: exact body position, exact joint angles, exact weight distribution
- Background: exact same environment, lighting, color tone
- Composition: exact framing, camera angle, subject position
- Body: exact proportions, exact silhouette (minus clothing)

## CRITICAL ANTI-DRIFT WARNING
The outfit reference images (IMAGE 2+) show garments on mannequins or other models.
IGNORE ALL POSES in outfit reference images.
IGNORE ALL FACES in outfit reference images.
IGNORE ALL BACKGROUNDS in outfit reference images.
Extract ONLY the garment details: color, material, logo, fit, design.
Apply these garments to the SOURCE pose, NOT the outfit image pose.

## OUTFIT TO APPLY (FROM IMAGES 2+)
{outfit_description}

## OUTFIT APPLICATION RULES
- Replace ALL clothing from source with the outfit items above
- Match outfit colors EXACTLY to reference images
- Match logos (text, position, color, size) EXACTLY to reference images
- Match material textures EXACTLY to reference images
- Match fit/silhouette EXACTLY to reference images
- Drape naturally on the SOURCE pose (wrinkles/folds match the body position)
- Clothing must conform to SOURCE body position, not float or detach

## ABSOLUTE PROHIBITIONS
1. DO NOT change the person's face from SOURCE
2. DO NOT change the person's pose from SOURCE
3. DO NOT change the background from SOURCE
4. DO NOT adopt any pose from outfit reference images
5. DO NOT mix source clothing with new outfit
6. DO NOT shrink, move, or rescale the person
7. DO NOT change the camera angle or framing
"""

# ============================================================
# 4. 검증 프롬프트
#    CLAUDE.md VLM 검수 프롬프트 원칙 완전 적용:
#    - STEP-BY-STEP 강제
#    - reason 형식 강제 (REF:~, GEN:~, 감점:~)
#    - 감점 계산 공식 명시
# ============================================================

VALIDATION_PROMPT = """
당신은 착장 스왑 이미지 검수 전문가입니다.
SOURCE 이미지와 RESULT 이미지를 비교해서 착장 스왑 품질을 판정합니다.

입력 이미지 순서:
- IMAGE 1: SOURCE (원본 - 얼굴/포즈/배경 보존 기준)
- IMAGE 2: RESULT (착장 스왑 결과 - 평가 대상)
- IMAGE 3+: OUTFIT REFERENCE (착장 레퍼런스 - 착장 정확도 판정 기준)

---

## 평가 기준 5가지

### 1. outfit_accuracy (착장 정확도) - 35%

[STEP 1] OUTFIT REFERENCE 착장 분석:
- 아이템 개수 세기 (상의/하의/겉옷/액세서리 각각)
- 각 아이템의 색상 = ?
- 각 아이템의 로고 텍스트/위치/색상 = ?
- 각 아이템의 소재 느낌 = ?

[STEP 2] RESULT 이미지 착장 분석:
- 착장된 아이템 개수 = ?
- 각 아이템의 색상 = ?
- 각 아이템의 로고 텍스트/위치/색상 = ?
- 각 아이템의 소재 느낌 = ?

[STEP 3] 비교 및 감점:
- 아이템 누락 1개당: -30
- 색상 불일치 1개당: -15
- 로고 텍스트/위치 불일치: -20
- 로고 색상 불일치: -10
- 소재 느낌 불일치: -8

[STEP 4] 최종 점수 = 100 - 합계 감점 (최소 0)

reason 필수 형식: "REF:아이템목록, GEN:아이템목록, 누락:아이템명, 감점:-숫자"
Auto-Fail 조건: 아이템 누락 1개 이상 OR 색상 불일치 AND 총점 < 70

---

### 2. face_identity (얼굴 동일성) - 25%

[STEP 1] SOURCE IMAGE 얼굴 분석:
- 얼굴형/눈/코/입/턱선 = ?
- 피부톤 = ?
- 나이대 = ?

[STEP 2] RESULT IMAGE 얼굴 분석:
- 얼굴형/눈/코/입/턱선 = ?
- 피부톤 = ?
- 나이대 = ?

[STEP 3] 비교 및 감점:
- 다른 인물: -100 (즉시 0점)
- 동일 인물이나 특징 변화 큼: -30
- 동일 인물이나 피부톤 변화: -10
- 동일 인물이나 나이대 다름: -15

[STEP 4] 최종 점수 = 100 - 합계 감점 (최소 0)

reason 필수 형식: "REF:얼굴특징, GEN:얼굴특징, 감점:-숫자"
Auto-Fail 조건: face_identity < 80 (다른 사람)

---

### 3. pose_preservation (포즈 유지) - 25%

[STEP 1] SOURCE IMAGE 포즈 분석:
- 전체 자세 = ?
- 팔 위치 (좌/우) = ?
- 다리 위치 (좌/우) = ?
- 머리/상체 각도 = ?

[STEP 2] RESULT IMAGE 포즈 분석:
- 전체 자세 = ?
- 팔 위치 (좌/우) = ?
- 다리 위치 (좌/우) = ?
- 머리/상체 각도 = ?

[STEP 3] 비교 및 감점:
- 전체 자세 변경: -40
- 팔 위치 변경 1개당: -15
- 다리 위치 변경 1개당: -10
- 머리/상체 각도 변경: -10

[STEP 4] 최종 점수 = 100 - 합계 감점 (최소 0)

reason 필수 형식: "REF:포즈설명, GEN:포즈설명, 감점:-숫자"
Auto-Fail 조건: pose_preservation < 90 (포즈 변경 심각)

---

### 4. outfit_draping (착장 드레이핑) - 10%

평가 기준:
- 착장이 포즈에 자연스럽게 맞는가?
- 주름/폴드가 물리적으로 타당한가?
- 옷이 몸에서 떠있거나 분리되지 않는가?
- 착장이 몸 윤곽을 자연스럽게 따르는가?

감점:
- 착장이 몸에서 떠있음: -30
- 물리적으로 불가능한 착장: -25
- 어색한 주름 패턴: -15
- 착장 경계가 부자연스러움: -10

최종 점수 = 100 - 합계 감점 (최소 0)

reason 필수 형식: "드레이핑 상태: 문제점 설명, 감점:-숫자"

---

### 5. background_preservation (배경 유지) - 5%

[STEP 1] SOURCE IMAGE 배경 분석: 설정/색조/조명 = ?
[STEP 2] RESULT IMAGE 배경 분석: 설정/색조/조명 = ?
[STEP 3] 감점: 배경 설정 변경(-40) / 색조 변화(-20) / 조명 방향 변화(-15)
[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:배경설명, GEN:배경설명, 감점:-숫자"

---

## 출력 형식 (JSON)

반드시 JSON만 출력하세요. 설명 없이!

```json
{
  "outfit_accuracy": {
    "score": 0-100,
    "reason": "REF:후디(블랙NY)+카고팬츠, GEN:후디(블랙NY)+카고팬츠, 감점:-0",
    "missing_items": [],
    "color_mismatches": []
  },
  "face_identity": {
    "score": 0-100,
    "reason": "REF:동양인여성/오목한눈/피부페어, GEN:동일인물/특징일치, 감점:-0"
  },
  "pose_preservation": {
    "score": 0-100,
    "reason": "REF:직립/왼손허리/오른팔늘어뜨림, GEN:동일포즈유지, 감점:-0"
  },
  "outfit_draping": {
    "score": 0-100,
    "reason": "드레이핑 상태: 자연스러운 착장, 감점:-0"
  },
  "background_preservation": {
    "score": 0-100,
    "reason": "REF:콘크리트벽/쿨그레이/왼쪽자연광, GEN:배경완전유지, 감점:-0"
  },
  "auto_fail": false,
  "auto_fail_reasons": [],
  "issues": [],
  "summary_kr": "한국어 요약 (2-3문장)"
}
```
"""

# ============================================================
# 프롬프트 조립 헬퍼 함수
# ============================================================


def build_outfit_swap_prompt(
    source_analysis: dict, outfit_descriptions: list[str]
) -> str:
    """
    착장 설명으로 최종 생성 프롬프트 조립

    편집 모드 프롬프트: 소스 이미지의 포즈/얼굴/배경은 텍스트로 명시하지 않고
    "SOURCE IMAGE에서 모든 것을 보존하라"는 블랭킷 지시로 처리한다.
    소스 분석 결과는 prompt.json에 기록용으로만 저장된다.

    Args:
        source_analysis: SOURCE_ANALYSIS_PROMPT로 얻은 분석 결과 (기록용)
        outfit_descriptions: 각 착장 아이템의 prompt_description 리스트

    Returns:
        완성된 프롬프트 문자열
    """
    # 착장 설명 포맷
    outfit_text = "\n".join(f"- {desc}" for desc in outfit_descriptions)

    return OUTFIT_SWAP_PROMPT_TEMPLATE.format(
        outfit_description=outfit_text,
    )


__all__ = [
    "SOURCE_ANALYSIS_PROMPT",
    "OUTFIT_ANALYSIS_PROMPT",
    "OUTFIT_SWAP_PROMPT_TEMPLATE",
    "VALIDATION_PROMPT",
    "build_outfit_swap_prompt",
]
