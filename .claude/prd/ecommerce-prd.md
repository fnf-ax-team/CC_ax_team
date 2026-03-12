# PRD: 이커머스 (Ecommerce)

> 작성일: 2026-02-19
> 상태: Draft

---

## 1. 개요

### 1.1 목적

얼굴 이미지와 착장 이미지를 입력받아 **무채색 스튜디오 배경** 기반의 **판매용 이커머스 모델 이미지**를 생성하는 워크플로.

브랜드컷이 브랜딩/에디토리얼 목적의 화보라면, 이커머스는 **상품 판매를 위한 상세페이지/룩북용** 이미지다. 포즈와 배경은 생성하되, 얼굴과 착장 디테일은 참조 이미지로부터 정확하게 반영한다.

### 1.2 타겟 사용자

- 이커머스팀: 상세페이지용 모델 이미지 대량 생성
- MD팀: 신상품 착용샷 빠른 생성 (스튜디오 촬영 전 시안)
- 마케팅팀: 온라인몰/룩북용 클린 배경 이미지

### 1.3 핵심 가치

| 가치 | 설명 |
|------|------|
| 비용 절감 | 스튜디오 촬영 없이 상품 착용 이미지 생성 |
| 속도 | 신상품 등록 리드타임 단축 |
| 일관성 | 무채색 배경 표준화로 채널 일관성 유지 |
| 착장 정확도 | 실제 판매 상품 색상/로고/디테일 정확 재현 |

### 1.4 브랜드컷과의 차이 (CRITICAL)

| 구분 | 이커머스 | 브랜드컷 |
|------|---------|---------|
| 목적 | 상품 판매 (상세페이지/룩북) | 브랜딩 (캠페인/화보) |
| 배경 | 무채색 강제 (흰/회색/미니멀) | 브랜드 컨셉 배경 허용 |
| 포즈 | 프리셋 기반 (전신/상반신/디테일컷) | 에디토리얼 자유 포즈 |
| 톤 | 클린/뉴트럴 | 브랜드 감성/무드 |
| 조명 | 균일한 스튜디오 조명 | 드라마틱/에디토리얼 조명 허용 |

### 1.5 워크플로 카테고리

**인물-정규** — 얼굴 필수, 착장 필수, 브랜드톤 필수

---

## 2. 요구사항

### 2.1 필수 기능 (Must Have)

- [ ] 얼굴 이미지 기반 인물 생성 (face_identity 유지)
- [ ] 착장 이미지 디테일 정확 재현 (색상/로고/소재/실루엣)
- [ ] 무채색 배경 강제 (white / gray / minimal indoor만 허용)
- [ ] 포즈 프리셋 선택 지원 (front_standing / front_casual / side_profile / back_view / detail_closeup)
- [ ] 배경 프리셋 선택 지원 (white_studio / gray_studio / minimal_indoor / outdoor_urban)
- [ ] 이커머스 상업용 품질 기준 적용 (commercial_quality >= 85)
- [ ] 브랜드컷과 완전히 독립된 프롬프트/검증 파이프라인
- [ ] 검수+재생성 루프 (최대 2회)

### 2.2 선택 기능 (Nice to Have)

- [ ] 포즈 커스텀 텍스트 입력 (프리셋 외 자유 기술)
- [ ] 복수 포즈 자동 조합 (한 번 실행으로 여러 포즈 생성)
- [ ] 상반신/하반신 부분 디테일컷 자동 생성

### 2.3 제외 범위 (Out of Scope)

- 유채색/드라마틱 배경 (→ 브랜드컷 워크플로)
- 포즈 보존 (→ outfit-swap 또는 pose-change 워크플로)
- 배경 보존 (→ 입력 배경 없음, 항상 생성)
- 제품 단독 샷 (인물 없음) (→ product-styled 워크플로)
- 브랜드 에디토리얼 무드 (→ 브랜드컷 워크플로)

---

## 3. 입출력 정의

### 3.1 입력

| 입력 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 얼굴 이미지 | Image[] | O | 인물 동일성 참조 (1~5장) |
| 착장 이미지 | Image[] | O | 착장 디테일 참조 (누끼 or 착용샷) |
| 포즈 프리셋 | string | O | POSE_PRESETS 중 선택 |
| 배경 프리셋 | string | O | BACKGROUND_PRESETS 중 선택 |
| 비율 | string | O | 3:4 기본 (core/options.py) |
| 수량 | int | O | 1, 3, 5, 10장 |
| 화질 | string | O | 1K, 2K, 4K |

