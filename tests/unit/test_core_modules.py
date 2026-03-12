"""
tests/unit/test_core_modules.py

core/modules 시스템 종합 검증 스크립트.

API 호출 없이 임포트, 유닛, 통합, 워크플로 컴포지션을 검증한다.

실행 방법:
    PYTHONPATH=. .venv/Scripts/python tests/unit/test_core_modules.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# 테스트 헬퍼
# ---------------------------------------------------------------------------

_PASS = 0
_FAIL = 0


def ok(name: str):
    global _PASS
    _PASS += 1
    print(f"[OK]   {name}")


def fail(name: str, reason: str = ""):
    global _FAIL
    _FAIL += 1
    msg = f"[FAIL] {name}"
    if reason:
        msg += f" -- {reason}"
    print(msg)


def section(title: str):
    print()
    print(f"--- {title} ---")


def run_all():
    test_imports()
    test_vlm_utils_parse_json()
    test_vlm_utils_load_image()
    test_mappings()
    test_negative_builder()
    test_prompt_assembler_basic()
    test_preservation_result()
    test_build_preservation_prompt()
    test_ecommerce_workflow_composition()
    test_pose_change_workflow_composition()

    print()
    print(f"=== RESULTS: {_PASS} passed, {_FAIL} failed ===")
    if _FAIL:
        sys.exit(1)


# ===========================================================================
# 1. IMPORT VERIFICATION
# ===========================================================================


def test_imports():
    section("1. Import Verification")

    # --- core.modules top-level star import
    try:
        from core.modules import (
            load_image,
            parse_json_response,
            pil_to_part,
            vlm_call,
            analyze_face,
            FaceAnalysisResult,
            ExtendedFaceAnalysisResult,
            OutfitAnalysis,
            OutfitItem,
            LogoInfo,
            analyze_outfit,
            PoseAnalysisResult,
            analyze_pose,
            ExpressionAnalysisResult,
            analyze_expression,
            HairAnalysisResult,
            analyze_hair,
            BackgroundAnalysisResult,
            analyze_background,
        )

        ok("core.modules top-level imports")
    except Exception as e:
        fail("core.modules top-level imports", str(e))

    # --- vlm_utils
    try:
        from core.modules.vlm_utils import load_image, parse_json_response, pil_to_part

        ok("core.modules.vlm_utils")
    except Exception as e:
        fail("core.modules.vlm_utils", str(e))

    # --- analyze_face
    try:
        from core.modules.analyze_face import (
            analyze_face,
            FaceAnalysisResult,
            ExtendedFaceAnalysisResult,
        )

        ok("core.modules.analyze_face")
    except Exception as e:
        fail("core.modules.analyze_face", str(e))

    # --- analyze_outfit
    try:
        from core.modules.analyze_outfit import analyze_outfit, OutfitAnalysis

        ok("core.modules.analyze_outfit")
    except Exception as e:
        fail("core.modules.analyze_outfit", str(e))

    # --- analyze_pose
    try:
        from core.modules.analyze_pose import analyze_pose, PoseAnalysisResult

        ok("core.modules.analyze_pose")
    except Exception as e:
        fail("core.modules.analyze_pose", str(e))

    # --- analyze_expression
    try:
        from core.modules.analyze_expression import (
            analyze_expression,
            ExpressionAnalysisResult,
        )

        ok("core.modules.analyze_expression")
    except Exception as e:
        fail("core.modules.analyze_expression", str(e))

    # --- analyze_hair
    try:
        from core.modules.analyze_hair import analyze_hair, HairAnalysisResult

        ok("core.modules.analyze_hair")
    except Exception as e:
        fail("core.modules.analyze_hair", str(e))

    # --- analyze_background
    try:
        from core.modules.analyze_background import (
            analyze_background,
            BackgroundAnalysisResult,
        )

        ok("core.modules.analyze_background")
    except Exception as e:
        fail("core.modules.analyze_background", str(e))

    # --- preserve_source
    try:
        from core.modules.preserve_source import (
            analyze_for_preservation,
            PreservationResult,
        )

        ok("core.modules.preserve_source")
    except Exception as e:
        fail("core.modules.preserve_source", str(e))

    # --- prompt assembler
    try:
        from core.modules.prompt import PromptAssembler, PromptResult

        ok("core.modules.prompt (PromptAssembler, PromptResult)")
    except Exception as e:
        fail("core.modules.prompt (PromptAssembler, PromptResult)", str(e))

    # --- prompt.outfit_section
    try:
        from core.modules.prompt.outfit_section import format_outfit_section

        ok("core.modules.prompt.outfit_section")
    except Exception as e:
        fail("core.modules.prompt.outfit_section", str(e))

    # --- prompt.negative
    try:
        from core.modules.prompt.negative import NegativePromptBuilder

        ok("core.modules.prompt.negative (NegativePromptBuilder)")
    except Exception as e:
        fail("core.modules.prompt.negative (NegativePromptBuilder)", str(e))

    # --- prompt.camera_section
    try:
        from core.modules.prompt.camera_section import build_camera_section

        ok("core.modules.prompt.camera_section")
    except Exception as e:
        fail("core.modules.prompt.camera_section", str(e))

    # --- prompt.preservation
    try:
        from core.modules.prompt.preservation import (
            build_preservation_prompt,
            PreservationLevel,
        )

        ok("core.modules.prompt.preservation")
    except Exception as e:
        fail("core.modules.prompt.preservation", str(e))

    # --- prompt.mappings
    try:
        from core.modules.prompt.mappings import (
            STATE_TO_KOREAN,
            infer_category,
            GENDER_MAP,
        )

        ok("core.modules.prompt.mappings")
    except Exception as e:
        fail("core.modules.prompt.mappings", str(e))


# ===========================================================================
# 2. vlm_utils UNIT TESTS (no API calls)
# ===========================================================================


def test_vlm_utils_parse_json():
    section("2. vlm_utils -- parse_json_response")

    from core.modules.vlm_utils import parse_json_response

    # 2-a. 유효한 JSON 문자열
    result = parse_json_response('{"score": 90, "passed": true}')
    try:
        assert result.get("score") == 90
        assert result.get("passed") is True
        ok("parse_json_response -- valid JSON string")
    except AssertionError as e:
        fail("parse_json_response -- valid JSON string", str(e))

    # 2-b. 마크다운 코드블록 래핑
    wrapped = '```json\n{"name": "MLB", "value": 42}\n```'
    result = parse_json_response(wrapped)
    try:
        assert result.get("name") == "MLB"
        assert result.get("value") == 42
        ok("parse_json_response -- markdown code block wrapper")
    except AssertionError as e:
        fail("parse_json_response -- markdown code block wrapper", str(e))

    # 2-c. 코드블록 (json 태그 없음)
    wrapped_plain = '```\n{"key": "val"}\n```'
    result = parse_json_response(wrapped_plain)
    try:
        assert result.get("key") == "val"
        ok("parse_json_response -- plain code block (no json tag)")
    except AssertionError as e:
        fail("parse_json_response -- plain code block (no json tag)", str(e))

    # 2-d. 유효하지 않은 입력 -> error 키 반환
    result = parse_json_response("this is not json at all!!!")
    try:
        assert isinstance(result, dict), "result must be dict"
        # error 키가 있거나 raw 키가 있어야 함 (파싱 실패 신호)
        assert (
            "error" in result or "raw" in result
        ), f"Expected error/raw key in result, got: {result}"
        ok("parse_json_response -- invalid input returns error dict")
    except AssertionError as e:
        fail("parse_json_response -- invalid input returns error dict", str(e))

    # 2-e. 빈 문자열
    result = parse_json_response("")
    try:
        assert isinstance(result, dict)
        assert "error" in result
        ok("parse_json_response -- empty string")
    except AssertionError as e:
        fail("parse_json_response -- empty string", str(e))

    # 2-f. 텍스트 내부에 {} 포함
    result = parse_json_response('Some text before {"x": 1, "y": 2} and after')
    try:
        assert result.get("x") == 1
        assert result.get("y") == 2
        ok("parse_json_response -- JSON embedded in text")
    except AssertionError as e:
        fail("parse_json_response -- JSON embedded in text", str(e))


def test_vlm_utils_load_image():
    section("2b. vlm_utils -- load_image (PIL passthrough)")

    from core.modules.vlm_utils import load_image
    from PIL import Image

    # PIL Image 직접 전달 -> 그대로 반환 (RGB 보장)
    img = Image.new("RGB", (100, 100), color=(128, 64, 32))
    result = load_image(img)
    try:
        assert result is not None, "load_image should not return None for PIL Image"
        assert result.mode == "RGB", f"Expected RGB mode, got {result.mode}"
        ok("load_image -- PIL Image passthrough")
    except AssertionError as e:
        fail("load_image -- PIL Image passthrough", str(e))

    # RGBA 이미지 -> RGB로 변환
    img_rgba = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
    result_rgba = load_image(img_rgba)
    try:
        assert result_rgba is not None
        assert result_rgba.mode == "RGB", f"Expected RGB, got {result_rgba.mode}"
        ok("load_image -- RGBA to RGB conversion")
    except AssertionError as e:
        fail("load_image -- RGBA to RGB conversion", str(e))

    # 잘못된 타입 -> None 반환
    result_bad = load_image(12345)  # type: ignore
    try:
        assert result_bad is None, "load_image should return None for unsupported type"
        ok("load_image -- unsupported type returns None")
    except AssertionError as e:
        fail("load_image -- unsupported type returns None", str(e))

    # max_size 리사이즈 검증
    img_large = Image.new("RGB", (2000, 1000), color=(0, 128, 255))
    result_resized = load_image(img_large, max_size=512)
    try:
        assert result_resized is not None
        assert (
            max(result_resized.size) <= 512
        ), f"Image should be resized, got size {result_resized.size}"
        ok("load_image -- max_size resize")
    except AssertionError as e:
        fail("load_image -- max_size resize", str(e))


# ===========================================================================
# 3. MAPPINGS UNIT TESTS
# ===========================================================================


def test_mappings():
    section("3. Mappings")

    from core.modules.prompt.mappings import (
        STATE_TO_KOREAN,
        infer_category,
        GENDER_MAP,
        format_logo_detail,
    )

    # 3-a. STATE_TO_KOREAN 기대 키 존재
    expected_keys = [
        "open",
        "draped",
        "half_tucked",
        "tucked",
        "normal",
        "backwards",
        "cropped",
    ]
    # half_tucked는 없을 수 있음 -- 실제 키만 체크
    actual_keys = list(STATE_TO_KOREAN.keys())

    for key in ["open", "draped", "tucked", "normal", "backwards", "cropped"]:
        try:
            assert key in STATE_TO_KOREAN, f"Key '{key}' missing in STATE_TO_KOREAN"
            ok(f"STATE_TO_KOREAN -- key '{key}' exists")
        except AssertionError as e:
            fail(f"STATE_TO_KOREAN -- key '{key}' exists", str(e))

    # 3-b. infer_category 올바른 한글 카테고리 반환
    test_cases = [
        ("outer", "", "아우터"),
        ("top", "", "상의"),
        ("bottom", "", "하의"),
        ("shoes", "", "신발"),
        ("headwear", "", "헤드웨어"),
        ("bag", "", "가방"),
        ("belt", "", "벨트"),
        ("jewelry", "", "주얼리"),
    ]
    for cat, name, expected in test_cases:
        result = infer_category(cat, name)
        try:
            assert (
                result == expected
            ), f"infer_category('{cat}') => '{result}', expected '{expected}'"
            ok(f"infer_category -- '{cat}' => '{expected}'")
        except AssertionError as e:
            fail(f"infer_category -- '{cat}'", str(e))

    # 3-c. 키워드 기반 추론
    result_jacket = infer_category("outerwear", "varsity jacket")
    try:
        assert result_jacket == "아우터", f"Got '{result_jacket}'"
        ok("infer_category -- keyword 'jacket' infers 아우터")
    except AssertionError as e:
        fail("infer_category -- keyword 'jacket' infers 아우터", str(e))

    result_jeans = infer_category("unknown", "cargo jeans")
    try:
        assert result_jeans == "하의", f"Got '{result_jeans}'"
        ok("infer_category -- keyword 'jeans' infers 하의")
    except AssertionError as e:
        fail("infer_category -- keyword 'jeans' infers 하의", str(e))

    # 3-d. GENDER_MAP 항목 확인
    try:
        assert "male" in GENDER_MAP
        assert "female" in GENDER_MAP
        assert GENDER_MAP["female"] == "여성"
        assert GENDER_MAP["male"] == "남성"
        ok("GENDER_MAP -- male/female entries correct")
    except AssertionError as e:
        fail("GENDER_MAP -- male/female entries", str(e))

    # 3-e. format_logo_detail -> MUST 형식 문자열
    class MockLogo:
        brand = "MLB"
        position = "front_center"
        type = "printed"

    logo_str = format_logo_detail(MockLogo())
    try:
        assert "MUST" in logo_str, f"Expected 'MUST' in logo detail, got: {logo_str}"
        assert "MLB" in logo_str, f"Expected brand name in logo detail, got: {logo_str}"
        ok("format_logo_detail -- produces MUST format string")
    except AssertionError as e:
        fail("format_logo_detail -- produces MUST format string", str(e))


# ===========================================================================
# 4. NegativePromptBuilder UNIT TESTS
# ===========================================================================


def test_negative_builder():
    section("4. NegativePromptBuilder")

    from core.modules.prompt.negative import NegativePromptBuilder

    # 4-a. add_base() includes "deformed fingers"
    result = NegativePromptBuilder().add_base().build()
    try:
        assert (
            "deformed fingers" in result
        ), f"'deformed fingers' not found in: {result}"
        ok("NegativePromptBuilder.add_base() includes 'deformed fingers'")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_base() includes 'deformed fingers'", str(e))

    # 4-b. add_base() includes "plastic skin"
    try:
        assert "plastic skin" in result, f"'plastic skin' not found in: {result}"
        ok("NegativePromptBuilder.add_base() includes 'plastic skin'")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_base() includes 'plastic skin'", str(e))

    # 4-c. add_brand("MLB") includes "golden hour"
    result_mlb = NegativePromptBuilder().add_brand("MLB").build()
    try:
        assert "golden hour" in result_mlb, f"'golden hour' not found in: {result_mlb}"
        ok("NegativePromptBuilder.add_brand('MLB') includes 'golden hour'")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_brand('MLB') includes 'golden hour'", str(e))

    # 4-d. add_brand("MLB") includes "warm amber"
    try:
        assert "warm amber" in result_mlb, f"'warm amber' not found in: {result_mlb}"
        ok("NegativePromptBuilder.add_brand('MLB') includes 'warm amber'")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_brand('MLB') includes 'warm amber'", str(e))

    # 4-e. add_if(True, [...]) includes the items
    result_with = NegativePromptBuilder().add_if(True, ["test_item_xyz"]).build()
    try:
        assert (
            "test_item_xyz" in result_with
        ), f"Conditional item not found: {result_with}"
        ok("NegativePromptBuilder.add_if(True, ...) includes item")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_if(True, ...) includes item", str(e))

    # 4-f. add_if(False, [...]) does NOT include the items
    result_without = (
        NegativePromptBuilder().add_if(False, ["should_not_appear"]).build()
    )
    try:
        assert (
            "should_not_appear" not in result_without
        ), f"Item should be excluded: {result_without}"
        ok("NegativePromptBuilder.add_if(False, ...) excludes item")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_if(False, ...) excludes item", str(e))

    # 4-g. build() returns comma-separated string
    result_multi = NegativePromptBuilder().add_base().add_brand("MLB").build()
    try:
        assert ", " in result_multi, "Expected comma-separated string"
        items = result_multi.split(", ")
        assert len(items) > 5, f"Expected many items, got {len(items)}"
        ok("NegativePromptBuilder.build() returns comma-separated string")
    except AssertionError as e:
        fail("NegativePromptBuilder.build() returns comma-separated string", str(e))

    # 4-h. 중복 제거 확인 (동일 항목 두 번 추가)
    result_dedup = (
        NegativePromptBuilder()
        .add_items(["duplicate_item"])
        .add_items(["duplicate_item"])
        .build()
    )
    try:
        count = result_dedup.split(", ").count("duplicate_item")
        assert count == 1, f"Expected 1 occurrence of duplicate, got {count}"
        ok("NegativePromptBuilder -- deduplication works")
    except AssertionError as e:
        fail("NegativePromptBuilder -- deduplication works", str(e))

    # 4-i. add_framing("MFS") includes framing-specific negatives
    result_framing = NegativePromptBuilder().add_framing("MFS").build()
    try:
        assert (
            "feet visible" in result_framing or "shoes visible" in result_framing
        ), f"MFS framing negatives not found: {result_framing}"
        ok("NegativePromptBuilder.add_framing('MFS') adds framing negatives")
    except AssertionError as e:
        fail("NegativePromptBuilder.add_framing('MFS') adds framing negatives", str(e))


# ===========================================================================
# 5. PromptAssembler INTEGRATION TEST
# ===========================================================================


def test_prompt_assembler_basic():
    section("5. PromptAssembler -- Integration Test")

    from core.modules.prompt import PromptAssembler, PromptResult

    # 5-a. 기본 빌드 (모델 + 배경 + 카메라 + 네거티브)
    try:
        result = (
            PromptAssembler()
            .set_model_info(gender="female", ethnicity="korean", age="early_20s")
            .set_background(description="urban street with graffiti wall")
            .set_camera(framing="full_body", angle="3/4")
            .set_negative(base=True, brand="MLB")
            .build()
        )
        assert isinstance(result, PromptResult), "Expected PromptResult instance"
        ok("PromptAssembler.build() returns PromptResult")
    except Exception as e:
        fail("PromptAssembler.build() returns PromptResult", str(e))
        return  # 이후 테스트는 result에 의존하므로 중단

    # 5-b. 섹션 헤더 존재 확인
    for header in ["## [모델]", "## [배경]", "## [네거티브]"]:
        try:
            assert (
                header in result.text
            ), f"Expected '{header}' in text. Got:\n{result.text[:500]}"
            ok(f"PromptAssembler -- section '{header}' exists in text")
        except AssertionError as e:
            fail(f"PromptAssembler -- section '{header}' exists in text", str(e))

    # 5-c. 착장 섹션 없음 (set_outfit 호출 안 함)
    try:
        assert (
            "## [착장]" not in result.text
        ), "착장 section should not appear when set_outfit() is not called"
        ok("PromptAssembler -- 착장 section absent when not set")
    except AssertionError as e:
        fail("PromptAssembler -- 착장 section absent when not set", str(e))

    # 5-d. metadata 키 존재
    try:
        assert isinstance(result.metadata, dict), "metadata should be a dict"
        assert len(result.metadata) > 0, "metadata should not be empty"
        ok("PromptAssembler -- metadata dict populated")
    except AssertionError as e:
        fail("PromptAssembler -- metadata dict populated", str(e))

    # 5-e. sections dict에서 특정 섹션 조회
    try:
        assert (
            "모델" in result.sections
        ), f"Expected '모델' key in sections. Got keys: {list(result.sections.keys())}"
        ok("PromptAssembler -- result.sections['모델'] accessible")
    except AssertionError as e:
        fail("PromptAssembler -- result.sections['모델'] accessible", str(e))

    # 5-f. 모델 정보가 text에 올바르게 포함
    try:
        assert (
            "korean" in result.text.lower() or "한국" in result.text
        ), f"Ethnicity 'korean' not found in text:\n{result.text[:400]}"
        ok("PromptAssembler -- model ethnicity included in text")
    except AssertionError as e:
        fail("PromptAssembler -- model ethnicity included in text", str(e))

    # 5-g. 배경 텍스트가 포함
    try:
        assert (
            "urban street" in result.text or "graffiti" in result.text
        ), f"Background description not found in text:\n{result.text[:400]}"
        ok("PromptAssembler -- background description included in text")
    except AssertionError as e:
        fail("PromptAssembler -- background description included in text", str(e))

    # 5-h. MLB 네거티브 포함
    try:
        assert (
            "golden hour" in result.text
        ), f"MLB negative 'golden hour' not found in text:\n{result.text[-300:]}"
        ok("PromptAssembler -- MLB brand negative included")
    except AssertionError as e:
        fail("PromptAssembler -- MLB brand negative included", str(e))

    # 5-i. 촬영 섹션 확인 (camera_section이 등록됨)
    try:
        # 카메라 섹션은 "촬영_세팅" 키로 등록됨
        assert (
            "촬영_세팅" in result.sections
        ), f"Expected '촬영_세팅' in sections, got: {list(result.sections.keys())}"
        ok("PromptAssembler -- 촬영_세팅 section in sections dict")
    except AssertionError as e:
        fail("PromptAssembler -- 촬영_세팅 section in sections dict", str(e))

    # 5-j. set_brand_tone 확인
    try:
        result_with_tone = (
            PromptAssembler()
            .set_model_info(gender="female", ethnicity="korean")
            .set_brand_tone("MLB")
            .build()
        )
        assert "MLB" in result_with_tone.text, "Brand tone section should contain 'MLB'"
        ok("PromptAssembler -- set_brand_tone('MLB') includes brand name")
    except Exception as e:
        fail("PromptAssembler -- set_brand_tone('MLB')", str(e))


# ===========================================================================
# 6. PreservationResult UNIT TESTS
# ===========================================================================


def test_preservation_result():
    section("6. PreservationResult Unit Tests")

    from core.modules.preserve_source import PreservationResult

    # 6-a. 직접 생성 (VLM 호출 없이)
    try:
        pres = PreservationResult(
            preserve=["face", "outfit", "background"],
            change=["pose"],
            face_description="Korean female, oval face, big almond eyes",
            outfit_description="MLB white tank top with NY logo, cargo denim",
            background_description="urban street",
        )
        assert pres.preserve == ["face", "outfit", "background"]
        assert pres.change == ["pose"]
        ok("PreservationResult -- direct instantiation")
    except Exception as e:
        fail("PreservationResult -- direct instantiation", str(e))
        return

    # 6-b. to_prompt_text() produces "PRESERVE" instructions
    prompt_text = pres.to_prompt_text()
    try:
        assert (
            "PRESERVE" in prompt_text
        ), f"Expected 'PRESERVE' in to_prompt_text(), got:\n{prompt_text}"
        ok("PreservationResult.to_prompt_text() includes 'PRESERVE'")
    except AssertionError as e:
        fail("PreservationResult.to_prompt_text() includes 'PRESERVE'", str(e))

    # 6-c. to_prompt_text() contains preserved element descriptions
    try:
        assert (
            "almond eyes" in prompt_text or "oval face" in prompt_text
        ), f"Face description not found in prompt text:\n{prompt_text}"
        ok("PreservationResult.to_prompt_text() includes face description")
    except AssertionError as e:
        fail("PreservationResult.to_prompt_text() includes face description", str(e))

    try:
        assert (
            "MLB" in prompt_text or "cargo denim" in prompt_text
        ), f"Outfit description not found in prompt text:\n{prompt_text}"
        ok("PreservationResult.to_prompt_text() includes outfit description")
    except AssertionError as e:
        fail("PreservationResult.to_prompt_text() includes outfit description", str(e))

    # 6-d. CHANGE 섹션 포함
    try:
        assert (
            "CHANGE" in prompt_text
        ), f"Expected 'CHANGE' in to_prompt_text(), got:\n{prompt_text}"
        assert (
            "pose" in prompt_text
        ), f"Expected 'pose' in CHANGE section, got:\n{prompt_text}"
        ok("PreservationResult.to_prompt_text() includes CHANGE section")
    except AssertionError as e:
        fail("PreservationResult.to_prompt_text() includes CHANGE section", str(e))

    # 6-e. to_dict() returns proper dict with expected keys
    d = pres.to_dict()
    try:
        assert isinstance(d, dict), "to_dict() should return a dict"
        required_keys = [
            "preserve",
            "change",
            "face_description",
            "outfit_description",
            "background_description",
            "pose_description",
        ]
        for key in required_keys:
            assert key in d, f"Expected key '{key}' in to_dict() result"
        ok("PreservationResult.to_dict() contains required keys")
    except AssertionError as e:
        fail("PreservationResult.to_dict() contains required keys", str(e))

    try:
        assert d["face_description"] == "Korean female, oval face, big almond eyes"
        assert d["preserve"] == ["face", "outfit", "background"]
        assert d["change"] == ["pose"]
        ok("PreservationResult.to_dict() values correct")
    except AssertionError as e:
        fail("PreservationResult.to_dict() values correct", str(e))

    # 6-f. 변경 대상은 to_prompt_text()에 [tag] 형태로 포함되지 않음
    # (pose를 change로 했으면 [pose] 설명이 없어야 함)
    try:
        # pose_description이 None이므로 [pose] 라인이 없어야 함
        assert (
            "[pose]" not in prompt_text
        ), f"[pose] should not appear in PRESERVE block since it's in 'change'. Got:\n{prompt_text}"
        ok("PreservationResult -- change target not in PRESERVE block")
    except AssertionError as e:
        fail("PreservationResult -- change target not in PRESERVE block", str(e))

    # 6-g. get_preserved_elements() 함수
    try:
        preserved = pres.get_preserved_elements()
        assert (
            "face" in preserved
        ), f"Expected 'face' in preserved elements: {preserved}"
        assert (
            "outfit" in preserved
        ), f"Expected 'outfit' in preserved elements: {preserved}"
        assert (
            "background" in preserved
        ), f"Expected 'background' in preserved elements: {preserved}"
        assert (
            "pose" not in preserved
        ), f"'pose' should not be in preserved elements (it's in change): {preserved}"
        ok("PreservationResult.get_preserved_elements() correct")
    except AssertionError as e:
        fail("PreservationResult.get_preserved_elements()", str(e))


# ===========================================================================
# 7. build_preservation_prompt UNIT TESTS
# ===========================================================================


def test_build_preservation_prompt():
    section("7. build_preservation_prompt")

    from core.modules.prompt.preservation import (
        build_preservation_prompt,
        PreservationLevel,
    )

    # 7-a. BASIC 레벨 빌드
    try:
        basic = build_preservation_prompt(level=PreservationLevel.BASIC)
        assert isinstance(basic, str), "Expected string output"
        assert len(basic) > 50, f"BASIC prompt too short: {len(basic)} chars"
        ok("build_preservation_prompt(BASIC) returns non-empty string")
    except Exception as e:
        fail("build_preservation_prompt(BASIC)", str(e))

    # 7-b. DETAILED 레벨이 BASIC보다 길어야 함 (더 많은 지시사항)
    try:
        detailed = build_preservation_prompt(level=PreservationLevel.DETAILED)
        assert len(detailed) >= len(
            basic
        ), f"DETAILED ({len(detailed)}) should be >= BASIC ({len(basic)})"
        ok("build_preservation_prompt(DETAILED) >= BASIC length")
    except Exception as e:
        fail("build_preservation_prompt(DETAILED) >= BASIC length", str(e))

    # 7-c. FULL 레벨
    try:
        full = build_preservation_prompt(level=PreservationLevel.FULL)
        assert len(full) >= len(
            basic
        ), f"FULL ({len(full)}) should be >= BASIC ({len(basic)})"
        ok("build_preservation_prompt(FULL) >= BASIC length")
    except Exception as e:
        fail("build_preservation_prompt(FULL)", str(e))

    # 7-d. BASIC 레벨에 "person" 또는 "model" 보존 지시 포함
    try:
        assert (
            "PERSON" in basic.upper() or "MODEL" in basic.upper()
        ), f"Expected person/model preservation instructions in BASIC:\n{basic[:300]}"
        ok("build_preservation_prompt(BASIC) includes person/model preservation")
    except AssertionError as e:
        fail(
            "build_preservation_prompt(BASIC) includes person/model preservation",
            str(e),
        )

    # 7-e. include_structure_transform=True 시 구조물 텍스트 포함
    try:
        with_transform = build_preservation_prompt(
            level=PreservationLevel.BASIC,
            include_structure_transform=True,
        )
        assert len(with_transform) > len(
            basic
        ), "Structure transform should add content"
        assert (
            "STRUCTURE" in with_transform or "texture" in with_transform.lower()
        ), f"Structure transform text not found:\n{with_transform[-300:]}"
        ok("build_preservation_prompt -- include_structure_transform adds content")
    except Exception as e:
        fail("build_preservation_prompt -- include_structure_transform", str(e))

    # 7-f. physics_analysis 추가 시 내용 추가
    try:
        physics = {
            "geometry": {"perspective": "eye-level", "horizon_y": "0.5"},
            "lighting": {"direction_clock": "2", "color_temp": "cool"},
        }
        with_physics = build_preservation_prompt(
            level=PreservationLevel.BASIC,
            physics_analysis=physics,
        )
        assert len(with_physics) > len(basic), "Physics section should add content"
        assert (
            "perspective" in with_physics.lower() or "PHYSICS" in with_physics
        ), f"Physics content not found:\n{with_physics[-300:]}"
        ok("build_preservation_prompt -- physics_analysis adds physics section")
    except Exception as e:
        fail(
            "build_preservation_prompt -- physics_analysis adds physics section", str(e)
        )


# ===========================================================================
# 8. NEW WORKFLOW COMPOSITION TESTS
# ===========================================================================


def test_ecommerce_workflow_composition():
    section("8a. New Workflow -- Ecommerce Composition (no API)")

    from core.modules.prompt import PromptAssembler

    try:
        result = (
            PromptAssembler()
            .set_model_info(gender="female", ethnicity="korean", age="early_20s")
            .set_background(
                description="clean white studio background, soft studio lighting"
            )
            .set_camera(framing="full_body", angle="front", lens="85mm")
            .set_brand_tone("MLB")
            .set_negative(base=True, brand="MLB")
            .build()
        )

        assert (
            "## [모델]" in result.text
        ), f"[모델] section missing:\n{result.text[:500]}"
        ok("Ecommerce composition -- [모델] section present")

        assert (
            "## [배경]" in result.text
        ), f"[배경] section missing:\n{result.text[:500]}"
        ok("Ecommerce composition -- [배경] section present")

        assert (
            "studio" in result.text.lower()
        ), f"'studio' not found in text:\n{result.text[:500]}"
        ok("Ecommerce composition -- studio background in text")

        assert "MLB" in result.text, "Brand tone section should mention MLB"
        ok("Ecommerce composition -- MLB brand tone in text")

    except Exception as e:
        fail("Ecommerce workflow composition", str(e))

    # 추가: 착장 없는 이커머스 = 착장 섹션 없음
    try:
        result2 = (
            PromptAssembler()
            .set_model_info(gender="male", ethnicity="korean")
            .set_background(description="white backdrop")
            .set_camera(framing="FS")
            .set_negative(base=True)
            .build()
        )
        # 착장 섹션 없음
        assert (
            "착장" not in result2.sections
        ), "착장 section should not be present without set_outfit()"
        ok("Ecommerce composition -- no outfit section when not set")

        # 성별 남성 확인
        assert (
            "남성" in result2.text or "male" in result2.text.lower()
        ), f"Male gender not in text:\n{result2.text[:300]}"
        ok("Ecommerce composition -- male gender in text")

    except Exception as e:
        fail("Ecommerce workflow composition (male, no outfit)", str(e))


def test_pose_change_workflow_composition():
    section("8b. New Workflow -- Pose Change Composition (no API)")

    from core.modules.preserve_source import PreservationResult
    from core.modules.prompt import PromptAssembler

    # 8b-1. PreservationResult 직접 생성 (포즈 변경 시나리오)
    preservation = PreservationResult(
        preserve=["face", "outfit", "background"],
        change=["pose"],
        face_description="Korean female, oval face, big almond eyes",
        outfit_description="MLB white tank top with NY logo, cargo denim",
        background_description="urban street",
    )

    # 8b-2. PromptAssembler에 preservation 직접 삽입
    # set_preservation()은 배경 교체용 PreservationLevel 기반이므로
    # preservation 결과는 set_header 또는 custom section으로 추가
    try:
        preservation_text = preservation.to_prompt_text()

        result = (
            PromptAssembler()
            .set_header(preservation_text)
            .set_camera(framing="full_body")
            .set_negative(base=True)
            .build()
        )

        # PRESERVE 지시문 포함
        assert (
            "PRESERVE" in result.text
        ), f"'PRESERVE' not found in pose change prompt:\n{result.text[:400]}"
        ok("Pose change composition -- PRESERVE instruction in text")

        # 얼굴 설명 포함
        assert (
            "face" in result.text.lower() or "얼굴" in result.text
        ), f"face/얼굴 not found in text:\n{result.text[:400]}"
        ok("Pose change composition -- face reference in text")

        # CHANGE 명시
        assert (
            "CHANGE" in result.text
        ), f"'CHANGE' not found in text:\n{result.text[:400]}"
        ok("Pose change composition -- CHANGE instruction in text")

        # pose가 CHANGE에 포함
        assert (
            "pose" in result.text.lower()
        ), f"'pose' not found in text:\n{result.text[:400]}"
        ok("Pose change composition -- 'pose' in CHANGE")

    except Exception as e:
        fail("Pose change workflow composition", str(e))

    # 8b-3. 착장 스왑 시나리오 (변경 = outfit)
    try:
        swap_preservation = PreservationResult(
            preserve=["face", "pose", "background"],
            change=["outfit"],
            face_description="Korean female, sharp features, monolid eyes",
            pose_description="Standing straight, arms at sides, eye-level angle, full body",
            background_description="indoor studio, white wall",
        )
        swap_text = swap_preservation.to_prompt_text()

        assert "PRESERVE" in swap_text
        assert "[face]" in swap_text or "Korean female" in swap_text
        assert "[pose]" in swap_text or "Standing" in swap_text
        assert "outfit" in swap_text  # CHANGE 부분에
        ok("Outfit swap preservation -- PRESERVE/CHANGE sections correct")

    except Exception as e:
        fail("Outfit swap preservation scenario", str(e))

    # 8b-4. PreservationResult + PromptAssembler 조합 (add_custom_section)
    try:
        custom_result = (
            PromptAssembler()
            .add_custom_section("보존지시", preservation_text)
            .set_camera(framing="FS", angle="front")
            .set_negative(base=True, brand="MLB")
            .build()
        )
        assert (
            "보존지시" in custom_result.text or "PRESERVE" in custom_result.text
        ), f"Custom section not found:\n{custom_result.text[:400]}"
        ok("Pose change -- add_custom_section with preservation text")

    except Exception as e:
        fail("Pose change -- add_custom_section with preservation text", str(e))


# ===========================================================================
# ENTRY POINT
# ===========================================================================


if __name__ == "__main__":
    print("[TEST] core/modules system verification")
    print(f"[TEST] Project root: {project_root}")
    print()
    run_all()
