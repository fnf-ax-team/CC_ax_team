# PRD: 포즈 따라하기 (Pose Copy)

> 작성일: 2026-02-19
> 상태: Draft

---

## 1. 개요

### 1.1 목적
레퍼런스 이미지의 **포즈를 소스 이미지 인물에 복제**하는 워크플로.
얼굴·착장·배경을 유지하면서 원하는 포즈로 변환.
원하는 포즈의 레퍼런스 이미지가 있을 때, 재촬영 없이 해당 포즈를 즉시 적용.

### 1.2 타겟 사용자
- 마케팅팀: 동일 모델로 다양한 포즈 버전 필요
- 화보팀: 레퍼런스 포즈를 기존 이미지에 적용
- 이커머스팀: 착장 유지 + 포즈만 변경한 상세페이지 이미지

### 1.3 핵심 가치
| 가치 | 설명 |
|------|------|
| 포즈 정밀 복제 | 레퍼런스 이미지와 높은 유사도의 포즈 재현 |
| 인물 일관성 | 얼굴/착장/체형 100% 유지 |
| 배경 유연성 | 배경 보존 또는 교체 선택 가능 |

### 1.4 워크플로 카테고리
**스왑** - 얼굴/착장 유지, 포즈만 복제, 배경 선택적

---

## 2. 요구사항

### 2.1 필수 기능 (Must Have)
- [x] 소스 이미지 얼굴 100% 보존
- [x] 소스 이미지 착장 100% 보존 (색상/로고/디테일)
- [x] 레퍼런스 이미지 포즈 정확 복제 (관절 위치/앵글/프레이밍)
- [x] 포즈 혼합(pose mixing) 방지 — Reference는 API 직접 전달, Source는 VLM 텍스트만
- [x] 레퍼런스 이미지 1장 필수 (정확도 보장을 위해 단일 레퍼런스)
- [x] 전신/반신/상반신 포즈 모두 지원

### 2.2 선택 기능 (Nice to Have)
- [ ] 배경 보존 또는 교체 선택
- [ ] 극단적 포즈 차이 시 단계적 변환 옵션
- [ ] 포즈 유사도 사전 미리보기 (텍스트 설명)

### 2.3 제외 범위 (Out of Scope)
- 얼굴 변경 (→ face-swap 워크플로)
- 착장 변경 (→ outfit-swap 워크플로)
- 텍스트/프리셋 기반 포즈 변경 (→ pose-change 워크플로)
- 배경 전용 교체 (→ background-swap 워크플로)

---

## 3. 입출력 정의

### 3.1 입력

| 입력 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 소스 이미지 | Image | O | 얼굴/착장/체형 보존 대상 (1장) |
| 레퍼런스 이미지 | Image | O | 복제할 포즈 (1장, 필수) |
| 배경 처리 | string | X | "preserve" (기본) 또는 "change" |
| 배경 설명 | string | X | 배경 변경 시 텍스트 설명 |
| 비율 | string | O | 1:1, 3:4, 4:5, 9:16 등 |
| 수량 | int | O | 1, 3, 5장 |
| 화질 | string | O | 1K, 2K, 4K |

### 3.2 출력

| 출력 | 타입 | 설명 |
|------|------|------|
| 생성 이미지 | Image[] | 포즈 복제된 결과물 |
| 검증 결과 | dict | 점수, 등급, 이슈 |
| 분석 로그 | JSON | 소스/레퍼런스 포즈 분석 결과 |

