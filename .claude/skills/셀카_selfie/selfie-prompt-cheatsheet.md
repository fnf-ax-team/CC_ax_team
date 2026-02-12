# 인플루언서 프롬프트 치트시트

> v1.0.0 | 최종 업데이트: 2026-02-11
>
> 인플루언서/셀럽 스타일 이미지 생성용 프롬프트 가이드

---

## 핵심 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│  한국어로 짧고 심플하게 - 영어 프롬프트 엔지니어링 금지           │
└─────────────────────────────────────────────────────────────────┘
```

**프롬프트 구조:**
```
이 얼굴로 [화질] [시점] [거리] [장소]에서 [자연스러움]
```

> 성별은 참조 이미지에서 자동 인식됨 - 별도 명시 불필요

---

## 프롬프트 예시

| 상황 | 프롬프트 |
|------|----------|
| 카페 셀카 | 이 얼굴로 예쁜 여자, 아이폰 들고 셀카 찍는 중, 완전 얼빡, 카페에서 끼부리는 표정 |
| 침대 셀카 | 이 얼굴로 예쁜 여자, 셀카 느낌, 완전 얼빡, 침대에서 끼부리는 표정, 손에 폰 없이 |
| 거울 전신샷 | 이 얼굴로 예쁜 여자, 거울 앞에서 폰 셀카, 전신, 헬스장에서 운동복 입고 |
| 남찍 카페 | 이 얼굴로 잘생긴 남자, 누가 찍어준 사진, 상반신, 카페에서 커피 마시는 중 |
| 차 안 셀카 | 이 얼굴로 예쁜 여자, 차 안에서 셀카, 얼빡, 선글라스 |

---

## 옵션 → 프롬프트 매핑

### 성별

| 옵션 | 프롬프트 |
|------|----------|
| 여자 | `예쁜 여자` |
| 남자 | `잘생긴 남자` |

### 촬영 스타일

| ID | 한글 | 프롬프트 |
|----|------|----------|
| selfie | 셀카 | `셀카 느낌, 카메라 응시, 손에 폰 없이` |
| mirror | 거울샷 | `거울 앞에서 폰 셀카, 거울에 비친 모습` |
| candid | 캔디드 | `자연스럽게 찍힌 듯, 누가 찍어준 사진, 폰카 느낌` |

### 거리/구도

| ID | 한글 | 프롬프트 |
|----|------|----------|
| close_up | 얼빡 | `완전 얼빡`, `얼굴 클로즈업` |
| upper_body | 상체 | `상반신`, `허리 위로` |
| full_body | 전신 | `전신샷`, `발끝까지` |
| lying | 누워서 | `누워서 찍은`, `침대에 누워서` |
| sitting | 앉아서 | `앉아서`, `소파에 앉아서` |

### 표정

| ID | 한글 | 프롬프트 |
|----|------|----------|
| flirty | 끼부리는 | `끼부리는 표정`, `playful seductive` |
| natural | 자연스러운 | `자연스러운 표정`, `대충 찍은 듯` |
| innocent | 청순한 | `청순한 눈빛`, `innocent look` |
| chic | 도도한 | `도도한 표정`, `chic attitude` |
| smiling | 웃는 | `살짝 웃는`, `subtle smile` |
| sleepy | 졸린 | `졸린 표정`, `just woke up` |

### 메이크업

| ID | 한글 | 프롬프트 |
|----|------|----------|
| bare | 민낯 | `bare face, no makeup, natural skin texture` |
| natural | 내추럴 | `natural makeup, subtle enhancement, minimal foundation` |
| full | 풀메이크업 | `full makeup, perfect skin, defined eyes, contoured face` |

### 착장 (의상)

```
착장 이미지 폴더 있으면 → VLM 분석 (analyze_outfit)
없으면 → 아래 카테고리에서 선택
```

**실내복:**

| ID | 한글 | 프롬프트 |
|----|------|----------|
| pajama | 잠옷 | `cozy pajama set, loungewear` |
| hoodie | 후드티 | `oversized hoodie, casual comfort` |
| sweatshirt | 맨투맨 | `crewneck sweatshirt, relaxed fit` |

**데일리:**

| ID | 한글 | 프롬프트 |
|----|------|----------|
| dress | 원피스 | `casual dress, one-piece` |
| jeans_tee | 청바지+티 | `jeans and t-shirt, casual denim look` |
| knit | 니트 | `knit sweater, cozy knitwear` |

**운동복:**

| ID | 한글 | 프롬프트 |
|----|------|----------|
| gym_wear | 운동복/레깅스 | `gym wear, sports bra and leggings` |
| tracksuit | 트레이닝복 | `tracksuit, sporty casual` |

**특수:**

| ID | 한글 | 프롬프트 |
|----|------|----------|
| lingerie | 슬립/란제리 | `satin slip dress, silk nightwear` |
| swimsuit | 수영복 | `swimsuit, bikini` |

### 장소

| ID | 한글 | 프롬프트 |
|----|------|----------|
| bedroom | 침대/방 | `bedroom interior`, `cozy bedroom, soft bedding` |
| cafe | 카페 | `cozy cafe interior`, `coffee shop` |
| car | 차 안 | `inside car`, `car interior, driver seat` |
| outdoor | 야외/거리 | `outdoor street`, `urban background` |
| gym | 헬스장 | `gym interior`, `fitness center` |
| bathroom | 욕실 | `bathroom`, `bathroom mirror` |
| hotel | 호텔 | `hotel room`, `luxury hotel interior` |
| club | 클럽 | `nightclub`, `club lighting` |
| pool | 수영장 | `poolside`, `swimming pool` |

### 시간대

| ID | 한글 | 프롬프트 |
|----|------|----------|
| day | 낮 | `daylight`, `natural light` |
| night | 밤 | `night time`, `evening lighting` |
| dawn | 새벽 | `early morning`, `soft dawn light` |

### 조명/무드

| ID | 한글 | 설명 | 프롬프트 |
|----|------|------|----------|
| natural_home | 자연광 (집) | 창문에서 들어오는 빛, 편안한 집 분위기 | `natural indoor lighting, casual home setting, soft daylight from window` |
| flash_dark | 플래시 (어두운 방) | 거울샷 특화, 폰 플래시 반사, 렌즈플레어 | `dark room, phone flash reflection in mirror, lens flare burst, low ambient light` |
| ring_light | 링라이트 | 인플루언서 스타일, 눈에 동그란 반사 | `ring light catchlight in eyes, even soft lighting, influencer style` |
| golden_hour | 골든아워 | 따뜻한 석양빛, 감성적 | `golden hour warm glow, sunset light through window, warm tones` |
| club_neon | 클럽/네온 | 밤놀이 분위기, 컬러풀한 조명 | `neon club lighting, colorful ambient, party vibe, vibrant colors` |
| bathroom_bright | 욕실 (밝은 조명) | 화장실 거울샷, 형광등 | `bright bathroom lighting, white fluorescent, clean mirror selfie` |
| bedroom_mood | 무드등 (침실) | 은은한 조명, 아늑한 분위기 | `dim bedroom lighting, mood lighting, cozy warm ambient, soft shadows` |

**조명별 추천 조합:**

| 조명 | 추천 장소 | 추천 촬영스타일 | 추천 분위기 |
|------|----------|----------------|-------------|
| 자연광 (집) | 방, 거실 | 셀카, 캔디드 | 자연스러운 |
| 플래시 (어두운 방) | 방, 클럽 | 거울샷 | 꾸민 느낌 |
| 링라이트 | 방, 스튜디오 | 셀카 | 꾸민 느낌 |
| 골든아워 | 야외, 카페 | 캔디드 | 자연스러운 |
| 클럽/네온 | 클럽, 바 | 셀카, 캔디드 | 꾸민 느낌 |
| 욕실 (밝은 조명) | 욕실 | 거울샷 | 자연스러운 |
| 무드등 (침실) | 침대/방 | 셀카, 누워서 | 자연스러운 |

---

## JSON 프롬프트 스키마 (고급)

```json
{
  "mode": "PRO",
  "portrait": {
    "type": "selfie | mirror selfie | candid snapshot | taken by someone",
    "framing": "close-up | upper body | full body",
    "expression": "표정 설명",
    "pose": "포즈 설명",
    "hand": "손 위치/동작"
  },
  "outfit": {
    "full_outfit": "전체 의상",
    "top": "상의",
    "bottom": "하의",
    "style": "스타일 키워드"
  },
  "environment": {
    "location": "장소",
    "background": "배경 설명",
    "background_detail": "배경 디테일",
    "props": "소품"
  },
  "lighting": {
    "main_light": "주 조명",
    "ambient": "분위기 조명",
    "color_temp": "색온도"
  },
  "camera": {
    "look": "smartphone | DSLR | film",
    "focus": "포커스 포인트",
    "depth_of_field": "심도",
    "grain": "필름 그레인"
  },
  "face": {
    "texture": "피부 질감",
    "retouching": "보정 수준",
    "eyes": "눈 표현"
  },
  "mood": ["키워드1", "키워드2"],
  "negative_prompt": ["제외할 것들"]
}
```

### JSON 예시

```json
{
  "mode": "PRO",
  "portrait": {
    "type": "mirror selfie",
    "framing": "upper body, chest up",
    "expression": "playful seductive, slight smirk",
    "pose": "one hand on hip, slight body angle"
  },
  "outfit": {
    "full_outfit": "cozy pajama set",
    "style": "loungewear comfortable"
  },
  "environment": {
    "location": "bedroom interior",
    "background": "cozy bedroom, soft bedding"
  },
  "lighting": {
    "main_light": "soft ambient indoor lighting",
    "color_temp": "warm cozy"
  },
  "mood": ["flirty", "confident", "cozy"]
}
```

---

## 다양성 만들기

**문제: 다 비슷하게 나옴**

표정만 바꾸면 다 비슷함:
```
끼부리는 표정 → 청순한 표정 → 도도한 표정
= 결과 다 얼빡 셀카에 표정만 살짝 다름
```

**해결: 상황/장소/포즈/조명을 확 다르게**

| 바꿔야 할 것 | 옵션들 |
|-------------|--------|
| **장소** | 방, 헬스장, 카페, 차 안, 야외, 클럽, 욕실, 호텔 |
| **포즈** | 얼빡, 전신, 앉아서, 누워서, 걷다가, 서서 |
| **옷** | 운동복, 원피스, 캐주얼, 파자마, 수건 |
| **조명** | 자연광, 플래시, 링라이트, 골든아워, 네온, 무드등 |
| **시간** | 낮, 밤, 새벽 |

---

## 금지 조합

### 포즈/장소 금지

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 1 | 전신 + 얼빡 | 물리적 모순 | 둘 중 하나만 |
| 2 | 거울셀카 + 누워서 | 거울 앞에서 눕기 어려움 | 침대 셀카로 변경 |
| 3 | 헬스장 + 파자마 | 상황 부적합 | 운동복으로 변경 |
| 4 | 수영복 + 카페 | 상황 부적합 | 수영장/해변으로 변경 |
| 5 | 남찍 + 거울셀카 | 촬영 방식 충돌 | 둘 중 하나만 |

### 조명 금지 조합

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 6 | 클럽/네온 + 집/방 | 조명-장소 불일치 | 장소를 클럽/바로 변경 |
| 7 | 골든아워 + 욕실 | 욕실에 석양빛 부자연스러움 | 야외/카페로 변경 또는 자연광 |
| 8 | 플래시 + 야외 (낮) | 낮에 플래시 부자연스러움 | 자연광 또는 골든아워로 |
| 9 | 링라이트 + 캔디드 | 링라이트는 정면 셀카용 | 셀카로 변경 또는 자연광 |
| 10 | 무드등 + 헬스장 | 헬스장에 무드등 없음 | 자연광 또는 링라이트 |

---

## 네거티브 프롬프트

### 기본 (항상 적용)

```
AI look, plastic skin, overprocessed, golden hour warm cast
```

### 조건부 추가

| 조건 | 추가 네거티브 |
|------|--------------|
| 셀카 | `professional studio lighting` |
| UGC 스타일 | `perfect skin, magazine quality` |
| 자연스러움 원할 때 | `posed, staged, artificial` |

---

## MLB 스타일 빈도 데이터

MLB 브랜드컷 22장 분석 기반 빈도 (인플루언서 스타일 참고용)

| 카테고리 | 주요 옵션 | 빈도 |
|----------|-----------|------|
| 헤어 스타일 | straight_loose (긴 생머리) | 95% |
| 헤어 컬러 | black (검정) | 100% |
| 메이크업 베이스 | natural (자연스러운 피부) | 85% |
| 립 컬러 | MLBB (내 입술처럼) | 50% |
| 프레이밍 | MS (허리위) | 40% |
| 포즈 | stand (서있는 자세) | 40% |
| 표정 베이스 | cool (쿨한 표정) | 45% |

---

## 검증 기준

### UGC/셀피 5개 항목

| 항목 | 비중 | 설명 |
|------|------|------|
| realism | 35% | 실제 사진처럼 보이는가 |
| person_preservation | 25% | 얼굴이 참조 이미지와 같은 사람인가 |
| scenario_fit | 20% | 장소/상황/옷이 자연스럽게 어울리는가 |
| skin_condition | 10% | 피부 질감이 자연스러운가 (AI 플라스틱 피부 X) |
| anti_polish_factor | 10% | 너무 완벽하지 않은가 (약간의 결점이 자연스러움) |

**원칙: "너무 잘 나오면 실패"**

### Auto-Fail 조건

- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람 (참조와 불일치)
- 누런 톤 (golden/amber/warm cast)
- AI 특유 플라스틱 피부
- 의도하지 않은 텍스트/워터마크

---

**데이터 소스:** SKILL.md v2.0 + option-mappings.json + MLB 스타일 VLM 분석 (2026-02-10)
