"""
재시도 생성기 v2 - 실패 항목별 타겟 강화

변경점 (v1 대비):
1. 실패 항목별로 해당 프롬프트만 강화 (착장 틀리면 착장만)
2. prompt_builder_v2의 enhance_prompt_for_retry() 사용
3. validator_v2의 14개 기준 사용
"""

import time
from typing import Optional, List, Union, TYPE_CHECKING
from pathlib import Path

from PIL import Image
from google import genai

from .generator_v2 import generate_brandcut
from .validator_v2 import (
    BrandcutValidator,
    ValidationResult,
    CRITERION_NAMES_KR,
    THRESHOLDS,
    ENHANCEMENT_RULES,
)
from .prompt_builder_v2 import enhance_prompt_for_retry

if TYPE_CHECKING:
    from core.outfit_analyzer import OutfitAnalysis


def generate_with_validation(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    api_key: str,
    max_retries: int = 2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    initial_temperature: float = 0.30,
    pose_reference: Optional[Image.Image] = None,
    expression_reference: Optional[Image.Image] = None,
    background_reference: Optional[Image.Image] = None,
    outfit_spec: Optional["OutfitAnalysis"] = None,
) -> dict:
    """
    단일 이미지 생성 + 검증 + 재생성 루프 (v2)

    변경점:
    - 실패 항목별 타겟 강화
    - 14개 기준 검증

    Args:
        prompt_json: 프롬프트 JSON (korean_prompt 포함)
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록
        api_key: Gemini API 키
        max_retries: 최대 재시도 횟수 (기본 2)
        aspect_ratio: 화면 비율
        resolution: 해상도
        initial_temperature: 초기 온도
        pose_reference: 포즈 레퍼런스 (선택)
        expression_reference: 표정 레퍼런스 (선택)
        outfit_spec: OutfitAnalysis 객체 (선택)

    Returns:
        dict: {
            "image": PIL.Image,
            "score": float,
            "passed": bool,
            "criteria": dict,
            "attempts": int,
            "history": List[dict]
        }
    """
    # Validator 초기화
    client = genai.Client(api_key=api_key)
    validator = BrandcutValidator(client)

    best_image = None
    best_score = -1
    best_result = None
    history = []

    current_prompt = prompt_json.copy()
    current_temp = initial_temperature

    for attempt in range(max_retries + 1):
        print(f"\n{'=' * 60}")
        print(
            f"  시도 {attempt + 1}/{max_retries + 1} | Temperature: {current_temp:.2f}"
        )
        print(f"{'=' * 60}")

        # =============================================
        # 1. 이미지 생성
        # =============================================
        image = generate_brandcut(
            prompt_json=current_prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            expression_reference=expression_reference,
            background_reference=background_reference,
            api_key=api_key,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=current_temp,
        )

        if image is None:
            print(f"[RetryGen] X 생성 실패 (시도 {attempt + 1})")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": "Generation failed",
                }
            )
            continue

        # =============================================
        # 2. 검증 (14개 기준)
        # =============================================
        try:
            validation_result = validator.validate(
                generated_img=image,
                face_images=face_images,
                outfit_images=outfit_images,
                pose_reference=pose_reference,
                outfit_spec=outfit_spec,
            )
        except Exception as e:
            print(f"[RetryGen] X 검증 실패: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": f"Validation error: {e}",
                }
            )
            continue

        # 결과 출력
        print(validation_result.format_korean())

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
            }
        )

        # 3. 최고 점수 추적
        if validation_result.total_score > best_score:
            best_image = image
            best_score = validation_result.total_score
            best_result = validation_result
            print(f"[RetryGen] * 최고 점수 갱신: {best_score}")

        # 4. 통과 조건 체크
        if validation_result.passed:
            print(f"[RetryGen] O 통과! (시도 {attempt + 1})")
            break

        # =============================================
        # 5. 실패 항목별 타겟 강화 (NEW!)
        # =============================================
        if attempt < max_retries:
            current_prompt, current_temp = _enhance_for_retry(
                original_prompt=prompt_json,
                validation_result=validation_result,
                current_temp=current_temp,
            )

        # Rate limit 방지
        if attempt < max_retries:
            time.sleep(2)

    # 최종 결과 반환
    return _build_result(best_image, best_result, history, max_retries)


