# Workflow Template Policy

> 모든 워크플로의 필수 구조 규칙

## 필수 4단계 구조

모든 이미지 생성 워크플로는 다음 4단계를 따른다:

```
1. 분석 (VLM)     - gemini-3-flash-preview로 참조 이미지 분석
2. 생성 (Image)   - gemini-3-pro-image-preview로 이미지 생성
3. 검수 (VLM)     - 워크플로별 검수 기준으로 품질 판정
4. 재생성 (Loop)  - 탈락 시 원인 진단 -> 프롬프트 수정 -> 재생성 (최대 2회)
```

## 검수+재생성 필수 (CRITICAL)

**모든 이미지 생성 워크플로는 반드시 검수+재생성 로직을 포함해야 한다.**

### 필수 패턴

```python
# 방법 1: 워크플로 모듈의 generate_with_validation()
from core.brandcut import generate_with_validation

result = generate_with_validation(
    prompt_json=prompt,
    face_images=face_imgs,
    outfit_images=outfit_imgs,
    api_key=api_key,
    max_retries=2,  # 필수: 최소 2회 재시도
)

# 방법 2: 통합 generate_with_workflow_validation()
from core.generators import generate_with_workflow_validation
from core.validators import WorkflowType

result = generate_with_workflow_validation(
    workflow_type=WorkflowType.BRANDCUT,
    generate_func=my_generate_func,
    prompt=prompt,
    reference_images={"face": [...], "outfit": [...]},
    config={"temperature": 0.25},
    max_retries=2,  # 필수
)
```

### 금지 패턴

```python
# FORBIDDEN: 검수 없이 직접 생성만 호출
image = generate_brandcut(prompt, face_imgs, outfit_imgs)
save_image(image)  # 검수 없이 저장 -> 불량 이미지 위험!

# FORBIDDEN: max_retries=0 또는 생략
result = generate_with_validation(..., max_retries=0)
```

## 검증기 위치

| 워크플로 | 검증기 파일 | 클래스 |
|----------|-------------|--------|
| 브랜드컷 | `core/brandcut/validator.py` | `BrandcutValidator` |
| 배경교체 | `core/background_swap/workflow_validator.py` | `BackgroundSwapWorkflowValidator` |
| 셀카 | `core/selfie/validator.py` | `SelfieWorkflowValidator` |
| 시딩UGC | `core/seeding_ugc/validator.py` | `UGCValidator` |

## 새 워크플로 추가 체크리스트

- [ ] `core/{workflow}/validator.py` 검증기 구현 (`@ValidatorRegistry.register`)
- [ ] `core/{workflow}/generator.py`에 `generate_with_validation()` 구현
- [ ] 검수 기준 및 우선순위 정의
- [ ] `core/validators/__init__.py`에 검증기 import 추가
- [ ] CLAUDE.md 품질 검증 기준 섹션에 추가

## 모델 사용 규칙

```python
from core.config import IMAGE_MODEL, VISION_MODEL

# 분석 단계: VISION_MODEL
# 생성 단계: IMAGE_MODEL
# 검수 단계: VISION_MODEL 또는 IMAGE_MODEL
```

## 옵션 사용 규칙

```python
from core.options import (
    get_workflow_defaults,
    validate_aspect_ratio,
    get_resolution_px,
)

# 워크플로별 기본값 사용
defaults = get_workflow_defaults("brandcut")
aspect_ratio = defaults.aspect_ratio
temperature = defaults.temperature
```

## 검수 결과 출력 형식

```markdown
## 검수 결과

| 항목 | 점수 | 기준 | 통과 |
|------|------|------|------|
| 착장 정확도 | 92 | >=70 | O |
| 얼굴 동일성 | 88 | >=70 | O |
| 포즈 자연스러움 | 75 | >=60 | O |

**총점**: 85/100 | **등급**: B | **판정**: 통과
```

## Auto-Fail 조건

다음 중 하나라도 해당하면 자동 탈락:

- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람
- 착장 색상/로고 불일치
- 체형 불일치
- 누런 톤 (golden/amber/warm cast)
- 의도하지 않은 텍스트/워터마크
- AI 특유 플라스틱 피부
