"""
VLM 배경 분석기

배경 레퍼런스 이미지에서 환경 정보를 추출하여
포즈 호환성 검증에 필요한 정보를 반환합니다.

핵심 분석 항목:
- provides: 배경이 제공하는 요소 (wall, seating, surface, mirror, rail, walkway)
- supported_stances: 해당 배경에서 가능한 포즈 (stand, sit, walk, lean_wall 등)
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class BackgroundAnalysisResult:
    """배경 분석 결과"""

    # 기본 정보
    scene_type: str  # 배경 유형 (cafe, street, graffiti, crosswalk, elevator 등)
    region: str  # 지역 (한국/성수, 미국/뉴욕 등)
    time_of_day: str  # 시간대 (주간, 야간, 실내 등)
    color_tone: str  # 색감

    # 핵심: 배경이 제공하는 요소
    provides: List[
        str
    ]  # wall, seating, surface, mirror, rail, walkway, door, potential_seating

    # 핵심: 해당 배경에서 가능한 포즈
    supported_stances: List[str]  # stand, sit, walk, lean_wall, lean, kneel

    # 상세 설명
    description: str  # 장소 상세 설명
    mood: str  # 분위기

    # 잠재적 좌석 위치 (연석, 계단, 낮은 벽 등)
    potential_seating_locations: List[str] = field(default_factory=list)

    # 앉기 추천 위치 (sit 포즈 시 여기에 앉으라고 명시)
    sit_on: str = ""  # 예: "골목 바닥", "연석", "계단"

    # 특이사항 (좌석 없음, 벽 없음 등)
    notes: List[str] = field(default_factory=list)

    # 신뢰도
    confidence: float = 0.5
    raw_response: Dict[str, Any] = None

    def to_schema_format(self) -> Dict[str, Any]:
        """프롬프트 스키마 형식으로 변환"""
        return {
            "지역": self.region,
            "시간대": self.time_of_day,
            "색감": self.color_tone,
            "장소": self.description,
            "분위기": self.mood,
        }

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트로 변환"""
        lines = []
        lines.append(f"[배경 유형]: {self.scene_type}")
        lines.append(f"[지역]: {self.region}")
        lines.append(f"[시간대]: {self.time_of_day}")
        lines.append(f"[색감]: {self.color_tone}")
        lines.append(f"[장소 설명]: {self.description}")
        lines.append(f"[분위기]: {self.mood}")
        lines.append(f"[제공 요소]: {', '.join(self.provides)}")
        lines.append(f"[가능한 포즈]: {', '.join(self.supported_stances)}")
        if self.potential_seating_locations:
            lines.append(
                f"[잠재적 좌석 위치]: {', '.join(self.potential_seating_locations)}"
            )
        if self.notes:
            lines.append(f"[특이사항]: {'; '.join(self.notes)}")
        return "\n".join(lines)

    def can_support_stance(self, stance: str) -> bool:
        """특정 stance가 가능한지 확인"""
        return stance in self.supported_stances

    def has_element(self, element: str) -> bool:
        """특정 요소가 있는지 확인"""
        return element in self.provides


