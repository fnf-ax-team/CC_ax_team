---
name: ai-influencer
description: AI 인플루언서 이미지 생성 - 이미지 레퍼런스 기반 (텍스트 최소화)
user-invocable: true
trigger-keywords: ["AI인플루언서", "ai인플", "인플루언서", "AI인플", "가상인플", "버추얼인플"]
---

# AI 인플루언서 이미지 생성 v2.0

> **이미지 레퍼런스 기반 생성 (텍스트 프롬프트 최소화)**
>
> 등록된 AI 인플루언서 캐릭터 + 프리셋 이미지로 일관된 시리즈 콘텐츠 생성

---

## v2.0 핵심 변경사항

| 항목 | v1.0 | v2.0 |
|------|------|------|
| 포즈 지정 | 텍스트 프롬프트 | **프리셋 이미지** |
| 표정 지정 | 텍스트 프롬프트 | **프리셋 이미지** |
| 배경 지정 | 텍스트 프롬프트 | **프리셋 이미지** |
| 착장 지정 | 텍스트 + 이미지 | **이미지만** |
| 프롬프트 방식 | JSON 스키마 조립 | **역할 설명만** |

**원칙: 이미지 레퍼런스 + VLM 분석 텍스트 병행. 이미지만으로는 프레이밍/앵글 정확도 부족.**

---

## 절대 규칙 (CRITICAL)

1. **필수 모델**: gemini-3-pro-image-preview
2. **이미지 레퍼런스 기반** - 포즈/표정/배경은 텍스트 대신 이미지로 전달
3. **캐릭터 얼굴 이미지 반드시 전송** - 다각도 3-5장
4. **얼굴 동일성 40%** - 셀카(25%)보다 높은 비중

### 기본 파라미터

| 항목 | 값 |
|------|-----|
| **모델** | `gemini-3-pro-image-preview` |
| **Temperature** | `0.5` (일관성 중시) |
| **Aspect Ratio** | `9:16` (스토리/릴스) |
| **해상도** | `2K` (2048px) |
| **비주얼 무드** | `OUTDOOR_CASUAL_001` (SNS용) |

---

## 비주얼 무드 프리셋 (CRITICAL)

**AI 인플루언서는 SNS용 프리셋 사용**

| 프리셋 ID | 용도 | 설명 |
|-----------|------|------|
| `OUTDOOR_CASUAL_001` | **SNS** | 강혜원 스타일, 인플루언서 일상, 인스타 피드용 |

```python
# 비주얼 무드 설정
visual_mood = {
    "preset_id": "OUTDOOR_CASUAL_001",
    "필름_텍스처": {
        "질감": "clean digital, natural smartphone quality, no grain",
        "보정법": "minimal edit, natural skin texture, Instagram-ready"
    },
    "컬러_그레이딩": {
        "주요색조": "neutral natural, soft muted tones",
        "채도": "slightly muted, natural",
        "노출": "soft natural light, balanced"
    },
    "조명": {
        "광원": "natural daylight, overcast sky, ambient outdoor light",
        "방향": "diffused all around, soft side light",
        "그림자": "soft natural shadows, minimal contrast"
    }
}
```

**반드시 이 프리셋을 프롬프트에 포함시켜야 한다.**

---

## 이미지 역할 (API 전송 순서)

```
[IMAGE ROLES]

IMAGE 1: POSE/EXPRESSION REFERENCE
- Copy EXACT pose, camera angle, framing
- Copy EXACT expression (mouth, eyes, vibe)
- Ignore face/outfit from this image

IMAGE 2-4: FACE REFERENCE (multi-angle)
- Use ONLY this person's face
- Maintain face identity across all angles
- Weight: 40%

IMAGE 5+: OUTFIT REFERENCE
- Wear EXACTLY these clothes
- Match colors, logos, details precisely

IMAGE LAST: BACKGROUND REFERENCE (if provided)
- Use this environment/setting
- Ignore any people in background image

[OUTPUT]
- Natural influencer photo
- Authentic, not overly polished
- Realistic skin texture
```

