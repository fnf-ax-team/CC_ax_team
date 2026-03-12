---
name: product-styled
description: 제품 연출컷 생성 - 상세페이지/라이프스타일/디테일샷
user-invocable: true
trigger-keywords: ["제품연출", "상세페이지", "제품촬영", "연출샷", "라이프스타일"]
---

# 제품 연출 스킬 (Product Styled)

## 개요
제품 연출샷 전문 생성 스킬. 상세페이지, 라이프스타일, 디테일샷 등 다양한 제품 촬영 스타일 지원.

**핵심 차별점:**
- 6가지 스튜디오급 조명/배경 프리셋
- 4가지 샷 타입 (단독/라이프스타일/디테일/그룹)
- VLM 기반 제품 색상 정확도 검증 (90% 이상 필수)
- 다단계 향상 파이프라인 (조명 → 텍스처 → 컬러매칭)

## 대화 플로우

### 1단계: 웰컴 + 제품 이미지 요청
```python
AskUserQuestion({
  "type": "requirement",
  "question": "📸 **제품 연출 스킬**에 오신 걸 환영합니다!\n\n촬영할 제품 이미지를 업로드해주세요.",
  "options": [
    "✅ 이미지 업로드 완료",
    "❓ 어떤 이미지를 업로드해야 하나요?"
  ]
})
```

**도움말 선택 시:**
```
권장 이미지:
- 투명 배경 PNG (또는 단색 배경)
- 정면/측면/디테일 각도
- 최소 1024x1024 해상도
- 제품 색상이 명확히 보이는 사진
```

### 2단계: 스타일 프리셋 선택
```python
AskUserQuestion({
  "type": "preference",
  "question": "🎨 **촬영 스타일**을 선택하세요:",
  "options": [
    "⚪ white_clean - 순백 배경, 소프트박스 (상세페이지용)",
    "⬜ gray_studio - 그레이 배경, 스튜디오 조명 (룩북용)",
    "🏠 lifestyle_indoor - 실내, 자연광, 라이프스타일",
    "🌳 lifestyle_outdoor - 야외, 자연광, 스트릿",
    "🔍 detail_macro - 디테일 클로즈업",
    "📐 flatlay - 탑다운 코디 (여러 제품 조합)"
  ]
})
```

### 3단계: 샷 타입 선택
```python
AskUserQuestion({
  "type": "preference",
  "question": "📷 **샷 타입**을 선택하세요:",
  "options": [
    "🎯 product_shot - 제품 단독샷 (hero 이미지)",
    "🌿 lifestyle - 라이프스타일 연출샷 (소품/배경 포함)",
    "🔬 detail - 디테일 클로즈업 (로고/소재 강조)",
    "🎁 group - 그룹샷/코디 (여러 제품 조합)"
  ]
})
```

### 4단계: 추가 옵션
```python
AskUserQuestion({
  "type": "preference",
  "question": "⚙️ **추가 옵션** (선택사항):",
  "options": [
    "✅ 기본 설정으로 진행",
    "🌈 색상 강조 (vivid color boost)",
    "✨ 프리미엄 텍스처 (고급 질감)",
    "📏 특정 비율 지정 (1:1, 3:4, 16:9 등)"
  ]
})
```

### 5단계: 생성 시작
```
🎬 생성을 시작합니다...

[1/4] 제품 분석 중 (VLM)...
[2/4] 기본 연출샷 생성...
[3/4] 조명/텍스처 향상...
[4/4] 색상 정확도 검증...

✅ 완료! 결과 이미지: output/product_styled_YYYYMMDD_HHMMSS.png
```

## 스타일 프리셋 정의

### 1. white_clean (순백 상세페이지)
```python
PRESETS["white_clean"] = {
    "background": "pure white seamless background, professional product photography backdrop",
    "lighting": "softbox lighting, even illumination, no harsh shadows, commercial studio lighting",
    "camera": "frontal angle, centered composition, high resolution product shot",
    "mood": "clean, minimal, professional, e-commerce ready",
    "post_processing": "color correction, shadow removal, perfect white balance",
    "use_case": "상세페이지 메인 이미지, 썸네일"
}
```

