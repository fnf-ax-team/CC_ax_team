---
name: fabric-generation
description: 원단/소재 텍스처 생성 - 10단계 속성 DB 기반 매칭
user-invocable: true
trigger-keywords: ["소재생성", "원단생성", "텍스처", "패브릭", "소재이미지"]
---

# 소재/원단 텍스처 생성 가이드

> 10단계 속성 DB 기반 원단 텍스처 이미지 생성 및 타일링 검증

---

## ⛔ 모델 필수 확인 (코드 작성 전 반드시 읽기!)

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ 사용 모델:                                               │
│     - 이미지 생성: gemini-3-pro-image-preview               │
│     - VLM 분석: gemini-3-flash-preview                      │
│                                                             │
│  ❌ 절대 금지:                                               │
│     - gemini-2.0-flash-exp-image-generation (품질 낮음)     │
│     - gemini-2.0-flash (이미지 생성 미지원)                  │
│     - gemini-2.5-flash (텍스트 전용)                        │
└─────────────────────────────────────────────────────────────┘
```

**이 규칙 위반 시 결과물 전체 삭제 후 재생성 필요.**

### core/config.py 의존성

```python
from core.config import IMAGE_MODEL, VISION_MODEL

# 절대 금지: 하드코딩된 모델명
# model = "gemini-pro"  # WRONG!
# model = IMAGE_MODEL   # CORRECT!
```

---

## Claude 행동 지침

### 필수 규칙

1. **모델 확인**: 코드 작성 전 반드시 `core/config.py`에서 모델 상수 임포트
2. **워크플로 확인**: 사용자가 원하는 방식 (1) 레퍼런스 이미지 기반 or (2) 속성 선택 기반
3. **타일링 필수**: 모든 원단 텍스처는 seamless tile 가능해야 함 (tileability >= 90 필수)
4. **DB 업데이트**: 생성 성공 시 fabric_library.json에 자동 등록

### 금지 사항

- ❌ 잘못된 모델 사용 (gemini-2.x 계열 절대 금지)
- ❌ 타일링 검증 없이 출력
- ❌ 임의의 속성값 가정 (반드시 VLM 분석 or 사용자 선택)

---

## 10단계 속성 분류 시스템

모든 원단은 10개의 1-10 스케일 속성으로 정의됨.

| 속성 | 영문 | 설명 | 예시 |
|------|------|------|------|
| 두께 | thickness | 원단 두께 (1=얇음, 10=두꺼움) | 시폰=2, 데님=7, 패딩=10 |
| 광택 | glossiness | 표면 광택도 (1=무광, 10=고광택) | 면=1, 새틴=8, 가죽=9 |
| 부드러움 | softness | 촉감 부드러움 (1=딱딱함, 10=부드러움) | 캔버스=2, 벨벳=9, 니트=8 |
| 질감 | texture | 표면 질감 복잡도 (1=매끄러움, 10=거침) | 실크=1, 트위드=9, 린넨=6 |
| 신축성 | stretch | 늘어나는 정도 (1=없음, 10=최대) | 데님=1, 스판덱스=10, 니트=7 |
| 투명도 | transparency | 비침 정도 (1=불투명, 10=투명) | 가죽=1, 쉬폰=8, 레이스=7 |
| 무게 | weight | 단위면적당 무게감 (1=가벼움, 10=무거움) | 쉬폰=1, 울=7, 가죽=9 |
| 통기성 | breathability | 공기 통과 정도 (1=낮음, 10=높음) | 가죽=1, 린넨=9, 면=7 |
| 드레이프 | drape | 낙하감/흘러내림 (1=뻣뻣함, 10=흐름성) | 캔버스=2, 실크=9, 새틴=8 |
| 내구성 | durability | 마모 저항성 (1=약함, 10=강함) | 레이스=2, 데님=9, 가죽=10 |

---

## 대화 플로우

### 플로우 A: 레퍼런스 이미지 기반

```
1. 사용자: "소재 이미지 만들어줘"

