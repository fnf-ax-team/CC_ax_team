# 착장 분석 필수 규칙

## 적용 대상

- 브랜드컷 워크플로 코드 (`*brandcut*`, `*brand_cut*`)
- `generate_brandcut()` 또는 `generate_with_validation()` 호출하는 모든 코드

## 규칙

### 1. 착장 분석 필수 호출

**금지:**
```python
# 착장 분석 없이 바로 생성
images = generate_brandcut(prompt, faces, outfits)
```

**필수:**
```python
from core.brandcut import analyze_outfit

# 1. 착장 분석 먼저
outfit_result = analyze_outfit(client, outfit_images)

# 2. 분석 결과로 프롬프트 조립
prompt = build_prompt(outfit_analysis=outfit_result, ...)

# 3. 생성
images = generate_brandcut(prompt, faces, outfits)
```

### 2. 착장 이미지 전체 전송

**금지:**
```python
# 착장 이미지 일부만 전송
generate_brandcut(prompt, faces, [outfits[0]])
```

**필수:**
```python
# 착장 이미지 전체 전송
generate_brandcut(prompt, faces, outfit_images)  # 모든 착장 이미지
```

## 검증 방법

1. `validate_outfit_analysis.py` 훅이 자동 검사
2. 브랜드컷 관련 파일 수정 시 경고 출력
3. 경고 발생 시 착장 분석 코드 추가

## 관련 문서

- `SKILL.md` > 모듈 인터페이스 > 1. 착장 분석
- `core/brandcut/analyzer.py` > `analyze_outfit()`

## 배경

착장 분석 없이 생성하면:
- 착장 색상/로고/디테일 불일치 확률 증가
- 검수 탈락률 증가
- 재생성 비용 증가

착장 분석은 VLM이 착장의 구체적 특징을 추출하여 프롬프트에 반영한다.
이 과정을 건너뛰면 생성 모델이 착장 이미지를 제대로 이해하지 못한다.
