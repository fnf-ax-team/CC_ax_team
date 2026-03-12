#!/usr/bin/env python3
"""
PostToolUse Hook: Python 파일 자동 포매팅 (ruff)
Write/Edit 후 .py 파일이면 ruff format 실행
"""
import json
import sys
import subprocess
import os

def main():
    try:
        input_data = json.load(sys.stdin)
        file_path = input_data.get('tool_input', {}).get('file_path', '')

        if not file_path.endswith('.py'):
            sys.exit(0)

        if not os.path.exists(file_path):
            sys.exit(0)

        # ruff format 실행
        result = subprocess.run(
            ['ruff', 'format', file_path],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # 조용히 성공
            pass
        else:
            # ruff 미설치 또는 에러 - 무시
            pass

    except Exception:
        # 훅 실패해도 작업 중단 안함
        pass

    sys.exit(0)

if __name__ == '__main__':
    main()
