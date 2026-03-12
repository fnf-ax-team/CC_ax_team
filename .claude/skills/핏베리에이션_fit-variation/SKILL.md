# 바지 핏 베리에이션 디자인 스킬

> 단일 바지 이미지에서 다양한 실루엣(핏) 변형을 생성한다.
> 색상/소재/로고는 100% 보존, 실루엣만 변경.

---

## 용도

디자이너가 하나의 바지 디자인에서 여러 핏 옵션을 빠르게 시각화.
실제 샘플 제작 전 핏 의사결정을 위한 도구.

---

## 핏 프리셋 (10종)

| ID | 한국어 | 설명 |
|----|--------|------|
| `skinny` | 스키니 | 허리~발목까지 밀착, 극도로 좁은 통 |
| `slim` | 슬림 | 밀착에 가깝지만 약간의 여유 |
| `regular` | 레귤러 | 클래식 스트레이트, 허벅지~밑단 일정 폭 |
| `relaxed` | 릴렉스드 | 전체적으로 여유로운 핏 |
| `wide` | 와이드 | 힙~밑단까지 넓은 A라인 |
| `bootcut` | 부츠컷 | 허벅지 피팅, 무릎부터 점진적 플레어 |
| `tapered` | 테이퍼드 | 넓은 허벅지에서 좁은 발목으로 |
| `baggy` | 배기 | 극도 오버사이즈, 드롭 크로치 |
| `jogger` | 조거 | 편안한 핏 + 발목 밴딩 |
| `cargo_wide` | 카고 와이드 | 와이드 레그 + 사이드 카고 포켓 |

## 디스플레이 모드 (3종)

| ID | 한국어 | 설명 |
|----|--------|------|
| `flatlay` | 플랫레이 | 바닥에 펼쳐놓은 탑다운 뷰 |
| `hanger` | 행거 | 옷걸이에 걸린 형태 |
| `model_wearing` | 모델 착용 | 하반신 착용 모습 |

---

## 워크플로

```
1. VLM 바지 분석  — 색상/소재/패턴/로고/디테일 추출
2. 프롬프트 생성  — 3x 보존 전략 (색상/소재/로고 3번 반복)
3. 이미지 생성    — gemini-3-pro-image-preview
4. 검증+재생성    — color_preservation auto-fail
```

### 3x 보존 전략

색상/소재/로고를 프롬프트에 3번 반복:
1. `[절대 보존]` 섹션 — 1차 명시
2. `[디테일 보존]` 섹션 하단 REMINDER — 2차 반복
3. `[네거티브]` 섹션 — 3차 변경 금지

---

## 기본 파라미터

| 항목 | 값 |
|------|-----|
| 모델 | `gemini-3-pro-image-preview` |
| Temperature | `0.3` |
| Aspect Ratio | `1:1` |
| 해상도 | `2K` |

---

## 모듈 인터페이스

### 1. 바지 분석

```python
from core.fit_variation import analyze_pants, PantsAnalysis

analysis = analyze_pants(pants_image_path)
analysis.current_fit      # "regular"
analysis.color_primary    # "dark navy"
analysis.material_type    # "denim"
analysis.logos            # [LogoInfo(...)]
analysis.to_preservation_text()  # 보존 속성 텍스트
analysis.to_dict()        # 전체 딕셔너리
```

### 2. 핏 프리셋

```python
from core.fit_variation import load_fit_preset, list_fit_presets

presets = list_fit_presets()  # [{"id": "skinny", ...}, ...]
preset = load_fit_preset("wide")
preset.silhouette  # "dramatically wide from hip to hem..."
preset.keywords    # ["wide leg", "palazzo", ...]
preset.negative    # ["tight, slim, ..."]
```

### 3. 프롬프트 생성

```python
from core.fit_variation import build_fit_variation_prompt

prompt = build_fit_variation_prompt(
    analysis=analysis,
    target_preset=preset,
    display_mode=display,
)
```

### 4. 통합 생성 (Single Entry Point)

```python
from core.fit_variation import generate_fit_variation

result = generate_fit_variation(
    pants_image="path/to/pants.png",
    target_fit="wide",
    display_mode="flatlay",
    max_retries=2,
    validate=True,
)

image = result["image"]         # PIL.Image
prompt = result["prompt"]       # 생성 프롬프트
analysis = result["analysis"]   # PantsAnalysis
validation = result["validation"]  # 검증 결과
```

---

## 검증 기준

| 항목 | 비중 | Auto-Fail |
|------|------|-----------|
| color_preservation | 30% | < 70 |
| silhouette_accuracy | 25% | - |
| material_fidelity | 20% | - |
| detail_preservation | 15% | - |
| overall_quality | 10% | - |

Pass: 총점 >= 80 AND color_preservation >= 70

---

## 대화형 워크플로

### Step 1: 바지 이미지 요청

```
바지 이미지를 알려주세요.
변형할 바지 이미지 경로를 입력해주세요.
```

### Step 2: 핏 선택

```python
{
    "question": "어떤 핏으로 변형할까요?",
    "header": "핏",
    "options": [
        {"label": "와이드", "description": "힙~밑단 넓은 A라인"},
        {"label": "스키니", "description": "허리~발목 밀착"},
        {"label": "테이퍼드", "description": "넓은 허벅지→좁은 발목"},
        {"label": "배기", "description": "극도 오버사이즈, 드롭 크로치"}
    ],
    "multiSelect": false
}
```

### Step 3: 디스플레이 모드

```python
{
    "question": "어떤 형태로 보여줄까요?",
    "header": "디스플레이",
    "options": [
        {"label": "플랫레이 (권장)", "description": "바닥에 펼쳐놓은 탑다운 뷰"},
        {"label": "행거", "description": "옷걸이에 걸린 형태"},
        {"label": "모델 착용", "description": "하반신 착용 모습"}
    ],
    "multiSelect": false
}
```

### Step 4: 수량/화질

### Step 5: 확인 및 생성

---

## 출력 구조

```
Fnf_studio_outputs/fit_variation/{timestamp}_{description}/
├── images/
│   ├── input_pants.png
│   ├── output_001_wide.jpg
│   ├── output_002_skinny.jpg
│   └── output_003_tapered.jpg
├── analysis.json
├── prompt.txt
├── config.json
└── validation.json
```

---

## 테스트

```bash
python tests/fit_variation/test_fit_variation.py --image path/to/pants.png --fit wide
```

---

**버전**: 1.0.0
**작성일**: 2026-03-04
