---
name: reference-brandcut
description: 레퍼런스 이미지 기반 브랜드컷 생성 - 페이스스왑 + 착장스왑 + 배경변경
user-invocable: true
trigger-keywords: ["레퍼런스", "참조 이미지", "이거랑 비슷하게", "이 스타일로", "레퍼런스 브랜드컷"]
---

# 레퍼런스 기반 브랜드컷 생성

> **핵심 개념**: Face Swap + Outfit Swap + Background Change ONLY
> 레퍼런스 이미지의 **정확한 포즈/표정/앵글/구도를 유지**하면서 얼굴/착장/배경만 변경
> 레퍼런스 이미지는 **직접 전달** (텍스트 분석 X) → 정확한 포즈 보존

---

## 모델 필수 확인

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ 이미지 생성: gemini-3-pro-image-preview                  │
│  ✅ VLM 분석: gemini-3.0-flash-preview (텍스트 분석용)               │
│                                                             │
│  ❌ 절대 금지:                                               │
│     - gemini-2.0-flash-exp-image-generation (품질 낮음)     │
│     - 배경 이미지 직접 전달 (어색한 합성 유발)               │
└─────────────────────────────────────────────────────────────┘
```

---

## V3 핵심 컨셉

```
┌─────────────────────────────────────────────────────────────┐
│  레퍼런스 브랜드컷 = Face Swap + Outfit Swap + BG Change    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  레퍼런스에서 유지:        변경:                            │
│  ├─ 포즈 (EXACT)          ├─ 얼굴 → 제공된 얼굴로 교체     │
│  ├─ 표정 (EXACT)          ├─ 착장 → 제공된 착장으로 교체   │
│  ├─ 앵글/구도 (EXACT)     └─ 배경 → 텍스트 설명으로 생성   │
│  ├─ 프레이밍 (EXACT)                                        │
│  └─ 체형 비율 (EXACT)                                       │
│                                                             │
│  ⚠️  레퍼런스 이미지는 API에 직접 전달 (텍스트 변환 X)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 입력 구조

| 입력 | 필수 | 수량 | 처리 방식 |
|------|------|------|----------|
| 레퍼런스 이미지 | ✅ | 1장 | **API에 직접 전달** (포즈/표정/구도 보존) |
| 얼굴 이미지 폴더 | ✅ | 자동 1~2장 선택 | 이미지로 직접 전달 (Face Swap) |
| 착장 이미지 폴더 | ✅ | N장 | 이미지로 직접 전달 + VLM 분석 텍스트 (Outfit Swap) |
| 배경 이미지/텍스트 | ❌ | 0~1장 | VLM 분석 → **텍스트로만** 전달 (인물 무시) |

### 이미지 전달 순서 (중요!)

```
1. 프롬프트 (텍스트)
2. 레퍼런스 이미지 (첫 번째 - 포즈 기준)
3. 얼굴 이미지들 (Face Swap 대상)
4. 착장 이미지들 (Outfit Swap 대상)
```

### 착장 처리 방식 (듀얼 어프로치)

1. **이미지 직접 전달**: API에 착장 이미지 첨부
2. **텍스트 보조**: VLM 분석 결과를 프롬프트에 추가
3. **둘 다 사용**: 이미지로 시각적 참조 + 텍스트로 세부사항 명시

---

## 대화 플로우 (효율적 버전)

> **원칙**: 한 번에 모든 경로를 수집해서 왔다갔다 최소화

```
1. 사용자: "레퍼런스로 브랜드컷 만들어줘" / "이 이미지랑 비슷하게"

2. Claude: "레퍼런스 이미지 경로 알려주세요!"

3. 사용자: [이미지 경로]

4. Claude: [레퍼런스 분석 결과 테이블 보여주기]
   그 다음 바로:
   "다음 경로들을 알려주세요:
   1. 얼굴 폴더 (필수)
   2. 착장 폴더 (선택 - 없으면 레퍼런스 착장 사용)
   3. 배경 이미지 (선택 - 없으면 레퍼런스 배경 사용)"

5. 사용자: [경로들 한 번에 또는 나눠서 입력]
   예: "얼굴: D:\faces, 착장: D:\outfits"
   예: "D:\faces" (얼굴만, 나머지는 레퍼런스 사용)

6. Claude: [모든 분석 결과 테이블로 보여주기]
   - 얼굴 선택 결과
   - 착장 분석 결과 (있으면)
   - 배경 분석 결과 (있으면)

7. Claude: [AskUserQuestion - 비율/수량 한 번에 선택]

8. Claude: [이미지 생성]
```

