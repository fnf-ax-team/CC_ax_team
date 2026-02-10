"""
MLB 브랜드컷 생성 모듈
- 얼굴 + 착장 이미지 → AI 화보 생성
- Gemini API 사용

Version: 1.0.0
Date: 2026-02-10
"""

import os
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 설정
# ============================================================
IMAGE_MODEL = "gemini-3-pro-image-preview"
VISION_MODEL = "gemini-3-flash-preview"


def get_api_key() -> str:
    """API 키 로테이션"""
    keys = os.getenv("GEMINI_API_KEY", "").split(",")
    return keys[0].strip() if keys else ""


def load_images_from_folder(folder_path: str, max_images: int = 10) -> List[Image.Image]:
    """폴더에서 이미지 로드"""
    images = []
    folder = Path(folder_path)

    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
        for img_path in sorted(folder.glob(ext))[:max_images]:
            try:
                img = Image.open(img_path).convert("RGB")
                images.append(img)
            except Exception as e:
                print(f"Failed to load {img_path.name}: {e}")

    return images


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(
        mime_type="image/png",
        data=buf.getvalue()
    ))


def analyze_outfit(outfit_images: List[Image.Image], api_key: str) -> Dict[str, Any]:
    """VLM으로 착장 분석"""
    client = genai.Client(api_key=api_key)

    prompt = """
착장 이미지들을 분석하여 AI가 놓치기 쉬운 디테일을 추출하세요.

반드시 포함:
1. 아이템별 색상 (정확한 색상명)
2. 로고/그래픽 위치와 디자인
3. 소재 질감
4. 특이 디테일 (스트라이프, 배색, 자수 등)

JSON 형식으로 출력:
{
  "outer": {"item": "", "color": "", "details": [], "logo_position": ""},
  "top": {"item": "", "color": "", "details": [], "logo_position": ""},
  "bottom": {"item": "", "color": "", "details": []},
  "shoes": {"item": "", "color": ""},
  "headwear": {"item": "", "color": "", "logo_position": ""},
  "bag": {"item": "", "color": "", "details": []},
  "accessories": []
}
"""

    parts = [types.Part(text=prompt)]
    for img in outfit_images:
        parts.append(pil_to_part(img))

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(temperature=0.1)
    )

    # JSON 파싱 시도
    try:
        text = response.text
        # JSON 블록 추출
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except:
        return {"raw_analysis": response.text}


