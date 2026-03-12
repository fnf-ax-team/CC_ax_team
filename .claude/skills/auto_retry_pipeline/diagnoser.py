"""
실패 원인 진단기 - 왜 실패했는지 분석하고 보강 정보 추출
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from io import BytesIO
from PIL import Image
from typing import Dict, Any, List
from .config import PipelineConfig
from core.utils import ImageUtils


DIAGNOSIS_PROMPT = """You are an expert at analyzing AI image generation failures.

Compare the ORIGINAL image and FAILED GENERATED image to diagnose what went wrong.

Analyze and score each aspect (0-100):

1. **pose_match**: Are body parts in EXACTLY the same position?
   - Check: arm positions, hand positions, leg positions, body angle, head tilt
   - Score 100 only if pose is pixel-perfect identical

2. **face_match**: Is the face IDENTICAL?
   - Check: facial features, expression, mouth (open/closed), eye direction
   - Score 100 only if face is unchanged

3. **scale_match**: Is the person the SAME SIZE in frame?
   - Check: is the person shrunk? zoomed out? cropped differently?
   - Score 100 only if framing is identical

4. **physics_plausibility**: Does the pose make PHYSICAL SENSE with the new background?
   - Check: if leaning, is there something to lean on?
   - Check: if sitting, is there something to sit on?
   - Check: are shadows consistent with pose and lighting?

5. **clothing_match**: Are clothes IDENTICAL?
   - Check: same garments, colors, logos, text, patterns
   - Score 100 only if clothing is perfectly preserved

6. **prop_style_consistency**: Do the props/furniture in the generated image match the background style?
   - If model is sitting on a modern metal stool but background is a rustic park → score low
   - If model is leaning on a concrete pillar and background is industrial → score high
   - If no props involved (standing freely) → score 100
   - Score 0-30 if prop style severely clashes with background
   - Score 70-100 if prop style fits naturally with background

7. **lighting_match**: Does the lighting on the model match the new background? BE STRICT.
   - Check: does the SHADOW DIRECTION on the model match the background's light source?
     If background has sunlight from upper-right, model must have highlights on right, shadows on left.
   - Check: do SHADOW PATTERNS match? Hard architectural shadows in background = model should have similar hard shadows.
   - Check: is the model DESATURATED or GREY-SHIFTED compared to natural skin tone?
     A model with grey/lifeless skin in a concrete background is a compositing tell - score LOW.
   - Check: does the model look like they were ACTUALLY PHOTOGRAPHED in this lighting?
   - Score 90-100 ONLY if lighting integration is seamless and natural
   - Score 50-70 if slight mismatch but not immediately obvious
   - Score 0-40 if model clearly looks "pasted on" due to lighting difference

8. **ground_contact**: Is the model properly grounded in the scene? CHECK SHADOWS.
   - Check: does the model cast a SHADOW on the ground matching the background light direction?
   - Check: is the shadow DIRECTION consistent with other shadows in the scene?
   - Check: is shadow SOFTNESS appropriate? (harsh sun = hard shadow, overcast = soft shadow)
   - Check: does the model's feet make REALISTIC CONTACT with the ground? No gap or floating?
   - Score 0-30 if shadow missing, wrong direction, or model appears to float
   - Score 50-70 if shadow exists but doesn't match scene lighting
   - Score 90-100 ONLY if ground contact and shadows are perfectly integrated

9. **edge_quality**: Are the edges around the person seamless? CHECK FOR COMPOSITING ARTIFACTS.
   - Check: any visible HALO, glow, or bright/dark fringe around the model outline?
   - Check: any COLOR BLEEDING between model and background at the boundary?
   - Check: is HAIR properly blended? (hair edges are hardest - look carefully)
   - Check: any jagged or unnaturally sharp/clean edges that look like a cutout?
   - Score 0-40 if obvious halo or fringing visible
   - Score 50-70 if mostly clean but some artifacts on close inspection
   - Score 90-100 ONLY if edges are indistinguishable from real photograph

10. **perspective_match**: Does the camera perspective match? CHECK SPATIAL DEPTH.
   - Check: does the model appear to EXIST INSIDE the 3D space, or look like a flat cutout?
   - Check: is the camera angle consistent between model and background?
   - Check: does DEPTH feel natural? Is atmospheric perspective consistent?
   - Check: does the model's SCALE relative to background elements make spatial sense?
   - Score 0-40 if model looks like a 2D cutout pasted onto 3D background
   - Score 50-70 if depth slightly off but passable
   - Score 90-100 ONLY if spatial integration is seamless

