---
name: anti-ai-look
description: AI 티 감지 및 해결 - 2단계 검증 (게이트 + 루브릭)
user-invocable: true
trigger-keywords: ["AI티", "AI 티", "AI스러움", "인공적", "부자연스러움", "ai티", "ai 티", "ai look", "인위적", "합성티"]
---

# AI 티 감지 스킬 (v2.0 - 게이트+루브릭)

> **핵심**: AI 생성 이미지의 "AI 티"를 2단계로 감지
> - **Step 0**: 합성티 게이트 (binary) - 하나라도 걸리면 FAIL
> - **Step 1**: 등급형 채점 (rubric) - 70/80/90/100점

---

## 2단계 검증 프로세스

### Step 0: 합성티 게이트 (0/1)

AI 아티팩트가 **하나라도 보이면 즉시 FAIL (0점)**.

| 게이트 항목 | 체크 내용 | 실패 예시 |
|------------|----------|----------|
| **눈/시선 인공감** | ring catchlight, white sclera, gaze mismatch | 도넛 모양 반사광, 공막 너무 하얌 |
| **피부 플라스틱** | no pores, over-sharpened, waxy surface | 모공 부재, 경계 과도한 날카로움 |
| **해부학 오류** | 손가락 개수, 기형 관절, 치아/귀/헤어라인 | 손가락 6개, 이상한 관절 |
| **조명 물리 위반** | shadow mismatch, no contact shadows | 그림자 방향 불일치, 접지 그림자 없음 |
| **로고/텍스트 오류** | logo distortion, unreadable text | 로고 번짐, 읽을 수 없는 글자 |

### Step 1: 등급형 채점 (게이트 통과 시에만)

| 점수 | 등급명 | 의미 | 사용 가능 여부 |
|------|--------|------|---------------|
| **100** | 캠페인 키비주얼급 | 매거진/광고 메인 이미지 수준 | 즉시 납품 가능 |
| **90** | 상업용 OK | 이커머스/SNS 메인 이미지 가능 | 사용 가능 |
| **80** | 서브컷 가능 | 보조 이미지/갤러리용 | 조건부 사용 |
| **70** | 재작업 권장 | 품질 미달 | 재생성 필요 |
| **0** | 게이트 실패 | AI 아티팩트 감지됨 | 즉시 재생성 |

### Pass 조건

```
PASS = (게이트 통과) AND (모든 카테고리 >= 88점)
```

---

## 5개 채점 카테고리

| 카테고리 | 설명 | 100점 기준 |
|----------|------|-----------|
| **skin** | 피부 텍스처 자연스러움 | 모공 보이고, 톤 균일, 자연스러운 광택 |
| **lighting** | 조명/그림자 자연스러움 | 단일 광원, 일관된 그림자, 물리적 정확성 |
| **outfit** | 착장 디테일 | 로고 선명, 자연스러운 주름, 소재감 |
| **composition** | 구도/프레이밍 | 적절한 여백, 시선 유도, 균형 |
| **overall** | 전체 분위기/완성도 | 실제 사진 수준, 자연스러운 무드 |

---

## 코드 사용 예시

### v2 방식 (권장)

```python
from google import genai
from core.ai_artifact_detector import AIArtifactDetector

client = genai.Client(api_key=api_key)
detector = AIArtifactDetector(client)

# v2: 게이트+루브릭 방식
result = detector.detect_v2("path/to/image.png")

# 게이트 결과 확인
if not result.gate_passed:
    print("FAIL: 합성티 게이트 실패")
    print(f"실패 사유: {result.gate_failed_reasons}")
else:
    # 루브릭 점수 확인
    print(f"등급: {result.rubric_level} ({result.rubric_score}점)")
    print(f"카테고리별: {result.category_scores}")

    if result.is_passed:
        print("PASS: 모든 카테고리 >= 88점")
    else:
        print(f"FAIL: {result.min_category}가 {result.min_score}점")
```

### v1 방식 (하위 호환)

```python
# 기존 방식도 계속 사용 가능
result = detector.detect("path/to/image.png")
print(f"총점: {result.total_ai_score}")  # 0-100, 높을수록 AI스러움
print(f"등급: {result.naturalness_grade}")  # S/A/B/C/F
```

### 배치 처리

```python
# v2 배치
results = detector.batch_detect_v2([
    "image1.png",
    "image2.png",
    "image3.png"
], max_workers=3)

for i, r in enumerate(results):
    status = "PASS" if r.gate_passed and r.is_passed else "FAIL"
    print(f"Image {i+1}: {status} ({r.rubric_score}점)")
```

