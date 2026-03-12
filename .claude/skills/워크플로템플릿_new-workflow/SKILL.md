---
name: new-workflow
description: 새 이미지 생성 워크플로 스킬 템플릿 생성
user-invocable: true
trigger-keywords: ["새 워크플로", "워크플로 생성", "스킬 생성", "new workflow"]
---

# 워크플로 템플릿 생성기

> 표준화된 이미지 생성 워크플로 스킬 자동 생성

---

## 용도

새로운 이미지 생성 워크플로를 만들 때 사용.
FNF Studio 표준 구조(4단계 + 검수 + 재생성)를 자동으로 적용.

---

## 실행 흐름

### Step 1: 워크플로 정보 수집

| 질문 | 필수 | 예시 |
|------|------|------|
| 워크플로 영문명 | ✅ | `face-swap` |
| 워크플로 한글명 | ✅ | `얼굴교체` |
| 워크플로 설명 | ✅ | `소스 이미지의 얼굴을 타겟에 합성` |
| 기본 비율 | ✅ | `3:4` (core/options.py 참조) |
| 기본 temperature | ✅ | `0.2` |
| 트리거 키워드 | ✅ | `["얼굴교체", "페이스스왑", "face swap"]` |

### Step 2: 파일 생성

다음 파일들을 자동 생성:

```
.claude/skills/{한글명}_{영문명}/
├── SKILL.md              # 스킬 정의 (이 템플릿 기반)
└── README.md             # 사용 가이드 (선택)

core/{영문명}/
├── __init__.py           # 모듈 export
├── analyzer.py           # VLM 분석 함수
├── generator.py          # generate_{workflow}() 함수
├── validator.py          # 검증기 (ValidatorRegistry 등록)
└── templates.py          # VLM 프롬프트 템플릿
```

### Step 3: 코드 템플릿 적용

모든 생성 코드에 다음 패턴 필수 적용:

```python
# 모델 - core/config.py에서 import
from core.config import IMAGE_MODEL, VISION_MODEL

# 옵션 - core/options.py에서 import
from core.options import (
    ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,
    get_workflow_defaults, get_cost, validate_aspect_ratio
)

# API 키 - 로테이션 사용
from core.api import get_next_api_key
```

---

## 생성되는 SKILL.md 구조

```markdown
---
name: {영문명}
description: {설명}
user-invocable: true
trigger-keywords: {키워드 배열}
---

# {한글명} ({영문명})

> {설명}

---

## 절대 규칙 (CRITICAL)

1. **모델은 core/config.py에서 import**
2. **옵션은 core/options.py에서 import**
3. **검수+재생성 로직 필수**

---

## 필수 리소스

```
core/{영문명}/                 <- 실행 모듈
core/validators/              <- 검증기 등록
.claude/rules/workflow-template.md  <- 구조 규칙
```

---

## 실행 파이프라인

```
1. 분석 (VLM)     -> analyze_*()
2. 생성 (Image)   -> generate_{영문명}()
3. 검증+재시도    -> generate_with_validation()
```

---

## 대화형 워크플로

### Step 1: 입력 수집

| 순서 | 질문 | 필수 | 기본값 |
|------|------|------|--------|
| 1 | ... | ✅ | - |
| 2 | 비율 | ✅ | {기본비율} |
| 3 | 수량 | ✅ | 3장 |
| 4 | 화질 | ✅ | 2K |

(core/options.py 참조)

### Step 2: 분석
-> VLM 분석

### Step 3: 생성
-> generate_{영문명}()

### Step 4: AI 검증 + 재시도
-> generate_with_validation(max_retries=2)

---

## 모듈 인터페이스

### 1. 분석
```python
from core.{영문명} import analyze_{대상}

result = analyze_{대상}(client=genai_client, images=[...])
```

### 2. 생성
```python
from core.{영문명} import generate_{영문명}

images = generate_{영문명}(
    prompt_json=prompt,
    api_key=get_next_api_key(),
    num_images=3,
    aspect_ratio="3:4",  # 사용자 선택값
    resolution="2K",
)
```

### 3. 검증+재시도
```python
from core.{영문명} import generate_with_validation

