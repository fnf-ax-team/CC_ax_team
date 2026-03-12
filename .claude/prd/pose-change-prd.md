# PRD: 포즈 변경 (Pose Change)

> 작성일: 2026-02-19
> 상태: Draft

---

## 1. 개요

### 1.1 목적

기존 이미지의 **얼굴/착장/배경을 100% 보존**하면서 **포즈만 변경**하는 워크플로.
텍스트 기반 프리셋 7종 또는 커스텀 지시로 포즈를 바꿔 재촬영 없이 다양한 포즈 버전 생성.

### 1.2 타겟 사용자

- 마케팅팀: 같은 모델/착장으로 다양한 포즈 버전 필요
- 이커머스팀: 상세페이지용 포즈 변형 (전면/측면/동적)
- 콘텐츠팀: SNS용 포즈 다양화 (스토리, 릴스 등)

### 1.3 핵심 가치

| 가치 | 설명 |
|------|------|
| 시간 절약 | 재촬영 없이 포즈 변경 |
| 일관성 | 동일 모델/착장/배경 유지 |
| 안전성 | 물리적 불가능 포즈 자동 거부 |
| 확장성 | 프리셋 + 커스텀 모두 지원 |

### 1.4 워크플로 카테고리

**스왑** - 포즈만 변경, 얼굴/착장/배경 유지

---

## 2. 요구사항

### 2.1 필수 기능 (Must Have)

- [x] 소스 이미지 얼굴 100% 보존
- [x] 소스 이미지 착장 100% 보존 (색상/로고/디테일)
- [x] 소스 이미지 배경 100% 보존
- [x] 7종 포즈 프리셋 지원
- [x] 커스텀 포즈 텍스트 지원 (VLM 검증 필수)
- [x] 물리적 불가능 포즈 VLM 검증 후 거부
- [x] 포즈 변경 후 착장 드레이핑 자연스러움 유지

### 2.2 선택 기능 (Nice to Have)

- [ ] 프리셋 조합 (예: lean_wall + arms_crossed)
- [ ] 강도 조절 (subtle / natural / dramatic)
- [ ] 포즈 미리보기 스케치 생성

### 2.3 제외 범위 (Out of Scope)

- 얼굴 변경 (→ face-swap 워크플로)
- 착장 변경 (→ outfit-swap 워크플로)
- 배경 변경 (→ background-swap 워크플로)
- 레퍼런스 이미지 기반 포즈 복제 (→ pose-copy 워크플로)

---

## 3. 입출력 정의

### 3.1 입력

| 입력 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 소스 이미지 | Image | O | 얼굴/착장/배경 보존 대상 (1장) |
| 타겟 포즈 | string | O | 프리셋 키 또는 커스텀 텍스트 |
| 비율 | string | O | 1:1, 3:4, 4:5, 9:16 등 |
| 수량 | int | O | 1, 3, 5장 |
| 화질 | string | O | 1K, 2K, 4K |

### 3.2 출력

| 출력 | 타입 | 설명 |
|------|------|------|
| 생성 이미지 | Image[] | 포즈 변경된 결과물 |
| 검증 결과 | dict | 점수, 등급, 이슈 |
| 분석 로그 | JSON | 소스/포즈 분석 결과, 시도 이력 |

### 3.3 출력 폴더

```
Fnf_studio_outputs/pose_change/{timestamp}/
├── result_01.png
├── result_02.png
├── result_03.png
└── analysis_log.json
```

---

## 4. 워크플로 설계

### 4.1 단계별 흐름

