"""
Face Swap Generator

얼굴 스왑 이미지 생성 모듈 (생성 + 검수 루프 포함)

4단계 워크플로:
1. 분석 (VLM)   - 최적 얼굴 이미지 선택 (소스 분석 불필요)
2. 생성 (Image) - IMAGE_MODEL로 얼굴 스왑 생성
3. 검수 (VLM)  - FaceSwapValidator로 품질 판정
4. 재생성 (Loop) - 탈락 시 재생성 (최대 2회)

핵심 변경 (2026-02-20):
- 얼굴 이미지 먼저 전송 (소스 나중)
- 한국어 프롬프트 사용
- temperature 0.5
- 소스 분석 제거 (불필요)
"""

from io import BytesIO
from typing import Any, Optional

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from core.api import _get_next_api_key
from core.utils import pil_to_part
from .analyzer import select_best_face_images
from .templates_final import FACE_SWAP_PROMPT, GENERATION_CONFIG
from .validator import FaceSwapValidator


# ============================================================
# 내부 유틸
# ============================================================


def _load_image(image: "Image.Image | str") -> Optional[Image.Image]:
    """이미지 로드 (경로 또는 PIL Image)"""
    if isinstance(image, str):
        try:
            return Image.open(image).convert("RGB")
        except Exception as e:
            print(f"[FaceSwapGenerator] 이미지 로드 실패 {image}: {e}")
            return None
    if isinstance(image, Image.Image):
        return image
    return None


def _get_failed_criteria(validation_result) -> list:
    """검수 결과에서 실패한 기준 목록 반환"""
    criteria_map = {
        "face_identity": (
            validation_result.criteria_scores.get("face_identity", 0),
            95,
        ),
        "pose_preservation": (
            validation_result.criteria_scores.get("pose_preservation", 0),
            95,
        ),
        "outfit_preservation": (
            validation_result.criteria_scores.get("outfit_preservation", 0),
            95,
        ),
        "lighting_consistency": (
            validation_result.criteria_scores.get("lighting_consistency", 0),
            80,
        ),
        "edge_quality": (validation_result.criteria_scores.get("edge_quality", 0), 80),
    }
    return [
        criterion
        for criterion, (score, threshold) in criteria_map.items()
        if score < threshold
    ]


# ============================================================
# 공개 함수
# ============================================================


def generate_face_swap(
    source_image: "Image.Image | str",
    face_images: "list[Image.Image | str]",
    client: Any,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    selected_faces: Optional[list] = None,
    enhancement: Optional[str] = None,
) -> Optional[Image.Image]:
    """얼굴 스왑 이미지 생성 (단일 생성, 검수 없음).

    이미지 순서: 얼굴 먼저 → 소스 나중 (테스트 결과 최적)
    Temperature: 0.5 (고정)

    Args:
        source_image: 소스 이미지 (포즈/착장/배경 보존)
        face_images: 교체할 얼굴 이미지 목록
        client: Google GenAI client instance
        aspect_ratio: 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")
        selected_faces: 선택된 얼굴 이미지 (없으면 자동 선택)
        enhancement: 재시도 시 추가할 강화 규칙 텍스트

    Returns:
        생성된 PIL.Image 또는 None
    """
    # 1. 소스 이미지 로드
    pil_source = _load_image(source_image)
    if pil_source is None:
        print("[FaceSwapGenerator] 소스 이미지 로드 실패")
        return None

    # 2. 최적 얼굴 이미지 선택 (없으면 실행)
    if selected_faces is None:
        selected_faces = select_best_face_images(face_images, client)

    if not selected_faces:
        print("[FaceSwapGenerator] 유효한 얼굴 이미지 없음")
        return None

    # 4. Parts 조립: 얼굴 이미지들 + 소스 이미지 + 프롬프트
    # (얼굴 먼저, 소스 나중 - 테스트 결과 이 순서가 최적)
    parts = []

    # 4-1. 얼굴 이미지 먼저 (첫 번째 이미지 = 이 사람)
    for face_img in selected_faces:
        pil_face = (
            _load_image(face_img) if not isinstance(face_img, Image.Image) else face_img
        )
        if pil_face is not None:
            parts.append(pil_to_part(pil_face))

    # 4-2. 소스 이미지 (두 번째 이미지 = 장면 참고용)
    parts.append(pil_to_part(pil_source))

    # 4-3. 프롬프트 (강화 규칙 포함)
    prompt = FACE_SWAP_PROMPT
    if enhancement:
        prompt = prompt.rstrip() + f"\n\n[ENHANCEMENT RULES]\n{enhancement}"
    parts.append(types.Part(text=prompt))

    # 5. 생성 (temperature 0.5 고정 - 테스트 결과 최적)
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=GENERATION_CONFIG["temperature"],
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                ),
            ),
        )

        # 결과 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data))

    except Exception as e:
        print(f"[FaceSwapGenerator] 생성 실패: {e}")

    return None


