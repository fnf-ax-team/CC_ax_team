#!/usr/bin/env python3
"""
PreToolUse Hook: 민감 파일 보호
.env, .git/, credentials 등 민감 파일 수정 차단

exit code:
  0 = 허용
  2 = 차단 (Claude에게 피드백 전달)
"""
import json
import sys
import os

# 보호 대상 패턴
PROTECTED_PATTERNS = [
    '.env',           # API 키
    '.env.local',
    '.env.production',
    'credentials',
    'secrets',
    '.git/',          # Git 내부
    'package-lock.json',
    'poetry.lock',
    'Pipfile.lock',
]

# 경고만 (차단 안함)
WARN_PATTERNS = [
    'core/config.py',  # 모델 설정 - 주의 필요
]

def main():
    try:
        input_data = json.load(sys.stdin)
        tool_input = input_data.get('tool_input', {})
        file_path = tool_input.get('file_path', '')

        if not file_path:
            sys.exit(0)

        # 경로 정규화
        normalized = file_path.replace('\\', '/').lower()

        # 보호 파일 체크
        for pattern in PROTECTED_PATTERNS:
            if pattern.lower() in normalized:
                print(json.dumps({
                    "decision": "block",
                    "reason": f"[BLOCKED] '{pattern}' 파일은 보호 대상입니다. 수동으로 수정하세요."
                }))
                sys.exit(2)

        # 경고 파일 체크
        for pattern in WARN_PATTERNS:
            if pattern.lower() in normalized:
                print(f"[WARNING] '{pattern}' 수정 시 주의하세요. 모델 설정이 변경될 수 있습니다.", file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # 훅 에러 시 허용 (작업 중단 방지)
        sys.exit(0)

if __name__ == '__main__':
    main()
