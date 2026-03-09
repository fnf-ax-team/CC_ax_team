# VLM 검수 프롬프트 작성 규칙

## 적용 대상

- `*_validator.py` 파일의 VALIDATION_PROMPT
- VLM에게 이미지 비교/평가를 요청하는 모든 프롬프트

## 규칙

### 1. 비교 요청 시 step-by-step 형식 강제

**금지:**
```
"[POSE REFERENCE]와 비교하세요. 다르면 70점 이하!"
```

**필수:**
```
[STEP 1] POSE REFERENCE 분석: REF 앵글=?, REF 프레이밍=?
[STEP 2] GENERATED IMAGE 분석: GEN 앵글=?, GEN 프레이밍=?
[STEP 3] 비교 및 감점 계산
[STEP 4] 최종 점수 = 100 - 합계 감점
```

### 2. 출력 형식 명시 강제

**금지:**
```
"사유를 적으세요"
```

**필수:**
```
reason 필수 형식: "REF:로우앵글+전신, GEN:아이레벨+무릎위, 감점:-35"
```

### 3. 감점 계산 공식 명시 강제

**금지:**
```
"다르면 -20점"
```

**필수:**
```
앵글: 같음(0) / 다름(-20)
프레이밍: 같음(0) / 다름(-15)
합계 감점 = ?
최종 점수 = 100 - 합계 감점
```

## 검증 방법

1. `validate_vlm_prompt.py` 훅이 자동 검사
2. VLM 응답의 `reason` 필드에서 형식 확인
3. 형식 미준수 시 프롬프트 수정

## 관련 문서

- `CLAUDE.md` → "VLM 검수 프롬프트 작성 원칙" 섹션
- `core/brandcut/mlb_validator.py` → 적용 예시

## 적용 예시

### pose_quality

```
[STEP 1] POSE REFERENCE 분석: REF 앵글=로우앵글, REF 프레이밍=전신
[STEP 2] GENERATED IMAGE 분석: GEN 앵글=아이레벨, GEN 프레이밍=무릎위
[STEP 3] 비교: 앵글(-20) + 프레이밍(-15) = -35
[STEP 4] 최종 점수 = 100 - 35 = 65점

reason: "REF:로우앵글+전신, GEN:아이레벨+무릎위, 감점:-35"
```

### outfit_accuracy

```
[STEP 1] OUTFIT REFERENCE 분석: 바시티점퍼(Red Sox) + 탱크탑(NY) + 카고데님(NY)
[STEP 2] GENERATED IMAGE 분석: 탱크탑(NY) + 카고데님(NY)
[STEP 3] 비교: 점퍼 완전 누락(-50) = -50
[STEP 4] 최종 점수 = 100 - 50 = 50점

reason: "REF:점퍼+탱크탑+데님, GEN:탱크탑+데님, 누락:점퍼, 감점:-50"
```

## 배경

VLM은 단순한 지시("비교하세요")를 무시하고 일반 평가만 수행하는 경향이 있음.
step-by-step 형식과 출력 형식을 강제해야 실제 비교가 수행됨.
