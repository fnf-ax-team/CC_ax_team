"""
WorkflowFactory 테스트

카테고리 설정, 팩토리 생성, 오버라이드, 프롬프트 조립을 검증한다.
API 호출 없이 구조/설정 레벨만 테스트.
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# ============================================================
# workflow_config 테스트
# ============================================================


class TestWorkflowConfig:
    """워크플로 설정 레지스트리 테스트"""

    def test_import_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            WorkflowConfig,
            WORKFLOW_REGISTRY,
            get_workflow_config,
            list_workflows,
        )

        assert WorkflowCategory is not None
        assert WorkflowConfig is not None
        assert len(WORKFLOW_REGISTRY) > 0

    def test_all_categories_have_workflows(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            list_by_category,
        )

        # 주요 카테고리에 워크플로가 등록되어 있는지
        for cat in [
            WorkflowCategory.PERSON_FORMAL,
            WorkflowCategory.PERSON_FREE,
            WorkflowCategory.SWAP,
            WorkflowCategory.BACKGROUND,
            WorkflowCategory.PRODUCT,
            WorkflowCategory.VMD,
        ]:
            workflows = list_by_category(cat)
            assert len(workflows) > 0, f"{cat.value} 카테고리에 워크플로 없음"

    def test_list_workflows(self):
        from core.modules.workflow_config import list_workflows

        names = list_workflows()
        assert "brandcut" in names
        assert "face_swap" in names
        assert "background_swap" in names
        assert "ecommerce" in names
        assert len(names) >= 15  # 최소 15개 등록

    def test_get_workflow_config(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("brandcut")
        assert cfg.name == "brandcut"
        assert cfg.name_kr == "브랜드컷"
        assert cfg.default_aspect_ratio == "3:4"

    def test_get_unknown_workflow_raises(self):
        from core.modules.workflow_config import get_workflow_config

        with pytest.raises(KeyError, match="미등록 워크플로"):
            get_workflow_config("nonexistent_workflow")

    def test_brandcut_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            AnalyzerSlot,
            get_workflow_config,
        )

        cfg = get_workflow_config("brandcut")
        assert cfg.category == WorkflowCategory.PERSON_FORMAL
        assert AnalyzerSlot.FACE in cfg.analyzers
        assert AnalyzerSlot.OUTFIT in cfg.analyzers
        assert AnalyzerSlot.POSE in cfg.analyzers
        assert cfg.outfit_detail == "full"
        assert cfg.prompt_mode == "korean_detailed"
        assert cfg.brand_tone is True
        assert "FACE" in cfg.image_roles
        assert "OUTFIT" in cfg.image_roles

    def test_ecommerce_config(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("ecommerce")
        assert cfg.outfit_detail == "commerce"
        assert cfg.extra.get("background") is not None
        assert "화이트" in cfg.extra["background"]

    def test_face_swap_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            AnalyzerSlot,
            get_workflow_config,
        )

        cfg = get_workflow_config("face_swap")
        assert cfg.category == WorkflowCategory.SWAP
        assert cfg.preserve == ["pose", "outfit", "background", "lighting"]
        assert cfg.change == ["face"]
        assert AnalyzerSlot.PRESERVATION in cfg.analyzers

    def test_outfit_swap_config(self):
        from core.modules.workflow_config import (
            AnalyzerSlot,
            get_workflow_config,
        )

        cfg = get_workflow_config("outfit_swap")
        assert cfg.preserve == ["face", "pose", "background"]
        assert cfg.change == ["outfit"]
        # 착장스왑은 PRESERVATION + OUTFIT 분석기 사용
        assert AnalyzerSlot.PRESERVATION in cfg.analyzers
        assert AnalyzerSlot.OUTFIT in cfg.analyzers

    def test_pose_change_config(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("pose_change")
        assert cfg.change == ["pose"]
        assert cfg.include_physical_constraints is True

    def test_background_swap_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            get_workflow_config,
        )

        cfg = get_workflow_config("background_swap")
        assert cfg.category == WorkflowCategory.BACKGROUND
        assert "face" in cfg.preserve
        assert cfg.change == ["background"]

    def test_mannequin_config(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("mannequin_outfit")
        assert cfg.extra.get("model_type") == "mannequin"

    def test_influencer_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            AnalyzerSlot,
            get_workflow_config,
        )

        cfg = get_workflow_config("influencer")
        assert cfg.category == WorkflowCategory.PERSON_FREE
        assert cfg.default_aspect_ratio == "9:16"
        assert AnalyzerSlot.BACKGROUND in cfg.analyzers

    def test_selfie_config(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("selfie")
        assert cfg.prompt_mode == "basic"

    def test_product_config(self):
        from core.modules.workflow_config import (
            WorkflowCategory,
            get_workflow_config,
        )

        cfg = get_workflow_config("product_design")
        assert cfg.category == WorkflowCategory.PRODUCT
        assert len(cfg.analyzers) == 0  # 제품은 분석기 불필요

    def test_reference_brandcut_image_roles(self):
        from core.modules.workflow_config import get_workflow_config

        cfg = get_workflow_config("reference_brandcut")
        assert "REFERENCE" in cfg.image_roles
        assert "FACE" in cfg.image_roles
        assert "OUTFIT" in cfg.image_roles
        assert "BACKGROUND" in cfg.image_roles


# ============================================================
# WorkflowFactory 테스트
# ============================================================


class TestWorkflowFactory:
    """팩토리 생성 + 인스턴스 테스트"""

    def test_import_factory(self):
        from core.modules.workflow_factory import (
            WorkflowFactory,
            WorkflowInstance,
            AnalysisBundle,
        )

        assert WorkflowFactory is not None
        assert WorkflowInstance is not None
        assert AnalysisBundle is not None

    def test_create_brandcut(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        assert wf.config.name == "brandcut"
        assert wf.brand == "MLB"

    def test_create_with_overrides(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create(
            "brandcut",
            brand="MLB",
            overrides={"framing": "MFS", "background": "화이트 스튜디오"},
        )
        assert wf._framing == "MFS"
        assert wf._background == "화이트 스튜디오"

    def test_ecommerce_auto_background(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("ecommerce", brand="MLB")
        assert "화이트" in wf._background

    def test_mannequin_model_type(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("mannequin_outfit", brand="MLB")
        assert wf._model_type == "mannequin"

    def test_list_available(self):
        from core.modules.workflow_factory import WorkflowFactory

        available = WorkflowFactory.list_available()
        assert "brandcut" in available
        assert len(available) >= 15

    def test_repr(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        r = repr(wf)
        assert "brandcut" in r
        assert "MLB" in r

    def test_aspect_ratio_property(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("influencer")
        assert wf.aspect_ratio == "9:16"

        wf2 = WorkflowFactory.create("brandcut")
        assert wf2.aspect_ratio == "3:4"

    def test_category_property(self):
        from core.modules.workflow_config import WorkflowCategory
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("face_swap")
        assert wf.category == WorkflowCategory.SWAP


# ============================================================
# 프롬프트 빌드 테스트 (분석 없이, 구조만)
# ============================================================


class TestPromptBuild:
    """분석 결과 없이 프롬프트 구조를 검증"""

    def test_brandcut_prompt_structure(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        result = wf.build_prompt()

        assert result.text  # 비어있지 않음
        assert "모델" in result.sections or "## [모델]" in result.text
        assert result.metadata["workflow"] == "brandcut"

    def test_brandcut_with_brand_tone(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        result = wf.build_prompt()

        assert "MLB" in result.text
        assert "브랜드 톤" in result.text
        assert result.metadata.get("brand") == "MLB"

    def test_brandcut_negative(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        result = wf.build_prompt()

        assert "네거티브" in result.text
        assert "golden hour" in result.text  # MLB 네거티브

    def test_ecommerce_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("ecommerce", brand="MLB")
        result = wf.build_prompt()

        assert "화이트" in result.text  # 자동 배경
        assert result.metadata["workflow"] == "ecommerce"

    def test_mannequin_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("mannequin_outfit", brand="MLB")
        result = wf.build_prompt()

        assert "마네킹" in result.text
        assert result.metadata["workflow"] == "mannequin_outfit"

    def test_influencer_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("influencer", brand="MLB")
        result = wf.build_prompt()

        assert result.metadata["workflow"] == "influencer"
        assert result.metadata["category"] == "인물-자유"

    def test_product_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("product_design", brand="MLB")
        result = wf.build_prompt(product_description="MLB 볼캡 제품 디자인")

        assert "MLB" in result.text
        assert result.metadata["category"] == "제품"

    def test_background_swap_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("background_swap")
        result = wf.build_prompt(background="해변 석양 배경")

        assert "해변" in result.text or "석양" in result.text
        assert result.metadata["workflow"] == "background_swap"

    def test_swap_prompt_no_analysis(self):
        """스왑 워크플로는 분석 없이도 기본 프롬프트 생성 가능"""
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("face_swap", brand="MLB")
        result = wf.build_prompt()

        assert result.text  # 비어있지 않음
        assert result.metadata["workflow"] == "face_swap"

    def test_image_roles_in_prompt(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        result = wf.build_prompt()

        assert "IMAGE REFERENCE ROLES" in result.text
        assert "FACE" in result.text
        assert "OUTFIT" in result.text

    def test_override_background(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create(
            "brandcut",
            brand="MLB",
            overrides={"background": "럭셔리 차량 앞"},
        )
        result = wf.build_prompt()
        assert "럭셔리" in result.text

    def test_no_brand_no_brand_section(self):
        from core.modules.workflow_factory import WorkflowFactory

        wf = WorkflowFactory.create("brandcut")  # brand 미지정
        result = wf.build_prompt()

        assert "브랜드 톤" not in result.text


# ============================================================
# AnalysisBundle 테스트
# ============================================================


class TestAnalysisBundle:
    """AnalysisBundle 데이터 구조 테스트"""

    def test_empty_bundle(self):
        from core.modules.workflow_factory import AnalysisBundle

        bundle = AnalysisBundle()
        assert not bundle.has("face")
        assert not bundle.has("outfit")
        assert bundle.analyzers_run == []
        assert bundle.errors == {}

    def test_bundle_has(self):
        from core.modules.workflow_factory import AnalysisBundle

        bundle = AnalysisBundle(face="mock_face_result")
        assert bundle.has("face")
        assert not bundle.has("outfit")

    def test_bundle_with_errors(self):
        from core.modules.workflow_factory import AnalysisBundle

        bundle = AnalysisBundle(errors={"face": "API error"})
        assert "face" in bundle.errors


# ============================================================
# 크로스-카테고리 테스트
# ============================================================


class TestCrossCategory:
    """여러 카테고리에 걸친 일관성 테스트"""

    def test_all_registered_workflows_create(self):
        """모든 등록된 워크플로가 팩토리로 생성 가능"""
        from core.modules.workflow_factory import WorkflowFactory

        for name in WorkflowFactory.list_available():
            wf = WorkflowFactory.create(name, brand="MLB")
            assert wf.config.name == name

    def test_all_registered_workflows_build_prompt(self):
        """모든 워크플로가 프롬프트 빌드 가능 (분석 없이)"""
        from core.modules.workflow_factory import WorkflowFactory

        for name in WorkflowFactory.list_available():
            wf = WorkflowFactory.create(name, brand="MLB")
            result = wf.build_prompt()
            assert result.text, f"{name}: 빈 프롬프트"
            assert result.metadata.get("workflow") == name

    def test_swap_workflows_have_preserve_change(self):
        """스왑 워크플로는 모두 preserve/change가 정의"""
        from core.modules.workflow_config import (
            WorkflowCategory,
            list_by_category,
        )

        swap_configs = list_by_category(WorkflowCategory.SWAP)
        for cfg in swap_configs:
            assert cfg.preserve is not None, f"{cfg.name}: preserve 미정의"
            assert cfg.change is not None, f"{cfg.name}: change 미정의"
            assert len(cfg.preserve) > 0
            assert len(cfg.change) > 0

    def test_person_formal_all_have_face_outfit(self):
        """인물-정규 워크플로는 모두 얼굴/착장 분석기 포함"""
        from core.modules.workflow_config import (
            WorkflowCategory,
            AnalyzerSlot,
            list_by_category,
        )

        formal_configs = list_by_category(WorkflowCategory.PERSON_FORMAL)
        for cfg in formal_configs:
            assert AnalyzerSlot.FACE in cfg.analyzers, f"{cfg.name}: FACE 분석기 없음"
            assert (
                AnalyzerSlot.OUTFIT in cfg.analyzers
            ), f"{cfg.name}: OUTFIT 분석기 없음"


# ============================================================
# 통합: from core.modules import 테스트
# ============================================================


class TestModuleImport:
    """core.modules에서 팩토리 import 가능 확인"""

    def test_import_from_modules(self):
        from core.modules import (
            WorkflowFactory,
            WorkflowInstance,
            AnalysisBundle,
            WorkflowCategory,
            get_workflow_config,
            list_workflows,
        )

        assert WorkflowFactory is not None
        assert list_workflows() is not None

    def test_full_workflow(self):
        """import → create → build_prompt 전체 흐름"""
        from core.modules import WorkflowFactory

        wf = WorkflowFactory.create("brandcut", brand="MLB")
        result = wf.build_prompt(
            gender="female",
            ethnicity="korean",
            age="early_20s",
        )
        assert "MLB" in result.text
        assert "female" in result.metadata.get("gender", "") or "여성" in result.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
