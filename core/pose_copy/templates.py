"""
pose_copy VLM 프롬프트 템플릿

핵심 원칙:
- 레퍼런스 이미지 → API에 직접 전달 (포즈/구도 보존)
- 소스 이미지 → VLM 텍스트 분석만 (포즈 혼동 방지)
"""

# ============================================================================
# 1. 레퍼런스 포즈 분석 프롬프트
# ============================================================================

REFERENCE_POSE_ANALYSIS_PROMPT = """
레퍼런스 이미지를 분석해서 포즈, 구도, 카메라 앵글을 정확히 추출하세요.

[STEP 1] 포즈 분석:
- 전체 신체 자세 (서있음/앉음/누움 등)
- 체중 이동 방향
- 상체 각도 (정면/측면/3/4뷰)
- 머리 방향 (좌/우/중앙, 위/아래)
- 왼팔 위치 (자세히)
- 오른팔 위치 (자세히)
- 왼다리 위치
- 오른다리 위치
- 전체적 느낌 (자신감/여유/에너지)

[STEP 2] 구도 분석:
- 인물 화면 위치 (중앙/좌/우, 상/중/하) → 정규화 좌표 0.0~1.0
- 인물이 화면에서 차지하는 비율 (0.0~1.0)
- 프레이밍 (전신/반신/상반신/클로즈업)
- 카메라 앵글 (아이레벨/로우앵글/하이앵글)
- 거리감 (클로즈업/미디엄샷/풀샷/와이드)

[STEP 3] 배경 분석:
- 배경 장소/환경
- 색조
- 깊이감
- 조명 방향과 성격

[STEP 4] 표정 분석:
- 표정
- 시선 방향
- 전체적 무드

아래 JSON 형식으로 출력하세요:
{
  "pose": {
    "body_position": "standing, weight on right leg, slight hip tilt",
    "torso_angle": "3/4 left, slight lean forward",
    "head_position": "turned slightly left, chin up",
    "arm_left": "bent at elbow 90deg, hand on hip",
    "arm_right": "relaxed, hanging naturally, fingers spread",
    "leg_left": "straight, weight-bearing",
    "leg_right": "slightly bent, relaxed",
    "overall_vibe": "confident, casual stance"
  },
  "composition": {
    "person_position": {"x": 0.5, "y": 0.6},
    "person_size_ratio": 0.7,
    "framing": "full body, centered",
    "camera_angle": "eye-level, slightly from below",
    "distance": "medium shot"
  },
  "background": {
    "setting": "concrete wall, industrial",
    "color_tone": "cool gray, muted",
    "depth": "shallow, simple",
    "lighting": "soft natural light from left, diffused"
  },
  "expression": {
    "face": "neutral, confident",
    "gaze_direction": "camera, direct eye contact",
    "mood": "relaxed, self-assured"
  }
}
"""

# ============================================================================
# 2. 소스 인물 분석 프롬프트 (얼굴/착장만 - 포즈 제외)
# ============================================================================

