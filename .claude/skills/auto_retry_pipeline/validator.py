"""
품질 검수기 - 원본과 생성 이미지 비교
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Tuple
from .config import PipelineConfig
from core.utils import ImageUtils


VALIDATION_PROMPT = """You are an EXTREMELY STRICT quality validator for AI background-swapped fashion photography.
Your job is to detect ANY sign of compositing, color mismatch, or unnatural appearance.
Score HARSHLY - a real fashion editor would reject anything that looks even slightly fake.

Compare the ORIGINAL image (first) and GENERATED image (second).

Score each aspect 0-100:

1. **model_preservation** (CRITICAL):
   - Is the person's SIZE identical? (not shrunk or enlarged)
   - Is the POSE identical? (same arm/leg/body positions)
   - Is the FACE identical? (same features, expression, angle)
   - Is the CLOTHING identical? (same garments, colors, logos)
   - Are the SKIN TONES identical? (not greyed out, not desaturated, not color-shifted)
   - Are CLOTHING COLORS identical? (navy must stay navy, not shift to black or grey)
   Score 100 ONLY if ALL are perfectly preserved INCLUDING color fidelity.
   Score 70-80 if pose/face OK but skin tone or clothing colors shifted.
   Score below 50 if colors are clearly different from original.

2. **lighting_match** (STRICT - CHECK SHADOW PATTERNS):
   - Does the SHADOW DIRECTION on the model match the background light source?
     Example: if background has sunlight from upper-right casting shadows to lower-left,
     the model MUST also show highlights on the right and shadows on the left.
   - Do SHADOW PATTERNS match? If background has hard geometric shadows (e.g. from architecture),
     does the model have similar hard shadow characteristics?
   - Is the LIGHT INTENSITY consistent? Studio-lit model in harsh sunlight background = FAIL.
   - Is COLOR TEMPERATURE consistent? Warm-toned model in cool blue-grey background = FAIL.
   - Has the model's skin tone been DESATURATED or GREY-SHIFTED to match a grey background?
     This is a CRITICAL compositing tell - score 30-50 if detected.
   - Score 90-100 ONLY if lighting feels completely natural and integrated.
   - Score 50-70 if slight mismatch but not immediately obvious.
   - Score 0-40 if model clearly looks "pasted on" due to lighting mismatch.

3. **perspective_match** (CHECK SPATIAL DEPTH):
   - Does the camera angle match between model and background?
   - Does the DEPTH feel natural? Does the model appear to exist INSIDE the 3D space?
   - Is ATMOSPHERIC PERSPECTIVE consistent? (distant objects should be hazier)
   - Does the model's SCALE relative to background elements make spatial sense?
   - Score 0-40 if model looks like a flat cutout pasted onto a 3D background.
   - Score 50-70 if depth is slightly off but passable.
   - Score 90-100 ONLY if spatial integration is completely seamless.

4. **ground_contact** (CHECK REAL SHADOW CASTING):
   - Does the model cast a SHADOW on the ground that matches the background lighting?
   - Is the shadow DIRECTION consistent with other shadows in the scene?
   - Is the shadow SOFTNESS appropriate? (hard sun = hard shadows, overcast = soft shadows)
   - Does the model's feet/base make REALISTIC CONTACT with the ground surface?
   - Is there a visible gap or floating appearance between model and ground?
   - If sitting: is there a visible surface with proper contact shadow?
   - Score 0-30 if shadow is missing, wrong direction, or model appears to float.
   - Score 50-70 if shadow exists but doesn't quite match the scene lighting.
   - Score 90-100 ONLY if ground contact and shadows are perfectly integrated.

5. **edge_quality**:
   - Are edges around the person SEAMLESSLY blended with the background?
   - Any visible HALO, glow, or bright/dark fringe around the model outline?
   - Any COLOR BLEEDING between model and background at the boundary?
   - Is HAIR properly blended? (hair edges are the hardest to get right)
   - Any JAGGED or unnaturally sharp edges?
   - Score 0-40 if obvious halo or fringing visible.
   - Score 50-70 if edges are mostly clean but some artifacts on close inspection.
   - Score 90-100 ONLY if edges are indistinguishable from a real photograph.

