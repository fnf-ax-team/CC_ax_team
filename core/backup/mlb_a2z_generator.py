"""
MLB A-to-Z Brandcut Generator

Production-ready class-based module for MLB brand fashion editorial image generation.
Generates images from face + outfit references without target images (true AI-driven editorial).

Author: FNF Studio
Version: 1.0.0
"""

import io
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL, VISION_MODEL


# ============================================================
# Exception Classes
# ============================================================

class MLBGenerationError(Exception):
    """Base exception for MLB generation errors."""
    pass


class APIError(MLBGenerationError):
    """API-related errors (rate limit, authentication, etc.)."""

    def __init__(self, message: str, error_code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


class ValidationError(MLBGenerationError):
    """Validation-related errors."""
    pass


class ConfigurationError(MLBGenerationError):
    """Configuration-related errors."""
    pass


# ============================================================
# Type Definitions
# ============================================================

class EyeAnalysis:
    """Type for eye analysis result."""

    def __init__(self, data: Dict[str, Any]):
        self.eye_size: str = data.get('eye_size', 'large')
        self.eye_openness_percent: int = data.get('eye_openness_percent', 90)
        self.eye_shape: str = data.get('eye_shape', 'almond')
        self.distinctive: str = data.get('distinctive', 'large almond eyes')
        self._raw = data

    def to_dict(self) -> Dict[str, Any]:
        return self._raw


class OutfitAnalysis:
    """Type for outfit analysis result."""

    def __init__(self, data: Dict[str, Any]):
        self.items: List[Dict[str, Any]] = data.get('items', [])
        self.overall_style: str = data.get('overall_style', '')
        self.color_palette: List[str] = data.get('color_palette', [])
        self._raw = data

    def to_dict(self) -> Dict[str, Any]:
        return self._raw


class GenerationResult:
    """Type for generation result."""

    def __init__(
        self,
        preset_id: str,
        image: Optional[Image.Image] = None,
        filepath: Optional[str] = None,
        validation: Optional[Dict[str, Any]] = None,
        success: bool = False,
        error: Optional[str] = None
    ):
        self.preset_id = preset_id
        self.image = image
        self.filepath = filepath
        self.validation = validation
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            'preset_id': self.preset_id,
            'filepath': self.filepath,
            'validation': self.validation,
            'success': self.success,
            'error': self.error
        }


# ============================================================
# Main Generator Class
# ============================================================

