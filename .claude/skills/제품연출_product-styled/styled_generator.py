"""
연출샷 생성기 - 스타일 프리셋 및 샷 타입 기반 이미지 생성
"""

from typing import Dict
from core.config import IMAGE_MODEL
from google import genai
from google.genai import types
import base64


# 스타일 프리셋 정의
PRESETS = {
    "white_clean": {
        "background": "pure white seamless background, professional product photography backdrop",
        "lighting": "softbox lighting, even illumination, no harsh shadows, commercial studio lighting",
        "camera": "frontal angle, centered composition, high resolution product shot",
        "mood": "clean, minimal, professional, e-commerce ready",
        "post_processing": "color correction, shadow removal, perfect white balance",
        "use_case": "상세페이지 메인 이미지, 썸네일"
    },
    "gray_studio": {
        "background": "neutral gray gradient backdrop, studio background paper",
        "lighting": "three-point studio lighting, rim light for depth, soft key light",
        "camera": "slight angle, dynamic composition, editorial product photography",
        "mood": "sophisticated, editorial, lookbook quality",
        "post_processing": "subtle vignette, professional color grading",
        "use_case": "룩북, 브랜드 카탈로그"
    },
    "lifestyle_indoor": {
        "background": "modern interior setting, natural home environment, minimalist decor",
        "lighting": "soft window light, natural indoor lighting, warm ambient glow",
        "camera": "lifestyle composition, product in context, relatable scene",
        "mood": "cozy, authentic, relatable, everyday life",
        "props": "complementary home objects, books, plants, natural textures",
        "use_case": "SNS 콘텐츠, 라이프스타일 매거진"
    },
    "lifestyle_outdoor": {
        "background": "urban outdoor setting, street photography backdrop, natural environment",
        "lighting": "natural daylight, golden hour lighting, outdoor ambient light",
        "camera": "environmental portrait style, product in lifestyle context",
        "mood": "dynamic, energetic, authentic, street-inspired",
        "props": "urban elements, nature elements, outdoor accessories",
        "use_case": "스트릿 브랜드, 아웃도어 제품"
    },
    "detail_macro": {
        "background": "blurred neutral background, shallow depth of field",
        "lighting": "focused lighting, texture-revealing illumination, macro lighting setup",
        "camera": "extreme close-up, macro lens effect, detail focus, sharp foreground",
        "mood": "premium, luxurious, attention to detail",
        "focus": "material texture, stitching, logo detail, craftsmanship",
        "use_case": "품질 강조, 프리미엄 소재 어필"
    },
    "flatlay": {
        "background": "flat surface, clean backdrop, overhead view suitable background",
        "lighting": "even top-down lighting, no harsh shadows, uniform illumination",
        "camera": "perfect overhead 90-degree angle, bird's eye view, symmetrical composition",
        "mood": "organized, curated, aesthetically pleasing arrangement",
        "composition": "balanced layout, complementary items, visual hierarchy",
        "use_case": "코디 제안, 제품 조합, SNS 콘텐츠"
    }
}


# 샷 타입 정의
SHOT_TYPES = {
    "product_shot": {
        "composition": "product as hero element, centered or rule of thirds, no distractions",
        "focus": "100% on product, minimal or no props",
        "scale": "product fills 60-80% of frame",
        "angle": "optimal product showcase angle",
        "prompt_suffix": ", isolated product, clear product visibility, professional commercial photography"
    },
    "lifestyle": {
        "composition": "product in natural context, storytelling composition",
        "focus": "product + environment (50/50 or 60/40)",
        "scale": "product visible but not dominant",
        "props": "contextual items, lifestyle accessories, natural elements",
        "prompt_suffix": ", lifestyle photography, product in use scenario, authentic moment, relatable setting"
    },
    "detail": {
        "composition": "extreme close-up, specific product feature emphasized",
        "focus": "single detail element (logo, texture, stitching, material)",
        "scale": "detail fills entire frame",
        "depth_of_field": "shallow DOF, blurred background",
        "prompt_suffix": ", macro photography, extreme detail, material texture emphasis, craftsmanship focus"
    },
    "group": {
        "composition": "multiple products arranged harmoniously, balanced layout",
        "focus": "equal emphasis on all products, cohesive ensemble",
        "scale": "all products clearly visible, no cropping",
        "arrangement": "aesthetic product arrangement, visual flow",
        "prompt_suffix": ", product flat lay, curated product collection, coordinated styling, editorial arrangement"
    }
}


