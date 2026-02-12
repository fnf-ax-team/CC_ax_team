---
name: background-swap
description: 배경 교체 - 인물 보존하고 배경만 교체
user-invocable: true
trigger-keywords: ["배경교체", "배경 바꿔", "배경 변경", "background swap"]
---

# 배경교체 (Background Swap)

> 인물과 오브젝트는 그대로, 배경만 교체

---

## 절대 규칙 (CRITICAL)

1. **필수 모델**:
   - 이미지 생성: `gemini-3-pro-image-preview`
   - VLM 분석: `gemini-3-flash-preview`
2. **인물 크기 1:1 보존** - 절대 축소 금지
3. **ONE UNIT 개념** - 인물+차량+오브젝트를 단일 단위로 보존
4. **StudioRelight 라우팅** - 스튜디오→야외 시 9-criteria 검증

---

## 필수 리소스

```
.claude/skills/배경교체_background-swap/background-swap-cheatsheet.md  ← 치트시트 (반드시 로드)

core/background_swap/                  ← 실행 모듈
  ├── __init__.py                      ← 통합 진입점 (swap 함수)
  ├── analyzer.py                      ← VFX/배경 분석
  ├── prompt_builder.py                ← 프롬프트 조립
  └── generator.py                     ← 생성 + 검증

core/background_swap_validator.py      ← 검증 모듈 (7/9-criteria)
```

**스킬 실행 시 치트시트를 먼저 로드하여 스타일 프리셋, VFX 분석 영역, 검증 기준을 참조한다.**

---

## 모드 비교

| 항목 | Fast Mode (기본) | Quality Mode (`--retry`) | Sweep Mode (`--sweep`) |
|------|-----------------|--------------------------|------------------------|
| 생성 | 1회 | 최대 3회 | 1회 (Fast) |
| 검증 | 점수만 | 이미지별 통과/실패 | 배치 일괄 검증 |
| 재생성 | 없음 | 이미지별 진단+재생성 | 실패분만 재생성 |
| Temperature | 0.2 고정 | 0.2→0.1→0.05 | 0.2→retry시 감소 |
| 용도 | 테스트 | 소량 프로덕션 | **대량 프로덕션 (추천)** |

---

## 모듈 인터페이스 (에이전트 호출 규격)

### 1. 통합 진입점

```python
from core.background_swap import swap

# Fast 모드 (기본)
swap("photo.jpg", "캘리포니아 해변 석양")

# Quality 모드
swap("photo.jpg", "파리 카페 테라스", enable_retry=True)

# Sweep 모드 (대량)
swap("./images", "베를린 콘크리트 벽", enable_sweep=True)
```

### 2. 분석 함수

```python
from core.background_swap import (
    analyze_model_physics,    # VFX 물리 분석 (6대 영역)
    analyze_for_background_swap,  # 차량/바닥/색보정 분석
    analyze_background,       # 배경 이미지 → 텍스트 변환
    detect_source_type,       # 스튜디오/야외 감지
)

# VFX 물리 분석
result = analyze_model_physics(image_pil, api_key)
# → {"status": "success", "data": {...}, "generated_guideline": str}

# 소스 타입 감지 (StudioRelight 라우팅용)
source_type = detect_source_type(image_pil, api_key)
# → "outdoor" | "white_studio" | "colored_studio" | "indoor"
```

### 3. 프롬프트 빌더

```python
from core.background_swap import (
    build_background_prompt,
    build_reference_prompt,
    build_one_unit_instructions,
)

# 참조 이미지 프롬프트 (5가지 reference_type)
prompt = build_reference_prompt(base_prompt, reference_type="style")
# reference_type: "style" | "pose" | "background" | "clothing" | "all"
```

### 4. 생성 + 검증

```python
from core.background_swap import generate_with_validation

result = generate_with_validation(
    source_image=image_pil,
    background_style="런던 브릭 골목",
    api_key=api_key,
    max_retries=2,
    image_size="2K"
)
# → {"image": PIL.Image, "score": int, "passed": bool, "issues": [...]}
```

---

## 검증 기준 (9-criteria)

| # | 항목 | 한글 | 비중 | Pass 기준 |
|---|------|------|------|----------|
| 1 | model_preservation | 인물 보존 | 25% | **= 100 (필수)** |
| 2 | relight_naturalness | 리라이트 자연스러움 | 15% | - |
| 3 | lighting_match | 조명 일치 | 12% | - |
| 4 | ground_contact | 접지감 | 12% | - |
| 5 | physics_plausibility | 물리 타당성 | 10% | **≥ 50 (필수)** |
| 6 | edge_quality | 경계 품질 | 8% | - |
| 7 | prop_style_consistency | 스타일 일치 | 8% | - |
| 8 | color_temperature_compliance | 색온도 준수 | 5% | **≥ 80 (필수)** |
| 9 | perspective_match | 원근 일치 | 5% | - |

