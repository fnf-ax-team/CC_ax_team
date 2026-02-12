# MLB 프롬프트 치트시트

> v6.5.0 | 최종 업데이트: 2026-02-10
>
> **v6.5.0: 모든 옵션 매핑 테이블에 빈도(%) 컬럼 추가 - 라이브러리로 활용 가능**

---

## JSON 스키마

```json
{
  "주제": {
    "character": "필름 그레인 질감, 에디토리얼 패션 사진 스타일",
    "mood": ""
  },
  "모델": {
    "민족": "",
    "성별": "",
    "나이": ""
  },
  "헤어": {
    "스타일": "",
    "컬러": "",
    "질감": ""
  },
  "메이크업": {
    "베이스": "",
    "블러셔": "",
    "립": "",
    "아이": ""
  },
  "촬영": {
    "프레이밍": "",
    "렌즈": "",
    "앵글": "",
    "높이": "",
    "구도": "",
    "조리개": "f/2.8"
  },
  "포즈": {
    "stance": "",
    "왼팔": "",
    "오른팔": "",
    "왼손": "",
    "오른손": "",
    "왼다리": "",
    "오른다리": "",
    "힙": ""
  },
  "표정": {
    "베이스": "",
    "바이브": "",
    "시선": "",
    "입": ""
  },
  "착장": {
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
  },
  "배경": {
    "장소": "",
    "배경상세": ""
  },
  "조명색감": {
    "조명": "",
    "색보정": ""
  },
  "출력품질": "professional fashion photography, high-end editorial, sharp focus, 8K quality",
  "네거티브": ""
}
```

---

## 기본값 (미입력시 자동 적용)

| 카테고리 | 필드 | 기본값 | 빈도 |
|---------|------|--------|------|
| 모델 | 민족 | korean | - |
| 모델 | 성별 | female | - |
| 모델 | 나이 | early_20s | - |
| 헤어 | 스타일 | straight_loose | 95% |
| 헤어 | 컬러 | black | 100% |
| 헤어 | 질감 | sleek | 70% |
| 메이크업 | 베이스 | natural | 85% |
| 메이크업 | 블러셔 | none | 60% |
| 메이크업 | 립 | mlbb | 50% |
| 메이크업 | 아이 | natural | 60% |
| 촬영 | 프레이밍 | MS | 40% |
| 촬영 | 렌즈 | 50mm | - |
| 촬영 | 앵글 | 3/4측면 | 40% |
| 촬영 | 높이 | 눈높이 | 80% |
| 촬영 | 구도 | 중앙 | 70% |
| 촬영 | 조리개 | f/2.8 (고정) | - |
| 포즈 | stance | stand | 40% |
| 포즈 | 왼팔 | natural | 30% |
| 포즈 | 오른팔 | relaxed | 25% |
| 포즈 | 왼손/오른손 | relaxed | 70% |
| 포즈 | 왼다리 | support | 60% |
| 포즈 | 오른다리 | knee_10 | 20% |
| 포즈 | 힙 | neutral | 60% |
| 표정 | 베이스 | cool | 50% |
| 표정 | 바이브 | mysterious | 40% |
| 표정 | 시선 | direct | 50% |
| 표정 | 입 | closed | 60% |
| 코디방법 | 아우터 | 정상착용 | `worn normally` |
| 코디방법 | 상의 | 한쪽어깨노출 | `off-shoulder on one side` |
| 코디방법 | 하의 | 정상착용 | `worn normally` |
| 코디방법 | 헤드웨어 | 정상착용 | `worn normally` |
| 코디방법 | 주얼리 | 정상착용 | `worn normally` |
| 코디방법 | 가방 | 정상착용 | `worn normally` |
| 코디방법 | 벨트 | 장식용 | `decorative styling` |
| 배경 | 장소 | 콘크리트 | 40% |
| 조명색감 | 조명 | 자연광흐림 | 45% |
| 조명색감 | 색보정 | 뉴트럴쿨 | 60% |

---

## 브랜드 DNA (DO & DON'T)

1. **큰 아몬드눈** 필수 - 쿨함은 입/태도로만
2. **쿨톤만** - 골든아워 절대 금지
3. 모델이 주인공, 배경은 조연
4. f/2.8로 배경 흐림
5. Languid Chic - 지루한 부자 아이 미학

### 스타일링 공식

