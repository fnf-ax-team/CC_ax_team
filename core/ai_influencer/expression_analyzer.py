"""
VLM 표정 분석기

표정 레퍼런스 이미지에서 상세 표정 정보를 추출하여
프롬프트 스키마 형식으로 반환합니다.

기존 프리셋의 문제점:
- "한쪽 윙크" → 어느 눈? 얼마나 감았는지? 눈썹 위치?
- "살짝 벌림" → 입술 두께? 치아 보임? 혀 위치?

이 분석기는 세세한 근육 단위 표정을 분석합니다.
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict, field
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class ExpressionAnalysisResult:
    """표정 분석 결과 - 상세 버전"""

    # === 기본 분위기 ===
    mood_base: str  # cool, natural, dreamy, playful, cute, sensual
    mood_vibe: str  # 구체적 분위기 (예: "mysterious, laid-back")

    # === 눈 상세 (CRITICAL!) ===
    # 눈 형태
    eye_shape: str  # 큰 눈, 고양이 눈, 아몬드형, 둥근 눈
    eye_size: str  # 크게 뜬, 자연스러운, 살짝 감은, 반쯤 감은

    # 왼쪽 눈 상세
    left_eye_openness: (
        str  # 완전히 뜬(100%), 자연스럽게 뜬(80%), 살짝 감은(50%), 윙크(10%), 감은(0%)
    )
    left_eye_direction: str  # 정면, 왼쪽, 오른쪽, 위, 아래
    left_eyebrow_position: str  # 올라간, 자연스러운, 내려간, 찌푸린

    # 오른쪽 눈 상세
    right_eye_openness: (
        str  # 완전히 뜬(100%), 자연스럽게 뜬(80%), 살짝 감은(50%), 윙크(10%), 감은(0%)
    )
    right_eye_direction: str  # 정면, 왼쪽, 오른쪽, 위, 아래
    right_eyebrow_position: str  # 올라간, 자연스러운, 내려간, 찌푸린

    # 눈빛/감정
    eye_emotion: str  # 자신감, 도도함, 장난기, 순수함, 나른함, 강렬함

    # === 입 상세 (CRITICAL!) ===
    mouth_state: str  # closed, slightly_parted, open, smiling, pouting
    lip_shape: str  # 다문, 살짝 벌린(5mm), 벌린(1cm), 활짝 벌린
    teeth_visible: bool  # 치아 보이는지
    teeth_detail: str  # 윗니만, 아랫니만, 둘 다, 안 보임
    tongue_visible: bool  # 혀 보이는지
    lip_corner: str  # 올라간(미소), 자연스러운, 내려간(찡그림)
    lip_pout: str  # 없음, 살짝, 많이 (삐죽)

    # === 얼굴 방향/각도 ===
    face_angle: str  # 정면, 3/4 왼쪽, 3/4 오른쪽, 측면
    chin_position: str  # 들어올린, 자연스러운, 내린
    head_tilt: str  # 왼쪽으로 기울임, 오른쪽으로 기울임, 수직

    # === 추가 디테일 ===
    cheek_expression: str  # 볼 부풀림, 자연스러운, 움푹 들어감
    nose_scrunch: bool  # 코 찡그림 여부
    forehead_wrinkle: bool  # 이마 주름 여부

    # === 손 위치 (표정과 연관) ===
    hand_near_face: str  # 없음, 턱 받침, 뺨 터치, 입 가림, 브이

    # === 특이사항 ===
    special_features: List[str] = field(default_factory=list)  # 보조개, 점, 피어싱 등

    # 신뢰도
    confidence: float = 0.5
    raw_response: Dict[str, Any] = None

    def to_schema_format(self) -> Dict[str, Any]:
        """프롬프트 스키마 형식으로 변환"""
        return {
            "베이스": self.mood_base,
            "바이브": self.mood_vibe,
            # 눈 상세
            "눈_형태": self.eye_shape,
            "눈_크기": self.eye_size,
            "왼눈_열림": self.left_eye_openness,
            "왼눈_방향": self.left_eye_direction,
            "왼눈썹": self.left_eyebrow_position,
            "오른눈_열림": self.right_eye_openness,
            "오른눈_방향": self.right_eye_direction,
            "오른눈썹": self.right_eyebrow_position,
            "눈빛": self.eye_emotion,
            # 입 상세
            "입_상태": self.mouth_state,
            "입술_형태": self.lip_shape,
            "치아_보임": self.teeth_visible,
            "치아_상세": self.teeth_detail,
            "혀_보임": self.tongue_visible,
            "입꼬리": self.lip_corner,
            "입술_삐죽": self.lip_pout,
            # 얼굴 방향
            "얼굴_각도": self.face_angle,
            "턱_위치": self.chin_position,
            "고개_기울기": self.head_tilt,
            # 추가
            "손_위치": self.hand_near_face,
        }

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트로 변환 (한글 문장형)"""
        lines = []

        # 기본 분위기
        lines.append(f"[표정 무드]: {self.mood_base}, {self.mood_vibe}")

        # 눈 상세
        lines.append(f"[눈 형태]: {self.eye_shape}, {self.eye_size}")

        # 왼눈/오른눈 분리 (윙크 등 비대칭 표정 핵심!)
        if self.left_eye_openness != self.right_eye_openness:
            lines.append(
                f"[왼쪽 눈]: 열림 {self.left_eye_openness}, 방향 {self.left_eye_direction}, 눈썹 {self.left_eyebrow_position}"
            )
            lines.append(
                f"[오른쪽 눈]: 열림 {self.right_eye_openness}, 방향 {self.right_eye_direction}, 눈썹 {self.right_eyebrow_position}"
            )
        else:
            lines.append(
                f"[양쪽 눈]: 열림 {self.left_eye_openness}, 방향 {self.left_eye_direction}, 눈썹 {self.left_eyebrow_position}"
            )

        lines.append(f"[눈빛/감정]: {self.eye_emotion}")

        # 입 상세
        mouth_desc = f"{self.mouth_state}, {self.lip_shape}"
        if self.teeth_visible:
            mouth_desc += f", 치아 보임({self.teeth_detail})"
        if self.tongue_visible:
            mouth_desc += ", 혀 보임"
        mouth_desc += f", 입꼬리 {self.lip_corner}"
        if self.lip_pout != "없음":
            mouth_desc += f", 삐죽 {self.lip_pout}"
        lines.append(f"[입]: {mouth_desc}")

        # 얼굴 방향
        lines.append(
            f"[얼굴 각도]: {self.face_angle}, 턱 {self.chin_position}, 고개 {self.head_tilt}"
        )

        # 손 위치
        if self.hand_near_face != "없음":
            lines.append(f"[손 위치]: {self.hand_near_face}")

        # 특이사항
        if self.special_features:
            lines.append(f"[특이사항]: {', '.join(self.special_features)}")

        return "\n".join(lines)

    def get_wink_info(self) -> Optional[Dict[str, str]]:
        """윙크 정보 반환 (비대칭 눈 표정)"""
        left_pct = self._parse_openness(self.left_eye_openness)
        right_pct = self._parse_openness(self.right_eye_openness)

        if left_pct < 30 and right_pct >= 70:
            return {
                "wink_eye": "left",
                "open_eye": "right",
                "wink_level": self.left_eye_openness,
            }
        elif right_pct < 30 and left_pct >= 70:
            return {
                "wink_eye": "right",
                "open_eye": "left",
                "wink_level": self.right_eye_openness,
            }
        return None

    def _parse_openness(self, openness: str) -> int:
        """열림 정도를 퍼센트로 변환"""
        if "100" in openness or "완전히 뜬" in openness:
            return 100
        elif "80" in openness or "자연스럽게" in openness:
            return 80
        elif "50" in openness or "살짝 감은" in openness:
            return 50
        elif "10" in openness or "윙크" in openness:
            return 10
        elif "0" in openness or "감은" in openness:
            return 0
        return 80  # 기본값


