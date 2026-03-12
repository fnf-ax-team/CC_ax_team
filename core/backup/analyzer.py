"""
VFX 모델 물리 분석 - 카메라, 조명, 포즈 의존성, 설치 논리 추출
"""

import json
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Optional
from core.config import VISION_MODEL


ANALYSIS_PROMPT = """You are a world-class VFX supervisor and photo director.
Analyze this person photo and extract physical constraints as JSON for seamless background compositing.
The person must NOT be modified at all - only the background will change.

Analyze and return JSON with these fields:

{
  "geometry": {
    "horizon_y": 0.0-1.0 (normalized horizon line position),
    "perspective": "eye-level" | "high-angle" | "low-angle",
    "focal_length_vibe": "35mm" | "50mm" | "85mm"
  },
  "lighting": {
    "direction_clock": "1"-"12" (clock direction of light source),
    "elevation": "low" | "mid" | "high",
    "softness": 0.0-1.0 (0=hard, 1=soft),
    "color_temp": "warm" | "neutral" | "cool" or Kelvin value
  },
  "pose_dependency": {
    "pose_type": "standing" | "sitting" | "leaning" | "crouching" | "lying",
    "support_required": true/false,
    "support_type": "wall" | "chair" | "bench" | "railing" | "steps" | "none",
    "support_direction": "behind" | "behind-left" | "behind-right" | "below" | "left" | "right" | "none",
    "prompt_requirement": "Background MUST include [specific support] at [direction] for [pose]" or "No support needed"
  },
  "installation_logic": {
    "props_detected": ["list of props/objects near model"],
    "fixed_props": true/false,
    "placement_rule": "description of spatial constraints",
    "forbidden_contexts": ["places where this setup cannot exist"]
  },
  "physics_anchors": {
    "contact_points": [{"label": "left_foot", "coord": [x, y]}, ...],
    "shadow_direction": [x, y]
  },
  "semantic_style": {
    "vibe": "street_editorial" | "studio" | "indoor" | "outdoor",
    "background_type": "white_studio" | "colored_studio" | "indoor" | "outdoor" (analyze the ACTUAL background behind the person - if it is a plain white/grey/light backdrop, it is "white_studio"),
    "recommended_locations": ["location1", "location2", ...]
  }
}

Be precise with numbers. Return ONLY valid JSON."""


def analyze_model_physics(image_pil: Image.Image, api_key: str) -> Dict[str, Any]:
    """
    모델 이미지의 물리적/맥락적 키값을 추출.

    Args:
        image_pil: PIL Image 객체
        api_key: Gemini API 키

    Returns:
        {"status": "success"|"error", "data": {...}, "generated_guideline": str}
    """
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=api_key)

        # 1024px 다운샘플링 (공간 분석이므로 높은 해상도)
        img = image_pil.copy().convert('RGB')
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        # PIL -> bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Content(role="user", parts=[
                types.Part(text=ANALYSIS_PROMPT),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)),
            ])],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2000,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        guideline = build_background_guideline(data)

        return {"status": "success", "data": data, "generated_guideline": guideline}

    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "data": {}, "generated_guideline": ""}


def build_background_guideline(analysis_data: dict) -> str:
    """추출된 키값을 배경 생성 프롬프트 가이드라인으로 조립."""
    geom = analysis_data.get('geometry', {})
    light = analysis_data.get('lighting', {})
    pose = analysis_data.get('pose_dependency', {})
    logic = analysis_data.get('installation_logic', {})
    style = analysis_data.get('semantic_style', {})

    parts = []

    # 카메라 지오메트리
    if geom:
        parts.append(f"Perspective: {geom.get('perspective', 'eye-level')} with vanishing point at y={geom.get('horizon_y', 0.5)}")
        if geom.get('focal_length_vibe'):
            parts.append(f"Focal length vibe: {geom['focal_length_vibe']}")

    # 조명
    if light:
        parts.append(f"Lighting: Source from {light.get('direction_clock', '12')} o'clock, {light.get('elevation', 'mid')} elevation, softness {light.get('softness', 0.5)}")
        if light.get('color_temp'):
            parts.append(f"Color temperature: {light['color_temp']}")

    # 포즈 의존성 (가장 중요)
    if pose and pose.get('support_required'):
        req = pose.get('prompt_requirement', '')
        if req and req != "No support needed":
            parts.append(f"CRITICAL - POSE SUPPORT: {req}")

    # 설치 논리
    if logic:
        if logic.get('placement_rule'):
            parts.append(f"Spatial Logic: {logic['placement_rule']}")
        forbidden = logic.get('forbidden_contexts', [])
        if forbidden:
            parts.append(f"Avoid: {', '.join(forbidden)}")

    # 스타일
    if style and style.get('vibe'):
        parts.append(f"Style vibe: {style['vibe']}")

    if not parts:
        return ""

    return "PHYSICS GUIDELINE: " + ". ".join(parts) + "."
