"""
AI Influencer Image Generation - Full Pipeline

=== 필수 파이프라인 (절대 생략 금지!) ===
1. analyze_hair()        -- 얼굴 이미지에서 헤어 정보 추출
2. analyze_expression()  -- 표정 이미지에서 표정 정보 추출
3. analyze_pose()        -- 포즈 이미지에서 포즈/프레이밍/앵글 추출
4. analyze_background()  -- 배경 이미지에서 장소/조명/분위기 추출
5. check_compatibility() -- 포즈-배경 호환성 검사
6. OutfitAnalyzer.analyze() -- 착장 이미지 상세 분석
7. build_schema_prompt() -- 분석 결과를 스키마 프롬프트로 조립
8. generate_image()      -- 프롬프트 + 모든 이미지 레퍼런스 → API 호출

WARNING: generate_ai_influencer()를 직접 호출하면 안됨!
   -> 그 함수는 VLM 분석을 건너뛰고 generic label만 사용함.
   -> 반드시 위 파이프라인을 거쳐야 포즈/프레이밍/배경 정확도 보장.

모든 이미지 레퍼런스(포즈+표정+배경)를 항상 포함.
스키마: db/influencer_prompt_schema.json
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import time
import shutil

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from PIL import Image
from google import genai
from google.genai import types
from io import BytesIO

from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key
from core.ai_influencer import (
    analyze_pose,
    analyze_background,
    check_compatibility,
    PoseAnalysisResult,
    BackgroundAnalysisResult,
)
from core.ai_influencer.presets import format_visual_mood_for_prompt
from core.outfit_analyzer import OutfitAnalyzer


# ============================================================
# OPTIONS (change these values)
# ============================================================
# aspect_ratio: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
# resolution: "1K", "2K", "4K"
# num_images: 1, 3, 5, 10
# cost: 1K~2K = 190won/image, 4K = 380won/image
# ============================================================
NUM_IMAGES = 3
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"


# ============================================================
# VLM ANALYZERS
# ============================================================


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def analyze_hair(client, face_image_path: Path) -> dict:
    """얼굴 이미지에서 헤어 정보 추출"""

    prompt = """이 이미지에서 인물의 헤어 정보를 분석하세요.

JSON 형식으로 출력:
```json
{
    "스타일": "straight_loose/wavy/ponytail/bun/braids/short_bob 중 하나",
    "컬러": "black/dark_brown/brown/blonde/red/ash_gray 중 하나",
    "질감": "sleek/voluminous/textured/messy 중 하나"
}
```

JSON만 출력하세요."""

    img = Image.open(face_image_path).convert("RGB")

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt), pil_to_part(img)],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        return json.loads(result_text)

    except Exception as e:
        print(f"[Hair Analysis] Error: {e}")
        return {"스타일": "straight_loose", "컬러": "dark_brown", "질감": "sleek"}


def analyze_expression(client, expression_image_path: Path) -> dict:
    """표정 이미지에서 표정 정보 추출"""

    prompt = """이 이미지에서 인물의 표정을 분석하세요.

JSON 형식으로 출력:
```json
{
    "베이스": "cool/natural/dreamy/playful/cute 중 하나",
    "바이브": "sensual/bold/mysterious/effortless/unbothered/intense/innocent/intimate/fresh/flirty/adorable 중 선택",
    "시선": "direct/side gaze/downcast/3/4 측면 중 하나",
    "입": "closed/slightly parted/soft smile/slight pout 중 하나"
}
```