- **미드리프 노출률**: 81%
- **체인 착용률**: 62.5%
- **오버사이즈 아우터**: 2-3사이즈 업

### 금지

- 골든/앰버/웜톤
- 익스트림 클로즈업
- 밝은 미소/치아 노출

---

## 옵션 값 + 프롬프트 매핑

### 모델

| ID | 한글 | Prompt |
|----|------|--------|
| korean | 한국인 | `Korean female model` |
| east_asian | 동아시아 | `East Asian female model` |
| mixed | 혼혈 | `Mixed Asian female model` |
| late_teens | 10대후반 | `late teens, fresh` |
| early_20s | 20대초반 | `early 20s, youthful` |
| mid_20s | 20대중반 | `mid 20s, confident` |

### 헤어

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| straight_loose | 스트레이트루즈 | `long straight hair, loose and flowing, sleek` | 95% |
| wavy | 웨이브 | `wavy hair, soft waves` | 5% |
| black | 블랙 | `black hair` | 100% |
| dark_brown | 다크브라운 | `dark brown hair` | - |
| sleek | 슬릭 | `sleek, glossy` | 70% |
| natural | 내추럴 | `natural texture` | 30% |

### 메이크업

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| natural | 내추럴베이스 | `natural skin, minimal foundation` | 85% |
| dewy | 듀이 | `dewy glass skin finish` | 15% |
| none | 블러셔없음 | (없음) | 60% |
| subtle_peach | 피치블러셔 | `subtle peach blush` | 40% |
| mlbb | MLBB립 | `MLBB lip color, my lips but better` | 50% |
| nude | 누드립 | `nude lip` | 30% |
| muted_pink | 뮤트핑크 | `muted pink lip` | 20% |
| natural | 내추럴아이 | `natural eye makeup` | 60% |
| brown_neutral | 브라운뉴트럴 | `brown neutral eyeshadow` | 25% |
| soft_smoky | 소프트스모키 | `soft smoky eye` | 15% |

### 촬영

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| MS | 허리위 | `medium shot framing, waist up` | 40% |
| MFS | 무릎위 | `medium full shot, knees up` | 30% |
| MCU | 가슴위 | `medium close-up, chest up` | 20% |
| CU | 얼굴 | `close-up, shoulders and face` | 10% |
| 35mm | 환경 | `35mm lens, wider environmental portrait` | - |
| 50mm | 기본 | `50mm lens, standard portrait perspective` | - |
| 85mm | 인물강조 | `85mm lens, compressed background` | - |
| 정면 | 친근 | `camera at eye level, frontal angle` | 35% |
| 3/4측면 | 입체감 | `camera 15 degrees to subject's side, 3/4 profile view` | 40% |
| 측면 | 시크 | `camera 30 degrees, side profile` | 5% |
| 약간측면 | 미세변화 | `camera 10 degrees off-center` | 20% |
| 살짝로앵글 | 파워감 | `camera 10cm below eye level` | 20% |
| 눈높이 | 친근 | `camera at eye level` | 80% |
| 중앙 | 중앙구도 | `subject centered in frame, balanced composition` | 70% |
| 왼쪽1/3 | 삼분할왼쪽 | `subject positioned at left third, rule of thirds` | 15% |
| 오른쪽1/3 | 삼분할오른쪽 | `subject positioned at right third, look room on left` | 15% |

---

## 포즈

### Stance (차량 없음)

| ID | 한글 | Prompt | 사용 배경 | 빈도 |
|----|------|--------|----------|------|
| stand | 자신감스탠딩 | `confident standing pose, weight shifted to one leg, contrapposto stance` | 메탈패널, 창고, 콘크리트 | 40% |
| lean_wall | 벽기대기 | `relaxed lean against concrete wall, casual cool posture` | 메탈패널, 창고, 콘크리트 | 10% |
| sit | 앉기 | `seated pose with confident posture on elevated surface` | 창고 | 5% |
| walk | 걷기 | `walking pose with confident stride` | 모든 배경 | 5% |
| lean_railing | 레일링기대기 | `relaxed lean against metal railing, hip against railing` | 창고, 산업공간 | - |
| sit_crouch | 쪼그려앉기 | `crouching or kneeling pose on ground, relaxed crouch` | 창고, 콘크리트 | - |
| back_look | 뒤돌아보기 | `back to camera, looking over shoulder, torso rotated 120 degrees` | 모든 배경 | - |

