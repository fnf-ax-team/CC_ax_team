"""
다중 얼굴 교체 생성기

두 가지 공개 함수를 제공한다:
    generate_multi_swap()       — 검증 없는 순수 생성 (내부/테스트용)
    generate_with_validation()  — 생성 + 검증 + 재생성 루프 (공개 API)

인원 수 제한:
    - 5명 이하: 권장 (최적 품질)
    - 6~10명: 경고 후 진행
    - 11명 이상: ValueError 발생 (품질 보장 불가)

폴백 전략:
    동시 스왑 3회 실패 시 → 순차 스왑으로 자동 전환
"""

import logging
import time
from io import BytesIO
from typing import Any, Union

from PIL import Image

from core.config import IMAGE_MODEL
from .analyzer import analyze_group_photo, analyze_replacement_faces
from .detector import detect_faces, map_faces, _load_image, _pil_to_part
from .prompt_builder import build_multi_swap_prompt
from .validator import MultiFaceSwapValidator

logger = logging.getLogger(__name__)

# ============================================================
# 인원 수 제한 상수
# ============================================================
FACE_LIMIT_RECOMMENDED = 5  # 권장 최대 인원
FACE_LIMIT_MAX = 10  # 절대 최대 인원 (이하는 경고 후 진행)
FACE_LIMIT_REJECT = 11  # 이상은 거부


# ============================================================
# 내부 헬퍼
# ============================================================


def _build_api_parts(
    source_image: Image.Image,
    prompt_text: str,
    face_mapping_loaded: dict[int, dict],
) -> list:
    """Gemini API 전달용 Parts 구성

    순서:
    1. 프롬프트 텍스트
    2. 원본 단체 사진 (구도/착장/포즈 보존 기준)
    3. 각 인물별 교체 얼굴 이미지 (person_id 순)

    Args:
        source_image: 원본 단체 사진 (PIL Image, RGB)
        prompt_text: 완성된 다중 얼굴 교체 프롬프트
        face_mapping_loaded: map_faces() 반환값
            {person_id: {"face_images": [PIL.Image], "person_info": dict, "mapped": bool}}

    Returns:
        google.genai.types.Part 리스트
    """
    from google.genai import types

    parts = []

    # 1. 프롬프트 텍스트
    parts.append(types.Part(text=prompt_text))

    # 2. 원본 단체 사진
    parts.append(
        types.Part(
            text=(
                "[SOURCE GROUP PHOTO] — 이 이미지의 구도/착장/포즈/배경을 "
                "100% 보존하세요. 얼굴만 교체합니다."
            )
        )
    )
    parts.append(_pil_to_part(source_image))

    # 3. 각 인물별 교체 얼굴 이미지 (person_id 오름차순)
    for person_id in sorted(face_mapping_loaded.keys()):
        entry = face_mapping_loaded[person_id]
        if not entry.get("mapped") or not entry.get("face_images"):
            continue

        person_info = entry.get("person_info", {})
        position = person_info.get("position", f"position_{person_id}")

        parts.append(
            types.Part(
                text=(
                    f"[FACE REFERENCE — PERSON {person_id} ({position})] "
                    f"이 얼굴을 해당 위치의 인물에게 정확히 적용하세요. "
                    f"착장/포즈/체형은 절대 변경하지 마세요."
                )
            )
        )
        # 최대 3장만 전송 (VLM 부담 최소화, API 제한 고려)
        for face_img in entry["face_images"][:3]:
            parts.append(_pil_to_part(face_img))

    return parts


def _extract_image_from_response(response: Any) -> Image.Image | None:
    """Gemini API 응답에서 PIL Image 추출

    Args:
        response: Gemini API generate_content() 반환값

    Returns:
        PIL Image 또는 None (이미지 없음)
    """
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))
    return None


