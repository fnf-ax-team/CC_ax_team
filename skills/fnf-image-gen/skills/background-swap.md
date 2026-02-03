---
name: background-swap
description: 배경 교체 통합 워크플로우. 분석(VFX+VLM) -> 오브젝트 보존 -> 프롬프트 조립 -> 생성 -> 7-criteria 검증 -> 진단 기반 재시도. 인물+차량 자동 보존(ONE UNIT). 대화형 컨셉 조율 지원.
user-invocable: true
argument-hint: <이미지/폴더> "원하는 배경" [--retry] [--sweep]
---

# Background Swap - 배경 교체 통합 워크플로우

## 사용법

### Python
```python
from background_swap import swap

# 단일 이미지 (빠른 모드: 생성 + 품질 점수 리포트)
swap("photo.jpg", "캘리포니아 해변 석양")

# 고품질 모드 (생성 + 검증 + 진단 + 자동 재시도)
swap("photo.jpg", "파리 카페 테라스", enable_retry=True)

# 폴더 전체 + 시안 여러 장
swap("./images", "런던 브릭 골목", variations=3)

# 전체 옵션
swap("./images", "도쿄 네온 골목",
     output_dir="./tokyo_results",
     variations=2,
     enable_retry=True,
     max_retries=2,
     image_size="2K")

# Sweep 모드 (Fast 생성 + 사후 일괄 검증 + 자동 재생성)
swap("./images", "베를린 콘크리트 벽",
     enable_sweep=True, max_sweep_rounds=2,
     image_size="2K")
```

### CLI
```bash
# 빠른 모드
python background_swap.py photo.jpg "캘리포니아 해변 석양"

# 고품질 모드 (--retry)
python background_swap.py photo.jpg "파리 카페 테라스" --retry

# 전체 옵션
python background_swap.py ./images "런던 브릭 골목" -v 3 --retry --size 2K -o ./outputs

# Sweep 모드 (배치 생성 후 자동 검증 + 재생성)
python background_swap.py ./images "베를린 콘크리트 벽" --sweep --sweep-rounds 2
```

## 핵심 특징

- **프리셋 없음**: 원하는 배경 자유롭게 입력
- **검증된 프롬프트**: AutoRetryPipeline과 동일한 BASE_PRESERVATION_PROMPT 사용
- **7-criteria 품질 검증**: 모든 생성 결과에 품질 점수 포함
- **선택적 자동 재시도**: `enable_retry=True`로 품질 보장 모드 활성화
- **ONE UNIT 보존**: 인물+차량+오브젝트를 하나의 단위로 자동 보존
- **VFX 물리 분석**: 카메라, 조명, 포즈 의존성 자동 감지
- **VLM 배경 분석**: 참조 이미지에서 배경 설명 자동 추출
- **2.5K 출력**: 고해상도
- **병렬 처리**: 6 workers

## 모드 비교

| 항목 | Fast Mode (기본) | Quality Mode (`--retry`) | Sweep Mode (`--sweep`) |
|------|-----------------|--------------------------|------------------------|
| 생성 | 1회 | 최대 3회 (1 + 2 재시도) | 1회 (Fast) |
| 사후 검증 | 점수만 (참고) | 이미지별 통과/실패 | 배치 일괄 검증 |
| 재생성 | 없음 | 이미지별 진단+보강+재생성 | 실패분만 자동 재생성 (retry 포함) |
| Temperature | 0.2 고정 | 0.2 -> 0.1 -> 0.05 | 0.2 (초기) -> retry시 0.1 -> 0.05 |
| 속도 | 빠름 | 실패 시 느림 | Fast + 실패분만 추가 처리 |
| 용도 | 프롬프트 방향 테스트 | 소량 프로덕션 | **대량 프로덕션 (추천)** |
| Sweep 루프 | - | - | 검증->실패추출->재생성->재검증 (최대 N라운드) |

