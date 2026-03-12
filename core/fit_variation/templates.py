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
FIT_VALIDATION_PROMPT = """두 이미지를 비교하세요.
IMAGE 1: 원본 바지 (참조)
IMAGE 2: 핏 변형 결과

다음 기준으로 평가하세요:

[STEP 1] 색상 보존 (color_preservation):
- 원본 색상 = ?
- 결과 색상 = ?
- 색상이 동일한가? (동일=100, 약간 다름=70, 많이 다름=30, 완전 다름=0)

[STEP 2] 실루엣 정확도 (silhouette_accuracy):
- 목표 핏: {target_fit}
- 결과 실루엣이 목표 핏과 일치하는가? (정확=100, 유사=80, 약간 다름=60, 다름=30)

[STEP 3] 소재 충실도 (material_fidelity):
- 원본 소재 질감 = ?
- 결과 소재 질감 = ?
- 소재/질감이 보존되었는가? (동일=100, 유사=80, 다름=50)

[STEP 4] 디테일 보존 (detail_preservation):
- 원본 디테일 (포켓/스티칭/로고/허리밴드) = ?
- 결과 디테일 = ?
- 디테일이 보존되었는가? (모두보존=100, 대부분=80, 일부누락=60, 많이누락=30)

[STEP 5] 전체 품질 (overall_quality):
- 이미지 품질, 자연스러움, 완성도 (100~0)

JSON 형식으로 출력:
```json
{
    "color_preservation": 점수,
    "color_reason": "REF:색상, GEN:색상, 차이:설명",
    "silhouette_accuracy": 점수,
    "silhouette_reason": "목표:핏, GEN:실제핏, 차이:설명",
    "material_fidelity": 점수,
    "material_reason": "REF:소재, GEN:소재, 차이:설명",
    "detail_preservation": 점수,
    "detail_reason": "보존:목록, 누락:목록",
    "overall_quality": 점수,
    "overall_reason": "설명"
}
```

JSON만 출력하세요."""