# VLM 표정 분석 프롬프트
EXPRESSION_ANALYSIS_PROMPT = """당신은 패션 화보 표정 분석 전문가입니다.

## 작업
이미지에서 모델의 표정을 매우 상세하게 분석하여 아래 JSON 형식으로 출력하세요.

★★★ 중요: 왼쪽/오른쪽 눈을 반드시 분리 분석! ★★★
윙크, 반쯤 감은 눈 등 비대칭 표정을 정확히 캡처해야 합니다.

## 분석 항목

### 1. 기본 분위기
- mood_base: 다음 중 선택
  - "cool": 쿨하고 도도함
  - "natural": 자연스럽고 편안함
  - "dreamy": 몽환적, 나른함
  - "playful": 장난스럽고 발랄함
  - "cute": 귀엽고 사랑스러움
  - "sensual": 섹시하고 관능적

- mood_vibe: 구체적 분위기 키워드 (예: "mysterious, laid-back", "flirty, adorable")

### 2. 눈 상세 (★★★ 매우 중요! ★★★)

#### 눈 기본 형태
- eye_shape: "큰 눈", "고양이 눈", "아몬드형", "둥근 눈", "날카로운 눈"
- eye_size: "크게 뜬", "자연스러운", "살짝 감은", "반쯤 감은"

#### 왼쪽 눈 (이미지 기준 왼쪽 = 모델의 오른쪽 눈)
- left_eye_openness: 열림 정도
  - "완전히 뜬(100%)": 눈이 최대로 열림
  - "자연스럽게 뜬(80%)": 보통 열림
  - "살짝 감은(50%)": 반쯤 감은 느낌
  - "윙크(10%)": 거의 감음, 실눈
  - "감은(0%)": 완전히 감음

- left_eye_direction: 시선 방향
  - "정면", "왼쪽", "오른쪽", "위", "아래"

- left_eyebrow_position: 눈썹 위치
  - "올라간": 놀람/의문
  - "자연스러운": 평소
  - "내려간": 졸림/편안
  - "찌푸린": 화남/집중

#### 오른쪽 눈 (이미지 기준 오른쪽 = 모델의 왼쪽 눈)
- right_eye_openness: (위와 동일)
- right_eye_direction: (위와 동일)
- right_eyebrow_position: (위와 동일)

#### 눈빛/감정
- eye_emotion: "자신감", "도도함", "장난기", "순수함", "나른함", "강렬함", "몽환적", "호기심"

### 3. 입 상세 (★★★ 매우 중요! ★★★)

- mouth_state: 입 상태
  - "closed": 다문 상태
  - "slightly_parted": 살짝 벌림 (숨쉬는 정도)
  - "open": 벌림 (손가락 들어갈 정도)
  - "smiling": 미소
  - "pouting": 삐죽

- lip_shape: 입술 형태 설명
  - 예: "자연스럽게 다문", "살짝 벌린(5mm)", "O자로 벌린", "활짝 벌린(1cm 이상)"

- teeth_visible: 치아 보이는지 (true/false)
- teeth_detail: 치아 상세
  - "안 보임", "윗니만", "아랫니만", "윗니와 아랫니 둘 다"

- tongue_visible: 혀 보이는지 (true/false)

- lip_corner: 입꼬리
  - "올라간": 미소 느낌
  - "자연스러운": 평소
  - "내려간": 찡그림/삐침

- lip_pout: 삐죽 정도
  - "없음", "살짝", "많이"

### 4. 얼굴 방향/각도

- face_angle: 얼굴이 향하는 방향
  - "정면", "3/4 왼쪽", "3/4 오른쪽", "측면 왼쪽", "측면 오른쪽"

- chin_position: 턱 위치
  - "들어올린": 턱을 올림 (자신감/도도)
  - "자연스러운": 평소
  - "내린": 턱을 당김 (귀여움/수줍음)

- head_tilt: 고개 기울기
  - "왼쪽으로 기울임", "오른쪽으로 기울임", "수직"

### 5. 추가 디테일

- cheek_expression: 볼 상태
  - "볼 부풀림", "자연스러운", "움푹 들어감"

- nose_scrunch: 코 찡그림 (true/false)
- forehead_wrinkle: 이마 주름 (true/false)

- hand_near_face: 손 위치
  - "없음", "턱 받침", "뺨 터치", "입 가림", "브이", "볼 꼬집기", "머리카락 넘기기"

- special_features: 특이사항 배열
  - 예: ["보조개 있음", "점 있음", "귀걸이"]

### 6. confidence
분석 신뢰도 (0-1)

## 출력 형식 (JSON)
```json
{
    "mood_base": "playful",
    "mood_vibe": "flirty, adorable",

    "eye_shape": "큰 눈",
    "eye_size": "자연스럽게 뜬",

    "left_eye_openness": "자연스럽게 뜬(80%)",
    "left_eye_direction": "정면",
    "left_eyebrow_position": "살짝 올라간",

    "right_eye_openness": "윙크(10%)",
    "right_eye_direction": "정면",
    "right_eyebrow_position": "자연스러운",

    "eye_emotion": "장난기",

    "mouth_state": "slightly_parted",
    "lip_shape": "살짝 벌린(5mm), 아랫입술이 살짝 두꺼움",
    "teeth_visible": false,
    "teeth_detail": "안 보임",
    "tongue_visible": false,
    "lip_corner": "올라간",
    "lip_pout": "살짝",

    "face_angle": "정면",
    "chin_position": "살짝 내린",
    "head_tilt": "오른쪽으로 기울임",

    "cheek_expression": "자연스러운",
    "nose_scrunch": false,
    "forehead_wrinkle": false,

    "hand_near_face": "브이",

    "special_features": ["보조개 있음"],

    "confidence": 0.9
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class ExpressionAnalyzer:
    """VLM 표정 분석기"""

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
        expression_image: Union[str, Path, Image.Image],
    ) -> ExpressionAnalysisResult:
        """
        표정 이미지 분석

        Args:
            expression_image: 표정 레퍼런스 이미지

        Returns:
            ExpressionAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(expression_image, (str, Path)):
            img = Image.open(expression_image).convert("RGB")
        else:
            img = expression_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=EXPRESSION_ANALYSIS_PROMPT),
            types.Part(text="[EXPRESSION IMAGE]:"),
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
            print(f"[ExpressionAnalyzer] API 호출 실패: {e}")
            # 기본 결과 반환
            return ExpressionAnalysisResult(
                mood_base="natural",
                mood_vibe="분석 실패",
                eye_shape="자연스러운",
                eye_size="자연스럽게 뜬",
                left_eye_openness="자연스럽게 뜬(80%)",
                left_eye_direction="정면",
                left_eyebrow_position="자연스러운",
                right_eye_openness="자연스럽게 뜬(80%)",
                right_eye_direction="정면",
                right_eyebrow_position="자연스러운",
                eye_emotion="자연스러운",
                mouth_state="closed",
                lip_shape="자연스럽게 다문",
                teeth_visible=False,
                teeth_detail="안 보임",
                tongue_visible=False,
                lip_corner="자연스러운",
                lip_pout="없음",
                face_angle="정면",
                chin_position="자연스러운",
                head_tilt="수직",
                cheek_expression="자연스러운",
                nose_scrunch=False,
                forehead_wrinkle=False,
                hand_near_face="없음",
                confidence=0.0,
                raw_response={"error": str(e)},
            )

        # 결과 변환
        return ExpressionAnalysisResult(
            mood_base=result_json.get("mood_base", "natural"),
            mood_vibe=result_json.get("mood_vibe", ""),
            eye_shape=result_json.get("eye_shape", ""),
            eye_size=result_json.get("eye_size", ""),
            left_eye_openness=result_json.get(
                "left_eye_openness", "자연스럽게 뜬(80%)"
            ),
            left_eye_direction=result_json.get("left_eye_direction", "정면"),
            left_eyebrow_position=result_json.get(
                "left_eyebrow_position", "자연스러운"
            ),
            right_eye_openness=result_json.get(
                "right_eye_openness", "자연스럽게 뜬(80%)"
            ),
            right_eye_direction=result_json.get("right_eye_direction", "정면"),
            right_eyebrow_position=result_json.get(
                "right_eyebrow_position", "자연스러운"
            ),
            eye_emotion=result_json.get("eye_emotion", ""),
            mouth_state=result_json.get("mouth_state", "closed"),
            lip_shape=result_json.get("lip_shape", ""),
            teeth_visible=result_json.get("teeth_visible", False),
            teeth_detail=result_json.get("teeth_detail", "안 보임"),
            tongue_visible=result_json.get("tongue_visible", False),
            lip_corner=result_json.get("lip_corner", "자연스러운"),
            lip_pout=result_json.get("lip_pout", "없음"),
            face_angle=result_json.get("face_angle", "정면"),
            chin_position=result_json.get("chin_position", "자연스러운"),
            head_tilt=result_json.get("head_tilt", "수직"),
            cheek_expression=result_json.get("cheek_expression", "자연스러운"),
            nose_scrunch=result_json.get("nose_scrunch", False),
            forehead_wrinkle=result_json.get("forehead_wrinkle", False),
            hand_near_face=result_json.get("hand_near_face", "없음"),
            special_features=result_json.get("special_features", []),
            confidence=result_json.get("confidence", 0.5),
            raw_response=result_json,
        )

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


def analyze_expression(
    expression_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> ExpressionAnalysisResult:
    """
    표정 분석 (편의 함수)

    Args:
        expression_image: 표정 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        ExpressionAnalysisResult: 분석 결과
    """
    analyzer = ExpressionAnalyzer(api_key=api_key)
    return analyzer.analyze(expression_image)
