# -*- coding: utf-8 -*-
"""
Shoe Rack Mockup - 신발장 목업 워크플로
========================================

스케치업 신발장 렌더링에 실제 신발을 실사처럼 합성하는 워크플로.

Usage:
    from core.shoe_rack_mockup import generate_mockup

    result = generate_mockup(
        rack_image=rack_img,
        shoe_images=shoe_imgs,
        output_dir=output_path,
    )
"""

from pathlib import Path
from typing import List, Optional, Dict, Union
from dataclasses import dataclass

from PIL import Image

# 모듈 import
from .slot_config import (
    SlotColor,
    DetectedSlot,
    DEFAULT_SLOT_COLORS,
    get_slot_color,
    get_colors_by_stage,
)

from .slot_detector import (
    detect_slots_from_image,
    slots_to_json,
    save_slots_json,
    visualize_slots,
    get_slots_by_stage,
)

from .compositor import (
    CompositeResult,
    PipelineResult,
    composite_single_stage,
    composite_with_retry,
    run_pipeline,
    save_pipeline_results,
    # v2.0 단일 패스
    composite_single_pass,
    run_single_pass_pipeline,
    # v3.0 슬롯별 파이프라인 (정면뷰 전용)
    composite_single_slot,
    run_slot_by_slot_pipeline,
    blend_slot_edges,
)

from .validator import (
    ValidationResult,
    StageValidationResult,
    validate_stage,
    validate_color_coverage,
    validate_background_preservation,
    validate_final_result,
    format_validation_result,
)

from .templates import (
    get_stage_prompt,
    get_prompt_with_context,
    get_verification_prompt,
    get_retry_prompt,
    build_dynamic_prompt,
    build_single_pass_prompt,
    # v3.0 슬롯별 프롬프트
    build_slot_inpaint_prompt,
)

from .silhouette_analyzer import (
    SilhouetteAnalysis,
    analyze_silhouette,
    get_arrangement_prompt_section,
)

from .mirror_processor import (
    process_mirror_reflection,
    process_mirror_with_mask,
    detect_mirror_side,
    apply_mirror_effect_to_image8,
)


@dataclass
class MockupResult:
    """신발장 목업 최종 결과"""

    final_image: Optional[Image.Image]
    success: bool
    pipeline_result: PipelineResult
    validation_result: Optional[ValidationResult]
    slots_detected: Dict[str, List[DetectedSlot]]
    output_files: List[Path]


def generate_mockup(
    rack_image: Union[Image.Image, Path, str],
    shoe_images: Union[List[Image.Image], List[Path], Path, str],
    output_dir: Optional[Union[Path, str]] = None,
    stages: List[int] = None,
    max_retries: int = 2,
    validate: bool = True,
    save_intermediates: bool = True,
    api_key: Optional[str] = None,
) -> MockupResult:
    """
    신발장 목업 생성 메인 함수

    Args:
        rack_image: 신발장 이미지 (PIL Image, Path, 또는 경로 문자열)
        shoe_images: 신발 이미지 목록 (PIL Image 리스트, Path 리스트, 또는 폴더 경로)
        output_dir: 출력 폴더 (None이면 저장 안함)
        stages: 실행할 스테이지 (기본: [1, 2, 3])
        max_retries: 스테이지별 최대 재시도 횟수
        validate: 검증 실행 여부
        save_intermediates: 중간 결과 저장 여부
        api_key: Gemini API 키

    Returns:
        MockupResult
    """
    # 1. 입력 처리
    rack_img = _load_image(rack_image)
    shoe_imgs = _load_shoe_images(shoe_images)

    if stages is None:
        stages = [1, 2, 3]

    print("=" * 60)
    print("SHOE RACK MOCKUP WORKFLOW")
    print("=" * 60)
    print(f"Rack image size: {rack_img.size}")
    print(f"Shoe images: {len(shoe_imgs)}")
    print(f"Stages: {stages}")

    # 2. 슬롯 감지
    print("\n[STEP 1] Detecting slots...")
    slots_by_color = detect_slots_from_image(rack_img)

    total_slots = sum(len(slots) for slots in slots_by_color.values())
    print(f"  Detected {total_slots} slots:")
    for color, slots in slots_by_color.items():
        print(f"    - {color}: {len(slots)}")

    # 3. 파이프라인 실행
    print("\n[STEP 2] Running composite pipeline...")
    pipeline_result = run_pipeline(
        input_image=rack_img,
        shoe_images=shoe_imgs,
        stages=stages,
        max_retries_per_stage=max_retries,
        api_key=api_key,
    )

    # 4. 검증
    validation_result = None
    if validate and pipeline_result.success and pipeline_result.final_image:
        print("\n[STEP 3] Validating result...")
        validation_result = validate_final_result(
            original_image=rack_img,
            result_image=pipeline_result.final_image,
            stages_completed=pipeline_result.stages_completed,
            api_key=api_key,
        )
        print(format_validation_result(validation_result))

    # 5. 저장
    output_files = []
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 슬롯 JSON 저장
        slots_json_path = output_path / "slots.json"
        save_slots_json(slots_by_color, slots_json_path)
        output_files.append(slots_json_path)

        # 슬롯 시각화 저장
        if save_intermediates:
            vis_path = output_path / "slots_visualized.png"
            visualize_slots(rack_img, slots_by_color, vis_path)
            output_files.append(vis_path)

        # 파이프라인 결과 저장
        saved = save_pipeline_results(
            result=pipeline_result,
            output_dir=output_path,
            original_image=rack_img,
        )
        output_files.extend(saved)

    # 6. 결과 반환
    return MockupResult(
        final_image=pipeline_result.final_image,
        success=pipeline_result.success,
        pipeline_result=pipeline_result,
        validation_result=validation_result,
        slots_detected=slots_by_color,
        output_files=output_files,
    )


