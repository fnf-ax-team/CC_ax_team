"""
VLM 포즈 분석기

포즈 레퍼런스 이미지에서 상세 신체 부위 정보를 추출하여
프롬프트 스키마 형식으로 반환합니다.

스키마 필드:
- stance: stand, sit, walk, lean_wall, lean, kneel
- 왼팔, 오른팔, 왼손, 오른손, 왼다리, 오른다리, 힙
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


@dataclass
class PoseAnalysisResult:
    """포즈 분석 결과"""

    # 기본 stance
    stance: str  # stand, sit, walk, lean_wall, lean, kneel

    # 신체 부위별 설명
    left_arm: str  # 왼팔
    right_arm: str  # 오른팔
    left_hand: str  # 왼손
    right_hand: str  # 오른손
    left_leg: str  # 왼다리
    right_leg: str  # 오른다리
    hip: str  # 힙 (무게중심)

    # 추가: 방향 및 기울기 정보
    torso_tilt: str = (
        ""  # 상체 기울기 (예: "왼쪽으로 10도 기울임", "오른쪽으로 살짝 기울임")
    )
    left_foot_direction: str = ""  # 왼발 방향 (안쪽/바깥쪽/정면)
    right_foot_direction: str = ""  # 오른발 방향 (안쪽/바깥쪽/정면)
    left_knee_direction: str = ""  # 왼쪽 무릎 방향 (안쪽/바깥쪽/정면) ★중요★
    right_knee_direction: str = ""  # 오른쪽 무릎 방향 (안쪽/바깥쪽/정면) ★중요★
    # 무릎 각도/높이/발 위치 (정밀 분석)
    left_knee_angle: str = ""  # 왼쪽 무릎 각도 (예: "약 90도", "약 45도")
    right_knee_angle: str = ""  # 오른쪽 무릎 각도
    left_knee_height: str = ""  # 왼쪽 무릎 높이 (예: "가슴 높이", "배꼽 높이")
    right_knee_height: str = ""  # 오른쪽 무릎 높이
    left_foot_position: str = ""  # 왼발 위치 (예: "엉덩이 바로 앞", "몸 바깥쪽")
    right_foot_position: str = ""  # 오른발 위치
    shoulder_line: str = ""  # 어깨 라인 (예: "왼쪽 어깨가 살짝 높음", "수평")
    face_direction: str = ""  # 얼굴 방향 (예: "카메라 정면", "왼쪽으로 15도 돌림")
    # 목/고개 (포즈 정확도 핵심)
    neck_tilt: str = ""  # 목 기울기 (예: "오른쪽으로 15도 기울임", "살짝 왼쪽")
    head_tilt: str = ""  # 고개 숙임/들기 (예: "살짝 숙임", "턱 들기", "수평")
    # 팔꿈치 정밀 분석 (팔 서브필드)
    left_elbow_angle: str = ""  # 왼쪽 팔꿈치 각도 (예: "약 90도", "펴짐(170도)")
    right_elbow_angle: str = ""  # 오른쪽 팔꿈치 각도
    left_elbow_direction: str = ""  # 왼쪽 팔꿈치 방향 (예: "바깥쪽", "아래쪽")
    right_elbow_direction: str = ""  # 오른쪽 팔꿈치 방향

    # ★★★ 다리 형태 (4자 vs L자) ★★★
    bent_leg_shape: str = ""  # "4자", "L자", "직립" (양쪽 다 펴짐)
    # 4자: 무릎이 옆(바깥)으로 벌어짐, 발이 지지다리 안쪽/뒤쪽
    # L자: 무릎이 앞/위로 올라감, 발이 아래로 매달림

    # 추가 정보
    camera_angle: str = ""  # 촬영 앵글 (정면, 측면, 3/4측면 등)
    camera_height: str = ""  # 촬영 높이 (눈높이, 로앵글, 하이앵글 등)
    framing: str = ""  # 프레이밍 (FS, MFS, MS, MCU, CU)

    # 신뢰도
    confidence: float = 0.5  # 0-1
    raw_response: Dict[str, Any] = None

    def to_schema_format(self) -> Dict[str, str]:
        """프롬프트 스키마 형식으로 변환"""
        return {
            "stance": self.stance,
            "왼팔": self.left_arm,
            "오른팔": self.right_arm,
            "왼손": self.left_hand,
            "오른손": self.right_hand,
            "왼다리": self.left_leg,
            "오른다리": self.right_leg,
            "힙": self.hip,
            # 방향 및 기울기
            "상체기울기": self.torso_tilt,
            "왼발방향": self.left_foot_direction,
            "오른발방향": self.right_foot_direction,
            "왼무릎방향": self.left_knee_direction,
            "오른무릎방향": self.right_knee_direction,
            # 무릎 정밀 분석 ★★★
            "왼무릎각도": self.left_knee_angle,
            "오른무릎각도": self.right_knee_angle,
            "왼무릎높이": self.left_knee_height,
            "오른무릎높이": self.right_knee_height,
            "왼발위치": self.left_foot_position,
            "오른발위치": self.right_foot_position,
            "어깨라인": self.shoulder_line,
            "얼굴방향": self.face_direction,
            # 목/고개
            "목기울기": self.neck_tilt,
            "고개각도": self.head_tilt,
            # 팔꿈치 정밀 분석
            "왼팔꿈치각도": self.left_elbow_angle,
            "오른팔꿈치각도": self.right_elbow_angle,
            "왼팔꿈치방향": self.left_elbow_direction,
            "오른팔꿈치방향": self.right_elbow_direction,
            # 다리 형태
            "다리형태": self.bent_leg_shape,
            # 촬영 세팅 (prompt.json 로깅용)
            "프레이밍": self.framing,
            "앵글": self.camera_angle,
            "높이": self.camera_height,
        }

    def to_camera_format(self) -> Dict[str, str]:
        """촬영 세팅 스키마 형식으로 변환"""
        return {
            "앵글": self.camera_angle,
            "높이": self.camera_height,
            "프레이밍": self.framing,
        }

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트로 변환 (한글 문장형)"""
        lines = []
        lines.append(f"[포즈 기본 자세]: {self._stance_korean(self.stance)}")
        lines.append(f"[왼팔]: {self.left_arm}")
        lines.append(f"[오른팔]: {self.right_arm}")
        lines.append(f"[왼손]: {self.left_hand}")
        lines.append(f"[오른손]: {self.right_hand}")
        lines.append(f"[왼다리]: {self.left_leg}")
        lines.append(f"[오른다리]: {self.right_leg}")
        lines.append(f"[무게중심]: {self.hip}")
        # ★★★ 다리 형태 (핵심!) ★★★
        if self.bent_leg_shape:
            lines.append(f"[다리 형태]: {self.bent_leg_shape}")
        # 방향 및 기울기 (★ 중요: 정확한 방향 재현 필수 ★)
        if self.torso_tilt:
            lines.append(f"[상체 기울기]: {self.torso_tilt}")
        if self.left_foot_direction:
            lines.append(f"[왼발 방향]: {self.left_foot_direction}")
        if self.right_foot_direction:
            lines.append(f"[오른발 방향]: {self.right_foot_direction}")
        # ★★★ 무릎 정밀 분석 (매우 중요!) ★★★
        if self.left_knee_angle:
            lines.append(f"[왼쪽 무릎 각도]: {self.left_knee_angle}")
        if self.right_knee_angle:
            lines.append(f"[오른쪽 무릎 각도]: {self.right_knee_angle}")
        if self.left_knee_height:
            lines.append(f"[왼쪽 무릎 높이]: {self.left_knee_height}")
        if self.right_knee_height:
            lines.append(f"[오른쪽 무릎 높이]: {self.right_knee_height}")
        if self.left_foot_position:
            lines.append(f"[왼발 위치]: {self.left_foot_position}")
        if self.right_foot_position:
            lines.append(f"[오른발 위치]: {self.right_foot_position}")
        if self.left_knee_direction:
            lines.append(f"[왼쪽 무릎 방향]: {self.left_knee_direction}")
        if self.right_knee_direction:
            lines.append(f"[오른쪽 무릎 방향]: {self.right_knee_direction}")
        if self.shoulder_line:
            lines.append(f"[어깨 라인]: {self.shoulder_line}")
        if self.face_direction:
            lines.append(f"[얼굴 방향]: {self.face_direction}")
        # 목/고개
        if self.neck_tilt:
            lines.append(f"[목 기울기]: {self.neck_tilt}")
        if self.head_tilt:
            lines.append(f"[고개 각도]: {self.head_tilt}")
        # 팔꿈치 정밀
        if self.left_elbow_angle:
            lines.append(f"[왼쪽 팔꿈치 각도]: {self.left_elbow_angle}")
        if self.right_elbow_angle:
            lines.append(f"[오른쪽 팔꿈치 각도]: {self.right_elbow_angle}")
        if self.left_elbow_direction:
            lines.append(f"[왼쪽 팔꿈치 방향]: {self.left_elbow_direction}")
        if self.right_elbow_direction:
            lines.append(f"[오른쪽 팔꿈치 방향]: {self.right_elbow_direction}")
        # 카메라 설정
        lines.append(f"[촬영 앵글]: {self.camera_angle}")
        lines.append(f"[촬영 높이]: {self.camera_height}")
        lines.append(f"[프레이밍]: {self.framing}")
        return "\n".join(lines)

    def _stance_korean(self, stance: str) -> str:
        """stance를 한국어로 변환"""
        mapping = {
            "stand": "서있는 자세",
            "sit": "앉은 자세",
            "walk": "걷는 자세",
            "lean_wall": "벽/구조물에 기댄 자세",
            "lean": "기댄 자세",
            "kneel": "무릎 꿇은 자세",
        }
        return mapping.get(stance, stance)


