---
name: selfie
description: 셀카/인플루언서 스타일 이미지 생성 - 분위기 선택 가능
user-invocable: true
trigger-keywords: ["셀카", "셀피", "인플", "인플루언서", "셀럽", "셀카 만들어", "예쁜 사진"]
---

# 셀카 이미지 생성

> 분위기 선택으로 꾸민 느낌 ~ 자연스러운 느낌까지

---

## 절대 규칙 (CRITICAL)

1. **필수 모델**: gemini-3-pro-image-preview
2. **한국어 프롬프트로 짧고 심플하게** (영어 엔지니어링 금지)
3. **얼굴 이미지 반드시 API 전송** - 얼굴 동일성 보장

### 금지 모델

```
❌ gemini-2.0-flash-exp (품질 낮음)
❌ gemini-2.0-flash (이미지 생성 미지원)
❌ gemini-2.5-flash (텍스트 전용)
```

### 기본 파라미터

| 항목 | 값 |
|------|-----|
| **모델** | `gemini-3-pro-image-preview` |
| **Temperature** | `0.7` |
| **Aspect Ratio** | `9:16` (스토리/릴스) |
| **해상도** | `2K` (2048px) |

---

## 필수 리소스

```
.claude/skills/셀카_selfie/selfie-prompt-cheatsheet.md  ← 프롬프트 치트시트 (반드시 로드)

core/selfie/                                            ← 실행 모듈
core/selfie_validator.py                                 ← 검증 모듈
```

---

## 대화형 워크플로 (CRITICAL)

**스킬 실행 시 반드시 순차 질문으로 시작하라. 코드 실행 전에 모든 입력을 수집해야 한다.**

### Step 1: 입력 수집 (대화형 필수)

사용자에게 순차적으로 질문한다. AskUserQuestion 도구 사용 권장.

| 순서 | 질문 | 필수 | 기본값 |
|------|------|------|--------|
| 1 | 얼굴 이미지 폴더 경로 | ✅ | - |
| 2 | 착장 이미지 폴더 경로 (선택) | ❌ | 없음 |
| 3 | 옵션 선택 (클릭) | ✅ | - |

### Step 2: 클릭 옵션 (AskUserQuestion) - 2단계

**1단계 (4개 질문):**

| 항목 | 옵션들 |
|------|--------|
| **분위기** | 꾸민 느낌 (인플 스타일), 자연스러운 (일상 느낌) |
| **촬영 스타일** | 셀카, 거울샷, 캔디드 |
| **메이크업** | 민낯, 내추럴 (가벼운 화장), 풀메이크업 |
| **착장** | 실내복, 데일리, 운동복, 특수 (수영복 등), 직접 입력, 착장 폴더 있음 |

**2단계 (2개 질문):**

| 항목 | 옵션들 |
|------|--------|
| **장소** | 집/방, 카페, 야외/거리, 헬스장, 호텔, 욕실, 클럽/바 |
| **조명** | 자연광 (기본), 플래시 (어두운 방), 링라이트, 골든아워, 클럽/네온, 무드등 |

**3단계 (3개 질문) - 비율/수량/화질:**

| 항목 | 옵션들 |
|------|--------|
| **비율** | 1:1 정사각, 2:3 세로, 3:2 가로, 3:4 세로화보, 4:3 가로화보, 4:5 인스타피드, 5:4 가로피드, 9:16 스토리/릴스 **(기본)**, 16:9 유튜브, 21:9 시네마틱 |
| **수량** | 1장 (₩190), 3장 (₩570), 5장 (₩950), 10장 (₩1,900) |
| **화질** | 1K 테스트 (₩190/장), 2K 기본 (₩190/장), 4K 고화질 (₩380/장) |

### 비율 전체 목록

| 비율 | 용도 |
|------|------|
| `1:1` | 정사각/프로필 |
| `2:3` | 세로 포트레이트 |
| `3:2` | 가로 랜드스케이프 |
| `3:4` | 세로 화보 |
| `4:3` | 가로 화보 |
| `4:5` | 인스타 피드 |
| `5:4` | 가로 피드 |
| `9:16` | **스토리/릴스 (기본)** |
| `16:9` | 유튜브/가로 영상 |
| `21:9` | 시네마틱/울트라와이드 |

### 비용 계산

| 화질 | 장당 비용 | 3장 | 5장 |
|------|----------|-----|-----|
| 1K~2K | ₩190 | ₩570 | ₩950 |
| 4K | ₩380 | ₩1,140 | ₩1,900 |

### 조명 옵션 설명

| 조명 | 설명 | 추천 조합 |
|------|------|----------|
| **자연광** (기본) | 창문에서 들어오는 빛, 편안함 | 집/방 + 자연스러운 |
| **플래시 (어두운 방)** | 폰 플래시 반사, 렌즈플레어 | 거울샷 + 꾸민 느낌 |
| **링라이트** | 눈에 동그란 반사, 인플루언서 느낌 | 셀카 + 꾸민 느낌 |
| **골든아워** | 따뜻한 석양빛, 감성적 | 야외/카페 + 캔디드 |
| **클럽/네온** | 컬러풀한 파티 분위기 | 클럽/바 + 꾸민 느낌 |
| **무드등** | 은은한 침실 조명, 아늑함 | 집/방 + 자연스러운 |

### Step 3: 프롬프트 조립
→ build_selfie_prompt() + 금지 조합 검증

### Step 4: 생성+검증
→ generate_with_validation() + SelfieValidator (5개 기준)

---

## 모듈 인터페이스 (에이전트 호출 규격)

### 1. 얼굴 분석