```
┌──────────────────────────────────────────────────────────────────┐
│                     포즈 변경 파이프라인                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 입력 수집                                                     │
│     └─ 소스 이미지 경로                                           │
│     └─ 포즈 선택 (프리셋 또는 커스텀 텍스트)                       │
│     └─ 옵션 선택 (비율/수량/화질)                                  │
│                                                                  │
│  2. 포즈 검증 (커스텀 선택 시)                                     │
│     └─ VLM으로 포즈 실현 가능성 검증                              │
│     └─ 물리적 불가능 포즈 → 거부 + 대안 제시                      │
│                                                                  │
│  3. VLM 분석 (병렬)                                               │
│     ├─ analyze_current_pose() → 소스 포즈 추출                    │
│     ├─ analyze_outfit_details() → 착장 디테일 추출                │
│     └─ analyze_background() → 배경 텍스트 추출                    │
│                                                                  │
│  4. 프롬프트 조립                                                  │
│     └─ build_pose_change_prompt()                                │
│         ├─ 보존 지시 (얼굴/착장/배경 EXACT)                        │
│         ├─ 포즈 변경 지시 (타겟 포즈 상세 설명)                    │
│         └─ 드레이핑 지시 (포즈에 맞는 착장 흐름)                   │
│                                                                  │
│  5. 이미지 생성                                                    │
│     └─ generate_pose_change()                                    │
│         ├─ 프롬프트                                               │
│         └─ 소스 이미지 (API 직접 전달)                             │
│                                                                  │
│  6. 검증                                                          │
│     └─ PoseChangeValidator.validate()                            │
│         ├─ face_identity (소스 vs 결과)                           │
│         ├─ outfit_preservation (착장 보존)                        │
│         ├─ pose_correctness (타겟 포즈 달성)                      │
│         ├─ physics_plausibility (물리 타당성)                     │
│         └─ lighting_consistency (조명 일관성)                     │
│                                                                  │
│  7. 재생성 (실패 시)                                               │
│     └─ 실패 원인별 프롬프트 강화 → 최대 2회                        │
│                                                                  │
│  8. 출력                                                          │
│     └─ 저장 + 결과 반환                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 포즈 프리셋 정의

```python
POSE_PRESETS = {
    "sit_floor": "sitting on floor, legs crossed",
    "sit_chair": "sitting on chair, natural pose",
    "lean_wall": "leaning against wall, casual",
    "walking": "walking, mid-stride",
    "back_turn": "back to camera, looking over shoulder",
    "arms_crossed": "arms crossed, confident stance",
    "hand_pocket": "hands in pockets, relaxed",
}
```

| 프리셋 키 | 설명 | 활용 |
|----------|------|------|
| `sit_floor` | 바닥에 앉기, 다리 교차 | 캐주얼/에디토리얼 |
| `sit_chair` | 의자에 앉기, 자연스러운 포즈 | 이커머스/화보 |
| `lean_wall` | 벽 기대기, 캐주얼 | SNS/룩북 |
| `walking` | 걷는 포즈, 스트라이드 | 캐주얼/스트릿 |
| `back_turn` | 뒤돌아서기, 어깨 너머 시선 | 에디토리얼 |
| `arms_crossed` | 팔짱 끼기, 자신감 있는 자세 | 브랜드/마케팅 |
| `hand_pocket` | 주머니에 손 넣기, 편안한 자세 | 이커머스/SNS |

### 4.3 커스텀 포즈 VLM 검증 기준

물리적 불가능 판정 기준:

| 판정 | 예시 | 처리 |
|------|------|------|
| 가능 | "한쪽 무릎을 세우고 앉기" | 통과 → 생성 |
| 위험 | "발을 머리 위로 들기" | 경고 후 확인 |
| 불가능 | "팔을 180도 반대로 꺾기" | 거부 + 대안 제시 |

### 4.4 대화형 질문 설계

**1단계: 경로 입력 (순차 텍스트)**

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "소스 이미지 경로?" | O |

**2단계: 포즈 선택 (AskUserQuestion 클릭)**

```python
AskUserQuestion(questions=[
    {
        "question": "변경할 포즈를 선택해주세요",
        "header": "포즈 선택",
        "options": [
            {"label": "sit_floor", "description": "바닥에 앉기 (다리 교차)"},
            {"label": "sit_chair", "description": "의자에 앉기 (자연스러운)"},
            {"label": "lean_wall", "description": "벽 기대기 (캐주얼)"},
            {"label": "walking", "description": "걷는 포즈 (스트라이드)"},
            {"label": "back_turn", "description": "뒤돌아서기 (어깨 너머 시선)"},
            {"label": "arms_crossed", "description": "팔짱 끼기 (자신감)"},
            {"label": "hand_pocket", "description": "주머니에 손 넣기 (편안함)"},
            {"label": "커스텀 입력", "description": "직접 포즈 설명 입력"}
        ],
        "multiSelect": False
    }
])
```

**3단계: 옵션 선택 (AskUserQuestion 클릭)**

```python
AskUserQuestion(questions=[
    {
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "1장", "description": "테스트용"},
            {"label": "3장 (Recommended)", "description": "다양한 결과 비교"},
            {"label": "5장", "description": "충분한 선택지"}
        ],
        "multiSelect": False
    },
    {
        "question": "화질을 선택해주세요",
        "header": "해상도",
        "options": [
            {"label": "1K", "description": "빠른 테스트"},
            {"label": "2K (Recommended)", "description": "일반 출력용"},
            {"label": "4K", "description": "최종 고품질"}
        ],
        "multiSelect": False
    }
])
```

---

## 5. 검증 기준

### 5.1 검증 기준 정의

| 기준 | 비중 | 설명 | Pass Threshold | Auto-Fail |
|------|------|------|----------------|-----------|
| face_identity | 30% | 얼굴 동일성 (소스 vs 결과) | >= 90 | < 85 |
| outfit_preservation | 25% | 착장 보존 (색상/로고/디테일) | >= 90 | < 80 |
| pose_correctness | 25% | 타겟 포즈 달성도 | >= 85 | - |
| physics_plausibility | 15% | 물리적 자연스러움 | >= 80 | < 60 |
| lighting_consistency | 5% | 조명 일관성 | >= 75 | - |

**Pass Condition**: `total_score >= 88`

### 5.2 등급 체계

| 등급 | 점수 | 판정 |
|------|------|------|
| S | 95+ | 바로 사용 |
| A | 90+ | 바로 사용 |
| B | 88+ | 확인 필요 |
| C | 75+ | 재생성 권장 |
| F | 75- | 재생성 필수 |

### 5.3 Auto-Fail 조건

| 조건 | 설명 |
|------|------|
| 얼굴 다른 사람 | face_identity < 85 |
| 착장 색상/로고 불일치 | outfit_preservation < 80 |
| 물리적으로 비자연스러운 포즈 | physics_plausibility < 60 |
| 손가락 6개 이상 / 기형적 손가락 | 공통 Auto-Fail |
| 누런 톤 (warm cast) | 공통 Auto-Fail |
| 의도하지 않은 텍스트/워터마크 | 공통 Auto-Fail |

### 5.4 VLM 검수 프롬프트 원칙 (pose_correctness)

```
[STEP 1] TARGET POSE 분석:
- 목표 포즈 = ?
- 주요 관절 위치 = ?

