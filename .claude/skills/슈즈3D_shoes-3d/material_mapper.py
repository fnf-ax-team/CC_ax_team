"""
소재 매핑 - VLM 소재를 PBR 파라미터로 변환
"""

from typing import Dict, List, Any


# VLM 소재 → PBR 파라미터 매핑 테이블
PBR_MATERIAL_MAP = {
    "leather": {
        "roughness": 0.4,
        "metallic": 0.0,
        "specular": 0.5,
        "normal_strength": 0.3
    },
    "mesh": {
        "roughness": 0.8,
        "metallic": 0.0,
        "opacity": 0.9,
        "normal_strength": 0.2
    },
    "rubber": {
        "roughness": 0.6,
        "metallic": 0.0,
        "bump": 0.2,
        "normal_strength": 0.4
    },
    "canvas": {
        "roughness": 0.7,
        "metallic": 0.0,
        "normal": "fabric_pattern",
        "normal_strength": 0.5
    },
    "synthetic_leather": {
        "roughness": 0.3,
        "metallic": 0.1,
        "specular": 0.6,
        "normal_strength": 0.2
    },
    "suede": {
        "roughness": 0.9,
        "metallic": 0.0,
        "fuzz": 0.3,
        "normal_strength": 0.6
    },
    "patent_leather": {
        "roughness": 0.1,
        "metallic": 0.0,
        "specular": 0.9,
        "normal_strength": 0.1
    },
    "nylon": {
        "roughness": 0.5,
        "metallic": 0.0,
        "specular": 0.3,
        "normal_strength": 0.3
    },
    "foam": {
        "roughness": 0.8,
        "metallic": 0.0,
        "subsurface": 0.2,
        "normal_strength": 0.4
    }
}


def map_materials_to_pbr(vlm_materials: List[str]) -> Dict[str, Any]:
    """
    VLM 분석 소재를 PBR 파라미터로 변환

    Args:
        vlm_materials: VLM이 감지한 소재 리스트

    Returns:
        dict: 소재별 PBR 파라미터
            {
                "leather": {"roughness": 0.4, "metallic": 0.0, ...},
                "mesh": {"roughness": 0.8, "metallic": 0.0, ...},
                ...
            }
    """
    mapped_materials = {}

    for material in vlm_materials:
        # 소재명 정규화 (소문자, 공백 제거)
        material_key = material.lower().replace(" ", "_").replace("-", "_")

        # 매핑 테이블에서 PBR 파라미터 조회
        if material_key in PBR_MATERIAL_MAP:
            mapped_materials[material] = PBR_MATERIAL_MAP[material_key]
        else:
            # 기본값 (알 수 없는 소재)
            mapped_materials[material] = {
                "roughness": 0.5,
                "metallic": 0.0,
                "specular": 0.4,
                "normal_strength": 0.3
            }

    return mapped_materials


def get_dominant_material_pbr(
    vlm_materials: List[str],
    material_weights: Dict[str, float] = None
) -> Dict[str, float]:
    """
    주요 소재의 PBR 파라미터 반환 (가중치 적용)

    Args:
        vlm_materials: VLM이 감지한 소재 리스트
        material_weights: 소재별 가중치 (없으면 균등)

    Returns:
        dict: 가중 평균 PBR 파라미터
    """
    if not vlm_materials:
        # 기본 소재
        return PBR_MATERIAL_MAP["synthetic_leather"]

    # 가중치 기본값 (균등 분배)
    if material_weights is None:
        material_weights = {mat: 1.0 / len(vlm_materials) for mat in vlm_materials}

    # PBR 파라미터 가중 평균
    weighted_pbr = {
        "roughness": 0.0,
        "metallic": 0.0,
        "specular": 0.0,
        "normal_strength": 0.0
    }

    mapped = map_materials_to_pbr(vlm_materials)

    for material, weight in material_weights.items():
        if material in mapped:
            pbr = mapped[material]
            weighted_pbr["roughness"] += pbr.get("roughness", 0.5) * weight
            weighted_pbr["metallic"] += pbr.get("metallic", 0.0) * weight
            weighted_pbr["specular"] += pbr.get("specular", 0.4) * weight
            weighted_pbr["normal_strength"] += pbr.get("normal_strength", 0.3) * weight

    return weighted_pbr