SOURCE_PERSON_ANALYSIS_PROMPT = """
소스 이미지를 분석해서 얼굴과 착장 정보를 추출하세요.

중요: 포즈/자세 정보는 추출하지 마세요. 얼굴과 착장만 분석합니다.

[STEP 1] 얼굴 분석 (AI가 놓치기 쉬운 특징까지 반드시 추출):
- 나이대 (구체적: mid-20s 등)
- 성별
- 민족/인종
- 피부톤 (fair/medium/tan/dark, cool/warm undertone, 구체적 색조)
- 얼굴형 (oval/round/heart/square/oblong)
- 눈: 모양(아몬드/둥근/쌍꺼풀유무), 크기, 간격
- 코: 높이, 폭, 콧날 모양
- 입술: 두께, 모양, 색상
- 턱선: 각진/둥근, 턱 길이
- 광대뼈: 높이, 돌출 정도
- 눈썹: 두께, 아치, 색상
- 고유 특징: 점, 보조개, 주근깨, 흉터 등 (반드시 3개 이상 기재, 없으면 "none detected" 기재)
- 전체 인상: 한 문장으로 요약 (예: "높은 광대뼈와 큰 아몬드눈이 특징적인 쿨톤 피부의 동아시아 여성")

[STEP 2] 착장 분석 (pixel-perfect 재현을 위해 상세히 추출):
- 전체 착장 아이템 목록 (아우터/상의/하의/신발/모자/액세서리 전부)
- 각 아이템별:
  - 정확한 색상 (단순 "black"이 아니라 "charcoal black" 또는 "jet black" 등 구체적으로)
  - 소재감/질감 (면/니트/데님/레더/나일론/폴리 등)
  - 핏/실루엣 (오버사이즈/레귤러/슬림/크롭 등)
  - 로고/그래픽: 브랜드명, 위치(예: "왼쪽 가슴 상단"), 크기(예: "가슴폭 1/3"), 색상
  - 부자재/디테일: 지퍼, 단추, 스티치, 포켓, 리벳, 자수 등
- 레이어링 순서 (안쪽부터 바깥쪽)
- 전체 스타일 방향: 스트릿/캐주얼/포멀/스포티 등

[STEP 3] 헤어 분석:
- 길이
- 색상
- 스타일
- 질감

아래 JSON 형식으로 출력하세요:
{
  "face": {
    "age": "mid-20s",
    "gender": "female",
    "ethnicity": "East Asian",
    "skin_tone": "fair, cool undertone, porcelain",
    "face_shape": "oval",
    "eyes": "large almond-shaped, double eyelid, wide-set",
    "nose": "medium height, narrow bridge, soft rounded tip",
    "lips": "medium thickness, natural pink tone, cupid's bow defined",
    "jawline": "soft V-line, narrow chin",
    "cheekbones": "high, subtly prominent",
    "eyebrows": "straight, medium thickness, dark brown",
    "distinctive_features": ["small mole under left eye", "dimple on right cheek", "slight freckles on nose bridge"],
    "overall_impression": "높은 광대뼈와 큰 아몬드눈이 특징적인 쿨톤 피부의 동아시아 여성"
  },
  "outfit": {
    "items": [
      {
        "type": "top",
        "item": "oversized hoodie",
        "color": "charcoal black",
        "material": "heavy cotton fleece",
        "fit": "oversized, dropped shoulders",
        "logo": {"brand": "MLB", "position": "center chest", "size": "large, 15cm width", "color": "white"},
        "details": ["drawstrings visible", "kangaroo pocket", "ribbed cuffs and hem"]
      }
    ],
    "layering_order": ["hoodie (outermost)"],
    "overall_style": "streetwear, casual, relaxed"
  },
  "hair": {
    "length": "long, past shoulders, mid-back",
    "color": "dark brown, natural, no highlights",
    "style": "straight, center part, loose and flowing",
    "texture": "sleek, smooth, healthy shine"
  }
}
"""

# ============================================================================
# 3. 메인 생성 프롬프트 (포즈 복제용)
# ============================================================================

POSE_COPY_PROMPT = """
[CRITICAL - IMAGE ROLE ASSIGNMENT]

You are receiving ONE reference image. Use it for POSE and COMPOSITION ONLY.

[REFERENCE IMAGE - COPY THESE EXACTLY]
The first image is your reference for pose and framing.

POSE (copy exactly from reference):
{pose_description}

COMPOSITION (copy exactly from reference):
{composition_description}

EXPRESSION (adapt from reference, keep mood):
{expression_description}

[SOURCE PERSON - TEXT DESCRIPTION ONLY]
Apply the following face and outfit to the reference pose.

FACE (MUST be the SAME PERSON as described):
{face_description}
- This person's face MUST be recognizable as the same individual described above
- PRESERVE every distinctive feature listed in the description above
- Match the face angle naturally to the pose (head position from reference)
- Skin tone and undertone: EXACT match to description
- Eye shape, nose, lips, jawline: EXACT match — not "similar", but IDENTICAL person
- Natural skin texture with visible pores — NO AI plastic/waxy skin
- DO NOT create a generic attractive face — create THIS specific person

OUTFIT (pixel-perfect 재현 필수):
{outfit_description}
- MUST reproduce every outfit element described above with zero modification
- Colors: EXACT match to description — no color shifting, no darkening/lightening
- Logos/Graphics: EXACT brand, position, size, and color as described
- Material/Texture: Match described fabric type and surface quality
- Fit/Silhouette: Match described fit exactly (oversized stays oversized, slim stays slim)
- Details: All zippers, buttons, stitching, pockets must be present
- NEVER substitute, omit, or modify any outfit element
- NEVER add items not described (no extra accessories, no added patterns)

HAIR:
{hair_description}

[BACKGROUND]
{background_instruction}

[CRITICAL CONSTRAINTS - DO NOT VIOLATE]
1. POSE: Must match reference image pose exactly
2. COMPOSITION: Must match reference framing, angle, and person position
3. FACE: Use source face description ONLY - do NOT use reference person's face
4. OUTFIT: Use source outfit description ONLY - do NOT use reference person's outfit
5. Ensure seamless integration between face, outfit, and pose
6. Natural lighting consistent with background
7. Expression and gaze direction should match reference mood

[OUTPUT QUALITY]
- High-end professional photography quality
- Natural skin texture with realistic pores (no plastic skin)
- Sharp focus, clean edges, no artifacts
- Consistent lighting across face, outfit, and background
- Pose must look natural and effortless, not stiff
- Photorealistic, NOT illustrated or rendered

★★★ CRITICAL WARNING — IDENTITY SEPARATION ★★★
The reference image person and the source person are DIFFERENT people.
- Do NOT use the reference person's face in the output
- Do NOT use the reference person's outfit in the output
- Do NOT use the reference person's hair style/color in the output
- ONLY use the reference for: pose, camera angle, framing, composition, expression mood
- Face, outfit, and hair MUST come from the TEXT DESCRIPTION above ONLY
- If in doubt: the text description overrides any visual information from the reference
"""

