"""
소재 생성 메인 실행 스크립트
"""

import os
from datetime import datetime
from pathlib import Path

from fabric_analyzer import analyze_fabric_attributes
from fabric_db import find_similar_texture, register_to_db
from texture_generator import generate_fabric_texture


def main():
    """대화형 플로우 - 소재 생성"""

    print("=" * 60)
    print("🎨 FNF Studio - 소재 이미지 생성")
    print("=" * 60)
    print()

    # 1. 생성 방식 선택
    print("어떤 방식으로 생성할까요?")
    print("  1) 레퍼런스 이미지 기반 (비슷한 텍스처 생성)")
    print("  2) 속성으로 직접 선택 (10단계 슬라이더)")
    print()

    choice = input("선택 (1 or 2): ").strip()
    print()

    attributes = None

    # ========== 플로우 A: 레퍼런스 이미지 기반 ==========
    if choice == "1":
        print("원단 레퍼런스 이미지 경로를 입력하세요:")
        image_path = input("경로: ").strip().strip('"')
        print()

        if not os.path.exists(image_path):
            print(f"❌ 파일이 존재하지 않습니다: {image_path}")
            return

        print("📸 이미지 분석 중...")
        attributes = analyze_fabric_attributes(image_path)

        print()
        print("✅ 분석 완료! 다음과 같이 분석되었습니다:")
        print(f"  - 소재 타입: {attributes.get('material_type', 'N/A')}")
        print(f"  - 색상: {attributes.get('color', 'N/A')}")
        print(f"  - 패턴: {attributes.get('pattern', 'N/A')}")
        print()
        print("  [10단계 속성]")
        print(f"  - 두께 (thickness): {attributes.get('thickness', 5)}/10")
        print(f"  - 광택 (glossiness): {attributes.get('glossiness', 5)}/10")
        print(f"  - 부드러움 (softness): {attributes.get('softness', 5)}/10")
        print(f"  - 질감 (texture): {attributes.get('texture', 5)}/10")
        print(f"  - 신축성 (stretch): {attributes.get('stretch', 5)}/10")
        print(f"  - 투명도 (transparency): {attributes.get('transparency', 5)}/10")
        print(f"  - 무게 (weight): {attributes.get('weight', 5)}/10")
        print(f"  - 통기성 (breathability): {attributes.get('breathability', 5)}/10")
        print(f"  - 드레이프 (drape): {attributes.get('drape', 5)}/10")
        print(f"  - 내구성 (durability): {attributes.get('durability', 5)}/10")
        print()

        confirm = input("이대로 생성할까요? (y/n): ").strip().lower()
        if confirm != 'y':
            print("취소되었습니다.")
            return
        print()

    # ========== 플로우 B: 속성 직접 선택 ==========
    elif choice == "2":
        print("10단계 속성을 입력하세요 (1~10):")
        print()

        attributes = {}
        attributes["thickness"] = int(input("  두께 (thickness, 1=얇음 10=두꺼움): ").strip() or "5")
        attributes["glossiness"] = int(input("  광택 (glossiness, 1=무광 10=고광택): ").strip() or "5")
        attributes["softness"] = int(input("  부드러움 (softness, 1=딱딱함 10=부드러움): ").strip() or "5")
        attributes["texture"] = int(input("  질감 (texture, 1=매끄러움 10=거침): ").strip() or "5")
        attributes["stretch"] = int(input("  신축성 (stretch, 1=없음 10=최대): ").strip() or "5")
        attributes["transparency"] = int(input("  투명도 (transparency, 1=불투명 10=투명): ").strip() or "5")
        attributes["weight"] = int(input("  무게 (weight, 1=가벼움 10=무거움): ").strip() or "5")
        attributes["breathability"] = int(input("  통기성 (breathability, 1=낮음 10=높음): ").strip() or "5")
        attributes["drape"] = int(input("  드레이프 (drape, 1=뻣뻣함 10=흐름성): ").strip() or "5")
        attributes["durability"] = int(input("  내구성 (durability, 1=약함 10=강함): ").strip() or "5")
        print()

        attributes["material_type"] = input("  소재 타입 (예: denim, silk, cotton): ").strip() or "fabric"
        attributes["color"] = input("  색상 (예: dark indigo blue): ").strip() or "neutral"
        attributes["pattern"] = input("  패턴 (예: twill weave, plain): ").strip() or "plain weave"
        print()

    else:
        print("❌ 잘못된 선택입니다.")
        return

    # ========== DB 유사도 매칭 ==========
    print("🔍 DB에서 유사한 소재 찾는 중...")
    similar = find_similar_texture(attributes)

    if similar:
        print()
        print("✅ DB에서 가장 유사한 소재:")
        for i, item in enumerate(similar, 1):
            print(f"  {i}. {item['name']} (유사도 {item['similarity']}%)")
        print()
    else:
        print("  -> DB에 등록된 소재가 없습니다. 첫 엔트리가 생성됩니다.")
        print()

    # ========== 이미지 생성 ==========
    print("🎨 원단 텍스처 생성 중... (타일링 검증 포함, 최대 3회 시도)")
    print()

    result_image = generate_fabric_texture(attributes, max_retries=2)

    if not result_image:
        print("❌ 생성 실패. 속성을 조정해보세요.")
        return

    # ========== 출력 저장 ==========
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    material_name = attributes.get("material_type", "fabric").replace(" ", "_")
    color_name = attributes.get("color", "").replace(" ", "_")[:20]

    output_dir = Path("Fnf_studio_outputs/fabric_generation")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{material_name}_{color_name}_{timestamp}.png"
    output_path = output_dir / filename

    result_image.save(str(output_path))
    print()
    print(f"✅ 생성 완료: {output_path}")
    print()

    # ========== DB 등록 ==========
    db_name = f"{material_name}_{color_name}_{timestamp}"
    register_to_db(db_name, attributes, str(output_path))
    print()
    print("=" * 60)
    print("🎉 소재 생성 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
