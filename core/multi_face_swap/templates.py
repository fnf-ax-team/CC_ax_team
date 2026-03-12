"""
다중 얼굴 교체 VLM 프롬프트 템플릿

세 가지 프롬프트를 제공한다:
1. FACE_DETECTION_PROMPT   — 단체 사진에서 모든 인물 감지 및 설명
2. MULTI_FACE_SWAP_PROMPT  — 여러 얼굴을 동시에 교체하는 생성 지시 (동적 빌드 함수 포함)
3. VALIDATION_PROMPT       — 교체 결과 검증 (위치/동일성/보존)

VLM 프롬프트 작성 원칙 (CLAUDE.md):
- 비교 요청은 step-by-step 형식으로 강제
- 출력 형식 명시 (reason 필드)
- 계산 공식 명시
"""


# =============================================================================
# 1. 인물 감지 프롬프트 (FACE_DETECTION_PROMPT)
# =============================================================================

FACE_DETECTION_PROMPT = """
이 단체 사진에서 모든 인물을 감지하고 각 인물의 위치와 특징을 분석하세요.

규칙:
1. 모든 인물을 왼쪽에서 오른쪽 순서로 ID 부여
2. bbox는 정규화된 좌표 (0.0 ~ 1.0)
3. clothing_hint는 사용자가 인물을 구분할 수 있는 구체적 특징 (색상+아이템)
4. face_angle은 정확히 파악 (각 얼굴마다 다를 수 있음)
5. 부분적으로 가려진 인물도 포함

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "total_persons": <정수>,
  "persons": [
    {
      "id": 1,
      "position": "left",
      "bbox": {
        "x1": 0.1,
        "y1": 0.2,
        "x2": 0.3,
        "y2": 0.8
      },
      "face_angle": "frontal",
      "clothing_hint": "빨간 재킷",
      "hair_hint": "긴 검은 머리",
      "distinguishing_features": "안경 착용"
    }
  ],
  "group_arrangement": "horizontal line",
  "overall_composition": "casual group shot"
}

position 허용값: "left", "center-left", "center", "center-right", "right"
face_angle 허용값: "frontal", "3/4 left", "3/4 right", "profile left", "profile right"
group_arrangement 허용값: "horizontal line", "staggered", "clustered", "v-shape", "arc"
"""


# =============================================================================
# 2. 다중 얼굴 교체 프롬프트 빌더 (MULTI_FACE_SWAP_PROMPT)
# =============================================================================