## 파라미터

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `input_path` | 이미지 파일 또는 폴더 | (필수) |
| `background` | 원하는 배경 설명 | (필수) |
| `output_dir` | 출력 폴더 | `./outputs` |
| `variations` | 시안 개수 | 1 |
| `max_images` | 최대 이미지 수 | 전체 |
| `max_workers` | 병렬 처리 수 | 6 |
| **`enable_retry`** | **자동 재시도 (진단+보강+재생성)** | **False** |
| **`max_retries`** | **최대 재시도 횟수** | **2** |
| **`image_size`** | **출력 해상도 (1K/2K/4K)** | **2K** |
| **`enable_sweep`** | **Sweep 모드 (사후 일괄 검증 + 자동 재생성)** | **False** |
| **`max_sweep_rounds`** | **최대 sweep 라운드 수** | **2** |

---

## Sweep 모드 워크플로우

대량 배치에서 Fast Mode의 속도와 Quality Mode의 품질 보증을 결합.

```
Step 1: Fast Mode 배치 생성 (전체 이미지)
  |
Step 2: 일괄 품질 검증 (원본 vs 생성 매칭)
  |--- 통과율 >= 95% --> 완료
  +--- 통과율 < 95%
  |
Step 3: QUALITY_ISSUE 이미지 추출
  |
Step 4: 실패분 재생성 (enable_retry=True, 진단+보강 포함)
  |
Step 5: 재검증 --> 통과율 체크
  |--- >= 95% 또는 max_rounds 도달 --> 완료
  +--- < 95% --> Step 3 반복
```

---

## 대화형 워크플로우

사용자와 자연스럽게 대화하며 배경 컨셉을 조율하고 생성하는 워크플로우.

### 전체 흐름 (6단계)

1. **컨셉 수집** - 사용자가 원하는 배경 파악
2. **포인트 정리** - 핵심 요소 정리해서 확인
3. **조율** - 피드백 반영하며 구체화
4. **테스트** - 샘플 생성해서 확인
5. **전체 적용** - 확정되면 배치 실행
6. **검수** - 품질 확인 및 리뷰 처리

### 실행 모드별 검수 규칙

**테스트 모드 (2~3장 샘플)**
- 검수 없이 빠르게 생성만. `max_retries=0` 설정, 검증/재시도 스킵
- 사용자가 직접 눈으로 확인하고 피드백
- 목적: 프롬프트 방향 확인, 빠른 이터레이션

**전체 배치 모드 (확정 후 전체 실행)**
- `max_retries=2` 설정, 자동 검증 + 재시도 활성화
- 완료 후 배치 검증 실행:
  ```bash
  python background_swap.py ./images "배경" --sweep
  ```
- 검수 기준: model_preservation=100 AND total >= 95
- QUALITY_ISSUE 이미지는 manual_review 폴더로 분류

### 4대 원칙

1. **영문 프롬프트 숨김** - 영문 프롬프트는 내부 처리용, 사용자에게 설명하지 않음
2. **이모지 금지** - 이모지 사용하지 않음
3. **친절한 척 금지** - 불필요한 존댓말이나 과도한 친절함 배제, 일만 함
4. **다른 스타일 제안 금지** - 사용자가 요청한 방향 외 다른 스타일 제안하지 않음

### 대화 예시

```
사용자: 베를린 느낌으로

Claude: 베를린 어떤 느낌? 모던? 클래식? 참조 있으면 보여줘.

사용자: 모던한 느낌

Claude: 모던 베를린.
        **포인트:**
        - 유리+철골 건축
        - 차가운 톤
        - 미래적
        이런 방향?

사용자: 좋아

Claude: 테스트 몇 장?

사용자: 2장

Claude: 2장 생성합니다.
```

### 내부 처리 (사용자에게 보이지 않음)

```python
# 1. 컨셉 이해
def understand_concept(user_input, reference_image=None):
    if reference_image:
        visual_analysis = analyze_reference_image(reference_image)
    points = extract_key_points(user_input, visual_analysis)
    return points

# 2. 영문 프롬프트 생성 (내부용)
def generate_internal_prompt(points, adjustments=None):
    base_prompt = translate_points_to_english(points)
    if adjustments:
        base_prompt = apply_adjustments(base_prompt, adjustments)
    return base_prompt

# 3. 테스트 이미지 선택
def select_test_images(input_dir, count):
    images = list_images(input_dir)
    selected = select_diverse_samples(images, count)
    return selected

# 4. 전체 배치 실행 (항상 AutoRetryPipeline 사용)
def run_full_batch(input_dir, output_dir, confirmed_prompt):
    from auto_retry_pipeline import AutoRetryPipeline
    pipeline = AutoRetryPipeline()
    result = pipeline.run(input_dir, output_dir, confirmed_prompt)
    return result
```

