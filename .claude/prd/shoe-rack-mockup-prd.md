# PRD: 신발장 목업 (Shoe Rack Mockup)

> 작성일: 2026-02-20
> 작성자: Claude Code
> 상태: In Progress (테스트 검증 완료)

---

## 1. 개요

### 1.1 목적

**스케치업 신발장 렌더링 이미지에 실제 신발 제품을 실사처럼 합성하여 회장님 보고용 VMD 시각화 자료 생성.**

**해결하려는 문제:**
- 와이드샷에서 신발 크기가 불일치
- 신발 각도가 슬롯마다 다름
- 중복 신발 발생
- 화질 뭉개짐
- 컬러 마스크 → 실사 변환 필요

**테스트 검증 결과:**
- 색상 마스크 기반 슬롯 감지 성공 (OpenCV) - `test_slot_detection.py`
- Gemini 인페인팅으로 실사 합성 가능 확인 - `test_realistic_placement.py`

### 1.2 타겟 사용자

- VMD 팀 (Visual Merchandising)
- 매장 기획 담당자
- 경영진 보고 자료 제작자

### 1.3 핵심 가치

| 기존 방식 | 이 워크플로 |
|----------|------------|
| 포토샵 수작업 (슬롯당 10분) | 자동 배치 (전체 5분) |
| 크기/각도 수동 조정 | 자동 계산 |
| 품질 불일치 | 일관된 고해상도 |
| 컬러 마스크 수동 변환 | AI 실사 변환 |

### 1.4 워크플로 카테고리

**VMD 카테고리** - 얼굴 없음, 착장(신발) 필수, 브랜드톤 중요

---

## 2. 핵심 불변량 (Core Invariants)

### 2.1 정의

| 불변량 | 우선순위 | 실패 임계값 | 비즈니스 영향 |
|--------|---------|------------|--------------|
| `slot_coverage` | 1 | 100% | 모든 색상 마스크 영역이 신발로 교체되어야 함. 누락 시 미완성 |
| `shoe_accuracy` | 1 | 80 | 참조 신발과 동일한 형태/색상/디테일. 불일치 시 잘못된 상품 노출 |
| `background_preservation` | 1 | 100 | 선반/메쉬/벽 등 배경이 100% 보존되어야 함. 변형 시 렌더링 의미 상실 |
| `size_consistency` | 2 | 80 | 같은 색상 슬롯 내 신발 크기 일관성. 불일치 시 비현실적 |
| `realistic_composite` | 2 | 75 | 실사처럼 자연스러운 합성. AI티 나면 보고용 부적합 |

### 2.2 보존 규칙

```json
{
  "must_change": ["색상 마스크 영역 (신발로)"],
  "must_preserve": ["선반", "메쉬 배경", "벽", "기둥", "조명"],
  "flexible": ["신발 그림자 세부", "신발 반사광"]
}
```

---

## 3. 입출력 정의

### 3.1 입력

| 입력 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 신발장 이미지 | Image | O | 스케치업 렌더링 (색상 마스크 포함) |
| 신발 이미지들 | Image[] | O | side view 신발 제품 이미지 |
| 슬롯 설정 | JSON | X | 색상별 신발 개수/크기 (자동 감지 가능) |

### 3.2 출력

| 출력 | 타입 | 설명 |
|------|------|------|
| 완성 이미지 | Image | 신발 배치 완료된 신발장 |
| 슬롯 분석 | JSON | 감지된 슬롯 좌표/크기 |
| 비교 이미지 | Image | Before/After 비교 |
| 메타데이터 | JSON | 매핑 정보, 설정 |

### 3.3 출력 폴더

```
Fnf_studio_outputs/shoe_rack_mockup/{timestamp}/
├── final/              # 최종 합성 이미지
├── slots/              # 슬롯별 분석 결과
├── comparison/         # Before/After 비교
└── metadata.json       # 전체 메타데이터
```

---

## 4. 워크플로 설계

