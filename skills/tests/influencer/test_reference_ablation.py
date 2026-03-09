# -*- coding: utf-8 -*-
"""
AI Influencer Reference Ablation Test
=====================================

Tests ALL image reference combinations (A-H) to measure quality impact.

Test Cases:
- A: Text Only (face + outfit only)
- B: + Pose Reference
- C: + Background Reference
- D: + Pose + Background (minimal text prompt)
- E: + Expression Only
- F: Pose + Expression
- G: All References (pose + expression + background)
- H: Temperature Ablation (0.3, 0.5, 0.7)

Uses prompt schema from db/influencer_prompt_schema.json

Author: FNF AX Team
Date: 2026-02-25
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import shutil
import time
import traceback

# Project root setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables BEFORE importing core modules
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from PIL import Image

# ============================================================
# TEST CONFIGURATION
# ============================================================
NUM_SAMPLES = 1  # Start with 1 for quick validation, increase to 5 for full test
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"
BASE_TEMPERATURE = 0.5

# User-provided test images
FACE_IMAGE = Path(r"D:\FNF_Studio_TEST\New-fnf-studio\AI인플\시안2\시안이 (9).png")
OUTFIT_TOP = Path(
    r"D:\FNF_Studio_TEST\New-fnf-studio\AI인플\착장\스크린샷 2026-02-24 110620.png"
)
OUTFIT_BOTTOM = Path(r"c:\Users\AC1060\Downloads\스크린샷 2026-02-25 112008.png")

# Preset image paths
PRESET_BASE = Path(
    r"C:\Users\AC1060\OneDrive - F&F (1)\바탕 화면\2025\260219_AI인플\OneDrive_2026-02-19 (2)"
)

# Output directory
OUTPUT_BASE = project_root / "Fnf_studio_outputs" / "ai_influencer_ablation"

# ============================================================
# PROMPT SCHEMA (from db/influencer_prompt_schema.json)
# ============================================================
PROMPT_SCHEMA = {
    "모델": {"국적": "한국인", "성별": "여성", "나이": "20대 초반"},
    "헤어": {"스타일": "wavy", "컬러": "dark_brown", "질감": "sleek"},
    "표정": {
        "베이스": "cool",
        "바이브": "effortless, unbothered",
        "눈": "큰 눈",
        "시선": "direct",
        "입": "slightly parted",
    },
    "포즈": {"stance": "stand", "힙": "자연스러운 무게중심"},
    "배경": {
        "지역": "한국",
        "시간대": "주간",
        "색감": "모던, 힙, 감각적",
        "장소": "트렌디한 핫플 카페. 인스타그래머블한 인테리어, 감각적인 소품, 자연광이 들어오는 공간.",
        "분위기": "힙하고 감각적인 카페 분위기",
    },
    "스타일링": {
        "overall_vibe": "스트릿 캐주얼",
        "아이템": {
            "상의": "MLB 화이트 크롭탑 with 블랙 NY 로고",
            "하의": "네이비 와이드 팬츠 with 필기체 자수",
        },
        "코디방법": {"상의": "크롭_배꼽노출", "하의": "정상착용"},
    },
    "비주얼_무드": {
        "필름_텍스처": {
            "질감": "slight grain, urban gritty feel",
            "보정법": "lifted blacks, street style edit",
        },
        "컬러_그레이딩": {
            "주요색조": "cool neutral",
            "채도": "natural",
            "노출": "balanced daylight",
        },
        "조명": {
            "광원": "natural daylight",
            "방향": "side lighting",
            "그림자": "medium contrast",
        },
    },
    "촬영_세팅": {
        "프레이밍": "FS",
        "렌즈": "35mm",
        "앵글": "약간측면",
        "높이": "살짝로앵글",
        "구도": "중앙",
        "조리개": "f/2.8",
    },
    "네거티브": "bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers, AI look, overprocessed",
}


# ============================================================
# PRESET IMAGE FINDER
# ============================================================
def find_preset_image(preset_type: str, subfolder: str = None) -> Path:
    """Find preset image"""
    type_folders = {
        "pose": "3. 포즈",
        "expression": "2. 표정",
        "background": "4. 배경",
    }

    folder = PRESET_BASE / type_folders.get(preset_type, "")
    if not folder.exists():
        print(f"[WARN] Folder not found: {folder}")
        return None

    # If subfolder specified
    if subfolder:
        target_folder = folder / subfolder
        if target_folder.exists():
            for img in target_folder.glob("*.png"):
                return img
            for img in target_folder.glob("*.jpg"):
                return img

    # Search any subfolder
    for sf in folder.iterdir():
        if sf.is_dir():
            for img in sf.glob("*.png"):
                return img
            for img in sf.glob("*.jpg"):
                return img

    # Try root level
    for img in folder.glob("*.png"):
        return img

    return None


# ============================================================
# SCHEMA TO PROMPT TEXT
# ============================================================
def schema_to_prompt_text(
    schema: dict, include_pose: bool = True, include_bg: bool = True
) -> str:
    """Convert schema to structured prompt text"""

    lines = []

    # Model info
    model = schema.get("모델", {})
    lines.append(f"[MODEL]")
    lines.append(
        f"- {model.get('국적', '한국인')} {model.get('성별', '여성')}, {model.get('나이', '20대 초반')}"
    )

    # Hair
    hair = schema.get("헤어", {})
    lines.append(f"\n[HAIR]")
    lines.append(f"- Style: {hair.get('스타일', 'wavy')}")
    lines.append(f"- Color: {hair.get('컬러', 'dark_brown')}")
    lines.append(f"- Texture: {hair.get('질감', 'sleek')}")

    # Expression
    expr = schema.get("표정", {})
    lines.append(f"\n[EXPRESSION]")
    lines.append(f"- Base: {expr.get('베이스', 'cool')}")
    lines.append(f"- Vibe: {expr.get('바이브', 'effortless')}")
    lines.append(f"- Eyes: {expr.get('눈', '큰 눈')}")
    lines.append(f"- Gaze: {expr.get('시선', 'direct')}")
    lines.append(f"- Mouth: {expr.get('입', 'slightly parted')}")

    # Pose (if not using image reference)
    if include_pose:
        pose = schema.get("포즈", {})
        lines.append(f"\n[POSE]")
        lines.append(f"- Stance: {pose.get('stance', 'stand')}")
        lines.append(f"- Hip: {pose.get('힙', '자연스러운 무게중심')}")

    # Background (if not using image reference)
    if include_bg:
        bg = schema.get("배경", {})
        lines.append(f"\n[BACKGROUND]")
        lines.append(f"- Location: {bg.get('지역', '한국/성수')}")
        lines.append(f"- Time: {bg.get('시간대', '주간')}")
        lines.append(f"- Colors: {bg.get('색감', '')}")
        lines.append(f"- Place: {bg.get('장소', '')}")
        lines.append(f"- Mood: {bg.get('분위기', '')}")

    # Styling
    style = schema.get("스타일링", {})
    items = style.get("아이템", {})
    method = style.get("코디방법", {})
    lines.append(f"\n[STYLING]")
    lines.append(f"- Overall: {style.get('overall_vibe', '스트릿 캐주얼')}")
    if items.get("상의"):
        lines.append(f"- Top: {items['상의']}")
        if method.get("상의"):
            lines.append(f"  - Styling: {method['상의']}")
    if items.get("하의"):
        lines.append(f"- Bottom: {items['하의']}")
        if method.get("하의"):
            lines.append(f"  - Styling: {method['하의']}")

    # Visual mood
    mood = schema.get("비주얼_무드", {})
    film = mood.get("필름_텍스처", {})
    color = mood.get("컬러_그레이딩", {})
    light = mood.get("조명", {})
    lines.append(f"\n[VISUAL MOOD]")
    lines.append(f"- Film texture: {film.get('질감', '')}")
    lines.append(
        f"- Color grading: {color.get('주요색조', '')} / {color.get('채도', '')}"
    )
    lines.append(f"- Lighting: {light.get('광원', '')} / {light.get('방향', '')}")

    # Camera
    cam = schema.get("촬영_세팅", {})
    lines.append(f"\n[CAMERA]")
    lines.append(f"- Framing: {cam.get('프레이밍', 'FS')} (Full Shot)")
    lines.append(f"- Lens: {cam.get('렌즈', '35mm')}")
    lines.append(f"- Angle: {cam.get('앵글', '약간측면')}")
    lines.append(f"- Height: {cam.get('높이', '살짝로앵글')}")
    lines.append(f"- Aperture: {cam.get('조리개', 'f/2.8')}")

    # Output quality
    lines.append(f"\n[OUTPUT QUALITY]")
    lines.append(f"- Natural influencer photo, authentic, realistic skin texture")
    lines.append(f"- 9:16 vertical format for Instagram Stories")

    # Negative
    neg = schema.get("네거티브", "")
    lines.append(f"\n[NEGATIVE - MUST AVOID]")
    lines.append(f"- {neg}")

    return "\n".join(lines)


# ============================================================
# BUILD PROMPT WITH IMAGE ROLES
# ============================================================
def build_full_prompt(
    has_pose_ref: bool = False,
    has_expr_ref: bool = False,
    has_bg_ref: bool = False,
) -> str:
    """Build prompt with image role descriptions"""

    parts = []

    # Image roles header
    parts.append("[IMAGE ROLES - CRITICAL]")

    # Pose reference
    if has_pose_ref:
        parts.append("""
