"""
pose_copy 이미지 생성 모듈

핵심 원칙:
- 레퍼런스 이미지 → API에 직접 전달 (포즈/구도 복제를 위해 필수)
- 소스 이미지 → VLM 텍스트 분석만 (포즈 혼동 방지)
"""

import time
from io import BytesIO
from typing import Any, Optional, Union

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from .analyzer import analyze_reference_pose, analyze_source_person
from .prompt_builder import build_pose_copy_prompt
from .validator import PoseCopyValidator

# 통과 기준 (검증기와 동기화)
_PASS_TOTAL = 92

# 온도 스케줄 (재시도 시 낮아짐)
_TEMPERATURE_SCHEDULE = [0.20, 0.15, 0.10]


# ============================================================================
# 유틸리티
# ============================================================================


def _pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buf.getvalue())
    )


def _load_pil(image: Union[Image.Image, str]) -> Image.Image:
    """경로 또는 PIL Image를 PIL Image로 반환"""
    if isinstance(image, str):
        return Image.open(image).convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _get_client(client: Optional[Any], api_key: Optional[str]) -> Any:
    """client 또는 api_key로 Gemini 클라이언트 반환"""
    if client is not None:
        return client
    if api_key is not None:
        return genai.Client(api_key=api_key)
    # 환경 변수에서 API 키 로테이션
    from core.api import _get_next_api_key

    return genai.Client(api_key=_get_next_api_key())


# ============================================================================
# 핵심 생성 함수 (검수 없음)
# ============================================================================


def generate_pose_copy(
    source_image: Union[Image.Image, str],
    reference_image: Union[Image.Image, str],
    client: Any,
    background_mode: str = "reference",
    custom_background: Optional[str] = None,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> Optional[Image.Image]:
    """포즈 복제 이미지 생성 (검수 없음).

    핵심 원칙:
    - 레퍼런스 이미지: API에 직접 전달 (포즈 복제를 위해)
    - 소스 이미지: VLM 텍스트 설명만 사용 (포즈 혼동 방지)

    흐름:
    1. 레퍼런스 포즈 상세 분석 (포즈/구도/배경)
    2. 소스 인물 분석 (얼굴/착장만, 포즈 제외)
    3. 배경 모드에 맞춰 프롬프트 조립
    4. 레퍼런스 이미지 + 프롬프트를 IMAGE_MODEL에 직접 전달

    Args:
        source_image: 소스 인물 이미지 (PIL.Image 또는 파일 경로)
        reference_image: 레퍼런스 이미지 (PIL.Image 또는 파일 경로)
            → API에 직접 전달되어 포즈/구도를 모델이 직접 참조
        client: Google GenAI client instance
        background_mode: 배경 처리 방식
            - "reference": 레퍼런스 이미지 배경 재현 (기본값)
            - "source": 소스 이미지 배경 컨텍스트 사용
            - "custom": custom_background 문자열 사용
        custom_background: background_mode="custom" 시 배경 설명 문자열
        temperature: 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")

    Returns:
        PIL.Image: 생성된 이미지, 실패 시 None
    """
    # 1. 이미지 로드
    ref_pil = _load_pil(reference_image)
    src_pil = _load_pil(source_image)

    # 2. VLM 분석
    print("[PoseCopyGen] 레퍼런스 포즈 분석 중...")
    reference_analysis = analyze_reference_pose(ref_pil, client)

    print("[PoseCopyGen] 소스 인물 분석 중 (얼굴/착장만)...")
    source_analysis = analyze_source_person(src_pil, client)

    # 3. 프롬프트 조립
    prompt = build_pose_copy_prompt(
        reference_analysis=reference_analysis,
        source_analysis=source_analysis,
        background_mode=background_mode,
        custom_background=custom_background,
    )

    # 4. API 파트 구성
    # CRITICAL: 레퍼런스 이미지를 먼저 전달 → 모델이 포즈/구도를 직접 참조
    parts = [
        types.Part(
            text="""[POSE & COMPOSITION REFERENCE] - COPY THIS EXACTLY!

THIS IMAGE IS THE POSE REFERENCE:
- Camera angle must match EXACTLY (low/eye-level/high angle)
- Framing must match EXACTLY (full body/half body/close-up)
- Body pose must match EXACTLY (every limb position)
- Person position in frame must match EXACTLY

Study this reference image carefully before generating:"""
        ),
        _pil_to_part(ref_pil),
        types.Part(
            text="""[REFERENCE NOTED] Now generate with the person described below,
using EXACTLY the same pose, camera angle, framing, and composition as the reference above.

DO NOT change the pose. DO NOT change the camera angle. DO NOT change the framing.
ONLY replace the person's identity (face + outfit) as described below.
"""
        ),
        types.Part(text=prompt),
    ]

    # 5. 생성 (API 에러 재시도 최대 3회)
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
                    return Image.open(BytesIO(part.inline_data.data))

            print("[PoseCopyGen] 응답에 이미지 없음")
            return None

        except Exception as e:
            error_str = str(e).lower()

            # 재시도 가능 에러 판별
            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            if not is_retryable:
                print(f"[PoseCopyGen] 생성 에러 (재시도 불가): {e}")
                return None

            if attempt < max_api_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[PoseCopyGen] API 에러 재시도 {attempt + 1}/{max_api_retries} "
                    f"({wait_time}초 대기): {e}"
                )
                time.sleep(wait_time)
            else:
                print(f"[PoseCopyGen] 최대 재시도 초과: {e}")

    return None