class MLBBrandcutGenerator:
    """
    MLB A-to-Z Brandcut Image Generator.

    Generates fashion editorial images from face + outfit references without target images.
    Uses Gemini API for both analysis and generation.

    Attributes:
        api_keys: List of API keys for rotation.
        face_folder: Default folder containing face reference images.
        output_dir: Directory for generated images.
        shot_presets_path: Path to JSON file containing shot presets.
        temperature: Generation temperature (0.0-1.0).
        image_size: Output image size ("1K", "2K", "4K").
        aspect_ratio: Output aspect ratio ("3:4", "4:5", "9:16", etc.).

    Example:
        ```python
        generator = MLBBrandcutGenerator(api_key="your_key_here")
        result = generator.generate_single(
            preset_id="urban_street_confident",
            face_folder="./faces",
            outfit_folder="./outfits"
        )
        ```
    """

    # Director Persona: Tyrone Lebon (The Old Money Rebel)
    DIRECTOR_PERSONA = {
        "name": "Tyrone Lebon",
        "style": "The Old Money Rebel",
        "signature": "완벽하게 통제된 건축물 속에서, 가장 이질적이고 반항적인 에너지를 포착",
        "mantra": "가장 완벽하고 비싼 공간을, 가장 지루해하는 표정으로 장악한다",
        "core_philosophy": "모든 컷은 하이엔드 직광 플래시(Direct Flash)를 사용한 것처럼 연출하라. 그림자는 날카롭고 짙어야 하며, 인물의 얼굴과 옷감에는 서늘한 광택(Specular Highlight)이 감돌아야 한다.",
        "aesthetic_rules": [
            "모델이 화면의 주인공. 시선이 자연스럽게 모델로 가야 함",
            "배경은 모델을 돋보이게 하는 역할. 절대 모델과 경쟁하지 않음",
            "심도(DOF)로 배경 블러 처리 - 모델만 선명, 배경은 부드럽게",
            "배경에 텍스트/간판/로고 등 시선 끄는 요소 배제",
            "차량은 측면/후면 등 그릴(앞면)보다 덜 화려한 각도로",
            "차량 로고/엠블럼이 모델보다 눈에 띄면 안 됨",
            "비싼 차는 모델의 배경이 아니라 모델의 '장난감'이다",
            "깨끗한 인더스트리얼 배경 - 그래피티 없는 완벽한 노출 콘크리트와 유리",
            "오만한 태도 - 이런 비싼 공간쯤은 익숙하다는 듯한 권태로운 표정",
            "카메라를 잡아먹을 듯이 쳐다보거나, 아예 무시하고 딴청을 피우는 시선 처리"
        ],
        "forbidden": [
            "그래피티, 지저분한 배경 (절대 금지)",
            "뻔한 모델 포즈 (손 허리, 45도 서기)",
            "활짝 웃기, 순수한 미소",
            "정자세로 서서 브이(V) 하기",
            "따뜻한 색감, 골든아워, 노을 톤",
            "차량 그릴 정면 클로즈업 (시선 뺏김)",
            "복잡한 그릴 디자인의 차량 (BMW 키드니, Lexus 스핀들 등)",
            "배경이 모델보다 화려한 구도",
            "공손하거나 착해 보이는 포즈",
            "너무 열심히 사는 듯한 역동적인 포즈",
            "가난해 보이는 빈티지 무드"
        ],
        "recommended_vehicles": [
            "Mercedes G-Wagon (G63) - 박시하고 심플한 디자인, 흰색 추천",
            "Range Rover - 클린하고 미니멀한 앞면, 흰색 추천",
            "Land Rover Defender - 클래식하고 심플, 흰색 추천",
            "Porsche Cayenne - 심플한 디자인",
            "Tesla Cybertruck - 극도로 미니멀"
        ],
        "color_grade": [
            "Desaturated cool tones - 채도 낮춘 쿨톤, MLB 시그니처",
            "Teal and steel - 틸 + 스틸 그레이 컬러",
            "Muted pastels - 뮤트된 파스텔, 세련됨",
            "Blue-green shadows - 그림자에 청록 컬러",
            "Lifted blacks, crushed whites - 필름 룩"
        ],
        "lighting": [
            "Hard directional sunlight - 강한 직사광선, 날카로운 그림자와 강렬한 대비 (최우선!)",
            "Harsh midday sun - 정오 직사광, 날카로운 그림자",
            "Cool-neutral color temperature (5600K-6200K)",
            "NO warm/golden tones, NO sunset colors, NO golden hour"
        ]
    }

    # Default shot presets (fallback if JSON not found)
    DEFAULT_PRESETS = [
        {
            "id": "urban_street_confident",
            "temperature": 0.3,
            "pose": "confident standing with slight hip shift, one hand in pocket",
            "expression": "cool neutral, mouth closed, eyes wide open direct gaze",
            "framing": "full body",
            "angle": "20 degrees from right, low angle looking up",
            "background": "urban concrete street, modern architecture, cool daylight",
            "mood": "street luxury, confident swagger"
        },
        {
            "id": "industrial_lean",
            "temperature": 0.3,
            "pose": "leaning against industrial wall, arms crossed",
            "expression": "slightly bored but eyes wide open, subtle smirk",
            "framing": "3/4 body",
            "angle": "25 degrees from left, eye level",
            "background": "raw concrete wall with exposed aggregate, minimal",
            "mood": "effortless cool, rebellious"
        },
        {
            "id": "seated_power",
            "temperature": 0.3,
            "pose": "seated on modern chair, legs crossed, leaning back confidently",
            "expression": "powerful gaze, neutral mouth, eyes wide open",
            "framing": "full body",
            "angle": "frontal with 15 degree tilt, straight on",
            "background": "minimalist studio, white/gray backdrop",
            "mood": "boss energy, controlled power"
        },
        {
            "id": "car_editorial",
            "temperature": 0.3,
            "pose": "leaning on luxury car door, one hand on frame",
            "expression": "detached cool, wide open eyes, neutral lips",
            "framing": "upper body to waist",
            "angle": "15 degrees low angle",
            "background": "luxury SUV/sedan, urban parking, cool tones",
            "mood": "young money, effortless luxury"
        },
        {
            "id": "dynamic_walk",
            "temperature": 0.3,
            "pose": "mid-stride walking, natural arm swing, looking at camera",
            "expression": "confident, eyes wide and alert, slight attitude",
            "framing": "full body",
            "angle": "30 degrees from right, dynamic perspective",
            "background": "city crosswalk or plaza, architectural elements",
            "mood": "on the move, unstoppable"
        },
        {
            "id": "closeup_fierce",
            "temperature": 0.3,
            "pose": "head and shoulders, slight head tilt",
            "expression": "intense direct gaze, LARGE eyes wide open, neutral mouth",
            "framing": "extreme closeup - face and upper chest only",
            "angle": "frontal, slight upward tilt",
            "background": "soft blur, neutral cool tones",
            "mood": "editorial beauty, fierce but approachable"
        },
        {
            "id": "floor_casual",
            "temperature": 0.3,
            "pose": "sitting on floor/ground, one knee up, relaxed",
            "expression": "casual cool, eyes open and relaxed, hint of smile",
            "framing": "full body",
            "angle": "20 degrees, slightly above eye level",
            "background": "studio floor, concrete, minimal props",
            "mood": "relaxed confidence, off-duty model"
        },
        {
            "id": "architectural_frame",
            "temperature": 0.3,
            "pose": "standing in doorway or architectural frame, hands at sides",
            "expression": "mysterious, wide eyes, closed mouth",
            "framing": "full body",
            "angle": "centered but 15 degrees rotated",
            "background": "modern architecture, geometric lines, cool lighting",
            "mood": "editorial high fashion, geometric beauty"
        }
    ]

    def __init__(
        self,
        api_key: str,
        face_folder: Optional[str] = None,
        output_dir: str = "Fnf_studio_outputs/mlb_brandcut/",
        shot_presets_path: str = "skills/fnf-image-gen/prompt-templates/mlb_shot_presets.json",
        config: Optional[Dict[str, Any]] = None,
        temperature: float = 0.3,
        image_size: str = "2K",
        aspect_ratio: str = "3:4"
    ):
        """
        Initialize the MLB Brandcut Generator.

        Args:
            api_key: Single API key or comma-separated list of keys for rotation.
            face_folder: Default folder containing face reference images.
            output_dir: Directory for generated images.
            shot_presets_path: Path to JSON file containing shot presets.
            config: Optional additional configuration dictionary.
            temperature: Generation temperature (0.0-1.0). Lower = more faithful.
            image_size: Output image size ("1K", "2K", "4K").
            aspect_ratio: Output aspect ratio ("3:4", "4:5", "9:16", etc.).

        Raises:
            ConfigurationError: If API key is not provided or invalid.
        """
        # API key management
        if not api_key:
            raise ConfigurationError("API key is required")

        self._api_keys = [k.strip() for k in api_key.split(',') if k.strip()]
        if not self._api_keys:
            raise ConfigurationError("No valid API keys provided")

        self._key_lock = threading.Lock()
        self._current_key_idx = 0

        # Configuration
        self.face_folder = face_folder
        self.output_dir = output_dir
        self.shot_presets_path = shot_presets_path
        self.temperature = temperature
        self.image_size = image_size
        self.aspect_ratio = aspect_ratio

        # Additional config
        self._config = config or {}

        # Cached presets
        self._presets: Optional[List[Dict[str, Any]]] = None
        self._presets_defaults: Optional[Dict[str, Any]] = None

        # Initialize client with first key
        self._client = genai.Client(api_key=self._api_keys[0])

    # ============================================================
    # API Key Management
    # ============================================================

    def _get_next_api_key(self) -> str:
        """
        Get next API key using round-robin rotation (thread-safe).

        Returns:
            Next API key in rotation.
        """
        with self._key_lock:
            key = self._api_keys[self._current_key_idx]
            self._current_key_idx = (self._current_key_idx + 1) % len(self._api_keys)
            return key

    def _refresh_client(self) -> None:
        """Refresh the API client with next key in rotation."""
        self._client = genai.Client(api_key=self._get_next_api_key())

    # ============================================================
    # Preset Management
    # ============================================================

    def load_presets(self) -> List[Dict[str, Any]]:
        """
        Load shot presets from JSON file.

        Returns:
            List of shot preset dictionaries.

        Note:
            Falls back to DEFAULT_PRESETS if JSON file not found.
        """
        if self._presets is not None:
            return self._presets

        try:
            if os.path.exists(self.shot_presets_path):
                with open(self.shot_presets_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._presets = data.get('presets', self.DEFAULT_PRESETS)
                    self._presets_defaults = data.get('defaults', {})
            else:
                self._presets = self.DEFAULT_PRESETS
                self._presets_defaults = {
                    "temperature": 0.3,
                    "aspect_ratio": "3:4",
                    "image_size": "2K"
                }
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load presets from {self.shot_presets_path}: {e}")
            self._presets = self.DEFAULT_PRESETS
            self._presets_defaults = {}

        return self._presets

    def get_preset_by_id(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific preset by its ID.

        Args:
            preset_id: The preset identifier.

        Returns:
            Preset dictionary if found, None otherwise.
        """
        presets = self.load_presets()
        for preset in presets:
            if preset.get('id') == preset_id:
                return preset
        return None

    def get_preset_ids(self) -> List[str]:
        """
        Get list of all available preset IDs.

        Returns:
            List of preset ID strings.
        """
        return [p.get('id', '') for p in self.load_presets() if p.get('id')]

    # ============================================================
    # Image Utilities
    # ============================================================

    @staticmethod
    def _get_images_from_folder(folder: str, max_images: Optional[int] = None) -> List[str]:
        """
        Get image paths from a folder.

        Args:
            folder: Path to folder containing images.
            max_images: Maximum number of images to return.

        Returns:
            List of image file paths.
        """
        exts = {'.jpg', '.jpeg', '.png', '.webp'}
        images = sorted([
            str(f) for f in Path(folder).iterdir()
            if f.suffix.lower() in exts
        ])
        return images[:max_images] if max_images else images

    @staticmethod
    def _load_image_as_pil(path: str) -> Image.Image:
        """
        Load image as PIL Image.

        Args:
            path: Path to image file.

        Returns:
            PIL Image object.
        """
        return Image.open(path)

    @staticmethod
    def _parse_json_response(text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            text: Raw response text.

        Returns:
            Parsed JSON dictionary.
        """
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    # ============================================================
    # Analysis Methods
    # ============================================================

    def analyze_model_eyes(self, face_images: List[str]) -> EyeAnalysis:
        """
        Analyze model's eye characteristics for preservation during generation.

        This is CRITICAL for maintaining the model's signature look.
        Eyes are often the most recognizable feature and must be preserved.

        Args:
            face_images: List of paths to face reference images.

        Returns:
            EyeAnalysis object containing eye characteristics.

        Raises:
            APIError: If API call fails.
            ValidationError: If response cannot be parsed.
        """
        prompt = """Analyze this model's EYE characteristics:

Return ONLY JSON:
{
    "eye_size": "large/medium/small",
    "eye_openness_percent": 90,
    "eye_shape": "almond/round/etc",
    "distinctive": "what makes eyes unique"
}"""

        parts: List[Any] = [prompt]
        for img_path in face_images[:3]:
            parts.append(self._load_image_as_pil(img_path))

        try:
            response = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=parts
            )
            result = self._parse_json_response(response.text)
            return EyeAnalysis(result)

        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse eye analysis response: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'rate' in error_str:
                raise APIError(str(e), error_code="RATE_LIMIT", retryable=True)
            elif '401' in error_str or 'auth' in error_str:
                raise APIError(str(e), error_code="AUTH_ERROR", retryable=False)
            raise APIError(f"Eye analysis failed: {e}")

    def analyze_outfit(self, outfit_images: List[str]) -> OutfitAnalysis:
        """
        Analyze outfit items for accurate reproduction in generated images.

        Args:
            outfit_images: List of paths to outfit reference images.

        Returns:
            OutfitAnalysis object containing outfit details.

        Raises:
            APIError: If API call fails.
            ValidationError: If response cannot be parsed.
        """
        prompt = """Analyze these fashion items for recreation:

Return ONLY JSON:
{
    "items": [
        {
            "category": "top/bottom/outerwear/accessory",
            "name": "item description",
            "color": "main color",
            "details": "logos, patterns, special features",
            "brand_visible": "brand name if visible"
        }
    ],
    "overall_style": "style description",
    "color_palette": ["color1", "color2"]
}"""

        parts: List[Any] = [prompt]
        for img_path in outfit_images[:5]:
            parts.append(self._load_image_as_pil(img_path))

        try:
            response = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=parts
            )
            result = self._parse_json_response(response.text)
            return OutfitAnalysis(result)

        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse outfit analysis response: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'rate' in error_str:
                raise APIError(str(e), error_code="RATE_LIMIT", retryable=True)
            elif '401' in error_str or 'auth' in error_str:
                raise APIError(str(e), error_code="AUTH_ERROR", retryable=False)
            raise APIError(f"Outfit analysis failed: {e}")

    # ============================================================
    # Prompt Building
    # ============================================================

    def _get_director_section(self) -> str:
        """
        Generate director persona prompt section.

        Returns:
            Director vision section for prompt.
        """
        persona = self.DIRECTOR_PERSONA

        aesthetic_rules = "\n".join(f"- {rule}" for rule in persona["aesthetic_rules"])
        forbidden_items = "\n".join(f"- {item}" for item in persona["forbidden"])
        lighting_rules = "\n".join(f"- {light}" for light in persona["lighting"])
        color_rules = "\n".join(f"- {color}" for color in persona["color_grade"])

        return f'''---DIRECTOR VISION---

Style: {persona["style"]}
Signature: {persona["signature"]}
Mantra: "{persona["mantra"]}"

CORE PHILOSOPHY:
{persona["core_philosophy"]}

AESTHETIC RULES:
{aesthetic_rules}

LIGHTING (MLB COOL TONE MANDATORY):
{lighting_rules}

COLOR GRADING (MLB SIGNATURE):
{color_rules}

FORBIDDEN ELEMENTS:
{forbidden_items}

RECOMMENDED VEHICLES (if applicable):
{chr(10).join(f"- {vehicle}" for vehicle in persona["recommended_vehicles"])}
'''

    def build_prompt(
        self,
        shot_preset: Dict[str, Any],
        eye_analysis: Union[EyeAnalysis, Dict[str, Any]],
        outfit_analysis: Union[OutfitAnalysis, Dict[str, Any]]
    ) -> str:
        """
        Build the generation prompt from shot preset and analysis results.

        This prompt is carefully crafted to:
        1. Preserve model's eye characteristics (CRITICAL)
        2. Accurately reproduce outfit items
        3. Maintain cool color temperature (no warm/golden tones)
        4. Execute the shot concept (pose, framing, background)

        Args:
            shot_preset: Shot preset dictionary with pose, expression, etc.
            eye_analysis: Eye analysis result (EyeAnalysis or dict).
            outfit_analysis: Outfit analysis result (OutfitAnalysis or dict).

        Returns:
            Complete generation prompt string.
        """
        # Handle both object and dict inputs
        if isinstance(eye_analysis, EyeAnalysis):
            eye_dict = eye_analysis.to_dict()
        else:
            eye_dict = eye_analysis

        if isinstance(outfit_analysis, OutfitAnalysis):
            outfit_dict = outfit_analysis.to_dict()
        else:
            outfit_dict = outfit_analysis

        eye_openness = eye_dict.get('eye_openness_percent', 90)
        eye_distinctive = eye_dict.get('distinctive', 'large almond eyes')
        eye_size = eye_dict.get('eye_size', 'large')

        # Build outfit description
        outfit_lines = []
        for i, item in enumerate(outfit_dict.get('items', []), 1):
            details = item.get('details', '')
            brand = item.get('brand_visible', '')
            name = item.get('name', 'item')
            color = item.get('color', '')
            outfit_lines.append(
                f"{i}. [MANDATORY] {name} - {color}, {details}, {brand}"
            )
        outfit_str = "\n".join(outfit_lines) if outfit_lines else \
            "Wear the outfit shown in reference images exactly"

        # Get director vision section
        director_section = self._get_director_section()

        prompt = f"""---GENERATION DIRECTIVE---

type: ultra_photorealistic_fashion_editorial
quality: 8k, maximum detail, professional photography
style: MLB Marketing Editorial - Young Money Rebel aesthetic

{director_section}

---SHOT CONCEPT: {shot_preset.get('id', 'custom')}---

This is a CREATIVE GENERATION - no target image, create something fresh and editorial.

---POSE---
{shot_preset.get('pose', 'natural standing pose')}

---CAMERA/FRAMING---
framing: {shot_preset.get('framing', 'full body')}
camera_angle: {shot_preset.get('angle', 'frontal')}

PHYSICAL SETUP (for non-frontal angles):
- If angle specifies "X degrees from right": camera is X degrees to the RIGHT of frontal
- If angle specifies "X degrees from left": camera is X degrees to the LEFT of frontal
- Result: one shoulder appears LARGER (closer), one SMALLER (farther)

---EXPRESSION (CRITICAL - PRESERVE MODEL'S SIGNATURE EYES)---

Overall: {shot_preset.get('expression', 'neutral, confident')}

EYE SPECIFICATIONS (MUST MATCH MODEL REFERENCE):
- Size: {eye_size} - preserve this EXACT size
- Openness: {eye_openness}% open - WIDE OPEN, NOT squinting
- Distinctive: {eye_distinctive}

EXPRESSION BREAKDOWN:
- MOUTH: Creates the "cool" look - neutral, closed, no smile
- EYEBROWS: Relaxed, natural position
- EYES: WIDE OPEN at {eye_openness}% - DO NOT narrow or squint

### COMMON MISTAKES TO AVOID ###
[X] Making eyes smaller to look "cool" or "bored"
[X] Squinting to look "editorial" or "chic"
[X] Half-closing eyes for "sleepy" aesthetic

[O] CORRECT: Cool expression through MOUTH only, LARGE eyes stay LARGE
[O] Think: K-pop idol photoshoot - big eyes, neutral lips

---OUTFIT (MANDATORY - COPY FROM REFERENCE EXACTLY)---
{outfit_str}

CRITICAL: Reproduce ALL items from outfit reference images EXACTLY.
- Preserve all logos, colors, patterns
- Do not substitute or simplify any items
- All visible items must appear in final image

---BACKGROUND---
{shot_preset.get('background', 'urban minimal, neutral tones')}

---MOOD & ATMOSPHERE---
{shot_preset.get('mood', 'confident, editorial')}

---LIGHTING---
- Professional editorial lighting
- Cool-neutral color temperature (5600K-6200K)
- Soft but directional, creating subtle shadows
- NO warm/golden tones

---SKIN---
- Natural skin texture with visible pores
- Subtle imperfections, realistic
- NO plastic/waxy appearance
- NO airbrushed perfection

---FINAL CHECKS (Before Generation)---
1. Model is the clear focal point (not competing with background/vehicle)
2. Background elements are blurred appropriately (shallow DOF)
3. Cool color temperature maintained (5600K-6200K, NO warm tones)
4. Expression: cool through MOUTH, but eyes WIDE OPEN at {eye_openness}%
5. Director's mantra: "완벽한 공간을 지루해하는 표정으로 장악"
6. NO graffiti, NO warm cast, NO squinting
7. If vehicle present: side/rear angle, model is hero not car
8. Clothing items match reference EXACTLY (logos, colors, details)

MLB Marketing - Directed by Tyrone Lebon (The Old Money Rebel)
"""
        return prompt

    # ============================================================
    # Image Generation
    # ============================================================

    def generate_image(
        self,
        prompt: str,
        face_images: List[str],
        outfit_images: List[str],
        temperature: Optional[float] = None,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> Optional[Image.Image]:
        """
        Generate an image using the Gemini API.

        Args:
            prompt: Generation prompt (from build_prompt).
            face_images: List of paths to face reference images.
            outfit_images: List of paths to outfit reference images.
            temperature: Override default temperature (0.0-1.0).
            aspect_ratio: Override default aspect ratio.
            image_size: Override default image size.

        Returns:
            PIL Image if successful, None otherwise.

        Raises:
            APIError: If API call fails after retries.
        """
        temp = temperature if temperature is not None else self.temperature
        ratio = aspect_ratio if aspect_ratio is not None else self.aspect_ratio
        size = image_size if image_size is not None else self.image_size

        parts: List[Any] = [prompt]

        # Face reference (identity + eye preservation)
        parts.append(
            "=== FACE REFERENCE (SAME PERSON - Preserve facial features and EYE SIZE EXACTLY) ==="
        )
        for i, img_path in enumerate(face_images[:4]):
            parts.append(
                f"[Face {i+1}] CRITICAL: Preserve LARGE EYES, WIDE OPEN - this is the model's signature"
            )
            parts.append(self._load_image_as_pil(img_path))

        # Outfit reference
        parts.append(
            "=== OUTFIT REFERENCE (Copy ALL items EXACTLY - logos, colors, details) ==="
        )
        for i, img_path in enumerate(outfit_images[:4]):
            parts.append(f"[Outfit {i+1}]")
            parts.append(self._load_image_as_pil(img_path))

        try:
            response = self._client.models.generate_content(
                model=IMAGE_MODEL,
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=temp,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=ratio,
                        image_size=size
                    )
                )
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return Image.open(io.BytesIO(part.inline_data.data))

            return None

        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'rate' in error_str:
                raise APIError(str(e), error_code="RATE_LIMIT", retryable=True)
            elif '503' in error_str or 'overload' in error_str:
                raise APIError(str(e), error_code="SERVER_OVERLOAD", retryable=True)
            elif '401' in error_str or 'auth' in error_str:
                raise APIError(str(e), error_code="AUTH_ERROR", retryable=False)
            elif 'safety' in error_str or 'blocked' in error_str:
                raise APIError(str(e), error_code="SAFETY_BLOCK", retryable=False)
            raise APIError(f"Image generation failed: {e}")

    # ============================================================
    # Batch Generation Methods
    # ============================================================

    def generate_single(
        self,
        preset_id: str,
        face_folder: str,
        outfit_folder: str,
        output_dir: Optional[str] = None,
        validate: bool = True,
        max_face_images: int = 5,
        max_outfit_images: int = 5,
        custom_prompt_additions: str = ""
    ) -> GenerationResult:
        """
        Generate a single image using a specific preset.

        Args:
            preset_id: ID of the shot preset to use.
            face_folder: Folder containing face reference images.
            outfit_folder: Folder containing outfit reference images.
            output_dir: Override output directory.
            validate: Whether to validate the result.
            max_face_images: Maximum face images to use.
            max_outfit_images: Maximum outfit images to use.
            custom_prompt_additions: Additional prompt text (e.g., from DiversityEngine).

        Returns:
            GenerationResult with image, filepath, validation, etc.

        Raises:
            ConfigurationError: If preset not found.
        """
        preset = self.get_preset_by_id(preset_id)
        if not preset:
            raise ConfigurationError(f"Preset '{preset_id}' not found")

        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        face_images = self._get_images_from_folder(face_folder, max_face_images)
        outfit_images = self._get_images_from_folder(outfit_folder, max_outfit_images)

        if not face_images:
            return GenerationResult(
                preset_id=preset_id,
                success=False,
                error="No face images found"
            )

        if not outfit_images:
            return GenerationResult(
                preset_id=preset_id,
                success=False,
                error="No outfit images found"
            )

        try:
            # Analyze
            eye_analysis = self.analyze_model_eyes(face_images)
            outfit_analysis = self.analyze_outfit(outfit_images)

            # Build prompt
            prompt = self.build_prompt(preset, eye_analysis, outfit_analysis)

            # Append custom prompt additions (e.g., from DiversityEngine)
            if custom_prompt_additions:
                prompt = f"{prompt}\n\n{custom_prompt_additions}"

            # Use preset-specific temperature if available
            temp = preset.get('temperature', self.temperature)

            # Generate
            image = self.generate_image(
                prompt=prompt,
                face_images=face_images,
                outfit_images=outfit_images,
                temperature=temp
            )

            if not image:
                return GenerationResult(
                    preset_id=preset_id,
                    success=False,
                    error="No image generated"
                )

            # Save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"a2z_{preset_id}_{timestamp}.png"
            filepath = os.path.join(out_dir, filename)
            image.save(filepath)

            # Validate if requested
            validation = None
            if validate:
                validation = self.validate_result(
                    generated_img=image,
                    face_images=face_images,
                    outfit_images=outfit_images,
                    shot_preset=preset
                )

            return GenerationResult(
                preset_id=preset_id,
                image=image,
                filepath=filepath,
                validation=validation,
                success=True
            )

        except MLBGenerationError as e:
            return GenerationResult(
                preset_id=preset_id,
                success=False,
                error=str(e)
            )

    def generate_batch(
        self,
        face_folder: str,
        outfit_folder: str,
        output_dir: Optional[str] = None,
        presets: Optional[List[str]] = None,
        validate: bool = True,
        max_face_images: int = 5,
        max_outfit_images: int = 5
    ) -> List[GenerationResult]:
        """
        Generate images for multiple presets.

        Args:
            face_folder: Folder containing face reference images.
            outfit_folder: Folder containing outfit reference images.
            output_dir: Override output directory.
            presets: List of preset IDs to use (None = all presets).
            validate: Whether to validate results.
            max_face_images: Maximum face images to use.
            max_outfit_images: Maximum outfit images to use.

        Returns:
            List of GenerationResult objects.
        """
        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        # Get images once for all presets
        face_images = self._get_images_from_folder(face_folder, max_face_images)
        outfit_images = self._get_images_from_folder(outfit_folder, max_outfit_images)

        if not face_images:
            return [GenerationResult(
                preset_id="batch",
                success=False,
                error="No face images found"
            )]

        if not outfit_images:
            return [GenerationResult(
                preset_id="batch",
                success=False,
                error="No outfit images found"
            )]

        # Analyze once for all presets
        try:
            eye_analysis = self.analyze_model_eyes(face_images)
            outfit_analysis = self.analyze_outfit(outfit_images)
        except MLBGenerationError as e:
            return [GenerationResult(
                preset_id="batch",
                success=False,
                error=f"Analysis failed: {e}"
            )]

        # Get presets to generate
        if presets:
            preset_list = [
                self.get_preset_by_id(pid) for pid in presets
                if self.get_preset_by_id(pid)
            ]
        else:
            preset_list = self.load_presets()

        results: List[GenerationResult] = []

        for i, preset in enumerate(preset_list):
            preset_id = preset.get('id', f'preset_{i}')
            print(f"\n[{i+1}/{len(preset_list)}] Generating: {preset_id}")

            try:
                # Build prompt
                prompt = self.build_prompt(preset, eye_analysis, outfit_analysis)

                # Use preset-specific temperature if available
                temp = preset.get('temperature', self.temperature)

                # Generate (rotate API key for each generation)
                self._refresh_client()
                image = self.generate_image(
                    prompt=prompt,
                    face_images=face_images,
                    outfit_images=outfit_images,
                    temperature=temp
                )

                if not image:
                    results.append(GenerationResult(
                        preset_id=preset_id,
                        success=False,
                        error="No image generated"
                    ))
                    continue

                # Save
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"a2z_{preset_id}_{timestamp}.png"
                filepath = os.path.join(out_dir, filename)
                image.save(filepath)
                print(f"  Saved: {filename}")

                # Validate if requested
                validation = None
                if validate:
                    validation = self.validate_result(
                        generated_img=image,
                        face_images=face_images,
                        outfit_images=outfit_images,
                        shot_preset=preset
                    )
                    print(f"  Score: {validation.get('total_score', 'N/A')}")
                    print(f"  Verdict: {validation.get('verdict', 'N/A')}")

                results.append(GenerationResult(
                    preset_id=preset_id,
                    image=image,
                    filepath=filepath,
                    validation=validation,
                    success=True
                ))

            except MLBGenerationError as e:
                print(f"  Error: {e}")
                results.append(GenerationResult(
                    preset_id=preset_id,
                    success=False,
                    error=str(e)
                ))

        return results

    # ============================================================
    # Validation
    # ============================================================

    def validate_result(
        self,
        generated_img: Image.Image,
        face_images: List[str],
        outfit_images: List[str],
        shot_preset: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a generated image against references and shot concept.

        Args:
            generated_img: The generated PIL Image.
            face_images: List of paths to face reference images.
            outfit_images: List of paths to outfit reference images.
            shot_preset: The shot preset used for generation.

        Returns:
            Validation result dictionary with scores and verdict.
        """
        prompt = f"""Evaluate this AI-generated fashion editorial image.

SHOT CONCEPT: {shot_preset.get('id', 'custom')}
- Intended pose: {shot_preset.get('pose', 'N/A')}
- Intended expression: {shot_preset.get('expression', 'N/A')}
- Intended framing: {shot_preset.get('framing', 'N/A')}
- Intended background: {shot_preset.get('background', 'N/A')}

Score 0-100 for each:

1. photorealism: Does it look like a real photograph?
2. anatomy: Correct human anatomy (fingers, proportions)?
3. face_identity: Same person as face references?
4. eye_preservation: Are eyes LARGE and WIDE OPEN?
5. is_squinting: Are eyes squinting? (true/false)
6. outfit_accuracy: All outfit items present and accurate?
7. pose_execution: Does pose match the concept?
8. expression_execution: Does expression match concept?
9. background_quality: Background appropriate and realistic?
10. color_grading: Cool tones maintained? No warm cast?
11. has_warm_cast: Unwanted warm/golden tones? (true/false)
12. editorial_quality: Does it look like a real MLB campaign photo?

Return ONLY JSON:
{{
    "photorealism": 85,
    "anatomy": 90,
    "face_identity": 95,
    "eye_preservation": 90,
    "is_squinting": false,
    "outfit_accuracy": 85,
    "pose_execution": 80,
    "expression_execution": 85,
    "background_quality": 80,
    "color_grading": 90,
    "has_warm_cast": false,
    "editorial_quality": 85,
    "total_score": 87,
    "issues": ["issue1"],
    "strengths": ["strength1"],
    "verdict": "RELEASE_READY" or "NEEDS_WORK" or "REGENERATE"
}}

Verdict:
- RELEASE_READY: total >= 85, face_identity >= 90, NOT squinting, NOT warm_cast
- NEEDS_WORK: total >= 70 but some issues
- REGENERATE: total < 70 or critical failures"""

        parts: List[Any] = [prompt]
        parts.append("FACE REFERENCES:")
        for img_path in face_images[:2]:
            parts.append(self._load_image_as_pil(img_path))
        parts.append("OUTFIT REFERENCES:")
        for img_path in outfit_images[:2]:
            parts.append(self._load_image_as_pil(img_path))
        parts.append("GENERATED IMAGE:")
        parts.append(generated_img)

        try:
            response = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=parts
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            return {
                "error": str(e),
                "total_score": 0,
                "verdict": "VALIDATION_FAILED"
            }

    # ============================================================
    # Reporting
    # ============================================================

    def generate_report(
        self,
        results: List[GenerationResult],
        eye_analysis: Optional[EyeAnalysis] = None,
        outfit_analysis: Optional[OutfitAnalysis] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Generate a JSON report from batch generation results.

        Args:
            results: List of GenerationResult objects.
            eye_analysis: Optional eye analysis to include.
            outfit_analysis: Optional outfit analysis to include.
            output_dir: Directory to save report (default: self.output_dir).

        Returns:
            Path to the saved report file.
        """
        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        valid_results = [r for r in results if r.success and r.validation]

        summary = {
            "total_shots": len(results),
            "generated": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "release_ready": 0,
            "avg_total_score": 0,
            "avg_face_identity": 0,
            "avg_eye_preservation": 0,
            "squinting_count": 0,
            "warm_cast_count": 0
        }

        if valid_results:
            summary["release_ready"] = sum(
                1 for r in valid_results
                if r.validation and r.validation.get('verdict') == 'RELEASE_READY'
            )
            summary["avg_total_score"] = sum(
                r.validation.get('total_score', 0) for r in valid_results
                if r.validation
            ) / len(valid_results)
            summary["avg_face_identity"] = sum(
                r.validation.get('face_identity', 0) for r in valid_results
                if r.validation
            ) / len(valid_results)
            summary["avg_eye_preservation"] = sum(
                r.validation.get('eye_preservation', 0) for r in valid_results
                if r.validation
            ) / len(valid_results)
            summary["squinting_count"] = sum(
                1 for r in valid_results
                if r.validation and r.validation.get('is_squinting')
            )
            summary["warm_cast_count"] = sum(
                1 for r in valid_results
                if r.validation and r.validation.get('has_warm_cast')
            )

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "A-to-Z (no target image)",
            "eye_analysis": eye_analysis.to_dict() if eye_analysis else None,
            "outfit_analysis": outfit_analysis.to_dict() if outfit_analysis else None,
            "shot_presets": self.load_presets(),
            "results": [r.to_dict() for r in results],
            "summary": summary
        }

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(out_dir, f"a2z_report_{timestamp}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report_path
