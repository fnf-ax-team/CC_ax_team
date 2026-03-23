---
name: selfie
description: 셀카/인플루언서 스타일 이미지 생성 - DB 기반 프리셋 + 호환성 자동 검증
user-invocable: true
trigger-keywords: ["셀카", "셀피", "인플", "인플루언서", "셀럽", "셀카 만들어", "예쁜 사진"]
---

# 셀카 이미지 생성 v7.1

> **DB 기반 프리셋 + 호환성 자동 검증 + 표정 프리셋**
>
> 75개 포즈 x 98개 씬 x 10개 표정 (JSON DB) + 레퍼런스 이미지 자동 연결

---

## 절대 규칙 (CRITICAL)

1. **필수 모델**: gemini-3-pro-image-preview
2. **한국어 프롬프트로 짧고 심플하게** (영어 엔지니어링 금지)
3. **얼굴 이미지 반드시 API 전송** - 얼굴 동일성 보장
4. **호환성 자동 검증** - 거울셀피+야외 등 불가능한 조합 자동 차단

### 금지 모델

```
gemini-2.0-flash-exp (품질 낮음)
gemini-2.0-flash (이미지 생성 미지원)
gemini-2.5-flash (텍스트 전용)
```

### 기본 파라미터

| 항목 | 값 |
|------|-----|
| **모델** | `gemini-3-pro-image-preview` |
| **Temperature** | `0.7` |
| **Aspect Ratio** | `9:16` (스토리/릴스) |
| **해상도** | `2K` (2048px) |
| **비주얼 무드** | `OUTDOOR_CASUAL_001` (SNS용) |

---

## 비주얼 무드 프리셋 (CRITICAL)

**셀카는 SNS용 프리셋 사용**

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

## 필수 리소스

```
db/pose_presets.json       <- 포즈 DB (75개)
db/scene_presets.json      <- 씬 DB (98개) + 레퍼런스 이미지 경로
db/expression_presets.json <- 표정 DB (10개) + 레퍼런스 이미지 경로

core/selfie/               <- 실행 모듈
core/selfie/db_loader.py   <- DB 로더 (포즈/씬/표정)
core/selfie/compatibility.py <- 호환성 검증
core/selfie/generator.py   <- v3 생성 함수
core/selfie/validator.py   <- 검증 모듈
```

---

## v7.1 핵심: DB 기반 + 호환성 자동 검증 + 표정 프리셋

### 데이터 구조

**포즈 DB (pose_presets.json)**
- 75개 포즈
- 각 포즈별 왼팔/오른팔/왼손/오른손/왼다리/오른다리/힙 상세 기술
- stance 타입: stand, walk, sit, lean_wall, kneel

**씬 DB (scene_presets.json)**
- 98개 씬
- 레퍼런스 이미지 경로 포함
- 태그 기반 검색 지원
- 호환성 규칙 내장

**표정 DB (expression_presets.json)**
- 10개 표정 (시크 5개 + 러블리 5개)
- 레퍼런스 이미지 경로 포함
- VLM 분석 정보 (눈/입/시선/전체분위기)
- 윙크 표정 구분 (is_wink, wink_eye)

### 호환성 자동 필터 (CRITICAL)

| 포즈 카테고리 | 호환 배경 | 차단 배경 |
|--------------|----------|----------|
| **전신** (21개) | ALL (9개 카테고리) | - |
| **상반신** (21개) | 8개 카테고리 | 횡단보도 |
| **앉기** (21개) | 핫플카페, 힙라이프, 지하철 | 횡단보도 |
| **거울셀피** (12개) | 엘레베이터, 힙라이프(일부), 지하철(일부) | 야외 전체 |

**특수 예외:**
- `힙라이프_05` (락커룸) → 거울셀피 가능

**지하철 + 거울셀피 규칙 (CRITICAL):**
- **역사/승강장 (허용)**: 지하철_02, 지하철_03, 지하철_04, 지하철_07, 지하철_09
  - 이유: 역사에는 유리문, 광고판 유리, 안전문 등 반사면 존재
- **전동차 내부 (금지)**: 지하철_05, 지하철_06, 지하철_08, 지하철_10
  - 이유: 지하철 칸 안에는 거울이 없음 → 비현실적 조합

---

