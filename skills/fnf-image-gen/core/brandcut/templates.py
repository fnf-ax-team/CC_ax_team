"""
브랜드컷 VLM 프롬프트 템플릿 모듈

착장/포즈/무드 분석 및 API 전송용 지시문 템플릿 제공
"""

# 착장 분석용 프롬프트 (모든 착장 이미지 대상)
OUTFIT_ANALYSIS_PROMPT = """
착장 이미지를 분석하여 AI가 놓치기 쉬운 디테일을 추출하세요.

반드시 포함:
1. 변형된 실루엣: 벌룬핏, 비대칭 커팅, 익스트림 크롭
2. 미세 부자재: 배색 스티치, 빈티지 워싱, 로고 각인 단추
3. 로고/그래픽 위치: 정확한 상대적 좌표 (예: "왼쪽 가슴 위, 어깨에서 10cm 아래")
4. 소재 질감: 시어, 슬러브, 헤어리, 코팅 가공

JSON 형식으로 출력:
{
  "outer": {"item": "", "color": "", "details": [], "logo_position": ""},
  "top": {"item": "", "color": "", "details": [], "logo_position": ""},
  "bottom": {"item": "", "color": "", "details": []},
  "shoes": {"item": "", "color": ""},
  "headwear": {"item": "", "color": "", "logo_position": ""},
  "accessories": []
}
"""


# 포즈/표정 레퍼런스 분석용 (상세 추출)
POSE_EXPRESSION_ANALYSIS_PROMPT = """
이 이미지에서 포즈와 표정을 **아주 상세하게** 분석하세요.
생성 AI가 **똑같이 따라할 수 있도록** 왼쪽/오른쪽을 구분하여 구체적으로 설명해야 합니다.

## 추출할 정보

### [전체 자세]
- 기본 자세: standing / sitting / leaning / walking / crouching / lying
- 체중 분배: 왼발 / 오른발 / 양발 균등
- 몸 방향: 카메라 정면 / 45도 왼쪽 / 45도 오른쪽 / 옆면

### [다리 - 왼쪽/오른쪽 구분 필수]
- 왼쪽 다리: 위치(땅에/들림/접힘), 무릎 방향, 발 위치
- 오른쪽 다리: 위치(땅에/들림/접힘), 무릎 방향, 발 위치
- 다리 간격: 붙어있음 / 어깨너비 / 넓게 벌림

### [팔/손 - 왼쪽/오른쪽 구분 필수]
- 왼쪽 팔: 위치(몸옆/허리/주머니/머리/기대기), 굽힘 정도
- 왼쪽 손: 손 모양, 손가락 위치
- 오른쪽 팔: 위치(몸옆/허리/주머니/머리/기대기), 굽힘 정도
- 오른쪽 손: 손 모양, 손가락 위치

### [상체/머리]
- 어깨: 수평 / 왼쪽 높음 / 오른쪽 높음
- 상체 기울기: 똑바로 / 왼쪽 기울임 / 오른쪽 기울임 / 뒤로 기댐
- 고개: 정면 / 왼쪽 돌림 / 오른쪽 돌림 / 위로 / 아래로 / 기울임

### [표정]
- 눈: 크게 뜸 / 자연스럽게 / 살짝 감음 / 찡그림
- 눈썹: 자연 / 올림 / 찌푸림
- 입: 다문 / 살짝 벌림 / 파우팅
- 전체 무드: cool / dreamy / natural / serious / playful / confident

### [카메라/구도]
- 시선: 카메라 직시 / 허공 / 왼쪽 / 오른쪽 / 아래
- 카메라 높이: 로우앵글(아래에서) / 아이레벨 / 하이앵글(위에서)
- 프레이밍: 전신(FS) / 무릎위(MFS) / 허리위(MS) / 가슴위(MCU) / 클로즈업(CU)
- 카메라 거리: 멀리 / 중간 / 가까이

## JSON 출력 (반드시 이 형식으로):
{
  "pose": {
    "stance": "leaning against car wheel",
    "weight": "on left leg",
    "body_direction": "facing camera at 30 degrees right",
    "left_leg": "bent, knee pointing outward, foot resting on car wheel",
    "right_leg": "straight, extended forward, foot flat on ground",
    "leg_spacing": "wide apart",
    "left_arm": "bent at elbow, hand resting on left thigh",
    "left_hand": "relaxed, fingers slightly curved",
    "right_arm": "relaxed, hanging by side",
    "right_hand": "relaxed",
    "shoulders": "left shoulder slightly higher, relaxed",
    "torso": "leaning back slightly against car",
    "head": "tilted slightly left, facing camera"
  },
  "expression": {
    "eyes": "large, wide open, confident gaze",
    "eyebrows": "natural, slightly raised",
    "mouth": "closed, neutral, slight pout",
    "mood": "cool, confident, chic"
  },
  "camera": {
    "gaze_direction": "directly at camera",
    "camera_height": "low angle (shooting from below)",
    "framing": "FS (full shot, head to toe)",
    "camera_distance": "medium"
  },
  "prompt_text": "Full body shot from low angle. Model leaning against black SUV wheel, left leg bent with foot on wheel, right leg extended straight on ground. Left arm on thigh, right arm relaxed. Head tilted left, confident gaze at camera. Cool, chic expression with large eyes and neutral mouth."
}
"""