### 3.2 출력

| 출력 | 타입 | 설명 |
|------|------|------|
| 생성 이미지 | Image[] | 이커머스 모델 이미지 |
| 검증 결과 | dict | 점수, 등급, 통과 여부, 이슈 |
| 분석 로그 | JSON | 착장 분석 결과, 시도 이력 |

### 3.3 출력 폴더

```
Fnf_studio_outputs/ecommerce/{timestamp}/
├── result_01.png
├── result_02.png
├── result_03.png
└── analysis_log.json
```

---

## 4. 워크플로 설계

### 4.1 단계별 흐름

```
┌──────────────────────────────────────────────────────────────────────┐
│                      이커머스 파이프라인                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. 입력 수집                                                         │
│     └─ 얼굴 이미지 경로                                               │
│     └─ 착장 이미지 경로                                               │
│     └─ 포즈 프리셋 선택                                               │
│     └─ 배경 프리셋 선택                                               │
│     └─ 옵션 선택 (비율/수량/화질)                                      │
│                                                                      │
│  2. VLM 분석 (병렬)                                                   │
│     ├─ analyze_outfit_for_ecommerce() → 착장 디테일 추출              │
│     │   (색상/로고/소재/실루엣/레이어 구성)                             │
│     └─ analyze_face() → 인물 특성 추출                               │
│         (피부톤/헤어/체형)                                             │
│                                                                      │
│  3. 프롬프트 조립                                                      │
│     └─ build_ecommerce_prompt()                                      │
│         ├─ 착장 VLM 분석 결과 → 텍스트 변환                            │
│         ├─ 포즈 프리셋 지시                                            │
│         ├─ 배경 프리셋 지시 (무채색 강제)                               │
│         └─ 이커머스 품질 지시 (균일 조명/클린 배경)                     │
│                                                                      │
│  4. 이미지 생성                                                        │
│     └─ generate_ecommerce_image()                                    │
│         ├─ 프롬프트 (텍스트)                                           │
│         ├─ 얼굴 이미지 (API 직접 전달)                                 │
│         └─ 착장 이미지 (API 직접 전달)                                 │
│                                                                      │
│  5. 검증                                                              │
│     └─ EcommerceValidator.validate()                                 │
│         ├─ outfit_accuracy (40%) — 착장 디테일 정확도                  │
│         ├─ face_identity (20%) — 동일 인물 여부                       │
│         ├─ pose_correctness (15%) — 프리셋 포즈 일치                  │
│         ├─ background_compliance (15%) — 무채색 배경 준수              │
│         └─ commercial_quality (10%) — 이커머스 품질 기준               │
│                                                                      │
│  6. 재생성 (실패 시)                                                   │
│     └─ 실패 원인별 프롬프트 강화 → 최대 2회                            │
│                                                                      │
│  7. 출력                                                              │
│     └─ 저장 + 결과 반환                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 대화형 질문 설계

**1단계: 경로 입력 (순차 텍스트)**

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "얼굴 이미지 경로 (또는 폴더)?" | O |
| 2 | "착장 이미지 경로 (또는 폴더)?" | O |

**2단계: 착장 분석 결과 확인**

```
착장 분석 결과:
| 부위 | 아이템    | 색상       | 로고                   | 디테일          |
|------|-----------|------------|------------------------|-----------------|
| 상의 | 크롭 티셔츠 | White      | NY (가슴 좌측, Navy) | 라운드넥, 반소매 |
| 하의 | 와이드 팬츠 | Black      | MLB (우측 허벅지)    | 와이드핏, 밴딩  |

