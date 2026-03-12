# PRD: 다중 얼굴 교체 (Multi-Face Swap)

> 작성일: 2026-02-19
> 상태: Draft

---

## 1. 개요

### 1.1 목적
단체 사진에서 **포즈/착장/배경을 100% 보존**하면서 **여러 명의 얼굴을 동시에 교체**하는 워크플로.
개별 얼굴 교체를 N회 반복하지 않고, N명을 한 번에 처리하여 시간을 절감하고 얼굴 간 일관성을 확보.

### 1.2 타겟 사용자
- 마케팅팀: 단체 캠페인 컷에서 특정 모델 얼굴 교체
- 이커머스팀: 단체 착장 컷 재활용 (얼굴만 변경)
- AX팀: 대량 단체 화보 배리에이션 생성

### 1.3 핵심 가치
| 가치 | 설명 |
|------|------|
| 효율성 | 단체 사진 N명 얼굴을 한 번에 처리 |
| 일관성 | 단일 생성에서 모든 얼굴 교체 → 색온도/조명/퀄리티 균일 |
| 보존성 | 포즈/착장/배경 100% 유지 |

### 1.4 워크플로 카테고리
**스왑** — 얼굴 N개 교체, 포즈/착장/배경 유지

---

## 2. 요구사항

### 2.1 필수 기능 (Must Have)
- [x] 소스 단체 이미지에서 N명 얼굴 동시 교체
- [x] 포즈 100% 보존 (관절 위치, 자세)
- [x] 착장 100% 보존 (색상/로고/디테일)
- [x] 배경 100% 보존
- [x] 얼굴-인물 매핑 (face_mapping: 누가 누구를 대체하는지 명시)
- [x] 5명 이하 권장, 10명 초과 시 거부
- [x] 얼굴 겹침 감지 시 순차 처리 폴백

### 2.2 선택 기능 (Nice to Have)
- [ ] 일부 인물만 선택적 교체 (나머지 원본 유지)
- [ ] 교체 결과 인물별 개별 검수 리포트
- [ ] 얼굴 위치 자동 감지 + 매핑 UI 보조

### 2.3 제외 범위 (Out of Scope)
- 포즈 변경 (→ pose-change 워크플로)
- 배경 변경 (→ background-swap 워크플로)
- 착장 변경 (→ outfit-swap 워크플로)
- 단일 얼굴 교체 (→ face-swap 워크플로)
- 비디오 얼굴 교체

---

## 3. 입출력 정의

### 3.1 입력

| 입력 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 소스 이미지 | Image | O | 단체 사진 원본 (1장) |
| face_mapping | dict[] | O | [{source_position: "left", face_image: Image}, ...] |
| 비율 | string | O | 1:1, 3:4, 4:5, 9:16 등 |
| 수량 | int | O | 1, 3, 5장 |
| 화질 | string | O | 1K, 2K, 4K |

**face_mapping 구조:**
```python
face_mapping = [
    {"position": "leftmost",  "face_image": face_img_1},  # 왼쪽 인물 → face_img_1
    {"position": "center",    "face_image": face_img_2},  # 가운데 인물 → face_img_2
    {"position": "rightmost", "face_image": face_img_3},  # 오른쪽 인물 → face_img_3
]
```

### 3.2 출력

| 출력 | 타입 | 설명 |
|------|------|------|
| 생성 이미지 | Image[] | N명 얼굴이 교체된 단체 결과물 |
| 검증 결과 | dict | 점수, 등급, 인물별 이슈 |
| 분석 로그 | JSON | 소스 분석, 매핑 결과, 시도 이력 |

