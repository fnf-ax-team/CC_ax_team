"""
Outfit Swap Prompt Builder

소스 분석 결과 + 착장 분석 결과를 합쳐서 생성 프롬프트 조립

두 가지 인터페이스를 지원한다:
1. SourceAnalysisResult 객체 기반 (기존 인터페이스)
2. dict 기반 (analyze_source_for_swap / analyze_outfit_items 반환값 사용)
"""

from typing import Optional, TYPE_CHECKING, Union

from .analyzer import SourceAnalysisResult
from .templates import (
    OUTFIT_SWAP_PROMPT_TEMPLATE,
    build_outfit_swap_prompt as _build_prompt_from_template,
)

if TYPE_CHECKING:
    from core.outfit_analyzer import OutfitAnalysisResult


def build_outfit_swap_prompt(
    source_analysis: Union[SourceAnalysisResult, dict],
    outfit_analyses: Optional[list] = None,
    outfit_analysis: Optional["OutfitAnalysisResult"] = None,
    outfit_text: Optional[str] = None,
) -> str:
    """
    소스 분석 + 착장 분석 결과를 합쳐서 생성 프롬프트 조립.

    두 가지 호출 방식을 지원한다:

    방법 1 — analyze_source_for_swap / analyze_outfit_items 반환값 사용 (dict 기반):
        source_analysis: dict with face_description, pose_description,
                         body_type, background_description keys
        outfit_analyses: list of dicts with prompt_description key

    방법 2 — SourceAnalysisResult 객체 사용 (기존 인터페이스):
        source_analysis: SourceAnalysisResult 객체
        outfit_analysis: OutfitAnalysisResult 객체 (선택)
        outfit_text: 착장 텍스트 직접 지정 (선택)

    드레이핑 고려사항 (Draping Considerations):
    - 착장이 소스 포즈에 자연스럽게 맞아야 함
    - 포즈에 따른 자연스러운 주름/폴드 처리
    - 중력에 따른 물리적으로 타당한 착장 처짐
    - 옷이 몸에서 떠있거나 분리되지 않도록

    Returns:
        str: Gemini 이미지 생성용 완성 프롬프트
    """
    # --- dict 기반 인터페이스 (analyze_source_for_swap + analyze_outfit_items 결과) ---
    if isinstance(source_analysis, dict):
        raw = source_analysis.get("_raw", {})

        # 착장 설명 목록 구성
        outfit_descriptions = []
        if outfit_analyses:
            for item in outfit_analyses:
                if isinstance(item, dict):
                    desc = item.get("prompt_description", "")
                    color = item.get("color", "")
                    item_type = item.get("item_type", "")
                    logo = item.get("logo")
                    material = item.get("material", "")
                    details = item.get("details", [])

                    # prompt_description이 있으면 우선 사용
                    if desc:
                        outfit_descriptions.append(desc)
                    else:
                        # 폴백: 필드 조합
                        parts = [p for p in [color, material, item_type] if p]
                        summary = " ".join(parts) if parts else "outfit item"
                        if logo:
                            summary += f" with {logo} logo"
                        if details:
                            det_str = ", ".join(details[:3])
                            summary += f" ({det_str})"
                        outfit_descriptions.append(summary)

        if not outfit_descriptions:
            outfit_descriptions = ["outfit items from reference images"]

        # 편집 모드 프롬프트: 소스 분석 결과는 기록용으로만 보존,
        # 프롬프트에는 포즈/얼굴/배경 텍스트를 나열하지 않음
        return _build_prompt_from_template(raw or {}, outfit_descriptions).strip()

    # --- SourceAnalysisResult 객체 기반 인터페이스 (기존) ---
    # 착장 설명 추출
    outfit_descriptions = []
    if outfit_analyses is not None:
        for item in outfit_analyses:
            if isinstance(item, dict):
                desc = item.get("prompt_description", str(item))
            else:
                desc = str(item)
            outfit_descriptions.append(desc)
    elif outfit_analysis is not None:
        outfit_descriptions = [outfit_analysis.prompt_section]
    elif outfit_text:
        outfit_descriptions = [outfit_text]
    else:
        outfit_descriptions = ["casual outfit"]

    # 편집 모드: 소스 분석은 기록용, 프롬프트에는 블랭킷 보존 지시만 사용
    return _build_prompt_from_template(
        source_analysis.to_dict(), outfit_descriptions
    ).strip()


def build_prompt_from_dict(
    source_data: dict,
    outfit_analysis: Optional["OutfitAnalysisResult"] = None,
    outfit_text: Optional[str] = None,
) -> str:
    """
    딕셔너리 형태의 소스 분석 결과로 프롬프트 생성

    편집 모드: 소스 분석 결과는 기록용으로만 보존,
    프롬프트에는 포즈/얼굴/배경을 텍스트로 나열하지 않음.

    Args:
        source_data: 소스 분석 결과 딕셔너리
        outfit_analysis: 착장 분석 결과
        outfit_text: 착장 텍스트

    Returns:
        str: 생성용 프롬프트
    """
    # 착장 설명 추출
    outfit_descriptions = []
    if outfit_analysis is not None:
        outfit_descriptions = [outfit_analysis.prompt_section]
    elif outfit_text:
        outfit_descriptions = [outfit_text]
    else:
        outfit_descriptions = ["casual outfit"]

    return _build_prompt_from_template(source_data, outfit_descriptions).strip()
