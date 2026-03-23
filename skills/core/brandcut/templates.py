"""
브랜드컷 VLM 프롬프트 템플릿 모듈

착장/포즈 분석 및 API 전송용 지시문 템플릿 제공
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


# [DEPRECATED] 포즈/표정 레퍼런스 분석용 (상세 추출)
# → PoseAnalyzer + ExpressionAnalyzer (core.ai_influencer) 로 대체됨
# → 삭제하지 않음 (하위 호환)
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

### [표정 - ★★★ K-뷰티 세분화 필수! ★★★]

#### 눈 (Eyes) - 5가지 요소
1. 눈 크기 (openness):
   - wide_open: 크게 뜬 눈 (놀람, 순수)
   - natural: 자연스러운 눈 크기
   - half_lidded: 반쯤 감은 눈 (나른함, 섹시)
   - slightly_closed: 살짝 감은 눈 (몽환)
   - squinting: 찡그린 눈 (강렬함)

2. 눈꼬리 방향 (eye_corner):
   - upturned: 눈꼬리 올라감 (시크, 날카로움)
   - neutral: 중립
   - downturned: 눈꼬리 내려감 (부드러움, 청순)

3. 눈빛 강도 (gaze_intensity):
   - intense_piercing: 강렬하게 꿰뚫는 시선 (시크)
   - smoldering: 뜨겁고 나른한 시선 (섹시)
   - soft_gentle: 부드럽고 따뜻한 시선 (러블리)
   - dreamy_unfocused: 몽환적이고 흐릿한 시선
   - innocent_clear: 맑고 순수한 시선 (청순)
   - cool_detached: 쿨하고 무관심한 시선 (도도)

4. 눈웃음 (eye_smile):
   - none: 눈웃음 없음 (시크, 도도)
   - slight: 살짝 눈웃음 (자연스러움)
   - full: 눈웃음 가득 (러블리, 밝음)

5. 눈썹 (eyebrows):
   - natural_relaxed: 자연스럽게 이완
   - slightly_raised: 살짝 올림 (관심, 놀람)
   - one_raised: 한쪽만 올림 (도발, 의문)
   - furrowed: 찌푸림 (집중, 강렬)
   - arched: 아치형으로 정돈 (세련됨)

#### 입 (Mouth) - 4가지 요소
1. 입 상태 (lip_state):
   - closed_neutral: 자연스럽게 다문 입
   - closed_tense: 긴장하며 다문 입
   - slightly_parted: 살짝 벌린 입 (섹시, 나른)
   - parted_relaxed: 편안하게 벌린 입
   - pouting: 뾰루퉁/파우팅
   - smiling_closed: 입 다문 미소
   - smiling_teeth: 이 보이는 미소

2. 입꼬리 각도 (mouth_corner):
   - upturned: 입꼬리 올라감 (미소, 밝음)
   - neutral: 중립
   - downturned: 입꼬리 내려감 (도도, 시크)
   - asymmetric_smirk: 비대칭 비웃음 (시크, 도발)

3. 입술 강조 (lip_emphasis):
   - natural: 자연스러운 입술
   - glossy_plump: 도톰하고 글로시한 입술
   - matte_defined: 매트하고 또렷한 입술
   - bitten_look: 깨문 듯한 입술

4. 입 긴장도 (lip_tension):
   - relaxed: 이완 (자연, 편안)
   - slightly_tense: 약간 긴장 (집중)
   - tense: 긴장 (강렬함)

#### 턱/얼굴 각도 (Chin/Face Angle)
1. 턱 위치 (chin_position):
   - raised: 턱 들어올림 (자신감, 도도)
   - neutral: 중립
   - lowered: 턱 숙임 (수줍음, 귀여움)
   - tilted_left: 왼쪽으로 기울임
   - tilted_right: 오른쪽으로 기울임

2. 턱 긴장도 (jaw_tension):
   - relaxed: 이완 (자연스러움)
   - defined: 또렷하게 긴장 (강렬함)
   - soft: 부드럽게 (여성스러움)

#### 전체 표정 카테고리 (K-Beauty Preset)
- chic_confident: 시크 + 자신감 (눈꼬리↑, 강렬한 시선, 입꼬리 중립~살짝↓, 턱↑)
- chic_mysterious: 시크 + 신비 (반쯤 감은 눈, 나른한 시선, 입 살짝 벌림)
- lovely_warm: 러블리 + 따뜻함 (눈웃음, 부드러운 시선, 자연스러운 미소)
- lovely_dreamy: 러블리 + 몽환 (살짝 감은 눈, 흐릿한 시선, 입 살짝 벌림)
- innocent_pure: 청순 (크게 뜬 눈, 맑은 시선, 자연스러운 입)
- haughty_cool: 도도 (쿨한 시선, 무표정, 턱↑)
- natural_effortless: 내추럴 (모든 요소 자연스럽게)
- fierce_intense: 강렬함 (찡그린 눈, 꿰뚫는 시선, 긴장된 입)

#### 표정 강도 (Expression Intensity) - 0~100
- 0-30: subtle (미묘함) - 거의 무표정에 가까움
- 31-60: moderate (보통) - 자연스러운 정도
- 61-80: noticeable (뚜렷함) - 명확하게 보임
- 81-100: intense (강렬함) - 매우 강하게 표현

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
    "preset": "chic_confident",
    "intensity": 75,
    "eyes": {
      "openness": "half_lidded",
      "eye_corner": "upturned",
      "gaze_intensity": "intense_piercing",
      "eye_smile": "none",
      "eyebrows": "natural_relaxed"
    },
    "mouth": {
      "lip_state": "slightly_parted",
      "mouth_corner": "neutral",
      "lip_emphasis": "glossy_plump",
      "lip_tension": "relaxed"
    },
    "chin": {
      "chin_position": "raised",
      "jaw_tension": "relaxed"
    },
    "mood_keywords": ["chic", "confident", "cool", "slightly seductive"]
  },
  "camera": {
    "gaze_direction": "directly at camera",
    "camera_height": "low angle (shooting from below)",
    "framing": "FS (full shot, head to toe)",
    "camera_distance": "medium"
  },
  "expression_prompt": "Chic confident expression with half-lidded eyes, upturned eye corners, intense piercing gaze directly at camera. No eye smile. Lips slightly parted, neutral mouth corners, glossy plump lips, relaxed tension. Chin slightly raised with relaxed jaw. Cool, confident, slightly seductive mood."
}
"""


