"""
이커머스 VLM 프롬프트 템플릿 모듈

SKILL.md 기반 프롬프트 3종:
1. OUTFIT_ANALYSIS_PROMPT  - 착장 상세 분석 (AI가 놓치기 쉬운 디테일 추출)
2. ECOMMERCE_GENERATION_PROMPT - 이커머스 모델 이미지 생성 지시문
3. VALIDATION_PROMPT        - Step-by-step VLM 검수 (CLAUDE.md 원칙 준수)

VLM 검수 프롬프트 작성 원칙 (CLAUDE.md):
- 단순 지시 대신 STEP-BY-STEP 출력 강제
- reason 필드 출력 형식 명시
- 감점 계산 공식 명시
"""

# ------------------------------------------------------------------
# 1. 착장 분석 프롬프트 (VLM → 이미지 생성 입력용)
# ------------------------------------------------------------------
OUTFIT_ANALYSIS_PROMPT = """
착장 이미지를 분석하여 AI가 놓치기 쉬운 디테일을 추출하세요.

이커머스 모델 이미지의 핵심은 **착장을 정확히 보여주는 것**입니다.
색상, 로고, 실루엣, 부자재를 빠짐없이 기록해야 합니다.

[STEP 1] 각 아이템별 분석:
- 변형된 실루엣: 벌룬핏, 비대칭 커팅, 익스트림 크롭, 오버사이즈, 슬림핏
- 미세 부자재: 배색 스티치, 단추, 지퍼, 디테일 장식
- 로고/그래픽 위치: 정확한 상대적 좌표 (예: "왼쪽 가슴, 어깨에서 10cm 아래")
- 소재 질감: 코튼, 니트, 데님, 레더, 나일론, 실크 등
- 색상: 정확한 색상 표현 (예: "다크 네이비", "크림 화이트", "머스타드 옐로우")

[STEP 2] 전체 착장 구성 파악:
- 아우터 + 상의 + 하의 + 신발 + 액세서리 전체

[STEP 3] 핵심 디테일 목록화:
- 생성 AI가 자주 놓치는 요소 3-5개 명시

JSON 형식으로 출력 (한국어 설명 포함):
{
  "outer": {"item": "", "color": "", "details": [], "logo_position": ""},
  "top": {"item": "", "color": "", "details": [], "logo_position": ""},
  "bottom": {"item": "", "color": "", "details": []},
  "shoes": {"item": "", "color": ""},
  "accessories": [],
  "overall_style": "",
  "key_details": []
}
"""


# ------------------------------------------------------------------
# 2. 이커머스 생성 프롬프트 (템플릿 - 실제 사용시 변수 치환)
# ------------------------------------------------------------------
ECOMMERCE_GENERATION_PROMPT = """
이커머스 상품 상세페이지용 모델 이미지를 생성하세요.

## 우선순위 (반드시 준수)

1. **착장 정확도 (최우선)**
   - 착장 이미지의 색상, 로고, 디테일, 실루엣을 pixel-perfect로 재현
   - 착장 이미지의 모든 아이템 (아우터, 상의, 하의, 신발, 액세서리) 포함
   - 단 하나의 착장 요소도 누락하거나 변형하지 말 것

2. **상업적 품질**
   - 프로페셔널한 스튜디오 조명
   - 클린하고 깔끔한 배경
   - 완벽한 포즈와 구도

3. **얼굴 동일성**
   - 얼굴 참조 이미지와 유사한 얼굴
   - (브랜드컷보다 낮은 우선순위 - 착장이 더 중요)

## 모델 설정

{
  "model": {
    "face": "similar to provided face reference image",
    "expression": "natural, approachable, looking at camera",
    "skin": "clean, natural skin tone"
  },
  "outfit": {
    "instruction": "CRITICAL: Copy ALL outfit elements from reference images exactly. NO color change, NO logo modification, NO detail omission.",
    "outer": "{{outfit_analysis.outer}}",
    "top": "{{outfit_analysis.top}}",
    "bottom": "{{outfit_analysis.bottom}}",
    "shoes": "{{outfit_analysis.shoes}}",
    "accessories": "{{outfit_analysis.accessories}}"
  },
  "pose": {
    "stance": "{{pose_preset.pose_desc}}",
    "framing": "{{pose_preset.framing}}",
    "angle": "{{pose_preset.angle}}"
  },
  "camera": {
    "lens": "{{pose_preset.lens}}",
    "height": "{{pose_preset.height}}",
    "lighting": "{{background_preset.lighting}}"
  },
  "background": {
    "location": "{{background_preset.location}}",
    "ambient": "{{background_preset.ambient}}",
    "mood": "{{background_preset.mood}}"
  },
  "forbidden": [
    "AI plastic skin appearance",
    "Over-retouched look",
    "Outfit color change",
    "Missing outfit details",
    "Logo distortion or removal",
    "6+ fingers or deformed hands",
    "Unintended text or watermarks",
    "Golden/amber/warm color cast",
    "Brand-specific conceptual background"
  ]
}
"""