2. Claude: "어떤 방식으로 생성할까요?"
   [AskUserQuestion]
   - 레퍼런스 이미지 있음 (비슷한 텍스처 생성)
   - 속성으로 직접 선택 (10단계 슬라이더)

3. 사용자: "레퍼런스 이미지 있음"

4. Claude: "원단 레퍼런스 이미지 경로 알려주세요!"

5. 사용자: "D:\fabrics\denim.jpg"

6. Claude:
   - VLM 분석 (gemini-3-flash-preview)
     → 10단계 속성 추출
     → DB 유사도 매칭 (find_similar_texture)
   - 분석 결과 사용자에게 확인
   "이 소재는 다음과 같이 분석됐어요:
    - 두께: 7/10 (두꺼움)
    - 광택: 2/10 (무광)
    - 질감: 6/10 (약간 거침)
    ...
    이대로 생성할까요? (수정 가능)"

7. Claude:
   - 프롬프트 빌드 (build_fabric_prompt)
   - 이미지 생성 (IMAGE_MODEL)
   - 타일링 검증 (VLM)
     → tileability < 90 시 재생성 (최대 2회)

8. Claude:
   - 생성 완료 결과 보고
   - DB 등록 (fabric_library.json)
```

### 플로우 B: 속성 직접 선택

```
1~3. (플로우 A와 동일)

4. Claude: "10단계 속성을 선택해주세요"
   [AskUserQuestion - 각 속성별 1~10 슬라이더]

5. 사용자: [두께: 7, 광택: 2, ...]

6. Claude:
   - DB 유사도 매칭
   - "DB에서 가장 유사한 소재: 데님 (유사도 95%)
      이 프롬프트를 기반으로 생성합니다"

7~8. (플로우 A와 동일)
```

---

## 기술 스펙 (API 연결)

### 패키지 설치

```bash
pip install google-genai pillow numpy
```

### API 키 설정

```bash
# .env 파일 (프로젝트 루트)
GEMINI_API_KEY=your_api_key_here

