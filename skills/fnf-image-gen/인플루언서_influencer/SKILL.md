---
name: influencer
description: 얼굴 합성으로 인플루언서/셀럽 스타일 이미지 생성 (성별 무관)
user-invocable: true
trigger-keywords: ["인플", "인플루언서", "셀럽", "셀카 만들어", "예쁜 사진"]
---

# 인플루언서 이미지 생성 가이드

> 성별 무관 - 얼굴 참조 이미지 기반으로 자동 인식

---

## 대화 플로우

```
1. 사용자: "인플루 만들고 싶어" / "셀럽 이미지 만들어줘"

2. Claude: "얼굴 사진 주세요! (2~3장, 정면 얼빡이 좋아요)"

3. 사용자: [사진 첨부]

4. Claude: [얼굴 사진 분석 → 성별 명확하면 자동 인식, 애매하면 질문]
   - 명확한 경우: 바로 5번으로
   - 애매한 경우: "성별 선택해주세요: 여자/남자"

5. Claude: "[성별] 이미지 만들게요! 옵션 선택해주세요:

   📷 스타일
   • 끼부리는 셀카 - 카메라 보면서 포즈, 표정
   • 자연스러운 셀카 - 대충 찍은 듯한 느낌
   • 남이 찍어준 사진 - 누군가 찍어준 자연스러운 사진
   • 거울 셀카 - 거울 앞에서 전신/반신

   📐 카메라 거리
   • 얼빡 (Extreme Close-up)
   • 상체 (Medium)
   • 전신 (Full-shot)

   🏠 장소 (선택 또는 직접 입력)
   • 카페
   • 헬스장
   • 침대/방
   • 차 안
   • 클럽/파티
   • 야외/거리
   • 욕실
   • 소파/거실
   • (직접 입력)

   🔢 수량: 1~10장

   ※ 화질은 자연스러운 아이폰 느낌으로 고정"

6. 사용자: (각 항목에서 하나씩 선택) 또는 직접 입력

7. Claude: [이미지 생성]
```

### 빠른 예시 조합

| 조합 | 설명 |
|------|------|
| 끼부리는 셀카 + 얼빡 + 카페 | 전형적인 인스타 셀카 |
| 자연스러운 셀카 + 얼빡 + 침대 | 집에서 대충 찍은 느낌 |
| 거울 셀카 + 전신 + 헬스장 | 오오티디 거울샷 |
| 남이 찍어준 + 상체 + 야외 | 남친이 찍어준 느낌 |
| 남이 찍어준 + 전신 + 카페 | 프로필 사진 느낌 |
| 끼부리는 셀카 + 상체 + 차 안 | 럭셔리한 느낌 |

---

## 기술 스펙 (API 연결)

### 패키지 설치

```bash
pip install google-genai pillow
```

### API 키 설정

```bash
# .env 파일 (프로젝트 루트)
GEMINI_API_KEY=your_api_key_here

# 여러 키 로테이션 (rate limit 대응)
GEMINI_API_KEY=key1,key2,key3
```

### 모델 & 파라미터

| 항목 | 값 | 설명 |
|------|-----|------|
| **모델** | `gemini-3-pro-image-preview` | 이미지 생성 전용 (필수) |
| **Temperature** | `0.5` | 자연스러운 다양성 (0.3~0.7 권장) |
| **Aspect Ratio** | `9:16` | 인스타 스토리/릴스 세로형 |
| **해상도** | `2K` (2048px) | 고품질 (1K/2K/4K 선택 가능) |

**⚠️ 절대 금지 모델:**
- `gemini-2.0-flash-exp-image-generation` → 품질 낮음
- `gemini-2.0-flash` → 이미지 생성 미지원
- `gemini-2.5-flash` → 텍스트 전용

### API 호출 코드 (복사해서 사용)

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

# ============ 1. API 키 로드 ============
def load_api_keys():
    """프로젝트 루트의 .env에서 API 키 로드"""
    env_path = ".env"  # 또는 절대경로
    api_keys = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                    _, value = line.strip().split('=', 1)
                    api_keys.extend([k.strip() for k in value.split(',')])
    return api_keys or [os.environ.get("GEMINI_API_KEY", "")]

API_KEYS = load_api_keys()
key_index = 0

