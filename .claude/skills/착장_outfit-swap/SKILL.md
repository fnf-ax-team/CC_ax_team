---
name: outfit-swap
description: 착장만 스왑 (얼굴, 포즈, 배경 유지)
user-invocable: true
trigger-keywords: ["착장 스왑", "착장 교체", "옷 바꾸기", "outfit swap"]
---

# 착장 스왑 (Outfit Swap)

> **핵심 개념**: 착장만 교체 (얼굴, 포즈, 배경 완전 유지)
> 소스 이미지의 **얼굴/포즈/배경을 정확히 보존**하면서 착장만 제공된 착장으로 교체
> **EDITING MODE** -- 이미지 재생성이 아닌 착장 레이어 교체

---

## 모델 필수 확인

```
from core.config import IMAGE_MODEL, VISION_MODEL
# IMAGE_MODEL = gemini-3-pro-image-preview (이미지 생성)
# VISION_MODEL = gemini-3-flash-preview (VLM 분석)
# 반드시 core/config.py에서 import! 하드코딩 금지!
```

---

## 핵심 컨셉: EDITING MODE

```
+------------------------------------------------------------------+
|  Outfit Swap = Photoshop 착장 레이어 교체                          |
+------------------------------------------------------------------+
|                                                                    |
|  LOCKED (변경 불가):          SWAP (교체 대상):                    |
|  +- 얼굴 (PIXEL-LOCKED)     +- 착장 -> 제공된 착장으로 완전 교체   |
|  +- 포즈 (PIXEL-LOCKED)                                           |
|  +- 배경 (PIXEL-LOCKED)                                           |
|  +- 체형 (PIXEL-LOCKED)                                           |
|  +- 스케일 (Scale=1.0)                                            |
|                                                                    |
|  프롬프트 패러다임:                                                 |
|  X 이미지 재구성 (reconstruction)                                  |
|  O 착장 레이어만 교체 (editing)                                    |
|                                                                    |
|  비율 자동 감지:                                                    |
|  소스 이미지 비율 -> 가장 가까운 Gemini 비율 자동 매칭              |
|  포즈 보존의 핵심! 비율 불일치 = 포즈 드리프트                     |
+------------------------------------------------------------------+
```

---

## 입력 구조

| 입력 | 필수 | 수량 | 처리 방식 |
|------|------|------|----------|
| 소스 이미지 | O | 1장 | **API에 직접 전달** (얼굴/포즈/배경 보존) |
| 착장 이미지 | O | 1~10장 | 이미지 직접 전달 + VLM 분석 텍스트 보조 |

### 이미지 전달 순서 (중요!)

```
1. 프롬프트 (텍스트) - EDITING MODE 지시 + 착장 설명
2. "[SOURCE IMAGE - EDITING CANVAS]" 라벨 + 소스 이미지
3. "[OUTFIT REFERENCE N]" 라벨 + 착장 이미지들
```

### 이미지 라벨 (CRITICAL)

```python
# 소스 이미지 라벨
"[SOURCE IMAGE - EDITING CANVAS] Preserve EVERYTHING (face, pose, background, scale). Change ONLY clothing."

# 착장 이미지 라벨 (각각)
"[OUTFIT REFERENCE {i}] Extract garment ONLY. IGNORE pose/face/background in this image."
```

### Anti-Drift 규칙

착장 레퍼런스 이미지에서 **착장 정보만 추출**하고 포즈/얼굴/배경은 완전 무시.
착장 이미지의 모델 포즈가 소스 포즈에 영향을 주면 포즈 드리프트 발생.

---

## 비율 자동 감지 (CRITICAL)

소스 이미지와 생성 이미지의 비율이 다르면 포즈가 변경됨.
반드시 소스 이미지 비율과 동일한 Gemini 비율로 생성해야 함.

```python
from core.options import detect_aspect_ratio

# 소스 이미지 비율 자동 감지
ratio = detect_aspect_ratio(source_pil)  # "2:3", "3:2", "3:4" 등

# generator.py 내부에서 자동 처리
# aspect_ratio="auto" 또는 "original" -> 자동 감지
```

### Gemini 지원 비율

| 비율 | 방향 | 수치 |
|------|------|------|
| 1:1 | 정사각 | 1.000 |
| 2:3 | 세로 | 0.667 |
| 3:2 | 가로 | 1.500 |
| 3:4 | 세로 | 0.750 |
| 4:3 | 가로 | 1.333 |
| 4:5 | 세로 | 0.800 |
| 5:4 | 가로 | 1.250 |
| 9:16 | 세로 | 0.563 |
| 16:9 | 가로 | 1.778 |

