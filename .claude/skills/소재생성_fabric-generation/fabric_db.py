"""
소재 DB 관리 - 유사도 매칭 및 등록
"""

import os
import json


def find_similar_texture(attributes: dict, db_path: str = "db/fabric_library.json", top_k: int = 3) -> list:
    """
    10단계 속성 → DB에서 유사한 원단 찾기

    Args:
        attributes: 10단계 속성 dict
        db_path: DB 파일 경로
        top_k: 상위 몇 개 반환할지

    Returns:
        [
            {"name": "Cotton Twill", "similarity": 95, "entry": {...}},
            ...
        ]
    """
    if not os.path.exists(db_path):
        print(f"⚠️  DB 파일 없음: {db_path}")
        return []

    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    attr_keys = ["thickness", "glossiness", "softness", "texture", "stretch",
                 "transparency", "weight", "breathability", "drape", "durability"]

    results = []
    # 배열 형식: db["fabrics"] 순회
    for fabric in db.get("fabrics", []):
        # attributes가 최상위 레벨에 있는 경우와 nested 경우 모두 처리
        fabric_attrs = fabric.get("attributes", {})

        # 유클리드 거리 계산
        dist = sum((attributes.get(k, 5) - fabric_attrs.get(k, 5)) ** 2 for k in attr_keys)
        similarity = max(0, 100 - (dist ** 0.5) * 3)  # 0-100 스케일
        results.append({
            "name": fabric.get("name", fabric.get("id", "unknown")),
            "similarity": round(similarity, 1),
            "entry": fabric
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def register_to_db(name: str, attributes: dict, image_path: str, db_path: str = "db/fabric_library.json"):
    """
    생성된 원단을 DB에 등록

    Args:
        name: 원단 이름
        attributes: 10단계 속성
        image_path: 생성된 이미지 경로
        db_path: DB 파일 경로
    """
    # DB 디렉토리 생성
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 기존 DB 로드 or 신규 생성
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        db = {"fabrics": []}

    # fabrics 배열 초기화 (호환성)
    if "fabrics" not in db:
        db["fabrics"] = []

    # 새 엔트리 생성 (배열 형식)
    new_entry = {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "attributes": attributes,
        "image_path": image_path,
        "created_at": __import__('datetime').datetime.now().isoformat()
    }

    # 배열에 추가
    db["fabrics"].append(new_entry)

    # DB 저장
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"✅ Registered '{name}' to DB ({len(db['fabrics'])} total entries)")
