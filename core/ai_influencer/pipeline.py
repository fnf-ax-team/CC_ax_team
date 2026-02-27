"""
AI 인플루언서 풀 파이프라인

VLM 분석 -> 프롬프트 조립 -> 이미지 생성의 전체 플로우를 오케스트레이션.

WARNING: generate_ai_influencer()를 직접 호출하면 안됨!
   -> 그 함수는 VLM 분석을 건너뛰고 generic label만 사용함.
   -> 반드시 이 파이프라인을 거쳐야 포즈/프레이밍/배경 정확도 보장.

파이프라인 단계:
1. analyze_hair()        -- 얼굴 이미지에서 헤어 정보 추출
2. analyze_expression()  -- 표정 이미지에서 표정 정보 추출 (상세 버전)
3. analyze_pose()        -- 포즈 이미지에서 포즈/프레이밍/앵글 추출
4. analyze_background()  -- 배경 이미지에서 장소/조명/분위기 추출
5. check_compatibility() -- 포즈-배경 호환성 검사
6. OutfitAnalyzer.analyze() -- 착장 이미지 상세 분석
7. build_schema_prompt() -- 분석 결과를 스키마 프롬프트로 조립
8. send_image_request()  -- 프롬프트 + 모든 이미지 레퍼런스 -> API 호출
"""

import time
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.ai_influencer.hair_analyzer import analyze_hair, HairAnalysisResult
from core.ai_influencer.expression_analyzer import (
    ExpressionAnalyzer,
    ExpressionAnalysisResult,
)
from core.ai_influencer.pose_analyzer import analyze_pose, PoseAnalysisResult
from core.ai_influencer.background_analyzer import (
    analyze_background,
    BackgroundAnalysisResult,
)
from core.ai_influencer.compatibility import check_compatibility, CompatibilityResult
from core.ai_influencer.prompt_builder import build_schema_prompt
from core.ai_influencer.generator import pil_to_part
from core.outfit_analyzer import OutfitAnalyzer


def send_image_request(
    client,
    prompt: str,
    face_images: List[Path],
    outfit_images: List[Path],
    pose_image: Path,
    expression_image: Path,
    background_image: Path,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.35,
) -> Optional[Image.Image]:
    """
    이미지 생성 API 호출 - 모든 레퍼런스 이미지 포함

    전송 순서:
    1. 프롬프트 (텍스트)
    2. [POSE REFERENCE] 포즈 이미지
    3. [EXPRESSION REFERENCE] 표정 이미지
    4. [FACE] 얼굴 이미지
    5. [OUTFIT 1~N] 착장 이미지
    6. [BACKGROUND REFERENCE] 배경 이미지
    7. [POSE REMINDER] 포즈 재강조
    """

    parts = []

    # 1. 프롬프트
    parts.append(types.Part(text=prompt))

    # 2. 포즈 레퍼런스
    if pose_image and Path(pose_image).exists():
        img = Image.open(pose_image).convert("RGB")
        parts.append(types.Part(text="[POSE REFERENCE]"))
        parts.append(pil_to_part(img))

    # 3. 표정 레퍼런스
    if expression_image and Path(expression_image).exists():
        img = Image.open(expression_image).convert("RGB")
        parts.append(
            types.Part(text="[EXPRESSION REFERENCE] - Copy expression only, NOT hair")
        )
        parts.append(pil_to_part(img))

    # 4. 얼굴 이미지
    for i, face_path in enumerate(face_images):
        if Path(face_path).exists():
            img = Image.open(face_path).convert("RGB")
            parts.append(
                types.Part(text=f"[FACE {i+1}] - Use this person's identity and hair")
            )
            parts.append(pil_to_part(img))

    # 5. 착장 이미지
    for i, outfit_path in enumerate(outfit_images):
        if Path(outfit_path).exists():
            img = Image.open(outfit_path).convert("RGB")
            parts.append(types.Part(text=f"[OUTFIT {i+1}]"))
            parts.append(pil_to_part(img))

    # 6. 배경 이미지
    if background_image and Path(background_image).exists():
        img = Image.open(background_image).convert("RGB")
        parts.append(
            types.Part(text="[BACKGROUND REFERENCE] - Ignore person in this image")
        )
        parts.append(pil_to_part(img))

    # 7. 포즈 재강조 (마지막에 다시 전송)
    if pose_image and Path(pose_image).exists():
        img = Image.open(pose_image).convert("RGB")
        parts.append(
            types.Part(
                text="[POSE REMINDER] *** CRITICAL: Copy this EXACT pose! If one leg is lifted, it MUST be lifted in the output! ***"
            )
        )
        parts.append(pil_to_part(img))

    # API 호출
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                ),
            ),
        )

        # 이미지 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data))

        return None

    except Exception as e:
        print(f"[Generate] Error: {e}")
        return None