**텍스트 설명은 위 역할만.** 포즈/표정/배경은 이미지가 정의함.

---

## 셀카 스킬과 차이점

| 항목 | 셀카 스킬 | AI 인플루언서 스킬 |
|------|----------|-------------------|
| 얼굴 입력 | 매번 경로 입력 | **폴더에서 자동 로드** |
| 얼굴 이미지 수 | 1장 | **1~2장** (다양한 각도) |
| 얼굴 동일성 검증 | 25% | **40%** (강화) |
| 프롬프트 방식 | 텍스트 + 이미지 | **이미지 레퍼런스만** |
| Temperature | 0.7 | **0.5** (일관성) |
| 목적 | 일회성 셀카 | **시리즈 콘텐츠** |

---

## 프리셋 이미지 연동

### 프리셋 폴더 구조

```
db/presets/
├── pose/                    # 포즈 레퍼런스 이미지
│   ├── 전신_01.jpg
│   ├── 전신_02.jpg
│   ├── 상반신_01.jpg
│   └── ...
├── expression/              # 표정 레퍼런스 이미지
│   ├── 시크_01.jpg
│   ├── 시크_02.jpg
│   ├── 러블리_01.jpg
│   └── ...
└── background/              # 배경 레퍼런스 이미지
    ├── 핫플카페_01.jpg
    ├── 그래피티_01.jpg
    └── ...
```

### 프리셋 ID → 이미지 매핑

| 프리셋 카테고리 | ID 패턴 | 예시 |
|----------------|---------|------|
| 포즈 | `{타입}_{번호}` | `전신_05`, `상반신_12`, `앉기_03` |
| 표정 | `{스타일}_{번호}` | `시크_02`, `러블리_04` |
| 배경 | `{장소}_{번호}` | `핫플카페_08`, `그래피티_05` |

```python
# 프리셋 ID로 이미지 경로 가져오기
pose_image = get_preset_image_path("pose", "전신_05")
# -> "db/presets/pose/전신_05.jpg"
```

---

## 캐릭터 설정

### 폴더 구조

```
db/ai_influencer/{캐릭터명}/
├── profile.json           <- 캐릭터 프로필
├── face/                  <- 기준 얼굴 이미지들 (3-5장)
│   ├── front.jpg          <- 정면 (필수)
│   ├── side.jpg           <- 측면 (권장)
│   └── smile.jpg          <- 미소 (권장)
└── style_guide.md         <- 스타일 가이드 (선택)
```

### profile.json 형식

```json
{
  "name": "루나",
  "name_en": "Luna",
  "gender": "여성",
  "age": "20대 초반",
  "ethnicity": "한국인",
  "face_features": {
    "face_shape": "계란형, 갸름한 턱선",
    "eyes": "크고 또렷한 쌍커풀 눈, 긴 속눈썹",
    "nose": "높고 오똑한 콧대",
    "lips": "도톰한 입술",
    "skin": "맑고 투명한 피부톤"
  },
  "style": {
    "brand_affinity": ["MLB", "스트릿", "캐주얼"],
    "preferred_colors": ["블랙", "화이트", "데님블루"],
    "makeup_style": "natural"
  },
  "personality": "밝고 친근한, 일상을 공유하는 인플루언서"
}
```

---

## 대화형 워크플로 (CRITICAL)

**사용자에게 단계별로 질문하며 진행한다. 한꺼번에 묻지 않는다!**

---

### Step 1: 얼굴 이미지 요청

```
얼굴 이미지를 알려주세요.

생성할 인물의 얼굴 이미지 경로를 입력해주세요.
(1~2장 권장, 다양한 각도면 더 좋아요)

예: D:\images\face.jpg
```

**파일 확인 후 썸네일 또는 파일명 표시**

---

### Step 2: 착장 이미지 요청

```
착장 이미지를 알려주세요.

입힐 옷 이미지들의 경로를 입력해주세요.
(여러 장이면 쉼표로 구분하거나 폴더 경로)

예: D:\images\outfit1.jpg, D:\images\outfit2.jpg
```

