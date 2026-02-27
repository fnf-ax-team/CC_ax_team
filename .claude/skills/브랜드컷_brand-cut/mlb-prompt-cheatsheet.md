# MLB 프롬프트 치트시트

> v9.0.0 | 최종 업데이트: 2026-02-24
>
> **v9.0.0: MLB 전용 프리셋 DB 연결 (`db/mlb_style/`)**

---

## 프리셋 참조 (Preset References)

> **MLB 전용 프리셋 위치**: `db/mlb_style/`
>
> 범용 프리셋(`db/*.json`) 대신 MLB 브랜드에 최적화된 전용 프리셋 사용

| 카테고리 | 참조 파일 | 프리셋 수 | 설명 |
|----------|-----------|----------|------|
| 포즈 | `db/mlb_style/mlb_pose_presets.json` | 16개 | 왼팔/오른팔/왼손/오른손/왼다리/오른다리/힙 상세 |
| 표정 | `db/mlb_style/mlb_expression_presets.json` | 8개 | 베이스/바이브/눈/시선/입 상세, 큰 아몬드눈 필수 |
| 배경 | `db/mlb_style/mlb_background_presets.json` | 12개 | 지역/시간대/색감/장소/분위기/provides/supported_stances |
| 비주얼_무드 | `db/mlb_style/mlb_visual_mood_presets.json` | 6개 | 필름텍스처/컬러그레이딩/조명, 쿨톤 필수 |
| 촬영_세팅 | `db/mlb_style/mlb_camera_presets.json` | 8개 | 포즈와 1:1 매칭, f/2.8 고정 |
| 스타일링 | `db/mlb_style/mlb_styling_presets.json` | 5개 | 아이템/코디방법/스타일링포인트 |
| 모델 | `db/mlb_style/mlb_model_presets.json` | 4개 | 민족/성별/나이/헤어 |

### 프리셋 사용법

```python
import json
from pathlib import Path

# MLB 프리셋 로드
mlb_presets_dir = Path("db/mlb_style")

with open(mlb_presets_dir / "mlb_pose_presets.json", encoding="utf-8") as f:
    pose_presets = json.load(f)

# 프리셋 ID로 참조
pose = pose_presets["categories"]["confident_standing"]["poses"][0]
# → 왼팔, 오른팔, 왼손, 오른손, 왼다리, 오른다리, 힙 필드 사용
```

---

## JSON 스키마

```json
{
  "모델": {
    "국적": "",
    "성별": "",
    "나이": ""
  },

  "헤어": {
    "스타일": "",
    "컬러": "",
    "질감": ""
  },

  "표정": {
    "preset_id": "",
    "베이스": "",
    "바이브": "",
    "눈": "",
    "시선": "",
    "입": ""
  },

  "포즈": {
    "preset_id": "",
    "stance": "",
    "왼팔": "",
    "오른팔": "",
    "왼손": "",
    "오른손": "",
    "왼다리": "",
    "오른다리": "",
    "힙": ""
  },

  "배경": {
    "preset_id": "",
    "지역": "",
    "시간대": "",
    "색감": "",
    "장소": "",
    "분위기": ""
  },

  "스타일링": {
    "preset_id": "",
    "overall_vibe": "",
    "아이템": {
      "아우터": "",
      "상의": "",
      "하의": "",
      "신발": "",
      "헤드웨어": "",
      "주얼리": "",
      "가방": "",
      "벨트": ""
    },
    "코디방법": {
      "아우터": "",
      "상의": "",
      "하의": "",
      "신발": "",
      "헤드웨어": "",
      "주얼리": "",
      "가방": "",
      "벨트": ""
    }
  },

  "비주얼_무드": {
    "preset_id": "",
    "필름_텍스처": {
      "질감": "",
      "보정법": ""
    },
    "컬러_그레이딩": {
      "주요색조": "",
      "채도": "",
      "노출": ""
    },
    "조명": {
      "광원": "",
      "방향": "",
      "그림자": ""
    }
  },

  "촬영_세팅": {
    "preset_id": "",
    "프레이밍": "",
    "렌즈": "",
    "앵글": "",
    "높이": "",
    "구도": "",
    "조리개": ""
  },

  "출력품질": "",
  "네거티브": ""
}
```

---

## 기본값 (미입력시 자동 적용)

