"""
VLM 배경 분석 - 참조 이미지에서 배경 스타일을 텍스트로 추출
"""

import json
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Optional
from core.config import VISION_MODEL


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


BACKGROUND_SWAP_ANALYSIS_PROMPT = """Analyze this photo for seamless background replacement. Return JSON only:

{
  "has_vehicle": true/false,
  "vehicle_description": "car/motorcycle/bicycle type and color if exists, or null",
  "ground": {
    "material": "concrete/asphalt/sand/tile/wood/cobblestone/etc",
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
}"""


def analyze_background(image_pil: Image.Image, api_key: str) -> str:
    """
    배경/참조 이미지를 구체적인 텍스트 설명으로 변환.

    Args:
        image_pil: PIL Image 객체
        api_key: Gemini API 키

    Returns:
        배경 설명 텍스트 (영문)
    """
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=api_key)

        # 512px 다운샘플링 (텍스트 추출이므로 낮은 해상도 가능)
        img = image_pil.copy().convert('RGB')
        max_size = 512
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=[
                types.Part(text=BACKGROUND_ANALYSIS_PROMPT),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)),
            ])],
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.9,
                max_output_tokens=512
            )
        )

        text = response.text.strip()
        # 마크다운 코드 블록 제거
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join([l for l in lines if not l.strip().startswith("```")])
        return text.strip()

    except Exception as e:
        return f"Error analyzing background: {str(e)[:100]}"


def analyze_for_background_swap(image_pil: Image.Image, api_key: str) -> Dict[str, Any]:
    """
    배경 교체용 상세 분석 (차량 감지, 바닥 톤 매칭, 색보정 포함).

    Args:
        image_pil: PIL Image 객체 (원본 인물 사진)
        api_key: Gemini API 키

    Returns:
        분석 결과 딕셔너리
    """
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=api_key)

        # 1024px 다운샘플링
        img = image_pil.copy().convert('RGB')
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=[
                types.Part(text=BACKGROUND_SWAP_ANALYSIS_PROMPT),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)),
            ])],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        return json.loads(response.text)

    except Exception as e:
        return {"error": str(e)[:100]}


def build_swap_instructions(swap_analysis: Dict[str, Any]) -> str:
    """
    배경교체 분석 결과를 프롬프트 지시문으로 변환.

    Args:
        swap_analysis: analyze_for_background_swap() 결과

    Returns:
        프롬프트에 추가할 지시문 텍스트
    """
    parts = []

    # 차량 보존
    if swap_analysis.get("has_vehicle"):
        desc = swap_analysis.get("vehicle_description", "vehicle")
        parts.append(f"""CRITICAL: VEHICLE PRESERVATION - There is a {desc} in this image. Keep it EXACTLY as is. Do NOT remove, hide, or modify the vehicle.""")

    # 바닥 연속성
    ground = swap_analysis.get("ground", {})
    if ground:
        parts.append(f"GROUND CONTINUITY: Ground material={ground.get('material', 'concrete')}, color={ground.get('color', 'gray')} ({ground.get('tone', 'neutral')} tone). Ground must continue seamlessly.")

    # 색보정 매칭
    color = swap_analysis.get("color_grading", {})
    if color:
        parts.append(f"COLOR MATCHING: Overall warmth={color.get('overall_warmth', 'neutral')}, saturation={color.get('saturation', 'medium')}. Apply same color grading to background.")

    return "\n".join(parts)
