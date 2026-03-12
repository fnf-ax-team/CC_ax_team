"""
Product Quality Validator using VLM for multi-criteria assessment.

This module implements a comprehensive product validation system that uses
Vision Language Models to assess product images against multiple quality criteria.
It supports different workflow types (product-design, fabric, styled, shoes-3d) with
customizable validation criteria and thresholds.

Usage:
    validator = ProductValidator()
    result = validator.validate(
        image_path="path/to/image.png",
        workflow_type="product-design",
        custom_criteria=["clarity", "lighting"]
    )

    if result.tier == ProductQualityTier.RELEASE_READY:
        print(f"Image passed validation with score {result.weighted_score}")
    elif result.tier == ProductQualityTier.NEEDS_REVIEW:
        print(f"Image needs review: {result.validation_message}")
    else:
        print(f"Image failed: {result.validation_message}")
"""

import base64
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import re

import google.generativeai as genai
from PIL import Image

from core.config import VISION_MODEL


class ProductQualityTier(Enum):
    """Quality tier classification for product images."""
    RELEASE_READY = "release_ready"  # Score >= 90, all minimum thresholds met
    NEEDS_REVIEW = "needs_review"    # Score 80-89, no auto-fail criteria
    REGENERATE = "regenerate"        # Score < 80 or auto-fail criteria triggered


@dataclass
class ProductValidationThresholds:
    """Configurable thresholds for product validation.

    Attributes:
        total_score_pass: Minimum score to pass validation (default: 85)
        total_score_release: Minimum score for RELEASE_READY tier (default: 90)
        total_score_review: Minimum score for NEEDS_REVIEW tier (default: 80)
        minimum_scores: Dict of criterion -> minimum acceptable score
    """
    total_score_pass: float = 85.0
    total_score_release: float = 90.0
    total_score_review: float = 80.0
    minimum_scores: Dict[str, float] = field(default_factory=lambda: {
        "clarity": 70.0,
        "realism": 75.0,
        "lighting": 70.0,
        "product_accuracy": 80.0,
        "background_quality": 65.0,
        "composition": 70.0,
        "color_accuracy": 75.0,
        "texture_quality": 70.0,
        "anatomy": 75.0,
        "ai_artifacts": 70.0,
    })


@dataclass
class ProductValidationResult:
    """Result of product quality validation.

    Attributes:
        passed: Whether the image passed validation
        tier: Quality tier classification
        weighted_score: Overall weighted quality score (0-100)
        grade: Letter grade (A+, A, B+, B, C, F)
        criteria_scores: Dict of criterion -> score
        criteria_reasons: Dict of criterion -> explanation text
        validation_message: Human-readable summary message
        auto_fail_triggered: Whether any auto-fail criteria were triggered
        auto_fail_reasons: List of auto-fail criterion names
        workflow_type: Type of workflow validated against
        raw_vlm_response: Raw response from VLM (for debugging)
    """
    passed: bool
    tier: ProductQualityTier
    weighted_score: float
    grade: str
    criteria_scores: Dict[str, float]
    criteria_reasons: Dict[str, str]
    validation_message: str
    auto_fail_triggered: bool
    auto_fail_reasons: List[str]
    workflow_type: str
    raw_vlm_response: Optional[str] = None


