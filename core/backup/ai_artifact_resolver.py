"""
AI Artifact Resolution Module

감지된 AI 티 문제에 대한 해결 전략을 제안하는 모듈.
문제 유형별 프롬프트 개선안, 인페인팅 제안, 재생성 vs 후처리 결정.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum


# ============================================================
# Resolution Strategy Database
# ============================================================

RESOLUTION_STRATEGIES = {
    # ===== SKIN (피부) 관련 =====
    "plastic_skin": {
        "prompt_add": [
            "CRITICAL: Natural skin with visible pores (forehead dense, nose visible, cheeks scattered)",
            "Real photograph texture, NOT airbrushed",
            "Subtle skin imperfections allowed"
        ],
        "inpaint_suggestion": "Face area inpainting with lower CFG",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "over_smoothing": {
        "prompt_add": [
            "Natural skin texture with visible pores",
            "Real photograph, NOT digital painting",
            "Subtle skin detail preserved"
        ],
        "inpaint_suggestion": "Face/skin areas with texture enhancement",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "uneven_skin_tone": {
        "prompt_add": [
            "Even natural skin tone",
            "Consistent skin color across face and body"
        ],
        "inpaint_suggestion": "Color correction on affected areas",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "strange_sheen": {
        "prompt_add": [
            "Natural skin reflection, NOT glossy or wet",
            "Matte to semi-matte skin finish"
        ],
        "inpaint_suggestion": "Reduce highlights on face area",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },

    # ===== HANDS (손/손가락) 관련 =====
    "finger_count": {
        "prompt_add": [
            "CRITICAL: Exactly 5 fingers per hand (thumb + 4 fingers)",
            "Perfect human anatomy",
            "Hands clearly visible and anatomically correct",
            "No extra or missing fingers"
        ],
        "inpaint_suggestion": "Hand area regeneration (entire hand)",
        "regenerate": True,  # 손가락 개수 오류는 항상 재생성
        "temperature_adjust": -0.1,
        "priority": 0  # 최우선
    },
    "finger_deformation": {
        "prompt_add": [
            "CRITICAL: Anatomically correct finger joints and proportions",
            "Natural finger length and thickness",
            "Proper knuckle alignment"
        ],
        "inpaint_suggestion": "Hand area regeneration with anatomy reference",
        "regenerate": True,
        "temperature_adjust": -0.1,
        "priority": 0
    },
    "nail_issues": {
        "prompt_add": [
            "Natural fingernails visible on all fingers",
            "Proper nail shape and position"
        ],
        "inpaint_suggestion": "Fingertip inpainting",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "hand_structure_collapse": {
        "prompt_add": [
            "CRITICAL: Clear palm and back of hand distinction",
            "Natural hand pose following anatomy",
            "No twisted or impossible hand positions"
        ],
        "inpaint_suggestion": "Full hand regeneration required",
        "regenerate": True,
        "temperature_adjust": -0.1,
        "priority": 0
    },

    # ===== FACE (얼굴) 관련 =====
    "asymmetric_eyes": {
        "prompt_add": [
            "Symmetrical eyes (same size, level, and iris size)",
            "Natural eye alignment"
        ],
        "inpaint_suggestion": "Eye area correction with symmetry guide",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "iris_mismatch": {
        "prompt_add": [
            "Matching pupils and iris size in both eyes",
            "Consistent eye reflection/catchlights"
        ],
        "inpaint_suggestion": "Eye detail inpainting",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "teeth_deformation": {
        "prompt_add": [
            "Natural teeth count and alignment",
            "Realistic dental structure"
        ],
        "inpaint_suggestion": "Mouth area regeneration",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "ear_issues": {
        "prompt_add": [
            "Anatomically correct ear shape and position",
            "Symmetrical ears"
        ],
        "inpaint_suggestion": "Ear area correction",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "hairline_issues": {
        "prompt_add": [
            "Natural hairline with realistic hair-skin boundary",
            "No harsh or artificial edges"
        ],
        "inpaint_suggestion": "Hairline blending",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },

    # ===== BACKGROUND (배경) 관련 =====
    "text_distortion": {
        "prompt_add": [
            "Clear, readable text on signs and backgrounds",
            "Proper spelling and font consistency",
            "NO gibberish or mixed alphabets"
        ],
        "inpaint_suggestion": "Background text areas regeneration or removal",
        "regenerate": False,  # 배경 텍스트는 인페인팅으로 처리 가능
        "temperature_adjust": 0,
        "priority": 1
    },
    "repetitive_patterns": {
        "prompt_add": [
            "Natural background variation, NO tiling",
            "Organic scene composition"
        ],
        "inpaint_suggestion": "Background texture variation",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "perspective_error": {
        "prompt_add": [
            "Correct perspective and vanishing points",
            "Consistent scale and proportions"
        ],
        "inpaint_suggestion": "Background regeneration with perspective guides",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "edge_blending": {
        "prompt_add": [
            "Natural person-background separation",
            "Realistic edge quality with appropriate depth of field"
        ],
        "inpaint_suggestion": "Edge refinement around subject",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },

    # ===== CLOTHING (착장) 관련 =====
    "logo_distortion": {
        "prompt_add": [
            "Clear, accurate brand logos (no distortion)",
            "Proper logo placement and spelling"
        ],
        "inpaint_suggestion": "Logo area inpainting with reference",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 1
    },
    "unnatural_wrinkles": {
        "prompt_add": [
            "Natural fabric wrinkles following physics",
            "Realistic cloth draping"
        ],
        "inpaint_suggestion": "Clothing area refinement",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "material_error": {
        "prompt_add": [
            "Accurate material texture (denim/knit/leather/etc)",
            "Consistent fabric appearance"
        ],
        "inpaint_suggestion": "Texture correction on clothing",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "color_bleeding": {
        "prompt_add": [
            "Clear color boundaries between clothing and skin/background",
            "NO color bleeding or smudging"
        ],
        "inpaint_suggestion": "Edge cleanup and color correction",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 1
    },

    # ===== LIGHTING (조명) 관련 =====
    "shadow_mismatch": {
        "prompt_add": [
            "Consistent shadow direction from single light source",
            "Natural shadow fall matching light position"
        ],
        "inpaint_suggestion": "Shadow correction or regeneration",
        "regenerate": True,
        "temperature_adjust": -0.05,
        "priority": 1
    },
    "highlight_error": {
        "prompt_add": [
            "Consistent highlights from primary light source",
            "Natural light reflection, NOT multiple conflicting sources"
        ],
        "inpaint_suggestion": "Highlight correction",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "color_temperature": {
        "prompt_add": [
            "Natural skin tone color temperature",
            "Balanced warm/cool tones appropriate for lighting"
        ],
        "inpaint_suggestion": "White balance adjustment",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    },
    "ambient_occlusion": {
        "prompt_add": [
            "Natural ambient light interaction",
            "Background color reflected on subject where appropriate"
        ],
        "inpaint_suggestion": "Ambient light adjustment",
        "regenerate": False,
        "temperature_adjust": 0,
        "priority": 2
    }
}


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ResolutionResult:
    """AI 티 해결 제안 결과"""

    # 재생성 vs 후처리 결정
    should_regenerate: bool
    regenerate_reason: str  # 재생성 권장 이유

    # 프롬프트 개선안
    prompt_improvements: List[str]  # 추가할 프롬프트 문구
    prompt_removals: List[str]      # 제거할 프롬프트 문구 (선택)

    # 인페인팅 제안
    inpaint_regions: List[str]      # 인페인팅 권장 영역

    # 우선순위별 수정사항
    priority_fixes: List[Dict[str, any]]  # [{priority: 0, issue_type: str, suggestion: str}]

    # Temperature 조정
    temperature_suggestion: Optional[float]  # None이면 기본값 유지
    temperature_reason: str

    # 메타데이터
    total_issues: int
    critical_count: int
    high_count: int


# ============================================================
# Resolver Class
# ============================================================

class AIArtifactResolver:
    """AI 티 문제 해결 제안 엔진

    감지된 AI 티 문제(AIArtifactResult)를 받아서:
    1. 재생성 vs 후처리 결정
    2. 프롬프트 개선안 생성
    3. 인페인팅 영역 제안
    4. 우선순위별 수정사항 정리
    """

    def __init__(self):
        """Resolution 전략 초기화"""
        self.strategies = RESOLUTION_STRATEGIES

    def resolve(self, artifact_result) -> ResolutionResult:
        """감지된 AI 티 문제에 대한 해결 방안 제안

        Args:
            artifact_result: AIArtifactResult 객체 (from ai_artifact_detector)

        Returns:
            ResolutionResult: 해결 제안
        """
        # Issue 타입별 그룹화
        issues_by_type = {}
        for issue in artifact_result.issues:
            issue_type = issue.issue_type
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # 프롬프트 개선안 수집
        prompt_improvements = self._get_prompt_improvements(issues_by_type)

        # 인페인팅 제안 수집
        inpaint_regions = self._get_inpaint_suggestions(issues_by_type)

        # 우선순위별 수정사항 정리
        priority_fixes = self._get_priority_fixes(issues_by_type)

        # 재생성 결정
        should_regenerate, regenerate_reason = self._should_regenerate(artifact_result, issues_by_type)

        # Temperature 조정 제안
        temperature_suggestion, temperature_reason = self._get_temperature_adjustment(issues_by_type)

        # 심각도별 카운트
        from core.ai_artifact_detector import Severity
        critical_count = sum(1 for i in artifact_result.issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in artifact_result.issues if i.severity == Severity.HIGH)

        return ResolutionResult(
            should_regenerate=should_regenerate,
            regenerate_reason=regenerate_reason,
            prompt_improvements=prompt_improvements,
            prompt_removals=[],  # 현재는 제거 제안 없음
            inpaint_regions=inpaint_regions,
            priority_fixes=priority_fixes,
            temperature_suggestion=temperature_suggestion,
            temperature_reason=temperature_reason,
            total_issues=len(artifact_result.issues),
            critical_count=critical_count,
            high_count=high_count
        )

    def _get_prompt_improvements(self, issues_by_type: Dict[str, List]) -> List[str]:
        """문제 유형별 프롬프트 개선안 생성

        Args:
            issues_by_type: {issue_type: [ArtifactIssue, ...]}

        Returns:
            List[str]: 추가할 프롬프트 문구 리스트 (중복 제거됨)
        """
        improvements = []
        seen = set()  # 중복 방지

        for issue_type, issues in issues_by_type.items():
            if issue_type in self.strategies:
                strategy = self.strategies[issue_type]
                for prompt in strategy["prompt_add"]:
                    if prompt not in seen:
                        improvements.append(prompt)
                        seen.add(prompt)

        return improvements

    def _get_inpaint_suggestions(self, issues_by_type: Dict[str, List]) -> List[str]:
        """인페인팅 영역 제안 생성

        Args:
            issues_by_type: {issue_type: [ArtifactIssue, ...]}

        Returns:
            List[str]: 인페인팅 권장 영역 리스트
        """
        suggestions = []
        seen = set()

        for issue_type, issues in issues_by_type.items():
            if issue_type in self.strategies:
                strategy = self.strategies[issue_type]
                suggestion = strategy["inpaint_suggestion"]
                if suggestion and suggestion not in seen:
                    # Location 정보 추가
                    locations = {issue.location for issue in issues}
                    detailed_suggestion = f"{suggestion} (위치: {', '.join(locations)})"
                    suggestions.append(detailed_suggestion)
                    seen.add(suggestion)

        return suggestions

    def _get_priority_fixes(self, issues_by_type: Dict[str, List]) -> List[Dict[str, any]]:
        """우선순위별 수정사항 정리

        Args:
            issues_by_type: {issue_type: [ArtifactIssue, ...]}

        Returns:
            List[Dict]: 우선순위별 정렬된 수정사항
                       [{priority: int, issue_type: str, suggestion: str, count: int}]
        """
        fixes = []

        for issue_type, issues in issues_by_type.items():
            if issue_type in self.strategies:
                strategy = self.strategies[issue_type]
                fixes.append({
                    "priority": strategy["priority"],
                    "issue_type": issue_type,
                    "suggestion": strategy["inpaint_suggestion"],
                    "count": len(issues),
                    "severity": max(issues, key=lambda i: i.severity.value).severity.value
                })

        # Priority 낮은 순 (0 = 최우선), 같으면 심각도 순
        fixes.sort(key=lambda x: (x["priority"], -len(x["severity"])))

        return fixes

    def _should_regenerate(self, artifact_result, issues_by_type: Dict[str, List]) -> tuple[bool, str]:
        """재생성 vs 후처리 결정

        재생성 필요 조건:
        1. CRITICAL 문제가 1개 이상 있음
        2. 손가락/손 구조 문제 있음 (regenerate=True 전략)
        3. Total AI Score가 70 이상 (F등급)

        Args:
            artifact_result: AIArtifactResult
            issues_by_type: {issue_type: [ArtifactIssue, ...]}

        Returns:
            (should_regenerate: bool, reason: str)
        """
        from core.ai_artifact_detector import Severity

        # 1. CRITICAL 문제 체크
        critical_issues = [i for i in artifact_result.issues if i.severity == Severity.CRITICAL]
        if critical_issues:
            return (True, f"CRITICAL 문제 {len(critical_issues)}개 발견 - 재생성 필수")

        # 2. 재생성 필수 문제 유형 체크
        regenerate_required_types = [
            issue_type for issue_type, issues in issues_by_type.items()
            if issue_type in self.strategies and self.strategies[issue_type]["regenerate"]
        ]
        if regenerate_required_types:
            return (True, f"재생성 필수 문제: {', '.join(regenerate_required_types)}")

        # 3. Total AI Score 70 이상 (F등급)
        if artifact_result.total_ai_score >= 70:
            return (True, f"Total AI Score {artifact_result.total_ai_score} (F등급) - 전면 재생성 권장")

        # 재생성 불필요 - 후처리로 해결 가능
        if artifact_result.total_ai_score >= 50:
            reason = f"AI Score {artifact_result.total_ai_score} (C등급) - 인페인팅으로 개선 시도 가능"
        else:
            reason = "사소한 문제 - 후처리로 충분"

        return (False, reason)

    def _get_temperature_adjustment(self, issues_by_type: Dict[str, List]) -> tuple[Optional[float], str]:
        """Temperature 조정 제안

        여러 문제 유형의 temperature_adjust를 종합하여 최종 조정값 산출.

        Args:
            issues_by_type: {issue_type: [ArtifactIssue, ...]}

        Returns:
            (temperature_adjustment: Optional[float], reason: str)
        """
        adjustments = []
        reasons = []

        for issue_type in issues_by_type:
            if issue_type in self.strategies:
                adjust = self.strategies[issue_type]["temperature_adjust"]
                if adjust != 0:
                    adjustments.append(adjust)
                    reasons.append(f"{issue_type}: {adjust:+.2f}")

        if not adjustments:
            return (None, "Temperature 조정 불필요")

        # 평균값 사용 (극단값 방지)
        avg_adjust = sum(adjustments) / len(adjustments)
        avg_adjust = round(avg_adjust, 2)

        reason_str = f"평균 조정값 {avg_adjust:+.2f} ({', '.join(reasons)})"

        return (avg_adjust, reason_str)
