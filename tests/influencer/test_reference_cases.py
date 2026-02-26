"""
AI Influencer Reference Test - A-H Cases

핵심 원칙:
1. 모든 케이스에 동일한 스키마 프롬프트 사용
2. 이미지 참조만 케이스별로 다름

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
# TEST CONFIGURATIONS
# ============================================================

TEST_FOLDERS = {
    "test1": project_root / "tests" / "인플테스트용",
    "test2": project_root / "tests" / "인플테스트2",
    "test3": project_root / "tests" / "인플테스트3",
}

# 테스트 케이스: 이미지 참조만 다름, 프롬프트는 동일
TEST_CASES = {
    "A": {
        "pose_img": False,
        "expr_img": False,
        "bg_img": False,
        "desc": "베이스라인 (텍스트만)",
    },
    "B": {"pose_img": True, "expr_img": False, "bg_img": False, "desc": "포즈 이미지"},
    "C": {"pose_img": False, "expr_img": True, "bg_img": False, "desc": "표정 이미지"},
    "D": {"pose_img": False, "expr_img": False, "bg_img": True, "desc": "배경 이미지"},
    "E": {
        "pose_img": True,
        "expr_img": True,
        "bg_img": False,
        "desc": "포즈+표정 이미지",
    },
    "F": {
        "pose_img": True,
        "expr_img": False,
        "bg_img": True,
        "desc": "포즈+배경 이미지",
    },
    "G": {
        "pose_img": False,
        "expr_img": True,
        "bg_img": True,
        "desc": "표정+배경 이미지",
    },
    "H": {
        "pose_img": True,
        "expr_img": True,
        "bg_img": True,
        "desc": "All Ref (모든 이미지)",
    },
}

NUM_IMAGES = 3
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"


# ============================================================
# SCHEMA LOADER
# ============================================================


def load_schema():
    """influencer_prompt_schema.json 로드"""
    schema_path = project_root / "db" / "influencer_prompt_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


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

    모든 분석 결과를 텍스트로 포함 (이미지 전송 여부와 무관)
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
    # 포즈
    # =====================================================
    lines.append("## [포즈] - Follow EXACTLY")
    lines.append(f"- stance: {pose_result.stance}")
    lines.append(f"- 왼팔: {pose_result.left_arm}")
    lines.append(f"- 오른팔: {pose_result.right_arm}")
    lines.append(f"- 왼손: {pose_result.left_hand}")
    lines.append(f"- 오른손: {pose_result.right_hand}")
    lines.append(f"- 왼다리: {pose_result.left_leg}")
    lines.append(f"- 오른다리: {pose_result.right_leg}")
    lines.append(f"- 힙: {pose_result.hip}")
    lines.append("")

    # =====================================================
    # 방향/기울기 (★★★ 매우 중요 - 정확히 재현 ★★★)
    # =====================================================
    lines.append("### [방향/기울기] ★★★ CRITICAL - EXACT DIRECTION ★★★")
    if pose_result.torso_tilt:
        lines.append(f"- 상체_기울기: {pose_result.torso_tilt}")
    if pose_result.left_foot_direction:
        lines.append(f"- 왼발_방향: {pose_result.left_foot_direction}")
    if pose_result.right_foot_direction:
        lines.append(f"- 오른발_방향: {pose_result.right_foot_direction}")
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
    # 네거티브
    # =====================================================
    lines.append("## [네거티브]")
    lines.append(
        "other people, crowd, bystanders, passersby, multiple people, random chair, random box, invented furniture, objects not in background reference, bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers, AI look, overprocessed"
    )
    lines.append("")

    # =====================================================
    # 이미지 역할 안내
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
    lines.append("[POSE REFERENCE] (if provided): Copy pose from this image")
    lines.append("  - Match body position EXACTLY")
    lines.append("  - Ignore face/outfit/background from this image")
    lines.append("")
    lines.append("[EXPRESSION REFERENCE] (if provided): Copy expression only")
    lines.append("  - Copy eyes, mouth, facial expression")
    lines.append("  - DO NOT copy hair from this image!")
    lines.append("")
    lines.append("[BACKGROUND REFERENCE] (if provided): Use this background")
    lines.append("  - Ignore any person in background image")
    lines.append("  - Match lighting/mood of background")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# IMAGE GENERATOR
# ============================================================


def generate_image(
    client,
    prompt: str,
    face_images: list,
    outfit_images: list,
    pose_image: Path = None,
    expression_image: Path = None,
    background_image: Path = None,
    include_pose_img: bool = False,
    include_expr_img: bool = False,
    include_bg_img: bool = False,
    temperature: float = 0.35,
) -> Image.Image:
    """
    이미지 생성

    프롬프트는 동일, 이미지 참조만 케이스별로 다름
    """

    parts = []

    # 1. 프롬프트 (모든 케이스 동일)
    parts.append(types.Part(text=prompt))

    # 2. 포즈 레퍼런스 (케이스별 선택)
    if include_pose_img and pose_image and pose_image.exists():
        img = Image.open(pose_image).convert("RGB")
        parts.append(types.Part(text="[POSE REFERENCE]"))
        parts.append(pil_to_part(img))

    # 3. 표정 레퍼런스 (케이스별 선택)
    if include_expr_img and expression_image and expression_image.exists():
        img = Image.open(expression_image).convert("RGB")
        parts.append(
            types.Part(text="[EXPRESSION REFERENCE] - Copy expression only, NOT hair")
        )
        parts.append(pil_to_part(img))

    # 4. 얼굴 이미지 (항상 전송)
    for i, face_path in enumerate(face_images):
        if face_path.exists():
            img = Image.open(face_path).convert("RGB")
            parts.append(
                types.Part(text=f"[FACE {i+1}] - Use this person's identity and hair")
            )
            parts.append(pil_to_part(img))

    # 5. 착장 이미지 (항상 전송)
    for i, outfit_path in enumerate(outfit_images):
        if outfit_path.exists():
            img = Image.open(outfit_path).convert("RGB")
            parts.append(types.Part(text=f"[OUTFIT {i+1}]"))
            parts.append(pil_to_part(img))

    # 6. 배경 이미지 (케이스별 선택)
    if include_bg_img and background_image and background_image.exists():
        img = Image.open(background_image).convert("RGB")
        parts.append(
            types.Part(text="[BACKGROUND REFERENCE] - Ignore person in this image")
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


def run_test_case(
    client,
    case_id: str,
    case_config: dict,
    prompt: str,
    face_images: list,
    outfit_images: list,
    pose_image: Path,
    expression_image: Path,
    background_image: Path,
    output_dir: Path,
) -> dict:
    """단일 테스트 케이스 실행"""

    print(f"\n{'=' * 60}")
    print(f"Case {case_id}: {case_config['desc']}")
    print(f"  - Pose image: {'Yes' if case_config['pose_img'] else 'No'}")
    print(f"  - Expression image: {'Yes' if case_config['expr_img'] else 'No'}")
    print(f"  - Background image: {'Yes' if case_config['bg_img'] else 'No'}")
    print(f"{'=' * 60}")

    # 케이스 출력 디렉토리
    case_dir = output_dir / f"case_{case_id}"
    images_dir = case_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 인풋 이미지 복사
    for face_path in face_images:
        if face_path.exists():
            shutil.copy(face_path, images_dir / f"input_face.png")
    for i, outfit_path in enumerate(outfit_images):
        shutil.copy(outfit_path, images_dir / f"input_outfit_{i+1:02d}.png")

    if case_config["pose_img"] and pose_image and pose_image.exists():
        shutil.copy(pose_image, images_dir / "input_pose.png")
    if case_config["expr_img"] and expression_image and expression_image.exists():
        shutil.copy(
            expression_image, images_dir / f"input_expression{expression_image.suffix}"
        )
    if case_config["bg_img"] and background_image and background_image.exists():
        shutil.copy(
            background_image, images_dir / f"input_background{background_image.suffix}"
        )

    # 프롬프트 저장 (모든 케이스 동일한 프롬프트)
    with open(case_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    # 이미지 생성
    results = []
    for i in range(NUM_IMAGES):
        print(f"[Generating] Image {i+1}/{NUM_IMAGES}...")

        image = generate_image(
            client=client,
            prompt=prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            include_pose_img=case_config["pose_img"],
            include_expr_img=case_config["expr_img"],
            include_bg_img=case_config["bg_img"],
            temperature=0.35,
        )

        if image:
            image.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)
            results.append({"index": i + 1, "status": "success"})
            print(f"  [OK] Saved output_{i+1:03d}.jpg")
        else:
            results.append({"index": i + 1, "status": "failed"})
            print(f"  [FAIL] Generation failed")

        time.sleep(2)  # Rate limit

    # 결과 저장
    success_count = sum(1 for r in results if r["status"] == "success")
    case_result = {
        "case_id": case_id,
        "description": case_config["desc"],
        "config": case_config,
        "generation_results": results,
        "success_rate": success_count / len(results) * 100 if results else 0,
    }

    with open(case_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump(case_result, f, ensure_ascii=False, indent=2)

    return case_result


def run_test(test_name: str, test_folder: Path, cases: list = None):
    """전체 테스트 실행"""

    print(f"\n{'#' * 60}")
    print(f"# AI INFLUENCER REFERENCE TEST: {test_name}")
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
        / "influencer_reference_test"
        / f"{test_name}_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # STEP 1: 모든 레퍼런스 분석 (한 번만)
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 1: Analyzing ALL references (once)")
    print("=" * 60)

    # 이미지 경로
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

    # 1-1. 헤어 분석
    print("\n[1-1] Analyzing hair from face image...")
    hair_info = analyze_hair(client, face_images[0])
    print(f"  Hair: {hair_info}")

    # 1-2. 표정 분석
    print("\n[1-2] Analyzing expression...")
    if expression_image and expression_image.exists():
        expression_info = analyze_expression(client, expression_image)
    else:
        expression_info = {
            "베이스": "cool",
            "바이브": "effortless",
            "시선": "direct",
            "입": "closed",
        }
    print(f"  Expression: {expression_info}")

    # 1-3. 포즈 분석
    print("\n[1-3] Analyzing pose...")
    if pose_image.exists():
        pose_result = analyze_pose(pose_image)
        print(f"  Stance: {pose_result.stance}, Framing: {pose_result.framing}")
    else:
        print(f"  [WARN] Pose image not found, using defaults")
        pose_result = None

    # 1-4. 배경 분석
    print("\n[1-4] Analyzing background...")
    if background_image and background_image.exists():
        background_result = analyze_background(background_image)
        print(
            f"  Scene: {background_result.scene_type}, Provides: {background_result.provides}"
        )
    else:
        print(f"  [WARN] Background image not found, using defaults")
        background_result = None

    # 1-5. 호환성 검사
    compatibility_result = None
    if pose_result and background_result:
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

    # =========================================================
    # STEP 2: 단일 프롬프트 생성 (모든 케이스 공통)
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 2: Building SINGLE prompt for ALL cases")
    print("=" * 60)

    if not pose_result or not background_result:
        print("[ERROR] Missing pose or background analysis, cannot continue")
        return

    prompt = build_schema_prompt(
        hair_info=hair_info,
        expression_info=expression_info,
        pose_result=pose_result,
        background_result=background_result,
        outfit_result=outfit_result,
        compatibility_result=compatibility_result,
    )

    # 프롬프트 저장
    with open(output_dir / "shared_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"  Saved: {output_dir / 'shared_prompt.txt'}")

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
    if compatibility_result:
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
    # STEP 3: 테스트 케이스 실행
    # =========================================================
    print("\n" + "=" * 60)
    print("STEP 3: Running test cases (same prompt, different images)")
    print("=" * 60)

    if cases is None:
        cases = list(TEST_CASES.keys())

    all_results = []

    for case_id in cases:
        if case_id not in TEST_CASES:
            print(f"[SKIP] Unknown case: {case_id}")
            continue

        case_result = run_test_case(
            client=client,
            case_id=case_id,
            case_config=TEST_CASES[case_id],
            prompt=prompt,  # 동일한 프롬프트
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            output_dir=output_dir,
        )
        all_results.append(case_result)

    # =========================================================
    # STEP 4: 전체 결과 저장
    # =========================================================
    summary = {
        "test_name": test_name,
        "test_folder": str(test_folder),
        "timestamp": timestamp,
        "total_cases": len(all_results),
        "analysis": {
            "hair": hair_info,
            "expression": expression_info,
            "pose": pose_result.to_schema_format() if pose_result else None,
            "background": background_result.to_schema_format()
            if background_result
            else None,
            "compatibility": {
                "level": compatibility_result.level.value
                if compatibility_result
                else None,
                "score": compatibility_result.score if compatibility_result else None,
            },
            "outfit": {
                "style": outfit_result.overall_style,
                "brand": outfit_result.brand_detected,
                "item_count": len(outfit_result.items),
            },
        },
        "cases": all_results,
    }

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print(f"\n{'=' * 60}")
    print(f"TEST COMPLETE: {test_name}")
    print(f"{'=' * 60}")
    print(f"Output: {output_dir}")
    print(f"\nResults:")
    for result in all_results:
        print(f"  Case {result['case_id']}: {result['success_rate']:.0f}% success")

    return summary


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Influencer Reference Test")
    parser.add_argument(
        "--test",
        type=str,
        default="test1",
        choices=["test1", "test2", "test3", "all"],
        help="Test folder to use",
    )
    parser.add_argument(
        "--cases",
        type=str,
        default=None,
        help="Comma-separated case IDs (e.g., 'A,B,H')",
    )

    args = parser.parse_args()

    # 테스트 케이스 파싱
    cases = None
    if args.cases:
        cases = [c.strip().upper() for c in args.cases.split(",")]

    # 테스트 실행
    if args.test == "all":
        for test_name, test_folder in TEST_FOLDERS.items():
            run_test(test_name, test_folder, cases)
    else:
        test_folder = TEST_FOLDERS.get(args.test)
        if test_folder:
            run_test(args.test, test_folder, cases)
        else:
            print(f"Unknown test: {args.test}")