# VLM 포즈 분석 프롬프트
POSE_ANALYSIS_PROMPT = """당신은 패션 화보 포즈 분석 전문가입니다.

## 작업
이미지에서 모델의 포즈를 분석하여 아래 JSON 형식으로 출력하세요.

★★★ 중요: 특정 물체/장소 추측 금지! ★★★
- "신호등에 기대다" → "수직 기둥에 기대다"
- "카페 의자에 앉다" → "의자에 앉다"
- "벤치에 앉다" → "평평한 표면에 앉다"
- 배경의 특정 장소나 물체를 언급하지 마세요!
- 오직 신체의 자세와 방향만 묘사하세요.

## 분석 항목

### 1. stance (기본 자세)
다음 중 하나를 선택:
- "stand": 서있는 자세 (체중을 다리로 지지)
- "sit": 앉은 자세 (무언가에 앉음)
- "walk": 걷는 자세 (한 발이 앞으로 나감)
- "lean_wall": 수직 표면에 기댄 자세
- "lean": 기대는 자세 (표면에 기댐)
- "kneel": 무릎 꿇은 자세

### 2. 신체 부위별 설명 (구체적으로!)

각 부위를 한국어로 상세히 설명하세요.
★ 주의: 특정 물체명 금지! 일반적 표현 사용 ★
★★★ 중요: 방향을 반드시 명시! (안쪽/바깥쪽, 왼쪽/오른쪽) ★★★

좋은 예시:
- 왼팔: "팔꿈치 구부려 가슴 높이로 들어올림, 팔꿈치가 바깥쪽을 향함"
- 오른팔: "자연스럽게 뒤로 스윙, 손바닥이 뒤쪽을 향함"
- 왼손: "가방 끈 잡기", "주머니에 엄지 걸침"
- 오른손: "손가락 펴서 허벅지에 올림, 손바닥이 안쪽을 향함"

★★★ 다리 설명 시 반드시 포함할 정보 ★★★

1) 무릎 각도 (0-180도)
   - 0도 = 완전히 접힘 (발이 엉덩이에 닿음)
   - 90도 = 직각 (무릎이 세워짐)
   - 180도 = 완전히 펴짐

2) 무릎 높이 (앉은 자세 기준)
   - "무릎이 가슴 높이까지 올라옴"
   - "무릎이 배꼽 높이"
   - "무릎이 허벅지와 수평"

3) 발 위치 (엉덩이 기준)
   - "발이 엉덩이 바로 앞"
   - "발이 엉덩이에서 30cm 앞"
   - "발이 몸 바깥쪽으로 뻗음"

4) 무릎 방향
   - "안쪽으로 모임" = X자 다리
   - "바깥쪽으로 벌어짐" = O자 다리
   - "정면" = 중립

좋은 예시:
- 왼다리: "무릎 각도 약 80도로 세움, 무릎이 가슴 높이까지 올라옴, 발은 엉덩이 바로 앞에, 무릎이 살짝 바깥쪽"
- 오른다리: "무릎 각도 약 120도로 느슨하게 구부림, 무릎이 왼쪽 무릎보다 낮음, 발은 몸 바깥쪽에, 무릎이 안쪽으로 기울어짐"
- 힙: "왼쪽 다리에 무게중심 70%, 골반이 왼쪽으로 10도 틀어짐"

나쁜 예시 (금지):
- "무릎 구부림" → 각도 없음! "무릎 약 90도로 구부림"으로 변경
- "다리 세움" → 높이 없음! "무릎이 가슴 높이까지 세움"으로 변경
- 방향 없이 설명 → 반드시 안쪽/바깥쪽/정면 명시!

### 3. 구부린 다리 형태 판별 (★★★ 최우선 확인! ★★★)

한쪽 다리가 구부러져 있으면, 아래 중 어떤 형태인지 반드시 판별하세요:

**"4자" (figure-4 shape):**
- 무릎이 **옆(바깥쪽)**으로 벌어짐
- 발이 지지다리의 안쪽 종아리/허벅지에 대거나 뒤쪽으로 접힘
- 위에서 보면 두 다리가 숫자 "4" 모양
- 예: 플라밍고 자세, 벽에 기대고 한 발을 벽에 붙인 자세
- 핵심: 허벅지가 **옆으로** 열림

**"L자" (L-shape / forward lift):**
- 무릎이 **앞/위**로 올라감
- 발이 아래로 매달리거나 앞쪽에 위치
- 옆에서 보면 다리가 "L" 모양
- 예: 계단 오르기, 무릎을 가슴 쪽으로 당기기
- 핵심: 허벅지가 **앞으로** 올라감

**"직립":** 양쪽 다리 모두 거의 펴져 있음 (무릎 각도 150도 이상)

bent_leg_shape 필드에 "4자", "L자", "직립" 중 하나를 적으세요.

### 4. 방향 및 기울기 (★★★ 매우 중요! ★★★)

- torso_tilt: 상체가 어느 방향으로 기울어졌는지
  예: "왼쪽으로 10도 기울임", "오른쪽으로 살짝 기울임", "수직 (기울지 않음)"

★★★ 목/고개 (CRITICAL!) ★★★

- neck_tilt: 목이 어느 방향으로 기울었는지 (갸우뚱)
  예: "오른쪽으로 15도 기울임", "왼쪽으로 살짝 기울임", "수직 (기울지 않음)"

- head_tilt: 고개를 숙이거나 들었는지 (상하)
  예: "살짝 숙임 (턱 당김)", "턱 들기 (위를 봄)", "수평 (정면)", "살짝 숙여 아래를 내려다봄"

★★★ 팔꿈치 상세 분석 (CRITICAL!) ★★★

- left_elbow_angle: 왼쪽 팔꿈치 구부림 각도
  예: "약 90도 (직각)", "약 150도 (살짝 구부림)", "펴짐 (약 170도)"

- right_elbow_angle: 오른쪽 팔꿈치 구부림 각도
  예: "약 90도", "약 120도", "펴짐"

- left_elbow_direction: 왼쪽 팔꿈치가 향하는 방향
  예: "바깥쪽", "아래쪽", "뒤쪽", "몸쪽"

- right_elbow_direction: 오른쪽 팔꿈치가 향하는 방향
  예: "바깥쪽", "위쪽", "뒤쪽"

- left_foot_direction: 왼발 끝이 향하는 방향
  예: "바깥쪽 45도", "안쪽으로 향함", "정면"

- right_foot_direction: 오른발 끝이 향하는 방향
  예: "바깥쪽 30도", "안쪽으로 향함", "정면"

★★★ 무릎 상세 분석 (CRITICAL!) ★★★

무릎 각도:
- left_knee_angle: 왼쪽 무릎 구부림 각도
  예: "약 90도 (직각)", "약 45도 (깊게 접힘)", "약 120도 (살짝 구부림)", "약 170도 (거의 펴짐)"

- right_knee_angle: 오른쪽 무릎 구부림 각도
  예: "약 90도", "약 60도", "약 150도"

무릎 높이 (앉은 자세에서 중요!):
- left_knee_height: 왼쪽 무릎이 올라온 높이
  예: "가슴 높이", "배꼽 높이", "허벅지와 수평", "낮게 (바닥 가까이)"

- right_knee_height: 오른쪽 무릎 높이
  예: "왼쪽 무릎보다 낮음", "가슴 높이", "허벅지와 수평"

발 위치:
- left_foot_position: 왼발 위치 (엉덩이 기준)
  예: "엉덩이 바로 앞", "엉덩이에서 30cm 앞", "몸 바깥쪽으로 뻗음"

- right_foot_position: 오른발 위치
  예: "몸 바깥쪽", "엉덩이 옆", "왼발보다 바깥쪽"

무릎 방향:
- left_knee_direction: 왼쪽 무릎이 향하는 방향
  예: "안쪽으로 모임", "바깥쪽으로 벌어짐", "정면"

- right_knee_direction: 오른쪽 무릎이 향하는 방향
  예: "안쪽으로 모임 (왼쪽 무릎 쪽으로)", "바깥쪽", "정면"

- shoulder_line: 어깨 라인의 기울기
  예: "왼쪽 어깨가 살짝 높음", "오른쪽 어깨가 높음", "수평"

- face_direction: 얼굴이 향하는 방향
  예: "카메라 정면", "왼쪽으로 15도 돌림", "오른쪽으로 30도 돌림"

### 4. 카메라 설정

- camera_angle: "정면", "약간측면", "3/4측면", "측면"
- camera_height: "눈높이", "살짝로앵글", "로앵글", "하이앵글", "살짝하이앵글"

★★★ framing (프레이밍) - 매우 정확하게 판별! ★★★

이미지의 **하단 경계선에서 잘리는 신체 부위**를 보고 판별하세요:

[STEP 1] 이미지 하단에 무엇이 보이는지 확인:
- 발/신발이 완전히 보임 → FS
- 무릎~종아리 부근에서 잘림, 발 안 보임 → MFS
- 허리/벨트 부근에서 잘림 → MS
- 가슴/어깨 부근에서 잘림 → MCU
- 얼굴/턱만 보임 → CU

[STEP 2] 프레이밍 선택:
- "CU": 얼굴+목만. 어깨 겨우 보임
- "MCU": 머리~가슴. 가슴 중간에서 잘림
- "MS": 머리~허리. 벨트 라인에서 잘림
- "MFS": 머리~무릎. 무릎~허벅지 중간에서 잘림. ★발이 안 보임★
- "FS": 머리~발끝. 발/신발이 바닥에 완전히 보임

★ 핵심 구분: MFS vs FS ★
- 발/신발이 보이면 → FS
- 발/신발이 안 보이고 무릎 근처에서 잘리면 → MFS

### 5. confidence
분석 신뢰도 (0-1). 이미지가 불명확하면 낮게 설정.

## 출력 형식 (JSON)
```json
{
    "stance": "sit",
    "left_arm": "팔꿈치 구부려 왼쪽 무릎 위에 올림, 손으로 턱을 괴고 있음",
    "right_arm": "아래로 뻗어 오른쪽 발을 잡고 있음",
    "left_hand": "손바닥으로 왼쪽 뺨과 턱을 받침",
    "right_hand": "오른쪽 신발 윗부분을 잡고 있음",
    "left_leg": "무릎 약 85도로 세움, 무릎이 가슴 높이까지 올라옴, 발은 엉덩이 바로 앞",
    "right_leg": "무릎 약 110도로 구부림, 무릎이 왼쪽보다 낮음, 발은 몸 바깥쪽",
    "hip": "평평한 표면에 앉음, 무게중심 중앙, 상체가 왼쪽으로 약간 틀어짐",
    "torso_tilt": "왼쪽으로 약 10도 기울임",
    "left_foot_direction": "정면",
    "right_foot_direction": "바깥쪽 45도",
    "left_knee_angle": "약 85도 (거의 직각으로 세움)",
    "right_knee_angle": "약 110도 (느슨하게 구부림)",
    "left_knee_height": "가슴 높이",
    "right_knee_height": "왼쪽 무릎보다 낮음, 배꼽 높이",
    "left_foot_position": "엉덩이 바로 앞",
    "right_foot_position": "몸 바깥쪽으로 뻗음",
    "left_knee_direction": "살짝 바깥쪽",
    "right_knee_direction": "안쪽으로 기울어짐 (왼쪽 무릎 방향)",
    "shoulder_line": "왼쪽 어깨가 높음",
    "face_direction": "카메라 정면",
    "neck_tilt": "오른쪽으로 약 10도 기울임",
    "head_tilt": "살짝 숙임 (턱 당김)",
    "left_elbow_angle": "약 90도 (직각으로 구부림)",
    "right_elbow_angle": "약 150도 (살짝 구부림)",
    "left_elbow_direction": "바깥쪽",
    "right_elbow_direction": "아래쪽",
    "bent_leg_shape": "4자",
    "camera_angle": "약간측면",
    "camera_height": "살짝로앵글",
    "framing": "FS",
    "confidence": 0.9
}
```

JSON만 출력하세요. 다른 텍스트는 금지입니다."""


