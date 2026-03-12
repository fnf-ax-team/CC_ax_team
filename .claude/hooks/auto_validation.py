#!/usr/bin/env python3
"""
자동 검증 Hook (PostToolUse)

이미지 생성 완료 후 자동으로 워크플로별 검증을 수행한다.
검증 실패 시 재생성을 제안한다.

Hook 타입: PostToolUse
트리거: 이미지 생성 함수 호출 완료 시

주의: 이 Hook은 Claude Code의 PostToolUse 이벤트에 연결되어야 한다.
실제 활성화는 settings.json에서 설정.
"""

import sys
import json
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def detect_workflow_from_context(tool_name: str, tool_input: dict) -> str:
    """도구 호출 컨텍스트에서 워크플로 타입 감지

    Args:
        tool_name: 호출된 도구 이름
        tool_input: 도구 입력 파라미터

    Returns:
        워크플로 타입 문자열 (감지 실패 시 None)
    """
    # 도구 이름 기반 감지
    tool_lower = tool_name.lower()

    if "brandcut" in tool_lower:
        return "brandcut"
    elif "background" in tool_lower or "bg_swap" in tool_lower:
        return "background_swap"
    elif "ugc" in tool_lower or "selfie" in tool_lower or "influencer" in tool_lower:
        return "ugc"

    # 입력 파라미터 기반 감지
    if tool_input:
        input_str = json.dumps(tool_input).lower()
        if "brandcut" in input_str:
            return "brandcut"
        elif "background" in input_str:
            return "background_swap"
        elif "ugc" in input_str or "selfie" in input_str:
            return "ugc"

    return None


def validate_generated_image(
    workflow_type: str,
    image_path: str,
    reference_images: dict,
) -> dict:
    """생성된 이미지 검증

    Args:
        workflow_type: 워크플로 타입
        image_path: 생성된 이미지 경로
        reference_images: 참조 이미지 딕셔너리

    Returns:
        검증 결과 딕셔너리
    """
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    from google import genai
    from core.api import _get_next_api_key
    from core.validators import ValidatorRegistry, WorkflowType

    # 워크플로 타입 변환
    wf_map = {
        "brandcut": WorkflowType.BRANDCUT,
        "background_swap": WorkflowType.BACKGROUND_SWAP,
        "ugc": WorkflowType.UGC,
        "selfie": WorkflowType.SELFIE,
    }
    wf_type = wf_map.get(workflow_type.lower())
    if not wf_type:
        return {"error": f"Unknown workflow type: {workflow_type}"}

    # 검증기 초기화
    api_key = _get_next_api_key()
    client = genai.Client(api_key=api_key)
    validator = ValidatorRegistry.get(wf_type, client)

    # 검증 실행
    try:
        result = validator.validate(
            generated_img=image_path,
            reference_images=reference_images,
        )
        return {
            "passed": result.passed,
            "score": result.total_score,
            "grade": result.grade,
            "tier": result.tier.value,
            "issues": result.issues[:5],
            "criteria": result.criteria_scores,
            "summary_kr": result.summary_kr,
        }
    except Exception as e:
        return {"error": str(e)}


def format_validation_report(result: dict) -> str:
    """검증 결과를 사람이 읽기 쉬운 형식으로 포맷

    Args:
        result: 검증 결과 딕셔너리

    Returns:
        포맷된 문자열
    """
    if "error" in result:
        return f"[VALIDATION ERROR] {result['error']}"

    status = "[PASS]" if result["passed"] else "[FAIL]"
    score = result["score"]
    grade = result["grade"]

    lines = [
        f"{status} Score: {score}/100 | Grade: {grade}",
    ]

    if result.get("issues"):
        lines.append("Issues:")
        for issue in result["issues"][:3]:
            lines.append(f"  - {issue}")

    if result.get("summary_kr"):
        lines.append(f"Summary: {result['summary_kr']}")

    return "\n".join(lines)


def main():
    """Hook 메인 함수 - PostToolUse 이벤트 처리

    stdin에서 JSON 형식의 이벤트 데이터를 읽어 처리.
    stdout으로 결과를 출력.
    """
    # stdin에서 이벤트 데이터 읽기
    event_data = sys.stdin.read()
    if not event_data:
        return

    try:
        event = json.loads(event_data)
    except json.JSONDecodeError:
        print("[AUTO_VALIDATION] Invalid event data", file=sys.stderr)
        return

    # 이벤트 정보 추출
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    tool_result = event.get("tool_result", {})

    # 이미지 생성 관련 도구인지 확인
    image_gen_keywords = [
        "generate", "create", "brandcut", "swap", "ugc", "selfie",
    ]
    is_image_gen = any(kw in tool_name.lower() for kw in image_gen_keywords)

    if not is_image_gen:
        return

    # 워크플로 감지
    workflow_type = detect_workflow_from_context(tool_name, tool_input)
    if not workflow_type:
        print(f"[AUTO_VALIDATION] Could not detect workflow type for {tool_name}", file=sys.stderr)
        return

    # 생성된 이미지 경로 추출
    image_path = tool_result.get("image_path") or tool_result.get("output_path")
    if not image_path:
        return

    # 참조 이미지 추출
    reference_images = tool_input.get("reference_images", {})
    if not reference_images:
        # 개별 키에서 추출 시도
        reference_images = {}
        if tool_input.get("face_images"):
            reference_images["face"] = tool_input["face_images"]
        if tool_input.get("outfit_images"):
            reference_images["outfit"] = tool_input["outfit_images"]
        if tool_input.get("original_image"):
            reference_images["original"] = [tool_input["original_image"]]

    if not reference_images:
        print("[AUTO_VALIDATION] No reference images found, skipping validation", file=sys.stderr)
        return

    # 검증 실행
    print(f"[AUTO_VALIDATION] Validating {workflow_type} image: {image_path}")
    result = validate_generated_image(workflow_type, image_path, reference_images)

    # 결과 출력
    report = format_validation_report(result)
    print(report)

    # 재생성 제안
    if not result.get("passed", True) and not result.get("error"):
        print("\n[SUGGESTION] Consider regenerating with enhanced prompt.")
        if result.get("issues"):
            print(f"Focus on: {', '.join(result['issues'][:3])}")


if __name__ == "__main__":
    main()
