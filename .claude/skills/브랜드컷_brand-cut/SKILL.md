---
name: brand-cut
description: MLB 브랜드컷 생성. 얼굴+착장 → 화보 이미지 생성.
user-invocable: true
trigger-keywords: ["브랜드컷", "화보", "에디토리얼", "룩북", "마케팅컷"]

# 브랜드컷 (Brand Cut) - MLB 마케팅 화보 생성

> 모델 얼굴 + 착장 이미지 → AI 화보 생성
> 

---

## 절대 규칙 (CRITICAL)

1. **착장 이미지 전체 사용 (1순위)** - 절대 빠뜨리면 안됨
2. **얼굴 이미지 반드시 API 전송** - 얼굴 동일성 보장
3. **앵글에 따른 착장 노출 규칙** - 전신샷에서 헤드웨어 누락 시 재생성

## MLB 브랜드 지침

**"Young & Rich" 컨셉 - 고급스러움 필수**

- 차량: 명품 SUV만 (G-Class, Range Rover, Cayenne)
- 배경: 모던/클린/미니멀
- 조명: 쿨톤 유지 (누런 톤 금지)

---

## 필수 리소스

```
.claude/skills/brand-dna/mlb-prompt-cheatsheet.md  ← 프롬프트 치트시트 (반드시 로드)

core/brandcut/                                     ← 실행 모듈
core/mlb_validator.py                               ← 검증 모듈
```

---

## 모듈 구조 (core/brandcut/)

```
core/brandcut/
├── __init__.py           # 모듈 export
├── analyzer.py           # VLM 분석 (착장, 포즈, 무드)
├── prompt_builder.py     # 프롬프트 조립
├── generator.py          # 이미지 생성 (generate_brandcut)
├── retry_generator.py    # 검증+재시도 (generate_with_validation)
├── mlb_validator.py      # MLB 12개 기준 검증
└── templates.py          # VLM 프롬프트 템플릿
```

---

## 실행 파이프라인

```
1. 분석 (VLM)     → analyze_outfit(), analyze_pose_expression(), analyze_mood()
2. 프롬프트 조립   → build_prompt()
3. 배치 생성      → generate_brandcut(num_images=N)
4. 검증+재시도    → generate_with_validation(max_retries=2)
```

### 대화형 질문 ↔ VLM 분석 연결

```
┌────────────────────────────┐     ┌──────────────────────────────┐
│      대화형 질문 수집       │     │         VLM 분석 함수        │
├────────────────────────────┤     ├──────────────────────────────┤
│ 1. 얼굴/착장 경로          │────▶│ analyze_outfit()             │
│ 2. 포즈/표정/구도 레퍼런스 │────▶│ analyze_pose_expression()    │
│ 3. 배경 레퍼런스           │────▶│ (차량 변환 로직)             │
│ 4. 무드 레퍼런스           │────▶│ analyze_mood()               │
│ 5. 비율/수량/화질          │────▶│ -                            │
└────────────────────────────┘     └──────────────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────────────┐
                                   │      build_prompt()          │
                                   │  (분석 결과 통합 → 프롬프트)  │
                                   └──────────────────────────────┘
```

---

## 대화형 워크플로 (CRITICAL)

**⚠️ 스킬 실행 시 반드시 순차 질문으로 시작하라. 코드 실행 전에 모든 입력을 수집해야 한다.**

### Step 1: 입력 수집 (대화형 필수)

사용자에게 순차적으로 질문한다. AskUserQuestion 도구 사용 권장.

| 순서 | 질문 | 필수 | 기본값 |
| --- | --- | --- | --- |
| 1 | 얼굴 이미지 폴더 경로 | ✅ | - |
| 2 | 착장 이미지 폴더 경로 | ✅ | - |
| 3 | 포즈/표정/구도/앵글 레퍼런스 | ❌ | 없음 |
| 4 | 배경 레퍼런스 | ✅ | - |
| 5 | 비율 | ✅ | 3:4 |
| 6 | 수량 | ✅ | 3장 |
| 7 | 화질 | ✅ | 2K |

**포즈 레퍼런스 분석 항목:**

- 포즈 (손/발/몸 위치)
- 표정 (눈빛/입/분위기)
- 구도 (프레이밍/크롭)
- 앵글 (하이앵글/로우앵글/아이레벨)

