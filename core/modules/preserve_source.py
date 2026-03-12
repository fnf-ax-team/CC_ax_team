"""
보존 분석 모듈 (스왑 워크플로 공통)

소스 이미지에서 "보존할 요소"와 "변경할 요소"를 선언적으로 분리하고,
VLM으로 보존 대상만 상세 분석하는 통합 패턴.

4대 스왑 워크플로의 소스 이미지 분석을 하나의 인터페이스로 통합:
- 얼굴 교체: preserve=[pose, outfit, background, lighting], change=[face]
- 착장 스왑: preserve=[face, pose, background], change=[outfit]
- 포즈 변경: preserve=[face, outfit, background], change=[pose]
- 포즈 복사: preserve=[face, outfit, hair], change=[pose, background]

사용법:
    from core.modules.preserve_source import analyze_for_preservation

    result = analyze_for_preservation(
        source_image,
        api_key=key,
        preserve=["pose", "outfit", "background"],
        change=["face"],
    )
    print(result.pose_description)
    print(result.to_prompt_text())
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image

from core.modules.vlm_utils import vlm_call


# ============================================================
# 지원하는 요소 목록
# ============================================================

# 분석 가능한 전체 요소 집합
SUPPORTED_ELEMENTS = frozenset(
    {
        "face",
        "pose",
        "outfit",
        "background",
        "lighting",
        "hair",
        "body_type",
    }
)

# 요소별 VLM 프롬프트 지시문
# VLM에게 해당 요소를 어떻게 상세 서술할지 지정
_ELEMENT_INSTRUCTIONS: Dict[str, str] = {
    "face": (
        '"face_description": 얼굴형(둥근/타원/각진), 눈 모양과 크기, '
        "코 형태, 입술 두께, 턱선, 피부톤, 이마 비율, "
        "인물이 동일하게 재현되도록 모든 고유 특징을 빠짐없이 서술"
    ),
    "pose": (
        '"pose_description": stance(서있기/앉기/기대기/걷기), '
        "왼팔/오른팔 위치와 각도, 왼손/오른손 동작, "
        "왼다리/오른다리 각도, 무게중심, 체중 분배, "
        "카메라 앵글(아이레벨/로우앵글/하이앵글), "
        "프레이밍(전신/3/4/무릎위/허리위/바스트샷)"
    ),
    "outfit": (
        '"outfit_description": 각 착장 아이템별로 — '
        "아이템명, 색상(메인/서브), 소재, 패턴, "
        "로고(브랜드명/유형/위치/색상), 핏(오버사이즈/슬림 등), "
        "특이 디테일(지퍼/단추/주름/스티칭), "
        "코디 방법(넣어입기/크롭/어깨걸침 등)"
    ),
    "background": (
        '"background_description": 배경 장소(실내/실외/스튜디오), '
        "배경 요소(건물/벽/나무/하늘 등), "
        "색조(웜/쿨/뉴트럴), 깊이감, "
        "인물과 배경의 거리감, 배경 디테일"
    ),
    "lighting": (
        '"lighting_description": 광원 방향(시계 방향 표기), '
        "광원 높이(낮은/중간/높은), 경도(하드/소프트), "
        "색온도(웜/뉴트럴/쿨), 그림자 방향과 강도, "
        "하이라이트 위치, 역광/순광/측광 여부"
    ),
    "hair": (
        '"hair_description": 헤어 스타일(직모/웨이브/컬/업스타일), '
        "길이(숏/미디엄/롱), 색상(자연색/염색), "
        "질감(매끈/볼륨/건조), 가르마 방향, "
        "앞머리 유무, 액세서리(헤어밴드/핀 등)"
    ),
    "body_type": (
        '"body_type": 체형(슬림/보통/근육질/볼륨), '
        "어깨 너비, 상체/하체 비율, 키 느낌(작은/보통/큰), "
        "체형 특징이 동일하게 재현되도록 서술"
    ),
}


# ============================================================
# 결과 데이터클래스
# ============================================================


@dataclass
class PreservationResult:
    """
    보존 분석 결과.

    preserve/change 선언에 따라 분석된 각 요소의 상세 설명을 담는다.
    change 대상은 None으로 남는다.

    Attributes:
        preserve: 보존 요소 리스트 (입력값 그대로)
        change: 변경 요소 리스트 (입력값 그대로)
        face_description: 얼굴 상세 설명 (보존 대상일 때만)
        pose_description: 포즈 상세 설명
        outfit_description: 착장 상세 설명
        background_description: 배경 상세 설명
        lighting_description: 조명 상세 설명
        hair_description: 헤어 상세 설명
        body_type: 체형 설명
        physical_constraints: 물리적 제약 (포즈 변경 시)
        raw_response: VLM 원본 응답
    """

    # 입력 선언
    preserve: List[str] = field(default_factory=list)
    change: List[str] = field(default_factory=list)

    # 요소별 분석 결과 (보존 대상만 채워짐)
    face_description: Optional[str] = None
    pose_description: Optional[str] = None
    outfit_description: Optional[str] = None
    background_description: Optional[str] = None
    lighting_description: Optional[str] = None
    hair_description: Optional[str] = None
    body_type: Optional[str] = None

    # 확장 필드: 포즈 변경 시 물리적 제약
    physical_constraints: Optional[Dict[str, Any]] = None

    # VLM 원본 응답
    raw_response: Optional[Dict[str, Any]] = None

    def to_prompt_text(self) -> str:
        """
        보존된 요소들을 프롬프트 지시 텍스트로 포매팅.

        "PRESERVE EXACTLY:" 헤더 아래에 각 보존 요소를 [태그] 형태로 나열.
        None인 요소는 건너뛴다.

        Returns:
            프롬프트에 삽입할 보존 지시 텍스트
        """
        lines = ["PRESERVE EXACTLY:"]

        # 요소명 -> (필드값, 태그 라벨) 매핑
        _field_map = [
            ("face", self.face_description, "face"),
            ("hair", self.hair_description, "hair"),
            ("body_type", self.body_type, "body_type"),
            ("pose", self.pose_description, "pose"),
            ("outfit", self.outfit_description, "outfit"),
            ("background", self.background_description, "background"),
            ("lighting", self.lighting_description, "lighting"),
        ]

        for element, value, tag in _field_map:
            if element in self.preserve and value:
                lines.append(f"[{tag}] {value}")

        # 물리적 제약 (있으면 추가)
        if self.physical_constraints:
            constraints = self.physical_constraints
            constraint_lines = []

            support_req = constraints.get("support_required", False)
            if support_req:
                support_type = constraints.get("support_type", "")
                support_dir = constraints.get("support_direction", "")
                constraint_lines.append(
                    f"  - support needed: {support_type} at {support_dir}"
                )

            balance = constraints.get("balance_type", "")
            if balance:
                constraint_lines.append(f"  - balance: {balance}")

            range_of_motion = constraints.get("range_of_motion", "")
            if range_of_motion:
                constraint_lines.append(f"  - range of motion: {range_of_motion}")

            if constraint_lines:
                lines.append("[physical_constraints]")
                lines.extend(constraint_lines)

        # 변경 요소 명시
        if self.change:
            change_tags = ", ".join(self.change)
            lines.append(f"\nCHANGE: {change_tags}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        직렬화용 dict 변환.

        JSON 저장/로깅에 사용.

        Returns:
            모든 필드를 포함한 dict
        """
        return {
            "preserve": self.preserve,
            "change": self.change,
            "face_description": self.face_description,
            "pose_description": self.pose_description,
            "outfit_description": self.outfit_description,
            "background_description": self.background_description,
            "lighting_description": self.lighting_description,
            "hair_description": self.hair_description,
            "body_type": self.body_type,
            "physical_constraints": self.physical_constraints,
            "raw_response": self.raw_response,
        }

    def get_preserved_elements(self) -> Dict[str, str]:
        """
        보존 요소 중 실제로 값이 있는 것만 반환.

        Returns:
            {요소명: 설명} dict (값이 None인 요소 제외)
        """
        result = {}

        _field_map = {
            "face": self.face_description,
            "pose": self.pose_description,
            "outfit": self.outfit_description,
            "background": self.background_description,
            "lighting": self.lighting_description,
            "hair": self.hair_description,
            "body_type": self.body_type,
        }

        for element in self.preserve:
            value = _field_map.get(element)
            if value:
                result[element] = value

        return result