def generate_base_shot(
    product_image: str,
    style_preset: str,
    shot_type: str,
    product_analysis: Dict,
    api_key: str,
    options: Dict = None
) -> bytes:
    """
    스타일 프리셋 + 샷 타입 + 제품 분석 결과를 조합하여 기본 연출샷 생성

    Args:
        product_image: 제품 이미지 경로
        style_preset: 스타일 프리셋 키 (예: "white_clean")
        shot_type: 샷 타입 키 (예: "product_shot")
        product_analysis: analyze_product()의 반환값
        api_key: Gemini API 키
        options: 추가 옵션 (vivid_colors, premium_texture, aspect_ratio 등)

    Returns:
        생성된 이미지 바이트
    """
    client = genai.Client(api_key=api_key)

    preset = PRESETS[style_preset]
    shot = SHOT_TYPES[shot_type]

    # 제품 특성 기반 프롬프트 구성
    product_desc = f"{product_analysis['product_type']}, {product_analysis['material']} material"
    color_desc = ", ".join(product_analysis['dominant_colors'])
    feature_desc = ", ".join(product_analysis['key_features'])

    # 기본 프롬프트
    prompt = f"""
    Professional product photography of {product_desc}.
    Product colors: {color_desc}.
    Key features: {feature_desc}.

    Background: {preset['background']}
    Lighting: {preset['lighting']}
    Camera: {preset['camera']}
    Composition: {shot['composition']}
    Mood: {preset['mood']}
    {shot['prompt_suffix']}

    High-resolution commercial photography, product catalog quality, perfect lighting, sharp focus.
    """

    # 옵션 적용
    if options:
        if options.get("vivid_colors"):
            prompt += """
            Enhanced color vibrancy, rich saturation, bold color presentation.
            Maintain natural look while emphasizing product colors.
            Professional color grading for maximum visual impact.
            """

        if options.get("premium_texture"):
            prompt += """
            Ultra-high detail texture rendering, premium material quality.
            Visible material grain, subtle reflections, luxurious finish.
            High-end product photography, editorial quality.
            """

        if options.get("aspect_ratio"):
            aspect_ratios = {
                "1:1": "square format, Instagram post optimized",
                "3:4": "portrait format, mobile-friendly",
                "4:3": "standard horizontal, e-commerce product page",
                "16:9": "wide format, banner, hero image"
            }
            ratio_desc = aspect_ratios.get(options["aspect_ratio"], "")
            if ratio_desc:
                prompt += f"\nComposition: {ratio_desc}"

    # 제품 이미지 로드
    with open(product_image, 'rb') as f:
        image_data = f.read()

    # 이미지 생성
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[
            types.Part.from_bytes(data=image_data, mime_type="image/png"),
            prompt
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=options.get("aspect_ratio", "3:4") if options else "3:4",
                image_size="2K"
            )
        )
    )

    # 이미지 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data

    raise ValueError("이미지 생성 실패: 응답에 이미지 없음")


def enhance_lighting_texture(base_image: bytes, preset: str, api_key: str) -> bytes:
    """
    조명 품질과 텍스처 디테일 향상

    Args:
        base_image: 기본 이미지 바이트
        preset: 스타일 프리셋 키
        api_key: Gemini API 키

    Returns:
        향상된 이미지 바이트
    """
    client = genai.Client(api_key=api_key)

    preset_config = PRESETS[preset]

    enhancement_prompt = f"""
    Enhance this product photography:
    - Improve lighting quality: {preset_config['lighting']}
    - Enhance material texture and detail
    - Perfect color accuracy and saturation
    - Remove any artifacts or imperfections
    - Professional retouching while maintaining natural look

    Maintain original composition and product placement exactly.
    High-end commercial photography quality.
    """

    # 이미지 향상
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[
            types.Part.from_bytes(data=base_image, mime_type="image/png"),
            enhancement_prompt
        ],
        config=types.GenerateContentConfig(
            temperature=0.15,
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="3:4",
                image_size="2K"
            )
        )
    )

    # 이미지 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data

    raise ValueError("이미지 향상 실패: 응답에 이미지 없음")
