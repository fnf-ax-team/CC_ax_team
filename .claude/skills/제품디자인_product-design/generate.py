"""
제품 디자인 생성 메인 스크립트
슬롯 기반 제품 디자인 시스템 - 대화형 플로우
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from core.config import IMAGE_MODEL, VISION_MODEL, OUTPUT_BASE_DIR
from slot_extractor import extract_slots_vlm
from slot_blender import merge_slots, ALL_SLOTS
from design_generator import generate_product_design, validate_design


def print_header(text):
    """헤더 출력"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_slots(slots, title="현재 슬롯 상태"):
    """슬롯 정보 출력"""
    print(f"\n📋 {title}:")
    for slot, value in slots.items():
        print(f"  • {slot}: {value}")


def select_mode():
    """작업 모드 선택"""
    print_header("제품 디자인 시스템")
    print("\n어떤 작업을 하시겠습니까?")
    print("1. 색상 변경 - 제품의 색상만 수정")
    print("2. 디테일 수정 - 특정 디자인 요소 변경")
    print("3. 요소 믹싱 - 여러 제품의 요소 조합")
    print("4. 새 디자인 - 처음부터 새로운 디자인 생성")

    while True:
        choice = input("\n선택 (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            modes = {
                "1": "색상 변경",
                "2": "디테일 수정",
                "3": "요소 믹싱",
                "4": "새 디자인"
            }
            return modes[choice]
        print("⚠️ 1-4 중 하나를 선택해주세요.")


def get_image_path(prompt="이미지 경로를 입력하세요"):
    """이미지 경로 입력 받기"""
    while True:
        path = input(f"\n{prompt}: ").strip()
        if os.path.exists(path):
            return path
        print(f"⚠️ 파일을 찾을 수 없습니다: {path}")


def mode_color_change():
    """색상 변경 모드"""
    print_header("색상 변경 모드")

    # 1. 원본 이미지 업로드
    original_image = get_image_path("원본 이미지 경로")

    # 2. VLM으로 슬롯 추출
    print("\n🔍 이미지 분석 중...")
    slots = extract_slots_vlm(original_image)
    print_slots(slots)

    # 3. 변경할 색상 선택
    print("\n어떤 색상을 변경하시겠습니까?")
    print("1. 메인 색상만")
    print("2. 포인트 색상만")
    print("3. 두 색상 모두")

    color_choice = input("\n선택 (1-3): ").strip()

    if color_choice in ["1", "3"]:
        new_main_color = input(f"새로운 메인 색상 (현재: {slots['main_color']}): ").strip()
        if new_main_color:
            slots["main_color"] = new_main_color

    if color_choice in ["2", "3"]:
        new_accent_color = input(f"새로운 포인트 색상 (현재: {slots['accent_color']}): ").strip()
        if new_accent_color:
            slots["accent_color"] = new_accent_color

    print_slots(slots, "수정된 슬롯")

    # 4. 생성
    print("\n🎨 디자인 생성 중...")
    result_path = generate_product_design(slots, reference_images=[original_image])

    return result_path, slots


def mode_detail_modify():
    """디테일 수정 모드"""
    print_header("디테일 수정 모드")

    # 1. 원본 이미지 업로드
    original_image = get_image_path("원본 이미지 경로")

    # 2. VLM으로 슬롯 추출
    print("\n🔍 이미지 분석 중...")
    slots = extract_slots_vlm(original_image)
    print_slots(slots)

    # 3. 수정할 슬롯 선택
    print("\n어떤 슬롯을 수정하시겠습니까?")
    for i, slot in enumerate(ALL_SLOTS, 1):
        print(f"{i:2d}. {slot:20s} → {slots.get(slot, 'None')}")

    while True:
        slot_choice = input("\n슬롯 번호 선택: ").strip()
        try:
            slot_idx = int(slot_choice) - 1
            if 0 <= slot_idx < len(ALL_SLOTS):
                selected_slot = ALL_SLOTS[slot_idx]
                break
        except ValueError:
            pass
        print("⚠️ 유효한 번호를 입력하세요.")

    # 4. 새 값 입력
    current_value = slots.get(selected_slot, "None")
    new_value = input(f"\n새로운 값 (현재: {current_value}): ").strip()
    if new_value:
        slots[selected_slot] = new_value

    print_slots(slots, "수정된 슬롯")

    # 5. 생성
    print("\n🎨 디자인 생성 중...")
    result_path = generate_product_design(slots, reference_images=[original_image])

    return result_path, slots


def mode_element_mixing():
    """요소 믹싱 모드"""
    print_header("요소 믹싱 모드")

    # 1. 여러 이미지 업로드
    print("2-4개의 이미지를 입력하세요 (빈 줄 입력 시 종료)")
    images = []
    for i in range(1, 5):
        path = input(f"\n이미지 {i} 경로 (선택): ").strip()
        if not path:
            break
        if os.path.exists(path):
            images.append(path)
        else:
            print(f"⚠️ 파일을 찾을 수 없습니다: {path}")

    if len(images) < 2:
        print("⚠️ 최소 2개의 이미지가 필요합니다.")
        return None, None

    # 2. 각 이미지별 슬롯 추출
    print("\n🔍 이미지들 분석 중...")
    slots_list = []
    for i, img_path in enumerate(images):
        print(f"\n--- 이미지 {i+1} ---")
        slots = extract_slots_vlm(img_path)
        slots_list.append(slots)
        print_slots(slots, f"이미지 {i+1} 슬롯")

    # 3. 슬롯별 이미지 선택
    print("\n각 슬롯마다 어떤 이미지의 요소를 사용할지 선택하세요")
    print("(빈 입력 시 이미지 1 사용)")

    selections = {}
    for slot in ALL_SLOTS:
        print(f"\n[{slot}]")
        for i, slots in enumerate(slots_list):
            print(f"  {i+1}. {slots.get(slot, 'None')}")

        choice = input(f"선택 (1-{len(slots_list)}): ").strip()
        if choice:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(slots_list):
                    selections[slot] = idx
            except ValueError:
                pass

    # 4. 슬롯 병합
    mixed_slots = merge_slots(slots_list, selections)
    print_slots(mixed_slots, "믹싱된 슬롯")

    # 5. 생성
    print("\n🎨 디자인 생성 중...")
    result_path = generate_product_design(mixed_slots, reference_images=images)

    return result_path, mixed_slots


