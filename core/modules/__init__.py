"""
core.modules - FNF Studio 분석 모듈 통합 패키지

기존 분산된 분석기들을 통합된 인터페이스로 제공한다.

Phase 1: VLM 유틸리티 + 프롬프트 매핑
Phase 2: 분석 래퍼 모듈 (얼굴/착장/포즈/표정/헤어/배경)

사용법:
    # VLM 유틸리티
    from core.modules import load_image, parse_json_response, pil_to_part, vlm_call

    # 분석 함수 (통합 인터페이스)
    from core.modules import analyze_face, analyze_outfit, analyze_pose
    from core.modules import analyze_expression, analyze_hair, analyze_background

    # 결과 데이터클래스
    from core.modules import FaceAnalysisResult, ExtendedFaceAnalysisResult
    from core.modules import OutfitAnalysis, OutfitItem, LogoInfo
    from core.modules import PoseAnalysisResult
    from core.modules import ExpressionAnalysisResult
    from core.modules import HairAnalysisResult
    from core.modules import BackgroundAnalysisResult

    # 프롬프트 매핑
    from core.modules.prompt import STATE_TO_KOREAN, GENDER_MAP, infer_category

    # 워크플로 팩토리 (효율적 조합)
    from core.modules.workflow_factory import WorkflowFactory
    from core.modules.workflow_config import get_workflow_config, list_workflows
"""

# VLM 유틸리티
from core.modules.vlm_utils import (
    load_image,
    parse_json_response,
    pil_to_part,
    vlm_call,
)

# 분석 래퍼 - 얼굴
# (core.ai_influencer 의존: 미설치 환경에서 ImportError 발생 가능)
try:
    from core.modules.analyze_face import (
        FaceAnalysisResult,
        ExtendedFaceAnalysisResult,
        analyze_face,
    )
except ImportError:
    FaceAnalysisResult = None
    ExtendedFaceAnalysisResult = None
    analyze_face = None

# 분석 래퍼 - 착장
try:
    from core.modules.analyze_outfit import (
        OutfitAnalysis,
        OutfitItem,
        LogoInfo,
        analyze_outfit,
    )
except ImportError:
    OutfitAnalysis = None
    OutfitItem = None
    LogoInfo = None
    analyze_outfit = None

# 분석 래퍼 - 포즈
try:
    from core.modules.analyze_pose import (
        PoseAnalysisResult,
        analyze_pose,
    )
except ImportError:
    PoseAnalysisResult = None
    analyze_pose = None

# 분석 래퍼 - 표정
try:
    from core.modules.analyze_expression import (
        ExpressionAnalysisResult,
        analyze_expression,
    )
except ImportError:
    ExpressionAnalysisResult = None
    analyze_expression = None

# 분석 래퍼 - 헤어
try:
    from core.modules.analyze_hair import (
        HairAnalysisResult,
        analyze_hair,
    )
except ImportError:
    HairAnalysisResult = None
    analyze_hair = None

# 분석 래퍼 - 배경
try:
    from core.modules.analyze_background import (
        BackgroundAnalysisResult,
        analyze_background,
    )
except ImportError:
    BackgroundAnalysisResult = None
    analyze_background = None

# 워크플로 팩토리 (카테고리 기반 자동 구성)
from core.modules.workflow_config import (
    WorkflowCategory,
    WorkflowConfig,
    get_workflow_config,
    list_workflows,
    list_by_category,
)
from core.modules.workflow_factory import (
    WorkflowFactory,
    WorkflowInstance,
    AnalysisBundle,
)


__all__ = [
    # VLM 유틸리티
    "load_image",
    "parse_json_response",
    "pil_to_part",
    "vlm_call",
    # 분석 함수
    "analyze_face",
    "analyze_outfit",
    "analyze_pose",
    "analyze_expression",
    "analyze_hair",
    "analyze_background",
    # 결과 데이터클래스
    "FaceAnalysisResult",
    "ExtendedFaceAnalysisResult",
    "OutfitAnalysis",
    "OutfitItem",
    "LogoInfo",
    "PoseAnalysisResult",
    "ExpressionAnalysisResult",
    "HairAnalysisResult",
    "BackgroundAnalysisResult",
    # 워크플로 팩토리
    "WorkflowFactory",
    "WorkflowInstance",
    "AnalysisBundle",
    "WorkflowCategory",
    "WorkflowConfig",
    "get_workflow_config",
    "list_workflows",
    "list_by_category",
]
