"""
Style Library Adapter - V2/V3 Compatibility Layer

Provides seamless integration between:
- V2 Style Library (DiversityEngine) - legacy format
- V3 Style Library (V3Sampler) - new 5-layer schema

Features:
- Automatic version detection based on schema structure
- V3 → V2 result conversion for backward compatibility
- V2 → V3 interface wrapping (optional)
- Safe imports with graceful fallback

Usage:
    # Auto-detect and load
    engine = StyleLibraryAdapter.load("path/to/style-library.json")

    # Convert V3 result to V2 format
    v2_combo = StyleLibraryAdapter.to_diversity_combo(v3_result)

    # Check version
    is_v3 = StyleLibraryAdapter.is_v3_schema("path/to/style-library.json")
"""

import json
import logging
from pathlib import Path
from typing import Union, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import V3Sampler
try:
    from core.v3_sampler import V3Sampler, SamplingResult
    V3_AVAILABLE = True
except ImportError:
    V3_AVAILABLE = False
    V3Sampler = None
    SamplingResult = None
    logger.warning("V3Sampler not available")

# Import DiversityEngine with exception handling
try:
    from core.diversity_engine import DiversityEngine, DiversityCombination
    V2_AVAILABLE = True
except ImportError:
    V2_AVAILABLE = False
    DiversityEngine = None
    DiversityCombination = None
    logger.warning("DiversityEngine not available")