### 경로 입력 파싱 예시

사용자가 다양한 형태로 입력해도 파싱:
- `D:\faces` → 얼굴만
- `얼굴: D:\faces, 착장: D:\outfits` → 얼굴 + 착장
- `D:\faces / D:\outfits / D:\bg.jpg` → 순서대로 얼굴/착장/배경
- `face=D:\faces outfit=D:\outfits bg=D:\bg.jpg` → 키=값 형태

### AskUserQuestion - 최종 옵션만

```python
# 비율 + 수량 한 번에 선택 (다른 건 텍스트로 받음)
AskUserQuestion(questions=[
    {
        "question": "이미지 비율을 선택해주세요",
        "header": "비율",
        "options": [
            {"label": "3:4 (Recommended)", "description": "에디토리얼 표준, 세로형"},
            {"label": "4:5", "description": "인스타그램 피드 최적화"},
            {"label": "9:16", "description": "스토리/릴스용 세로 풀스크린"},
            {"label": "1:1", "description": "정사각형"}
        ],
        "multiSelect": False
    },
    {
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "1장", "description": "테스트용 빠른 생성"},
            {"label": "3장 (Recommended)", "description": "다양한 결과 비교"},
            {"label": "5장", "description": "충분한 선택지"}
        ],
        "multiSelect": False
    }
])
```

---

## VLM 분석 프롬프트

### 레퍼런스 이미지 분석

```python
REFERENCE_ANALYSIS_PROMPT = """
이 이미지를 분석해서 다음 정보를 JSON으로 추출해주세요:

{
  "style": {
    "overall_mood": "전체적인 무드 (예: 미니멀, 럭셔리, 스트릿, 청순)",
    "color_tone": "색감 (예: 차가운 톤, 따뜻한 톤, 뉴트럴)",
    "aesthetic": "미학적 스타일 (예: 에디토리얼, 캐주얼, 하이패션)"
  },
  "pose": {
    "body_position": "자세 (예: 서있음, 앉아있음, 기대어있음)",
    "pose_detail": "구체적 포즈 (예: 벽에 기대어 한 손 주머니에)",
    "expression": "표정 (예: 무표정, 살짝 미소, 도도한)"
  },
  "composition": {
    "framing": "프레이밍 (예: 클로즈업, 상반신, 전신)",
    "subject_position": "피사체 위치 (예: 중앙, 좌측 1/3, 우측)",
    "camera_angle": "카메라 앵글 (예: 아이레벨, 로우앵글, 하이앵글)"
  },
  "lighting": {
    "type": "조명 종류 (예: 자연광, 스튜디오, 혼합)",
    "direction": "조명 방향 (예: 정면, 측면, 역광)",
    "quality": "조명 품질 (예: 부드러운, 강한, 드라마틱)"
  },
  "background": {
    "setting": "배경 장소 (예: 콘크리트 벽, 스튜디오, 야외)",
    "description": "배경 상세 설명"
  }
}
"""
```

### 착장 이미지 분석

```python
OUTFIT_ANALYSIS_PROMPT = """
이 이미지의 착장(의류/액세서리)을 분석해서 AI 이미지 생성에 사용할 수 있도록
상세하게 설명해주세요.

다음 항목별로 분석해주세요:
1. headwear (모자/헤어액세서리): 종류, 색상, 소재, 브랜드 로고 위치
2. outer (아우터): 종류, 색상, 소재, 디테일, 로고/패턴
3. top (상의): 종류, 색상, 소재, 넥라인, 기장
4. bottom (하의): 종류, 색상, 소재, 핏, 기장
5. shoes (신발): 종류, 색상, 소재, 브랜드
6. accessories (액세서리): 가방, 목걸이, 귀걸이 등

JSON 형식:
{
  "headwear": {"type": "", "color": "", "material": "", "details": ""},
  "outer": {"type": "", "color": "", "material": "", "details": "", "logo": ""},
  "top": {"type": "", "color": "", "material": "", "details": ""},
  "bottom": {"type": "", "color": "", "material": "", "fit": "", "details": ""},
  "shoes": {"type": "", "color": "", "material": "", "brand": ""},
  "accessories": [{"type": "", "description": ""}],
  "outfit_summary": "전체 착장을 한 문장으로 요약 (프롬프트용)",
  "style_keywords": ["스타일 키워드1", "스타일 키워드2"]
}

**중요**:
- 로고 위치가 있으면 정확히 명시 (예: front_left, back_center)
- 색상은 구체적으로 (예: "brown" 대신 "chocolate brown", "burgundy")
- outfit_summary는 이미지 생성 프롬프트에 바로 사용할 수 있게 작성
"""
```

