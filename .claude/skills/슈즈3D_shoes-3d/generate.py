"""
슈즈 3D 생성 메인 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import IMAGE_MODEL, VISION_MODEL, TRIPO_API_KEY

# 절대 import로 변경
try:
    from .pipeline import Shoes3DPipeline
except ImportError:
    from pipeline import Shoes3DPipeline


def get_gemini_api_key() -> str:
    """환경변수에서 Gemini API 키 로드"""
    api_keys = os.getenv("GEMINI_API_KEY", "")
    if not api_keys:
        raise ValueError("GEMINI_API_KEY not set in .env file")

    # 멀티 키 로테이션 지원 (첫 번째 키 사용)
    keys = [k.strip() for k in api_keys.split(",") if k.strip()]
    return keys[0]


async def main():
    """대화형 플로우 실행"""
    print("=== 슈즈 3D 생성 ===\n")

    # 1. 입력 이미지 수집
    print("신발 이미지를 업로드해주세요 (여러 각도 사진일수록 좋습니다)")
    print("이미지 경로를 입력하세요 (여러 개는 쉼표로 구분):")
    image_paths_input = input("> ").strip()

    if not image_paths_input:
        print("❌ 이미지 경로를 입력해주세요")
        return

    image_paths = [p.strip() for p in image_paths_input.split(",")]

    # 파일 존재 확인
    for path in image_paths:
        if not Path(path).exists():
            print(f"❌ 파일을 찾을 수 없음: {path}")
            return

    print(f"✅ {len(image_paths)}개 이미지 로드됨\n")

    # 2. 품질 선택
    print("3D 모델 품질을 선택하세요:")
    print("1. 빠른 프리뷰 (1분, 20K 폴리곤)")
    print("2. 표준 품질 (3분, 50K 폴리곤) [기본값]")
    print("3. 프리미엄 (5분, 100K 폴리곤 + PBR)")
    quality_input = input("선택 (1-3): ").strip()

    quality_map = {
        "1": "draft",
        "2": "standard",
        "3": "premium"
    }
    quality = quality_map.get(quality_input, "standard")
    print(f"✅ 품질: {quality}\n")

    # 3. 렌더링 각도 선택
    print("렌더링할 각도를 선택하세요 (쉼표로 구분):")
    print("1. 정면 (Front)")
    print("2. 측면 (Side)")
    print("3. 후면 (Back)")
    print("4. 윗면 (Top)")
    print("5. 밑창 (Bottom)")
    print("6. 3/4 뷰 (Three-quarter)")
    print("7. 전체 7각도")
    angles_input = input("선택 (1-7 또는 'all'): ").strip()

    angle_map = {
        "1": ["front"],
        "2": ["side"],
        "3": ["back"],
        "4": ["top"],
        "5": ["bottom"],
        "6": ["three_quarter"],
        "7": ["front", "back", "left", "right", "top", "bottom", "three_quarter"],
        "all": ["front", "back", "left", "right", "top", "bottom", "three_quarter"]
    }

    if angles_input in angle_map:
        render_angles = angle_map[angles_input]
    else:
        # 다중 선택 파싱
        selected = [s.strip() for s in angles_input.split(",")]
        render_angles = []
        for s in selected:
            if s in angle_map:
                render_angles.extend(angle_map[s])

    if not render_angles:
        render_angles = ["front", "side", "three_quarter"]

    print(f"✅ 렌더링 각도: {', '.join(render_angles)}\n")

    # 4. 배경 옵션
    print("배경 스타일:")
    print("1. 투명 배경 (PNG)")
    print("2. 순백 스튜디오 [기본값]")
    print("3. 그라데이션 배경")
    print("4. 실내 환경 (HDRI)")
    background_input = input("선택 (1-4): ").strip()

    background_map = {
        "1": "transparent",
        "2": "white_studio",
        "3": "gradient",
        "4": "indoor_hdri"
    }
    background = background_map.get(background_input, "white_studio")
    print(f"✅ 배경: {background}\n")

    # API 키 로드
    try:
        gemini_api_key = get_gemini_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return

    # 파이프라인 실행
    print("=== 3D 생성 시작 ===\n")

    try:
        pipeline = Shoes3DPipeline(
            gemini_api_key=gemini_api_key,
            tripo_api_key=TRIPO_API_KEY
        )

        result = await pipeline.run(
            input_images=image_paths,
            quality=quality,
            render_angles=render_angles,
            background=background
        )

        print("\n=== 생성 완료 ===")
        print(f"✅ 3D 모델: {result.model_path}")
        print(f"📸 렌더링: {len(result.renders)}개")
        print(f"🎯 형태 정확도: {result.validation['shape_accuracy']:.1f}%")
        print(f"🎨 소재 충실도: {result.validation['material_fidelity']:.1f}%")
        print(f"🌈 색상 일치도: {result.validation['color_match']:.1f}%")
        print(f"⭐ 총점: {result.validation['overall_score']:.1f}%")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