**파일 확인 후 아이템 목록 표시**

---

### Step 3: 레퍼런스 이미지 요청 (선택)

```
레퍼런스 이미지가 있으신가요?

| 유형 | 설명 | 필수 |
|------|------|------|
| 포즈 | 따라할 포즈 이미지 | 권장 |
| 표정 | 따라할 표정 이미지 | 선택 |
| 배경 | 원하는 배경 이미지 | 선택 |

경로를 입력하거나, 없으면 "없음"이라고 해주세요.
```

**AskUserQuestion 예시:**
```python
{
    "questions": [{
        "question": "어떤 레퍼런스 이미지가 있나요?",
        "header": "레퍼런스",
        "options": [
            {"label": "모두 있음", "description": "포즈, 표정, 배경 이미지 모두 제공"},
            {"label": "포즈만", "description": "포즈 레퍼런스만 제공"},
            {"label": "포즈+배경", "description": "포즈와 배경 이미지 제공"},
            {"label": "없음", "description": "레퍼런스 없이 텍스트로 지정"}
        ],
        "multiSelect": false
    }]
}
```

---

### Step 4: 비율 선택

```python
{
    "questions": [{
        "question": "이미지 비율을 선택해주세요",
        "header": "비율",
        "options": [
            {"label": "9:16 (권장)", "description": "스토리/릴스용 세로"},
            {"label": "3:4", "description": "세로 화보"},
            {"label": "4:5", "description": "인스타 피드"},
            {"label": "1:1", "description": "정사각형"}
        ],
        "multiSelect": false
    }]
}
```

---

### Step 5: 수량 선택

```python
{
    "questions": [{
        "question": "몇 장 생성할까요?",
        "header": "수량",
        "options": [
            {"label": "3장 (권장)", "description": "570원 (190원 x 3)"},
            {"label": "1장", "description": "190원 - 테스트용"},
            {"label": "5장", "description": "950원"},
            {"label": "10장", "description": "1,900원"}
        ],
        "multiSelect": false
    }]
}
```

---

### Step 6: 화질 선택

```python
{
    "questions": [{
        "question": "화질을 선택해주세요",
        "header": "화질",
        "options": [
            {"label": "2K (권장)", "description": "2048px - SNS/웹용"},
            {"label": "4K", "description": "4096px - 인쇄용 (비용 2배)"}
        ],
        "multiSelect": false
    }]
}
```

---

### Step 7: 최종 확인 및 생성

```
## 생성 설정 확인

| 항목 | 값 |
|------|-----|
| 얼굴 | face.jpg |
| 착장 | outfit1.jpg, outfit2.jpg (2개) |
| 포즈 레퍼런스 | pose.jpg |
| 표정 레퍼런스 | expression.jpg |
| 배경 레퍼런스 | background.jpg |
| 비율 | 3:4 |
| 수량 | 10장 |
| 화질 | 2K |
| 예상 비용 | 1,900원 |

이대로 생성할까요?
```

**확인 후 생성 시작**

---

### 워크플로 요약

```
1. 얼굴 이미지 → 경로 입력받기
2. 착장 이미지 → 경로 입력받기
3. 레퍼런스 이미지 → 포즈/표정/배경 (선택)
4. 비율 선택 → AskUserQuestion
5. 수량 선택 → AskUserQuestion
6. 화질 선택 → AskUserQuestion
7. 최종 확인 → 설정 표 보여주고 확인
8. 생성 실행 → 진행률 표시
9. 결과 출력 → 저장 경로 안내
```

---

## 모듈 인터페이스 (v2.0)

### 1. VLM 포즈 분석 (CRITICAL)