# ============================================================
# 요소별 기본값 (VLM 실패 시 폴백)
# ============================================================

_ELEMENT_DEFAULTS: Dict[str, str] = {
    "face_description": "Korean female, oval face, natural skin tone",
    "pose_description": "Standing naturally, arms relaxed at sides, weight centered",
    "outfit_description": "Casual outfit, standard fit",
    "background_description": "Neutral studio background",
    "lighting_description": "Soft studio lighting, neutral color temperature",
    "hair_description": "Dark brown, straight, medium length",
    "body_type": "Average build, proportional",
}


# ============================================================
# VLM 프롬프트 빌더
# ============================================================


def _build_analysis_prompt(
    preserve: List[str],
    change: List[str],
    include_physical_constraints: bool = False,
) -> str:
    """
    보존/변경 선언에 따라 VLM 분석 프롬프트를 동적 구성.

    보존 대상만 상세 서술을 요청하고,
    변경 대상은 명시적으로 분석 제외를 지시.

    Args:
        preserve: 보존할 요소 리스트
        change: 변경할 요소 리스트
        include_physical_constraints: 물리적 제약 분석 포함 여부

    Returns:
        VLM에게 전달할 프롬프트 텍스트
    """
    # 보존 요소 분석 지시 구성
    preserve_instructions = []
    for element in preserve:
        instruction = _ELEMENT_INSTRUCTIONS.get(element)
        if instruction:
            preserve_instructions.append(f"  {instruction}")

    preserve_block = ",\n".join(preserve_instructions)

    # 변경 요소 제외 지시
    change_list = ", ".join(change) if change else "없음"

    # 물리적 제약 추가 필드 (포즈 변경 워크플로용)
    physical_constraints_field = ""
    if include_physical_constraints:
        physical_constraints_field = """,
  "physical_constraints": {
    "support_required": true/false (현재 포즈가 지지대 필요 여부),
    "support_type": "wall/chair/bench/railing/steps/floor/none",
    "support_direction": "behind/left/right/below/none",
    "balance_type": "centered/shifted_left/shifted_right/leaning",
    "range_of_motion": "자유로운 포즈 변경 가능 범위 설명"
  }"""

    prompt = f"""이 이미지에서 스왑(교체) 작업을 위해 보존할 요소를 상세 분석하세요.

== 분석 규칙 ==
- 보존 대상 요소만 정밀하게 서술하세요 (변경 대상은 분석하지 마세요)
- 각 요소는 재현에 충분한 수준으로 구체적으로 서술하세요
- 한국어로 서술하되, 브랜드명/영어 고유명사는 영어 유지

== 변경 대상 (분석 제외) ==
{change_list}

== 보존 대상 (상세 분석 필수) ==

JSON 형식으로 출력:
```json
{{
{preserve_block}{physical_constraints_field}
}}
```

JSON만 출력하세요."""

    return prompt