[STEP 2] GENERATED IMAGE 분석:
- GEN 포즈 = ?
- GEN 관절 위치 = ?

[STEP 3] 비교 및 감점:
- 상체 방향: 일치(0) / 불일치(-15)
- 하체/다리 위치: 일치(0) / 불일치(-20)
- 손/팔 위치: 일치(0) / 불일치(-10)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "TARGET:arms_crossed+정면, GEN:손옆으로+정면, 감점:-20"
```

### 5.5 재생성 로직

| 실패 기준 | 프롬프트 강화 방향 |
|----------|-------------------|
| face_identity 실패 | "EXACT same face, identical person from source image" 강조 |
| outfit_preservation 실패 | 착장 색상/로고/디테일 반복 + "DO NOT change any clothing element" |
| pose_correctness 실패 | 타겟 포즈 설명 구체화 + 관절별 위치 상세 기술 |
| physics_plausibility 실패 | "natural body mechanics, realistic weight distribution" 추가 |

**재시도 설정:**
- 최대 재시도: 2회
- Temperature: 0.25 → 0.20 → 0.15

---

## 6. 기술 설계

### 6.1 모듈 구조

```
core/pose_change/
├── __init__.py           # 통합 진입점 (pose_change, generate_with_validation)
├── presets.py            # POSE_PRESETS dict
├── analyzer.py           # analyze_current_pose(), analyze_outfit_details()
├── prompt_builder.py     # build_pose_change_prompt()
├── generator.py          # generate_pose_change()
├── validator.py          # PoseChangeValidator
└── templates.py          # VLM 프롬프트 템플릿
```

### 6.2 기존 모듈 재사용

| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 착장 분석 (이미 구현됨) |
| `core/validators/base.py` | 검증기 베이스 클래스 |
| `core/api.py` | API 키 로테이션 |
| `core/config.py` | 모델 상수 (IMAGE_MODEL, VISION_MODEL) |
| `core/options.py` | 비율/해상도/비용 옵션 |

### 6.3 API 사용

| 용도 | 모델 | Temperature |
|------|------|-------------|
| 커스텀 포즈 검증 | VISION_MODEL | 0.1 |
| 소스 포즈 분석 | VISION_MODEL | 0.1 |
| 착장 분석 | VISION_MODEL | 0.2 |
| 이미지 생성 | IMAGE_MODEL | 0.25 |
| 검증 | VISION_MODEL | 0.1 |

### 6.4 이미지 전달 순서

```
1. 프롬프트 (텍스트) - 포즈 변경 지시 + 보존 지시 + 착장 상세 설명
2. 소스 이미지 (API 직접 전달) - 얼굴/착장/배경 보존 기준
```

**핵심 원칙:**
- 소스 이미지: **API 직접 전달** (얼굴/착장/배경 정확 보존)
- 배경: VLM 분석 후 텍스트로만 전달 (배경 변경 방지)
- 착장: VLM 분석 결과 텍스트 + 소스 이미지 직접 전달 (이중 보장)

### 6.5 WorkflowType 등록

```python
# core/validators/__init__.py에 추가
from core.validators.base import WorkflowType

