"""
재시도 생성기 - 생성 → 검증 → 프롬프트 강화 → 재생성

역할:
- generator.py의 generate_brandcut() 호출
- mlb_validator.py의 validate() 호출
- 검증 실패 시 실패 원인별 프롬프트 강화
- 재생성 루프 관리
"""

import time
from typing import Optional, List, Union
from pathlib import Path

from PIL import Image
from google import genai

from .generator import generate_brandcut
from .mlb_validator import (
    MLBValidator,
    ENHANCEMENT_RULES,
    CRITERION_NAMES_KR,
    format_validation_result,
)


def generate_with_validation(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    api_key: str,
    max_retries: int = 2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    initial_temperature: float = 0.35,  # 수정: 1.0 -> 0.35 (품질 향상)
    pose_reference: Optional[Image.Image] = None,
    style_reference: Optional[Image.Image] = None,
    mood_reference: Optional[Image.Image] = None,
    check_ai_artifacts: bool = False,
    check_gate: bool = True,
) -> dict:
    """
    단일 이미지 생성 + 검증 + 재생성 루프

    흐름:
    1. generator.generate_brandcut() 호출 → 이미지 1장 생성
    2. mlb_validator.validate() 호출 → 검증
    3. 실패 시 → 실패 원인별 프롬프트 강화 → 1번으로

    Note:
        배치 생성은 generator.py의 generate_brandcut(num_images=N) 사용.
        이 함수는 1장씩 검증+재시도만 담당.

    Args:
        prompt_json: 프롬프트 JSON 객체
        face_images: 얼굴 이미지 목록 (검증용으로도 사용)
        outfit_images: 착장 이미지 목록 (검증용으로도 사용)
        api_key: Gemini API 키
        max_retries: 최대 재시도 횟수 (기본 2)
        aspect_ratio: 화면 비율
        resolution: 해상도
        initial_temperature: 초기 온도 (기본 0.25)
        pose_reference: 포즈 레퍼런스 이미지 (선택)
        style_reference: 스타일 레퍼런스 이미지 (선택) - 무드/조명/분위기 복사
        mood_reference: 무드 레퍼런스 이미지 (선택)
        check_ai_artifacts: AI 티 검사 수행 여부
        check_gate: 합성티 게이트 체크 수행 여부

    Returns:
        dict: {
            "image": PIL.Image,       # 생성된 이미지 (최고 점수)
            "score": float,           # 총점 (0-100)
            "passed": bool,           # 통과 여부
            "criteria": dict,         # 12개 기준 점수
            "attempts": int,          # 시도 횟수
            "history": List[dict]     # 시도 이력
        }
    """
    # Validator 초기화
    client = genai.Client(api_key=api_key)
    validator = MLBValidator(client)

    best_image = None
    best_score = -1  # -1로 초기화하여 점수 0인 이미지도 저장
    best_result = None
    history = []

    current_prompt = prompt_json.copy()
    current_temp = initial_temperature

    for attempt in range(max_retries + 1):
        print(f"\n{'#' * 60}")
        print(
            f"# ATTEMPT {attempt + 1}/{max_retries + 1} | Temperature: {current_temp:.2f}"
        )
        print(f"{'#' * 60}")

        # =============================================
        # 1. 이미지 생성 (generator.py 호출)
        # =============================================
        image = generate_brandcut(
            prompt_json=current_prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            style_reference=style_reference,
            api_key=api_key,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=current_temp,
        )

        if image is None:
            print(f"[RetryGen] X Generation failed (attempt {attempt + 1})")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": "Generation failed",
                }
            )
            continue

        # =============================================
        # 2. 검증 (mlb_validator.py 호출)
        # =============================================
        try:
            validation_result = validator.validate(
                generated_img=image,
                face_images=face_images,
                outfit_images=outfit_images,
                pose_reference=pose_reference,
                mood_reference=mood_reference,
                check_ai_artifacts=check_ai_artifacts,
                check_gate=check_gate,
            )
        except Exception as e:
            print(f"[RetryGen] X Validation failed: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": f"Validation error: {e}",
                }
            )
            continue

        # 결과 출력 (표 형식)
        print_validation_result_table(validation_result, attempt=attempt + 1)

        # 이력 기록
        history.append(
            {
                "attempt": attempt + 1,
                "temperature": current_temp,
                "total_score": validation_result.total_score,
                "grade": validation_result.grade,
                "passed": validation_result.passed,
                "auto_fail": validation_result.auto_fail,
                "auto_fail_reasons": validation_result.auto_fail_reasons,
                "issues": validation_result.issues[:5],
            }
        )

        # 3. 최고 점수 추적
        if validation_result.total_score > best_score:
            best_image = image
            best_score = validation_result.total_score
            best_result = validation_result
            print(f"[RetryGen] * New best score: {best_score}")

        # 4. 통과 조건 체크
        if validation_result.passed:
            print(f"[RetryGen] PASSED at attempt {attempt + 1}!")
            break

        # =============================================
        # 5. 실패 원인별 프롬프트 강화
        # =============================================
        if attempt < max_retries:
            current_prompt, current_temp = _enhance_prompt_for_retry(
                original_prompt=prompt_json,
                validation_result=validation_result,
                current_temp=current_temp,
                attempt=attempt,
            )

        # Rate limit 방지 대기
        if attempt < max_retries:
            time.sleep(2)

    # 최종 결과 반환
    return _build_result(best_image, best_result, history, max_retries)


