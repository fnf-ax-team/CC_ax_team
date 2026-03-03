# Image Generation Options Policy

> 이미지 생성 옵션의 Single Source of Truth

## 원칙

**모든 옵션은 `core/options.py`에서 import해서 사용한다. 하드코딩 금지!**

```python
# 올바른 사용
from core.options import (
    ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,
    DEFAULT_ASPECT_RATIO, DEFAULT_RESOLUTION,
    get_cost, get_resolution_px, validate_aspect_ratio
)

# 금지 패턴
aspect_ratio = "auto"  # FORBIDDEN - 하드코딩
image_size = "2K"     # FORBIDDEN - 하드코딩
cost = 190            # FORBIDDEN - 비용 하드코딩
```

## 비율 (Aspect Ratio)

`core/options.py`의 `ASPECT_RATIOS` 참조

| 비율 | 용도 |
|------|------|
| `1:1` | 정사각/프로필/SNS |
| `2:3` | 세로 포트레이트 |
| `3:2` | 가로 랜드스케이프 |
| `3:4` | 세로 화보 (기본) |
| `4:3` | 가로 화보 |
| `4:5` | 인스타 피드 |
| `5:4` | 가로 피드 |
| `9:16` | 스토리/릴스/숏폼 |
| `16:9` | 유튜브/가로 영상 |
| `21:9` | 시네마틱/울트라와이드 |

## 해상도 (Resolution)

`core/options.py`의 `RESOLUTIONS` 참조

| 화질 | 해상도 | 용도 | 비용 티어 |
|------|--------|------|----------|
| `1K` | 1024px | 테스트/미리보기 | standard |
| `2K` | 2048px | 기본값 (SNS/웹) | standard |
| `4K` | 4096px | 최종 결과물/인쇄 | premium |

## 비용 (Cost)

`core/options.py`의 `COST_TABLE` 참조

| 티어 | 장당 비용 | 적용 해상도 |
|------|----------|------------|
| standard | 190원 | 1K, 2K |
| premium | 380원 | 4K |

**비용 계산:** `get_cost(resolution, quantity)` 함수 사용

```python
from core.options import get_cost

total = get_cost("2K", 5)  # 950원
total = get_cost("4K", 3)  # 1140원
```

## 워크플로별 기본값

`core/options.py`의 `WORKFLOW_DEFAULTS` 참조

```python
from core.options import get_workflow_defaults

defaults = get_workflow_defaults("brandcut")
# defaults.aspect_ratio = "3:4"
# defaults.temperature = 0.25
```

## 사용자 질문 필수 항목

이미지 생성 스킬 실행 시 반드시 질문:

1. **비율** - `ASPECT_RATIOS` 목록에서 선택
2. **수량** - 1, 3, 5, 10장 중 선택
3. **화질** - `RESOLUTIONS` 목록에서 선택

```python
from core.options import format_options_for_user

# 사용자에게 옵션 표 표시
print(format_options_for_user())
```

## Hook 감지 패턴

`core/options.py`의 `HARDCODED_PATTERNS` 참조

- 비율 문자열 하드코딩 감지
- 해상도 문자열 하드코딩 감지
- 비용 숫자 하드코딩 감지

## 위반 시

- Hook이 경고 메시지 출력
- `core/options.py`에서 import 안내
- 반복 위반 시 커밋 차단