### 배경 이미지 분석 (텍스트 변환용, 인물 무시)

```python
BACKGROUND_ANALYSIS_PROMPT = """
이 이미지에서 **배경만** 분석해주세요.
**이미지에 사람이 있더라도 완전히 무시하고 배경 환경만 분석합니다.**

다음 정보를 포함해주세요:
1. 장소/공간 타입 (예: 주차장, 갤러리, 카페, 도심 거리)
2. 주요 요소들 (예: 콘크리트 바닥, 그래피티 벽, 철제 문) - 인물 제외
3. 색감/톤 (예: 차가운 회색 톤, 따뜻한 베이지)
4. 조명 상태 (예: 오후 자연광, 형광등, 네온)
5. 분위기 (예: 인더스트리얼, 미니멀, 빈티지)

JSON 형식:
{
  "location_type": "장소 타입",
  "key_elements": ["요소1", "요소2", "요소3"],
  "color_palette": "색감 설명",
  "lighting": "조명 상태",
  "atmosphere": "분위기",
  "prompt_description": "이 배경을 재현하기 위한 프롬프트 (영어, 상세하게)"
}

**중요**:
- 이미지에 사람이 있어도 **완전히 무시**하고 배경만 설명
- prompt_description에 사람 관련 내용 절대 포함 금지
- 이미지 생성 AI가 이 배경을 재현할 수 있도록 구체적으로 작성
"""
```

---

## 얼굴 이미지 자동 선택 로직

```python
FACE_SELECTION_PROMPT = """
이 폴더의 얼굴 이미지들을 분석해서 AI 이미지 생성에 가장 적합한 1~2장을 선택해주세요.

선택 기준 (우선순위):
1. 정면 또는 살짝 측면 (3/4 뷰)
2. 조명이 균일하고 밝은 것
3. 표정이 자연스러운 것
4. 해상도가 높은 것
5. 얼굴이 화면의 50% 이상 차지하는 것

JSON 형식:
{
  "selected_images": [
    {
      "filename": "파일명",
      "reason": "선택 이유",
      "face_angle": "정면/측면/3/4뷰",
      "quality_score": 1-10
    }
  ],
  "total_analyzed": 분석한 총 이미지 수
}

최대 2장만 선택하세요. 1장으로도 충분하면 1장만 선택하세요.
"""
```

---

## 프롬프트 조립 로직

```python
def build_reference_prompt(reference_analysis, outfit_analysis=None, background_analysis=None):
    """
    레퍼런스 분석 + 착장 분석 + 배경 분석 결과를 합쳐서 프롬프트 생성

    핵심:
    - 착장: outfit_analysis가 있으면 사용, 없으면 레퍼런스 착장 사용
    - 배경: 텍스트로만 전달 (이미지 직접 전달 X)
    """

    # 레퍼런스에서 추출한 스타일 요소
    style = reference_analysis["style"]
    pose = reference_analysis["pose"]
    composition = reference_analysis["composition"]
    lighting = reference_analysis["lighting"]

    # 착장 결정 (우선순위: 착장 폴더 분석 > 레퍼런스 착장)
    if outfit_analysis:
        outfit_prompt = outfit_analysis["outfit_summary"]
        style_keywords = ", ".join(outfit_analysis.get("style_keywords", []))
    else:
        # 레퍼런스의 착장 정보 사용 (있으면)
        outfit_prompt = reference_analysis.get("outfit", {}).get("description", "")
        style_keywords = ""

    # 배경 결정 (우선순위: 배경 이미지 분석 > 레퍼런스 배경)
    if background_analysis:
        background_prompt = background_analysis["prompt_description"]
    else:
        background_prompt = reference_analysis["background"]["description"]

    # 프롬프트 조립
    prompt = f"""
이 얼굴로 사진 생성:

[스타일]
- 무드: {style["overall_mood"]}
- 색감: {style["color_tone"]}
- 미학: {style["aesthetic"]}
{f"- 키워드: {style_keywords}" if style_keywords else ""}

[포즈]
- 자세: {pose["body_position"]}, {pose["pose_detail"]}
- 표정: {pose["expression"]}

[구도]
- 프레이밍: {composition["framing"]}
- 위치: {composition["subject_position"]}
- 앵글: {composition["camera_angle"]}

[조명]
- 타입: {lighting["type"]}
- 방향: {lighting["direction"]}
- 품질: {lighting["quality"]}

[착장 - 정확하게 재현]
{outfit_prompt}

[배경 - 텍스트로만 생성, 인물 없음]
{background_prompt}

스타일: 고품질 패션 화보, 실제 사진처럼
"""

    return prompt.strip()
```