For any score below threshold, provide DETAILED DESCRIPTION for fixing:

Return ONLY valid JSON:
{
  "scores": {
    "pose_match": <0-100>,
    "face_match": <0-100>,
    "scale_match": <0-100>,
    "physics_plausibility": <0-100>,
    "clothing_match": <0-100>,
    "prop_style_consistency": <0-100>,
    "lighting_match": <0-100>,
    "ground_contact": <0-100>,
    "edge_quality": <0-100>,
    "perspective_match": <0-100>
  },
  "issues": ["POSE_MISMATCH", "FACE_CHANGED", "SCALE_SHRUNK", "PHYSICS_ERROR", "PHYSICS_INCOMPATIBLE", "CLOTHING_CHANGED", "PROP_STYLE_MISMATCH", "LIGHTING_MISMATCH", "GROUND_POOR", "EDGE_ARTIFACTS", "PERSPECTIVE_MISMATCH"],
  "pose_description": "Detailed description of the ORIGINAL pose: e.g., 'Both arms raised above head, hands touching the top of the black beanie, elbows bent outward, fingers spread...'",
  "face_description": "Description of face: e.g., 'Slight smile, mouth slightly open, looking directly at camera, head tilted 5 degrees right...'",
  "clothing_description": "Detailed clothing: e.g., 'Pink zip-up jacket with dark blue NY Yankees logo on left chest, black inner top visible at neckline...'",
  "physics_requirement": "What background needs: e.g., 'Model is standing freely, no support needed' or 'Model is leaning left, needs wall or pillar on left side'",
  "frame_description": "Framing: e.g., 'Close-up shot, model fills 90% of frame vertically, cropped at waist level...'",
  "lighting_description": "Lighting analysis: e.g., 'Background has hard directional sunlight from upper-right but model has flat studio lighting with no matching shadows. Model skin appears grey/desaturated.'",
  "ground_description": "Ground contact analysis: e.g., 'Model casts no shadow on ground. Background shadows point to lower-left but model has no corresponding shadow. Feet appear to float.'",
  "edge_description": "Edge quality analysis: e.g., 'Visible white halo around model hair. Color fringing on left shoulder. Hair edges look hard-cut rather than natural.'",
  "perspective_description": "Perspective analysis: e.g., 'Model appears as flat 2D cutout. Background has receding depth but model has no atmospheric perspective. Scale feels wrong relative to doorway.'"
}"""


PROP_ANALYSIS_PROMPT = """You are an expert at analyzing props and furniture in fashion photography.

Analyze this image and identify any PROPS the model is interacting with (sitting on, leaning against, holding, standing near).

A "prop" is any object the model physically contacts or relies on for their pose:
- Chairs, stools, benches, ledges, steps
- Tables, counters, bars
- Walls, pillars, railings, posts
- Vehicles (cars, motorcycles)
- Other objects (boxes, crates, suitcases)

For each prop found, describe:
1. **prop_type**: What is it? (e.g., "wooden bar stool", "metal folding chair", "concrete ledge")
2. **prop_style**: Visual style (e.g., "industrial", "vintage", "modern minimalist", "rustic", "luxury")
3. **prop_material**: Material appearance (e.g., "wood", "metal", "concrete", "leather", "plastic")
4. **prop_color**: Color/finish (e.g., "matte black", "natural wood", "white painted")
5. **interaction_type**: How the model uses it (e.g., "sitting on", "leaning against", "arm resting on", "standing next to")
6. **is_removable**: Can this prop be swapped for a different style without breaking the pose? (true/false)
7. **swap_constraints**: If removable, what must the replacement have? (e.g., "same seat height ~75cm", "flat surface to lean on")

If NO props detected (model is standing freely), return empty props list.