---

## 대화 플로우

```
1. 사용자: "착장 스왑" 또는 "outfit swap"

2. Claude: "소스 이미지 경로?"
3. 사용자: D:\source.jpg

4. Claude: "착장 이미지 폴더 경로?"
5. 사용자: D:\outfits

6. Claude: [착장 분석 후 테이블 출력]
   | 부위 | 아이템 | 색상 | 로고 | 디테일 |
   |------|--------|------|------|--------|
   | 상의 | 후디 | 블랙 | NY (가슴 중앙, 화이트) | 오버사이즈, 드롭숄더 |
   | 하의 | 와이드진 | 라이트블루 | 없음 | 하이웨이스트, 카고포켓 |

   [AskUserQuestion - 수량/해상도 선택]

7. 사용자: 클릭으로 선택

8. Claude:
   - 소스 이미지 VLM 분석 (얼굴/포즈/배경)
   - 착장 이미지들 VLM 분석 (상세 디테일)
   - 이미지 생성 (비율 자동 감지)
   - 검수 (outfit_accuracy, face_identity, pose_preservation)
   - 결과 저장 및 경로 안내
```

---

## 코어 모듈 구조

```
core/outfit_swap/
+-- __init__.py         # 공개 API export
+-- analyzer.py         # VLM 분석 (소스 + 착장)
+-- prompt_builder.py   # 프롬프트 조립 어댑터
+-- templates.py        # VLM/생성 프롬프트 템플릿
+-- generator.py        # 이미지 생성 + 검수 루프
+-- validator.py        # 착장 스왑 검증기
```

---

## 모듈 인터페이스 (core.outfit_swap)

### 1. 분석 함수 (analyzer.py)

```python
from core.outfit_swap import (
    analyze_source_for_swap,  # 소스 이미지 분석 (얼굴/포즈/배경)
    analyze_outfit_items,     # 착장 이미지들 분석 (색상/로고/소재)
    pil_to_part,              # PIL Image -> API Part 변환
    SourceAnalysisResult,     # 소스 분석 결과 객체
)

# 소스 분석 (반환: dict)
source_analysis = analyze_source_for_swap(source_pil, client)
# -> {"face_description": ..., "pose_description": ..., "background_description": ..., "_raw": {...}}

# 착장 분석 (반환: list[dict])
outfit_analyses = analyze_outfit_items(outfit_pils, client)
# -> [{"item_type": ..., "color": ..., "logo": ..., "prompt_description": ...}, ...]
```

### 2. 프롬프트 빌더 (prompt_builder.py)

```python
from core.outfit_swap import build_outfit_swap_prompt

# dict 기반 (analyze_source_for_swap + analyze_outfit_items 결과)
prompt = build_outfit_swap_prompt(
    source_analysis=source_analysis,  # dict
    outfit_analyses=outfit_analyses,  # list[dict]
)
```

**프롬프트 설계 원칙:**
- 소스 분석 결과(face/pose/background)는 **prompt.json에 기록용으로만 저장**
- 프롬프트에는 포즈/얼굴/배경 텍스트를 나열하지 않음
- "SOURCE IMAGE에서 모든 것을 보존하라"는 블랭킷 지시만 사용
- 착장 설명만 프롬프트에 포함 ({outfit_description})

### 3. 생성 함수 (generator.py)

```python
from core.outfit_swap import generate_outfit_swap, generate_with_validation

# 검수 없이 단순 생성
image = generate_outfit_swap(
    source_image=source_pil,        # PIL Image 또는 파일 경로
    outfit_images=[outfit1, outfit2], # PIL Image 목록 (최대 10개)
    client=genai_client,
    temperature=0.2,
    aspect_ratio="auto",            # "auto" = 소스 비율 자동 감지 (권장!)
    resolution="2K",
)

# 검수 포함 생성 (권장)
result = generate_with_validation(
    source_image=source_pil,
    outfit_images=[outfit1, outfit2],
    client=genai_client,             # 없으면 api_key로 자동 생성
    api_key=None,                    # 없으면 자동 로테이션
    max_retries=2,                   # 최대 재시도 횟수
    temperature=0.2,
    aspect_ratio="auto",             # 소스 비율 자동 감지
    resolution="2K",
)
# result = {"image": PIL.Image, "score": int, "passed": bool, "criteria": dict, "history": list}

if result["passed"]:
    result["image"].save("output.png")
```

### 4. 비율 자동 감지 (core.options)