### 3.3 출력 폴더
```
Fnf_studio_outputs/multi_face_swap/{timestamp}/
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
│                  다중 얼굴 교체 파이프라인                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 입력 수집                                                     │
│     └─ 소스 단체 이미지 경로                                       │
│     └─ 인물별 교체 얼굴 이미지 경로 (N개)                          │
│     └─ 옵션 선택 (비율/수량/화질)                                  │
│                                                                  │
│  2. VLM 분석 (병렬)                                               │
│     ├─ detect_faces()    → 소스에서 인물 위치/수 감지              │
│     ├─ analyze_group()   → 포즈/착장/배경 분석                    │
│     └─ map_faces()       → 인물 위치와 face_mapping 연결          │
│                                                                  │
│  3. 얼굴 겹침 확인                                                 │
│     ├─ 겹침 없음 → 동시 처리                                       │
│     └─ 겹침 감지 → 순차 처리 폴백 (위치 순서대로)                  │
│                                                                  │
│  4. 프롬프트 조립                                                  │
│     └─ build_multi_swap_prompt()                                 │
│         ├─ 소스 보존 지시 (포즈/착장/배경 EXACT)                   │
│         └─ N명 얼굴 교체 지시 (위치별 매핑)                        │
│                                                                  │
│  5. 이미지 생성                                                    │
│     └─ generate_multi_swap()                                     │
│         ├─ 프롬프트                                               │
│         ├─ 소스 이미지 (직접 전달)                                 │
│         └─ N개 얼굴 이미지 (위치 순서대로 직접 전달)               │
│                                                                  │
│  6. 검증                                                          │
│     └─ MultiFaceSwapValidator.validate()                         │
│         ├─ all_faces_identity (N명 전원 동일성)                   │
│         ├─ face_consistency (얼굴 간 색온도/조명 균일)             │
│         ├─ pose_preservation (소스 vs 결과)                       │
│         ├─ outfit_preservation (소스 vs 결과)                     │
│         └─ edge_quality (경계 품질)                               │
│                                                                  │
│  7. 재생성 (실패 시)                                               │
│     └─ 실패 원인별 프롬프트 강화 → 최대 2회                        │
│                                                                  │
│  8. 출력                                                          │
│     └─ 저장 + 결과 반환                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 대화형 질문 설계

**1단계: 경로 입력 (순차 텍스트)**

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "소스 단체 이미지 경로?" | O |
| 2 | "교체할 얼굴 이미지들 경로? (쉼표 구분, 왼쪽→오른쪽 순서)" | O |

**2단계: 소스 분석 결과 확인**

```
소스 분석 결과:
- 감지된 인물: 3명
- 인물 위치: 왼쪽 / 가운데 / 오른쪽

얼굴 매핑 확인:
| 위치 | 원본 인물 | 교체 얼굴 |
|------|----------|----------|
| 왼쪽 | 인물 A   | face_01.jpg |
| 가운데 | 인물 B | face_02.jpg |
| 오른쪽 | 인물 C | face_03.jpg |

이 매핑이 맞나요? (확인 후 진행)
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

| 기준 | 비중 | 설명 | Auto-Fail |
|------|------|------|-----------|
| all_faces_identity | 40% | N명 전원 얼굴 동일성 (각 참조 이미지 vs 결과) | < 90 |
| face_consistency | 20% | 얼굴 간 색온도/조명/피부톤 균일도 | < 85 |
| pose_preservation | 20% | 포즈 유지 (관절 위치, 전체 자세) | < 95 |
| outfit_preservation | 15% | 착장 보존 (색상/로고/디테일) | < 95 |
| edge_quality | 5% | 얼굴-신체 경계 품질 (N개 모두) | < 80 |

**Pass Condition:** `total_score >= 92`

### 5.2 all_faces_identity 세부 기준

N명 전원을 개별 평가하여 가장 낮은 점수를 대표값으로 사용.

```
인물별 점수 = [face1_score, face2_score, ..., faceN_score]
all_faces_identity = min(인물별 점수)   # 한 명이라도 실패하면 전체 실패
```

### 5.3 등급 체계

| 등급 | 점수 | 판정 |
|------|------|------|
| S | 97+ | 바로 사용 |
| A | 92+ | 바로 사용 |
| B | 87+ | 확인 필요 |
| C | 80+ | 재생성 권장 |
| F | 80- | 재생성 필수 |

### 5.4 Auto-Fail 조건

| 조건 | 설명 |
|------|------|
| 한 명이라도 다른 사람 | all_faces_identity < 90 (최솟값 기준) |
| 포즈 변경됨 | pose_preservation < 95 |
| 착장 색상/로고 불일치 | outfit_preservation < 95 |
| 누런 톤 (warm cast) | 색온도 위반 |
| 얼굴-신체 경계 불자연 | edge_quality < 80 |

### 5.5 인원 제한 정책

| 인원 수 | 처리 방식 |
|---------|----------|
| 1~5명 | 정상 처리 (권장) |
| 6~10명 | 경고 + 품질 저하 안내 후 처리 |
| 11명 이상 | 거부 (품질 보장 불가) |

### 5.6 VLM 검수 프롬프트 구조 (CRITICAL)

CLAUDE.md 원칙 준수: 단계별 강제 출력으로 VLM 비교 건너뜀 방지.

**all_faces_identity 검수 프롬프트 예시:**
```
### all_faces_identity (N명 전원 동일성 확인)

[STEP 1] 참조 얼굴 분석:
- REF_1 특징 = ? (피부톤, 눈/코/입 비율, 윤곽)
- REF_2 특징 = ?
- REF_N 특징 = ?

[STEP 2] 결과 이미지 인물 분석 (위치별):
- GEN 왼쪽 인물 특징 = ?
- GEN 가운데 인물 특징 = ?
- GEN 오른쪽 인물 특징 = ?

[STEP 3] 매핑 비교 및 감점:
- 왼쪽: REF_1과 일치(0) / 불일치(-30)
- 가운데: REF_2와 일치(0) / 불일치(-30)
- 오른쪽: REF_N과 일치(0) / 불일치(-30)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF1:맞음, REF2:맞음, REF3:불일치(피부톤 차이), 감점:-30"
```

