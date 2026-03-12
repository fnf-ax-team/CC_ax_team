---
name: validate-brandcut
description: 브랜드컷 품질 검수 - 참조 이미지 기반 얼굴/착장/품질 검증
user-invocable: true
trigger-keywords: ["검수", "검증", "validate", "품질 체크", "이거 봐", "이거 검사해"]
---

# 브랜드컷 검수 스킬

> **핵심**: 검수할 이미지 + 참조 이미지(얼굴/착장)로 검증
> 참조 없이 검수 불가 - 반드시 비교 대상 필요

---

## 사용 케이스 2가지 (중요!)

| 케이스 | 상황 | 참조 처리 |
|--------|------|----------|
| **1. 생성 → 검수** | 브랜드컷 생성 후 검수 | 생성할 때 받은 착장+모델 **그대로 사용** |
| **2. 검수만 테스트** | 이미 생성된 이미지만 검수 | 참조 **물어봐야 함** |

### 케이스 1: 생성 → 검수 (연속)

```
1. 사용자: "브랜드컷 만들어줘"
2. Claude: 모델 얼굴 경로? → 사용자: [얼굴 경로]
3. Claude: 착장 경로? → 사용자: [착장 경로]
4. [이미지 생성]
5. [검수] ← 2, 3번에서 받은 참조 그대로 사용 (다시 안 물어봄)
```

### 케이스 2: 검수만 테스트 (단독)

```
1. 사용자: "이거 검수해" (생성 없이 바로 검수 요청)
2. Claude: 검수할 이미지 경로? → 사용자: [이미지 경로]
3. Claude: 얼굴 참조 경로? → 사용자: [얼굴 경로]  ← 물어봐야 함!
4. Claude: 착장 참조 경로? → 사용자: [착장 경로]  ← 물어봐야 함!
5. [검수 실행]
```

**절대 금지**: 참조를 모르는데 임의로 넣기 (예: 카리나로 추측)

---

## 검수 플로우 - 케이스 2 (AskUserQuestion 사용)

```
1. 사용자: "이거 검수해" / "검증해봐" / "품질 체크"

2. Claude: "검수할 이미지 경로를 알려주세요!"

3. 사용자: [이미지 경로 또는 이미지 직접 첨부]

4. Claude: [이미지 미리보기 + 기본 정보 테이블]

5. Claude: "얼굴 참조 이미지를 알려주세요! (face_identity 비교용)"

6. 사용자: [얼굴 이미지 경로]

7. Claude: [얼굴 참조 미리보기]

8. Claude: "착장 참조 이미지를 알려주세요! (outfit_accuracy 비교용)"

9. 사용자: [착장 이미지 경로]

10. Claude: [착장 참조 미리보기]

11. Claude: [검수 실행 → 결과 테이블 + 등급 + 피드백]
```

---

## AskUserQuestion 예시

### 검수 유형 선택 (선택사항)

```python
# 검수 유형 선택
AskUserQuestion(questions=[{
    "question": "어떤 검수를 실행할까요?",
    "header": "검수 유형",
    "options": [
        {"label": "전체 검수 (Recommended)", "description": "12개 기준 전체 검증"},
        {"label": "얼굴만", "description": "face_identity, expression, anatomy만 검증"},
        {"label": "착장만", "description": "outfit_accuracy, color_accuracy만 검증"},
        {"label": "품질만", "description": "photorealism, composition, lighting만 검증"}
    ],
    "multiSelect": False
}])
```

---

## 검수 기준 (12개)

| 기준 | 가중치 | Pass 조건 | 설명 |
|------|--------|-----------|------|
| photorealism | 20% | ≥ 85 | 실제 사진 같은지 |
| anatomy | 15% | ≥ 90 | 해부학적 정확성 (손가락, 비율) |
| **face_identity** | 15% | ≥ 90 | **얼굴 참조와 같은 사람인지** |
| **outfit_accuracy** | 15% | ≥ 85 | **착장 참조와 색상/로고/소재 일치** |
| body_type | 10% | ≥ 85 | 체형 보존 |
| brand_compliance | 10% | ≥ 80 | 브랜드 톤앤매너 |
| composition | 8% | ≥ 80 | 구도/프레이밍 |
| lighting_mood | 7% | ≥ 80 | 조명/분위기 |
| expression | - | - | 표정 자연스러움 |
| background_quality | - | - | 배경 품질 |
| overall_harmony | - | - | 전체 조화 |
| color_accuracy | - | - | 색 재현 정확도 |