```python
from core.outfit_swap import detect_aspect_ratio

# PIL Image, 파일 경로, (width, height) 튜플 모두 지원
ratio = detect_aspect_ratio(source_pil)         # "2:3"
ratio = detect_aspect_ratio("path/to/image.jpg") # "3:4"
ratio = detect_aspect_ratio((8256, 5504))        # "3:2"
```

### 5. 검증기 (validator.py)

```python
from core.outfit_swap import OutfitSwapValidator

validator = OutfitSwapValidator(client)
result = validator.validate(
    generated_img=generated_pil,
    reference_images={
        "source": [source_pil],
        "outfit": outfit_pils,
    },
)
# result.total_score, result.passed, result.criteria_scores, result.issues
```

---

## 프롬프트 템플릿 (templates.py)

### EDITING MODE 생성 프롬프트

```
OUTFIT EDITING MODE - NOT IMAGE GENERATION

This is a CLOTHING LAYER SWAP on an existing photograph.
Think of it as Photoshop: the person, pose, and background are LOCKED layers.
You are ONLY replacing the clothing layer.

## MATHEMATICAL PRESERVATION REQUIREMENTS (ABSOLUTE)
- Person height / Frame height = IDENTICAL to SOURCE IMAGE
- Scale factor = 1.0 (NO resizing, NO repositioning)
- Body angle, joint positions, weight distribution = PIXEL-LOCKED to SOURCE
- Face identity, expression, skin = PIXEL-LOCKED to SOURCE
- Background, lighting, color grade = PIXEL-LOCKED to SOURCE

## CRITICAL ANTI-DRIFT WARNING
IGNORE ALL POSES in outfit reference images.
IGNORE ALL FACES in outfit reference images.
Extract ONLY the garment details: color, material, logo, fit, design.

## OUTFIT TO APPLY (FROM IMAGES 2+)
{outfit_description}

## ABSOLUTE PROHIBITIONS
1. DO NOT change the person's face from SOURCE
2. DO NOT change the person's pose from SOURCE
3. DO NOT change the background from SOURCE
4. DO NOT adopt any pose from outfit reference images
5. DO NOT mix source clothing with new outfit
6. DO NOT shrink, move, or rescale the person
7. DO NOT change the camera angle or framing
```

---

## 검수 기준 (Validation)

| 항목 | 가중치 | 개별 Pass | Auto-Fail |
|------|--------|----------|-----------|
| outfit_accuracy (착장 정확도) | 35% | >= 90 | < 70 |
| face_identity (얼굴 동일성) | 25% | >= 95 | < 80 |
| pose_preservation (포즈 유지) | 25% | >= 95 | < 90 |
| outfit_draping (착장 자연스러움) | 10% | >= 80 | - |
| background_preservation (배경 유지) | 5% | >= 90 | - |

**Pass 조건:** total_score >= 92 AND 각 필수 기준 통과

### Auto-Fail 조건

- 얼굴 다른 사람 (face_identity < 80)
- 포즈 변경 심각 (pose_preservation < 90)
- 착장 색상/로고 불일치 (outfit_accuracy < 70)

### 검수 프롬프트 (VLM STEP-BY-STEP)

CLAUDE.md VLM 검수 원칙 준수:
1. 지시만 하지 말고 STEP-BY-STEP으로 강제
2. 출력 형식 명시 (reason: "REF:~, GEN:~, 감점:~")
3. 감점 계산 공식 명시 (100 - 합계 감점)

---

## 재시도 전략 (Retry)

| 시도 | Temperature | 추가 조치 |
|------|-------------|----------|
| 1회 | 0.2 | 기본 프롬프트 |
| 2회 | 0.25 | 실패 기준별 ENHANCEMENT_RULES 추가 |
| 3회 | 0.30 | 강화 프롬프트 + 온도 상향 |

최대 재시도: 2회 (총 3번 시도)

### 실패 기준별 강화 규칙

| 실패 기준 | 강화 내용 |
|----------|----------|
| outfit_accuracy | EXACT colors, ALL items present, logo match |
| face_identity | Preserve face EXACTLY, same person |
| pose_preservation | EXACT same pose, arm/leg positions match |
| outfit_draping | Natural draping, physics-based wrinkles |
| background_preservation | Keep background EXACTLY as SOURCE |

---

## 전체 사용 예시

