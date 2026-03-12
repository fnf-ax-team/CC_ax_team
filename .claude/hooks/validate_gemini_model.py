#!/usr/bin/env python3
"""
PostToolUse Hook: Gemini 모델 사용 검증
Write/Edit 후 .py 파일에서 금지된 모델 사용 및 하드코딩 여부 체크

허용 모델:
  - gemini-3-pro-image-preview (이미지 생성)
  - gemini-3-flash-preview (VLM 분석)

금지 모델:
  - gemini-2.x 시리즈
  - gemini-1.x 시리즈
  - 기타 구버전

금지 패턴:
  - model="gemini-..." 형태의 하드코딩
  - generate_content(model="...") 형태
"""

import json
import sys
import os

# core/policy.py에서 import (Single Source of Truth)
# 훅 실행 시 프로젝트 루트를 path에 추가
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

try:
    from core.policy import (
        FORBIDDEN_MODELS,
        ALLOWED_MODELS,
        check_forbidden_models_in_content,
        check_model_hardcode,
    )

    POLICY_LOADED = True
except ImportError:
    # core/policy.py가 없는 경우 폴백 (하위 호환성)
    POLICY_LOADED = False
    FORBIDDEN_MODELS = {
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0",
    }
    ALLOWED_MODELS = {
        "gemini-3-pro-image-preview",
        "gemini-3-flash-preview",
    }

# 허용 경로 (이 경로는 검사 스킵)
SKIP_PATHS = [
    "core/policy.py",  # 정책 정의 파일 자체
    "core/config.py",  # 설정 파일
    ".claude/hooks/",  # 훅 파일들
    "__pycache__",
]


def should_skip_file(file_path):
    """검사 스킵할 파일인지 확인"""
    normalized = file_path.replace("\\", "/")
    for skip in SKIP_PATHS:
        if skip in normalized:
            return True
    return False


def check_file_for_violations(file_path):
    """파일에서 모델 관련 위반 사항 체크"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return [], []

    if POLICY_LOADED:
        # core/policy.py의 함수 사용
        forbidden_violations = check_forbidden_models_in_content(content)
        hardcode_violations = check_model_hardcode(content)
    else:
        # 폴백: 기본 체크
        forbidden_violations = []
        hardcode_violations = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#"):
                continue

            for model in FORBIDDEN_MODELS:
                if model in line:
                    forbidden_violations.append(
                        {"line": i, "model": model, "content": line.strip()[:80]}
                    )

    return forbidden_violations, hardcode_violations


def main():
    try:
        input_data = json.load(sys.stdin)
        file_path = input_data.get("tool_input", {}).get("file_path", "")

        if not file_path.endswith(".py"):
            sys.exit(0)

        if not os.path.exists(file_path):
            sys.exit(0)

        if should_skip_file(file_path):
            sys.exit(0)

        forbidden_violations, hardcode_violations = check_file_for_violations(file_path)

        has_violations = forbidden_violations or hardcode_violations

        if has_violations:
            print("\n" + "=" * 60, file=sys.stderr)
            print("[GEMINI MODEL WARNING] 모델 정책 위반 감지!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(f"파일: {file_path}", file=sys.stderr)

            if forbidden_violations:
                print("-" * 60, file=sys.stderr)
                print("[금지된 모델 사용]", file=sys.stderr)
                for v in forbidden_violations:
                    print(f"  Line {v['line']}: {v['model']}", file=sys.stderr)
                    print(f"    > {v['content']}", file=sys.stderr)

            if hardcode_violations:
                print("-" * 60, file=sys.stderr)
                print("[모델 하드코딩]", file=sys.stderr)
                for v in hardcode_violations:
                    print(f"  Line {v['line']}: 하드코딩 감지", file=sys.stderr)
                    print(f"    > {v['match']}", file=sys.stderr)

            print("-" * 60, file=sys.stderr)
            print("올바른 사용:", file=sys.stderr)
            print(
                "  from core.config import IMAGE_MODEL, VISION_MODEL", file=sys.stderr
            )
            print("", file=sys.stderr)
            print("허용된 모델:", file=sys.stderr)
            for m in sorted(ALLOWED_MODELS):
                print(f"  - {m}", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)

            # 피드백으로 Claude에게 전달
            feedback_parts = []
            if forbidden_violations:
                models = set(v["model"] for v in forbidden_violations)
                feedback_parts.append(f"금지된 모델 사용: {', '.join(models)}")
            if hardcode_violations:
                feedback_parts.append("모델 문자열 하드코딩 발견")

            feedback = {
                "feedback": f"[MODEL VIOLATION] {file_path}에서 모델 정책 위반. "
                f"{'; '.join(feedback_parts)}. "
                f"core/config.py의 IMAGE_MODEL, VISION_MODEL을 import해서 사용하세요."
            }
            print(json.dumps(feedback))

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
