"""
VLM 분석기 및 호환성 체커 테스트

테스트 항목:
1. PoseAnalyzer - 포즈 이미지에서 상세 신체 부위 분석
2. BackgroundAnalyzer - 배경 이미지에서 provides/supported_stances 추출
3. CompatibilityChecker - 포즈-배경 호환성 검증

실행:
    python tests/influencer/test_vlm_analyzers.py
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from core.ai_influencer import (
    PoseAnalyzer,
    analyze_pose,
    PoseAnalysisResult,
    BackgroundAnalyzer,
    analyze_background,
    BackgroundAnalysisResult,
    CompatibilityChecker,
    check_compatibility,
    CompatibilityLevel,
)


# ============================================================
# TEST CONFIGURATION
# ============================================================
TEST_DB_PATH = project_root / "db" / "인플테스트"

# 테스트 케이스 정의
POSE_TEST_CASES = [
    {
        "name": "walking_full_body",
        "path": TEST_DB_PATH / "3. 포즈" / "1. 전신" / "전신 (1).jpeg",
        "expected_stances": ["stand", "walk"],  # VLM이 보행/서있기로 분석 가능
    },
    {
        "name": "sitting_pose",
        "path": TEST_DB_PATH / "3. 포즈" / "3. 앉아있는" / "앉아있는 (1).png",
        "expected_stances": ["sit"],
    },
    {
        "name": "mirror_selfie",
        "path": TEST_DB_PATH / "3. 포즈" / "4. 거울셀피" / "거울셀피 (1).png",
        "expected_stances": ["stand"],  # 거울셀피도 대부분 서있음
    },
]

BACKGROUND_TEST_CASES = [
    {
        "name": "crosswalk",
        "path": TEST_DB_PATH / "4. 배경" / "9. 횡단보도" / "횡단보도 (1).jpeg",
        "expected_scene_type": "crosswalk",
        "expected_provides": ["walkway"],
        # VLM은 물리적 가능성만 분석 - 비논리적 조합은 CompatibilityChecker에서 필터링
        "should_support": ["stand", "walk"],
    },
    {
        "name": "cafe",
        "path": TEST_DB_PATH / "4. 배경" / "1. 핫플카페" / "핫플 카페 (1).jpeg",
        # 실외 거리 카페일 수 있음 - scene_type 유연하게
        "expected_scene_types": ["cafe", "street"],  # 여러 가능성 허용
        "should_support": ["stand"],  # 최소한 서기는 가능
    },
    {
        "name": "elevator",
        "path": TEST_DB_PATH / "4. 배경" / "8. 엘레베이터" / "엘리베이터 (1).jpeg",
        "expected_scene_type": "elevator",
        "expected_provides": ["mirror", "wall"],
        # VLM이 물리적으로 분석 - walk/sit 불가는 비즈니스 로직
        "should_support": ["stand", "lean_wall"],
    },
    {
        "name": "graffiti_wall",
        "path": TEST_DB_PATH / "4. 배경" / "2. 그래피티" / "그래피티 (1).png",
        "expected_scene_type": "graffiti",
        "should_support": ["stand", "lean_wall"],  # 그래피티벽은 기대기 가능
    },
]

# 호환성 테스트 케이스 (예상되는 비호환 조합)
INCOMPATIBILITY_TEST_CASES = [
    {
        "name": "crosswalk_sit",
        "pose_path": TEST_DB_PATH / "3. 포즈" / "3. 앉아있는" / "앉아있는 (1).png",
        "bg_path": TEST_DB_PATH / "4. 배경" / "9. 횡단보도" / "횡단보도 (1).jpeg",
        "expected_level": CompatibilityLevel.INCOMPATIBLE,
        "reason": "Sitting at crosswalk is illogical",
    },
    {
        "name": "elevator_sit",
        "pose_path": TEST_DB_PATH / "3. 포즈" / "3. 앉아있는" / "앉아있는 (1).png",
        "bg_path": TEST_DB_PATH / "4. 배경" / "8. 엘레베이터" / "엘리베이터 (1).jpeg",
        "expected_level": CompatibilityLevel.INCOMPATIBLE,
        "reason": "Sitting in elevator is illogical (no seating)",
    },
    {
        "name": "graffiti_stand",
        "pose_path": TEST_DB_PATH / "3. 포즈" / "1. 전신" / "전신 (1).jpeg",
        "bg_path": TEST_DB_PATH / "4. 배경" / "2. 그래피티" / "그래피티 (1).png",
        "expected_level": CompatibilityLevel.COMPATIBLE,
        "reason": "Standing at graffiti wall - compatible",
    },
    {
        "name": "elevator_stand",
        "pose_path": TEST_DB_PATH / "3. 포즈" / "4. 거울셀피" / "거울셀피 (1).png",
        "bg_path": TEST_DB_PATH / "4. 배경" / "8. 엘레베이터" / "엘리베이터 (1).jpeg",
        "expected_level": CompatibilityLevel.COMPATIBLE,
        "reason": "Standing in elevator - compatible (mirror selfie)",
    },
]


# ============================================================
# TEST FUNCTIONS
# ============================================================


def test_pose_analyzer():
    """PoseAnalyzer 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] PoseAnalyzer")
    print("=" * 60)

    results = []

    for case in POSE_TEST_CASES:
        if not case["path"].exists():
            print(f"  [SKIP] {case['name']}: File not found")
            continue

        print(f"\n  [TESTING] {case['name']}")
        print(f"    Path: {case['path']}")

        try:
            result = analyze_pose(case["path"])

            # 결과 출력
            expected = case.get("expected_stances", [case.get("expected_stance")])
            print(f"    [RESULT]")
            print(f"      stance: {result.stance} (expected: {expected})")
            print(f"      confidence: {result.confidence:.2f}")
            print(f"      camera_angle: {result.camera_angle}")
            print(f"      framing: {result.framing}")
            print(f"      Body parts:")
            print(f"        left_arm: {result.left_arm}")
            print(f"        right_arm: {result.right_arm}")
            print(f"        left_hand: {result.left_hand}")
            print(f"        right_hand: {result.right_hand}")
            print(f"        left_leg: {result.left_leg}")
            print(f"        right_leg: {result.right_leg}")
            print(f"        hip: {result.hip}")

            # stance 일치 여부 (복수 허용)
            stance_match = result.stance in expected
            print(f"    [STANCE MATCH]: {'PASS' if stance_match else 'FAIL'}")

            results.append(
                {
                    "case": case["name"],
                    "stance_match": stance_match,
                    "result": result,
                }
            )

        except Exception as e:
            print(f"    [ERROR] {e}")
            results.append(
                {
                    "case": case["name"],
                    "stance_match": False,
                    "error": str(e),
                }
            )

    return results