```python
from core.ai_influencer import analyze_pose, PoseAnalysisResult

# 포즈 이미지 분석
pose_result = analyze_pose(client, pose_image_path)

# 분석 결과 필드
pose_result.stance           # stand, sit, lean_wall, walk 등
pose_result.framing          # FS(전신), WS(넓은샷), MS(미디엄), CU(클로즈업)
pose_result.camera_angle     # 정면, 3/4측면, 측면, 약간측면
pose_result.camera_height    # 아이레벨, 로앵글, 하이앵글
pose_result.left_arm         # "팔꿈치를 굽혀 무릎 위에 올림"
pose_result.right_arm        # "아래로 뻗어 발목 부근에 위치"
pose_result.left_leg         # "무릎을 깊게 구부려 세우고 발바닥을 지면에 붙임"
pose_result.right_leg        # "무릎을 구부려 세우고 발바닥을 지면에 붙임"
pose_result.left_knee_direction   # 안쪽으로 모임, 바깥쪽으로 벌어짐, 정면
pose_result.right_knee_direction  # 안쪽으로 모임, 바깥쪽으로 벌어짐, 정면
pose_result.torso_tilt       # "왼쪽으로 약 10도 기울어짐"
pose_result.shoulder_line    # "왼쪽 어깨가 오른쪽보다 높음"
```

#### 무릎 방향 중요성

| 무릎 방향 | 설명 | 다리 형태 |
|----------|------|----------|
| 안쪽으로 모임 | 양 무릎이 서로 가까워짐 | X자 다리 |
| 바깥쪽으로 벌어짐 | 양 무릎이 서로 멀어짐 | O자 다리 |
| 정면 | 무릎이 앞을 향함 | 일반 자세 |

### 2. 캐릭터 관리

```python
from core.ai_influencer import load_character, list_characters, Character

characters = list_characters()  # ["luna", ...]
character = load_character("luna")
# character.name, character.face_images, character.profile
```

### 2. 프리셋 로드

```python
from core.ai_influencer import load_preset, list_presets, get_preset_categories

# 프리셋 카테고리
categories = get_preset_categories()  # ["pose", "expression", "background"]

# 프리셋 목록
poses = list_presets("pose")  # ["전신_01", "전신_02", ...]

# 프리셋 로드 (이미지 경로 반환)
pose_img = load_preset("pose", "전신_05")
```

### 3. 이미지 생성 (Full Pipeline - CORRECT)

```python
# tests/influencer/test_reference_cases.py의 파이프라인 사용
from tests.influencer.test_reference_cases import (
    analyze_hair,
    analyze_expression,
    build_schema_prompt,
    generate_image,
)
from core.ai_influencer import analyze_pose, analyze_background, check_compatibility
from core.outfit_analyzer import OutfitAnalyzer

# STEP 1: VLM 분석 (6단계)
hair_info = analyze_hair(client, face_image)
expression_info = analyze_expression(client, expression_image)
pose_result = analyze_pose(pose_image)
background_result = analyze_background(background_image)
compatibility = check_compatibility(pose_result, background_result)
outfit_result = OutfitAnalyzer(client).analyze(outfit_images)

# STEP 2: 스키마 프롬프트 조립
prompt = build_schema_prompt(
    hair_info, expression_info, pose_result,
    background_result, outfit_result, compatibility,
)

# STEP 3: 생성 (모든 레퍼런스 이미지 포함)
image = generate_image(
    client=client,
    prompt=prompt,
    face_images=face_images,
    outfit_images=outfit_images,
    pose_image=pose_image,
    expression_image=expression_image,
    background_image=background_image,
    temperature=0.35,
)
```

### 4. generate_ai_influencer() - LOW-LEVEL (직접 호출 금지!)

```python
# WARNING: 이 함수는 VLM 분석을 건너뛰는 저수준 함수!
# 포즈 프레이밍/앵글/관절 상세가 누락되어 품질 저하 발생
# 반드시 위 Full Pipeline을 사용할 것!
from core.ai_influencer import generate_ai_influencer  # DO NOT USE DIRECTLY
```

---

## 검증 기준 (얼굴 동일성 강화)

| 항목 | 비중 | 설명 |
|------|------|------|
| **face_consistency** | **40%** | 캐릭터 얼굴과 동일한가 |
| realism | 25% | 실제 사진처럼 보이는가 |
| scenario_fit | 15% | 장소/상황이 자연스러운가 |
| skin_condition | 10% | 피부 질감이 자연스러운가 |
| anti_polish_factor | 10% | 너무 완벽하지 않은가 |

