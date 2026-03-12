---
name: product-design
description: AI 제품 디자인 생성/변형 - 슬롯 기반 믹싱 시스템
user-invocable: true
trigger-keywords: ["제품디자인", "슬롯믹싱", "디자인생성", "색상변경", "디테일변경"]
---

# 제품디자인 (Product Design) - Slot-Based Design System

**핵심 기능:** 기존 제품 이미지를 14개 슬롯으로 분해하여 색상/디테일/요소 믹싱/새 디자인 생성

## 📋 개요

슬롯 기반 제품 디자인 시스템으로 AI가 제품 이미지를 14개의 디자인 슬롯으로 분석하여 다양한 변형을 생성합니다.

**4가지 작업 모드:**
1. **색상 변경** - 전체/부분 색상 수정
2. **디테일 수정** - 특정 디자인 요소 변경
3. **요소 믹싱** - 여러 제품의 요소 조합
4. **새 디자인** - 슬롯 사양으로 완전히 새로운 디자인 생성

---

## 🎯 14-Slot System Architecture

### Core Slots (필수 요소)

| Slot | 설명 | 예시 |
|------|------|------|
| `silhouette` | 전체 실루엣/형태 | Oversized boxy, Fitted cropped, A-line midi, Slim tapered |
| `main_color` | 주 색상 | Pure white, Navy blue, Forest green, Charcoal gray |
| `accent_color` | 포인트 색상 | Burgundy, Gold, Electric blue, None |
| `material_base` | 주 소재 | Cotton jersey, Wool blend, Leather, Denim |
| `material_accent` | 보조 소재 | Satin lining, Mesh panels, Suede trim, None |

### Detail Slots (세부 요소)

| Slot | 설명 | 예시 |
|------|------|------|
| `pattern` | 패턴/프린트 | Solid, Stripes, Floral print, Checkered |
| `collar_neckline` | 칼라/넥라인 | Crew neck, V-neck, Notched lapel, Hooded |
| `sleeve_arm` | 소매/팔 스타일 | Long sleeve, Short sleeve, Sleeveless, Raglan |
| `pocket` | 주머니 | Patch pockets, Welt pockets, Hidden zip, None |
| `closure` | 여밈 방식 | Buttons, Zipper, Snap buttons, Pull-on |

### Finishing Slots (마무리 요소)

| Slot | 설명 | 예시 |
|------|------|------|
| `hem_edge` | 밑단/엣지 | Raw edge, Ribbed hem, Rolled hem, Frayed |
| `logo_branding` | 로고/브랜딩 | Embroidered logo, Woven label, Printed graphic, None |
| `hardware` | 하드웨어 | Silver zippers, Gold buttons, Plastic snaps, None |
| `details` | 기타 디테일 | Contrast stitching, Drawstring, Belt loops, Pleats |

---

## 🔄 대화 플로우

### 1단계: 모드 선택

```
AskUserQuestion(
  question="어떤 작업을 하시겠습니까?",
  options=[
    "색상 변경 - 제품의 색상만 수정",
    "디테일 수정 - 특정 디자인 요소 변경",
    "요소 믹싱 - 여러 제품의 요소 조합",
    "새 디자인 - 처음부터 새로운 디자인 생성"
  ]
)
```

### 2단계: 입력 수집 (모드별 분기)

#### 모드 A: 색상 변경
```
1. 원본 이미지 업로드 요청
2. AskUserQuestion(
     question="어떤 색상을 변경하시겠습니까?",
     options=["전체 색상 변경", "메인 색상만", "포인트 색상만", "두 색상 모두"]
   )
3. 원하는 색상 입력 받기 (예: "Navy blue → Burgundy")
```

#### 모드 B: 디테일 수정
```
1. 원본 이미지 업로드 요청
2. VLM으로 현재 슬롯 추출 → 사용자에게 표시
3. AskUserQuestion(
     question="어떤 슬롯을 수정하시겠습니까?",
     options=[슬롯 14개 목록 + "직접 입력"]
   )
4. 수정할 내용 입력 받기
```