### 3.3 출력 폴더
```
Fnf_studio_outputs/pose_copy/{timestamp}/
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
│                   포즈 따라하기 파이프라인                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 입력 수집                                                     │
│     └─ 소스 이미지 경로                                           │
│     └─ 레퍼런스 이미지 경로 (필수 1장)                             │
│     └─ 배경 처리 선택 (보존/변경)                                  │
│     └─ 옵션 선택 (비율/수량/화질)                                  │
│                                                                  │
│  2. VLM 분석 (병렬)                                               │
│     ├─ analyze_source_person()  → 얼굴/착장/체형 텍스트 추출       │
│     └─ analyze_reference_pose() → 포즈 앵글/관절/프레이밍 텍스트 추출│
│                                                                  │
│  3. 프롬프트 조립                                                  │
│     └─ build_pose_copy_prompt()                                  │
│         ├─ 소스 인물 보존 지시 (얼굴/착장 EXACT, 텍스트 only)       │
│         └─ 레퍼런스 포즈 복제 지시 (이미지 직접 전달)               │
│                                                                  │
│  4. 이미지 생성                                                    │
│     └─ generate_pose_copy()                                      │
│         ├─ 프롬프트 (텍스트)                                       │
│         ├─ 레퍼런스 이미지 (API 직접 전달 — 포즈 정확도)            │
│         └─ 소스 → VLM 분석 텍스트만 사용 (포즈 혼합 방지!)          │
│                                                                  │
│  5. 검증                                                          │
│     └─ PoseCopyValidator.validate()                              │
│         ├─ pose_similarity (레퍼런스 vs 결과)                     │
│         ├─ face_preservation (소스 vs 결과)                       │
│         ├─ outfit_preservation (소스 vs 결과)                     │
│         └─ composition_match (레퍼런스 vs 결과)                   │
│                                                                  │
│  6. 재생성 (실패 시)                                               │
│     └─ 실패 원인별 프롬프트 강화 → 최대 2회                        │
│                                                                  │
│  7. 출력                                                          │
│     └─ 저장 + 결과 반환                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 이미지 전달 전략 (CRITICAL)

**포즈 혼합(pose mixing) 방지를 위한 핵심 원칙:**

| 이미지 | 전달 방식 | 이유 |
|--------|----------|------|
| 레퍼런스 이미지 | **API 직접 전달** | 포즈를 이미지로 읽어야 정확도 높음 |
| 소스 이미지 | **VLM 텍스트만** | API 직접 전달 시 포즈가 혼합될 위험 |

```
1. 프롬프트 (텍스트) — 소스 인물 설명 (VLM 분석 결과) + 포즈 복제 지시
2. 레퍼런스 이미지 (API 직접 전달) — 포즈 참조
```

### 4.3 대화형 질문 설계

**1단계: 경로 입력 (순차 텍스트)**

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "소스 이미지 경로? (얼굴/착장 보존 대상)" | O |
| 2 | "레퍼런스 이미지 경로? (복제할 포즈, 1장)" | O |

**2단계: 포즈 분석 결과 확인**

```
[소스 인물 분석]
- 얼굴: 동양 여성, 보정된 피부톤
- 착장: NY 바시티 점퍼 (네이비/화이트) + 카고 데님
- 체형: 슬림, 170cm 추정

[레퍼런스 포즈 분석]
- 앵글: 로우앵글 (아래에서 위로)
- 프레이밍: 전신
- 자세: 양팔 벌림, 하늘 바라봄
- 관절: 팔꿈치 90도 굽힘, 다리 어깨너비 벌림

[주의] 포즈 차이가 큰 경우 결과 품질이 저하될 수 있습니다.
```

**3단계: 배경 처리 (AskUserQuestion)**

```python
AskUserQuestion(questions=[
    {
        "question": "배경을 어떻게 처리할까요?",
        "header": "배경 처리",
        "options": [
            {"label": "보존 (Recommended)", "description": "소스 이미지 배경 유지"},
            {"label": "변경", "description": "새 배경 텍스트로 지정"}
        ],
        "multiSelect": False
    }
])
```

**4단계: 생성 옵션 (AskUserQuestion)**

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

| 기준 | 비중 | 설명 | Pass 기준 |
|------|------|------|----------|
| pose_similarity | 50% | 레퍼런스 포즈와 결과 포즈 유사도 (앵글/관절/프레이밍) | >= 85 |
| face_preservation | 20% | 소스 인물 얼굴 동일성 | >= 90 |
| outfit_preservation | 20% | 소스 착장 보존 (색상/로고/디테일) | >= 90 |
| composition_match | 10% | 레퍼런스와 화면 구성 일치 (카메라 앵글/거리) | >= 80 |

**Pass Condition**: `total_score >= 92`

### 5.2 등급 체계

| 등급 | 점수 | 판정 |
|------|------|------|
| S | 95+ | 바로 사용 |
| A | 92+ | 바로 사용 |
| B | 85+ | 확인 필요 |
| C | 75+ | 재생성 권장 |
| F | 75- | 재생성 필수 |

### 5.3 Auto-Fail 조건

| 조건 | 설명 |
|------|------|
| 얼굴 다른 사람 | face_preservation < 90 |
| 포즈 유사도 낮음 | pose_similarity < 85 |
| 착장 색상/로고 불일치 | outfit_preservation < 90 |
| 손가락 6개 이상 / 기형 | 공통 Auto-Fail |
| 누런 톤 (warm cast) | 공통 Auto-Fail |
| 의도하지 않은 텍스트 | 공통 Auto-Fail |
| AI 플라스틱 피부 | 공통 Auto-Fail |

### 5.4 VLM 검증 프롬프트 설계 (pose_similarity)

VLM 프롬프트 작성 원칙에 따라 step-by-step 강제:

```
### pose_similarity ★★★ [REFERENCE IMAGE]와 반드시 비교! ★★★