### 4.1 3단계 컬러 처리 파이프라인

테스트 결과 확인된 핵심 접근법: **색상별 순차 처리**

```
┌─────────────────────────────────────────────────────────────────┐
│                    신발장 목업 워크플로                           │
└─────────────────────────────────────────────────────────────────┘

[STAGE 1] 민트/청록색 영역 처리
    │
    │  └── 각 민트 슬롯 → 신발 2개씩 (작은 사이즈 쌍)
    │      "민트색 실루엣이 2개 신발 윤곽을 나타냄"
    ▼
[STAGE 2] 코랄/분홍색 영역 처리
    │
    │  └── 각 코랄 슬롯 → 신발 1개씩 (큰 사이즈)
    │      "코랄색 영역에 단일 큰 신발 배치"
    ▼
[STAGE 3] 흰색 영역 처리 (기존 신발 유지 또는 교체)
    │
    │  └── 각 흰색 슬롯 → 상태 확인 후 처리
    ▼
[OUTPUT] 최종 합성 이미지
```

### 4.2 단계별 상세

#### Step 1: 슬롯 감지 (OpenCV)

```python
# 테스트 코드에서 검증된 방식
target_colors = {
    "mint": (130, 240, 210),    # 민트/청록 - 신발 2개 쌍
    "coral": (240, 110, 110),   # 코랄/분홍 - 신발 1개
    "white": (255, 255, 255),   # 흰색 - 기존 신발 또는 교체
}
tolerance = 50  # 색상 허용 오차
min_area = 500  # 최소 픽셀 (노이즈 필터)
```

#### Step 2: 슬롯별 설정 적용

| 색상 | 신발 개수 | 크기 | 배치 패턴 |
|------|----------|------|----------|
| 민트 | 2개 | 작음 (pair) | 나란히 |
| 코랄 | 1개 | 큼 (single) | 중앙 |
| 흰색 | 2개 | 중간 | 유지/교체 |

#### Step 3: Gemini 인페인팅

```python
# 테스트 코드에서 검증된 프롬프트 구조
prompt = """Edit ONLY the MINT/CYAN colored areas on the LEFT column of this shoe rack.

LOOK CAREFULLY at the mint/cyan shapes:
- Each mint shape already has a WAVY SILHOUETTE showing TWO SHOES side by side
- The wavy outline represents 2 shoe tops next to each other
- You must fill this silhouette with 2 REALISTIC SNEAKERS matching that outline

Replace the flat mint color with 2 photorealistic small sneakers that FIT the existing wavy silhouette shape.

DO NOT CHANGE:
- Coral/pink areas (keep as flat coral color)
- White shoes on right side
- Shelves, mesh background, blue wall"""
```

#### Step 4: 검증 + 재생성

검증 실패 시 프롬프트 강화 후 재시도 (최대 2회)

### 4.3 대화형 질문 설계

**1단계: 입력 확인**

| 질문 | 옵션 | 기본값 |
|------|------|--------|
| 신발장 이미지 경로 | 경로 입력 | - |
| 신발 이미지 폴더 | 경로 입력 | - |

**2단계: 슬롯 설정**

| 질문 | 옵션 | 기본값 |
|------|------|--------|
| 슬롯 감지 방식 | 자동(색상마스크) / 수동(JSON) | 자동 |
| 색상별 신발 개수 | 민트:2, 코랄:1, 흰색:2 | 기본값 |

**3단계: 출력 옵션**

| 질문 | 옵션 | 기본값 |
|------|------|--------|
| 출력 해상도 | 원본 유지 / 2K / 4K | 원본 유지 |
| 비교 이미지 생성 | 예 / 아니오 | 예 |

---

## 5. 검증 기준

### 5.1 검증 기준 정의