### Auto-Fail 조건

- **얼굴 다른 사람** (가장 중요!)
- 손가락 6개+ / 기형적 손가락
- AI 특유 플라스틱 피부

---

## 출력

```
Fnf_studio_outputs/ai_influencer/{캐릭터명}_{타임스탬프}/
├── images/
│   ├── input_face_01.jpg
│   ├── input_face_02.jpg
│   ├── input_face_03.jpg
│   ├── input_pose_ref.jpg        # 포즈 레퍼런스
│   ├── input_expression_ref.jpg  # 표정 레퍼런스 (별도면)
│   ├── input_outfit_01.jpg
│   ├── input_background_ref.jpg  # 배경 레퍼런스
│   └── output_001.jpg
├── prompt.json         <- 사용된 프롬프트 (역할 설명)
├── prompt.txt          <- 가독용
├── config.json
└── validation.json
```

---

## 사용법

CLI:
```
/AI인플루언서
```

Claude가 캐릭터 확인 → 프리셋 선택 → 이미지 조합 → 생성 → 검증

---

## 에러 핸들링

| 에러 | 복구 |
|------|------|
| 캐릭터 없음 | 등록 안내 |
| 프리셋 ID 없음 | 유효한 ID 안내 |
| 프리셋 이미지 없음 | 이미지 경로 확인 안내 |
| 얼굴 불일치 | Temperature 낮추고 재생성 |

---

## AskUserQuestion 예시

### 포즈 프리셋 선택

```python
{
    "question": "어떤 포즈 프리셋을 원하세요?",
    "header": "포즈",
    "options": [
        {"label": "전신 (권장)", "description": "전신_01~21: 걷기, 기대기, S라인 등"},
        {"label": "상반신", "description": "상반신_01~21: 팔올리기, 소품 들기 등"},
        {"label": "앉기", "description": "앉기_01~21: 쪼그려, 계단, 바닥 등"},
        {"label": "커스텀 이미지", "description": "직접 포즈 레퍼런스 이미지 제공"}
    ],
    "multiSelect": false
}
```

### 표정 프리셋 선택

```python
{
    "question": "어떤 표정을 원하세요?",
    "header": "표정",
    "options": [
        {"label": "시크 (권장)", "description": "시크_01~05: 쿨하고 도도한 무드"},
        {"label": "러블리", "description": "러블리_01~05: 사랑스럽고 부드러운 무드"},
        {"label": "포즈와 동일", "description": "포즈 레퍼런스의 표정 그대로 사용"},
        {"label": "커스텀 이미지", "description": "직접 표정 레퍼런스 이미지 제공"}
    ],
    "multiSelect": false
}
```

### 배경 프리셋 선택

```python
{
    "question": "어떤 배경을 원하세요?",
    "header": "배경",
    "options": [
        {"label": "핫플카페 (권장)", "description": "유럽풍, 모던, 레트로 카페"},
        {"label": "그래피티", "description": "스트릿 아트, 힙한 느낌"},
        {"label": "해외스트릿", "description": "홍콩, 파리, 뉴욕 등"},
        {"label": "커스텀 이미지", "description": "직접 배경 레퍼런스 이미지 제공"}
    ],
    "multiSelect": false
}
```

### 수량/화질 선택

```python
{
    "question": "수량과 화질을 선택하세요",
    "header": "출력설정",
    "options": [
        {"label": "3장 2K (권장)", "description": "9:16, 2K 해상도, 570원"},
        {"label": "5장 2K", "description": "9:16, 2K 해상도, 950원"},
        {"label": "3장 4K", "description": "9:16, 4K 고화질, 1,140원"},
        {"label": "1장 테스트", "description": "9:16, 2K, 190원"}
    ],
    "multiSelect": false
}
```

---

## 프롬프트 최적화 원칙 (CRITICAL)

### 정보 과부하 방지

