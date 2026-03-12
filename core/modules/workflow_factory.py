"""
워크플로 팩토리 (카테고리 기반 자동 구성)

카테고리만 선언하면 분석→프롬프트→생성→검수 파이프라인을 자동 구성.

사용법:
    from core.modules.workflow_factory import WorkflowFactory

    # 1. 카테고리 기본값으로 생성
    wf = WorkflowFactory.create("brandcut", brand="MLB")

    # 2. 오버라이드 적용
    wf = WorkflowFactory.create("ecommerce", brand="MLB",
        overrides={"background": "화이트 스튜디오", "outfit_detail": "commerce"})

    # 3. 분석 실행
    analysis = wf.analyze(face_images=[...], outfit_images=[...])

    # 4. 프롬프트 생성
    prompt_result = wf.build_prompt(analysis)

    # 5. 또는 한번에 (분석 → 프롬프트)
    prompt_result = wf.analyze_and_build(face_images=[...], outfit_images=[...])
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image

from core.modules.workflow_config import (
    AnalyzerSlot,
    WorkflowCategory,
    WorkflowConfig,
    get_workflow_config,
)
from core.modules.prompt.assembler import PromptAssembler, PromptResult


# ============================================================
# 분석 결과 컨테이너
# ============================================================


@dataclass
class AnalysisBundle:
    """모든 분석 결과를 담는 통합 컨테이너.

    워크플로 설정에서 요구하는 분석기만 실행하고,
    결과를 슬롯별로 저장한다.
    """

    face: Any = None
    outfit: Any = None
    pose: Any = None
    expression: Any = None
    hair: Any = None
    background: Any = None
    preservation: Any = None

    # 메타데이터
    workflow_name: str = ""
    analyzers_run: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    def has(self, slot: str) -> bool:
        """슬롯에 분석 결과가 있는지 확인"""
        return getattr(self, slot, None) is not None


# ============================================================
# 워크플로 인스턴스
# ============================================================


class WorkflowInstance:
    """
    팩토리가 생성한 워크플로 인스턴스.

    config + overrides를 바탕으로:
    1. analyze() — 필요한 분석기만 실행
    2. build_prompt() — PromptAssembler 자동 구성
    3. analyze_and_build() — 1+2 한번에
    """

    def __init__(
        self,
        config: WorkflowConfig,
        brand: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ):
        self.config = config
        self.brand = brand
        self.overrides = overrides or {}

        # 오버라이드 적용된 실제 값
        self._outfit_detail = self.overrides.get("outfit_detail", config.outfit_detail)
        self._prompt_mode = self.overrides.get("prompt_mode", config.prompt_mode)
        self._background = self.overrides.get(
            "background", config.extra.get("background")
        )
        self._model_type = self.overrides.get(
            "model_type", config.extra.get("model_type")
        )
        self._framing = self.overrides.get("framing", config.default_framing)
        self._aspect_ratio = self.overrides.get(
            "aspect_ratio", config.default_aspect_ratio
        )

    # ============================================================
    # 분석
    # ============================================================

    def analyze(
        self,
        face_images: Optional[List] = None,
        outfit_images: Optional[List] = None,
        source_image: Optional[Any] = None,
        reference_image: Optional[Any] = None,
        api_key: Optional[str] = None,
    ) -> AnalysisBundle:
        """설정에 따라 필요한 분석기만 실행.

        Args:
            face_images: 얼굴 이미지 리스트 (인물 워크플로)
            outfit_images: 착장 이미지 리스트
            source_image: 소스 이미지 (스왑 워크플로)
            reference_image: 레퍼런스 이미지 (포즈카피 등)
            api_key: Gemini API 키 (None이면 자동 로테이션)

        Returns:
            AnalysisBundle (실행된 분석 결과만 채워짐)
        """
        bundle = AnalysisBundle(workflow_name=self.config.name)

        for slot in self.config.analyzers:
            try:
                if slot == AnalyzerSlot.FACE and face_images:
                    bundle.face = self._analyze_face(face_images[0], api_key)
                    bundle.analyzers_run.append("face")

                elif slot == AnalyzerSlot.OUTFIT and outfit_images:
                    bundle.outfit = self._analyze_outfit(outfit_images, api_key)
                    bundle.analyzers_run.append("outfit")

                elif slot == AnalyzerSlot.POSE and (reference_image or source_image):
                    img = reference_image or source_image
                    bundle.pose = self._analyze_pose(img, api_key)
                    bundle.analyzers_run.append("pose")

                elif slot == AnalyzerSlot.EXPRESSION and (
                    reference_image or source_image
                ):
                    img = reference_image or source_image
                    bundle.expression = self._analyze_expression(img, api_key)
                    bundle.analyzers_run.append("expression")

                elif slot == AnalyzerSlot.HAIR and face_images:
                    bundle.hair = self._analyze_hair(face_images[0], api_key)
                    bundle.analyzers_run.append("hair")

                elif slot == AnalyzerSlot.BACKGROUND and (
                    reference_image or source_image
                ):
                    img = reference_image or source_image
                    bundle.background = self._analyze_background(img, api_key)
                    bundle.analyzers_run.append("background")

                elif slot == AnalyzerSlot.PRESERVATION and source_image:
                    bundle.preservation = self._analyze_preservation(
                        source_image, api_key
                    )
                    bundle.analyzers_run.append("preservation")

            except Exception as e:
                bundle.errors[slot.value] = str(e)
                print(f"[WorkflowInstance] {slot.value} 분석 실패: {e}")

        return bundle

    # ============================================================
    # 프롬프트 빌드
    # ============================================================

    def build_prompt(
        self,
        analysis: Optional[AnalysisBundle] = None,
        gender: str = "female",
        ethnicity: str = "korean",
        age: str = "early_20s",
        **kwargs,
    ) -> PromptResult:
        """분석 결과로 PromptAssembler 자동 구성.

        워크플로 카테고리에 따라 필요한 섹션만 자동으로 채운다.

        Args:
            analysis: AnalysisBundle (없으면 빈 프롬프트)
            gender: 성별
            ethnicity: 민족
            age: 나이대
            **kwargs: 추가 오버라이드 (background, framing 등)

        Returns:
            PromptResult (text, metadata, sections)
        """
        asm = PromptAssembler()
        category = self.config.category

        # 최종 오버라이드 적용
        bg_desc = kwargs.get("background", self._background)
        framing = kwargs.get("framing", self._framing)

        # ── 카테고리별 프롬프트 구성 ──

        if category in (
            WorkflowCategory.PERSON_FORMAL,
            WorkflowCategory.PERSON_FREE,
            WorkflowCategory.VMD,
        ):
            self._build_person_prompt(
                asm, analysis, gender, ethnicity, age, bg_desc, framing
            )

        elif category == WorkflowCategory.SWAP:
            self._build_swap_prompt(asm, analysis, bg_desc, framing)

        elif category == WorkflowCategory.BACKGROUND:
            self._build_background_prompt(asm, analysis, bg_desc)

        elif category == WorkflowCategory.PRODUCT:
            self._build_product_prompt(asm, bg_desc, framing, **kwargs)

        # ── 공통: 브랜드톤 + 네거티브 + 이미지 역할 ──

        if self.config.brand_tone and self.brand:
            asm.set_brand_tone(self.brand)

        if self.config.negative_base:
            outfit_items = None
            if analysis and analysis.has("outfit"):
                outfit_items = getattr(analysis.outfit, "items", None)
            asm.set_negative(
                base=True,
                brand=self.brand,
                framing=framing,
                outfit_items=outfit_items,
            )

        if self.config.image_roles:
            asm.set_image_roles(self.config.image_roles)

        # 메타데이터 주입
        result = asm.build()
        result.metadata["workflow"] = self.config.name
        result.metadata["category"] = category.value
        if self.brand:
            result.metadata["brand"] = self.brand

        return result

    # ============================================================
    # 분석 + 빌드 한번에
    # ============================================================

    def analyze_and_build(
        self,
        face_images: Optional[List] = None,
        outfit_images: Optional[List] = None,
        source_image: Optional[Any] = None,
        reference_image: Optional[Any] = None,
        api_key: Optional[str] = None,
        gender: str = "female",
        ethnicity: str = "korean",
        age: str = "early_20s",
        **kwargs,
    ) -> PromptResult:
        """분석 → 프롬프트 빌드를 한번에 실행.

        Args:
            (analyze 파라미터 + build_prompt 파라미터)

        Returns:
            PromptResult
        """
        analysis = self.analyze(
            face_images=face_images,
            outfit_images=outfit_images,
            source_image=source_image,
            reference_image=reference_image,
            api_key=api_key,
        )
        return self.build_prompt(
            analysis=analysis,
            gender=gender,
            ethnicity=ethnicity,
            age=age,
            **kwargs,
        )

    # ============================================================
    # 카테고리별 프롬프트 빌드 내부 메서드
    # ============================================================

    def _build_person_prompt(
        self,
        asm: PromptAssembler,
        analysis: Optional[AnalysisBundle],
        gender: str,
        ethnicity: str,
        age: str,
        bg_desc: Optional[str],
        framing: Optional[str],
    ):
        """인물 워크플로 프롬프트 구성 (인물-정규 / 인물-자유 / VMD)"""
        face_result = analysis.face if analysis else None

        # 모델 타입에 따른 분기
        if self._model_type == "mannequin":
            asm.add_custom_section(
                "모델",
                "마네킹 디스플레이 (인물 아님)\n" "의류 핏과 실루엣을 보여주는 마네킹",
            )
        else:
            asm.set_model_info(
                gender=gender,
                ethnicity=ethnicity,
                age=age,
                face_result=face_result,
            )

        if analysis:
            # 분석 결과가 있으면 해당 섹션 자동 설정
            if analysis.has("hair"):
                asm.set_hair(analysis.hair)

            if analysis.has("outfit"):
                asm.set_outfit(analysis.outfit, mode=self._prompt_mode)

            if analysis.has("pose"):
                asm.set_pose(analysis.pose)

            if analysis.has("expression"):
                asm.set_expression(analysis.expression)

            asm.set_camera(
                framing=framing,
                pose_result=analysis.pose if analysis.has("pose") else None,
            )

            if analysis.has("background"):
                asm.set_background(analysis_result=analysis.background)
            elif bg_desc:
                asm.set_background(description=bg_desc)
        else:
            # 분석 없이 기본값
            asm.set_camera(framing=framing)
            if bg_desc:
                asm.set_background(description=bg_desc)

    def _build_swap_prompt(
        self,
        asm: PromptAssembler,
        analysis: Optional[AnalysisBundle],
        bg_desc: Optional[str],
        framing: Optional[str],
    ):
        """스왑 워크플로 프롬프트 구성"""
        if analysis and analysis.has("preservation"):
            preservation = analysis.preservation

            # 보존 텍스트를 커스텀 섹션으로 삽입
            asm.add_custom_section("보존", preservation.to_prompt_text())

            # 보존 결과에서 착장이 있으면 착장 섹션도 추가
            if analysis.has("outfit"):
                asm.set_outfit(analysis.outfit, mode=self._prompt_mode)

        asm.set_camera(framing=framing)

        if bg_desc:
            asm.set_background(description=bg_desc)

    def _build_background_prompt(
        self,
        asm: PromptAssembler,
        analysis: Optional[AnalysisBundle],
        bg_desc: Optional[str],
    ):
        """배경교체 워크플로 프롬프트 구성"""
        from core.modules.prompt.preservation import (
            PreservationLevel,
            build_preservation_prompt,
        )

        asm.set_preservation(level=PreservationLevel.DETAILED)

        if analysis and analysis.has("preservation"):
            # 보존 분석 결과로 인물 디테일 보강
            preservation = analysis.preservation
            preserved = preservation.get_preserved_elements()
            if preserved:
                detail_lines = []
                for element, desc in preserved.items():
                    detail_lines.append(f"[{element}] {desc}")
                asm.add_custom_section("인물_디테일", "\n".join(detail_lines))

        if bg_desc:
            asm.set_background(description=bg_desc)

    def _build_product_prompt(
        self,
        asm: PromptAssembler,
        bg_desc: Optional[str],
        framing: Optional[str],
        **kwargs,
    ):
        """제품 워크플로 프롬프트 구성"""
        product_desc = kwargs.get("product_description", "")
        if product_desc:
            asm.add_custom_section("제품", product_desc)

        asm.set_camera(framing=framing or "제품 중심")

        if bg_desc:
            asm.set_background(description=bg_desc)

    # ============================================================
    # 분석기 래퍼 (lazy import)
    # ============================================================

    def _analyze_face(self, image, api_key):
        """얼굴 분석 (core.modules.analyze_face 래핑)"""
        from core.modules.analyze_face import analyze_face

        return analyze_face(image, api_key=api_key)

    def _analyze_outfit(self, images, api_key):
        """착장 분석 (core.modules.analyze_outfit 래핑)"""
        from core.modules.analyze_outfit import analyze_outfit

        return analyze_outfit(
            images=images,
            api_key=api_key,
            detail_level=self._outfit_detail,
        )

    def _analyze_pose(self, image, api_key):
        """포즈 분석 (core.modules.analyze_pose 래핑)"""
        from core.modules.analyze_pose import analyze_pose

        return analyze_pose(image, api_key=api_key)

    def _analyze_expression(self, image, api_key):
        """표정 분석 (core.modules.analyze_expression 래핑)"""
        from core.modules.analyze_expression import analyze_expression

        return analyze_expression(image, api_key=api_key)

    def _analyze_hair(self, image, api_key):
        """헤어 분석 (core.modules.analyze_hair 래핑)"""
        from core.modules.analyze_hair import analyze_hair

        return analyze_hair(image, api_key=api_key)

    def _analyze_background(self, image, api_key):
        """배경 분석 (core.modules.analyze_background 래핑)"""
        from core.modules.analyze_background import analyze_background

        return analyze_background(image, api_key=api_key)

    def _analyze_preservation(self, image, api_key):
        """보존 분석 (core.modules.preserve_source 래핑)"""
        from core.modules.preserve_source import analyze_for_preservation

        return analyze_for_preservation(
            image,
            api_key=api_key,
            preserve=self.config.preserve,
            change=self.config.change,
            include_physical_constraints=self.config.include_physical_constraints,
        )

    # ============================================================
    # 유틸리티
    # ============================================================

    @property
    def aspect_ratio(self) -> str:
        return self._aspect_ratio

    @property
    def category(self) -> WorkflowCategory:
        return self.config.category

    def __repr__(self) -> str:
        return (
            f"WorkflowInstance(name={self.config.name!r}, "
            f"category={self.config.category.value!r}, "
            f"brand={self.brand!r})"
        )


# ============================================================
# WorkflowFactory
# ============================================================


class WorkflowFactory:
    """
    워크플로 인스턴스를 카테고리 설정에서 자동 생성.

    사용법:
        # 기본
        wf = WorkflowFactory.create("brandcut", brand="MLB")

        # 오버라이드
        wf = WorkflowFactory.create("ecommerce", brand="MLB",
            overrides={"background": "화이트 스튜디오"})

        # 분석 → 프롬프트 한번에
        prompt = wf.analyze_and_build(
            face_images=[face_img],
            outfit_images=[outfit_img],
        )
    """

    @staticmethod
    def create(
        workflow_name: str,
        brand: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """워크플로 인스턴스 생성.

        Args:
            workflow_name: 워크플로 영문명 (예: "brandcut", "face_swap")
            brand: 브랜드명 (예: "MLB")
            overrides: 카테고리 기본값 오버라이드

        Returns:
            WorkflowInstance
        """
        config = get_workflow_config(workflow_name)
        return WorkflowInstance(
            config=config,
            brand=brand,
            overrides=overrides,
        )

    @staticmethod
    def list_available() -> List[str]:
        """사용 가능한 워크플로 목록"""
        from core.modules.workflow_config import list_workflows

        return list_workflows()

    @staticmethod
    def list_by_category(
        category: WorkflowCategory,
    ) -> List[WorkflowConfig]:
        """카테고리별 워크플로 목록"""
        from core.modules.workflow_config import list_by_category

        return list_by_category(category)


__all__ = [
    "AnalysisBundle",
    "WorkflowInstance",
    "WorkflowFactory",
]
