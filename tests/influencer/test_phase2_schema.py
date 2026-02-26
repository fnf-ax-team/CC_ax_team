"""
Phase 2 테스트: 스키마 프롬프트 vs 간단 프롬프트 비교

개선사항:
1. VLM 분석 결과를 스키마 형태로 프롬프트에 포함
2. 포즈 분석에서 물체 추측 제거
3. 헤어 컬러/스타일 고정
4. 배경-포즈 호환성 사전 검증
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

from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key
from core.ai_influencer import (
    analyze_pose,
    analyze_background,
    check_compatibility,
    PoseAnalysisResult,
    BackgroundAnalysisResult,
)
from core.outfit_analyzer import OutfitAnalyzer


# ============================================================
# TEST CONFIGURATIONS
# ============================================================

TEST_FOLDERS = {
    "test1": project_root / "tests" / "인플테스트용",
    "test2": project_root / "tests" / "인플테스트2",
    "test3": project_root / "tests" / "인플테스트3",
}

# 테스트 케이스 정의
TEST_CASES = {
    "A": {
        "pose": False,
        "expression": False,
        "background": False,
        "desc": "베이스라인 (레퍼런스 없음)",
    },
    "B": {"pose": True, "expression": False, "background": False, "desc": "포즈만"},
    "C": {"pose": False, "expression": True, "background": False, "desc": "표정만"},
    "D": {"pose": False, "expression": False, "background": True, "desc": "배경만"},
    "E": {"pose": True, "expression": True, "background": False, "desc": "포즈+표정"},
    "F": {"pose": True, "expression": False, "background": True, "desc": "포즈+배경"},
    "G": {"pose": False, "expression": True, "background": True, "desc": "표정+배경"},
    "H": {
        "pose": True,
        "expression": True,
        "background": True,
        "desc": "All Ref (포즈+표정+배경)",
    },
}

# 생성 설정
NUM_IMAGES = 3
ASPECT_RATIO = "9:16"
RESOLUTION = "2K"


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    from io import BytesIO

    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def analyze_face_for_hair(client, face_image_path: Path) -> dict:
    """얼굴 이미지에서 헤어 정보 추출"""

    prompt = """이 이미지에서 인물의 헤어 정보를 분석하세요.

