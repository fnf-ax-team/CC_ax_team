"""
워크플로 통합 생성 + 검증 함수

워크플로 타입에 따라 적절한 검증기를 자동 선택하고,
검증 실패 시 워크플로별 우선순위에 따라 프롬프트를 강화하여 재생성.

사용법:
    from core.generators import generate_with_workflow_validation
    from core.validators import WorkflowType

    result = generate_with_workflow_validation(
        workflow_type=WorkflowType.BRANDCUT,
        generate_func=my_generate_func,
        prompt=prompt_json,
        reference_images={"face": [...], "outfit": [...]},
        config={"temperature": 0.25},
        max_retries=2,
    )
"""

from typing import Callable, Dict, List, Optional, Union
from pathlib import Path
from PIL import Image

from google import genai

from core.validators.base import WorkflowType, CommonValidationResult, QualityTier
from core.validators.registry import ValidatorRegistry
from core.api import _get_next_api_key


def generate_with_workflow_validation(
    workflow_type: WorkflowType,
    generate_func: Callable,
    prompt: Union[str, dict],
    reference_images: Dict[str, List[Union[str, Path, Image.Image]]],
    config: dict,
    max_retries: int = 2,
    check_ai_artifacts: bool = False,
    check_gate: bool = True,
    api_key: Optional[str] = None,
) -> dict:
    """
    워크플로 통합 생성 + 검증 함수

    워크플로 타입에 따라 적절한 검증기를 자동 선택하고,
    검증 실패 시 워크플로별 우선순위에 따라 프롬프트를 강화하여 재생성.

    Args:
        workflow_type: 워크플로 타입 (BRANDCUT, BACKGROUND_SWAP, UGC 등)
        generate_func: 이미지 생성 함수
            - 시그니처: (prompt, reference_images, config) -> Image.Image
        prompt: 생성 프롬프트 (문자열 또는 JSON dict)
        reference_images: 참조 이미지 딕셔너리
            - brandcut: {"face": [...], "outfit": [...], "style": [...]}
            - background_swap: {"original": [...]}
            - ugc: {"face": [...], "outfit": [...]}
        config: 생성 설정 (temperature, aspect_ratio 등)
        max_retries: 최대 재시도 횟수 (기본 2)
        check_ai_artifacts: AI 티 검사 수행 여부 (기본 False)
        check_gate: 합성티 게이트 체크 수행 여부 (기본 True)
        api_key: API 키 (미지정 시 자동 로테이션)

    Returns:
        dict:
            - "image": PIL.Image - 최고 점수 이미지
            - "score": int - 총점 (0-100)
            - "passed": bool - 통과 여부
            - "criteria": dict - 워크플로별 세부 점수
            - "attempts": int - 시도 횟수
            - "history": List[dict] - 시도 이력
            - "validation_result": CommonValidationResult - 전체 검증 결과
    """
    # API 클라이언트 초기화
    key = api_key or _get_next_api_key()
    client = genai.Client(api_key=key)

    # 워크플로에 맞는 검증기 가져오기
    validator = ValidatorRegistry.get(workflow_type, client)

    # 추적 변수
    best_image = None
    best_score = 0
    best_result = None
    history = []

    # 프롬프트 및 설정 복사 (원본 보존)
    current_prompt = prompt.copy() if isinstance(prompt, dict) else prompt
    current_config = config.copy()
    current_temp = current_config.get("temperature", 0.25)

    for attempt in range(max_retries + 1):
        # 1. 이미지 생성
        current_config["temperature"] = current_temp
        try:
            image = generate_func(current_prompt, reference_images, current_config)
        except Exception as e:
            history.append({
                "attempt": attempt + 1,
                "temperature": current_temp,
                "error": str(e),
            })
            continue

        if image is None:
            history.append({
                "attempt": attempt + 1,
                "temperature": current_temp,
                "error": "Generation returned None",
            })
            continue

        # 2. 워크플로별 검증
        try:
            result = validator.validate(
                generated_img=image,
                reference_images=reference_images,
                check_ai_artifacts=check_ai_artifacts,
                check_gate=check_gate,
            )
        except Exception as e:
            history.append({
                "attempt": attempt + 1,
                "temperature": current_temp,
                "error": f"Validation error: {str(e)}",
            })
            continue

        # 이력 기록
        history.append({
            "attempt": attempt + 1,
            "temperature": current_temp,
            "total_score": result.total_score,
            "grade": result.grade,
            "passed": result.passed,
            "auto_fail": result.auto_fail,
            "auto_fail_reasons": result.auto_fail_reasons[:3] if result.auto_fail_reasons else [],
            "issues": result.issues[:5] if result.issues else [],
        })

        # 3. 최고 점수 추적
        if result.total_score > best_score:
            best_image = image
            best_score = result.total_score
            best_result = result

        # 4. 통과 시 종료
        if result.passed:
            break

        # 5. 재시도 준비 - 워크플로별 우선순위에 따른 프롬프트 강화
        if attempt < max_retries and validator.should_retry(result):
            failed_criteria = validator._extract_failed_criteria(result)
            enhancement = validator.get_enhancement_rules(failed_criteria)

            if enhancement:
                current_prompt = _append_enhancement(
                    prompt=current_prompt,
                    enhancement=enhancement,
                    attempt=attempt,
                    prev_score=result.total_score,
                    prev_grade=result.grade,
                    failed_criteria=failed_criteria,
                )

            # 온도 감소 (디테일 향상)
            current_temp = max(0.15, current_temp - 0.03)

    return {
        "image": best_image,
        "score": best_score,
        "passed": best_result.passed if best_result else False,
        "criteria": best_result.criteria_scores if best_result else {},
        "attempts": len(history),
        "history": history,
        "validation_result": best_result,
    }


def _append_enhancement(
    prompt: Union[str, dict],
    enhancement: str,
    attempt: int,
    prev_score: int,
    prev_grade: str,
    failed_criteria: List[str],
) -> Union[str, dict]:
    """프롬프트에 강화 규칙 추가

    Args:
        prompt: 원본 프롬프트
        enhancement: 강화 규칙 텍스트
        attempt: 현재 시도 번호 (0-indexed)
        prev_score: 이전 점수
        prev_grade: 이전 등급
        failed_criteria: 실패한 기준 목록

    Returns:
        강화된 프롬프트
    """
    header = f"""
=== RETRY ENHANCEMENT (Attempt #{attempt + 2}) ===
Previous score: {prev_score}/100 | Grade: {prev_grade}
Failed on: {', '.join(failed_criteria[:5])}

MUST FIX:
"""
    footer = "\n================================================"

    if isinstance(prompt, dict):
        # JSON 프롬프트의 경우 _RETRY_NOTES 키에 추가
        prompt_copy = prompt.copy()
        prompt_copy["_RETRY_NOTES"] = header + enhancement + footer
        return prompt_copy
    else:
        # 텍스트 프롬프트의 경우 끝에 추가
        return prompt + header + enhancement + footer
