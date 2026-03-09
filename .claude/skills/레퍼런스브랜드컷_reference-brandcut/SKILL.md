---
name: reference-brandcut
description: 레퍼런스 이미지 기반 브랜드컷 생성 - 페이스스왑 + 착장스왑 + 배경변경
user-invocable: true
trigger-keywords: ["레퍼런스 브랜드컷", "참조 이미지 브랜드컷", "이거랑 비슷하게 브랜드컷", "이 스타일로 브랜드컷", "레퍼런스 브랜드컷"]
---

# 레퍼런스 기반 브랜드컷 생성

> **핵심 개념**: Face Swap + Outfit Swap + Background Change ONLY
> 레퍼런스 이미지의 **정확한 포즈/표정/앵글/구도를 유지**하면서 얼굴/착장/배경만 변경
> 레퍼런스 이미지는 **직접 전달** (텍스트 분석 X) → 정확한 포즈 보존

---

## 모델 필수 확인

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ 이미지 생성: IMAGE_MODEL (gemini-3-pro-image-preview)   │
│  ✅ VLM 분석: VISION_MODEL (gemini-3-flash-preview)         │
│                                                             │
│  ⚠️  반드시 core/config.py 에서 import 해서 사용!           │
│  ✅ 배경 이미지 직접 전달 가능 (V4 업데이트)                │
└─────────────────────────────────────────────────────────────┘
```

---

## V4 핵심 컨셉

```
┌─────────────────────────────────────────────────────────────┐
│  레퍼런스 브랜드컷 = Face Swap + Outfit Swap + BG Change    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  레퍼런스에서 유지:        변경:                            │
│  ├─ 포즈 (EXACT)          ├─ 얼굴 → 제공된 얼굴로 교체     │
│  ├─ 표정 (EXACT)          ├─ 착장 → 제공된 착장으로 교체   │
│  ├─ 앵글/구도 (EXACT)     └─ 배경 → 이미지 또는 텍스트     │
│  ├─ 프레이밍 (EXACT)                                        │
│  └─ 체형 비율 (EXACT)                                       │
│                                                             │
│  ✅ 모든 이미지를 1회 API 호출로 동시 전달                  │
│  ✅ 배경 이미지 직접 전달 시 더 정확한 배경 재현 가능       │
└─────────────────────────────────────────────────────────────┘
```

---

## 입력 구조

| 입력 | 필수 | 수량 | 처리 방식 |
|------|------|------|----------|
| 레퍼런스 이미지 | ✅ | 1장 | **API에 직접 전달** (포즈/표정/구도 보존) |
| 얼굴 이미지 | ✅ | 1~2장 | **API에 직접 전달** (Face Swap) |
| 착장 이미지 | ❌ | N장 | **API에 직접 전달** (Outfit Swap) |
| 배경 이미지 | ❌ | 0~1장 | **API에 직접 전달** (정확한 배경 재현) ← V4 변경! |

### 이미지 전달 순서 (중요!)

```
┌─────────────────────────────────────────────────────────────┐
│  1회 API 호출에 모든 이미지 동시 전달                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 프롬프트 (텍스트) - 각 이미지 역할 명시                 │
│  2. IMAGE 1: 레퍼런스 이미지 (포즈/표정/앵글 기준)          │
│  3. IMAGE 2: 얼굴 이미지 (Face Swap 대상)                   │
│  4. IMAGE 3: 착장 이미지 (Outfit Swap 대상)                 │
│  5. IMAGE 4: 배경 이미지 (Background 기준) ← V4 추가!       │
│                                                             │
│  → Gemini가 한번에 합성하여 결과물 생성                     │
└─────────────────────────────────────────────────────────────┘
```

### 착장 처리 방식 (듀얼 어프로치)

1. **이미지 직접 전달**: API에 착장 이미지 첨부
2. **텍스트 보조**: VLM 분석 결과를 프롬프트에 추가
3. **둘 다 사용**: 이미지로 시각적 참조 + 텍스트로 세부사항 명시

---

## 대화 플로우 (경로 순차 → 옵션 클릭 → 일괄 분석)

> **원칙**: 경로 하나씩 질문 → 옵션 클릭 선택 → 마지막에 한번에 분석/생성

### 플로우

```
1. 사용자: "레퍼런스 브랜드컷"

