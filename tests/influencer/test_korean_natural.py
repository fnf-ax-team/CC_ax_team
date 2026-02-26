#!/usr/bin/env python3
"""
Korean Natural Moments Test: 자연스러운 순간 포착 3가지 버전
==============================================================
목표: 한국어 프롬프트로 AI스럽지 않고 진짜 화보 같은 자연스러운 순간 포착

테스트 조건:
- 얼굴: MLB_KARINA 참조
- 착장: MLB 갈색 바시티 재킷 + 블랙 탱크탑 + 카고진 + 호보백 + 비니
- 스타일 참조: MLB_STYLE (1).jpg
- API: gemini-3-pro-image-preview
- Temperature: 0.4 (고정)
- 한국어 프롬프트

3가지 연출 버전:
V1: 순간 포착 (걷다가 뒤돌아보는 찰나)
V2: 동작 중간 (가방 뒤적이는 순간)
V3: 여유로운 순간 (기대서 쉬는)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List
from PIL import Image
from io import BytesIO

from google import genai
from google.genai import types
from core.config import IMAGE_MODEL, OUTPUT_BASE_DIR

# Import helper functions
from generate_mlb_brandcut import (
    pil_to_part,
    load_face_references,
    load_outfit_images,
    STYLE_REF_DIR,
    ApiKeyManager
)

# ============================================================
# TEST CONFIGURATION
# ============================================================

OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "korean_natural_test")
ASPECT_RATIO = "3:4"
IMAGE_SIZE = "2K"
MAX_IMAGE_DIM = 1024
INTER_IMAGE_DELAY = 8  # seconds between API calls
TEMPERATURE = 0.4  # Fixed temperature for all versions

# ============================================================
# PROMPT BUILDERS (ALL KOREAN)
# ============================================================

def build_prompt_v1_moment() -> str:
    """V1: 순간 포착 (걷다가 뒤돌아보는 찰나)"""
    return """이 얼굴의 한국인 여성 모델.

[착장]
갈색 바시티 재킷 열어입고 안에 블랙 탱크탑(가슴에 작은 NY 로고).
다크 차콜 카고진 와이드핏.
크림색 NY 호보백 오른손에.
다크 차콜 퍼지 비니(NY 로고 오른쪽, 접힌 부분 없음).
긴 생머리가 비니 밑으로.

[순간]
LA 로데오 드라이브를 걷다가 누군가 이름을 불러서 뒤돌아보는 찰나.
"뭐?" 하는 표정으로 어깨 너머로 쳐다보는 순간.
머리카락이 움직임에 살짝 흩날린다.
햇빛이 강하게 내리쬐어 얼굴에 날카로운 그림자.

자연스럽고 즉흥적인 순간. 포즈 취하는 게 아니라 진짜 걷다가 멈춘 느낌.
패션 매거진 스트리트 스냅 같은 자연스러운 화보.

[품질]
초사실적 패션 화보. 진짜 사진과 구분 안 되게.
자연스러운 피부 질감, 모공까지 보이게.
손가락 정확히 5개.
천의 자연스러운 주름과 무게감.
진짜 카메라로 찍은 것 같은 얕은 심도와 보케.

절대 안 됨: 밝은 미소, 인위적인 포즈, 다른 사람들, 만화 느낌, 플라스틱 피부"""


def build_prompt_v2_bag() -> str:
    """V2: 동작 중간 (가방 뒤적이는 순간)"""
    return """이 얼굴의 한국인 여성 모델.

[착장]
갈색 바시티 재킷 열어입고 안에 블랙 탱크탑(가슴에 작은 NY 로고).
다크 차콜 카고진 와이드핏.
크림색 NY 호보백 오른손에.
다크 차콜 퍼지 비니(NY 로고 오른쪽, 접힌 부분 없음).
긴 생머리가 비니 밑으로.

[순간]
LA 로데오 드라이브 카페 앞에서 잠깐 멈춰 서서
호보백에서 뭔가 찾으려고 가방 안을 들여다보는 순간.
고개를 살짝 숙이고 한 손은 가방 안에.
"어디 뒀더라" 하는 집중한 표정.
햇빛 아래 자연스러운 그림자.

포즈가 아니라 진짜 일상의 한 순간처럼.
파파라치가 몰래 찍은 것 같은 자연스러운 스냅.

[품질]
초사실적 패션 화보. 진짜 사진과 구분 안 되게.
자연스러운 피부 질감, 모공까지 보이게.
손가락 정확히 5개.
천의 자연스러운 주름과 무게감.
진짜 카메라로 찍은 것 같은 얕은 심도와 보케.

절대 안 됨: 밝은 미소, 인위적인 포즈, 다른 사람들, 만화 느낌, 플라스틱 피부"""


def build_prompt_v3_lean() -> str:
    """V3: 여유로운 순간 (기대서 쉬는)"""
    return """이 얼굴의 한국인 여성 모델.

[착장]
갈색 바시티 재킷 열어입고 안에 블랙 탱크탑(가슴에 작은 NY 로고).
다크 차콜 카고진 와이드핏.
크림색 NY 호보백 오른손에.
다크 차콜 퍼지 비니(NY 로고 오른쪽, 접힌 부분 없음).
긴 생머리가 비니 밑으로.