class StyleLibraryAdapter:
    """
    V2 ↔ V3 Style Library Compatibility Adapter

    Provides backward compatibility and unified interface for both
    legacy (DiversityEngine) and new (V3Sampler) style libraries.

    Version Detection:
    - V3: JSON contains "samplers" AND "constraints" keys
    - V2: Everything else
    """

    @staticmethod
    def is_v3_schema(path: str) -> bool:
        """
        Detect if style library is V3 schema.

        V3 Detection Criteria:
        - Must have "samplers" key
        - Must have "constraints" key

        Args:
            path: Path to style library JSON file

        Returns:
            True if V3 schema, False if V2 or error
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                logger.error(f"Style library not found: {path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # V3 must have both samplers and constraints
            has_samplers = "samplers" in data
            has_constraints = "constraints" in data

            is_v3 = has_samplers and has_constraints

            logger.info(
                f"Schema detection for {file_path.name}: "
                f"V{'3' if is_v3 else '2'} "
                f"(samplers={has_samplers}, constraints={has_constraints})"
            )

            return is_v3

        except Exception as e:
            logger.error(f"Error detecting schema version: {e}")
            return False

    @staticmethod
    def load(path: str) -> Union['V3Sampler', 'DiversityEngine']:
        """
        Load style library with automatic version detection.

        Returns appropriate engine based on schema:
        - V3 schema → V3Sampler
        - V2 schema → DiversityEngine

        Args:
            path: Path to style library JSON file

        Returns:
            V3Sampler or DiversityEngine instance

        Raises:
            ImportError: If required engine class not available
            FileNotFoundError: If style library file doesn't exist
        """
        if not Path(path).exists():
            raise FileNotFoundError(f"Style library not found: {path}")

        is_v3 = StyleLibraryAdapter.is_v3_schema(path)

        if is_v3:
            if not V3_AVAILABLE:
                raise ImportError(
                    "V3 schema detected but V3Sampler not available. "
                    "Check core/v3_sampler.py import."
                )

            logger.info(f"Loading V3 Style Library: {path}")
            return V3Sampler(path)

        else:
            if not V2_AVAILABLE:
                raise ImportError(
                    "V2 schema detected but DiversityEngine not available. "
                    "Check core/diversity_engine.py import."
                )

            logger.info(f"Loading V2 Style Library: {path}")
            return DiversityEngine(path)

    @staticmethod
    def to_diversity_combo(v3_result: 'SamplingResult') -> 'DiversityCombination':
        """
        Convert V3 SamplingResult to V2 DiversityCombination.

        Enables backward compatibility by translating V3 sampling results
        into V2 format expected by existing pipelines.

        Field Mapping:
        - framing: Direct mapping (MS, MCU, MFS, CU)
        - lens: Maps camera.lens (50mm_standard → "50mm")
        - angle: Extracts degrees from camera_angle selection
        - pose: Direct mapping (confident_standing, relaxed_lean, etc.)
        - background: Wraps in dict with "id" key
        - reference_entry: None (V3 doesn't use reference entries)

        Args:
            v3_result: SamplingResult from V3Sampler

        Returns:
            DiversityCombination compatible with V2 pipelines

        Raises:
            ImportError: If DiversityCombination not available
        """
        if not V2_AVAILABLE:
            raise ImportError(
                "Cannot convert to DiversityCombination: "
                "core.diversity_engine not available"
            )

        selections = v3_result.selections

        # Extract framing (direct)
        framing = selections.get("framing", "MS")

        # Extract lens (remove _standard/_wide/_tele suffix)
        lens_raw = selections.get("lens", "50mm_standard")
        lens = lens_raw.split("_")[0]  # "50mm_standard" → "50mm"

        # Extract angle (parse degrees from camera_angle)
        angle_raw = selections.get("camera_angle", "frontal")
        angle = StyleLibraryAdapter._parse_angle(angle_raw)

        # Extract pose (direct)
        pose = selections.get("pose", "confident_standing")

        # Extract background (wrap in dict)
        background_id = selections.get("background", "metal_panel")
        background = {"id": background_id}

        combo = DiversityCombination(
            framing=framing,
            lens=lens,
            angle=angle,
            pose=pose,
            background=background,
            reference_entry=None  # V3 doesn't use reference entries
        )

        logger.debug(
            f"Converted V3→V2: framing={framing}, lens={lens}, "
            f"angle={angle}, pose={pose}, background={background_id}"
        )

        return combo

    @staticmethod
    def _parse_angle(camera_angle_id: str) -> int:
        """
        Parse camera angle ID to degrees.

        Mapping:
        - frontal → 0
        - 3_4_profile → 15
        - side_profile → 30
        - slight_angle → 10
        - slight_low → 0 (fallback, angle is about height not rotation)

        Args:
            camera_angle_id: V3 camera_angle selection ID

        Returns:
            Angle in degrees (0, 10, 15, 30)
        """
        angle_map = {
            "frontal": 0,
            "3_4_profile": 15,
            "side_profile": 30,
            "slight_angle": 10,
            "slight_low": 0,  # Height angle, not rotation
        }

        return angle_map.get(camera_angle_id, 0)

    @staticmethod
    def wrap_v2_engine(engine: 'DiversityEngine') -> 'V3SamplerInterface':
        """
        Wrap V2 DiversityEngine with V3-compatible interface.

        Optional feature for unified interface across V2/V3.
        Returns a thin wrapper that translates V3-style calls to V2 methods.

        Args:
            engine: DiversityEngine instance

        Returns:
            V3SamplerInterface wrapper

        Note:
            Not implemented yet - reserved for future use if needed.
            Current pipelines can use V2 and V3 separately via load().
        """
        raise NotImplementedError(
            "V2→V3 wrapping not yet implemented. "
            "Use StyleLibraryAdapter.load() for automatic detection instead."
        )


def test_adapter():
    """Test StyleLibraryAdapter with both V2 and V3 libraries."""
    import sys
    from pathlib import Path

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Find test files
    project_root = Path(__file__).parent.parent
    v2_path = project_root / ".claude" / "skills" / "brand-dna" / "mlb-style-library.json"
    v3_path = project_root / ".claude" / "skills" / "brand-dna" / "mlb-style-library-v3.json"

    logger.info("=== Testing StyleLibraryAdapter ===")

    # Test V2 detection
    if v2_path.exists():
        logger.info(f"\nTesting V2 library: {v2_path}")
        is_v3 = StyleLibraryAdapter.is_v3_schema(str(v2_path))
        logger.info(f"Is V3? {is_v3} (expected: False)")

        try:
            engine = StyleLibraryAdapter.load(str(v2_path))
            logger.info(f"Loaded: {type(engine).__name__}")

            # Test V2 functionality
            if isinstance(engine, DiversityEngine):
                combo = engine.select_combination(batch_index=0, total_batch=10)
                logger.info(f"V2 combo: framing={combo.framing}, pose={combo.pose}")
        except Exception as e:
            logger.error(f"V2 test error: {e}")
    else:
        logger.warning(f"V2 library not found: {v2_path}")

    # Test V3 detection
    if v3_path.exists():
        logger.info(f"\nTesting V3 library: {v3_path}")
        is_v3 = StyleLibraryAdapter.is_v3_schema(str(v3_path))
        logger.info(f"Is V3? {is_v3} (expected: True)")

        try:
            engine = StyleLibraryAdapter.load(str(v3_path))
            logger.info(f"Loaded: {type(engine).__name__}")

            # Test V3 functionality
            if isinstance(engine, V3Sampler):
                result = engine.sample_with_constraints(
                    ["pose", "framing", "camera_angle", "lens", "background"]
                )
                logger.info(f"V3 result: {result.selections}")

                # Test conversion to V2 format
                v2_combo = StyleLibraryAdapter.to_diversity_combo(result)
                logger.info(
                    f"Converted to V2: framing={v2_combo.framing}, "
                    f"lens={v2_combo.lens}, angle={v2_combo.angle}, "
                    f"pose={v2_combo.pose}"
                )
        except Exception as e:
            logger.error(f"V3 test error: {e}")
    else:
        logger.warning(f"V3 library not found: {v3_path}")

    logger.info("\n=== Test Complete ===")


if __name__ == "__main__":
    test_adapter()
