---
name: 일상컷_daily-casual
description: 일상 캐주얼 사진 생성 워크플로. 타인 촬영/타이머 촬영의 자연스러운 일상 사진. 폰/디카 촬영 → 브랜드 DNA 병합 → 프롬프트 조립 → 이미지 생성 → 검증.
user-invocable: true
argument-hint: [브랜드명] [상황] [수량] (예: MLB 카페 일상 3장, Discovery 스트릿 걸어가는 2장)
---

# 일상컷 - 캐주얼 데일리 사진 생성 워크플로

> **범용 레퍼런스**: Gemini API, 프롬프트 패턴, 유틸리티 함수 등
> 워크플로에 종속되지 않는 기초 지식은 `이미지생성_레퍼런스_image-gen-reference/SKILL.md` 참조

> **템플릿 파일**: `prompt-templates/daily_casual.json`

## 컨셉

셀피(본인 촬영)가 아닌, **다른 사람이 찍어주거나 타이머/거치대로 촬영한 캐주얼 일상 사진**.
브랜드컷(에디토리얼)과 셀피의 중간 지점으로, 자연스럽고 꾸미지 않은 느낌이 핵심.

### 셀피 vs 일상컷 차이

| 항목 | 셀피 | 일상컷 |
|------|------|--------|
| 촬영자 | 본인 (팔 뻗기) | 타인 또는 타이머 |
| 프레이밍 | 얼굴 클로즈업~상반신 | 상반신~전신 다양 |
| 앵글 | 높은 각도 (셀카 앵글) | eye-level 또는 다양한 각도 |
| 렌즈 왜곡 | 강한 wide-angle | 보통 수준 |
| 포즈 | 셀카 포즈 | 자연스러운 일상 동작 |
| 배경 | 보케 처리 | 배경 인식 가능 |

## 사용법

```
/일상컷_daily-casual MLB 카페에서 앉아있는 사진 3장
/일상컷_daily-casual Discovery 거리 걸어가는 스트릿 컷 2장
/일상컷_daily-casual Banillaco 골든아워 공원 산책 4장
/일상컷_daily-casual 남친짤 느낌 데이트룩 카페 2장
```

### Python 워크플로 (API 연동용)

```python
from workflow import ImageGenerationWorkflow

workflow = ImageGenerationWorkflow(api_key="YOUR_API_KEY")

result = workflow.generate(
    user_input="MLB 카페에서 앉아있는 사진 3장",
    template="daily_casual",        # 일상컷 템플릿
    model_images=[face_pil],         # 얼굴 유지용
    outfit_images=[outfit_pil],      # 착장 반영용
    input_vars={
        "gender": "여성",
        "age": "20대 초반",
        "shot_type": "sitting_candid",  # AI가 자동 선택 또는 지정
        "location": "카페 내부",
        "lighting": "indoor_ambient"
    },
    count=3,
    max_workers=4
)
```

---

# 파이프라인 (5단계)

```
사용자 입력 → Step 1: 브랜드 라우팅 + 템플릿 로드
            → Step 2: AI 판단 (shot_type, pose, lighting 자동 선택)
            → Step 3: 프롬프트 조립
            → Step 4: 이미지 생성 (Gemini 3 Pro, 2K)
            → Step 5: 검증 + 결과 반환
```

---

## Step 1: 브랜드 라우팅 + 템플릿 로드

사용자 요청에서 브랜드를 감지하고, `daily_casual.json` 템플릿과 해당 brand DNA를 로드합니다.

| 키워드 | 브랜드 | DNA 파일 |
|--------|--------|----------|
| MLB, 엠엘비 | MLB Marketing | `mlb-marketing.json` |
| Discovery, 디스커버리 | Discovery | `discovery.json` |
| Duvetica, 두베티카 | Duvetica | `duvetica.json` |
| Banillaco, 바닐라코, 뷰티 | Banillaco | `banillaco.json` |
| SergioTacchini, 세르지오 | Sergio Tacchini | `sergio-tacchini.json` |

