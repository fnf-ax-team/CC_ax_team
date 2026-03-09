"""
Face Swap VLM 프롬프트 템플릿

포함 항목:
1. SOURCE_ANALYSIS_PROMPT  - 소스 이미지 분석 (보존 요소 추출)
2. FACE_SELECTION_PROMPT   - 얼굴 폴더에서 최적 이미지 선택
3. FACE_SWAP_PROMPT        - 메인 생성 프롬프트 (얼굴만 교체)
4. VALIDATION_PROMPT       - step-by-step 검수 (CLAUDE.md VLM 규칙 준수)

VLM 프롬프트 작성 원칙 (CLAUDE.md 준수):
- 지시만 하지 말고 강제: [STEP 1], [STEP 2] ... 형식
- 출력 형식 명시: reason 필수 형식 지정
- 감점 계산 공식 명시: 같음(0) / 다름(-N) 형식
"""

# ============================================================
# 1. 소스 이미지 분석 프롬프트
# ============================================================

SOURCE_ANALYSIS_PROMPT = """소스 이미지를 분석해서 얼굴 스왑 시 보존해야 할 요소를 추출하세요.

다음 정보를 정확히 추출하여 JSON으로 출력하세요:

```json
{
  "face": {
    "position": {"x": 0.5, "y": 0.3},
    "angle": "3/4 left",
    "head_tilt": "slight left",
    "size_ratio": 0.25
  },
  "preserve_elements": {
    "pose": {
      "body_position": "standing, weight on right leg",
      "arm_left": "bent at elbow, hand on hip",
      "arm_right": "hanging naturally",
      "leg_position": "casual stance"
    },
    "outfit": {
      "description": "black oversized hoodie with white logo, wide leg jeans",
      "colors": ["black", "white", "light blue"],
      "style": "streetwear, casual"
    },
    "background": {
      "setting": "concrete wall, industrial",
      "color_tone": "cool gray",
      "lighting": "soft natural light from left"
    },
    "lighting": {
      "direction": "left side",
      "quality": "soft, diffused",
      "face_lighting": "even, no harsh shadows"
    }
  },
  "constraints": {
    "must_preserve": ["pose", "outfit", "background", "body_proportions"],
    "can_adapt": ["hair", "facial_expression"]
  }
}
```

주의:
- face.position: 정규화 좌표 (0.0~1.0), x=가로, y=세로
- face.angle: frontal / 3/4 left / 3/4 right / profile left / profile right
- face.size_ratio: 얼굴이 화면 전체에서 차지하는 비율 (0.0~1.0)
- JSON만 반환, 설명 없이
"""


# ============================================================
# 2. 얼굴 이미지 자동 선택 프롬프트
# ============================================================

FACE_SELECTION_PROMPT = """이 폴더의 얼굴 이미지들을 분석해서 AI 이미지 생성에 가장 적합한 1~2장을 선택해주세요.

선택 기준 (우선순위):
1. 정면 또는 살짝 측면 (3/4 뷰)
2. 조명이 균일하고 밝은 것
3. 표정이 자연스러운 것
4. 해상도가 높은 것
5. 얼굴이 화면의 50% 이상 차지하는 것

JSON 형식으로만 반환:
```json
{
  "selected_images": [
    {
      "filename": "파일명",
      "reason": "선택 이유",
      "face_angle": "정면/측면/3/4뷰",
      "quality_score": 8
    }
  ],
  "total_analyzed": 5
}
```

최대 2장만 선택하세요. 1장으로도 충분하면 1장만 선택하세요.
JSON만 반환, 설명 없이.
"""


# ============================================================
# 3. 메인 생성 프롬프트 (얼굴만 교체)
# ============================================================

