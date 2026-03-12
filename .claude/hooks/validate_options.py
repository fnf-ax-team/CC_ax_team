#!/usr/bin/env python3
"""
PostToolUse Hook: 옵션 하드코딩 감지

Write/Edit 후 .py 파일에서 옵션 하드코딩 여부 체크

감지 패턴:
  - 비율 하드코딩: aspect_ratio = "3:4"
  - 해상도 하드코딩: image_size = "2K"
  - 비용 하드코딩: cost = 190

올바른 패턴:
  - from core.options import ASPECT_RATIOS, RESOLUTIONS, COST_TABLE
"""

import json
import sys
import os
import re

# 허용 경로 (이 경로의 파일은 하드코딩 허용)
ALLOWED_PATHS = [
    "core/options.py",  # Single Source of Truth
    "core/config.py",  # 설정 파일
    ".claude/",  # Claude 설정
    "tests/",  # 테스트 코드
]

# 감지 패턴 (core/options.py에서 정의한 것과 동일)
HARDCODED_PATTERNS = {
    "aspect_ratio": [
        r'aspect_ratio\s*=\s*["\'][\d:]+["\']',  # aspect_ratio = "3:4"
    ],
    "resolution": [
        r'image_size\s*=\s*["\'][124]K["\']',  # image_size = "2K"
        r'resolution\s*=\s*["\'][124]K["\']',  # resolution = "2K"
    ],
}

# 허용 패턴 (core/options.py에서 import하면 OK)
ALLOWED_IMPORT_PATTERNS = [
    r"from\s+core\.options\s+import",
    r"from\s+core\s+import\s+options",
    r"import\s+core\.options",
]


def is_allowed_path(file_path):
    """허용된 경로인지 확인"""
    normalized = file_path.replace("\\", "/")
    for allowed in ALLOWED_PATHS:
        if allowed in normalized:
            return True
    return False


def has_proper_import(content):
    """core.options import가 있는지 확인"""
    for pattern in ALLOWED_IMPORT_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def check_file_for_hardcoded_options(file_path):
    """파일에서 하드코딩된 옵션 감지"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    # core.options import가 있으면 체크 안함
    if has_proper_import(content):
        return []

    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # 주석 제외
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for option_type, patterns in HARDCODED_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line):
                    violations.append(
                        {"line": i, "type": option_type, "content": stripped[:80]}
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

        # 허용된 경로면 스킵
        if is_allowed_path(file_path):
            sys.exit(0)

        violations = check_file_for_hardcoded_options(file_path)

        if violations:
            print("\n" + "=" * 60, file=sys.stderr)
            print("[OPTIONS WARNING] 옵션 하드코딩 감지!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(f"파일: {file_path}", file=sys.stderr)
            print("-" * 60, file=sys.stderr)

            for v in violations:
                print(f"  Line {v['line']}: {v['type']} 하드코딩", file=sys.stderr)
                print(f"    > {v['content']}", file=sys.stderr)

            print("-" * 60, file=sys.stderr)
            print("올바른 사용:", file=sys.stderr)
            print("  from core.options import (", file=sys.stderr)
            print("      ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,", file=sys.stderr)
            print("      DEFAULT_ASPECT_RATIO, DEFAULT_RESOLUTION,", file=sys.stderr)
            print("      get_cost, validate_aspect_ratio", file=sys.stderr)
            print("  )", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)

            # 피드백으로 Claude에게 전달
            feedback = {
                "feedback": f"[OPTIONS WARNING] {file_path}에서 옵션 하드코딩 발견. "
                f"core/options.py에서 import해서 사용하세요. "
                f"위반 항목: {', '.join(v['type'] for v in violations)}"
            }
            print(json.dumps(feedback))

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