# ============================================================
# 메인 분석 함수
# ============================================================


def analyze_for_preservation(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
    preserve: Optional[List[str]] = None,
    change: Optional[List[str]] = None,
    include_physical_constraints: bool = False,
    temperature: float = 0.1,
    max_image_size: int = 1024,
) -> PreservationResult:
    """
    소스 이미지에서 보존할 요소를 VLM으로 분석.

    사용자가 preserve/change를 선언하면, 보존 대상만 VLM으로 상세 분석하여
    PreservationResult에 담아 반환한다.

    Args:
        source_image: 소스 이미지 (경로 또는 PIL Image)
        api_key: Gemini API 키 (None이면 자동 로테이션)
        preserve: 보존할 요소 리스트 (예: ["face", "pose", "outfit"])
        change: 변경할 요소 리스트 (예: ["background"])
        include_physical_constraints: 물리적 제약 분석 포함 (포즈 변경 워크플로용)
        temperature: VLM 온도 (낮을수록 정확, 기본 0.1)
        max_image_size: VLM 전달 최대 이미지 크기

    Returns:
        PreservationResult 객체 (보존 요소만 값이 채워짐)

    Raises:
        ValueError: preserve/change에 지원하지 않는 요소가 포함된 경우

    사용 예시:
        # 얼굴 교체: 얼굴만 변경
        result = analyze_for_preservation(
            img, api_key=key,
            preserve=["pose", "outfit", "background", "lighting"],
            change=["face"],
        )

        # 착장 스왑: 착장만 변경
        result = analyze_for_preservation(
            img, api_key=key,
            preserve=["face", "pose", "background"],
            change=["outfit"],
        )

        # 포즈 변경: 포즈만 변경 (물리적 제약 포함)
        result = analyze_for_preservation(
            img, api_key=key,
            preserve=["face", "outfit", "background"],
            change=["pose"],
            include_physical_constraints=True,
        )

        # 포즈 복사: 정체성만 보존 (포즈/배경은 변경)
        result = analyze_for_preservation(
            img, api_key=key,
            preserve=["face", "outfit", "hair"],
            change=["pose", "background"],
        )
    """
    # 기본값 설정
    if preserve is None:
        preserve = ["face", "pose", "outfit", "background"]
    if change is None:
        change = []

    # 입력 검증
    all_elements = set(preserve) | set(change)
    unsupported = all_elements - SUPPORTED_ELEMENTS
    if unsupported:
        raise ValueError(
            f"지원하지 않는 요소: {unsupported}. "
            f"사용 가능: {sorted(SUPPORTED_ELEMENTS)}"
        )

    # preserve와 change 중복 검사
    overlap = set(preserve) & set(change)
    if overlap:
        raise ValueError(
            f"preserve와 change에 동시에 포함된 요소: {overlap}. "
            "각 요소는 보존 또는 변경 중 하나만 선택하세요."
        )

    # API 키 자동 로드
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # VLM 프롬프트 구성
    prompt = _build_analysis_prompt(
        preserve=preserve,
        change=change,
        include_physical_constraints=include_physical_constraints,
    )

    # VLM 호출
    raw_response = vlm_call(
        api_key=api_key,
        prompt=prompt,
        images=[source_image],
        temperature=temperature,
        max_image_size=max_image_size,
    )

    # 결과 파싱 + PreservationResult 구성
    result = _parse_to_result(
        raw_response=raw_response,
        preserve=preserve,
        change=change,
    )

    return result