| 카테고리 | 필드 | 기본값 | 빈도 |
|---------|------|--------|------|
| 모델 | 국적 | 한국인 | - |
| 모델 | 성별 | 여성 | - |
| 모델 | 나이 | 20대 초반 | - |
| 헤어 | 스타일 | straight_loose | 95% |
| 헤어 | 컬러 | black | 100% |
| 헤어 | 질감 | sleek | 70% |
| 촬영_세팅 | 프레이밍 | MS | 40% |
| 촬영_세팅 | 렌즈 | 50mm | - |
| 촬영_세팅 | 앵글 | 3/4측면 | 40% |
| 촬영_세팅 | 높이 | 눈높이 | 80% |
| 촬영_세팅 | 구도 | 중앙 | 70% |
| 촬영_세팅 | 조리개 | f/2.8 (고정) | - |
| 포즈 | stance | stand | 40% |
| 표정 | 베이스 | cool | 50% |
| 표정 | 바이브 | mysterious | 40% |
| 표정 | 시선 | direct | 50% |
| 표정 | 입 | closed | 60% |
| 배경 | 장소 | 콘크리트 | 40% |
| 비주얼_무드.조명 | 광원 | 자연광흐림 | 45% |
| 비주얼_무드.컬러_그레이딩 | 주요색조 | 뉴트럴쿨 | 60% |

---

## 브랜드 DNA (DO & DON'T)

### 컨셉: "Young & Rich" - Languid Chic

**지루한 부자 아이 미학** - 고급스러움 필수

1. **큰 아몬드눈** 필수 - 쿨함은 입/태도로만
2. **쿨톤만** - 골든아워 절대 금지
3. 모델이 주인공, 배경은 조연
4. f/2.8로 배경 흐림
5. Languid Chic - 지루한 부자 아이 미학

### 스타일링 공식

- **미드리프 노출률**: 81%
- **체인 착용률**: 62.5%
- **오버사이즈 아우터**: 2-3사이즈 업

### 배경 톤앤매너 (모던 힙스트릿)

| DO | DON'T |
|----|-------|
| 콘크리트/시멘트 질감 | 자연 풍경 (숲, 바다) |
| 메탈/산업적 요소 | 따뜻한 원목/우드톤 |
| 도심/스트릿 | 전원/시골 |
| 지하주차장/창고 | 카페/레스토랑 |
| 미니멀/클린 | 복잡한 패턴/꽃무늬 |
| 쿨그레이/뉴트럴 | 파스텔/따뜻한 색감 |
| 럭셔리 차량 (SUV, 빈티지) | 일반 승용차/경차 |

**배경 키워드**: `industrial`, `urban`, `concrete`, `metallic`, `minimal`, `cool-toned`, `street`

**배경 금지어**: `cozy`, `warm`, `rustic`, `natural greenery`, `golden hour lighting`

### 금지

- 골든/앰버/웜톤
- 익스트림 클로즈업
- 밝은 미소/치아 노출
- 따뜻하고 아늑한 배경

---

## 필드 규칙 (Field Rules)

### 모델

| 필드 | 필수 | 기본값 | 옵션 |
|------|------|--------|------|
| 국적 | O | 한국인 | 한국인, 동아시아인, 혼혈 |
| 성별 | O | 여성 | 여성, 남성 |
| 나이 | X | 20대 초반 | 10대 후반, 20대 초반, 20대 중반 |

**프롬프트 매핑:**

| ID | 한글 | Prompt |
|----|------|--------|
| korean | 한국인 | `Korean female model` |
| east_asian | 동아시아인 | `East Asian female model` |
| mixed | 혼혈 | `Mixed Asian female model` |
| late_teens | 10대후반 | `late teens, fresh` |
| early_20s | 20대초반 | `early 20s, youthful` |
| mid_20s | 20대중반 | `mid 20s, confident` |

---

### 헤어

| 필드 | 필수 | 기본값 | 옵션 |
|------|------|--------|------|
| 스타일 | X | straight_loose | straight_loose, wavy, ponytail, bun |
| 컬러 | X | black | black, dark_brown |
| 질감 | X | sleek | sleek, natural |

**프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| straight_loose | 스트레이트루즈 | `long straight hair, loose and flowing, sleek` | 95% |
| wavy | 웨이브 | `wavy hair, soft waves` | 5% |
| black | 블랙 | `black hair` | 100% |
| dark_brown | 다크브라운 | `dark brown hair` | - |
| sleek | 슬릭 | `sleek, glossy` | 70% |
| natural | 내추럴 | `natural texture` | 30% |

