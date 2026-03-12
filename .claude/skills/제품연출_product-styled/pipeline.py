"""
파이프라인 통합 - 제품 연출 전체 워크플로
"""

import os
from typing import Dict
from datetime import datetime
from product_analyzer import analyze_product
from styled_generator import generate_base_shot, enhance_lighting_texture
from color_validator import validate_color_accuracy, should_regenerate


def run_product_styled_pipeline(
    product_image: str,
    style_preset: str,
    shot_type: str,
    api_key: str,
    output_dir: str = None,
    options: Dict = None
) -> Dict:
    """
    전체 제품 연출 파이프라인 실행

    Args:
        product_image: 제품 이미지 경로
        style_preset: 스타일 프리셋 키
        shot_type: 샷 타입 키
        api_key: Gemini API 키
        output_dir: 출력 디렉토리 (기본값: Fnf_studio_outputs/product_styled/)
        options: 추가 옵션 (vivid_colors, premium_texture, aspect_ratio 등)

    Returns:
        {
            "final_image_path": str,
            "product_analysis": dict,
            "validation": dict,
            "metadata": dict
        }
    """
    # 출력 디렉토리 설정
    if output_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(
            project_root,
            "Fnf_studio_outputs",
            "product_styled",
            timestamp
        )

    os.makedirs(output_dir, exist_ok=True)

    # 1단계: 제품 분석 (VLM)
    print("[1/4] 제품 분석 중 (VLM)...")
    product_analysis = analyze_product(product_image, api_key)
    print(f"   제품 타입: {product_analysis['product_type']}")
    print(f"   주요 색상: {', '.join(product_analysis['dominant_colors'])}")
    print(f"   소재: {product_analysis['material']}")

    # 2단계: 기본 연출샷 생성
    print("[2/4] 기본 연출샷 생성...")
    base_shot = generate_base_shot(
        product_image,
        style_preset,
        shot_type,
        product_analysis,
        api_key,
        options
    )

    # 3단계: 조명/텍스처 향상
    print("[3/4] 조명/텍스처 향상...")
    enhanced_shot = enhance_lighting_texture(base_shot, style_preset, api_key)

    # 4단계: 색상 정확도 검증
    print("[4/4] 색상 정확도 검증...")
    validation = validate_color_accuracy(
        product_image,
        enhanced_shot,
        product_analysis["dominant_colors"],
        api_key
    )

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"product_styled_{style_preset}_{shot_type}_{timestamp}.png"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'wb') as f:
        f.write(enhanced_shot)

    # 검증 결과 출력
    if not validation["color_match"]:
        print(f"\n⚠️  색상 정확도: {validation['accuracy_score']}% (90% 미만)")
        if validation.get("issues"):
            print(f"   문제: {', '.join(validation['issues'])}")
        print("   재생성을 권장합니다.")
    else:
        print(f"\n✅ 색상 정확도: {validation['accuracy_score']}%")

    # 메타데이터 생성
    metadata = {
        "style_preset": style_preset,
        "shot_type": shot_type,
        "options": options,
        "product_analysis": product_analysis,
        "validation": validation,
        "output_path": output_path
    }

    # 메타데이터 저장
    import json
    metadata_path = os.path.join(output_dir, f"metadata_{timestamp}.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return {
        "final_image_path": output_path,
        "product_analysis": product_analysis,
        "validation": validation,
        "metadata": metadata
    }