### 5.7 재생성 로직

| 실패 기준 | 프롬프트 강화 방향 |
|----------|-------------------|
| all_faces_identity 실패 | 실패 인물 위치 명시 + "EXACT same face" 강조 |
| face_consistency 실패 | "uniform lighting and skin tone across all persons" 추가 |
| pose_preservation 실패 | "EXACT same pose, joint positions unchanged" 강조 |
| outfit_preservation 실패 | 착장 디테일 반복 + "DO NOT change any clothing" 강조 |
| edge_quality 실패 | "seamless face integration, natural neck/jawline" 추가 |

**재시도 설정:**
- 최대 재시도: 2회
- Temperature: 0.2 → 0.15 → 0.1

---

## 6. 기술 설계

### 6.1 모듈 구조

```
core/multi_face_swap/
├── __init__.py           # 통합 진입점: multi_face_swap(), generate_with_validation()
├── detector.py           # detect_faces(), map_faces()
├── analyzer.py           # analyze_group_photo() — 포즈/착장/배경 분석
├── prompt_builder.py     # build_multi_swap_prompt()
├── generator.py          # generate_multi_swap() — 동시/순차 처리 분기
├── validator.py          # MultiFaceSwapValidator (@ValidatorRegistry.register)
└── templates.py          # VLM 프롬프트 템플릿
```

### 6.2 기존 모듈 재사용

| 모듈 | 용도 |
|------|------|
| `core/face_swap/analyzer.py` | 단일 얼굴 분석 로직 참조 |
| `core/validators/base.py` | 검증기 베이스 클래스 |
| `core/api.py` | API 키 로테이션 |
| `core/config.py` | 모델 상수 (IMAGE_MODEL, VISION_MODEL) |
| `core/options.py` | 비율/해상도/비용 옵션 |

### 6.3 API 사용

| 용도 | 모델 | Temperature |
|------|------|-------------|
| 인물 감지/분석 | VISION_MODEL | 0.1 |
| 단체 이미지 분석 | VISION_MODEL | 0.1 |
| 이미지 생성 | IMAGE_MODEL | 0.2 |
| 검증 | VISION_MODEL | 0.1 |

### 6.4 이미지 전달 순서

```
1. 프롬프트 (텍스트) — 매핑 지시 + 소스 보존 지시
2. 소스 이미지 (첫 번째) — 포즈/착장/배경 보존 대상
3. 얼굴 이미지들 — 위치 순서대로 (왼쪽→오른쪽)
   예: [face_left.jpg, face_center.jpg, face_right.jpg]
```

**핵심 원칙:**
- 소스 이미지: API 직접 전달 (포즈/착장/배경 정확 보존)
- 얼굴 이미지: API 직접 전달 (위치 순서 준수 필수)

### 6.5 동시 처리 vs 순차 처리

```python
# 얼굴 겹침 감지
overlap_detected = detector.check_overlap(source_image, face_positions)

if not overlap_detected:
    # 동시 처리: 모든 얼굴을 한 번에 교체 (품질 균일)
    result = generate_all_at_once(source, face_mapping)
else:
    # 순차 처리 폴백: 왼쪽→오른쪽 순서로 1명씩 처리
    result = generate_sequential(source, face_mapping)
```

### 6.6 WorkflowType 등록

```python
# core/validators/__init__.py
class WorkflowType(Enum):
    # 기존
    BRANDCUT = "brandcut"
    BACKGROUND_SWAP = "background_swap"
    SELFIE = "selfie"
    UGC = "ugc"

    # 신규
    MULTI_FACE_SWAP = "multi_face_swap"
```

---

## 7. 핵심 불변량 (Core Invariants)

### 7.1 보존 규칙

| 구분 | 요소 | 변경 허용 |
|------|------|----------|
| must_preserve | 포즈 (관절 위치, 전체 자세) | 절대 불가 |
| must_preserve | 착장 (색상/로고/소재/디테일) | 절대 불가 |
| must_preserve | 배경 | 절대 불가 |
| must_preserve | 체형 | 절대 불가 |
| must_change | N명 얼굴 | 필수 변경 |
| flexible | 얼굴-신체 경계 블렌딩 | 자연스럽게 처리 |

### 7.2 N명 처리 원칙