---

### 표정

| 필드 | 필수 | 기본값 | 비고 |
|------|------|--------|------|
| preset_id | X | - | expression_presets.json 참조 |
| 베이스 | O | cool | cool, natural, dreamy, neutral, serious |
| 바이브 | X | mysterious | mysterious, effortless, unbothered, sophisticated |
| 눈 | O | **큰 눈 (고정)** | MLB DNA: 큰 아몬드눈 필수 |
| 시선 | X | direct | direct, past, side |
| 입 | X | closed | closed, parted, smile |

**베이스 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| cool | 쿨 | `cool expression, unbothered attitude, expression intensity 5-6` | 50% |
| natural | 내추럴 | `natural subtle smile, relaxed composure, expression intensity 4-5` | 25% |
| dreamy | 몽환 | `dreamy expression, distant contemplative mood, expression intensity 3-4` | - |
| neutral | 뉴트럴 | `neutral expression, blank but confident, expression intensity 4` | 15% |
| serious | 시리어스 | `serious expression, intense focus, expression intensity 6-7` | 10% |

**바이브 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| mysterious | 미스테리어스 | `mysterious vibe, enigmatic presence` | 40% |
| approachable | 어프로처블 | `approachable vibe, accessible coolness` | 25% |
| sophisticated | 소피스티케이티드 | `sophisticated vibe, refined elegance` | 35% |

**시선 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| direct | 직시 | `direct but disinterested gaze at camera` | 50% |
| past | 허공응시 | `looking slightly past camera, distant focus` | 30% |
| side | 곁눈질 | `subtle side glance, mysterious` | 20% |

**입 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| closed | 닫힌입 | `mouth closed in neutral position, lips together` | 60% |
| parted | 살짝벌림 | `lips slightly parted, relaxed mouth` | 30% |
| smile | 미세미소 | `subtle hint of smile, corners barely raised` | 10% |

---

### 포즈

| 필드 | 필수 | 기본값 | 비고 |
|------|------|--------|------|
| preset_id | X | - | pose_presets.json 참조 (권장) |
| stance | O | stand | stand, lean_wall, lean_car, sit, walk |
| 왼팔~힙 | X | - | preset_id 사용 시 자동 채움 |

---

## 포즈 프리셋 라이브러리 (MLB 고유) - v7.0

> **16개 검증된 프리셋**. 147개 실제 촬영본 VLM 분석에서 추출.
>
> **사용법**: `포즈.preset_id`에 프리셋 ID 입력
> **커스텀**: 개별 부위 직접 지정

### 프리셋 요약 테이블

| ID | 한글명 | 카테고리 | 차량 | 에너지 | 호환 배경 | 빈도 |
|----|--------|----------|------|--------|----------|------|
| confident_standing_none_neutral | 자신감스탠딩_중립 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 12.9% |
| confident_standing_none_hand_on_hip | 자신감스탠딩_허리손 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 12.2% |
| confident_standing_none_arms_relaxed | 자신감스탠딩_편안 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 10.9% |
| confident_standing_none_hand_in_pocket | 자신감스탠딩_주머니손 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 8.8% |
| confident_standing_none_holding_bag | 자신감스탠딩_가방들기 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 4.8% |
| confident_standing_none_hand_on_chin | 자신감스탠딩_턱괴기 | confident_standing | X | 4 | 메탈패널, 창고, 콘크리트, 도심 | 4.8% |
| confident_standing_none_hand_on_hat | 자신감스탠딩_모자터치 | confident_standing | X | 3 | 메탈패널, 창고, 콘크리트, 도심 | 2.7% |
| confident_standing_car_neutral | 자신감스탠딩_차량_중립 | confident_standing | O | 3 | 메탈패널, 창고, 콘크리트, 도심 | 2.0% |
| relaxed_lean_car_neutral | 편안한기대기_차량_중립 | relaxed_lean | O | 3 | 벽, 기둥, 차량, 야외 | 8.2% |
| relaxed_lean_car_hand_on_hip | 편안한기대기_차량_허리손 | relaxed_lean | O | 3 | 벽, 기둥, 차량, 야외 | 2.0% |
| relaxed_lean_car_hand_in_pocket | 편안한기대기_차량_주머니손 | relaxed_lean | O | 3 | 벽, 기둥, 차량, 야외 | 1.4% |
| relaxed_lean_none_neutral | 편안한기대기_중립 | relaxed_lean | X | 3 | 벽, 기둥, 차량, 야외 | 3.4% |
| seated_none_neutral | 앉기_중립 | seated | X | 1 | 의자, 벤치, 차량, 바닥 | 6.8% |
| seated_none_hand_on_chin | 앉기_턱괴기 | seated | X | 2 | 의자, 벤치, 차량, 바닥 | 4.1% |
| seated_car_neutral | 앉기_차량_중립 | seated | O | 2 | 의자, 벤치, 차량, 바닥 | 3.4% |
| static_car_neutral | 정적서기_차량_중립 | static | O | 1 | 스튜디오, 단색배경, 미니멀 | 1.4% |