def test_background_analyzer():
    """BackgroundAnalyzer 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] BackgroundAnalyzer")
    print("=" * 60)

    results = []

    for case in BACKGROUND_TEST_CASES:
        if not case["path"].exists():
            print(f"  [SKIP] {case['name']}: File not found")
            continue

        print(f"\n  [TESTING] {case['name']}")
        print(f"    Path: {case['path']}")

        try:
            result = analyze_background(case["path"])

            # 결과 출력
            expected_scene = case.get("expected_scene_type") or case.get(
                "expected_scene_types", "any"
            )
            print(f"    [RESULT]")
            print(f"      scene_type: {result.scene_type} (expected: {expected_scene})")
            print(f"      provides: {result.provides}")
            print(f"      supported_stances: {result.supported_stances}")
            print(f"      region: {result.region}")
            print(f"      time_of_day: {result.time_of_day}")
            print(f"      confidence: {result.confidence:.2f}")

            if result.notes:
                print(f"      notes: {result.notes}")

            # 검증
            checks = {}

            # scene_type 검증 (단일 또는 복수 허용)
            if "expected_scene_type" in case:
                checks["scene_type_match"] = (
                    result.scene_type == case["expected_scene_type"]
                )
            elif "expected_scene_types" in case:
                checks["scene_type_match"] = (
                    result.scene_type in case["expected_scene_types"]
                )
                print(
                    f"    [SCENE TYPE]: {result.scene_type} (allowed: {case['expected_scene_types']})"
                )

            # provides 검증
            if "expected_provides" in case:
                checks["provides_match"] = all(
                    p in result.provides for p in case["expected_provides"]
                )

            # should_support 검증 (호환 stance)
            if "should_support" in case:
                checks["should_support"] = all(
                    s in result.supported_stances for s in case["should_support"]
                )
                print(f"    [SHOULD SUPPORT]: {case['should_support']}")
                print(f"      Check: {'PASS' if checks['should_support'] else 'FAIL'}")

            all_passed = all(checks.values())
            print(f"    [OVERALL]: {'PASS' if all_passed else 'FAIL'}")

            results.append(
                {
                    "case": case["name"],
                    "checks": checks,
                    "all_passed": all_passed,
                    "result": result,
                }
            )

        except Exception as e:
            print(f"    [ERROR] {e}")
            results.append(
                {
                    "case": case["name"],
                    "all_passed": False,
                    "error": str(e),
                }
            )

    return results


def test_compatibility_checker():
    """CompatibilityChecker 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] CompatibilityChecker")
    print("=" * 60)

    results = []

    for case in INCOMPATIBILITY_TEST_CASES:
        pose_path = case["pose_path"]
        bg_path = case["bg_path"]

        if not pose_path.exists() or not bg_path.exists():
            print(f"  [SKIP] {case['name']}: File not found")
            continue

        print(f"\n  [TESTING] {case['name']}")
        print(f"    Pose: {pose_path.name}")
        print(f"    Background: {bg_path.name}")
        print(f"    Expected: {case['expected_level'].value}")
        print(f"    Reason: {case['reason']}")

        try:
            # 각각 분석
            pose_result = analyze_pose(pose_path)
            bg_result = analyze_background(bg_path)

            print(f"\n    [POSE ANALYSIS]")
            print(f"      stance: {pose_result.stance}")

            print(f"\n    [BACKGROUND ANALYSIS]")
            print(f"      scene_type: {bg_result.scene_type}")
            print(f"      provides: {bg_result.provides}")
            print(f"      supported_stances: {bg_result.supported_stances}")

            # 호환성 검사
            compat_result = check_compatibility(pose_result, bg_result)

            print(f"\n    [COMPATIBILITY RESULT]")
            print(f"      level: {compat_result.level.value}")
            print(f"      score: {compat_result.score}/100")

            if compat_result.issues:
                print(f"      issues:")
                for issue in compat_result.issues:
                    print(f"        - [{issue.severity}] {issue.description}")
                    print(f"          -> {issue.suggestion}")

            if compat_result.alternative_stances:
                print(f"      alternative_stances: {compat_result.alternative_stances}")

            # 예상 결과와 비교
            level_match = compat_result.level == case["expected_level"]
            print(f"\n    [LEVEL MATCH]: {'PASS' if level_match else 'FAIL'}")

            if not level_match:
                print(f"      Expected: {case['expected_level'].value}")
                print(f"      Got: {compat_result.level.value}")

            results.append(
                {
                    "case": case["name"],
                    "level_match": level_match,
                    "result": compat_result,
                }
            )

        except Exception as e:
            print(f"    [ERROR] {e}")
            import traceback

            traceback.print_exc()
            results.append(
                {
                    "case": case["name"],
                    "level_match": False,
                    "error": str(e),
                }
            )

    return results