계속하시겠습니까? (착장 분석 결과가 정확하지 않으면 이미지를 교체해 주세요)
```

**3단계: 포즈 + 배경 선택 (AskUserQuestion 클릭)**

```python
AskUserQuestion(questions=[
    {
        "question": "포즈를 선택해주세요",
        "header": "포즈 프리셋",
        "options": [
            {"label": "전신 정면 (기본)", "description": "standing front view, neutral pose"},
            {"label": "전신 캐주얼", "description": "standing front view, one hand on hip"},
            {"label": "측면", "description": "side profile view"},
            {"label": "후면", "description": "back view, slight turn"},
            {"label": "상반신 디테일컷", "description": "upper body closeup for detail"}
        ],
        "multiSelect": False
    },
    {
        "question": "배경을 선택해주세요",
        "header": "배경 프리셋",
        "options": [
            {"label": "화이트 스튜디오 (권장)", "description": "pure white studio background"},
            {"label": "그레이 스튜디오", "description": "neutral gray studio background"},
            {"label": "미니멀 인도어", "description": "minimal indoor setting, light colors"},
            {"label": "어반 아웃도어", "description": "clean urban outdoor, shallow depth"}
        ],
        "multiSelect": False
    }
])
```

**4단계: 수량 + 화질 선택 (AskUserQuestion 클릭)**

```python
AskUserQuestion(questions=[
    {
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "1장", "description": "테스트용"},
            {"label": "3장 (Recommended)", "description": "다양한 결과 비교"},
            {"label": "5장", "description": "충분한 선택지"},
            {"label": "10장", "description": "대량 생성"}
        ],
        "multiSelect": False
    },
    {
        "question": "화질을 선택해주세요",
        "header": "해상도",
        "options": [
            {"label": "1K", "description": "빠른 테스트"},
            {"label": "2K (Recommended)", "description": "상세페이지/SNS용"},
            {"label": "4K", "description": "인쇄/최종 결과물"}
        ],
        "multiSelect": False
    }
])
```

### 4.3 포즈/배경 프리셋 정의

```python
POSE_PRESETS = {
    "front_standing": "standing front view, neutral pose",
    "front_casual":   "standing front view, one hand on hip",
    "side_profile":   "side profile view",
    "back_view":      "back view, slight turn",
    "detail_closeup": "upper body closeup for detail",
}

BACKGROUND_PRESETS = {
    "white_studio":   "pure white studio background",
    "gray_studio":    "neutral gray studio background",
    "minimal_indoor": "minimal indoor setting, light colors",
    "outdoor_urban":  "clean urban outdoor, shallow depth",
}
```

---

## 5. 검증 기준

### 5.1 검증 기준 정의

| 기준 | 비중 | 설명 | Pass Threshold | Auto-Fail |
|------|------|------|----------------|-----------|
| outfit_accuracy | 40% | 착장 색상/로고/소재/실루엣 일치 | >= 85 | < 70 |
| face_identity | 20% | 동일 인물 여부 | >= 70 | < 60 |
| pose_correctness | 15% | 선택한 프리셋 포즈 일치 | >= 80 | - |
| background_compliance | 15% | 무채색 배경 준수 (유채색 배경 = 즉시 탈락) | >= 90 | < 90 |
| commercial_quality | 10% | 균일 조명/아티팩트 없음/해상도 | >= 85 | - |

**Pass Condition:** `total_score >= 85`

### 5.2 등급 체계

| 등급 | 점수 | 판정 |
|------|------|------|
| S | 95+ | 바로 사용 |
| A | 90+ | 바로 사용 |
| B | 85+ | 확인 후 사용 |
| C | 75+ | 재생성 권장 |
| F | 75- | 재생성 필수 |

### 5.3 Auto-Fail 조건

| 조건 | 설명 |
|------|------|
| 배경에 유채색 포함 | background_compliance < 90 — 즉시 탈락 |
| 착장 색상/로고 불일치 | outfit_accuracy < 70 |
| 얼굴 다른 사람 | face_identity < 60 |
| 손가락 6개 이상/기형 | 공통 Auto-Fail |
| 누런 톤 (warm cast) | 공통 Auto-Fail |
| 의도하지 않은 텍스트 | 공통 Auto-Fail |
| AI 특유 플라스틱 피부 | commercial_quality 감점 |

**브랜드컷과의 차이:** 이커머스는 `background_compliance`가 필수 통과 기준. 배경에 색상이 들어가면 무조건 재생성.

### 5.4 VLM 검수 프롬프트 구조

CLAUDE.md VLM 검수 원칙 준수: step-by-step 강제 + 출력 형식 명시 + 계산 강제.

**outfit_accuracy 검수 예시:**

```
[STEP 1] OUTFIT REFERENCE 분석:
- 상의 = ?, 색상 = ?, 로고 위치/색 = ?, 소재 = ?
- 하의 = ?, 색상 = ?, 로고 위치/색 = ?

[STEP 2] GENERATED IMAGE 분석:
- 상의 = ?, 색상 = ?, 로고 = ?
- 하의 = ?, 색상 = ?, 로고 = ?

[STEP 3] 비교 및 감점:
- 상의 색상: 일치(0) / 불일치(-20)
- 상의 로고: 정확(0) / 위치오류(-10) / 누락(-25)
- 하의 색상: 일치(0) / 불일치(-15)
- 하의 로고: 정확(0) / 위치오류(-10) / 누락(-20)

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:흰크롭티(NY좌가슴)+블랙와이드(MLB우허벅지), GEN:흰크롭티(NY좌가슴)+블랙와이드(MLB우허벅지), 감점:0"
```

**background_compliance 검수 예시:**

```
[STEP 1] 배경 색상 분석:
- 배경에 유채색(빨강/노랑/파랑/초록 등) 존재 여부 = ?
- 배경 전반 색조 = ?

