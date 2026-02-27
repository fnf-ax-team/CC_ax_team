# 셀카/인플루언서 프롬프트 치트시트

> v3.0.0 | 최종 업데이트: 2026-02-20
>
> VLM 분석 기반 (표정 10장 + 포즈 75장 + 배경 96장 + 스타일링 12장 = 총 193장)
>
> 인플루언서/셀럽 스타일 이미지 생성용 통합 가이드

---

## 핵심 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│  참조 이미지 필수! 배경/스타일링 프리셋 이미지가 있어야 퀄리티 UP │
└─────────────────────────────────────────────────────────────────┘
```

**왜 참조 이미지가 중요한가?**
- 텍스트만으로는 분위기/톤 전달 한계
- 배경, 스타일링, 포즈 프리셋 이미지를 함께 전송해야 퀄리티 상승
- **프리셋 이미지 = API에 직접 전달**

**프롬프트 구조:**

```
이 얼굴로 [예쁜 여자/잘생긴 남자]
{pose_preset}      ← 프리셋 이미지 전송
{background_preset} ← 프리셋 이미지 전송
{expression}
```

> 성별은 참조 이미지에서 자동 인식됨 - 별도 명시 불필요
> 한국어로 짧고 심플하게 - 영어 프롬프트 엔지니어링 금지

---

## 목차

1. [프리셋 이미지 경로](#프리셋-이미지-경로)
2. [표정 카테고리](#1-표정-카테고리-2개-10장)
3. [포즈 카테고리](#2-포즈-카테고리-4개-75장)
4. [배경 카테고리](#3-배경-카테고리-9개-96장)
5. [스타일링 카테고리](#4-스타일링-카테고리-2개-12장)
6. [JSON 프롬프트 스키마](#json-프롬프트-스키마)
7. [호환 규칙](#호환-규칙)
8. [금지 조합](#금지-조합)
9. [검증 기준](#검증-기준)
10. [AskUserQuestion 예시](#askuserquestion-예시)
11. [랜덤 선택 로직](#랜덤-선택-로직)

---

## 프리셋 이미지 경로

**기본 경로**: `OneDrive_2026-02-19 (2)/`


| 카테고리 | 폴더         | 프리셋 수 |
| ---- | ---------- | ----- |
| 표정   | `2. 표정/`   | 10장   |
| 포즈   | `3. 포즈/`   | 75장   |
| 배경   | `4. 배경/`   | 96장   |
| 스타일링 | `5. 스타일링/` | 12장   |


---

## 1. 표정 카테고리 (2개, 10장)

### 1.1 시크 (chic) - 5장


| ID        | 파일명         | 키워드         |
| --------- | ----------- | ----------- |
| `chic_01` | 시크 (1).png  | 시크, 무표정, 도도 |
| `chic_02` | 시크 (2).jpeg | 쿨, 당당, 시선   |
| `chic_03` | 시크 (3).png  | 세련됨, 카리스마   |
| `chic_04` | 시크 (4).png  | 고급스러움, 차가움  |
| `chic_05` | 시크 (5).jpeg | 미스터리, 시크    |


**프롬프트 키워드:**

```
시크한 무표정, 도도한 눈빛, 당당한 시선, 쿨한 분위기
```

### 1.2 러블리 (lovely) - 5장


| ID          | 파일명         | 키워드        |
| ----------- | ----------- | ---------- |
| `lovely_01` | 러블리 (1).png | 사랑스러움, 미소  |
| `lovely_02` | 러블리 (2).png | 귀여움, 밝음    |
| `lovely_03` | 러블리 (3).png | 청순함, 자연스러움 |
| `lovely_04` | 러블리 (4).png | 부드러움, 따뜻함  |
| `lovely_05` | 러블리 (5).png | 발랄함, 에너지   |


**프롬프트 키워드:**

```
자연스러운 미소, 밝고 사랑스러운 표정, 청순한 눈빛, 부드러운 분위기
```

### 1.3 자연스러움 (natural) - 5장


| ID           | 파일명          | 키워드        |
| ------------ | ------------ | ---------- |
| `natural_01` | 자연스러움 (1).png | 편안함, 일상    |
| `natural_02` | 자연스러움 (2).png | 힘 뺀, 무심    |
| `natural_03` | 자연스러움 (3).png | 나른함, 여유    |
| `natural_04` | 자연스러움 (4).png | 자연스러운 미소   |
| `natural_05` | 자연스러움 (5).png | 릴렉스, 캐주얼   |


**프롬프트 키워드:**

```
편안한 표정, 힘 뺀 자연스러운 느낌, 일상적인 분위기, 나른한 눈빛
```

### 1.4 도발적 (provocative) - 5장


| ID               | 파일명         | 키워드       |
| ---------------- | ----------- | --------- |
| `provocative_01` | 도발적 (1).png | 끼부림, 섹시   |
| `provocative_02` | 도발적 (2).png | 몽환적, 나른   |
| `provocative_03` | 도발적 (3).png | 유혹적, 시선   |
| `provocative_04` | 도발적 (4).png | 도발, 자신감   |
| `provocative_05` | 도발적 (5).png | 섹시, 당당    |


**프롬프트 키워드:**

```
끼부리는 표정, 몽환적인 눈빛, 도발적인 시선, 섹시한 분위기
```

---

## 2. 포즈 카테고리 (4개, 75장)

### 2.1 전신 (fullbody) - 21장


| ID                            | 파일명                       | 추천 배경           |
| ----------------------------- | ------------------------- | --------------- |
| `fullbody_01` ~ `fullbody_21` | 전신 (1).jpeg ~ 전신 (21).png | 스트릿, 그래피티, 횡단보도 |


**특징:** 다리 길어 보이는 로우앵글, 역동적 포즈, 걷기/기대기/S라인

**프롬프트 키워드:**

```
전신 포즈, 로우앵글, 다리 길게, 역동적, 걷는 포즈, 벽에 기대기, S라인 강조
```

### 2.2 상반신 (upperbody) - 21장


| ID                              | 파일명                         | 추천 배경         |
| ------------------------------- | --------------------------- | ------------- |
| `upperbody_01` ~ `upperbody_21` | 상반신 (1).png ~ 상반신 (21).jpeg | 카페, 문, 라이프스타일 |


**특징:** 얼굴 가까이, 팔/손 포즈, 소품 활용

**프롬프트 키워드:**

```
상반신, 허리 위로, 팔 올리기, 머리 만지기, 소품 들기, 얼굴 가까이
```

### 2.3 앉아있는 (sitting) - 21장


| ID                          | 파일명                          | 추천 배경       |
| --------------------------- | ---------------------------- | ----------- |
| `sitting_01` ~ `sitting_21` | 앉아있는 (1).png ~ 앉아있는 (21).png | 카페, 계단, 스트릿 |


**특징:** 쪼그려 앉기, 계단, 바닥, 벤치

**프롬프트 키워드:**

```
앉은 포즈, 쪼그려 앉기, 계단에 앉기, 다리 뻗기, 턱 괴기, 나른한 자세
```

### 2.4 거울셀피 (mirror) - 12장


| ID                        | 파일명                           | 추천 배경     |
| ------------------------- | ----------------------------- | --------- |
| `mirror_01` ~ `mirror_12` | 거울셀피 (1).png ~ 거울셀피 (12).jpeg | 엘리베이터, 실내 |


**특징:** 거울 앞 셀카, 플래시, 인플루언서 스타일

**프롬프트 키워드:**

```
거울샷, 폰 셀카, 플래시, 전신 거울, 피팅룸, 머리 만지기, S라인
```

---

## 3. 배경 카테고리 (9개, 96장)

### 3.1 핫플카페 (cafe) - 21장


| ID                    | 파일명                             |
| --------------------- | ------------------------------- |
| `cafe_01` ~ `cafe_21` | 핫플 카페 (1).jpeg ~ 핫플 카페 (21).png |


**스타일:** 유럽풍 노천카페, 모던 브루어리, 레트로 다이너, 미니멀 화이트

**프롬프트 키워드:**

```
유럽풍 카페, 빈티지 테라스, 라탄 의자, 대리석 테이블, 타일 외벽
모던 카페, 금속 간판, 통유리창, 인더스트리얼
레트로 다이너, 80년대 빈티지, 컬러풀 포스터
```

### 3.2 그래피티 (graffiti) - 15장


| ID                            | 파일명                          |
| ----------------------------- | ---------------------------- |
| `graffiti_01` ~ `graffiti_15` | 그래피티 (1).png ~ 그래피티 (15).png |


**스타일:** 캐릭터 그래피티, 스프레이 아트, 태깅, 스티커

**프롬프트 키워드:**

```
그래피티 벽, 스프레이 아트, 캐릭터 그림, 태깅
컬러풀한 벽화, 스트릿 아트, 언더그라운드
콘크리트 벽, 철문에 그래피티
```

### 3.3 철문 (shutter) - 10장


| ID                          | 파일명                       |
| --------------------------- | ------------------------- |
| `shutter_01` ~ `shutter_10` | 철문 (1).jpeg ~ 철문 (10).png |


**스타일:** 금속 셔터, 수평 슬랫, 산업적 분위기

**프롬프트 키워드:**

```
금속 셔터, 가로 줄무늬, 회색 철문
인더스트리얼, 미니멀, 산업적 분위기
콘크리트 바닥, 무채색 톤
```

### 3.4 기타 문 (door) - 10장


| ID                    | 파일명                           |
| --------------------- | ----------------------------- |
| `door_01` ~ `door_10` | 기타 문 (1).png ~ 기타 문 (10).jpeg |


**스타일:** 유럽 빈티지 문, 컬러 대문, 클래식 스타일

**프롬프트 키워드:**

```
빈티지 나무 문, 유럽풍 대문, 석조 벽면
클래식 블루 문, 레드 문, 아이보리 벽
숫자 표지판, 오래된 문틀
```

### 3.5 해외스트릿 (street) - 10장


| ID                        | 파일명                               |
| ------------------------- | --------------------------------- |
| `street_01` ~ `street_10` | 해외 스트릿 (1).jpeg ~ 해외 스트릿 (10).png |


**스타일:** 홍콩, 파리, 런던, 뉴욕 거리 느낌

**프롬프트 키워드:**

```
유럽 거리, 파리 골목, 뉴욕 스트릿
빈티지 간판, 카페 테라스, 자전거
이국적인 도시 풍경, 보도블록
```

### 3.6 힙라이프스타일 (lifestyle) - 10장


| ID                              | 파일명                               |
| ------------------------------- | --------------------------------- |
| `lifestyle_01` ~ `lifestyle_10` | 힙 스트릿 라이프 스타일 (1).png ~ (10).jpeg |


**스타일:** 아트 북숍, 편의점, 레코드샵, 비디오샵

**프롬프트 키워드:**

```
아트 북숍, 잡지 진열대, 서점 내부
편의점, 일본풍, 형광등 조명
LP샵, 빈티지 레코드, 90년대 감성
```

### 3.7 지하철 (subway) - 10장


| ID                        | 파일명                         |
| ------------------------- | --------------------------- |
| `subway_01` ~ `subway_10` | 지하철 (1).jpeg ~ 지하철 (10).png |


**스타일:** 지하철 통로, 계단, 객차 내부, 플랫폼

**프롬프트 키워드:**

```
지하철 통로, 타일 벽면, 형광등
금속 핸드레일, 노란 점자블록
지하철 내부, 손잡이, 좌석
```

### 3.8 엘리베이터 (elevator) - 5장


| ID                            | 파일명                             |
| ----------------------------- | ------------------------------- |
| `elevator_01` ~ `elevator_05` | 엘리베이터 (1).jpeg ~ 엘리베이터 (5).jpeg |


**스타일:** 금속 엘리베이터 거울, 미니멀

**프롬프트 키워드:**

```
엘리베이터 내부, 금속 벽면, 전신 거울
LED 조명, 버튼 패널, 미니멀 공간
```

### 3.9 횡단보도 (crosswalk) - 5장


| ID                              | 파일명                          |
| ------------------------------- | ---------------------------- |
| `crosswalk_01` ~ `crosswalk_05` | 횡단보도 (1).jpeg ~ 횡단보도 (5).png |


**스타일:** 유럽풍 교차로, 도시 횡단보도

**프롬프트 키워드:**

```
횡단보도, 교차로, 신호등
유럽풍 건물, 도시 거리
보도블록, 자연광
```

### 3.10 집 침실 (bedroom) - 5장


| ID                          | 파일명                         |
| --------------------------- | --------------------------- |
| `bedroom_01` ~ `bedroom_05` | 집 침실 (1).png ~ 집 침실 (5).png |


**스타일:** 자연광 침실, 거울샷, 일상적 분위기

**프롬프트 키워드:**

```
침실, 자연광, 거울, 침대
일상적 분위기, 편안한 공간
아늑한 인테리어, 쿠션, 이불
```

---

## 4. 스타일링 카테고리 (2개, 12장)

### 4.1 SPRING (1-3월) - 6장


| ID                        | 파일명                               | 시즌       |
| ------------------------- | --------------------------------- | -------- |
| `spring_01` ~ `spring_06` | SPRING (1).jpeg ~ SPRING (6).jpeg | 봄 (1-3월) |


**특징:** 봄 시즌 스타일링

**프롬프트 키워드:**

```
봄 스타일링, 레이어링, 청순한 느낌
```

### 4.2 SUMMER (4-6월) - 6장


| ID                        | 파일명                             | 시즌        |
| ------------------------- | ------------------------------- | --------- |
| `summer_01` ~ `summer_06` | SUMMER (1).png ~ SUMMER (6).jpg | 여름 (4-6월) |


**특징:** 여름 시즌 스타일링, 가벼운 소재, 시원한 컬러

**프롬프트 키워드:**

```
여름 스타일링, 반팔, 민소매
```

---

## JSON 프롬프트 스키마

### 기본 스키마

```json
{
  "워크플로": "selfie",
  "버전": "3.0.0",

  "표정": {
    "카테고리": "",        // [필수] "chic" | "lovely"
    "프리셋_id": "",       // [선택] chic_01 ~ chic_05, lovely_01 ~ lovely_05
    "커스텀": ""           // [선택] 프리셋 대신 직접 입력
  },

  "포즈": {
    "카테고리": "",        // [필수] "fullbody" | "upperbody" | "sitting" | "mirror"
    "프리셋_id": "",       // [선택] fullbody_01 ~ fullbody_21 등
    "커스텀": ""           // [선택] 프리셋 대신 직접 입력
  },

  "배경": {
    "카테고리": "",        // [필수] "cafe" | "graffiti" | "shutter" | "door" | "street" | "lifestyle" | "subway" | "elevator" | "crosswalk"
    "프리셋_id": "",       // [선택] cafe_01 ~ cafe_21 등
    "커스텀": ""           // [선택] 프리셋 대신 직접 입력
  },

  "스타일링": {
    "시즌": "",            // [선택] "spring" | "summer"
    "프리셋_id": "",       // [선택] spring_01 ~ spring_06 등
    "커스텀": ""           // [선택] 직접 의상 설명
  },

  "촬영": {
    "프레이밍": "",        // [필수] "얼빡" | "상반신" | "전신"
    "앵글": "",            // [선택] "로우앵글" | "아이레벨" | "하이앵글"
    "조명": ""             // [선택] "자연광" | "플래시" | "형광등" | "무드등"
  },

  "수량": 1,               // [필수] 1, 3, 5, 10
  "비율": "9:16",          // [필수] 기본값 9:16 (스토리/릴스)
  "해상도": "2K",          // [필수] "1K" | "2K" | "4K"

  "네거티브": "AI look, plastic skin, overprocessed, golden hour warm cast"
}
```

### 예시: 시크한 전신 그래피티 배경

```json
{
  "워크플로": "selfie",
  "버전": "3.0.0",

  "표정": {
    "카테고리": "chic",
    "프리셋_id": "chic_03"
  },

  "포즈": {
    "카테고리": "fullbody",
    "프리셋_id": "fullbody_05"
  },

  "배경": {
    "카테고리": "graffiti",
    "프리셋_id": "graffiti_07"
  },

  "스타일링": {
    "시즌": "summer",
    "프리셋_id": "summer_02"
  },

  "촬영": {
    "프레이밍": "전신",
    "앵글": "로우앵글",
    "조명": "자연광"
  },

  "수량": 3,
  "비율": "9:16",
  "해상도": "2K",

  "네거티브": "AI look, plastic skin, overprocessed, golden hour warm cast"
}
```

---

## 호환 규칙

### 포즈 ↔ 배경 권장 조합


| 포즈 카테고리         | 추천 배경                 | 비추천 배경        |
| --------------- | --------------------- | ------------- |
| 전신 (fullbody)   | 그래피티, 해외스트릿, 횡단보도, 철문 | 엘리베이터 (공간 좁음) |
| 상반신 (upperbody) | 카페, 기타문, 힙라이프         | -             |
| 앉기 (sitting)    | 카페, 계단, 해외스트릿         | 엘리베이터, 횡단보도   |
| 거울셀피 (mirror)   | 엘리베이터, 실내             | 야외 배경 전체      |


### 표정 ↔ 배경 권장 조합


| 표정           | 추천 배경                | 분위기           |
| ------------ | -------------------- | ------------- |
| 시크 (chic)    | 지하철, 그래피티, 철문, 엘리베이터 | 도시적, 힙한, 쿨    |
| 러블리 (lovely) | 카페, 해외스트릿, 힙라이프      | 여유로운, 감성, 따뜻한 |


### 스타일링 ↔ 시즌 권장 조합


| 스타일링   | 추천 포즈   | 추천 배경           |
| ------ | ------- | --------------- |
| SPRING | 전신, 상반신 | 카페, 해외스트릿, 횡단보도 |
| SUMMER | 전신, 상반신 | 그래피티, 해외스트릿, 카페 |


---

## 금지 조합

### 물리적 불가능


| #   | 조합          | 이유         | 대안         |
| --- | ----------- | ---------- | ---------- |
| 1   | 전신 + 얼빡     | 물리적 모순     | 둘 중 하나만    |
| 2   | 거울셀피 + 야외배경 | 거울이 야외에 없음 | 엘리베이터로 변경  |
| 3   | 앉기 + 엘리베이터  | 공간 부적합     | 카페/계단으로 변경 |
| 4   | 앉기 + 횡단보도   | 상황 부자연스러움  | 스트릿/카페로 변경 |


### 분위기 충돌


| #   | 조합           | 이유       | 대안          |
| --- | ------------ | -------- | ----------- |
| 5   | 시크 + 밝은미소    | 표정 컨셉 충돌 | 러블리로 변경     |

> **참고**: 러블리 + 철문/지하철은 금지 조합이 아님. 러블리한 분위기로 다양한 배경 가능.


---

## 네거티브 프롬프트

### 기본 (항상 적용)

```
AI look, plastic skin, overprocessed, golden hour warm cast
```

### 조건부 추가


| 조건         | 추가 네거티브                                            |
| ---------- | -------------------------------------------------- |
| 셀카 스타일     | `professional studio lighting, magazine quality`   |
| UGC 스타일    | `perfect skin, heavily retouched, overly polished` |
| 자연스러움 원할 때 | `posed, staged, artificial, symmetrical`           |


---

## 검증 기준

### UGC/셀피 5개 항목


| 항목       | 영문                  | 비중  | 설명                   |
| -------- | ------------------- | --- | -------------------- |
| 리얼리즘     | realism             | 35% | 실제 사진처럼 보이는가         |
| 인물 보존    | person_preservation | 25% | 얼굴이 참조 이미지와 같은 사람인가  |
| 시나리오 적합성 | scenario_fit        | 20% | 장소/상황/옷이 자연스럽게 어울리는가 |
| 피부 상태    | skin_condition      | 10% | 피부 질감이 자연스러운가        |
| 역검증      | anti_polish_factor  | 10% | 너무 완벽하지 않은가          |


**원칙: "너무 잘 나오면 실패"**

### Auto-Fail 조건

- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람 (참조와 불일치)
- 누런 톤 (golden/amber/warm cast)
- AI 특유 플라스틱 피부
- 의도하지 않은 텍스트/워터마크

---

## AskUserQuestion 예시

```python
questions = [
    {
        "question": "어떤 표정을 원하세요?",
        "header": "표정",
        "options": [
            {"label": "시크/쿨 (권장)", "description": "무표정, 당당, 도도한 느낌 - 5가지"},
            {"label": "러블리", "description": "사랑스러운 미소, 밝은 느낌 - 5가지"}
        ],
        "multiSelect": False
    },
    {
        "question": "어떤 포즈 스타일을 원하세요?",
        "header": "포즈",
        "options": [
            {"label": "전신 (권장)", "description": "걷기, 기대기, S라인 등 - 21가지"},
            {"label": "상반신", "description": "팔올리기, 소품 들기 등 - 21가지"},
            {"label": "앉기", "description": "쪼그려, 계단, 바닥 등 - 21가지"},
            {"label": "거울셀피", "description": "플래시, 자연광 등 - 12가지"}
        ],
        "multiSelect": False
    },
    {
        "question": "어떤 배경을 원하세요?",
        "header": "배경",
        "options": [
            {"label": "그래피티 (권장)", "description": "스트릿 아트, 힙한 느낌 - 15가지"},
            {"label": "핫플카페", "description": "유럽풍, 모던, 레트로 - 21가지"},
            {"label": "해외스트릿", "description": "홍콩, 파리, 뉴욕 등 - 10가지"},
            {"label": "지하철", "description": "통로, 플랫폼 등 - 10가지"}
        ],
        "multiSelect": False
    },
    {
        "question": "어떤 스타일링(의상)을 원하세요?",
        "header": "스타일링",
        "options": [
            {"label": "SPRING (1-3월)", "description": "봄 시즌 스타일링 - 6가지"},
            {"label": "SUMMER (4-6월)", "description": "여름 시즌 스타일링 - 6가지"},
            {"label": "자유", "description": "스타일링 레퍼런스 없이 자유롭게"}
        ],
        "multiSelect": False
    }
]
```

---

## 랜덤 선택 로직

```python
import random
from pathlib import Path

