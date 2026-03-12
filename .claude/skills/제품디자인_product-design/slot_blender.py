"""
슬롯 믹싱 엔진
여러 제품의 슬롯을 병합하여 새로운 디자인 생성
"""

# 전체 슬롯 정의 (14개)
ALL_SLOTS = [
    "silhouette",
    "main_color",
    "accent_color",
    "material_base",
    "material_accent",
    "pattern",
    "collar_neckline",
    "sleeve_arm",
    "pocket",
    "closure",
    "hem_edge",
    "logo_branding",
    "hardware",
    "details"
]


def merge_slots(slots_list: list[dict], selections: dict) -> dict:
    """
    여러 제품의 슬롯을 사용자 선택에 따라 병합

    Args:
        slots_list: [{슬롯14개}, {슬롯14개}, ...]
        selections: {"silhouette": 0, "collar_neckline": 1, ...}  # 이미지 인덱스

    Returns:
        merged_slots: {14개 슬롯}

    Example:
        >>> slots_a = {"silhouette": "Boxy", "main_color": "White", ...}
        >>> slots_b = {"silhouette": "Fitted", "main_color": "Black", ...}
        >>> selections = {"silhouette": 0, "main_color": 1}
        >>> merged = merge_slots([slots_a, slots_b], selections)
        >>> merged["silhouette"]  # "Boxy" (from slots_a)
        >>> merged["main_color"]   # "Black" (from slots_b)
    """
    merged = {}

    # 사용자 선택에 따라 슬롯 병합
    for slot_name, image_idx in selections.items():
        if slot_name in ALL_SLOTS and 0 <= image_idx < len(slots_list):
            merged[slot_name] = slots_list[image_idx][slot_name]

    # 선택되지 않은 슬롯은 첫 번째 이미지 기본값
    for slot in ALL_SLOTS:
        if slot not in merged:
            merged[slot] = slots_list[0].get(slot, "None")

    return merged


def validate_slots(slots: dict) -> bool:
    """
    슬롯 딕셔너리가 유효한지 검증

    Args:
        slots: 검증할 슬롯 딕셔너리

    Returns:
        True if valid, False otherwise
    """
    # 모든 필수 슬롯이 있는지 확인
    for slot in ALL_SLOTS:
        if slot not in slots:
            return False

    return True


def get_core_slots(slots: dict) -> dict:
    """
    핵심 슬롯만 추출 (silhouette, main_color, material_base)

    Args:
        slots: 전체 슬롯 딕셔너리

    Returns:
        핵심 슬롯만 포함된 딕셔너리
    """
    core_slot_names = ["silhouette", "main_color", "material_base"]
    return {k: v for k, v in slots.items() if k in core_slot_names}


def get_detail_slots(slots: dict) -> dict:
    """
    디테일 슬롯만 추출

    Args:
        slots: 전체 슬롯 딕셔너리

    Returns:
        디테일 슬롯만 포함된 딕셔너리
    """
    detail_slot_names = [
        "pattern", "collar_neckline", "sleeve_arm",
        "pocket", "closure"
    ]
    return {k: v for k, v in slots.items() if k in detail_slot_names}


def get_finishing_slots(slots: dict) -> dict:
    """
    마무리 슬롯만 추출

    Args:
        slots: 전체 슬롯 딕셔너리

    Returns:
        마무리 슬롯만 포함된 딕셔너리
    """
    finishing_slot_names = [
        "hem_edge", "logo_branding", "hardware", "details"
    ]
    return {k: v for k, v in slots.items() if k in finishing_slot_names}


def diff_slots(slots_a: dict, slots_b: dict) -> dict:
    """
    두 슬롯 간 차이점 반환

    Args:
        slots_a: 첫 번째 슬롯
        slots_b: 두 번째 슬롯

    Returns:
        {
            "slot_name": ("value_a", "value_b"),
            ...
        }
    """
    diff = {}
    for slot in ALL_SLOTS:
        val_a = slots_a.get(slot, "None")
        val_b = slots_b.get(slot, "None")
        if val_a != val_b:
            diff[slot] = (val_a, val_b)

    return diff


if __name__ == "__main__":
    # 테스트 코드

    # 예시 슬롯 데이터
    slots_1 = {
        "silhouette": "Oversized boxy",
        "main_color": "Pure white",
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

    slots_2 = {
        "silhouette": "Fitted cropped",
        "main_color": "Navy blue",
        "accent_color": "Gold",
        "material_base": "Wool blend",
        "material_accent": "Satin lining",
        "pattern": "Solid",
        "collar_neckline": "Notched lapel",
        "sleeve_arm": "Long sleeve",
        "pocket": "Welt pockets",
        "closure": "Buttons",
        "hem_edge": "Straight hem",
        "logo_branding": "Gold buttons",
        "hardware": "Gold buttons",
        "details": "None"
    }

    # 믹싱 테스트
    selections = {
        "silhouette": 0,      # slots_1
        "main_color": 1,      # slots_2
        "collar_neckline": 1  # slots_2
    }

    merged = merge_slots([slots_1, slots_2], selections)

    print("📋 믹싱 결과:")
    for slot, value in merged.items():
        source = ""
        if slot in selections:
            source = f" (from image {selections[slot] + 1})"
        print(f"  • {slot:20s} → {value}{source}")

    # 차이점 확인
    print("\n📊 슬롯 차이:")
    diff = diff_slots(slots_1, slots_2)
    for slot, (val_a, val_b) in diff.items():
        print(f"  • {slot:20s}: {val_a} → {val_b}")