def mode_new_design():
    """새 디자인 모드"""
    print_header("새 디자인 생성 모드")

    # 1. 기본 정보 수집
    print("\n제품 카테고리를 선택하세요:")
    categories = ["상의", "하의", "아우터", "원피스", "가방", "신발"]
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")

    cat_choice = input("\n선택 (1-6): ").strip()
    try:
        category = categories[int(cat_choice) - 1]
    except (ValueError, IndexError):
        category = "상의"

    print("\n스타일 방향을 선택하세요:")
    styles = ["미니멀", "스트릿", "클래식", "아방가르드"]
    for i, style in enumerate(styles, 1):
        print(f"{i}. {style}")

    style_choice = input("\n선택 (1-4): ").strip()
    try:
        style = styles[int(style_choice) - 1]
    except (ValueError, IndexError):
        style = "미니멀"

    # 2. 핵심 슬롯 입력
    print("\n📝 핵심 슬롯 입력 (필수)")

    silhouette = input("실루엣 (예: Oversized boxy, Fitted cropped): ").strip()
    main_color = input("메인 색상 (예: Pure white, Navy blue): ").strip()
    material_base = input("주 소재 (예: Cotton jersey, Wool blend): ").strip()

    # 3. 선택적 슬롯 입력
    print("\n📝 선택적 슬롯 입력 (Enter 시 기본값)")

    accent_color = input("포인트 색상 (기본: None): ").strip() or "None"
    material_accent = input("보조 소재 (기본: None): ").strip() or "None"
    pattern = input("패턴 (기본: Solid): ").strip() or "Solid"
    collar_neckline = input("칼라/넥라인 (예: Crew neck): ").strip() or "Crew neck"
    sleeve_arm = input("소매 스타일 (예: Long sleeve): ").strip() or "Long sleeve"
    pocket = input("주머니 (기본: None): ").strip() or "None"
    closure = input("여밈 방식 (예: Zipper): ").strip() or "Buttons"
    hem_edge = input("밑단 (기본: Straight hem): ").strip() or "Straight hem"
    logo_branding = input("로고/브랜딩 (기본: None): ").strip() or "None"
    hardware = input("하드웨어 (기본: None): ").strip() or "None"
    details = input("기타 디테일 (기본: None): ").strip() or "None"

    # 4. 슬롯 구성
    slots = {
        "silhouette": silhouette,
        "main_color": main_color,
        "accent_color": accent_color,
        "material_base": material_base,
        "material_accent": material_accent,
        "pattern": pattern,
        "collar_neckline": collar_neckline,
        "sleeve_arm": sleeve_arm,
        "pocket": pocket,
        "closure": closure,
        "hem_edge": hem_edge,
        "logo_branding": logo_branding,
        "hardware": hardware,
        "details": details
    }

    print_slots(slots, "입력된 슬롯")

    # 5. 생성
    print("\n🎨 디자인 생성 중...")
    result_path = generate_product_design(slots, product_category=category)

    return result_path, slots


def save_session(mode, slots, result_path):
    """세션 정보 저장"""
    output_dir = os.path.join(OUTPUT_BASE_DIR, "product_design", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(output_dir, exist_ok=True)

    session_data = {
        "mode": mode,
        "slots": slots,
        "result_path": result_path,
        "timestamp": datetime.now().isoformat()
    }

    session_file = os.path.join(output_dir, "session.json")
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    # 결과 이미지도 복사
    if result_path and os.path.exists(result_path):
        import shutil
        output_image = os.path.join(output_dir, "result.png")
        shutil.copy(result_path, output_image)
        return output_dir

    return output_dir


def main():
    """메인 실행 함수"""
    try:
        # 모드 선택
        mode = select_mode()

        # 모드별 실행
        if mode == "색상 변경":
            result_path, slots = mode_color_change()
        elif mode == "디테일 수정":
            result_path, slots = mode_detail_modify()
        elif mode == "요소 믹싱":
            result_path, slots = mode_element_mixing()
        elif mode == "새 디자인":
            result_path, slots = mode_new_design()
        else:
            print("⚠️ 알 수 없는 모드")
            return

        # 결과 검증
        if result_path:
            print("\n✅ 생성 완료!")
            print(f"결과 경로: {result_path}")

            print("\n🔍 품질 검증 중...")
            validation = validate_design(result_path, slots)

            print(f"\n📊 검증 결과:")
            print(f"  점수: {validation['score']:.2%}")
            print(f"  피드백: {validation['feedback']}")

            if validation['score'] >= 0.85:
                print("\n✅ 품질 검증 통과!")
            else:
                print("\n⚠️ 품질 검증 실패 - 재생성을 권장합니다.")

            # 세션 저장
            output_dir = save_session(mode, slots, result_path)
            print(f"\n💾 세션 저장 완료: {output_dir}")

            # 재생성 여부 확인
            retry = input("\n재생성하시겠습니까? (y/n): ").strip().lower()
            if retry == 'y':
                print("\n🔄 재생성 중...")
                result_path = generate_product_design(slots, reference_images=None)
                print(f"재생성 완료: {result_path}")

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