# 프리셋 이미지 기본 경로
PRESET_BASE_PATH = Path("OneDrive_2026-02-19 (2)")

# 카테고리별 프리셋 정의
EXPRESSION_PRESETS = {
    "chic": [f"chic_{i:02d}" for i in range(1, 6)],      # 5개
    "lovely": [f"lovely_{i:02d}" for i in range(1, 6)]   # 5개
}

POSE_PRESETS = {
    "fullbody": [f"fullbody_{i:02d}" for i in range(1, 22)],   # 21개
    "upperbody": [f"upperbody_{i:02d}" for i in range(1, 22)], # 21개
    "sitting": [f"sitting_{i:02d}" for i in range(1, 22)],     # 21개
    "mirror": [f"mirror_{i:02d}" for i in range(1, 13)]        # 12개
}

BACKGROUND_PRESETS = {
    "cafe": [f"cafe_{i:02d}" for i in range(1, 22)],           # 21개
    "graffiti": [f"graffiti_{i:02d}" for i in range(1, 16)],   # 15개
    "shutter": [f"shutter_{i:02d}" for i in range(1, 11)],     # 10개
    "door": [f"door_{i:02d}" for i in range(1, 11)],           # 10개
    "street": [f"street_{i:02d}" for i in range(1, 11)],       # 10개
    "lifestyle": [f"lifestyle_{i:02d}" for i in range(1, 11)], # 10개
    "subway": [f"subway_{i:02d}" for i in range(1, 11)],       # 10개
    "elevator": [f"elevator_{i:02d}" for i in range(1, 6)],    # 5개
    "crosswalk": [f"crosswalk_{i:02d}" for i in range(1, 6)]   # 5개
}

