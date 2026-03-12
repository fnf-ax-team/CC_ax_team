"""Prompt combinator for hierarchical MLB prompt library."""
import json
from pathlib import Path
from typing import Dict, Optional

# Library path
LIBRARY_PATH = Path("skills/fnf-image-gen/prompt-templates/mlb_hierarchical_library.json")

_library_cache: Optional[dict] = None

def load_hierarchical_library() -> dict:
    """Load the hierarchical prompt library (cached)."""
    global _library_cache
    if _library_cache is None:
        with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
            _library_cache = json.load(f)
    return _library_cache

def get_option(layer: str, option_id: str) -> Optional[dict]:
    """Get a specific option from a layer."""
    library = load_hierarchical_library()

    # Find the layer by checking all keys
    for key, layer_data in library["layers"].items():
        # Extract layer name from key (e.g., "1_expression" -> "expression")
        layer_name = key.split("_", 1)[1] if "_" in key else key
        if layer_name == layer:
            for option in layer_data.get("options", []):
                if option["id"] == option_id:
                    return option
    return None

def combine_prompt(selections: Dict[str, str]) -> str:
    """
    Combine selections from each layer into a final prompt.

    Args:
        selections: Dict mapping layer name to selected option ID
                   e.g., {"expression": "cool_confidence", "pose": "confident_stand", ...}

    Returns:
        Combined prompt string
    """
    library = load_hierarchical_library()
    segments = []

    # Priority order from library
    priority_order = library.get("priority_order",
        ["expression", "pose", "composition", "angle", "background", "lighting"])

    for layer_name in priority_order:
        option_id = selections.get(layer_name)
        if not option_id:
            continue

        # Find the option
        option = get_option(layer_name, option_id)
        if option and "prompt_segment" in option:
            segments.append(option["prompt_segment"])

    # Use separator from library
    separator = library.get("combinator", {}).get("separator", " | ")

    return separator.join(segments)

def validate_selections(selections: Dict[str, str]) -> bool:
    """Validate that all selections exist in the library."""
    library = load_hierarchical_library()
    priority_order = library.get("priority_order", [])

    for layer_name in priority_order:
        option_id = selections.get(layer_name)
        if option_id and not get_option(layer_name, option_id):
            return False
    return True

def get_layer_options(layer_name: str) -> list:
    """Get all options for a specific layer."""
    library = load_hierarchical_library()

    for key, layer_data in library["layers"].items():
        # Extract layer name from key (e.g., "1_expression" -> "expression")
        layer_key = key.split("_", 1)[1] if "_" in key else key
        if layer_key == layer_name:
            return layer_data.get("options", [])
    return []

def get_default_selections() -> Dict[str, str]:
    """Get default selections (first option of each layer)."""
    library = load_hierarchical_library()
    defaults = {}

    for key, layer_data in library["layers"].items():
        # Extract layer name from key (e.g., "1_expression" -> "expression")
        layer_name = key.split("_", 1)[1] if "_" in key else key
        options = layer_data.get("options", [])
        if options:
            defaults[layer_name] = options[0]["id"]

    return defaults