### 착장 분석 함수

```python
def analyze_outfit(outfit_folder):
    """착장 이미지 폴더를 분석해서 착장 정보 추출"""
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = [f for f in os.listdir(outfit_folder)
              if os.path.splitext(f)[1].lower() in extensions]

    if not images:
        return None

    # 첫 번째 이미지로 착장 분석 (대표 이미지)
    # 여러 장이면 각각 분석 후 병합 가능
    outfit_path = os.path.join(outfit_folder, images[0])
    return analyze_with_vlm(outfit_path, OUTFIT_ANALYSIS_PROMPT)
```

---

## API 호출 코드

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import json

# ============ API 키 로드 ============
def load_api_keys():
    """프로젝트 루트의 .env에서 API 키 로드"""
    env_path = ".env"
    api_keys = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                    _, value = line.strip().split('=', 1)
                    api_keys.extend([k.strip() for k in value.split(',')])
    return api_keys or [os.environ.get("GEMINI_API_KEY", "")]

API_KEYS = load_api_keys()
key_index = 0

def get_next_api_key():
    global key_index
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ============ 이미지 변환 ============
def pil_to_part(img, max_size=1024):
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

# ============ VLM 분석 (텍스트 응답) ============
def analyze_with_vlm(image_path, prompt):
    """이미지를 VLM으로 분석해서 텍스트(JSON) 응답 받기"""
    client = genai.Client(api_key=get_next_api_key())

    img = Image.open(image_path).convert("RGB")

    response = client.models.generate_content(
        model="gemini-2.0-flash",  # VLM 분석용
        contents=[types.Content(role="user", parts=[
            types.Part(text=prompt),
            pil_to_part(img)
        ])],
        config=types.GenerateContentConfig(
            temperature=0.3,
            response_modalities=["TEXT"]  # 텍스트만 응답
        )
    )

    # JSON 파싱
    text = response.candidates[0].content.parts[0].text
    # JSON 블록 추출
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

# ============ 레퍼런스 분석 ============
def analyze_reference(reference_path):
    """레퍼런스 이미지에서 스타일/포즈/구도/조명 추출"""
    return analyze_with_vlm(reference_path, REFERENCE_ANALYSIS_PROMPT)

# ============ 배경 분석 (텍스트 변환) ============
def analyze_background(background_path):
    """배경 이미지를 분석해서 텍스트 프롬프트로 변환"""
    return analyze_with_vlm(background_path, BACKGROUND_ANALYSIS_PROMPT)

# ============ 얼굴 이미지 자동 선택 ============
def select_face_images(face_folder):
    """폴더에서 가장 적합한 얼굴 이미지 1~2장 선택"""
    # 이미지 파일 목록
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = [f for f in os.listdir(face_folder)
              if os.path.splitext(f)[1].lower() in extensions]

    if not images:
        raise ValueError(f"폴더에 이미지가 없습니다: {face_folder}")

    if len(images) <= 2:
        # 2장 이하면 전부 사용
        return [os.path.join(face_folder, img) for img in images]

    # 3장 이상이면 VLM으로 선택
    # 첫 번째 이미지로 대표 분석 (전체 폴더 분석은 비용이 높아서)
    # 실제로는 각 이미지를 빠르게 평가

    selected = []
    for img_name in images[:5]:  # 최대 5장만 분석
        img_path = os.path.join(face_folder, img_name)
        try:
            img = Image.open(img_path)
            # 간단한 품질 체크 (해상도)
            if img.size[0] >= 512 and img.size[1] >= 512:
                selected.append(img_path)
                if len(selected) >= 2:
                    break
        except:
            continue

    return selected if selected else [os.path.join(face_folder, images[0])]