## Step 2: AI 판단 (자동 선택)

`daily_casual.json`의 `_ai_guide`에 따라 사용자 요청에서 키워드를 파악하고 최적 조합을 선택합니다.

### Shot Type 자동 매칭

| 사용자 키워드 | → shot_type |
|---------------|-------------|
| "친구가 찍어준", "스냅" | `friend_snap` |
| "남친짤", "여친짤", "데이트" | `boyfriend_shot` |
| "걸어가는", "거리", "스트릿" | `walking_candid` |
| "카페", "앉아있는", "벤치" | `sitting_candid` |
| "OOTD", "전신", "코디" | `timer_shot` |
| "뒷모습", "감성", "풍경" | `over_shoulder` |

### Pose 자동 매칭

| 사용자 키워드 | → pose_type |
|---------------|-------------|
| "서있는", "기본" | `natural_stand` |
| "걷는", "걸어가는" | `walking` |
| "기대", "벽", "쿨한" | `leaning` |
| "앉아", "카페" | `sitting_casual` |
| "캔디드", "자연스러운" | `looking_away` |
| "웃는", "밝은" | `laughing` |

### Lighting 자동 매칭

| 사용자 키워드 | → lighting |
|---------------|------------|
| "야외", "맑은 날" | `outdoor_daylight` |
| "석양", "노을", "감성" | `golden_hour` |
| "흐린", "부드러운" | `overcast` |
| "카페", "실내" | `indoor_ambient` |
| "밤", "네온" | `night_street` |

## Step 3: 프롬프트 조립

선택된 shot_type, pose, lighting과 brand DNA를 병합하여 Gemini API 프롬프트를 조립합니다.

### 프롬프트 구조
```
[shooting_style] + [device] + [subject 정보] + [attire/brand] +
[pose prompt_fragment] + [shot_type 특성] + [lighting setup] +
[environment] + [technical specs] + [brand_injection]
```

### 예시 조립 결과
```
candid daily life photo, taken by friend or timer, iPhone 15 Pro 24mm f/1.9,
young Korean woman, early 20s, realistic skin texture natural pores,
wearing MLB casual everyday style, sitting casually on cafe chair legs crossed,
friend at eye-level 1-2 meters distance, mixed window light and indoor ambient,
cafe interior warm atmosphere, 2K resolution, smartphone natural bokeh,
in the style of MLB Marketing
```

## Step 4: 이미지 생성

```python
# Gemini API 호출
config = types.GenerateContentConfig(
    temperature=0.3,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="4:5",   # 일상컷 기본 (9:16도 가능)
        image_size="2K"
    )
)
```

| 설정 | 값 | 비고 |
|------|-----|------|
| 모델 | `gemini-3-pro-image-preview` | 필수 |
| temperature | 0.3 | 자연스러움 확보 |
| 비율 | 4:5 (기본) / 9:16 (세로) / 3:4 | 사용자 지정 가능 |
| 해상도 | 2K | 프로덕션 품질 |

## Step 5: 검증

생성된 이미지의 품질을 VLM으로 검증합니다.

### 일상컷 전용 검증 기준

| 기준 | 가중치 | 설명 |
|------|--------|------|
| 자연스러움 | 30% | 포즈, 표정이 자연스러운가? 모델 느낌이 아닌가? |
| 인물 보존 | 25% | 얼굴/체형이 원본과 일치하는가? |
| 카메라 리얼리즘 | 20% | 실제 폰/디카로 찍은 것처럼 보이는가? |
| 착장 반영 | 15% | 의상이 정확히 반영되었는가? |
| 배경 적합성 | 10% | 요청한 장소/분위기와 맞는가? |

### 실패 시 자동 재시도
- 자연스러움 < 80: 포즈/표정 프롬프트 보강
- 카메라 리얼리즘 < 80: 폰 카메라 특성 프롬프트 강화
- temperature 하향: 0.3 → 0.2 → 0.15