| 기준 | 영문 | 비중 | 설명 | 자동탈락 |
|------|------|------|------|----------|
| 슬롯 완전 커버 | slot_coverage | 25% | 모든 색상 마스크가 신발로 교체됨 | < 100% |
| 신발 정확도 | shoe_accuracy | 25% | 참조 신발과 동일 | < 70 |
| 배경 보존 | background_preservation | 20% | 선반/메쉬/벽 변형 없음 | < 95 |
| 크기 일관성 | size_consistency | 15% | 같은 슬롯 타입 내 크기 편차 | 편차 > 25% |
| 합성 자연스러움 | composite_quality | 15% | 경계선, 그림자, 조명 자연스러움 | - |

### 5.2 등급 체계

| 등급 | 점수 | 판정 |
|------|------|------|
| S | 95+ | 바로 보고 가능 |
| A | 90+ | 바로 사용 |
| B | 85+ | 경미한 수정 필요 |
| C | 75+ | 부분 재생성 필요 |
| F | 75- | 전체 재생성 |

### 5.3 자동 탈락 조건 (Auto-Fail)

- 색상 마스크 영역이 그대로 남아있음 (미처리)
- 선반/메쉬 배경이 변형됨
- 신발이 슬롯 바운딩박스 밖으로 삐져나옴
- 참조 신발과 완전히 다른 신발 생성
- 신발 잘림 (crop)
- 명백한 합성 경계선

### 5.4 재생성 로직

| 실패 기준 | 프롬프트 강화 방향 |
|----------|-------------------|
| 색상 마스크 잔존 | "REPLACE completely" 강조, 색상 hex 명시 |
| 배경 변형 | "DO NOT CHANGE" 리스트 확장 |
| 신발 불일치 | 참조 신발 이미지 추가 전송 |
| 크기 불일치 | "same size as other shoes" 강조 |
| 경계선 보임 | "seamless blend" 키워드 추가 |

**재시도 설정:**
- 최대 재시도: 2회
- Temperature: 0.3 → 0.25 → 0.2
- 단계별 처리 (한 색상씩)

---

## 6. 기술 설계

### 6.1 모듈 구조

```
core/shoe_rack_mockup/
├── __init__.py              # 통합 진입점
├── slot_detector.py         # 색상 마스크 기반 슬롯 감지 (OpenCV)
├── slot_config.py           # 색상별 설정 (개수, 크기, 패턴)
├── compositor.py            # Gemini 인페인팅 엔진
├── validator.py             # 검증 로직
└── templates.py             # 프롬프트 템플릿
```

### 6.2 핵심 클래스

```python
@dataclass
class SlotColor:
    """슬롯 색상 타입 정의"""
    name: str                      # "mint", "coral", "white"
    rgb: Tuple[int, int, int]      # (130, 240, 210)
    shoes_per_slot: int            # 2, 1, 2
    shoe_size: str                 # "small", "large", "medium"
    placement_pattern: str         # "side_by_side", "center"

@dataclass
class DetectedSlot:
    """감지된 슬롯"""
    id: str                        # "mint_1", "coral_3"
    color_type: str                # "mint", "coral", "white"
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    center: Tuple[int, int]
    area: int

@dataclass
class MockupResult:
    """목업 결과"""
    image: Image.Image
    slots_processed: int
    validation_score: int
    grade: str
    metadata: dict
```

### 6.3 API 사용

| 용도 | 모델 | Temperature |
|------|------|-------------|
| 슬롯 감지 | OpenCV (로컬) | - |
| 인페인팅 | gemini-3-pro-image-preview | 0.3 |
| 품질 검증 | gemini-3-flash-preview | 0.1 |

### 6.4 스킬 파일 구조

```
.claude/skills/신발장목업_shoe-rack-mockup/
├── SKILL.md                     # 스킬 정의 (간결하게)
├── slot-colors.json             # 색상별 설정
└── prompt-templates/            # 프롬프트 템플릿
    ├── stage1_mint.txt
    ├── stage2_coral.txt
    └── stage3_white.txt
```

---

## 7. 구현 우선순위

### Phase 1: MVP (현재)