---

## 등급 시스템

| Grade | 점수 | QualityTier | 의미 |
|-------|------|-------------|------|
| S | 95+ | RELEASE_READY | 바로 사용 가능 |
| A | 90-94 | RELEASE_READY | 바로 사용 가능 |
| B | 85-89 | NEEDS_MINOR_EDIT | 약간 수정 필요 |
| C | 75-84 | REGENERATE | 재생성 권장 |
| F | <75 | REGENERATE | 재생성 필수 |

---

## Auto-Fail 조건 (점수 무관 즉시 재생성)

- 손가락 6개 이상 / 기형적 손가락
- **얼굴 다른 사람** (face_identity < 70)
- **착장 색상/로고 불일치** (outfit_accuracy < 70)
- **체형 불일치** (body_type < 70)
- **누런 톤 (golden/amber/warm cast)**
- 의도하지 않은 텍스트/워터마크
- AI 특유 플라스틱 피부

---

## 코드 사용법

```python
from core.mlb_validator import MLBValidator

# Validator 초기화
validator = MLBValidator()

# 검수 실행 - 참조 이미지 필수!
result = validator.validate(
    generated_image_path="path/to/generated.png",
    face_images=["path/to/face_ref.jpg"],      # 필수!
    outfit_images=["path/to/outfit_ref.jpg"],  # 필수!
    brand_context="MLB 마케팅 화보"
)

# 결과 확인
print(f"등급: {result.grade}")  # S/A/B/C/F
print(f"점수: {result.weighted_score:.1f}")
print(f"티어: {result.tier.value}")  # RELEASE_READY / NEEDS_MINOR_EDIT / REGENERATE
print(f"피드백: {result.feedback}")

# 개별 점수
for criterion, score in result.scores.items():
    print(f"  {criterion}: {score}")
```

---

## 출력 예시

```
┌─────────────────────────────────────────────────────────────────┐
│                    검수 결과 - Grade A (92.3점)                  │
├─────────────────────────────────────────────────────────────────┤
│ Tier: RELEASE_READY (바로 사용 가능)                            │
├─────────────────────────────────────────────────────────────────┤
│ 기준             │ 점수  │ Pass │ 설명                          │
│ ─────────────────│───────│──────│───────────────────────────────│
│ photorealism     │ 95    │ ✅   │ 실제 사진 같음                │
│ anatomy          │ 92    │ ✅   │ 손가락 정상, 비율 적절        │
│ face_identity    │ 94    │ ✅   │ 참조와 같은 사람              │
│ outfit_accuracy  │ 88    │ ✅   │ 착장 색상/로고 일치           │
│ body_type        │ 90    │ ✅   │ 체형 보존                     │
│ brand_compliance │ 85    │ ✅   │ 브랜드 톤앤매너 준수          │
│ composition      │ 92    │ ✅   │ 구도 좋음                     │
│ lighting_mood    │ 88    │ ✅   │ 조명 적절                     │
├─────────────────────────────────────────────────────────────────┤
│ Auto-Fail: 없음                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 피드백: 전체적으로 높은 품질. 착장 로고 위치 약간 확인 필요.    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 핵심 원칙

| 항목 | 설명 |
|------|------|
| **참조 필수** | 얼굴/착장 참조 없이 검수 불가 |
| **먼저 물어봄** | 검수 전에 참조 경로 확인 |
| **임의 추측 금지** | 참조를 모르면 물어봄, 임의로 넣지 않음 |
| **비교 기반 검증** | face_identity는 참조와 비교해서 판단 |

---

## 파일 위치

```
core/mlb_validator.py       - Validator 클래스
.claude/skills/검수_validate-brandcut/SKILL.md - 이 문서
```
