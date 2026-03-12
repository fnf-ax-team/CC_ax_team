"""
이커머스 이미지 생성 모듈

generate_ecommerce_image(): 순수 생성 (검증 없음)
generate_with_validation(): 생성 + 검증 + 재생성 루프 (공개 API)

브랜드컷 대비 차이점:
- 중립 배경(white/gray/minimal) 필수 — 브랜드 특화 배경 금지
- 착장 정확도(40%) 최우선 — 상품 정확도가 브랜드 무드보다 중요
- 얼굴 동일성 기준 완화 (>= 70, 브랜드컷보다 낮음)
"""

import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from .analyzer import analyze_outfit_for_ecommerce, analyze_face_for_model
from .prompt_builder import build_ecommerce_prompt
from .presets import POSE_PRESETS, BACKGROUND_PRESETS, VALID_ECOMMERCE_BACKGROUNDS
from .validator import EcommerceValidator


# ------------------------------------------------------------------
# 내부 헬퍼
# ------------------------------------------------------------------


def _load_pil(image: "Image.Image | str | Path") -> "Image.Image | None":
    """PIL Image 또는 경로(str/Path)를 PIL Image로 변환."""
    if isinstance(image, (str, Path)):
        try:
            return Image.open(image).convert("RGB")
        except Exception as e:
            print(f"[EcommerceGenerator] 이미지 로드 실패: {image} -> {e}")
            return None
    return image.convert("RGB") if image.mode != "RGB" else image