# ============================================================
# 응답 파싱
# ============================================================


def _parse_to_result(
    raw_response: Dict[str, Any],
    preserve: List[str],
    change: List[str],
) -> PreservationResult:
    """
    VLM 응답을 PreservationResult로 변환.

    보존 대상 요소만 응답에서 추출하고, 실패 시 기본값으로 폴백.

    Args:
        raw_response: VLM 응답 dict
        preserve: 보존 요소 리스트
        change: 변경 요소 리스트

    Returns:
        PreservationResult 객체
    """
    # VLM 에러 발생 시 전체 기본값 폴백
    if "error" in raw_response:
        print(f"[preserve_source] VLM 에러, 기본값 사용: {raw_response['error']}")
        return _build_fallback_result(preserve, change, raw_response)

    # 응답에서 각 요소 추출 (요소명_description 키 또는 요소명 키)
    result = PreservationResult(
        preserve=list(preserve),
        change=list(change),
        raw_response=raw_response,
    )

    # 요소별 필드 매핑 (응답 키 -> 결과 필드)
    _response_key_map = {
        "face": "face_description",
        "pose": "pose_description",
        "outfit": "outfit_description",
        "background": "background_description",
        "lighting": "lighting_description",
        "hair": "hair_description",
        "body_type": "body_type",
    }

    for element in preserve:
        field_name = _response_key_map.get(element)
        if not field_name:
            continue

        # VLM 응답에서 값 추출 (여러 키 형태 시도)
        value = (
            raw_response.get(field_name)  # face_description
            or raw_response.get(element)  # face
            or raw_response.get(f"{element}_desc")  # face_desc
        )

        if value:
            # dict면 문자열로 변환
            if isinstance(value, dict):
                value = _dict_to_description(value)
            elif isinstance(value, list):
                value = ", ".join(str(v) for v in value)

            setattr(result, field_name, str(value))
        else:
            # 응답에 없으면 기본값 폴백
            default = _ELEMENT_DEFAULTS.get(field_name)
            if default:
                setattr(result, field_name, default)
                print(f"[preserve_source] '{element}' 응답 없음, " f"기본값 사용")

    # 물리적 제약 추출 (있으면)
    physical = raw_response.get("physical_constraints")
    if physical and isinstance(physical, dict):
        result.physical_constraints = physical

    return result