# ============================================================================
# 4. 검수 프롬프트 (step-by-step 강제, VLM 건너뜀 방지)
# ============================================================================

VALIDATION_PROMPT = """
세 이미지를 비교해서 Pose Copy 결과를 단계별로 검수하세요.

Image 1: 레퍼런스 이미지 (포즈/구도 ground truth)
Image 2: 소스 이미지 (얼굴/착장 ground truth)
Image 3: 생성 결과 이미지

========================================
[SECTION A] 포즈 유사도 (pose_similarity) ★★★ 가장 중요 ★★★
========================================

[A-STEP 1] 레퍼런스 이미지(Image 1) 포즈 분석:
- REF 신체자세 = ?
- REF 상체각도 = ?
- REF 머리방향 = ?
- REF 왼팔 = ?
- REF 오른팔 = ?
- REF 다리자세 = ?

[A-STEP 2] 생성결과(Image 3) 포즈 분석:
- GEN 신체자세 = ?
- GEN 상체각도 = ?
- GEN 머리방향 = ?
- GEN 왼팔 = ?
- GEN 오른팔 = ?
- GEN 다리자세 = ?

[A-STEP 3] 비교 및 감점 계산:
- 신체자세: 일치(0) / 약간다름(-5) / 많이다름(-15)
- 상체각도: 일치(0) / 약간다름(-5) / 많이다름(-15)
- 머리방향: 일치(0) / 약간다름(-3) / 많이다름(-10)
- 왼팔: 일치(0) / 약간다름(-5) / 많이다름(-15)
- 오른팔: 일치(0) / 약간다름(-5) / 많이다름(-15)
- 다리자세: 일치(0) / 약간다름(-5) / 많이다름(-15)

[A-STEP 4] 포즈 최종 점수 = 100 - 합계 감점 = ?

reason 필수 형식: "REF:오른손엉덩이+왼팔내림+정면, GEN:양손내림+측면, 감점:-40"

========================================
[SECTION B] 얼굴 보존 (face_preservation)
========================================

[B-STEP 1] 소스 이미지(Image 2) 얼굴 특징:
- SRC 인물 특징 = ?

[B-STEP 2] 생성결과(Image 3) 얼굴:
- GEN 동일 인물인가? (yes/no)
- GEN 차이점 = ?

[B-STEP 3] 감점 계산:
- 동일 인물: 감점 없음(0) / 약간 다름(-10) / 다른 사람(-40)
- 피부톤 일치: 일치(0) / 불일치(-5)
- 뚜렷한 특징 보존: 보존(0) / 손실(-5 ~ -15)

[B-STEP 4] 얼굴 최종 점수 = 100 - 합계 감점 = ?

reason 필수 형식: "SRC:높은광대뼈+아몬드눈, GEN:동일인물확인, 감점:0"

========================================
[SECTION C] 착장 보존 (outfit_preservation)
========================================

[C-STEP 1] 소스 이미지(Image 2) 착장:
- SRC 착장 = ?

[C-STEP 2] 생성결과(Image 3) 착장:
- GEN 착장 = ?
- 변경된 요소 = ?

[C-STEP 3] 감점 계산:
- 색상 일치: 일치(0) / 불일치(-15 per item)
- 로고/패턴: 보존(0) / 변경(-15) / 누락(-20)
- 아이템 누락: 없음(0) / 아이템당 -20
- 핏/실루엣: 일치(0) / 변경(-10)

[C-STEP 4] 착장 최종 점수 = 100 - 합계 감점 = ?

reason 필수 형식: "SRC:MLB블랙후디+청바지, GEN:후디색변경(흰색), 감점:-15"

========================================
[SECTION D] 구도 일치 (composition_match)
========================================

[D-STEP 1] 레퍼런스 이미지(Image 1) 구도:
- REF 프레이밍 = ?
- REF 카메라앵글 = ?
- REF 인물위치 = ?

[D-STEP 2] 생성결과(Image 3) 구도:
- GEN 프레이밍 = ?
- GEN 카메라앵글 = ?
- GEN 인물위치 = ?

[D-STEP 3] 감점 계산:
- 프레이밍: 일치(0) / 약간다름(-10) / 많이다름(-25)
- 카메라앵글: 일치(0) / 약간다름(-10) / 많이다름(-20)
- 인물위치: 일치(0) / 약간다름(-5) / 많이다름(-15)

[D-STEP 4] 구도 최종 점수 = 100 - 합계 감점 = ?

reason 필수 형식: "REF:전신+아이레벨+중앙, GEN:반신+하이앵글+중앙, 감점:-35"

========================================
[AUTO-FAIL 체크]
========================================

다음 중 해당하는 것이 있으면 auto_fail = true:
- pose_similarity < 70: 포즈가 완전히 다름
- face_preservation < 80: 다른 사람의 얼굴
- outfit_preservation < 80: 착장이 완전히 다름
- 손가락 6개 이상 / 기형적 손가락 발견
- 누런 톤 (golden/amber cast) 심각
- 레퍼런스 인물의 얼굴이 결과에 사용됨

========================================
[최종 JSON 출력]
========================================

{
  "pose_similarity": {
    "score": 88,
    "matching_elements": ["body_position", "left_arm"],
    "differing_elements": ["head_angle slightly off"],
    "issues": [],
    "reason": "REF:오른손엉덩이+정면, GEN:오른손엉덩이+정면, 감점:-12"
  },
  "face_preservation": {
    "score": 95,
    "same_person": true,
    "issues": [],
    "reason": "SRC:높은광대뼈+아몬드눈, GEN:동일확인, 감점:0"
  },
  "outfit_preservation": {
    "score": 92,
    "changed_elements": [],
    "issues": [],
    "reason": "SRC:블랙후디+청바지, GEN:동일확인, 감점:-8"
  },
  "composition_match": {
    "score": 90,
    "person_position_match": true,
    "framing_match": true,
    "camera_angle_match": true,
    "issues": [],
    "reason": "REF:전신+아이레벨, GEN:전신+아이레벨, 감점:-10"
  },
  "auto_fail": false,
  "auto_fail_reasons": [],
  "pass": true
}
"""

