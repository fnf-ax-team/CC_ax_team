"""
MLB Style Library V3 Sampler

Weighted sampling engine for MLB Style Library V3 schema (.claude/skills/brand-dna/mlb-style-library-v3.json).

Features:
- Weighted random sampling from category distributions (pose, framing, expression, etc.)
- Three-tier constraint system (HARD/COMPATIBILITY/PREFERENCE)
- Automatic fallback handling for constraint violations
- Nested prompt_blocks support (e.g., pose.confident_standing.base + arms.hand_in_pocket)
- Optional nested element sampling (random arms/surfaces/positions for poses)

Usage:
    sampler = V3Sampler("path/to/mlb-style-library-v3.json")
    result = sampler.sample_with_constraints(["pose", "expression", "framing", ...])
    prompt = sampler.build_prompt(result.selections, include_nested=True)
    negative = sampler.get_negative_prompt()

Constraint Evaluation Order:
    1. HARD - Must satisfy, resample if violation (max 3 attempts)
    2. COMPATIBILITY - Use fallback if violation (e.g., pose-background compatibility)
    3. PREFERENCE - Warning only, no enforcement (e.g., expression-eyes pairing)
"""

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class SamplingResult:
    """Result of a sampling operation with constraints applied."""
    selections: Dict[str, str]  # category -> selected_id
    prompt_parts: List[str]  # assembled prompt parts
    applied_constraints: List[str]  # constraint names applied
    warnings: List[str]  # warning messages for PREFERENCE violations