JSON 형식으로 출력:
```json
{
    "hair_color": "다크브라운/블랙/브라운/금발/등",
    "hair_length": "롱/미디엄/숏/등",
    "hair_style": "스트레이트/웨이브/컬/등",
    "hair_texture": "부드러운/볼륨있는/등"
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
                    parts=[
                        types.Part(text=prompt),
                        pil_to_part(img),
                    ],
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
        return {
            "hair_color": "다크브라운",
            "hair_length": "롱",
            "hair_style": "스트레이트",
            "hair_texture": "부드러운",
        }


def build_schema_prompt(
    pose_result: PoseAnalysisResult = None,
    background_result: BackgroundAnalysisResult = None,
    outfit_result=None,
    hair_info: dict = None,
    compatibility_result=None,
) -> str:
    """스키마 기반 상세 프롬프트 생성"""

    lines = []

    # 1. 헤어 고정 (최우선)
    if hair_info:
        lines.append("## [CRITICAL] HAIR - DO NOT CHANGE")
        lines.append(f"- Color: {hair_info.get('hair_color', '다크브라운')}")
        lines.append(f"- Length: {hair_info.get('hair_length', '롱')}")
        lines.append(f"- Style: {hair_info.get('hair_style', '스트레이트')}")
        lines.append(f"- Texture: {hair_info.get('hair_texture', '부드러운')}")
        lines.append("")
        lines.append("IMPORTANT: Keep hair color and style EXACTLY as specified above!")
        lines.append("Do NOT copy hair from expression or background reference images.")
        lines.append("")

    # 2. 포즈 스키마
    if pose_result:
        lines.append("## [POSE SCHEMA] - Follow EXACTLY")
        lines.append(f"- stance: {pose_result.stance}")
        lines.append(f"- left_arm: {pose_result.left_arm}")
        lines.append(f"- right_arm: {pose_result.right_arm}")
        lines.append(f"- left_hand: {pose_result.left_hand}")
        lines.append(f"- right_hand: {pose_result.right_hand}")
        lines.append(f"- left_leg: {pose_result.left_leg}")
        lines.append(f"- right_leg: {pose_result.right_leg}")
        lines.append(f"- hip: {pose_result.hip}")
        lines.append("")
        lines.append(f"- camera_angle: {pose_result.camera_angle}")
        lines.append(f"- camera_height: {pose_result.camera_height}")
        lines.append(f"- framing: {pose_result.framing}")
        lines.append("")

    # 3. 배경 스키마
    if background_result:
        lines.append("## [BACKGROUND SCHEMA]")
        lines.append(f"- scene_type: {background_result.scene_type}")
        lines.append(f"- region: {background_result.region}")
        lines.append(f"- time_of_day: {background_result.time_of_day}")
        lines.append(f"- color_tone: {background_result.color_tone}")
        lines.append(f"- mood: {background_result.mood}")
        lines.append("")

        # 호환성 경고
        if compatibility_result and not compatibility_result.is_compatible():
            lines.append("## [COMPATIBILITY WARNING]")
            for issue in compatibility_result.issues:
                lines.append(f"- {issue.description}")
            if compatibility_result.suggested_adjustments:
                lines.append("Adjustments:")
                for adj in compatibility_result.suggested_adjustments:
                    lines.append(f"  - {adj}")
            lines.append("")

    # 4. 착장 스키마
    if outfit_result:
        lines.append("## [OUTFIT SCHEMA] - Match EXACTLY")
        lines.append(f"- overall_style: {outfit_result.overall_style}")
        lines.append(f"- brand: {outfit_result.brand_detected}")
        lines.append(f"- color_palette: {', '.join(outfit_result.color_palette)}")
        lines.append("")
        for i, item in enumerate(outfit_result.items, 1):
            lines.append(f"Item {i}: {item.category}")
            lines.append(f"  - name: {item.name}")
            lines.append(f"  - color: {item.color}")
            lines.append(f"  - fit: {item.fit}")
            if item.logos:
                for logo in item.logos:
                    lines.append(
                        f"  - logo: {logo.brand} ({logo.type}) at {logo.position}"
                    )
        lines.append("")

    # 5. 이미지 역할 설명
    lines.append("## [IMAGE ROLES]")
    lines.append("")

    if pose_result:
        lines.append("POSE REFERENCE:")
        lines.append("- Copy EXACT pose from schema above")
        lines.append("- Match camera angle, height, framing")
        lines.append("- Ignore face/outfit/background from this image")
        lines.append("")

    lines.append("FACE images: Use this person's face")
    lines.append("- KEEP hair color/style as specified in HAIR section!")
    lines.append("")

    if outfit_result:
        lines.append("OUTFIT images: Match outfit EXACTLY")
        lines.append("- Copy colors, logos, details")
        lines.append("")

    if background_result:
        lines.append("BACKGROUND REFERENCE: Use this background")
        lines.append("- Ignore any person in background image")
        lines.append("")

    return "\n".join(lines)


def generate_with_schema(
    client,
    face_images: list,
    outfit_images: list,
    pose_image: Path = None,
    expression_image: Path = None,
    background_image: Path = None,
    schema_prompt: str = None,
    temperature: float = 0.35,
) -> Image.Image:
    """스키마 프롬프트를 사용하여 이미지 생성"""

    parts = []

    # 1. 스키마 프롬프트
    if schema_prompt:
        parts.append(types.Part(text=schema_prompt))

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
        from io import BytesIO

        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data))

        return None

    except Exception as e:
        print(f"[Generate] Error: {e}")
        return None


def run_test_case(
    client,
    test_folder: Path,
    case_id: str,
    case_config: dict,
    output_dir: Path,
    hair_info: dict,
    outfit_result,
) -> dict:
    """단일 테스트 케이스 실행"""

    print(f"\n{'=' * 60}")
    print(f"Case {case_id}: {case_config['desc']}")
    print(f"{'=' * 60}")

    # 이미지 경로
    face_images = [test_folder / "얼굴.png"]
    outfit_images = list(test_folder.glob("착장*.png"))
    pose_image = test_folder / "포즈.png" if case_config["pose"] else None
    expression_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        expr_path = test_folder / f"표정{ext}"
        if expr_path.exists():
            expression_image = expr_path if case_config["expression"] else None
            break

    background_image = None
    for ext in [".png", ".jpeg", ".jpg"]:
        bg_path = test_folder / f"배경{ext}"
        if bg_path.exists():
            background_image = bg_path if case_config["background"] else None
            break

    # VLM 분석
    pose_result = None
    background_result = None
    compatibility_result = None

    if case_config["pose"] and pose_image and pose_image.exists():
        print("[Analyzing] Pose...")
        pose_result = analyze_pose(pose_image)
        print(f"  stance: {pose_result.stance}, framing: {pose_result.framing}")

    if case_config["background"] and background_image and background_image.exists():
        print("[Analyzing] Background...")
        background_result = analyze_background(background_image)
        print(
            f"  scene: {background_result.scene_type}, provides: {background_result.provides}"
        )

        # 호환성 검사
        if pose_result:
            print("[Checking] Compatibility...")
            compatibility_result = check_compatibility(pose_result, background_result)
            print(
                f"  level: {compatibility_result.level.value}, score: {compatibility_result.score}"
            )

    # 스키마 프롬프트 생성
    schema_prompt = build_schema_prompt(
        pose_result=pose_result,
        background_result=background_result,
        outfit_result=outfit_result,
        hair_info=hair_info,
        compatibility_result=compatibility_result,
    )

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
    if pose_image and pose_image.exists():
        shutil.copy(pose_image, images_dir / "input_pose.png")
    if expression_image and expression_image.exists():
        shutil.copy(
            expression_image, images_dir / f"input_expression{expression_image.suffix}"
        )
    if background_image and background_image.exists():
        shutil.copy(
            background_image, images_dir / f"input_background{background_image.suffix}"
        )

    # 프롬프트 저장
    with open(case_dir / "schema_prompt.txt", "w", encoding="utf-8") as f:
        f.write(schema_prompt)

    # 이미지 생성
    results = []
    for i in range(NUM_IMAGES):
        print(f"[Generating] Image {i+1}/{NUM_IMAGES}...")

        image = generate_with_schema(
            client=client,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            schema_prompt=schema_prompt,
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
    case_result = {
        "case_id": case_id,
        "description": case_config["desc"],
        "config": case_config,
        "pose_analysis": pose_result.to_schema_format() if pose_result else None,
        "background_analysis": background_result.to_schema_format()
        if background_result
        else None,
        "compatibility": {
            "level": compatibility_result.level.value if compatibility_result else None,
            "score": compatibility_result.score if compatibility_result else None,
        }
        if compatibility_result
        else None,
        "hair_info": hair_info,
        "generation_results": results,
        "success_rate": sum(1 for r in results if r["status"] == "success")
        / len(results)
        * 100,
    }

    with open(case_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump(case_result, f, ensure_ascii=False, indent=2)

    return case_result


def run_phase2_test(test_name: str, test_folder: Path, cases: list = None):
    """Phase 2 테스트 실행"""

    print(f"\n{'#' * 60}")
    print(f"# PHASE 2 TEST: {test_name}")
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
        / "phase2_schema"
        / f"{test_name}_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 헤어 분석 (한 번만)
    print("\n[Step 1] Analyzing hair from face image...")
    face_image = test_folder / "얼굴.png"
    hair_info = analyze_face_for_hair(client, face_image)
    print(f"  Hair: {hair_info}")

    # 2. 착장 분석 (한 번만)
    print("\n[Step 2] Analyzing outfit...")
    outfit_images = list(test_folder.glob("착장*.png"))
    outfit_analyzer = OutfitAnalyzer(client)
    outfit_result = outfit_analyzer.analyze([str(p) for p in outfit_images])
    print(f"  Style: {outfit_result.overall_style}")
    print(f"  Brand: {outfit_result.brand_detected}")
    print(f"  Items: {len(outfit_result.items)}")

    # 3. 테스트 케이스 실행
    if cases is None:
        cases = list(TEST_CASES.keys())

    all_results = []

    for case_id in cases:
        if case_id not in TEST_CASES:
            print(f"[SKIP] Unknown case: {case_id}")
            continue

        case_result = run_test_case(
            client=client,
            test_folder=test_folder,
            case_id=case_id,
            case_config=TEST_CASES[case_id],
            output_dir=output_dir,
            hair_info=hair_info,
            outfit_result=outfit_result,
        )
        all_results.append(case_result)

    # 4. 전체 결과 저장
    summary = {
        "test_name": test_name,
        "test_folder": str(test_folder),
        "timestamp": timestamp,
        "total_cases": len(all_results),
        "hair_info": hair_info,
        "outfit_summary": {
            "style": outfit_result.overall_style,
            "brand": outfit_result.brand_detected,
            "item_count": len(outfit_result.items),
        },
        "cases": all_results,
    }

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 5. 결과 출력
    print(f"\n{'=' * 60}")
    print(f"PHASE 2 TEST COMPLETE: {test_name}")
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

    parser = argparse.ArgumentParser(description="Phase 2 Schema Prompt Test")
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
            run_phase2_test(test_name, test_folder, cases)
    else:
        test_folder = TEST_FOLDERS.get(args.test)
        if test_folder:
            run_phase2_test(args.test, test_folder, cases)
        else:
            print(f"Unknown test: {args.test}")