**문제**: VLM 분석 결과를 모두 프롬프트에 넣으면 오히려 품질 저하

```
❌ 금지: 무릎 정밀 분석 섹션 별도 추가
- 무릎_각도: 약 45도
- 무릎_높이: 가슴 높이
- 무릎_방향: 바깥쪽
→ 기존 다리 설명과 중복 → 모델 혼란 → 팔 3개, 포즈 엉망

✅ 권장: 다리 설명에 정보 통합
- 왼다리: 무릎을 깊게 구부려 세우고 발바닥을 지면에 붙임, 무릎이 바깥쪽으로 살짝 벌어짐
→ 한 문장에 통합 → 모델이 이해하기 쉬움
```

### 프롬프트 길이 가이드라인

| 상태 | 줄 수 | 결과 |
|------|-------|------|
| 적정 | 100~140줄 | 안정적 |
| 주의 | 140~160줄 | 품질 저하 가능 |
| 위험 | 160줄+ | 기형/오류 확률 증가 |

### 중복 제거 원칙

1. **같은 정보는 한 곳에만** - 다리 각도를 2군데에 쓰지 말 것
2. **보조 설명보다 이미지 레퍼런스** - 텍스트 줄이고 이미지에 의존
3. **CRITICAL 표시 남발 금지** - 모두 중요하면 아무것도 중요하지 않음

---

## 필수 파이프라인 (CRITICAL)

**이미지 생성 시 반드시 아래 8단계를 모두 거쳐야 한다. 하나라도 빠뜨리면 품질 저하!**

```
1. analyze_hair()        -- 얼굴 이미지에서 헤어 스타일/컬러/질감 추출
2. analyze_expression()  -- 표정 이미지에서 베이스/바이브/시선/입 추출
3. analyze_pose()        -- 포즈 이미지에서 stance/framing/앵글/각 관절 추출
4. analyze_background()  -- 배경 이미지에서 장소/조명/시간대/분위기 추출
5. check_compatibility() -- 포즈-배경 호환성 검사 (앉기↔의자 등)
6. OutfitAnalyzer.analyze() -- 착장 이미지에서 아이템/색상/로고/핏 상세 분석
7. build_schema_prompt() -- 위 분석 결과를 한국어 스키마 프롬프트로 조립
8. generate_image()      -- 프롬프트 + 모든 이미지 레퍼런스 → API 호출
```

### WARNING: generate_ai_influencer()를 직접 호출하지 마라!

```python
# FORBIDDEN - VLM 분석을 건너뛰고 generic label만 사용
from core.ai_influencer import generate_ai_influencer
image = generate_ai_influencer(character=..., pose_image=..., ...)
# -> 포즈 프레이밍 무시, 전신/상반신 구분 불가, 배경 분위기 누락

# CORRECT - 반드시 tests/influencer/test_reference_cases.py의 파이프라인 사용
# analyze_hair → analyze_expression → analyze_pose → analyze_background
# → check_compatibility → OutfitAnalyzer → build_schema_prompt → generate_image
```

`generate_ai_influencer()`는 내부적으로 `_build_simple_prompt()`를 호출하는데,
이 함수는 "[POSE REFERENCE] Copy EXACT pose" 같은 단순 라벨만 생성한다.
VLM 포즈 분석(프레이밍, 앵글, 관절 상세)이 전혀 포함되지 않아
상반신 포즈를 전신으로 생성하는 등 프레이밍 오류가 발생한다.

### 테스트 실행

```bash
python tests/influencer/test_reference_cases.py --test-dir tests/인플테스트3 --num-images 5
```

모든 레퍼런스 이미지(포즈+표정+배경)를 항상 포함하여 생성한다.

---

**버전**: 2.2.0
**작성일**: 2026-02-26
**방식**: 이미지 레퍼런스 기반 (텍스트 최소화)
**변경사항**:
- v2.2.0: 대화형 워크플로 개선 (단계별 질문 방식)
- v2.1.0: VLM 포즈 분석 모듈 추가, 프롬프트 최적화 원칙 추가