# 여러 키 로테이션 (rate limit 대응)
GEMINI_API_KEY=key1,key2,key3
```

### 모델 & 파라미터

| 항목 | 값 | 설명 |
|------|-----|------|
| **이미지 생성 모델** | `gemini-3-pro-image-preview` | IMAGE_MODEL 상수 사용 필수 |
| **VLM 모델** | `gemini-3-flash-preview` | VISION_MODEL 상수 사용 필수 |
| **Temperature** | `0.15` | 일관성 중시 (원단은 재현성 중요) |
| **Aspect Ratio** | `1:1` | 타일링 적합 정사각형 |
| **해상도** | `2K` (2048px) | 고품질 텍스처 디테일 |

### API 호출 코드 패턴

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import json

# ============ 1. Config Import (필수!) ============
from core.config import IMAGE_MODEL, VISION_MODEL

# ============ 2. API 키 로드 ============
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
    """API 키 로테이션 (rate limit 대응)"""
    global key_index
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ============ 3. VLM 분석 ============
def analyze_fabric_attributes(image_path: str) -> dict:
    """
    원단 이미지 → 10단계 속성 추출

    Returns:
        {
            "thickness": 7,
            "glossiness": 2,
            "softness": 5,
            "texture": 6,
            "stretch": 1,
            "transparency": 1,
            "weight": 7,
            "breathability": 5,
            "drape": 3,
            "durability": 9,
            "material_type": "denim",
            "color": "dark indigo blue",
            "pattern": "plain twill weave"
        }
    """
    prompt = """Analyze this fabric/material texture in detail.

Rate each property on a 1-10 scale:
- thickness: 1=sheer/thin, 10=very thick/padded
- glossiness: 1=matte, 10=high gloss/shiny
- softness: 1=stiff/hard, 10=very soft
- texture: 1=smooth, 10=very rough/coarse
- stretch: 1=no stretch, 10=maximum stretch
- transparency: 1=opaque, 10=transparent
- weight: 1=lightweight, 10=heavyweight
- breathability: 1=low, 10=high
- drape: 1=stiff, 10=fluid/flowing
- durability: 1=delicate, 10=very durable

Also identify:
- material_type: e.g. denim, silk, cotton, leather, knit
- color: exact color description
- pattern: plain, twill, jacquard, printed, etc.

Return JSON only:
{
  "thickness": 7,
  "glossiness": 2,
  ...
}"""

    img = Image.open(image_path).convert("RGB")

    # PIL → API Part 변환
    buf = BytesIO()
    if max(img.size) > 1024:
        img.thumbnail((1024, 1024), Image.LANCZOS)
    img.save(buf, format="PNG")

    client = genai.Client(api_key=get_next_api_key())
    response = client.models.generate_content(
        model=VISION_MODEL,  # core/config.py에서 가져온 상수!
        contents=[types.Content(role="user", parts=[
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))
        ])]
    )

    text = response.candidates[0].content.parts[0].text
    # JSON 추출 (```json ... ``` 제거)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]

    return json.loads(text.strip())

# ============ 4. DB 유사도 매칭 ============
def find_similar_texture(attributes: dict, db_path: str = "fabric_library.json", top_k: int = 3) -> list:
    """
    10단계 속성 → DB에서 유사한 원단 찾기

    Returns:
        [
            {"name": "denim", "similarity": 95, "entry": {...}},
            ...
        ]
    """
    if not os.path.exists(db_path):
        return []

    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    attr_keys = ["thickness", "glossiness", "softness", "texture", "stretch",
                 "transparency", "weight", "breathability", "drape", "durability"]

    results = []
    for name, entry in db.items():
        # 유클리드 거리 계산
        dist = sum((attributes.get(k, 5) - entry.get(k, 5)) ** 2 for k in attr_keys)
        similarity = max(0, 100 - (dist ** 0.5) * 3)  # 0-100 스케일
        results.append({
            "name": name,
            "similarity": round(similarity, 1),
            "entry": entry
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]

# ============ 5. 프롬프트 빌드 ============
def build_fabric_prompt(attributes: dict) -> str:
    """
    10단계 속성 → 영문 생성 프롬프트

    Returns:
        "High-quality fabric texture: thick heavyweight denim, ..."
    """
    # 속성 → 영문 표현 매핑
    thickness_desc = ["ultra-thin", "very thin", "thin", "light", "medium-light",
                      "medium", "medium-thick", "thick", "very thick", "ultra-thick"]
    glossiness_desc = ["matte", "nearly matte", "low sheen", "subtle sheen", "slight gloss",
                       "semi-gloss", "glossy", "very glossy", "high gloss", "mirror-like"]
    texture_desc = ["ultra-smooth", "very smooth", "smooth", "fine", "medium-fine",
                    "medium", "medium-coarse", "coarse", "very coarse", "ultra-rough"]
    drape_desc = ["very stiff", "stiff", "structured", "semi-structured", "medium",
                  "soft drape", "flowing", "very fluid", "extremely fluid", "liquid-like"]

    t = attributes.get("thickness", 5)
    g = attributes.get("glossiness", 5)
    tx = attributes.get("texture", 5)
    d = attributes.get("drape", 5)

    material = attributes.get("material_type", "fabric")
    color = attributes.get("color", "neutral")
    pattern = attributes.get("pattern", "plain weave")

    prompt = f"""High-quality seamless fabric texture photograph.
Material: {material}, {color} color
Surface: {thickness_desc[t-1]}, {glossiness_desc[g-1]}, {texture_desc[tx-1]}
Drape: {drape_desc[d-1]}
Weave pattern: {pattern}

Technical requirements:
- Macro photography, even lighting
- Seamless tileable edges (pattern continues at borders)
- No shadows, no wrinkles, flat surface
- Focus on material weave and fiber texture detail
- Clean, professional product photography style
- Resolution: 2K, square format"""

    return prompt

# ============ 6. 타일링 검증 ============
def validate_tileability(image: Image.Image) -> dict:
    """
    생성된 텍스처의 타일링 가능성 검증 (VLM 판단)

    Returns:
        {
            "tileability": 85,  # 0-100
            "edge_match": "좌우 엣지 색상 약간 불일치",
            "pattern_continuity": "패턴 반복 자연스러움",
            "pass": False  # tileability >= 90 필요
        }
    """
    prompt = """Evaluate this texture image for seamless tiling capability.

Check:
1. Edge matching: Do left/right and top/bottom edges match perfectly?
2. Pattern continuity: Does the pattern repeat naturally?
3. Color consistency: Are edges the same brightness/color as center?

Rate tileability on 0-100 scale:
- 90-100: Perfect seamless tile
- 70-89: Minor edge mismatch, fixable
- 50-69: Noticeable seams
- 0-49: Cannot tile

Return JSON:
{
  "tileability": 85,
  "edge_match": "description",
  "pattern_continuity": "description",
  "color_consistency": "description"
}"""

    buf = BytesIO()
    image.save(buf, format="PNG")

    client = genai.Client(api_key=get_next_api_key())
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))
        ])]
    )

    text = response.candidates[0].content.parts[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]

    result = json.loads(text.strip())
    result["pass"] = result.get("tileability", 0) >= 90
    return result

# ============ 7. 원단 생성 (재시도 포함) ============
def generate_fabric_texture(attributes: dict, max_retries: int = 2) -> Image.Image:
    """
    10단계 속성 → 타일 가능한 원단 텍스처 생성

    Returns:
        PIL Image or None
    """
    prompt = build_fabric_prompt(attributes)

    for attempt in range(max_retries + 1):
        print(f"[Attempt {attempt+1}/{max_retries+1}] Generating fabric texture...")

        # 이미지 생성
        client = genai.Client(api_key=get_next_api_key())
        response = client.models.generate_content(
            model=IMAGE_MODEL,  # core/config.py 상수!
            contents=[types.Content(role="user", parts=[
                types.Part(text=prompt)
            ])],
            config=types.GenerateContentConfig(
                temperature=0.15,  # 일관성 중시
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                    image_size="2K"
                )
            )
        )

        # 결과 추출
        image = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image = Image.open(BytesIO(part.inline_data.data))
                break

        if not image:
            print(f"  -> No image in response, retrying...")
            continue

        # 타일링 검증
        validation = validate_tileability(image)
        print(f"  -> Tileability: {validation['tileability']}/100")

        if validation["pass"]:
            print(f"  -> Success! Tileability >= 90")
            return image
        else:
            print(f"  -> Failed: {validation['edge_match']}")
            if attempt < max_retries:
                # 프롬프트 강화
                prompt += "\n\nIMPORTANT: Edges must match PERFECTLY for seamless tiling. Ensure pattern continues at borders."

    print(f"  -> Max retries reached, returning best attempt")
    return image

# ============ 8. DB 등록 ============
def register_to_db(name: str, attributes: dict, image_path: str, db_path: str = "fabric_library.json"):
    """생성된 원단을 DB에 등록"""
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        db = {}

    db[name] = {
        **attributes,
        "image_path": image_path,
        "created_at": __import__('datetime').datetime.now().isoformat()
    }

    with open(db_path, 'w', encoding='utf-8') as f:
        json.dumps(db, f, ensure_ascii=False, indent=2)

    print(f"✅ Registered '{name}' to DB ({len(db)} total entries)")
```

