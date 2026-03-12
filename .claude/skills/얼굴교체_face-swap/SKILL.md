---
name: face-swap
description: 얼굴만 교체 (포즈, 착장, 배경 유지)
user-invocable: true
trigger-keywords: ["얼굴 교체", "얼굴 스왑", "페이스 스왑", "face swap"]
---

# 얼굴 교체 (Face Swap)

> **핵심 개념**: 소스 이미지에서 얼굴만 교체, 다른 모든 요소는 정확히 유지

---

## 모델 필수 확인

```
┌─────────────────────────────────────────────────────────────┐
│  이미지 생성: IMAGE_MODEL (gemini-3-pro-image-preview)       │
│  VLM 분석: VISION_MODEL (gemini-3-flash-preview)            │
│                                                             │
│  반드시 core/config.py 에서 import 해서 사용!               │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 컨셉

```
┌─────────────────────────────────────────────────────────────┐
│  Face Swap = 얼굴만 교체                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  유지:                      변경:                            │
│  ├─ 포즈 (EXACT)           └─ 얼굴 → 제공된 얼굴로 교체       │
│  ├─ 착장 (EXACT)                                            │
│  ├─ 배경 (EXACT)                                            │
│  ├─ 조명 (EXACT)                                            │
│  ├─ 표정 (COPY)   ← 소스 표정 복사                          │
│  └─ 체형 (EXACT)                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 변경 (2026-02-20)

| 항목 | 이전 | 현재 |
|------|------|------|
| 프롬프트 언어 | 영어 | **한국어** |
| 이미지 순서 | 소스 먼저 | **얼굴 먼저** |
| Temperature | 0.2 (변동) | **0.5 고정** |
| 소스 분석 | VLM 분석 필요 | **불필요** |

---

## 입력 구조

| 입력 | 필수 | 수량 | 처리 방식 |
|------|------|------|----------|
| 얼굴 이미지 | O | **2장 권장** | API에 **첫 번째, 두 번째** 전달 (얼굴 특징 인식용) |
| 소스 이미지 | O | 1장 | API에 **세 번째** 전달 (포즈/착장/배경/화질 참조) |

---

## API 전송 순서 (CRITICAL)

```
1. 얼굴 이미지 1 (첫 번째) - "이미지 1 = 이 사람"
2. 얼굴 이미지 2 (두 번째) - "이미지 2 = 이 사람" (같은 사람 다른 각도)
3. 소스 이미지 (세 번째) - "이미지 3 = 참고 장면" (포즈/착장/배경/화질 참조)
4. 프롬프트 (텍스트) - 한국어 프롬프트
```

**핵심 원칙:**
- **얼굴 이미지 2장 권장** (얼굴 특징 더 정확히 인식)
- 소스 이미지는 "참고 장면"으로 명시
- **화질 매칭 필수** - "한 장의 사진처럼" 생성

---

## 프롬프트 (최종 버전 v2 - 2026-02-24)

```python
# 얼굴 이미지 2장 권장
FACE_SWAP_PROMPT = """[이미지 1, 2] = 이 사람
[이미지 3] = 참고 장면

이 사람이 실제로 그 장소에서 찍은 사진을 만들어줘.
합성이 아니라 진짜 한 장의 사진처럼.

[한 장의 사진 규칙]
- 얼굴과 몸의 화질이 똑같아야 함
- 얼굴과 배경의 선명도가 똑같아야 함
- 전체가 같은 카메라로 찍은 것처럼
- 이미지 3의 화질 특성 유지 (흐림, 노이즈 등)

복사: 포즈, 옷, 배경, 표정 (입모양, 눈표정, 미소)
이미지 3 얼굴 사용 금지.

합성처럼 보이면 실패야."""

GENERATION_CONFIG = {
    "temperature": 0.5,
    "response_modalities": ["Image"],
}
```

**왜 이 프롬프트가 효과적인가?**
- "한 장의 사진처럼" → 합성이 아닌 실제 사진 프레이밍
- "화질이 똑같아야 함" → 얼굴만 선명한 합성 티 방지
- "이미지 3의 화질 특성 유지" → 원본 흐림/노이즈 매칭
- "합성처럼 보이면 실패야" → 품질 기준 명시
- 얼굴 이미지 2장 → 얼굴 특징 더 정확히 인식

---

## Workflow Pattern (3 Steps)

```
1. select_faces()    → 얼굴 폴더에서 최적 이미지 선택 (VLM)
2. generate_image()  → Gemini API 호출 (temperature 0.5)
3. validate()        → 얼굴 동일성 + 다른 요소 보존 검증
```

**소스 분석 불필요** — 프롬프트에서 직접 복사 지시

---

## 모듈 인터페이스

### 1. 생성 함수 (단일 생성)