## 카테고리 목록 (JSON DB 기준)

### 포즈 (4개 카테고리, 75개)

| 카테고리 | 개수 | stance | 설명 |
|----------|------|--------|------|
| **전신** | 21개 | stand, walk, lean_wall | 걷기, 기대기, S라인 |
| **상반신** | 21개 | stand, lean_wall | 팔올리기, 소품, 턱괴기 |
| **앉기** | 21개 | sit | 쪼그려, 계단, 바닥, 벤치 |
| **거울셀피** | 12개 | stand, kneel, lean | 플래시, 자연광, V포즈 |

### 배경 (9개 카테고리, 98개)

| 카테고리 | 개수 | 태그 예시 | 호환 포즈 |
|----------|------|----------|----------|
| **핫플카페** | 21개 | 파리, 멜버른, 도쿄, 한옥 | 전신, 상반신, 앉기 |
| **그래피티** | 15개 | 뉴욕, 런던, LA, 베를린 | 전신, 상반신 |
| **철문** | 10개 | 을지로, 브루클린, 그리스 | 전신, 상반신 |
| **기타문** | 10개 | 파리, 런던, 모로코, 청담 | 전신, 상반신 |
| **해외스트릿** | 10개 | 런던, 파리, 뉴욕, 로마 | 전신, 상반신 |
| **힙라이프** | 11개 | 레코드샵, 네온, 편의점 | 전신, 상반신, 앉기, 거울(일부) |
| **지하철** | 11개 | 뉴욕, 파리, 도쿄, 서울 | 전신, 상반신, 앉기, 거울(일부) |
| **엘레베이터** | 5개 | 오피스, 갤러리, 아파트 | 전신, 상반신, 거울셀피 |
| **횡단보도** | 5개 | 파리, 뉴욕, 부다페스트 | 전신만 |

### 표정 (2개 카테고리, 10개 프리셋)

**expression_presets.json 기반** - 레퍼런스 이미지 포함

| 카테고리 | 개수 | 설명 | 윙크 |
|----------|------|------|------|
| **시크** | 5개 | 도도하고 쿨한 표정, 무표정에 가까운 자신감 | 1개 (왼눈) |
| **러블리** | 5개 | 사랑스럽고 부드러운 미소, 청순한 눈빛 | 1개 (오른눈) |

**표정 프리셋 ID 예시:**
- `시크_01` ~ `시크_05`
- `러블리_01` ~ `러블리_05`

**윙크 표정:**
- `시크_04`: 왼쪽 눈 윙크 (is_wink=true, wink_eye="left")
- `러블리_02`: 오른쪽 눈 윙크 (is_wink=true, wink_eye="right")

---

## 실행 파이프라인 (v7.1)

```
1. 입력 수집      → 얼굴 + 포즈 카테고리 + 배경 카테고리 + 표정 카테고리
2. 호환성 검증    → is_compatible() 자동 필터
3. 랜덤 조합      → 포즈/씬/표정 각각 N개 랜덤 선택
4. 프롬프트 조립  → build_prompt_from_db() + 레퍼런스 이미지 (씬/표정)
5. 생성+검증     → generate_batch_v3() + SelfieValidator
```

---

## 대화형 워크플로 (CRITICAL)

**스킬 실행 시 반드시 순차 질문으로 시작하라.**

### Step 1: 입력 수집

| 순서 | 질문 | 필수 | 기본값 |
|------|------|------|--------|
| 1 | 얼굴 이미지 경로 | YES | - |
| 2 | 착장 이미지 경로 | NO | 자유 |
| 3 | 표정 카테고리 | YES | 시크 |
| 4 | 포즈 카테고리 | YES | 전신 |
| 5 | 배경 카테고리 | YES | **호환되는 것만 표시** |
| 6 | 수량/비율/화질 | YES | 3장, 9:16, 2K |

### Step 2: 클릭 옵션 (AskUserQuestion)

**1단계 - 표정:**

| 옵션 | 설명 |
|------|------|
| 시크 | 무표정, 당당, 도도, 쿨한 눈빛 |
| 러블리 | 사랑스러움, 미소, 청순 |
| 자연스러움 | 편안, 일상적, 힘 뺀 표정 |
| 도발적 | 끼부리는, 몽환적 |

**2단계 - 포즈 카테고리:**