def save_test_results(pose_results, bg_results, compat_results):
    """테스트 결과 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "Fnf_studio_outputs" / "vlm_analyzer_tests" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # 요약 생성
    summary = {
        "timestamp": timestamp,
        "pose_analyzer": {
            "total": len(pose_results),
            "passed": sum(1 for r in pose_results if r.get("stance_match", False)),
        },
        "background_analyzer": {
            "total": len(bg_results),
            "passed": sum(1 for r in bg_results if r.get("all_passed", False)),
        },
        "compatibility_checker": {
            "total": len(compat_results),
            "passed": sum(1 for r in compat_results if r.get("level_match", False)),
        },
    }

    # 상세 결과 (dataclass는 직렬화 불가하므로 요약만)
    def serialize_result(r):
        """결과를 JSON 직렬화 가능하게 변환"""
        if "result" in r and hasattr(r["result"], "__dict__"):
            # dataclass를 dict로 변환 (raw_response 제외)
            result_dict = {}
            for k, v in r["result"].__dict__.items():
                if k != "raw_response":
                    if hasattr(v, "value"):  # Enum
                        result_dict[k] = v.value
                    elif hasattr(v, "__dict__"):  # nested dataclass
                        result_dict[k] = str(v)
                    else:
                        result_dict[k] = v
            return {
                **{k: v for k, v in r.items() if k != "result"},
                "result": result_dict,
            }
        return r

    detailed = {
        "pose_analyzer": [serialize_result(r) for r in pose_results],
        "background_analyzer": [serialize_result(r) for r in bg_results],
        "compatibility_checker": [serialize_result(r) for r in compat_results],
    }

    # 저장
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open(output_dir / "detailed_results.json", "w", encoding="utf-8") as f:
        json.dump(detailed, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[SAVED] Results saved to: {output_dir}")
    return summary, output_dir


def print_summary(summary):
    """요약 출력"""
    print("\n" + "=" * 60)
    print("[SUMMARY]")
    print("=" * 60)

    for test_name, stats in summary.items():
        if test_name == "timestamp":
            continue
        passed = stats["passed"]
        total = stats["total"]
        pct = (passed / total * 100) if total > 0 else 0
        status = "PASS" if passed == total else "FAIL"
        print(f"  {test_name}: {passed}/{total} ({pct:.0f}%) [{status}]")


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("VLM Analyzer & Compatibility Checker Test")
    print("=" * 60)
    print(f"Test DB: {TEST_DB_PATH}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 테스트 실행
    pose_results = test_pose_analyzer()
    bg_results = test_background_analyzer()
    compat_results = test_compatibility_checker()

    # 결과 저장 및 요약
    summary, output_dir = save_test_results(pose_results, bg_results, compat_results)
    print_summary(summary)

    # 전체 통과 여부
    all_tests_passed = all(
        [
            summary["pose_analyzer"]["passed"] == summary["pose_analyzer"]["total"],
            summary["background_analyzer"]["passed"]
            == summary["background_analyzer"]["total"],
            summary["compatibility_checker"]["passed"]
            == summary["compatibility_checker"]["total"],
        ]
    )

    print("\n" + "=" * 60)
    if all_tests_passed:
        print("[OVERALL] ALL TESTS PASSED")
    else:
        print("[OVERALL] SOME TESTS FAILED - Check detailed results")
    print("=" * 60)

    return all_tests_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
