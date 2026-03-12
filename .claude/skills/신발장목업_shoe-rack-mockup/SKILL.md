---
name: shoe-rack-mockup
description: 스케치업 신발장 렌더링에 실제 신발 목업 합성 - VMD 보고용
---

# 신발장 목업 (Shoe Rack Mockup)

> 스케치업 신발장 렌더링의 색상 마스크 영역을 실제 신발로 교체

---

## 1. 절대 규칙 (CRITICAL)

| # | 규칙 | 위반 시 |
|---|------|--------|
| 1 | **모든 색상 마스크 영역 → 신발로 교체** | 미처리 영역 = 실패 |
| 2 | **배경(선반/메쉬/벽) 100% 보존** | 배경 변형 = 실패 |
| 3 | **색상별 순차 처리** (민트 → 코랄 → 흰색) | 혼합 처리 = 품질 저하 |

---

## 2. 실행 파이프라인

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. 분석   │───▶│ 2. 감지   │───▶│ 3. 생성   │───▶│ 4. 검증   │───▶│ 5. 재생성 │
│ VLM 자동  │    │  OpenCV  │    │ Gemini   │    │  VLM     │    │  Loop    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
 실루엣 배치      색상 마스크     동적 프롬프트    슬롯 커버       실패 시
 패턴 자동 분석   슬롯 추출       3단계 순차      + 배경 보존      프롬프트 강화
```

### 자동 분석 (v0.8 신규)

**어떤 신발장 이미지가 와도 자동 대응!**

VLM이 원본 실루엣을 분석하여:
- **배치 패턴**: depth-overlap / side-by-side / single
- **방향**: left-toe-forward / right-toe-forward / front-facing
- **슬롯당 신발 수**: 1 또는 2

분석 결과를 프롬프트에 동적 반영 → 하드코딩 없이 자동 적응

### 3단계 색상 처리

| Stage | 색상 | RGB | 신발/슬롯 | 참조 신발 |
|-------|------|-----|----------|----------|
| 1 | 민트/청록 | (130, 240, 210) | 2개 (pair) | 1~6번 |
| 2 | 코랄/분홍 | (240, 110, 110) | 2개 (pair) | 7~12번 |
| 3 | 흰색 | (255, 255, 255) | 2개 (pair) | 13~18번 |

---

## 3. 대화형 질문

**1단계: 입력**

| 질문 | 옵션 | 기본값 |
|------|------|--------|
| 신발장 이미지 | 경로 | - |
| 신발 폴더 | 경로 | - |

**2단계: 설정**

| 질문 | 옵션 | 기본값 |
|------|------|--------|
| 슬롯 감지 | 자동 / 수동(JSON) | 자동 |
| 출력 해상도 | 원본 / 2K / 4K | 원본 |

---

## 4. 검증 기준

| 기준 | 비중 | 설명 | 필수 |
|------|------|------|------|
| slot_coverage | 25% | 모든 마스크 → 신발 | = 100% |
| shoe_accuracy | 25% | 참조 신발과 일치 | >= 70 |
| background_preservation | 20% | 배경 변형 없음 | >= 95 |
| size_consistency | 15% | 같은 슬롯 크기 일관 | 편차 < 25% |
| composite_quality | 15% | 경계/그림자 자연스러움 | - |

**등급:** S(95+), A(90+), B(85+), C(75+), F(75-)

**Auto-Fail (v1.0 강화):**
- 색상 마스크 영역 미처리
- 선반/메쉬 배경 변형 (색상 변경 포함!)
- 신발 슬롯 외 삐져나옴
- 명백한 합성 경계선
- **신발 중복** (같은 디자인 2회 이상 등장)
- **비스듬한 배치** (신발이 선반과 평행하지 않음)
- **배경 색상 오염** (철제 매대 색상 변경)

---

## 5. 모듈 구조

```
core/shoe_rack_mockup/
├── __init__.py              # 진입점 (v1.0: 거울 처리 export 추가)
├── silhouette_analyzer.py   # VLM 기반 실루엣 배치 패턴 자동 분석 (v0.7)
├── slot_detector.py         # OpenCV 색상 마스크 감지
├── slot_config.py           # 색상별 설정
├── compositor.py            # Gemini 인페인팅 (v0.7: 자동 분석 통합)
├── validator.py             # 검증 로직
├── templates.py             # 프롬프트 템플릿 (v1.0: 중복방지/정면배치/배경보존 강화)
└── mirror_processor.py      # 거울 반사 후처리 (v1.0 신규)
```

---

## 6. API 사용

```python
from core.config import IMAGE_MODEL, VISION_MODEL