# ============ 이미지 생성 ============
def generate_reference_brandcut(
    reference_path,
    face_folder,
    background_path=None,
    aspect_ratio="3:4",
    count=1
):
    """
    레퍼런스 기반 브랜드컷 생성

    Args:
        reference_path: 레퍼런스 이미지 경로 (스타일 참조)
        face_folder: 얼굴 이미지 폴더 경로
        background_path: 배경 이미지 경로 (없으면 레퍼런스 배경 사용)
        aspect_ratio: 비율 ("3:4", "4:5", "9:16", "1:1")
        count: 생성 수량

    Returns:
        List[PIL.Image]
    """

    # 1. 레퍼런스 분석
    print("📷 레퍼런스 이미지 분석 중...")
    reference_analysis = analyze_reference(reference_path)
    print(f"  - 스타일: {reference_analysis['style']['overall_mood']}")
    print(f"  - 포즈: {reference_analysis['pose']['pose_detail']}")

    # 2. 배경 분석 (있으면)
    background_analysis = None
    if background_path and os.path.exists(background_path):
        print("🏞️ 배경 이미지 분석 중...")
        background_analysis = analyze_background(background_path)
        print(f"  - 배경: {background_analysis['location_type']}")

    # 3. 얼굴 이미지 선택
    print("👤 얼굴 이미지 선택 중...")
    face_paths = select_face_images(face_folder)
    print(f"  - 선택됨: {[os.path.basename(p) for p in face_paths]}")

    # 4. 프롬프트 조립
    prompt = build_reference_prompt(reference_analysis, background_analysis)
    print(f"\n📝 최종 프롬프트:\n{prompt[:200]}...")

    # 5. 얼굴 이미지 로드
    face_images = [Image.open(p).convert("RGB") for p in face_paths]

    # 6. 이미지 생성
    results = []
    for i in range(count):
        print(f"\n🎨 이미지 생성 중... ({i+1}/{count})")

        # API 호출
        client = genai.Client(api_key=get_next_api_key())

        # 프롬프트 + 얼굴 이미지 조합 (배경 이미지는 전달 안 함!)
        parts = [types.Part(text=prompt)]
        for face_img in face_images:
            parts.append(pil_to_part(face_img))

        try:
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",  # 이미지 생성용
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="2K"
                    )
                )
            )

            # 결과 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    results.append(img)
                    print(f"  ✅ 생성 완료!")
                    break

        except Exception as e:
            print(f"  ❌ 생성 실패: {e}")
            continue

    return results
```

---

## 전체 사용 예시

```python
from datetime import datetime
import os

# 1. 경로 설정
reference_path = r"D:\사진\reference.jpg"
face_folder = r"D:\사진\얼굴"
background_path = r"D:\사진\배경.jpg"  # 선택사항

# 2. 출력 폴더
output_dir = f"Fnf_studio_outputs/reference_brandcut/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(output_dir, exist_ok=True)

# 3. 생성
results = generate_reference_brandcut(
    reference_path=reference_path,
    face_folder=face_folder,
    background_path=background_path,  # 없으면 None
    aspect_ratio="3:4",
    count=3
)

# 4. 저장
for i, img in enumerate(results):
    output_path = f"{output_dir}/result_{i+1:02d}.png"
    img.save(output_path)
    print(f"💾 저장: {output_path}")
```

---

## 핵심 원칙 (V3)

| 항목 | 처리 방식 |
|------|----------|
| 레퍼런스 이미지 | **API에 직접 전달** (포즈/표정/구도 보존 핵심!) |
| 얼굴 이미지 | **이미지로 직접 전달** (Face Swap) |
| 착장 이미지 | **이미지로 직접 전달** + VLM 분석 텍스트 보조 (Outfit Swap) |
| 배경 이미지 | VLM 분석 → **텍스트 프롬프트로만 전달** (인물 무시!) |

**왜 레퍼런스를 직접 전달?**
- 텍스트로 변환하면 정확한 포즈/표정/앵글이 손실됨
- 직접 전달하면 AI가 정확히 같은 포즈를 재현 가능
- "Face Swap + Outfit Swap" 수준의 정확도 달성

**왜 배경을 텍스트로만?**
- 배경 이미지를 직접 전달하면 어색한 합성 발생
- 텍스트로 설명하면 AI가 자연스럽게 배경을 재생성
- 조명/그림자/원근감이 자연스럽게 매칭됨

**배경 이미지의 인물 무시**
- 배경 참조용 이미지에 사람이 있어도 **완전히 무시**
- VLM 분석 시 "인물 제외하고 배경만 분석" 명시
- prompt_description에 사람 관련 내용 포함 금지

---

## V3 프롬프트 템플릿

```python
V3_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION - FACE SWAP + OUTFIT SWAP + BACKGROUND CHANGE]