### 프리셋 상세 (full_prompt 포함)

#### confident_standing 카테고리 (8개)

**confident_standing_none_neutral** (자신감스탠딩_중립)
```
confident standing, weight: left 55%, right 45%, left arm: down, slightly bent at elbow, right arm: down, slightly bent at elbow, left leg: not visible, right leg: not visible
```

**confident_standing_none_hand_on_hip** (자신감스탠딩_허리손)
```
confident standing, weight: left 55%, right 45%, left arm: hand on hip, right arm: holding bag strap, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**confident_standing_none_arms_relaxed** (자신감스탠딩_편안)
```
confident standing, weight: left 55%, right 45%, left arm: relaxed at side, slightly bent, right arm: relaxed at side, slightly bent, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**confident_standing_none_hand_in_pocket** (자신감스탠딩_주머니손)
```
confident standing, weight: left 50%, right 50%, left arm: hand in pocket, right arm: hand in pocket, left leg: straight support leg, right leg: straight support leg
```

**confident_standing_none_holding_bag** (자신감스탠딩_가방들기)
```
confident standing, weight: left 55%, right 45%, left arm: holding bag strap, elbow bent 90°, right arm: hand in pocket, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**confident_standing_none_hand_on_chin** (자신감스탠딩_턱괴기)
```
confident standing, weight: left 60%, right 40%, left arm: across chest, hand touching right shoulder, right arm: holding bag strap, arm slightly bent, left leg: slightly bent at knee 5°, right leg: slightly bent at knee 10°
```

**confident_standing_none_hand_on_hat** (자신감스탠딩_모자터치)
```
confident standing, weight: left 55%, right 45%, left arm: hand touching hat brim, right arm: hanging loosely at side, jacket draped over shoulder, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**confident_standing_car_neutral** (자신감스탠딩_차량_중립)
```
confident standing, weight: left 55%, right 45%, left arm: extended, resting on car, right arm: extended, slightly bent, hand relaxed, left leg: straight support leg, right leg: slightly bent at knee 5°
```

#### relaxed_lean 카테고리 (4개)

**relaxed_lean_car_neutral** (편안한기대기_차량_중립)
```
relaxed lean, weight: left 30%, right 70%, left arm: resting on car hood, slightly bent, right arm: resting on right thigh, slightly bent, left leg: bent at knee 45°, foot on ground, right leg: bent at knee 30°, resting on car tire
```