#### 모드 C: 요소 믹싱
```
1. 여러 이미지 업로드 요청 (2-4개)
2. 각 이미지별 VLM 슬롯 추출
3. "어떤 요소를 가져올까요?" 대화형 선택
   - 이미지A의 silhouette + 이미지B의 collar + 이미지C의 color
4. 최종 슬롯 조합 확인
```

#### 모드 D: 새 디자인
```
1. 기본 정보 수집:
   - AskUserQuestion("제품 카테고리?", options=["상의", "하의", "아우터", "원피스", "가방", "신발"])
   - AskUserQuestion("스타일 방향?", options=["미니멀", "스트릿", "클래식", "아방가르드"])
2. 핵심 슬롯 우선 입력:
   - silhouette, main_color, material_base
3. 나머지 슬롯 선택적 입력 (기본값 제공)
```

### 3단계: 실행

**모드별 파이프라인:**

```python
# 색상 변경 파이프라인
if mode == "색상 변경":
    slots = extract_slots_vlm(original_image)
    slots["main_color"] = new_main_color
    slots["accent_color"] = new_accent_color
    result = generate_product_design(slots, reference_image=original_image)

# 디테일 수정 파이프라인
elif mode == "디테일 수정":
    slots = extract_slots_vlm(original_image)
    slots[target_slot] = new_value
    result = generate_product_design(slots, reference_image=original_image)

# 요소 믹싱 파이프라인
elif mode == "요소 믹싱":
    slots_list = [extract_slots_vlm(img) for img in images]
    mixed_slots = merge_slots(slots_list, user_selections)
    result = generate_product_design(mixed_slots, reference_images=images)

# 새 디자인 파이프라인
elif mode == "새 디자인":
    slots = collect_slots_from_user()
    result = generate_product_design(slots, reference_image=None)
```

### 4단계: 검증 및 출력

```python
# 자동 검증
validation_result = validate_design(result_image, target_slots)

# 사용자 확인
if validation_result["score"] >= 0.85:
    show_result(result_image, validation_result)
    ask_regenerate_if_needed()
else:
    auto_regenerate_with_adjustments()
```

---

## 🛠️ 핵심 함수

### 1. VLM Slot Extraction

```python
def extract_slots_vlm(image_path: str) -> dict:
    """
    VLM을 사용하여 이미지에서 14개 슬롯 추출

    Returns:
        {
            "silhouette": "Oversized boxy",
            "main_color": "Pure white",
            "accent_color": "None",
            ...
        }
    """
    from core.config import VISION_MODEL

    prompt = """
    Analyze this product image and extract design elements into 14 slots.
    Return ONLY a JSON object with these exact keys:

    {
      "silhouette": "describe overall shape/fit",
      "main_color": "primary color",
      "accent_color": "secondary color or 'None'",
      "material_base": "main fabric/material",
      "material_accent": "secondary material or 'None'",
      "pattern": "pattern/print type",
      "collar_neckline": "collar or neckline style",
      "sleeve_arm": "sleeve style",
      "pocket": "pocket type or 'None'",
      "closure": "closure method",
      "hem_edge": "hem/edge finish",
      "logo_branding": "branding elements or 'None'",
      "hardware": "hardware details or 'None'",
      "details": "other notable details or 'None'"
    }

    Guidelines:
    - Be specific and descriptive (e.g., "Navy blue" not "blue")
    - Use "None" for absent elements, not empty string
    - Focus on visible, objective features
    - Use fashion industry standard terms
    """

    response = genai.GenerativeModel(VISION_MODEL).generate_content([
        prompt,
        PIL.Image.open(image_path)
    ])

    return json.loads(response.text)
```

### 2. Slot Merging

