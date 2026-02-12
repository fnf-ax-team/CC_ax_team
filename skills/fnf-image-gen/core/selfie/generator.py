"""
셀피/인플루언서 이미지 생성 모듈

이미지 생성 및 검증 기능 제공
- generate_selfie: 단일 이미지 생성
- generate_with_validation: 생성 + 검증 루프
"""

import time
from io import BytesIO
from typing import Optional, List, Union
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """
    PIL Image를 Gemini Part로 변환

    Args:
        img: PIL Image 객체
        max_size: 최대 크기 (기본 1024px)

    Returns:
        types.Part: Gemini API에 전달 가능한 Part 객체
    """
    # 크기 조정 (필요 시)
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    # PNG로 변환하여 BytesIO에 저장
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # Gemini Part 객체 생성
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def generate_selfie(
    prompt: str,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> Optional[Image.Image]:
    """
    셀피/인플루언서 스타일 이미지 생성

    Args:
        prompt: 프롬프트 문자열 (build_selfie_prompt 결과)
        face_images: 얼굴 이미지 목록 (필수)
        outfit_images: 착장 이미지 목록 (선택)
        aspect_ratio: 화면 비율 (기본 9:16 - 스토리/릴스용)
        resolution: 해상도 (1K/2K/4K)
        temperature: 생성 온도 (기본 0.7 - 브랜드컷보다 높음)
        api_key: Gemini API 키 (None이면 get_next_api_key 사용)

    Returns:
        PIL.Image: 생성된 이미지 (실패 시 None)
    """
    # API 키 처리
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # API 파트 구성
    parts = [types.Part(text=prompt)]

    # 얼굴 이미지 전송 (필수)
    for i, img_input in enumerate(face_images):
        # 이미지 로드
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(text=f"[FACE REFERENCE {i+1}] - 이 얼굴을 정확히 복사하세요:")
        )
        parts.append(pil_to_part(img))

    # 착장 이미지 전송 (선택적)
    if outfit_images:
        for i, img_input in enumerate(outfit_images):
            # 이미지 로드
            if isinstance(img_input, (str, Path)):
                img = Image.open(img_input).convert("RGB")
            else:
                img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

            parts.append(
                types.Part(text=f"[OUTFIT REFERENCE {i+1}] - 이 착장을 참고하세요:")
            )
            parts.append(pil_to_part(img))

    # CLAUDE.md 규칙: 최대 3회 재시도, (attempt + 1) * 5초 대기
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            # API 호출
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio, image_size=resolution
                    ),
                ),
            )

            # 이미지 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            print("[SelfieGenerator] API 응답에 이미지 없음")
            return None

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # 재시도 가능 에러 판별
            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            # 재시도 불가능한 에러는 즉시 종료
            if not is_retryable:
                if "safety" in error_str or "blocked" in error_str:
                    print(f"[SelfieGenerator] Safety Block: {e}")
                elif "401" in error_str or "auth" in error_str:
                    print(f"[SelfieGenerator] Auth Error: {e}")
                else:
                    print(f"[SelfieGenerator] 생성 실패: {e}")
                return None

            # 재시도 가능하면 대기 후 재시도
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[SelfieGenerator] Retry {attempt + 1}/{max_retries} "
                    f"({error_str[:50]}...) - {wait_time}초 대기"
                )
                time.sleep(wait_time)
            else:
                print(f"[SelfieGenerator] 최대 재시도 횟수 초과: {e}")

    return None


def generate_with_validation(
    prompt: str,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    initial_temperature: float = 0.7,
    validator=None,  # SelfieValidator 인스턴스 (별도 태스크에서 구현)
) -> dict:
    """
    생성 + 검증 + 재생성 루프

    validator가 None이면 검증 없이 단순 생성만 수행.
    SelfieValidator 구현 후 연동 예정.

    Args:
        prompt: 프롬프트 문자열
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록 (선택)
        api_key: Gemini API 키
        max_retries: 최대 재시도 횟수 (기본 2)
        aspect_ratio: 화면 비율
        resolution: 해상도
        initial_temperature: 초기 온도 (기본 0.7)
        validator: SelfieValidator 인스턴스 (None이면 검증 생략)

    Returns:
        dict: {
            "image": PIL.Image,       # 생성된 이미지
            "score": float,            # 총점 (0-100) - validator 없으면 0
            "passed": bool,            # 통과 여부 - validator 없으면 True
            "attempts": int,           # 시도 횟수
            "history": List[dict]      # 시도 이력
        }
    """
    # API 키 처리
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    best_image = None
    best_score = 0
    history = []

    current_temp = initial_temperature

    for attempt in range(max_retries + 1):
        print(f"\n{'#' * 60}")
        print(
            f"# ATTEMPT {attempt + 1}/{max_retries + 1} | Temperature: {current_temp:.2f}"
        )
        print(f"{'#' * 60}")

        # 1. 이미지 생성
        image = generate_selfie(
            prompt=prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=current_temp,
            api_key=api_key,
        )

        if image is None:
            print(f"[Validation] 생성 실패 (attempt {attempt + 1})")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": "Generation failed",
                }
            )
            continue

        # 2. 검증 (validator 있으면)
        if validator is not None:
            try:
                validation_result = validator.validate(
                    generated_img=image,
                    face_images=face_images,
                )
                score = validation_result.get("total_score", 0)
                passed = validation_result.get("passed", False)

                print(
                    f"[Validation] Score: {score}/100 | "
                    f"{'PASS' if passed else 'FAIL'}"
                )

                history.append(
                    {
                        "attempt": attempt + 1,
                        "temperature": current_temp,
                        "total_score": score,
                        "passed": passed,
                    }
                )

                if score > best_score:
                    best_image = image
                    best_score = score
                    print(f"[Validation] New best score: {best_score}")

                if passed:
                    print(f"[Validation] PASSED at attempt {attempt + 1}!")
                    break

            except Exception as e:
                print(f"[Validation] 검증 실패: {e}")
                history.append(
                    {
                        "attempt": attempt + 1,
                        "temperature": current_temp,
                        "error": f"Validation error: {e}",
                    }
                )
                # 검증 실패해도 이미지는 저장
                if best_image is None:
                    best_image = image

        else:
            # validator 없으면 첫 성공 이미지 반환
            best_image = image
            best_score = 100  # 검증 없으므로 만점 처리
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "total_score": 100,
                    "passed": True,
                    "note": "No validator provided",
                }
            )
            print(f"[Validation] 검증 생략 - 이미지 생성 성공")
            break

        # 3. 재시도 준비 (온도 낮추기)
        if attempt < max_retries:
            current_temp = max(0.3, current_temp - 0.1)
            time.sleep(2)  # Rate limit 방지

    # 최종 결과 반환
    if best_image is None:
        print(f"\n[Validation] 모든 시도 실패")
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "attempts": max_retries + 1,
            "history": history,
        }

    print(f"\n[Validation] Best result: {best_score}/100")

    return {
        "image": best_image,
        "score": best_score,
        "passed": best_score >= 80 or validator is None,
        "attempts": len(history),
        "history": history,
    }