---

## 파이프라인 (전체 흐름)

```
입력 이미지
    |
    v
[1] 모델 물리 분석 (VFX) -----> 카메라/조명/포즈/설치논리 JSON
    |
    v
[2] 배경 분석 (VLM) ----------> 배경 텍스트 설명 또는 JSON
    |
    v
[3] 오브젝트 보존 프롬프트 ----> ONE UNIT 보존 지시문
    |
    v
[4] 프롬프트 조립 ------------> BASE_PRESERVATION_PROMPT + 분석 결과 + 배경 설명
    |
    v
[5] 이미지 생성 (Gemini) -----> temperature 0.2, 2K
    |
    v
[6] 7-criteria 품질 검증
    |--- PASS (total >= 95, model_preservation = 100) --> 완료 (release/)
    |--- FAIL --> [7] 실패 원인 진단 (6가지 이슈)
                      |
                      v
                  [8] 이슈별 프롬프트 보강
                      |
                      v
                  [9] 재생성 (temperature 0.1) --> [6] 재검증
                      (최대 2회 재시도, temperature 0.2 -> 0.1 -> 0.05)
```

---

## 모델 물리 분석 (VFX)

VFX 슈퍼바이저 관점에서 인물 사진의 물리적 제약 조건을 수치화하여, 배경 합성 시 공간적 불일치를 방지한다.

### 6대 분석 영역

| 영역 | 추출값 | 용도 |
|------|--------|------|
| Camera Geometry | horizon_y, perspective, focal_length_vibe | 원근/소실점 매칭 |
| Lighting Physics | direction_clock, elevation, softness, color_temp | 조명 방향/강도 매칭 |
| Pose Dependency | pose_type, support_required, support_direction | 지지대 필요 여부 판단 |
| Installation Logic | prop_detected, is_fixed_prop, forbidden_contexts | 소품 배치 규칙 |
| Physics Anchors | contact_points [x,y], shadow_casting_direction | 접지/그림자 정합 |
| Semantic Style | vibe, recommended_locations | 분위기 매칭 |

### ANALYSIS_PROMPT

```python
ANALYSIS_PROMPT = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한
물리적 제약 조건을 수치화된 데이터로 추출해야 합니다.

## 분석 집중 대상:

### 1. Camera Geometry (카메라 지오메트리)
- 수평선 높이: 이미지 높이 기준 0.0~1.0 정규화 좌표
- 원근감: eye-level | high-angle | low-angle
- 초점 거리 느낌: 35mm | 50mm | 85mm

### 2. Lighting Physics (조명 물리)
- 광원 방향: 시계 방향 1~12시
- 고도: low | mid | high
- 부드러움: 0.0 (hard) ~ 1.0 (soft)
- 색온도: K 값 또는 warm/neutral/cool

### 3. Pose Dependency (포즈 의존성) - CRITICAL
- 포즈 타입: standing | sitting | leaning | crouching | lying
- 지지대 필요 여부:
  - leaning -> 반드시 기댈 수 있는 벽/기둥/난간 필요
  - sitting -> 반드시 앉을 수 있는 의자/벤치/바닥 필요
  - standing -> 지지대 불필요
- 지지대 방향: behind | left | right | below
- 지지대 거리: close(접촉) | near(30cm이내) | far(30cm이상)

### 4. Installation Logic (설치 논리) - CRITICAL
- 소품 감지: 모델이 사용 중인 소품 식별
- 고정형 여부: 고정형 vs 이동형 판별
- 배치 규칙: 상세한 공간 논리
- 금지 컨텍스트: 소품이 자연스럽게 존재할 수 없는 장소

### 5. Physics Anchors (물리적 앵커)
- 접촉점: [x, y] 정규화 좌표
- 그림자 방향: [x, y] 벡터

### 6. Semantic Style (의미적 스타일)
- 분위기: street_editorial | studio | indoor | outdoor
- 추천 위치: ["subway", "lounge", "shop_interior"] 등
"""
```

### JSON 출력 형식