# VLM 배경 분석 프롬프트
BACKGROUND_ANALYSIS_PROMPT = """당신은 패션 화보 촬영 배경 분석 전문가입니다.

## 작업
이미지에서 배경 환경을 분석하여 아래 JSON 형식으로 출력하세요.

## 핵심 분석 항목

### 1. scene_type (배경 유형)
다음 중 하나를 선택:
- "cafe": 카페/브런치
- "street": 거리/골목
- "graffiti": 그래피티/벽화
- "crosswalk": 횡단보도/교차로
- "subway": 지하철 역사/차량 내부
- "elevator": 엘리베이터 (거울 있음)
- "door": 건물 출입문
- "park": 공원/정원
- "indoor": 실내 공간
- "rooftop": 루프탑/테라스
- "other": 기타

### 2. provides (배경이 제공하는 요소) - 매우 중요!
이미지에서 실제로 보이는 요소를 선택:
- "wall": 기댈 수 있는 벽/구조물
- "seating": 앉을 수 있는 곳 (의자, 벤치, 계단)
- "potential_seating": 앉을 수 있는 잠재적 장소 (연석, 턱, 낮은 벽, 화분대 가장자리, 볼라드)
- "surface": 물건을 올릴 수 있는 표면 (테이블, 난간 상단)
- "mirror": 거울 (셀카 가능)
- "rail": 기댈 수 있는 난간
- "walkway": 걸을 수 있는 통로
- "door": 문

★★★ 잠재적 좌석 적극 탐색! ★★★
패션 화보에서 모델이 앉을 수 있는 곳을 찾으세요:
- 연석(curb): 도로와 인도 경계의 높은 턱
- 계단(steps): 건물 입구, 지하철 출입구 등
- 낮은 벽(ledge): 화단 벽, 건물 기단부
- 화분대 가장자리: 대형 화분의 테두리
- 볼라드(bollard): 차량 진입 방지용 기둥 (앉을 수 있는 평평한 상단)

### 3. potential_seating_locations (잠재적 좌석 위치) - 중요!
이미지에서 모델이 앉을 수 있는 구체적 위치를 설명하세요.
예시:
- "이미지 왼쪽 연석 (curb)"
- "건물 입구 계단 (3개 단)"
- "오른쪽 화단 낮은 벽"
- "배경 중앙 볼라드"

### 3-1. sit_on (앉기 추천 위치) - 매우 중요!
만약 모델이 앉는다면, 이 배경에서 가장 자연스러운 앉을 위치를 하나 지정하세요.
★★★ 배경에 이미 존재하는 요소만 사용! 새로운 물체 만들기 금지! ★★★
예시:
- "바닥" (길바닥, 골목 바닥)
- "연석" (도로 경계)
- "계단" (건물 입구)
- "벤치" (있으면)
- "낮은 벽" (화단 벽 등)
- "의자" (카페 등)

없으면 빈 문자열 ""

### 4. supported_stances (가능한 포즈) - 매우 중요!
provides를 기반으로 물리적으로 가능한 포즈만 선택:
- "stand": 서있기 (항상 가능)
- "sit": 앉기 (seating 또는 potential_seating 있으면 가능!)
- "walk": 걷기 (walkway 또는 넓은 공간 필요)
- "lean_wall": 벽에 기대기 (wall 필요!)
- "lean": 난간/표면에 기대기 (rail 또는 surface 필요)
- "kneel": 무릎 꿇기 (바닥/낮은 공간 필요)

★★★ sit 판단 기준 ★★★
- seating 있으면 → sit 가능
- potential_seating 있으면 → sit 가능 (연석, 계단, 낮은 벽 등)
- 둘 다 없으면 → sit 불가능

### 5. 불가능한 stance 설명
만약 일반적인 stance가 불가능하다면 notes에 이유를 적으세요.

## 출력 형식 (JSON)
```json
{
    "scene_type": "street",
    "region": "중국/상하이",
    "time_of_day": "주간",
    "color_tone": "그레이, 베이지",
    "provides": ["walkway", "potential_seating", "wall"],
    "potential_seating_locations": ["왼쪽 연석 (curb)", "건물 입구 계단"],
    "sit_on": "연석",
    "supported_stances": ["stand", "walk", "sit", "lean_wall"],
    "description": "상하이 거리. 횡단보도 근처, 건물과 연석 있음.",
    "mood": "도시적, 모던",
    "notes": [],
    "confidence": 0.9
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class BackgroundAnalyzer:
    """VLM 배경 분석기"""

    # provides 요소별로 필요한 stance
    # OR 조건: 리스트 내 요소 중 하나라도 있으면 가능
    STANCE_REQUIREMENTS = {
        "sit": [
            "seating",
            "potential_seating",
        ],  # 앉기: seating 또는 potential_seating (OR)
        "lean_wall": ["wall"],  # 벽에 기대기: wall 필수
        "lean": ["rail", "surface"],  # 기대기: rail 또는 surface 필요 (OR)
        "kneel": [],  # 무릎 꿇기: 특별한 요소 불필요
        "stand": [],  # 서기: 항상 가능
        "walk": ["walkway"],  # 걷기: walkway 또는 넓은 공간
    }

    # OR 조건으로 처리해야 하는 stance 목록
    OR_CONDITION_STANCES = ["sit", "lean"]

    def __init__(self, api_key: Optional[str] = None):
        """
        분석기 초기화

        Args:
            api_key: Gemini API 키 (None이면 자동 로드)
        """
        if api_key is None:
            from core.api import _get_next_api_key

            api_key = _get_next_api_key()

        self.client = genai.Client(api_key=api_key)

    def analyze(
        self,
        background_image: Union[str, Path, Image.Image],
    ) -> BackgroundAnalysisResult:
        """
        배경 이미지 분석

        Args:
            background_image: 배경 레퍼런스 이미지

        Returns:
            BackgroundAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(background_image, (str, Path)):
            img = Image.open(background_image).convert("RGB")
        else:
            img = background_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=BACKGROUND_ANALYSIS_PROMPT),
            types.Part(text="[BACKGROUND IMAGE]:"),
            self._pil_to_part(img),
        ]

        # API 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            # JSON 파싱
            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_json = json.loads(result_text)

        except Exception as e:
            print(f"[BackgroundAnalyzer] API 호출 실패: {e}")
            # 기본 결과 반환
            return BackgroundAnalysisResult(
                scene_type="unknown",
                region="알 수 없음",
                time_of_day="주간",
                color_tone="",
                provides=["walkway"],  # 최소한 걸을 수 있다고 가정
                supported_stances=["stand", "walk"],
                description="분석 실패",
                mood="",
                notes=[f"API 오류: {e}"],
                confidence=0.0,
                raw_response={"error": str(e)},
            )

        # 결과 변환
        provides = result_json.get("provides", [])
        supported_stances = result_json.get("supported_stances", [])
        potential_seating_locations = result_json.get("potential_seating_locations", [])
        sit_on = result_json.get("sit_on", "")

        # VLM 결과 검증 및 보정
        validated_stances = self._validate_stances(provides, supported_stances)

        return BackgroundAnalysisResult(
            scene_type=result_json.get("scene_type", "unknown"),
            region=result_json.get("region", ""),
            time_of_day=result_json.get("time_of_day", "주간"),
            color_tone=result_json.get("color_tone", ""),
            provides=provides,
            supported_stances=validated_stances,
            description=result_json.get("description", ""),
            mood=result_json.get("mood", ""),
            potential_seating_locations=potential_seating_locations,
            sit_on=sit_on,
            notes=result_json.get("notes", []),
            confidence=result_json.get("confidence", 0.5),
            raw_response=result_json,
        )

    def _validate_stances(
        self,
        provides: List[str],
        vlm_stances: List[str],
    ) -> List[str]:
        """
        VLM이 반환한 stance를 provides 기반으로 검증

        Args:
            provides: 배경이 제공하는 요소
            vlm_stances: VLM이 반환한 stance 목록

        Returns:
            검증된 stance 목록
        """
        validated = []

        for stance in vlm_stances:
            required = self.STANCE_REQUIREMENTS.get(stance, [])

            # 필수 요소가 없으면 통과
            if not required:
                # 필수 요소 없음 (stand, kneel 등)
                validated.append(stance)
            elif stance in self.OR_CONDITION_STANCES:
                # OR 조건: sit, lean은 요소 중 하나라도 있으면 가능
                if any(r in provides for r in required):
                    validated.append(stance)
            else:
                # AND 조건: 모든 요소 필요
                if all(r in provides for r in required):
                    validated.append(stance)

        # stand는 항상 가능
        if "stand" not in validated:
            validated.append("stand")

        return validated

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )


def analyze_background(
    background_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> BackgroundAnalysisResult:
    """
    배경 분석 (편의 함수)

    Args:
        background_image: 배경 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        BackgroundAnalysisResult: 분석 결과
    """
    analyzer = BackgroundAnalyzer(api_key=api_key)
    return analyzer.analyze(background_image)