[POSE REFERENCE IMAGE]
- Copy EXACT pose, body position, limb placement
- Copy EXACT camera angle, framing, composition
- IGNORE face and outfit from this image""")

    # Expression reference
    if has_expr_ref:
        parts.append("""
[EXPRESSION REFERENCE IMAGE]
- Copy EXACT expression: eyes, mouth, facial muscles
- Copy EXACT mood and vibe
- IGNORE face identity from this image""")

    # Face images
    parts.append("""
[FACE IMAGES]
- Use this person's face EXACTLY
- Keep face identity with HIGH priority (40% weight)
- Natural skin texture, NO plastic look""")

    # Outfit images
    parts.append("""
[OUTFIT IMAGES]
- Use these outfits EXACTLY
- Copy colors, logos, details precisely
- MLB white crop top with black NY logo
- Navy wide pants with cursive embroidery""")

    # Background reference
    if has_bg_ref:
        parts.append("""
[BACKGROUND REFERENCE IMAGE]
- Use this background style and mood
- IGNORE any person in background image
- Match lighting and color temperature""")

    # Add schema-based prompt
    parts.append("\n" + "=" * 50)
    schema_text = schema_to_prompt_text(
        PROMPT_SCHEMA, include_pose=not has_pose_ref, include_bg=not has_bg_ref
    )
    parts.append(schema_text)

    return "\n".join(parts)


# ============================================================
# CASE CONFIGURATIONS
# ============================================================
def get_case_configs():
    """Get all test case configurations (A-H)"""

    pose_img = find_preset_image("pose", "1. 전신")
    expr_img = find_preset_image("expression", "1. 시크")
    bg_img = find_preset_image("background", "1. 핫플카페")

    print(f"[INFO] Pose image: {pose_img}")
    print(f"[INFO] Expression image: {expr_img}")
    print(f"[INFO] Background image: {bg_img}")

    return {
        "A_text_only": {
            "pose_image": None,
            "expression_image": None,
            "background_image": None,
            "description": "Text Only (no image references)",
            "temperature": BASE_TEMPERATURE,
        },
        "B_pose": {
            "pose_image": pose_img,
            "expression_image": None,
            "background_image": None,
            "description": "+ Pose Reference",
            "temperature": BASE_TEMPERATURE,
        },
        "C_bg": {
            "pose_image": None,
            "expression_image": None,
            "background_image": bg_img,
            "description": "+ Background Reference",
            "temperature": BASE_TEMPERATURE,
        },
        "D_pose_bg": {
            "pose_image": pose_img,
            "expression_image": None,
            "background_image": bg_img,
            "description": "+ Pose + Background",
            "temperature": BASE_TEMPERATURE,
        },
        "E_expression": {
            "pose_image": None,
            "expression_image": expr_img,
            "background_image": None,
            "description": "+ Expression Only",
            "temperature": BASE_TEMPERATURE,
        },
        "F_pose_expr": {
            "pose_image": pose_img,
            "expression_image": expr_img,
            "background_image": None,
            "description": "+ Pose + Expression",
            "temperature": BASE_TEMPERATURE,
        },
        "G_all_refs": {
            "pose_image": pose_img,
            "expression_image": expr_img,
            "background_image": bg_img,
            "description": "All References (pose + expression + bg)",
            "temperature": BASE_TEMPERATURE,
        },
        "H1_temp_0.3": {
            "pose_image": pose_img,
            "expression_image": None,
            "background_image": bg_img,
            "description": "Temperature 0.3 (Pose + BG)",
            "temperature": 0.3,
        },
        "H2_temp_0.5": {
            "pose_image": pose_img,
            "expression_image": None,
            "background_image": bg_img,
            "description": "Temperature 0.5 (Pose + BG)",
            "temperature": 0.5,
        },
        "H3_temp_0.7": {
            "pose_image": pose_img,
            "expression_image": None,
            "background_image": bg_img,
            "description": "Temperature 0.7 (Pose + BG)",
            "temperature": 0.7,
        },
    }


# ============================================================
# GENERATION FUNCTION
# ============================================================
def generate_image_direct(
    face_images: list,
    outfit_images: list,
    pose_image: Path = None,
    expression_image: Path = None,
    background_image: Path = None,
    temperature: float = 0.5,
    api_key: str = None,
) -> Image.Image:
    """Generate image using direct Gemini API call"""

    from google import genai
    from google.genai import types
    from core.api import _get_next_api_key, _pil_to_part
    from core.config import IMAGE_MODEL

    if api_key is None:
        api_key = _get_next_api_key()

    client = genai.Client(api_key=api_key)

    # Build parts list
    parts = []

    # 1. Build prompt text based on what references are provided
    has_pose = pose_image and pose_image.exists()
    has_expr = expression_image and expression_image.exists()
    has_bg = background_image and background_image.exists()

    prompt_text = build_full_prompt(
        has_pose_ref=has_pose,
        has_expr_ref=has_expr,
        has_bg_ref=has_bg,
    )
    parts.append(types.Part(text=prompt_text))

    # 2. Pose reference (if provided)
    if has_pose:
        parts.append(types.Part(text="[POSE REFERENCE IMAGE]"))
        pose_pil = Image.open(pose_image)
        if pose_pil.mode == "RGBA":
            pose_pil = pose_pil.convert("RGB")
        parts.append(_pil_to_part(pose_pil))

    # 3. Expression reference (if provided)
    if has_expr:
        parts.append(types.Part(text="[EXPRESSION REFERENCE IMAGE]"))
        expr_pil = Image.open(expression_image)
        if expr_pil.mode == "RGBA":
            expr_pil = expr_pil.convert("RGB")
        parts.append(_pil_to_part(expr_pil))

    # 4. Face images
    for i, face_path in enumerate(face_images):
        if Path(face_path).exists():
            parts.append(types.Part(text=f"[FACE IMAGE {i+1}]"))
            face_pil = Image.open(face_path)
            if face_pil.mode == "RGBA":
                face_pil = face_pil.convert("RGB")
            parts.append(_pil_to_part(face_pil))

    # 5. Outfit images
    for i, outfit_path in enumerate(outfit_images):
        if Path(outfit_path).exists():
            parts.append(types.Part(text=f"[OUTFIT IMAGE {i+1}]"))
            outfit_pil = Image.open(outfit_path)
            if outfit_pil.mode == "RGBA":
                outfit_pil = outfit_pil.convert("RGB")
            parts.append(_pil_to_part(outfit_pil))

    # 6. Background reference (if provided)
    if has_bg:
        parts.append(types.Part(text="[BACKGROUND REFERENCE IMAGE - IGNORE PERSON]"))
        bg_pil = Image.open(background_image)
        if bg_pil.mode == "RGBA":
            bg_pil = bg_pil.convert("RGB")
        parts.append(_pil_to_part(bg_pil))

    # API call with retry logic
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_modalities=["IMAGE", "TEXT"],
    )

    print(f"[API] Calling {IMAGE_MODEL} with {len(parts)} parts, temp={temperature}...")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                config=config,
                contents=[types.Content(role="user", parts=parts)],
            )

            # Extract image from response
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        import io

                        image_data = part.inline_data.data
                        return Image.open(io.BytesIO(image_data))

            return None

        except Exception as e:
            error_str = str(e).lower()
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10  # 10, 20, 30 seconds
                print(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"[RETRY] Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise

    return None


# ============================================================
# RESULT SAVING (with all inputs)
# ============================================================
def save_test_results(
    case_id: str,
    sample_idx: int,
    output_dir: Path,
    result_image: Image.Image,
    config: dict,
    prompt_text: str,
    face_images: list,
    outfit_images: list,
    pose_image: Path = None,
    expression_image: Path = None,
    background_image: Path = None,
):
    """Save test results with all inputs"""

    case_dir = output_dir / case_id
    images_dir = case_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy input images
    for i, face_path in enumerate(face_images):
        if Path(face_path).exists():
            shutil.copy(
                face_path, images_dir / f"input_face_{i+1:02d}{Path(face_path).suffix}"
            )

    for i, outfit_path in enumerate(outfit_images):
        if Path(outfit_path).exists():
            shutil.copy(
                outfit_path,
                images_dir / f"input_outfit_{i+1:02d}{Path(outfit_path).suffix}",
            )

    if pose_image and pose_image.exists():
        shutil.copy(pose_image, images_dir / f"input_pose_ref{pose_image.suffix}")

    if expression_image and expression_image.exists():
        shutil.copy(
            expression_image, images_dir / f"input_expr_ref{expression_image.suffix}"
        )

    if background_image and background_image.exists():
        shutil.copy(
            background_image, images_dir / f"input_bg_ref{background_image.suffix}"
        )

    # 2. Save output image
    if result_image:
        result_image.save(images_dir / f"output_{sample_idx:03d}.jpg", quality=95)

    # 3. Save prompt.txt
    prompt_file = case_dir / "prompt.txt"
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(f"=== TEST INFO ===\n")
        f.write(f"Case: {case_id}\n")
        f.write(f"Description: {config.get('description', '')}\n")
        f.write(f"Sample: {sample_idx}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"=== INPUTS ===\n")
        f.write(f"Face: {[str(p) for p in face_images]}\n")
        f.write(f"Outfit: {[str(p) for p in outfit_images]}\n")
        f.write(f"Pose Ref: {pose_image}\n")
        f.write(f"Expression Ref: {expression_image}\n")
        f.write(f"BG Ref: {background_image}\n\n")
        f.write(f"=== PROMPT ===\n")
        f.write(prompt_text)

    # 4. Save config.json
    config_file = case_dir / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2, default=str)

    # 5. Save prompt_schema.json
    schema_file = case_dir / "prompt_schema.json"
    with open(schema_file, "w", encoding="utf-8") as f:
        json.dump(PROMPT_SCHEMA, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {case_dir}")


# ============================================================
# MAIN TEST RUNNER
# ============================================================
def run_test(cases_to_run: list = None):
    """Run ablation test

    Args:
        cases_to_run: List of case IDs to run, or None for all
    """

    print("=" * 60)
    print("AI INFLUENCER REFERENCE ABLATION TEST")
    print("ALL CASES: A, B, C, D, E, F, G, H")
    print("=" * 60)

    # Verify input images exist
    print("\n[CHECK] Verifying input images...")

    if not FACE_IMAGE.exists():
        print(f"[ERROR] Face image not found: {FACE_IMAGE}")
        return
    print(f"[OK] Face: {FACE_IMAGE.name}")

    if not OUTFIT_TOP.exists():
        print(f"[ERROR] Outfit top not found: {OUTFIT_TOP}")
        return
    print(f"[OK] Outfit top: {OUTFIT_TOP.name}")

    if not OUTFIT_BOTTOM.exists():
        print(f"[ERROR] Outfit bottom not found: {OUTFIT_BOTTOM}")
        return
    print(f"[OK] Outfit bottom: {OUTFIT_BOTTOM.name}")

    # Get case configs
    case_configs = get_case_configs()

    # Filter cases if specified
    if cases_to_run:
        case_configs = {k: v for k, v in case_configs.items() if k in cases_to_run}

    print(f"\n[CASES] Running {len(case_configs)} cases: {list(case_configs.keys())}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_BASE / f"{timestamp}_reference_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[OUTPUT] {output_dir}")

    # Prepare input lists
    face_images = [FACE_IMAGE]
    outfit_images = [OUTFIT_TOP, OUTFIT_BOTTOM]

    # Run each case
    results = {}

    for case_id, config in case_configs.items():
        print(f"\n{'='*60}")
        print(f"[CASE] {case_id}: {config['description']}")
        print(f"{'='*60}")

        for sample_idx in range(1, NUM_SAMPLES + 1):
            print(f"\n[SAMPLE {sample_idx}/{NUM_SAMPLES}]")

            try:
                # Build prompt for this case
                has_pose = (
                    config.get("pose_image") and config.get("pose_image").exists()
                )
                has_expr = (
                    config.get("expression_image")
                    and config.get("expression_image").exists()
                )
                has_bg = (
                    config.get("background_image")
                    and config.get("background_image").exists()
                )

                prompt_text = build_full_prompt(
                    has_pose_ref=has_pose,
                    has_expr_ref=has_expr,
                    has_bg_ref=has_bg,
                )

                # Generate image
                result_image = generate_image_direct(
                    face_images=face_images,
                    outfit_images=outfit_images,
                    pose_image=config.get("pose_image"),
                    expression_image=config.get("expression_image"),
                    background_image=config.get("background_image"),
                    temperature=config.get("temperature", BASE_TEMPERATURE),
                )

                if result_image:
                    print(f"[OK] Generated: {result_image.size}")

                    # Save results with all inputs
                    save_test_results(
                        case_id=case_id,
                        sample_idx=sample_idx,
                        output_dir=output_dir,
                        result_image=result_image,
                        config={
                            "case_id": case_id,
                            "description": config["description"],
                            "pose_image": str(config.get("pose_image"))
                            if config.get("pose_image")
                            else None,
                            "expression_image": str(config.get("expression_image"))
                            if config.get("expression_image")
                            else None,
                            "background_image": str(config.get("background_image"))
                            if config.get("background_image")
                            else None,
                            "temperature": config.get("temperature", BASE_TEMPERATURE),
                            "aspect_ratio": ASPECT_RATIO,
                            "resolution": RESOLUTION,
                            "timestamp": datetime.now().isoformat(),
                        },
                        prompt_text=prompt_text,
                        face_images=face_images,
                        outfit_images=outfit_images,
                        pose_image=config.get("pose_image"),
                        expression_image=config.get("expression_image"),
                        background_image=config.get("background_image"),
                    )

                    results[f"{case_id}_{sample_idx}"] = {
                        "success": True,
                        "image_size": result_image.size,
                    }
                else:
                    print(f"[FAIL] No image generated")
                    results[f"{case_id}_{sample_idx}"] = {
                        "success": False,
                        "error": "No image",
                    }

            except Exception as e:
                print(f"[ERROR] {e}")
                traceback.print_exc()
                results[f"{case_id}_{sample_idx}"] = {"success": False, "error": str(e)}

            # Rate limit delay
            if sample_idx < NUM_SAMPLES:
                print("[WAIT] 5 seconds...")
                time.sleep(5)

        # Delay between cases
        print("\n[WAIT] 10 seconds before next case...")
        time.sleep(10)

    # Save summary
    summary_file = output_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "num_samples": NUM_SAMPLES,
                "cases": list(case_configs.keys()),
                "results": results,
                "prompt_schema": PROMPT_SCHEMA,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {output_dir}")

    # Print summary
    success_count = sum(1 for r in results.values() if r.get("success"))
    total_count = len(results)
    print(f"Success: {success_count}/{total_count}")

    return output_dir


if __name__ == "__main__":
    # Run all cases by default
    # Or specify: run_test(["A_text_only", "D_pose_bg"])
    run_test()
