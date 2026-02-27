"""
AI 인플루언서 이미지 생성 모듈 v2.0

이미지 레퍼런스 기반 생성 (텍스트 프롬프트 최소화)
- 포즈/표정 → 이미지 레퍼런스
- 얼굴 → 다각도 이미지 (3-5장)
- 착장 → 이미지 (선택)
- 배경 → 이미지 (선택)
"""

import time
import warnings
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL
from .character import Character


# 프리셋 이미지 기본 경로
PRESET_IMAGE_BASE = Path(
    r"C:\Users\AC1060\OneDrive - F&F (1)\바탕 화면\2025\260219_AI인플\OneDrive_2026-02-19 (2)"
)


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def _load_image(img_input: Union[str, Path, Image.Image]) -> Image.Image:
    """이미지 로드 (경로 또는 PIL Image)"""
    if isinstance(img_input, Image.Image):
        return img_input.convert("RGB") if img_input.mode != "RGB" else img_input
    return Image.open(img_input).convert("RGB")


def _get_preset_image_path(preset_type: str, preset_id: str) -> Optional[Path]:
    """
    프리셋 ID로 이미지 경로 반환

    Args:
        preset_type: "pose" | "expression" | "background"
        preset_id: 프리셋 ID (예: "전신_05", "시크_02", "핫플카페_08")

    Returns:
        이미지 파일 경로
    """
    # 프리셋 타입별 폴더 매핑
    folder_map = {
        "pose": {
            "전신": "3. 포즈/1. 전신",
            "상반신": "3. 포즈/2. 상반신",
            "앉기": "3. 포즈/3. 앉아있는",
            "거울셀피": "3. 포즈/4. 거울셀피",
        },
        "expression": {
            "시크": "2. 표정/1. 시크",
            "러블리": "2. 표정/2. 러블리",
        },
        "background": {
            "핫플카페": "4. 배경/1. 핫플카페",
            "그래피티": "4. 배경/2. 그래피티",
            "철문": "4. 배경/3. 철문",
            "기타문": "4. 배경/4. 기타 문",
            "해외스트릿": "4. 배경/5. 해외스트릿",
            "힙라이프": "4. 배경/6. 힙스트릿 라이프스타일",
            "지하철": "4. 배경/7. 지하철",
            "엘레베이터": "4. 배경/8. 엘레베이터",
            "횡단보도": "4. 배경/9. 횡단보도",
        },
    }

    # 파일명 프리픽스 매핑
    prefix_map = {
        "pose": {
            "전신": "전신",
            "상반신": "상반신",
            "앉기": "앉아있는",
            "거울셀피": "거울셀피",
        },
        "expression": {
            "시크": "시크",
            "러블리": "러블리",
        },
        "background": {
            "핫플카페": "핫플 카페",
            "그래피티": "그래피티",
            "철문": "철문",
            "기타문": "기타 문",
            "해외스트릿": "해외 스트릿",
            "힙라이프": "힙 스트릿 라이프 스타일",
            "지하철": "지하철",
            "엘레베이터": "엘리베이터",
            "횡단보도": "횡단보도",
        },
    }

    # 프리셋 ID 파싱 (예: "전신_05" -> category="전신", num=5)
    parts = preset_id.rsplit("_", 1)
    if len(parts) != 2:
        return None

    category = parts[0]
    try:
        num = int(parts[1])
    except ValueError:
        return None

    # 폴더 경로 찾기
    type_folders = folder_map.get(preset_type, {})
    folder = type_folders.get(category)
    if not folder:
        return None

    # 파일명 프리픽스 찾기
    type_prefixes = prefix_map.get(preset_type, {})
    prefix = type_prefixes.get(category, category)

    # 실제 파일 찾기 (확장자 다양)
    base_path = PRESET_IMAGE_BASE / folder
    for ext in [".png", ".jpeg", ".jpg", ".webp"]:
        file_path = base_path / f"{prefix} ({num}){ext}"
        if file_path.exists():
            return file_path

    return None