def build_multi_face_swap_prompt(persons_info: dict, face_mappings: dict) -> str:
    """다중 얼굴 교체 프롬프트 동적 생성

    Args:
        persons_info: FACE_DETECTION_PROMPT 분석 결과 딕셔너리
            예: {"total_persons": 4, "persons": [...], "group_arrangement": "..."}
        face_mappings: {person_id: face_folder_path} 형태의 매핑
            예: {1: "D:\\faces\\alice", 2: "D:\\faces\\bob"}

    Returns:
        str: 완성된 다중 얼굴 교체 프롬프트
    """
    total = persons_info.get("total_persons", len(persons_info.get("persons", [])))
    persons = persons_info.get("persons", [])

    # 인물별 매핑 설명 생성
    mapping_lines = []
    for person in persons:
        pid = person["id"]
        pos = person.get("position", "unknown")
        clothing = person.get("clothing_hint", "")
        features = person.get("distinguishing_features", "")
        desc = f"{pos}, {clothing}"
        if features and features != "없음":
            desc += f", {features}"
        mapping_lines.append(
            f"  PERSON_{pid} ({desc}): Use face from PERSON_{pid} reference images"
        )

    mapping_text = "\n".join(mapping_lines)

    # 안전 가드: persons 리스트가 비어있을 때 대비
    def _safe_person_position(idx: int) -> str:
        if idx < len(persons):
            return persons[idx].get("position", f"position_{idx+1}")
        return f"position_{idx+1}"

    # 위치 주석 (최대 10명까지) — x좌표 추정 포함
    # 인물을 왼쪽부터 오른쪽으로 균등 분배하여 x좌표를 추정한다
    # 예: 3명 → x≈0.2, 0.5, 0.8 / 4명 → x≈0.1, 0.4, 0.6, 0.9
    n = len(persons[:10])
    position_notes = []
    for i, person in enumerate(persons[:10]):
        pid = person["id"]
        pos = person.get("position", "")
        if n <= 1:
            x_coord = 0.5
        else:
            # 전체 프레임 너비(0.0~1.0) 내에서 균등 분배, 좌우 여백 0.1 적용
            x_coord = round(0.1 + (i / (n - 1)) * 0.8, 2)
        position_notes.append(
            f"  - PERSON_{pid} reference images → person at {pos} position (x≈{x_coord} of frame width)"
        )
    position_notes_text = "\n".join(position_notes)

    prompt = f"""[CRITICAL - MULTI-FACE SWAP INSTRUCTION]

You are receiving a GROUP PHOTO with {total} people.
Replace each person's face with the corresponding reference face.

=== IMAGE ROLE ASSIGNMENT — CRITICAL ===

IMAGE 1 (SOURCE): Group photo — PRESERVE EVERYTHING EXCEPT FACES
- PRESERVE all poses EXACTLY — every person's body position unchanged
- PRESERVE all outfits EXACTLY — colors, logos, details, fit unchanged
- PRESERVE the background EXACTLY — no modification
- PRESERVE all body proportions EXACTLY — no resizing
- PRESERVE the group arrangement EXACTLY — nobody moves position
- PRESERVE the lighting direction and quality
- Do NOT use any faces from this image

IMAGE 2+: FACE REFERENCE images for each person (PERSON_1, PERSON_2, ...)
- Use ONLY the face identity from each reference
- Do NOT use pose, outfit, or background from reference images

=== FACE MAPPING ===
{mapping_text}

=== IMAGE TO PERSON MAPPING ===
{position_notes_text}

=== WHAT TO PRESERVE (ABSOLUTE — NO EXCEPTIONS) ===
- Body poses: PIXEL-LOCKED for each person — exact joint angles, weight distribution
- Clothing: PIXEL-LOCKED for each person — exact colors, logos, patterns, fit
- Body proportions and silhouettes: PIXEL-LOCKED — no resizing, no reshaping
- Group arrangement and spacing: PIXEL-LOCKED — exact relative positions
- Background: PIXEL-LOCKED — zero modifications
- Lighting direction and intensity: PIXEL-LOCKED — consistent across all persons
- Relative positions of all persons: PIXEL-LOCKED — NO position swaps
- Camera angle and framing: PIXEL-LOCKED

=== WHAT TO CHANGE ===
- ONLY: Each person's face, replaced with the corresponding PERSON_N reference face
- Nothing else. Zero other changes.

=== CRITICAL ANTI-DRIFT WARNING ===
Face reference images show faces on different people with different poses.
IGNORE ALL POSES in face reference images.
IGNORE ALL OUTFITS in face reference images.
IGNORE ALL BACKGROUNDS in face reference images.
Extract ONLY the face identity from each reference image.

=== CRITICAL RULES (VIOLATION = FAILURE) ===
1. NEVER swap positions — person on left stays on left, right stays on right
2. NEVER mix up face assignments — PERSON_1 face goes to PERSON_1 position ONLY
3. NEVER change any clothing — not even slightly
4. NEVER change any pose — not even slightly
5. NEVER change the background — not even slightly
6. NEVER resize or reposition any person
7. Natural neck/face boundary blending for all faces — seamless transition
8. Consistent lighting/skin tone matching on all replaced faces
9. Maintain face angle appropriate for each person's body pose
10. No AI artifacts on any face
11. Natural group photo appearance — all faces must look cohesive together

=== OUTPUT ===
Produce a single high-quality group photo with all {total} faces swapped accurately.
Everything except the faces must be pixel-perfect preserved.

DO NOT:
- Change any clothing
- Change any poses
- Move any person to a different position
- Alter the background
- Mix up face assignments between persons
- Add or remove any persons
- Add watermarks or text
"""

    return prompt.strip()


# =============================================================================
# 3. 검증 프롬프트 (VALIDATION_PROMPT)
# =============================================================================

