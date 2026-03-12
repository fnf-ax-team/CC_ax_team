"""
프롬프트 어셈블러 (통합 빌더)

3대 워크플로의 프롬프트 조립 패턴을 하나의 플루언트 API로 통합.
마크다운 섹션 형식의 프롬프트를 생성한다.

출력 형식:
    ## [모델]
    ## [헤어]
    ## [착장]
    ## [포즈]
    ## [표정]
    ## [촬영_세팅]
    ## [배경]
    ## [브랜드톤]
    ## [네거티브]
    ## [IMAGE REFERENCE ROLES]

사용법:
    result = (
        PromptAssembler()
        .set_model_info("female", "korean", "early_20s")
        .set_outfit(outfit_analysis, mode="korean_detailed")
        .set_camera(framing="MFS", angle="3/4측면")
        .set_negative(base=True, brand="MLB")
        .build()
    )
    print(result.text)  # 전체 프롬프트
    print(result.sections["착장"])  # 착장 섹션만
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from core.modules.prompt.mappings import GENDER_MAP
from core.modules.prompt.outfit_section import format_outfit_section
from core.modules.prompt.negative import NegativePromptBuilder
from core.modules.prompt.camera_section import (
    build_camera_section,
    get_framing_short,
    should_describe_below_thigh,
)
from core.modules.prompt.preservation import (
    PreservationLevel,
    build_preservation_prompt,
)


# ============================================================
# 결과 데이터클래스
# ============================================================


@dataclass
class PromptResult:
    """프롬프트 어셈블러 빌드 결과"""

    text: str
    """전체 프롬프트 텍스트 (마크다운 섹션 형식)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """메타데이터 (브랜드, 워크플로, 설정 등)"""

    sections: Dict[str, str] = field(default_factory=dict)
    """섹션별 텍스트 딕셔너리 (디버깅/부분 사용용)"""


# ============================================================
# 프롬프트 어셈블러
# ============================================================