### 2. gray_studio (그레이 스튜디오)
```python
PRESETS["gray_studio"] = {
    "background": "neutral gray gradient backdrop, studio background paper",
    "lighting": "three-point studio lighting, rim light for depth, soft key light",
    "camera": "slight angle, dynamic composition, editorial product photography",
    "mood": "sophisticated, editorial, lookbook quality",
    "post_processing": "subtle vignette, professional color grading",
    "use_case": "룩북, 브랜드 카탈로그"
}
```

### 3. lifestyle_indoor (실내 라이프스타일)
```python
PRESETS["lifestyle_indoor"] = {
    "background": "modern interior setting, natural home environment, minimalist decor",
    "lighting": "soft window light, natural indoor lighting, warm ambient glow",
    "camera": "lifestyle composition, product in context, relatable scene",
    "mood": "cozy, authentic, relatable, everyday life",
    "props": "complementary home objects, books, plants, natural textures",
    "use_case": "SNS 콘텐츠, 라이프스타일 매거진"
}
```

### 4. lifestyle_outdoor (야외 스트릿)
```python
PRESETS["lifestyle_outdoor"] = {
    "background": "urban outdoor setting, street photography backdrop, natural environment",
    "lighting": "natural daylight, golden hour lighting, outdoor ambient light",
    "camera": "environmental portrait style, product in lifestyle context",
    "mood": "dynamic, energetic, authentic, street-inspired",
    "props": "urban elements, nature elements, outdoor accessories",
    "use_case": "스트릿 브랜드, 아웃도어 제품"
}
```

### 5. detail_macro (디테일 클로즈업)
```python
PRESETS["detail_macro"] = {
    "background": "blurred neutral background, shallow depth of field",
    "lighting": "focused lighting, texture-revealing illumination, macro lighting setup",
    "camera": "extreme close-up, macro lens effect, detail focus, sharp foreground",
    "mood": "premium, luxurious, attention to detail",
    "focus": "material texture, stitching, logo detail, craftsmanship",
    "use_case": "품질 강조, 프리미엄 소재 어필"
}
```

### 6. flatlay (탑다운 코디)
```python
PRESETS["flatlay"] = {
    "background": "flat surface, clean backdrop, overhead view suitable background",
    "lighting": "even top-down lighting, no harsh shadows, uniform illumination",
    "camera": "perfect overhead 90-degree angle, bird's eye view, symmetrical composition",
    "mood": "organized, curated, aesthetically pleasing arrangement",
    "composition": "balanced layout, complementary items, visual hierarchy",
    "use_case": "코디 제안, 제품 조합, SNS 콘텐츠"
}
```

## 샷 타입별 프롬프트 전략

### Product Shot (제품 단독샷)
```python
SHOT_TYPES["product_shot"] = {
    "composition": "product as hero element, centered or rule of thirds, no distractions",
    "focus": "100% on product, minimal or no props",
    "scale": "product fills 60-80% of frame",
    "angle": "optimal product showcase angle",
    "prompt_suffix": ", isolated product, clear product visibility, professional commercial photography"
}
```

### Lifestyle (라이프스타일 연출)
```python
SHOT_TYPES["lifestyle"] = {
    "composition": "product in natural context, storytelling composition",
    "focus": "product + environment (50/50 or 60/40)",
    "scale": "product visible but not dominant",
    "props": "contextual items, lifestyle accessories, natural elements",
    "prompt_suffix": ", lifestyle photography, product in use scenario, authentic moment, relatable setting"
}
```

### Detail (디테일 클로즈업)
```python
SHOT_TYPES["detail"] = {
    "composition": "extreme close-up, specific product feature emphasized",
    "focus": "single detail element (logo, texture, stitching, material)",
    "scale": "detail fills entire frame",
    "depth_of_field": "shallow DOF, blurred background",
    "prompt_suffix": ", macro photography, extreme detail, material texture emphasis, craftsmanship focus"
}
```

### Group (그룹샷/코디)
```python
SHOT_TYPES["group"] = {
    "composition": "multiple products arranged harmoniously, balanced layout",
    "focus": "equal emphasis on all products, cohesive ensemble",
    "scale": "all products clearly visible, no cropping",
    "arrangement": "aesthetic product arrangement, visual flow",
    "prompt_suffix": ", product flat lay, curated product collection, coordinated styling, editorial arrangement"
}
```

