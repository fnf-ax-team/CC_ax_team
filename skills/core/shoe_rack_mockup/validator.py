# -*- coding: utf-8 -*-
"""
Validator - 신발장 목업 검증기
==============================
생성된 이미지의 품질 검증
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import numpy as np
from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL
from core.api import _get_next_api_key as get_next_api_key

from .templates import get_verification_prompt
from .slot_config import DEFAULT_SLOT_COLORS, COLOR_TOLERANCE


@dataclass
class ValidationResult:
    """검증 결과"""

    passed: bool
    total_score: int
    grade: str
    scores: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageValidationResult:
    """스테이지별 검증 결과"""

    stage: int
    color_remaining_percent: float
    scores: Dict[str, int]
    issues: List[str]
    passed: bool


def validate_stage(
    image: Image.Image,
    stage: int,
    api_key: Optional[str] = None,
) -> StageValidationResult:
    """
    스테이지 완료 검증 (VLM 사용)

    Args:
        image: 검증할 이미지
        stage: 검증할 스테이지 (1, 2, 3)
        api_key: API 키

    Returns:
        StageValidationResult
    """
    if api_key is None:
        api_key = get_next_api_key()

    client = genai.Client(api_key=api_key)

    prompt = get_verification_prompt(stage)

    print(f"[VALIDATE] Stage {stage} verification...")

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_modalities=["TEXT"],
            ),
        )

        # JSON 파싱 시도
        text = response.text
        # JSON 블록 추출
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            result_data = json.loads(text.strip())
        except json.JSONDecodeError:
            # 파싱 실패 시 기본값
            result_data = {
                "color_remaining_percent": 50,
                "scores": {
                    "slot_coverage": 50,
                    "shoe_count_accuracy": 50,
                    "realism": 50,
                    "background_preservation": 50,
                },
                "issues": ["Could not parse VLM response"],
                "passed": False,
            }

        return StageValidationResult(
            stage=stage,
            color_remaining_percent=result_data.get("color_remaining_percent", 0),
            scores=result_data.get("scores", {}),
            issues=result_data.get("issues", []),
            passed=result_data.get("passed", False),
        )

    except Exception as e:
        print(f"[VALIDATE] Error: {e}")
        return StageValidationResult(
            stage=stage,
            color_remaining_percent=100,
            scores={},
            issues=[str(e)],
            passed=False,
        )


def validate_color_coverage(
    original_image: Image.Image,
    result_image: Image.Image,
    target_color: str = "mint",
) -> float:
    """
    색상 커버리지 검증 (픽셀 기반)

    Args:
        original_image: 원본 이미지
        result_image: 결과 이미지
        target_color: 검증할 색상

    Returns:
        교체 비율 (0.0 ~ 1.0)
    """
    if target_color not in DEFAULT_SLOT_COLORS:
        raise ValueError(f"Unknown color: {target_color}")

    color_config = DEFAULT_SLOT_COLORS[target_color]
    target_rgb = color_config.rgb
    tolerance = COLOR_TOLERANCE

    # 원본에서 대상 색상 픽셀 수
    orig_array = np.array(original_image.convert("RGB"))
    lower = np.array([max(0, c - tolerance) for c in target_rgb])
    upper = np.array([min(255, c + tolerance) for c in target_rgb])

    orig_mask = np.all((orig_array >= lower) & (orig_array <= upper), axis=2)
    orig_count = np.sum(orig_mask)

    if orig_count == 0:
        return 1.0  # 원본에 해당 색상 없음

    # 결과에서 대상 색상 픽셀 수
    result_array = np.array(result_image.convert("RGB"))
    result_mask = np.all((result_array >= lower) & (result_array <= upper), axis=2)
    result_count = np.sum(result_mask)

    # 교체 비율 계산
    replaced_ratio = 1.0 - (result_count / orig_count)
    return max(0.0, min(1.0, replaced_ratio))


def validate_background_preservation(
    original_image: Image.Image,
    result_image: Image.Image,
    exclude_colors: List[str] = None,
) -> float:
    """
    배경 보존 검증

    Args:
        original_image: 원본 이미지
        result_image: 결과 이미지
        exclude_colors: 제외할 색상 (마스크 영역)

    Returns:
        보존 비율 (0.0 ~ 1.0)
    """
    if exclude_colors is None:
        exclude_colors = ["mint", "coral", "white"]

    orig_array = np.array(original_image.convert("RGB"))
    result_array = np.array(result_image.convert("RGB"))

    # 크기 불일치 체크
    if orig_array.shape != result_array.shape:
        print(f"[WARN] Size mismatch: {orig_array.shape} vs {result_array.shape}")
        return 0.5  # 크기 불일치는 중간 점수

    # 마스크 영역 제외
    exclude_mask = np.zeros(orig_array.shape[:2], dtype=bool)

    for color_name in exclude_colors:
        if color_name not in DEFAULT_SLOT_COLORS:
            continue
        color_config = DEFAULT_SLOT_COLORS[color_name]
        target_rgb = color_config.rgb
        tolerance = COLOR_TOLERANCE

        lower = np.array([max(0, c - tolerance) for c in target_rgb])
        upper = np.array([min(255, c + tolerance) for c in target_rgb])

        color_mask = np.all((orig_array >= lower) & (orig_array <= upper), axis=2)
        exclude_mask |= color_mask

    # 배경 픽셀만 비교
    background_mask = ~exclude_mask
    background_count = np.sum(background_mask)

    if background_count == 0:
        return 1.0

    # 픽셀 차이 계산
    diff = np.abs(orig_array.astype(float) - result_array.astype(float))
    diff_sum = np.sum(diff, axis=2)  # RGB 채널 합

    # 배경 영역의 평균 차이
    background_diff = diff_sum[background_mask]
    avg_diff = np.mean(background_diff) if len(background_diff) > 0 else 0

    # 점수 계산 (차이가 적을수록 높은 점수)
    # 0 차이 = 1.0, 255*3 차이 = 0.0
    preservation_score = 1.0 - (avg_diff / (255 * 3))
    return max(0.0, min(1.0, preservation_score))


def validate_final_result(
    original_image: Image.Image,
    result_image: Image.Image,
    stages_completed: List[int],
    api_key: Optional[str] = None,
) -> ValidationResult:
    """
    최종 결과 종합 검증

    Args:
        original_image: 원본 이미지
        result_image: 최종 이미지
        stages_completed: 완료된 스테이지 목록
        api_key: API 키

    Returns:
        ValidationResult
    """
    scores = {}
    issues = []
    details = {}

    # 1. 색상 커버리지 검증
    stage_colors = {1: "mint", 2: "coral", 3: "white"}
    total_coverage = 0

    for stage in stages_completed:
        color = stage_colors.get(stage)
        if color:
            coverage = validate_color_coverage(original_image, result_image, color)
            scores[f"{color}_coverage"] = int(coverage * 100)
            total_coverage += coverage

            if coverage < 1.0:
                issues.append(
                    f"{color} color not fully replaced ({int(coverage*100)}%)"
                )

    if stages_completed:
        scores["slot_coverage"] = int((total_coverage / len(stages_completed)) * 100)
    else:
        scores["slot_coverage"] = 0

    # 2. 배경 보존 검증
    bg_preservation = validate_background_preservation(original_image, result_image)
    scores["background_preservation"] = int(bg_preservation * 100)

    if bg_preservation < 0.95:
        issues.append(f"Background modified ({int(bg_preservation*100)}% preserved)")

    # 3. 종합 점수 계산
    weights = {
        "slot_coverage": 0.4,
        "background_preservation": 0.3,
    }

    total_score = 0
    total_weight = 0

    for key, weight in weights.items():
        if key in scores:
            total_score += scores[key] * weight
            total_weight += weight

    # 개별 색상 커버리지 점수도 반영
    for stage in stages_completed:
        color = stage_colors.get(stage)
        if color and f"{color}_coverage" in scores:
            total_score += scores[f"{color}_coverage"] * 0.1
            total_weight += 0.1

    if total_weight > 0:
        total_score = int(total_score / total_weight)
    else:
        total_score = 0

    # 4. 등급 판정
    if total_score >= 95:
        grade = "S"
    elif total_score >= 90:
        grade = "A"
    elif total_score >= 85:
        grade = "B"
    elif total_score >= 75:
        grade = "C"
    else:
        grade = "F"

    # 5. 통과 여부
    passed = (
        scores.get("slot_coverage", 0) >= 95
        and scores.get("background_preservation", 0) >= 90
        and grade in ["S", "A", "B"]
    )

    return ValidationResult(
        passed=passed,
        total_score=total_score,
        grade=grade,
        scores=scores,
        issues=issues,
        details=details,
    )


def format_validation_result(result: ValidationResult) -> str:
    """검증 결과를 표 형식으로 포맷"""
    lines = [
        "## 검수 결과",
        "",
        "| 항목 | 점수 | 기준 | 통과 |",
        "|------|------|------|------|",
    ]

    criteria = {
        "slot_coverage": ("슬롯 커버리지", 95),
        "background_preservation": ("배경 보존", 90),
        "mint_coverage": ("민트 영역", 95),
        "coral_coverage": ("코랄 영역", 95),
        "white_coverage": ("흰색 영역", 95),
    }

    for key, (name, threshold) in criteria.items():
        if key in result.scores:
            score = result.scores[key]
            passed = "O" if score >= threshold else "X"
            lines.append(f"| {name} | {score} | >={threshold} | {passed} |")

    lines.append("")
    lines.append(
        f"**총점**: {result.total_score}/100 | **등급**: {result.grade} | **판정**: {'통과' if result.passed else '재검토 필요'}"
    )

    if result.issues:
        lines.append("")
        lines.append("### 이슈 사항")
        for issue in result.issues:
            lines.append(f"- {issue}")

    return "\n".join(lines)