```json
{
  "geometry": {
    "horizon_y": 0.65,
    "perspective": "eye-level",
    "camera_height": "eye-level",
    "viewing_angle": "3/4",
    "focal_length_vibe": "50mm"
  },
  "lighting": {
    "direction_clock": "10",
    "elevation": "mid",
    "softness": 0.7,
    "color_temp": "5500K"
  },
  "pose_dependency": {
    "pose_type": "leaning",
    "support_required": true,
    "support_type": "wall or pillar",
    "support_direction": "behind-left",
    "support_distance": "close",
    "prompt_requirement": "Background MUST include a wall or pillar behind-left of the model for leaning"
  },
  "installation_logic": {
    "prop_detected": "고정형 외다리 의자",
    "is_fixed_prop": true,
    "placement_rule": "Must be against a wall. Cannot be placed in open spaces.",
    "forbidden_contexts": ["길 한복판", "야외 공원 중앙", "계단 중간"]
  },
  "physics_anchors": {
    "contact_points": [
      {"label": "left_foot", "coord": [0.3, 0.92]},
      {"label": "chair_base", "coord": [0.5, 0.88]}
    ],
    "shadow_casting_direction": [0.2, 0.8]
  },
  "semantic_style": {
    "vibe": "street_editorial",
    "recommended_locations": ["subway", "lounge", "shop_interior"]
  }
}
```

### analyze_model_physics() 함수

```python
import json
from google import genai
from google.genai import types
from PIL import Image

def analyze_model_physics(image_pil: Image.Image, api_key: str, additional_context: str = ""):
    """
    모델 이미지의 물리적/맥락적 키값을 추출.

    Returns:
        {"status": "success"|"error", "data": {...}, "generated_guideline": str}
    """
    client = genai.Client(api_key=api_key)

    # 1024px 다운샘플링 (공간 분석이므로 높은 해상도)
    max_size = 1024
    if max(image_pil.size) > max_size:
        image_pil.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    system_instruction = """당신은 세계 최고의 시각효과(VFX) 슈퍼바이저이자 사진 디렉터입니다.
입력된 인물 사진을 분석하여, 이 인물을 '한 픽셀도 변형하지 않고' 새로운 배경에 합성하기 위한 물리적 제약 조건을 수치화된 데이터로 추출해야 합니다."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[types.Content(role="user", parts=[
            types.Part(text=ANALYSIS_PROMPT + f"\n{additional_context}"),
            image_pil
        ])],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            max_output_tokens=1200,
            response_mime_type="application/json"
        )
    )

    result = json.loads(response.text)
    guideline = build_background_guideline(result)

    return {"status": "success", "data": result, "generated_guideline": guideline}
```

### build_background_guideline() 함수

```python
def build_background_guideline(analysis_data: dict) -> str:
    """추출된 키값을 배경 생성 프롬프트 가이드라인으로 조립."""
    geom = analysis_data.get('geometry', {})
    light = analysis_data.get('lighting', {})
    pose = analysis_data.get('pose_dependency', {})
    logic = analysis_data.get('installation_logic', {})
    style = analysis_data.get('semantic_style', {})

    parts = []

    if geom:
        parts.append(f"Perspective: {geom.get('perspective', 'eye-level')} with vanishing point at y={geom.get('horizon_y', 0.5)}")
        if geom.get('focal_length_vibe'):
            parts.append(f"Focal length vibe: {geom['focal_length_vibe']}")

    if light:
        parts.append(f"Lighting: Source from {light.get('direction_clock', '12')} o'clock, {light.get('elevation', 'mid')} elevation, {light.get('softness', 0.5)} softness")
        if light.get('color_temp'):
            parts.append(f"Color temperature: {light['color_temp']}")

    # 포즈 의존성 - 가장 중요
    if pose and pose.get('support_required'):
        parts.append(f"CRITICAL - POSE SUPPORT: {pose.get('prompt_requirement', 'Support structure required')}")

    if logic:
        if logic.get('placement_rule'):
            parts.append(f"Spatial Logic: {logic['placement_rule']}")
        if logic.get('forbidden_contexts'):
            parts.append(f"Avoid: {', '.join(logic['forbidden_contexts'])}")

    if style and style.get('vibe'):
        parts.append(f"Style vibe: {style['vibe']}")

    return "Create a professional background. " + ". ".join(parts) + "."
```

---