VALIDATION_PROMPT = """
두 이미지를 비교하여 다중 얼굴 교체가 정확히 수행되었는지 검증하세요.

Image 1: SOURCE — 원본 단체 사진 (비교 기준)
Image 2: RESULT — 얼굴 교체 결과 이미지
Image 3+: 각 인물의 참조 얼굴 이미지 (PERSON_1, PERSON_2, ...)

============================================================
검증 지시 — 반드시 아래 STEP을 순서대로 수행하고 각 STEP 결과를 기록하세요.
============================================================

[STEP 1] SOURCE 분석
- 인물 수: ?명
- 각 인물 위치 (왼쪽→오른쪽): ?
- 각 인물 착장 요약: ?
- 전체 구도: ?

[STEP 2] RESULT 분석
- 인물 수: ?명
- 각 인물 위치 (왼쪽→오른쪽): ?
- 각 인물 착장 요약: ?
- 착장 변경 여부: ?
- 포즈 변경 여부: ?

[STEP 3] 인물 수 및 위치 비교
- 인물 수 일치: 같음(0) / 다름(Auto-Fail)
- 위치 순서 일치: 모두 같음(0) / 뒤바뀜(Auto-Fail)
- 착장 보존: 모두 유지(0) / 변경됨(-20 per person)
- 포즈 보존: 유지(0) / 변경(-20 per person)
- 소계 감점 = ?

[STEP 4] 각 인물 얼굴 동일성 평가
각 인물별로 참조 얼굴과 결과 이미지의 얼굴을 비교:
- PERSON_1: 동일 인물 여부, 점수(0-100)
- PERSON_2: 동일 인물 여부, 점수(0-100)
- PERSON_3: 동일 인물 여부, 점수(0-100)
(존재하는 인물 수만큼 반복)
- 최저 얼굴 동일성 점수 = ?

[STEP 5] 가중 점수 계산
- all_faces_identity (40%): 모든 얼굴 동일성 평균 = ?
- face_consistency (20%): 얼굴들이 자연스럽게 어울리는가 (0-100) = ?
- pose_preservation (20%): 포즈 보존 점수 (0-100) = ?
- outfit_preservation (15%): 착장 보존 점수 (0-100) = ?
- edge_quality (5%): 얼굴 경계 품질 (0-100) = ?
- 총점 = (all_faces_identity * 0.40) + (face_consistency * 0.20) + (pose_preservation * 0.20) + (outfit_preservation * 0.15) + (edge_quality * 0.05)

[STEP 6] Auto-Fail 체크
다음 중 하나라도 해당하면 auto_fail=true:
- 인물 수 불일치 (SOURCE vs RESULT)
- 위치 뒤바뀜 (어느 한 명이라도)
- 얼굴 동일성 < 80 (어느 한 명이라도)
- 착장 변경됨 (어느 한 명이라도)
- 체형 변경됨

[STEP 7] JSON 출력
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "step1_source": {
    "person_count": <정수>,
    "positions": ["left", "center", "right"],
    "outfits_summary": ["빨간 재킷", "흰 티셔츠"],
    "composition": "수평 일렬"
  },
  "step2_result": {
    "person_count": <정수>,
    "positions": ["left", "center", "right"],
    "outfits_summary": ["빨간 재킷", "흰 티셔츠"],
    "clothing_changed": false,
    "pose_changed": false
  },
  "step3_comparison": {
    "person_count_match": true,
    "position_order_match": true,
    "outfit_preserved": true,
    "pose_preserved": true,
    "subtotal_penalty": 0,
    "reason": "SOURCE:4명 수평배치, RESULT:4명 동일배치, 감점:0"
  },
  "step4_face_identities": [
    {"person": 1, "position": "left", "score": 96, "match": true, "reason": "REF:동일인물, GEN:일치"},
    {"person": 2, "position": "center-left", "score": 94, "match": true, "reason": "REF:동일인물, GEN:일치"},
    {"person": 3, "position": "center-right", "score": 95, "match": true, "reason": "REF:동일인물, GEN:일치"},
    {"person": 4, "position": "right", "score": 97, "match": true, "reason": "REF:동일인물, GEN:일치"}
  ],
  "step5_scores": {
    "all_faces_identity": 95,
    "face_consistency": 92,
    "pose_preservation": 98,
    "outfit_preservation": 99,
    "edge_quality": 88,
    "total_score": 94
  },
  "step6_auto_fail": {
    "auto_fail": false,
    "reasons": []
  },
  "passed": true,
  "issues": [],
  "summary_kr": "4명 단체 사진 다중 얼굴 교체 완료. 모든 얼굴 동일성 90점 이상, 포즈/착장 보존 정상."
}

Pass 기준:
- auto_fail = false
- all_faces_identity >= 90 (모든 인물)
- face_consistency >= 85
- pose_preservation >= 95
- outfit_preservation >= 95
- edge_quality >= 80
- total_score >= 92
"""