# 슬롯 감지: OpenCV (로컬)
# 인페인팅: IMAGE_MODEL (temp=0.3)
# 검증: VISION_MODEL (temp=0.1)
```

---

## 7. 프롬프트 패턴

**핵심 원칙:**
1. **전체 이미지 인페인팅** - 개별 슬롯 생성+붙여넣기 아님
2. **크기 기준 명시** - 코랄/흰색 실루엣을 크기 기준으로 참조
3. **2켤레(PAIR) 강조** - "2 shoes side by side" 명시
4. **경계 오버플로우 방지** - "must NOT overflow outside the mint boundary"
5. **신발 정확도** - 참조 이미지 EXACT COPY 강조

```python
# Stage 1: 민트색 영역 처리 (v0.5 - Optimal V4)
MINT_PROMPT = """[SHOE RACK - MINT TO REALISTIC SHOES]

This shoe rack has 3 COLUMNS of shoe silhouettes:
- LEFT: MINT/CYAN colored (6 rows)
- CENTER: CORAL/PINK colored (6 rows)
- RIGHT: WHITE colored (6 rows)

ALL THREE COLUMNS have the SAME shoe size.
Look at CORAL and WHITE silhouettes - that is the CORRECT SIZE.

★★★ CRITICAL SIZE RULE ★★★
Each mint slot contains 2 SHOES side by side (a PAIR).
The mint shoes must be the SAME SIZE as coral/white silhouettes.
DO NOT make mint shoes LARGER than coral/white shoes.
Shoes must NOT overflow outside the mint boundary.

Compare your result:
- Mint shoes size = Coral shoes size = White shoes size
- If mint shoes look bigger than coral/white = WRONG

★★★ EACH SLOT = 2 SHOES (PAIR) ★★★
Row 1: 2 shoes side by side (Reference Shoe 1 design)
Row 2: 2 shoes side by side (Reference Shoe 2 design)
...

★★★ DESIGN COPY ★★★
Copy EXACT design from each reference shoe:
- Color (white, black, gray)
- Logo (MLB NY logo)
- Material texture
- Details (stitching, patterns)

★★★ PRESERVATION ★★★
- CORAL areas: Keep as flat pink. NO changes.
- WHITE areas: Keep exactly as white shapes. NO changes.
- Shelves, mesh, wall: Keep identical."""
```

---

## 8. 출력 폴더

```
Fnf_studio_outputs/shoe_rack_mockup/{timestamp}/
├── final/              # 최종 이미지
├── slots/              # 슬롯 분석 (JSON)
├── comparison/         # Before/After
└── metadata.json
```

---

## 9. 테스트 현황

| 테스트 | 파일 | 상태 | 비고 |
|--------|------|------|------|
| 슬롯 감지 | `test_slot_detection.py` | Pass | OpenCV 색상 마스크 |
| 인페인팅 | `test_realistic_placement.py` | Pass | 개별 슬롯 (deprecated) |
| 파이프라인 Stage 1 | `test_optimal_v4.py` | **Pass** | 민트색 → 신발 ✓ |
| 파이프라인 Stage 2 | `test_stage2_coral_v3.py` | **Pass** | 코랄색 → 신발 ✓ |
| 파이프라인 Stage 3 | `test_stage3_white.py` | **Pass** | 흰색 → 신발 ✓ |
| 검증 | `test_validation.py` | 예정 | VLM 검증 |

**Stage 1 테스트 결과 (2026-02-20):**
- 민트색 영역 → 신발 교체 ✓
- 코랄색/흰색 영역 → 그대로 유지 ✓
- MLB NY 로고 신발 생성 ✓
- 신발 2켤레(PAIR) 생성 ✓
- 크기 = 코랄/흰색 실루엣과 동일 ✓
- 경계 오버플로우 방지 ✓

**Stage 2 테스트 결과 (2026-02-20):**
- Stage 1 결과물 입력으로 사용 ✓
- 코랄색 영역 → 신발 7~12번 교체 ✓
- 민트색(Stage 1 결과) 보존 ✓
- 흰색 영역 → 그대로 유지 ✓
- 신발 2켤레(PAIR) 생성 ✓

**Stage 3 테스트 결과 (2026-02-20):**
- Stage 2 결과물 입력으로 사용 ✓
- 흰색 영역 → 신발 13~18번 교체 ✓
- 민트색/코랄색(Stage 1, 2 결과) 보존 ✓
- 신발 2켤레(PAIR) 생성 ✓

**v0.9 수정 사항 (2026-02-20):**
- LEFT 열과 RIGHT 열이 **다른 신발**임을 명시
- 정면 뷰에서 2개가 겹쳐 1개로 보이지만 실제로 다른 디자인
- comparison 이미지 생성 제거 (불필요)

### 특수 케이스: 이미지 8번 (거울) - v1.0 구현

**상황:** 이미지 8번은 왼쪽에 거울이 있어서 오른쪽 캐비닛이 반사됨

**v1.0 처리 방법 (mirror_processor.py):**
1. 오른쪽 캐비닛 영역만 3단계 처리 (신발 교체)
2. 결과물을 좌우 반전 (mirror flip)
3. Gaussian blur 적용 (거울 느낌, radius=4.0)
4. 왼쪽 거울 영역에 합성

**사용법:**
```python
from core.shoe_rack_mockup import apply_mirror_effect_to_image8

