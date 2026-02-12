# 셀카 (Selfie)

> 인플루언서/셀럽 스타일 셀카 이미지 생성 - 자연스러운 일상 느낌

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Selfie Workflow                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   INPUT      │     │   ANALYZE    │     │   GENERATE   │     │   VALIDATE   │
│              │     │              │     │              │     │              │
│ Face Image   │────>│ Scene        │────>│ Natural      │────>│ 5-Criteria   │
│ Scene/Mood   │     │ Analysis     │     │ Selfie       │     │ + Anti-      │
│              │     │              │     │ Generation   │     │ Polish       │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                       │
                                          ┌────────────────────────────┘
                                          │
                                          v
                           ┌─────────────────────────────┐
                           │      PASS + NOT TOO         │
                           │      PERFECT?               │
                           └─────────────────────────────┘
                                    │           │
                              YES   │           │ NO
                                    v           v
                           ┌───────────┐  ┌───────────────┐
                           │  OUTPUT   │  │ RETRY (max 2) │
                           │  Image    │  │ + Imperfection│
                           └───────────┘  └───────────────┘
```

---

## 모듈 구조

```
core/selfie/
├── __init__.py          # 통합 진입점
├── analyzer.py          # 씬/분위기 분석
├── generator.py         # 셀카 생성
├── prompt_builder.py    # 프롬프트 조립
├── templates.py         # 프롬프트 템플릿
└── validator.py         # 5-criteria + 역검증

.claude/skills/셀카_selfie/
├── README.md            # 이 문서
├── SKILL.md             # Claude용 스킬 정의
├── selfie-prompt-cheatsheet.md
└── validator.py         # 스킬용 검증기
```

---

## 데이터 플로우

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ANALYSIS PHASE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Face Image + Scene Request
     │
     └──> analyze_selfie_scene() ──> Scene Analysis
               │
               ├── scene_type: "cafe" | "street" | "home" | "mirror" | ...
               ├── lighting: "natural_window" | "golden_hour" | "flash" | ...
               ├── mood: "chill" | "excited" | "flirty" | "casual" | ...
               ├── angle: "high_angle" | "eye_level" | "mirror_selfie"
               └── props: ["coffee_cup", "phone_visible", "mirror", ...]


┌─────────────────────────────────────────────────────────────────────────────┐
│                              GENERATION PHASE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Scene Analysis + Face Image
     │
     └──> build_selfie_prompt()
               │
               ├── 1. Natural Selfie Base
               │       "Authentic smartphone selfie, NOT professional photo"
               │
               ├── 2. Imperfection Injection
               │       "Slightly uneven lighting"
               │       "Natural skin texture visible"
               │       "Casual, unstaged pose"
               │
               ├── 3. Scene/Environment
               │       Scene details, props, background
               │
               ├── 4. Lighting Style
               │       Natural, not studio
               │
               └── 5. Anti-AI Instructions
                       "No plastic skin"
                       "No perfect symmetry"
                       "Real person feeling"
                         │
                         v
               generate_selfie()
                         │
                         ├── Face Image (API 직접 전달)
                         ├── aspect_ratio: "9:16" (기본)
                         └── temperature: 0.3~0.5 (자연스러움)


┌─────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION PHASE (5-Criteria)                        │
└─────────────────────────────────────────────────────────────────────────────┘

Generated Image + Face Reference
     │
     └──> SelfieValidator.validate()
               │
               │   ┌─────────────────────────────────────────┐
               │   │        "너무 잘 나오면 실패"             │
               │   │        Anti-Polish Principle            │
               │   └─────────────────────────────────────────┘
               │
               ├── 1. realism (35%)
               │         │
               │         ├── 실제 스마트폰 셀카처럼 보이나?
               │         ├── 자연스러운 조명?
               │         └── 일상적인 느낌?
               │
               ├── 2. person_preservation (25%)
               │         │
               │         ├── 동일 인물?
               │         └── 얼굴 특징 유지?
               │
               ├── 3. scenario_fit (20%)
               │         │
               │         ├── 요청한 씬과 일치?
               │         └── 적절한 소품/배경?
               │
               ├── 4. skin_condition (10%)
               │         │
               │         ├── 자연스러운 피부 텍스처?
               │         └── 플라스틱 느낌 없음?
               │
               └── 5. anti_polish_factor (10%) ★ 역검증
                         │
                         ├── 너무 완벽하면 감점!
                         ├── 약간의 불완전함 = 가산점
                         └── 스튜디오 느낌 = 큰 감점
```

