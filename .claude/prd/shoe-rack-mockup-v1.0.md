# PRD: Shoe Rack Mockup v1.0

> 신발장 목업 워크플로 개선 - 2026-02-24

---

## 1. 배경 및 현황

### 1.1 현재 버전
- **v0.9** (2026-02-20)
- 배치 테스트 완료: 7/7 이미지 성공

### 1.2 배치 테스트 결과물 분석
- **출력 폴더**: `Fnf_studio_outputs/shoe_rack_mockup/20260220_182839_batch_2to8/`
- **VLM 분석 결과**:
  - 이미지 2~5: `single` 패턴, `left-toe-forward`
  - 이미지 6~7: `depth-overlap` 패턴, `left-toe-forward`
  - 이미지 8: `depth-overlap` 패턴, `right-toe-forward` (거울 반사)

---

## 2. 발견된 문제점

### 2.1 이미지별 문제

| 이미지 | 문제 | 심각도 | 카테고리 |
|--------|------|--------|----------|
| **3** | 신발이 비스듬하게 연출됨 | HIGH | 포즈 위반 |
| **3** | 왼쪽/오른쪽 신발이 동일 | HIGH | 중복 신발 |
| **4** | 신발이 비스듬하게 연출됨 | HIGH | 포즈 위반 |
| **5** | 배경이 코랄색으로 변함 | CRITICAL | 배경 보존 실패 |
| **5** | 겹치는(중복) 신발이 너무 많음 | HIGH | 중복 신발 |
| **6** | 신발 뒤에 이상한 아티팩트 | MEDIUM | 품질 문제 |
| **6** | 겹치는(중복) 신발이 많음 | HIGH | 중복 신발 |
| **7** | 겹치는(중복) 신발이 많음 (거의 완벽) | MEDIUM | 중복 신발 |
| **8** | 철제 매대가 코랄~민트 그라데이션 | CRITICAL | 배경 보존 실패 |
| **8** | 신발 방향이 전부 틀림 | HIGH | 방향 오류 |
| **8** | 거울면이 너무 또렷함 | HIGH | 거울 처리 실패 |
| **8** | 거울면 신발 mirror 반전 안됨 | HIGH | 거울 처리 실패 |

### 2.2 문제 카테고리 분석

| 카테고리 | 해당 이미지 | 근본 원인 | 해결 방안 |
|----------|------------|----------|----------|
| **중복 신발** | 3, 5, 6, 7 | 프롬프트가 "다른 신발" 강제 못함 | 프롬프트 강화: 모든 신발 UNIQUE 강조 |
| **비스듬한 연출** | 3, 4 | 프롬프트에 "정면 배치" 규칙 없음 | 프롬프트 추가: "shoes face STRAIGHT forward" |
| **배경 보존 실패** | 5, 8 | 인페인팅이 마스크 외 영역 변형 | 프롬프트 강화 + 검증 추가 |
| **거울 처리** | 8 | 거울 로직 미구현 | 후처리 로직 추가 (blur + mirror flip) |
| **아티팩트** | 6 | 생성 품질 문제 | 검증 + 재생성 로직 |

### 2.3 공통 요청사항

1. **사용된 신발 이미지를 아웃풋 폴더에 복사**
2. **신발 이미지 경로 변경**: `vlm_테스트용/신발/side_view_left_toe` (56개)

---

## 3. 수정 요구사항

### 3.1 신발 중복 방지 (CRITICAL)

**현재 문제:**
- 같은 디자인의 신발이 여러 슬롯에 반복 등장
- LEFT 열과 RIGHT 열에 동일 신발 사용

**요구사항:**
```
- 모든 18개 슬롯에 서로 다른 신발 디자인 사용
- Stage 1: 신발 1~6 (각각 다른 디자인)
- Stage 2: 신발 7~12 (각각 다른 디자인)
- Stage 3: 신발 13~18 (각각 다른 디자인)
- 같은 row 내 LEFT/RIGHT도 다른 디자인 (총 36개 필요 → 56개 중 사용)
```

**프롬프트 추가:**
```
*** CRITICAL: NO DUPLICATE SHOES ***
- ALL 6 rows must have COMPLETELY DIFFERENT shoe designs
- Row 1 ≠ Row 2 ≠ Row 3 ≠ Row 4 ≠ Row 5 ≠ Row 6
- Do NOT repeat any shoe design within this color column
```

### 3.2 비스듬한 연출 금지 (HIGH)

**현재 문제:**
- 신발이 비스듬하게(angled) 배치됨
- 신발장 진열대 느낌이 아닌 예술적 연출 느낌

**요구사항:**
```
- 신발은 항상 선반과 평행하게 정면 배치
- 비스듬한 각도 금지
- 매장 진열대 실제 배치 방식 준수
```