## 배경 분석 (VLM)

배경 이미지를 구체적인 텍스트 설명으로 변환하여 프롬프트에 바로 사용할 수 있도록 한다.

### 분석 타입

| 분석 타입 | 출력 형식 | 용도 | 해상도 |
|----------|----------|------|--------|
| 기본 분석 | 텍스트 (2-4문장) | 이미지 생성 프롬프트 | 512px |
| 배경교체용 상세 분석 | JSON | 차량/바닥/색보정 매칭 | 1024px |
| 포토 디렉터 분석 | JSON | 합성 기획 (조명/그림자/색상) | 512px |

### BACKGROUND_ANALYSIS_PROMPT (기본)

```python
BACKGROUND_ANALYSIS_PROMPT = """You are a professional location scout and set designer. Analyze this background image and provide a DETAILED, SPECIFIC text description that can be used directly in image generation prompts.

## What to Analyze:
1. **Location Type**: What kind of place is this? (cafe, street, interior, outdoor, etc.)
2. **Specific Elements**: Furniture, architectural details, decorative items, plants, windows, doors, etc.
3. **Materials & Textures**: Wood, concrete, glass, fabric, metal, etc.
4. **Color Palette**: Dominant colors, accent colors, overall tone
5. **Lighting**: Natural light source, artificial lights, shadows, brightness
6. **Atmosphere**: Clean/minimal, cozy, industrial, luxury, casual, etc.

## Output Format:
Provide a SINGLE, DETAILED text description (2-4 sentences) that captures:
- The specific location and its key elements
- Materials and textures visible
- Color scheme and lighting
- Overall atmosphere

Example format:
"minimalist cafe interior, wooden table with terracotta legs, white built-in sofa, large open window, potted trees, warm natural light, beige/cream tones"

Be SPECIFIC and DETAILED. Use concrete nouns and descriptive adjectives.
Return ONLY the text description, no JSON, no markdown, no explanations."""
```

### analyze_background() 함수

```python
def analyze_background(image_pil: Image.Image) -> str:
    """배경 이미지를 구체적인 텍스트 설명으로 변환."""
    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)
    model = get_text_model()

    # 512px 다운샘플링
    image_part = pil_to_part(image_pil, max_size=512)

    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[
            types.Part(text=BACKGROUND_ANALYSIS_PROMPT),
            types.Part(text="\n\n[Background image to analyze]:"),
            image_part
        ])],
        config=types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.9,
            max_output_tokens=512
        )
    )

    # 마크다운 코드 블록 제거
    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join([l for l in lines if not l.strip().startswith("```")])

    return text.strip()
```

### BACKGROUND_SWAP_ANALYSIS_PROMPT (차량/바닥/색보정)

```python
BACKGROUND_SWAP_ANALYSIS_PROMPT = """
Analyze this photo for seamless background replacement. Return JSON only:

{
  "has_vehicle": true/false,
  "vehicle_description": "car/motorcycle/bicycle type and color if exists",
  "ground": {
    "material": "concrete/asphalt/sand/tile/etc",
    "color": "specific color like beige/gray/brown",
    "tone": "warm/neutral/cool"
  },
  "lighting": {
    "direction": "front/back/left/right/top",
    "intensity": "soft/medium/hard",
    "color_temp": "warm/neutral/cool"
  },
  "color_grading": {
    "overall_warmth": "warm/neutral/cool",
    "saturation": "low/medium/high"
  }
}
"""
```

### analyze_for_background_swap() 함수

```python
def analyze_for_background_swap(image_pil: Image.Image) -> dict:
    """배경 교체용 상세 분석 (차량 감지, 바닥 톤 매칭, 색보정 포함)."""
    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)

    image_part = pil_to_part(image_pil, max_size=1024)

    response = client.models.generate_content(
        model="gemini-3-flash-preview",  # 분석용
        contents=[types.Content(role="user", parts=[
            types.Part(text=BACKGROUND_SWAP_ANALYSIS_PROMPT),
            image_part,
        ])],
        config=types.GenerateContentConfig(temperature=0.1)
    )

    text = response.text
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()

    return json.loads(text.strip())
```

### 분석 결과 활용

```python
analysis = analyze_for_background_swap(source_image)