def _enhance_for_retry(
    original_prompt: dict,
    validation_result: ValidationResult,
    current_temp: float,
) -> tuple:
    """
    실패 항목별 타겟 프롬프트 강화

    핵심: 착장 틀리면 착장만, 얼굴 틀리면 얼굴만 강화!
    """
    # 실패 기준 분석
    failed_criteria = _get_failed_criteria(validation_result)

    if not failed_criteria:
        return original_prompt.copy(), max(0.15, current_temp - 0.02)

    print(f"\n[RetryGen] 실패 항목: {', '.join(failed_criteria)}")

    # reasons dict 추출
    reasons = validation_result.reasons or {}

    # prompt_builder_v2의 타겟 강화 함수 사용
    enhanced_prompt = enhance_prompt_for_retry(
        original_prompt=original_prompt,
        failed_criteria=failed_criteria,
        reasons=reasons,
    )

    # 실패 항목별 로그
    for criterion in failed_criteria:
        score = getattr(validation_result, criterion, 0)
        reason = reasons.get(criterion, "")
        print(f"  - {CRITERION_NAMES_KR.get(criterion, criterion)}: {score}점")
        if reason:
            print(f"    사유: {reason[:50]}...")

    # 온도 조정 (더 보수적으로)
    new_temp = max(0.15, current_temp - 0.02)

    return enhanced_prompt, new_temp


def _get_failed_criteria(validation_result: ValidationResult) -> List[str]:
    """검증 결과에서 실패한 기준 추출"""
    failed = []

    for key, threshold in THRESHOLDS.items():
        score = getattr(validation_result, key, 100)
        if score < threshold:
            failed.append(key)

    # 우선순위 정렬 (중요한 것 먼저)
    priority_order = [
        "outfit_accuracy",
        "face_identity",
        "aesthetic_appeal",
        "brand_vibe",
        "anatomy",
        "lighting_mood",
        "pose_quality",
        "brand_compliance",
        "expression",
        "body_type",
        "photorealism",
        "micro_detail",
        "composition",
        "environmental_integration",
    ]

    return sorted(
        failed, key=lambda x: priority_order.index(x) if x in priority_order else 99
    )


def _build_result(best_image, best_result, history, max_retries) -> dict:
    """최종 결과 딕셔너리 생성"""
    if best_image is None or best_result is None:
        print(f"\n[RetryGen] X 모든 시도 실패")
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "attempts": max_retries + 1,
            "history": history,
        }

    print(
        f"\n[RetryGen] 최종 결과: {best_result.total_score}/100 (등급: {best_result.grade})"
    )

    return {
        "image": best_image,
        "score": best_result.total_score,
        "passed": best_result.passed,
        "criteria": {
            "photorealism": best_result.photorealism,
            "anatomy": best_result.anatomy,
            "micro_detail": best_result.micro_detail,
            "aesthetic_appeal": best_result.aesthetic_appeal,  # NEW
            "face_identity": best_result.face_identity,
            "expression": best_result.expression,
            "body_type": best_result.body_type,
            "outfit_accuracy": best_result.outfit_accuracy,
            "brand_compliance": best_result.brand_compliance,
            "brand_vibe": best_result.brand_vibe,  # NEW
            "environmental_integration": best_result.environmental_integration,
            "lighting_mood": best_result.lighting_mood,
            "composition": best_result.composition,
            "pose_quality": best_result.pose_quality,
        },
        "attempts": len(history),
        "history": history,
        "validation_result": best_result,
        "outfit_missing_items": best_result.outfit_missing_items,
        "outfit_mismatched_attributes": best_result.outfit_mismatched_attributes,
    }


__all__ = ["generate_with_validation"]