Return ONLY valid JSON:
{
  "props_detected": true/false,
  "props": [
    {
      "prop_type": "wooden bar stool",
      "prop_style": "industrial",
      "prop_material": "metal and wood",
      "prop_color": "matte black frame, natural wood seat",
      "interaction_type": "sitting on",
      "is_removable": true,
      "swap_constraints": "Must be a seat at approximately the same height, model's legs are crossed"
    }
  ],
  "pose_type": "sitting/standing/leaning/crouching",
  "overall_style_recommendation": "For background swap, props should match: [style keywords that fit the detected props]"
}"""


class IssueDiagnoser:
    """실패 원인 진단기"""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def diagnose(self, original_path: str, generated_path: str, api_key: str) -> Dict[str, Any]:
        """실패 원인 진단 및 보강 정보 추출"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        original_bytes = ImageUtils.load_image(original_path, self.config.max_image_size)
        generated_bytes = ImageUtils.load_image(generated_path, self.config.max_image_size)

        try:
            response = client.models.generate_content(
                model=self.config.vision_model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=DIAGNOSIS_PROMPT),
                    types.Part(text="ORIGINAL IMAGE:"),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=original_bytes)),
                    types.Part(text="FAILED GENERATED IMAGE:"),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=generated_bytes)),
                ])],
                config=types.GenerateContentConfig(temperature=0.1)
            )

            result_text = response.candidates[0].content.parts[0].text
            result = ImageUtils.parse_json(result_text)

            # 이슈 자동 판별
            if result.get("scores"):
                result["issues"] = self._detect_issues(result["scores"])

            return result

        except Exception as e:
            return {
                "error": str(e),
                "scores": {},
                "issues": []
            }

    def analyze_original_only(self, original_path: str, api_key: str) -> Dict[str, Any]:
        """원본 이미지만 분석 (사전 분석용)"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        original_bytes = ImageUtils.load_image(original_path, self.config.max_image_size)

        analyze_prompt = """Analyze this fashion photo in detail for AI image generation guidance.

Describe:
1. **pose_description**: Exact pose - arm positions, hand positions, leg stance, body angle, head tilt
2. **face_description**: Expression, mouth state, eye direction, any distinctive features
3. **clothing_description**: All garments, colors, logos, text, patterns, accessories
4. **physics_requirement**: Does the pose require any support (wall, chair, etc.)?
5. **frame_description**: How the subject is framed (close-up, full body, crop position)

Return ONLY valid JSON:
{
  "pose_description": "...",
  "face_description": "...",
  "clothing_description": "...",
  "physics_requirement": "...",
  "frame_description": "..."
}"""

        try:
            response = client.models.generate_content(
                model=self.config.vision_model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=analyze_prompt),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=original_bytes)),
                ])],
                config=types.GenerateContentConfig(temperature=0.1)
            )

            result_text = response.candidates[0].content.parts[0].text
            return ImageUtils.parse_json(result_text)

        except Exception as e:
            return {"error": str(e)}

    def analyze_props(self, original_path: str, api_key: str, target_background: str = "") -> Dict[str, Any]:
        """원본 이미지의 소품 분석 및 배경 스타일 매칭 추천"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        original_bytes = ImageUtils.load_image(original_path, self.config.max_image_size)

        # 배경 정보가 있으면 스타일 매칭 요청 추가
        extra_context = ""
        if target_background:
            extra_context = f"""

ADDITIONAL CONTEXT - TARGET BACKGROUND:
The background will be changed to: "{target_background}"

Based on this target background, also provide:
- "style_match_verdict": Does the current prop style match the target background? ("match", "mismatch", "neutral")
- "recommended_replacement": If mismatch, what style of prop would fit better? (e.g., "rustic wooden bench" for a park background)
- "replacement_prompt_snippet": A short prompt instruction for the AI to generate the right prop style.
  Example: "Replace the metal stool with a weathered wooden bench that fits the rustic park setting"
"""

        full_prompt = PROP_ANALYSIS_PROMPT + extra_context

        try:
            response = client.models.generate_content(
                model=self.config.vision_model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=full_prompt),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=original_bytes)),
                ])],
                config=types.GenerateContentConfig(temperature=0.1)
            )

            result_text = response.candidates[0].content.parts[0].text
            return ImageUtils.parse_json(result_text)

        except Exception as e:
            return {"error": str(e), "props_detected": False, "props": []}

    def analyze_lighting(self, original_path: str, api_key: str) -> Dict[str, Any]:
        """원본 이미지의 모델 조명 특성 사전 분석 (Stage 0용)"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        original_bytes = ImageUtils.load_image(original_path, self.config.max_image_size)

        lighting_prompt = """You are an expert lighting analyst for fashion photography.