class V3Sampler:
    """
    MLB Style Library V3 sampler with weighted distribution and constraint validation.

    Features:
    - Weighted random sampling with avoid/required filters
    - Three-tier constraint system (HARD/COMPATIBILITY/PREFERENCE)
    - Nested prompt_blocks support (e.g., pose.confident_standing.base)
    - Automatic fallback handling
    """

    def __init__(self, style_library_path: str):
        """
        Initialize sampler with style library JSON.

        Args:
            style_library_path: Path to mlb-style-library-v3.json
        """
        self.library_path = Path(style_library_path)
        if not self.library_path.exists():
            raise FileNotFoundError(f"Style library not found: {style_library_path}")

        with open(self.library_path, 'r', encoding='utf-8') as f:
            self.library = json.load(f)

        self.samplers = self.library.get("samplers", {})
        self.prompt_blocks = self.library.get("prompt_blocks", {})
        self.constraints = self.library.get("constraints", {})
        self.negatives = self.library.get("negatives", {})

        logger.info(f"Loaded MLB Style Library V3 from {style_library_path}")
        logger.info(f"Available samplers: {list(self.samplers.keys())}")

    def sample_category(
        self,
        category: str,
        avoid: Optional[List[str]] = None,
        required: Optional[str] = None
    ) -> str:
        """
        Sample a single category with weighted distribution.

        Args:
            category: Sampler category name (e.g., "pose", "framing")
            avoid: List of option IDs to exclude
            required: If specified, return this ID directly (no sampling)

        Returns:
            Selected option ID
        """
        if required:
            return required

        if category not in self.samplers:
            raise ValueError(f"Unknown sampler category: {category}")

        sampler_config = self.samplers[category]
        options = sampler_config.get("options", [])

        if not options:
            fallback = sampler_config.get("default_fallback")
            logger.warning(f"No options in sampler '{category}', using fallback: {fallback}")
            return fallback

        # Filter out avoided options
        avoid = avoid or []
        valid_options = [opt for opt in options if opt["id"] not in avoid]

        if not valid_options:
            fallback = sampler_config.get("default_fallback")
            logger.warning(
                f"All options avoided in '{category}', using fallback: {fallback}"
            )
            return fallback

        # Re-normalize weights
        total_weight = sum(opt["weight"] for opt in valid_options)

        # Weighted random selection
        rand_val = random.random() * total_weight
        cumulative = 0.0

        for opt in valid_options:
            cumulative += opt["weight"]
            if rand_val <= cumulative:
                return opt["id"]

        # Fallback (shouldn't reach here)
        return valid_options[-1]["id"]

    def sample_with_constraints(
        self,
        categories: List[str],
        fixed: Optional[Dict[str, str]] = None
    ) -> SamplingResult:
        """
        Sample multiple categories with constraint validation.

        Args:
            categories: List of category names to sample
            fixed: Pre-selected values to fix (category -> id)

        Returns:
            SamplingResult with selections and validation results
        """
        fixed = fixed or {}
        selections = dict(fixed)
        applied_constraints = []
        warnings = []

        max_attempts = self.constraints.get("_max_resample_attempts", 3)

        for attempt in range(max_attempts):
            # Sample remaining categories
            for category in categories:
                if category not in selections:
                    selections[category] = self.sample_category(category)

            # Validate constraints
            is_valid, constraint_errors = self.validate_combination(selections)

            if is_valid:
                # Build prompt parts
                prompt_parts = self._build_prompt_parts(selections)
                return SamplingResult(
                    selections=selections,
                    prompt_parts=prompt_parts,
                    applied_constraints=applied_constraints,
                    warnings=warnings
                )

            # Handle constraint violations
            selections, applied, warns = self._apply_constraint_fixes(
                selections, constraint_errors
            )
            applied_constraints.extend(applied)
            warnings.extend(warns)

            logger.info(
                f"Constraint validation attempt {attempt + 1}/{max_attempts}: "
                f"applied {len(applied)} fixes"
            )

        # Final attempt failed - use fallbacks
        logger.warning(
            f"Failed to satisfy constraints after {max_attempts} attempts, "
            "using best-effort result"
        )
        prompt_parts = self._build_prompt_parts(selections)

        return SamplingResult(
            selections=selections,
            prompt_parts=prompt_parts,
            applied_constraints=applied_constraints,
            warnings=warnings + ["Failed to fully satisfy all constraints"]
        )

    def validate_combination(
        self,
        selections: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Validate a combination of selections against constraints.

        Args:
            selections: category -> id mapping

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Evaluation order: HARD → COMPATIBILITY → PREFERENCE
        eval_order = self.constraints.get("_evaluation_order", ["HARD", "COMPATIBILITY", "PREFERENCE"])

        for constraint_name, constraint_config in self.constraints.items():
            if constraint_name.startswith("_"):
                continue

            priority = constraint_config.get("priority")
            if priority not in eval_order:
                continue

            rules = constraint_config.get("rules", [])

            for rule in rules:
                if_conditions = rule.get("if", {})
                then_allowed = rule.get("then", {})

                # Check if this rule applies
                if not self._matches_conditions(selections, if_conditions):
                    continue

                # Validate then conditions
                for category, allowed_values in then_allowed.items():
                    if category not in selections:
                        continue

                    current_value = selections[category]

                    if current_value not in allowed_values:
                        error_msg = (
                            f"{priority} constraint '{constraint_name}': "
                            f"{category}={current_value} not allowed when "
                            f"{if_conditions}"
                        )
                        errors.append(error_msg)

        return (len(errors) == 0, errors)

    def _matches_conditions(
        self,
        selections: Dict[str, str],
        conditions: Dict[str, str]
    ) -> bool:
        """Check if selections match all conditions."""
        for category, expected_value in conditions.items():
            if selections.get(category) != expected_value:
                return False
        return True

    def _apply_constraint_fixes(
        self,
        selections: Dict[str, str],
        errors: List[str]
    ) -> Tuple[Dict[str, str], List[str], List[str]]:
        """
        Apply constraint fixes based on error messages and constraint rules.

        Returns:
            (fixed_selections, applied_constraint_names, warnings)
        """
        fixed_selections = dict(selections)
        applied = []
        warnings = []

        # Parse errors and apply fixes
        for error_msg in errors:
            if "PREFERENCE" in error_msg:
                # PREFERENCE: warning only, no fix needed
                warnings.append(error_msg)
                continue

            # For HARD and COMPATIBILITY violations, find the constraint and apply fallback
            for constraint_name, constraint_config in self.constraints.items():
                if constraint_name.startswith("_"):
                    continue

                if constraint_name not in error_msg:
                    continue

                priority = constraint_config.get("priority")
                rules = constraint_config.get("rules", [])

                # Find the matching rule
                for rule in rules:
                    if_conditions = rule.get("if", {})

                    # Check if this rule applies
                    if not self._matches_conditions(fixed_selections, if_conditions):
                        continue

                    # Apply fallback for violating category
                    fallback = rule.get("fallback")
                    then_allowed = rule.get("then", {})

                    for category, allowed_values in then_allowed.items():
                        current_value = fixed_selections.get(category)

                        if current_value and current_value not in allowed_values:
                            # Apply fallback
                            if fallback:
                                fixed_selections[category] = fallback
                                applied.append(f"{priority}_{constraint_name}")
                                logger.debug(
                                    f"Applied {priority} fallback for {category}: "
                                    f"{current_value} -> {fallback}"
                                )
                            else:
                                # No fallback defined, try first allowed value
                                if allowed_values:
                                    fixed_selections[category] = allowed_values[0]
                                    applied.append(f"{priority}_{constraint_name}_first")
                                    logger.debug(
                                        f"Applied {priority} first-allowed for {category}: "
                                        f"{current_value} -> {allowed_values[0]}"
                                    )

        return fixed_selections, applied, warnings

    def _build_prompt_parts(self, selections: Dict[str, str]) -> List[str]:
        """
        Build prompt parts from selections, handling nested structures.

        Args:
            selections: category -> id mapping

        Returns:
            List of prompt strings
        """
        parts = []

        for category, selected_id in selections.items():
            # Navigate nested prompt_blocks structure
            prompt_text = self._get_prompt_block(category, selected_id)

            if prompt_text:
                parts.append(prompt_text)
            else:
                logger.warning(
                    f"No prompt_block found for {category}={selected_id}"
                )

        return parts

    def _get_prompt_block(self, category: str, selected_id: str) -> Optional[str]:
        """
        Retrieve prompt block text, handling nested structures.

        Supports:
        - Direct: prompt_blocks[category][selected_id]
        - Nested: prompt_blocks[pose][confident_standing][base]
                  prompt_blocks[expression][base][cool]
                  prompt_blocks[expression][eyes][large_almond]
                  prompt_blocks[camera][lens][50mm_standard]

        Args:
            category: Sampler category (e.g., "pose", "expression", "lens", "camera_angle")
            selected_id: Selected option ID (e.g., "confident_standing", "cool", "50mm_standard")

        Returns:
            Prompt text or None if not found
        """
        # Category mapping: sampler category -> prompt_blocks path
        category_map = {
            "camera_angle": ("camera", "angle"),
            "lens": ("camera", "lens"),
            "mouth": ("expression", "mouth"),
            "eyes": ("expression", "eyes"),
        }

        # Get the actual prompt_blocks path
        if category in category_map:
            path_parts = category_map[category]
            blocks = self.prompt_blocks

            # Navigate nested path
            for part in path_parts:
                if part not in blocks:
                    return None
                blocks = blocks[part]

            # Now blocks should be the final dict with selected_id
            if isinstance(blocks.get(selected_id), str):
                return blocks[selected_id]
            return None

        # Standard categories
        if category not in self.prompt_blocks:
            return None

        category_blocks = self.prompt_blocks[category]

        # Direct mapping (e.g., framing.MS -> string)
        if isinstance(category_blocks.get(selected_id), str):
            return category_blocks[selected_id]

        # Nested mapping (e.g., pose.confident_standing.base)
        if isinstance(category_blocks.get(selected_id), dict):
            nested = category_blocks[selected_id]

            # Try "base" key first
            if "base" in nested and isinstance(nested["base"], str):
                return nested["base"]

        # For expression.base.cool pattern
        if "base" in category_blocks and isinstance(category_blocks["base"], dict):
            if selected_id in category_blocks["base"]:
                return category_blocks["base"][selected_id]

        return None

    def build_prompt(self, selections: Dict[str, str], include_nested: bool = False) -> str:
        """
        Build a complete prompt from selections.

        Args:
            selections: category -> id mapping
            include_nested: If True, add random nested elements (e.g., arms for pose)

        Returns:
            Assembled prompt string
        """
        parts = self._build_prompt_parts(selections)

        # Optionally add nested elements
        if include_nested:
            nested_parts = self._sample_nested_elements(selections)
            parts.extend(nested_parts)

        return ", ".join(parts)

    def _sample_nested_elements(self, selections: Dict[str, str]) -> List[str]:
        """
        Sample nested elements for categories that have sub-options.

        For example, if pose=confident_standing, randomly sample an arms variation.

        Args:
            selections: Current selections

        Returns:
            List of additional prompt parts
        """
        nested_parts = []

        # Handle pose arms/surfaces/positions
        if "pose" in selections:
            pose_id = selections["pose"]

            if pose_id in self.prompt_blocks.get("pose", {}):
                pose_blocks = self.prompt_blocks["pose"][pose_id]

                # Sample arms for confident_standing
                if "arms" in pose_blocks and isinstance(pose_blocks["arms"], dict):
                    arms_options = list(pose_blocks["arms"].keys())
                    selected_arm = random.choice(arms_options)
                    nested_parts.append(pose_blocks["arms"][selected_arm])

                # Sample surfaces for relaxed_lean
                if "surfaces" in pose_blocks and isinstance(pose_blocks["surfaces"], dict):
                    surface_options = list(pose_blocks["surfaces"].keys())
                    selected_surface = random.choice(surface_options)
                    nested_parts.append(pose_blocks["surfaces"][selected_surface])

                # Sample positions for seated
                if "positions" in pose_blocks and isinstance(pose_blocks["positions"], dict):
                    position_options = list(pose_blocks["positions"].keys())
                    selected_position = random.choice(position_options)
                    nested_parts.append(pose_blocks["positions"][selected_position])

                # Sample variations for dynamic_walk
                if "variations" in pose_blocks and isinstance(pose_blocks["variations"], dict):
                    variation_options = list(pose_blocks["variations"].keys())
                    selected_variation = random.choice(variation_options)
                    nested_parts.append(pose_blocks["variations"][selected_variation])

        return nested_parts

    def get_negative_prompt(self) -> str:
        """
        Get the global negative prompt template.

        Returns:
            Negative prompt string
        """
        return self.negatives.get("negative_prompt_template", "")


def test_sampler():
    """Simple test function for V3Sampler."""
    import os

    # Find style library
    script_dir = Path(__file__).parent
    library_path = script_dir.parent / ".claude" / "skills" / "brand-dna" / "mlb-style-library-v3.json"

    if not library_path.exists():
        logger.error(f"Style library not found: {library_path}")
        return

    # Initialize sampler
    sampler = V3Sampler(str(library_path))

    # Test sampling
    categories = ["pose", "expression", "mouth", "eyes", "framing", "lens", "camera_angle", "background", "lighting", "color_grade"]

    logger.info("=== Testing V3Sampler ===")

    for i in range(3):
        logger.info(f"\n--- Sample {i + 1} ---")
        result = sampler.sample_with_constraints(categories)

        logger.info(f"Selections: {result.selections}")
        logger.info(f"Applied constraints: {result.applied_constraints}")
        logger.info(f"Warnings: {result.warnings}")

        # Test both with and without nested elements
        prompt_basic = sampler.build_prompt(result.selections, include_nested=False)
        prompt_nested = sampler.build_prompt(result.selections, include_nested=True)

        logger.info(f"Basic Prompt:\n{prompt_basic}")
        if prompt_basic != prompt_nested:
            logger.info(f"With Nested:\n{prompt_nested}")

    logger.info(f"\nNegative prompt:\n{sampler.get_negative_prompt()}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_sampler()
