"""
VLM 슬롯 추출기
이미지에서 14개 디자인 슬롯을 VLM을 사용하여 추출
"""

import json
import sys
from pathlib import Path
from PIL import Image
import google.generativeai as genai

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from core.config import VISION_MODEL


# VLM 슬롯 추출 프롬프트 (영문)
EXTRACTION_PROMPT = """
Analyze this product image and extract design elements into 14 slots.
Return ONLY a JSON object with these exact keys:

{
  "silhouette": "describe overall shape/fit",
  "main_color": "primary color",
  "accent_color": "secondary color or 'None'",
  "material_base": "main fabric/material",
  "material_accent": "secondary material or 'None'",
  "pattern": "pattern/print type",
  "collar_neckline": "collar or neckline style",
  "sleeve_arm": "sleeve style",
  "pocket": "pocket type or 'None'",
  "closure": "closure method",
  "hem_edge": "hem/edge finish",
  "logo_branding": "branding elements or 'None'",
  "hardware": "hardware details or 'None'",
  "details": "other notable details or 'None'"
}

Guidelines:
- Be specific and descriptive (e.g., "Navy blue" not "blue")
- Use "None" for absent elements, not empty string
- Focus on visible, objective features
- Use fashion industry standard terms
"""


def extract_slots_vlm(image_path: str) -> dict:
    """
    VLM을 사용하여 이미지에서 14개 슬롯 추출

    Args:
        image_path: 분석할 이미지 경로

    Returns:
        {
            "silhouette": "Oversized boxy",
            "main_color": "Pure white",
            "accent_color": "None",
            ...
        }
    """
    # API 키 설정 (환경변수에서 자동 로드됨)
    # genai.configure() 는 SDK가 자동으로 처리

    # 이미지 로드
    image = Image.open(image_path)

    # VLM 모델 생성
    model = genai.GenerativeModel(VISION_MODEL)

    # 분석 요청
    response = model.generate_content([
        EXTRACTION_PROMPT,
        image
    ])

    # JSON 파싱
    try:
        # 응답에서 JSON 부분만 추출
        text = response.text.strip()

        # 코드 블록 제거
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        if text.startswith("json"):
            text = text[4:].strip()

        slots = json.loads(text)

        # 슬롯 검증 (필수 키 확인)
        required_slots = [
            "silhouette", "main_color", "accent_color",
            "material_base", "material_accent", "pattern",
            "collar_neckline", "sleeve_arm", "pocket",
            "closure", "hem_edge", "logo_branding",
            "hardware", "details"
        ]

        for slot in required_slots:
            if slot not in slots:
                slots[slot] = "None"

        return slots

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON 파싱 실패: {e}")
        print(f"응답 내용:\n{response.text}")

        # 기본값 반환
        return {
            "silhouette": "Unknown",
            "main_color": "Unknown",
            "accent_color": "None",
            "material_base": "Unknown",
            "material_accent": "None",
            "pattern": "Solid",
            "collar_neckline": "Unknown",
            "sleeve_arm": "Unknown",
            "pocket": "None",
            "closure": "Unknown",
            "hem_edge": "Unknown",
            "logo_branding": "None",
            "hardware": "None",
            "details": "None"
        }


def save_slots(slots: dict, output_path: str):
    """슬롯 정보를 JSON 파일로 저장"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(slots, f, indent=2, ensure_ascii=False)


def load_slots(input_path: str) -> dict:
    """JSON 파일에서 슬롯 정보 로드"""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # 테스트 코드
    import sys

    if len(sys.argv) < 2:
        print("사용법: python slot_extractor.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print(f"🔍 이미지 분석 중: {image_path}")
    slots = extract_slots_vlm(image_path)

    print("\n📋 추출된 슬롯:")
    for slot, value in slots.items():
        print(f"  • {slot:20s} → {value}")

    # JSON 저장
    output_path = "extracted_slots.json"
    save_slots(slots, output_path)
    print(f"\n💾 저장 완료: {output_path}")