def _pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini API Part로 변환. 필요 시 리사이즈."""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _validate_background(background: str) -> str:
    """배경 키가 이커머스 유효 목록에 있는지 검증.

    유효하지 않으면 경고 후 white_studio 반환.
    """
    if background in VALID_ECOMMERCE_BACKGROUNDS:
        return background
    print(
        f"[EcommerceGenerator] 경고: '{background}'는 유효하지 않은 이커머스 배경입니다. "
        f"허용 배경: {VALID_ECOMMERCE_BACKGROUNDS}. white_studio로 폴백."
    )
    return "white_studio"


def _get_client(client: Any | None, api_key: str | None) -> Any:
    """클라이언트 또는 api_key로 genai.Client 반환.

    client가 제공되면 그대로 사용, 아니면 api_key로 생성.
    둘 다 없으면 core.api._get_next_api_key()로 자동 조회.
    """
    if client is not None:
        return client
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()
    return genai.Client(api_key=api_key)


def _build_generation_parts(
    prompt_text: str,
    face_images: "list[Image.Image | str]",
    outfit_images: "list[Image.Image | str]",
    pose: str,
    background: str,
) -> list:
    """API 파트 목록 구성.

    전송 순서:
    1. 프롬프트 텍스트 (착장 분석 결과 포함)
    2. 얼굴 이미지
    3. 착장 이미지
    """
    parts = []

    # 1. 프롬프트 텍스트 (착장 정확도 강조 포함)
    ecommerce_header = (
        "## 이커머스 모델 이미지 생성\n\n"
        "착장 정확도가 최우선입니다 — 색상, 로고, 디테일을 참조 이미지와 완벽히 일치시키세요.\n"
        f"포즈: {pose} | 배경: {background}\n\n"
    )
    parts.append(types.Part(text=ecommerce_header + prompt_text))

    # 2. 얼굴 이미지
    face_pils = [_load_pil(img) for img in face_images]
    for i, img in enumerate(face_pils):
        if img is None:
            continue
        parts.append(
            types.Part(
                text=(
                    f"[FACE REFERENCE {i+1}] - 이 얼굴과 동일한 인물이어야 합니다:\n"
                    f"- 이목구비(눈, 코, 입, 턱선, 광대뼈) 정확히 재현\n"
                    f"- 피부톤, 얼굴형 동일하게 유지\n"
                    f"- 고유 특징(점, 보조개, 눈 모양 등) 보존 필수\n"
                    f"- 다른 사람이 되면 안 됨 — same person identity 필수\n"
                    f"- AI 플라스틱 피부 금지 — 자연스러운 피부 텍스처 유지:"
                )
            )
        )
        parts.append(_pil_to_part(img))

    # 3. 착장 이미지 (최우선 비교 대상 - 강조)
    outfit_pils = [_load_pil(img) for img in outfit_images]
    parts.append(
        types.Part(
            text=(
                "[OUTFIT REFERENCE - 최우선!] 아래 착장 이미지의 모든 요소를 정확히 재현하세요:\n"
                "- 색상: 참조 이미지와 pixel-perfect 일치\n"
                "- 로고/그래픽: 위치, 크기, 내용 완벽 보존\n"
                "- 디테일: 소재감, 핏, 실루엣 유지\n"
                "- 레이어링: 누락 없이 모든 아이템 포함"
            )
        )
    )
    for i, img in enumerate(outfit_pils):
        if img is None:
            continue
        parts.append(
            types.Part(
                text=f"[OUTFIT REFERENCE {i+1}] - 모든 디테일을 참조하세요 (최우선 비교 대상):"
            )
        )
        parts.append(_pil_to_part(img))

    return parts


# ------------------------------------------------------------------
# 공개 API
# ------------------------------------------------------------------


def generate_ecommerce_image(
    face_images: "list[Image.Image | str]",
    outfit_images: "list[Image.Image | str]",
    client: Any,
    pose: str = "front_standing",
    background: str = "white_studio",
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> "Image.Image | None":
    """이커머스 모델 이미지 생성 (검증 없음).

    단계:
    1. 착장 분석 (VLM) — 상업적 디스플레이 관점
    2. 얼굴 분석 (VLM) — 피부톤·이목구비 추출
    3. 프롬프트 조립 (포즈/배경 프리셋 적용)
    4. IMAGE_MODEL로 이미지 생성

    브랜드컷 대비 차이점:
    - 중립 배경만 허용 (white/gray/minimal studio)
    - 상업적 초점 — 착장 정확도 최우선 (40%)
    - 얼굴 동일성 기준 완화 (>= 70)

    Args:
        face_images: 얼굴 이미지 리스트 (PIL.Image 또는 경로)
        outfit_images: 착장 이미지 리스트 (PIL.Image 또는 경로)
        client: Google GenAI 클라이언트
        pose: POSE_PRESETS 키 (front_standing, front_casual, side_profile, back_view, detail_closeup)
        background: BACKGROUND_PRESETS 키 (white_studio, gray_studio, minimal_indoor, outdoor_urban)
        temperature: 생성 온도 (기본 0.2 — 상업적 재현성 우선)
        aspect_ratio: 화면 비율 (기본 3:4)
        resolution: 해상도 (1K/2K/4K)

    Returns:
        PIL.Image (성공) 또는 None (실패)
    """
    # 배경 유효성 검증
    background = _validate_background(background)

    # 1. 착장 분석
    print("[EcommerceGenerator] 착장 분석 중...")
    outfit_analysis = analyze_outfit_for_ecommerce(outfit_images, client)

    # 2. 얼굴 분석
    print("[EcommerceGenerator] 얼굴 분석 중...")
    face_analysis = analyze_face_for_model(face_images, client)

    # 3. 프롬프트 조립
    print(f"[EcommerceGenerator] 프롬프트 조립 중... (pose={pose}, bg={background})")
    prompt_text = build_ecommerce_prompt(
        outfit_analysis=outfit_analysis,
        face_analysis=face_analysis,
        pose=pose,
        background=background,
    )

    # 4. API 파트 구성
    parts = _build_generation_parts(
        prompt_text=prompt_text,
        face_images=face_images,
        outfit_images=outfit_images,
        pose=pose,
        background=background,
    )

    # 5. 이미지 생성 (최대 3회 재시도 — API 에러 전용)
    max_api_retries = 3
    for attempt in range(max_api_retries):
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
                    print("[EcommerceGenerator] 이미지 생성 완료")
                    return Image.open(BytesIO(part.inline_data.data))

            print("[EcommerceGenerator] 응답에 이미지 없음")
            return None

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            if not is_retryable:
                print(f"[EcommerceGenerator] 재시도 불가 에러: {e}")
                return None

            if attempt < max_api_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[EcommerceGenerator] API 재시도 {attempt + 1}/{max_api_retries} "
                    f"- {wait_time}초 대기"
                )
                time.sleep(wait_time)
            else:
                print(f"[EcommerceGenerator] 최대 재시도 초과: {e}")

    return None


def _generate_batch_with_validation(
    face_images: "list[Image.Image | str]",
    outfit_images: "list[Image.Image | str]",
    poses: "list[str]",
    background: str,
    num_images: int,
    client: Any | None = None,
    api_key: str | None = None,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """여러 이미지 생성 + 검증 (배치 모드).

    각 이미지를 순차적으로 생성하고 검증합니다.
    Rate limit 방지를 위해 이미지 간 1초 대기.

    Args:
        face_images: 얼굴 이미지 리스트
        outfit_images: 착장 이미지 리스트
        poses: 포즈 프리셋 리스트 (순환 적용)
        background: 배경 프리셋
        num_images: 생성할 이미지 수
        client: GenAI 클라이언트
        api_key: API 키 (client 없을 때 사용)
        max_retries: 이미지당 최대 재시도 횟수
        temperature: 생성 온도
        aspect_ratio: 화면 비율
        resolution: 해상도

    Returns:
        dict:
            - images (list[PIL.Image | None]): 생성된 이미지 리스트
            - results (list[dict]): 각 이미지별 검증 결과
            - pass_count (int): 검수 통과 이미지 수
            - total_count (int): 총 생성 이미지 수
    """
    results = []
    images = []

    print(f"\n[EcommerceGenerator] 배치 모드: {num_images}장 생성 시작")
    print(f"  포즈: {poses[:min(5, len(poses))]}{'...' if len(poses) > 5 else ''}")
    print(f"  배경: {background}")

    for i in range(num_images):
        # 포즈 순환 적용
        current_pose = poses[i % len(poses)]

        print(
            f"\n[EcommerceGenerator] === 이미지 {i + 1}/{num_images} (pose={current_pose}) ==="
        )

        # 단일 이미지 생성 (재귀 호출 방지: num_images=1 고정)
        result = generate_with_validation(
            face_images=face_images,
            outfit_images=outfit_images,
            client=client,
            api_key=api_key,
            pose=current_pose,
            background=background,
            num_images=1,  # 재귀 방지
            max_retries=max_retries,
            temperature=temperature,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

        results.append(result)
        images.append(result.get("image"))

        # Rate limit 방지 (마지막 이미지 제외)
        if i < num_images - 1:
            print("[EcommerceGenerator] Rate limit 방지 1초 대기...")
            time.sleep(1)

    pass_count = sum(1 for r in results if r.get("passed"))
    print(f"\n[EcommerceGenerator] 배치 완료: {pass_count}/{num_images} 통과")

    return {
        "images": images,
        "results": results,
        "pass_count": pass_count,
        "total_count": num_images,
    }


def generate_with_validation(
    face_images: "list[Image.Image | str]",
    outfit_images: "list[Image.Image | str]",
    client: Any | None = None,
    api_key: str | None = None,
    pose: "Union[str, list[str]]" = "front_standing",
    background: str = "white_studio",
    num_images: int = 1,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """이커머스 이미지 생성 + 검증 루프 (공개 API).

    흐름:
    1. generate_ecommerce_image() 호출 → 이미지 생성
    2. EcommerceValidator.validate() 호출 → 검수
    3. 실패 시 → 실패 기준별 프롬프트 강화 규칙 적용 → 재생성

    Pass 조건:
    - total_score >= 85
    - background_compliance >= 90 (중립 배경 필수)
    - outfit_accuracy >= 85, face_identity >= 70,
      pose_correctness >= 80, commercial_quality >= 85

    Args:
        face_images: 얼굴 이미지 리스트 (PIL.Image 또는 경로)
        outfit_images: 착장 이미지 리스트 (PIL.Image 또는 경로)
        client: Google GenAI 클라이언트 (없으면 api_key 또는 자동 조회)
        api_key: Gemini API 키 (client 없을 때 사용)
        pose: POSE_PRESETS 키 (단일 str 또는 list[str])
        background: BACKGROUND_PRESETS 키 (VALID_ECOMMERCE_BACKGROUNDS 에 있어야 함)
        num_images: 생성할 이미지 수 (기본 1, 1 초과 시 배치 모드)
        max_retries: 최대 재생성 횟수 (기본 2, 품질 보장을 위해 0 금지)
        temperature: 초기 생성 온도
        aspect_ratio: 화면 비율
        resolution: 해상도

    Returns:
        num_images == 1:
            dict:
                - image (PIL.Image | None): 최종 이미지
                - passed (bool): 검수 통과 여부
                - score (int): 최종 총점
                - grade (str): 최종 등급 (S/A/B/C/F)
                - criteria (dict): 기준별 점수
                - history (list[dict]): 시도별 검수 결과 이력
                - attempts (int): 실제 시도 횟수

        num_images > 1:
            dict:
                - images (list[PIL.Image | None]): 생성된 이미지 리스트
                - results (list[dict]): 각 이미지별 검증 결과
                - pass_count (int): 검수 통과 이미지 수
                - total_count (int): 총 생성 이미지 수
    """
    # 수량 제한 (1~10장)
    if num_images < 1:
        num_images = 1
    elif num_images > 10:
        print(
            f"[EcommerceGenerator] 경고: 최대 10장까지 가능합니다. {num_images} -> 10으로 제한"
        )
        num_images = 10

    # 배치 모드 (num_images > 1)
    if num_images > 1:
        # pose가 리스트면 그대로, 아니면 동일 포즈로 채움
        poses = pose if isinstance(pose, list) else [pose] * num_images
        return _generate_batch_with_validation(
            face_images=face_images,
            outfit_images=outfit_images,
            poses=poses,
            background=background,
            num_images=num_images,
            client=client,
            api_key=api_key,
            max_retries=max_retries,
            temperature=temperature,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

    # 단일 모드 (기존 로직)
    # pose가 리스트면 첫 번째 사용
    if isinstance(pose, list):
        pose = pose[0] if pose else "front_standing"

    if max_retries < 1:
        raise ValueError(
            "[EcommerceGenerator] max_retries는 최소 1 이상이어야 합니다. "
            "검수 없이 저장하면 품질 보장 불가. (CLAUDE.md 규칙)"
        )

    # 배경 유효성 검증
    background = _validate_background(background)

    # 클라이언트 초기화
    gen_client = _get_client(client, api_key)

    # 검증기 초기화
    validator = EcommerceValidator(client=gen_client)

    history = []
    best_result = None
    best_image = None
    current_temperature = temperature

    # 착장/얼굴 분석은 루프 밖에서 1회만 수행 (비용 절감)
    print("[EcommerceGenerator] 착장 분석 중...")
    outfit_analysis = analyze_outfit_for_ecommerce(outfit_images, gen_client)
    print("[EcommerceGenerator] 얼굴 분석 중...")
    face_analysis = analyze_face_for_model(face_images, gen_client)

    # 프롬프트 조립 (재생성 시 강화 규칙 추가를 위해 분리)
    base_prompt = build_ecommerce_prompt(
        outfit_analysis=outfit_analysis,
        face_analysis=face_analysis,
        pose=pose,
        background=background,
    )

    current_prompt = base_prompt
    enhancement_suffix = ""

    for attempt in range(max_retries + 1):
        print(
            f"\n[EcommerceGenerator] 생성 시도 {attempt + 1}/{max_retries + 1} "
            f"(temperature={current_temperature:.2f})"
        )

        # API 파트 구성 (강화 규칙 포함)
        combined_prompt = current_prompt
        if enhancement_suffix:
            combined_prompt = (
                "## [재생성] 이전 검수 실패 — 아래 강화 규칙을 반드시 적용하세요:\n\n"
                + enhancement_suffix
                + "\n\n---\n\n"
                + current_prompt
            )

        parts = _build_generation_parts(
            prompt_text=combined_prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose=pose,
            background=background,
        )

        # 이미지 생성 (API 에러 재시도 포함)
        generated_image = None
        max_api_retries = 3
        for api_attempt in range(max_api_retries):
            try:
                response = gen_client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        temperature=current_temperature,
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=resolution,
                        ),
                    ),
                )

                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        generated_image = Image.open(BytesIO(part.inline_data.data))
                        break

                if generated_image is not None:
                    break

                print("[EcommerceGenerator] 응답에 이미지 없음")
                break

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = (
                    "429" in error_str
                    or "rate" in error_str
                    or "503" in error_str
                    or "overload" in error_str
                    or "timeout" in error_str
                )

                if not is_retryable:
                    print(f"[EcommerceGenerator] 재시도 불가 에러: {e}")
                    break

                if api_attempt < max_api_retries - 1:
                    wait_time = (api_attempt + 1) * 5
                    print(
                        f"[EcommerceGenerator] API 재시도 {api_attempt + 1}/{max_api_retries} "
                        f"- {wait_time}초 대기"
                    )
                    time.sleep(wait_time)
                else:
                    print(f"[EcommerceGenerator] API 최대 재시도 초과: {e}")

        if generated_image is None:
            attempt_record = {
                "attempt": attempt + 1,
                "passed": False,
                "score": 0,
                "grade": "F",
                "criteria": {},
                "error": "이미지 생성 실패",
            }
            history.append(attempt_record)
            if attempt < max_retries:
                print("[EcommerceGenerator] 이미지 생성 실패 — 재시도")
                current_temperature = max(0.05, current_temperature - 0.05)
            continue

        # 검수 수행
        print(f"[EcommerceGenerator] 검수 중... (시도 {attempt + 1})")
        validation_result = validator.validate(
            generated_img=generated_image,
            reference_images={
                "face": list(face_images),
                "outfit": list(outfit_images),
            },
            pose_preset=pose,
            background_preset=background,
        )

        attempt_record = {
            "attempt": attempt + 1,
            "passed": validation_result.passed,
            "score": validation_result.total_score,
            "grade": validation_result.grade,
            "criteria": validation_result.criteria_scores,
            "summary_kr": validation_result.summary_kr,
        }
        history.append(attempt_record)

        print(
            f"[EcommerceGenerator] 검수 결과: {validation_result.grade}등급 "
            f"{validation_result.total_score}점 | "
            f"통과={'예' if validation_result.passed else '아니오'}"
        )

        # 최고 점수 이미지 추적
        if (
            best_result is None
            or validation_result.total_score > best_result.total_score
        ):
            best_result = validation_result
            best_image = generated_image

        if validation_result.passed:
            print("[EcommerceGenerator] 검수 통과!")
            break

        # 재시도 준비 — 실패 기준별 강화 규칙 생성
        if attempt < max_retries:
            failed_criteria = [
                k
                for k, v in validation_result.criteria_scores.items()
                if v < validator.PASS_THRESHOLDS.get(k, 85)
            ]
            if validation_result.auto_fail:
                # Auto-Fail: 해당 기준 강화 규칙 최우선 적용
                for reason in validation_result.auto_fail_reasons:
                    print(f"[EcommerceGenerator] Auto-Fail: {reason}")

            enhancement_suffix = validator.get_enhancement_rules(failed_criteria)
            print(
                f"[EcommerceGenerator] 실패 기준: {failed_criteria} "
                f"-> 강화 규칙 {len(enhancement_suffix.splitlines())}개 적용"
            )

            # 재생성 시 온도 낮춤 (착장 재현성 향상)
            current_temperature = max(0.05, current_temperature - 0.05)

    # 최종 결과 조립
    if best_result is None:
        return {
            "image": None,
            "passed": False,
            "score": 0,
            "grade": "F",
            "criteria": {},
            "history": history,
            "attempts": len(history),
        }

    print(
        f"\n[EcommerceGenerator] 최종 결과: {best_result.grade}등급 "
        f"{best_result.total_score}점 | 통과={'예' if best_result.passed else '아니오'}"
    )
    if best_result.summary_kr:
        print(best_result.summary_kr)

    return {
        "image": best_image,
        "passed": best_result.passed,
        "score": best_result.total_score,
        "grade": best_result.grade,
        "criteria": best_result.criteria_scores,
        "history": history,
        "attempts": len(history),
    }