STYLING_PRESETS = {
    "spring": [f"spring_{i:02d}" for i in range(1, 7)],  # 6개
    "summer": [f"summer_{i:02d}" for i in range(1, 7)]   # 6개
}

# 프리셋 ID → 파일 경로 매핑
PRESET_FILE_MAP = {
    # 표정
    "chic": ("2. 표정/1. 시크", "시크"),
    "lovely": ("2. 표정/2. 러블리", "러블리"),
    # 포즈
    "fullbody": ("3. 포즈/1. 전신", "전신"),
    "upperbody": ("3. 포즈/2. 상반신", "상반신"),
    "sitting": ("3. 포즈/3. 앉아있는", "앉아있는"),
    "mirror": ("3. 포즈/4. 거울셀피", "거울셀피"),
    # 배경
    "cafe": ("4. 배경/1. 핫플카페", "핫플 카페"),
    "graffiti": ("4. 배경/2. 그래피티", "그래피티"),
    "shutter": ("4. 배경/3. 철문", "철문"),
    "door": ("4. 배경/4. 기타 문", "기타 문"),
    "street": ("4. 배경/5. 해외스트릿", "해외 스트릿"),
    "lifestyle": ("4. 배경/6. 힙스트릿 라이프스타일", "힙 스트릿 라이프 스타일"),
    "subway": ("4. 배경/7. 지하철", "지하철"),
    "elevator": ("4. 배경/8. 엘레베이터", "엘리베이터"),
    "crosswalk": ("4. 배경/9. 횡단보도", "횡단보도"),
    # 스타일링
    "spring": ("5. 스타일링/1. SPRING (1-3월)", "SPRING"),
    "summer": ("5. 스타일링/2. SUMMER (4-6월)", "SUMMER")
}