### 클릭 옵션 (AskUserQuestion)

**1단계 - 경로 입력:**

- 얼굴 이미지 폴더 경로
- 착장 이미지 폴더 경로

**2단계 - 포즈/표정/구도/앵글 레퍼런스:**

| 항목 | 옵션들 |
| --- | --- |
| **레퍼런스(포즈, 표정, 구도, 앵글 참고용)** | 없음, 있음 (경로 입력) |

→ "있음" 선택 시: VLM으로 **포즈, 표정, 구도, 앵글** 전부 분석

**3단계 - 배경 레퍼런스:**

| 항목 | 옵션들 |
| --- | --- |
| **배경** | 포즈 레퍼런스 배경 그대로, 별도 배경 이미지 있음 (경로 입력) |

**배경 차량 자동 변환 로직:**

```
레퍼런스 배경에 차량 있음?
├─ YES → 차량 종류 분석
│   ├─ 명품 SUV (G-Class, Range Rover, Cayenne 등) → 그대로 유지
│   └─ 그 외 (사이버트럭, 일반 차량 등) → 명품 SUV로 변환
└─ NO → 배경 그대로
```

**허용 차량 리스트 (MLB 브랜드 지침):**

- Mercedes-Benz: G-Class, GLE, GLS
- Land Rover: Range Rover
- Porsche: Cayenne
- BMW: X5, X7
- Bentley: Bentayga
- Tesla: Cybertruck

→ 리스트에 있는 차량은 **그대로 유지**
→ 리스트에 없는 차량 (일반 세단, 경차 등)은 **G-Class로 자동 변환**


**4단계 - 무드 레퍼런스:**

| 항목 | 옵션들 |
| --- | --- |
| **무드** | 포즈 레퍼런스 무드 그대로, 별도 무드 이미지 있음 (경로 입력) |

→ "별도 이미지 있음" 선택 시: `analyze_mood()` 호출

**5단계 - 비율/수량/화질 (3개 질문):**

| 항목 | 옵션들 |
| --- | --- |
| **비율** | 1:1,2:3,3:2,3:4,4:3,4:5,5:4,9:16,16:9,21:9 |
| **화질** | 1K 테스트 (₩190/장), 2K 기본 (₩190/장), 4K 고화질 (₩380/장) |
| **수량** | 1장, 3장, 5장, 10장  |

### 비율 전체 목록

| 비율 | 용도 |
|------|------|
| `1:1` | 정사각/프로필 |
| `2:3` | 세로 포트레이트 |
| `3:2` | 가로 랜드스케이프 |
| `3:4` | **세로 화보 (기본)** |
| `4:3` | 가로 화보 |
| `4:5` | 인스타 피드 |
| `5:4` | 가로 피드 |
| `9:16` | 스토리/릴스/숏폼 |
| `16:9` | 유튜브/가로 영상 |
| `21:9` | 시네마틱/울트라와이드 |

### 비용 계산

| 화질 | 장당 비용 | 3장 | 5장 | 10장 |
|------|----------|-----|-----|------|
| 1K~2K | ₩190 | ₩570 | ₩950 | ₩1,900 |
| 4K | ₩380 | ₩1,140 | ₩1,900 | ₩3,800 |

### Step 2: VLM 분석
→ analyze_outfit(), analyze_pose_expression(), analyze_mood()

### Step 3: 프롬프트 조립
→ build_prompt() + 금지 조합 검증

### Step 4: 배치 생성
→ generate_brandcut(num_images=N) - 사용자가 선택한 대로 N장 생성

### Step 5: AI 검증 + 재시도
→ generate_with_validation() - 각 이미지별 검증, 실패 시 재생성

---

## 모듈 인터페이스 (에이전트 호출 규격)

### 1. 착장 분석
```python
from core.brandcut import analyze_outfit, OutfitAnalysis

result: OutfitAnalysis = analyze_outfit(
    client=genai_client,  # google.genai.Client, 필수 (첫 번째)
    images=["path/to/outfit.jpg"]  # List[str], 필수 (두 번째)
)
```

