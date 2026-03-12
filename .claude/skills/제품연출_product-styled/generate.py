"""
제품 연출 스킬 - 메인 실행 스크립트
"""

import os
import sys
from typing import Dict, Optional
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.config import IMAGE_MODEL, VISION_MODEL
from pipeline import run_product_styled_pipeline
from styled_generator import PRESETS, SHOT_TYPES


def get_api_key() -> str:
    """
    환경변수에서 Gemini API 키 로드
    """
    load_dotenv()

    api_keys_str = os.getenv("GEMINI_API_KEY", "")
    if not api_keys_str:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    # 첫 번째 키 사용
    api_keys = [k.strip() for k in api_keys_str.split(",")]
    return api_keys[0]


def print_welcome():
    """웰컴 메시지 출력"""
    print("\n" + "="*60)
    print("📸 **제품 연출 스킬**에 오신 걸 환영합니다!")
    print("="*60)
    print("\n상세페이지, 라이프스타일, 디테일샷 등 다양한 제품 촬영 스타일 지원.")
    print(f"\n사용 모델:")
    print(f"  - 이미지 생성: {IMAGE_MODEL}")
    print(f"  - VLM 분석: {VISION_MODEL}")
    print()


def get_product_image() -> str:
    """제품 이미지 경로 입력받기"""
    print("📷 **제품 이미지 업로드**")
    print("\n권장 이미지:")
    print("  - 투명 배경 PNG (또는 단색 배경)")
    print("  - 정면/측면/디테일 각도")
    print("  - 최소 1024x1024 해상도")
    print("  - 제품 색상이 명확히 보이는 사진")
    print()

    while True:
        image_path = input("제품 이미지 경로 입력: ").strip()

        if os.path.exists(image_path):
            return image_path
        else:
            print(f"⚠️  파일을 찾을 수 없습니다: {image_path}")
            print("다시 입력해주세요.\n")


def select_style_preset() -> str:
    """스타일 프리셋 선택"""
    print("\n" + "="*60)
    print("🎨 **촬영 스타일 선택**")
    print("="*60)

    presets = list(PRESETS.keys())
    for i, preset in enumerate(presets, 1):
        use_case = PRESETS[preset]["use_case"]
        print(f"{i}. {preset} - {use_case}")

    while True:
        try:
            choice = input(f"\n스타일 선택 (1-{len(presets)}): ").strip()
            idx = int(choice) - 1

            if 0 <= idx < len(presets):
                selected = presets[idx]
                print(f"✅ 선택: {selected}")
                return selected
            else:
                print(f"⚠️  1-{len(presets)} 범위의 숫자를 입력하세요.")
        except ValueError:
            print("⚠️  숫자를 입력하세요.")


def select_shot_type() -> str:
    """샷 타입 선택"""
    print("\n" + "="*60)
    print("📷 **샷 타입 선택**")
    print("="*60)

    shot_types = list(SHOT_TYPES.keys())
    descriptions = {
        "product_shot": "제품 단독샷 (hero 이미지)",
        "lifestyle": "라이프스타일 연출샷 (소품/배경 포함)",
        "detail": "디테일 클로즈업 (로고/소재 강조)",
        "group": "그룹샷/코디 (여러 제품 조합)"
    }

    for i, shot_type in enumerate(shot_types, 1):
        desc = descriptions.get(shot_type, "")
        print(f"{i}. {shot_type} - {desc}")

    while True:
        try:
            choice = input(f"\n샷 타입 선택 (1-{len(shot_types)}): ").strip()
            idx = int(choice) - 1

            if 0 <= idx < len(shot_types):
                selected = shot_types[idx]
                print(f"✅ 선택: {selected}")
                return selected
            else:
                print(f"⚠️  1-{len(shot_types)} 범위의 숫자를 입력하세요.")
        except ValueError:
            print("⚠️  숫자를 입력하세요.")


def select_options() -> Dict:
    """추가 옵션 선택"""
    print("\n" + "="*60)
    print("⚙️  **추가 옵션** (선택사항)")
    print("="*60)
    print("1. 기본 설정으로 진행")
    print("2. 색상 강조 (vivid color boost)")
    print("3. 프리미엄 텍스처 (고급 질감)")
    print("4. 특정 비율 지정 (1:1, 3:4, 16:9 등)")

    options = {}

    while True:
        choice = input("\n옵션 선택 (1-4, 여러 개 선택 가능. 예: 2,3): ").strip()

        if choice == "1":
            print("✅ 기본 설정으로 진행합니다.")
            break

        selected = [c.strip() for c in choice.split(",")]

        if "2" in selected:
            options["vivid_colors"] = True
            print("✅ 색상 강조 활성화")

        if "3" in selected:
            options["premium_texture"] = True
            print("✅ 프리미엄 텍스처 활성화")

        if "4" in selected:
            print("\n비율 선택:")
            print("1. 1:1 (정사각형, Instagram)")
            print("2. 3:4 (세로, 모바일 친화)")
            print("3. 4:3 (가로, 이커머스)")
            print("4. 16:9 (와이드, 배너)")

            ratio_choice = input("비율 선택 (1-4): ").strip()
            ratio_map = {
                "1": "1:1",
                "2": "3:4",
                "3": "4:3",
                "4": "16:9"
            }

            if ratio_choice in ratio_map:
                options["aspect_ratio"] = ratio_map[ratio_choice]
                print(f"✅ 비율: {ratio_map[ratio_choice]}")

        break

    return options


def print_result(result: Dict):
    """결과 출력"""
    print("\n" + "="*60)
    print("✅ **제품 연출 완료**")
    print("="*60)

    metadata = result["metadata"]
    product_analysis = result["product_analysis"]
    validation = result["validation"]

    print(f"\n📸 **스타일:** {metadata['style_preset']}")
    print(f"📷 **샷 타입:** {metadata['shot_type']}")

    print(f"\n🎨 **제품 분석:**")
    print(f"  - 제품: {product_analysis['product_type']}")
    print(f"  - 주요 색상: {', '.join(product_analysis['dominant_colors'])}")
    print(f"  - 소재: {product_analysis['material']}")
    print(f"  - 특징: {', '.join(product_analysis['key_features'])}")

    print(f"\n✅ **검증 결과:**")
    print(f"  - 색상 정확도: {validation['accuracy_score']}%")

    if validation.get("issues"):
        print(f"  - 이슈: {', '.join(validation['issues'])}")
    else:
        print(f"  - 이슈: 없음")

    print(f"\n💾 **저장 위치:**")
    print(f"  - {result['final_image_path']}")
    print()


def main():
    """메인 실행 함수"""
    try:
        # API 키 로드
        api_key = get_api_key()

        # 대화형 플로우
        print_welcome()

        # 1. 제품 이미지 입력
        product_image = get_product_image()

        # 2. 스타일 프리셋 선택
        style_preset = select_style_preset()

        # 3. 샷 타입 선택
        shot_type = select_shot_type()

        # 4. 추가 옵션 선택
        options = select_options()

        # 5. 생성 시작
        print("\n" + "="*60)
        print("🎬 생성을 시작합니다...")
        print("="*60)

        result = run_product_styled_pipeline(
            product_image=product_image,
            style_preset=style_preset,
            shot_type=shot_type,
            api_key=api_key,
            options=options
        )

        # 6. 결과 출력
        print_result(result)

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