```python
def merge_slots(slots_list: list[dict], selections: dict) -> dict:
    """
    여러 제품의 슬롯을 사용자 선택에 따라 병합

    Args:
        slots_list: [{슬롯14개}, {슬롯14개}, ...]
        selections: {"silhouette": 0, "collar_neckline": 1, ...}  # 이미지 인덱스

    Returns:
        merged_slots: {14개 슬롯}
    """
    merged = {}
    for slot_name, image_idx in selections.items():
        merged[slot_name] = slots_list[image_idx][slot_name]

    # 선택되지 않은 슬롯은 첫 번째 이미지 기본값
    for slot in ALL_SLOTS:
        if slot not in merged:
            merged[slot] = slots_list[0][slot]

    return merged
```

### 3. Design Generation

```python
def generate_product_design(
    slots: dict,
    reference_images: list[str] = None,
    product_category: str = None
) -> str:
    """
    슬롯 사양으로 제품 디자인 생성

    Args:
        slots: 14개 슬롯 딕셔너리
        reference_images: 참조 이미지 경로 리스트 (선택)
        product_category: 제품 카테고리 (선택)

    Returns:
        output_path: 생성된 이미지 경로
    """
    from core.config import IMAGE_MODEL

    # 프롬프트 구성
    prompt = build_design_prompt(slots, product_category)

    # 이미지 생성
    if reference_images:
        # 참조 이미지 첨부
        result = generate_with_references(prompt, reference_images)
    else:
        result = genai.ImageGenerationModel(IMAGE_MODEL).generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1"
        )

    # 저장 및 반환
    output_path = save_result(result.images[0])
    return output_path

def build_design_prompt(slots: dict, category: str = None) -> str:
    """슬롯 사양을 프롬프트로 변환"""

    base = f"Professional product photography of a {category or 'fashion item'}. "

    # Core slots (필수 강조)
    core_desc = (
        f"Silhouette: {slots['silhouette']}. "
        f"Main color: {slots['main_color']}. "
        f"Material: {slots['material_base']}. "
    )

    # Detail slots (있는 것만 포함)
    details = []
    if slots.get('accent_color') and slots['accent_color'] != "None":
        details.append(f"accent color {slots['accent_color']}")
    if slots.get('pattern') and slots['pattern'] != "Solid":
        details.append(f"{slots['pattern']} pattern")
    if slots.get('collar_neckline'):
        details.append(f"{slots['collar_neckline']}")
    if slots.get('sleeve_arm'):
        details.append(f"{slots['sleeve_arm']}")
    if slots.get('pocket') and slots['pocket'] != "None":
        details.append(f"with {slots['pocket']}")
    if slots.get('closure'):
        details.append(f"{slots['closure']} closure")

    detail_desc = ", ".join(details) + ". " if details else ""

    # Finishing slots
    finishing = []
    if slots.get('hem_edge'):
        finishing.append(f"{slots['hem_edge']} hem")
    if slots.get('hardware') and slots['hardware'] != "None":
        finishing.append(slots['hardware'])
    if slots.get('details') and slots['details'] != "None":
        finishing.append(slots['details'])

    finishing_desc = ", ".join(finishing) + ". " if finishing else ""

    # Style directives
    style = (
        "Clean white background. Front view. Studio lighting. "
        "High resolution. Product catalog style. No model. "
        "Focus on garment details and texture."
    )

    return base + core_desc + detail_desc + finishing_desc + style
```

### 4. Validation

