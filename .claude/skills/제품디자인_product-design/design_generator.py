"""
디자인 생성기
슬롯 사양으로 제품 디자인 이미지 생성 및 검증
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from google.generativeai import types

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from core.config import IMAGE_MODEL, VISION_MODEL, OUTPUT_BASE_DIR
from slot_extractor import extract_slots_vlm
from slot_blender import ALL_SLOTS


def build_design_prompt(slots: dict, category: str = None) -> str:
    """
    슬롯 사양을 프롬프트로 변환

    Args:
        slots: 14개 슬롯 딕셔너리
        category: 제품 카테고리 (예: "아우터")

    Returns:
        생성 프롬프트 문자열
    """
    base = f"Professional product photography of a {category or 'fashion item'}. "

    # Core slots (필수 강조)
    core_desc = (
        f"Silhouette: {slots['silhouette']}. "
        f"Main color: {slots['main_color']}. "
        f"Material: {slots['material_base']}. "
    )

    # Detail slots (있는 것만 포함)
    details = []
    if slots.get('accent_color') and slots['accent_color'] != "None":
        details.append(f"accent color {slots['accent_color']}")
    if slots.get('pattern') and slots['pattern'] != "Solid":
        details.append(f"{slots['pattern']} pattern")
    if slots.get('collar_neckline'):
        details.append(f"{slots['collar_neckline']}")
    if slots.get('sleeve_arm'):
        details.append(f"{slots['sleeve_arm']}")
    if slots.get('pocket') and slots['pocket'] != "None":
        details.append(f"with {slots['pocket']}")
    if slots.get('closure'):
        details.append(f"{slots['closure']} closure")

    detail_desc = ", ".join(details) + ". " if details else ""

    # Finishing slots
    finishing = []
    if slots.get('hem_edge'):
        finishing.append(f"{slots['hem_edge']} hem")
    if slots.get('hardware') and slots['hardware'] != "None":
        finishing.append(slots['hardware'])
    if slots.get('details') and slots['details'] != "None":
        finishing.append(slots['details'])

    finishing_desc = ", ".join(finishing) + ". " if finishing else ""

    # Style directives
    style = (
        "Clean white background. Front view. Studio lighting. "
        "High resolution. Product catalog style. No model. "
        "Focus on garment details and texture."
    )

    return base + core_desc + detail_desc + finishing_desc + style


def generate_product_design(
    slots: dict,
    reference_images: list[str] = None,
    product_category: str = None,
    temperature: float = 0.2
) -> str:
    """
    슬롯 사양으로 제품 디자인 생성

    Args:
        slots: 14개 슬롯 딕셔너리
        reference_images: 참조 이미지 경로 리스트 (선택)
        product_category: 제품 카테고리 (선택)
        temperature: 생성 온도 (기본: 0.2)

    Returns:
        output_path: 생성된 이미지 경로
    """
    # 프롬프트 구성
    prompt = build_design_prompt(slots, product_category)

    print(f"\n🎨 생성 프롬프트:\n{prompt}\n")

    # 모델 설정
    model = genai.GenerativeModel(IMAGE_MODEL)

    # 생성 설정
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
            image_size="2K"
        )
    )

    # 컨텐츠 구성
    contents = [prompt]

    # 참조 이미지 추가
    if reference_images:
        for img_path in reference_images:
            if os.path.exists(img_path):
                contents.append(Image.open(img_path))

    # 이미지 생성
    try:
        response = model.generate_content(
            contents,
            generation_config=config
        )

        # 이미지 추출 및 저장
        if hasattr(response, '_result') and response._result.candidates:
            candidate = response._result.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # 출력 경로 생성
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_dir = os.path.join(OUTPUT_BASE_DIR, "product_design", timestamp)
                        os.makedirs(output_dir, exist_ok=True)

                        output_path = os.path.join(output_dir, "generated.png")

                        # 이미지 저장
                        with open(output_path, "wb") as f:
                            f.write(part.inline_data.data)

                        print(f"✅ 이미지 생성 완료: {output_path}")
                        return output_path

        # 이미지를 찾지 못한 경우
        print("⚠️ 응답에서 이미지를 찾을 수 없습니다.")
        return None

    except Exception as e:
        print(f"❌ 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def semantic_match(expected: str, actual: str, threshold: float = 0.7) -> bool:
    """
    의미적 유사도 검사 (간단한 키워드 매칭)

    Args:
        expected: 기대값
        actual: 실제값
        threshold: 유사도 임계값

    Returns:
        True if match, False otherwise
    """
    if expected == "None" and actual == "None":
        return True

    # 정규화
    exp_lower = expected.lower()
    act_lower = actual.lower()

    # 정확 일치
    if exp_lower == act_lower:
        return True

    # 키워드 포함 검사
    exp_keywords = set(exp_lower.split())
    act_keywords = set(act_lower.split())

    if not exp_keywords:
        return True

    overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
    return overlap >= threshold


def validate_design(image_path: str, target_slots: dict) -> dict:
    """
    생성된 디자인이 슬롯 사양과 일치하는지 검증

    Args:
        image_path: 검증할 이미지 경로
        target_slots: 목표 슬롯 사양

    Returns:
        {
            "score": 0.92,  # 0-1 scale
            "matches": {
                "silhouette": True,
                "main_color": True,
                ...
            },
            "feedback": "Collar style doesn't match specification"
        }
    """
    # VLM으로 생성 이미지 분석
    generated_slots = extract_slots_vlm(image_path)

    # 슬롯별 가중치
    weights = {
        "silhouette": 0.15,
        "main_color": 0.15,
        "material_base": 0.10,
        "accent_color": 0.10,
        "pattern": 0.08,
        "collar_neckline": 0.08,
        "sleeve_arm": 0.08,
        "pocket": 0.06,
        "closure": 0.06,
        "hem_edge": 0.05,
        "material_accent": 0.04,
        "logo_branding": 0.02,
        "hardware": 0.02,
        "details": 0.01
    }

    matches = {}
    weighted_score = 0.0

    for slot, weight in weights.items():
        expected = target_slots.get(slot, "None")
        actual = generated_slots.get(slot, "None")

        # 의미적 유사도 검사
        is_match = semantic_match(expected, actual)
        matches[slot] = is_match

        if is_match:
            weighted_score += weight

    # 피드백 생성
    failed_slots = [k for k, v in matches.items() if not v and target_slots.get(k) != "None"]
    feedback = f"Mismatches in: {', '.join(failed_slots)}" if failed_slots else "All slots match"

    return {
        "score": weighted_score,
        "matches": matches,
        "feedback": feedback,
        "generated_slots": generated_slots
    }


if __name__ == "__main__":
    # 테스트 코드

    # 예시 슬롯
    test_slots = {
        "silhouette": "Oversized boxy",
        "main_color": "Navy blue",
        "accent_color": "None",
        "material_base": "Cotton jersey",
        "material_accent": "None",
        "pattern": "Solid",
        "collar_neckline": "Crew neck",
        "sleeve_arm": "Long sleeve",
        "pocket": "None",
        "closure": "Pull-on",
        "hem_edge": "Ribbed hem",
        "logo_branding": "None",
        "hardware": "None",
        "details": "None"
    }

    # 프롬프트 생성 테스트
    print("📝 생성 프롬프트:")
    prompt = build_design_prompt(test_slots, "상의")
    print(prompt)

    # 실제 생성 테스트는 주석 처리 (API 키 필요)
    # result_path = generate_product_design(test_slots, product_category="상의")
    # if result_path:
    #     validation = validate_design(result_path, test_slots)
    #     print(f"\n검증 결과: {validation}")