| 옵션 | 개수 | 설명 |
|------|------|------|
| 전신 | 21개 | 걷기, 기대기, S라인, 다리들기 |
| 상반신 | 21개 | 팔올리기, 소품 들기, 턱괴기 |
| 앉기 | 21개 | 쪼그려, 계단, 바닥, 벤치 |
| 거울셀피 | 12개 | 플래시, 자연광, 전신거울 |

**3단계 - 배경 카테고리 (호환되는 것만 표시):**

```python
# 포즈 선택 후 → 호환 배경만 옵션으로 제시
compatible = get_compatible_scene_categories(pose_category)
```

| 포즈 → 배경 옵션 |
|-----------------|
| 전신 → 9개 전체 |
| 상반신 → 8개 (횡단보도 제외) |
| 앉기 → 핫플카페, 힙라이프, 지하철 |
| 거울셀피 → 엘레베이터, 힙라이프, 지하철 |

**4단계 - 비율/수량/화질:**

| 항목 | 옵션들 |
|------|--------|
| **비율** | 1:1 정사각, 3:4 세로화보, 4:5 인스타피드, **9:16 스토리/릴스 (기본)**, 16:9 유튜브 |
| **수량** | 1장 (190원), 3장 (570원), 5장 (950원), 10장 (1,900원) |
| **화질** | 1K 테스트, **2K 기본**, 4K 고화질 |

---

## 모듈 인터페이스 (v7.1)

### 1. DB 조회

```python
from core.selfie import (
    # 포즈
    get_pose_categories,
    get_poses_by_category,
    get_pose_by_id,
    # 씬
    get_scene_categories,
    get_scenes_by_category,
    get_scene_by_id,
    # 표정
    get_expression_categories,
    get_expressions_by_category,
    get_expression_by_id,
    get_random_expressions,
    get_wink_expressions,
    # 공통
    get_category_summary,
)

# 카테고리 목록
pose_cats = get_pose_categories()  # ["전신", "상반신", "앉기", "거울셀피"]
scene_cats = get_scene_categories()  # ["핫플카페", "그래피티", ...]
expr_cats = get_expression_categories()  # ["시크", "러블리"]

# 카테고리별 프리셋
poses = get_poses_by_category("전신")  # 21개 포즈 dict 리스트
scenes = get_scenes_by_category("핫플카페")  # 21개 씬 dict 리스트
expressions = get_expressions_by_category("시크")  # 5개 표정 dict 리스트

# ID로 개별 조회
expr = get_expression_by_id("시크_01")  # 표정 dict

# 랜덤 선택
random_exprs = get_random_expressions("러블리", count=3)  # 3개 랜덤 선택
random_exprs = get_random_expressions(None, count=3)  # 전체에서 3개 랜덤
random_exprs = get_random_expressions("시크", count=3, exclude_wink=True)  # 윙크 제외

# 윙크 표정만
winks = get_wink_expressions()  # [시크_04, 러블리_02]

# 전체 요약
summary = get_category_summary()
# {"poses": {...}, "scenes": {...}, "expressions": {"시크": {"count": 5, ...}, "러블리": {...}}}
```

### 2. 호환성 검증

```python
from core.selfie import (
    is_compatible,
    get_compatible_scene_categories,
    get_compatible_scenes,
)

# 호환 여부 확인
is_compatible("거울셀피", "엘레베이터")  # True
is_compatible("거울셀피", "횡단보도")    # False

# 호환 배경 카테고리 목록
compatible = get_compatible_scene_categories("거울셀피")
# ["엘레베이터", "힙스트릿라이프스타일", "지하철"]

# 호환 씬 목록 (예외 처리 포함)
scenes = get_compatible_scenes("거울셀피", "지하철")
# [scene_지하철_07, scene_지하철_07_mirror] (2개만 반환)
```

### 3. 프롬프트 조립

```python
from core.selfie import build_prompt_from_db

prompt = build_prompt_from_db(
    pose=pose_dict,           # DB에서 로드한 포즈
    scene=scene_dict,         # DB에서 로드한 씬
    gender="female",
    expression="시크",
    makeup="natural",
    outfit_analysis=None,     # 선택
)
```

### 4. 배치 생성 (v3 핵심)