**Pass 조건**: `model_preservation = 100` AND `physics_plausibility ≥ 50` AND `color_temperature_compliance ≥ 80` AND `total ≥ 90`

---

## 검증기 (통합 9-criteria)

모든 소스 타입에 동일한 9개 기준 적용:

| 소스 타입 | Validator | 기준 |
|-----------|-----------|------|
| outdoor | BackgroundSwapValidator | 9개 기준 |
| studio | BackgroundSwapValidator | 9개 기준 |
| indoor | BackgroundSwapValidator | 9개 기준 |

**핵심 추가 기준:**
- `relight_naturalness` (15%) - 인물에 배경 조명이 자연스럽게 반영되었는가
- `color_temperature_compliance` (5%) - 누런 톤 없이 쿨/뉴트럴 유지

---

## 자동 재시도

| 이슈 | 임계값 | 보강 방향 |
|------|--------|----------|
| POSE_MISMATCH | match < 90 | 포즈 고정 강제 |
| FACE_CHANGED | match < 95 | 얼굴 고정 강제 |
| SCALE_SHRUNK | match < 85 | 스케일 1:1 강제 |
| PHYSICS_ERROR | phys < 80 | 물리 제약 강화 |
| LIGHTING_MISMATCH | light < 80 | 조명 동기화 |
| GROUND_POOR | ground < 80 | 접지 강화 |
| EDGE_ARTIFACTS | edge < 85 | 경계 최적화 |

**Temperature 감소**: 0.2 → 0.1 → 0.05

---

## VFX 물리 분석 (6대 영역)

| 영역 | 추출값 | 용도 |
|------|--------|------|
| Camera Geometry | horizon_y, perspective, focal_length_vibe | 원근/소실점 매칭 |
| Lighting Physics | direction_clock, elevation, softness, color_temp | 조명 방향/강도 매칭 |
| Pose Dependency | pose_type, support_required, support_direction | 지지대 필요 여부 판단 |
| Installation Logic | prop_detected, is_fixed_prop, forbidden_contexts | 소품 배치 규칙 |
| Physics Anchors | contact_points [x,y], shadow_casting_direction | 접지/그림자 정합 |
| Semantic Style | vibe, recommended_locations | 분위기 매칭 |

---

## 대화형 워크플로 (4대 원칙)

1. **영문 프롬프트 숨김** - 내부 처리용
2. **이모지 금지**
3. **친절한 척 금지** - 일만 함
4. **다른 스타일 제안 금지**

### 대화 예시

```
사용자: 베를린 느낌으로

Claude: 베를린 어떤 느낌? 모던? 클래식?

사용자: 모던한 느낌

Claude: 모던 베를린. 유리+철골, 차가운 톤. 몇 장?

사용자: 2장

Claude: 2장 생성합니다.
```

---

## 에러 핸들링

| 에러 | 복구 액션 |
|------|----------|
| API Timeout | 최대 3회 재시도 (5s, 10s, 15s) |
| Rate Limit (429) | 60초 대기 후 재시도 |
| 인물 축소됨 | 프레이밍 고정 프롬프트 강화 |
| File Not Found | 사용자에게 경로 재입력 요청 |

---

## 출력

```
Fnf_studio_outputs/background_swap/{설명}_{타임스탬프}/
```

---

## DO/DON'T

### DO
- ONE UNIT 개념 적용 (인물+차량+오브젝트 = 단일 단위)
- 7-criteria 검증 사용
- Temperature 단계적 감소 (재시도 시)
- `get_next_api_key()` 패턴 사용
- 1024px 다운샘플링 (VFX 분석)
- 512px 다운샘플링 (배경 분석)

### DON'T
- 인물과 차량을 개별 보존 지시 (X)
- 이전 5-criteria 기준 사용 (X)
- 단일 API 키 하드코딩 (X)
- 원본 해상도 그대로 VLM 전달 (X)
- 설치 논리 무시 (X)

---

**버전**: 5.0.0 (모듈 분리)
**작성일**: 2026-02-11

**변경사항 (v5.0.0)**:
- 인라인 코드 제거 → `core/background_swap/` 모듈 참조
- 검증 코드 제거 → `core/background_swap_validator.py` 참조
- 모듈 인터페이스 섹션 추가
- 1021줄 → 250줄 리팩터링 완료