# 표정 레퍼런스 API 전송 시 사용하는 지시문 태그
# 얼굴 이미지와 별개로 표정/무드만 복사하도록 지시
EXPRESSION_REFERENCE_TAG = """
[EXPRESSION REFERENCE] - COPY THIS EXPRESSION EXACTLY!

★★★ K-BEAUTY EXPRESSION GUIDE ★★★

FROM THIS REFERENCE IMAGE, COPY:

1. EYE EXPRESSION (눈 표현) - CRITICAL!
   - Eye openness: 크게 뜸 / 반쯤 감음 / 나른하게
   - Eye corner angle: 눈꼬리 올라감 / 내려감 / 중립
   - Gaze intensity: 강렬한 시선 / 부드러운 시선 / 몽환적 시선
   - Eye smile (눈웃음): 있음 / 없음

2. MOUTH EXPRESSION (입 표현) - CRITICAL!
   - Lip state: 다문 / 살짝 벌림 / 파우팅
   - Mouth corner angle: 입꼬리 올라감 / 내려감 / 중립
   - Lip tension: 긴장 / 이완 / 도톰하게 강조

3. CHIN/JAW ANGLE (턱 각도)
   - Chin position: 살짝 들어올림 / 중립 / 살짝 숙임
   - Jaw tension: 이완 / 긴장

4. OVERALL MOOD (전체 무드)
   - 시크 (Chic): cool, confident, slightly aloof
   - 러블리 (Lovely): warm, soft, approachable
   - 청순 (Innocent): pure, fresh, doe-eyed
   - 도도 (Haughty): detached, unreachable, cool

DO NOT COPY FROM THIS IMAGE:
- Face identity (얼굴 특징) → use FACE REFERENCE instead
- Makeup details (메이크업)
- Hair style (헤어스타일)

★★★ MATCH THE EXACT EXPRESSION MOOD AND INTENSITY! ★★★
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
    "POSE_REFERENCE_TAG",
    "EXPRESSION_REFERENCE_TAG",
]
