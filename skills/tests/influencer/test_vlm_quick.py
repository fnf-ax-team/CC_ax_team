"""
인플테스트용 폴더 이미지로 VLM 분석기 테스트

테스트 이미지:
- 포즈.png
- 표정.jpeg
- 배경.jpeg
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from core.ai_influencer import (
    analyze_pose,
    analyze_background,
    check_compatibility,
    CompatibilityLevel,
)
from core.outfit_analyzer import OutfitAnalyzer
from google import genai
from core.api import _get_next_api_key


# ============================================================
# TEST IMAGES
# ============================================================
TEST_DIR = project_root / "tests" / "인플테스트용"

POSE_IMAGE = TEST_DIR / "포즈.png"
EXPRESSION_IMAGE = TEST_DIR / "표정.jpeg"
BACKGROUND_IMAGE = TEST_DIR / "배경.jpeg"
FACE_IMAGE = TEST_DIR / "얼굴.png"
OUTFIT_IMAGES = [
    TEST_DIR / "착장 (1).png",
    TEST_DIR / "착장 (2).png",
    TEST_DIR / "착장 (3).png",
    TEST_DIR / "착장 (4).png",
]


def main():
    print("=" * 60)
    print("VLM Analyzer Quick Test - 인플테스트용")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Dir: {TEST_DIR}")
    print()

    # GenAI client for outfit analysis
    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)

    results = {}

    # 1. 포즈 분석
    print("[1] POSE ANALYSIS")
    print("-" * 40)
    if POSE_IMAGE.exists():
        print(f"Image: {POSE_IMAGE.name}")
        pose_result = analyze_pose(POSE_IMAGE)

        print(f"\n[RESULT]")
        print(f"  stance: {pose_result.stance}")
        print(f"  confidence: {pose_result.confidence:.2f}")
        print(f"  camera_angle: {pose_result.camera_angle}")
        print(f"  camera_height: {pose_result.camera_height}")
        print(f"  framing: {pose_result.framing}")
        print(f"\n  [Body Parts]")
        print(f"    left_arm: {pose_result.left_arm}")
        print(f"    right_arm: {pose_result.right_arm}")
        print(f"    left_hand: {pose_result.left_hand}")
        print(f"    right_hand: {pose_result.right_hand}")
        print(f"    left_leg: {pose_result.left_leg}")
        print(f"    right_leg: {pose_result.right_leg}")
        print(f"    hip: {pose_result.hip}")

        results["pose"] = {
            "stance": pose_result.stance,
            "confidence": pose_result.confidence,
            "camera_angle": pose_result.camera_angle,
            "framing": pose_result.framing,
            "body_parts": pose_result.to_schema_format(),
        }
    else:
        print(f"[SKIP] File not found: {POSE_IMAGE}")

    print()

    # 2. 배경 분석
    print("[2] BACKGROUND ANALYSIS")
    print("-" * 40)
    if BACKGROUND_IMAGE.exists():
        print(f"Image: {BACKGROUND_IMAGE.name}")
        bg_result = analyze_background(BACKGROUND_IMAGE)

        print(f"\n[RESULT]")
        print(f"  scene_type: {bg_result.scene_type}")
        print(f"  region: {bg_result.region}")
        print(f"  time_of_day: {bg_result.time_of_day}")
        print(f"  color_tone: {bg_result.color_tone}")
        print(f"  mood: {bg_result.mood}")
        print(f"  confidence: {bg_result.confidence:.2f}")
        print(f"\n  [Provides]: {bg_result.provides}")
        print(f"  [Supported Stances]: {bg_result.supported_stances}")
        if bg_result.potential_seating_locations:
            print(f"  [Potential Seating Locations]:")
            for loc in bg_result.potential_seating_locations:
                print(f"    - {loc}")
        if bg_result.notes:
            print(f"  [Notes]:")
            for note in bg_result.notes:
                print(f"    - {note}")

        results["background"] = {
            "scene_type": bg_result.scene_type,
            "region": bg_result.region,
            "provides": bg_result.provides,
            "supported_stances": bg_result.supported_stances,
            "potential_seating_locations": bg_result.potential_seating_locations,
            "confidence": bg_result.confidence,
        }
    else:
        print(f"[SKIP] File not found: {BACKGROUND_IMAGE}")

    print()

    # 3. 착장 분석
    print("[3] OUTFIT ANALYSIS")
    print("-" * 40)
    existing_outfits = [p for p in OUTFIT_IMAGES if p.exists()]
    if existing_outfits:
        print(f"Images: {[p.name for p in existing_outfits]}")

        outfit_analyzer = OutfitAnalyzer(client)
        outfit_result = outfit_analyzer.analyze([str(p) for p in existing_outfits])

        print(f"\n[RESULT]")
        print(f"  overall_style: {outfit_result.overall_style}")
        print(f"  formality: {outfit_result.formality}")
        print(f"  style_era: {outfit_result.style_era}")
        print(f"  brand_detected: {outfit_result.brand_detected}")
        print(f"  color_palette: {outfit_result.color_palette}")

        print(f"\n  [Items] ({len(outfit_result.items)} items)")
        for i, item in enumerate(outfit_result.items, 1):
            print(f"    {i}. {item.category}: {item.name}")
            print(f"       color: {item.color}, fit: {item.fit}")
            if item.logos:
                for logo in item.logos:
                    print(f"       logo: {logo.brand} ({logo.type}) at {logo.position}")
            if item.details:
                print(f"       details: {', '.join(item.details)}")

        results["outfit"] = {
            "overall_style": outfit_result.overall_style,
            "formality": outfit_result.formality,
            "style_era": outfit_result.style_era,
            "brand_detected": outfit_result.brand_detected,
            "color_palette": outfit_result.color_palette,
            "item_count": len(outfit_result.items),
            "items": [
                {
                    "category": item.category,
                    "name": item.name,
                    "color": item.color,
                    "fit": item.fit,
                }
                for item in outfit_result.items
            ],
        }
    else:
        print(f"[SKIP] No outfit images found")

    print()

    # 4. 호환성 검사
    print("[4] COMPATIBILITY CHECK")
    print("-" * 40)
    if POSE_IMAGE.exists() and BACKGROUND_IMAGE.exists():
        compat_result = check_compatibility(pose_result, bg_result)

        level_emoji = {
            CompatibilityLevel.COMPATIBLE: "[OK]",
            CompatibilityLevel.ADJUSTABLE: "[!]",
            CompatibilityLevel.INCOMPATIBLE: "[X]",
        }

        print(f"\n[RESULT]")
        print(
            f"  Level: {level_emoji.get(compat_result.level, '[-]')} {compat_result.level.value}"
        )
        print(f"  Score: {compat_result.score}/100")
        print(f"  Pose Stance: {compat_result.pose_stance}")
        print(f"  Background Provides: {compat_result.background_provides}")
        print(f"  Background Supports: {compat_result.background_supports}")

        if compat_result.issues:
            print(f"\n  [Issues]")
            for issue in compat_result.issues:
                severity_icon = {
                    "critical": "[X]",
                    "warning": "[!]",
                    "info": "[i]",
                }.get(issue.severity, "[-]")
                print(f"    {severity_icon} {issue.description}")
                print(f"        -> {issue.suggestion}")

        if compat_result.alternative_stances:
            print(f"\n  [Alternative Stances]: {compat_result.alternative_stances}")

        if compat_result.suggested_adjustments:
            print(f"\n  [Suggested Adjustments]")
            for adj in compat_result.suggested_adjustments:
                print(f"    - {adj}")

        results["compatibility"] = {
            "level": compat_result.level.value,
            "score": compat_result.score,
            "is_compatible": compat_result.is_compatible(),
            "issues": [
                {
                    "type": i.issue_type,
                    "severity": i.severity,
                    "description": i.description,
                }
                for i in compat_result.issues
            ],
            "alternative_stances": compat_result.alternative_stances,
        }

    print()

    # 5. 결과 저장
    print("[5] SAVE RESULTS")
    print("-" * 40)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "Fnf_studio_outputs" / "vlm_quick_test" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {output_dir}")

    # 6. 요약
    print()
    print("=" * 60)
    print("[SUMMARY]")
    print("=" * 60)

    if "pose" in results:
        print(f"Pose: {results['pose']['stance']} ({results['pose']['framing']})")

    if "outfit" in results:
        print(
            f"Outfit: {results['outfit']['item_count']} items, style={results['outfit']['overall_style']}"
        )

    if "background" in results:
        print(
            f"Background: {results['background']['scene_type']} - supports {results['background']['supported_stances']}"
        )

    if "compatibility" in results:
        compat = results["compatibility"]
        status = "COMPATIBLE" if compat["is_compatible"] else "INCOMPATIBLE"
        print(f"Compatibility: {status} (score: {compat['score']}/100)")

        if not compat["is_compatible"]:
            print(f"  -> Alternatives: {compat['alternative_stances']}")

    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