- 매핑 순서가 결과 품질에 영향: 위치를 명확히 지정
- 한 명이라도 실패하면 전체 재생성 (부분 재생성 없음)
- 겹침 처리 순서: 항상 왼쪽→오른쪽 (화면 기준)

---

## 8. 테스트 계획

### 8.1 테스트 케이스

| # | 시나리오 | 입력 | 예상 결과 |
|---|---------|------|----------|
| 1 | 2명 교체 기본 | 2인 단체 + 얼굴 2개 | 2명 얼굴 정확 교체 |
| 2 | 3명 교체 기본 | 3인 단체 + 얼굴 3개 | 3명 얼굴 정확 교체 |
| 3 | 5명 교체 (권장 최대) | 5인 단체 + 얼굴 5개 | 5명 얼굴 교체, 품질 확인 |
| 4 | 일부 교체 | 3인 단체 + 얼굴 2개 | 지정 2명만 교체, 1명 원본 유지 |
| 5 | 10명 교체 (경계) | 10인 단체 + 얼굴 10개 | 경고 + 처리 (품질 저하 예상) |
| 6 | 11명 초과 | 11인 이상 단체 | 거부 메시지 출력 |
| 7 | 얼굴 겹침 | 겹친 인물이 있는 사진 | 순차 처리 폴백 |
| 8 | 포즈 보존 확인 | 다양한 포즈 단체 | 포즈 100% 유지 |
| 9 | 착장 보존 확인 | MLB 로고 착장 | 로고/색상 100% 유지 |

### 8.2 테스트 파일 위치
```
tests/multi_face_swap/
├── test_basic_2persons.py      # 2명 기본 교체
├── test_basic_3persons.py      # 3명 기본 교체
├── test_limit_5persons.py      # 5명 권장 최대
├── test_limit_10persons.py     # 10명 경계 케이스
├── test_reject_11plus.py       # 11명 이상 거부
├── test_overlap_fallback.py    # 겹침 순차 처리
├── test_pose_preserve.py       # 포즈 보존
├── test_outfit_preserve.py     # 착장 보존
└── test_integration.py         # 전체 파이프라인
```

---

## 9. 릴리즈 체크리스트

### 9.1 코드 완성도
- [ ] `core/multi_face_swap/` 모듈 완성
- [ ] `detector.py` — 인물 감지/매핑 구현
- [ ] `analyzer.py` — 단체 사진 분석 구현
- [ ] `validator.py` — MultiFaceSwapValidator 구현 + ValidatorRegistry 등록
- [ ] `generator.py` — 동시 처리 + 순차 폴백 구현
- [ ] `generate_with_validation()` 구현 (max_retries=2)
- [ ] 인원 제한 로직 (5명 권장, 10명 경고, 11명 거부) 구현
- [ ] 에러 핸들링 완료

### 9.2 문서화
- [ ] SKILL.md 작성 (`.claude/skills/다중얼굴교체_multi-face-swap/`)
- [ ] CLAUDE.md 업데이트 (검증 기준 섹션)
- [ ] `core/validators/__init__.py`에 WorkflowType.MULTI_FACE_SWAP 추가

### 9.3 테스트
- [ ] 2명 케이스 통과
- [ ] 3명 케이스 통과
- [ ] 5명 케이스 통과 (권장 최대)
- [ ] 10명 경계 케이스 처리 확인
- [ ] 11명 거부 확인
- [ ] 겹침 폴백 동작 확인
- [ ] 포즈/착장 보존 통과

### 9.4 검증
- [ ] MultiFaceSwapValidator 정상 작동
- [ ] all_faces_identity 최솟값 로직 정상 작동
- [ ] 재생성 로직 정상 작동 (최대 2회)
- [ ] 릴리즈 품질 이미지 5장 이상 확보

---

## 10. 참조

### 10.1 관련 워크플로
| 워크플로 | 관계 |
|----------|------|
| 얼굴 교체 (face-swap) | 단일 얼굴 교체 — 핵심 로직 공유 |
| 착장 스왑 (outfit-swap) | 보존 검증 로직 유사 |
| 배경교체 (background-swap) | 이미지 보존 패턴 참조 |

### 10.2 재사용 모듈
| 모듈 | 용도 |
|------|------|
| `core/face_swap/` | 단일 얼굴 교체 로직 참조 |
| `core/validators/base.py` | 검증기 인터페이스 |
| `core/api.py` | API 키 로테이션 |
| `core/options.py` | 비율/해상도/비용 옵션 |

### 10.3 spec 참조
- `D:\FNF_Studio_TEST\New-fnf-studio\.omc\autopilot\spec.md` — Part 2: 검증 기준 원본

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-02-19 | 초안 작성 (spec.md + outfit-swap-prd.md 기반) | Claude |