FACE_SWAP_PROMPT = """[CRITICAL - IMAGE ROLE ASSIGNMENT]

You are receiving multiple images. Each has a SPECIFIC role:

IMAGE 1 (FIRST IMAGE): SOURCE - PRESERVE EVERYTHING EXCEPT FACE
- This is your PRIMARY reference
- PRESERVE the pose EXACTLY
- PRESERVE the outfit EXACTLY (colors, logos, all details)
- PRESERVE the background EXACTLY
- PRESERVE the body proportions EXACTLY
- PRESERVE the lighting direction and quality
- Do NOT use the face from this image

IMAGE 2-3: FACE REFERENCE - USE THIS FACE ONLY
- Use ONLY the face from these images
- Apply this face to the person in SOURCE image
- Match the face angle from SOURCE image
- Match the lighting from SOURCE image
- Adapt hair naturally to the new face

[FROM SOURCE IMAGE - COPY EXACTLY]
POSE:
{pose_description}

OUTFIT:
{outfit_description}

BACKGROUND:
{background_description}

LIGHTING:
{lighting_description}

[FACE SWAP INSTRUCTIONS]
- Replace ONLY the face with the provided face images
- Match the face angle from SOURCE ({face_angle})
- Keep the same face position ({face_position})
- Adapt hair naturally to match the new face
- Match skin tone to face reference
- Ensure lighting on face matches SOURCE lighting direction and quality

[CRITICAL CONSTRAINTS - MUST NOT CHANGE]
- DO NOT change pose
- DO NOT change outfit (colors, logos, style, any details)
- DO NOT change background
- DO NOT change body proportions or body type
- DO NOT change lighting direction
- ONLY change: face identity (who the person is)

[OUTPUT QUALITY]
- High-end professional photography quality
- Natural skin texture (no plastic/overly smooth appearance)
- Sharp focus on face
- Consistent lighting across entire image
- Clean edge between face and surrounding area, no artifacts
- Natural hair transition

CRITICAL REMINDERS:
1. Pose/outfit/background from IMAGE 1 ONLY (SOURCE)
2. Face from IMAGE 2-3 ONLY
3. Do NOT mix or alter preserved elements
4. Face swap should look completely natural and seamless
"""


# ============================================================
# 4. 검수 프롬프트 (CLAUDE.md VLM 규칙 준수 - step-by-step 형식)
# ============================================================