def generate_full_pipeline(
    face_images: List[Union[str, Path]],
    outfit_images: List[Union[str, Path]],
    pose_image: Union[str, Path],
    expression_image: Union[str, Path],
    background_image: Union[str, Path],
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.35,
    client=None,
) -> Dict[str, Any]:
    """
    AI 인플루언서 풀 파이프라인 실행

    8단계 파이프라인:
    1. analyze_hair
    2. analyze_expression (상세 버전)
    3. analyze_pose
    4. analyze_background
    5. check_compatibility
    6. OutfitAnalyzer.analyze
    7. build_schema_prompt
    8. send_image_request

    Args:
        face_images: 얼굴 이미지 경로 목록
        outfit_images: 착장 이미지 경로 목록
        pose_image: 포즈 레퍼런스 이미지 경로
        expression_image: 표정 레퍼런스 이미지 경로
        background_image: 배경 레퍼런스 이미지 경로
        aspect_ratio: 화면 비율 (기본 9:16)
        resolution: 해상도 (기본 2K)
        temperature: 생성 온도 (기본 0.35)
        client: genai.Client (None이면 자동 생성)

    Returns:
        dict: {
            "image": PIL.Image or None,
            "prompt": str,
            "analysis": {
                "hair": HairAnalysisResult,
                "expression": ExpressionAnalysisResult,
                "pose": PoseAnalysisResult,
                "background": BackgroundAnalysisResult,
                "compatibility": CompatibilityResult,
                "outfit": OutfitAnalysisResult,
            }
        }
    """
    # Path 변환
    face_images = [Path(p) for p in face_images]
    outfit_images = [Path(p) for p in outfit_images]
    pose_image = Path(pose_image)
    expression_image = Path(expression_image)
    background_image = Path(background_image)

    # 클라이언트 생성
    if client is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    # =========================================================
    # STEP 1: 헤어 분석
    # =========================================================
    print("\n[1/8] Analyzing hair from face image...")
    hair_result = analyze_hair(face_images[0])
    print(f"  Hair: {hair_result.to_schema_format()}")

    # =========================================================
    # STEP 2: 표정 분석 (상세 버전 - ExpressionAnalysisResult)
    # =========================================================
    print("\n[2/8] Analyzing expression (detailed)...")
    expr_analyzer = ExpressionAnalyzer()
    expression_result = expr_analyzer.analyze(expression_image)
    print(f"  Mood: {expression_result.mood_base}, {expression_result.mood_vibe}")

    # =========================================================
    # STEP 3: 포즈 분석
    # =========================================================
    print("\n[3/8] Analyzing pose...")
    pose_result = analyze_pose(pose_image)
    print(f"  Stance: {pose_result.stance}, Framing: {pose_result.framing}")

    # =========================================================
    # STEP 4: 배경 분석
    # =========================================================
    print("\n[4/8] Analyzing background...")
    background_result = analyze_background(background_image)
    print(
        f"  Scene: {background_result.scene_type}, Provides: {background_result.provides}"
    )

    # =========================================================
    # STEP 5: 호환성 검사
    # =========================================================
    print("\n[5/8] Checking compatibility...")
    compatibility_result = check_compatibility(pose_result, background_result)
    print(
        f"  Level: {compatibility_result.level.value}, Score: {compatibility_result.score}"
    )

    # =========================================================
    # STEP 6: 착장 분석
    # =========================================================
    print("\n[6/8] Analyzing outfit...")
    outfit_analyzer = OutfitAnalyzer(client)
    outfit_result = outfit_analyzer.analyze([str(p) for p in outfit_images])
    print(f"  Style: {outfit_result.overall_style}")
    print(f"  Brand: {outfit_result.brand_detected}")
    print(f"  Items: {len(outfit_result.items)}")

    # =========================================================
    # STEP 7: 프롬프트 조립
    # =========================================================
    print("\n[7/8] Building schema prompt...")
    prompt = build_schema_prompt(
        hair_result=hair_result,
        expression_result=expression_result,
        pose_result=pose_result,
        background_result=background_result,
        outfit_result=outfit_result,
        compatibility_result=compatibility_result,
    )
    print(f"  Prompt length: {len(prompt.splitlines())} lines")

    # =========================================================
    # STEP 8: 이미지 생성
    # =========================================================
    print("\n[8/8] Generating image (all references included)...")
    image = send_image_request(
        client=client,
        prompt=prompt,
        face_images=face_images,
        outfit_images=outfit_images,
        pose_image=pose_image,
        expression_image=expression_image,
        background_image=background_image,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        temperature=temperature,
    )

    if image:
        print("  [OK] Image generated successfully")
    else:
        print("  [FAIL] Image generation failed")

    return {
        "image": image,
        "prompt": prompt,
        "analysis": {
            "hair": hair_result,
            "expression": expression_result,
            "pose": pose_result,
            "background": background_result,
            "compatibility": compatibility_result,
            "outfit": outfit_result,
        },
    }