# 차량 보존 지시문 생성
if analysis.get("has_vehicle"):
    vehicle_instruction = f"""
=== CRITICAL: VEHICLE PRESERVATION ===
THERE IS A VEHICLE IN THIS IMAGE: {analysis['vehicle_description']}
YOU MUST KEEP THIS VEHICLE EXACTLY AS IT IS.
DO NOT REMOVE, HIDE, OR MODIFY THE VEHICLE IN ANY WAY.
"""

# 바닥 연속성 지시문 생성
ground = analysis.get("ground", {})
ground_instruction = f"""
=== GROUND CONTINUITY ===
- Ground material: {ground.get('material', 'concrete')}
- Ground color: {ground.get('color', 'gray')} ({ground.get('tone', 'neutral')} tone)
- The ground MUST continue seamlessly from foreground to background
"""

# 색보정 매칭 지시문 생성
color = analysis.get("color_grading", {})
color_instruction = f"""
=== COLOR MATCHING ===
- Overall warmth: {color.get('overall_warmth', 'neutral')}
- Saturation: {color.get('saturation', 'medium')}
Apply the SAME color grading to the background as the person has.
"""
```

### 포토 디렉터 상세 분석 결과 형식 (JSON)

```json
{
  "source_style": {
    "sharpness": "sharp",
    "contrast": "medium",
    "saturation": "natural",
    "photographic_style": "editorial",
    "depth_of_field": "shallow"
  },
  "environment": {
    "location_type": "cafe",
    "tone_mood": "calm and modern minimalist",
    "color_palette": "cool gray tones with subtle blue undertones",
    "ground_surface": "concrete",
    "wall_textures": "smooth concrete"
  },
  "lighting_design": {
    "key_light": "natural window light from left",
    "fill_light": "ambient light fills shadows softly",
    "rim_light": "subtle edge highlights from window"
  },
  "shadow_design": {
    "ground_shadow": "soft shadow falls to the right, about 2 feet long",
    "body_shadow": "soft shadows on person to match environment"
  },
  "color_design": {
    "temperature": "slightly cool to match background",
    "environment_reflection": "subtle blue-gray tones reflected on person"
  },
  "ground_connection": {
    "shadow_type": "soft ambient occlusion",
    "surface_material": "concrete",
    "surface_condition": "smooth"
  }
}
```

---

## 오브젝트 보존 (ONE UNIT)

### 핵심 개념

```
문제: 인물과 차를 따로 보존하라고 하면 AI가 혼란 -> 둘 다 변형됨
해결: 인물+차+오브젝트 = 하나의 FOREGROUND SUBJECT로 묶어서 보존
```

배경교체 스킬은 이 보존 프롬프트를 **자동으로 포함**한다. 사용자가 별도로 호출할 필요 없음.

### 3단계 보존 레벨

**BASIC - 모든 배경교체에 기본 적용**
```
FRAMING: Model fills 90% of the frame height. KEEP THIS.
DO NOT make the model smaller. DO NOT zoom out.

The BLACK CAR (if exists) is a PROP, not background.

COPY EXACTLY FROM INPUT:
- Model size in frame (CRITICAL - must be same %)
- Model face, pose, clothes, hair
- Any vehicle/object near model (color, shape, position)

REPLACE: Background only
```

**DETAILED - 차량이 확인된 경우**
```
=== FOREGROUND SUBJECT PRESERVATION (CRITICAL) ===

SUBJECT = Person + Vehicle as ONE CONNECTED UNIT
Treat them as a SINGLE subject, NOT separate objects.

DO NOT MODIFY THE SUBJECT:
- Person: exact face, body, clothes, pose, hair
- Vehicle: exact color, model, wheels, reflections, position
- Their spatial relationship: distance, angle, contact points
- Combined shadows on ground

The person and vehicle are ONE COMPOSITION.
Moving, resizing, or modifying either one breaks the composition.

ONLY REPLACE: Background environment behind this unit
```

**FULL - 최대 강도**
```
=== FOREGROUND SUBJECT = ONE UNIT (DO NOT SEPARATE) ===

Everything in foreground (person + vehicle + objects) = SINGLE SUBJECT
This is NOT "person" + "car". This is ONE connected unit.

