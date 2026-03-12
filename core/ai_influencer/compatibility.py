"""
포즈-배경 호환성 체커

포즈 분석 결과와 배경 분석 결과를 비교하여
물리적 타당성을 검증하고, 비호환 시 대안을 제안합니다.

핵심 규칙:
1. 앉기 포즈(sit) → 배경에 seating 필요
2. 벽 기대기(lean_wall) → 배경에 wall 필요
3. 횡단보도에서 앉기 = 비논리적 (불가능)
4. 배경에 없는 요소를 새로 만들지 말 것 (벤치 환각 금지)
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .pose_analyzer import PoseAnalysisResult
from .background_analyzer import BackgroundAnalysisResult


class CompatibilityLevel(Enum):
    """호환성 수준"""

    COMPATIBLE = "compatible"  # 완전 호환
    ADJUSTABLE = "adjustable"  # 조정 필요 (수정 가능)
    INCOMPATIBLE = "incompatible"  # 비호환 (불가능)


@dataclass
class CompatibilityIssue:
    """호환성 이슈"""

    issue_type: str  # stance_mismatch, missing_element, logical_error
    severity: str  # critical, warning, info
    description: str  # 문제 설명 (한국어)
    suggestion: str  # 해결 방안 (한국어)


@dataclass
class CompatibilityResult:
    """호환성 검사 결과"""

    level: CompatibilityLevel
    pose_stance: str  # 포즈의 stance
    background_provides: List[str]  # 배경이 제공하는 요소
    background_supports: List[str]  # 배경이 지원하는 stance

    # 이슈 목록
    issues: List[CompatibilityIssue] = field(default_factory=list)

    # 대안 제안
    alternative_stances: List[str] = field(default_factory=list)
    suggested_adjustments: List[str] = field(default_factory=list)

    # 점수 (0-100)
    score: int = 100

    def is_compatible(self) -> bool:
        """호환 가능 여부"""
        return self.level != CompatibilityLevel.INCOMPATIBLE

    def format_korean(self) -> str:
        """한국어 결과 출력"""
        lines = []
        lines.append(f"## 포즈-배경 호환성 검사 결과")
        lines.append("")
        lines.append(f"**호환성**: {self._level_korean(self.level)}")
        lines.append(f"**점수**: {self.score}/100")
        lines.append("")
        lines.append(f"**포즈 stance**: {self.pose_stance}")
        lines.append(f"**배경 제공 요소**: {', '.join(self.background_provides)}")
        lines.append(f"**배경 지원 stance**: {', '.join(self.background_supports)}")

        if self.issues:
            lines.append("")
            lines.append("### 이슈")
            for issue in self.issues:
                severity_icon = {
                    "critical": "[X]",
                    "warning": "[!]",
                    "info": "[i]",
                }.get(issue.severity, "[-]")
                lines.append(f"{severity_icon} {issue.description}")
                lines.append(f"    -> {issue.suggestion}")

        if self.alternative_stances:
            lines.append("")
            lines.append(f"### 대안 포즈 (배경과 호환)")
            for stance in self.alternative_stances:
                lines.append(f"- {stance}")

        if self.suggested_adjustments:
            lines.append("")
            lines.append("### 조정 제안")
            for adj in self.suggested_adjustments:
                lines.append(f"- {adj}")

        return "\n".join(lines)

    def _level_korean(self, level: CompatibilityLevel) -> str:
        """호환성 수준 한국어 변환"""
        mapping = {
            CompatibilityLevel.COMPATIBLE: "호환 (OK)",
            CompatibilityLevel.ADJUSTABLE: "조정 필요",
            CompatibilityLevel.INCOMPATIBLE: "비호환 (불가능)",
        }
        return mapping.get(level, str(level))


class CompatibilityChecker:
    """포즈-배경 호환성 체커"""

    # stance별 필수 요소
    STANCE_REQUIREMENTS = {
        "sit": {
            "required_or": [
                "seating",
                "potential_seating",
            ],  # 연석, 계단 등 잠재적 좌석도 가능
            "description": "앉기 포즈는 앉을 곳(seating 또는 연석/계단 등)이 필요합니다",
        },
        "lean_wall": {
            "required": ["wall"],
            "description": "벽에 기대는 포즈는 벽(wall)이 필요합니다",
        },
        "lean": {
            "required_or": ["rail", "surface"],
            "description": "기대는 포즈는 난간(rail) 또는 표면(surface)이 필요합니다",
        },
        "walk": {
            "required": ["walkway"],
            "description": "걷는 포즈는 걸을 수 있는 공간(walkway)이 필요합니다",
            "can_substitute": True,  # 넓은 공간이면 walkway 없어도 가능
        },
        "stand": {
            "required": [],
            "description": "서있는 포즈는 특별한 요소가 필요하지 않습니다",
        },
        "kneel": {
            "required": [],
            "description": "무릎 꿇는 포즈는 바닥 공간만 있으면 됩니다",
        },
    }

    # 비논리적 조합 (절대 불가)
    ILLOGICAL_COMBINATIONS = [
        {
            "scene_type": "crosswalk",
            "stance": "sit",
            "reason": "횡단보도에서 앉는 것은 비논리적입니다",
        },
        {
            "scene_type": "crosswalk",
            "stance": "kneel",
            "reason": "횡단보도에서 무릎 꿇는 것은 비논리적입니다",
        },
        {
            "scene_type": "elevator",
            "stance": "walk",
            "reason": "엘리베이터 안에서 걷는 것은 공간상 불가능합니다",
        },
        {
            "scene_type": "elevator",
            "stance": "sit",
            "reason": "엘리베이터 안에서 앉는 것은 비논리적입니다 (좌석 없음)",
        },
    ]

    def check(
        self,
        pose: PoseAnalysisResult,
        background: BackgroundAnalysisResult,
    ) -> CompatibilityResult:
        """
        포즈와 배경의 호환성 검사

        Args:
            pose: 포즈 분석 결과
            background: 배경 분석 결과

        Returns:
            CompatibilityResult: 호환성 결과
        """
        issues = []
        score = 100

        # 1. 비논리적 조합 체크 (절대 불가 - 단, 잠재적 좌석이 있으면 예외)
        for combo in self.ILLOGICAL_COMBINATIONS:
            if (
                background.scene_type == combo["scene_type"]
                and pose.stance == combo["stance"]
            ):
                # 잠재적 좌석이 있으면 sit은 가능 (연석, 계단 등에 앉기)
                if pose.stance == "sit" and (
                    "potential_seating" in background.provides
                    or "seating" in background.provides
                ):
                    # 잠재적 좌석이 있으므로 비논리적 조합 규칙 무시
                    continue

                issues.append(
                    CompatibilityIssue(
                        issue_type="logical_error",
                        severity="critical",
                        description=combo["reason"],
                        suggestion=f"'{pose.stance}' 대신 배경에 맞는 포즈를 사용하세요",
                    )
                )
                score = 0  # 절대 불가

        # 2. stance 필수 요소 체크
        requirements = self.STANCE_REQUIREMENTS.get(pose.stance, {})
        required = requirements.get("required", [])
        required_or = requirements.get("required_or", [])

        if required:
            # AND 조건: 모든 요소 필요
            missing = [r for r in required if r not in background.provides]
            if missing:
                issues.append(
                    CompatibilityIssue(
                        issue_type="missing_element",
                        severity="critical",
                        description=f"'{pose.stance}' 포즈에 필요한 요소가 배경에 없습니다: {', '.join(missing)}",
                        suggestion=requirements.get("description", ""),
                    )
                )
                score = max(0, score - 50)

        if required_or:
            # OR 조건: 하나라도 있으면 OK
            has_any = any(r in background.provides for r in required_or)
            if not has_any:
                # 잠재적 좌석 위치가 있는지도 확인 (potential_seating_locations)
                has_potential_seating = (
                    hasattr(background, "potential_seating_locations")
                    and background.potential_seating_locations
                )
                if not has_potential_seating:
                    issues.append(
                        CompatibilityIssue(
                            issue_type="missing_element",
                            severity="critical",
                            description=f"'{pose.stance}' 포즈에 필요한 요소({' 또는 '.join(required_or)})가 배경에 없습니다",
                            suggestion=requirements.get("description", ""),
                        )
                    )
                    score = max(0, score - 50)

        # 3. 배경의 supported_stances에 포즈 stance가 있는지 체크
        if pose.stance not in background.supported_stances:
            # VLM이 이미 불가능하다고 판단한 경우
            issues.append(
                CompatibilityIssue(
                    issue_type="stance_mismatch",
                    severity="warning",
                    description=f"배경 분석 결과 '{pose.stance}' 포즈는 권장되지 않습니다",
                    suggestion=f"권장 포즈: {', '.join(background.supported_stances)}",
                )
            )
            score = max(0, score - 30)

        # 4. 대안 stance 제안
        alternative_stances = [
            s for s in background.supported_stances if s != pose.stance
        ]

        # 5. 조정 제안 생성
        suggested_adjustments = self._generate_adjustments(pose, background, issues)

        # 6. 호환성 수준 결정
        if score == 0:
            level = CompatibilityLevel.INCOMPATIBLE
        elif score < 70:
            level = CompatibilityLevel.ADJUSTABLE
        else:
            level = CompatibilityLevel.COMPATIBLE

        return CompatibilityResult(
            level=level,
            pose_stance=pose.stance,
            background_provides=background.provides,
            background_supports=background.supported_stances,
            issues=issues,
            alternative_stances=alternative_stances,
            suggested_adjustments=suggested_adjustments,
            score=score,
        )

    def _generate_adjustments(
        self,
        pose: PoseAnalysisResult,
        background: BackgroundAnalysisResult,
        issues: List[CompatibilityIssue],
    ) -> List[str]:
        """조정 제안 생성"""
        adjustments = []

        for issue in issues:
            if issue.issue_type == "logical_error":
                # 비논리적 조합: stance 변경 필수
                safe_stances = [
                    s for s in background.supported_stances if s in ["stand", "walk"]
                ]
                if safe_stances:
                    adjustments.append(f"포즈를 '{safe_stances[0]}'(으)로 변경하세요")

            elif issue.issue_type == "missing_element":
                # 요소 부족: 대안 찾기
                if pose.stance == "sit" and "seating" not in background.provides:
                    # 앉기 → 기존 배경 요소 활용
                    if "wall" in background.provides:
                        adjustments.append(
                            "벽에 기대서 서있는 포즈(lean_wall)로 변경하세요"
                        )
                    elif "rail" in background.provides:
                        adjustments.append("난간에 기대는 포즈(lean)로 변경하세요")
                    else:
                        adjustments.append("서있는 포즈(stand)로 변경하세요")

                elif pose.stance == "lean_wall" and "wall" not in background.provides:
                    # 벽 기대기 → 벽 없음
                    if "rail" in background.provides:
                        adjustments.append("난간에 기대는 포즈(lean)로 변경하세요")
                    else:
                        adjustments.append("서있는 포즈(stand)로 변경하세요")

        # 배경 방향 조정 제안
        if background.scene_type == "crosswalk" and pose.stance in ["sit", "lean_wall"]:
            adjustments.append(
                "배경에서 횡단보도가 보이지 않는 방향으로 구도를 조정하세요"
            )
            adjustments.append("또는 카메라 앵글을 좁혀서 걷는 모습만 포착하세요")

        return adjustments

    def find_best_stance(
        self,
        background: BackgroundAnalysisResult,
        preferred_category: str = None,
    ) -> List[str]:
        """
        배경에 가장 적합한 stance 찾기

        Args:
            background: 배경 분석 결과
            preferred_category: 선호 카테고리 (전신, 상반신, 앉기 등)

        Returns:
            추천 stance 목록 (우선순위순)
        """
        # 배경이 지원하는 stance 기반
        supported = background.supported_stances.copy()

        # 우선순위 정렬
        priority = {
            "stand": 1,
            "lean_wall": 2,
            "walk": 3,
            "lean": 4,
            "sit": 5,
            "kneel": 6,
        }

        return sorted(supported, key=lambda s: priority.get(s, 99))


def check_compatibility(
    pose: PoseAnalysisResult,
    background: BackgroundAnalysisResult,
) -> CompatibilityResult:
    """
    포즈-배경 호환성 검사 (편의 함수)

    Args:
        pose: 포즈 분석 결과
        background: 배경 분석 결과

    Returns:
        CompatibilityResult: 호환성 결과
    """
    checker = CompatibilityChecker()
    return checker.check(pose, background)


def get_safe_stances_for_background(
    background: BackgroundAnalysisResult,
) -> List[str]:
    """
    배경에서 안전하게 사용 가능한 stance 목록

    Args:
        background: 배경 분석 결과

    Returns:
        안전한 stance 목록
    """
    checker = CompatibilityChecker()
    return checker.find_best_stance(background)