**프롬프트 추가:**
```
*** CRITICAL: STRAIGHT PLACEMENT ***
- Shoes must face STRAIGHT forward
- NO angled or tilted placement
- Shoes sit FLAT on shelf, parallel to shelf edge
- This is a retail display, NOT artistic arrangement
```

### 3.3 배경 보존 강화 (CRITICAL)

**현재 문제:**
- 배경 색상이 변형됨 (코랄색으로 물듦)
- 철제 매대가 그라데이션으로 변함

**요구사항:**
```
- 마스크 영역(색상 실루엣) 외에는 절대 변경 금지
- 선반, 메쉬, 벽면, 철제 구조물 100% 보존
- 원본 이미지의 조명/그림자도 유지
```

**프롬프트 추가:**
```
*** ABSOLUTE BACKGROUND PRESERVATION ***
- ONLY change the colored silhouette areas
- Metal shelves: DO NOT CHANGE COLOR
- Mesh/grid: Keep exact same pattern
- Wall: Keep exact same color and texture
- ANY change to background = FAILURE
```

### 3.4 거울 처리 (이미지 8 전용)

**현재 문제:**
- 이미지 8번 왼쪽은 거울에 비친 오른쪽 캐비닛
- 현재 거울면이 너무 또렷하고, mirror 반전 안됨

**요구사항:**
```
1. 오른쪽 캐비닛만 먼저 처리 (신발 교체)
2. 결과물을 좌우 반전(mirror flip)
3. 거울 영역에 blur 효과 적용 (gaussian blur 3~5px)
4. 원본 거울 영역에 합성
```

**후처리 파이프라인:**
```python
def process_mirror_image(result_image, mirror_mask):
    # 1. 오른쪽 캐비닛 영역 추출
    right_cabinet = crop_right_cabinet(result_image)

    # 2. 좌우 반전
    mirrored = right_cabinet.transpose(Image.FLIP_LEFT_RIGHT)

    # 3. blur 적용 (거울 느낌)
    blurred = mirrored.filter(ImageFilter.GaussianBlur(4))

    # 4. 거울 영역에 합성
    final = composite_to_mirror_area(result_image, blurred, mirror_mask)

    return final
```

### 3.5 사용된 신발 저장

**요구사항:**
```
- 각 이미지 출력 폴더에 `inputs/` 서브폴더 생성
- 해당 이미지에 사용된 신발 18장 복사
- 파일명: shoe_01.jpg ~ shoe_18.jpg (순번 + 원본명)
```

**출력 구조:**
```
Fnf_studio_outputs/shoe_rack_mockup/{timestamp}/
├── image_2/
│   ├── inputs/
│   │   ├── shoe_01_커브러너.jpg
│   │   ├── shoe_02_범프청키.jpg
│   │   └── ... (18개)
│   ├── img2_final_mockup.png
│   ├── img2_stage1_result.png
│   ├── img2_stage2_result.png
│   └── img2_stage3_result.png
├── image_3/
│   └── ...
└── batch_results.json
```

---

## 4. 기술 구현 계획

### 4.1 templates.py 수정

**변경사항:**
1. 중복 방지 섹션 추가
2. 비스듬한 연출 금지 섹션 추가
3. 배경 보존 강화 섹션 추가

```python
# v1.0 추가 규칙
NO_DUPLICATE_SECTION = """*** CRITICAL: NO DUPLICATE SHOES ***
- ALL 6 rows must have COMPLETELY DIFFERENT shoe designs
- Row 1 ≠ Row 2 ≠ Row 3 ≠ Row 4 ≠ Row 5 ≠ Row 6
- Each reference shoe used EXACTLY ONCE
- Do NOT repeat any shoe design within this color column"""

STRAIGHT_PLACEMENT_SECTION = """*** CRITICAL: STRAIGHT PLACEMENT ***
- Shoes must face STRAIGHT forward, parallel to shelf
- NO angled, tilted, or artistic placement
- Shoes sit FLAT on shelf surface
- This is a RETAIL DISPLAY, not artistic arrangement
- Toe direction: {direction}"""

BACKGROUND_PRESERVATION_SECTION = """*** ABSOLUTE BACKGROUND PRESERVATION ***
- ONLY change the {color} colored silhouette areas
- Metal shelves: DO NOT CHANGE COLOR (no gradients!)
- Mesh/grid: Keep EXACT same pattern and color
- Wall: Keep EXACT same color and texture
- Frame/structure: NO color changes allowed
- ANY change to non-silhouette areas = FAILURE"""
```

### 4.2 test_batch_pipeline.py 수정

**변경사항:**
1. SHOES_DIR 경로 변경
2. 사용된 신발 저장 로직 추가