ABSOLUTE PRESERVATION:
- Person: 100% identical (face, body, clothing, pose, expression)
- Vehicle (if exists): 100% identical (color, shape, wheels, reflections)
- Objects (if exist): 100% identical
- All contact points and spatial relationships: LOCKED
- All shadows: preserve direction and shape

NEVER:
- Separate person from vehicle
- Move person relative to vehicle
- Change vehicle color/shape/size
- Add new people, cars, or objects

ONLY CHANGE: Background behind the foreground subject
```

### Python 사용법

```python
PRESERVATION_BASIC = """
FOREGROUND SUBJECT = ALL foreground elements as ONE UNIT
(person, vehicle, objects - whatever exists in foreground)

PRESERVE 100% IDENTICAL:
- Every person: face, body, clothing, pose, hair, expression
- Every object/vehicle near the person (if any): color, shape, position
- Spatial relationships between all foreground elements

ONLY CHANGE: Background environment
"""

# 프롬프트에 삽입
full_prompt = f"""
{PRESERVATION_BASIC}

BACKGROUND: {your_background_description}
"""
```

---

## 프롬프트 구조

검증된 `BASE_PRESERVATION_PROMPT` 사용 (AutoRetryPipeline과 동일):

```
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
DO NOT CHANGE THE PERSON'S FACE. KEEP EXACT SAME FACE.

MODEL PRESERVATION (100% IDENTICAL):
- FACE: identical to input - same features, expression, hair
- BODY: identical to input - same pose, proportions, position
- CLOTHING: identical to input - same garments, colors, logos, details
- SCALE: identical to input - person height ratio must match exactly

PHYSICS CONSTRAINTS:
- Match original lighting direction and intensity
- Match original perspective and horizon line
- Shadows consistent with light source

OUTPUT: Professional fashion photography, seamless compositing, no artifacts

BACKGROUND CHANGE:
{사용자 입력 배경 설명}
```

분석 결과가 있을 경우 추가되는 요소:

```python
# VFX 분석 결과 통합
if model_analysis:
    prompt += f"\n{model_analysis['generated_guideline']}"

# 차량 감지 시 ONE UNIT 보존 삽입
if bg_analysis.get("has_vehicle"):
    prompt = PRESERVATION_DETAILED + "\n" + prompt

# 바닥/색보정 매칭
prompt += ground_instruction + color_instruction
```

---

## 품질 검증 (7-criteria)

모든 생성 결과에 아래 7개 항목의 검수 점수가 포함된다.

| 항목 | 비중 | 설명 |
|------|------|------|
| model_preservation | 30% | 인물 보존 (포즈, 얼굴, 의상, 스케일) |
| physics_plausibility | 15% | 물리적 타당성 (앉기->의자, 기대기->벽) |
| ground_contact | 13% | 접지감 (발/그림자 자연스러움) |
| lighting_match | 12% | 조명 방향/강도 일치 |
| prop_style_consistency | 12% | 소품-배경 스타일 일치 |
| edge_quality | 10% | 인물 경계면 깔끔함 |
| perspective_match | 8% | 카메라 앵글/원근 일치 |

### PASS 기준
- `model_preservation = 100` (필수)
- `physics_plausibility >= 50` (필수)
- `total >= 95`

### 검증 스크립트

검증은 background_swap.py에 내장되어 있음. 별도 스크립트 불필요.

```bash
# Quality Mode (이미지별 검증 + 자동 재시도)
python background_swap.py photo.jpg "배경" --retry

# Sweep Mode (배치 일괄 검증 + 실패분 재생성)
python background_swap.py ./images "배경" --sweep
```

### 배치 결과 요약

```
=== Quality Check Report ===
Total: 66 images
RELEASE_READY: 52 (78.8%)
QUALITY_ISSUE: 14 (21.2%)

Top Issues:
1. lighting_match: 12 images
2. perspective_match: 8 images
3. ground_contact: 5 images
```

### 이전 5-criteria 시스템과의 관계

quality-check 스킬이 사용하던 이전 5-criteria 체계(model_preservation 35%, object_preservation 25%, color_temperature 20%, lighting_match 15%, edge_quality 10%)는 현재 7-criteria 시스템으로 대체됨. 이전 `object_preservation` 항목은 `prop_style_consistency` + ONE UNIT 보존 프롬프트로 흡수되었고, `color_temperature`는 `lighting_match` + VLM 배경분석의 `color_grading`으로 커버된다.

---

## 재시도 워크플로우 (enable_retry=True)

```
1. 생성 (temperature=0.2)
   |
