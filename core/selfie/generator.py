"""
셀피/인플루언서 이미지 생성 모듈

이미지 생성 및 검증 기능 제공
- generate_selfie: 단일 이미지 생성
- generate_with_validation: 생성 + 검증 루프
- generate_selfie_v3: DB 기반 생성 (v3)
- generate_batch_v3: DB 기반 배치 생성 (v3)
"""

import time
import random
from io import BytesIO
from typing import Optional, List, Union, Dict, Tuple
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
    pose_reference: Optional[Union[str, Path, Image.Image]] = None,
    bg_reference: Optional[Union[str, Path, Image.Image]] = None,
    expression_reference: Optional[Union[str, Path, Image.Image]] = None,
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
        pose_reference: 포즈 프리셋 이미지 (선택) - 퀄리티 향상에 중요!
        bg_reference: 배경 프리셋 이미지 (선택) - 퀄리티 향상에 중요!
        expression_reference: 표정 프리셋 이미지 (선택) - 표정 재현에 중요!
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

    # 포즈 참조 이미지 전송 (선택적 - 퀄리티 향상에 중요!)
    if pose_reference is not None:
        if isinstance(pose_reference, (str, Path)):
            pose_img = Image.open(pose_reference).convert("RGB")
        else:
            pose_img = (
                pose_reference.convert("RGB")
                if pose_reference.mode != "RGB"
                else pose_reference
            )

        parts.append(
            types.Part(
                text="""[POSE REFERENCE] ★★★ 최우선 - 이 포즈를 100% 똑같이 복사 ★★★

반드시 따라할 것:
1. 팔 위치: 왼팔/오른팔 정확히 같은 위치와 각도
2. 다리 위치: 왼다리/오른다리 정확히 같은 위치, 꼬임, 구부림
3. 몸 방향: 정면/측면/뒤 같은 방향
4. 카메라 앵글: 로우앵글/아이레벨/하이앵글 똑같이
5. 프레이밍: 전신/상반신/클로즈업 똑같이

★ 포즈가 다르면 실패입니다! 레퍼런스 이미지 포즈를 1:1로 복사하세요! ★
착장/배경/얼굴은 무시하고 포즈만 정확히 복사!"""
            )
        )
        parts.append(pil_to_part(pose_img))

    # 배경 참조 이미지 전송 (선택적 - 퀄리티 향상에 중요!)
    if bg_reference is not None:
        if isinstance(bg_reference, (str, Path)):
            bg_img = Image.open(bg_reference).convert("RGB")
        else:
            bg_img = (
                bg_reference.convert("RGB")
                if bg_reference.mode != "RGB"
                else bg_reference
            )

        parts.append(
            types.Part(text="[BACKGROUND REFERENCE] - 이 배경 분위기를 참고하세요:")
        )
        parts.append(pil_to_part(bg_img))

    # 표정 참조 이미지 전송 (선택적 - 표정 재현에 중요!)
    if expression_reference is not None:
        if isinstance(expression_reference, (str, Path)):
            expr_img = Image.open(expression_reference).convert("RGB")
        else:
            expr_img = (
                expression_reference.convert("RGB")
                if expression_reference.mode != "RGB"
                else expression_reference
            )

        parts.append(
            types.Part(
                text="""[EXPRESSION REFERENCE] ★★★ 이 표정을 정확히 복사 ★★★

반드시 따라할 것:
1. 눈 표정: 눈빛, 눈 크기, 눈 방향을 똑같이
2. 입 모양: 벌림 정도, 입꼬리 방향 똑같이
3. 전체 무드: 표정의 감정/분위기 똑같이
4. 윙크가 있으면 똑같이 윙크

★ 얼굴 생김새는 FACE REFERENCE를 따르되, 표정만 이 레퍼런스처럼! ★"""
            )
        )
        parts.append(pil_to_part(expr_img))

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
    pose_reference: Optional[Union[str, Path, Image.Image]] = None,
    bg_reference: Optional[Union[str, Path, Image.Image]] = None,
    expression_reference: Optional[Union[str, Path, Image.Image]] = None,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    initial_temperature: float = 0.7,
    validator=None,  # SelfieValidator 인스턴스
) -> dict:
    """
    생성 + 검증 + 재생성 루프

    validator가 None이면 검증 없이 단순 생성만 수행.

    Args:
        prompt: 프롬프트 문자열
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록 (선택)
        pose_reference: 포즈 프리셋 이미지 (선택) - 퀄리티 향상에 중요!
        bg_reference: 배경 프리셋 이미지 (선택) - 퀄리티 향상에 중요!
        expression_reference: 표정 프리셋 이미지 (선택) - 표정 재현에 중요!
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

        # 1. 이미지 생성 (포즈/배경/표정 참조 이미지 포함)
        image = generate_selfie(
            prompt=prompt,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            bg_reference=bg_reference,
            expression_reference=expression_reference,
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

                # SelfieValidationResult 객체 처리
                if hasattr(validation_result, "total_score"):
                    score = validation_result.total_score
                    passed = validation_result.passed
                else:
                    # dict 호환 (레거시)
                    score = validation_result.get("total_score", 0)
                    passed = validation_result.get("passed", False)

                # 검수표 형식으로 출력
                print(f"\n{'=' * 60}")
                print(f"검증 결과 (시도 {attempt + 1})")
                print(f"{'=' * 60}")
                if hasattr(validation_result, "format_korean"):
                    print(validation_result.format_korean())
                else:
                    print(f"Score: {score}/100 | {'PASS' if passed else 'FAIL'}")
                print(f"{'=' * 60}\n")

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


# ============================================================
# V3: DB 기반 생성 함수
# ============================================================


def generate_selfie_v3(
    face_images: List[Union[str, Path, Image.Image]],
    pose: Dict,
    scene: Dict,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    gender: str = "female",
    expression="시크",  # str (카테고리) 또는 Dict (프리셋)
    makeup: str = "natural",
    outfit_analysis: Optional[Dict] = None,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    use_reference_image: bool = True,
    use_expression_reference: bool = True,
) -> Optional[Image.Image]:
    """
    DB 프리셋 기반 셀피 생성 (v3)

    Args:
        face_images: 얼굴 이미지 목록 (필수)
        pose: pose_presets.json의 포즈 dict
        scene: scene_presets.json의 씬 dict
        outfit_images: 착장 이미지 목록 (선택)
        gender: "female" | "male"
        expression: 카테고리 문자열("시크") 또는 expression_presets.json의 프리셋 Dict
        makeup: "bare" | "natural" | "full"
        outfit_analysis: VLM 착장 분석 결과 (선택)
        aspect_ratio: 화면 비율 (기본 9:16)
        resolution: 해상도 (1K/2K/4K)
        temperature: 생성 온도 (기본 0.7)
        api_key: Gemini API 키
        use_reference_image: 씬의 레퍼런스 이미지 사용 여부
        use_expression_reference: 표정 프리셋 레퍼런스 이미지 사용 여부

    Returns:
        PIL.Image: 생성된 이미지 (실패 시 None)
    """
    from .prompt_builder import build_prompt_from_db, build_prompt_from_db_simple
    from .db_loader import get_reference_image_path, get_expression_reference_image_path

    # 씬 레퍼런스 이미지 경로
    reference_image_path = None
    if use_reference_image:
        reference_image_path = get_reference_image_path(scene)

    # 표정 레퍼런스 이미지 경로 (expression이 Dict인 경우)
    expression_image_path = None
    if use_expression_reference and isinstance(expression, dict):
        expression_image_path = get_expression_reference_image_path(expression)

    # 프롬프트 생성 (레퍼런스 있으면 간단하게)
    if reference_image_path:
        prompt = build_prompt_from_db_simple(pose, scene, gender, expression)
    else:
        prompt = build_prompt_from_db(
            pose, scene, gender, expression, makeup, outfit_analysis
        )

    # generate_selfie 호출 (레퍼런스 이미지 전달)
    return generate_selfie(
        prompt=prompt,
        face_images=face_images,
        outfit_images=outfit_images,
        pose_reference=reference_image_path,  # 씬 레퍼런스를 포즈 레퍼런스로 사용
        bg_reference=None,
        expression_reference=expression_image_path,  # 표정 레퍼런스
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        temperature=temperature,
        api_key=api_key,
    )


def generate_batch_v3(
    face_images: List[Union[str, Path, Image.Image]],
    pose_category: str,
    scene_category: str,
    count: int = 3,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    gender: str = "female",
    expression="시크",  # str (카테고리) 또는 Dict (프리셋) 또는 List[Dict] (프리셋 리스트)
    expression_category: Optional[str] = None,  # 표정 카테고리 (랜덤 선택용)
    makeup: str = "natural",
    outfit_analysis: Optional[Dict] = None,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    use_reference_image: bool = True,
    use_expression_reference: bool = True,
    validator=None,
    max_retries: int = 2,
) -> List[Dict]:
    """
    DB 기반 배치 생성 (v3) - 카테고리에서 랜덤 조합

    Args:
        face_images: 얼굴 이미지 목록 (필수)
        pose_category: "전신" | "상반신" | "앉기" | "거울셀피"
        scene_category: "핫플카페" | "그래피티" | ...
        count: 생성할 이미지 수
        outfit_images: 착장 이미지 목록 (선택)
        gender: "female" | "male"
        expression: 카테고리 문자열("시크"), 프리셋 Dict, 또는 프리셋 List[Dict]
        expression_category: 표정 카테고리 (랜덤 선택용, "시크"|"러블리"|None=전체)
        makeup: 메이크업
        outfit_analysis: VLM 착장 분석 결과 (선택)
        aspect_ratio: 화면 비율
        resolution: 해상도
        temperature: 생성 온도
        api_key: Gemini API 키
        use_reference_image: 레퍼런스 이미지 사용 여부
        use_expression_reference: 표정 레퍼런스 이미지 사용 여부
        validator: SelfieValidator 인스턴스 (선택)
        max_retries: 검증 실패 시 재시도 횟수

    Returns:
        List[Dict]: 생성 결과 리스트
            [
                {
                    "image": PIL.Image,
                    "pose": pose_dict,
                    "scene": scene_dict,
                    "expression": expression_dict or str,
                    "score": float,
                    "passed": bool,
                    "attempts": int,
                },
                ...
            ]
    """
    from .db_loader import get_random_poses, get_random_scenes, get_random_expressions
    from .compatibility import get_compatible_scenes, is_compatible

    # 호환성 검증
    if not is_compatible(pose_category, scene_category):
        print(f"[ERROR] {pose_category}와 {scene_category}는 호환되지 않습니다.")
        return []

    # 호환되는 씬만 가져오기
    compatible_scenes = get_compatible_scenes(pose_category, scene_category)
    if not compatible_scenes:
        print(f"[ERROR] {scene_category}에서 호환되는 씬이 없습니다.")
        return []

    # 포즈 랜덤 선택
    poses = get_random_poses(pose_category, count)

    # 씬 랜덤 선택 (호환되는 씬에서)
    if count <= len(compatible_scenes):
        scenes = random.sample(compatible_scenes, count)
    else:
        scenes = []
        while len(scenes) < count:
            remaining = count - len(scenes)
            sample_size = min(remaining, len(compatible_scenes))
            scenes.extend(random.sample(compatible_scenes, sample_size))

    # 표정 프리셋 랜덤 선택 (expression_category가 있거나 expression이 str인 경우)
    expressions = None
    if expression_category is not None:
        # 카테고리에서 랜덤 선택
        expressions = get_random_expressions(expression_category, count)
    elif isinstance(expression, str):
        # 문자열이면 해당 카테고리에서 랜덤 선택 (시크/러블리 매핑)
        if expression in ["시크", "러블리"]:
            expressions = get_random_expressions(expression, count)
        else:
            # 지원하지 않는 카테고리면 전체에서 선택
            expressions = get_random_expressions(None, count)
    elif isinstance(expression, list):
        # 리스트면 그대로 사용
        expressions = expression
    elif isinstance(expression, dict):
        # 단일 프리셋이면 모든 이미지에 동일 적용
        expressions = [expression] * count

    results = []

    for i, (pose, scene) in enumerate(zip(poses, scenes)):
        # 표정 선택
        current_expression = expressions[i] if expressions else expression
        expr_id = (
            current_expression.get("id", "text")
            if isinstance(current_expression, dict)
            else current_expression
        )

        print(f"\n{'=' * 60}")
        print(
            f"[{i + 1}/{count}] Pose: {pose['id']} | Scene: {scene['id']} | Expression: {expr_id}"
        )
        print(f"{'=' * 60}")

        # API 키 처리
        if api_key is None:
            from core.api import _get_next_api_key

            current_api_key = _get_next_api_key()
        else:
            current_api_key = api_key

        # 생성 + 검증 루프
        best_image = None
        best_score = 0
        attempts = 0
        current_temp = temperature

        for attempt in range(max_retries + 1):
            attempts = attempt + 1
            print(f"  Attempt {attempts}/{max_retries + 1} (temp={current_temp:.2f})")

            image = generate_selfie_v3(
                face_images=face_images,
                pose=pose,
                scene=scene,
                outfit_images=outfit_images,
                gender=gender,
                expression=current_expression,
                makeup=makeup,
                outfit_analysis=outfit_analysis,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                temperature=current_temp,
                api_key=current_api_key,
                use_reference_image=use_reference_image,
                use_expression_reference=use_expression_reference,
            )

            if image is None:
                print(f"  [FAIL] Generation failed")
                current_temp = max(0.3, current_temp - 0.1)
                time.sleep(2)
                continue

            # 검증
            if validator:
                try:
                    validation_result = validator.validate(
                        generated_img=image,
                        face_images=face_images,
                    )
                    if hasattr(validation_result, "total_score"):
                        score = validation_result.total_score
                        passed = validation_result.passed
                    else:
                        score = validation_result.get("total_score", 0)
                        passed = validation_result.get("passed", False)

                    print(f"  Score: {score}/100 | {'PASS' if passed else 'FAIL'}")

                    if score > best_score:
                        best_image = image
                        best_score = score

                    if passed:
                        break

                except Exception as e:
                    print(f"  [WARN] Validation error: {e}")
                    if best_image is None:
                        best_image = image
                        best_score = 75  # 기본 점수
            else:
                # 검증 없으면 첫 성공 이미지 사용
                best_image = image
                best_score = 100
                break

            # 재시도 준비
            current_temp = max(0.3, current_temp - 0.1)
            time.sleep(2)

        results.append(
            {
                "image": best_image,
                "pose": pose,
                "scene": scene,
                "expression": current_expression,
                "score": best_score,
                "passed": best_score >= 80 or validator is None,
                "attempts": attempts,
            }
        )

    return results


def get_random_combinations(
    pose_category: str,
    scene_category: str,
    count: int = 3,
) -> List[Tuple[Dict, Dict]]:
    """
    카테고리에서 랜덤 포즈-씬 조합 생성

    Args:
        pose_category: 포즈 카테고리
        scene_category: 씬 카테고리
        count: 조합 개수

    Returns:
        [(pose, scene), ...] 튜플 리스트
    """
    from .db_loader import get_random_poses
    from .compatibility import get_compatible_scenes, is_compatible

    if not is_compatible(pose_category, scene_category):
        return []

    compatible_scenes = get_compatible_scenes(pose_category, scene_category)
    if not compatible_scenes:
        return []

    poses = get_random_poses(pose_category, count)

    if count <= len(compatible_scenes):
        scenes = random.sample(compatible_scenes, count)
    else:
        scenes = []
        while len(scenes) < count:
            remaining = count - len(scenes)
            sample_size = min(remaining, len(compatible_scenes))
            scenes.extend(random.sample(compatible_scenes, sample_size))

    return list(zip(poses, scenes))