### Stance (차량 있음)

| ID | 한글 | Prompt | 사용 배경 | 빈도 |
|----|------|--------|----------|------|
| lean_car | 차기대기 | `relaxed lean against luxury vehicle` | 럭셔리SUV, 빈티지카, 지하주차장 | 25% |
| sit_car | 차앉기 | `seated on car hood or trunk` | 럭셔리SUV, 빈티지카 | 15% |
| bumper_foot | 범퍼발 | `foot resting on car bumper` | 럭셔리SUV, 빈티지카 | - |
| door_lean | 차문기대기 | `leaning against car door` | 럭셔리SUV, 빈티지카, 지하주차장 | - |
| lean_car_window | 차창기대기 | `relaxed lean with arm resting on car window frame` | 럭셔리SUV, 빈티지카 | - |

### 팔/손

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| hip | 허리손 | `one hand on hip with attitude, arm bent at elbow` | - |
| pocket | 주머니손 | `hand casually in pocket` | 15% |
| crossed | 팔짱 | `arms loosely crossed with attitude` | 5% |
| hat | 모자터치 | `hand touching hat brim dismissively` | 10% |
| chin | 턱받침 | `hand supporting chin, fingers relaxed` | 5% |
| behind | 뒤로손 | `hands behind back` | - |
| natural | 자연내림 | `arm hanging naturally, relaxed` | 30% |
| relaxed | 릴렉스내림 | `arm hanging relaxed, slightly bent at elbow` | 25% |
| face | 얼굴터치 | `arm bent at elbow, hand near face, fingers gently touching` | - |
| extend_wall | 벽뻗기 | `arm extended, hand touching wall` | - |
| extend_pole | 기둥뻗기 | `arm extended, hand on pole` | - |
| across | 가슴가로지르기 | `arm across chest, hand touching other arm` | - |
| on_legs | 무릎손 | `arms resting on legs` | - |
| car_hand | 차에손 | `hand resting on car` | - |
| car_roof | 차지붕손 | `arm resting on car roof` | - |
| car_door | 차문손 | `hand on car door` | 10% |
| car_window_arm | 차창팔걸침 | `arm resting on car window frame, elbow on door` | - |

### 손 디테일

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| relaxed | 릴렉스 | `fingers relaxed` | 70% |
| curled | 살짝굽힘 | `fingers relaxed, slightly curled` | - |
| spread | 살짝벌림 | `fingers relaxed, slightly spread` | - |
| chin_touch | 턱받침 | `fingers supporting chin` | - |
| face_touch | 얼굴터치 | `fingers gently touching face` | - |

### 다리

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| support | 지지다리 | `straight support leg` | 60% |
| knee_10 | 무릎10도 | `slightly bent at knee 10 degrees` | 20% |
| knee_45 | 무릎45도 | `bent at knee 45 degrees` | 10% |
| knee_90 | 무릎90도 | `bent at knee 90 degrees` | - |
| crossed_leg | 다리교차 | `crossed over other leg at knee` | 10% |
| car_bumper | 차범퍼발 | `foot resting on car bumper` | - |
| car_tire | 차타이어발 | `foot resting on car tire` | - |

### 힙

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| neutral | 중립 | `hips neutral, balanced stance` | 60% |
| pop_right | 오른쪽빼기 | `hip popped to right, contrapposto` | 20% |
| pop_left | 왼쪽빼기 | `hip popped to left, weight shifted` | 15% |
| back | 뒤로빼기 | `hips pushed back, slight lean forward` | 5% |
| low | 낮춤 | `hips lowered, relaxed slouch` | - |

---

## 표정

### 베이스

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| cool | 쿨 | `cool expression, unbothered attitude, expression intensity 5-6` | 50% |
| natural | 내추럴 | `natural subtle smile, relaxed composure, expression intensity 4-5` | 25% |
| dreamy | 몽환 | `dreamy expression, distant contemplative mood, expression intensity 3-4` | - |
| neutral | 뉴트럴 | `neutral expression, blank but confident, expression intensity 4` | 15% |
| serious | 시리어스 | `serious expression, intense focus, expression intensity 6-7` | 10% |

### 바이브

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| mysterious | 미스테리어스 | `mysterious vibe, enigmatic presence` | 40% |
| approachable | 어프로처블 | `approachable vibe, accessible coolness` | 25% |
| sophisticated | 소피스티케이티드 | `sophisticated vibe, refined elegance` | 35% |