def get_preset_file_path(preset_id: str) -> Path:
    """
    프리셋 ID로 실제 파일 경로 반환
    예: "cafe_05" -> "4. 배경/1. 핫플카페/핫플 카페 (5).png"
    """
    category = preset_id.rsplit("_", 1)[0]
    num = int(preset_id.rsplit("_", 1)[1])

    folder, prefix = PRESET_FILE_MAP[category]

    # 실제 파일 찾기 (확장자 다양)
    base_path = PRESET_BASE_PATH / folder
    for ext in [".png", ".jpeg", ".jpg", ".webp"]:
        file_path = base_path / f"{prefix} ({num}){ext}"
        if file_path.exists():
            return file_path

    return None


def get_random_combinations(
    expression_category: str,
    pose_category: str,
    bg_category: str,
    styling_category: str = None,
    count: int = 1
) -> list:
    """
    카테고리에서 중복 없이 랜덤 조합 반환

    Args:
        expression_category: "chic" | "lovely"
        pose_category: "fullbody" | "upperbody" | "sitting" | "mirror"
        bg_category: "cafe" | "graffiti" | "shutter" | "door" | "street" | "lifestyle" | "subway" | "elevator" | "crosswalk"
        styling_category: "spring" | "summer" | None
        count: 생성할 이미지 수

    Returns:
        [
            {
                "expression": "chic_03",
                "pose": "fullbody_05",
                "background": "graffiti_07",
                "styling": "summer_02"  # optional
            },
            ...
        ]
    """
    expressions = EXPRESSION_PRESETS[expression_category].copy()
    poses = POSE_PRESETS[pose_category].copy()
    bgs = BACKGROUND_PRESETS[bg_category].copy()
    stylings = STYLING_PRESETS.get(styling_category, []).copy() if styling_category else []

    random.shuffle(expressions)
    random.shuffle(poses)
    random.shuffle(bgs)
    if stylings:
        random.shuffle(stylings)

    # 프리셋 수보다 많이 요청하면 순환
    while len(expressions) < count:
        expressions.extend(EXPRESSION_PRESETS[expression_category])
    while len(poses) < count:
        poses.extend(POSE_PRESETS[pose_category])
    while len(bgs) < count:
        bgs.extend(BACKGROUND_PRESETS[bg_category])
    if stylings:
        while len(stylings) < count:
            stylings.extend(STYLING_PRESETS[styling_category])

    results = []
    for i in range(count):
        combo = {
            "expression": expressions[i],
            "pose": poses[i],
            "background": bgs[i]
        }
        if stylings:
            combo["styling"] = stylings[i]
        results.append(combo)

    return results