class ProductValidator:
    """Validates product images using VLM-based multi-criteria assessment.

    This validator supports multiple workflow types with customizable criteria:
    - product-design: General product photography
    - fabric: Fabric texture and drape assessment
    - styled: Styled product shots with models
    - shoes-3d: 3D-rendered shoe products

    Each workflow type has default criteria that can be overridden via
    custom_criteria parameter.
    """

    def __init__(
        self,
        thresholds: Optional[ProductValidationThresholds] = None,
        model_name: Optional[str] = None
    ):
        """Initialize ProductValidator.

        Args:
            thresholds: Custom validation thresholds (uses defaults if None)
            model_name: VLM model name (uses VISION_MODEL from config if None)
        """
        self.thresholds = thresholds or ProductValidationThresholds()
        self.model_name = model_name or VISION_MODEL

        # Configure Gemini API
        genai.configure(api_key=self._get_api_key())
        self.model = genai.GenerativeModel(self.model_name)

    def _get_api_key(self) -> str:
        """Get Google API key from environment or config."""
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment. "
                "Set it via: export GOOGLE_API_KEY='your-key-here'"
            )
        return api_key

    def validate(
        self,
        image_path: str,
        workflow_type: str = "product-design",
        custom_criteria: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> ProductValidationResult:
        """Validate a product image against quality criteria.

        Args:
            image_path: Path to the image file to validate
            workflow_type: Type of workflow ("product-design", "fabric", "styled", "shoes-3d")
            custom_criteria: Optional list of criteria to use (overrides workflow defaults)
            custom_weights: Optional dict of criterion -> weight (must sum to 1.0)

        Returns:
            ProductValidationResult with detailed assessment

        Raises:
            FileNotFoundError: If image_path does not exist
            ValueError: If workflow_type is invalid or weights don't sum to 1.0
        """
        # Validate inputs
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        valid_workflows = ["product-design", "fabric", "styled", "shoes-3d"]
        if workflow_type not in valid_workflows:
            raise ValueError(
                f"Invalid workflow_type '{workflow_type}'. "
                f"Must be one of: {valid_workflows}"
            )

        # Get criteria and weights
        if custom_criteria:
            criteria = custom_criteria
            # Default to equal weights if not provided
            weights = custom_weights or {c: 1.0 / len(criteria) for c in criteria}
        else:
            criteria, weights = self._get_default_criteria(workflow_type)

        # Validate weights sum to 1.0
        weight_sum = sum(weights.values())
        if not (0.99 <= weight_sum <= 1.01):  # Allow small floating point error
            raise ValueError(
                f"Custom weights must sum to 1.0, got {weight_sum}. "
                f"Weights: {weights}"
            )

        # Load image
        image = self._load_image(image_path)

        # Call VLM for validation
        vlm_response = self._call_vlm_validation(image, criteria, workflow_type)

        # Process VLM response
        result = self._process_result(
            vlm_response=vlm_response,
            criteria=criteria,
            weights=weights,
            workflow_type=workflow_type
        )

        return result

    def _get_default_criteria(self, workflow_type: str) -> tuple[List[str], Dict[str, float]]:
        """Get default criteria and weights for a workflow type.

        Args:
            workflow_type: Type of workflow

        Returns:
            Tuple of (criteria_list, weights_dict)
        """
        if workflow_type == "product-design":
            criteria = [
                "clarity",
                "realism",
                "lighting",
                "product_accuracy",
                "background_quality",
                "composition",
                "color_accuracy",
                "ai_artifacts"
            ]
            weights = {
                "clarity": 0.15,
                "realism": 0.15,
                "lighting": 0.12,
                "product_accuracy": 0.20,
                "background_quality": 0.10,
                "composition": 0.10,
                "color_accuracy": 0.10,
                "ai_artifacts": 0.08
            }

        elif workflow_type == "fabric":
            criteria = [
                "clarity",
                "texture_quality",
                "lighting",
                "product_accuracy",
                "color_accuracy",
                "realism",
                "ai_artifacts"
            ]
            weights = {
                "clarity": 0.15,
                "texture_quality": 0.25,
                "lighting": 0.12,
                "product_accuracy": 0.18,
                "color_accuracy": 0.15,
                "realism": 0.10,
                "ai_artifacts": 0.05
            }

        elif workflow_type == "styled":
            criteria = [
                "clarity",
                "realism",
                "lighting",
                "product_accuracy",
                "anatomy",
                "composition",
                "color_accuracy",
                "ai_artifacts"
            ]
            weights = {
                "clarity": 0.12,
                "realism": 0.15,
                "lighting": 0.12,
                "product_accuracy": 0.18,
                "anatomy": 0.15,
                "composition": 0.12,
                "color_accuracy": 0.10,
                "ai_artifacts": 0.06
            }

        elif workflow_type == "shoes-3d":
            criteria = [
                "clarity",
                "realism",
                "lighting",
                "product_accuracy",
                "background_quality",
                "composition",
                "texture_quality",
                "ai_artifacts"
            ]
            weights = {
                "clarity": 0.15,
                "realism": 0.15,
                "lighting": 0.12,
                "product_accuracy": 0.20,
                "background_quality": 0.08,
                "composition": 0.10,
                "texture_quality": 0.15,
                "ai_artifacts": 0.05
            }

        else:
            raise ValueError(f"Unknown workflow_type: {workflow_type}")

        return criteria, weights

    def _load_image(self, image_path: str) -> Image.Image:
        """Load image from path.

        Args:
            image_path: Path to image file

        Returns:
            PIL Image object
        """
        return Image.open(image_path)

    def _call_vlm_validation(
        self,
        image: Image.Image,
        criteria: List[str],
        workflow_type: str
    ) -> str:
        """Call VLM to validate image against criteria.

        Args:
            image: PIL Image to validate
            criteria: List of criteria to assess
            workflow_type: Type of workflow for context

        Returns:
            Raw VLM response text
        """
        # Build criteria descriptions
        criteria_descriptions = {
            "clarity": "Image sharpness and detail resolution (0-100)",
            "realism": "Photorealistic quality and believability (0-100)",
            "lighting": "Natural, consistent lighting without harsh shadows (0-100)",
            "product_accuracy": "Product matches requirements, correct details (0-100)",
            "background_quality": "Background cleanness and appropriateness (0-100)",
            "composition": "Visual balance, framing, and aesthetic appeal (0-100)",
            "color_accuracy": "Color fidelity and consistency (0-100)",
            "texture_quality": "Fabric/material texture realism and detail (0-100)",
            "anatomy": "Human anatomy accuracy (if applicable) (0-100)",
            "ai_artifacts": "Absence of AI artifacts (fingers, text, distortions) (0-100)"
        }

        # Build prompt
        prompt_parts = [
            f"You are a professional product quality inspector validating a {workflow_type} image.",
            "\nPlease assess the image against these criteria and provide scores (0-100) with brief explanations:\n"
        ]

        for criterion in criteria:
            desc = criteria_descriptions.get(criterion, f"{criterion} quality (0-100)")
            prompt_parts.append(f"- {criterion}: {desc}")

        prompt_parts.append(
            "\n\nProvide your response in this exact JSON format:\n"
            "{\n"
            '  "scores": {\n'
            '    "criterion_name": score_number,\n'
            "    ...\n"
            "  },\n"
            '  "reasons": {\n'
            '    "criterion_name": "brief explanation",\n'
            "    ...\n"
            "  }\n"
            "}\n\n"
            "Important:\n"
            "- Scores must be integers 0-100\n"
            "- Be strict: only exceptional images should score above 90\n"
            "- Provide specific, actionable feedback in reasons\n"
            "- Focus on objective quality metrics"
        )

        prompt = "".join(prompt_parts)

        # Call VLM
        response = self.model.generate_content([prompt, image])

        return response.text

    def _process_result(
        self,
        vlm_response: str,
        criteria: List[str],
        weights: Dict[str, float],
        workflow_type: str
    ) -> ProductValidationResult:
        """Process VLM response into ProductValidationResult.

        Args:
            vlm_response: Raw VLM response text
            criteria: List of criteria assessed
            weights: Dict of criterion -> weight
            workflow_type: Type of workflow validated

        Returns:
            ProductValidationResult with all fields populated
        """
        # Parse JSON from VLM response
        try:
            # Try to extract JSON from response (may contain markdown code blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', vlm_response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{.*\}', vlm_response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    raise ValueError("No JSON found in VLM response")

            parsed = json.loads(json_text)
            scores = parsed.get("scores", {})
            reasons = parsed.get("reasons", {})

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: return failed result with error message
            return ProductValidationResult(
                passed=False,
                tier=ProductQualityTier.REGENERATE,
                weighted_score=0.0,
                grade="F",
                criteria_scores={},
                criteria_reasons={},
                validation_message=f"Failed to parse VLM response: {str(e)}",
                auto_fail_triggered=True,
                auto_fail_reasons=["vlm_parse_error"],
                workflow_type=workflow_type,
                raw_vlm_response=vlm_response
            )

        # Convert scores to floats and validate
        criteria_scores = {}
        for criterion in criteria:
            score = scores.get(criterion, 0)
            try:
                criteria_scores[criterion] = float(score)
            except (ValueError, TypeError):
                criteria_scores[criterion] = 0.0

        # Get reasons
        criteria_reasons = {c: reasons.get(c, "No reason provided") for c in criteria}

        # Calculate weighted score
        weighted_score = self._calculate_weighted_score(criteria_scores, weights)

        # Check for auto-fail conditions
        auto_fail_triggered, auto_fail_reasons = self._check_auto_fail(
            criteria_scores,
            self.thresholds.minimum_scores
        )

        # Determine grade and tier
        grade = self._determine_grade(weighted_score)
        tier = self._determine_tier(
            weighted_score,
            auto_fail_triggered,
            self.thresholds
        )

        # Determine if passed
        passed = (
            weighted_score >= self.thresholds.total_score_pass
            and not auto_fail_triggered
        )

        # Build validation message
        if tier == ProductQualityTier.RELEASE_READY:
            validation_message = (
                f"Image passed validation with {grade} grade ({weighted_score:.1f}/100). "
                "Ready for release."
            )
        elif tier == ProductQualityTier.NEEDS_REVIEW:
            validation_message = (
                f"Image scored {grade} grade ({weighted_score:.1f}/100). "
                "Manual review recommended before release."
            )
        else:
            if auto_fail_triggered:
                failed_criteria = ", ".join(auto_fail_reasons)
                validation_message = (
                    f"Image failed validation ({weighted_score:.1f}/100). "
                    f"Critical issues: {failed_criteria}. Regeneration recommended."
                )
            else:
                validation_message = (
                    f"Image scored {grade} grade ({weighted_score:.1f}/100). "
                    "Score below minimum threshold. Regeneration recommended."
                )

        return ProductValidationResult(
            passed=passed,
            tier=tier,
            weighted_score=weighted_score,
            grade=grade,
            criteria_scores=criteria_scores,
            criteria_reasons=criteria_reasons,
            validation_message=validation_message,
            auto_fail_triggered=auto_fail_triggered,
            auto_fail_reasons=auto_fail_reasons,
            workflow_type=workflow_type,
            raw_vlm_response=vlm_response
        )

    def _calculate_weighted_score(
        self,
        scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted average score.

        Args:
            scores: Dict of criterion -> score
            weights: Dict of criterion -> weight

        Returns:
            Weighted average score (0-100)
        """
        total = 0.0
        for criterion, weight in weights.items():
            score = scores.get(criterion, 0.0)
            total += score * weight
        return total

    def _check_auto_fail(
        self,
        scores: Dict[str, float],
        minimum_scores: Dict[str, float]
    ) -> tuple[bool, List[str]]:
        """Check if any scores fall below minimum thresholds.

        Args:
            scores: Dict of criterion -> score
            minimum_scores: Dict of criterion -> minimum acceptable score

        Returns:
            Tuple of (auto_fail_triggered, list_of_failed_criteria)
        """
        failed_criteria = []
        for criterion, min_score in minimum_scores.items():
            if criterion in scores and scores[criterion] < min_score:
                failed_criteria.append(criterion)

        return len(failed_criteria) > 0, failed_criteria

    def _determine_grade(self, score: float) -> str:
        """Determine letter grade from numeric score.

        Args:
            score: Numeric score (0-100)

        Returns:
            Letter grade (A+, A, A-, B+, B, B-, C+, C, C-, D, F)
        """
        if score >= 97:
            return "A+"
        elif score >= 93:
            return "A"
        elif score >= 90:
            return "A-"
        elif score >= 87:
            return "B+"
        elif score >= 83:
            return "B"
        elif score >= 80:
            return "B-"
        elif score >= 77:
            return "C+"
        elif score >= 73:
            return "C"
        elif score >= 70:
            return "C-"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _determine_tier(
        self,
        score: float,
        auto_fail_triggered: bool,
        thresholds: ProductValidationThresholds
    ) -> ProductQualityTier:
        """Determine quality tier from score and auto-fail status.

        Args:
            score: Weighted average score
            auto_fail_triggered: Whether any auto-fail criteria triggered
            thresholds: Validation thresholds

        Returns:
            ProductQualityTier enum value
        """
        if auto_fail_triggered:
            return ProductQualityTier.REGENERATE

        if score >= thresholds.total_score_release:
            return ProductQualityTier.RELEASE_READY
        elif score >= thresholds.total_score_review:
            return ProductQualityTier.NEEDS_REVIEW
        else:
            return ProductQualityTier.REGENERATE


# Example usage
if __name__ == "__main__":
    # Example: Validate a product image
    validator = ProductValidator()

    result = validator.validate(
        image_path="test_product.png",
        workflow_type="product-design"
    )

    print(f"Validation Result:")
    print(f"  Passed: {result.passed}")
    print(f"  Tier: {result.tier.value}")
    print(f"  Score: {result.weighted_score:.1f}/100 ({result.grade})")
    print(f"  Message: {result.validation_message}")
    print(f"\nCriteria Scores:")
    for criterion, score in result.criteria_scores.items():
        reason = result.criteria_reasons[criterion]
        print(f"  {criterion}: {score:.1f}/100 - {reason}")
