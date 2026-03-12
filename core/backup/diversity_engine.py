"""
Diversity Slot Machine Engine

Ensures diversity across batch image generations for MLB brandcuts.
Based on mlb-brandcut-quality.md design, implements:
- Framing quota system (MS 40%, MCU 25%, MFS 20%, CU 15%)
- Pose/angle variety with anti-repetition
- Background compatibility matching
- Style library reference selection
"""

import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class DiversityCombination:
    """Result of diversity selection"""
    framing: str  # MS, MCU, MFS, CU
    lens: str     # 50mm, 85mm, 35mm
    angle: int    # 0, 10, 15, 30
    pose: str     # confident_standing, relaxed_lean, seated, dynamic
    background: Dict[str, Any]
    reference_entry: Optional[Dict] = None


class DiversityEngine:
    """
    Diversity Slot Machine for MLB brandcut generation.

    Ensures batch variety through:
    1. Framing quota enforcement
    2. Weighted pose/angle selection with anti-repetition
    3. Background-pose compatibility matching
    4. 147-entry style library reference selection
    """

    FRAMING_QUOTA = {
        "MS": 0.40,    # Medium Shot 40%
        "MCU": 0.25,   # Medium Close-Up 25%
        "MFS": 0.20,   # Medium Full Shot 20%
        "CU": 0.15     # Close-Up 15%
    }

    LENS_FOR_FRAMING = {
        "MS": ["50mm", "35mm"],
        "MCU": ["85mm", "50mm"],
        "MFS": ["50mm", "35mm"],
        "CU": ["85mm"]
    }

    ANGLE_WEIGHTS = {0: 0.30, 10: 0.15, 15: 0.35, 30: 0.20}

    POSE_WEIGHTS = {
        "confident_standing": 0.40,
        "relaxed_lean": 0.25,
        "seated": 0.20,
        "dynamic": 0.15
    }

    BACKGROUND_POOL = [
        {
            "id": "metal_panel_studio",
            "prompt": "sleek gray metallic panel wall, industrial studio backdrop, cool steel texture, minimalist, cool-toned 5600K lighting",
            "weight": 0.30,
            "compatible_poses": ["confident_standing", "relaxed_lean"]
        },
        {
            "id": "luxury_suv",
            "prompt": "silver Hummer H2 SUV in industrial garage, luxury vehicle, matte finish, urban garage setting, cool-toned lighting",
            "weight": 0.25,
            "compatible_poses": ["relaxed_lean", "seated"]
        },
        {
            "id": "industrial_space",
            "prompt": "industrial space with metal ladders, pipes, raw concrete floor, warehouse aesthetic, cool 6000K lighting",
            "weight": 0.25,
            "compatible_poses": ["confident_standing", "relaxed_lean", "seated"]
        },
        {
            "id": "brutalist_concrete",
            "prompt": "brutalist concrete architecture, raw cement walls, minimalist geometric forms, cold tones, 5800K neutral daylight",
            "weight": 0.20,
            "compatible_poses": ["confident_standing", "relaxed_lean"]
        }
    ]

    def __init__(self, style_library_path: Optional[str] = None):
        """
        Initialize DiversityEngine.

        Args:
            style_library_path: Path to MLB style library JSON (optional)
        """
        self.style_library = None
        self.recent_combos: List[DiversityCombination] = []

        if style_library_path:
            self.load_style_library(style_library_path)

    def load_style_library(self, path: str) -> None:
        """Load the 147-entry MLB style library."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.style_library = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load style library: {e}")
            self.style_library = None

    def select_combination(
        self,
        batch_index: int,
        total_batch: int,
        avoid_recent: int = 3
    ) -> DiversityCombination:
        """
        Select diverse combination for batch position.

        Args:
            batch_index: Current position in batch (0-indexed)
            total_batch: Total batch size
            avoid_recent: Number of recent combinations to avoid repeating

        Returns:
            DiversityCombination with all selection results
        """
        # 1. Framing by quota
        framing = self._select_framing_by_quota(batch_index, total_batch)

        # 2. Lens for framing
        lens = random.choice(self.LENS_FOR_FRAMING[framing])

        # 3. Angle with anti-repetition
        angle = self._weighted_select_angle(avoid_recent)

        # 4. Pose with anti-repetition
        pose = self._weighted_select_pose(avoid_recent)

        # 5. Compatible background
        background = self._select_compatible_background(pose)

        # 6. Style library reference (if loaded)
        reference = self._find_closest_entry(framing, pose)

        combo = DiversityCombination(
            framing=framing,
            lens=lens,
            angle=angle,
            pose=pose,
            background=background,
            reference_entry=reference
        )

        # Track for anti-repetition
        self.recent_combos.append(combo)
        if len(self.recent_combos) > 10:
            self.recent_combos.pop(0)

        return combo

    def _select_framing_by_quota(self, idx: int, total: int) -> str:
        """Select framing based on quota allocation."""
        ms_slots = int(total * self.FRAMING_QUOTA["MS"])
        mcu_slots = int(total * self.FRAMING_QUOTA["MCU"])
        mfs_slots = int(total * self.FRAMING_QUOTA["MFS"])

        if idx < ms_slots:
            return "MS"
        elif idx < ms_slots + mcu_slots:
            return "MCU"
        elif idx < ms_slots + mcu_slots + mfs_slots:
            return "MFS"
        else:
            return "CU"

    def _weighted_select_angle(self, avoid_recent: int) -> int:
        """Select angle avoiding recent choices."""
        recent_angles = [c.angle for c in self.recent_combos[-avoid_recent:]]

        available = {k: v for k, v in self.ANGLE_WEIGHTS.items()
                     if k not in recent_angles}
        if not available:
            available = self.ANGLE_WEIGHTS

        return self._weighted_random_choice(available)

    def _weighted_select_pose(self, avoid_recent: int) -> str:
        """Select pose avoiding recent choices."""
        recent_poses = [c.pose for c in self.recent_combos[-avoid_recent:]]

        available = {k: v for k, v in self.POSE_WEIGHTS.items()
                     if k not in recent_poses}
        if not available:
            available = self.POSE_WEIGHTS

        return self._weighted_random_choice(available)

    def _weighted_random_choice(self, weights: Dict) -> Any:
        """Generic weighted random selection."""
        total = sum(weights.values())
        r = random.random() * total
        cumulative = 0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return list(weights.keys())[-1]

    def _select_compatible_background(self, pose: str) -> Dict:
        """Select background compatible with pose."""
        compatible = [bg for bg in self.BACKGROUND_POOL
                      if pose in bg["compatible_poses"]]
        if not compatible:
            compatible = self.BACKGROUND_POOL

        # Weighted selection
        total = sum(bg["weight"] for bg in compatible)
        r = random.random() * total
        cumulative = 0
        for bg in compatible:
            cumulative += bg["weight"]
            if r <= cumulative:
                return bg
        return compatible[-1]

    def _find_closest_entry(self, framing: str, pose: str) -> Optional[Dict]:
        """Find matching entry from 147 style library."""
        if not self.style_library or "entries" not in self.style_library:
            return None

        matches = []
        for entry in self.style_library.get("entries", []):
            entry_framing = entry.get("composition", {}).get("framing_type", "")
            entry_pose = entry.get("pose", {}).get("overall_pose_category", "")

            if framing in entry_framing and pose == entry_pose:
                matches.append(entry)

        return random.choice(matches) if matches else None

    def get_batch_plan(self, batch_size: int) -> List[DiversityCombination]:
        """
        Generate diversity plan for entire batch.

        Args:
            batch_size: Number of images to generate

        Returns:
            List of DiversityCombination for each position
        """
        self.recent_combos = []  # Reset for new batch
        return [
            self.select_combination(i, batch_size)
            for i in range(batch_size)
        ]

    def get_diversity_stats(self, combinations: List[DiversityCombination]) -> Dict:
        """
        Calculate diversity statistics for a batch.

        Args:
            combinations: List of combinations to analyze

        Returns:
            Statistics dict with framing/pose/background distributions
        """
        if not combinations:
            return {}

        total = len(combinations)

        framing_dist = {}
        pose_dist = {}
        bg_dist = {}

        for c in combinations:
            framing_dist[c.framing] = framing_dist.get(c.framing, 0) + 1
            pose_dist[c.pose] = pose_dist.get(c.pose, 0) + 1
            bg_id = c.background.get("id", "unknown")
            bg_dist[bg_id] = bg_dist.get(bg_id, 0) + 1

        return {
            "total": total,
            "framing_distribution": {k: f"{v}/{total} ({v/total*100:.1f}%)"
                                     for k, v in framing_dist.items()},
            "pose_distribution": {k: f"{v}/{total} ({v/total*100:.1f}%)"
                                  for k, v in pose_dist.items()},
            "background_distribution": {k: f"{v}/{total} ({v/total*100:.1f}%)"
                                        for k, v in bg_dist.items()},
            "unique_framings": len(framing_dist),
            "unique_poses": len(pose_dist),
            "unique_backgrounds": len(bg_dist)
        }

    def build_prompt_additions(self, combo: DiversityCombination) -> str:
        """
        Build prompt additions from diversity combination.

        Args:
            combo: DiversityCombination to convert to prompt

        Returns:
            Prompt string with framing, pose, camera specifications
        """
        parts = [
            f"FRAMING: {combo.framing} (Medium Shot = waist up, MCU = chest up, MFS = knee up, CU = face focus)",
            f"CAMERA: {combo.lens} lens, {combo.angle}° low angle",
            f"POSE CATEGORY: {combo.pose}",
            f"BACKGROUND: {combo.background['prompt']}"
        ]

        if combo.reference_entry:
            ref = combo.reference_entry
            if "pose" in ref:
                pose_desc = ref["pose"].get("description", "")
                if pose_desc:
                    parts.append(f"POSE REFERENCE: {pose_desc}")
            if "expression" in ref:
                expr_desc = ref["expression"].get("mood_description", "")
                if expr_desc:
                    parts.append(f"EXPRESSION REFERENCE: {expr_desc}")

        return "\n".join(parts)
