"""
MLB 거울 셀카 완성 (백스테이지 대기실)
- 콘서트 대기실에서 거울 앞 셀카 촬영
- 3컷 생성 (포즈/표정/앵글 자동 변경)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Windows 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# .env 로드
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    print("[OK] .env loaded")

from workflow import ImageGenerationWorkflow
from PIL import Image

# core.config import를 위한 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core.config import OUTPUT_BASE_DIR

# 경로 설정
OUTPUT_DIR = Path(OUTPUT_BASE_DIR)
LOG_DIR = OUTPUT_DIR / "logs"

# 모델 이미지 (얼굴)
MODEL_FILES = [
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\MLB_KARINA\MLB_KARINA (15).jpg"),
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\MLB_KARINA\MLB_KARINA (18).jpg"),
]

# 착장 이미지
OUTFIT_FILES = [
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\새 폴더\스크린샷 2025-11-27 180704.png"),
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\새 폴더\스크린샷 2025-12-11 203420.png"),
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\새 폴더\스크린샷 2025-12-12 121521.png"),
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\새 폴더\화면 캡처 2025-10-17 101457.png"),
    Path(r"D:\FNF_Studio_TEST\New-fnf-studio\test_imgs\새 폴더\화면 캡처 2025-10-17 105825.png"),
]

def main():
    print("=" * 80)
    print("MLB 거울 셀카 완성 (백스테이지 대기실, 3컷)")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # PIL Image로 로드
    print(f"\n[모델 이미지] {len(MODEL_FILES)}장")
    for p in MODEL_FILES:
        print(f"  - {p.name}")
    model_images = [Image.open(f) for f in MODEL_FILES if f.exists()]

    print(f"\n[착장 이미지] {len(OUTFIT_FILES)}개")
    for p in OUTFIT_FILES:
        print(f"  - {p.name}")
    outfit_images = [Image.open(f) for f in OUTFIT_FILES if f.exists()]

    if not model_images:
        print("[ERROR] 모델 이미지가 없습니다!")
        return
    if not outfit_images:
        print("[ERROR] 착장 이미지가 없습니다!")
        return

    # 워크플로 실행
    wf = ImageGenerationWorkflow()

    # ═══════════════════════════════════════════════════════════════
    # 백스테이지 셀피 - MLB 셀피 스타일
    # ═══════════════════════════════════════════════════════════════
    user_input = """MLB 셀피 백스테이지 거울 셀카

    [레퍼런스 무드]
    - 콘서트 백스테이지 대기실
    - 전신 거울 앞에서 셀카
    - 화장대 조명 + 형광등
    - 무심하고 쿨한 표정
    - SNS에 올릴 것 같은 리얼한 셀피
    - 스마트폰 화질
    """

    # 3장 생성 (다양성 확인)
    TEST_COUNT = 3
    all_images = []
    all_details = []

    for i in range(TEST_COUNT):
        print(f"\n{'='*80}")
        print(f"🎬 연출 #{i+1}/{TEST_COUNT} 생성 중...")
        print(f"{'='*80}")

        result = wf.generate_with_details(
            user_input=user_input,
            model_images=model_images,
            outfit_images=outfit_images,
            input_vars={"gender": "여성", "age": "20대 초반"},
            count=1,
            variation_index=i  # 각각 다른 포즈/앵글
        )

        if result.get("status") == "success" and result.get("images"):
            all_images.append(result["images"][0])
            all_details.append(result.get("details", {}))

            # 상세 정보 출력
            skills = result.get("details", {}).get("skills", {})
            print(f"\n  [스킬 호출 결과]")
            print(f"  ├─ 브랜드: {skills.get('1_brand_routing', {}).get('brand', 'N/A')}")
            print(f"  ├─ 스타일: {skills.get('1_brand_routing', {}).get('style', 'N/A')}")
            print(f"  ├─ 착장 분석: {len(skills.get('4_outfit_analysis', {}).get('garments', []))}개 아이템")

            dv = skills.get('5_director_vision', {})
            print(f"  ├─ 강제 포즈: {dv.get('forced_pose', 'N/A')}")
            print(f"  ├─ 강제 표정: {dv.get('forced_expression', 'N/A')[:30] if dv.get('forced_expression') else 'N/A'}...")
            print(f"  └─ 강제 앵글: {dv.get('forced_angle', 'N/A')}")

            print(f"✅ 연출 #{i+1} 완료")
        else:
            print(f"❌ 연출 #{i+1} 실패: {result.get('error', 'unknown')}")

    print(f"\n{'='*80}")
    print(f"📊 총 {len(all_images)}/{TEST_COUNT}개 생성 완료")
    print(f"{'='*80}")

    if all_images:
        # 이미지 각각 저장
        saved_paths = []
        for i, img in enumerate(all_images):
            output_path = OUTPUT_DIR / f"mlb_mirror_selfie_{timestamp}_{i+1:02d}.png"
            img.save(output_path)
            saved_paths.append(output_path)
            print(f"[저장] {output_path.name}")

        print(f"\n✅ 총 {len(saved_paths)}개 이미지 저장 완료")

        # 상세 로그 저장
        log_path = LOG_DIR / f"mlb_mirror_selfie_{timestamp}.md"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"# MLB 거울 셀카 완성 - {TEST_COUNT}컷\n\n")
            f.write(f"**생성 시간**: {timestamp}\n\n")
            f.write(f"**총 생성**: {len(all_images)}개\n\n")
            f.write(f"## 입력\n")
            f.write(f"- 모델 이미지: {', '.join([p.name for p in MODEL_FILES])}\n")
            f.write(f"- 착장 이미지: {len(OUTFIT_FILES)}개\n")
            f.write(f"- 배경: 백스테이지 대기실 거울\n\n")

            f.write(f"## 다양성 검증\n\n")
            f.write(f"| # | 포즈 | 표정 | 앵글 |\n")
            f.write(f"|---|------|------|------|\n")
            for i, detail in enumerate(all_details):
                dv = detail.get('skills', {}).get('5_director_vision', {})
                pose = (dv.get('forced_pose', 'N/A') or 'N/A')[:25]
                expr = (dv.get('forced_expression', 'N/A') or 'N/A')[:20]
                angle = (dv.get('forced_angle', 'N/A') or 'N/A')[:20]
                f.write(f"| {i+1} | {pose} | {expr} | {angle} |\n")

            f.write(f"\n## 생성된 이미지\n\n")
            for i, path in enumerate(saved_paths):
                f.write(f"{i+1}. `{path.name}`\n")

        print(f"[로그 저장] {log_path}")
    else:
        print(f"\n[실패] 이미지 생성 실패")

if __name__ == "__main__":
    main()
