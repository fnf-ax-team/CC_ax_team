# Background Swap Prompt Generator

## 목적

인물 모델을 **1픽셀도 변형하지 않고**, 물리적/맥락적 개연성이 완벽한 배경으로 교체하는 프롬프트 생성.

## 파이프라인 구조

```
[model_image] ──→ model-analysis ──┐
                                   ├──→ background-swap-prompt ──→ image-generation-base
[reference_bg] ──→ background-analysis ──┘
```

### 병렬 실행 가능 구간
- `model-analysis`와 `background-analysis`는 독립적이므로 **병렬 실행 가능** (Group A)

## 입력

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `model_image` | `PIL.Image` | 인물이 포함된 원본 이미지 |
| `reference_bg` | `PIL.Image` | 참조할 배경 스타일 이미지 |

## 출력

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `prompt` | `string` | 배경 교체용 프롬프트 |
| `negative_prompt` | `string` | 네거티브 프롬프트 |

## 사용법

### 1. 물리적 제약 추출 (background-swap)

```python
from skills.배경교체_background_swap import analyze_model_physics

physics = await analyze_model_physics(model_image)
# Returns:
# {
#   "geometry": {"horizon_y": 0.65, "perspective": "eye-level", ...},
#   "lighting": {"direction_clock": 10, "elevation": "mid", ...},
#   "physics_anchors": {"contact_points": [...], ...},
#   "installation_logic": {"is_fixed_prop": true, "forbidden_contexts": [...]}
# }
```

### 2. 배경 스타일 추출 (background-swap)

```python
from skills.배경교체_background_swap import analyze_background

bg_style = await analyze_background(reference_bg)
# Returns:
# {
#   "description": "Minimalist cafe interior with wooden tables...",
#   "location_type": "indoor/cafe",
#   "materials": ["wood", "concrete", "glass"],
#   "color_palette": ["beige", "cream", "warm brown"],
#   "atmosphere": "calm, modern, minimalist"
# }
```

### 3. 프롬프트 조립 (background-swap.json 템플릿 사용)

```python
import json

# 템플릿 로드
with open(".claude/skills/prompt-templates/background-swap.json") as f:
    template = json.load(f)

# 프롬프트 조립
prompt = template["prompt_builder"]["format"].format(
    physics=physics,
    bg_style=bg_style,
    template=template["template"]
)

negative_prompt = ", ".join(template["prompt_builder"]["negative_prompt_base"])
# 금지 컨텍스트 추가
if physics["installation_logic"]["forbidden_contexts"]:
    negative_prompt += ", " + ", ".join(physics["installation_logic"]["forbidden_contexts"])
```

### 4. 이미지 생성 (image-generation-base)

```python
from skills.이미지생성기본_image_generation_base import call_gemini_with_retry

result = await call_gemini_with_retry(
    prompt=prompt,
    reference_images=[model_image],  # 인물 보존용
    negative_prompt=negative_prompt
)
```

## 프롬프트 템플릿 구조

`background-swap.json` 파일 참조:

```json
{
  "preservation": "인물 보존 지시문 (CRITICAL)",
  "physics_constraints": "물리적 제약 (수평선, 원근감, 조명)",
  "installation_logic": "설치 논리 (고정 소품, 금지 컨텍스트)",
  "background_style": "배경 스타일 (장소, 재질, 분위기)",
  "output_requirements": "출력 요구사항 (해상도, 품질)"
}
```

## 핵심 원칙

### 인물 보존 (Non-negotiable)
```
CRITICAL: Preserve the person EXACTLY as shown - no modifications allowed.
- Face: 동일
- Body/Pose: 동일
- Clothing: 동일
- Lighting on person: 동일
```

### 물리적 일관성
- **수평선**: 원본과 동일한 높이 유지
- **원근감**: 원본 카메라 앵글 유지
- **조명 방향**: 원본 광원 방향과 일치
- **접촉점**: 지면 접촉 및 그림자 방향 일치

### 금지 컨텍스트 예시
- 벽에 기댄 포즈 → 도로 한가운데 불가
- 앉은 포즈 → 공중 배경 불가
- 실내 조명 → 강한 직사광선 배경 불가

## 예시 출력

```
CRITICAL: Preserve the person EXACTLY as shown - no modifications allowed.
Replace ONLY the background. Eye-level perspective with horizon at y=0.65,
50mm focal length feel. Minimalist cafe interior with wooden tables,
white built-in sofa, large windows, warm natural light, beige cream tones.
Lighting from 10 o'clock, mid elevation, 5500K color temperature.
Must be against a wall - cannot be in open street or center of road.
Ground contact and shadows must align with original.
Calm modern minimalist atmosphere.
```

## 관련 스킬

- `배경교체_background-swap`: 통합 배경 교체 워크플로우 (물리적 제약 추출, 배경 스타일 추출 포함)
- `브랜드컷_brand-cut`: Gemini API 호출

---

**작성일**: 2026-01-22
**버전**: 1.0