```python
# 신발 경로 변경
SHOES_DIR = project_root / "vlm_테스트용" / "신발" / "side_view_left_toe"

# 신발 저장 함수
def save_used_shoes(shoes_for_image, output_dir):
    """사용된 신발 이미지를 inputs/ 폴더에 저장"""
    inputs_dir = output_dir / "inputs"
    inputs_dir.mkdir(exist_ok=True)

    for i, (name, img) in enumerate(shoes_for_image):
        # 순번 + 원본 파일명
        safe_name = name.replace(" ", "_")
        dest_path = inputs_dir / f"shoe_{i+1:02d}_{safe_name}"
        img.save(dest_path, quality=95)
```

### 4.3 mirror_processor.py (신규)

**이미지 8 전용 후처리 모듈:**

```python
"""
Mirror Processor - 거울 반사 처리
=================================
이미지 8번처럼 왼쪽에 거울이 있는 경우 처리
"""

from PIL import Image, ImageFilter

def process_mirror_reflection(
    result_image: Image.Image,
    mirror_side: str = "left",
    blur_radius: float = 4.0,
) -> Image.Image:
    """
    거울 반사 후처리

    1. 원본 캐비닛 영역 복사
    2. 좌우 반전 (mirror flip)
    3. blur 적용 (거울 느낌)
    4. 거울 영역에 합성
    """
    width, height = result_image.size
    half_width = width // 2

    if mirror_side == "left":
        # 오른쪽 캐비닛 추출
        cabinet = result_image.crop((half_width, 0, width, height))
        # 좌우 반전
        mirrored = cabinet.transpose(Image.FLIP_LEFT_RIGHT)
        # blur 적용
        blurred = mirrored.filter(ImageFilter.GaussianBlur(blur_radius))
        # 왼쪽에 합성
        result = result_image.copy()
        result.paste(blurred, (0, 0))
    else:
        # 왼쪽 캐비닛 추출
        cabinet = result_image.crop((0, 0, half_width, height))
        # 좌우 반전
        mirrored = cabinet.transpose(Image.FLIP_LEFT_RIGHT)
        # blur 적용
        blurred = mirrored.filter(ImageFilter.GaussianBlur(blur_radius))
        # 오른쪽에 합성
        result = result_image.copy()
        result.paste(blurred, (half_width, 0))

    return result
```

### 4.4 compositor.py 수정

**변경사항:**
1. save_pipeline_results()에 신발 저장 로직 추가
2. 이미지 8 거울 처리 옵션 추가

---

## 5. 검증 기준

### 5.1 v1.0 검증 체크리스트

| # | 항목 | 기준 | 필수 |
|---|------|------|------|
| 1 | 중복 신발 없음 | 18개 슬롯 모두 다른 디자인 | YES |
| 2 | 정면 배치 | 모든 신발 선반과 평행 | YES |
| 3 | 배경 보존 | 마스크 외 영역 100% 동일 | YES |
| 4 | 신발 저장 | inputs/ 폴더에 18장 저장 | YES |
| 5 | 거울 처리 (이미지 8) | blur + mirror flip 적용 | YES |
| 6 | 신발 방향 일치 | VLM 분석 방향과 동일 | YES |

### 5.2 Auto-Fail 조건

- 배경 색상 변형 (철제 매대 색상 변경)
- 같은 신발 디자인 2회 이상 등장
- 신발 비스듬한 배치
- 이미지 8 거울면 미처리

---

## 6. 파일 변경 목록

| 파일 | 변경 내용 | 상태 |
|------|----------|------|
| `templates.py` | 프롬프트 강화 (v1.0) | 대기 |
| `test_batch_pipeline.py` | 경로 변경 + 신발 저장 | 대기 |
| `compositor.py` | 신발 저장 + 거울 옵션 | 대기 |
| `mirror_processor.py` | 신규 모듈 | 대기 |
| `SKILL.md` | v1.0 변경사항 | 대기 |

---

## 7. 테스트 계획

### 7.1 단계별 테스트

1. **단일 이미지 테스트** (이미지 2)
   - 프롬프트 변경 효과 확인
   - 중복 방지, 정면 배치, 배경 보존 검증

2. **거울 테스트** (이미지 8)
   - mirror_processor 동작 확인
   - blur 강도 조절

3. **전체 배치 테스트** (이미지 2~8)
   - 7개 이미지 순차 처리
   - 모든 검증 기준 확인

### 7.2 예상 소요 시간

- 단일 이미지: ~2분 (3 stages)
- 거울 테스트: ~3분 (3 stages + 후처리)
- 전체 배치: ~20분 (7 images × 3 stages)

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| PRD v1.0 | 2026-02-24 | 초안 작성 - 문제점 분석 및 수정 계획 |
