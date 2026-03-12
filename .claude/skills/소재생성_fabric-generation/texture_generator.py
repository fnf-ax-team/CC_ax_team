"""
텍스처 생성기 - 타일 가능한 원단 이미지 생성
"""

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

from core.config import IMAGE_MODEL, VISION_MODEL


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


def build_fabric_prompt(attributes: dict) -> str:
    """
    10단계 속성 → 영문 생성 프롬프트

    Args:
        attributes: 10단계 속성 dict

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


def validate_tileability(image: Image.Image) -> dict:
    """
    생성된 텍스처의 타일링 가능성 검증 (VLM 판단)

    Args:
        image: 검증할 이미지

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

    # JSON 추출
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

    import json
    result = json.loads(text.strip())
    result["pass"] = result.get("tileability", 0) >= 90
    return result


def generate_fabric_texture(attributes: dict, max_retries: int = 2) -> Image.Image:
    """
    10단계 속성 → 타일 가능한 원단 텍스처 생성

    Args:
        attributes: 10단계 속성 dict
        max_retries: 최대 재시도 횟수

    Returns:
        PIL Image or None
    """
    prompt = build_fabric_prompt(attributes)

    for attempt in range(max_retries + 1):
        print(f"[Attempt {attempt+1}/{max_retries+1}] Generating fabric texture...")

        # 이미지 생성
        client = genai.Client(api_key=get_next_api_key())
        response = client.models.generate_content(
            model=IMAGE_MODEL,  # core/config.py 상수
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
            print(f"  -> Failed: {validation.get('edge_match', 'edge mismatch')}")
            if attempt < max_retries:
                # 프롬프트 강화
                prompt += "\n\nIMPORTANT: Edges must match PERFECTLY for seamless tiling. Ensure pattern continues at borders."

    print(f"  -> Max retries reached, returning best attempt")
    return image