# 사용 예시
if __name__ == "__main__":
    combos = get_random_combinations(
        expression_category="chic",
        pose_category="fullbody",
        bg_category="graffiti",
        styling_category="summer",
        count=3
    )

    for i, combo in enumerate(combos, 1):
        print(f"\n[Image {i}]")
        print(f"  Expression: {combo['expression']}")
        print(f"  Pose: {combo['pose']}")
        print(f"  Background: {combo['background']}")
        if 'styling' in combo:
            print(f"  Styling: {combo['styling']}")
```

---

## Quick Reference

### 프리셋 수 요약


| 카테고리   | 하위 분류                                  | 수량                                       | 합계      |
| ------ | -------------------------------------- | ---------------------------------------- | ------- |
| 표정     | 시크, 러블리                                | 5 + 5                                    | **10**  |
| 포즈     | 전신, 상반신, 앉기, 거울                        | 21 + 21 + 21 + 12                        | **75**  |
| 배경     | 카페, 그래피티, 철문, 문, 스트릿, 라이프, 지하철, 엘베, 횡단 | 21 + 15 + 10 + 10 + 10 + 10 + 10 + 5 + 5 | **96**  |
| 스타일링   | SPRING, SUMMER                         | 6 + 6                                    | **12**  |
| **총합** |                                        |                                          | **193** |


### 앵글 가이드


| 앵글   | 효과           | 추천 포즈      |
| ---- | ------------ | ---------- |
| 로우앵글 | 다리 길어보임, 위엄  | 전신 걷기, 서있기 |
| 하이앵글 | 얼굴 작아보임, 귀여움 | 앉기, 쪼그리기   |
| 아이레벨 | 자연스러움        | 상반신, 거울샷   |


### 조명 가이드


| 조명      | 분위기       | 추천 배경           |
| ------- | --------- | --------------- |
| 자연광(야외) | 힙함, 스트릿   | 그래피티, 스트릿, 횡단보도 |
| 자연광(창가) | 나른함, 몽환   | 카페, 라이프스타일      |
| 플래시     | 끼부리기, Y2K | 거울셀피, 엘리베이터     |
| 형광등     | 일상적, 캐주얼  | 지하철, 편의점        |


---

**버전**: 3.0.0
**작성일**: 2026-02-20
**데이터 소스**: 표정 10장 + 포즈 75장 + 배경 96장 + 스타일링 12장 = 총 193장