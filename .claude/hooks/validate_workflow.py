#!/usr/bin/env python3
"""
PostToolUse Hook: 워크플로 검수 로직 감지

Write/Edit 후 .py 파일에서 검수 없이 저장하는 패턴 감지

금지 패턴:
  - generate_* 호출 후 바로 save_image() 호출
  - max_retries=0 또는 생략

필수 패턴:
  - generate_with_validation() 사용
  - 또는 generate_with_workflow_validation() 사용
"""

import json
import sys
import os
import re

# 검사 대상 파일 패턴
TARGET_PATH_PATTERNS = [
    r"core/.*\.py$",
    r".*workflow.*\.py$",
    r".*generator.*\.py$",
]

# 스킵할 경로
SKIP_PATHS = [
    "tests/",
    ".claude/",
    "__pycache__",
    "validator.py",  # 검증기 자체는 스킵
]

# 금지 패턴: generate_ 호출 후 검수 없이 저장
FORBIDDEN_PATTERNS = [
    # generate_ 결과를 바로 save
    r"(generate_\w+\([^)]*\))\s*\n\s*save_image\(",
    # max_retries=0
    r"max_retries\s*=\s*0",
]

# 안전 패턴: 이게 있으면 OK
SAFE_PATTERNS = [
    r"generate_with_validation",
    r"generate_with_workflow_validation",
    r"result\[.?passed.?\]",
    r"result\.passed",
    r"validator\.validate",
    r"ValidatorRegistry\.get",
]


def should_check_file(file_path):
    """검사 대상 파일인지 확인"""
    normalized = file_path.replace("\\", "/")

    # 스킵 경로 체크
    for skip in SKIP_PATHS:
        if skip in normalized:
            return False

    # 대상 패턴 체크
    for pattern in TARGET_PATH_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return False


def has_safe_pattern(content):
    """안전 패턴이 있는지 확인"""
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def check_file_for_validation_bypass(file_path):
    """파일에서 검수 우회 패턴 감지"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    # 안전 패턴이 있으면 OK
    if has_safe_pattern(content):
        return []

    violations = []

    # generate_ 함수 호출이 있는지 확인
    if not re.search(r"generate_\w+\(", content):
        return []

    # 금지 패턴 체크
    for pattern in FORBIDDEN_PATTERNS:
        matches = re.finditer(pattern, content)
        for match in matches:
            # 라인 번호 계산
            line_num = content[: match.start()].count("\n") + 1
            violations.append(
                {"line": line_num, "pattern": pattern, "match": match.group()[:60]}
            )

    return violations


def main():
    try:
        input_data = json.load(sys.stdin)
        file_path = input_data.get("tool_input", {}).get("file_path", "")

        if not file_path.endswith(".py"):
            sys.exit(0)

        if not os.path.exists(file_path):
            sys.exit(0)

        if not should_check_file(file_path):
            sys.exit(0)

        violations = check_file_for_validation_bypass(file_path)

        if violations:
            print("\n" + "=" * 60, file=sys.stderr)
            print("[VALIDATION WARNING] 검수 로직 누락 감지!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(f"파일: {file_path}", file=sys.stderr)
            print("-" * 60, file=sys.stderr)

            for v in violations:
                print(f"  Line {v['line']}: 검수 없이 저장 시도", file=sys.stderr)
                print(f"    > {v['match']}", file=sys.stderr)

            print("-" * 60, file=sys.stderr)
            print("필수 패턴:", file=sys.stderr)
            print("  result = generate_with_validation(", file=sys.stderr)
            print("      ...,", file=sys.stderr)
            print("      max_retries=2,  # 필수", file=sys.stderr)
            print("  )", file=sys.stderr)
            print("  if result['passed']:", file=sys.stderr)
            print("      save_image(result['image'])", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)

            # 피드백으로 Claude에게 전달
            feedback = {
                "feedback": f"[VALIDATION WARNING] {file_path}에서 검수 로직 누락 감지. "
                f"generate_with_validation() 또는 generate_with_workflow_validation()을 "
                f"사용하고 max_retries=2 이상으로 설정하세요."
            }
            print(json.dumps(feedback))

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
