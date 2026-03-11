"""
FNF AI Studio MCP Server

F&F 패션 브랜드 AI 이미지 생성 플랫폼의 MCP 서버.
7가지 주요 워크플로 + 2가지 유틸리티 도구를 제공합니다.

도구 목록:
  1. generate_brandcut     - 브랜드컷(에디토리얼 화보) 생성
  2. swap_background       - 배경 교체
  3. swap_outfit            - 착장 교체
  4. generate_influencer   - AI 인플루언서 이미지 생성
  5. swap_face              - 얼굴 교체 (포즈/착장/배경 유지)
  6. generate_ecommerce    - 이커머스 모델 이미지 생성
  7. copy_pose              - 포즈 따라하기 (레퍼런스 포즈 복제)
  8. list_options           - 비율/해상도/비용 옵션 조회
  9. list_presets           - 프리셋/캐릭터 목록 조회
"""

import os
import json
import traceback

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from fnf_studio_mcp.helpers import (
    protect_stdout,
    load_image,
    load_images,
    save_generation_result,
)

# .env 로드 (GEMINI_API_KEY)
load_dotenv()

# FastMCP 서버 인스턴스
mcp = FastMCP("fnf-studio")


# ============================================================
# 공통 유틸리티
# ============================================================


def _get_api_key() -> str:
    """환경변수에서 API 키 가져오기 (core.api 모듈의 로테이션 사용)."""
    with protect_stdout():
        from core.api import _get_next_api_key

        return _get_next_api_key()


def _serialize_result(result: dict) -> dict:
    """생성 결과에서 PIL Image 등 직렬화 불가능한 객체 제거."""
    serializable = {}
    for k, v in result.items():
        if k == "image":
            continue  # PIL Image 제외
        try:
            json.dumps(v)
            serializable[k] = v
        except (TypeError, ValueError):
            serializable[k] = str(v)
    return serializable


# ============================================================
# Tool 1: 브랜드컷 생성
# ============================================================


@mcp.tool()
def generate_brandcut(
    face_image_paths: list[str],
    outfit_image_paths: list[str],
    prompt_json: dict,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2,
    temperature: float = 0.30,
    pose_reference_path: str | None = None,
    expression_reference_path: str | None = None,
    background_reference_path: str | None = None,
) -> str:
    """브랜드컷(에디토리얼 화보) 이미지를 생성합니다.
    얼굴 이미지 + 착장 이미지 + 프롬프트를 기반으로 브랜드 화보를 생성하고,
    자동 검증 + 재시도를 수행합니다.

    Args:
        face_image_paths: 얼굴 이미지 파일 경로 목록 (1~3장)
        outfit_image_paths: 착장 이미지 파일 경로 목록 (전체 전송 필수)
        prompt_json: 프롬프트 JSON (한국어 스키마)
        aspect_ratio: 비율 (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수
        temperature: 생성 온도
        pose_reference_path: 포즈 레퍼런스 이미지 경로 (선택)
        expression_reference_path: 표정 레퍼런스 이미지 경로 (선택)
        background_reference_path: 배경 레퍼런스 이미지 경로 (선택)

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()

        # 옵션 레퍼런스 이미지 로드
        pose_ref = load_image(pose_reference_path) if pose_reference_path else None
        expr_ref = (
            load_image(expression_reference_path) if expression_reference_path else None
        )
        bg_ref = (
            load_image(background_reference_path) if background_reference_path else None
        )

        with protect_stdout():
            from core.brandcut import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                prompt_json=prompt_json,
                face_images=face_image_paths,
                outfit_images=outfit_image_paths,
                api_key=api_key,
                max_retries=max_retries,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                initial_temperature=temperature,
                pose_reference=pose_ref,
                expression_reference=expr_ref,
                background_reference=bg_ref,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                    "history": result.get("history", []),
                },
                ensure_ascii=False,
            )

        # 결과 저장
        output_path = save_generation_result(
            workflow="brand_cut",
            image=result["image"],
            prompt_json=prompt_json,
            config={
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "temperature": temperature,
            },
            validation=result.get("criteria"),
            input_images={
                "face": face_image_paths,
                "outfit": outfit_image_paths,
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 2: 배경 교체
# ============================================================


@mcp.tool()
def swap_background(
    source_image_path: str,
    background_style: str,
    resolution: str = "2K",
    max_retries: int = 2,
) -> str:
    """인물 이미지의 배경을 교체합니다.
    인물은 그대로 보존하고 배경만 변경합니다.

    Args:
        source_image_path: 원본 인물 이미지 파일 경로
        background_style: 원하는 배경 스타일 설명 (예: "urban street at night", "beach sunset")
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()
        source_image = load_image(source_image_path)

        with protect_stdout():
            from core.background_swap import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                source=source_image,
                background_style=background_style,
                api_key=api_key,
                max_retries=max_retries,
                resolution=resolution,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="background_swap",
            image=result["image"],
            config={
                "resolution": resolution,
                "background_style": background_style,
            },
            validation=result.get("criteria"),
            input_images={"source": [source_image_path]},
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 3: 착장 교체
# ============================================================