def build_brandcut_prompt(
    outfit_analysis: Dict[str, Any],
    variation: int = 0,
    has_vehicle: bool = False
) -> Dict[str, Any]:
    """치트시트 기반 프롬프트 조립"""

    # 포즈 변형
    pose_variations = [
        {
            "stance": "confident standing pose, weight shifted to one leg, contrapposto stance",
            "left_arm": "arm bent at elbow, hand near face",
            "right_arm": "arm hanging naturally",
            "framing": "medium full shot, knees up",
            "angle": "camera 15 degrees to subject's side, 3/4 profile view",
        },
        {
            "stance": "relaxed lean against wall, casual cool posture",
            "left_arm": "hand casually in pocket",
            "right_arm": "arm relaxed at side",
            "framing": "medium shot framing, waist up",
            "angle": "camera at eye level, frontal angle",
        },
        {
            "stance": "confident standing pose, weight balanced",
            "left_arm": "arm hanging naturally",
            "right_arm": "hand on hip with attitude",
            "framing": "medium full shot, knees up",
            "angle": "camera 10 degrees off-center",
        }
    ]

    v = pose_variations[variation % len(pose_variations)]

    # 배경 설정
    if has_vehicle:
        background = {
            "장소": "luxury SUV parking area",
            "배경상세": "silver luxury SUV (Mercedes G-Class or Range Rover) parked in clean modern parking structure, polished concrete floor, soft natural daylight"
        }
        v["stance"] = "relaxed lean against luxury vehicle"
    else:
        background = {
            "장소": "industrial studio setting",
            "배경상세": "clean brushed metal panels and raw concrete walls, minimalist modern backdrop, soft diffused lighting"
        }

    # 착장 설명 조립
    outfit_desc = "CRITICAL OUTFIT REQUIREMENTS - COPY EXACTLY:\n"
    if outfit_analysis.get("outer"):
        o = outfit_analysis["outer"]
        outfit_desc += f"1. OUTER: {o.get('item', '')} - {o.get('color', '')}, {', '.join(o.get('details', []))}\n"
    if outfit_analysis.get("top"):
        t = outfit_analysis["top"]
        outfit_desc += f"2. TOP: {t.get('item', '')} - {t.get('color', '')}, {', '.join(t.get('details', []))}\n"
    if outfit_analysis.get("bottom"):
        b = outfit_analysis["bottom"]
        outfit_desc += f"3. BOTTOM: {b.get('item', '')} - {b.get('color', '')}, {', '.join(b.get('details', []))}\n"
    if outfit_analysis.get("headwear"):
        h = outfit_analysis["headwear"]
        outfit_desc += f"4. HEADWEAR: {h.get('item', '')} - {h.get('color', '')} - MUST BE VISIBLE\n"
    if outfit_analysis.get("bag"):
        bag = outfit_analysis["bag"]
        outfit_desc += f"5. BAG: {bag.get('item', '')} - {bag.get('color', '')}\n"

    prompt = {
        "주제": {
            "character": "high-end fashion editorial photography, film grain texture",
            "mood": "Young & Rich MLB lifestyle, cool and confident"
        },
        "모델": {
            "instruction": "CRITICAL: Copy the face from reference images EXACTLY",
            "민족": "Korean female model",
            "나이": "early 20s, youthful"
        },
        "헤어": {
            "스타일": "long hair, loose and flowing",
            "컬러": "dark hair",
            "질감": "natural texture"
        },
        "메이크업": {
            "베이스": "natural skin, minimal foundation",
            "립": "MLBB lip color",
            "아이": "natural eye makeup"
        },
        "촬영": {
            "프레이밍": v["framing"],
            "렌즈": "50mm lens, standard portrait perspective",
            "앵글": v["angle"],
            "높이": "camera at eye level",
            "구도": "subject centered in frame",
            "조리개": "f/2.8"
        },
        "포즈": {
            "stance": v["stance"],
            "왼팔": v["left_arm"],
            "오른팔": v["right_arm"],
            "힙": "hips neutral or slightly popped"
        },
        "표정": {
            "베이스": "cool expression, unbothered attitude",
            "시선": "direct but disinterested gaze at camera",
            "입": "mouth closed in neutral position"
        },
        "착장": {
            "instruction": outfit_desc
        },
        "배경": background,
        "조명색감": {
            "조명": "studio lighting with cool temperature, 5500-6000K",
            "색보정": "neutral-cool color grade, NO warm cast"
        },
        "출력품질": "professional fashion photography, high-end editorial, sharp focus",
        "네거티브": "bright smile, teeth showing, golden hour, warm amber, distorted hands, extra fingers"
    }

    return prompt


def generate_brandcut(
    prompt_json: Dict[str, Any],
    face_images: List[Image.Image],
    outfit_images: List[Image.Image],
    concept_image: Optional[Image.Image] = None,
    api_key: Optional[str] = None,
    aspect_ratio: str = "3:4",
    image_size: str = "2K"
) -> Optional[Image.Image]:
    """브랜드컷 이미지 생성"""

    if api_key is None:
        api_key = get_api_key()

    client = genai.Client(api_key=api_key)

    # 프롬프트 텍스트
    prompt_text = f"""
Generate a high-end MLB fashion editorial photograph.

CRITICAL RULES:
1. FACE: Copy the face from [FACE REFERENCE] images EXACTLY
2. OUTFIT: Copy ALL outfit items from [OUTFIT REFERENCE] images EXACTLY
3. STYLE: Match the mood/pose/lighting from [CONCEPT REFERENCE] if provided
4. NO warm/golden tones - use cool neutral color grading only

{json.dumps(prompt_json, ensure_ascii=False, indent=2)}
"""

    parts = [types.Part(text=prompt_text)]

    # 얼굴 이미지 (CRITICAL)
    parts.append(types.Part(text="\n\n[FACE REFERENCE] - Copy this face EXACTLY:"))
    for img in face_images[:3]:
        parts.append(pil_to_part(img))

    # 착장 이미지 (CRITICAL - 1순위)
    parts.append(types.Part(text="\n\n[OUTFIT REFERENCE] - Copy ALL these outfit items EXACTLY:"))
    for img in outfit_images:
        parts.append(pil_to_part(img))

    # 컨셉 레퍼런스
    if concept_image:
        parts.append(types.Part(text="\n\n[CONCEPT REFERENCE] - Match this mood/pose/lighting:"))
        parts.append(pil_to_part(concept_image))

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.25,
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size
            )
        )
    )

    # 이미지 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))

    return None