---

## 결과 테이블 포맷

```
+-----------------------------------------------------------+
|              AI 티 감지 결과 - PASS (90점)                 |
+-----------------------------------------------------------+
| Step 0: 게이트 | PASS (모든 항목 통과)                     |
+-----------------------------------------------------------+
| Step 1: 루브릭 채점                                        |
|-----------------------------------------------------------|
| 카테고리       | 점수 | 상태                              |
|----------------|------|-----------------------------------|
| skin           |  92  | OK                                |
| lighting       |  88  | OK (최소 기준)                    |
| outfit         |  95  | OK                                |
| composition    |  90  | OK                                |
| overall        |  90  | OK                                |
|----------------|------|-----------------------------------|
| 최종 점수      |  88  | 최저 카테고리 기준                |
| 등급           | 상업용 OK                             |
+-----------------------------------------------------------+
| 판정: PASS (모든 카테고리 >= 88)                           |
+-----------------------------------------------------------+
```

```
+-----------------------------------------------------------+
|              AI 티 감지 결과 - FAIL (0점)                  |
+-----------------------------------------------------------+
| Step 0: 게이트 | FAIL                                      |
|-----------------------------------------------------------|
| 실패 사유:                                                 |
| - 피부 모공 부재 (skin_synthetic)                          |
| - 로고 왜곡 (logo_text_errors)                             |
+-----------------------------------------------------------+
| Step 1: 채점 생략 (게이트 실패)                            |
+-----------------------------------------------------------+
| 개선 제안:                                                 |
| 1. 프롬프트: "natural skin with visible pores" 추가       |
| 2. 프롬프트: "clear, sharp brand logos" 추가              |
| 3. Temperature 낮추기 (0.2 → 0.15)                        |
+-----------------------------------------------------------+
```

---

## MLBValidator 통합

브랜드컷 생성 시 게이트 체크가 자동으로 실행됩니다.

```python
from core.mlb_validator import MLBValidator

validator = MLBValidator(client)

# check_gate=True (기본값) - 게이트 먼저 체크
result = validator.validate(
    generated_img,
    face_images=[ref_face],
    outfit_images=[ref_outfit],
    check_gate=True  # 기본 활성화
)

if not result.gate_passed:
    print(f"게이트 실패: {result.gate_failed_reasons}")
    # 12개 기준 채점은 실행되지 않음
else:
    print(f"총점: {result.total_score}")
    # 게이트 통과 후 12개 기준 채점 진행
```

---

## 검수 스킬과의 차이

| 항목 | 검수 스킬 (validate-brandcut) | AI 티 감지 (anti-ai-look) |
|------|------------------------------|--------------------------|
| 목적 | 참조 이미지와의 일치도 검증 | AI 아티팩트 절대적 품질 평가 |
| 참조 이미지 | **필수** (얼굴, 착장) | **불필요** |
| 평가 방식 | 12개 기준 가중 평균 | **2단계: 게이트 → 루브릭** |
| 게이트 | 없음 (점수만 산출) | **있음 (binary fail)** |
| Pass 기준 | 총점 >= 85 | 게이트 통과 + 모든 카테고리 >= 88 |

---

## 권장 워크플로

```
1. 이미지 생성
2. AI 티 감지 게이트 (Step 0) → FAIL 시 즉시 재생성
3. AI 티 루브릭 채점 (Step 1) → < 88점 카테고리 있으면 재생성
4. 검수 스킬 (참조 비교) → 불일치 시 재생성
5. 모든 검사 통과 → 최종 승인
```

---

## 파일 위치

```
core/ai_artifact_detector.py      - AI 티 감지 (v1 + v2)
core/ai_artifact_resolver.py      - 해결 방법 제안
core/mlb_validator.py             - 브랜드컷 검증 (게이트 통합)
core/brandcut_gate_validator.py   - 독립 게이트 검증 모듈
.claude/skills/AI티감지_anti-ai-look/SKILL.md - 이 문서
```

---

## 업데이트 로그

| 날짜 | 버전 | 변경 사항 |
|------|------|----------|
| 2026-01-XX | 1.0 | 초기 생성 (6개 카테고리 점수 방식) |
| 2026-02-10 | 2.0 | 게이트+루브릭 방식으로 전환, MLBValidator 통합 |