```python
def validate_design(image_path: str, target_slots: dict) -> dict:
    """
    생성된 디자인이 슬롯 사양과 일치하는지 검증

    Returns:
        {
            "score": 0.92,  # 0-1 scale
            "matches": {
                "silhouette": True,
                "main_color": True,
                "collar_neckline": False,
                ...
            },
            "feedback": "Collar style doesn't match specification"
        }
    """
    from core.config import VISION_MODEL

    # VLM으로 생성 이미지 분석
    generated_slots = extract_slots_vlm(image_path)

    # 슬롯별 가중치
    weights = {
        "silhouette": 0.15,
        "main_color": 0.15,
        "material_base": 0.10,
        "accent_color": 0.10,
        "pattern": 0.08,
        "collar_neckline": 0.08,
        "sleeve_arm": 0.08,
        "pocket": 0.06,
        "closure": 0.06,
        "hem_edge": 0.05,
        "material_accent": 0.04,
        "logo_branding": 0.02,
        "hardware": 0.02,
        "details": 0.01
    }

    matches = {}
    weighted_score = 0.0

    for slot, weight in weights.items():
        expected = target_slots.get(slot, "None")
        actual = generated_slots.get(slot, "None")

        # 의미적 유사도 검사
        is_match = semantic_match(expected, actual)
        matches[slot] = is_match

        if is_match:
            weighted_score += weight

    # 피드백 생성
    failed_slots = [k for k, v in matches.items() if not v and target_slots.get(k) != "None"]
    feedback = f"Mismatches in: {', '.join(failed_slots)}" if failed_slots else "All slots match"

    return {
        "score": weighted_score,
        "matches": matches,
        "feedback": feedback
    }

def semantic_match(expected: str, actual: str, threshold: float = 0.7) -> bool:
    """의미적 유사도 검사 (간단한 키워드 매칭)"""
    if expected == "None" and actual == "None":
        return True

    # 정규화
    exp_lower = expected.lower()
    act_lower = actual.lower()

    # 정확 일치
    if exp_lower == act_lower:
        return True

    # 키워드 포함 검사
    exp_keywords = set(exp_lower.split())
    act_keywords = set(act_lower.split())

    overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
    return overlap >= threshold
```

---

## 📁 파일 구조

```
.claude/skills/제품디자인_product-design/
├── SKILL.md                    # 이 문서
├── generate.py                 # 메인 생성 스크립트
├── schemas/
│   ├── slots.json              # 14-slot 스키마 정의
│   └── categories.json         # 제품 카테고리별 기본값
├── examples/
│   ├── color_change.json       # 색상 변경 예시
│   ├── detail_modify.json      # 디테일 수정 예시
│   ├── element_mixing.json     # 요소 믹싱 예시
│   └── new_design.json         # 새 디자인 예시
└── prompts/
    ├── extraction_template.txt # VLM 슬롯 추출 프롬프트
    └── generation_template.txt # 이미지 생성 프롬프트
```

---

## 🎨 사용 예시

### 예시 1: 색상 변경

**입력:**
- 원본 이미지: white_tshirt.jpg
- 변경: Main color → Navy blue

**처리:**
```python
slots = extract_slots_vlm("white_tshirt.jpg")
# {"silhouette": "Relaxed fit", "main_color": "Pure white", ...}

slots["main_color"] = "Navy blue"
result = generate_product_design(slots, reference_images=["white_tshirt.jpg"])
```

**출력:** Navy blue 티셔츠 (다른 요소는 동일)

---

### 예시 2: 디테일 수정

**입력:**
- 원본 이미지: basic_hoodie.jpg
- 변경: Pocket → Kangaroo pocket

**처리:**
```python
slots = extract_slots_vlm("basic_hoodie.jpg")
slots["pocket"] = "Kangaroo pocket"
result = generate_product_design(slots, reference_images=["basic_hoodie.jpg"])
```

---

### 예시 3: 요소 믹싱

**입력:**
- 이미지 A: vintage_jacket.jpg (실루엣 좋음)
- 이미지 B: modern_coat.jpg (칼라 좋음)
- 이미지 C: classic_blazer.jpg (색상 좋음)

**처리:**
```python
slots_a = extract_slots_vlm("vintage_jacket.jpg")
slots_b = extract_slots_vlm("modern_coat.jpg")
slots_c = extract_slots_vlm("classic_blazer.jpg")

mixed_slots = {
    "silhouette": slots_a["silhouette"],
    "collar_neckline": slots_b["collar_neckline"],
    "main_color": slots_c["main_color"],
    # ... 나머지 슬롯
}

result = generate_product_design(
    mixed_slots,
    reference_images=["vintage_jacket.jpg", "modern_coat.jpg", "classic_blazer.jpg"]
)
```