# ============================================================================
# 검수 포함 생성 (공개 API)
# ============================================================================


def generate_with_validation(
    source_image: Union[Image.Image, str],
    reference_image: Union[Image.Image, str],
    client: Optional[Any] = None,
    api_key: Optional[str] = None,
    background_mode: str = "reference",
    custom_background: Optional[str] = None,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """포즈 복제 생성 + 검수 + 재생성 루프 (공개 API).

    흐름:
    1. generate_pose_copy()로 이미지 생성
    2. PoseCopyValidator로 검수
    3. 실패 시 강화 규칙 추가 후 재생성 (최대 max_retries회)

    통과 기준:
    - total_score >= 92 (pose_similarity 50% 가중치 최우선)
    - pose_similarity >= 85, face_preservation >= 90,
      outfit_preservation >= 90, composition_match >= 80

    Args:
        source_image: 소스 인물 이미지 (PIL.Image 또는 파일 경로)
        reference_image: 레퍼런스 이미지 (PIL.Image 또는 파일 경로)
            → API에 직접 전달됨 (포즈 복제 핵심)
        client: Google GenAI client instance (api_key와 택일)
        api_key: Gemini API 키 (client와 택일)
        background_mode: 배경 처리 방식 ("reference"/"source"/"custom")
        custom_background: background_mode="custom" 시 배경 설명 문자열
        max_retries: 최대 재시도 횟수 (기본 2)
        temperature: 초기 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")

    Returns:
        dict: {
            "image": PIL.Image,              # 최고 점수 이미지 (실패 시 None)
            "score": int,                    # 총점 (0~100)
            "passed": bool,                  # 통과 여부
            "criteria": dict,                # 기준별 점수
            "attempts": int,                 # 시도 횟수
            "history": List[dict],           # 시도 이력
            "summary_kr": str,               # 한국어 검수 요약 (표 형식)
        }
    """
    # 클라이언트 준비
    active_client = _get_client(client, api_key)

    # 검증기 초기화
    validator = PoseCopyValidator(active_client)

    # 이미지 로드 (재시도 루프 전에 1회만)
    ref_pil = _load_pil(reference_image)
    src_pil = _load_pil(source_image)

    best_image = None
    best_score = -1
    best_result = None
    history = []

    # 현재 프롬프트 강화 메모 (재시도마다 누적)
    enhancement_notes = ""
    current_temp = temperature

    for attempt in range(max_retries + 1):
        print(f"\n{'=' * 60}")
        print(
            f"[PoseCopyGen] 시도 {attempt + 1}/{max_retries + 1} "
            f"| 온도: {current_temp:.2f}"
        )
        print(f"{'=' * 60}")

        # -------------------------------------------------------
        # 1. 이미지 생성
        # -------------------------------------------------------
        # 강화 노트가 있으면 custom_background에 추가하거나
        # 별도 파트로 전달 (여기서는 generate_pose_copy 내부 프롬프트에 주입)
        gen_client = active_client
        image = _generate_with_enhancement(
            source_image=src_pil,
            reference_image=ref_pil,
            client=gen_client,
            background_mode=background_mode,
            custom_background=custom_background,
            temperature=current_temp,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            enhancement_notes=enhancement_notes,
        )

        if image is None:
            print(f"[PoseCopyGen] X 생성 실패 (시도 {attempt + 1})")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": "생성 실패",
                }
            )
            if attempt < max_retries:
                current_temp = _get_temperature(attempt + 1)
            continue

        # -------------------------------------------------------
        # 2. 검수
        # -------------------------------------------------------
        try:
            validation_result = validator.validate(
                generated_img=image,
                reference_images={
                    "reference": [ref_pil],
                    "source": [src_pil],
                },
            )
        except Exception as e:
            print(f"[PoseCopyGen] X 검수 실패: {e}")
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "error": f"검수 오류: {e}",
                }
            )
            if attempt < max_retries:
                current_temp = _get_temperature(attempt + 1)
            continue

        # 결과 출력
        print(validation_result.summary_kr)

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
                "issues": validation_result.issues[:5],
                "criteria_scores": validation_result.criteria_scores,
            }
        )

        # 3. 최고 점수 추적
        if validation_result.total_score > best_score:
            best_image = image
            best_score = validation_result.total_score
            best_result = validation_result
            print(f"[PoseCopyGen] * 최고 점수 갱신: {best_score}")

        # 4. 통과 체크
        if validation_result.passed:
            print(f"[PoseCopyGen] PASSED! (시도 {attempt + 1})")
            break

        # -------------------------------------------------------
        # 5. 프롬프트 강화 (재시도가 남아있는 경우)
        # -------------------------------------------------------
        if attempt < max_retries:
            enhancement_notes = _build_enhancement_notes(
                validation_result=validation_result,
                validator=validator,
                attempt=attempt,
            )
            current_temp = _get_temperature(attempt + 1)
            time.sleep(2)  # Rate limit 방지

    # 최종 결과 반환
    return _build_result(best_image, best_result, history, max_retries)