**relaxed_lean_car_hand_on_hip** (편안한기대기_차량_허리손)
```
relaxed lean, weight: left 60%, right 40%, left arm: straight, hand on hip, right arm: bent, leaning on car, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**relaxed_lean_car_hand_in_pocket** (편안한기대기_차량_주머니손)
```
relaxed lean, weight: left 60%, right 40%, left arm: hand in pocket, right arm: resting on car, left leg: straight support leg, right leg: slightly bent at knee 5°
```

**relaxed_lean_none_neutral** (편안한기대기_중립)
```
relaxed lean, weight: left 60%, right 40%, left arm: extended, hand on pole, right arm: holding bag, slightly bent, left leg: straight support leg, right leg: bent at knee 20°, foot slightly raised
```

#### seated 카테고리 (3개)

**seated_none_neutral** (앉기_중립)
```
seated, weight: left 50%, right 50%, left arm: resting on chair arm, right arm: resting on lap, left leg: slightly bent at knee 10°, right leg: slightly bent at knee 10°
```

**seated_none_hand_on_chin** (앉기_턱괴기)
```
seated, weight: left 60%, right 40%, left arm: elbow resting on left knee, hand supporting chin, right arm: bent at elbow, hand resting on right thigh, left leg: bent at knee 90°, foot flat on ground, right leg: bent at knee 120°, foot resting on toes
```

**seated_car_neutral** (앉기_차량_중립)
```
seated, weight: left 60%, right 40%, left arm: resting on bent left leg, right arm: resting on ground, slightly bent, left leg: bent at knee 70°, foot flat on ground, right leg: extended, slightly bent at knee 10°
```

#### static 카테고리 (1개)

**static_car_neutral** (정적서기_차량_중립)
```
static, weight: left 50%, right 50%, left arm: hanging naturally, right arm: hanging naturally, left leg: not visible, right leg: not visible
```

### energy_level 설명

| Level | 의미 | 설명 |
|-------|------|------|
| 1 | 매우 차분 | 직립 부동, 정적 |
| 2 | 차분 | 자연스러운 서기, 기대기 |
| 3 | 중립 | 힙 팝, 무게 이동 |
| 4 | 역동적 | 걷기, 회전 |
| 5 | 매우 역동적 | 점프, 큰 동작 |

---

### 배경

| 필드 | 필수 | 기본값 | 비고 |
|------|------|--------|------|
| preset_id | X | - | background_presets.json 참조 |
| 지역 | X | - | 한국/성수, 미국/뉴욕 등 |
| 시간대 | X | 주간 | 주간, 야간, 실내 |
| 색감 | X | 쿨그레이 | 쿨그레이, 블랙, 메탈릭 |
| 장소 | O | 콘크리트 | 구체적 장소 설명 |
| 분위기 | X | 인더스트리얼 | 힙하고 모던한, 미니멀 |

**배경 프롬프트 매핑:**

| ID | 한글 | Prompt | 타입 | 빈도 |
|----|------|--------|------|------|
| 메탈패널 | 메탈패널 | `sleek gray metallic panel wall, industrial studio backdrop` | 차량없음 | 10% |
| 창고 | 창고 | `industrial warehouse space with metal ladders, raw concrete` | 차량없음 | 5% |
| 콘크리트 | 콘크리트 | `brutalist concrete architecture, raw cement walls` | 차량없음 | 40% |
| 럭셔리SUV | 럭셔리SUV | `silver luxury SUV in industrial garage, matte metallic` | 차량있음 | 20% |
| 빈티지카 | 빈티지카 | `vintage car, classic vehicle` | 차량있음 | 15% |
| 지하주차장 | 지하주차장 | `underground parking garage, concrete pillars` | 차량있음 | 10% |

---

### 스타일링

| 필드 | 필수 | 기본값 | 비고 |
|------|------|--------|------|
| preset_id | X | - | styling_preset_db.json 참조 |
| overall_vibe | X | 스트릿 캐주얼 | 스트릿 캐주얼, Y2K, 애슬레저 |

**아이템 필드:**

| 필드 | 필수 | 예시 |
|------|------|------|
| 아우터 | X | MLB 그린 바시티 자켓 |
| 상의 | O | MLB 화이트 크롭 탱크탑 with NY 로고 |
| 하의 | O | 와이드 핏 카고 데님 |
| 신발 | X | MLB 청키 스니커즈 |
| 헤드웨어 | X | MLB CP66 볼캡 |
| 주얼리 | X | 볼드한 골드 체인 목걸이 |
| 가방 | X | 나일론 크로스바디 백 |
| 벨트 | X | 체인 벨트 |

**헤드웨어 프롬프트 매핑:**

| ID | 한글 | Prompt |
|----|------|--------|
| mlb_cap | MLB캡 | `MLB baseball cap` |
| beanie | 비니 | `MLB beanie with logo` |

**주얼리 프롬프트 매핑:**

| ID | 한글 | Prompt |
|----|------|--------|
| chain_necklace | 체인목걸이 | `gold chain necklace, chunky link chain` |
| layered_necklace | 레이어드목걸이 | `layered necklaces, multiple chains` |
| hoop_earring | 후프귀걸이 | `gold hoop earrings` |
| stud_earring | 스터드귀걸이 | `small stud earrings` |
| rings | 반지 | `rings on fingers, minimal jewelry` |

**가방/벨트 프롬프트 매핑:**

| ID | 한글 | Prompt |
|----|------|--------|
| chain_belt | 체인벨트 | `chain belt at waist, decorative belt` |
| crossbody_bag | 크로스바디백 | `MLB crossbody bag, small shoulder bag` |
| hobo_bag | 호보백 | `MLB hobo bag, slouchy shoulder bag` |

**코디방법 옵션 + 프롬프트 매핑:**

| 아이템 | ID | 한글 | Prompt |
|--------|---|------|--------|
| 아우터 | 정상착용 | 정상 | `worn normally` |
| 아우터 | 어깨에_걸침 | 걸침 | `jacket draped over shoulder` |
| 아우터 | 한팔만_소매에_넣고_착용 | 한쪽 | `worn on one arm only` |
| 아우터 | 지퍼_오픈 | 오픈 | `zipper open` |
| 아우터 | 지퍼_클로즈 | 클로즈 | `zipper closed` |
| 아우터 | 손에_들고 | 손 | `held in hand` |
| 상의 | 정상착용 | 정상 | `worn normally` |
| 상의 | 크롭_배꼽노출 | 크롭 | `cropped above waist` |
| 상의 | 오프숄더_한쪽어깨_흘러내림 | 어깨 | `off-shoulder on one side` |
| 상의 | 넣어입기 | 인 | `tucked into pants` |
| 상의 | 버튼_오픈 | 오픈 | `buttons open` |
| 상의 | 오버사이즈 | 오버 | `oversized fit, 2-3 sizes up` |
| 하의 | 정상착용 | 정상 | `worn normally` |
| 하의 | 하이웨이스트 | 하이 | `high-waisted fit` |
| 하의 | 로우라이즈 | 로우 | `low-rise fit` |
| 하의 | 밑단_롤업 | 롤업 | `cuffed at ankle` |
| 하의 | 원레그롤업 | 원롤 | `one leg cuffed` |
| 신발 | 정상착용 | 정상 | `worn normally` |
| 신발 | 루즈삭스_함께 | 루즈 | `with loose socks` |
| 신발 | 크루삭스_함께 | 크루 | `with crew socks` |
| 신발 | 끈풀림 | 풀림 | `laces untied` |
| 신발 | 뒤꿈치밟기 | 밟기 | `heel stepped down` |
| 헤드웨어 | 정방향 | 정상 | `worn normally` |
| 헤드웨어 | 뒤로쓰기 | 뒤 | `cap worn backwards` |
| 헤드웨어 | 옆으로쓰기 | 옆 | `cap worn sideways` |
| 헤드웨어 | 살짝_들어올림 | 올림 | `cap slightly lifted` |
| 헤드웨어 | 손에_들고 | 손 | `held in hand` |
| 주얼리 | 정상착용 | 정상 | `worn normally` |
| 주얼리 | 레이어드_여러개 | 레이어 | `layered jewelry` |
| 주얼리 | 언발런스 | 언발 | `asymmetric styling` |
| 가방 | 한쪽어깨 | 정상 | `worn normally` |
| 가방 | 크로스바디_앞으로 | 크로스 | `crossbody wear` |
| 가방 | 크로스바디_옆으로 | 숄더 | `shoulder wear` |
| 가방 | 손에_들고 | 손 | `held in hand` |
| 가방 | 바닥에_놓기 | 바닥 | `placed on ground` |
| 벨트 | 정상착용 | 정상 | `worn normally` |
| 벨트 | 느슨하게 | 느슨 | `worn loosely` |
| 벨트 | 장식용 | 장식 | `decorative styling` |

---

### 비주얼_무드

| 필드 | 필수 | 기본값 | 비고 |
|------|------|--------|------|
| preset_id | X | - | visual_mood_preset_db.json 참조 |

**필름_텍스처:**

| 필드 | 옵션 | MLB 기본값 |
|------|------|-----------|
| 질감 | clean digital, slight grain, 35mm film grain | slight grain |
| 보정법 | faded black, VSCO film look, minimal edit | faded black, high contrast |

**컬러_그레이딩:**

| 필드 | 옵션 | MLB 기본값 |
|------|------|-----------|
| 주요색조 | cool muted, neutral, warm beige | **cool muted (필수)** |
| 채도 | vibrant, natural, slightly muted, desaturated | slightly muted |
| 노출 | high-key, balanced, slightly overexposed | balanced |

**조명 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 소프트박스 | 소프트박스 | `softbox lighting at 45 degrees, 5500K neutral temperature` | 20% |
| 스튜디오쿨 | 스튜디오쿨 | `studio lighting with cool temperature, 5500-6000K` | 35% |
| 자연광흐림 | 자연광흐림 | `natural overcast daylight, soft even illumination` | 45% |

**색보정 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 뉴트럴쿨 | 뉴트럴쿨 | `neutral-cool color grade, clean digital look, no warm cast` | 60% |
| 채도낮춤 | 채도낮춤 | `slightly desaturated with cool undertones` | 30% |
| 고대비쿨 | 고대비쿨 | `high contrast with blue shadow tones` | 10% |

---

### 촬영_세팅

| 필드 | 필수 | 기본값 | 옵션 |
|------|------|--------|------|
| preset_id | X | - | camera_presets.json (포즈와 1:1 매칭) |
| 프레이밍 | O | MS | FS, MFS, MS, MCU, CU |
| 렌즈 | X | 50mm | 35mm, 50mm, 85mm |
| 앵글 | X | 3/4측면 | 정면, 약간측면, 3/4측면, 측면 |
| 높이 | X | 눈높이 | 눈높이, 살짝로앵글, 로앵글, 하이앵글 |
| 구도 | X | 중앙 | 중앙, 왼쪽1/3, 오른쪽1/3 |
| 조리개 | X | **f/2.8 (고정)** | 배경 아웃포커싱용 |

**프레이밍 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| FS | 전신 | `full shot framing, head to toe` | 10% |
| MFS | 무릎위 | `medium full shot, knees up` | 30% |
| MS | 허리위 | `medium shot framing, waist up` | 40% |
| MCU | 가슴위 | `medium close-up, chest up` | 15% |
| CU | 얼굴 | `close-up, shoulders and face` | 5% |

**렌즈 프롬프트 매핑:**

| ID | Prompt |
|----|--------|
| 35mm | `35mm lens, wider environmental portrait` |
| 50mm | `50mm lens, standard portrait perspective` |
| 85mm | `85mm lens, compressed background` |

**앵글 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 정면 | 친근 | `camera at eye level, frontal angle` | 35% |
| 약간측면 | 미세변화 | `camera 10 degrees off-center` | 20% |
| 3/4측면 | 입체감 | `camera 15 degrees to subject's side, 3/4 profile view` | 40% |
| 측면 | 시크 | `camera 30 degrees, side profile` | 5% |