2. Claude: "레퍼런스 이미지 경로?"
3. 사용자: D:\ref.jpg

4. Claude: "얼굴 폴더 경로?"
5. 사용자: D:\faces

6. Claude: "착장 폴더? (없으면 '없음' 또는 엔터)"
7. 사용자: D:\outfits (또는 "없음")

8. Claude: "배경 이미지? ('레퍼런스 처럼'' 또는 '입력')"
9. 사용자: 없음

10. Claude: [AskUserQuestion - 비율/수량 클릭 선택]

11. 사용자: 클릭으로 선택

12. Claude:
    - 모든 이미지 한번에 병렬 분석
    - 분석 결과 테이블 출력
    - 이미지 생성
    - 결과 저장 및 경로 안내
```

### 경로 질문 (순차, 일반 텍스트)

| 순서 | 질문 | 필수 |
|------|------|------|
| 1 | "레퍼런스 이미지 경로?" | ✅ |
| 2 | "얼굴 폴더 경로?" | ✅ |
| 3 | "착장 폴더? (없으면 '없음')" | ❌ |
| 4 | "배경 이미지? (없으면 '없음')" | ❌ |

### 옵션 선택 (AskUserQuestion 클릭)

```python
AskUserQuestion(questions=[
    {
        "question": "이미지 비율을 선택해주세요",
        "header": "비율",
        "options": [
            {"label": "3:4 (Recommended)", "description": "에디토리얼 표준, 세로형"},
            {"label": "4:5", "description": "인스타그램 피드"},
            {"label": "9:16", "description": "스토리/릴스"},
            {"label": "1:1", "description": "정사각형"}
        ],
        "multiSelect": False
    },
    {
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "1장", "description": "테스트용"},
            {"label": "3장 (Recommended)", "description": "다양한 결과 비교"},
            {"label": "5장", "description": "충분한 선택지"}
        ],
        "multiSelect": False
    }
])
```

### 기본값

| 항목 | 기본값 |
|------|--------|
| 착장 | 레퍼런스 착장 유지 |
| 배경 | 레퍼런스 배경 유지 |

---

## VLM 분석 프롬프트

### 레퍼런스 이미지 분석 (V2 - 순간포착 느낌 포함)

```python
REFERENCE_ANALYSIS_PROMPT = """
이 이미지를 분석해서 다음 정보를 JSON으로 추출해주세요.
특히 "순간포착(candid)" vs "작정하고 찍은(posed)" 느낌을 정확히 구분해주세요.

{
  "style": {
    "overall_mood": "전체적인 무드 (예: 미니멀, 럭셔리, 스트릿, 청순)",
    "color_tone": "색감 (예: 차가운 톤, 따뜻한 톤, 뉴트럴)",
    "aesthetic": "미학적 스타일 (예: 에디토리얼, 캐주얼, 하이패션)"
  },
  "expression": {
    "mouth": "입 상태 (닫힘/살짝 벌림/말하는 중/웃음)",
    "eyes": "눈 상태 (정면 응시/측면/자연스러운 시선/감음)",
    "overall_vibe": "촬영 느낌 (posed/candid/caught-mid-moment)",
    "specific_details": "구체적 묘사 (예: 말하려다 찍힌 느낌, 바람에 머리 날리며)"
  },
  "pose": {
    "body_position": "자세 (예: 서있음, 앉아있음, 기대어있음)",
    "pose_detail": "구체적 포즈 (예: 벽에 기대어 한 손 주머니에)",
    "hand_position": "손 위치"
  },
  "hair": {
    "movement": "움직임 (정적/살짝 날림/크게 날림/바람에 휘날림)",
    "style": "헤어스타일",
    "direction": "날리는 방향 (있으면)"
  },
  "camera": {
    "type": "카메라 타입 추정 (DSLR/스마트폰/필름)",
    "focus": "포커스 상태 (sharp/slight-blur/motion-blur)",
    "feel": "느낌 (professional/casual-snapshot/candid-moment)"
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
  },
  "prompt_description": "이 정확한 이미지를 재현하기 위한 영어 프롬프트 (상세하게, candid/posed 느낌 포함)"
}

**중요**:
- candid/순간포착이면 반드시 표시 (말하려다 찍힘, 자연스러운 순간 등)
- 머리카락 움직임 상세히 (바람에 날리는 방향, 정도)
- 스마트폰 느낌이면 명시 (캐주얼 스냅샷, 약간의 흔들림 등)
"""
```

### 착장 이미지 분석 (VLM 자동화)

**핵심**: 착장 폴더의 각 이미지를 VLM으로 개별 분석 → 프롬프트에 자동 포함

```python
from core.config import VISION_MODEL  # gemini-3-flash-preview