@mcp.tool()
def swap_outfit(
    source_image_path: str,
    outfit_image_paths: list[str],
    resolution: str = "2K",
    max_retries: int = 2,
) -> str:
    """인물 이미지의 착장(옷)만 교체합니다.
    얼굴, 포즈, 배경은 그대로 유지합니다.

    Args:
        source_image_path: 원본 인물 이미지 파일 경로
        outfit_image_paths: 교체할 착장 이미지 파일 경로 목록 (최대 10장)
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()
        source_image = load_image(source_image_path)
        outfit_images = load_images(outfit_image_paths)

        with protect_stdout():
            from core.outfit_swap import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                source_image=source_image,
                outfit_images=outfit_images,
                api_key=api_key,
                max_retries=max_retries,
                resolution=resolution,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="outfit_swap",
            image=result["image"],
            config={"resolution": resolution},
            validation=result.get("criteria"),
            input_images={
                "source": [source_image_path],
                "outfit": outfit_image_paths,
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 4: AI 인플루언서 생성
# ============================================================


@mcp.tool()
def generate_influencer(
    character_name: str,
    pose_preset_id: str | None = None,
    expression_preset_id: str | None = None,
    background_preset_id: str | None = None,
) -> str:
    """AI 인플루언서 이미지를 생성합니다.
    등록된 캐릭터의 얼굴 이미지를 기반으로 이미지 레퍼런스 방식으로 생성합니다.

    Args:
        character_name: 등록된 캐릭터 이름
        pose_preset_id: 포즈 프리셋 ID (선택, list_presets로 확인)
        expression_preset_id: 표정 프리셋 ID (선택)
        background_preset_id: 배경 프리셋 ID (선택)

    Returns:
        생성 결과 JSON (success, output_path, score, passed)
    """
    try:
        api_key = _get_api_key()

        with protect_stdout():
            from core.ai_influencer import generate_with_validation

            result = generate_with_validation(
                character_name=character_name,
                pose_preset_id=pose_preset_id or "natural_stand",
                expression_preset_id=expression_preset_id or "natural_smile",
                api_key=api_key,
                max_retries=2,
                background_preset_id=background_preset_id,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="ai_influencer",
            image=result["image"],
            config={
                "character_name": character_name,
                "pose_preset": pose_preset_id,
                "expression_preset": expression_preset_id,
                "background_preset": background_preset_id,
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 5: 얼굴 교체
# ============================================================


@mcp.tool()
def swap_face(
    source_image_path: str,
    face_image_paths: list[str],
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2,
) -> str:
    """인물 이미지의 얼굴만 교체합니다.
    포즈, 착장, 배경은 그대로 유지합니다.

    Args:
        source_image_path: 원본 인물 이미지 파일 경로 (포즈/착장/배경 보존)
        face_image_paths: 교체할 얼굴 이미지 파일 경로 목록 (1~3장)
        aspect_ratio: 비율 (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()

        with protect_stdout():
            from core.face_swap import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                source_image=source_image_path,
                face_images=face_image_paths,
                api_key=api_key,
                max_retries=max_retries,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                    "history": result.get("history", []),
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="face_swap",
            image=result["image"],
            config={
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            },
            validation=result.get("criteria"),
            input_images={
                "source": [source_image_path],
                "face": face_image_paths,
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 6: 이커머스 모델 이미지 생성
# ============================================================


@mcp.tool()
def generate_ecommerce(
    face_image_paths: list[str],
    outfit_image_paths: list[str],
    pose: str = "front_standing",
    background: str = "white_studio",
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2,
    temperature: float = 0.2,
) -> str:
    """이커머스용 모델 이미지를 생성합니다.
    온라인 쇼핑몰 상세페이지 및 룩북용. 착장 정확도를 최우선합니다.

    Args:
        face_image_paths: 얼굴 이미지 파일 경로 목록 (1~3장)
        outfit_image_paths: 착장 이미지 파일 경로 목록 (전체 전송 필수)
        pose: 포즈 프리셋 (front_standing, side_standing, walking 등)
        background: 배경 프리셋 (white_studio, gray_studio, minimal 등)
        aspect_ratio: 비율 (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수
        temperature: 생성 온도 (기본 0.2, 상업적 일관성)

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()

        with protect_stdout():
            from core.ecommerce import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                face_images=face_image_paths,
                outfit_images=outfit_image_paths,
                api_key=api_key,
                pose=pose,
                background=background,
                max_retries=max_retries,
                temperature=temperature,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                    "history": result.get("history", []),
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="ecommerce",
            image=result["image"],
            prompt_json=result.get("prompt"),
            config={
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "temperature": temperature,
                "pose": pose,
                "background": background,
            },
            validation=result.get("criteria"),
            input_images={
                "face": face_image_paths,
                "outfit": outfit_image_paths,
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 7: 포즈 따라하기
# ============================================================


@mcp.tool()
def copy_pose(
    source_image_path: str,
    reference_image_path: str,
    background_mode: str = "reference",
    custom_background: str | None = None,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    max_retries: int = 2,
) -> str:
    """레퍼런스 이미지의 포즈를 소스 인물에 적용합니다.
    소스의 얼굴, 착장을 유지하면서 레퍼런스의 포즈/구도를 복제합니다.

    Args:
        source_image_path: 소스 인물 이미지 파일 경로 (얼굴/착장 보존)
        reference_image_path: 레퍼런스 이미지 파일 경로 (포즈/구도 복제 대상)
        background_mode: 배경 처리 ("reference"=레퍼런스배경, "source"=소스배경, "custom"=직접지정)
        custom_background: background_mode가 "custom"일 때 배경 설명
        aspect_ratio: 비율 (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
        resolution: 해상도 (1K, 2K, 4K)
        max_retries: 최대 재시도 횟수

    Returns:
        생성 결과 JSON (success, output_path, score, passed, attempts, cost_krw)
    """
    try:
        api_key = _get_api_key()

        with protect_stdout():
            from core.pose_copy import generate_with_validation
            from core.options import get_cost

            result = generate_with_validation(
                source_image=source_image_path,
                reference_image=reference_image_path,
                api_key=api_key,
                background_mode=background_mode,
                custom_background=custom_background,
                max_retries=max_retries,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )

        if result.get("image") is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "All generation attempts failed",
                    "history": result.get("history", []),
                },
                ensure_ascii=False,
            )

        output_path = save_generation_result(
            workflow="pose_copy",
            image=result["image"],
            config={
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "background_mode": background_mode,
                "custom_background": custom_background,
            },
            validation=result.get("criteria"),
            input_images={
                "source": [source_image_path],
                "reference": [reference_image_path],
            },
        )

        return json.dumps(
            {
                "success": True,
                "output_path": output_path,
                "score": result.get("score", 0),
                "passed": result.get("passed", False),
                "attempts": result.get("attempts", 1),
                "cost_krw": get_cost(resolution, result.get("attempts", 1)),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )


# ============================================================
# Tool 8: 옵션 조회
# ============================================================


@mcp.tool()
def list_options() -> str:
    """사용 가능한 이미지 생성 옵션을 조회합니다.
    비율, 해상도, 비용 정보를 반환합니다.

    Returns:
        옵션 정보 JSON (aspect_ratios, resolutions, costs, workflow_defaults)
    """
    try:
        with protect_stdout():
            from core.options import (
                ASPECT_RATIOS,
                RESOLUTIONS,
                COST_TABLE,
                WORKFLOW_DEFAULTS,
            )

        return json.dumps(
            {
                "aspect_ratios": sorted(list(ASPECT_RATIOS)),
                "resolutions": {k: f"{v}px" for k, v in RESOLUTIONS.items()},
                "cost_per_image": {
                    "1K": "190 KRW",
                    "2K": "190 KRW",
                    "4K": "380 KRW",
                },
                "workflow_defaults": {
                    name: {
                        "aspect_ratio": d.aspect_ratio,
                        "temperature": d.temperature,
                    }
                    for name, d in WORKFLOW_DEFAULTS.items()
                }
                if hasattr(list(WORKFLOW_DEFAULTS.values())[0], "aspect_ratio")
                else str(WORKFLOW_DEFAULTS),
            },
            ensure_ascii=False,
            default=str,
        )

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# Tool 9: 프리셋 조회
# ============================================================


@mcp.tool()
def list_presets(
    preset_type: str | None = None,
) -> str:
    """AI 인플루언서 프리셋 및 캐릭터 목록을 조회합니다.

    Args:
        preset_type: 프리셋 유형 ("pose", "expression", "background"). 미지정 시 전체 조회.

    Returns:
        프리셋 목록 JSON (characters, presets)
    """
    try:
        with protect_stdout():
            from core.ai_influencer import (
                list_characters,
                list_presets as _list_presets,
            )

            result = {}

            # 캐릭터 목록
            try:
                result["characters"] = list_characters()
            except Exception:
                result["characters"] = []

            # 프리셋 목록
            if preset_type:
                try:
                    result["presets"] = _list_presets(preset_type)
                except Exception:
                    result["presets"] = []
            else:
                result["presets"] = {}
                for pt in ["pose", "expression", "background"]:
                    try:
                        result["presets"][pt] = _list_presets(pt)
                    except Exception:
                        result["presets"][pt] = []

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# 서버 엔트리포인트
# ============================================================


def main():
    """MCP 서버 시작 (stdio 모드)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