## 다단계 향상 파이프라인

### Stage 1: 제품 분석 (VLM)
```python
def analyze_product(image_path: str) -> dict:
    """
    VLM으로 제품 특성 추출

    Returns:
        {
            "product_type": str,  # "sneakers", "bag", "watch" 등
            "dominant_colors": list[str],  # ["white", "navy blue"]
            "material": str,  # "leather", "canvas", "metal"
            "key_features": list[str],  # ["logo on tongue", "metal buckle"]
        }
    """
    from core.config import VISION_MODEL

    vlm_prompt = """
    Analyze this product image and extract:
    1. Product type (be specific: e.g., "high-top sneakers", "crossbody bag")
    2. Dominant colors (list top 2-3 colors in order of prominence)
    3. Primary material (leather, canvas, metal, plastic, etc.)
    4. Key visual features (logo placement, hardware, patterns, textures)

    Return in JSON format:
    {
        "product_type": "...",
        "dominant_colors": ["color1", "color2"],
        "material": "...",
        "key_features": ["feature1", "feature2"]
    }
    """

    response = call_vlm(VISION_MODEL, image_path, vlm_prompt)
    return parse_json(response)
```

### Stage 2: 기본 연출샷 생성
```python
def generate_base_shot(
    product_image: str,
    style_preset: str,
    shot_type: str,
    product_analysis: dict
) -> str:
    """
    스타일 프리셋 + 샷 타입 + 제품 분석 결과를 조합하여 프롬프트 생성
    """
    from core.config import IMAGE_MODEL

    preset = PRESETS[style_preset]
    shot = SHOT_TYPES[shot_type]

    # 제품 특성 기반 프롬프트 구성
    product_desc = f"{product_analysis['product_type']}, {product_analysis['material']} material"
    color_desc = ", ".join(product_analysis['dominant_colors'])
    feature_desc = ", ".join(product_analysis['key_features'])

    prompt = f"""
    Professional product photography of {product_desc}.
    Product colors: {color_desc}.
    Key features: {feature_desc}.

    Background: {preset['background']}
    Lighting: {preset['lighting']}
    Camera: {preset['camera']} {shot['angle']}
    Composition: {shot['composition']}
    Mood: {preset['mood']}
    {shot['prompt_suffix']}

    High-resolution commercial photography, product catalog quality, perfect lighting, sharp focus.
    """

    # 제품 이미지를 reference로 사용 (imagen3 edit 모드 또는 flux redux)
    return call_image_api(
        model=IMAGE_MODEL,
        prompt=prompt,
        reference_image=product_image,
        mode="edit"  # 제품 형태 유지하면서 배경/조명만 변경
    )
```

### Stage 3: 조명/텍스처 향상
```python
def enhance_lighting_texture(base_image: str, preset: str) -> str:
    """
    조명 품질과 텍스처 디테일 향상
    """
    from core.config import IMAGE_MODEL

    enhancement_prompt = f"""
    Enhance this product photography:
    - Improve lighting quality: {PRESETS[preset]['lighting']}
    - Enhance material texture and detail
    - Perfect color accuracy and saturation
    - Remove any artifacts or imperfections
    - Professional retouching while maintaining natural look

    Maintain original composition and product placement exactly.
    High-end commercial photography quality.
    """

    return call_image_api(
        model=IMAGE_MODEL,
        prompt=enhancement_prompt,
        reference_image=base_image,
        mode="enhance",
        guidance_scale=3.5  # 강한 가이드로 품질 향상
    )
```

### Stage 4: 색상 정확도 검증
```python
def validate_color_accuracy(
    original_product: str,
    generated_image: str,
    expected_colors: list[str]
) -> dict:
    """
    생성된 이미지의 제품 색상이 원본과 일치하는지 VLM으로 검증

    Returns:
        {
            "accuracy_score": float,  # 0-100
            "color_match": bool,  # True if >= 90
            "detected_colors": list[str],
            "issues": list[str]  # 발견된 문제점
        }
    """
    from core.config import VISION_MODEL

    vlm_prompt = f"""
    Compare the product colors in these two images:
    Image 1 (original product): Reference
    Image 2 (generated styled shot): To validate

    Expected product colors: {", ".join(expected_colors)}

    Evaluate:
    1. Color accuracy score (0-100): How well do the product colors match?
    2. Are all expected colors present and accurate?
    3. Any color shifts, saturation issues, or incorrect tones?

    Return in JSON format:
    {{
        "accuracy_score": <number 0-100>,
        "detected_colors": ["color1", "color2"],
        "issues": ["issue1 if any", "issue2 if any"]
    }}

    Focus ONLY on the product itself, ignore background/lighting differences.
    """

    response = call_vlm_compare(VISION_MODEL, original_product, generated_image, vlm_prompt)
    result = parse_json(response)
    result["color_match"] = result["accuracy_score"] >= 90
    return result
```