```python
from core.selfie import generate_batch_v3

results = generate_batch_v3(
    face_images=["face.jpg"],
    pose_category="전신",            # 포즈 카테고리
    scene_category="핫플카페",        # 배경 카테고리 (호환성 자동 검증)
    count=3,                         # 생성 수량
    expression="시크",               # 표정: 카테고리 str 또는 프리셋 Dict
    expression_category="시크",      # 표정 카테고리 (랜덤 선택용)
    gender="female",
    makeup="natural",
    outfit_images=None,              # 선택
    aspect_ratio="9:16",
    resolution="2K",
    temperature=0.7,
    use_reference_image=True,        # 씬 레퍼런스 이미지 사용
    use_expression_reference=True,   # 표정 레퍼런스 이미지 사용
    validator=None,                  # SelfieValidator 인스턴스 (선택)
    max_retries=2,
)

# 반환:
# [
#     {
#         "image": PIL.Image,
#         "pose": {"id": "전신_01", ...},
#         "scene": {"id": "scene_핫플카페_03", ...},
#         "expression": {"id": "시크_01", ...},  # 표정 프리셋 정보
#         "score": 85,
#         "passed": True,
#         "attempts": 1,
#     },
#     ...
# ]
```

**표정 파라미터 사용법:**

| 방식 | expression 값 | expression_category | 결과 |
|------|---------------|---------------------|------|
| **카테고리에서 랜덤** | `"시크"` | `"시크"` | 시크 5개 중 랜덤 선택 |
| **전체에서 랜덤** | `"시크"` | `None` | 전체 10개 중 랜덤 선택 |
| **특정 프리셋 고정** | `{프리셋 dict}` | 무시됨 | 해당 프리셋 고정 사용 |
| **프리셋 리스트** | `[프리셋1, 프리셋2, ...]` | 무시됨 | 순서대로 적용 |

**레퍼런스 이미지:**
- `use_expression_reference=True` 설정 시 표정 프리셋의 `image_path`를 API에 전송
- VLM 분석된 표정 상세 (눈, 입, 시선 등)가 프롬프트에 자동 포함

### 5. 랜덤 조합 미리보기

```python
from core.selfie import get_random_combinations

# 생성 전 조합 확인
combinations = get_random_combinations(
    pose_category="전신",
    scene_category="그래피티",
    count=3,
)
# [(pose_dict, scene_dict), (pose_dict, scene_dict), ...]

for pose, scene in combinations:
    print(f"Pose: {pose['id']} | Scene: {scene['id']}")
    print(f"  Tags: {scene.get('tags', [])}")
```

---

## 검증 기준 (5개 기준)

| 항목 | 비중 | 설명 |
|------|------|------|
| **realism** | 35% | 실제 사진처럼 보이는가 |
| **person_preservation** | 25% | 얼굴이 참조 이미지와 같은 사람인가 |
| **scenario_fit** | 20% | 장소/상황/옷이 자연스럽게 어울리는가 |
| **skin_condition** | 10% | 피부 질감이 자연스러운가 (AI 플라스틱 피부 X) |
| **anti_polish_factor** | 10% | 너무 완벽하지 않은가 (약간의 결점이 자연스러움) |

**핵심 원칙: "너무 잘 나오면 실패"**

**등급**: S/A(90+ 바로사용), B(75+ 확인필요), C/F(75- 재생성)

**Auto-Fail**: 손가락 6개+, 얼굴 불일치, 누런 톤, AI 플라스틱 피부

---

## 레퍼런스 이미지 자동 연결

v7.1의 핵심 개선: **씬/표정 DB에 레퍼런스 이미지 경로가 포함됨**

### 씬 레퍼런스

```python
from core.selfie import get_reference_image_path

# 씬의 레퍼런스 이미지 경로 가져오기
ref_path = get_reference_image_path(scene)
# "D:/FNF_Studio_TEST/.../4. 배경/1. 핫플카페/핫플 카페 (3).png"
```

`generate_batch_v3(use_reference_image=True)` 설정 시:
- 자동으로 레퍼런스 이미지 로드
- API에 배경 레퍼런스로 전송
- 배경 정확도 대폭 향상

### 표정 레퍼런스 (v7.1 신규)