```python
from core.selfie import analyze_face, SelfieAnalyzer

# 편의 함수
result = analyze_face(
    client=genai_client,  # google.genai.Client, 필수 (첫 번째)
    image="path/to/face.jpg"  # 이미지 경로 또는 PIL.Image
)
# 반환: {"gender": "female", "features": {...}}

# 또는 클래스 사용
analyzer = SelfieAnalyzer(client=genai_client)
result = analyzer.analyze_face(image)
```

### 2. 착장 분석 (선택)

```python
from core.brandcut import analyze_outfit  # brandcut 모듈 재사용

outfit_analysis = analyze_outfit(
    client=genai_client,
    images=["path/to/outfit1.jpg"]
)
# → 자동으로 상의/하의/색상/스타일 추출하여 프롬프트에 포함
```

### 3. 프롬프트 조립

```python
from core.selfie import build_selfie_prompt, PROMPT_OPTIONS

prompt = build_selfie_prompt(
    options={
        "gender": "female",            # 또는 "male"
        "shooting_style": "selfie",    # selfie, mirror, candid
        "framing": "close_up",         # close_up, upper_body, full_body
        "expression": "flirty",        # flirty, natural, innocent, chic
        "makeup": "natural",           # bare, natural, full
        "outfit_category": "loungewear",  # 또는 outfit_analysis 사용
        "location": "bedroom",         # bedroom, cafe, car, outdoor, gym, club
        "lighting": "natural_home"     # natural_home, flash_dark, ring_light, golden_hour, club_neon, bedroom_mood
    },
    outfit_analysis=outfit_analysis  # 선택: 착장 분석 결과
)
# 반환: "이 얼굴로 예쁜 여자, 셀카 느낌, 완전 얼빡, 침대에서..."
```

### 4. 이미지 생성 + 검증

```python
from core.selfie import generate_with_validation

result = generate_with_validation(
    prompt=prompt,
    face_images=["path/to/face.jpg"],
    outfit_images=["path/to/outfit.jpg"],  # 선택
    api_key="GEMINI_API_KEY",
    max_retries=2,
    aspect_ratio="9:16",           # 화면 비율
    resolution="2K",               # 해상도
    temperature=0.7                # 다양성 (기본 0.7)
)
# 반환:
# {
#     "image": PIL.Image,            # 생성된 이미지 (최고 점수)
#     "score": float,                # 총점 (0-100)
#     "passed": bool,                # 통과 여부
#     "criteria": dict,              # 5개 기준 점수
#     "attempts": int,               # 시도 횟수
#     "history": List[dict]          # 시도 이력
# }
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

- 모든 점수가 95점 이상 → anti_polish_factor 30점 감점
- 완벽한 피부 + 완벽한 조명 + 완벽한 구도 = TOO POLISHED = FAIL

**등급**: S/A(90↑ 바로사용), B(75↑ 확인필요), C/F(75↓ 재생성)

**Auto-Fail**: 손가락 6개↑, 얼굴 불일치, 누런 톤, AI 플라스틱 피부, 의도하지 않은 텍스트

---

## 에러 핸들링

| 에러 | 복구 액션 |
|------|----------|
| API Timeout | 최대 3회 재시도 (5s, 10s, 15s) |
| Rate Limit (429) | 60초 대기 후 재시도 |
| 얼굴 안 닮음 | 정면 얼빡 참조 이미지 사용 |
| File Not Found | 사용자에게 경로 재입력 요청 |

---

## 금지 조합

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 1 | 전신 + 얼빡 | 물리적 모순 | 둘 중 하나만 |
| 2 | 거울셀카 + 누워서 | 거울 앞에서 눕기 어려움 | 침대 셀카로 변경 |
| 3 | 헬스장 + 파자마 | 상황 부적합 | 운동복으로 변경 |
| 4 | 수영복 + 카페 | 상황 부적합 | 수영장/해변으로 변경 |
| 5 | 남찍 + 거울셀카 | 촬영 방식 충돌 | 둘 중 하나만 |
| 6 | 클럽/네온 + 집/방 | 조명-장소 불일치 | 장소를 클럽/바로 변경 |
| 7 | 골든아워 + 욕실 | 조명-장소 불일치 | 야외/카페로 변경 또는 자연광으로 |
| 8 | 플래시 + 야외 | 낮에 플래시 부자연스러움 | 자연광 또는 골든아워로 |
| 9 | 링라이트 + 캔디드 | 링라이트는 정면 셀카용 | 셀카로 변경 또는 자연광으로 |

→ `build_selfie_prompt()`가 자동으로 금지 조합 감지 및 대안 적용

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 너무 인위적 | 영어 프롬프트 | 한국어로 짧게 |
| 다 비슷함 | 표정만 바꿈 | 장소/포즈/옷 확 다르게 |
| 얼굴 안 닮음 | 참조 이미지 품질 | 정면 얼빡 이미지 사용 |
| 손 이상함 | AI 한계 | 손 안 보이는 포즈로 |
| 누런 톤 | 조명 설정 | "cool lighting" 추가 |
| 너무 꾸며 보임 | 인플 느낌 과함 | 분위기를 "자연스러운"으로 |

---

## 출력

```
Fnf_studio_outputs/selfie/{설명}_{타임스탬프}/
```

---

## 사용법

CLI:
```
/셀카
```

Claude가 순차 질문 → 옵션 수집 → 프롬프트 조립 → 생성 → 검증

---

**버전**: 5.0.0 (모듈 분리)
**작성일**: 2026-02-11

**변경사항 (v5.0.0)**:
- 인라인 코드 제거 → `core/selfie/` 모듈 참조
- 검증 코드 제거 → `core/selfie_validator.py` 참조
- 모듈 인터페이스 섹션 추가
- 프롬프트 치트시트 분리 (기존 유지)