class PromptAssembler:
    """
    마크다운 섹션 형식 프롬프트를 단계적으로 조립하는 빌더.

    각 set_*() 메서드로 섹션을 설정하고, build()로 최종 결과를 생성한다.
    설정하지 않은 섹션은 자동으로 생략된다.
    """

    def __init__(self):
        # 섹션 데이터 (설정된 것만 포함)
        self._sections: Dict[str, str] = {}
        # 메타데이터
        self._metadata: Dict[str, Any] = {}
        # 네거티브 빌더
        self._neg_builder: Optional[NegativePromptBuilder] = None
        # 커스텀 섹션 (순서 유지)
        self._custom_sections: List[tuple] = []
        # 헤더 라인 (프롬프트 맨 앞에 삽입)
        self._header_lines: List[str] = []

    # ============================================================
    # 모델 정보
    # ============================================================

    def set_model_info(
        self,
        gender: str = "female",
        ethnicity: str = "korean",
        age: str = "early_20s",
        face_result=None,
    ) -> "PromptAssembler":
        """모델(인물) 정보 섹션 설정.

        Args:
            gender: 성별 (예: "female", "male", "여성")
            ethnicity: 민족/국적 (예: "korean", "한국인")
            age: 나이대 (예: "early_20s", "20대 초반")
            face_result: 얼굴 분석 결과 (to_prompt_text() 또는 dict)

        Returns:
            self
        """
        gender_kr = GENDER_MAP.get(gender.lower(), gender)

        lines = ["## [모델]"]
        lines.append(f"- 민족: {ethnicity}")
        lines.append(f"- 성별: {gender_kr}")
        lines.append(f"- 나이: {age}")

        # 얼굴 특징 앵커링 (VLM 분석 결과)
        if face_result is not None:
            if hasattr(face_result, "to_prompt_text"):
                lines.append(f"- 얼굴 특징: {face_result.to_prompt_text()}")
            elif isinstance(face_result, dict):
                parts = [f"{k} {v}" for k, v in face_result.items() if v]
                if parts:
                    lines.append(f"- 얼굴 특징: {', '.join(parts)}")

        self._sections["모델"] = "\n".join(lines)
        self._metadata["gender"] = gender
        self._metadata["ethnicity"] = ethnicity
        return self

    # ============================================================
    # 착장 (스타일링)
    # ============================================================

    def set_outfit(
        self,
        outfit_analysis=None,
        mode: str = "korean_detailed",
        show_legs: bool = True,
    ) -> "PromptAssembler":
        """착장 섹션 설정.

        Args:
            outfit_analysis: OutfitAnalysis 객체 또는 items 속성을 가진 객체
            mode: 포맷 모드 ("korean_detailed", "image_first", "basic")
            show_legs: 하체 표시 여부

        Returns:
            self
        """
        if outfit_analysis is None:
            return self

        items = getattr(outfit_analysis, "items", [])
        if not items:
            return self

        section_text = format_outfit_section(items, mode=mode, show_legs=show_legs)

        # mode에 따라 헤더 포맷 분기
        if mode == "image_first":
            # image_first는 이미 ## 헤더 포함
            self._sections["착장"] = section_text
        else:
            lines = ["[착장] - 반드시 모든 아이템 포함!"]
            lines.append(section_text)
            self._sections["착장"] = "\n".join(lines)

        self._metadata["outfit_mode"] = mode
        return self

    # ============================================================
    # 포즈
    # ============================================================

    def set_pose(self, pose_analysis=None) -> "PromptAssembler":
        """포즈 섹션 설정.

        PoseAnalysisResult의 to_prompt_text() 사용 또는 dict에서 변환.

        Args:
            pose_analysis: PoseAnalysisResult 또는 dict 또는 None

        Returns:
            self
        """
        if pose_analysis is None:
            return self

        # PoseAnalysisResult 타입 (to_prompt_text 메서드 존재)
        if hasattr(pose_analysis, "to_prompt_text"):
            self._sections["포즈"] = f"## [포즈]\n{pose_analysis.to_prompt_text()}"
        elif isinstance(pose_analysis, dict):
            pose = pose_analysis.get("pose", pose_analysis)
            if not pose:
                return self
            lines = ["## [포즈]"]
            if isinstance(pose, dict):
                for key, val in pose.items():
                    if val and not key.startswith("_"):
                        lines.append(f"- {key}: {val}")
            self._sections["포즈"] = "\n".join(lines)

        return self

    # ============================================================
    # 표정
    # ============================================================

    def set_expression(self, expression_analysis=None) -> "PromptAssembler":
        """표정 섹션 설정.

        ExpressionAnalysisResult의 to_prompt_text() 사용 또는 dict에서 변환.

        Args:
            expression_analysis: ExpressionAnalysisResult 또는 dict 또는 None

        Returns:
            self
        """
        if expression_analysis is None:
            return self

        # ExpressionAnalysisResult (to_prompt_text 메서드 존재)
        if hasattr(expression_analysis, "to_prompt_text"):
            self._sections["표정"] = (
                f"## [표정]\n{expression_analysis.to_prompt_text()}"
            )
        elif isinstance(expression_analysis, dict):
            lines = ["## [표정]"]
            for key in ["베이스", "눈", "시선", "입", "얼굴각도", "턱"]:
                val = expression_analysis.get(key, "")
                if val:
                    lines.append(f"- {key}: {val}")
            # 윙크
            if expression_analysis.get("is_wink"):
                wink_eye = expression_analysis.get("wink_eye", "")
                side = "왼쪽" if wink_eye == "left" else "오른쪽"
                lines.append(f"- 윙크: {side} 눈")
            self._sections["표정"] = "\n".join(lines)

        return self

    # ============================================================
    # 헤어
    # ============================================================

    def set_hair(self, hair_result=None) -> "PromptAssembler":
        """헤어 섹션 설정.

        Args:
            hair_result: HairAnalysisResult(to_schema_format()) 또는 dict

        Returns:
            self
        """
        if hair_result is None:
            return self

        if hasattr(hair_result, "to_schema_format"):
            hair_dict = hair_result.to_schema_format()
        elif isinstance(hair_result, dict):
            hair_dict = hair_result
        else:
            return self

        style = hair_dict.get("스타일", "straight_loose")
        color = hair_dict.get("컬러", "dark_brown")
        texture = hair_dict.get("질감", "sleek")

        lines = ["## [헤어] *** DO NOT CHANGE ***"]
        lines.append(f"- 스타일: {style}, 컬러: {color}, 질감: {texture}")

        self._sections["헤어"] = "\n".join(lines)
        return self

    # ============================================================
    # 카메라/촬영 세팅
    # ============================================================

    def set_camera(
        self,
        framing: Optional[str] = None,
        angle: Optional[str] = None,
        height: Optional[str] = None,
        lens: Optional[str] = None,
        aperture: Optional[str] = None,
        composition: Optional[str] = None,
        pose_result=None,
    ) -> "PromptAssembler":
        """촬영 세팅 섹션 설정.

        직접 값을 전달하거나, pose_result에서 자동 추출.

        Args:
            framing: 프레이밍 코드 (예: "FS", "MFS")
            angle: 촬영 앵글
            height: 카메라 높이
            lens: 렌즈 (예: "50mm")
            aperture: 조리개 (예: "f/2.8")
            composition: 구도
            pose_result: PoseAnalysisResult (자동 추출용)

        Returns:
            self
        """
        section = build_camera_section(
            framing=framing,
            angle=angle,
            height=height,
            lens=lens,
            aperture=aperture,
            composition=composition,
            pose_result=pose_result,
        )
        self._sections["촬영_세팅"] = section

        # 프레이밍 메타데이터 저장
        actual_framing = framing
        if actual_framing is None and pose_result is not None:
            actual_framing = getattr(pose_result, "framing", None)
        self._metadata["framing"] = actual_framing or "MS"

        return self

    # ============================================================
    # 배경
    # ============================================================

    def set_background(
        self,
        description: Optional[str] = None,
        analysis_result=None,
    ) -> "PromptAssembler":
        """배경 섹션 설정.

        Args:
            description: 배경 텍스트 설명 (직접 지정)
            analysis_result: BackgroundAnalysisResult 객체 (자동 추출)

        Returns:
            self
        """
        lines = ["## [배경] -- Match [BACKGROUND REFERENCE] image"]

        if analysis_result is not None:
            scene = getattr(analysis_result, "scene_type", "")
            time = getattr(analysis_result, "time_of_day", "")
            color = getattr(analysis_result, "color_tone", "")
            if scene or time or color:
                parts = [p for p in [scene, time, f"{color} 톤" if color else ""] if p]
                lines.append(f"- {', '.join(parts)}")
        elif description:
            lines.append(f"- {description}")

        lines.append("- 인물 제외: 배경에 다른 사람 없음")

        self._sections["배경"] = "\n".join(lines)
        return self

    # ============================================================
    # 브랜드 톤
    # ============================================================

    def set_brand_tone(self, brand: Optional[str] = None) -> "PromptAssembler":
        """브랜드 톤 섹션 설정.

        브랜드 DNA 기반 톤 & 무드 지시사항을 추가한다.

        Args:
            brand: 브랜드명 (예: "MLB", "Discovery")

        Returns:
            self
        """
        if not brand:
            return self

        self._metadata["brand"] = brand

        # 브랜드별 톤 지시 (MLB DNA 기반)
        brand_tones = {
            "MLB": [
                "## [브랜드 톤 - MLB]",
                "강렬한 눈빛으로 카메라 응시.",
                "도도하고 자신감 있는 표정.",
                "파워포즈 - 공간을 지배하는 당당함.",
                "클린한 배경 - 단색 스튜디오 또는 럭셔리 차량.",
                "쿨톤 색감 유지.",
                "프리미엄하고 세련된 느낌.",
            ],
            "Discovery": [
                "## [브랜드 톤 - Discovery]",
                "액티브하고 에너지 넘치는 분위기.",
                "자연광 활용.",
                "아웃도어/자연 배경.",
            ],
        }

        tone_lines = brand_tones.get(brand, [f"## [브랜드 톤 - {brand}]"])
        self._sections["브랜드톤"] = "\n".join(tone_lines)
        return self

    # ============================================================
    # 보존 (배경 교체 워크플로용)
    # ============================================================

    def set_preservation(
        self,
        level: PreservationLevel = PreservationLevel.BASIC,
        physics_analysis: Optional[dict] = None,
        swap_analysis: Optional[dict] = None,
        include_structure_transform: bool = False,
    ) -> "PromptAssembler":
        """보존 섹션 설정 (배경 교체 워크플로용).

        Args:
            level: 보존 강도 (BASIC/DETAILED/FULL)
            physics_analysis: VFX 물리 분석 결과
            swap_analysis: 스왑 분석 결과
            include_structure_transform: 구조물 스타일 변환 포함 여부

        Returns:
            self
        """
        section = build_preservation_prompt(
            level=level,
            physics_analysis=physics_analysis,
            swap_analysis=swap_analysis,
            include_structure_transform=include_structure_transform,
        )
        self._sections["보존"] = section
        self._metadata["preservation_level"] = level.value
        return self

    # ============================================================
    # 네거티브
    # ============================================================

    def set_negative(
        self,
        base: bool = True,
        brand: Optional[str] = None,
        framing: Optional[str] = None,
        pose_tags: Optional[List[str]] = None,
        conditional: Optional[List[str]] = None,
    ) -> "PromptAssembler":
        """네거티브 섹션 설정.

        NegativePromptBuilder를 사용하여 조건별 네거티브를 조립.

        Args:
            base: 기본 AI 공통 네거티브 포함
            brand: 브랜드별 네거티브 (예: "MLB")
            framing: 프레이밍 기반 네거티브
            pose_tags: 포즈 기반 네거티브 태그
            conditional: 추가 조건부 네거티브 리스트

        Returns:
            self
        """
        builder = NegativePromptBuilder()

        if base:
            builder.add_base()
        if brand:
            builder.add_brand(brand)
        if framing:
            builder.add_framing(framing)
        if pose_tags:
            builder.add_pose(pose_tags)
        if conditional:
            builder.add_items(conditional)

        negative_text = builder.build()

        self._sections["네거티브"] = f"## [네거티브]\n{negative_text}"
        return self

    # ============================================================
    # 이미지 역할 안내
    # ============================================================

    def set_image_roles(
        self, roles: Optional[Dict[str, str]] = None
    ) -> "PromptAssembler":
        """IMAGE REFERENCE ROLES 섹션 설정.

        각 참조 이미지의 역할을 명시한다.

        Args:
            roles: 역할 딕셔너리 (예: {"FACE": "이 사람의 얼굴을...", "OUTFIT": "착장 그대로..."})

        Returns:
            self
        """
        if not roles:
            return self

        lines = ["## [IMAGE REFERENCE ROLES]"]
        for role, desc in roles.items():
            lines.append(f"[{role}]: {desc}")

        self._sections["IMAGE_ROLES"] = "\n".join(lines)
        return self

    # ============================================================
    # 커스텀 섹션
    # ============================================================

    def add_custom_section(self, name: str, content: str) -> "PromptAssembler":
        """커스텀 섹션 추가.

        표준 섹션에 포함되지 않는 추가 내용을 삽입한다.

        Args:
            name: 섹션 이름
            content: 섹션 내용

        Returns:
            self
        """
        self._custom_sections.append((name, content))
        return self

    # ============================================================
    # 헤더 설정
    # ============================================================

    def set_header(self, *lines: str) -> "PromptAssembler":
        """프롬프트 상단에 삽입할 헤더 라인 설정.

        프레이밍 BOLD 강조 등 프롬프트 최상단에 표시할 내용.

        Args:
            *lines: 헤더 라인들

        Returns:
            self
        """
        self._header_lines.extend(lines)
        return self

    # ============================================================
    # 빌드
    # ============================================================

    def build(self) -> PromptResult:
        """
        설정된 섹션들을 마크다운 형식으로 조립하여 PromptResult를 반환.

        설정되지 않은 섹션은 자동으로 생략된다.

        Returns:
            PromptResult (text, metadata, sections)
        """
        # 섹션 출력 순서 (설정된 것만 포함)
        section_order = [
            "보존",  # 배경 교체 시 최상단
            "모델",
            "헤어",
            "착장",
            "포즈",
            "표정",
            "촬영_세팅",
            "배경",
            "브랜드톤",
            "네거티브",
            "IMAGE_ROLES",
        ]

        output_parts = []

        # 헤더 라인 (최상단)
        if self._header_lines:
            output_parts.extend(self._header_lines)
            output_parts.append("")

        # 표준 섹션 (순서대로, 설정된 것만)
        for section_key in section_order:
            if section_key in self._sections:
                output_parts.append(self._sections[section_key])
                output_parts.append("")  # 섹션 간 빈 줄

        # 커스텀 섹션
        for name, content in self._custom_sections:
            output_parts.append(f"## [{name}]")
            output_parts.append(content)
            output_parts.append("")

        text = "\n".join(output_parts).strip()

        return PromptResult(
            text=text,
            metadata=self._metadata.copy(),
            sections=self._sections.copy(),
        )


__all__ = [
    "PromptResult",
    "PromptAssembler",
]