---

## DB 구조 (fabric_library.json)

```json
{
  "denim_dark_indigo": {
    "thickness": 7,
    "glossiness": 2,
    "softness": 5,
    "texture": 6,
    "stretch": 1,
    "transparency": 1,
    "weight": 7,
    "breathability": 5,
    "drape": 3,
    "durability": 9,
    "material_type": "denim",
    "color": "dark indigo blue",
    "pattern": "twill weave",
    "image_path": "Fnf_studio_outputs/fabric_generation/denim_dark_indigo_20260211_143022.png",
    "created_at": "2026-02-11T14:30:22"
  },
  "silk_charmeuse_ivory": {
    "thickness": 2,
    "glossiness": 9,
    "softness": 9,
    "texture": 1,
    "stretch": 2,
    "transparency": 6,
    "weight": 2,
    "breathability": 7,
    "drape": 9,
    "durability": 3,
    "material_type": "silk",
    "color": "ivory white",
    "pattern": "satin weave",
    "image_path": "Fnf_studio_outputs/fabric_generation/silk_charmeuse_ivory_20260211_145512.png",
    "created_at": "2026-02-11T14:55:12"
  }
}
```

### DB 파일 위치

```
D:\FNF_Studio_TEST\New-fnf-studio\fabric_library.json
```

