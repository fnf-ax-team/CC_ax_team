"""Generation function registry: WorkflowType -> generate_func lookup.

Lazy-imports workflow generation functions to avoid circular imports.
"""

import importlib
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Workflow type -> (module_path, function_name)
WORKFLOW_GENERATORS = {
    "brand_cut": ("core.brandcut.generator", "generate_brandcut"),
    "ai_influencer": ("core.ai_influencer.pipeline", "generate_full_pipeline"),
    "background_swap": ("core.background_swap.generator", "generate_background_swap"),
    "outfit_swap": ("core.outfit_swap.generator", "generate_outfit_swap"),
}

# Cache for imported functions
_cache: dict[str, Callable] = {}


def get_generate_func(workflow_type: str) -> Optional[Callable]:
    """Lazy-import and return the generation function for a workflow.

    Args:
        workflow_type: e.g. 'brand_cut', 'ai_influencer'

    Returns:
        The generation function, or None if not found/importable
    """
    if workflow_type in _cache:
        return _cache[workflow_type]

    entry = WORKFLOW_GENERATORS.get(workflow_type)
    if entry is None:
        logger.warning(f"No generator registered for workflow: {workflow_type}")
        return None

    module_path, func_name = entry
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        _cache[workflow_type] = func
        logger.info(f"Loaded generator for {workflow_type}: {module_path}.{func_name}")
        return func
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load generator for {workflow_type}: {e}")
        return None


def list_available_workflows() -> list[str]:
    """List all workflow types with registered generators."""
    return list(WORKFLOW_GENERATORS.keys())


def is_workflow_supported(workflow_type: str) -> bool:
    """Check if a workflow type has a registered generator."""
    return workflow_type in WORKFLOW_GENERATORS
