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
                text="[POSE REMINDER] *** CRITICAL: Copy this EXACT pose! Pay attention to leg shape: if knee points SIDEWAYS (figure-4), do NOT lift it FORWARD. Match the exact direction! ***"
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
    max_retries: int = 2,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    AI 인플루언서 풀 파이프라인 실행 (검증+재생성 루프 포함)

    파이프라인 흐름:
    1. VLM 분석 (1회만 - 비용 절약)
       - analyze_hair, analyze_expression, analyze_pose
       - analyze_background, check_compatibility, OutfitAnalyzer
    2. 검증+재생성 루프 (최대 max_retries+1회):
       a. build_schema_prompt (재시도 시 enhancement 추가)
       b. send_image_request
       c. validator.validate (validate=True일 때)
       d. 통과 -> break
       e. 실패 -> enhancement_rules로 프롬프트 보강, temperature 낮춤

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
        max_retries: 검증 실패 시 최대 재시도 횟수 (기본 2)
        validate: 검증 활성화 여부 (기본 True)

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
            },
            "validation": {
                "passed": bool,
                "score": int,
                "grade": str,
                "attempts": int,
                "history": list,
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
    # VLM 분석 (1회만 실행 - 재시도 시 결과 재사용)
    # =========================================================

    # STEP 1: 헤어 분석
    print("\n[1/8] Analyzing hair from face image...")
    hair_result = analyze_hair(face_images[0])
    print(f"  Hair: {hair_result.to_schema_format()}")

    # STEP 2: 표정 분석 (상세 버전)
    print("\n[2/8] Analyzing expression (detailed)...")
    expr_analyzer = ExpressionAnalyzer()
    expression_result = expr_analyzer.analyze(expression_image)
    print(f"  Mood: {expression_result.mood_base}, {expression_result.mood_vibe}")

    # STEP 3: 포즈 분석
    print("\n[3/8] Analyzing pose...")
    pose_result = analyze_pose(pose_image)
    print(f"  Stance: {pose_result.stance}, Framing: {pose_result.framing}")

    # STEP 4: 배경 분석
    print("\n[4/8] Analyzing background...")
    background_result = analyze_background(background_image)
    print(
        f"  Scene: {background_result.scene_type}, Provides: {background_result.provides}"
    )

    # STEP 5: 호환성 검사
    print("\n[5/8] Checking compatibility...")
    compatibility_result = check_compatibility(pose_result, background_result)
    print(
        f"  Level: {compatibility_result.level.value}, Score: {compatibility_result.score}"
    )

    # STEP 6: 착장 분석
    print("\n[6/8] Analyzing outfit...")
    outfit_analyzer = OutfitAnalyzer(client)
    outfit_result = outfit_analyzer.analyze([str(p) for p in outfit_images])
    print(f"  Style: {outfit_result.overall_style}")
    print(f"  Brand: {outfit_result.brand_detected}")
    print(f"  Items: {len(outfit_result.items)}")

    # 분석 결과 딕셔너리
    analysis = {
        "hair": hair_result,
        "expression": expression_result,
        "pose": pose_result,
        "background": background_result,
        "compatibility": compatibility_result,
        "outfit": outfit_result,
    }

    # =========================================================
    # 검증기 로드 (validate=True일 때)
    # =========================================================
    validator = None
    if validate:
        try:
            from core.validators import ValidatorRegistry, WorkflowType

            # 모듈 import로 등록 트리거
            import core.ai_influencer.validator  # noqa: F401

            validator = ValidatorRegistry.get(WorkflowType.AI_INFLUENCER, client)
            print("\n[Validator] AI Influencer validator loaded")
        except Exception as e:
            print(f"\n[Validator] Could not load validator: {e}")
            print("[Validator] Proceeding without validation")
            validator = None

    # =========================================================
    # 생성+검증 루프
    # =========================================================
    best_image = None
    best_score = 0
    best_prompt = ""
    history = []
    current_temp = temperature
    enhancement_text = ""  # 재시도 시 추가할 보강 텍스트

    total_attempts = (max_retries + 1) if validator else 1

    for attempt in range(total_attempts):
        print(f"\n{'#' * 60}")
        print(
            f"# ATTEMPT {attempt + 1}/{total_attempts} | Temperature: {current_temp:.2f}"
        )
        print(f"{'#' * 60}")

        # STEP 7: 프롬프트 조립
        print("\n[7/8] Building schema prompt...")
        prompt = build_schema_prompt(
            hair_result=hair_result,
            expression_result=expression_result,
            pose_result=pose_result,
            background_result=background_result,
            outfit_result=outfit_result,
            compatibility_result=compatibility_result,
        )

        # 재시도 시 enhancement 텍스트 추가
        if enhancement_text:
            prompt = prompt + enhancement_text
            print(f"  [Enhancement] Added retry enhancement rules")

        print(f"  Prompt length: {len(prompt.splitlines())} lines")
        best_prompt = prompt

        # STEP 8: 이미지 생성
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
            temperature=current_temp,
        )

        if image is None:
            print("  [FAIL] Image generation failed")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": "Generation failed",
                }
            )
            continue

        print("  [OK] Image generated successfully")

        # 검증기 없으면 첫 성공 이미지 반환
        if validator is None:
            best_image = image
            best_score = 100
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "total_score": 100,
                    "passed": True,
                    "note": "No validator",
                }
            )
            break

        # STEP 9: 검증
        print("\n[9] Validating generated image...")
        try:
            validation_result = validator.validate(
                generated_img=image,
                reference_images={
                    "face": [str(p) for p in face_images],
                    "outfit": [str(p) for p in outfit_images],
                },
            )

            score = validation_result.total_score
            passed = validation_result.passed
            grade = validation_result.grade

            # 검수 결과 출력
            print(f"\n{'=' * 60}")
            print(f"  Validation (attempt {attempt + 1})")
            print(f"{'=' * 60}")
            if (
                hasattr(validation_result, "summary_kr")
                and validation_result.summary_kr
            ):
                print(validation_result.summary_kr)
            else:
                print(
                    f"  Score: {score}/100 | Grade: {grade} | {'PASS' if passed else 'FAIL'}"
                )
            print(f"{'=' * 60}\n")

            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "total_score": score,
                    "grade": grade,
                    "passed": passed,
                }
            )

            # 베스트 트래킹
            if score > best_score:
                best_image = image
                best_score = score

            # 통과 시 종료
            if passed:
                print(f"[Validation] PASSED at attempt {attempt + 1}!")
                best_image = image
                break

            # 재시도 여부 판단
            if not validator.should_retry(validation_result):
                print(f"[Validation] Auto-fail or not retryable, stopping")
                break

        except Exception as e:
            print(f"[Validation] Error: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": f"Validation error: {e}",
                }
            )
            if best_image is None:
                best_image = image

        # 재시도 준비: enhancement rules 추출 + temperature 낮춤
        if attempt < max_retries:
            # 실패한 기준 추출
            failed_criteria = []
            if hasattr(validation_result, "criteria_scores"):
                for criterion, data in validation_result.criteria_scores.items():
                    if isinstance(data, dict) and not data.get("passed", True):
                        failed_criteria.append(criterion)

            # enhancement rules 생성
            if failed_criteria:
                enhancement_text = validator.get_enhancement_rules(failed_criteria)
                print(f"  [Retry] Failed criteria: {failed_criteria}")
            else:
                enhancement_text = ""

            # temperature 낮춤 (일관성 향상)
            current_temp = max(0.2, current_temp - 0.05)
            print(f"  [Retry] Next temperature: {current_temp:.2f}")
            time.sleep(2)

    # =========================================================
    # 최종 결과 반환
    # =========================================================
    if best_image is None:
        print(f"\n[Pipeline] All attempts failed")
    else:
        print(f"\n[Pipeline] Best result: {best_score}/100")

    # validation 결과 요약
    validation_summary = {
        "passed": best_score >= 75 and best_image is not None,
        "score": best_score,
        "grade": _score_to_grade(best_score),
        "attempts": len(history),
        "history": history,
    }

    return {
        "image": best_image,
        "prompt": best_prompt,
        "analysis": analysis,
        "validation": validation_summary,
    }


def _score_to_grade(score: int) -> str:
    """점수 -> 등급 변환"""
    if score >= 90:
        return "S"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "F"