---

## VLM 프롬프트 (영문 전용)

### 속성 분석 프롬프트

```
Analyze this fabric/material texture in detail.

Rate each property on a 1-10 scale:
- thickness: 1=sheer/thin, 10=very thick/padded
- glossiness: 1=matte, 10=high gloss/shiny
- softness: 1=stiff/hard, 10=very soft
- texture: 1=smooth, 10=very rough/coarse
- stretch: 1=no stretch, 10=maximum stretch
- transparency: 1=opaque, 10=transparent
- weight: 1=lightweight, 10=heavyweight
- breathability: 1=low, 10=high
- drape: 1=stiff, 10=fluid/flowing
- durability: 1=delicate, 10=very durable

Also identify:
- material_type: e.g. denim, silk, cotton, leather, knit
- color: exact color description
- pattern: plain, twill, jacquard, printed, etc.

Return JSON only.
```

### 타일링 검증 프롬프트

```
Evaluate this texture image for seamless tiling capability.

Check:
1. Edge matching: Do left/right and top/bottom edges match perfectly?
2. Pattern continuity: Does the pattern repeat naturally?
3. Color consistency: Are edges the same brightness/color as center?

Rate tileability on 0-100 scale:
- 90-100: Perfect seamless tile
- 70-89: Minor edge mismatch, fixable
- 50-69: Noticeable seams
- 0-49: Cannot tile

Return JSON with tileability score and descriptions.
```

---

## 품질 검증 기준

### 필수 통과 조건

| 항목 | 기준 | 비고 |
|------|------|------|
| **Tileability** | >= 90 | VLM 판단, 필수 |
| **해상도** | 2K (2048px) | 고품질 텍스처 |
| **Aspect Ratio** | 1:1 | 타일링 최적 |
| **엣지 매칭** | Perfect | 좌우/상하 경계 완벽 일치 |
| **패턴 연속성** | Natural | 반복 시 인위적이지 않음 |

### 재생성 조건

- Tileability < 90
- 엣지 색상/밝기 불일치
- 패턴 불연속
- 그림자/주름 존재

최대 재시도 2회. 실패 시 속성 조정 권장.

---

## 사용 예시

### 1. 레퍼런스 이미지 기반 생성

```python
# 1. 레퍼런스 분석
attributes = analyze_fabric_attributes("reference_denim.jpg")
print(attributes)
# {
#   "thickness": 7,
#   "glossiness": 2,
#   ...
# }

# 2. DB 유사도 매칭
similar = find_similar_texture(attributes)
print(f"가장 유사한 DB 엔트리: {similar[0]['name']} (유사도 {similar[0]['similarity']}%)")

# 3. 생성
result = generate_fabric_texture(attributes)

# 4. 저장 및 DB 등록
if result:
    output_path = "Fnf_studio_outputs/fabric_generation/custom_denim_20260211_143022.png"
    result.save(output_path)
    register_to_db("custom_denim", attributes, output_path)
```

### 2. 속성 직접 선택 생성

