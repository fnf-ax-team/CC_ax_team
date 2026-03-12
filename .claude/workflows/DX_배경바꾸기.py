"""
DX_배경바꾸기 - 배경 교체 워크플로우
====================================

기능:
- 여러 이미지의 배경을 모던 인더스트리얼 스타일로 교체
- 각 이미지당 여러 시안 생성
- 2K 고해상도 출력
- 병렬 처리로 빠른 생성

사용법:
1. INPUT_DIR에 입력 폴더 경로 설정
2. python DX_배경바꾸기.py 실행

설정 변경:
- NUM_VARIATIONS: 시안 개수 (기본 3)
- TARGET_SIZE: 출력 해상도 (기본 2048)
- MAX_WORKERS: 병렬 워커 수 (기본 6)
"""

import os
import sys
import json
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

# core.config import를 위한 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core.config import OUTPUT_BASE_DIR

# ============================================================
# 설정 - 여기서 수정하세요
# ============================================================

# 입력 폴더 경로 (직접 지정)
INPUT_DIR = None  # None이면 자동 탐색, 경로 지정시 해당 폴더 사용
# 예: INPUT_DIR = r"C:\Users\AC1060\Pictures\my_images"

# 출력 폴더
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "DX_배경바꾸기_결과")

# 생성 설정
NUM_VARIATIONS = 3      # 각 이미지당 시안 개수
TARGET_SIZE = 2048      # 출력 해상도 (2K)
MAX_WORKERS = 6         # 동시 처리 수

# 배경 스타일
BACKGROUND_STYLE = "modern_industrial"  # 현재: 모던 인더스트리얼

# ============================================================
# 프롬프트
# ============================================================

PROMPTS = {
    "modern_industrial": """
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

MATHEMATICAL REQUIREMENTS:
- Person height / Frame height = 0.97
- Scale factor = 1.0

DO NOT SHRINK. DO NOT SHRINK. DO NOT SHRINK.
The person's size must be IDENTICAL to input.

PERSON PRESERVATION (100% IDENTICAL):
- FACE, BODY, CLOTHING, HAIR: Exact same

BACKGROUND: Modern industrial concrete wall, cool gray tones, metal shutters
MOOD: Editorial, fashion-forward, urban cool
""",
    "luxury_european": """
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. The person's size must be IDENTICAL to input.

PERSON PRESERVATION (100% IDENTICAL):
- FACE, BODY, CLOTHING, HAIR: Exact same

BACKGROUND: Elegant European architecture, cream/beige stone buildings, Parisian style
MOOD: Luxurious, sophisticated, timeless elegance
""",
    "nature_minimal": """
EXTREME CLOSE-UP - 97% FRAME FILL - SCALE 1:1

DO NOT SHRINK. The person's size must be IDENTICAL to input.

PERSON PRESERVATION (100% IDENTICAL):
- FACE, BODY, CLOTHING, HAIR: Exact same

BACKGROUND: Minimal natural setting, soft greenery, clean outdoor environment
MOOD: Fresh, natural, peaceful
"""
}

# ============================================================
# 코드 (수정 불필요)
# ============================================================

def load_env():
    """환경변수 로드"""
    # 프로젝트 루트의 .env 파일 찾기
    current = os.path.dirname(__file__)
    for _ in range(5):
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if ',' in value:
                            value = value.split(',')[0].strip()
                        os.environ[key] = value
            return True
        current = os.path.dirname(current)
    return False

load_env()
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
IMAGE_MODEL = "gemini-3-pro-image-preview"


def get_aspect_ratio(width, height):
    ratio = width / height
    ratios = {"1:1": 1.0, "3:4": 0.75, "4:3": 1.333, "9:16": 0.5625, "16:9": 1.778, "2:3": 0.667, "3:2": 1.5, "4:5": 0.8, "5:4": 1.25}
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))