### 파이프라인 통합
```python
def run_product_styled_pipeline(
    product_image: str,
    style_preset: str,
    shot_type: str,
    options: dict = None
) -> dict:
    """
    전체 제품 연출 파이프라인 실행
    """
    print("[1/4] 제품 분석 중 (VLM)...")
    product_analysis = analyze_product(product_image)

    print("[2/4] 기본 연출샷 생성...")
    base_shot = generate_base_shot(
        product_image,
        style_preset,
        shot_type,
        product_analysis
    )

    print("[3/4] 조명/텍스처 향상...")
    enhanced_shot = enhance_lighting_texture(base_shot, style_preset)

    print("[4/4] 색상 정확도 검증...")
    validation = validate_color_accuracy(
        product_image,
        enhanced_shot,
        product_analysis["dominant_colors"]
    )

    if not validation["color_match"]:
        print(f"⚠️  색상 정확도: {validation['accuracy_score']}% (90% 미만)")
        print(f"   문제: {', '.join(validation['issues'])}")
        print("   재생성을 권장합니다.")
    else:
        print(f"✅ 색상 정확도: {validation['accuracy_score']}%")

    return {
        "final_image": enhanced_shot,
        "product_analysis": product_analysis,
        "validation": validation,
        "metadata": {
            "style_preset": style_preset,
            "shot_type": shot_type,
            "options": options
        }
    }
```

## 검증 기준

### 필수 통과 조건
| 항목 | 기준 | 측정 방법 |
|------|------|-----------|
| **색상 정확도** | ≥ 90% | VLM 비교 분석 |
| **제품 형태 보존** | 왜곡 없음 | VLM 구조 검증 |
| **조명 품질** | 자연스러움 | 전문가 기준 (그림자/하이라이트) |
| **배경 일관성** | 프리셋 일치 | 프롬프트 준수 여부 |

### 자동 재생성 트리거
```python
def should_regenerate(validation: dict) -> bool:
    """
    재생성 필요 여부 판단
    """
    if validation["accuracy_score"] < 90:
        return True

    critical_issues = [
        "wrong product color",
        "color shift",
        "product deformation",
        "missing key features"
    ]

    for issue in validation["issues"]:
        if any(crit in issue.lower() for crit in critical_issues):
            return True

    return False
```

## 옵션별 프롬프트 조정

### 색상 강조 (vivid color boost)
```python
if options.get("vivid_colors"):
    prompt += """
    Enhanced color vibrancy, rich saturation, bold color presentation.
    Maintain natural look while emphasizing product colors.
    Professional color grading for maximum visual impact.
    """
```

### 프리미엄 텍스처
```python
if options.get("premium_texture"):
    prompt += """
    Ultra-high detail texture rendering, premium material quality.
    Visible material grain, subtle reflections, luxurious finish.
    High-end product photography, editorial quality.
    """
```

### 특정 비율 지정
```python
ASPECT_RATIOS = {
    "1:1": "square format, Instagram post optimized",
    "3:4": "portrait format, mobile-friendly",
    "4:3": "standard horizontal, e-commerce product page",
    "16:9": "wide format, banner, hero image"
}

if options.get("aspect_ratio"):
    ratio_desc = ASPECT_RATIOS[options["aspect_ratio"]]
    prompt += f"\nComposition: {ratio_desc}"
```

## 출력 형식

