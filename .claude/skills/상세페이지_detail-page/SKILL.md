---
name: detail-page
description: Figma 이커머스 상세페이지 자동 생성 - MLB 기준 템플릿
user-invocable: true
trigger-keywords: ["상세페이지", "detail page", "제품 상세", "상세 페이지"]
---

# 상세페이지 자동 생성

> 제품/모델 이미지 → Figma에 상세페이지 레이아웃 자동 조립

---

## 핵심 컨셉

이커머스 상세페이지를 Figma에 자동으로 생성한다.
모델컷 5장 + 제품 누끼 2장 + FABRIC 섹션 + 디테일 클로즈업 3장.

---

## MLB 표준 레이아웃 (860px)

| 순서 | 섹션 | 슬롯 수 | 사이즈 | 소스 |
|------|------|---------|--------|------|
| 1 | 모델컷 | 5장 | 860x1140 (3:4) | AI 생성 또는 촬영 이미지 |
| 2 | 제품 단독 | 2장 | 860x860 (1:1) | 제품 누끼 |
| 3 | FABRIC | 1섹션 | 860x500 | 소재 정보 텍스트 |
| 4 | 디테일 | 3장 | 860x860 (1:1) | 로고/라벨/원단 크롭 |

총 10개 이미지 슬롯 + 1개 정보 섹션

---

## 워크플로

```
1. 사용자: "상세페이지 만들어"
   |
   v
2. Claude: [AskUserQuestion] 필수 정보 수집
   - 모델 이미지 폴더 (또는 개별 파일)
   - 제품 이미지 (앞/뒤)
   - 상품명, MODEL SPEC (Height, Fitting Size)
   - 소재 정보 (FABRIC)
   |
   v
3. Claude: DetailPageFigmaBuilder로 빌드 시퀀스 생성
   |
   v
4. Claude: Figma MCP 도구 순차 호출
   - join_channel          → Figma 연결
   - create_frame          → 메인 페이지 프레임 (860px, VERTICAL)
   - 섹션별 이미지 슬롯 생성 + 이미지 배치
   - 텍스트 요소 삽입 (MODEL SPEC, FABRIC)
   |
   v
5. 결과: Figma에 완성된 상세페이지
```

---

## 필수 입력

| 입력 | 필수 | 설명 |
|------|------|------|
| 모델 이미지 | O | 모델컷 5장 (AI 생성 가능) |
| 제품 이미지 | O | 앞면/뒷면 누끼 |
| 상품명 | O | 제품명 |
| MODEL SPEC | X | Height, Fitting Size |
| FABRIC 정보 | X | 소재 아이콘/설명 |
| 디테일 이미지 | X | 로고/라벨/원단 클로즈업 |

---

## AI 이미지 생성 연동

모델 이미지가 없으면 이커머스 스킬로 자동 생성:

```
얼굴 이미지 + 착장 이미지 제공 시:
→ core/ecommerce/detail_page.py의 DetailPageGenerator 사용
→ 5개 포즈 자동 생성 (front_standing, front_casual x2, front_standing, detail_closeup)
→ 검수 + 재생성 (최대 2회)
→ 생성된 이미지를 Figma 슬롯에 자동 배치
```

---

## 코드 모듈

| 파일 | 역할 |
|------|------|
| `db/ecommerce_templates.json` | 상세페이지 레이아웃 템플릿 DB |
| `core/ecommerce/template_presets.py` | 템플릿 프리셋 관리 |
| `core/ecommerce/figma_builder.py` | Figma MCP 시퀀스 생성기 |
| `core/ecommerce/detail_page.py` | AI 이미지 세트 생성기 |

---

## Figma MCP 빌드 시퀀스

```python
# 1. 메인 페이지 프레임 (860px 고정폭, 세로 자동)
create_frame(x=0, y=0, width=860, height=total_height,
             name="상세페이지_MLB_{product_name}",
             layoutMode="VERTICAL")

# 2. 모델컷 섹션 (5장, 각 860x1140)
for i, model_img in enumerate(model_images):
    rect = create_rectangle(x=0, y=y_offset, width=860, height=1140,
                            parent=page_frame_id)
    set_node_image_fill(rect.id, imageUrl=model_img, scaleMode="FILL")

# 3. 제품 단독 섹션 (2장, 각 860x860)
for i, product_img in enumerate(product_images):
    rect = create_rectangle(x=0, y=y_offset, width=860, height=860,
                            parent=page_frame_id)
    set_node_image_fill(rect.id, imageUrl=product_img, scaleMode="FIT")

# 4. FABRIC 섹션 (860x500, 텍스트 블록)
fabric_frame = create_frame(x=0, y=y_offset, width=860, height=500,
                             parent=page_frame_id,
                             fillColor={"r":0.97,"g":0.97,"b":0.97,"a":1})
create_text(x=40, y=40, text="FABRIC", fontSize=24, fontWeight=700,
            parent=fabric_frame.id)
create_text(x=40, y=80, text=fabric_info, fontSize=14,
            parent=fabric_frame.id)

# 5. 디테일 클로즈업 섹션 (3장, 각 860x860)
for i, detail_img in enumerate(detail_images):
    rect = create_rectangle(x=0, y=y_offset, width=860, height=860,
                            parent=page_frame_id)
    set_node_image_fill(rect.id, imageUrl=detail_img, scaleMode="FILL")
```

---

## MODEL SPEC 섹션 포함 시

모델 정보가 제공되면 모델컷 첫 장 아래에 삽입:

```
HEIGHT: 172cm
FITTING SIZE: S (TOP) / 26 (BOTTOM)
```

---

## 섹션 구성 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| 모델컷 수 | 5장 | 최소 1장, 최대 8장 |
| 제품 이미지 수 | 2장 | 앞/뒤 |
| FABRIC 섹션 | 포함 | 소재 정보 있으면 자동 삽입 |
| 디테일 수 | 3장 | 선택 (없으면 생략) |
| MODEL SPEC | 선택 | 모델 신체/착용 정보 |

---

## 이미지 모드 선택

```
[A] 이미지 직접 제공  → 제공된 이미지를 Figma 슬롯에 배치
[B] AI 자동 생성      → 얼굴+착장 이미지 기반으로 모델컷 생성 후 배치
[C] 혼합              → 일부는 직접 제공, 부족한 슬롯은 AI 생성
```

---

**버전**: 1.0.0
**작성일**: 2026-03-04
**관련 스킬**: `ecommerce` (AI 이미지 생성 연동)
**관련 DB**: `db/ecommerce_templates.json`