JSON만 출력하세요."""

    img = Image.open(expression_image_path).convert("RGB")

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt), pil_to_part(img)],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        return json.loads(result_text)

    except Exception as e:
        print(f"[Expression Analysis] Error: {e}")
        return {
            "베이스": "cool",
            "바이브": "effortless",
            "시선": "direct",
            "입": "closed",
        }


# ============================================================
# SCHEMA PROMPT BUILDER
# ============================================================


def build_schema_prompt(
    hair_info: dict,
    expression_info: dict,
    pose_result: PoseAnalysisResult,
    background_result: BackgroundAnalysisResult,
    outfit_result,
    compatibility_result=None,
) -> str:
    """
    스키마 기반 프롬프트 생성

    모든 분석 결과를 텍스트로 포함
    """

    lines = []

    # 기본 설정
    lines.append("# AI Influencer Image Generation")
    lines.append("")
    lines.append("Generate a fashion editorial photo following this schema EXACTLY.")
    lines.append("")

    # =====================================================
    # 모델 정보
    # =====================================================
    lines.append("## [모델]")
    lines.append("- 국적: 한국인")
    lines.append("- 성별: 여성")
    lines.append("- 나이: 20대 초반")
    lines.append("")

    # =====================================================
    # 헤어 (CRITICAL - 변경 금지)
    # =====================================================
    lines.append("## [헤어] ★★★ CRITICAL - DO NOT CHANGE ★★★")
    lines.append(f"- 스타일: {hair_info.get('스타일', 'straight_loose')}")
    lines.append(f"- 컬러: {hair_info.get('컬러', 'dark_brown')}")
    lines.append(f"- 질감: {hair_info.get('질감', 'sleek')}")
    lines.append("")
    lines.append("IMPORTANT: 헤어 컬러와 스타일은 위에 명시된 대로 유지!")
    lines.append("다른 레퍼런스 이미지의 헤어를 복사하지 마세요!")
    lines.append("")

    # =====================================================
    # 표정
    # =====================================================
    lines.append("## [표정]")
    lines.append(f"- 베이스: {expression_info.get('베이스', 'cool')}")
    lines.append(f"- 바이브: {expression_info.get('바이브', 'effortless')}")
    lines.append("- 눈: 큰 눈")
    lines.append(f"- 시선: {expression_info.get('시선', 'direct')}")
    lines.append(f"- 입: {expression_info.get('입', 'closed')}")
    lines.append("")

    # =====================================================
    # 포즈 (강화된 지시)
    # =====================================================
    lines.append("## [포즈] ★★★ MUST FOLLOW EXACTLY - DO NOT SIMPLIFY ★★★")
    lines.append(f"- stance: {pose_result.stance}")
    lines.append(f"- 왼팔: {pose_result.left_arm}")
    lines.append(f"- 오른팔: {pose_result.right_arm}")
    lines.append(f"- 왼손: {pose_result.left_hand}")
    lines.append(f"- 오른손: {pose_result.right_hand}")
    lines.append(f"- 왼다리: {pose_result.left_leg}")
    lines.append(f"- 오른다리: {pose_result.right_leg}")
    lines.append(f"- 힙: {pose_result.hip}")
    lines.append("")

    # 특이 포즈 감지 및 강조 (한 다리 들기, 앉기 등)
    unusual_pose_warning = []
    left_leg_lifted = any(
        kw in pose_result.left_leg.lower()
        for kw in ["들어올", "구부", "90도", "배꼽 높이"]
    )
    right_leg_lifted = any(
        kw in pose_result.right_leg.lower()
        for kw in ["들어올", "구부", "90도", "배꼽 높이"]
    )

    if left_leg_lifted:
        unusual_pose_warning.append(
            f"★ LEFT LEG LIFTED: {pose_result.left_leg} - DO NOT put this foot on ground!"
        )
    if right_leg_lifted:
        unusual_pose_warning.append(
            f"★ RIGHT LEG LIFTED: {pose_result.right_leg} - DO NOT put this foot on ground!"
        )

    if unusual_pose_warning:
        lines.append("### ★★★ CRITICAL POSE WARNING ★★★")
        for warning in unusual_pose_warning:
            lines.append(warning)
        lines.append("")
        lines.append("This is an UNUSUAL pose. DO NOT default to normal standing pose!")
        lines.append("The model MUST have ONE LEG LIFTED as specified above.")
        lines.append("")

    # =====================================================
    # 방향/기울기 (★★★ 매우 중요 - 정확히 재현 ★★★)
    # =====================================================
    lines.append("### [방향/기울기] ★★★ CRITICAL - EXACT DIRECTION ★★★")
    if pose_result.torso_tilt:
        lines.append(f"- 상체_기울기: {pose_result.torso_tilt}")

    # ★★★ 무릎 방향 (가장 중요!) ★★★
    if pose_result.left_knee_direction:
        lines.append(f"- 왼무릎_방향: {pose_result.left_knee_direction}")
    if pose_result.right_knee_direction:
        lines.append(f"- 오른무릎_방향: {pose_result.right_knee_direction}")

    # 발 방향
    if pose_result.left_foot_direction:
        lines.append(f"- 왼발_방향: {pose_result.left_foot_direction}")
    if pose_result.right_foot_direction:
        lines.append(f"- 오른발_방향: {pose_result.right_foot_direction}")

    # 무릎 상세 (각도, 높이, 발 위치)
    if pose_result.left_knee_angle:
        lines.append(f"- 왼무릎_각도: {pose_result.left_knee_angle}")
    if pose_result.right_knee_angle:
        lines.append(f"- 오른무릎_각도: {pose_result.right_knee_angle}")
    if pose_result.left_knee_height:
        lines.append(f"- 왼무릎_높이: {pose_result.left_knee_height}")
    if pose_result.right_knee_height:
        lines.append(f"- 오른무릎_높이: {pose_result.right_knee_height}")
    if pose_result.left_foot_position:
        lines.append(f"- 왼발_위치: {pose_result.left_foot_position}")
    if pose_result.right_foot_position:
        lines.append(f"- 오른발_위치: {pose_result.right_foot_position}")

    if pose_result.shoulder_line:
        lines.append(f"- 어깨_라인: {pose_result.shoulder_line}")
    if pose_result.face_direction:
        lines.append(f"- 얼굴_방향: {pose_result.face_direction}")
    lines.append("")

    # sit 포즈일 때 앉는 위치 명시
    if pose_result.stance == "sit" and background_result.sit_on:
        lines.append(f"- 앉는_위치: {background_result.sit_on}")
        lines.append("")
        lines.append("★★★ IMPORTANT: 배경에 이미 있는 위치에 앉으세요! ★★★")
        lines.append(
            "새로운 의자/물체를 만들지 마세요. 배경 레퍼런스에 보이는 곳에 앉으세요."
        )
        lines.append("")

    # =====================================================
    # 촬영 세팅
    # =====================================================
    lines.append("## [촬영_세팅]")
    lines.append(f"- 프레이밍: {pose_result.framing}")
    lines.append("- 렌즈: 50mm")
    lines.append(f"- 앵글: {pose_result.camera_angle}")
    lines.append(f"- 높이: {pose_result.camera_height}")
    lines.append("- 구도: 중앙")
    lines.append("- 조리개: f/2.8")
    lines.append("")

    # =====================================================
    # 배경
    # =====================================================
    lines.append("## [배경]")
    lines.append(f"- 지역: {background_result.region}")
    lines.append(f"- 시간대: {background_result.time_of_day}")
    lines.append(f"- 색감: {background_result.color_tone}")
    lines.append(f"- 장소: {background_result.scene_type}")
    lines.append(f"- 분위기: {background_result.mood}")
    lines.append("- 인물제외: 배경에 다른 사람 없음. 주인공 한 명만 등장.")
    lines.append("")

    # 호환성 경고
    if compatibility_result and not compatibility_result.is_compatible():
        lines.append("## [COMPATIBILITY WARNING]")
        for issue in compatibility_result.issues:
            lines.append(f"- {issue.description}")
        lines.append("")

    # =====================================================
    # 스타일링 (착장)
    # =====================================================
    lines.append("## [스타일링] - Match EXACTLY")
    lines.append(f"- overall_vibe: {outfit_result.overall_style}")
    lines.append("")
    lines.append("### 아이템:")
    for item in outfit_result.items:
        lines.append(f"- {item.category}: {item.name}")
        lines.append(f"  - 색상: {item.color}")
        lines.append(f"  - 핏: {item.fit}")
        if item.logos:
            for logo in item.logos:
                lines.append(f"  - 로고: {logo.brand} ({logo.type}) at {logo.position}")
        if item.details:
            lines.append(f"  - 디테일: {', '.join(item.details)}")
    lines.append("")

    # =====================================================
    # 비주얼 무드 (프리셋에서 로드)
    # =====================================================
    visual_mood_lines = format_visual_mood_for_prompt("OUTDOOR_CASUAL_001")
    lines.extend(visual_mood_lines)

    # =====================================================
    # 네거티브 (동적 추가)
    # =====================================================
    lines.append("## [네거티브]")
    base_negative = "other people, crowd, bystanders, passersby, multiple people, random chair, random box, invented furniture, objects not in background reference, bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers, AI look, overprocessed"

    # 특이 포즈일 때 네거티브 추가
    extra_negative = []
    if left_leg_lifted or right_leg_lifted:
        extra_negative.append("both feet on ground")
        extra_negative.append("standing with both legs")
        extra_negative.append("flat-footed stance")
        extra_negative.append("symmetrical leg position")

    if extra_negative:
        full_negative = base_negative + ", " + ", ".join(extra_negative)
    else:
        full_negative = base_negative

    lines.append(full_negative)
    lines.append("")

    # =====================================================
    # 이미지 역할 안내 (항상 모든 레퍼런스 포함)
    # =====================================================
    lines.append("=" * 50)
    lines.append("## [IMAGE REFERENCE ROLES]")
    lines.append("")
    lines.append("[FACE] images: Use this person's face identity")
    lines.append("  - KEEP hair color/style as specified in [헤어] section!")
    lines.append("")
    lines.append("[OUTFIT] images: Match outfit EXACTLY")
    lines.append("  - Copy all colors, logos, patterns, details")
    lines.append("")
    lines.append("[POSE REFERENCE]: Copy pose from this image")
    lines.append("  - Match body position EXACTLY")
    lines.append("  - Ignore face/outfit/background from this image")
    lines.append("")
    lines.append("[EXPRESSION REFERENCE]: Copy expression only")
    lines.append("  - Copy eyes, mouth, facial expression")
    lines.append("  - DO NOT copy hair from this image!")
    lines.append("")
    lines.append("[BACKGROUND REFERENCE]: Use this background")
    lines.append("  - Ignore any person in background image")
    lines.append("  - Match lighting/mood of background")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# IMAGE GENERATOR (항상 모든 레퍼런스 포함)
# ============================================================


def generate_image(
    client,
    prompt: str,
    face_images: list,
    outfit_images: list,
    pose_image: Path,
    expression_image: Path,
    background_image: Path,
    temperature: float = 0.35,
) -> Image.Image:
    """
    이미지 생성 - 모든 레퍼런스 이미지 포함

    전송 순서:
    1. 프롬프트 (텍스트)
    2. [POSE REFERENCE] 포즈 이미지
    3. [EXPRESSION REFERENCE] 표정 이미지
    4. [FACE] 얼굴 이미지
    5. [OUTFIT 1~N] 착장 이미지
    6. [BACKGROUND REFERENCE] 배경 이미지
    7. [POSE REMINDER] 포즈 재강조
    """

    parts = []

    # 1. 프롬프트
    parts.append(types.Part(text=prompt))

    # 2. 포즈 레퍼런스
    if pose_image and pose_image.exists():
        img = Image.open(pose_image).convert("RGB")
        parts.append(types.Part(text="[POSE REFERENCE]"))
        parts.append(pil_to_part(img))

    # 3. 표정 레퍼런스
    if expression_image and expression_image.exists():
        img = Image.open(expression_image).convert("RGB")
        parts.append(
            types.Part(text="[EXPRESSION REFERENCE] - Copy expression only, NOT hair")
        )
        parts.append(pil_to_part(img))

    # 4. 얼굴 이미지
    for i, face_path in enumerate(face_images):
        if face_path.exists():
            img = Image.open(face_path).convert("RGB")
            parts.append(
                types.Part(text=f"[FACE {i+1}] - Use this person's identity and hair")
            )
            parts.append(pil_to_part(img))

    # 5. 착장 이미지
    for i, outfit_path in enumerate(outfit_images):
        if outfit_path.exists():
            img = Image.open(outfit_path).convert("RGB")
            parts.append(types.Part(text=f"[OUTFIT {i+1}]"))
            parts.append(pil_to_part(img))

    # 6. 배경 이미지
    if background_image and background_image.exists():
        img = Image.open(background_image).convert("RGB")
        parts.append(
            types.Part(text="[BACKGROUND REFERENCE] - Ignore person in this image")
        )
        parts.append(pil_to_part(img))

    # 7. 포즈 재강조 (마지막에 다시 전송)
    if pose_image and pose_image.exists():
        img = Image.open(pose_image).convert("RGB")
        parts.append(
            types.Part(
                text="[POSE REMINDER] ★★★ CRITICAL: Copy this EXACT pose! If one leg is lifted, it MUST be lifted in the output! ★★★"
            )
        )
        parts.append(pil_to_part(img))

    # API 호출
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=ASPECT_RATIO,
                    image_size=RESOLUTION,
                ),
            ),
        )

        # 이미지 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data))

        return None

    except Exception as e:
        print(f"[Generate] Error: {e}")
        return None


# ============================================================
# TEST RUNNER
# ============================================================


def run_test(test_name: str, test_folder: Path):
    """
    AI 인플루언서 이미지 생성 테스트

    파이프라인:
    STEP 1: VLM 분석 (헤어/표정/포즈/배경/호환성/착장)
    STEP 2: 스키마 프롬프트 생성
    STEP 3: 이미지 생성 (모든 레퍼런스 포함)
    STEP 4: 결과 저장
    """

    print(f"\n{'#' * 60}")
    print(f"# AI INFLUENCER - FULL PIPELINE TEST: {test_name}")
    print(f"# Folder: {test_folder}")
    print(f"{'#' * 60}")

    if not test_folder.exists():
        print(f"[ERROR] Test folder not found: {test_folder}")
        return

    # API 클라이언트
    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)

    # 출력 디렉토리
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        project_root
        / "Fnf_studio_outputs"
        / "ai_influencer"
        / f"{test_name}_{timestamp}"
    )
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # 이미지 경로 탐색
    # =========================================================
    face_images = [test_folder / "얼굴.png"]
    outfit_images = sorted(list(test_folder.glob("착장*.png")))
    pose_image = test_folder / "포즈.png"

    expression_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        expr_path = test_folder / f"표정{ext}"
        if expr_path.exists():
            expression_image = expr_path
            break

    background_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        bg_path = test_folder / f"배경{ext}"
        if bg_path.exists():
            background_image = bg_path
            break

    # 필수 이미지 확인
    missing = []
    if not face_images[0].exists():
        missing.append("얼굴.png")
    if not pose_image.exists():
        missing.append("포즈.png")
    if not expression_image:
        missing.append("표정.png/jpeg/jpg")
    if not background_image:
        missing.append("배경.png/jpeg/jpg")
    if not outfit_images:
        missing.append("착장*.png")

    if missing:
        print(f"[ERROR] Missing required images: {', '.join(missing)}")
        return

    # 인풋 이미지 복사
    for face_path in face_images:
        shutil.copy(face_path, images_dir / f"input_face.png")
    for i, outfit_path in enumerate(outfit_images):
        shutil.copy(outfit_path, images_dir / f"input_outfit_{i+1:02d}.png")
    shutil.copy(pose_image, images_dir / "input_pose.png")
    shutil.copy(
        expression_image, images_dir / f"input_expression{expression_image.suffix}"
    )
    shutil.copy(
        background_image, images_dir / f"input_background{background_image.suffix}"
    )
    print(f"[OK] {3 + len(outfit_images) + len(face_images)} input images copied")

    # =========================================================
    # STEP 1: VLM 분석 (모든 레퍼런스)
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 1: VLM Analysis (all references)")
    print("=" * 60)

    # 1-1. 헤어 분석
    print("\n[1-1] Analyzing hair from face image...")
    hair_info = analyze_hair(client, face_images[0])
    print(f"  Hair: {hair_info}")

    # 1-2. 표정 분석
    print("\n[1-2] Analyzing expression...")
    expression_info = analyze_expression(client, expression_image)
    print(f"  Expression: {expression_info}")

    # 1-3. 포즈 분석
    print("\n[1-3] Analyzing pose...")
    pose_result = analyze_pose(pose_image)
    print(f"  Stance: {pose_result.stance}, Framing: {pose_result.framing}")

    # 1-4. 배경 분석
    print("\n[1-4] Analyzing background...")
    background_result = analyze_background(background_image)
    print(
        f"  Scene: {background_result.scene_type}, Provides: {background_result.provides}"
    )

    # 1-5. 호환성 검사
    print("\n[1-5] Checking compatibility...")
    compatibility_result = check_compatibility(pose_result, background_result)
    print(
        f"  Level: {compatibility_result.level.value}, Score: {compatibility_result.score}"
    )

    # 1-6. 착장 분석
    print("\n[1-6] Analyzing outfit...")
    outfit_analyzer = OutfitAnalyzer(client)
    outfit_result = outfit_analyzer.analyze([str(p) for p in outfit_images])
    print(f"  Style: {outfit_result.overall_style}")
    print(f"  Brand: {outfit_result.brand_detected}")
    print(f"  Items: {len(outfit_result.items)}")

    # 분석 결과 저장
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    with open(analysis_dir / "hair_analysis.json", "w", encoding="utf-8") as f:
        json.dump(hair_info, f, ensure_ascii=False, indent=2)
    with open(analysis_dir / "expression_analysis.json", "w", encoding="utf-8") as f:
        json.dump(expression_info, f, ensure_ascii=False, indent=2)
    with open(analysis_dir / "pose_analysis.json", "w", encoding="utf-8") as f:
        json.dump(pose_result.to_schema_format(), f, ensure_ascii=False, indent=2)
    with open(analysis_dir / "background_analysis.json", "w", encoding="utf-8") as f:
        json.dump(background_result.to_schema_format(), f, ensure_ascii=False, indent=2)
    with open(analysis_dir / "compatibility.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "level": compatibility_result.level.value,
                "score": compatibility_result.score,
                "issues": [
                    {"type": i.issue_type, "description": i.description}
                    for i in compatibility_result.issues
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # =========================================================
    # STEP 2: 프롬프트 생성
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 2: Building schema prompt")
    print("=" * 60)

    prompt = build_schema_prompt(
        hair_info=hair_info,
        expression_info=expression_info,
        pose_result=pose_result,
        background_result=background_result,
        outfit_result=outfit_result,
        compatibility_result=compatibility_result,
    )

    # 프롬프트 저장
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"  Saved: prompt.txt")

    # prompt.json 저장
    prompt_json = {
        "module": "tests.influencer.test_reference_cases",
        "pipeline": [
            "analyze_hair",
            "analyze_expression",
            "analyze_pose",
            "analyze_background",
            "check_compatibility",
            "OutfitAnalyzer.analyze",
            "build_schema_prompt",
            "generate_image",
        ],
        "analysis": {
            "hair": hair_info,
            "expression": expression_info,
            "pose": pose_result.to_schema_format(),
            "background": background_result.to_schema_format(),
        },
        "references": {
            "pose_image": str(pose_image),
            "expression_image": str(expression_image),
            "background_image": str(background_image),
            "face_images": [str(p) for p in face_images],
            "outfit_images": [str(p) for p in outfit_images],
        },
    }
    with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_json, f, ensure_ascii=False, indent=2)

    # =========================================================
    # STEP 3: 이미지 생성 (모든 레퍼런스 포함)
    # =========================================================
    print("\n" + "=" * 60)
    print(f"STEP 3: Generating {NUM_IMAGES} images (all references included)")
    print("=" * 60)

    results = []
    for i in range(NUM_IMAGES):
        print(f"\n[Generating] Image {i+1}/{NUM_IMAGES}...")

        image = generate_image(
            client=client,
            prompt=prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            temperature=0.35,
        )

        if image:
            image.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)
            results.append({"index": i + 1, "status": "success"})
            print(f"  [OK] Saved output_{i+1:03d}.jpg")
        else:
            results.append({"index": i + 1, "status": "failed"})
            print(f"  [FAIL] Generation failed")

        if i < NUM_IMAGES - 1:
            time.sleep(2)  # Rate limit

    # =========================================================
    # STEP 4: 결과 저장
    # =========================================================
    success_count = sum(1 for r in results if r["status"] == "success")

    # config.json
    config = {
        "workflow": "ai_influencer",
        "module": "tests.influencer.test_reference_cases",
        "description": test_name,
        "timestamp": datetime.now().isoformat(),
        "model": IMAGE_MODEL,
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "temperature": 0.35,
        "num_images": NUM_IMAGES,
        "cost_per_image": 190,
        "total_cost": NUM_IMAGES * 190,
        "input_summary": {
            "face": len(face_images),
            "outfits": len(outfit_images),
            "pose_reference": True,
            "expression_reference": True,
            "background_reference": True,
        },
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # validation.json
    validation = {
        "workflow": "ai_influencer",
        "results": results,
        "total_generated": success_count,
        "total_failed": NUM_IMAGES - success_count,
        "success_rate": success_count / NUM_IMAGES * 100 if NUM_IMAGES > 0 else 0,
        "analysis": {
            "hair": hair_info,
            "expression": expression_info,
            "pose": pose_result.to_schema_format(),
            "background": background_result.to_schema_format(),
            "compatibility": {
                "level": compatibility_result.level.value,
                "score": compatibility_result.score,
            },
            "outfit": {
                "style": outfit_result.overall_style,
                "brand": outfit_result.brand_detected,
                "item_count": len(outfit_result.items),
            },
        },
    }
    with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print(f"\n{'=' * 60}")
    print(f"TEST COMPLETE: {test_name}")
    print(f"{'=' * 60}")
    print(f"Output: {output_dir}")
    print(f"Results: {success_count}/{NUM_IMAGES} success")
    print(f"Cost: {NUM_IMAGES * 190} won ({NUM_IMAGES} x 190)")

    return validation


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Influencer Full Pipeline Test")
    parser.add_argument(
        "--test-dir",
        type=str,
        required=True,
        help="Test folder path (e.g., tests/인플테스트3)",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=3,
        help="Number of images (default: 3)",
    )

    args = parser.parse_args()

    # Override NUM_IMAGES
    NUM_IMAGES = args.num_images

    # Resolve test folder
    test_folder = Path(args.test_dir)
    if not test_folder.is_absolute():
        test_folder = project_root / args.test_dir

    test_name = test_folder.name
    run_test(test_name, test_folder)