[STEP 1] REFERENCE IMAGE 포즈 분석:
- REF 앵글 = ?
- REF 프레이밍 = ?
- REF 팔 위치 = ?
- REF 다리 위치 = ?
- REF 몸통 각도 = ?

[STEP 2] GENERATED IMAGE 포즈 분석:
- GEN 앵글 = ?
- GEN 프레이밍 = ?
- GEN 팔 위치 = ?
- GEN 다리 위치 = ?
- GEN 몸통 각도 = ?

[STEP 3] 비교 및 감점:
- 앵글: 같음(0) / 다름(-20)
- 프레이밍: 같음(0) / 다름(-15)
- 팔 위치: 같음(0) / 유사(-5) / 다름(-10)
- 다리 위치: 같음(0) / 유사(-3) / 다름(-8)
- 몸통 각도: 같음(0) / 유사(-2) / 다름(-7)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:로우앵글+전신+팔벌림, GEN:아이레벨+반신+팔내림, 감점:-35"
```

### 5.5 재생성 로직

| 실패 기준 | 프롬프트 강화 방향 |
|----------|-------------------|
| pose_similarity 실패 | "EXACT same pose as reference image" 강조, 관절별 세부 지시 |
| face_preservation 실패 | "EXACT same face from source person" 강조 |
| outfit_preservation 실패 | 착장 디테일 텍스트 반복 + "PRESERVE outfit EXACTLY" |
| composition_match 실패 | "Same camera angle and framing as reference" 강조 |

**재시도 설정:**
- 최대 재시도: 2회
- Temperature: 0.2 → 0.15 → 0.10

**극단적 포즈 차이 감지 시:**
- VLM이 분석 단계에서 포즈 차이가 극단적임을 감지
- 사용자에게 "단계적 변환"을 제안 (중간 포즈 레퍼런스 추가)
- 또는 pose-change 워크플로 사용 권장

---

## 6. 기술 설계

### 6.1 모듈 구조

```
core/pose_copy/
├── __init__.py           # 통합 진입점 (pose_copy, generate_with_validation)
├── analyzer.py           # analyze_reference_pose(), analyze_source_person()
├── prompt_builder.py     # build_pose_copy_prompt()
├── generator.py          # generate_pose_copy()
├── validator.py          # PoseCopyValidator
└── templates.py          # VLM 프롬프트 템플릿
```

### 6.2 기존 모듈 재사용

| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 소스 착장 분석 (이미 구현됨) |
| `core/validators/base.py` | 검증기 베이스 클래스 |
| `core/api.py` | API 키 로테이션 |
| `core/config.py` | 모델 상수 (IMAGE_MODEL, VISION_MODEL) |

### 6.3 API 사용

| 용도 | 모델 | Temperature |
|------|------|-------------|
| 소스 인물 분석 | VISION_MODEL | 0.1 |
| 레퍼런스 포즈 분석 | VISION_MODEL | 0.1 |
| 이미지 생성 | IMAGE_MODEL | 0.2 |
| 검증 | VISION_MODEL | 0.1 |

### 6.4 이미지 전달 순서

```
1. 프롬프트 (텍스트)
   └─ 소스 인물 설명: 얼굴/착장/체형 (VLM 분석 결과)
   └─ 포즈 복제 지시 (레퍼런스 기반)
   └─ 배경 지시 (보존 또는 변경)

2. 레퍼런스 이미지 (API 직접 전달)
   └─ 포즈 앵글/관절/프레이밍 참조용
```

**소스 이미지 전달 금지:**
소스 이미지를 API에 직접 전달하면 포즈 혼합(pose mixing)이 발생.
소스 인물 정보는 반드시 VLM 분석 텍스트로만 전달.

### 6.5 WorkflowType 등록

```python
# core/validators/base.py
class WorkflowType(Enum):
    # 기존
    BRANDCUT = "brandcut"
    BACKGROUND_SWAP = "background_swap"
    SELFIE = "selfie"
    UGC = "ugc"
    FACE_SWAP = "face_swap"
    OUTFIT_SWAP = "outfit_swap"

    # 신규
    POSE_COPY = "pose_copy"  # 추가