```python
from core.selfie import get_expression_reference_image_path

# 표정 프리셋의 레퍼런스 이미지 경로 가져오기
expr = get_expression_by_id("시크_01")
expr_ref_path = get_expression_reference_image_path(expr)
# "db/model/expressions/시크/시크_01.jpg"
```

`generate_batch_v3(use_expression_reference=True)` 설정 시:
- 표정 프리셋의 레퍼런스 이미지 자동 로드
- API에 표정 가이드 이미지로 전송
- 눈/입/시선 등 상세 표정 재현 정확도 향상

**표정 프리셋 구조:**
```json
{
  "id": "시크_01",
  "name": "시크무드_무표정",
  "image_path": "db/model/expressions/시크/시크_01.jpg",
  "vlm_analysis": {
    "눈": "살짝 치켜뜬 아몬드형 눈, 무심한 듯 날카로운 시선",
    "입": "일자로 다문 입술, 힘 뺀 자연스러운 상태",
    "시선": "카메라를 직접 응시, 도전적인 느낌",
    "전체분위기": "도도하고 자신감 있는, 쿨한 분위기"
  }
}
```

---

## 에러 핸들링

| 에러 | 복구 액션 |
|------|----------|
| 호환성 불일치 | 자동 차단 + 호환 배경 안내 |
| API Timeout | 최대 3회 재시도 (5s, 10s, 15s) |
| Rate Limit (429) | 60초 대기 후 재시도 |
| 얼굴 안 닮음 | 정면 얼빡 참조 이미지 사용 |
| 레퍼런스 없음 | 텍스트 프롬프트로 폴백 |

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 거울셀피인데 야외 | 호환성 무시 | `is_compatible()` 사용 |
| 포즈가 다름 | 레퍼런스 미사용 | `use_reference_image=True` |
| 배경 분위기 다름 | 태그 불일치 | `get_scenes_by_tags()` 사용 |
| 다 비슷함 | 랜덤 범위 좁음 | 다른 카테고리 시도 |
| 얼굴 안 닮음 | 참조 이미지 품질 | 정면 얼빡 이미지 |
| 누런 톤 | 프롬프트 누락 | 쿨톤 지시 확인 |

---

## 출력

```
Fnf_studio_outputs/selfie/{YYYYMMDD_HHMMSS}_{설명}/
├── images/
│   ├── input_face_01.jpg
│   ├── output_001.jpg
│   ├── output_002.jpg
│   └── output_003.jpg
├── prompt.json
├── config.json
└── validation.json
```

---

## 사용법

CLI:
```
/셀카
```

Claude가 순차 질문 → 호환성 검증 → 랜덤 조합 → 생성 → 검증

---

**버전**: 7.1.0 (표정 프리셋 DB 연결)
**작성일**: 2026-02-27

**변경사항 (v7.1.0)**:
- **표정 프리셋 DB 연결** - expression_presets.json (10개, 2개 카테고리)
- **표정 레퍼런스 이미지** - 표정 프리셋에 image_path 포함, API 전송 지원
- **VLM 분석 표정** - 눈/입/시선/분위기 상세 분석 포함
- **윙크 표정 지원** - is_wink, wink_eye 필드로 윙크 방향 구분
- **새 API 함수** - `get_expression_categories()`, `get_expressions_by_category()`, `get_random_expressions()`, `get_wink_expressions()`, `get_expression_reference_image_path()`
- **generate_batch_v3 개선** - `expression_category`, `use_expression_reference` 파라미터 추가

**변경사항 (v7.0.0)**:
- **JSON DB 도입** - pose_presets.json (75개), scene_presets.json (98개)
- **호환성 자동 검증** - 거울셀피+야외 등 불가능한 조합 자동 차단
- **레퍼런스 이미지 자동 연결** - 씬 DB에 이미지 경로 포함
- **새 API 함수** - `generate_batch_v3()`, `is_compatible()`, `get_compatible_scenes()`
- **모듈 분리** - db_loader.py, compatibility.py 추가

**변경사항 (v6.1.0)**:
- 카테고리 기반 선택 - 프리셋 대신 카테고리만 선택
- 랜덤 조합 로직 - N장 요청 시 N개 다른 조합

**변경사항 (v6.0.0)**:
- 포즈 프리셋 v2.0 (45+종)
- 배경 프리셋 v2.0 (45+종)
