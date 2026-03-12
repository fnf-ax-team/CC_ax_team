"""
Product-specific utility functions for FNF Studio.

This module provides utilities for analyzing product images and generating
product-focused AI images with proper configuration management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import base64
from pathlib import Path

from core.config import IMAGE_MODEL, VISION_MODEL, PipelineConfig
from core.api import generate_image as api_generate_image


class ProductCategory(Enum):
    """Product categories for specialized handling."""
    FASHION = "fashion"
    BEAUTY = "beauty"
    ACCESSORIES = "accessories"
    FOOTWEAR = "footwear"
    JEWELRY = "jewelry"
    BAGS = "bags"
    EYEWEAR = "eyewear"
    WATCHES = "watches"
    UNKNOWN = "unknown"


class OutputFormat(Enum):
    """Output format specifications."""
    SQUARE = "1:1"
    PORTRAIT = "3:4"
    LANDSCAPE = "4:3"
    VERTICAL = "9:16"
    HORIZONTAL = "16:9"


@dataclass
class ProductAnalysis:
    """Analysis result from VLM for product images."""
    category: ProductCategory
    attributes: Dict[str, Any]
    colors: List[str]
    materials: List[str]
    style_tags: List[str]
    confidence: float
    raw_response: str


@dataclass
class GenerationResult:
    """Result from image generation."""
    success: bool
    image_path: Optional[str]
    prompt_used: str
    model_used: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


PRODUCT_ANALYSIS_PROMPT = """Analyze this product image and provide a detailed description including:

1. Product Category: Identify the main product type (fashion, beauty, accessories, etc.)
2. Visual Attributes: Describe colors, materials, textures, patterns
3. Style & Aesthetic: Identify the style (casual, formal, luxury, streetwear, etc.)
4. Key Features: Notable design elements, logos, embellishments
5. Context Suitability: Suggest appropriate contexts for featuring this product

Provide your analysis in a structured format with clear categories."""


def analyze_product_image(
    image_path: str,
    custom_prompt: Optional[str] = None
) -> ProductAnalysis:
    """
    Analyze a product image using Vision Language Model.

    Args:
        image_path: Path to the product image file
        custom_prompt: Optional custom analysis prompt (defaults to PRODUCT_ANALYSIS_PROMPT)

    Returns:
        ProductAnalysis object with structured analysis results

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image format is not supported
    """
    from core.api import call_gemini_vision

    # Validate image path
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Read and encode image
    with open(img_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Use custom prompt or default
    prompt = custom_prompt or PRODUCT_ANALYSIS_PROMPT

    # Call VLM (using VISION_MODEL from config)
    response = call_gemini_vision(
        prompt=prompt,
        image_data=image_data,
        model=VISION_MODEL
    )

    # Parse response into structured format
    # This is a simplified parser - real implementation would be more robust
    analysis_text = response.lower()

    # Detect category
    category = ProductCategory.UNKNOWN
    for cat in ProductCategory:
        if cat.value in analysis_text:
            category = cat
            break

    # Extract basic attributes (simplified)
    attributes = {
        "description": response[:200],  # First 200 chars as summary
        "full_analysis": response
    }

    # Extract colors (basic implementation)
    common_colors = ["red", "blue", "green", "black", "white", "pink",
                    "yellow", "purple", "orange", "brown", "gray", "beige"]
    colors = [color for color in common_colors if color in analysis_text]

    # Extract materials (basic implementation)
    common_materials = ["cotton", "leather", "silk", "denim", "wool",
                       "polyester", "metal", "plastic", "gold", "silver"]
    materials = [mat for mat in common_materials if mat in analysis_text]

    # Extract style tags (basic implementation)
    style_keywords = ["casual", "formal", "luxury", "streetwear", "vintage",
                     "modern", "classic", "sporty", "elegant", "minimalist"]
    style_tags = [style for style in style_keywords if style in analysis_text]

    return ProductAnalysis(
        category=category,
        attributes=attributes,
        colors=colors or ["unknown"],
        materials=materials or ["unknown"],
        style_tags=style_tags or ["general"],
        confidence=0.85,  # Placeholder - real implementation would calculate this
        raw_response=response
    )


def generate_product_image(
    prompt: str,
    output_path: str,
    product_analysis: Optional[ProductAnalysis] = None,
    aspect_ratio: OutputFormat = OutputFormat.SQUARE,
    negative_prompt: Optional[str] = None,
    config: Optional[PipelineConfig] = None
) -> GenerationResult:
    """
    Generate product-focused image using IMAGE_MODEL from config.

    Args:
        prompt: Text prompt for image generation
        output_path: Path where generated image will be saved
        product_analysis: Optional ProductAnalysis to enhance prompt
        aspect_ratio: Desired output format (default: square)
        negative_prompt: Optional negative prompt for quality control
        config: Optional PipelineConfig override (defaults to config.IMAGE_MODEL)

    Returns:
        GenerationResult with success status and metadata
    """
    try:
        # Enhance prompt with product analysis if available
        enhanced_prompt = prompt
        if product_analysis:
            style_context = ", ".join(product_analysis.style_tags)
            color_context = ", ".join(product_analysis.colors[:3])  # Top 3 colors
            enhanced_prompt = f"{prompt}, {style_context} style, featuring {color_context} tones"

        # Determine model to use (config override or default from core.config)
        model_to_use = config.image_model if config else IMAGE_MODEL

        # Set default negative prompt if not provided
        default_negative = "low quality, blurry, distorted, watermark, text, logo"
        final_negative = negative_prompt or default_negative

        # Call image generation API
        result_path = api_generate_image(
            prompt=enhanced_prompt,
            output_path=output_path,
            model=model_to_use,
            aspect_ratio=aspect_ratio.value,
            negative_prompt=final_negative
        )

        # Build metadata
        metadata = {
            "model": model_to_use,
            "aspect_ratio": aspect_ratio.value,
            "enhanced": product_analysis is not None
        }

        if product_analysis:
            metadata["product_category"] = product_analysis.category.value
            metadata["style_tags"] = product_analysis.style_tags

        return GenerationResult(
            success=True,
            image_path=result_path,
            prompt_used=enhanced_prompt,
            model_used=model_to_use,
            metadata=metadata
        )

    except Exception as e:
        return GenerationResult(
            success=False,
            image_path=None,
            prompt_used=enhanced_prompt if 'enhanced_prompt' in locals() else prompt,
            model_used=model_to_use if 'model_to_use' in locals() else IMAGE_MODEL,
            error=str(e)
        )
