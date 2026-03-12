"""
슈즈 3D (Shoes 3D) - 신발 3D 모델 생성 워크플로

신발 이미지 또는 CAD 파일을 3D 모델로 변환하여 다각도 렌더링 제공
"""

from .pipeline import Shoes3DPipeline, Shoes3DResult
from .shoe_analyzer import analyze_shoe
from .silhouette_generator import generate_silhouette_views
from .material_mapper import map_materials_to_pbr, get_dominant_material_pbr, PBR_MATERIAL_MAP
from .renderer import RENDER_ANGLES, render_config, validate_3d_quality, check_quality_thresholds

__all__ = [
    "Shoes3DPipeline",
    "Shoes3DResult",
    "analyze_shoe",
    "generate_silhouette_views",
    "map_materials_to_pbr",
    "get_dominant_material_pbr",
    "PBR_MATERIAL_MAP",
    "RENDER_ANGLES",
    "render_config",
    "validate_3d_quality",
    "check_quality_thresholds"
]