**높이 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 눈높이 | 친근 | `camera at eye level` | 80% |
| 살짝로앵글 | 파워감 | `camera 10cm below eye level` | 20% |

**구도 프롬프트 매핑:**

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 중앙 | 중앙구도 | `subject centered in frame, balanced composition` | 70% |
| 왼쪽1/3 | 삼분할왼쪽 | `subject positioned at left third, rule of thirds` | 15% |
| 오른쪽1/3 | 삼분할오른쪽 | `subject positioned at right third, look room on left` | 15% |

---

### 출력품질

**고정값:**
```
professional fashion photography, high-end editorial, sharp focus, 8K quality
```

---

### 네거티브

**기본 (항상 적용):**
```
bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers
```

**조건부 추가:**

| 조건 | 추가 네거티브 |
|------|--------------|
| CU 프레이밍 | `full body visible` |
| walk 포즈 | `static pose, standing still` |
| 차량 배경 | `front grille visible, license plate` |

---

## 호환 규칙 (MLB 고유)

### 렌즈-프레이밍

| 렌즈 | 권장 프레이밍 |
|------|--------------|
| 85mm | MCU, CU |
| 50mm | MS, MFS, MCU |
| 35mm | MFS, FS |

### 표정-입

| 표정 | 가능 입 |
|------|--------|
| cool | closed, parted |
| natural | closed, parted |
| dreamy | parted, closed |
| neutral | closed |
| serious | closed |