### 2. 포즈/무드 분석 (선택)
```python
from core.brandcut import analyze_pose_expression, analyze_mood

pose_result = analyze_pose_expression(
    client=genai_client,
    image="path/to/pose.jpg"
)

mood_result = analyze_mood(
    client=genai_client,
    image="path/to/mood.jpg"
)
```

### 3. 프롬프트 조립
```python
from core.brandcut import build_prompt

prompt_json = build_prompt(
    outfit_analysis=result,
    pose_analysis=pose_result,  # 선택
    mood_analysis=mood_result,  # 선택
    background_type="with_car",
    user_options={"count": 3, "aspect_ratio": "3:4"}
)
```

### 4. 이미지 생성 (배치)
```python
from core.brandcut import generate_brandcut

# ============================================================
# 사용자 입력 (4단계에서 수집된 값)
# ============================================================
user_aspect_ratio = "3:4"   # 사용자 선택 비율
user_resolution = "2K"      # 사용자 선택 화질
user_num_images = 3         # 사용자 선택 수량
# ============================================================

# 사용자가 선택한 대로 N장 순수 생성
images = generate_brandcut(
    prompt_json=prompt_json,
    face_images=face_image_paths,       # 사용자 입력 얼굴 폴더의 이미지들
    outfit_images=outfit_image_paths,   # 사용자 입력 착장 폴더의 이미지들
    api_key=get_next_api_key(),         # 로테이션 API 키
    num_images=user_num_images,         # 사용자 선택 수량 (배치)
    aspect_ratio=user_aspect_ratio,     # 사용자 선택 비율
    resolution=user_resolution,         # 사용자 선택 화질
    temperature=0.25,
    pose_reference=pose_ref_image,      # 포즈 레퍼런스 (선택)
)
# 반환: List[PIL.Image] (num_images개, 실패한 이미지는 None)
```

### 5. AI 검증 + 재시도 (각 이미지별)
```python
from core.brandcut import generate_with_validation

# 각 이미지에 대해 AI 검증 + 실패 시 재생성
validated_results = []
for i, img in enumerate(images):
    if img is None:
        continue

    result = generate_with_validation(
        prompt_json=prompt_json,
        face_images=face_image_paths,
        outfit_images=outfit_image_paths,
        api_key=get_next_api_key(),
        aspect_ratio=user_aspect_ratio,
        resolution=user_resolution,
        max_retries=2,                  # 검증 실패 시 최대 2회 재시도
        initial_temperature=0.25,
        pose_reference=pose_ref_image,
        check_ai_artifacts=False,
        check_gate=True
    )
    validated_results.append(result)
    print(f"[{i+1}/{len(images)}] Score: {result['score']:.1f} | Passed: {result['passed']}")

# 반환 (각 이미지별):
# {
#     "image": PIL.Image,           # 검증 통과한 이미지 (최고 점수)
#     "score": float,               # 총점 (0-100)
#     "passed": bool,               # 통과 여부
#     "criteria": dict,             # 12개 기준 점수
#     "attempts": int,              # 시도 횟수
#     "history": List[dict]         # 시도 이력
# }
```

---

## 검증 기준 (12개 기준, 5 카테고리)

| 카테고리 | 기준 | 비중 |
|----------|------|------|
| **A. 기본품질 (23%)** | photorealism | 8% |
|                       | anatomy | 8% |
|                       | micro_detail | 7% |
| **B. 인물보존 (30%)** | face_identity | 15% |
|                       | expression | 8% |
|                       | body_type | 7% |
| **C. 착장 (15%)**     | outfit_accuracy | 15% |
| **D. 브랜드 (20%)**   | brand_compliance | 10% |
|                       | environmental_integration | 5% |
|                       | lighting_mood | 5% |
| **E. 구도 (12%)**     | composition | 6% |
|                       | pose_quality | 6% |

**등급**: S/A(95/90↑ 바로사용), B(85↑ 확인필요), C/F(75↑/↓ 재생성)

**Auto-Fail**:
- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람
- 착장/로고 누락 또는 변형
- 체형 불일치
- 누런 톤 (warm cast)
- 의도하지 않은 텍스트/워터마크
- AI 특유 플라스틱 피부

