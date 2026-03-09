# Gemini API Policy

> FNF Studio의 Gemini API 사용 절대 규칙

## Single Source of Truth

**모든 모델 정책은 `core/policy.py`에서 관리됨.**

```python
from core.policy import (
    FORBIDDEN_MODELS, ALLOWED_MODELS,
    is_forbidden_model, is_allowed_model
)
```

## 허용 모델

| 용도 | 모델 | 상수명 |
|------|------|--------|
| 이미지 생성 | `gemini-3-pro-image-preview` | `IMAGE_MODEL` |
| VLM 분석 | `gemini-3-flash-preview` | `VISION_MODEL` |

## 금지 모델

절대 사용 금지. Hook에서 자동 차단됨.

**금지 모델 목록 (gemini-2.x, 1.x 시리즈):**
- `gemini-2.0-flash-exp`
- `gemini-2.0-flash`
- `gemini-2.5-flash`
- `gemini-2.5-pro`
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-1.0`

**금지 접두사 패턴:**
- `gemini-2.*` (모든 2.x 버전)
- `gemini-1.*` (모든 1.x 버전)

## 필수 패턴

```python
# 반드시 core/config.py에서 import
from core.config import IMAGE_MODEL, VISION_MODEL

# 금지: 모델명 하드코딩
model = "gemini-3-pro-image-preview"  # FORBIDDEN - 훅이 감지함
generate_content(model="gemini-...")  # FORBIDDEN - 훅이 감지함
```

## API 키 관리

```bash
# .env format - 여러 키로 rate limit 로테이션
GEMINI_API_KEY=key1,key2,key3,key4,key5
```

**필수:** `get_next_api_key()` 함수 사용 (thread-safe 로테이션)

```python
from core.api import get_next_api_key

api_key = get_next_api_key()  # 자동 로테이션
```

## 재시도 정책

| 에러 | 코드 | 재시도 |
|------|------|--------|
| 429 / rate limit | RATE_LIMIT | Yes |
| 503 / overloaded | SERVER_OVERLOAD | Yes |
| timeout | TIMEOUT | Yes |
| 401 / api key | AUTH_ERROR | No |
| safety / blocked | SAFETY_BLOCK | No |

**재시도 간격:** `(attempt + 1) * 5`초, 최대 3회

## API 설정 템플릿

```python
from google.genai import types
from core.config import IMAGE_MODEL

config = types.GenerateContentConfig(
    temperature=0.2,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="3:4",
        image_size="2K"
    )
)

response = client.models.generate_content(
    model=IMAGE_MODEL,
    config=config,
    contents=[...]
)
```

## 위반 시

- Hook이 자동 감지하여 경고
- PR 리뷰에서 차단
- 금지 모델 문자열 발견 시 빌드 실패