### 성공 케이스
```
✅ **제품 연출 완료**

📸 **스타일:** gray_studio (그레이 스튜디오)
📷 **샷 타입:** lifestyle (라이프스타일 연출)

🎨 **제품 분석:**
- 제품: High-top sneakers
- 주요 색상: White, Navy blue
- 소재: Canvas with rubber sole
- 특징: Logo on tongue, Contrast stitching

✅ **검증 결과:**
- 색상 정확도: 94%
- 모든 주요 색상 정확히 재현
- 이슈: 없음

💾 **저장 위치:**
- output/product_styled_gray_studio_lifestyle_20260211_143022.png

📋 **메타데이터:**
- metadata_20260211_143022.json
```

### 실패 케이스 (재생성 권장)
```
⚠️  **색상 정확도 미달**

색상 정확도: 82% (목표: 90% 이상)

🔍 **발견된 문제:**
- Navy blue 색상이 약간 더 어둡게 렌더링됨
- Slight color shift in primary product color

💡 **권장 조치:**
1. 다시 생성 (자동 색상 보정 강화)
2. 다른 스타일 프리셋 시도
3. 원본 이미지 품질 확인

다시 생성하시겠습니까? (Y/N)
```

## 사용 예시

### 예시 1: 화이트 배경 상세페이지
```
User: 스니커즈 상세페이지 이미지 만들어줘
Bot: [이미지 업로드 요청]
User: [sneakers.png 업로드]
Bot: [스타일 선택 UI]
User: white_clean 선택
Bot: [샷 타입 선택 UI]
User: product_shot 선택
Bot: [생성 진행]
Result: 순백 배경에 스니커즈 단독샷, 색상 정확도 96%
```

### 예시 2: 라이프스타일 연출샷
```
User: 가방 라이프스타일 이미지 필요해
Bot: [이미지 업로드 요청]
User: [bag.png 업로드]
Bot: [스타일 선택 UI]
User: lifestyle_indoor 선택
Bot: [샷 타입 선택 UI]
User: lifestyle 선택
Bot: [생성 진행]
Result: 실내 자연광 환경에서 가방 + 책/식물 소품 연출
```

### 예시 3: 디테일 클로즈업
```
User: 시계 로고 디테일샷
Bot: [이미지 업로드 요청]
User: [watch.png 업로드]
Bot: [스타일 선택 UI]
User: detail_macro 선택
Bot: [샷 타입 선택 UI]
User: detail 선택
Result: 시계 로고/문자판 극클로즈업, shallow DOF
```

## 기술 스택

### 필수 의존성
```python
from core.config import IMAGE_MODEL, VISION_MODEL, PipelineConfig
from core.api import call_image_api, call_vlm
from core.validation import validate_image_quality
import json
import os
from datetime import datetime
```

### 설정 파일 참조
```python
# core/config.py에서 모델 설정 가져오기 (MANDATORY)
IMAGE_MODEL = "gemini-3-pro-image-preview"  # 이미지 생성
VISION_MODEL = "gemini-3-flash-preview"      # VLM 분석/검증
```

## 제약사항 및 유의사항

### 제약사항
1. **입력 이미지 품질:** 최소 1024x1024 권장
2. **제품 가시성:** 배경이 복잡하면 분석 정확도 하락
3. **색상 검증:** 조명 차이로 인한 자연스러운 편차는 허용 (±10%)
4. **생성 시간:** VLM 분석 포함 시 전체 파이프라인 약 30-60초

### Best Practices
1. **투명 배경 PNG 사용:** 제품 추출이 정확함
2. **다양한 각도 준비:** frontal + side + detail 각도별 원본 보유
3. **프리셋 조합:** white_clean + product_shot = 상세페이지 기본
4. **검증 실패 시:** 원본 이미지 조명/색상 확인 먼저

## 향후 확장 계획

### v1.1 (계획)
- [ ] 배치 모드: 여러 제품 동시 처리
- [ ] 커스텀 배경 업로드 지원
- [ ] A/B 테스트: 2개 스타일 동시 생성 비교

### v1.2 (계획)
- [ ] 360도 회전 뷰 생성
- [ ] 제품 크기/비율 자동 조정
- [ ] 브랜드 컬러 팔레트 적용

## 문의 및 지원

- 색상 정확도 90% 미만 계속 발생 시: 원본 이미지 품질 점검
- 특정 제품 타입 최적화 필요 시: 커스텀 프리셋 요청 가능
- 대량 배치 처리: 별도 스크립트 제공 예정
