#!/usr/bin/env python3
"""
VLM 검수 프롬프트 검증 훅

VLM 검수 프롬프트 작성 시 step-by-step 비교 형식을 강제한다.
"""

import sys
import json


def validate_vlm_prompt():
    """
    Edit/Write 시 VLM 검수 프롬프트가 올바른 형식인지 검증

    검증 대상:
    - VALIDATION_PROMPT 문자열
    - 비교 항목 (pose_quality, lighting_mood, face_identity 등)

    필수 패턴:
    - [STEP 1], [STEP 2], [STEP 3] 형식
    - "REF:~, GEN:~" 형식 예시
    - 감점 계산 공식
    """
    try:
        # stdin에서 변경 내용 읽기
        input_data = sys.stdin.read()

        if not input_data.strip():
            return True

        data = json.loads(input_data)

        # 파일 경로 확인
        file_path = data.get("tool_input", {}).get("file_path", "")
        content = data.get("tool_input", {}).get("content", "")
        old_string = data.get("tool_input", {}).get("old_string", "")
        new_string = data.get("tool_input", {}).get("new_string", "")

        # validator 파일만 검사
        if "validator" not in file_path.lower():
            return True

        # 검사할 내용
        check_content = content or new_string
        if not check_content:
            return True

        # VLM 프롬프트 패턴 검사
        issues = []

        # 비교 항목이 있는지 확인
        comparison_keywords = [
            "pose_quality",
            "lighting_mood",
            "face_identity",
            "레퍼런스 비교",
            "REFERENCE",
            "비교하세요",
        ]

        has_comparison = any(kw in check_content for kw in comparison_keywords)

        if has_comparison:
            # step-by-step 형식 확인
            if "[STEP" not in check_content and "STEP 1" not in check_content:
                issues.append(
                    "비교 항목에 step-by-step 형식 없음 (STEP 1, STEP 2, STEP 3 권장)"
                )

            # 출력 형식 예시 확인
            if "REF:" not in check_content and "GEN:" not in check_content:
                issues.append("비교 출력 형식 예시 없음 (REF:~, GEN:~ 형식 권장)")

            # 감점 계산 확인
            if "감점" not in check_content and "점수" not in check_content:
                issues.append("감점/점수 계산 공식 없음")

        if issues:
            print(f"[VLM Prompt Warning] {file_path}", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            print("  참고: CLAUDE.md > VLM 검수 프롬프트 작성 원칙", file=sys.stderr)

        # 경고만 출력, 차단하지 않음
        return True

    except json.JSONDecodeError:
        return True
    except Exception as e:
        print(f"[VLM Prompt Hook Error] {e}", file=sys.stderr)
        return True


if __name__ == "__main__":
    validate_vlm_prompt()