- [x] 색상 마스크 기반 슬롯 감지 - `test_slot_detection.py`
- [x] 단일 색상 인페인팅 테스트 - `test_realistic_placement.py`
- [ ] 3단계 순차 처리 파이프라인
- [ ] 기본 검증 로직

### Phase 2: 완성

- [ ] 검증 + 재생성 루프
- [ ] 신발 매핑 (어떤 신발을 어떤 슬롯에)
- [ ] 다중 섹션 조립 (전체 와이드샷)

### Phase 3: 고도화

- [ ] 웹 UI (드래그앤드롭)
- [ ] 실시간 미리보기
- [ ] 배치 처리 (여러 신발장)

---

## 8. 테스트 계획

### 8.1 테스트 케이스

| # | 시나리오 | 입력 | 예상 결과 |
|---|---------|------|----------|
| 1 | 민트 슬롯 감지 | 2.png | 민트색 영역 N개 감지 |
| 2 | 코랄 슬롯 감지 | 2.png | 코랄색 영역 M개 감지 |
| 3 | 민트 → 신발 2개 | 민트 슬롯 + 신발 | 2개 신발 자연스럽게 배치 |
| 4 | 코랄 → 신발 1개 | 코랄 슬롯 + 신발 | 1개 신발 중앙 배치 |
| 5 | 배경 보존 | 전체 | 선반/메쉬/벽 변형 없음 |
| 6 | 크기 일관성 | 같은 색상 슬롯 | 크기 편차 < 20% |

### 8.2 테스트 파일 위치

```
tests/shoe_rack_mockup/
├── test_slot_detection.py     # 슬롯 감지 테스트 (완료)
├── test_realistic_placement.py # 인페인팅 테스트 (완료)
├── test_pipeline.py           # 전체 파이프라인 (예정)
├── test_validation.py         # 검증 테스트 (예정)
└── output/                    # 테스트 출력
    ├── 2_slots_detected.png
    ├── 2_slots.json
    └── 2_realistic_mockup.png
```

---

## 9. 릴리즈 체크리스트

### 9.1 코드 완성도

- [ ] `core/shoe_rack_mockup/` 모듈 완성
- [x] `slot_detector.py` 구현 (테스트 코드에서 검증)
- [ ] `compositor.py` 구현
- [ ] `validator.py` 구현
- [ ] 에러 핸들링 완료

### 9.2 문서화

- [x] PRD 작성 (이 문서)
- [x] SKILL.md 작성 (기존 초안)
- [ ] slot-colors.json 작성
- [ ] CLAUDE.md 업데이트

### 9.3 테스트

- [x] 슬롯 감지 테스트 통과
- [x] 단일 인페인팅 테스트 통과
- [ ] 3단계 파이프라인 테스트 통과
- [ ] 검증 로직 테스트 통과
- [ ] 실제 보고용 이미지 생성 완료

### 9.4 검증

- [ ] 검증 기준 정상 작동
- [ ] 크기 일관성 검증 통과
- [ ] 회장님 보고용 품질 이미지 확보

---

## 10. 참조

### 10.1 테스트 코드

- `tests/shoe_rack_mockup/test_slot_detection.py` - OpenCV 색상 마스크 감지
- `tests/shoe_rack_mockup/test_realistic_placement.py` - Gemini 인페인팅

### 10.2 테스트 데이터

```
vlm_테스트용/매장/
├── 정면.png      # 전체 와이드샷
├── 2.png         # 좌측 섹션 (색상 마스크 포함) - 주요 테스트 대상
├── 3.png ~ 8.png # 기타 섹션

신발 이미지: side_view_left_toe/*.jpg
```

### 10.3 관련 워크플로

- 슈즈 3D: `.claude/skills/슈즈3D_shoes-3d/` - 신발 3D 렌더링 (필요 시 연동)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-02-20 | 초안 작성 | Claude Code |
| 0.2 | 2026-02-20 | 테스트 결과 반영, 3단계 파이프라인 설계 | Claude Code |