### 시선

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| direct | 직시 | `direct but disinterested gaze at camera` | 50% |
| past | 허공응시 | `looking slightly past camera, distant focus` | 30% |
| side | 곁눈질 | `subtle side glance, mysterious` | 20% |

### 입

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| closed | 닫힌입 | `mouth closed in neutral position, lips together` | 60% |
| parted | 살짝벌림 | `lips slightly parted, relaxed mouth` | 30% |
| smile | 미세미소 | `subtle hint of smile, corners barely raised` | 10% |

---

## 착장 스타일링

### 헤드웨어

| ID | 한글 | Prompt |
|----|------|--------|
| mlb_cap | MLB캡 | `MLB baseball cap` |
| beanie | 비니 | `MLB beanie with logo` |

### 주얼리

| ID | 한글 | Prompt |
|----|------|--------|
| chain_necklace | 체인목걸이 | `gold chain necklace, chunky link chain` |
| layered_necklace | 레이어드목걸이 | `layered necklaces, multiple chains` |
| hoop_earring | 후프귀걸이 | `gold hoop earrings` |
| stud_earring | 스터드귀걸이 | `small stud earrings` |
| rings | 반지 | `rings on fingers, minimal jewelry` |

### 가방/벨트

| ID | 한글 | Prompt |
|----|------|--------|
| chain_belt | 체인벨트 | `chain belt at waist, decorative belt` |
| crossbody_bag | 크로스바디백 | `MLB crossbody bag, small shoulder bag` |
| hobo_bag | 호보백 | `MLB hobo bag, slouchy shoulder bag` |

---

## 코디방법 (어떻게 입는지)

| 아이템 | ID | 한글 | Prompt |
|--------|---|------|--------|
| 아우터 | 정상착용 | 정상 | `worn normally` |
| 아우터 | 어깨걸침 | 걸침 | `jacket draped over shoulder` |
| 아우터 | 한쪽만착용 | 한쪽 | `worn on one arm only` |
| 아우터 | 지퍼오픈 | 오픈 | `zipper open` |
| 아우터 | 지퍼클로즈 | 클로즈 | `zipper closed` |
| 아우터 | 손에들고 | 손 | `held in hand` |
| 상의 | 정상착용 | 정상 | `worn normally` |
| 상의 | 크롭 | 크롭 | `cropped above waist` |
| 상의 | 넣어입기 | 인 | `tucked into pants` |
| 상의 | 한쪽어깨노출 | 어깨 | `off-shoulder on one side` |
| 상의 | 버튼오픈 | 오픈 | `buttons open` |
| 상의 | 오버사이즈 | 오버 | `oversized fit, 2-3 sizes up` |
| 하의 | 정상착용 | 정상 | `worn normally` |
| 하의 | 하이웨이스트 | 하이 | `high-waisted fit` |
| 하의 | 로우웨이스트 | 로우 | `low-rise fit` |
| 하의 | 롤업 | 롤업 | `cuffed at ankle` |
| 하의 | 원레그롤업 | 원롤 | `one leg cuffed` |
| 신발 | 정상착용 | 정상 | `worn normally` |
| 신발 | 끈풀림 | 풀림 | `laces untied` |
| 신발 | 뒤꿈치밟기 | 밟기 | `heel stepped down` |
| 헤드웨어 | 정상착용 | 정상 | `worn normally` |
| 헤드웨어 | 뒤로쓰기 | 뒤 | `cap worn backwards` |
| 헤드웨어 | 옆으로쓰기 | 옆 | `cap worn sideways` |
| 헤드웨어 | 살짝올려쓰기 | 올림 | `cap slightly lifted` |
| 헤드웨어 | 손에들고 | 손 | `held in hand` |
| 주얼리 | 정상착용 | 정상 | `worn normally` |
| 주얼리 | 레이어드 | 레이어 | `layered jewelry` |
| 주얼리 | 언발런스 | 언발 | `asymmetric styling` |
| 가방 | 정상착용 | 정상 | `worn normally` |
| 가방 | 크로스바디 | 크로스 | `crossbody wear` |
| 가방 | 숄더 | 숄더 | `shoulder wear` |
| 가방 | 손에들고 | 손 | `held in hand` |
| 가방 | 바닥에놓기 | 바닥 | `placed on ground` |
| 벨트 | 정상착용 | 정상 | `worn normally` |
| 벨트 | 느슨하게 | 느슨 | `worn loosely` |
| 벨트 | 장식용 | 장식 | `decorative styling` |

