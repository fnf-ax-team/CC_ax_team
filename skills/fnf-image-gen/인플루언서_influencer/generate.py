"""
인플루언서/셀럽 이미지 생성 스킬 (성별 무관)
사용법: python generate.py [상황] -n [수량]
예: python generate.py 카페 청순 -n 3
"""

import os
import sys
import time
import argparse
from datetime import datetime
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 기본 얼굴 이미지 경로 (설정 필요)
DEFAULT_FACE_DIR = os.path.join(os.path.dirname(__file__), "faces")

def load_api_keys():
    # 프로젝트 루트의 .env 찾기
    current = os.path.dirname(__file__)
    for _ in range(5):
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            break
        current = os.path.dirname(current)

    api_keys = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                    _, value = line.strip().split('=', 1)
                    api_keys.extend([k.strip() for k in value.split(',')])
    return api_keys or [os.environ.get("GEMINI_API_KEY", "")]

API_KEYS = load_api_keys()
key_idx = 0

def get_api_key():
    global key_idx
    key = API_KEYS[key_idx % len(API_KEYS)]
    key_idx += 1
    return key

def pil_to_part(img, max_size=1024):
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

def load_face_images(face_dir=None, face_paths=None):
    """얼굴 이미지 로드"""
    images = []

    if face_paths:
        for p in face_paths:
            if os.path.exists(p):
                images.append(Image.open(p).convert("RGB"))
    elif face_dir and os.path.exists(face_dir):
        for f in os.listdir(face_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(Image.open(os.path.join(face_dir, f)).convert("RGB"))

    return images

def generate_image(prompt, face_images, output_dir):
    """이미지 생성"""
    full_prompt = f"이 얼굴로 {prompt}"

    parts = [types.Part(text=full_prompt)]
    for img in face_images:
        parts.append(pil_to_part(img))

    for attempt in range(3):
        try:
            client = genai.Client(api_key=get_api_key())
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio="9:16",
                        image_size="2K"
                    )
                )
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    result = Image.open(BytesIO(part.inline_data.data))
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"influencer_{timestamp}.png"
                    filepath = os.path.join(output_dir, filename)
                    result.save(filepath, "PNG")
                    return filepath

        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                time.sleep((attempt + 1) * 10)
                continue
            print(f"Error: {e}")
            return None

    return None


def main():
    parser = argparse.ArgumentParser(description='인플루언서 이미지 생성')
    parser.add_argument('prompt', nargs='*', help='상황 설명 (예: 카페 청순)')
    parser.add_argument('-n', '--count', type=int, default=1, help='생성 수량')
    parser.add_argument('-f', '--faces', nargs='+', help='얼굴 이미지 경로들')
    parser.add_argument('-o', '--output', help='출력 폴더')

    args = parser.parse_args()

    # 프롬프트
    prompt = ' '.join(args.prompt) if args.prompt else "예쁜 셀카, 끼부리는 표정"

    # 얼굴 이미지
    face_images = load_face_images(
        face_dir=DEFAULT_FACE_DIR,
        face_paths=args.faces
    )

    if not face_images:
        print("[ERROR] 얼굴 이미지 없음")
        print(f"  - faces 폴더에 이미지 넣기: {DEFAULT_FACE_DIR}")
        print(f"  - 또는 -f 옵션으로 경로 지정")
        return

    print(f"[OK] 얼굴 이미지 {len(face_images)}장 로드")

    # 출력 폴더
    if args.output:
        output_dir = args.output
    else:
        # 프로젝트 루트 찾기
        current = os.path.dirname(__file__)
        for _ in range(5):
            if os.path.exists(os.path.join(current, ".env")):
                break
            current = os.path.dirname(current)
        output_dir = os.path.join(current, "Fnf_studio_outputs", "influencer")

    os.makedirs(output_dir, exist_ok=True)

    # 생성
    print(f"\n프롬프트: {prompt}")
    print(f"수량: {args.count}")
    print(f"출력: {output_dir}\n")

    for i in range(args.count):
        print(f"[{i+1}/{args.count}] 생성 중...")
        result = generate_image(prompt, face_images, output_dir)
        if result:
            print(f"  -> {os.path.basename(result)}")
        else:
            print(f"  -> 실패")

        if i < args.count - 1:
            time.sleep(3)

    print(f"\n완료! 출력 폴더: {output_dir}")


if __name__ == "__main__":
    main()
