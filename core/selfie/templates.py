"""
셀피/인플루언서 VLM 프롬프트 템플릿 모듈

얼굴 분석 및 착장 분석용 지시문 템플릿 제공
"""

# 얼굴 분석용 프롬프트 (성별, 특징 감지)
FACE_ANALYSIS_PROMPT = """
이 얼굴 이미지를 분석하세요.

추출할 정보:
1. 성별: male 또는 female
2. 추정 나이대: teens, early_20s, mid_20s, late_20s, early_30s
3. 얼굴형: oval, round, square, heart, long
4. 피부톤: fair, light, medium, tan, dark
5. 주요 특징: (예: 큰 눈, 오뚝한 코, 날카로운 턱선 등)

JSON 출력:
{
  "gender": "female",
  "age_range": "mid_20s",
  "face_shape": "oval",
  "skin_tone": "light",
  "features": ["큰 눈", "작은 입", "뚜렷한 이목구비"],
  "description": "20대 중반 여성, 타원형 얼굴에 밝은 피부톤, 뚜렷한 이목구비"
}
"""


# 착장 분석용 프롬프트 (셀피용 - 간소화)
OUTFIT_ANALYSIS_PROMPT = """
착장 이미지를 분석하세요.

추출할 정보:
1. 카테고리: pajama, hoodie, sweatshirt, dress, jeans_tee, knit, gym_wear, tracksuit, lingerie, swimsuit
2. 상의 설명: 색상, 핏, 디테일
3. 하의 설명: (있는 경우)
4. 전체 스타일 분위기

JSON 출력:
{
  "category": "hoodie",
  "top": {
    "item": "oversized hoodie",
    "color": "cream",
    "fit": "oversized",
    "details": ["drawstring hood", "kangaroo pocket"]
  },
  "bottom": {
    "item": "",
    "color": "",
    "details": []
  },
  "style": "cozy casual loungewear",
  "prompt_text": "cream oversized hoodie with kangaroo pocket, cozy casual loungewear"
}
"""


# 셀피 스타일 분석 프롬프트 (참조 이미지 분석용)
SELFIE_STYLE_ANALYSIS_PROMPT = """
이 셀피/인플루언서 스타일 이미지를 분석하세요.

추출할 정보:
1. 촬영 스타일: selfie (셀카), mirror (거울샷), candid (자연스러운)
2. 거리/구도: close_up (얼빡), upper_body (상체), full_body (전신)
3. 표정: flirty (끼부리는), natural (자연스러운), innocent (청순한), chic (도도한), smiling (웃는)
4. 장소: bedroom (침대/방), cafe (카페), car (차 안), outdoor (야외), gym (헬스장)
5. 조명/분위기: 자연광, 실내조명, 따뜻한, 시원한

JSON 출력:
{
  "shooting_style": "selfie",
  "framing": "close_up",
  "expression": "flirty",
  "location": "bedroom",
  "lighting": "soft indoor lighting",
  "mood": "cozy, intimate",
  "prompt_text": "selfie style, close-up framing, flirty expression, cozy bedroom with soft lighting"
}
"""


__all__ = [
    "FACE_ANALYSIS_PROMPT",
    "OUTFIT_ANALYSIS_PROMPT",
    "SELFIE_STYLE_ANALYSIS_PROMPT",
]
