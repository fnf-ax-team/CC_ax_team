# 배경교체 (Background Swap)

> 인물과 오브젝트는 그대로, 배경만 교체

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Background Swap Workflow                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   INPUT      │     │   ANALYZE    │     │   GENERATE   │     │   VALIDATE   │
│              │     │              │     │              │     │              │
│ Source Image │────>│ VFX Physics  │────>│ Style        │────>│ 9-Criteria   │
│ Background   │     │ Source Type  │     │ Transform    │     │ Check        │
│ Style        │     │ Swap Analysis│     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                       │
                                          ┌────────────────────────────┘
                                          │
                                          v
                           ┌─────────────────────────────┐
                           │      PASS (≥95점)?          │
                           └─────────────────────────────┘
                                    │           │
                              YES   │           │ NO
                                    v           v
                           ┌───────────┐  ┌───────────────┐
                           │  OUTPUT   │  │ RETRY (max 2) │
                           │  Image    │  │ + Enhancement │
                           └───────────┘  └───────────────┘
```

---

## 모듈 구조

```
core/background_swap/
├── __init__.py          # 통합 진입점 (swap, generate_with_validation)
├── analyzer.py          # VFX 물리 분석, 소스 타입 감지
├── generator.py         # 이미지 생성 + 검증 루프
├── prompt_builder.py    # 프롬프트 조립
├── templates.py         # 프롬프트 템플릿
├── validator.py         # 9-criteria 검증기
├── presets.py           # 스타일 프리셋
└── presets.json         # 프리셋 데이터

.claude/skills/배경교체_background-swap/
├── README.md            # 이 문서
├── SKILL.md             # Claude용 스킬 정의
├── background-swap-cheatsheet.md
└── 검수표_템플릿.md
```

---

## 데이터 플로우

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ANALYSIS PHASE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Source Image
     │
     ├──> analyze_model_physics() ──> VFX Data (6영역)
     │         │
     │         ├── geometry: horizon_y, perspective, focal_length
     │         ├── lighting: direction, elevation, softness, color_temp
     │         ├── pose_dependency: pose_type, support_required
     │         ├── installation_logic: prop_detected, forbidden_contexts
     │         ├── physics_anchors: contact_points, shadow_direction
     │         └── semantic_style: vibe, recommended_locations
     │
     ├──> detect_source_type() ──> "outdoor" | "white_studio" | "colored_studio" | "indoor"
     │
     └──> analyze_for_background_swap() ──> Swap Analysis
               │
               ├── has_vehicle: bool
               ├── ground: {material, color, tone}
               ├── color_grading: {warmth, saturation}
               └── lighting: {direction, intensity, color_temp}


┌─────────────────────────────────────────────────────────────────────────────┐
│                              GENERATION PHASE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Analysis Results
     │
     └──> build_background_prompt()
               │
               ├── 1. BASE_PRESERVATION_PROMPT (인물 보존)
               ├── 2. STRUCTURE_STYLE_TRANSFORM (구조물 스타일 변환)
               ├── 3. ONE_UNIT_PROMPTS (차량 감지 시)
               ├── 4. VFX Physical Constraints
               ├── 5. Reference Background Analysis
               ├── 6. Swap Analysis Instructions
               └── 7. User Background Style
                         │
                         v
               generate_background_swap()
                         │
                         ├── aspect_ratio: 원본 비율 유지
                         ├── image_size: "1K" | "2K" | "4K"
                         └── temperature: 0.2 → 0.1 → 0.05 (재시도 시)


┌─────────────────────────────────────────────────────────────────────────────┐
│                              VALIDATION PHASE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Generated Image + Source Image
     │
     └──> BackgroundSwapValidator.validate()
               │
               ├── 1. model_preservation (25%) - 필수 =100
               ├── 2. relight_naturalness (15%)
               ├── 3. lighting_match (12%)
               ├── 4. ground_contact (10%)
               ├── 5. physics_plausibility (10%) - 필수 ≥50
               ├── 6. perspective_match (10%) - 필수 ≥70
               ├── 7. edge_quality (8%)
               ├── 8. prop_style_consistency (5%)
               └── 9. color_temperature_compliance (5%) - 필수 ≥80
                         │
                         v
               Pass Condition:
               - total_score ≥ 95
               - model_preservation = 100
               - physics_plausibility ≥ 50
               - perspective_match ≥ 70
               - color_temperature_compliance ≥ 80
```

---

## 핵심 원칙

### 1. STRUCTURE STYLE TRANSFORM (구조물 스타일 변환)

```
원본 구조물 위치/원근 유지 + 스타일만 변경

KEEP (변경 금지):
- 구조물 위치 (x, y 좌표)
- 원근감, 소실점
- 깊이 관계

CHANGE (변경 허용):
- 텍스처, 재질
- 색상, 마감
- 스타일/미감
```

### 2. ONE UNIT 개념

```
인물 + 차량 + 오브젝트 = 단일 단위로 보존
개별 분리 금지
```

### 3. VFX 물리 분석 (6대 영역)

| 영역 | 추출값 | 용도 |
|------|--------|------|
| Camera Geometry | horizon_y, perspective | 원근 매칭 |
| Lighting Physics | direction, color_temp | 조명 매칭 |
| Pose Dependency | support_required | 지지대 필요 여부 |
| Installation Logic | forbidden_contexts | 금지 컨텍스트 |
| Physics Anchors | contact_points | 접지/그림자 |
| Semantic Style | vibe | 분위기 매칭 |

---

## 사용법

### Python API

```python
from core.background_swap import swap, generate_with_validation

# 간단한 사용
swap("photo.jpg", "LA 다운타운")

# 품질 모드 (검증 + 재시도)
swap("photo.jpg", "파리 카페", enable_retry=True)

# 직접 호출
result = generate_with_validation(
    source_image=pil_image,
    background_style="베를린 콘크리트 벽",
    api_key=api_key,
    max_retries=2,
    image_size="2K",
)
```

### 결과 구조

```python
{
    "image": PIL.Image,      # 생성된 이미지
    "score": 97,             # 총점
    "passed": True,          # 통과 여부
    "grade": "S",            # 등급 (S/A/B/C/D/F)
    "issues": [],            # 이슈 목록
    "attempts": 2,           # 시도 횟수
    "history": [...]         # 시도 기록
}
```

---

## 검증 기준 (9-criteria)

| # | 항목 | 비중 | Pass 기준 |
|---|------|------|----------|
| 1 | 인물 보존 | 25% | = 100 (필수) |
| 2 | 리라이트 자연스러움 | 15% | - |
| 3 | 조명 일치 | 12% | - |
| 4 | 접지감 | 10% | - |
| 5 | 물리 타당성 | 10% | ≥ 50 (필수) |
| 6 | 원근 일치 | 10% | ≥ 70 (필수) |
| 7 | 경계 품질 | 8% | - |
| 8 | 스타일 일치 | 5% | - |
| 9 | 색온도 준수 | 5% | ≥ 80 (필수) |

**Pass 조건**: 총점 ≥ 95 + 필수 항목 모두 충족

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 5.1.0 | 2026-02-12 | STRUCTURE_STYLE_TRANSFORM 추가, aspect_ratio 원본 유지, 총점 95점 기준 |
| 5.0.0 | 2026-02-11 | 모듈 분리 (core/background_swap/) |
| 4.0.0 | 2026-02-10 | 9-criteria 검증 체계 |
