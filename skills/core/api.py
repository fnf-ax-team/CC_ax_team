"""
Core API module for Gemini API interactions.

This module provides centralized functions for:
- Image generation via Gemini
- Vision analysis (VLM) via Gemini
- Proper error handling and retries
- Configuration management from core.config
"""

import base64
import io
import os
import time
from pathlib import Path
from typing import Optional, Union, List, Any

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL, VISION_MODEL


# ============================================================
# Exception Classes
# ============================================================

class APIError(Exception):
    """Base exception for API-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    def __init__(self, message: str):
        super().__init__(message, error_code="RATE_LIMIT", retryable=True)


class AuthenticationError(APIError):
    """Authentication error."""
    def __init__(self, message: str):
        super().__init__(message, error_code="AUTH_ERROR", retryable=False)


class SafetyBlockError(APIError):
    """Safety filter blocked the request."""
    def __init__(self, message: str):
        super().__init__(message, error_code="SAFETY_BLOCK", retryable=False)


# ============================================================
# API Key Management
# ============================================================

def _get_api_keys() -> List[str]:
    """Get all available API keys from environment."""
    api_key_str = os.getenv("GEMINI_API_KEY", "")
    keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
    if not keys:
        raise AuthenticationError("No GEMINI_API_KEY found in environment")
    return keys


_api_key_index = 0
_api_keys = None


def _get_next_api_key() -> str:
    """Get next API key using round-robin strategy."""
    global _api_keys, _api_key_index

    if _api_keys is None:
        _api_keys = _get_api_keys()

    key = _api_keys[_api_key_index]
    _api_key_index = (_api_key_index + 1) % len(_api_keys)
    return key


# ============================================================
# Helper Functions
# ============================================================

def _load_image(image_input: Union[str, Path, Image.Image], max_size: int = 2048) -> Image.Image:
    """
    Load and optionally resize an image.

    Args:
        image_input: Path to image file or PIL Image
        max_size: Maximum dimension (width or height)

    Returns:
        PIL Image in RGB mode
    """
    if isinstance(image_input, Image.Image):
        img = image_input
    else:
        img = Image.open(image_input)

    # Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if needed
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    return img


def _pil_to_part(img: Image.Image, format: str = "JPEG", quality: int = 90) -> types.Part:
    """
    Convert PIL Image to Gemini Part object.

    Args:
        img: PIL Image object
        format: Image format (JPEG or PNG)
        quality: JPEG quality (1-100)

    Returns:
        types.Part with inline image data
    """
    buf = io.BytesIO()
    img.save(buf, format=format, quality=quality)

    mime_type = f"image/{format.lower()}"
    return types.Part(inline_data=types.Blob(mime_type=mime_type, data=buf.getvalue()))


def _base64_to_part(image_data: str) -> types.Part:
    """
    Convert base64 encoded image to Gemini Part object.

    Args:
        image_data: Base64 encoded image string

    Returns:
        types.Part with inline image data
    """
    # Decode base64
    img_bytes = base64.b64decode(image_data)

    # Determine mime type from image data
    if img_bytes.startswith(b'\x89PNG'):
        mime_type = "image/png"
    elif img_bytes.startswith(b'\xff\xd8\xff'):
        mime_type = "image/jpeg"
    elif img_bytes.startswith(b'RIFF') and b'WEBP' in img_bytes[:12]:
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"  # Default fallback

    return types.Part(inline_data=types.Blob(mime_type=mime_type, data=img_bytes))


# ============================================================
# Vision API (VLM)
# ============================================================

def call_gemini_vision(
    prompt: str,
    image_data: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_retries: int = 3
) -> str:
    """
    Call Gemini Vision API for image analysis.

    Args:
        prompt: Analysis prompt
        image_data: Base64 encoded image data
        model: Model to use (defaults to VISION_MODEL from config)
        temperature: Generation temperature (0.0-1.0)
        max_retries: Maximum number of retry attempts

    Returns:
        Text response from the model

    Raises:
        APIError: If API call fails after all retries
        AuthenticationError: If authentication fails
        SafetyBlockError: If content is blocked by safety filters
    """
    model = model or VISION_MODEL

    for attempt in range(max_retries):
        try:
            api_key = _get_next_api_key()
            client = genai.Client(api_key=api_key)

            # Convert base64 image to Part
            image_part = _base64_to_part(image_data)

            # Create content
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        image_part
                    ]
                )
            ]

            # Call API
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature
                )
            )

            # Extract text from response
            if hasattr(response, 'text') and response.text:
                return response.text

            # Fallback: extract from parts
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        return part.text

            raise APIError("No text response received from vision API")

        except Exception as e:
            error_str = str(e).lower()

            # Check for specific error types
            if '429' in error_str or 'rate' in error_str or 'quota' in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                    time.sleep(wait_time)
                    continue
                raise RateLimitError(f"Rate limit exceeded: {e}")

            if '401' in error_str or 'auth' in error_str or 'api key' in error_str:
                raise AuthenticationError(f"Authentication failed: {e}")

            if 'safety' in error_str or 'blocked' in error_str:
                raise SafetyBlockError(f"Content blocked by safety filters: {e}")

            if '503' in error_str or 'overload' in error_str:
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                raise APIError(f"Server overloaded: {e}", error_code="SERVER_ERROR", retryable=True)

            # Generic error
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise APIError(f"Vision API call failed: {e}")

    raise APIError(f"Vision API call failed after {max_retries} attempts")


# ============================================================
# Image Generation API
# ============================================================

def generate_image(
    prompt: str,
    output_path: Union[str, Path],
    model: Optional[str] = None,
    aspect_ratio: str = "3:4",
    negative_prompt: Optional[str] = None,
    temperature: float = 0.3,
    image_size: str = "2K",
    reference_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    max_retries: int = 3
) -> Optional[str]:
    """
    Generate an image using Gemini API and save to file.

    Args:
        prompt: Generation prompt
        output_path: Path to save generated image
        model: Model to use (defaults to IMAGE_MODEL from config)
        aspect_ratio: Image aspect ratio (e.g., "1:1", "3:4", "16:9")
        negative_prompt: Optional negative prompt to avoid certain features
        temperature: Generation temperature (0.0-1.0)
        image_size: Image size ("2K" or "1K")
        reference_images: Optional list of reference images (paths or PIL Images)
        max_retries: Maximum number of retry attempts

    Returns:
        Path to saved image (as string) if successful, None otherwise

    Raises:
        APIError: If generation fails after all retries
        AuthenticationError: If authentication fails
        SafetyBlockError: If content is blocked by safety filters
    """
    model = model or IMAGE_MODEL
    output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build parts list
    parts: List[Any] = []

    # Add reference images first
    if reference_images:
        for i, ref_img in enumerate(reference_images):
            parts.append(f"[Reference Image {i+1}]")
            img = _load_image(ref_img, max_size=2048)
            parts.append(_pil_to_part(img))

    # Add prompt
    full_prompt = prompt
    if negative_prompt:
        full_prompt += f"\n\nDO NOT GENERATE: {negative_prompt}"
    parts.append(full_prompt)

    for attempt in range(max_retries):
        try:
            api_key = _get_next_api_key()
            client = genai.Client(api_key=api_key)

            # Call API
            response = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size
                    )
                )
            )

            # Extract image from response
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # Save image
                        img = Image.open(io.BytesIO(part.inline_data.data))
                        img.save(output_path)
                        return str(output_path)

            raise APIError("No image data in response")

        except Exception as e:
            error_str = str(e).lower()

            # Check for specific error types
            if '429' in error_str or 'rate' in error_str or 'quota' in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                raise RateLimitError(f"Rate limit exceeded: {e}")

            if '401' in error_str or 'auth' in error_str or 'api key' in error_str:
                raise AuthenticationError(f"Authentication failed: {e}")

            if 'safety' in error_str or 'blocked' in error_str:
                raise SafetyBlockError(f"Content blocked by safety filters: {e}")

            if '503' in error_str or 'overload' in error_str:
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                raise APIError(f"Server overloaded: {e}", error_code="SERVER_ERROR", retryable=True)

            # Generic error
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise APIError(f"Image generation failed: {e}")

    return None


# ============================================================
# Batch Generation Helper
# ============================================================

def generate_batch_images(
    prompts: List[str],
    output_dir: Union[str, Path],
    model: Optional[str] = None,
    aspect_ratio: str = "3:4",
    temperature: float = 0.3,
    image_size: str = "2K",
    prefix: str = "generated"
) -> List[Path]:
    """
    Generate multiple images in batch.

    Args:
        prompts: List of generation prompts
        output_dir: Directory to save generated images
        model: Model to use (defaults to IMAGE_MODEL from config)
        aspect_ratio: Image aspect ratio
        temperature: Generation temperature
        image_size: Image size
        prefix: Filename prefix for generated images

    Returns:
        List of paths to successfully generated images
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_paths = []

    for i, prompt in enumerate(prompts):
        output_path = output_dir / f"{prefix}_{i+1:03d}.png"

        try:
            result_path = generate_image(
                prompt=prompt,
                output_path=output_path,
                model=model,
                aspect_ratio=aspect_ratio,
                temperature=temperature,
                image_size=image_size
            )

            if result_path:
                generated_paths.append(Path(result_path))
                print(f"Generated {i+1}/{len(prompts)}: {Path(result_path).name}")
            else:
                print(f"Failed {i+1}/{len(prompts)}")

        except Exception as e:
            print(f"✗ Error {i+1}/{len(prompts)}: {e}")
            continue

    return generated_paths