### 표정-시선

| 표정 | 가능 시선 |
|------|----------|
| cool | direct, past, side |
| natural | direct, past |
| dreamy | past, side |
| neutral | direct |
| serious | direct |

### 배경-프리셋 호환 규칙

| 배경 | 호환 프리셋 카테고리 |
|------|---------------------|
| 메탈패널 | confident_standing_none_*, static_*, dynamic_none_* |
| 창고 | confident_standing_none_*, relaxed_lean_none_*, seated_none_*, dynamic_none_* |
| 콘크리트 | confident_standing_none_*, relaxed_lean_none_*, dynamic_none_* |
| 럭셔리SUV | *_car_* (차량 프리셋만) |
| 빈티지카 | *_car_* |
| 지하주차장 | confident_standing_car_*, relaxed_lean_car_* |

### 배경-포즈 (커스텀 모드 전용)

| 배경 | 가능 포즈 |
|------|----------|
| 메탈패널 | stand, lean_wall, walk, back_look |
| 창고 | stand, lean_wall, sit, sit_crouch, lean_railing, walk, back_look |
| 콘크리트 | stand, lean_wall, sit_crouch, walk, back_look |
| 럭셔리SUV | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 빈티지카 | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 지하주차장 | lean_car, door_lean |

---

## 금지 조합 (MLB 고유)

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 1 | 85mm + MFS | 과도한 배경 압축 | 50mm 또는 35mm |
| 2 | 35mm + CU | 광각 왜곡으로 얼굴 변형 | 85mm 또는 50mm |
| 3 | sit + 메탈패널/콘크리트 | 앉을 곳 없음 | 창고 배경 또는 stand |
| 4 | CU + walk | 걷기는 전신 필요 | MCU 이상 또는 stand |
| 5 | dreamy + direct(정면직시) | 컨셉 충돌 | past 또는 side |
| 6 | serious + smile | 컨셉 충돌 | closed |
| 7 | cool + smile | 쿨한데 미소는 모순 | closed 또는 parted |
| 8 | 골든아워 + MLB | 브랜드 DNA 위반 | 소프트박스 또는 스튜디오쿨 |