class PoseAnalyzer:
    """VLM 포즈 분석기"""

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
        pose_image: Union[str, Path, Image.Image],
    ) -> PoseAnalysisResult:
        """
        포즈 이미지 분석

        Args:
            pose_image: 포즈 레퍼런스 이미지

        Returns:
            PoseAnalysisResult: 분석 결과
        """
        # 이미지 로드
        if isinstance(pose_image, (str, Path)):
            img = Image.open(pose_image).convert("RGB")
        else:
            img = pose_image.convert("RGB")

        # API 파트 구성
        parts = [
            types.Part(text=POSE_ANALYSIS_PROMPT),
            types.Part(text="[POSE IMAGE]:"),
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
            print(f"[PoseAnalyzer] API 호출 실패: {e}")
            # 기본 결과 반환
            return PoseAnalysisResult(
                stance="stand",
                left_arm="분석 실패",
                right_arm="분석 실패",
                left_hand="분석 실패",
                right_hand="분석 실패",
                left_leg="분석 실패",
                right_leg="분석 실패",
                hip="분석 실패",
                camera_angle="정면",
                camera_height="눈높이",
                framing="FS",
                confidence=0.0,
                raw_response={"error": str(e)},
            )

        # 결과 변환
        return PoseAnalysisResult(
            stance=result_json.get("stance", "stand"),
            left_arm=result_json.get("left_arm", ""),
            right_arm=result_json.get("right_arm", ""),
            left_hand=result_json.get("left_hand", ""),
            right_hand=result_json.get("right_hand", ""),
            left_leg=result_json.get("left_leg", ""),
            right_leg=result_json.get("right_leg", ""),
            hip=result_json.get("hip", ""),
            # 방향 및 기울기 정보
            torso_tilt=result_json.get("torso_tilt", ""),
            left_foot_direction=result_json.get("left_foot_direction", ""),
            right_foot_direction=result_json.get("right_foot_direction", ""),
            left_knee_direction=result_json.get("left_knee_direction", ""),
            right_knee_direction=result_json.get("right_knee_direction", ""),
            # 무릎 각도/높이/발 위치 (정밀 분석)
            left_knee_angle=result_json.get("left_knee_angle", ""),
            right_knee_angle=result_json.get("right_knee_angle", ""),
            left_knee_height=result_json.get("left_knee_height", ""),
            right_knee_height=result_json.get("right_knee_height", ""),
            left_foot_position=result_json.get("left_foot_position", ""),
            right_foot_position=result_json.get("right_foot_position", ""),
            shoulder_line=result_json.get("shoulder_line", ""),
            face_direction=result_json.get("face_direction", ""),
            # 목/고개
            neck_tilt=result_json.get("neck_tilt", ""),
            head_tilt=result_json.get("head_tilt", ""),
            # 팔꿈치 정밀 분석
            left_elbow_angle=result_json.get("left_elbow_angle", ""),
            right_elbow_angle=result_json.get("right_elbow_angle", ""),
            left_elbow_direction=result_json.get("left_elbow_direction", ""),
            right_elbow_direction=result_json.get("right_elbow_direction", ""),
            # 다리 형태
            bent_leg_shape=result_json.get("bent_leg_shape", "직립"),
            # 카메라 설정
            camera_angle=result_json.get("camera_angle", "정면"),
            camera_height=result_json.get("camera_height", "눈높이"),
            framing=result_json.get("framing", "FS"),
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


def analyze_pose(
    pose_image: Union[str, Path, Image.Image],
    api_key: Optional[str] = None,
) -> PoseAnalysisResult:
    """
    포즈 분석 (편의 함수)

    Args:
        pose_image: 포즈 레퍼런스 이미지
        api_key: Gemini API 키

    Returns:
        PoseAnalysisResult: 분석 결과
    """
    analyzer = PoseAnalyzer(api_key=api_key)
    return analyzer.analyze(pose_image)