```

---

## 7. 핵심 불변량 (Core Invariants)

### 7.1 보존 규칙

| 구분 | 요소 | 변경 허용 |
|------|------|----------|
| **must_preserve** | 얼굴 (동일 인물) | 절대 불가 |
| **must_preserve** | 착장 (색상/로고/디테일) | 절대 불가 |
| **must_preserve** | 체형 | 절대 불가 |
| **must_copy** | 포즈 (앵글/관절/프레이밍) | 레퍼런스 기준 |
| **optional** | 배경 | 보존 또는 변경 선택 가능 |

### 7.2 포즈 드레이핑 규칙

포즈가 바뀌면 착장 드레이핑도 포즈에 맞게 자연스럽게 변해야 함:
- 팔 들어올림 → 소매/겨드랑이 주름 변화
- 상체 기울임 → 상의 드레이프 변화
- 다리 벌림/모음 → 하의 실루엣 변화
- 물리적으로 불가능한 착장 드레이핑 X

### 7.3 포즈 혼합 방지 원칙

```
WRONG:  소스 이미지 → API 직접 전달  → 포즈가 소스와 레퍼런스 혼합됨
RIGHT:  소스 이미지 → VLM 분석 텍스트만 → 포즈 혼합 없음
        레퍼런스   → API 직접 전달      → 포즈 정확히 복제
```

---

## 8. 테스트 계획

### 8.1 테스트 케이스

| # | 시나리오 | 입력 | 예상 결과 |
|---|---------|------|----------|
| 1 | 기본 포즈 복제 | 서있는 소스 + 다른 자세 레퍼런스 | 레퍼런스 포즈로 변환, 얼굴/착장 유지 |
| 2 | 앵글 변화 | 정면 소스 + 로우앵글 레퍼런스 | 앵글 변화, 인물 보존 |
| 3 | 프레이밍 변화 | 반신 소스 + 전신 레퍼런스 | 전신 프레이밍으로 변환 |
| 4 | 팔 포즈 변화 | 손 모은 소스 + 팔 벌린 레퍼런스 | 팔 포즈만 변경 |
| 5 | 배경 보존 | 실외 배경 소스 | 배경 유지 |
| 6 | 배경 변경 | 실외 배경 + "스튜디오 흰 배경" | 배경 교체 |
| 7 | MLB 착장 보존 | NY 로고 착장 소스 | 포즈 변경 후 로고 정확도 |
| 8 | 극단적 포즈 차이 | 정면 서있는 자세 + 누워있는 포즈 | 경고 메시지 + 단계적 변환 권장 |

### 8.2 테스트 파일 위치
```
tests/pose_copy/
├── test_basic.py               # 기본 포즈 복제
├── test_pose_similarity.py     # 포즈 유사도 검증
├── test_preservation.py        # 얼굴/착장 보존
├── test_background.py          # 배경 처리 (보존/변경)
└── test_integration.py         # 통합 테스트
```

---

## 9. 릴리즈 체크리스트

### 9.1 코드 완성도
- [ ] core/pose_copy/ 모듈 완성
- [ ] PoseCopyValidator 구현 (`@ValidatorRegistry.register`)
- [ ] generate_with_validation() 구현
- [ ] analyze_reference_pose() 구현
- [ ] analyze_source_person() 구현
- [ ] 에러 핸들링 완료

### 9.2 문서화
- [ ] SKILL.md 작성
- [ ] CLAUDE.md 품질 검증 기준 섹션에 pose_copy 추가
- [ ] core/validators/__init__.py에 WorkflowType.POSE_COPY 추가

### 9.3 테스트
- [ ] 기본 포즈 복제 통과
- [ ] 얼굴 보존 통과
- [ ] 착장 보존 통과
- [ ] MLB 로고 정확도 통과

### 9.4 검증
- [ ] 검증 기준 정상 작동 (total_score >= 92)
- [ ] 재생성 로직 정상 작동 (최대 2회)
- [ ] 릴리즈 품질 이미지 5장 이상 확보

---

## 10. 참조

### 10.1 관련 워크플로
| 워크플로 | 관계 |
|----------|------|
| 포즈 변경 (pose-change) | 텍스트/프리셋 기반 포즈 변경 (레퍼런스 이미지 없음) |
| 착장 스왑 (outfit-swap) | 보존 검증 로직 유사 |
| 레퍼런스 브랜드컷 | 레퍼런스 이미지 직접 전달 패턴 공유 |
| 얼굴 교체 (face-swap) | 대칭 구조 (얼굴 교체 vs 포즈 교체) |

### 10.2 재사용 모듈
| 모듈 | 용도 |
|------|------|
| `core/outfit_analyzer.py` | 소스 착장 VLM 분석 |
| `core/validators/base.py` | 검증기 인터페이스 |
| `.claude/skills/*/mlb-prompt-cheatsheet.md` | MLB 브랜드 치트시트 |

### 10.3 spec.md 참조
- 파일: `.omc/autopilot/spec.md`
- 관련 섹션: Part 2.2 (pose_copy validation criteria), Part 3.2 (pose mixing risk)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-02-19 | 초안 작성 (spec.md + outfit-swap-prd.md 기반) | Claude |