Analyze the LIGHTING on the model (person) in this image. Focus ONLY on the light hitting the model's body, face, and clothing - ignore the current background.

Determine:

1. **light_direction**: Primary light source direction relative to the model.
   Examples: "upper-left 45°", "front-center slightly elevated", "right side at eye level", "overhead diffused"

2. **light_type**: Type of lighting.
   - "hard directional" = strong single source, sharp shadows on face/body
   - "soft diffused" = broad even light, gentle shadows
   - "mixed" = combination of hard key + soft fill
   - "flat" = very even, almost shadowless (overcast or ring light)
   - "dramatic" = high contrast, strong shadows

3. **color_temperature**: Estimated color temperature of the light on the model.
   - "warm (3000-4000K)" = golden/warm tones on skin
   - "neutral (4500-5500K)" = natural daylight feel
   - "cool (6000-7500K)" = slightly blue/cool tones
   - "mixed warm-cool" = warm key light with cool fill

4. **shadow_characteristics**: Description of shadows ON the model.
   Examples: "soft shadow under chin falling to lower-right", "hard shadow on left side of face", "minimal shadows, very even lighting"

5. **intensity**: Overall light intensity on the model.
   - "high-key" = bright, well-lit, few dark areas
   - "medium" = balanced highlights and shadows
   - "low-key" = moody, more shadow areas than highlights

6. **skin_tone_appearance**: How the model's skin appears under this lighting.
   Examples: "warm golden skin with natural glow", "neutral tone with slight warmth", "cool-toned with muted colors"

7. **background_lighting_recommendation**: What kind of background lighting would MATCH the model's lighting.
   Be specific! Example: "Background should have overcast sky / diffused natural light from the left. Avoid harsh direct sunlight or dramatic shadows. Ground should show soft diffused shadows, not hard-edged ones."

Return ONLY valid JSON:
{
  "light_direction": "...",
  "light_type": "...",
  "color_temperature": "...",
  "shadow_characteristics": "...",
  "intensity": "...",
  "skin_tone_appearance": "...",
  "background_lighting_recommendation": "..."
}"""

        try:
            response = client.models.generate_content(
                model=self.config.vision_model,
                contents=[types.Content(role="user", parts=[
                    types.Part(text=lighting_prompt),
                    types.Part(inline_data=types.Blob(mime_type="image/png", data=original_bytes)),
                ])],
                config=types.GenerateContentConfig(temperature=0.1)
            )

            result_text = response.candidates[0].content.parts[0].text
            return ImageUtils.parse_json(result_text)

        except Exception as e:
            return {"error": str(e)}

    def _detect_issues(self, scores: Dict[str, int]) -> List[str]:
        """점수 기반 이슈 자동 판별"""
        issues = []

        if scores.get("pose_match", 100) < self.config.pose_match_threshold:
            issues.append("POSE_MISMATCH")

        if scores.get("face_match", 100) < self.config.face_match_threshold:
            issues.append("FACE_CHANGED")

        if scores.get("scale_match", 100) < self.config.scale_match_threshold:
            issues.append("SCALE_SHRUNK")

        physics_score = scores.get("physics_plausibility", 100)
        if physics_score < self.config.physics_threshold:
            issues.append("PHYSICS_ERROR")
        if physics_score < 50:
            issues.append("PHYSICS_INCOMPATIBLE")

        if scores.get("clothing_match", 100) < self.config.clothing_match_threshold:
            issues.append("CLOTHING_CHANGED")

        if scores.get("prop_style_consistency", 100) < self.config.prop_style_threshold:
            issues.append("PROP_STYLE_MISMATCH")

        if scores.get("lighting_match", 100) < self.config.lighting_match_threshold:
            issues.append("LIGHTING_MISMATCH")

        if scores.get("ground_contact", 100) < self.config.ground_contact_threshold:
            issues.append("GROUND_POOR")

        if scores.get("edge_quality", 100) < self.config.edge_quality_threshold:
            issues.append("EDGE_ARTIFACTS")

        if scores.get("perspective_match", 100) < self.config.perspective_match_threshold:
            issues.append("PERSPECTIVE_MISMATCH")

        return issues