VALIDATION_PROMPT = """Face Swap 결과를 검수하세요.

수신 이미지:
- Image 1: 얼굴 참조 이미지 (교체된 얼굴의 원본 - ground truth)
- Image 2: 소스 이미지 (원본 포즈/착장/배경)
- Image 3: Face Swap 결과 이미지 (검수 대상)

아래 5개 기준을 순서대로 평가하세요.
각 기준마다 STEP을 반드시 따르세요. STEP을 건너뛰면 안됩니다.

---

### 1. face_identity (가중치 40%, 임계값 >= 95)
★★★ 얼굴 참조 이미지(Image 1)와 반드시 비교! ★★★

[STEP 1] 얼굴 참조(Image 1) 분석:
- REF 인물 특징 = ? (이목구비, 피부톤, 얼굴형)
- REF 얼굴 각도 = ?

[STEP 2] 결과물(Image 3) 얼굴 분석:
- GEN 인물 특징 = ?
- GEN 얼굴 각도 = ?

[STEP 3] 비교 및 감점:
- 동일 인물 여부: 같음(0) / 비슷하지만 다름(-20) / 완전히 다른 사람(-60)
- 얼굴 각도 불일치: 일치(0) / 약간 다름(-10) / 크게 다름(-20)
- 피부톤 불일치: 일치(0) / 다름(-10)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:이목구비특징+피부톤, GEN:이목구비특징+피부톤, 감점:-N"

---

### 2. pose_preservation (가중치 25%, 임계값 >= 95)
★★★ 소스 이미지(Image 2)와 반드시 비교! ★★★

[STEP 1] 소스(Image 2) 포즈 분석:
- SRC 몸 위치 = ?
- SRC 팔 위치 = ?
- SRC 다리 위치 = ?

[STEP 2] 결과물(Image 3) 포즈 분석:
- GEN 몸 위치 = ?
- GEN 팔 위치 = ?
- GEN 다리 위치 = ?

[STEP 3] 비교 및 감점:
- 몸 위치: 일치(0) / 약간 다름(-15) / 크게 다름(-40)
- 팔 위치: 일치(0) / 다름(-15)
- 다리 위치: 일치(0) / 다름(-15)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:포즈설명, GEN:포즈설명, 감점:-N"

---

### 3. outfit_preservation (가중치 20%, 임계값 >= 95)
★★★ 소스 이미지(Image 2)와 반드시 비교! ★★★

[STEP 1] 소스(Image 2) 착장 분석:
- SRC 착장 아이템 = ? (상의, 하의, 신발 등)
- SRC 색상 = ?
- SRC 로고/디테일 = ?

[STEP 2] 결과물(Image 3) 착장 분석:
- GEN 착장 아이템 = ?
- GEN 색상 = ?
- GEN 로고/디테일 = ?

[STEP 3] 비교 및 감점:
- 아이템 누락: 없음(0) / 일부 누락(-30) / 전체 변경(-80)
- 색상 불일치: 일치(0) / 약간 다름(-10) / 크게 다름(-30)
- 로고 불일치: 일치(0) / 다름(-15)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:착장설명, GEN:착장설명, 감점:-N"

---

### 4. lighting_consistency (가중치 10%, 임계값 >= 80)
얼굴의 조명이 소스 이미지(Image 2)의 전체 조명과 일치하는지 확인.

[STEP 1] 소스(Image 2) 조명 분석:
- SRC 광원 방향 = ?
- SRC 조명 성질 = ? (소프트/하드)

[STEP 2] 결과물(Image 3) 얼굴 조명 분석:
- GEN 광원 방향 = ?
- GEN 조명 성질 = ?

[STEP 3] 비교 및 감점:
- 광원 방향 불일치: 일치(0) / 약간 다름(-10) / 크게 다름(-25)
- 조명 성질 불일치: 일치(0) / 다름(-15)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:광원방향+성질, GEN:광원방향+성질, 감점:-N"

---

### 5. edge_quality (가중치 5%, 임계값 >= 80)
얼굴 경계 품질 및 아티팩트 확인. 소스 이미지와 비교 불필요, 결과물(Image 3)만 판단.

[STEP 1] 경계 영역 확인:
- 얼굴-머리카락 경계 = ?
- 얼굴-배경/의상 경계 = ?

[STEP 2] 아티팩트 확인:
- 글로우/달무리 = ? (있음/없음)
- 색상 번짐 = ? (있음/없음)
- 피부톤 경계 불일치 = ? (있음/없음)

[STEP 3] 감점 계산:
- 경계 품질 나쁨: 없음(0) / 약간(-10) / 심각(-30)
- 글로우/달무리: 없음(0) / 있음(-15)
- 색상 번짐: 없음(0) / 있음(-10)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "경계품질:설명, 아티팩트:설명, 감점:-N"

---

### Auto-Fail 조건 확인

다음 중 해당하는 항목 모두 체크:
- face_identity < 80: 완전히 다른 사람 → auto_fail
- 포즈 변경됨 (팔/다리 위치 다름): → auto_fail
- 착장 변경됨 (색상/로고/스타일 다름): → auto_fail
- 배경 변경됨: → auto_fail
- 손가락 6개 이상: → auto_fail
- 누런 톤 (golden/amber cast): → auto_fail

---

## 출력 (JSON만 반환)

```json
{
  "face_identity": {
    "score": 95,
    "reason": "REF:이목구비특징+피부톤, GEN:이목구비특징+피부톤, 감점:-5"
  },
  "pose_preservation": {
    "score": 98,
    "reason": "SRC:포즈설명, GEN:포즈설명, 감점:-2"
  },
  "outfit_preservation": {
    "score": 100,
    "reason": "SRC:착장설명, GEN:착장설명, 감점:0"
  },
  "lighting_consistency": {
    "score": 90,
    "reason": "SRC:광원방향+성질, GEN:광원방향+성질, 감점:-10"
  },
  "edge_quality": {
    "score": 92,
    "reason": "경계품질:깨끗함, 아티팩트:없음, 감점:-8"
  },
  "auto_fail": false,
  "auto_fail_reasons": []
}
```

JSON만 반환. 설명 없이.
"""