def find_default_folder():
    """기본 테스트 폴더 자동 탐색"""
    base = os.path.expanduser("~")
    onedrive = os.path.join(base, 'OneDrive - F&F (1)')

    if not os.path.exists(onedrive):
        return None

    for item in os.listdir(onedrive):
        item_path = os.path.join(onedrive, item)
        if os.path.isdir(item_path):
            try:
                if '2025' in os.listdir(item_path):
                    path_2025 = os.path.join(item_path, '2025')
                    for folder in os.listdir(path_2025):
                        if '260112' in folder:
                            folder_path = os.path.join(path_2025, folder)
                            for sub in os.listdir(folder_path):
                                sub_path = os.path.join(folder_path, sub)
                                if os.path.isdir(sub_path):
                                    contents = os.listdir(sub_path)
                                    numbered = [f for f in contents if f.split('.')[0].isdigit() and f.endswith(('.png', '.jpg'))]
                                    if len(numbered) == 8:
                                        return sub_path
            except:
                pass
    return None


def generate_single(args) -> dict:
    """단일 시안 생성"""
    image_path, image_name, variation_num, original_size, prompt = args

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    img = Image.open(image_path).convert('RGB')
    max_size = 1024
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    aspect_ratio = get_aspect_ratio(*img.size)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    result = {
        "image": image_name,
        "variation": variation_num,
        "status": "pending",
        "output": None
    }

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=[
                types.Part(text=prompt),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes)),
            ])],
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
            )
        )

        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                result_image = Image.open(BytesIO(part.inline_data.data))

                w, h = original_size
                if w > h:
                    new_w, new_h = TARGET_SIZE, int(TARGET_SIZE * h / w)
                else:
                    new_h, new_w = TARGET_SIZE, int(TARGET_SIZE * w / h)

                result_image = result_image.resize((new_w, new_h), Image.LANCZOS)

                output_name = f"{os.path.splitext(image_name)[0]}_v{variation_num}_{TIMESTAMP}.png"
                output_path = os.path.join(OUTPUT_DIR, output_name)
                result_image.save(output_path, quality=95)

                result["status"] = "success"
                result["output"] = output_name
                result["size"] = f"{new_w}x{new_h}"
                break

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:50]

    return result


def run(input_dir=None):
    """메인 실행"""
    print("=" * 60)
    print("DX_배경바꾸기 - Background Swap Workflow")
    print(f"Style: {BACKGROUND_STYLE}")
    print(f"{NUM_VARIATIONS} variations x {TARGET_SIZE}px, {MAX_WORKERS} workers")
    print("=" * 60)

    # 입력 폴더 결정
    if input_dir:
        folder = input_dir
    elif INPUT_DIR:
        folder = INPUT_DIR
    else:
        folder = find_default_folder()

    if not folder or not os.path.exists(folder):
        print("ERROR: Input folder not found")
        print("Please set INPUT_DIR in the script")
        return

    print(f"Input: {folder}")
    print(f"Output: {OUTPUT_DIR}")

    # 이미지 목록
    image_files = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    if not image_files:
        print("ERROR: No images found in folder")
        return

    print(f"\n{len(image_files)} images x {NUM_VARIATIONS} = {len(image_files) * NUM_VARIATIONS} generations")
    print("=" * 60)

    # 프롬프트 선택
    prompt = PROMPTS.get(BACKGROUND_STYLE, PROMPTS["modern_industrial"])

    # 작업 준비
    tasks = []
    for img_name in image_files:
        img_path = os.path.join(folder, img_name)
        original_size = Image.open(img_path).size
        for v in range(1, NUM_VARIATIONS + 1):
            tasks.append((img_path, img_name, v, original_size, prompt))

    print(f"\nStarting parallel generation...")
    print("-" * 60)

    t_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(generate_single, task): task for task in tasks}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "OK" if result["status"] == "success" else "ERR"
            size = result.get("size", "")
            print(f"  [{status}] {result['image']}_v{result['variation']} {size}")

    elapsed = time.time() - t_start
    success = sum(1 for r in results if r["status"] == "success")

    # 로그 저장
    log_data = {
        "timestamp": TIMESTAMP,
        "input_dir": folder,
        "output_dir": OUTPUT_DIR,
        "style": BACKGROUND_STYLE,
        "num_variations": NUM_VARIATIONS,
        "target_size": TARGET_SIZE,
        "results": results
    }
    with open(os.path.join(OUTPUT_DIR, f"log_{TIMESTAMP}.json"), "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"COMPLETE! {success}/{len(results)} in {elapsed:.1f}s")
    print(f"({elapsed/len(results):.1f}s per image)")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not found")
        print("Please set GEMINI_API_KEY in .env file")
        exit(1)
    run()