def _build_fallback_result(
    preserve: List[str],
    change: List[str],
    raw_response: Dict[str, Any],
) -> PreservationResult:
    """
    VLM 호출 실패 시 기본값으로 채운 PreservationResult 반환.

    Args:
        preserve: 보존 요소 리스트
        change: 변경 요소 리스트
        raw_response: VLM 원본 응답 (에러 포함)

    Returns:
        기본값으로 채워진 PreservationResult
    """
    _response_key_map = {
        "face": "face_description",
        "pose": "pose_description",
        "outfit": "outfit_description",
        "background": "background_description",
        "lighting": "lighting_description",
        "hair": "hair_description",
        "body_type": "body_type",
    }

    result = PreservationResult(
        preserve=list(preserve),
        change=list(change),
        raw_response=raw_response,
    )

    for element in preserve:
        field_name = _response_key_map.get(element)
        if field_name:
            default = _ELEMENT_DEFAULTS.get(field_name, "")
            setattr(result, field_name, default)

    return result


def _dict_to_description(d: Dict[str, Any], separator: str = ", ") -> str:
    """
    dict를 자연어 설명 문자열로 변환.

    {"color": "white", "brand": "MLB"} -> "color: white, brand: MLB"

    Args:
        d: 변환할 dict
        separator: 항목 간 구분자

    Returns:
        포매팅된 문자열
    """
    parts = []
    for key, value in d.items():
        if isinstance(value, dict):
            # 중첩 dict -> 재귀
            nested = _dict_to_description(value, separator="; ")
            parts.append(f"{key}: ({nested})")
        elif isinstance(value, list):
            list_str = ", ".join(str(v) for v in value)
            parts.append(f"{key}: [{list_str}]")
        else:
            parts.append(f"{key}: {value}")
    return separator.join(parts)


# ============================================================
# 편의 함수: 워크플로 프리셋
# ============================================================


def analyze_for_face_swap(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PreservationResult:
    """
    얼굴 교체용 보존 분석 프리셋.

    얼굴만 변경, 나머지(포즈/착장/배경/조명) 전부 보존.

    Args:
        source_image: 소스 이미지
        api_key: Gemini API 키

    Returns:
        PreservationResult (face_description은 None)
    """
    return analyze_for_preservation(
        source_image,
        api_key=api_key,
        preserve=["pose", "outfit", "background", "lighting"],
        change=["face"],
    )


def analyze_for_outfit_swap(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PreservationResult:
    """
    착장 스왑용 보존 분석 프리셋.

    착장만 변경, 나머지(얼굴/포즈/배경) 전부 보존.

    Args:
        source_image: 소스 이미지
        api_key: Gemini API 키

    Returns:
        PreservationResult (outfit_description은 None)
    """
    return analyze_for_preservation(
        source_image,
        api_key=api_key,
        preserve=["face", "pose", "background"],
        change=["outfit"],
    )


def analyze_for_pose_change(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PreservationResult:
    """
    포즈 변경용 보존 분석 프리셋.

    포즈만 변경, 나머지(얼굴/착장/배경) 보존.
    물리적 제약(지지대/균형/동작 범위) 분석 포함.

    Args:
        source_image: 소스 이미지
        api_key: Gemini API 키

    Returns:
        PreservationResult (pose_description은 None, physical_constraints 포함)
    """
    return analyze_for_preservation(
        source_image,
        api_key=api_key,
        preserve=["face", "outfit", "background"],
        change=["pose"],
        include_physical_constraints=True,
    )


def analyze_for_pose_copy(
    source_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PreservationResult:
    """
    포즈 복사용 보존 분석 프리셋.

    인물 정체성(얼굴/착장/헤어)만 보존, 포즈와 배경은 변경.
    레퍼런스 이미지의 포즈를 적용할 때 소스의 정체성을 추출.

    Args:
        source_image: 소스 이미지
        api_key: Gemini API 키

    Returns:
        PreservationResult (pose/background는 None)
    """
    return analyze_for_preservation(
        source_image,
        api_key=api_key,
        preserve=["face", "outfit", "hair"],
        change=["pose", "background"],
    )


__all__ = [
    "SUPPORTED_ELEMENTS",
    "PreservationResult",
    "analyze_for_preservation",
    # 워크플로 프리셋
    "analyze_for_face_swap",
    "analyze_for_outfit_swap",
    "analyze_for_pose_change",
    "analyze_for_pose_copy",
]