# ============================================================================
# 배경 옵션별 지시 생성
# ============================================================================


def get_background_instruction(
    bg_option: str, ref_bg: dict, source_bg: dict = None, custom_bg: str = None
) -> str:
    """배경 옵션별 프롬프트 생성

    Args:
        bg_option: "reference" / "source" / "custom"
        ref_bg: 레퍼런스 이미지 배경 분석 결과 (dict)
        source_bg: 소스 이미지 배경 분석 결과 (dict, source 옵션 시 필수)
        custom_bg: 커스텀 배경 설명 문자열 (custom 옵션 시 필수)

    Returns:
        str: 프롬프트에 삽입할 배경 지시문
    """
    if bg_option == "reference":
        return f"""BACKGROUND (from reference image):
Setting: {ref_bg.get('setting', 'unspecified')}
Color tone: {ref_bg.get('color_tone', 'neutral')}
Depth: {ref_bg.get('depth', 'medium')}
Lighting: {ref_bg.get('lighting', 'natural')}

Recreate this background. Match the mood and color temperature exactly."""

    elif bg_option == "source":
        if not source_bg:
            raise ValueError("source_bg dict required when bg_option='source'")
        return f"""BACKGROUND (from source image):
Setting: {source_bg.get('setting', 'unspecified')}
Color tone: {source_bg.get('color_tone', 'neutral')}
Depth: {source_bg.get('depth', 'medium')}
Lighting: {source_bg.get('lighting', 'natural')}

Use the source person's background context.
Adjust lighting direction to match the reference pose naturally."""

    elif bg_option == "custom":
        if not custom_bg:
            raise ValueError("custom_bg string required when bg_option='custom'")
        return f"""BACKGROUND (custom):
{custom_bg}

Ensure:
- Lighting direction matches the pose naturally
- Depth appropriate for the framing
- Visual style cohesive with the outfit"""

    # 기본값: 심플 뉴트럴 배경
    return "BACKGROUND: Clean, neutral studio background. Simple and minimal."
