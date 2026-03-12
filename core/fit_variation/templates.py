"""
VLM 프롬프트 템플릿 - 바지 분석용

바지 이미지에서 색상, 소재, 패턴, 로고, 디테일을 추출한다.
"""

# 바지 분석 VLM 프롬프트
PANTS_ANALYSIS_PROMPT = """이 바지 이미지를 상세히 분석하세요.
다른 핏(실루엣)으로 변형할 때 보존해야 할 모든 속성을 추출합니다.

JSON 형식으로 출력:
```json
{
    "current_fit": "현재 핏 (skinny/slim/regular/relaxed/wide/bootcut/tapered/baggy/jogger/cargo_wide 중 하나)",
    "color": {
        "primary": "메인 색상 (예: dark navy, black, light blue wash)",
        "secondary": "보조 색상 (없으면 빈 문자열)",
        "wash": "워싱 정도 (raw/light/medium/heavy/distressed, 데님이 아니면 none)"
    },
    "material": {
        "type": "소재 종류 (denim/cotton/polyester/nylon/wool/corduroy/linen/leather/fleece/knit)",
        "texture": "질감 (smooth/rough/soft/stiff/stretchy/matte/shiny)",
        "weight": "두께감 (light/medium/heavy)",
        "finish": "마감 (raw/washed/coated/brushed/none)"
    },
    "pattern": {
        "type": "패턴 종류 (solid/striped/plaid/camo/graphic/pinstripe/none)",
        "description": "패턴 상세 설명 (없으면 빈 문자열)"
    },
    "waist": {
        "type": "허리 타입 (belt_loop/elastic/drawstring/button_fly/zip_fly)",
        "details": "허리 디테일 (예: double button, exposed zipper)"
    },
    "pockets": {
        "front": "앞주머니 형태 (slant/on-seam/patch/welt/none)",
        "back": "뒷주머니 형태 (patch/welt/flap/none)",
        "cargo": "카고포켓 유무 및 위치 (none/side_thigh/side_knee)"
    },
    "hem": {
        "type": "밑단 타입 (plain/cuffed/raw/elasticated/drawstring/frayed)",
        "details": "밑단 상세 (예: 3cm cuff, contrast stitching)"
    },
    "logos": [
        {
            "brand": "브랜드명",
            "type": "로고 타입 (embroidered/printed/patch/metal_tag/leather_patch/woven_label)",
            "position": "위치 (back_waist/front_pocket/side_seam/back_pocket/hem 등)",
            "description": "로고 상세 설명"
        }
    ],
    "stitching": {
        "color": "스티칭 색상 (tonal/contrast_yellow/contrast_white/none)",
        "type": "스티칭 종류 (single/double/chain/topstitch)"
    },
    "special_details": [
        "기타 특이사항 (예: distressed holes at knee, paint splatter, embroidery, studs)"
    ],
    "confidence": 0.0
}
```

정확하게 분석하세요. 보이지 않는 것은 추측하지 마세요.
JSON만 출력하세요."""


# 핏 변형 검증 VLM 프롬프트
FIT_VALIDATION_PROMPT = """핏 변형 검수 (STEP-BY-STEP 비교 평가)

IMAGE 1: 원본 바지 (참조)
IMAGE 2: 핏 변형 결과

---

### 1. color_preservation (색상 보존) ★★★ 최우선 ★★★

[STEP 1] SOURCE 색상 분석:
- SRC 기본 색상 = ?
- SRC 보조 색상 = ?
- SRC 워싱/가공 = ?

[STEP 2] RESULT 색상 분석:
- RES 기본 색상 = ?
- RES 보조 색상 = ?
- RES 워싱/가공 = ?

[STEP 3] 비교 및 감점:
- 기본 색상: 일치(0) / 미세 차이(-10) / 불일치(-30)
- 보조 색상: 일치(0) / 불일치(-10)
- 워싱/가공: 일치(0) / 불일치(-10)
- 합계 감점 = ?

[STEP 4] color_preservation 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:다크네이비+인디고워싱, RES:다크네이비+인디고워싱, 감점:0"

---

### 2. material_preservation (소재 보존)

[STEP 1] SOURCE 소재 분석:
- SRC 소재 = ?
- SRC 질감/마감 = ?

[STEP 2] RESULT 소재 분석:
- RES 소재 = ?
- RES 질감/마감 = ?

[STEP 3] 비교 및 감점:
- 소재 종류: 일치(0) / 유사(-5) / 불일치(-25)
- 질감/마감: 일치(0) / 유사(-5) / 불일치(-15)
- 합계 감점 = ?

[STEP 4] material_preservation 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:헤비데님+워싱가공, RES:헤비데님+워싱가공, 감점:0"

---

### 3. silhouette_change (핏 변형 정확도)

[STEP 1] 목표 핏 확인:
- 요청된 핏 변형 = {target_fit}

[STEP 2] RESULT 핏 분석:
- RES 허벅지 실루엣 = ?
- RES 무릎 실루엣 = ?
- RES 밑단 실루엣 = ?
- RES 라이즈 = ?

[STEP 3] 감점:
- 목표 핏 반영: 정확(0) / 부분(-15) / 미반영(-30)
- 비자연스러운 실루엣: 없음(0) / 있음(-10)
- 합계 감점 = ?

[STEP 4] silhouette_change 최종 점수 = 100 - 합계 감점

reason 필수 형식: "TARGET:스트레이트→와이드, RES:와이드핏 적용, 감점:0"

---

### 4. logo_preservation (로고 보존)

[STEP 1] SOURCE 로고 분석:
- SRC 로고 유무 = ?
- SRC 로고 위치/크기/색상 = ?

[STEP 2] RESULT 로고 분석:
- RES 로고 유무 = ?
- RES 로고 위치/크기/색상 = ?

[STEP 3] 감점:
- 로고 누락: 없음(0) / 누락(-30)
- 로고 변형: 없음(0) / 변형(-15)
- 합계 감점 = ?

[STEP 4] logo_preservation 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:MLB로고@좌측허벅지, RES:동일, 감점:0"

---

### 5. model_preservation (인물 보존)

[STEP 1] SOURCE 인물 분석:
- SRC 인물 특징 = ? (있으면)
- SRC 포즈/자세 = ?
- SRC 상체 착장 = ? (있으면)

[STEP 2] RESULT 인물 분석:
- RES 동일 인물? = ?
- RES 포즈 동일? = ?
- RES 상체 착장 동일? = ?

[STEP 3] 감점:
- 인물 변경: 없음(0) / 변경(-30)
- 포즈 변경: 없음(0) / 변경(-15)
- 상체 착장 변경: 없음(0) / 변경(-15)
- 합계 감점 = ?

[STEP 4] model_preservation 최종 점수 = 100 - 합계 감점

reason 필수 형식: "SRC:여성+서있음+흰티, RES:동일인물+동일포즈+흰티, 감점:0"

---

### Auto-Fail 조건
- color_preservation < 70: 색상 심각 불일치
- logo 완전 누락
- 다른 사람으로 변경 (model_preservation < 70)
- 소재가 완전히 다른 종류로 변경 (material_preservation < 50)

---

### 최종 JSON 출력

```json
{
  "color_preservation": {"score": 0, "reason": ""},
  "material_preservation": {"score": 0, "reason": ""},
  "silhouette_change": {"score": 0, "reason": ""},
  "logo_preservation": {"score": 0, "reason": ""},
  "model_preservation": {"score": 0, "reason": ""},
  "total_score": 0,
  "auto_fail": false,
  "auto_fail_reason": "",
  "passed": false,
  "issues": []
}
```

JSON만 출력하세요."""