def _enhance_prompt_for_retry(
    original_prompt: dict,
    validation_result,
    current_temp: float,
    attempt: int,
) -> tuple:
    """
    검증 실패 원인별 프롬프트 강화

    개선 (v2):
    - VLM이 반환한 구체적 사유(reasons)를 프롬프트에 직접 포함
    - 일반 규칙(ENHANCEMENT_RULES) + 구체적 사유 조합

    Args:
        original_prompt: 원본 프롬프트
        validation_result: 검증 결과
        current_temp: 현재 온도
        attempt: 현재 시도 횟수

    Returns:
        tuple: (강화된 프롬프트, 조정된 온도)
    """
    print(f"[RetryGen] Analyzing failures... (issues: {len(validation_result.issues)})")

    # 실패 기준 분석
    failed_criteria = _get_failed_criteria(validation_result)

    if not failed_criteria:
        return original_prompt.copy(), max(0.15, current_temp - 0.03)

    # VLM이 반환한 구체적 사유 추출
    reasons = getattr(validation_result, "reasons", {}) or {}

    # 구체적 실패 사유 블록 생성 (VLM 반환값 기반)
    specific_issues = []
    for criterion in failed_criteria:
        reason = reasons.get(criterion, "")
        if reason:
            specific_issues.append(f"[{criterion}] {reason}")

    # 일반 강화 규칙 텍스트 생성
    general_rules = []

    # 우선순위 순서대로 강화 규칙 추가
    priority_order = [
        "outfit_accuracy",  # 1순위 - 착장
        "face_identity",  # 2순위 - 얼굴
        "expression",
        "anatomy",
        "brand_compliance",
        "lighting_mood",
        "micro_detail",
        "environmental_integration",
        "body_type",
        "photorealism",
        "composition",
        "pose_quality",
    ]

    for criterion in priority_order:
        if criterion in failed_criteria and criterion in ENHANCEMENT_RULES:
            general_rules.extend(
                ENHANCEMENT_RULES[criterion][:2]
            )  # 각 기준당 상위 2개 규칙만
            print(f"[RetryGen]   -> Enhancing: {criterion}")

    # 구체적 사유 블록 (VLM 피드백 기반)
    specific_block = ""
    if specific_issues:
        specific_block = "## SPECIFIC ISSUES FROM PREVIOUS ATTEMPT:\n"
        specific_block += "\n".join([f"- {issue}" for issue in specific_issues[:8]])
        specific_block += "\n\n** FIX THE ABOVE ISSUES EXACTLY **\n"

    # 일반 규칙 블록 (최대 8개 항목)
    general_block = "\n".join([f"- {line}" for line in general_rules[:8]])

    enhancement_text = f"""
=== RETRY ENHANCEMENT (Attempt #{attempt + 2}) ===
Previous score: {validation_result.total_score}/100 | Grade: {validation_result.grade}
Failed on: {', '.join(failed_criteria[:6])}

{specific_block}
## GENERAL RULES TO FOLLOW:
{general_block}
================================================
"""

    # 프롬프트 JSON에 강화 텍스트 추가
    enhanced_prompt = original_prompt.copy()
    if isinstance(enhanced_prompt, dict):
        enhanced_prompt["_RETRY_NOTES"] = enhancement_text

    print(f"[RetryGen] Added enhancement for {len(failed_criteria)} criteria")
    if specific_issues:
        print(f"[RetryGen]   -> Specific issues: {len(specific_issues)}")

    # 온도 낮추기 (디테일 향상)
    new_temp = max(0.15, current_temp - 0.03)

    return enhanced_prompt, new_temp