def _generate_simultaneous(
    source_image: Image.Image,
    prompt_text: str,
    face_mapping_loaded: dict[int, dict],
    client: Any,
    temperature: float,
    aspect_ratio: str,
    resolution: str,
    max_api_retries: int = 3,
) -> Image.Image | None:
    """모든 얼굴을 동시에 교체하는 생성 시도

    Args:
        source_image: 원본 단체 사진
        prompt_text: 완성된 프롬프트
        face_mapping_loaded: map_faces() 반환값
        client: Gemini API 클라이언트
        temperature: 생성 온도
        aspect_ratio: 화면 비율
        resolution: 해상도
        max_api_retries: API 에러 시 최대 재시도 횟수

    Returns:
        PIL Image 또는 None
    """
    from google.genai import types

    parts = _build_api_parts(source_image, prompt_text, face_mapping_loaded)

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
            img = _extract_image_from_response(response)
            if img is not None:
                return img
            logger.warning(
                "[MULTI_FACE_SWAP] 동시 스왑 응답에 이미지 없음 (시도 %d)", attempt + 1
            )

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(
                kw in error_str for kw in ("429", "rate", "503", "overload", "timeout")
            )

            if not is_retryable:
                logger.error("[MULTI_FACE_SWAP] 동시 스왑 비재시도 에러: %s", e)
                return None

            if attempt < max_api_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(
                    "[MULTI_FACE_SWAP] 동시 스왑 API 에러 (재시도 %d/%d, %ds 대기): %s",
                    attempt + 1,
                    max_api_retries,
                    wait_time,
                    e,
                )
                time.sleep(wait_time)
            else:
                logger.error("[MULTI_FACE_SWAP] 동시 스왑 최대 재시도 초과: %s", e)

    return None


def _generate_sequential(
    source_image: Image.Image,
    face_mapping_loaded: dict[int, dict],
    group_analysis: dict,
    client: Any,
    temperature: float,
    aspect_ratio: str,
    resolution: str,
) -> Image.Image | None:
    """얼굴을 한 명씩 순차 교체하는 폴백 전략

    동시 스왑이 3회 모두 실패했을 때 호출된다.
    각 인물을 개별 프롬프트로 순서대로 교체하며,
    이전 교체 결과를 다음 교체의 원본으로 사용한다.

    Args:
        source_image: 원본 단체 사진
        face_mapping_loaded: map_faces() 반환값
        group_analysis: analyze_group_photo() 반환값
        client: Gemini API 클라이언트
        temperature: 생성 온도
        aspect_ratio: 화면 비율
        resolution: 해상도

    Returns:
        최종 교체 결과 PIL Image 또는 None
    """
    from google.genai import types

    logger.info(
        "[MULTI_FACE_SWAP] 순차 스왑 폴백 시작 (총 %d명)", len(face_mapping_loaded)
    )

    current_image = source_image
    scene_desc = group_analysis.get("scene_description", "group photo")
    lighting_desc = group_analysis.get("lighting_description", "natural light")

    for person_id in sorted(face_mapping_loaded.keys()):
        entry = face_mapping_loaded[person_id]
        if not entry.get("mapped") or not entry.get("face_images"):
            logger.debug("[MULTI_FACE_SWAP] person_id=%d 매핑 없음, 건너뜀", person_id)
            continue

        person_info = entry.get("person_info", {})
        position = person_info.get("position", f"position_{person_id}")
        clothing_hint = person_info.get("clothing_hint", "")

        # 단일 인물 교체 프롬프트
        sequential_prompt = (
            f"Face swap for PERSON {person_id} only.\n\n"
            f"Scene: {scene_desc}\n"
            f"Lighting: {lighting_desc}\n\n"
            f"TARGET: The person at {position} position"
            + (f" wearing {clothing_hint}" if clothing_hint else "")
            + ".\n\n"
            f"RULES:\n"
            f"- Replace ONLY this person's face with the provided reference face\n"
            f"- Preserve ALL other persons' faces exactly\n"
            f"- Preserve ALL clothing, poses, body shapes\n"
            f"- Preserve background exactly\n"
            f"- Apply consistent lighting to the replaced face\n"
            f"- Seamless edge blending at face-neck boundary\n"
        )

        parts = [
            types.Part(text=sequential_prompt),
            types.Part(
                text="[CURRENT IMAGE — 포즈/착장/배경 기준, 이 이미지에서 교체 수행]:"
            ),
            _pil_to_part(current_image),
        ]

        # 교체 얼굴 이미지 추가
        parts.append(
            types.Part(
                text=(
                    f"[FACE REFERENCE — PERSON {person_id}] "
                    "이 얼굴을 위 이미지의 해당 인물에게 적용하세요:"
                )
            )
        )
        for face_img in entry["face_images"][:3]:
            parts.append(_pil_to_part(face_img))

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
            result_img = _extract_image_from_response(response)
            if result_img is not None:
                current_image = result_img
                logger.info("[MULTI_FACE_SWAP] 순차 스왑 person_id=%d 완료", person_id)
            else:
                logger.warning(
                    "[MULTI_FACE_SWAP] 순차 스왑 person_id=%d 이미지 없음, 건너뜀",
                    person_id,
                )

        except Exception as e:
            logger.warning(
                "[MULTI_FACE_SWAP] 순차 스왑 person_id=%d 에러: %s — 건너뜀",
                person_id,
                e,
            )
            # 에러 발생 시 현재 이미지 유지하고 다음 인물로 진행

    # 원본과 동일하면 전부 실패로 간주
    if current_image is source_image:
        logger.error("[MULTI_FACE_SWAP] 순차 스왑: 모든 인물 교체 실패")
        return None

    return current_image