```python
# 사용자가 선택한 속성
attributes = {
    "thickness": 8,
    "glossiness": 1,
    "softness": 7,
    "texture": 8,
    "stretch": 6,
    "transparency": 1,
    "weight": 6,
    "breathability": 8,
    "drape": 6,
    "durability": 7,
    "material_type": "cotton knit",
    "color": "grey heather",
    "pattern": "jersey knit"
}

# DB 매칭 (참고용)
similar = find_similar_texture(attributes)

# 생성
result = generate_fabric_texture(attributes)
```

### 3. 배치 생성 (여러 색상 변형)

```python
base_attributes = analyze_fabric_attributes("base_fabric.jpg")

colors = ["black", "navy blue", "grey", "beige", "white"]

for color in colors:
    attributes = {**base_attributes, "color": color}
    result = generate_fabric_texture(attributes)

    if result:
        name = f"{base_attributes['material_type']}_{color.replace(' ', '_')}"
        path = f"Fnf_studio_outputs/fabric_generation/{name}.png"
        result.save(path)
        register_to_db(name, attributes, path)
```

---

## 출력 폴더 구조

```
Fnf_studio_outputs/
└── fabric_generation/
    ├── denim_dark_indigo_20260211_143022.png
    ├── silk_charmeuse_ivory_20260211_145512.png
    └── cotton_knit_grey_20260211_150033.png

fabric_library.json (프로젝트 루트)
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| Tileability < 90 | 엣지 패턴 불일치 | 프롬프트에 "seamless" 강조, 재시도 |
| 그림자 존재 | 조명 불균일 | 프롬프트에 "flat lighting, no shadows" 추가 |
| 색상 불균일 | 텍스처 노이즈 과다 | Texture 속성 낮추기 (8 → 5) |
| 패턴 너무 복잡 | Pattern 설명 과도 | 심플한 weave pattern으로 변경 |
| DB 매칭 실패 | DB 비어있음 | 초기 엔트리 수동 생성 |

---

## Linn_node 패턴 참조 (코드베이스 존재 시)

> 참고: 현재 코드베이스에 Linn_node_Fabric.py, sort_fabrics.py가 없으므로 위 구현이 기준이 됨.

만약 해당 파일들이 추가되면:

```python
# sort_fabrics.py 참조 패턴
ITEM_FULL_MAP = {
    "denim": {
        "thickness": 7,
        "glossiness": 2,
        ...
    }
}

# Linn_node_Fabric.py 참조 패턴
def detect_material_from_image(image_path: str) -> dict:
    """VLM으로 소재 자동 분석"""
    ...

def find_similar_texture(attributes: dict, top_k: int = 3) -> list:
    """DB 유사도 매칭"""
    ...

def build_fabric_prompt(attributes: dict) -> str:
    """속성 → 프롬프트 변환"""
    ...
```

---

## 핵심 요약

| 항목 | 내용 |
|------|------|
| **패키지** | `pip install google-genai pillow numpy` |
| **생성 모델** | `gemini-3-pro-image-preview` (IMAGE_MODEL) |
| **분석 모델** | `gemini-3-flash-preview` (VISION_MODEL) |
| **Temperature** | `0.15` (일관성 중시) |
| **해상도** | `2K` (2048px) |
| **비율** | `1:1` (정사각형) |
| **필수 검증** | Tileability >= 90 |
| **DB 파일** | `fabric_library.json` |
| **10단계 속성** | thickness, glossiness, softness, texture, stretch, transparency, weight, breathability, drape, durability |

---

## 체크리스트

생성 전:
- [ ] `core/config.py`에서 IMAGE_MODEL, VISION_MODEL 임포트 확인
- [ ] 레퍼런스 이미지 or 속성 선택 확인
- [ ] DB 파일 위치 확인 (fabric_library.json)

생성 중:
- [ ] VLM 분석 결과 사용자 확인
- [ ] DB 유사도 매칭 결과 표시
- [ ] Tileability 검증 (>= 90 필수)

생성 후:
- [ ] 타일링 테스트 (좌우/상하 반복 확인)
- [ ] DB 등록 완료
- [ ] 출력 파일 저장 확인
