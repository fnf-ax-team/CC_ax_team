"""
포즈 변경 이미지 생성 모듈

역할: 소스 이미지 + 목표 포즈 → 포즈 변경 이미지 생성
검증/재시도 로직은 generate_with_validation()에서 처리
"""

import json
import time
from io import BytesIO
from typing import Any, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.api import _get_next_api_key
from .analyzer import analyze_source_for_pose_change, validate_target_pose
from .prompt_builder import build_pose_change_prompt
from .presets import POSE_PRESETS, get_pose_description
from .validator import PoseChangeValidator


# =============================================================================
# 내부 헬퍼
# =============================================================================


def _pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL 이미지를 Gemini API Part로 변환 (크기 제한 포함)."""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _load_image(image: Union[str, Image.Image]) -> Image.Image:
    """경로 또는 PIL Image를 PIL Image로 반환."""
    if isinstance(image, str):
        return Image.open(image)
    return image


def _is_retryable_error(error_str: str) -> bool:
    """API 에러가 재시도 가능한지 판별."""
    return (
        "429" in error_str
        or "rate" in error_str
        or "503" in error_str
        or "overload" in error_str
        or "timeout" in error_str
    )


# =============================================================================
# 순수 생성 함수 (검증 없음)
# =============================================================================


def generate_pose_change(
    source_image: Union[Image.Image, str],
    target_pose: str,
    client: Any,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> Union[Image.Image, None]:
    """포즈 변경 이미지 생성 (검증 없음).

    1. 소스 이미지 분석 (얼굴/착장/배경/체형 제약)
    2. 목표 포즈 물리적 타당성 검증
    3. 프리셋 키 해석 또는 커스텀 설명 그대로 사용
    4. 프롬프트 조립
    5. IMAGE_MODEL로 이미지 생성

    Args:
        source_image: 소스 이미지 (PIL Image 또는 파일 경로)
        target_pose: 프리셋 키 (예: "lean_wall") 또는 커스텀 포즈 설명
        client: Google GenAI client 인스턴스
        temperature: 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 3:4)
        resolution: 해상도 (기본 2K)

    Returns:
        PIL Image (생성 성공) 또는 None (실패)

    Raises:
        ValueError: 물리적으로 불가능한 포즈가 요청된 경우
    """
    pil_source = _load_image(source_image)

    # 1단계: 소스 이미지 분석
    print("[PoseChange] 소스 이미지 분석 중...")
    source_analysis = analyze_source_for_pose_change(pil_source, client)

    # 체형 제약 추출 (물리 검증에 사용)
    physical_constraints = source_analysis.get("physical_constraints", {})
    body_type = source_analysis.get("preserve_elements", {}).get("body_type", {})
    body_constraints_text = (
        f"ground_type: {physical_constraints.get('ground_type', 'flat floor')}, "
        f"space: {physical_constraints.get('space_available', 'indoor')}, "
        f"build: {body_type.get('build', 'slim')}"
    )

    # 2단계: 목표 포즈 물리적 타당성 검증
    pose_description = get_pose_description(target_pose)
    print(f"[PoseChange] 포즈 타당성 검증: {pose_description}")
    is_valid, reason = validate_target_pose(
        pose_description, body_constraints_text, client
    )

    if not is_valid:
        raise ValueError(f"포즈 불가능: {reason}")

    if reason and reason != "검증 완료":
        print(f"[PoseChange] 포즈 검증 경고: {reason}")

    # 3~4단계: 프롬프트 조립
    prompt_text = build_pose_change_prompt(source_analysis, pose_description)

    # 5단계: IMAGE_MODEL로 이미지 생성
    parts = [
        types.Part(text="[SOURCE IMAGE - REFERENCE FOR PRESERVATION]"),
        _pil_to_part(pil_source),
        types.Part(text=prompt_text),
    ]

    # API 에러 재시도 (최대 3회)
    api_max_retries = 3
    for attempt in range(api_max_retries):
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

            print("[PoseChange] 응답에 이미지 없음")
            return None

        except Exception as e:
            error_str = str(e).lower()

            if not _is_retryable_error(error_str):
                print(f"[PoseChange] 재시도 불가 에러: {e}")
                return None

            if attempt < api_max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[PoseChange] API 재시도 {attempt + 1}/{api_max_retries} "
                    f"- {wait_time}초 대기"
                )
                time.sleep(wait_time)
            else:
                print(f"[PoseChange] 최대 재시도 초과: {e}")

    return None


# =============================================================================
# 검증 포함 생성 함수 (공개 API)
# =============================================================================


def generate_with_validation(
    source_image: Union[Image.Image, str],
    target_pose: str,
    client: Any = None,
    api_key: str = None,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """포즈 변경 이미지 생성 + 검증 루프 (공개 API).

    흐름:
    1. 포즈 물리적 불가능 여부 사전 검사 → 불가능 시 early return
    2. generate_pose_change() 호출 → 이미지 생성
    3. PoseChangeValidator.validate() 호출 → 검수
    4. 통과 기준(총점 >= 88) 미달 시 프롬프트 강화 후 재생성 (최대 max_retries회)

    Temperature 시퀀스: 0.2 → 0.15 → 0.1

    Args:
        source_image: 소스 이미지 (PIL Image 또는 파일 경로)
        target_pose: 프리셋 키 또는 커스텀 포즈 설명
        client: Google GenAI client 인스턴스 (api_key와 택 1)
        api_key: Gemini API 키 (client 없을 때 사용)
        max_retries: 최대 재시도 횟수 (기본 2, CLAUDE.md 필수)
        temperature: 초기 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 3:4)
        resolution: 해상도 (기본 2K)

    Returns:
        dict:
            - image (PIL.Image | None): 생성된 이미지
            - score (int): 총점 (0~100)
            - passed (bool): 검수 통과 여부
            - criteria (dict): 항목별 점수
            - history (list): 시도별 기록
            - error (str | None): 에러 메시지 (포즈 불가능 등)
            - summary_kr (str): 한국어 검수 결과 요약
    """
    # client / api_key 해결
    if client is None:
        if api_key is None:
            api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    # Temperature 시퀀스
    temperature_schedule = [0.2, 0.15, 0.1]

    # ------------------------------------------------------------------
    # 사전 검사: 포즈 물리적 타당성 (소스 분석 전 키워드 기반)
    # ------------------------------------------------------------------
    pose_description = get_pose_description(target_pose)

    # 키워드 기반 1차 검사만 수행 (소스 분석 비용 절약)
    # validate_target_pose는 소스 분석 이후 generate_pose_change 내부에서 재수행됨
    from .analyzer import _IMPOSSIBLE_POSE_KEYWORDS

    pose_lower = pose_description.lower()
    for keyword in _IMPOSSIBLE_POSE_KEYWORDS:
        if keyword in pose_lower:
            return {
                "image": None,
                "score": 0,
                "passed": False,
                "criteria": {},
                "history": [],
                "error": f"물리적으로 불가능한 포즈: '{keyword}' 감지. 다른 포즈를 선택해주세요.",
                "summary_kr": f"포즈 사전 검사 실패: {keyword}",
            }

    # ------------------------------------------------------------------
    # 소스 이미지 분석 (한 번만 수행 — 재시도 시 재사용)
    # ------------------------------------------------------------------
    pil_source = _load_image(source_image)
    print("[PoseChange] 소스 이미지 분석 중 (검증 루프)...")

    try:
        source_analysis = analyze_source_for_pose_change(pil_source, client)
    except Exception as e:
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "history": [],
            "error": f"소스 이미지 분석 실패: {e}",
            "summary_kr": "소스 분석 실패",
        }

    # VLM 기반 포즈 타당성 검증 (체형 제약 포함)
    physical_constraints = source_analysis.get("physical_constraints", {})
    body_type = source_analysis.get("preserve_elements", {}).get("body_type", {})
    body_constraints_text = (
        f"ground_type: {physical_constraints.get('ground_type', 'flat floor')}, "
        f"space: {physical_constraints.get('space_available', 'indoor')}, "
        f"build: {body_type.get('build', 'slim')}"
    )

    try:
        is_valid, reason = validate_target_pose(
            pose_description, body_constraints_text, client
        )
    except Exception as e:
        is_valid, reason = True, f"VLM 검증 불가: {e}"

    if not is_valid:
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "history": [],
            "error": f"포즈 불가능: {reason}",
            "summary_kr": f"포즈 검증 실패: {reason}",
        }

    # ------------------------------------------------------------------
    # 검증기 초기화
    # ------------------------------------------------------------------
    validator = PoseChangeValidator(client)

    # ------------------------------------------------------------------
    # 생성 → 검수 → 재생성 루프
    # ------------------------------------------------------------------
    history = []
    best_image = None
    best_score = 0
    best_result = None
    enhancement_additions = ""  # 재시도 시 추가할 강화 규칙

    total_attempts = max_retries + 1  # 초기 1회 + 재시도

    for attempt in range(total_attempts):
        # Temperature 결정 (시퀀스 범위 초과 시 마지막 값 사용)
        temp_idx = min(attempt, len(temperature_schedule) - 1)
        current_temp = temperature_schedule[temp_idx]

        print(
            f"[PoseChange] 생성 시도 {attempt + 1}/{total_attempts} "
            f"(temperature={current_temp})"
        )

        # 프롬프트 조립 (강화 규칙 추가)
        base_prompt = build_pose_change_prompt(source_analysis, pose_description)
        if enhancement_additions:
            prompt_text = (
                base_prompt + f"\n\n[RETRY ENHANCEMENTS]\n{enhancement_additions}"
            )
        else:
            prompt_text = base_prompt

        # 이미지 생성 (API 에러 재시도 포함)
        parts = [
            types.Part(text="[SOURCE IMAGE - REFERENCE FOR PRESERVATION]"),
            _pil_to_part(pil_source),
            types.Part(text=prompt_text),
        ]

        generated_img = None
        api_max_retries = 3
        for api_attempt in range(api_max_retries):
            try:
                response = client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        temperature=current_temp,
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=resolution,
                        ),
                    ),
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        generated_img = Image.open(BytesIO(part.inline_data.data))
                        break
                if generated_img is not None:
                    break
                print("[PoseChange] 응답에 이미지 없음")
                break

            except Exception as e:
                error_str = str(e).lower()
                if not _is_retryable_error(error_str):
                    print(f"[PoseChange] 재시도 불가 API 에러: {e}")
                    break
                if api_attempt < api_max_retries - 1:
                    wait_time = (api_attempt + 1) * 5
                    print(
                        f"[PoseChange] API 재시도 {api_attempt + 1}/{api_max_retries} "
                        f"- {wait_time}초 대기"
                    )
                    time.sleep(wait_time)
                else:
                    print(f"[PoseChange] API 최대 재시도 초과: {e}")

        if generated_img is None:
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "score": 0,
                    "passed": False,
                    "error": "이미지 생성 실패",
                }
            )
            continue

        # 검수
        try:
            validation_result = validator.validate(
                generated_img=generated_img,
                reference_images={"source": [pil_source]},
                target_pose=pose_description,
            )
        except Exception as e:
            print(f"[PoseChange] 검수 실패: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "score": 0,
                    "passed": False,
                    "error": f"검수 실패: {e}",
                }
            )
            # 검수 자체가 실패하면 이미지를 최선으로 보관
            if best_image is None:
                best_image = generated_img
            continue

        score = validation_result.total_score
        passed = validation_result.passed

        history.append(
            {
                "attempt": attempt + 1,
                "temperature": current_temp,
                "score": score,
                "passed": passed,
                "criteria": validation_result.criteria_scores,
                "auto_fail": validation_result.auto_fail,
            }
        )

        print(
            f"[PoseChange] 검수 결과: {score}점 | "
            f"{'통과' if passed else '탈락'} | "
            f"등급: {validation_result.grade}"
        )
        print(validation_result.summary_kr)

        # 최고 점수 업데이트
        if score > best_score:
            best_score = score
            best_image = generated_img
            best_result = validation_result

        if passed:
            print(f"[PoseChange] 검수 통과! (시도 {attempt + 1})")
            return {
                "image": generated_img,
                "score": score,
                "passed": True,
                "criteria": validation_result.criteria_scores,
                "history": history,
                "error": None,
                "summary_kr": validation_result.summary_kr,
            }

        # 마지막 시도이면 루프 종료
        if attempt >= total_attempts - 1:
            break

        # 재시도 전 프롬프트 강화 규칙 생성
        failed_criteria = [
            k
            for k, v in validation_result.criteria_scores.items()
            if v < validator.config.auto_fail_thresholds.get(k, 85)
        ]
        if failed_criteria:
            enhancement_additions = validator.get_enhancement_rules(failed_criteria)
            print(f"[PoseChange] 강화 규칙 적용: {failed_criteria}")

        # 재시도 전 짧은 대기
        time.sleep(2)

    # ------------------------------------------------------------------
    # 최대 재시도 도달 — 최고 점수 이미지 반환
    # ------------------------------------------------------------------
    summary_kr = best_result.summary_kr if best_result else "검수 결과 없음"
    print(
        f"[PoseChange] 최대 재시도 도달. 최고 점수: {best_score}점 "
        f"({'통과' if best_score >= 88 else '미달'})"
    )

    return {
        "image": best_image,
        "score": best_score,
        "passed": False,
        "criteria": best_result.criteria_scores if best_result else {},
        "history": history,
        "error": None,
        "summary_kr": summary_kr,
    }