OUTFIT_ITEM_ANALYSIS_PROMPT = """
이 이미지의 의류/액세서리를 분석해서 AI 이미지 생성 프롬프트용으로 상세하게 설명해주세요.

JSON 형식으로 응답:
{
  "item_type": "의류 종류 (예: beanie, jacket, pants, bag, top)",
  "color": "구체적 색상 (예: dark charcoal gray, ivory cream)",
  "material": "소재/질감 (예: fuzzy mohair, washed denim, leather)",
  "logo": {
    "exists": true/false,
    "text": "로고 텍스트 (예: NY, Red Sox)",
    "position": "위치 (예: right side, center, front left)",
    "color": "로고 색상"
  },
  "details": "기타 특징 (예: wide fit, cargo pockets, stripe trim)",
  "prompt_description": "이미지 생성용 한 줄 설명 (영어)"
}

**중요**:
- 소재/질감을 매우 구체적으로 (fuzzy, fluffy, smooth, washed 등)
- 로고 위치를 정확하게 (center, left, right, front, back)
- prompt_description은 영어로, AI가 재현할 수 있게 상세하게
"""

def analyze_outfit_with_vlm(image_path):
    """착장 이미지를 VLM으로 분석해서 세부사항 추출"""
    client = genai.Client(api_key=get_next_api_key())

    img = Image.open(image_path).convert("RGB")
    if max(img.size) > 1024:
        img.thumbnail((1024, 1024), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG")
    img_part = types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

    response = client.models.generate_content(
        model=VISION_MODEL,  # config에서 로드
        contents=[types.Content(role="user", parts=[
            types.Part(text=OUTFIT_ITEM_ANALYSIS_PROMPT),
            img_part
        ])],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_modalities=["TEXT"]
        )
    )

    # JSON 파싱
    text = response.candidates[0].content.parts[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

def analyze_all_outfits(outfit_folder):
    """착장 폴더 전체를 VLM으로 분석"""
    outfit_paths = [
        os.path.join(outfit_folder, f)
        for f in os.listdir(outfit_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    ]

    analyses = []
    for path in outfit_paths:
        analysis = analyze_outfit_with_vlm(path)
        analyses.append(analysis)

    return analyses
```

### 배경 이미지 분석 (선택사항 - V4에서는 직접 전달 권장)

> **V4 권장**: 배경 이미지를 API에 직접 전달하면 더 정확한 재현 가능.
> VLM 분석은 배경 이미지가 없거나 텍스트 설명만 필요할 때 사용.

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
    - 배경: V4에서는 이미지 직접 전달 가능 (더 정확한 재현)
    - 배경 이미지 있으면 프롬프트에 IMAGE 4 역할만 명시
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

[배경 - IMAGE 4 참조 또는 텍스트]
{background_prompt}
# V4: 배경 이미지가 있으면 "Use background from IMAGE 4" 로 대체

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

# Config에서 모델 상수 로드 (절대 하드코딩 금지!)
from core.config import IMAGE_MODEL, VISION_MODEL

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
        model=VISION_MODEL,  # config에서 로드
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
                model=IMAGE_MODEL,  # gemini-3-pro-image-preview (config에서 로드)
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

## 핵심 원칙 (V4)

| 항목 | 처리 방식 |
|------|----------|
| 레퍼런스 이미지 | **API에 직접 전달** (포즈/표정/머리카락/카메라느낌 보존!) |
| 얼굴 이미지 | **API에 직접 전달** (Face Swap) |
| 착장 이미지 | **API에 직접 전달** (Outfit Swap) |
| 배경 이미지 | **API에 직접 전달** (정확한 배경 재현) ← V4 변경! |

**왜 모든 이미지를 직접 전달?**
- 텍스트 변환 시 정보 손실 발생
- 이미지 직접 전달 시 더 정확한 재현 가능
- 1회 API 호출로 모든 이미지를 동시에 합성

**배경 이미지 직접 전달의 장점 (V4)**
- 특정 간판, 가판대, 거리 요소 등 정확히 재현
- VLM 분석 → 텍스트 변환 과정에서의 정보 손실 방지
- "이 배경 그대로 사용" 수준의 정확도 달성

**배경 이미지에 인물이 있는 경우**
- 프롬프트에 "IMAGE 4의 배경만 사용, 인물 무시" 명시
- AI가 배경만 추출하여 새 인물을 합성

---

## V3.1 추가 원칙 - 순간포착/카메라 스타일

### Candid vs Posed 구분 (중요!)

레퍼런스 이미지가 **순간포착(candid)** 느낌인지 **작정샷(posed)** 느낌인지 구분해서 프롬프트에 반영.

| 타입 | 특징 | 프롬프트 키워드 |
|------|------|----------------|
| Candid | 말하려다 찍힘, 바람에 머리 날림, 자연스러운 순간 | `caught mid-moment`, `spontaneous`, `natural` |
| Posed | 의도적 포즈, 카메라 응시, 정돈된 느낌 | `deliberate pose`, `looking at camera`, `composed` |

### 머리카락 움직임 보존

| 상태 | 프롬프트 예시 |
|------|--------------|
| 정적 | `hair at rest, neat` |
| 살짝 날림 | `hair gently flowing, light breeze` |
| 크게 날림 | `hair flowing dramatically, wind-blown` |
| 특정 방향 | `hair flowing to the right side` |

### 카메라 스타일

| 느낌 | 특징 | 프롬프트 |
|------|------|----------|
| 스마트폰/아이폰 | 살짝 흔들림, 캐주얼 스냅샷 | `iPhone photo`, `slight motion blur`, `casual snapshot` |
| DSLR | 샤프, 프로페셔널 | `sharp focus`, `professional quality`, `editorial` |

### VLM 분석 필수 항목

레퍼런스 이미지를 VLM으로 분석할 때 반드시 다음 항목 추출:

```python
{
  "expression": {
    "mouth": "입 상태",
    "eyes": "눈 상태",
    "overall_vibe": "candid/posed/caught-mid-moment"
  },
  "hair": {
    "movement": "정적/살짝 날림/크게 날림",
    "direction": "날리는 방향"
  },
  "camera": {
    "type": "DSLR/스마트폰/필름",
    "feel": "professional/casual-snapshot/candid-moment"
  }
}
```

---

## V4 프롬프트 템플릿

### 이미지 순서 규칙 (중요!)

```
┌─────────────────────────────────────────────────────────────┐
│  IMAGE ORDER (AI가 혼동하지 않도록 명확히 구분)              │
├─────────────────────────────────────────────────────────────┤
│  IMAGE 1: REFERENCE - 포즈/표정/머리카락/구도 복사 대상     │
│  IMAGE 2: FACE - 이 얼굴만 사용                             │
│  IMAGE 3: OUTFIT - 이 착장만 사용 (레퍼런스 착장 무시)      │
│  IMAGE 4: BACKGROUND - 이 배경만 사용 (인물 무시!) ← V4!   │
└─────────────────────────────────────────────────────────────┘
```

### 프롬프트에 레퍼런스 특징 명시 필수

레퍼런스 이미지만 전달하면 AI가 제대로 따라하지 않음.
**반드시 텍스트로도 구체적 특징 명시:**

```python
# 레퍼런스 분석 후 프롬프트에 추가할 내용
[FROM REFERENCE IMAGE - COPY EXACTLY]
- POSE: {구체적 포즈 설명}
- EXPRESSION: {구체적 표정 설명}
- HEAD ANGLE: {머리 각도}
- HAIR: {머리카락 상태 - 바람에 날림 등}
- BODY POSITION: {자세}
```

### V4 프롬프트 템플릿 (순간포착/카메라 스타일 + 배경 직접 전달)

```python
V4_PROMPT_TEMPLATE = """
[CRITICAL - IMAGE ROLE ASSIGNMENT]

You are receiving multiple images. Each has a SPECIFIC role:

IMAGE 1 (FIRST IMAGE): REFERENCE
- This is your POSE/EXPRESSION/HAIR reference
- COPY the pose EXACTLY
- COPY the expression EXACTLY - MOST IMPORTANT!
- COPY the hair movement EXACTLY (if flowing, keep flowing!)
- COPY the head angle EXACTLY
- COPY the body position EXACTLY
- Do NOT use the face identity from this image
- Do NOT use the outfit from this image

IMAGE 2: FACE REFERENCE
- Use ONLY the face identity from this image
- Apply this face to the reference pose/expression

IMAGE 3: OUTFIT REFERENCE
- Use ONLY this outfit
- IGNORE all clothing from IMAGE 1 (reference)

IMAGE 4: BACKGROUND REFERENCE ← V4 추가!
- Use this image's BACKGROUND ONLY
- IGNORE any person in this image completely
- Copy the scene, elements, signage, atmosphere
- Place our subject (from IMAGE 1-3) INTO this background

[FROM REFERENCE IMAGE 1 - COPY EXACTLY]
- POSE: {pose_description}
- EXPRESSION: {expression_description}
- EXPRESSION VIBE: {expression_vibe} (candid/posed/caught-mid-moment)
- HEAD ANGLE: {head_angle_description}
- HAIR: {hair_description} (movement direction and intensity!)
- MOUTH: {mouth_state} (if slightly open, KEEP IT slightly open!)

[EXPRESSION DETAILS - VLM ANALYSIS]
{expression_vlm_details}

[CANDID vs POSED - CRITICAL!]
{candid_section}

[CAMERA STYLE]
{camera_style_section}

[OUTFIT]
{outfit_section}

[BACKGROUND]
{background_description}

[BODY PROPORTIONS]
- Fashion model proportions (8-head ratio)
- Long legs, slim silhouette
- Height: 170-175cm

[LIGHTING]
- Match lighting feel from reference
- Cool color temperature (5500-6000K)
- No golden/warm cast

[OUTPUT]
{output_style}

CRITICAL REMINDERS:
1. Pose/expression/hair/CANDID-FEEL from IMAGE 1
2. Face identity from IMAGE 2-3
3. Preserve the EXACT vibe (candid moment vs posed photo)
4. Hair movement must match reference
"""

# ============================================================
# Candid Section Template (레퍼런스가 순간포착 느낌일 때)
# ============================================================
CANDID_SECTION_TEMPLATE = """
- The reference is a CANDID moment, caught mid-action
- Do NOT make it look like a posed, deliberate photo
- Preserve: {candid_details}
- Do NOT "fix" or "improve" the expression to look more photogenic
- Keep the spontaneous, natural feel
"""

# ============================================================
# Camera Style Template (스마트폰/아이폰 느낌일 때)
# ============================================================
SMARTPHONE_CAMERA_TEMPLATE = """
- Shot on iPhone / smartphone camera feel
- Slight motion blur is OK (adds authenticity)
- NOT a professional DSLR sharp photo
- Casual snapshot feel, not studio photoshoot
- Natural slight grain/noise is acceptable
- Less polished, more real/authentic
"""

DSLR_CAMERA_TEMPLATE = """
- Professional DSLR quality
- Sharp focus throughout
- High-end fashion editorial feel
"""

# ============================================================
# Output Style Template
# ============================================================
OUTPUT_CANDID_TEMPLATE = """
- Natural, spontaneous photo feel
- Slight softness/motion blur OK (NOT perfectly sharp)
- Cool color temperature (no golden/warm cast)
- Casual snapshot, NOT high-end editorial
"""

OUTPUT_EDITORIAL_TEMPLATE = """
- High-end fashion editorial quality
- Sharp focus, natural skin texture
- Cool color temperature (no golden/warm cast)
"""
```

### 착장 폴더 전체 로드

```python
def load_outfit_images(outfit_folder):
    """착장 폴더의 모든 이미지 자동 로드"""
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    outfit_paths = [
        os.path.join(outfit_folder, f)
        for f in os.listdir(outfit_folder)
        if os.path.splitext(f)[1].lower() in extensions
    ]
    return outfit_paths  # 전체 반환, 하드코딩 X
```

---

## V4 코드 패턴

```python
from core.config import IMAGE_MODEL, VISION_MODEL

def generate_reference_brandcut_v4(
    reference_path,
    face_paths,
    outfit_paths,
    background_path,  # V4: 배경 이미지 직접 전달
    aspect_ratio="4:5",
    resolution="2K",
):
    """
    V4: All images passed directly in single API call
    - Reference image: pose/expression/angle
    - Face image: face swap
    - Outfit image: outfit swap
    - Background image: background reference (V4!)
    """

    # Build prompt with IMAGE roles
    prompt = V4_PROMPT_TEMPLATE  # IMAGE 1~4 역할 명시

    # Build parts in ORDER (important!)
    parts = [types.Part(text=prompt)]

    # 1. Reference image FIRST (pose reference)
    reference_img = Image.open(reference_path).convert("RGB")
    parts.append(pil_to_part(reference_img))  # IMAGE 1

    # 2. Face images (for face swap)
    for face_path in face_paths:
        face_img = Image.open(face_path).convert("RGB")
        parts.append(pil_to_part(face_img))  # IMAGE 2

    # 3. Outfit images (for outfit swap)
    for outfit_path in outfit_paths:
        outfit_img = Image.open(outfit_path).convert("RGB")
        parts.append(pil_to_part(outfit_img))  # IMAGE 3

    # 4. Background image (V4 - direct pass!)
    if background_path:
        background_img = Image.open(background_path).convert("RGB")
        parts.append(pil_to_part(background_img))  # IMAGE 4

    # Generate - single API call with all 4 images
    client = genai.Client(api_key=get_next_api_key())

    response = client.models.generate_content(
        model=IMAGE_MODEL,  # gemini-3-pro-image-preview
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.25,  # Low for consistency
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution
            )
        )
    )

    return extract_image(response)
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 스타일이 다름 | 레퍼런스 분석 부족 | VLM 프롬프트 구체화 |
| 배경이 완전히 다름 | 텍스트 변환 시 정보 손실 | **V4: 배경 이미지 직접 전달** |
| 배경 합성 어색함 | 조명/원근 불일치 | 프롬프트에 조명/원근 맞춤 지시 |
| 얼굴 안 닮음 | 얼굴 이미지 품질 | 정면 고해상도 사용 |
| 포즈가 다름 | pose_detail 추출 부족 | 프롬프트에 상세 포즈 텍스트 추가 |
| 앵글/프레이밍 다름 | 레퍼런스 특징 미명시 | LOW ANGLE, 프레이밍 등 명시 |

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
