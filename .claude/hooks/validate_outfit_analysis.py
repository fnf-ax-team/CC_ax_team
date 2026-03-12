#!/usr/bin/env python3
"""
착장 분석 누락 방지 훅

브랜드컷 관련 코드 작성 시 착장 분석(analyze_outfit) 호출 여부를 검증한다.
"""

import sys
import json


def validate_outfit_analysis():
    """
    브랜드컷 워크플로 코드에서 착장 분석 호출 여부 검증

    검증 대상:
    - brandcut 관련 파일 (테스트, 파이프라인 등)
    - generate_brandcut 호출이 있는 파일

    필수 패턴:
    - analyze_outfit() 호출
    - outfit_analysis 변수 사용
    """
    try:
        input_data = sys.stdin.read()

        if not input_data.strip():
            return True

        data = json.loads(input_data)

        file_path = data.get("tool_input", {}).get("file_path", "").lower()
        content = data.get("tool_input", {}).get("content", "")
        new_string = data.get("tool_input", {}).get("new_string", "")

        # 브랜드컷 관련 파일만 검사
        brandcut_keywords = ["brandcut", "brand_cut", "brand-cut"]
        is_brandcut_file = any(kw in file_path for kw in brandcut_keywords)

        # 테스트/파이프라인 파일도 검사
        is_test_file = "test" in file_path or "pipeline" in file_path

        if not (is_brandcut_file or is_test_file):
            return True

        # 검사할 내용
        check_content = content or new_string
        if not check_content:
            return True

        # generate_brandcut 호출이 있는지 확인
        has_generate = (
            "generate_brandcut" in check_content
            or "generate_with_validation" in check_content
        )

        if not has_generate:
            return True

        # 착장 분석 호출 여부 확인
        issues = []

        outfit_patterns = [
            "analyze_outfit",
            "outfit_analysis",
            "OutfitAnalysis",
        ]

        has_outfit_analysis = any(
            pattern in check_content for pattern in outfit_patterns
        )

        if not has_outfit_analysis:
            issues.append("착장 분석(analyze_outfit) 호출 누락!")
            issues.append("  -> from core.brandcut import analyze_outfit")
            issues.append("  -> outfit_result = analyze_outfit(client, outfit_images)")

        # 착장 이미지 전송 확인
        if "outfit_images" not in check_content and "outfit_imgs" not in check_content:
            issues.append("착장 이미지(outfit_images) 파라미터 누락 가능성")

        if issues:
            print(f"\n[Outfit Analysis Warning] {file_path}", file=sys.stderr)
            print("=" * 50, file=sys.stderr)
            for issue in issues:
                print(f"  {issue}", file=sys.stderr)
            print("=" * 50, file=sys.stderr)
            print("  참고: SKILL.md > 모듈 인터페이스 > 1. 착장 분석", file=sys.stderr)
            print(
                "  착장 분석 없이 생성하면 착장 정확도가 크게 떨어집니다!",
                file=sys.stderr,
            )
            print()

        # 경고만 출력, 차단하지 않음
        return True

    except json.JSONDecodeError:
        return True
    except Exception as e:
        print(f"[Outfit Analysis Hook Error] {e}", file=sys.stderr)
        return True


if __name__ == "__main__":
    validate_outfit_analysis()