def get_next_api_key():
    """API 키 로테이션 (rate limit 대응)"""
    global key_index
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ============ 2. 이미지 변환 ============
def pil_to_part(img, max_size=1024):
    """PIL 이미지를 API Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

# ============ 3. 이미지 생성 ============
def generate_influencer_image(prompt, face_images):
    """
    인플루언서 이미지 생성

    Args:
        prompt: 한국어 프롬프트 (예: "이 얼굴로 카페에서 셀카")
        face_images: PIL Image 리스트 (얼굴 참조 이미지 2~3장)

    Returns:
        PIL Image or None
    """
    # 프롬프트 + 얼굴 이미지 조합
    parts = [types.Part(text=prompt)]
    for face_img in face_images:
        parts.append(pil_to_part(face_img))

    # API 호출
    client = genai.Client(api_key=get_next_api_key())
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",  # 필수: 이 모델만 사용
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=0.5,                    # 0.3~0.7 권장
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio="9:16",            # 세로형 (인스타)
                image_size="2K"                 # 2048px 해상도
            )
        )
    )

    # 결과 추출
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))

    return None
```

### 에러 처리

```python
import time

def generate_with_retry(prompt, face_images, max_retries=3):
    """재시도 로직 포함 생성"""
    for attempt in range(max_retries):
        try:
            return generate_influencer_image(prompt, face_images)
        except Exception as e:
            error_str = str(e).lower()
            # 재시도 가능한 에러
            if any(x in error_str for x in ["429", "503", "overloaded", "timeout", "rate"]):
                wait_time = (attempt + 1) * 10  # 10초, 20초, 30초
                print(f"Rate limit, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            # 재시도 불가능한 에러
            else:
                print(f"Error: {e}")
                return None
    return None
```

### 전체 사용 예시

```python
from PIL import Image

# 1. 얼굴 이미지 로드
face1 = Image.open("face1.png").convert("RGB")
face2 = Image.open("face2.png").convert("RGB")
face_images = [face1, face2]

# 2. 프롬프트 (한국어로 심플하게!)
prompt = "이 얼굴로 예쁜 여자, 침대에서 아이폰 셀카, 완전 얼빡, 끼부리는 표정"

# 3. 생성
result = generate_with_retry(prompt, face_images)

# 4. 저장
if result:
    result.save("output.png")
    print("Success!")
```

---

## 핵심 요약

| 항목 | 내용 |
|------|------|
| **패키지** | `pip install google-genai pillow` |
| **모델** | `gemini-3-pro-image-preview` (필수) |
| **Temperature** | `0.5` (자연스러운 다양성) |
| **비율** | `9:16` (인스타 스토리/릴스) |
| **해상도** | `2K` (2048px) |
| **프롬프트** | 한국어로 짧게 (영어 금지) |

---

## 프롬프트 작성법

### 원칙: 한국어로 짧고 심플하게

```
❌ 이렇게 하면 인위적 (영어 프롬프트 엔지니어링)
"Professional Instagram influencer photo, iPhone 15 Pro Max camera,
content creator aesthetic, gorgeous person, neutral-cool 5600K..."

✅ 이렇게 하면 자연스러움 (한국어로 친구한테 말하듯이)
"이 얼굴로 카페에서 턱 괴고 청순하게"
```

### 프롬프트 구조

```
이 얼굴로 [화질] [시점] [거리] [장소]에서 [자연스러움]
```

> 성별은 참조 이미지에서 자동 인식됨 - 별도 명시 불필요

### 옵션 → 프롬프트 변환

**구조:**
```
이 얼굴로 [성별] [화질] [시점] [거리] [장소]에서 [자연스러움]
```

**변환표:**

| 옵션 | 프롬프트 키워드 |
|------|----------------|
| **성별** | |
| 여자 | "예쁜 여자" |
| 남자 | "잘생긴 남자" |
| **스타일** | |
| 끼부리는 셀카 | "아이폰 셀카, 끼부리는 표정, 카메라 보면서 포즈" |
| 자연스러운 셀카 | "아이폰 셀카, 대충 찍은 듯, 자연스럽게" |
| 남이 찍어준 | "누가 찍어준 사진, 자연스럽게, 폰카 느낌" |
| 거울 셀카 | "거울 앞에서 폰 셀카, 거울에 비친 모습" |
| **거리** | |
| 얼빡 | "완전 얼빡", "얼굴 클로즈업" |
| 상체 | "상반신", "허리 위로" |
| 전신 | "전신샷", "발끝까지" |

### 조합 예시

| 선택 | 프롬프트 |
|------|----------|
| 여자 + 끼부리는 셀카 + 얼빡 + 카페 | 이 얼굴로 예쁜 여자 아이폰 셀카, 완전 얼빡, 카페에서 끼부리는 표정 |
| 여자 + 거울 셀카 + 전신 + 헬스장 | 이 얼굴로 예쁜 여자 거울 앞에서 폰 셀카, 전신, 헬스장에서 운동복 입고 포즈 |
| 남자 + 남이 찍어준 + 상체 + 카페 | 이 얼굴로 잘생긴 남자, 누가 찍어준 사진, 상반신, 카페에서 커피 마시는 중 |
| 남자 + 끼부리는 셀카 + 얼빡 + 차 안 | 이 얼굴로 잘생긴 남자 아이폰 셀카, 얼빡, 차 안에서 선글라스 |
| 여자 + 자연스러운 셀카 + 상체 + 침대 | 이 얼굴로 예쁜 여자 아이폰 셀카, 상반신, 침대에서 대충 찍은 듯 자연스럽게 |

---

## 다양하게 만들기

### 문제: 다 비슷하게 나옴

표정만 바꾸면 다 비슷함:
```
끼부리는 표정 → 청순한 표정 → 도도한 표정
= 결과 다 얼빡 셀카에 표정만 살짝 다름
```

### 해결: 상황/장소/포즈를 확 다르게

| 바꿔야 할 것 | 옵션들 |
|-------------|--------|
| **장소** | 방, 헬스장, 카페, 차 안, 야외, 클럽, 욕실, 호텔 |
| **포즈** | 얼빡, 전신, 앉아서, 누워서, 걷다가, 서서 |
| **옷** | 운동복, 원피스, 캐주얼, 파자마, 수건 |
| **시간** | 낮, 밤, 새벽 |

---

## 얼굴 참조 이미지

### 좋은 참조 이미지
- 정면 얼빡 셀카 2~3장
- 조명 좋은 것
- 다양한 표정 있으면 좋음

### 사용법
프롬프트와 함께 얼굴 이미지를 같이 첨부해서 API 호출

---

## 코드 예시

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# 이미지를 API Part로 변환
def pil_to_part(img, max_size=1024):
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.getvalue()))

# 얼굴 이미지 로드
face1 = Image.open("face1.png")
face2 = Image.open("face2.png")

# 프롬프트
prompt = "이 얼굴로 카페에서 턱 괴고 청순하게"

# API 호출
client = genai.Client(api_key="YOUR_KEY")
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[types.Content(role="user", parts=[
        types.Part(text=prompt),
        pil_to_part(face1),
        pil_to_part(face2),
    ])],
    config=types.GenerateContentConfig(
        temperature=0.5,
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio="9:16",
            image_size="2K"
        )
    )
)

# 결과 저장
for part in response.candidates[0].content.parts:
    if part.inline_data:
        Image.open(BytesIO(part.inline_data.data)).save("result.png")
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 너무 인위적 | 영어 프롬프트, 과한 기술 명세 | 한국어로 짧게 |
| 다 비슷함 | 표정만 바꿈 | 장소/포즈/옷 확 다르게 |
| 얼굴 안 닮음 | 참조 이미지 품질 | 정면 얼빡 이미지 사용 |
| 손 이상함 | AI 한계 | 손 안 보이는 포즈로 |

---

## 배치 생성 (여러 장)

```python
import time
from datetime import datetime

# 다양한 상황 프롬프트
PROMPTS = [
    "이 얼굴로 예쁜 여자, 침대에서 셀카, 얼빡, 끼부리는 표정, 윙크",
    "이 얼굴로 예쁜 여자, 카페에서 턱 괴고, 상체, 청순한 눈빛",
    "이 얼굴로 예쁜 여자, 헬스장 거울샷, 전신, 운동복",
    "이 얼굴로 예쁜 여자, 차 안에서 셀카, 얼빡, 선글라스",
    "이 얼굴로 예쁜 여자, 소파에 누워서 셀카, 파자마, 졸린 표정",
]

def batch_generate(face_images, output_dir):
    """여러 장 생성"""
    os.makedirs(output_dir, exist_ok=True)

    for i, prompt in enumerate(PROMPTS):
        print(f"[{i+1}/{len(PROMPTS)}] Generating...")

        result = generate_with_retry(prompt, face_images)

        if result:
            timestamp = datetime.now().strftime("%H%M%S")
            result.save(f"{output_dir}/influencer_{i+1:02d}_{timestamp}.png")
            print(f"  -> Success!")
        else:
            print(f"  -> Failed")

        time.sleep(3)  # rate limit 방지
```

---

## 출력 폴더

```
Fnf_studio_outputs/
└── hotgirl_influencer/
    └── bedroom_selfie_20260209_093758/
        ├── influencer_01_093836.png
        ├── influencer_02_093922.png
        └── ...
```

---

## 파일 구조

```
skills/fnf-image-gen/인플루언서_influencer/
├── README.md         # 빠른 시작 가이드
├── SKILL.md          # 이 문서
├── generate.py       # CLI 실행 스크립트
└── faces/            # 베이스 얼굴 이미지 폴더 (로컬 전용)
    ├── face1.png
    └── face2.png
```

---

## 빠른 시작

```bash
# 1. 패키지 설치
pip install google-genai pillow

# 2. API 키 설정 (.env 파일)
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. 얼굴 이미지 준비 (2~3장, 정면 얼빡)

# 4. Claude에게 "인플 이미지 만들어줘" 라고 말하면 끝!
```