def generate_with_validation(
    source_image: "Image.Image | str",
    face_images: "list[Image.Image | str]",
    client: Any = None,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
) -> dict:
    """얼굴 스왑 이미지 생성 + 검수 루프 (공개 API).

    3단계 워크플로:
    1. 분석 (VLM) - 최적 얼굴 이미지 선택
    2. 생성 (Image) - generate_face_swap 호출 (temp 0.5 고정)
    3. 검수 (VLM) - FaceSwapValidator 검수
    4. 재시도 - 탈락 시 재생성 (최대 max_retries회)

    핵심 변경 (2026-02-20):
    - 소스 분석 제거 (불필요)
    - 이미지 순서: 얼굴 먼저 → 소스 나중
    - Temperature 0.5 고정

    Args:
        source_image: 소스 이미지 (포즈/착장/배경 보존)
        face_images: 교체할 얼굴 이미지 목록
        client: Google GenAI client (없으면 api_key로 생성)
        api_key: Gemini API 키 (없으면 자동 로테이션)
        max_retries: 최대 재시도 횟수 (기본 2)
        aspect_ratio: 비율 (기본 "3:4")
        resolution: 해상도 (기본 "2K")

    Returns:
        dict:
            - image: PIL.Image (최종 생성 이미지, 실패 시 마지막 생성 이미지)
            - score: int (검수 총점)
            - passed: bool (검수 통과 여부)
            - criteria: dict (기준별 점수)
            - history: list (재시도 이력)
    """
    history = []
    last_image = None
    last_validation = None

    # 클라이언트 생성
    if client is None:
        key = api_key or _get_next_api_key()
        client = genai.Client(api_key=key)

    # ============================================================
    # 1. 분석 (VLM) - 최적 얼굴 이미지 선택만
    # ============================================================
    print("[ANALYZE] 최적 얼굴 이미지 선택 중...")
    selected_faces = select_best_face_images(face_images, client)
    print(f"  - 선택된 얼굴 이미지: {len(selected_faces)}장")

    if not selected_faces:
        return {
            "image": None,
            "score": 0,
            "passed": False,
            "criteria": {},
            "history": [{"attempt": 0, "status": "no_valid_face_images"}],
        }

    # 소스 이미지 PIL 로드 (검수 시 참조용)
    pil_source = _load_image(source_image)

    # ============================================================
    # 2-4. 생성 + 검수 + 재시도 루프
    # ============================================================
    validator = FaceSwapValidator(client)

    for attempt in range(max_retries + 1):
        print(f"\n[GENERATE] 시도 {attempt + 1}/{max_retries + 1} (temperature=0.5)...")

        # 실패 기준 기반 강화 규칙 (2회차부터)
        enhancement = None
        if attempt > 0 and last_validation is not None:
            failed = _get_failed_criteria(last_validation)
            if failed:
                enhancement = validator.get_enhancement_rules(failed)
                print(f"  - 강화 규칙 적용: {', '.join(failed)}")

        # API 키 로테이션
        next_client = genai.Client(api_key=_get_next_api_key())

        # 2. 생성 (Image) - temperature 0.5 고정
        generated_image = generate_face_swap(
            source_image=source_image,
            face_images=face_images,
            client=next_client,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            selected_faces=selected_faces,
            enhancement=enhancement,
        )

        if generated_image is None:
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": 0.5,
                    "status": "generation_failed",
                }
            )
            print("  - 생성 실패")
            continue

        last_image = generated_image

        # 3. 검수 (VLM)
        print("[VALIDATE] 검수 중...")
        validation_result = validator.validate(
            generated_img=generated_image,
            reference_images={
                "face": selected_faces,
                "source": [pil_source] if pil_source else [],
            },
        )
        last_validation = validation_result

        history.append(
            {
                "attempt": attempt + 1,
                "temperature": 0.5,
                "score": validation_result.total_score,
                "passed": validation_result.passed,
                "grade": validation_result.grade,
                "criteria": validation_result.criteria_scores,
                "auto_fail": validation_result.auto_fail,
                "auto_fail_reasons": validation_result.auto_fail_reasons,
            }
        )

        print(
            f"  - 점수: {validation_result.total_score} | 등급: {validation_result.grade} | 판정: {'PASS' if validation_result.passed else 'FAIL'}"
        )

        # 4. 검수 통과 시 즉시 반환
        if validation_result.passed:
            print(f"[OK] 검수 통과 (시도 {attempt + 1}회)")
            return {
                "image": generated_image,
                "score": validation_result.total_score,
                "passed": True,
                "criteria": validation_result.criteria_scores,
                "history": history,
            }

        print(f"  - 재시도 (탈락 기준: {_get_failed_criteria(validation_result)})")

    # ============================================================
    # 최대 재시도 후에도 실패
    # ============================================================
    print(f"[FAIL] 최대 재시도 횟수 초과 ({max_retries + 1}회)")

    final_score = last_validation.total_score if last_validation else 0
    final_criteria = last_validation.criteria_scores if last_validation else {}

    return {
        "image": last_image,
        "score": final_score,
        "passed": False,
        "criteria": final_criteria,
        "history": history,
    }
