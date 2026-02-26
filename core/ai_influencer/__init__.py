"""
AI 인플루언서 이미지 생성 모듈 v2.1

이미지 레퍼런스 기반 생성 (텍스트 프롬프트 최소화)
- 캐릭터 관리 (등록된 얼굴 이미지 로드 - 3~5장)
- 프리셋 이미지 연동 (포즈, 표정, 배경)
- 얼굴 동일성 강화 검증 (40%)
- VLM 포즈/배경 분석기 (v2.1)
- 포즈-배경 호환성 체커 (v2.1)
"""

from .character import (
    load_character,
    list_characters,
    Character,
)

from .presets import (
    load_preset,
    list_presets,
    get_preset_categories,
    # 비주얼 무드 프리셋
    get_visual_mood_preset,
    get_visual_mood_for_prompt,
    format_visual_mood_for_prompt,
    DEFAULT_VISUAL_MOOD_PRESET,
)

from .generator import (
    generate_ai_influencer,
    generate_with_validation,
)

from .validator import (
    AIInfluencerValidator,
)

from .validator_v2 import (
    AIInfluencerValidatorV2,
    ValidationResultV2,
    validate_ai_influencer_v2,
)

# v2.1: VLM 분석기
from .pose_analyzer import (
    PoseAnalyzer,
    PoseAnalysisResult,
    analyze_pose,
)

from .background_analyzer import (
    BackgroundAnalyzer,
    BackgroundAnalysisResult,
    analyze_background,
)

from .compatibility import (
    CompatibilityChecker,
    CompatibilityResult,
    CompatibilityLevel,
    check_compatibility,
    get_safe_stances_for_background,
)

__all__ = [
    # 캐릭터
    "load_character",
    "list_characters",
    "Character",
    # 프리셋
    "load_preset",
    "list_presets",
    "get_preset_categories",
    # 비주얼 무드 프리셋
    "get_visual_mood_preset",
    "get_visual_mood_for_prompt",
    "format_visual_mood_for_prompt",
    "DEFAULT_VISUAL_MOOD_PRESET",
    # 생성 (이미지 레퍼런스 기반)
    "generate_ai_influencer",
    "generate_with_validation",
    # 검증
    "AIInfluencerValidator",
    # v2: 개선된 검증기
    "AIInfluencerValidatorV2",
    "ValidationResultV2",
    "validate_ai_influencer_v2",
    # v2.1: VLM 분석기
    "PoseAnalyzer",
    "PoseAnalysisResult",
    "analyze_pose",
    "BackgroundAnalyzer",
    "BackgroundAnalysisResult",
    "analyze_background",
    # v2.1: 호환성 체커
    "CompatibilityChecker",
    "CompatibilityResult",
    "CompatibilityLevel",
    "check_compatibility",
    "get_safe_stances_for_background",
]
