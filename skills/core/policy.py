"""
정책 상수 - Gemini 모델 및 API 사용 정책의 Single Source of Truth

모든 훅, 테스트, 검증에서 이 모듈의 상수를 import해서 사용한다.
금지 모델 추가 시 이 파일만 수정하면 전체 반영.

사용법:
    from core.policy import (
        FORBIDDEN_MODELS, ALLOWED_MODELS,
        MODEL_HARDCODE_PATTERNS, is_forbidden_model
    )
"""

from typing import List, Set
import re


# ============================================================
# 허용 모델 (이미지 생성 / VLM 분석용)
# ============================================================
ALLOWED_MODELS: Set[str] = {
    "gemini-3-pro-image-preview",  # 이미지 생성
    "gemini-3-flash-preview",  # VLM 분석
}

# 모델 역할별 매핑
IMAGE_MODEL = "gemini-3-pro-image-preview"
VISION_MODEL = "gemini-3-flash-preview"


# ============================================================
# 금지 모델 (절대 사용 금지)
# ============================================================
FORBIDDEN_MODELS: Set[str] = {
    # Gemini 2.x 시리즈 (구버전)
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    # Gemini 1.x 시리즈 (구버전)
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
    "gemini-1.0",
    # 기타 금지 패턴
    "gemini-pro",  # 구버전 이름
    "gemini-pro-vision",  # 구버전 이름
}

# 금지 모델 접두사 패턴 (gemini-2.*, gemini-1.* 등)
FORBIDDEN_MODEL_PREFIXES: List[str] = [
    "gemini-2.",
    "gemini-1.",
]


# ============================================================
# 모델 하드코딩 감지 패턴
# ============================================================
MODEL_HARDCODE_PATTERNS: List[str] = [
    # model="..." 형태의 하드코딩
    r'model\s*=\s*["\']gemini-[^"\']+["\']',
    # generate_content(model="...") 형태
    r'generate_content\s*\([^)]*model\s*=\s*["\']gemini-[^"\']+["\']',
    # Client(model="...") 형태
    r'Client\s*\([^)]*model\s*=\s*["\']gemini-[^"\']+["\']',
]

# 허용되는 import 패턴 (이 패턴이 있으면 하드코딩 검사 스킵)
ALLOWED_MODEL_IMPORT_PATTERNS: List[str] = [
    r"from\s+core\.config\s+import.*IMAGE_MODEL",
    r"from\s+core\.config\s+import.*VISION_MODEL",
    r"from\s+core\.policy\s+import",
    r"from\s+core\s+import\s+config",
    r"from\s+core\s+import\s+policy",
]


# ============================================================
# 헬퍼 함수
# ============================================================
def is_forbidden_model(model_name: str) -> bool:
    """모델이 금지 목록에 있는지 확인

    Args:
        model_name: 모델 이름 (e.g., "gemini-2.0-flash")

    Returns:
        금지 여부
    """
    # 정확히 일치
    if model_name in FORBIDDEN_MODELS:
        return True

    # 접두사 패턴 매칭
    for prefix in FORBIDDEN_MODEL_PREFIXES:
        if model_name.startswith(prefix):
            return True

    return False


def is_allowed_model(model_name: str) -> bool:
    """모델이 허용 목록에 있는지 확인

    Args:
        model_name: 모델 이름

    Returns:
        허용 여부
    """
    return model_name in ALLOWED_MODELS


def check_model_hardcode(content: str) -> List[dict]:
    """코드에서 모델 하드코딩 패턴 감지

    Args:
        content: 검사할 코드 내용

    Returns:
        감지된 위반 목록 [{"line": int, "pattern": str, "match": str}, ...]
    """
    # 허용된 import가 있으면 스킵
    for pattern in ALLOWED_MODEL_IMPORT_PATTERNS:
        if re.search(pattern, content):
            return []

    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # 주석 제외
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for pattern in MODEL_HARDCODE_PATTERNS:
            match = re.search(pattern, line)
            if match:
                violations.append(
                    {
                        "line": i,
                        "pattern": pattern,
                        "match": match.group()[:80],
                    }
                )

    return violations


def check_forbidden_models_in_content(content: str) -> List[dict]:
    """코드에서 금지된 모델 문자열 감지

    Args:
        content: 검사할 코드 내용

    Returns:
        감지된 위반 목록 [{"line": int, "model": str, "content": str}, ...]
    """
    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # 주석 제외
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # 금지 모델 직접 매칭
        for model in FORBIDDEN_MODELS:
            if model in line:
                violations.append(
                    {
                        "line": i,
                        "model": model,
                        "content": stripped[:80],
                    }
                )

        # 금지 접두사 패턴 매칭
        for prefix in FORBIDDEN_MODEL_PREFIXES:
            # "gemini-2.x-xxx" 형태 찾기
            pattern = rf'["\']({re.escape(prefix)}[a-zA-Z0-9\-_.]+)["\']'
            matches = re.findall(pattern, line)
            for match in matches:
                if match not in ALLOWED_MODELS:
                    violations.append(
                        {
                            "line": i,
                            "model": match,
                            "content": stripped[:80],
                        }
                    )

    return violations


# ============================================================
# 모듈 직접 실행 시 정책 요약 출력
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Gemini Model Policy")
    print("=" * 60)

    print("\n[ALLOWED MODELS]")
    for model in sorted(ALLOWED_MODELS):
        print(f"  + {model}")

    print("\n[FORBIDDEN MODELS]")
    for model in sorted(FORBIDDEN_MODELS):
        print(f"  - {model}")

    print("\n[FORBIDDEN PREFIXES]")
    for prefix in FORBIDDEN_MODEL_PREFIXES:
        print(f"  - {prefix}*")

    print("\n" + "=" * 60)