def validate_brandcut(
    generated_image: Image.Image,
    face_reference: Image.Image,
    outfit_images: List[Image.Image],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """생성된 이미지 품질 검증"""

    if api_key is None:
        api_key = get_api_key()

    client = genai.Client(api_key=api_key)

    prompt = """
생성된 이미지를 평가하세요.

평가 기준 (0-100):
1. photorealism: 실제 사진처럼 보이는지
2. anatomy: 해부학적 정확성 (손가락, 비율)
3. face_identity: 얼굴 동일성
4. outfit_accuracy: 착장 재현도
5. outfit_completeness: 착장 누락 여부

JSON 출력:
{
  "photorealism": 0,
  "anatomy": 0,
  "face_identity": 0,
  "outfit_accuracy": 0,
  "outfit_completeness": 0,
  "pass": true/false,
  "missing_items": [],
  "issues": []
}

Pass 조건: photorealism>=85, anatomy>=90, face_identity>=90, outfit_accuracy>=85
"""

    parts = [types.Part(text=prompt)]
    parts.append(types.Part(text="\n[GENERATED IMAGE]:"))
    parts.append(pil_to_part(generated_image))
    parts.append(types.Part(text="\n[FACE REFERENCE]:"))
    parts.append(pil_to_part(face_reference))
    parts.append(types.Part(text="\n[OUTFIT REFERENCES]:"))
    for img in outfit_images[:3]:
        parts.append(pil_to_part(img))

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(temperature=0.1)
    )

    try:
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except:
        return {"raw_validation": response.text, "pass": False}


def generate_brandcut_batch(
    face_folder: str,
    outfit_folder: str,
    output_folder: str,
    concept_image_path: Optional[str] = None,
    num_images: int = 3,
    has_vehicle: bool = False,
    aspect_ratio: str = "3:4",
    image_size: str = "2K",
    api_key: Optional[str] = None
) -> List[str]:
    """브랜드컷 배치 생성

    Args:
        face_folder: 얼굴 이미지 폴더 경로
        outfit_folder: 착장 이미지 폴더 경로
        output_folder: 출력 폴더 경로
        concept_image_path: 컨셉 레퍼런스 이미지 경로 (선택)
        num_images: 생성할 이미지 수
        has_vehicle: 배경에 차량 포함 여부
        aspect_ratio: 비율 (3:4, 4:5, 9:16 등)
        image_size: 화질 (1K, 2K, 4K)
        api_key: Gemini API 키

    Returns:
        생성된 이미지 파일 경로 목록
    """

    if api_key is None:
        api_key = get_api_key()

    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 이미지 로드
    print("Loading images...")
    face_images = load_images_from_folder(face_folder)
    outfit_images = load_images_from_folder(outfit_folder)

    if not face_images:
        raise ValueError("No face images found!")
    if not outfit_images:
        raise ValueError("No outfit images found!")

    concept_image = None
    if concept_image_path and os.path.exists(concept_image_path):
        concept_image = Image.open(concept_image_path).convert("RGB")

    # 착장 분석
    print("Analyzing outfits...")
    outfit_analysis = analyze_outfit(outfit_images, api_key)

    # 이미지 생성
    results = []
    for i in range(num_images):
        print(f"\nGenerating image {i + 1}/{num_images}...")

        prompt = build_brandcut_prompt(outfit_analysis, i, has_vehicle)

        try:
            image = generate_brandcut(
                prompt,
                face_images,
                outfit_images,
                concept_image,
                api_key,
                aspect_ratio,
                image_size
            )

            if image:
                filename = f"brandcut_{timestamp}_{i + 1}.png"
                filepath = os.path.join(output_folder, filename)
                image.save(filepath, "PNG")
                print(f"  Saved: {filename}")
                results.append(filepath)

        except Exception as e:
            print(f"  Error: {e}")

    return results


# CLI 실행
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MLB Brand Cut Generator")
    parser.add_argument("--face", required=True, help="Face images folder")
    parser.add_argument("--outfit", required=True, help="Outfit images folder")
    parser.add_argument("--output", default="./output", help="Output folder")
    parser.add_argument("--concept", help="Concept reference image")
    parser.add_argument("--num", type=int, default=3, help="Number of images")
    parser.add_argument("--vehicle", action="store_true", help="Include vehicle")
    parser.add_argument("--ratio", default="3:4", help="Aspect ratio")
    parser.add_argument("--quality", default="2K", help="Image quality")

    args = parser.parse_args()

    results = generate_brandcut_batch(
        face_folder=args.face,
        outfit_folder=args.outfit,
        output_folder=args.output,
        concept_image_path=args.concept,
        num_images=args.num,
        has_vehicle=args.vehicle,
        aspect_ratio=args.ratio,
        image_size=args.quality
    )

    print(f"\nGenerated {len(results)} images")