# ============================================================
# 공개 함수 1: 순수 생성 (검증 없음)
# ============================================================


def generate_multi_swap(
    source_image: Union[Image.Image, str],
    face_mapping: dict[int, list[Union[Image.Image, str]]],
    client: Any,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> Image.Image | None:
    """다중 얼굴 교체 이미지 생성 (검증 없음)

    워크플로:
    1. 원본 사진에서 인물 감지 (인원 수 제한 검사)
    2. 감지된 인물 ↔ 교체 얼굴 이미지 매핑
    3. 단체 사진 장면/조명/포즈 컨텍스트 분석
    4. 교체 얼굴 특징 분석
    5. 최종 프롬프트 조립
    6. IMAGE_MODEL로 이미지 생성 (동시 스왑)
    7. 동시 스왑 3회 실패 시 → 순차 스왑 폴백

    인원 수 제한:
        - 5명 이하: 권장 (최적 품질)
        - 6~10명: 경고 후 진행
        - 11명 이상: ValueError 발생

    Args:
        source_image: 원본 단체 사진 (PIL Image 또는 파일 경로)
        face_mapping: {person_id: [교체 얼굴 이미지, ...]} 형태
            person_id는 1-indexed int (detect_faces() 반환 ID 기준)
        client: 초기화된 Gemini API 클라이언트
        temperature: 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")

    Returns:
        생성된 PIL Image 또는 None (생성 실패)

    Raises:
        ValueError: 인원 11명 이상 또는 감지 실패 시
        TypeError: 지원하지 않는 이미지 타입 시
    """
    # ── STEP 1: 인원 수 사전 체크 (face_mapping 기준)
    num_requested = len(face_mapping)
    if num_requested > FACE_LIMIT_MAX:
        raise ValueError(
            f"교체 요청 인원({num_requested}명)이 최대 허용 인원({FACE_LIMIT_MAX}명)을 초과합니다. "
            f"{FACE_LIMIT_MAX}명 이하로 요청하세요."
        )
    if num_requested > FACE_LIMIT_RECOMMENDED:
        logger.warning(
            "[MULTI_FACE_SWAP] 교체 요청 %d명 (권장: %d명 이하). 품질이 저하될 수 있습니다.",
            num_requested,
            FACE_LIMIT_RECOMMENDED,
        )

    # ── STEP 2: 원본 이미지 로드
    source_img = _load_image(source_image)

    # ── STEP 3: 인물 감지 (11명 이상이면 ValueError)
    logger.info("[MULTI_FACE_SWAP] STEP 1 — 인물 감지 시작")
    detected_faces = detect_faces(source_image, client)
    logger.info("[MULTI_FACE_SWAP] STEP 1 — %d명 감지 완료", len(detected_faces))

    # ── STEP 4: 얼굴 매핑
    logger.info("[MULTI_FACE_SWAP] STEP 2 — 얼굴 매핑")
    face_mapping_loaded = map_faces(detected_faces, face_mapping)

    # 실제 매핑된 인원 수 확인
    mapped_count = sum(1 for v in face_mapping_loaded.values() if v.get("mapped"))
    if mapped_count == 0:
        logger.error("[MULTI_FACE_SWAP] 유효한 얼굴 매핑 없음. 생성 중단.")
        return None

    # ── STEP 5: 단체 사진 장면 분석
    logger.info("[MULTI_FACE_SWAP] STEP 3 — 단체 사진 컨텍스트 분석")
    group_analysis = analyze_group_photo(source_image, detected_faces, client)

    # ── STEP 6: 교체 얼굴 특징 분석
    logger.info("[MULTI_FACE_SWAP] STEP 4 — 교체 얼굴 분석")
    face_analyses = analyze_replacement_faces(face_mapping, client)

    # ── STEP 7: 프롬프트 조립
    logger.info("[MULTI_FACE_SWAP] STEP 5 — 프롬프트 조립")
    prompt_text = build_multi_swap_prompt(
        group_analysis=group_analysis,
        detected_faces=detected_faces,
        face_analyses=face_analyses,
    )

    # ── STEP 8: 동시 스왑 생성 (최대 3회 시도)
    logger.info("[MULTI_FACE_SWAP] STEP 6 — 동시 스왑 생성 시작")
    SIMULTANEOUS_ATTEMPTS = 3
    result_img = None

    for attempt in range(SIMULTANEOUS_ATTEMPTS):
        logger.info(
            "[MULTI_FACE_SWAP] 동시 스왑 시도 %d/%d",
            attempt + 1,
            SIMULTANEOUS_ATTEMPTS,
        )
        # 재시도 시 temperature 소폭 낮춤 (보존 정확도 향상)
        attempt_temperature = max(0.05, temperature - attempt * 0.05)

        result_img = _generate_simultaneous(
            source_image=source_img,
            prompt_text=prompt_text,
            face_mapping_loaded=face_mapping_loaded,
            client=client,
            temperature=attempt_temperature,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            max_api_retries=1,  # 외부 루프가 재시도 관리
        )

        if result_img is not None:
            logger.info("[MULTI_FACE_SWAP] 동시 스왑 성공 (시도 %d)", attempt + 1)
            return result_img

        logger.warning("[MULTI_FACE_SWAP] 동시 스왑 시도 %d 실패", attempt + 1)
        if attempt < SIMULTANEOUS_ATTEMPTS - 1:
            time.sleep(3)  # 다음 시도 전 짧은 대기

    # ── STEP 9: 동시 스왑 전부 실패 → 순차 스왑 폴백
    logger.warning(
        "[MULTI_FACE_SWAP] 동시 스왑 %d회 모두 실패. 순차 스왑 폴백 시작.",
        SIMULTANEOUS_ATTEMPTS,
    )
    result_img = _generate_sequential(
        source_image=source_img,
        face_mapping_loaded=face_mapping_loaded,
        group_analysis=group_analysis,
        client=client,
        temperature=temperature,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )

    if result_img is None:
        logger.error("[MULTI_FACE_SWAP] 동시 스왑 + 순차 스왑 모두 실패.")

    return result_img


# ============================================================
# 공개 함수 2: 생성 + 검증 + 재생성 루프 (공개 API)
# ============================================================


def generate_with_validation(
    source_image: Union[Image.Image, str],
    face_mapping: dict[int, list[Union[Image.Image, str]]],
    client: Any | None = None,
    api_key: str | None = None,
    max_retries: int = 2,
    temperature: float = 0.2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """다중 얼굴 교체 생성 + 검증 + 재생성 루프 (공개 API)

    CLAUDE.md 필수 패턴 준수:
    - 검수 없이 이미지 저장 금지
    - max_retries >= 2 필수

    통과 기준:
        - total_score >= 92
        - all_faces_identity >= 90 (가중 평균)
        - 개별 얼굴 동일성 < 80이면 Auto-Fail

    인원 수 제한:
        - 5명 이하: 권장
        - 6~10명: 경고 후 진행
        - 11명 이상: 즉시 ValueError (품질 보장 불가)

    Args:
        source_image: 원본 단체 사진 (PIL Image 또는 파일 경로)
        face_mapping: {person_id: [교체 얼굴 이미지, ...]} 형태
        client: 초기화된 Gemini API 클라이언트 (client 또는 api_key 중 하나 필수)
        api_key: Gemini API 키 (client 없을 때 사용)
        max_retries: 최대 재시도 횟수 (기본 2, 최소 0)
        temperature: 초기 생성 온도 (기본 0.2)
        aspect_ratio: 화면 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")

    Returns:
        dict:
            - image: PIL.Image | None — 최종 이미지 (통과 또는 최선 결과)
            - passed: bool — 검증 통과 여부
            - score: int — 총점 (0~100)
            - grade: str — 등급 (S/A/B/C/F)
            - criteria: dict — 항목별 점수
            - attempts: int — 시도 횟수
            - history: list[dict] — 각 시도 결과 이력
            - auto_fail: bool — Auto-Fail 발생 여부
            - auto_fail_reasons: list[str] — Auto-Fail 사유
            - issues: list[str] — 검수 이슈 목록
            - summary_kr: str — 한국어 검수 요약

    Raises:
        ValueError: 인원 11명 이상, client/api_key 모두 없음, 감지 실패 시
    """
    from google import genai

    # ── 인원 수 사전 체크
    num_requested = len(face_mapping)
    if num_requested >= FACE_LIMIT_REJECT:
        raise ValueError(
            f"교체 요청 인원({num_requested}명)이 최대 허용 인원({FACE_LIMIT_MAX}명)을 초과합니다. "
            f"품질 보장이 불가하므로 처리를 거부합니다. "
            f"{FACE_LIMIT_MAX}명 이하로 분할하세요."
        )
    if num_requested > FACE_LIMIT_RECOMMENDED:
        logger.warning(
            "[MULTI_FACE_SWAP] 교체 요청 %d명 (권장: %d명 이하). "
            "정확도가 낮아질 수 있습니다. 진행합니다.",
            num_requested,
            FACE_LIMIT_RECOMMENDED,
        )

    # ── 클라이언트 준비
    if client is None:
        if api_key is None:
            try:
                from core.api import get_next_api_key

                api_key = get_next_api_key()
            except Exception:
                raise ValueError("client 또는 api_key 중 하나를 제공해야 합니다.")
        client = genai.Client(api_key=api_key)

    # ── 검증기 초기화
    validator = MultiFaceSwapValidator(client=client)

    # ── 이력 및 상태 초기화
    history = []
    best_image = None
    best_score = -1
    best_result = None

    # ── 검증에 사용할 reference_images 구성
    # source 이미지 로드
    source_img_pil = _load_image(source_image)
    reference_images: dict[str, list] = {"source": [source_img_pil]}
    for person_id, face_imgs in face_mapping.items():
        key = f"face_{person_id}"
        reference_images[key] = [_load_image(img) for img in face_imgs[:3]]

    # ── 생성 + 검증 루프
    total_attempts = max_retries + 1  # 최초 시도 + 재시도
    for attempt in range(total_attempts):
        logger.info(
            "[MULTI_FACE_SWAP] 생성+검증 시도 %d/%d",
            attempt + 1,
            total_attempts,
        )

        # 재시도 시 temperature 낮춤 (보존 정확도 향상)
        attempt_temperature = max(0.05, temperature - attempt * 0.05)

        # 생성
        try:
            generated_img = generate_multi_swap(
                source_image=source_image,
                face_mapping=face_mapping,
                client=client,
                temperature=attempt_temperature,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )
        except ValueError:
            # 인원 수 제한 등 복구 불가 에러 — 즉시 전파
            raise
        except Exception as e:
            logger.error("[MULTI_FACE_SWAP] 생성 에러 (시도 %d): %s", attempt + 1, e)
            history.append(
                {
                    "attempt": attempt + 1,
                    "image": None,
                    "score": 0,
                    "passed": False,
                    "error": str(e),
                }
            )
            if attempt < total_attempts - 1:
                time.sleep((attempt + 1) * 5)
            continue

        if generated_img is None:
            logger.warning("[MULTI_FACE_SWAP] 생성 결과 없음 (시도 %d)", attempt + 1)
            history.append(
                {
                    "attempt": attempt + 1,
                    "image": None,
                    "score": 0,
                    "passed": False,
                    "error": "생성 결과 없음",
                }
            )
            if attempt < total_attempts - 1:
                time.sleep((attempt + 1) * 5)
            continue

        # 검증
        try:
            validation_result = validator.validate(
                generated_img=generated_img,
                reference_images=reference_images,
            )
        except Exception as e:
            logger.error("[MULTI_FACE_SWAP] 검증 에러 (시도 %d): %s", attempt + 1, e)
            history.append(
                {
                    "attempt": attempt + 1,
                    "image": generated_img,
                    "score": 0,
                    "passed": False,
                    "error": f"검증 에러: {e}",
                }
            )
            # 검증 실패 시 이미지는 보관 (폴백용)
            if best_score < 0:
                best_image = generated_img
                best_score = 0
            if attempt < total_attempts - 1:
                time.sleep((attempt + 1) * 5)
            continue

        score = validation_result.total_score
        passed = validation_result.passed

        history.append(
            {
                "attempt": attempt + 1,
                "image": generated_img,
                "score": score,
                "passed": passed,
                "grade": validation_result.grade,
                "criteria": validation_result.criteria_scores,
                "auto_fail": validation_result.auto_fail,
                "auto_fail_reasons": validation_result.auto_fail_reasons,
                "issues": validation_result.issues,
            }
        )

        # 최고점 이미지 갱신
        if score > best_score:
            best_score = score
            best_image = generated_img
            best_result = validation_result

        logger.info(
            "[MULTI_FACE_SWAP] 시도 %d — 점수: %d, 등급: %s, 통과: %s",
            attempt + 1,
            score,
            validation_result.grade,
            passed,
        )

        if passed:
            logger.info("[MULTI_FACE_SWAP] 검증 통과! 시도 %d", attempt + 1)
            break

        if attempt < total_attempts - 1:
            # 실패한 기준 분석 → 다음 시도에서 generate_multi_swap이
            # 내부적으로 재시도하므로 로그만 남김
            failed_criteria = [
                k for k, v in validation_result.criteria_scores.items() if v < 90
            ]
            logger.info(
                "[MULTI_FACE_SWAP] 재시도 준비 — 실패 기준: %s",
                failed_criteria,
            )
            time.sleep((attempt + 1) * 5)

    # ── 결과 구성
    # best_result가 없으면 (모든 시도에서 검증 에러) 기본값
    if best_result is None:
        return {
            "image": best_image,
            "passed": False,
            "score": 0,
            "grade": "F",
            "criteria": {},
            "attempts": len(history),
            "history": history,
            "auto_fail": False,
            "auto_fail_reasons": [],
            "issues": ["모든 시도에서 생성 또는 검증 실패"],
            "summary_kr": "다중 얼굴 교체 실패: 생성/검증 오류",
        }

    return {
        "image": best_image,
        "passed": best_result.passed,
        "score": best_result.total_score,
        "grade": best_result.grade,
        "criteria": best_result.criteria_scores,
        "attempts": len(history),
        "history": history,
        "auto_fail": best_result.auto_fail,
        "auto_fail_reasons": best_result.auto_fail_reasons,
        "issues": best_result.issues,
        "summary_kr": best_result.summary_kr,
    }