# ------------------------------------------------------------------
# 3. 검수 프롬프트 (VLM - STEP-BY-STEP 강제, CLAUDE.md 원칙 준수)
# ------------------------------------------------------------------
VALIDATION_PROMPT = """
이커머스 모델 이미지를 단계별로 평가하세요.
각 STEP의 출력을 건너뛰지 말고 반드시 작성하세요.

## 평가 기준

| 기준 | 비중 | Pass 기준 |
|------|------|----------|
| outfit_accuracy | 40% | >= 85 (최우선) |
| background_compliance | 15% | >= 90 (중립 배경 필수) |
| pose_correctness | 15% | >= 80 |
| face_identity | 20% | >= 70 (이커머스 완화 기준) |
| commercial_quality | 10% | >= 85 |

---

### 1. outfit_accuracy [OUTFIT REFERENCE]와 반드시 비교

[STEP 1] OUTFIT REFERENCE 분석:
- REF 아이템 목록 = ?
- REF 핵심 색상 = ?
- REF 로고/그래픽 = ?

[STEP 2] GENERATED IMAGE 분석:
- GEN 아이템 목록 = ?
- GEN 색상 일치 여부 = ?
- GEN 로고/그래픽 = ?

[STEP 3] 누락/불일치 항목 목록:
- 아이템 누락: 있음(-30) / 없음(0)
- 색상 불일치: 있음(-25) / 없음(0)
- 로고 변형/누락: 있음(-20) / 없음(0)
- 디테일 누락: 있음(-10) / 없음(0)
- 합계 감점 = ?

[STEP 4] outfit_accuracy 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:아이템목록, GEN:아이템목록, 누락:항목, 감점:-N"

---

### 2. background_compliance 배경 중립성 확인

[STEP 1] 배경 유형 판정:
- white_studio / gray_studio / minimal_indoor / outdoor_urban / 기타

[STEP 2] 이커머스 허용 배경 여부:
- 허용(0) / 브랜드 특화 배경(-30) / 복잡한 배경(-20) / 과도한 소품(-15)

[STEP 3] 배경 조명/품질:
- 스튜디오급 조명(0) / 조명 부자연스러움(-10)
- 합계 감점 = ?

[STEP 4] background_compliance 최종 점수 = 100 - 합계 감점

reason 필수 형식: "BG타입:white_studio, 품질:정상, 감점:-N"

---

### 3. pose_correctness 포즈 검수

[STEP 1] 요청 포즈 분석:
- REF 프레이밍(FS/MS) = ?
- REF 각도(front/side/back) = ?

[STEP 2] GENERATED IMAGE 분석:
- GEN 프레이밍 = ?
- GEN 각도 = ?

[STEP 3] 감점:
- 프레이밍 불일치: 같음(0) / 다름(-20)
- 각도 불일치: 같음(0) / 다름(-20)
- 해부학적 문제(손가락/관절): 없음(0) / 있음(-15)
- 합계 감점 = ?

[STEP 4] pose_correctness 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:FS+front, GEN:FS+front, 해부학:정상, 감점:-N"

---

### 4. face_identity 얼굴 동일성

[STEP 1] FACE REFERENCE 특징:
- 얼굴형, 피부톤, 주요 특징 = ?

[STEP 2] GENERATED IMAGE 얼굴:
- 동일 인물 여부 = ?
- 유사도 = ?

[STEP 3] 감점:
- 완전히 다른 사람(-30) / 유사하나 차이있음(-10) / 매우 유사(0)
- AI 플라스틱 피부(-15) / 정상(0)
- 합계 감점 = ?

[STEP 4] face_identity 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF특징:타원형+밝은피부, GEN:유사, 감점:-N"

---

### 5. commercial_quality 상업적 품질

[STEP 1] 조명 품질 평가:
- 프로페셔널 스튜디오급(0) / 부자연스러운 그림자(-15) / 조명 부족(-15)

[STEP 2] 전체 상업적 완성도:
- 이커머스 사용 가능(0) / 보정 필요(-10) / 사용 불가(-25)

[STEP 3] 합계 감점 = ?

[STEP 4] commercial_quality 최종 점수 = 100 - 합계 감점

reason 필수 형식: "조명:정상, 완성도:양호, 감점:-N"

---

## Auto-Fail 조건 (즉시 재생성, 이하 중 하나라도 해당 시)

- outfit_accuracy < 70 (착장 심각 불일치)
- 로고 완전 누락 또는 브랜드명 변형
- 손가락 6개 이상 / 기형적 손발
- 완전히 다른 사람 (face_identity < 40)
- 누런 톤 (golden/amber/warm cast)
- 의도하지 않은 텍스트/워터마크

---

## 최종 결과 JSON 출력

{
  "outfit_accuracy": 0,
  "background_compliance": 0,
  "pose_correctness": 0,
  "face_identity": 0,
  "commercial_quality": 0,
  "total_score": 0,
  "auto_fail": false,
  "auto_fail_reason": "",
  "passed": false,
  "issues": [],
  "reasons": {
    "outfit_accuracy": "",
    "background_compliance": "",
    "pose_correctness": "",
    "face_identity": "",
    "commercial_quality": ""
  }
}

총점 계산식:
total_score = outfit_accuracy * 0.40 + face_identity * 0.20 + background_compliance * 0.15 + pose_correctness * 0.15 + commercial_quality * 0.10

Pass 조건 (AND):
- outfit_accuracy >= 85
- background_compliance >= 90
- pose_correctness >= 80
- face_identity >= 70
- commercial_quality >= 85
- total_score >= 85
- auto_fail == false
"""


__all__ = [
    "OUTFIT_ANALYSIS_PROMPT",
    "ECOMMERCE_GENERATION_PROMPT",
    "VALIDATION_PROMPT",
]