def _get_failed_criteria(validation_result) -> List[str]:
    """검증 결과에서 실패한 기준 추출"""
    failed_criteria = []

    thresholds = {
        "outfit_accuracy": 80,  # 착장 - 1순위
        "face_identity": 90,  # 얼굴 - 2순위 (mlb_validator.py와 통일)
        "expression": 75,
        "anatomy": 80,
        "brand_compliance": 75,
        "lighting_mood": 75,
        "micro_detail": 75,
        "environmental_integration": 75,
        "body_type": 85,
        "photorealism": 85,
        "composition": 80,
        "pose_quality": 75,
    }

    for criterion, threshold in thresholds.items():
        score = getattr(validation_result, criterion, 100)
        if score < threshold:
            failed_criteria.append(criterion)

    return failed_criteria


def print_validation_result_table(result, attempt: int = 1) -> str:
    """
    검수 결과를 CLAUDE.md 형식의 표로 출력

    [CHANGED] mlb_validator.format_validation_result()에 위임

    Args:
        result: ValidationResult 또는 dict 객체
        attempt: 시도 횟수 (기본 1)

    Returns:
        str: 표 형식 문자열 (출력용)
    """
    if hasattr(result, "total_score"):
        # ValidationResult 객체 - canonical 함수 사용
        output = format_validation_result(result, filename=f"시도 {attempt}")
    else:
        # dict 객체 - 레거시 호환
        output = _format_dict_result(result, attempt)

    print(output)
    return output


def _format_dict_result(result: dict, attempt: int) -> str:
    """레거시 dict 결과 포맷 (호환성 유지용)"""
    criteria = result.get("criteria", {})
    total_score = result.get("score", 0)
    grade = result.get("grade", "F")
    passed = result.get("passed", False)

    lines = [f"\n## 검수 결과 (시도 {attempt})\n"]
    lines.append("| 항목 | 점수 | 통과 |")
    lines.append("|------|------|------|")

    for key, score in criteria.items():
        korean_name = CRITERION_NAMES_KR.get(key, key)
        check_mark = "O" if score >= 75 else "X"
        lines.append(f"| {korean_name} | {score} | {check_mark} |")

    lines.append(f"\n**총점**: {total_score}/100 | **등급**: {grade}")

    return "\n".join(lines)


def _build_result(best_image, best_result, history, max_retries) -> dict:
    """최종 결과 딕셔너리 생성"""
    if best_image is None or best_result is None:
        print(f"\n[RetryGen] X All attempts failed")
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "attempts": max_retries + 1,
            "history": history,
        }

    print(
        f"\n[RetryGen] Best result: {best_result.total_score}/100 (Grade: {best_result.grade})"
    )

    return {
        "image": best_image,
        "score": best_result.total_score,
        "passed": best_result.passed,
        "criteria": {
            # A. 기본품질
            "photorealism": best_result.photorealism,
            "anatomy": best_result.anatomy,
            "micro_detail": best_result.micro_detail,
            # B. 인물보존
            "face_identity": best_result.face_identity,
            "expression": best_result.expression,
            "body_type": best_result.body_type,
            # C. 착장
            "outfit_accuracy": best_result.outfit_accuracy,
            # D. 브랜드
            "brand_compliance": best_result.brand_compliance,
            "environmental_integration": best_result.environmental_integration,
            "lighting_mood": best_result.lighting_mood,
            # E. 구도
            "composition": best_result.composition,
            "pose_quality": best_result.pose_quality,
        },
        "attempts": len(history),
        "history": history,
        "validation_result": best_result,
    }
