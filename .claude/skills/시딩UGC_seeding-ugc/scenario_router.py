"""
시나리오 자동 라우팅 모듈

사용자의 자연어 한국어 입력을 seeding_ugc.json의 시나리오, 카메라 스타일, 피부 상태로 자동 매칭합니다.

Example:
    router = ScenarioRouter()
    result = router.route("아침 루틴 3장 촬영해줘")
    # RoutingResult(scenario="morning_routine", camera_style="mirror_film", count=3, ...)

    # 전후 비교 자동 감지
    results = router.route("피부 루틴 전후 비교")
    # [before_skincare, after_skincare] 두 개의 결과 반환
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class RoutingResult:
    """라우팅 결과"""
    category: str  # pain_point, before_after, daily_routine
    scenario: str  # headache_sun, morning_routine 등
    camera_style: str  # selfie_complaint, mirror_film, friend_recording
    skin_state: List[str]  # ["oily_shiny"], ["bare_clean", "post_product"] 등
    brand_name: Optional[str] = None
    count: int = 1
    confidence: float = 0.0  # 0.0-1.0, 키워드 매칭 신뢰도
    before_after: bool = False  # True if part of before/after pair


class ScenarioRouter:
    """시나리오 자동 라우터 - 키워드 기반 매칭"""

    # 시나리오별 키워드 매핑
    SCENARIO_KEYWORDS = {
        # Pain Point 시나리오
        "pain_point.headache_sun": ["두통", "햇빛", "자외선", "여름", "뜨거운", "햇살", "일광"],
        "pain_point.oily_frustration": ["번들거림", "유분", "기름", "오일리", "텍스처", "번들", "번들번들"],
        "pain_point.acne_concern": ["트러블", "여드름", "뾰루지", "피부 고민", "피부문제", "피부트러블"],
        "pain_point.dryness_flaking": ["건조", "각질", "당김", "겨울", "보습", "푸석", "갈라짐"],
        "pain_point.dark_circles": ["피곤", "다크서클", "수면부족", "피로", "다크", "눈밑", "다크써클"],
        "pain_point.wind_mess": ["바람", "엉망", "흐트러진", "야외", "바람맞은", "헝클어진"],

        # Before/After 시나리오
        "before_after.before_skincare": ["전", "before", "루틴 전", "세안 후", "비포", "사용 전"],
        "before_after.after_skincare": ["후", "after", "루틴 후", "완료", "애프터", "사용 후", "바른 후"],
        "before_after.before_makeup": ["메이크업 전", "맨얼굴", "민낯", "화장 전", "베이스 전"],
        "before_after.after_makeup": ["메이크업 후", "완성", "결과", "화장 후", "메이크업완료", "완료된"],

        # Daily Routine 시나리오
        "daily_routine.morning_routine": ["아침", "모닝", "루틴", "출근 전", "바르는", "아침루틴", "기상"],
        "daily_routine.commute_touchup": ["출근", "이동", "터치업", "외출", "출근길", "통근"],
        "daily_routine.midday_refresh": ["점심", "오후", "리프레시", "번들거림", "정오", "낮"],
        "daily_routine.night_routine": ["저녁", "클렌징", "나이트", "잠자기 전", "밤루틴", "취침전"],
        "daily_routine.workout_post": ["운동", "땀", "헬스", "필라테스", "러닝", "요가", "운동후", "체육관"],
    }

    # 카메라 스타일 기본값 (시나리오 카테고리별)
    CAMERA_STYLE_DEFAULTS = {
        "pain_point": "selfie_complaint",
        "before_after": "mirror_film",
        "daily_routine": "mirror_film",  # 일부는 friend_recording (아래 오버라이드)
    }

    # 특정 시나리오별 카메라 스타일 오버라이드
    CAMERA_STYLE_OVERRIDES = {
        "daily_routine.workout_post": "friend_recording",
        "daily_routine.commute_touchup": "friend_recording",
    }

    # 피부 상태 기본값 (시나리오별)
    SKIN_STATE_DEFAULTS = {
        "pain_point.headache_sun": ["sweaty_flushed", "sun_damaged"],
        "pain_point.oily_frustration": ["oily_shiny"],
        "pain_point.acne_concern": ["blemished"],
        "pain_point.dryness_flaking": ["dry_flaky"],
        "pain_point.dark_circles": ["tired_dull"],
        "pain_point.wind_mess": ["normal_daily"],  # with wind redness

        "before_after.before_skincare": ["bare_clean"],
        "before_after.after_skincare": ["post_product"],
        "before_after.before_makeup": ["bare_clean"],  # with imperfections
        "before_after.after_makeup": ["post_product"],

        "daily_routine.morning_routine": ["bare_clean", "post_product"],  # progressive
        "daily_routine.commute_touchup": ["normal_daily"],
        "daily_routine.midday_refresh": ["oily_shiny"],
        "daily_routine.night_routine": ["tired_dull"],
        "daily_routine.workout_post": ["sweaty_flushed"],
    }

    # 브랜드명 키워드
    BRAND_KEYWORDS = {
        "Banillaco": ["바닐라코", "banillaco", "바닐라꼬"],
        "MLB": ["mlb", "엠엘비", "MLB"],
        "Discovery": ["디스커버리", "discovery", "Discovery"],
        "Duvetica": ["듀베티카", "duvetica", "Duvetica"],
        "SergioTacchini": ["세르지오", "타키니", "sergio", "tacchini", "세르지오타키니"],
    }

    # 전후 비교 키워드
    BEFORE_AFTER_KEYWORDS = ["전후", "비교", "before/after", "before after", "비포애프터", "전/후"]

    def __init__(self):
        """초기화"""
        pass

    def route(self, user_input: str, overrides: Optional[Dict[str, Any]] = None) -> List[RoutingResult]:
        """
        사용자 입력을 시나리오로 라우팅

        Args:
            user_input: 한국어 자연어 입력 (예: "아침 루틴 3장", "피부 전후 비교")
            overrides: 명시적 오버라이드 (예: {"camera_style": "friend_recording"})

        Returns:
            List[RoutingResult]: 라우팅 결과 리스트 (전후 비교인 경우 2개)
        """
        overrides = overrides or {}
        user_input_lower = user_input.lower()

        # 1. 전후 비교 감지
        is_before_after_comparison = any(keyword in user_input_lower for keyword in self.BEFORE_AFTER_KEYWORDS)

        # 2. 장수 추출 (예: "3장", "4장")
        count = self._extract_count(user_input)

        # 3. 브랜드명 추출
        brand_name = self._extract_brand(user_input)

        # 4. 시나리오 매칭
        matched_scenario, confidence = self._match_scenario(user_input_lower)

        if not matched_scenario:
            # 매칭 실패 시 기본값 반환
            return [self._create_default_result(count, brand_name, overrides)]

        # 5. 전후 비교인 경우 두 개의 결과 생성
        if is_before_after_comparison:
            return self._create_before_after_pair(matched_scenario, count, brand_name, confidence, overrides)

        # 6. 단일 결과 생성
        return [self._create_routing_result(matched_scenario, count, brand_name, confidence, overrides)]

    def _match_scenario(self, user_input: str) -> tuple[Optional[str], float]:
        """
        키워드 매칭으로 시나리오 찾기

        Returns:
            (scenario_full_name, confidence_score)
        """
        best_match = None
        max_matches = 0

        for scenario_full, keywords in self.SCENARIO_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in user_input)
            if matches > max_matches:
                max_matches = matches
                best_match = scenario_full

        if not best_match:
            return None, 0.0

        # 신뢰도 계산 (매칭된 키워드 수 / 해당 시나리오의 총 키워드 수)
        total_keywords = len(self.SCENARIO_KEYWORDS[best_match])
        confidence = min(max_matches / total_keywords, 1.0)

        return best_match, confidence

    def _extract_count(self, user_input: str) -> int:
        """장수 추출 (예: "3장" → 3)"""
        match = re.search(r'(\d+)\s*장', user_input)
        if match:
            return int(match.group(1))
        return 1

    def _extract_brand(self, user_input: str) -> Optional[str]:
        """브랜드명 추출"""
        user_input_lower = user_input.lower()
        for brand, keywords in self.BRAND_KEYWORDS.items():
            if any(keyword.lower() in user_input_lower for keyword in keywords):
                return brand
        return None

    def _create_routing_result(
        self,
        scenario_full: str,
        count: int,
        brand_name: Optional[str],
        confidence: float,
        overrides: Dict[str, Any]
    ) -> RoutingResult:
        """RoutingResult 객체 생성"""
        # 시나리오 파싱 (예: "pain_point.headache_sun" → category="pain_point", scenario="headache_sun")
        category, scenario = scenario_full.split(".", 1)

        # 카메라 스타일 결정
        if "camera_style" in overrides:
            camera_style = overrides["camera_style"]
        elif scenario_full in self.CAMERA_STYLE_OVERRIDES:
            camera_style = self.CAMERA_STYLE_OVERRIDES[scenario_full]
        else:
            camera_style = self.CAMERA_STYLE_DEFAULTS.get(category, "mirror_film")

        # 피부 상태 결정
        if "skin_state" in overrides:
            skin_state = overrides["skin_state"]
        else:
            skin_state = self.SKIN_STATE_DEFAULTS.get(scenario_full, ["normal_daily"])

        return RoutingResult(
            category=category,
            scenario=scenario,
            camera_style=camera_style,
            skin_state=skin_state,
            brand_name=overrides.get("brand_name", brand_name),
            count=overrides.get("count", count),
            confidence=confidence
        )

    def _create_before_after_pair(
        self,
        matched_scenario: str,
        count: int,
        brand_name: Optional[str],
        confidence: float,
        overrides: Dict[str, Any]
    ) -> List[RoutingResult]:
        """전후 비교 시나리오 페어 생성"""
        category = matched_scenario.split(".", 1)[0]

        # 카테고리에 따라 before/after 시나리오 결정
        if category == "pain_point":
            # pain_point는 전후 비교가 없으므로 동일한 시나리오 2회
            return [
                self._create_routing_result(matched_scenario, count, brand_name, confidence, overrides),
                self._create_routing_result(matched_scenario, count, brand_name, confidence, overrides),
            ]
        elif category == "before_after":
            # 이미 before/after 시나리오인 경우 (카테고리명은 유지, 시나리오명만 변경)
            _, scn = matched_scenario.split(".", 1)
            if "before" in scn:
                after_scn = scn.replace("before", "after")
                after_scenario = f"before_after.{after_scn}"
            else:
                before_scn = scn.replace("after", "before")
                after_scenario = matched_scenario
                matched_scenario = f"before_after.{before_scn}"
        else:  # daily_routine
            # daily_routine은 일반적으로 skincare 전후로 매핑
            matched_scenario = "before_after.before_skincare"
            after_scenario = "before_after.after_skincare"

        before_result = self._create_routing_result(matched_scenario, count, brand_name, confidence, overrides)
        after_result = self._create_routing_result(after_scenario, count, brand_name, confidence, overrides)

        # Mark as before/after pair
        before_result.before_after = True
        after_result.before_after = True

        return [before_result, after_result]

    def _create_default_result(
        self,
        count: int,
        brand_name: Optional[str],
        overrides: Dict[str, Any]
    ) -> RoutingResult:
        """매칭 실패 시 기본 결과 생성"""
        return RoutingResult(
            category=overrides.get("category", "daily_routine"),
            scenario=overrides.get("scenario", "morning_routine"),
            camera_style=overrides.get("camera_style", "mirror_film"),
            skin_state=overrides.get("skin_state", ["normal_daily"]),
            brand_name=overrides.get("brand_name", brand_name),
            count=overrides.get("count", count),
            confidence=0.0
        )


# 편의 함수
def route_scenario(user_input: str, overrides: Optional[Dict[str, Any]] = None) -> List[RoutingResult]:
    """
    글로벌 편의 함수 - 시나리오 라우팅

    Example:
        results = route_scenario("아침 루틴 3장")
        results = route_scenario("피부 전후 비교", overrides={"brand_name": "Banillaco"})
    """
    router = ScenarioRouter()
    return router.route(user_input, overrides)