2. 7-criteria 품질 검증
   |-- PASS -> 완료
   +-- FAIL |
3. 실패 원인 진단 (6가지 이슈 감지)
   - POSE_MISMATCH, FACE_CHANGED, SCALE_SHRUNK
   - PHYSICS_ERROR, CLOTHING_CHANGED, PROP_STYLE_MISMATCH
   |
4. 이슈별 프롬프트 보강
   - 각 이슈에 맞는 전용 강화 템플릿 적용
   |
5. 재생성 (temperature=0.1)
   |
6. 재검증 -> 실패 시 3-5 반복 (temperature=0.05)
```

---

## 배경 예시

```python
# 도시
swap(img, "캘리포니아 해변 석양과 팜트리")
swap(img, "파리 에펠탑이 보이는 카페 테라스")
swap(img, "뉴욕 브루클린 브릭월 앞")

# 자연
swap(img, "눈 내리는 스위스 산장")
swap(img, "하와이 열대 해변")

# 실내
swap(img, "모던 화이트 스튜디오")
swap(img, "럭셔리 호텔 로비")
```

---

## 모델 / 환경 설정

`gemini-3-pro-image-preview` 사용 (품질 보장)

```bash
# .env 파일
GEMINI_API_KEY=key1,key2,key3
```

여러 키 쉼표로 구분하면 자동 로테이션

---

## 아키텍처

`core/` 공통 모듈과 `auto_retry_pipeline/` 컴포넌트를 공유:

```
core/
+-- utils.py      -> ImageUtils, ApiKeyManager
+-- prompts.py    -> BASE_PRESERVATION_PROMPT, build_generation_prompt
+-- config.py     -> PipelineConfig

auto_retry_pipeline/
+-- generator.py  -> ImageGenerator (생성)
+-- validator.py  -> QualityValidator (검증)
+-- diagnoser.py  -> IssueDiagnoser (진단) [retry only]
+-- enhancer.py   -> PromptEnhancer (보강) [retry only]
```

---

## DO/DON'T

### DO

- 1024px 다운샘플링 (모델 물리 분석 - 공간 분석이므로 높은 해상도)
- 512px 다운샘플링 (배경 분석 - 텍스트 추출이므로 낮은 해상도 가능)
- `response_mime_type="application/json"` (VFX 분석 시 JSON 강제 반환)
- temperature 0.1 (VFX 분석 - 일관된 수치 추출)
- temperature 0.2 (배경 분석 - 정확한 분석)
- temperature 0.2 (이미지 생성 - 첫 시도)
- ONE UNIT 개념 적용 (인물+차량+오브젝트 = 하나의 덩어리)
- 항상 `AutoRetryPipeline` 사용 (background_swap.py 아님)
- 영문 프롬프트는 내부 처리용으로만 (사용자에게 노출하지 않음)
- 배치 모드에서 반드시 7-criteria 품질 검증 실행 (--retry 또는 --sweep)

### DON'T

- 원본 해상도 그대로 VLM에 전달 (다운샘플링 필수)
- 높은 temperature로 VFX 수치 추출 (일관성 저하)
- 인물과 차량을 개별 보존 지시 (반드시 ONE UNIT)
- 설치 논리 무시 (고정형 의자가 길 한복판에 있으면 부자연스러움)
- 접촉점 좌표 누락 (배경 합성 시 접지 불일치)
- 금지 컨텍스트 누락 (물리적으로 불가능한 배경 생성)
- 사용자에게 영문 프롬프트 설명
- 이모지 사용
- 과도한 친절함
- 사용자가 요청하지 않은 다른 스타일 제안
- 이전 5-criteria 기준 사용 (7-criteria가 최신)

---

## 관련 스킬

- **이미지생성_레퍼런스_image-gen-reference**: Gemini API, 프롬프트 패턴 기초
- **브랜드컷_brand-cut**: 화보컷 생성 워크플로우

---

**통합일**: 2026-02-02
**통합 출처**: 배경교체, 배경분석, 배경생성워크플로우, 오브젝트보존, quality-check, 모델분석
