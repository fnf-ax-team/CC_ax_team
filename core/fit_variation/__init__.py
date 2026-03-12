"""
바지 핏 베리에이션 모듈

단일 바지 이미지에서 다양한 실루엣(핏) 변형을 생성한다.
색상/소재/로고는 100% 보존하고 실루엣만 변경.

사용법:
    from core.fit_variation import (
        analyze_pants,
        PantsAnalysis,
        build_fit_variation_prompt,
        generate_fit_variation,
        load_fit_preset,
        list_fit_presets,
    )
"""

from .analyzer import PantsAnalysis, PantsAnalyzer, analyze_pants
from .fit_presets import load_fit_preset, list_fit_presets, get_display_mode
from .prompt_builder import build_fit_variation_prompt
from .generator import generate_fit_variation

__all__ = [
    "PantsAnalysis",
    "PantsAnalyzer",
    "analyze_pants",
    "load_fit_preset",
    "list_fit_presets",
    "get_display_mode",
    "build_fit_variation_prompt",
    "generate_fit_variation",
]