[STEP 2] 무채색 준수 여부 판정:
- 순백 또는 회색 계열 = 준수(100)
- 미니멀 아이보리/오프화이트 = 경계(85)
- 유채색 포함 = 위반(0) → AUTO-FAIL

[STEP 3] 최종 점수 = 위 판정값

reason 필수 형식: "배경:순백, 유채색없음, 준수(100)"
```

### 5.5 재생성 로직

| 실패 기준 | 프롬프트 강화 방향 |
|----------|-------------------|
| outfit_accuracy 실패 | 착장 디테일 반복 강화 + "EXACT color match, EXACT logo position" |
| face_identity 실패 | "EXACT same face identity from reference" 강조 |
| pose_correctness 실패 | 포즈 프리셋 텍스트 재강조 + 구체적 포즈 기술 추가 |
| background_compliance 실패 | "STRICTLY pure white/gray background ONLY, NO colored elements" 강조 |
| commercial_quality 실패 | "even studio lighting, no shadows, crisp detail" 추가 |

**재시도 설정:**
- 최대 재시도: 2회
- Temperature: 0.25 → 0.20 → 0.15
- background_compliance 2회 연속 실패 → 사용자에게 배경 프리셋 재선택 요청

---

## 6. 기술 설계

### 6.1 모듈 구조

```
core/ecommerce/
├── __init__.py           # generate_ecommerce, generate_with_validation
├── presets.py            # POSE_PRESETS, BACKGROUND_PRESETS
├── analyzer.py           # analyze_outfit_for_ecommerce(), analyze_face()
├── prompt_builder.py     # build_ecommerce_prompt()
├── generator.py          # generate_ecommerce_image()
├── validator.py          # EcommerceValidator (@ValidatorRegistry.register)
└── templates.py          # VLM 프롬프트 템플릿
```

### 6.2 기존 모듈 재사용

| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 착장 VLM 분석 (재사용 또는 래핑) |
| `core/validators/base.py` | 검증기 베이스 클래스 |
| `core/api.py` | API 키 로테이션 |
| `core/config.py` | IMAGE_MODEL, VISION_MODEL 상수 |
| `core/options.py` | 비율/해상도/비용 (하드코딩 금지) |

### 6.3 API 사용

| 용도 | 모델 | Temperature |
|------|------|-------------|
| 착장 VLM 분석 | VISION_MODEL | 0.1 |
| 얼굴 분석 | VISION_MODEL | 0.1 |
| 이미지 생성 | IMAGE_MODEL | 0.25 |
| 검수 | VISION_MODEL | 0.1 |

### 6.4 이미지 전달 순서

```
1. 프롬프트 (텍스트) — 착장 상세 + 포즈 지시 + 배경 지시
2. 얼굴 이미지 (API 직접 전달) — face_identity 보장
3. 착장 이미지 (API 직접 전달) — outfit_accuracy 보장
```

**핵심 원칙:**
- 얼굴/착장: API 직접 전달 (이미지 품질 우선)
- 포즈/배경: 텍스트 프리셋으로 전달 (새로 생성)
- 컨셉 레퍼런스: 없음 (이커머스는 프리셋 기반)

### 6.5 WorkflowType 등록

```python
# core/validators/__init__.py
class WorkflowType(Enum):
    # 기존
    BRANDCUT = "brandcut"
    BACKGROUND_SWAP = "background_swap"
    SELFIE = "selfie"
    UGC = "ugc"

    # 신규 추가
    ECOMMERCE = "ecommerce"