---

## 핵심 원칙

### 1. Anti-Polish (역검증)

```
일반 검증: 품질 높을수록 좋음
셀카 검증: 너무 완벽하면 실패!

GOOD (자연스러움):
- 약간 기울어진 앵글
- 자연광의 불균일함
- 실제 피부 텍스처
- 캐주얼한 표정

BAD (너무 완벽함):
- 완벽한 대칭
- 스튜디오 조명
- 에어브러시된 피부
- 포즈 잡은 느낌
```

### 2. Imperfection Injection

```python
# 프롬프트에 자연스러운 불완전함 주입
"Natural smartphone selfie with:
- Slightly off-center framing
- Casual, unstaged expression
- Real skin texture (pores visible)
- Authentic lighting (not studio)"
```

### 3. Scene Authenticity

| 씬 | 자연스러운 요소 | 어색한 요소 |
|-----|----------------|------------|
| 카페 | 커피잔 일부 보임, 창가 자연광 | 완벽한 라떼아트, 스튜디오 조명 |
| 거울 | 폰 들고 있는 손, 약간 흔들림 | 삼각대 느낌, 완벽한 포즈 |
| 길거리 | 배경에 행인, 자연스러운 햇빛 | 정리된 배경, 균일한 조명 |

---

## 사용법

### Python API

```python
from core.selfie import generate_with_validation

result = generate_with_validation(
    face_image=face_img,
    scene="cozy cafe with morning light",
    mood="chill weekend vibe",
    api_key=api_key,
    max_retries=2,
)
```

### 결과 구조

```python
{
    "image": PIL.Image,
    "score": 85,
    "passed": True,
    "criteria": {
        "realism": 88,
        "person_preservation": 92,
        "scenario_fit": 85,
        "skin_condition": 80,
        "anti_polish_factor": 75,  # 높을수록 자연스러움
    },
    "attempts": 1,
}
```

---

## 검증 기준 (5-Criteria)

| # | 항목 | 비중 | 설명 |
|---|------|------|------|
| 1 | realism | 35% | 실제 셀카처럼 보이나 |
| 2 | person_preservation | 25% | 동일 인물 유지 |
| 3 | scenario_fit | 20% | 씬/상황 일치 |
| 4 | skin_condition | 10% | 자연스러운 피부 |
| 5 | anti_polish_factor | 10% | 너무 완벽하면 감점 |

**Pass 조건**: 총점 ≥ 80 + anti_polish_factor ≥ 60

---

## 씬 프리셋

| 씬 | 조명 | 앵글 | 특징 |
|-----|------|------|------|
| cafe | natural_window | high_angle | 커피/음료, 테이블 |
| mirror | bathroom_light | eye_level | 폰 보임, 거울 프레임 |
| street | golden_hour | selfie_stick | 배경 보케, 행인 |
| home | soft_lamp | bed_level | 편안한, 캐주얼 |
| car | dashboard_light | driver_seat | 안전벨트, 창문 |

---

## Auto-Fail 조건

- 플라스틱 피부 (에어브러시 과다)
- 완벽한 스튜디오 조명
- 포즈 잡은 모델 느낌
- 얼굴 완전히 다른 사람
- AI 특유의 대칭성

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 2.0.0 | 2026-02-11 | 모듈 분리 (core/selfie/) |
| 1.5.0 | 2026-02-10 | Anti-Polish 검증 추가 |
| 1.0.0 | 2026-02-08 | 초기 버전 |