---

### 예시 4: 새 디자인

**입력:**
- 카테고리: 아우터
- 스타일: 미니멀
- 핵심 사양:
  - Silhouette: Oversized boxy
  - Main color: Camel
  - Material: Wool blend

**처리:**
```python
slots = {
    "silhouette": "Oversized boxy",
    "main_color": "Camel",
    "accent_color": "None",
    "material_base": "Wool blend",
    "material_accent": "Satin lining",
    "pattern": "Solid",
    "collar_neckline": "Notched lapel",
    "sleeve_arm": "Long sleeve",
    "pocket": "Welt pockets",
    "closure": "Buttons",
    "hem_edge": "Straight hem",
    "logo_branding": "None",
    "hardware": "Gold buttons",
    "details": "None"
}

result = generate_product_design(slots, product_category="아우터")
```

---

## ⚙️ 설정 참조

**모델 설정은 반드시 `core/config.py`에서 가져오기:**

```python
from core.config import IMAGE_MODEL, VISION_MODEL, PipelineConfig

# Good
model = IMAGE_MODEL  # "gemini-3-pro-image-preview"
vision = VISION_MODEL  # "gemini-3-flash-preview"

# Bad (절대 금지!)
model = "gemini-pro"  # WRONG!
```

---

## 🔍 검증 기준

**자동 검증 가중치:**

| 슬롯 | 가중치 | 중요도 |
|------|--------|--------|
| silhouette | 15% | 매우 높음 |
| main_color | 15% | 매우 높음 |
| material_base | 10% | 높음 |
| accent_color | 10% | 높음 |
| pattern | 8% | 중간 |
| collar_neckline | 8% | 중간 |
| sleeve_arm | 8% | 중간 |
| pocket | 6% | 보통 |
| closure | 6% | 보통 |
| hem_edge | 5% | 낮음 |
| material_accent | 4% | 낮음 |
| logo_branding | 2% | 매우 낮음 |
| hardware | 2% | 매우 낮음 |
| details | 1% | 매우 낮음 |

**합격 기준:**
- Score ≥ 0.85: 자동 승인
- 0.70 ≤ Score < 0.85: 사용자 확인 요청
- Score < 0.70: 자동 재생성

---

## 🚀 실행 방법

### Claude Code에서 호출

```
사용자: "제품디자인 스킬 실행"
또는
사용자: "이 티셔츠 색상을 바꿔줘"
```

### 직접 Python 실행

```bash
cd .claude/skills/제품디자인_product-design
python generate.py
```

---

## 📚 추가 리소스

- **슬롯 스키마 상세:** `schemas/slots.json`
- **카테고리별 기본값:** `schemas/categories.json`
- **프롬프트 템플릿:** `prompts/` 디렉토리
- **설정 파일:** `core/config.py`

---

## 🐛 트러블슈팅

### 문제: VLM이 슬롯을 잘못 추출
**해결:** `prompts/extraction_template.txt`에서 예시 추가

### 문제: 생성 이미지가 사양과 다름
**해결:**
1. `build_design_prompt()` 프롬프트 가중치 조정
2. Reference image 품질 확인
3. Validation threshold 조정

### 문제: 색상이 정확하지 않음
**해결:**
1. 색상명을 더 구체적으로 (예: "Blue" → "Navy blue #1A2B3C")
2. Reference image에서 색상 영역 강조

---

## 📝 개발 노트

**버전:** 1.0.0
**최종 업데이트:** 2026-02-11
**개발자:** FNF Studio Team

**향후 개선 사항:**
- [ ] 슬롯별 신뢰도 점수 추가
- [ ] 다중 뷰 생성 (앞/뒤/옆)
- [ ] 실시간 프리뷰 기능
- [ ] 사용자 커스텀 슬롯 추가 지원
