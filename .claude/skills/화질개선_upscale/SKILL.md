---
name: 화질개선_upscale
description: 기존 이미지의 내용 변경 없이 4K 해상도로 업스케일
user-invocable: false
trigger-keywords: [업스케일, 4K, 화질개선, 고화질, upscale, enhance, 해상도]
---

# 4K 화질 개선 (Upscale)

> 기존 이미지의 내용을 변경하지 않고 해상도만 4K(4096px)로 향상.
> 얼굴, 착장, 포즈, 배경, 색감 등 모든 요소 100% 보존.

---

## 절대 규칙 (CRITICAL)

1. **모델**: `core/config.py`의 `IMAGE_MODEL` 사용 (하드코딩 금지)
2. **검증 모델**: `core/config.py`의 `VISION_MODEL` 사용
3. **옵션**: `core/options.py`에서 import (하드코딩 금지)
4. **Temperature**: 0.05 (최소 변동 — 내용 보존 최우선)
5. **출력 해상도**: 항상 4K (4096px)
6. **비율**: 원본 이미지에서 자동 감지 (`detect_aspect_ratio()`)
7. **검수 필수**: 원본과 결과 비교 검증 후 저장

---

## 필수 리소스

| 리소스 | 위치 |
|--------|------|
| 생성기 | `core/upscale/generator.py` |
| 검증기 | `core/upscale/validator.py` |
| 비율 감지 | `core/options.py` → `detect_aspect_ratio()` |
| 모델 상수 | `core/config.py` → `IMAGE_MODEL`, `VISION_MODEL` |

---

## 모듈 인터페이스

### 1. 단일 이미지 업스케일

```python
from core.upscale import upscale_image

result = upscale_image(
    source_image="path/to/image.jpg",  # 또는 PIL Image
    api_key=None,                       # None이면 자동 로테이션
    max_retries=3,
)
# result: PIL.Image 또는 None
```

### 2. 업스케일 + 검증

```python
from core.upscale import upscale_with_validation

result = upscale_with_validation(
    source_image="path/to/image.jpg",
    max_retries=2,
)
# result: {image, score, passed, criteria, attempts, history}
```

### 3. 배치 업스케일

```python
from core.upscale import upscale_batch

result = upscale_batch(
    input_dir="path/to/folder",
    output_dir=None,        # None이면 input_dir/4K
    max_retries=3,
    delay=2.0,              # rate limit 방지
    skip_existing=True,
)
# result: {success, failed, skipped, results}
```

---

## 실행 파이프라인

```
1. 입력           — 이미지 파일/폴더 경로 받기
2. 비율 자동감지   — detect_aspect_ratio()로 원본 비율 감지
3. 업스케일 생성   — Gemini API로 4K 재생성 (temperature=0.05)
4. 검증           — 원본 vs 결과 비교 (5개 기준)
5. 재시도         — 검증 실패 시 최대 2회 재시도
6. 저장           — 표준 출력 폴더 구조로 저장
```

---

## 대화형 워크플로

### Step 1: 이미지 입력

사용자에게 질문:
- 단일 이미지 경로 또는 폴더 경로

### Step 2: 확인

표시 정보:
- 감지된 비율
- 이미지 수량
- 예상 비용 (4K = 380원/장)

### Step 3: 실행

- 단일: `upscale_with_validation()` 사용
- 배치: `upscale_batch()` 사용

### Step 4: 결과 출력

검수 결과 표 출력 (한국어):

```
## 검수 결과

| 항목 | 점수 | 기준 | 통과 |
|------|------|------|------|
| 구도 보존 | 98 | >=90 | O |
| 인물 보존 | 97 | >=90 | O |
| 착장 보존 | 96 | >=85 | O |
| 색감 보존 | 95 | - | O |
| 디테일 향상 | 85 | - | O |

**총점**: 95/100 | **등급**: S | **판정**: 통과
```

---

## 검증 기준 (5-criteria)

| 항목 | 영문 | 비중 | Auto-fail |
|------|------|------|-----------|
| 구도 보존 | composition_preservation | 25% | < 90 |
| 인물 보존 | person_preservation | 25% | < 90 |
| 착장 보존 | outfit_preservation | 20% | < 85 |
| 색감 보존 | color_fidelity | 15% | - |
| 디테일 향상 | detail_enhancement | 15% | - |

**Pass 기준**: 총점 >= 90 AND auto-fail 없음

---

## 에러 핸들링

| 에러 | 처리 |
|------|------|
| 429 / rate limit | (attempt + 1) * 5초 대기 후 재시도 |
| Safety block | 해당 이미지 스킵 |
| Timeout | 재시도 |
| 검증 실패 | 최대 2회 재시도 |

---

## 비용

| 항목 | 비용 |
|------|------|
| 4K 업스케일 1장 | 380원 |
| 검증 (VLM) | ~10원 |
| 재시도 포함 최대 | ~1,150원/장 |

---

## 출력 폴더 구조

```
Fnf_studio_outputs/
└── upscale/
    └── {YYYYMMDD_HHMMSS}_{description}/
        ├── images/
        │   ├── input_source_01.jpg     # 원본
        │   └── output_001.jpg          # 4K 결과
        ├── config.json
        └── validation.json
```