### 재생성 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    generate_with_validation()                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐     ┌─────────┐     ┌──────────────┐          │
│  │ 1. 생성  │────▶│ 2. 검증  │────▶│ 통과? (85+)  │          │
│  └─────────┘     └─────────┘     └──────┬───────┘          │
│       ▲                                  │                   │
│       │                           YES    │    NO             │
│       │                           ┌──────▼──────┐            │
│       │                           │   반환      │            │
│       │                           └─────────────┘            │
│       │                                  │                   │
│       │         ┌────────────────────────┘                   │
│       │         ▼                                            │
│       │  ┌─────────────────┐                                │
│       │  │ 3. 실패 원인 분석 │                                │
│       │  └────────┬────────┘                                │
│       │           ▼                                          │
│       │  ┌─────────────────┐                                │
│       │  │ 4. 프롬프트 강화  │                                │
│       │  └────────┬────────┘                                │
│       │           ▼                                          │
│       │  ┌─────────────────┐                                │
│       └──│ 5. 온도 -0.03    │ (max_retries 초과 시 종료)      │
│          └─────────────────┘                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 재생성 핵심 파라미터

| 항목 | 값 | 설명 |
|------|-----|------|
| **max_retries** | 2 | 최대 재시도 횟수 (총 3회 시도) |
| **온도 감소** | -0.03/회 | 재시도마다 온도 낮춤 (최소 0.15) |
| **통과 기준** | 85+ | 등급 B 이상 |
| **최고 점수 추적** | O | 모든 시도 중 최고 점수 이미지 반환 |

### 기준별 임계값 (threshold)

| 기준 | 임계값 | 미달 시 |
|------|--------|---------|
| face_identity | 85 | 프롬프트 강화 |
| outfit_accuracy | 80 | 프롬프트 강화 |
| anatomy | 80 | 프롬프트 강화 |
| photorealism | 85 | 프롬프트 강화 |
| body_type | 85 | 프롬프트 강화 |
| composition | 80 | 프롬프트 강화 |
| 기타 | 75 | 프롬프트 강화 |

### 재시도 프롬프트 강화

검증 실패 시 자동으로 프롬프트가 강화됨.

**강화 규칙 위치:** `core/mlb_validator.py` → `ENHANCEMENT_RULES` (lines 188-260)

**강화 로직:**
1. 실패한 기준 분석 (threshold 미달 기준 추출)
2. 우선순위 순서로 강화 규칙 적용:
   - `outfit_accuracy` → `face_identity` → `expression` → `anatomy` → ...
3. 프롬프트 JSON에 `_RETRY_NOTES` 키로 강화 내용 추가
4. 온도 0.03씩 감소 (최소 0.15)

**예시 (내부 구조):**
```python
current_prompt["_RETRY_NOTES"] = """
=== RETRY ENHANCEMENT (Attempt #2) ===
Previous score: 78/100 | Grade: C
Failed on: face_identity, expression

MUST FIX:
- CRITICAL: Face must be IDENTICAL to reference
- Preserve exact eye shape, nose, jawline
- EXPRESSION: Large, wide-open eyes (K-pop style)
================================================
"""
```

---

## 에러 핸들링

| 에러 | 복구 액션 |
|------|----------|
| API Timeout | 최대 3회 재시도 (2s, 4s, 8s) |
| Rate Limit (429) | 60초 대기 후 재시도 |
| VLM Failure | 프롬프트 간소화 후 재시도 |
| File Not Found | 사용자에게 경로 재입력 요청 |

---

## 사용법

CLI:
```
/브랜드컷
```

Claude가 순차 질문 → 분석 → 프롬프트 조립 → 생성 → 검증

---

**버전**: 3.1.0 (코드 동기화)
**작성일**: 2026-02-11

**변경사항 (v3.1.0)**:
- generate_with_validation 파라미터 추가: pose_reference, check_ai_artifacts, check_gate
- 반환 구조에 attempts, history, validation_result 추가
- 12개 검증 기준을 A~E 5개 카테고리로 재구조화
- 재시도 프롬프트 강화 로직 참조 추가 (ENHANCEMENT_RULES)

**변경사항 (v3.0.0)**:
- 코드 섹션 제거 (→ core/brandcut/ 모듈 참조)
- VLM 템플릿 제거 (→ core/brandcut/templates.py 참조)
- 검증 코드 제거 (→ core/mlb_validator.py 참조)
- 모듈 인터페이스 섹션 추가
