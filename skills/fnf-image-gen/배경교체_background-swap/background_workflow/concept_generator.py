"""
컨셉 생성기 - 사용자 입력을 여러 베리에이션으로 해석
"""

import json
from io import BytesIO
from PIL import Image
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from core.config import VISION_MODEL


@dataclass
class ConceptVariation:
    """컨셉 베리에이션"""
    id: str  # V1, V2, V3
    name: str  # "모던 베를린"
    keywords: List[str]  # ["유리", "철골", "차가운 톤"]
    description: str  # 짧은 설명
    prompt: str  # 생성용 상세 프롬프트


# 레퍼런스 이미지 없을 때 - 다양한 해석
VARIATION_PROMPT_NO_REF = """You are a creative director for fashion photography backgrounds.

The user wants: "{user_concept}"

Generate {count} DISTINCTLY DIFFERENT visual interpretations of this concept.
Each variation should be visually unique and suitable for fashion photography.

For each variation, provide:
1. A short name (e.g., "Modern Berlin", "Classic Berlin")
2. Key visual keywords (3-5 words)
3. A brief description (1 sentence)
4. A detailed background prompt for AI image generation

Return ONLY valid JSON (no markdown):
{{
  "variations": [
    {{
      "id": "V1",
      "name": "variation name",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "description": "Brief description of this interpretation",
      "prompt": "Detailed prompt for background generation: [location], [materials], [colors], [lighting], [mood], [specific details]. Professional fashion photography background."
    }}
  ]
}}

Make each variation clearly distinct:
- Different architectural styles or settings
- Different color palettes
- Different moods/atmospheres
- Different times of day or lighting conditions"""


# 레퍼런스 이미지 있을 때 - 세밀한 베리에이션
VARIATION_PROMPT_WITH_REF = """You are a creative director for fashion photography backgrounds.

The user wants: "{user_concept}"
They provided a REFERENCE IMAGE showing the desired style/mood.

Analyze the reference image and generate {count} SUBTLE VARIATIONS of the same concept.
All variations should maintain the core visual identity but emphasize different aspects.

Examples of subtle variations:
- Material emphasis: V1 emphasizes metal, V2 emphasizes concrete, V3 emphasizes texture
- Lighting emphasis: V1 warmer tones, V2 cooler tones, V3 dramatic contrast
- Detail emphasis: V1 clean/minimal, V2 more texture detail, V3 architectural detail

For each variation, provide:
1. A short name describing the emphasis (e.g., "Metal Focus", "Texture Rich")
2. Key visual keywords (3-5 words)
3. A brief description of what makes this variation unique
4. A detailed background prompt

Return ONLY valid JSON (no markdown):
{{
  "base_concept": "description of the core concept from reference",
  "variations": [
    {{
      "id": "V1",
      "name": "variation name (emphasis point)",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "description": "What this variation emphasizes differently",
      "prompt": "Detailed prompt maintaining base concept but emphasizing [specific aspect]. Professional fashion photography background."
    }}
  ]
}}

IMPORTANT: Variations should be SUBTLE, not completely different concepts.
Think of it as different "flavors" of the same dish, not different dishes."""


REFINE_PROMPT = """You are refining a background concept based on user feedback.

Original concept:
- Name: {original_name}
- Prompt: {original_prompt}

User feedback: "{feedback}"

Modify the prompt to incorporate the feedback while keeping the base concept.

Return ONLY valid JSON:
{{
  "name": "updated name if needed",
  "keywords": ["updated", "keywords"],
  "description": "updated description",
  "prompt": "updated detailed prompt incorporating feedback"
}}"""


class ConceptGenerator:
    """컨셉 생성기"""

    def __init__(self, api_key: str, model: str = VISION_MODEL):
        self.api_key = api_key
        self.model = model

    def generate_variations(
        self,
        user_concept: str,
        count: int = 3,
        reference_image_path: Optional[str] = None
    ) -> List[ConceptVariation]:
        """사용자 컨셉을 여러 베리에이션으로 확장"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        parts = []

        # 레퍼런스 이미지 유무에 따라 다른 프롬프트
        if reference_image_path:
            prompt_text = VARIATION_PROMPT_WITH_REF.format(
                user_concept=user_concept,
                count=count
            )
        else:
            prompt_text = VARIATION_PROMPT_NO_REF.format(
                user_concept=user_concept,
                count=count
            )
        parts.append(types.Part(text=prompt_text))

        # 참조 이미지가 있으면 추가
        if reference_image_path:
            img_bytes = self._load_image(reference_image_path)
            parts.append(types.Part(text="Reference image:"))
            parts.append(types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)))

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.7)
            )

            result_text = response.candidates[0].content.parts[0].text
            result = self._parse_json(result_text)

            variations = []
            for v in result.get("variations", []):
                variations.append(ConceptVariation(
                    id=v.get("id", f"V{len(variations)+1}"),
                    name=v.get("name", ""),
                    keywords=v.get("keywords", []),
                    description=v.get("description", ""),
                    prompt=self._build_full_prompt(v.get("prompt", ""))
                ))

            return variations

        except Exception as e:
            print(f"Error generating variations: {e}")
            return []

    def refine_concept(
        self,
        original: ConceptVariation,
        feedback: str
    ) -> ConceptVariation:
        """사용자 피드백으로 컨셉 수정"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        prompt = REFINE_PROMPT.format(
            original_name=original.name,
            original_prompt=original.prompt,
            feedback=feedback
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=prompt)
                ])],
                config=types.GenerateContentConfig(temperature=0.5)
            )

            result_text = response.candidates[0].content.parts[0].text
            result = self._parse_json(result_text)

            return ConceptVariation(
                id=original.id + "_refined",
                name=result.get("name", original.name),
                keywords=result.get("keywords", original.keywords),
                description=result.get("description", original.description),
                prompt=self._build_full_prompt(result.get("prompt", original.prompt))
            )

        except Exception as e:
            print(f"Error refining concept: {e}")
            return original

    def _build_full_prompt(self, background_prompt: str) -> str:
        """배경 프롬프트를 전체 생성 프롬프트로 확장"""
        return f"""BACKGROUND SPECIFICATION:
{background_prompt}

Style: Professional fashion photography
Lighting: Soft, flattering light matching the scene
Quality: High-end editorial look, seamless compositing"""

    def _load_image(self, path: str) -> bytes:
        """이미지 로드"""
        img = Image.open(path).convert('RGB')
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """JSON 파싱"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(text)
        except:
            return {}