# ============================================================================
# 내부 유틸리티
# ============================================================================


def _get_temperature(attempt_index: int) -> float:
    """재시도 횟수에 따른 온도 반환"""
    if attempt_index < len(_TEMPERATURE_SCHEDULE):
        return _TEMPERATURE_SCHEDULE[attempt_index]
    return _TEMPERATURE_SCHEDULE[-1]


def _generate_with_enhancement(
    source_image: Image.Image,
    reference_image: Image.Image,
    client: Any,
    background_mode: str,
    custom_background: Optional[str],
    temperature: float,
    aspect_ratio: str,
    resolution: str,
    enhancement_notes: str,
) -> Optional[Image.Image]:
    """강화 노트를 포함하여 이미지 생성.

    enhancement_notes가 있으면 프롬프트에 추가하여 재시도 품질을 높인다.
    """
    # VLM 분석
    reference_analysis = analyze_reference_pose(reference_image, client)
    source_analysis = analyze_source_person(source_image, client)

    # 기본 프롬프트 조립
    prompt = build_pose_copy_prompt(
        reference_analysis=reference_analysis,
        source_analysis=source_analysis,
        background_mode=background_mode,
        custom_background=custom_background,
    )

    # 강화 노트 추가 (재시도 시)
    if enhancement_notes:
        prompt = prompt + "\n\n" + enhancement_notes

    # API 파트 구성 (레퍼런스 이미지 직접 전달)
    parts = [
        types.Part(
            text="""[POSE & COMPOSITION REFERENCE] - COPY THIS EXACTLY!

THIS IMAGE IS THE POSE REFERENCE:
- Camera angle must match EXACTLY (low/eye-level/high angle)
- Framing must match EXACTLY (full body/half body/close-up)
- Body pose must match EXACTLY (every limb position)
- Person position in frame must match EXACTLY

Study this reference image carefully before generating:"""
        ),
        _pil_to_part(reference_image),
        types.Part(
            text="""[REFERENCE NOTED] Now generate with the person described below,
using EXACTLY the same pose, camera angle, framing, and composition as the reference above.

DO NOT change the pose. DO NOT change the camera angle. DO NOT change the framing.
ONLY replace the person's identity (face + outfit) as described below.
"""
        ),
        types.Part(text=prompt),
    ]

    # API 호출 (에러 재시도 최대 3회)
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

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            print("[PoseCopyGen] 응답에 이미지 없음")
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
                print(f"[PoseCopyGen] 생성 에러 (재시도 불가): {e}")
                return None

            if attempt < max_api_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[PoseCopyGen] API 재시도 {attempt + 1}/{max_api_retries} "
                    f"({wait_time}초 대기)"
                )
                time.sleep(wait_time)
            else:
                print(f"[PoseCopyGen] 최대 API 재시도 초과: {e}")

    return None


def _build_enhancement_notes(
    validation_result,
    validator: PoseCopyValidator,
    attempt: int,
) -> str:
    """검수 실패 기준에 따른 강화 노트 생성"""
    # 실패 기준 목록 추출
    failed_criteria = [
        issue.split(":")[0].strip() for issue in (validation_result.issues or [])
    ]

    # 검증기의 강화 규칙 사용
    enhancement_rules = validator.get_enhancement_rules(failed_criteria)

    if not enhancement_rules:
        return ""

    auto_fail_block = ""
    if validation_result.auto_fail_reasons:
        auto_fail_block = "## AUTO-FAIL 사유 (반드시 수정):\n"
        for reason in validation_result.auto_fail_reasons:
            auto_fail_block += f"- {reason}\n"
        auto_fail_block += "\n"

    notes = f"""
=== 재시도 강화 노트 (시도 #{attempt + 2}) ===
이전 점수: {validation_result.total_score}/100 | 등급: {validation_result.grade}
실패 항목: {', '.join(failed_criteria[:4]) if failed_criteria else '기준 미달'}

{auto_fail_block}## 수정 규칙:
{enhancement_rules}
=============================================
"""
    return notes.strip()


def _build_result(
    best_image: Optional[Image.Image],
    best_result,
    history: list,
    max_retries: int,
) -> dict:
    """최종 결과 딕셔너리 생성"""
    if best_image is None or best_result is None:
        print("\n[PoseCopyGen] X 모든 시도 실패")
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "attempts": max_retries + 1,
            "history": history,
            "summary_kr": "## 포즈 따라하기 검수 결과\n\n모든 시도 실패",
        }

    print(
        f"\n[PoseCopyGen] 최종 결과: {best_result.total_score}/100 "
        f"(등급: {best_result.grade}, 통과: {best_result.passed})"
    )

    return {
        "image": best_image,
        "score": best_result.total_score,
        "passed": best_result.passed,
        "criteria": best_result.criteria_scores,
        "attempts": len(history),
        "history": history,
        "summary_kr": best_result.summary_kr,
    }