```

### 6.6 핵심 불변량 (Core Invariants)

| 구분 | 요소 | 규칙 |
|------|------|------|
| **must_use** | 얼굴 (동일 인물) | 참조 이미지 기반 생성 |
| **must_use** | 착장 (디테일 정확) | 참조 이미지 기반 생성 |
| **must_generate** | 포즈 | 프리셋 기반 새로 생성 |
| **must_generate** | 배경 | 무채색 프리셋 강제 생성 |
| **forbidden** | 유채색 배경 | 절대 불가, Auto-Fail |
| **forbidden** | 드라마틱 조명 | 이커머스 품질 위배 |

---

## 7. 테스트 계획

### 7.1 테스트 케이스

| # | 시나리오 | 입력 | 예상 결과 |
|---|---------|------|----------|
| 1 | 기본 — 전신 정면 | 얼굴 + 착장 + front_standing + white_studio | 전신 착장 정확, 흰 배경 |
| 2 | 상반신 디테일컷 | 얼굴 + 착장 + detail_closeup + gray_studio | 상반신 착장 디테일 클로즈업 |
| 3 | 후면 | 얼굴 + 착장 + back_view + white_studio | 후면 착장 정확 재현 |
| 4 | MLB 로고 정확도 | NY 로고 착장 + front_standing | 로고 위치/색상/크기 정확 |
| 5 | 다중 착장 레이어 | 코트+티셔츠+바지 + front_casual | 전체 레이어 정확 재현 |
| 6 | 유채색 배경 차단 | (내부적으로 생성된 이미지가 유채색 배경일 때) | Auto-Fail + 재생성 |
| 7 | 에러 처리 — rate limit | 정상 입력 + rate limit 환경 | 재시도 3회 후 에러 반환 |

### 7.2 브랜드컷 vs 이커머스 구분 테스트

```
동일 입력으로 두 워크플로 실행 시:
- 이커머스: 무채색 배경, 프리셋 포즈, 균일 조명
- 브랜드컷: 컨셉 배경, 에디토리얼 포즈, 브랜드 감성
→ 두 결과물이 명확히 구분되어야 함
```

### 7.3 테스트 파일 위치

```
tests/ecommerce/
├── test_basic.py             # 기본 생성 테스트
├── test_background.py        # 무채색 배경 강제 테스트
├── test_outfit_accuracy.py   # 착장 정확도 테스트
├── test_mlb_logo.py          # MLB 로고 정확도
└── test_integration.py       # 전체 파이프라인 테스트
```

---

## 8. 릴리즈 체크리스트

### 8.1 코드 완성도

- [ ] `core/ecommerce/` 모듈 완성
- [ ] `EcommerceValidator` 구현 (`@ValidatorRegistry.register`)
- [ ] `generate_with_validation()` 구현 (max_retries=2 필수)
- [ ] `WorkflowType.ECOMMERCE` 등록
- [ ] `core/validators/__init__.py` import 추가
- [ ] 에러 핸들링 완료 (429/503/timeout 재시도)

### 8.2 문서화

- [ ] SKILL.md 작성 (`.claude/skills/이커머스_ecommerce/`)
- [ ] CLAUDE.md 품질 검증 기준 섹션에 이커머스 추가
- [ ] CLAUDE.md 워크플로 목록에서 상태 업데이트 (🔜 → ✅)

### 8.3 테스트

- [ ] 전신 정면 케이스 통과
- [ ] 상반신 디테일컷 케이스 통과
- [ ] 무채색 배경 강제 통과 (유채색 배경 자동 탈락 확인)
- [ ] MLB 로고 정확도 통과
- [ ] 재생성 루프 정상 작동 확인

### 8.4 검증

- [ ] `background_compliance` Auto-Fail 정상 작동
- [ ] 5개 검증 기준 정상 작동
- [ ] 재생성 로직 실패 원인별 프롬프트 강화 확인
- [ ] 릴리즈 품질 이미지 5장 이상 확보

---

## 9. 참조

### 9.1 관련 워크플로

| 워크플로 | 관계 |
|----------|------|
| 브랜드컷 | 착장 분석 로직 공유, 목적 구분 |
| 착장스왑 | 착장 정확도 검증 로직 유사 |
| 배경교체 | 배경 준수 검증 로직 참조 |
| 포즈변경 | 포즈 프리셋 개념 공유 |

### 9.2 재사용 모듈

| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 착장 VLM 분석 |
| `core/validators/base.py` | 검증기 인터페이스 |
| `core/options.py` | 비율/해상도/비용 옵션 |
| `.claude/skills/*/mlb-prompt-cheatsheet.md` | MLB 브랜드 치트시트 |

### 9.3 정책 문서

| 문서 | 참조 내용 |
|------|----------|
| `CLAUDE.md` | 검수+재생성 필수 패턴, VLM 프롬프트 원칙 |
| `.claude/rules/gemini-policy.md` | 모델 사용 규칙 |
| `.claude/rules/image-options.md` | 옵션 하드코딩 금지 |
| `.claude/rules/workflow-template.md` | 4단계 워크플로 구조 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-02-19 | 초안 작성 (spec.md + outfit-swap-prd.md 기반) | Claude |