result = generate_with_validation(
    prompt_json=prompt,
    api_key=get_next_api_key(),
    max_retries=2,
)
```

---

## 검증 기준

| 항목 | 비중 |
|------|------|
| ... | ...% |

---

## 에러 핸들링

| 에러 | 복구 액션 |
|------|----------|
| API Timeout | 최대 3회 재시도 |
| Rate Limit (429) | 60초 대기 후 재시도 |
| File Not Found | 경로 재입력 요청 |

---

**버전**: 1.0.0
**작성일**: {날짜}
```

---

## 생성되는 core/{영문명}/__init__.py

```python
"""
{한글명} 워크플로 모듈

실행 파이프라인:
1. 분석 (VLM)
2. 생성 (Image)
3. 검증+재시도

사용법:
    from core.{영문명} import (
        analyze_{대상},
        generate_{영문명},
        generate_with_validation,
    )
"""

from .analyzer import analyze_{대상}
from .generator import generate_{영문명}, generate_with_validation

__all__ = [
    "analyze_{대상}",
    "generate_{영문명}",
    "generate_with_validation",
]
```

---

## 생성되는 core/{영문명}/generator.py 기본 구조

```python
"""
{한글명} 이미지 생성 모듈
"""
from typing import List, Optional, Dict, Any
from PIL import Image

from core.config import IMAGE_MODEL, VISION_MODEL
from core.options import (
    get_workflow_defaults,
    get_resolution_px,
    validate_aspect_ratio,
)


def generate_{영문명}(
    prompt_json: Dict[str, Any],
    api_key: str,
    num_images: int = 1,
    aspect_ratio: str = "{기본비율}",
    resolution: str = "2K",
    temperature: float = {기본temp},
) -> List[Optional[Image.Image]]:
    """
    {한글명} 이미지 생성

    Args:
        prompt_json: 프롬프트 JSON
        api_key: Gemini API 키
        num_images: 생성할 이미지 수
        aspect_ratio: 비율 (core/options.py 참조)
        resolution: 해상도 ("1K", "2K", "4K")
        temperature: 생성 온도

    Returns:
        List[PIL.Image] - 생성된 이미지 리스트
    """
    # 비율 검증
    if not validate_aspect_ratio(aspect_ratio):
        raise ValueError(f"Invalid aspect_ratio: {aspect_ratio}")

    # 해상도 변환
    image_size = resolution  # "2K" -> 2048px (API에서 처리)

    # TODO: 생성 로직 구현
    pass


def generate_with_validation(
    prompt_json: Dict[str, Any],
    api_key: str,
    max_retries: int = 2,
    aspect_ratio: str = "{기본비율}",
    resolution: str = "2K",
    initial_temperature: float = {기본temp},
) -> Dict[str, Any]:
    """
    {한글명} 이미지 생성 + 검증 + 재시도

    Args:
        prompt_json: 프롬프트 JSON
        api_key: Gemini API 키
        max_retries: 최대 재시도 횟수 (필수: 2 이상)
        aspect_ratio: 비율
        resolution: 해상도
        initial_temperature: 초기 온도

    Returns:
        {
            "image": PIL.Image,
            "score": float,
            "passed": bool,
            "criteria": dict,
            "attempts": int,
            "history": list,
        }
    """
    if max_retries < 2:
        raise ValueError("max_retries must be at least 2")

    # TODO: 검증+재시도 로직 구현
    pass
```

---

## 생성되는 core/{영문명}/validator.py 기본 구조

```python
"""
{한글명} 검증기
"""
from dataclasses import dataclass
from typing import Dict, Any, List

from core.validators import ValidatorRegistry, WorkflowType, ValidationResult


@ValidatorRegistry.register(WorkflowType.{영문명대문자})
class {영문명Pascal}Validator:
    """
    {한글명} 검증기

    검증 기준:
    - ...
    """

    def __init__(self, client):
        self.client = client

    def validate(
        self,
        generated_img,
        reference_images: Dict[str, Any],
    ) -> ValidationResult:
        """
        생성된 이미지 검증

        Args:
            generated_img: 생성된 이미지 (PIL.Image 또는 경로)
            reference_images: 참조 이미지 딕셔너리

        Returns:
            ValidationResult
        """
        # TODO: 검증 로직 구현
        pass
```

---

## 사용법

```
/새 워크플로
```

또는

```
/new-workflow
```

Claude가 대화형으로 정보 수집 -> 파일 자동 생성

---

**버전**: 1.0.0
**작성일**: 2026-02-11
