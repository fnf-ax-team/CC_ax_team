"""
하위호환 re-export stub

원본이 core.modules.pose_analyzer로 이동됨.
기존 import 경로를 유지하기 위한 re-export.
"""

from core.modules.pose_analyzer import (
    PoseAnalysisResult,
    PoseAnalyzer,
    POSE_ANALYSIS_PROMPT,
    analyze_pose,
)

__all__ = [
    "PoseAnalysisResult",
    "PoseAnalyzer",
    "POSE_ANALYSIS_PROMPT",
    "analyze_pose",
]