You are given:
1. A REFERENCE IMAGE - This shows the EXACT pose, expression, angle, composition, and framing to replicate
2. FACE IMAGES - Use this face instead of the reference face
3. OUTFIT IMAGES - Use these outfits instead of the reference outfit

YOUR TASK:
- Keep the EXACT same pose from the reference image
- Keep the EXACT same expression from the reference image
- Keep the EXACT same camera angle from the reference image
- Keep the EXACT same composition/framing from the reference image
- Keep the EXACT same body proportions (model proportions, long legs, slim)
- SWAP the face with the provided face images
- SWAP the outfit with the provided outfit images
- CHANGE the background based on the text description below

This is essentially a FACE SWAP + OUTFIT SWAP operation.
The pose and composition MUST match the reference image EXACTLY.

[BODY PROPORTIONS - MUST PRESERVE]
- Fashion model proportions (8-head ratio)
- Long legs (4+ heads)
- Slim, elongated silhouette
- Small head proportion
- Height appearance: 170-175cm

[OUTFIT TO USE - From outfit images]
{outfit_descriptions}

[BACKGROUND - Generate from text, NOT from reference]
{background_description}

[LIGHTING]
- Match the lighting mood from reference
- Dramatic studio lighting
- Cool color temperature (5500-6000K)

[OUTPUT]
- Photo aspect ratio: 3:4 vertical portrait
- High-end fashion editorial quality
- Magazine cover worthy
- Sharp focus, professional photography
- Natural skin texture (NOT plastic/artificial)

REMEMBER: The pose, expression, angle, and composition MUST be IDENTICAL to the reference image.
Only the face, outfit, and background should change.
"""
```

---

## V3 코드 패턴

```python
from core.config import IMAGE_MODEL, VISION_MODEL

def generate_reference_brandcut_v3(
    reference_path,
    face_paths,
    outfit_paths,
    outfit_descriptions,
    background_description,
):
    """
    V3: Direct reference approach
    - Reference image passed directly (not converted to text)
    - Preserves exact pose/expression/angle/composition
    """

    # Build prompt
    prompt = V3_PROMPT_TEMPLATE.format(
        outfit_descriptions=outfit_descriptions,
        background_description=background_description
    )

    # Build parts in ORDER (important!)
    parts = [types.Part(text=prompt)]

    # 1. Reference image FIRST (pose reference)
    reference_img = Image.open(reference_path).convert("RGB")
    parts.append(pil_to_part(reference_img))

    # 2. Face images (for face swap)
    for face_path in face_paths:
        face_img = Image.open(face_path).convert("RGB")
        parts.append(pil_to_part(face_img))

    # 3. Outfit images (for outfit swap)
    for outfit_path in outfit_paths:
        outfit_img = Image.open(outfit_path).convert("RGB")
        parts.append(pil_to_part(outfit_img))

    # Generate
    client = genai.Client(api_key=get_next_api_key())

    response = client.models.generate_content(
        model=IMAGE_MODEL,  # gemini-3-pro-image-preview
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.2,  # Low for consistency
            response_modalities=["IMAGE", "TEXT"],
        )
    )

    return extract_image(response)
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 스타일이 다름 | 레퍼런스 분석 부족 | VLM 프롬프트 구체화 |
| 배경이 어색 | 배경 이미지 직접 전달 | 텍스트로만 전달 (이 스킬 방식) |
| 얼굴 안 닮음 | 얼굴 이미지 품질 | 정면 고해상도 사용 |
| 포즈가 다름 | pose_detail 추출 부족 | 레퍼런스 분석 강화 |

---

## 출력 폴더

```
Fnf_studio_outputs/
└── reference_brandcut/
    └── 20260209_103045/
        ├── result_01.png
        ├── result_02.png
        └── analysis_log.json  # 분석 결과 기록
```

---

## 파일 구조

```
.claude/skills/레퍼런스브랜드컷_reference-brandcut/
├── SKILL.md          # 이 문서
└── examples/         # 예시 이미지 (선택)
```