[순간]
LA 로데오 드라이브 고급 매장 유리벽에 한쪽 어깨를 기대고 서 있다.
한 손은 주머니에, 한 손은 가방 끈을 느슨하게.
먼 곳을 바라보며 생각에 잠긴 표정.
"뭐 할까" 하는 약간 지루한 듯한 무표정.
햇빛이 옆에서 비춰 얼굴 반쪽에 그림자.

포즈가 아니라 진짜 쉬고 있는 순간.
친구가 몰래 찍은 것 같은 자연스러운 느낌.

[품질]
초사실적 패션 화보. 진짜 사진과 구분 안 되게.
자연스러운 피부 질감, 모공까지 보이게.
손가락 정확히 5개.
천의 자연스러운 주름과 무게감.
진짜 카메라로 찍은 것 같은 얕은 심도와 보케.

절대 안 됨: 밝은 미소, 인위적인 포즈, 다른 사람들, 만화 느낌, 플라스틱 피부"""


# ============================================================
# IMAGE GENERATION
# ============================================================

def generate_image_korean_natural(
    prompt: str,
    face_parts: List,
    outfit_parts: List,
    style_part,
    api_key: str,
) -> Image.Image:
    """Generate image with Korean natural moment prompt."""
    client = genai.Client(api_key=api_key)

    # Combine all parts
    prompt_parts = [types.Part(text=prompt)]
    prompt_parts.append(style_part)  # Style reference
    prompt_parts.extend(face_parts)  # Face references
    prompt_parts.extend(outfit_parts)  # Outfit references

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=prompt_parts)],
        config=types.GenerateContentConfig(
            temperature=TEMPERATURE,
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio=ASPECT_RATIO,
                image_size=IMAGE_SIZE,
            ),
        ),
    )

    # Extract image
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))

    raise RuntimeError("No image data in API response")


# ============================================================
# MAIN TEST LOGIC
# ============================================================

def run_korean_natural_test():
    """Run Korean natural moments test."""
    print("=" * 70)
    print("KOREAN NATURAL MOMENTS TEST")
    print("=" * 70)

    # Setup output directory
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    test_dir = os.path.join(OUTPUT_DIR, f"natural_{timestamp}")
    os.makedirs(test_dir, exist_ok=True)
    print(f"\n[OUTPUT] {test_dir}\n")

    # Load API key
    import dotenv
    dotenv.load_dotenv()
    api_keys = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()]
    if not api_keys:
        raise ValueError("No GEMINI_API_KEY in .env")
    key_manager = ApiKeyManager(api_keys)
    api_key = key_manager.get_key()

    # Load references
    print("[1/5] Loading face references...")
    face_imgs = load_face_references()
    face_parts = [pil_to_part(img, MAX_IMAGE_DIM) for img in face_imgs]
    print(f"      Loaded {len(face_parts)} face references\n")

    print("[2/5] Loading outfit images...")
    outfit_items = load_outfit_images()
    outfit_parts = [pil_to_part(img, MAX_IMAGE_DIM) for _, img in outfit_items]
    print(f"      Loaded {len(outfit_parts)} outfit items\n")

    print("[3/5] Loading style reference...")
    style_ref_path = os.path.join(STYLE_REF_DIR, "MLB_STYLE (1).jpg")
    if not os.path.exists(style_ref_path):
        raise FileNotFoundError(f"Style ref not found: {style_ref_path}")
    style_img = Image.open(style_ref_path).convert("RGB")
    style_part = pil_to_part(style_img, MAX_IMAGE_DIM)
    print(f"      Loaded MLB_STYLE (1).jpg\n")

    # Test configurations
    test_configs = [
        {
            "version": "v1_moment",
            "prompt_builder": build_prompt_v1_moment,
            "description": "순간 포착 (걷다가 뒤돌아보는 찰나)",
            "filename": "kr_v1_moment.png",
        },
        {
            "version": "v2_bag",
            "prompt_builder": build_prompt_v2_bag,
            "description": "동작 중간 (가방 뒤적이는 순간)",
            "filename": "kr_v2_bag.png",
        },
        {
            "version": "v3_lean",
            "prompt_builder": build_prompt_v3_lean,
            "description": "여유로운 순간 (기대서 쉬는)",
            "filename": "kr_v3_lean.png",
        },
    ]

    print("[4/5] Generating images for each version...")
    results = []
    all_metadata = {
        "test_name": "Korean Natural Moments",
        "timestamp": datetime.now().isoformat(),
        "temperature": TEMPERATURE,
        "model": IMAGE_MODEL,
        "versions": []
    }

    for i, config in enumerate(test_configs, 1):
        version = config["version"]
        print(f"\n[{i}/3] Version {version}: {config['description']}")
        print(f"      Temperature: {TEMPERATURE}")

        # Build prompt
        prompt = config["prompt_builder"]()

        # Generate image
        try:
            print(f"      Generating image...")
            start_time = time.time()

            img = generate_image_korean_natural(
                prompt=prompt,
                face_parts=face_parts,
                outfit_parts=outfit_parts,
                style_part=style_part,
                api_key=api_key,
            )

            elapsed = time.time() - start_time

            # Save image
            img_path = os.path.join(test_dir, config["filename"])
            img.save(img_path, "PNG")
            print(f"      [OK] Saved: {img_path} ({elapsed:.1f}s)")

            # Add to metadata
            version_metadata = {
                "version": version,
                "description": config["description"],
                "filename": config["filename"],
                "generation_time_seconds": elapsed,
                "prompt": prompt,
                "success": True,
            }
            all_metadata["versions"].append(version_metadata)

            results.append({
                "version": version,
                "description": config["description"],
                "filename": config["filename"],
                "generation_time": elapsed,
                "success": True,
            })

            # Rate limiting
            if i < len(test_configs):
                print(f"      Waiting {INTER_IMAGE_DELAY}s before next generation...")
                time.sleep(INTER_IMAGE_DELAY)

        except Exception as e:
            print(f"      [FAIL] FAILED: {str(e)[:150]}")

            version_metadata = {
                "version": version,
                "description": config["description"],
                "filename": config["filename"],
                "success": False,
                "error": str(e),
            }
            all_metadata["versions"].append(version_metadata)

            results.append({
                "version": version,
                "description": config["description"],
                "filename": config["filename"],
                "success": False,
                "error": str(e),
            })

    # Save unified metadata
    print(f"\n[5/5] Saving unified metadata...")
    metadata_path = os.path.join(test_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    print(f"      [OK] Saved: metadata.json\n")

    # Generate comparison report
    print(f"Generating comparison report...")
    report_path = os.path.join(test_dir, "comparison_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Korean Natural Moments Test - Comparison Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Test Configuration\n\n")
        f.write(f"- **Model**: {IMAGE_MODEL}\n")
        f.write(f"- **Temperature**: {TEMPERATURE} (고정)\n")
        f.write(f"- **Face References**: MLB_KARINA\n")
        f.write(f"- **Outfit Items**: {len(outfit_items)} items\n")
        f.write(f"- **Style Reference**: MLB_STYLE (1).jpg\n")
        f.write(f"- **Language**: 한국어 프롬프트\n\n")

        f.write("## Test Concept\n\n")
        f.write("AI스럽지 않고 진짜 화보 같은 자연스러운 순간 포착\n\n")
        f.write("- V1: 순간 포착 (걷다가 뒤돌아보는 찰나)\n")
        f.write("- V2: 동작 중간 (가방 뒤적이는 순간)\n")
        f.write("- V3: 여유로운 순간 (기대서 쉬는)\n\n")

        f.write("## Results\n\n")
        for result in results:
            f.write(f"### {result['version']}: {result['description']}\n\n")

            if result['success']:
                f.write(f"- **Generation Time**: {result['generation_time']:.1f}s\n")
                f.write(f"- **Filename**: `{result['filename']}`\n")
                f.write(f"- **Status**: ✓ Success\n\n")
                f.write(f"![{result['version']}]({result['filename']})\n\n")
            else:
                f.write(f"- **Status**: ✗ Failed\n")
                f.write(f"- **Error**: {result.get('error', 'Unknown error')}\n\n")

        f.write("## Evaluation Criteria\n\n")
        f.write("각 이미지를 다음 기준으로 평가하세요:\n\n")
        f.write("1. **자연스러움** (0-100%)\n")
        f.write("   - 포즈가 자연스러운가? (인위적이지 않은가?)\n")
        f.write("   - 진짜 순간을 포착한 것 같은가?\n")
        f.write("   - AI 느낌이 나지 않는가?\n\n")
        f.write("2. **착장 정확도** (0-100%)\n")
        f.write("   - 모든 아이템이 올바르게 착용되었는가?\n")
        f.write("   - 로고 위치가 정확한가?\n")
        f.write("   - 색상/재질/핏이 올바른가?\n\n")
        f.write("3. **화보 품질** (0-100%)\n")
        f.write("   - 패션 매거진 화보 수준인가?\n")
        f.write("   - 조명과 피부 질감이 자연스러운가?\n")
        f.write("   - 전문 카메라로 찍은 것 같은가?\n\n")
        f.write("4. **얼굴 일관성** (0-100%)\n")
        f.write("   - 참조 얼굴(Karina)과 동일 인물로 보이는가?\n")
        f.write("   - 한국인 특징이 유지되었는가?\n\n")

        f.write("## Notes\n\n")
        f.write("- 전체 메타데이터는 `metadata.json` 참조\n")
        f.write("- 모든 프롬프트는 한국어로 작성됨\n")
        f.write("- Temperature는 0.4로 고정\n")
        f.write("- 폴더 나누지 않고 파일명으로 구분\n")

    print(f"      [OK] Report saved: {report_path}\n")

    # Summary
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"\nOutput directory: {test_dir}\n")
    print("Results:")
    for result in results:
        status = "[OK]" if result['success'] else "[FAIL]"
        print(f"  {status} {result['version']}: {result['description']}")
    print(f"\nComparison report: {report_path}\n")


if __name__ == "__main__":
    run_korean_natural_test()
