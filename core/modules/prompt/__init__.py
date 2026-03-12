"""
프롬프트 서브패키지

프롬프트 빌드에 필요한 매핑, 변환, 포매팅 유틸리티를 제공한다.

하위 모듈:
- mappings: STATE_TO_KOREAN, infer_category, format_logo_detail 등 매핑/포맷 유틸
- outfit_section: 착장 섹션 포매터 (korean_detailed/image_first/basic 모드)
- negative: 네거티브 프롬프트 빌더 (플루언트 API)
- camera_section: 촬영 세팅 섹션 빌더
- preservation: 보존 프롬프트 모듈 (배경 교체용)
- assembler: 통합 프롬프트 어셈블러 (마크다운 섹션 형식)
"""

# 매핑 유틸리티
from core.modules.prompt.mappings import (
    STATE_TO_KOREAN,
    GENDER_MAP,
    infer_category,
    format_logo_detail,
    format_critical_detail,
)

# 착장 섹션 포매터
from core.modules.prompt.outfit_section import (
    format_outfit_section,
)

# 네거티브 프롬프트 빌더
from core.modules.prompt.negative import (
    NegativePromptBuilder,
    BASE_NEGATIVES,
    BRAND_NEGATIVES,
    FRAMING_NEGATIVES,
    BLIND_SPOT_NEGATIVE_PATTERNS,
    extract_negatives_from_blind_spots,
    build_default_negative,
)

# 촬영 세팅 섹션 빌더
from core.modules.prompt.camera_section import (
    build_camera_section,
    build_camera_dict,
    get_framing_description,
    get_framing_short,
    should_describe_below_thigh,
)

# 보존 프롬프트 (배경 교체용)
from core.modules.prompt.preservation import (
    PreservationLevel,
    build_preservation_prompt,
    build_swap_instructions,
)

# 통합 프롬프트 어셈블러
from core.modules.prompt.assembler import (
    PromptResult,
    PromptAssembler,
)

__all__ = [
    # 매핑
    "STATE_TO_KOREAN",
    "GENDER_MAP",
    "infer_category",
    "format_logo_detail",
    "format_critical_detail",
    # 착장
    "format_outfit_section",
    # 네거티브
    "NegativePromptBuilder",
    "BASE_NEGATIVES",
    "BRAND_NEGATIVES",
    "FRAMING_NEGATIVES",
    "BLIND_SPOT_NEGATIVE_PATTERNS",
    "extract_negatives_from_blind_spots",
    "build_default_negative",
    # 카메라
    "build_camera_section",
    "build_camera_dict",
    "get_framing_description",
    "get_framing_short",
    "should_describe_below_thigh",
    # 보존
    "PreservationLevel",
    "build_preservation_prompt",
    "build_swap_instructions",
    # 어셈블러
    "PromptResult",
    "PromptAssembler",
]