---

## 배경

| ID | 한글 | Prompt | 타입 | 빈도 |
|----|------|--------|------|------|
| 메탈패널 | 메탈패널 | `sleek gray metallic panel wall, industrial studio backdrop` | 차량없음 | 10% |
| 창고 | 창고 | `industrial warehouse space with metal ladders, raw concrete` | 차량없음 | 5% |
| 콘크리트 | 콘크리트 | `brutalist concrete architecture, raw cement walls` | 차량없음 | 40% |
| 럭셔리SUV | 럭셔리SUV | `silver luxury SUV in industrial garage, matte metallic` | 차량있음 | 20% |
| 빈티지카 | 빈티지카 | `vintage car, classic vehicle` | 차량있음 | 15% |
| 지하주차장 | 지하주차장 | `underground parking garage, concrete pillars` | 차량있음 | 10% |

---

## 조명/색보정

### 조명

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 소프트박스 | 소프트박스 | `softbox lighting at 45 degrees, 5500K neutral temperature` | 20% |
| 스튜디오쿨 | 스튜디오쿨 | `studio lighting with cool temperature, 5500-6000K` | 35% |
| 자연광흐림 | 자연광흐림 | `natural overcast daylight, soft even illumination` | 45% |

### 색보정

| ID | 한글 | Prompt | 빈도 |
|----|------|--------|------|
| 뉴트럴쿨 | 뉴트럴쿨 | `neutral-cool color grade, clean digital look, no warm cast` | 60% |
| 채도낮춤 | 채도낮춤 | `slightly desaturated with cool undertones` | 30% |
| 고대비쿨 | 고대비쿨 | `high contrast with blue shadow tones` | 10% |

---

## 호환 규칙

### 렌즈-프레이밍

| 렌즈 | 권장 프레이밍 |
|------|--------------|
| 85mm | MCU, CU |
| 50mm | MS, MFS, MCU |
| 35mm | MFS, MS |

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

### 배경-포즈 (차량 없음)

| 배경 | 가능 포즈 |
|------|----------|
| 메탈패널 | stand, lean_wall, walk, back_look |
| 창고 | stand, lean_wall, sit, sit_crouch, lean_railing, walk, back_look |
| 콘크리트 | stand, lean_wall, sit_crouch, walk, back_look |

### 배경-포즈 (차량 있음)

| 배경 | 가능 포즈 |
|------|----------|
| 럭셔리SUV | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 빈티지카 | lean_car, lean_car_window, sit_car, bumper_foot, door_lean |
| 지하주차장 | lean_car, door_lean |

---

## 금지 조합

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 1 | 85mm + MFS | 과도한 배경 압축 | 50mm 또는 35mm |
| 2 | 35mm + CU | 광각 왜곡으로 얼굴 변형 | 85mm 또는 50mm |
| 3 | 차량 포즈 + 차량 없는 배경 | 물리적 모순 | 럭셔리SUV/지하주차장 배경 |
| 4 | 차량 없는 포즈 + 차량 배경 | 차 있는데 안 쓰면 어색 | 차량 포즈로 변경 |
| 5 | sit + 메탈패널/콘크리트 | 앉을 곳 없음 | 창고 배경 또는 stand |
| 6 | CU + walk | 걷기는 전신 필요 | MCU 이상 또는 stand |
| 7 | dreamy + direct(정면직시) | 컨셉 충돌 | past 또는 side |
| 8 | serious + smile | 컨셉 충돌 | closed |
| 9 | cool + smile | 쿨한데 미소는 모순 | closed 또는 parted |
| 10 | 골든아워 + MLB | 브랜드 DNA 위반 | 소프트박스 또는 스튜디오쿨 |

---

## 네거티브 프롬프트

### 기본 (항상 적용)

```
bright smile, teeth showing, golden hour, warm amber
```

### 조건부 추가

| 조건 | 추가 네거티브 |
|------|--------------|
| CU 프레이밍 | `full body visible` |
| walk 포즈 | `static pose, standing still` |
| 차량 배경 | `front grille visible, license plate` |

---

---

**데이터 소스:** mlb-style-library.json + 노션 MLB 치트시트 + 실제 촬영본 16장 VLM 분석 (2026-02-10)
