"""Generation router for marketer test mode.

입력 이미지 경로는 프로젝트 루트 기준 상대 경로 (예: db/model/face.jpg).
FNF_STORAGE_MODE=s3 이면 S3에서 다운로드, FNF_OUTPUT_MODE=s3 이면 S3에 업로드.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import uuid

from core.config import IMAGE_MODEL, VISION_MODEL
from core.storage import resolve_path, is_s3_mode, is_output_s3

router = APIRouter(prefix="/generate", tags=["generation"])


# ============================================================
# Request/Response Schemas
# ============================================================


class StandardGenerationRequest(BaseModel):
    """Request schema for Standard Brandcut generation."""

    expression_id: str = Field(..., description="Expression layer ID")
    pose_id: str = Field(..., description="Pose layer ID")
    composition_id: str = Field(..., description="Composition layer ID")
    angle_id: str = Field(..., description="Angle layer ID")
    background_id: str = Field(..., description="Background layer ID")
    lighting_id: str = Field(..., description="Lighting layer ID")
    face_image_urls: List[str] = Field(
        ..., min_length=1, max_length=2, description="1-2 face images"
    )
    outfit_image_urls: Optional[List[str]] = Field(
        None, description="Optional outfit images"
    )
    aspect_ratio: Literal["3:4", "4:5", "9:16", "1:1"] = Field(
        "3:4", description="Image aspect ratio"
    )


class ReferenceGenerationRequest(BaseModel):
    """Request schema for Reference Brandcut generation."""

    reference_image_url: str = Field(..., description="Reference image URL (required)")
    face_image_urls: List[str] = Field(
        ..., min_length=1, max_length=2, description="1-2 face images"
    )
    outfit_image_urls: Optional[List[str]] = Field(
        None, description="Optional outfit images"
    )
    background_image_url: Optional[str] = Field(
        None, description="Optional background image (text extraction only)"
    )
    aspect_ratio: Literal["3:4", "4:5", "9:16", "1:1"] = Field(
        "3:4", description="Image aspect ratio"
    )
    count: Literal[1, 3, 5] = Field(1, description="Number of images to generate")


class GenerationResponse(BaseModel):
    """Response schema for image generation."""

    generation_id: str = Field(..., description="UUID for this generation session")
    image_urls: List[str] = Field(..., description="URLs of generated images")
    prompt_used: str = Field(..., description="Final prompt used for generation")
    mode: str = Field(..., description="Generation mode (standard or reference)")


class PromptPreviewResponse(BaseModel):
    """Response schema for prompt preview."""

    prompt: str = Field(..., description="Assembled prompt text")
    selections: dict = Field(..., description="Selected layer options")


class AnalysisRequest(BaseModel):
    """Request schema for VLM analysis."""

    image_url: str = Field(..., description="URL or path to image for analysis")


class ReferenceAnalysisResponse(BaseModel):
    """Response schema for reference image analysis."""

    style: str = Field(..., description="Overall style description")
    pose: str = Field(..., description="Pose description")
    composition: str = Field(..., description="Composition description")
    lighting: str = Field(..., description="Lighting description")
    background: str = Field(..., description="Background description")


class OutfitAnalysisResponse(BaseModel):
    """Response schema for outfit analysis."""

    outfit_description: str = Field(
        ..., description="Detailed outfit description for prompting"
    )
    style_keywords: List[str] = Field(
        default_factory=list, description="Style keywords"
    )


class BackgroundAnalysisResponse(BaseModel):
    """Response schema for background analysis."""

    background_description: str = Field(
        ..., description="Background description (people ignored)"
    )
    prompt_ready: str = Field(..., description="Prompt-ready background description")


# ============================================================
# Input Path Resolution (로컬/S3 자동 전환)
# ============================================================


def _resolve_input(relative_path: str):
    """입력 이미지 경로를 실제 파일 경로로 resolve.

    - 로컬 모드: 프로젝트 루트 기준 로컬 경로 반환
    - S3 모드: S3에서 다운로드 후 캐시 경로 반환

    Args:
        relative_path: 'db/model/face.jpg' 같은 상대 경로

    Returns:
        실제 파일에 접근 가능한 Path

    Raises:
        FileNotFoundError: 파일이 없으면 발생
    """
    return resolve_path(relative_path)


def _resolve_inputs(paths: list[str]) -> list:
    """여러 입력 경로를 한번에 resolve."""
    return [_resolve_input(p) for p in paths]


# ============================================================
# Generation Endpoints
# ============================================================


@router.post("/standard", response_model=GenerationResponse)
async def generate_standard(request: StandardGenerationRequest):
    """
    Generate image from 6-layer selection (Standard mode).

    This endpoint:
    1. Assembles prompt from hierarchical library
    2. Calls MLB generator with selected layers
    3. Returns generated image URLs

    Note: Implementation placeholder - connect to actual generation logic
    """
    generation_id = str(uuid.uuid4())

    # Assemble selections dictionary
    selections = {
        "expression": request.expression_id,
        "pose": request.pose_id,
        "composition": request.composition_id,
        "angle": request.angle_id,
        "background": request.background_id,
        "lighting": request.lighting_id,
    }

    # TODO: Implement actual prompt assembly
    # from core.prompt_combinator import combine_prompt
    # prompt = combine_prompt(selections)
    prompt = f"[Placeholder] Standard generation with {selections}"

    # TODO: Implement actual generation
    # from core.mlb_a2z_generator import MLBBrandcutGenerator
    # generator = MLBBrandcutGenerator()
    # result = await generator.generate(prompt, request.face_image_urls, request.outfit_image_urls)

    # Placeholder response
    return GenerationResponse(
        generation_id=generation_id,
        image_urls=[f"/api/v1/images/{generation_id}/outputs/result_001.png"],
        prompt_used=prompt,
        mode="standard",
    )


@router.post("/reference", response_model=GenerationResponse)
async def generate_reference(request: ReferenceGenerationRequest):
    """
    Generate image from reference image (Reference mode).

    This endpoint:
    1. Analyzes reference image with VLM
    2. Analyzes outfit if provided
    3. Analyzes background if provided (text only)
    4. Generates with face images

    Note: Implementation placeholder - connect to Reference Brandcut workflow
    """
    generation_id = str(uuid.uuid4())

    # TODO: Implement Reference Brandcut workflow
    # 1. Analyze reference image
    # ref_analysis = await analyze_reference(request.reference_image_url)

    # 2. Analyze outfit if provided
    # outfit_analysis = None
    # if request.outfit_image_urls:
    #     outfit_analysis = await analyze_outfit(request.outfit_image_urls[0])

    # 3. Analyze background if provided (text only)
    # bg_analysis = None
    # if request.background_image_url:
    #     bg_analysis = await analyze_background(request.background_image_url)

    # 4. Build prompt
    # from core.reference_brandcut import build_reference_prompt
    # prompt = build_reference_prompt(ref_analysis, outfit_analysis, bg_analysis)

    # 5. Generate with face images
    # result = await generator.generate_reference(
    #     prompt=prompt,
    #     reference_image=request.reference_image_url,
    #     face_images=request.face_image_urls,
    #     count=request.count
    # )

    prompt = "[Placeholder] Reference mode - VLM extracted prompt"

    return GenerationResponse(
        generation_id=generation_id,
        image_urls=[
            f"/api/v1/images/{generation_id}/outputs/result_{i:03d}.png"
            for i in range(1, request.count + 1)
        ],
        prompt_used=prompt,
        mode="reference",
    )


@router.post("/preview", response_model=PromptPreviewResponse)
async def preview_prompt(request: StandardGenerationRequest):
    """
    Preview assembled prompt without generating images.

    This endpoint:
    1. Assembles prompt from selections
    2. Returns prompt text for review
    3. Does NOT call generation API

    Useful for marketers to review prompt before generation.
    """
    selections = {
        "expression": request.expression_id,
        "pose": request.pose_id,
        "composition": request.composition_id,
        "angle": request.angle_id,
        "background": request.background_id,
        "lighting": request.lighting_id,
    }

    # TODO: Implement actual prompt assembly
    # from core.prompt_combinator import combine_prompt
    # prompt = combine_prompt(selections)
    prompt = f"[Placeholder] Assembled prompt for {selections}"

    return PromptPreviewResponse(prompt=prompt, selections=selections)


# ============================================================
# VLM Analysis Endpoints
# ============================================================


@router.post("/analyze/reference", response_model=ReferenceAnalysisResponse)
async def analyze_reference(request: AnalysisRequest):
    """
    Analyze reference image for style/pose/composition/lighting.

    Uses VLM (VISION_MODEL from config) to extract:
    - Overall style and mood
    - Pose details
    - Composition and framing
    - Lighting setup
    - Background setting

    Note: Implementation placeholder - connect to VLM analysis
    """
    # TODO: Implement VLM analysis using VISION_MODEL
    # from core.vlm_analysis import analyze_with_vlm
    # from .omc.reference-brandcut-vlm-prompts import REFERENCE_ANALYSIS_PROMPT
    # result = await analyze_with_vlm(request.image_url, REFERENCE_ANALYSIS_PROMPT)

    return ReferenceAnalysisResponse(
        style="[Placeholder] Minimal, cool-toned editorial style",
        pose="[Placeholder] Confident standing pose, slight hip shift",
        composition="[Placeholder] Full body, centered, eye-level angle",
        lighting="[Placeholder] Soft overcast natural light from front-left",
        background="[Placeholder] Urban concrete wall with geometric shadows",
    )


@router.post("/analyze/outfit", response_model=OutfitAnalysisResponse)
async def analyze_outfit(request: AnalysisRequest):
    """
    Analyze outfit images for detailed clothing description.

    Uses VLM to extract:
    - Headwear, outer, top, bottom, shoes
    - Colors, materials, details
    - Logo positions
    - Style keywords

    Note: Implementation placeholder - connect to VLM analysis
    """
    # TODO: Implement VLM analysis using VISION_MODEL
    # from core.vlm_analysis import analyze_with_vlm
    # from .omc.reference-brandcut-vlm-prompts import OUTFIT_ANALYSIS_PROMPT
    # result = await analyze_with_vlm(request.image_url, OUTFIT_ANALYSIS_PROMPT)

    return OutfitAnalysisResponse(
        outfit_description="[Placeholder] Burgundy wool beanie, oversized charcoal bomber jacket with front logo, black slim jeans, white leather sneakers",
        style_keywords=["streetwear", "minimal", "urban"],
    )


@router.post("/analyze/background", response_model=BackgroundAnalysisResponse)
async def analyze_background(request: AnalysisRequest):
    """
    Analyze background image (IGNORE people, extract environment only).

    CRITICAL: This analysis ignores all people in the image and
    extracts ONLY the background environment description.

    Uses VLM to extract:
    - Location type (parking lot, gallery, street, etc.)
    - Key elements (walls, floors, architectural features)
    - Color palette and atmosphere
    - Lighting conditions

    Result is TEXT ONLY - no image is passed to generation API.

    Note: Implementation placeholder - connect to VLM analysis
    """
    # TODO: Implement VLM analysis using VISION_MODEL
    # from core.vlm_analysis import analyze_with_vlm
    # from .omc.reference-brandcut-vlm-prompts import BACKGROUND_ANALYSIS_PROMPT
    # result = await analyze_with_vlm(request.image_url, BACKGROUND_ANALYSIS_PROMPT)

    return BackgroundAnalysisResponse(
        background_description="[Placeholder] Clean parking structure with exposed concrete pillars, industrial ceiling, cool gray tones",
        prompt_ready="clean parking garage, concrete pillars, industrial ceiling, cool gray tones, afternoon natural light",
    )


# ============================================================
# Configuration Info
# ============================================================


@router.get("/config")
async def get_generation_config():
    """
    Get current generation configuration.

    Returns model names and settings from core.config.
    Useful for debugging and verification.
    """
    return {
        "image_model": IMAGE_MODEL,
        "vision_model": VISION_MODEL,
        "supported_aspect_ratios": ["3:4", "4:5", "9:16", "1:1"],
        "supported_modes": ["standard", "reference"],
        "max_face_images": 2,
        "reference_count_options": [1, 3, 5],
    }


# ============================================================
# AI Influencer Generation
# ============================================================


class InfluencerGenerationRequest(BaseModel):
    """AI 인플루언서 생성 요청."""

    face_image_paths: List[str] = Field(
        ..., min_length=1, max_length=3, description="얼굴 이미지 경로 (1-3장)"
    )
    outfit_image_paths: List[str] = Field(
        ..., min_length=1, description="착장 이미지 경로 (1장 이상)"
    )
    pose_image_path: str = Field(..., description="포즈 레퍼런스 이미지 경로")
    expression_image_path: str = Field(..., description="표정 레퍼런스 이미지 경로")
    background_image_path: str = Field(..., description="배경 레퍼런스 이미지 경로")
    aspect_ratio: str = Field("9:16", description="비율")
    resolution: str = Field("2K", description="해상도")
    title: Optional[str] = Field(None, description="갤러리 표시용 제목")
    auto_showcase: bool = Field(True, description="자동으로 갤러리에 등록")


class InfluencerGenerationResponse(BaseModel):
    """AI 인플루언서 생성 응답."""

    generation_id: str
    image_url: Optional[str] = None
    showcase_id: Optional[str] = None
    validation: Optional[dict] = None
    prompt_used: Optional[str] = None
    success: bool
    error: Optional[str] = None


@router.post("/influencer", response_model=InfluencerGenerationResponse)
async def generate_influencer(request: InfluencerGenerationRequest):
    """
    AI 인플루언서 이미지 생성 + 갤러리 자동 등록.

    1. generate_full_pipeline() 호출
    2. 결과 이미지 저장
    3. showcase_data.json에 자동 등록
    4. 프론트엔드 갤러리에 바로 표시
    """
    import asyncio

    generation_id = str(uuid.uuid4())

    try:
        # 경로 resolve (로컬/S3 자동 전환)
        face_images = _resolve_inputs(request.face_image_paths)
        outfit_images = _resolve_inputs(request.outfit_image_paths)
        pose_image = _resolve_input(request.pose_image_path)
        expression_image = _resolve_input(request.expression_image_path)
        background_image = _resolve_input(request.background_image_path)

        # generate_full_pipeline 호출 (동기 함수를 async로 래핑)
        from core.ai_influencer.pipeline import generate_full_pipeline

        result = await asyncio.to_thread(
            generate_full_pipeline,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_image=pose_image,
            expression_image=expression_image,
            background_image=background_image,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution,
            temperature=0.7,
            validate=True,
            max_retries=2,
        )

        if result.get("image") is None:
            return InfluencerGenerationResponse(
                generation_id=generation_id,
                success=False,
                error="Image generation failed - no image returned",
            )

        # _save_and_register로 통합 저장 (로컬/S3 자동 전환)
        saved = _save_and_register(
            workflow="ai_influencer",
            result_image=result["image"],
            title=request.title,
            input_files={
                "face": request.face_image_paths,
                "outfit": request.outfit_image_paths,
                "pose": request.pose_image_path,
                "expression": request.expression_image_path,
                "background": request.background_image_path,
            },
            prompt_text=result.get("prompt", ""),
            config_extra={
                "aspect_ratio": request.aspect_ratio,
                "resolution": request.resolution,
                "temperature": 0.7,
            },
            validation=result.get("validation"),
            auto_showcase=request.auto_showcase,
        )

        return InfluencerGenerationResponse(
            generation_id=generation_id,
            success=True,
            **saved,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return InfluencerGenerationResponse(
            generation_id=generation_id, success=False, error=str(e)
        )


# ============================================================
# Shared helpers for all generation endpoints
# ============================================================


def _save_and_register(
    workflow: str,
    result_image,
    title: str,
    input_files: dict,
    prompt_text: str,
    config_extra: dict,
    validation: dict = None,
    auto_showcase: bool = True,
    showcase_type: str = None,
) -> dict:
    """모든 워크플로 공통: 결과 저장 + showcase 등록.

    FNF_OUTPUT_MODE에 따라:
    - local: Fnf_studio_outputs/ 에 로컬 저장
    - s3: S3에 업로드, URL 반환
    """
    import json as _json
    from datetime import datetime
    from core.storage import (
        save_output_image,
        save_output_json,
        save_output_file,
        get_output_url,
        is_output_s3,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title_safe = (title or workflow).replace(" ", "_").replace("/", "_")[:50]
    base_path = f"{workflow}/{timestamp}_{title_safe}"

    # 인풋 이미지 복사
    for category, paths in input_files.items():
        if isinstance(paths, (list, tuple)):
            for i, p in enumerate(paths):
                ext = p.rsplit(".", 1)[-1] if "." in str(p) else "jpg"
                save_output_file(
                    str(p),
                    f"{base_path}/images/input_{category}_{i+1:02d}.{ext}",
                )
        else:
            ext = str(paths).rsplit(".", 1)[-1] if "." in str(paths) else "jpg"
            save_output_file(
                str(paths),
                f"{base_path}/images/input_{category}.{ext}",
            )

    # 결과 이미지 저장
    relative_path = f"{base_path}/images/output_001.jpg"
    save_output_image(result_image, relative_path)

    # prompt.json
    save_output_json({"prompt": prompt_text}, f"{base_path}/prompt.json")

    # config.json
    config = {"workflow": workflow, "timestamp": datetime.now().isoformat()}
    config.update(config_extra)
    save_output_json(config, f"{base_path}/config.json")

    # validation.json
    if validation:
        save_output_json(validation, f"{base_path}/validation.json")

    # 이미지 URL (로컬: /outputs/... , S3: https://...)
    image_url = get_output_url(relative_path)

    # showcase 등록
    showcase_id = None
    if auto_showcase:
        try:
            from api.routers.showcase import register_to_showcase

            showcase_id = register_to_showcase(
                workflow_type=showcase_type or workflow,
                image_path=relative_path,
                title=title or f"{workflow} {timestamp}",
                description=f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )
        except Exception:
            pass  # showcase 실패해도 생성 결과는 유지

    return {
        "image_url": image_url,
        "showcase_id": showcase_id,
        "validation": validation,
        "prompt_used": (prompt_text or "")[:500],
    }


# ============================================================
# Selfie Generation (→ ai_influencer 갤러리에 등록)
# ============================================================


class SelfieGenerationRequest(BaseModel):
    """셀카 생성 요청."""

    face_image_paths: List[str] = Field(
        ..., min_length=1, max_length=3, description="얼굴 이미지 경로"
    )
    outfit_image_paths: List[str] = Field(
        default_factory=list, description="착장 이미지 경로 (선택)"
    )
    pose_image_path: Optional[str] = Field(
        None, description="포즈 레퍼런스 경로 (선택)"
    )
    expression_image_path: Optional[str] = Field(
        None, description="표정 레퍼런스 경로 (선택)"
    )
    background_image_path: Optional[str] = Field(
        None, description="배경 레퍼런스 경로 (선택)"
    )
    prompt: str = Field("", description="추가 프롬프트 텍스트")
    aspect_ratio: str = Field("9:16", description="비율")
    resolution: str = Field("2K", description="해상도")
    title: Optional[str] = Field(None, description="갤러리 표시용 제목")
    auto_showcase: bool = Field(True, description="자동으로 갤러리에 등록")


class WorkflowGenerationResponse(BaseModel):
    """공통 워크플로 생성 응답."""

    generation_id: str
    image_url: Optional[str] = None
    showcase_id: Optional[str] = None
    validation: Optional[dict] = None
    prompt_used: Optional[str] = None
    success: bool
    error: Optional[str] = None


@router.post("/selfie", response_model=WorkflowGenerationResponse)
async def generate_selfie_endpoint(request: SelfieGenerationRequest):
    """셀카 생성 + ai_influencer 갤러리 자동 등록."""
    import asyncio

    generation_id = str(uuid.uuid4())
    try:
        # 경로 resolve (로컬/S3 자동 전환)
        face_images = _resolve_inputs(request.face_image_paths)
        outfit_images = (
            _resolve_inputs(request.outfit_image_paths)
            if request.outfit_image_paths
            else []
        )
        pose_ref = (
            _resolve_input(request.pose_image_path) if request.pose_image_path else None
        )
        expr_ref = (
            _resolve_input(request.expression_image_path)
            if request.expression_image_path
            else None
        )
        bg_ref = (
            _resolve_input(request.background_image_path)
            if request.background_image_path
            else None
        )

        from core.selfie.generator import generate_with_validation

        result = await asyncio.to_thread(
            generate_with_validation,
            prompt=request.prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_ref,
            bg_reference=bg_ref,
            expression_reference=expr_ref,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution,
            max_retries=2,
        )

        if result.get("image") is None:
            return WorkflowGenerationResponse(
                generation_id=generation_id,
                success=False,
                error="Selfie generation failed",
            )

        input_files = {"face": request.face_image_paths}
        if request.outfit_image_paths:
            input_files["outfit"] = request.outfit_image_paths

        saved = _save_and_register(
            workflow="selfie",
            result_image=result["image"],
            title=request.title,
            input_files=input_files,
            prompt_text=request.prompt,
            config_extra={
                "aspect_ratio": request.aspect_ratio,
                "resolution": request.resolution,
            },
            validation=result.get("validation"),
            auto_showcase=request.auto_showcase,
            showcase_type="ai_influencer",  # 셀카 → 인플 갤러리
        )

        return WorkflowGenerationResponse(
            generation_id=generation_id, success=True, **saved
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return WorkflowGenerationResponse(
            generation_id=generation_id, success=False, error=str(e)
        )


# ============================================================
# Brandcut Generation (브랜드컷)
# ============================================================


class BrandcutGenerationRequest(BaseModel):
    """브랜드컷 생성 요청."""

    face_image_paths: List[str] = Field(
        ..., min_length=1, max_length=3, description="얼굴 이미지 경로"
    )
    outfit_image_paths: List[str] = Field(
        ..., min_length=1, description="착장 이미지 경로"
    )
    pose_image_path: Optional[str] = Field(
        None, description="포즈 레퍼런스 경로 (선택)"
    )
    prompt_json: Optional[dict] = Field(
        None, description="프롬프트 JSON (없으면 자동 생성)"
    )
    aspect_ratio: str = Field("3:4", description="비율")
    resolution: str = Field("2K", description="해상도")
    title: Optional[str] = Field(None, description="갤러리 표시용 제목")
    auto_showcase: bool = Field(True, description="자동으로 갤러리에 등록")


@router.post("/brandcut", response_model=WorkflowGenerationResponse)
async def generate_brandcut_endpoint(request: BrandcutGenerationRequest):
    """브랜드컷 생성 + 갤러리 자동 등록."""
    import asyncio

    generation_id = str(uuid.uuid4())
    try:
        # 경로 resolve (로컬/S3 자동 전환)
        face_images = _resolve_inputs(request.face_image_paths)
        outfit_images = _resolve_inputs(request.outfit_image_paths)
        pose_ref = (
            _resolve_input(request.pose_image_path) if request.pose_image_path else None
        )

        from core.brandcut import generate_with_validation

        result = await asyncio.to_thread(
            generate_with_validation,
            prompt_json=request.prompt_json or {},
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_ref,
            max_retries=2,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution,
        )

        if result.get("image") is None:
            return WorkflowGenerationResponse(
                generation_id=generation_id,
                success=False,
                error="Brandcut generation failed",
            )

        saved = _save_and_register(
            workflow="brand_cut",
            result_image=result["image"],
            title=request.title,
            input_files={
                "face": request.face_image_paths,
                "outfit": request.outfit_image_paths,
            },
            prompt_text=str(result.get("prompt", request.prompt_json or "")),
            config_extra={
                "aspect_ratio": request.aspect_ratio,
                "resolution": request.resolution,
            },
            validation=result.get("criteria") or result.get("validation"),
            auto_showcase=request.auto_showcase,
        )

        return WorkflowGenerationResponse(
            generation_id=generation_id, success=True, **saved
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return WorkflowGenerationResponse(
            generation_id=generation_id, success=False, error=str(e)
        )


# ============================================================
# Background Swap Generation (배경 변경)
# ============================================================


class BackgroundSwapGenerationRequest(BaseModel):
    """배경 변경 생성 요청."""

    source_image_path: str = Field(..., description="원본 인물 이미지 경로")
    background_style: str = Field(..., description="배경 스타일 설명 텍스트")
    resolution: str = Field("2K", description="해상도")
    title: Optional[str] = Field(None, description="갤러리 표시용 제목")
    auto_showcase: bool = Field(True, description="자동으로 갤러리에 등록")


@router.post("/background-swap", response_model=WorkflowGenerationResponse)
async def generate_background_swap_endpoint(request: BackgroundSwapGenerationRequest):
    """배경 변경 + 갤러리 자동 등록."""
    import asyncio

    generation_id = str(uuid.uuid4())
    try:
        # 경로 resolve (로컬/S3 자동 전환)
        source = _resolve_input(request.source_image_path)

        from core.background_swap.generator import generate_with_validation

        result = await asyncio.to_thread(
            generate_with_validation,
            source_image=source,
            background_style=request.background_style,
            max_retries=2,
            image_size=request.resolution,
        )

        if result.get("image") is None:
            return WorkflowGenerationResponse(
                generation_id=generation_id,
                success=False,
                error="Background swap failed",
            )

        saved = _save_and_register(
            workflow="background_swap",
            result_image=result["image"],
            title=request.title,
            input_files={"source": request.source_image_path},
            prompt_text=request.background_style,
            config_extra={
                "resolution": request.resolution,
                "background_style": request.background_style,
            },
            validation=result.get("validation")
            or {
                "score": result.get("score"),
                "passed": result.get("passed"),
                "grade": result.get("grade"),
            },
            auto_showcase=request.auto_showcase,
        )

        return WorkflowGenerationResponse(
            generation_id=generation_id, success=True, **saved
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return WorkflowGenerationResponse(
            generation_id=generation_id, success=False, error=str(e)
        )


# ============================================================
# Outfit Swap Generation (착장 변경)
# ============================================================


class OutfitSwapGenerationRequest(BaseModel):
    """착장 변경 생성 요청."""

    source_image_path: str = Field(..., description="원본 인물 이미지 경로")
    outfit_image_paths: List[str] = Field(
        ..., min_length=1, description="새 착장 이미지 경로"
    )
    aspect_ratio: str = Field("auto", description="비율 (auto=원본 유지)")
    resolution: str = Field("2K", description="해상도")
    title: Optional[str] = Field(None, description="갤러리 표시용 제목")
    auto_showcase: bool = Field(True, description="자동으로 갤러리에 등록")


@router.post("/outfit-swap", response_model=WorkflowGenerationResponse)
async def generate_outfit_swap_endpoint(request: OutfitSwapGenerationRequest):
    """착장 변경 + 갤러리 자동 등록."""
    import asyncio

    generation_id = str(uuid.uuid4())
    try:
        # 경로 resolve (로컬/S3 자동 전환)
        source = _resolve_input(request.source_image_path)
        outfit_images = _resolve_inputs(request.outfit_image_paths)

        from core.outfit_swap.generator import generate_with_validation

        result = await asyncio.to_thread(
            generate_with_validation,
            source_image=source,
            outfit_images=outfit_images,
            client=None,
            max_retries=2,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution,
        )

        if result.get("image") is None:
            return WorkflowGenerationResponse(
                generation_id=generation_id, success=False, error="Outfit swap failed"
            )

        saved = _save_and_register(
            workflow="outfit_swap",
            result_image=result["image"],
            title=request.title,
            input_files={
                "source": request.source_image_path,
                "outfit": request.outfit_image_paths,
            },
            prompt_text=str(result.get("prompt", "")),
            config_extra={
                "aspect_ratio": request.aspect_ratio,
                "resolution": request.resolution,
            },
            validation=result.get("criteria") or result.get("validation"),
            auto_showcase=request.auto_showcase,
        )

        return WorkflowGenerationResponse(
            generation_id=generation_id, success=True, **saved
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return WorkflowGenerationResponse(
            generation_id=generation_id, success=False, error=str(e)
        )