def generate_ai_influencer(
    character: Character,
    pose_preset: str = None,
    pose_image: Union[str, Path, Image.Image] = None,
    expression_preset: str = None,
    expression_image: Union[str, Path, Image.Image] = None,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    background_preset: str = None,
    background_image: Union[str, Path, Image.Image] = None,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    temperature: float = 0.5,
    api_key: Optional[str] = None,
    additional_prompt: str = None,  # 추가 프롬프트 (포즈/표정/배경 텍스트 설명)
) -> Optional[Image.Image]:
    """
    AI 인플루언서 이미지 생성 v2.0 (이미지 레퍼런스 기반)

    Args:
        character: 캐릭터 객체 (얼굴 이미지 자동 로드)
        pose_preset: 포즈 프리셋 ID (예: "전신_05")
        pose_image: 포즈 이미지 직접 제공 (preset보다 우선)
        expression_preset: 표정 프리셋 ID (예: "시크_02") - 선택적
        expression_image: 표정 이미지 직접 제공 - 선택적
        outfit_images: 착장 이미지 목록 (선택)
        background_preset: 배경 프리셋 ID (예: "핫플카페_08")
        background_image: 배경 이미지 직접 제공 (preset보다 우선)
        aspect_ratio: 화면 비율 (기본 9:16)
        resolution: 해상도 (기본 2K)
        temperature: 생성 온도 (기본 0.5)
        api_key: Gemini API 키

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
    parts = []

    # 1. 프롬프트 구성 (역할 설명 + 추가 프롬프트)
    prompt_text = _build_simple_prompt(
        has_pose=(pose_preset is not None or pose_image is not None),
        has_expression=(expression_preset is not None or expression_image is not None),
        has_outfit=(outfit_images is not None and len(outfit_images) > 0),
        has_background=(background_preset is not None or background_image is not None),
        additional_prompt=additional_prompt,  # 추가 프롬프트 전달
    )
    parts.append(types.Part(text=prompt_text))

    # 2. 포즈 레퍼런스 이미지
    pose_img = None
    if pose_image:
        pose_img = _load_image(pose_image)
    elif pose_preset:
        pose_path = _get_preset_image_path("pose", pose_preset)
        if pose_path:
            pose_img = _load_image(pose_path)

    if pose_img:
        parts.append(types.Part(text="[POSE REFERENCE]"))
        parts.append(pil_to_part(pose_img))

    # 3. 표정 레퍼런스 (포즈와 별도로 항상 전송)
    expr_img = None
    if expression_image:
        expr_img = _load_image(expression_image)
    elif expression_preset:
        expr_path = _get_preset_image_path("expression", expression_preset)
        if expr_path:
            expr_img = _load_image(expr_path)

    if expr_img:
        parts.append(types.Part(text="[EXPRESSION REFERENCE]"))
        parts.append(pil_to_part(expr_img))

    # 4. 얼굴 이미지 (캐릭터에서 - 여러 장)
    face_images = character.face_images
    for i, face_path in enumerate(face_images):
        img = Image.open(face_path).convert("RGB")
        face_type = _get_face_type(face_path.name)
        parts.append(types.Part(text=f"[FACE {i+1}] {face_type}"))
        parts.append(pil_to_part(img))

    # 5. 착장 이미지 (선택적)
    if outfit_images:
        for i, img_input in enumerate(outfit_images):
            img = _load_image(img_input)
            parts.append(types.Part(text=f"[OUTFIT {i+1}]"))
            parts.append(pil_to_part(img))

    # 6. 배경 이미지 (선택적)
    bg_img = None
    if background_image:
        bg_img = _load_image(background_image)
    elif background_preset:
        bg_path = _get_preset_image_path("background", background_preset)
        if bg_path:
            bg_img = _load_image(bg_path)

    if bg_img:
        parts.append(types.Part(text="[BACKGROUND REFERENCE]"))
        parts.append(pil_to_part(bg_img))

    # API 호출 (재시도 로직)
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
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

            print("[AIInfluencer] API 응답에 이미지 없음")
            return None

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            if not is_retryable:
                if "safety" in error_str or "blocked" in error_str:
                    print(f"[AIInfluencer] Safety Block: {e}")
                elif "401" in error_str or "auth" in error_str:
                    print(f"[AIInfluencer] Auth Error: {e}")
                else:
                    print(f"[AIInfluencer] 생성 실패: {e}")
                return None

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[AIInfluencer] Retry {attempt + 1}/{max_retries} - {wait_time}초 대기"
                )
                time.sleep(wait_time)
            else:
                print(f"[AIInfluencer] 최대 재시도 횟수 초과: {e}")

    return None


def _build_simple_prompt(
    has_pose: bool,
    has_expression: bool,
    has_outfit: bool,
    has_background: bool,
    additional_prompt: str = None,
) -> str:
    """프롬프트 생성 (이미지 역할 설명 + 추가 프롬프트)"""

    lines = []

    # 추가 프롬프트가 있으면 먼저 추가 (포즈/표정/배경 텍스트 설명)
    if additional_prompt:
        lines.append("[SCENE DESCRIPTION]")
        lines.append("")
        lines.append(additional_prompt)
        lines.append("")

    lines.append("[IMAGE ROLES]")
    lines.append("")

    # 포즈 레퍼런스
    if has_pose:
        lines.extend(
            [
                "POSE REFERENCE:",
                "- Copy EXACT pose, body position, camera angle, framing",
                "- Ignore face/outfit/background from this image",
                "",
            ]
        )

    # 표정 레퍼런스 (포즈와 별도)
    if has_expression:
        lines.extend(
            [
                "EXPRESSION REFERENCE:",
                "- Copy EXACT expression (eyes, mouth, mood, vibe)",
                "- Ignore face identity from this image",
                "",
            ]
        )

    # 얼굴 이미지 설명
    lines.append("FACE images: Use this person's face")
    if has_expression:
        lines.append("- Apply expression style from EXPRESSION REFERENCE")
    lines.append("")

    if has_outfit:
        lines.extend(
            [
                "OUTFIT images: Use this outfit exactly",
                "- Copy colors, logos, details",
                "",
            ]
        )

    if has_background:
        lines.extend(
            [
                "BACKGROUND REFERENCE: Use this background",
                "- Ignore any person in background image",
                "",
            ]
        )

    return "\n".join(lines)


def _get_face_type(filename: str) -> str:
    """파일명에서 얼굴 타입 추론"""
    filename_lower = filename.lower()
    if "front" in filename_lower or "정면" in filename_lower:
        return "정면"
    elif "side" in filename_lower or "측면" in filename_lower:
        return "측면"
    elif "smile" in filename_lower or "미소" in filename_lower:
        return "미소"
    elif "angle" in filename_lower:
        return "다른 앵글"
    else:
        return "참조"


def generate_with_validation(
    character: Character,
    pose_preset: str = None,
    pose_image: Union[str, Path, Image.Image] = None,
    expression_preset: str = None,
    expression_image: Union[str, Path, Image.Image] = None,
    outfit_images: Optional[List[Union[str, Path, Image.Image]]] = None,
    background_preset: str = None,
    background_image: Union[str, Path, Image.Image] = None,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    aspect_ratio: str = "9:16",
    resolution: str = "2K",
    initial_temperature: float = 0.5,
    validator=None,
) -> Dict[str, Any]:
    """
    생성 + 검증 + 재생성 루프

    .. deprecated::
        이 함수는 VLM 분석 없이 단순 라벨만 사용합니다.
        대신 ``core.ai_influencer.pipeline.generate_full_pipeline()``을 사용하세요.
        generate_full_pipeline()은 8단계 VLM 분석 + 검증+재생성 루프를 모두 포함합니다.

    Returns:
        dict: {
            "image": PIL.Image,
            "score": float,
            "passed": bool,
            "attempts": int,
            "history": List[dict]
        }
    """
    warnings.warn(
        "generate_with_validation()은 VLM 분석 없이 단순 라벨만 사용합니다. "
        "대신 core.ai_influencer.pipeline.generate_full_pipeline()을 사용하세요.",
        DeprecationWarning,
        stacklevel=2,
    )
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
        image = generate_ai_influencer(
            character=character,
            pose_preset=pose_preset,
            pose_image=pose_image,
            expression_preset=expression_preset,
            expression_image=expression_image,
            outfit_images=outfit_images,
            background_preset=background_preset,
            background_image=background_image,
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

        # 2. 검증
        if validator is not None:
            try:
                validation_result = validator.validate(
                    generated_img=image,
                    character=character,
                )

                if hasattr(validation_result, "total_score"):
                    score = validation_result.total_score
                    passed = validation_result.passed
                else:
                    score = validation_result.get("total_score", 0)
                    passed = validation_result.get("passed", False)

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
                if best_image is None:
                    best_image = image
        else:
            # validator 없으면 첫 성공 이미지 반환
            best_image = image
            best_score = 100
            history.append(
                {
                    "attempt": attempt + 1,
                    "temperature": current_temp,
                    "total_score": 100,
                    "passed": True,
                    "note": "No validator provided",
                }
            )
            break

        # 3. 재시도 준비 (온도 낮추기)
        if attempt < max_retries:
            current_temp = max(0.2, current_temp - 0.1)
            time.sleep(2)

    # 최종 결과
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