class WorkflowType(Enum):
    # 기존
    BRANDCUT = "brandcut"
    BACKGROUND_SWAP = "background_swap"
    SELFIE = "selfie"
    UGC = "ugc"
    FACE_SWAP = "face_swap"
    OUTFIT_SWAP = "outfit_swap"

    # 추가
    POSE_CHANGE = "pose_change"
```

---

## 7. 핵심 불변량 (Core Invariants)

### 7.1 보존 규칙

| 구분 | 요소 | 변경 허용 |
|------|------|----------|
| **must_preserve** | 얼굴 (동일 인물) | 절대 불가 |
| **must_preserve** | 착장 (색상/로고/디테일) | 절대 불가 |
| **must_preserve** | 배경 | 절대 불가 |
| **must_preserve** | 체형 | 절대 불가 |
| **must_change** | 포즈 | 타겟 포즈로 변경 |
| **flexible** | 착장 드레이핑 | 포즈에 맞게 자연스럽게 |
| **flexible** | 그림자 방향 | 포즈 변경에 따라 자연스럽게 |

### 7.2 드레이핑 규칙

포즈 변경 후 착장이 새 포즈에 맞게 자연스럽게 적용되어야 함:
- 앉기 → 바지/스커트 주름
- 팔짱 끼기 → 소매 당김 표현
- 벽 기대기 → 상의 자연스러운 늘어짐
- 걷기 → 바지 스트라이드 주름

### 7.3 물리적 거부 기준

아래 경우는 VLM 검증 단계에서 거부:
- 관절 가동 범위 초과 포즈
- 중력에 반하는 비자연스러운 포즈
- 두 포즈의 모순적 결합 (예: 앉으면서 달리기)

---

## 8. 테스트 계획

### 8.1 테스트 케이스

| # | 시나리오 | 입력 | 예상 결과 |
|---|---------|------|----------|
| 1 | 프리셋 기본 | 소스 이미지 + sit_floor | 바닥 앉기 포즈 + 얼굴/착장/배경 유지 |
| 2 | 프리셋 back_turn | 소스 이미지 + back_turn | 뒤돌아 포즈 + 착장 보존 |
| 3 | 커스텀 포즈 (유효) | 소스 이미지 + "무릎 꿇기" | 포즈 변경 + 보존 |
| 4 | 커스텀 포즈 (불가능) | 소스 이미지 + "팔을 뒤로 180도 꺾기" | 거부 + 대안 제시 |
| 5 | MLB 로고 착장 | NY 로고 착장 소스 + walking | 로고 위치/색상 정확 보존 |
| 6 | 얼굴 보존 확인 | 소스 이미지 + arms_crossed | 얼굴 동일 인물 유지 |
| 7 | 배경 보존 확인 | 배경 있는 소스 + lean_wall | 배경 100% 유지 |
| 8 | 재생성 트리거 | face_identity 실패 케이스 | 자동 재생성 2회 |

### 8.2 테스트 파일 위치

```
tests/pose_change/
├── test_basic.py              # 기본 프리셋 테스트
├── test_custom_pose.py        # 커스텀 포즈 + 물리 검증
├── test_preservation.py       # 얼굴/착장/배경 보존 검증
├── test_mlb_outfit.py         # MLB 착장 로고 보존
└── test_integration.py        # 통합 테스트
```

---

## 9. 릴리즈 체크리스트

### 9.1 코드 완성도

- [ ] `core/pose_change/` 모듈 완성
- [ ] `core/pose_change/presets.py` — POSE_PRESETS 7종 정의
- [ ] `core/pose_change/validator.py` — PoseChangeValidator 구현
- [ ] `core/pose_change/generator.py` — generate_with_validation() 구현
- [ ] `core/validators/__init__.py` — POSE_CHANGE 타입 등록
- [ ] 커스텀 포즈 VLM 검증 로직 구현
- [ ] 에러 핸들링 완료

### 9.2 문서화

- [ ] SKILL.md 작성
- [ ] pose-change-cheatsheet.md 작성 (프리셋 가이드)
- [ ] CLAUDE.md 품질 검증 기준 섹션 업데이트

### 9.3 테스트

- [ ] 7종 프리셋 모두 통과
- [ ] 커스텀 포즈 유효성 검증 통과
- [ ] 물리적 불가능 포즈 거부 동작 확인
- [ ] MLB 착장 보존 통과
- [ ] 얼굴 보존 통과 (face_identity >= 90)

### 9.4 검증

- [ ] PoseChangeValidator 정상 작동
- [ ] 재생성 로직 정상 작동 (최대 2회)
- [ ] 릴리즈 품질 이미지 5장 이상 확보 (프리셋별 최소 1장)

---

## 10. 참조

### 10.1 관련 워크플로

| 워크플로 | 관계 |
|----------|------|
| 착장 스왑 (outfit-swap) | 대칭 구조, 보존 검증 로직 공유 |
| 포즈 따라하기 (pose-copy) | 포즈 달성 검증 로직 유사 |
| 레퍼런스 브랜드컷 | 소스 이미지 분석 패턴 참조 |
| 배경교체 (background-swap) | 배경 보존 검증 로직 참조 |

### 10.2 재사용 모듈

| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 착장 VLM 분석 |
| `core/validators/base.py` | 검증기 인터페이스 |
| `.claude/skills/*/mlb-prompt-cheatsheet.md` | MLB 브랜드 치트시트 |
| `core/options.py` | 비율/해상도/비용 옵션 |

### 10.3 spec.md 참조

- 파일: `.omc/autopilot/spec.md`
- Part 2.1: 파일 구조 (`core/pose_change/`)
- Part 2.2: 검증 기준 (pose_change 섹션)
- Part 3.1: Edge Cases (물리적 불가능 포즈 처리)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-02-19 | 초안 작성 (spec.md + outfit-swap-prd.md 기반) | Claude |