def _load_image(source: Union[Image.Image, Path, str]) -> Image.Image:
    """이미지 로드"""
    if isinstance(source, Image.Image):
        return source.convert("RGB")
    return Image.open(Path(source)).convert("RGB")


def _load_shoe_images(
    source: Union[List[Image.Image], List[Path], Path, str],
) -> List[Image.Image]:
    """신발 이미지 목록 로드"""
    if isinstance(source, list):
        if not source:
            return []
        if isinstance(source[0], Image.Image):
            return [img.convert("RGB") for img in source]
        return [Image.open(p).convert("RGB") for p in source]

    # 폴더 경로인 경우
    folder = Path(source)
    if folder.is_dir():
        # detail 이미지 우선, 없으면 모든 jpg/png
        files = sorted(folder.glob("*detail*.jpg"))
        if not files:
            files = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        return [Image.open(f).convert("RGB") for f in files[:12]]

    return []


# Public API
__all__ = [
    # 메인 함수
    "generate_mockup",
    "MockupResult",
    # 슬롯 설정
    "SlotColor",
    "DetectedSlot",
    "DEFAULT_SLOT_COLORS",
    "get_slot_color",
    "get_colors_by_stage",
    # 슬롯 감지
    "detect_slots_from_image",
    "slots_to_json",
    "save_slots_json",
    "visualize_slots",
    "get_slots_by_stage",
    # 합성
    "CompositeResult",
    "PipelineResult",
    "composite_single_stage",
    "composite_with_retry",
    "run_pipeline",
    "save_pipeline_results",
    # v2.0 단일 패스
    "composite_single_pass",
    "run_single_pass_pipeline",
    # v3.0 슬롯별 파이프라인
    "composite_single_slot",
    "run_slot_by_slot_pipeline",
    "blend_slot_edges",
    # 검증
    "ValidationResult",
    "StageValidationResult",
    "validate_stage",
    "validate_color_coverage",
    "validate_background_preservation",
    "validate_final_result",
    "format_validation_result",
    # 템플릿
    "get_stage_prompt",
    "get_prompt_with_context",
    "get_verification_prompt",
    "get_retry_prompt",
    "build_dynamic_prompt",
    "build_single_pass_prompt",
    "build_slot_inpaint_prompt",
    # 실루엣 분석 (v0.7)
    "SilhouetteAnalysis",
    "analyze_silhouette",
    "get_arrangement_prompt_section",
    # 거울 처리 (v1.0)
    "process_mirror_reflection",
    "process_mirror_with_mask",
    "detect_mirror_side",
    "apply_mirror_effect_to_image8",
]
