"""
촬영 세팅(카메라) 섹션 빌더

브랜드컷/인플루언서의 촬영 섹션 빌드 로직을 통합:
- 프레이밍, 앵글, 높이, 렌즈, 조리개 설정
- PoseAnalysisResult에서 자동 추출 가능
- 마크다운 섹션 형식 출력 (## [촬영_세팅])

원본:
- core.brandcut.prompt_builder_v2._build_camera_section() / _build_camera_section_text()
- core.ai_influencer.prompt_builder.build_schema_prompt() 촬영_세팅 섹션
"""

from typing import Optional, Union


# ============================================================
# 프레이밍 설명 매핑
# 원본: influencer prompt_builder._FRAMING_DESCRIPTIONS
# ============================================================

FRAMING_DESCRIPTIONS = {
    "ECU": "Extreme close-up: only face fills the frame",
    "CU": "Close-up: face and neck, shoulders barely visible",
    "MCU": "Medium close-up: head to mid-chest",
    "MS": "Medium shot: head to waist, frame ends at belt line",
    "MFS": "Cowboy shot: head to mid-thigh. Frame edge cuts through upper legs. Knees, calves, and feet are NOT in the image",
    "FS": "Full shot: entire body from head to toe, feet on ground",
    "WS": "Wide shot: full body plus surrounding environment",
}

# 프레이밍 한줄 설명 (프롬프트 첫줄용)
# 원본: influencer prompt_builder._get_framing_short()
FRAMING_SHORT = {
    "ECU": "extreme close-up, face only",
    "CU": "close-up, face and neck",
    "MCU": "medium close-up, head to chest",
    "MS": "medium shot, head to waist",
    "MFS": "cowboy shot, head to mid-thigh, NO knees/feet/shoes visible",
    "FS": "full shot, head to toe",
    "WS": "wide shot, full body + environment",
}


def get_framing_description(framing: str) -> str:
    """프레이밍 코드를 상세 설명 텍스트로 변환"""
    return FRAMING_DESCRIPTIONS.get((framing or "FS").upper(), framing)


def get_framing_short(framing: str) -> str:
    """프레이밍 코드를 한줄 설명으로 변환 (프롬프트 첫줄용)"""
    return FRAMING_SHORT.get((framing or "FS").upper(), framing)


def should_describe_below_thigh(framing: str) -> bool:
    """프레이밍에서 무릎 이하가 보이는지 여부. FS/WS만 True."""
    return (framing or "FS").upper() in ("FS", "WS")


# ============================================================
# 카메라 높이 변환 헬퍼
# 원본: brandcut prompt_builder_v2._build_camera_section() 높이 로직
# ============================================================


def _normalize_camera_height(height_raw: str) -> str:
    """카메라 높이 문자열을 한글 표준으로 정규화"""
    if not height_raw:
        return "눈높이"

    lower = height_raw.lower()
    if "low" in lower or "로우" in lower:
        return "로우앵글"
    elif "high" in lower or "하이" in lower:
        return "하이앵글"
    else:
        return "눈높이"


def _normalize_framing(framing_raw: str, default: str = "MS") -> str:
    """프레이밍 문자열을 표준 코드로 정규화"""
    if not framing_raw:
        return default

    upper = framing_raw.upper()
    # 이미 표준 코드면 그대로
    if upper in FRAMING_DESCRIPTIONS:
        return upper

    # 키워드 기반 추론
    lower = framing_raw.lower()
    if "full" in lower or "전신" in lower:
        return "FS"
    elif "knee" in lower or "cowboy" in lower:
        return "MFS"
    elif "close" in lower and "medium" not in lower:
        return "CU"
    elif "wide" in lower:
        return "WS"
    elif "waist" in lower or "허리" in lower:
        return "MS"

    return default


# ============================================================
# 메인 함수
# ============================================================


def build_camera_section(
    framing: Optional[str] = None,
    angle: Optional[str] = None,
    height: Optional[str] = None,
    lens: Optional[str] = None,
    aperture: Optional[str] = None,
    composition: Optional[str] = None,
    pose_result=None,
) -> str:
    """
    촬영 세팅 섹션을 마크다운 형식으로 빌드.

    직접 값을 전달하거나, pose_result(PoseAnalysisResult)에서 자동 추출 가능.
    직접 전달한 값이 우선.

    Args:
        framing: 프레이밍 코드 (예: "FS", "MFS", "MS")
        angle: 촬영 앵글 (예: "정면", "3/4측면")
        height: 카메라 높이 (예: "눈높이", "로우앵글")
        lens: 렌즈 (예: "50mm", "85mm")
        aperture: 조리개 (예: "f/2.8")
        composition: 구도 (예: "중앙")
        pose_result: PoseAnalysisResult 객체 (선택, 자동 추출용)

    Returns:
        마크다운 형식의 촬영 세팅 섹션 텍스트
    """
    # PoseAnalysisResult에서 값 추출 (직접 전달한 값이 우선)
    if pose_result is not None:
        if framing is None:
            framing = getattr(pose_result, "framing", None) or "MFS"
        if angle is None:
            angle = getattr(pose_result, "camera_angle", None)
        if height is None:
            height = getattr(pose_result, "camera_height", None)

    # 기본값 설정
    framing = _normalize_framing(framing or "MS")
    angle = angle or "3/4측면"
    height = _normalize_camera_height(height or "")
    lens = lens or "50mm"
    composition = composition or "중앙"

    # 마크다운 섹션 빌드
    lines = ["## [촬영_세팅]"]
    lines.append(f"- 프레이밍: {framing} -- {get_framing_short(framing)}")
    lines.append(f"- 앵글: {angle}")
    lines.append(f"- 높이: {height}")
    lines.append(f"- 렌즈: {lens}")
    if aperture:
        lines.append(f"- 조리개: {aperture}")
    lines.append(f"- 구도: {composition}")

    return "\n".join(lines)


def build_camera_dict(
    framing: Optional[str] = None,
    angle: Optional[str] = None,
    height: Optional[str] = None,
    lens: Optional[str] = None,
    pose_result=None,
    user_options: Optional[dict] = None,
) -> dict:
    """
    촬영 섹션을 dict 형태로 반환 (JSON 스키마용).

    원본: brandcut prompt_builder_v2._build_camera_section()

    Args:
        framing: 프레이밍 코드
        angle: 앵글
        height: 높이
        lens: 렌즈
        pose_result: PoseAnalysisResult (자동 추출용)
        user_options: 사용자 옵션 dict (폴백용)

    Returns:
        {"프레이밍": ..., "렌즈": ..., "앵글": ..., "높이": ...}
    """
    user_options = user_options or {}

    # PoseAnalysisResult에서 추출
    if pose_result is not None:
        _framing = framing or getattr(pose_result, "framing", None)
        _angle = angle or getattr(pose_result, "camera_angle", None)
        _height = height or getattr(pose_result, "camera_height", None)
    else:
        _framing = framing
        _angle = angle
        _height = height

    return {
        "프레이밍": _normalize_framing(
            _framing or user_options.get("촬영.프레이밍", "MS")
        ),
        "렌즈": lens or user_options.get("촬영.렌즈", "50mm"),
        "앵글": _angle or user_options.get("촬영.앵글", "3/4측면"),
        "높이": _normalize_camera_height(_height or user_options.get("촬영.높이", "")),
    }


__all__ = [
    "build_camera_section",
    "build_camera_dict",
    "get_framing_description",
    "get_framing_short",
    "should_describe_below_thigh",
    "FRAMING_DESCRIPTIONS",
    "FRAMING_SHORT",
]