---

## 사용 예시

```json
{
  "모델": {
    "국적": "한국인",
    "성별": "여성",
    "나이": "20대 초반"
  },

  "헤어": {
    "스타일": "straight_loose",
    "컬러": "black",
    "질감": "sleek"
  },

  "표정": {
    "preset_id": "시크_02",
    "베이스": "cool",
    "바이브": "mysterious, effortless",
    "눈": "큰 눈",
    "시선": "3/4 측면",
    "입": "closed"
  },

  "포즈": {
    "preset_id": "confident_standing_none_hand_on_hip",
    "stance": "stand",
    "왼팔": "hand on hip",
    "오른팔": "holding bag strap",
    "왼다리": "straight support leg",
    "오른다리": "slightly bent at knee 5°",
    "힙": "left 55%, right 45%"
  },

  "배경": {
    "preset_id": "콘크리트_01",
    "지역": "한국/성수",
    "시간대": "주간",
    "색감": "쿨그레이, 콘크리트, 메탈릭",
    "장소": "브루탈리즘 콘크리트 건축물. 노출 시멘트 벽, 기하학적 구조.",
    "분위기": "인더스트리얼, 모던, 힙"
  },

  "스타일링": {
    "preset_id": "MLB_STREET_01",
    "overall_vibe": "스트릿 캐주얼",
    "아이템": {
      "아우터": "MLB 그린 바시티 자켓 with NY 로고",
      "상의": "MLB 화이트 크롭 탱크탑 with NY 로고",
      "하의": "와이드 핏 카고 데님 with NY 자수",
      "신발": "MLB 청키 스니커즈",
      "헤드웨어": "MLB CP66 볼캡",
      "주얼리": "골드 체인 목걸이",
      "가방": "나일론 크로스바디 백"
    },
    "코디방법": {
      "아우터": "어깨에_걸침",
      "상의": "크롭_배꼽노출",
      "하의": "정상착용",
      "헤드웨어": "정방향",
      "주얼리": "레이어드_여러개",
      "가방": "크로스바디_앞으로"
    }
  },

  "비주얼_무드": {
    "preset_id": "COOL_MINIMAL_01",
    "필름_텍스처": {
      "질감": "slight grain, editorial feel",
      "보정법": "faded black, high contrast"
    },
    "컬러_그레이딩": {
      "주요색조": "cool muted, neutral-cool",
      "채도": "slightly muted",
      "노출": "balanced"
    },
    "조명": {
      "광원": "자연광흐림",
      "방향": "45 degrees, front-side",
      "그림자": "soft minimal"
    }
  },

  "촬영_세팅": {
    "preset_id": "confident_standing_none_hand_on_hip",
    "프레이밍": "MFS",
    "렌즈": "50mm",
    "앵글": "3/4측면",
    "높이": "눈높이",
    "구도": "중앙",
    "조리개": "f/2.8"
  },

  "출력품질": "professional fashion photography, high-end editorial, sharp focus, 8K quality",
  "네거티브": "bright smile, teeth showing, golden hour, warm amber, plastic skin, deformed fingers"
}
```

---

**데이터 소스:** mlb-style-library.json + 실제 촬영본 147장 VLM 분석 (2026-02-10)
**스키마 기준:** influencer_prompt_schema.json v1.0 + MLB 고유 확장