6. **physics_plausibility** (CRITICAL - COMPARE BOTH IMAGES CAREFULLY):
   - Look at the ORIGINAL image: what is supporting each person? (stairs, bench, wall, ground)
   - Look at the GENERATED image: is that SAME support structure present?
   - SITTING POSE CHECK: If any person is sitting in the original (bent knees, elevated hips),
     the generated image MUST have a visible surface at the SAME HEIGHT to sit on.
     A flat ground/road does NOT count as a sitting surface if the original shows steps/bench.
     Score 0-20 if sitting pose exists but no elevated surface in generated image.
   - LEANING POSE CHECK: If leaning against something in original, generated must have
     equivalent wall/surface. Score 0-20 if nothing to lean on.
   - HEIGHT CONSISTENCY: If original shows people at different vertical heights (e.g. stairs),
     the generated background MUST explain those height differences.
     Score 0-20 if people are at impossible heights with no supporting structure.
   - Score 0 if physically impossible (person floating, no support for seated pose)
   - Score 80-100 ONLY if all poses have matching physical support in the generated scene

7. **prop_style_consistency**:
   - If the model is sitting on, leaning against, or interacting with a prop/furniture:
     Does that prop's style MATCH the background environment?
   - Examples of MISMATCH: modern metal stool in a rustic park, plastic chair in luxury hotel lobby,
     industrial bench in a beach setting, ornate wooden chair in minimalist concrete studio
   - Examples of MATCH: wooden bench in park, metal stool in industrial loft, elegant chair in hotel lobby
   - If NO props (model standing freely): score 100
   - Score 0-30: severe style clash (prop looks completely out of place)
   - Score 40-60: noticeable mismatch but not jarring
   - Score 70-100: prop style fits naturally with background

IMPORTANT COMPOSITING TELLS TO WATCH FOR:
- Model's skin appears GREY or DESATURATED compared to how real skin looks in that lighting
- Model has FLAT studio lighting but background has DIRECTIONAL natural light
- Model's shadow goes in DIFFERENT DIRECTION than background shadows
- Model looks like a 2D CUTOUT pasted onto a 3D space (no depth integration)
- Color grading on model DOESN'T MATCH color grading on background
- Model's clothing colors SHIFTED from original (navy→black, brown→grey)

Return ONLY valid JSON (no markdown):
{
  "scores": {
    "model_preservation": <0-100>,
    "lighting_match": <0-100>,
    "perspective_match": <0-100>,
    "ground_contact": <0-100>,
    "edge_quality": <0-100>,
    "physics_plausibility": <0-100>,
    "prop_style_consistency": <0-100>
  },
  "total": <weighted average>,
  "pass": <true if model_preservation=100 AND physics_plausibility>=50 AND total>=95>,
  "notes": "<brief explanation of any compositing issues detected>"
}"""


class QualityValidator:
    """품질 검수기"""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def validate(self, original_path: str, generated_path: str, api_key: str) -> Dict[str, Any]:
        """원본과 생성 이미지 비교 검수"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # 이미지 로드
        original_bytes = ImageUtils.load_image(original_path, self.config.max_image_size)
        generated_bytes = ImageUtils.load_image(generated_path, self.config.max_image_size)

        try:
            response = client.models.generate_content(
                model=self.config.vision_model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=VALIDATION_PROMPT),
                    types.Part(text="ORIGINAL IMAGE:"),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=original_bytes)),
                    types.Part(text="GENERATED IMAGE:"),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=generated_bytes)),
                ])],
                config=types.GenerateContentConfig(temperature=0.1)
            )

            result_text = response.candidates[0].content.parts[0].text
            result = ImageUtils.parse_json(result_text)

            # 판정 로직 (CLAUDE.md 기준)
            if result.get("scores"):
                scores = result["scores"]
                model_pres = scores.get("model_preservation", 0)

                # 가중 평균 계산 (7개 항목)
                physics_plaus = scores.get("physics_plausibility", 100)
                prop_style = scores.get("prop_style_consistency", 100)
                total = (
                    model_pres * 0.30 +
                    scores.get("lighting_match", 0) * 0.12 +
                    scores.get("perspective_match", 0) * 0.08 +
                    scores.get("ground_contact", 0) * 0.13 +
                    scores.get("edge_quality", 0) * 0.10 +
                    physics_plaus * 0.15 +
                    prop_style * 0.12
                )

                result["total"] = round(total, 1)
                result["pass"] = (
                    model_pres >= self.config.model_preservation_threshold and
                    physics_plaus >= self.config.physics_plausibility_threshold and
                    total >= self.config.total_score_threshold
                )

            return result

        except Exception as e:
            return {
                "error": str(e),
                "scores": {},
                "total": 0,
                "pass": False
            }
