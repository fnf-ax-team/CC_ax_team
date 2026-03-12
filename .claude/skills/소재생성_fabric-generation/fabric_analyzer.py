"""
소재 분석기 - VLM으로 10단계 속성 추출
"""

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import json

from core.config import VISION_MODEL


def load_api_keys():
    """프로젝트 루트의 .env에서 API 키 로드"""
    import os
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


def analyze_fabric_attributes(image_path: str) -> dict:
    """
    원단 이미지 → 10단계 속성 추출

    Args:
        image_path: 분석할 원단 이미지 경로

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
        model=VISION_MODEL,  # core/config.py에서 가져온 상수
        contents=[types.Content(role="user", parts=[
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))
        ])]
    )

    text = response.candidates[0].content.parts[0].text

    # JSON 추출 (```json ... ``` 제거)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        # 마크다운 코드블럭 일반 형태
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

    return json.loads(text.strip())