```python
from PIL import Image
from google import genai
from core.api import _get_next_api_key
from core.outfit_swap import (
    generate_with_validation,
    detect_aspect_ratio,
)

# 1. 이미지 로드
source_pil = Image.open("source.jpg").convert("RGB")
outfit_pils = [
    Image.open("outfit_top.jpg").convert("RGB"),
    Image.open("outfit_bottom.jpg").convert("RGB"),
]

# 2. 비율 확인
ratio = detect_aspect_ratio(source_pil)
print(f"Source ratio: {source_pil.size} -> {ratio}")

# 3. 생성 + 검수
client = genai.Client(api_key=_get_next_api_key())
result = generate_with_validation(
    source_image=source_pil,
    outfit_images=outfit_pils,
    client=client,
    aspect_ratio="auto",  # 소스 비율 자동 감지
    resolution="2K",
    max_retries=2,
)

# 4. 결과 확인
if result["passed"]:
    result["image"].save("output.jpg", quality=95)
    print(f"Score: {result['score']}/100")
else:
    print(f"Failed: {result['score']}/100")
    print(f"Issues: {result['history'][-1].get('issues', [])}")
```

---

## 핵심 원칙

| 항목 | 처리 방식 |
|------|----------|
| 소스 이미지 | **API에 직접 전달** + EDITING CANVAS 라벨 |
| 착장 이미지 | **이미지 직접 전달** + OUTFIT REFERENCE 라벨 + VLM 텍스트 보조 |
| 비율 | **소스 비율 자동 감지** (aspect_ratio="auto") |
| 프롬프트 | **EDITING MODE** (착장 레이어만 교체, 나머지 LOCKED) |
| 포즈 보존 | **소스 분석 텍스트를 프롬프트에 넣지 않음** (블랭킷 보존 지시) |
| Anti-Drift | 착장 이미지에서 포즈/얼굴/배경 **완전 무시** 지시 |

### 왜 EDITING MODE?

기존 방식 (reconstruction):
- VLM으로 포즈/얼굴/배경을 텍스트로 변환
- 텍스트로 재구성 지시 -> VLM 변환 과정에서 정보 손실
- 결과: 포즈 드리프트, 얼굴 변형

현재 방식 (editing):
- 소스 이미지 자체가 "편집 캔버스"
- 텍스트로 포즈/얼굴을 설명하지 않음
- "모든 것 유지, 착장만 교체" 블랭킷 지시
- 결과: 포즈/얼굴/배경 정확 보존

### 왜 비율 자동 감지?

- 소스 2:3(세로) + 생성 3:4(세로) = 비율 불일치 -> 포즈 약간 변경
- 소스 3:2(**가로**) + 생성 3:4(**세로**) = 심각한 불일치 -> 포즈 완전 변경
- 자동 감지로 소스와 동일 비율 사용 -> 포즈 보존

---

## 출력 폴더 구조

```
Fnf_studio_outputs/
+-- outfit_swap/
    +-- 20260303_141839_st_tennis_dress/
        +-- images/
        |   +-- input_source_01.jpg
        |   +-- input_outfit_01.jpg
        |   +-- input_outfit_02.jpg
        |   +-- output_001.jpg
        |   +-- output_002.jpg
        |   +-- output_003.jpg
        +-- prompt.json       # 프롬프트 + 분석 결과
        +-- prompt.txt        # 가독용 텍스트
        +-- config.json       # 생성 설정
        +-- validation.json   # 검수 결과 (있으면)
```

---

## 파일 구조

```
.claude/skills/착장_outfit-swap/
+-- SKILL.md          # 이 문서

core/outfit_swap/
+-- __init__.py       # 공개 API (generate_with_validation 등)
+-- analyzer.py       # VLM 분석 (analyze_source_for_swap, analyze_outfit_items)
+-- prompt_builder.py # 프롬프트 조립 어댑터
+-- templates.py      # EDITING MODE 프롬프트 + VLM 분석/검수 프롬프트
+-- generator.py      # 생성 엔진 + 검수 루프 + 비율 자동 감지
+-- validator.py      # OutfitSwapValidator (WorkflowValidator 기반)
```

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 포즈 변경됨 (서있는데 앉음) | 비율 불일치 (가로->세로 등) | aspect_ratio="auto" 사용 |
| 포즈 약간 달라짐 | 착장 이미지 모델 포즈 영향 | Anti-Drift 라벨 확인 |
| 얼굴 안 닮음 | 소스 이미지 품질 낮음 | 고해상도 정면 이미지 사용 |
| 착장 색상 틀림 | VLM 분석 부정확 | 착장 분석 프롬프트 강화 |
| 착장 로고 누락 | 착장 이미지 해상도 낮음 | 착장 이미지 고해상도 사용 |
| 드레이핑 어색 | 포즈와 착장 호환성 낮음 | 드레이핑 규칙 프롬프트 강화 |
| 사람 크기 변경 | Scale factor != 1.0 | MATHEMATICAL PRESERVATION 확인 |