```python
from core.face_swap.generator import generate_face_swap

result_img = generate_face_swap(
    source_image="path/to/source.jpg",       # 소스 이미지
    face_images=["path/to/face1.jpg"],       # 얼굴 이미지 목록
    client=client,                           # GenAI 클라이언트
    aspect_ratio="3:4",                      # 비율
    resolution="2K",                         # 해상도
    selected_faces=None,                     # 미리 선택된 얼굴 (없으면 자동 선택)
    enhancement=None,                        # 강화 규칙 (재시도 시)
)
# Temperature 0.5 고정
```

### 2. 생성 + 검수 루프 (권장)

```python
from core.face_swap.generator import generate_with_validation

result = generate_with_validation(
    source_image="path/to/source.jpg",
    face_images=["path/to/face1.jpg", "path/to/face2.jpg"],
    max_retries=2,                           # 최대 재시도 횟수
    aspect_ratio="3:4",
    resolution="2K",
)

# 반환값
# {
#     "image": PIL.Image,           # 최종 이미지
#     "score": int,                 # 검수 총점
#     "passed": bool,               # 통과 여부
#     "criteria": dict,             # 기준별 점수
#     "history": list,              # 재시도 이력
# }
```

---

## 검수 기준

### 검수 항목

| 항목 | 영문 | 가중치 | Pass 기준 |
|------|------|--------|----------|
| 얼굴 동일성 | face_identity | 40% | >= 95 |
| 포즈 보존 | pose_preservation | 25% | >= 95 |
| 착장 보존 | outfit_preservation | 20% | >= 95 |
| 조명 일관성 | lighting_consistency | 10% | >= 80 |
| 경계 품질 | edge_quality | 5% | >= 80 |

**Pass 조건:** `total_score >= 90`

### Auto-Fail Conditions

- 얼굴 동일성 < 80 (완전히 다른 사람)
- 포즈 변경됨 (팔/다리 위치 다름)
- 착장 변경됨 (색상/로고/스타일 다름)
- 배경 변경됨 (설정/톤 다름)
- 손가락 6개 이상
- 누런 톤 (golden/amber cast)

---

## 대화 플로우

```
1. 사용자: "얼굴 교체" 또는 "face swap"

2. Claude: "소스 이미지 경로?" (얼굴 교체 대상)
3. 사용자: D:\source.jpg

4. Claude: "얼굴 이미지 폴더 경로?"
5. 사용자: D:\faces

6. Claude: [AskUserQuestion - 수량/화질 클릭 선택]

7. 사용자: 클릭으로 선택

8. Claude:
   - 얼굴 이미지 자동 선택 (1~2장)
   - 이미지 생성 (temperature 0.5)
   - 검수
   - 결과 저장 및 경로 안내
```

---

## 출력 폴더 구조

```
Fnf_studio_outputs/
└── face_swap/
    └── 20260220_103045/
        ├── images/
        │   ├── input_face_01.jpg
        │   ├── input_source_01.jpg
        │   ├── output_001.jpg
        │   ├── output_002.jpg
        │   └── output_003.jpg
        ├── prompt.json
        ├── prompt.txt
        ├── config.json
        └── validation.json
```

---

## 파일 구조

```
core/face_swap/
├── __init__.py
├── analyzer.py         # 얼굴 이미지 선택 (VLM)
├── generator.py        # 생성 + 검수 루프
├── templates_final.py  # 최종 프롬프트
└── validator.py        # FaceSwapValidator
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 얼굴이 안 닮음 | 얼굴 이미지 품질 | 정면, 고해상도 이미지 사용 |
| 소스 얼굴 그대로 | 이미지 순서 잘못 | 얼굴 먼저, 소스 나중 확인 |
| 포즈가 다름 | 프롬프트 약함 | 프롬프트 확인, temperature 0.5 확인 |
| 착장 변경됨 | API 혼동 | 프롬프트에 "옷 복사" 명시 확인 |
| 혀가 없는데 혀 나옴 | 프롬프트에 혀 언급 | 구체적 표정 언급 제거 |
| 표정 안 맞음 | 표정 복사 누락 | "표정 복사" 명시 확인 |

---

## 핵심 원칙

| 항목 | 처리 방식 |
|------|----------|
| 얼굴 이미지 | **2장 권장**, API에 첫 번째/두 번째로 전달 |
| 소스 이미지 | API에 세 번째로 전달 (장면 + 화질 참조) |
| 프롬프트 | 한국어, 마지막에 전달 |
| Temperature | 0.5 고정 |
| 포즈/착장/배경 | 소스에서 복사 |
| 표정 | 소스에서 복사 |
| **화질** | 소스와 동일하게 매칭 (핵심!) |

**핵심 개선점 (v2):**
- 얼굴 2장 → 얼굴 특징 더 정확히 인식
- "한 장의 사진처럼" → 화질 매칭으로 합성 티 제거
- "합성처럼 보이면 실패" → 품질 기준 명시