# 무드/분위기 레퍼런스 분석용
MOOD_ANALYSIS_PROMPT = """
이 이미지의 무드와 분위기를 **아주 상세하게** 분석하세요.
생성 AI가 **똑같은 분위기를 재현**할 수 있도록 구체적으로 설명해야 합니다.

## 추출할 정보

### [조명 상세]
- 조명 타입: 자연광 / 스튜디오 / 혼합
- 조명 방향: 정면 / 왼쪽 45도 / 오른쪽 45도 / 역광 / 탑라이트 / 언더라이트
- 조명 품질: 소프트(부드러운 그림자) / 하드(날카로운 그림자)
- 색온도: 쿨(청색 5600K+) / 뉴트럴(5000-5600K) / 웜(따뜻한 4000K 이하)
- 그림자 강도: 없음 / 약함 / 중간 / 강함

### [색감/톤]
- 전체 색감: 쿨톤 / 뉴트럴 / 웜톤
- 채도: 높음 / 중간 / 낮음 / 무채색
- 콘트라스트: 높음 / 중간 / 낮음
- 하이라이트: 밝음 / 중간 / 어두움
- 색상 캐스트: 없음 / 블루 / 청록 / 핑크 / 옐로우 (절대 없어야 하면 명시)

### [배경/환경]
- 배경 타입: 실내 / 실외 / 스튜디오
- 배경 스타일: 미니멀 / 산업적 / 럭셔리 / 도시 / 자연
- 배경 요소: 있는 것들 나열 (차량, 건물, 콘크리트 등)
- 배경 선명도: 선명 / 약간 흐림 / 많이 흐림(보케)

### [전체 무드]
- 분위기: cool / warm / dreamy / natural / edgy / elegant / playful / serious
- 브랜드 느낌: high-end / casual / street / sporty / luxurious
- 시간대 느낌: 새벽 / 아침 / 낮 / 저녁 / 밤

## JSON 출력 (반드시 이 형식으로):
{
  "lighting": {
    "type": "natural daylight, overcast sky",
    "direction": "soft front-left 45 degrees",
    "quality": "soft, diffused",
    "color_temperature": "neutral to cool (5600K-6000K)",
    "shadow_intensity": "soft, subtle shadows"
  },
  "color_grade": {
    "overall_tone": "cool neutral",
    "saturation": "medium-low, desaturated",
    "contrast": "medium",
    "highlights": "clean, bright",
    "color_cast": "none, absolutely no warm/yellow cast"
  },
  "background": {
    "type": "outdoor urban",
    "style": "industrial minimal, brutalist",
    "elements": "black SUV, concrete pavement, modern architecture",
    "blur": "sharp foreground, slightly blurred background"
  },
  "mood": {
    "atmosphere": "cool, confident, urban chic",
    "brand_feel": "high-end streetwear, young & rich",
    "time_feel": "daytime, neutral lighting"
  },
  "keywords": ["editorial", "high-end", "confident", "urban", "cool", "clean"],
  "prompt_text": "Urban outdoor setting with black SUV. Neutral-cool daylight, soft diffused lighting from front-left. Clean cool tones, no warm color cast. Industrial minimal background with modern architecture. High-end streetwear editorial mood."
}
"""


# 포즈 레퍼런스 API 전송 시 사용하는 지시문 태그
POSE_REFERENCE_TAG = """
[POSE REFERENCE] - POSE, CAMERA ANGLE, AND FRAMING:

COPY FROM THIS IMAGE:
- Body position, gesture, stance (자세, 제스처)
- Camera angle and perspective (카메라 앵글/구도 - 하이앵글/로우앵글/눈높이)
- Model's face direction relative to camera (얼굴이 카메라를 향하는 각도)
- FRAMING TIGHTNESS: How much the model fills the frame (모델이 프레임을 채우는 비율)
- Subject size relative to frame (프레임 대비 피사체 크기)

IGNORE FROM THIS IMAGE (절대 복사 금지):
- Face features (얼굴) → use FACE REFERENCE instead
- Clothing/outfit (착장) → use OUTFIT REFERENCE instead
- Hair style (헤어스타일)
- Background scene (배경 장면)

CRITICAL:
- Match the CAMERA ANGLE exactly
- Match the FRAMING TIGHTNESS - model should fill the frame similarly
- If model fills 80% of reference frame, model should fill 80% of generated frame
"""


__all__ = [
    "OUTFIT_ANALYSIS_PROMPT",
    "POSE_EXPRESSION_ANALYSIS_PROMPT",
    "MOOD_ANALYSIS_PROMPT",
    "POSE_REFERENCE_TAG",
]