# 3단계 처리 완료 후
final_with_mirror = apply_mirror_effect_to_image8(
    result_image=pipeline_result.final_image,
    blur_radius=4.0,  # 거울 흐림 강도
)
```

**거울 처리 체크리스트:**
- [ ] 거울면 흐릿함 (blur 적용)
- [ ] 신발 방향 좌우반전 (mirror flip)
- [ ] 배경과 자연스럽게 합성

---

## 10. 사용법

```
/신발장목업

# 또는
신발장 이미지: vlm_테스트용/매장/2.png
신발 폴더: 신발/side_view_left_toe/
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| **1.0** | **2026-02-24** | **대규모 품질 개선**: (1) 신발 중복 방지 강화 - 모든 슬롯 다른 디자인, (2) 비스듬한 연출 금지 - 정면 배치 강제, (3) 배경 보존 강화 - 마스크 외 영역 변경 시 실패 처리, (4) 거울 처리 모듈 추가 (mirror_processor.py) - 이미지 8번 전용, (5) 사용된 신발 저장 기능 - inputs/ 폴더에 18장 복사 |
| 0.9 | 2026-02-20 | **LEFT/RIGHT 열 다른 신발 명시**: 정면 뷰에서 겹쳐 보이지만 LEFT ≠ RIGHT 신발, comparison 이미지 생성 제거 |
| 0.8 | 2026-02-20 | **자동 분석 파이프라인 완성**: VLM 기반 실루엣 배치 패턴 자동 분석 (depth-overlap/side-by-side/single), 동적 프롬프트 생성, templates.py에 build_dynamic_prompt() 추가 |
| 0.7 | 2026-02-20 | **실루엣 분석기 통합**: silhouette_analyzer.py 추가, compositor.py run_pipeline() 자동 분석 통합, __init__.py export 추가 |
| 0.6 | 2026-02-20 | **Stage 2, 3 최적화 완료**: 모든 스테이지 2켤레(PAIR) 통일, 이전 스테이지 결과물 보존 명시, 전체 파이프라인 테스트 Pass |
| 0.5 | 2026-02-20 | **Stage 1 최적화 (V4)**: 2켤레(PAIR) 강조, 코랄/흰색 크기 기준 참조, 경계 오버플로우 방지 |
| 0.4 | 2026-02-20 | 신발 참조 정확도 개선 (EXACT COPY 강조), Stage 1 테스트 Pass |
| 0.3 | 2026-02-20 | compositor.py 전체 이미지 인페인팅 방식으로 변경 (슬롯별 생성+붙여넣기 → 전체 인페인팅), 프롬프트 강화 (색상 영역 보존 명시) |
| 0.2 | 2026-02-20 | 테스트 결과 반영, 3단계 파이프라인 확정 |
| 0.1 | 2026-02-20 | 초안 작성 |
