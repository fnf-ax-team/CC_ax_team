---
name: ecommerce-fullset
description: 이커머스 풀세트 - AI 이미지 생성 + 상세페이지 + 채널 배너 End-to-End
user-invocable: true
trigger-keywords: ["풀세트", "이커머스 풀세트", "전체 세트", "ecommerce full", "상세+배너"]
---

# 이커머스 풀세트 (End-to-End)

> 제품 정보만 입력하면 AI 이미지 생성 -> 상세페이지 -> 채널 배너까지 한 번에

---

## 핵심 컨셉

하나의 명령으로 이커머스에 필요한 모든 에셋을 자동 생성:

```
입력: 얼굴 + 착장 + 제품 이미지 + 상품 정보
  |
  v
Phase 1: AI 모델 이미지 5장 생성 (포즈별)
Phase 2: Figma 상세페이지 자동 조립 (10슬롯)
Phase 3: Figma 채널 배너 30종 자동 생성
Phase 4: 결과 저장 + 요약
  |
  v
출력: Figma 상세페이지 + 30종 배너 + 검수 결과
```

---

## 워크플로

```
1. Claude: [AskUserQuestion] 순차 입력 수집

   Q1: "얼굴 이미지 폴더 경로?" (AI 생성 시 필수)
   Q2: "착장 이미지 폴더 경로?" (AI 생성 시 필수)
   Q3: "제품 이미지 경로? (앞/뒤)" (필수)
   Q4: "상품명?" (필수)
   Q5: "MODEL SPEC? (Height, Fitting Size)" (선택)
   Q6: "소재 정보? (FABRIC)" (선택)
   Q7: [AskUserQuestion 클릭] 배너 채널 선택 (네이버/구글/카카오/메타/유튜브/전체)
   Q8: "가격?" (선택)
   Q9: "CTA 텍스트?" (기본: 자세히 보기)

2. Claude: EcommercePipeline 실행
   - Phase 1: DetailPageGenerator.generate_full_set()
   - Phase 2: DetailPageFigmaBuilder.build_sequence()
   - Phase 3: BannerFigmaBuilder.build_channel_banners()
   - Phase 4: 결과 저장

3. Claude: Figma MCP 순차 실행
   - join_channel -> Figma 연결
   - 상세페이지 액션 실행 (20+ 도구 호출)
   - 채널 배너 액션 실행 (채널당 40~70 도구 호출)

4. Claude: 결과 보고
   - 생성된 이미지 요약
   - 검수 결과 (한국어 표)
   - Figma 링크
   - 저장 경로 안내
```

---

## 코드 사용법

### 파이프라인 실행

```python
from core.ecommerce.pipeline import EcommercePipeline, PipelineConfig

config = PipelineConfig(
    product_name="MLB NY 빅로고 반팔티",
    brand="MLB",
    price="59,000",
    discount="20%",

    # 이미지 경로
    face_image_dir="inputs/face",
    outfit_image_dir="inputs/outfit",
    product_image_paths=["inputs/product_front.jpg", "inputs/product_back.jpg"],
    detail_image_paths=["inputs/logo.jpg", "inputs/label.jpg"],

    # 모델 스펙
    model_spec={"height": "175", "fitting_size": "S / 240mm"},
    fabric_info={"icon": "SPAN", "description": "모달 원사로 부드럽고 시원한 착용감"},

    # 배너 채널
    channels=["naver", "google", "kakao", "meta", "youtube"],
)

pipeline = EcommercePipeline(config)
result = pipeline.run()
```

### 간편 실행

```python
from core.ecommerce.pipeline import run_ecommerce_pipeline

result = run_ecommerce_pipeline(
    product_name="MLB NY 빅로고 반팔티",
    face_image_dir="inputs/face",
    outfit_image_dir="inputs/outfit",
    product_image_paths=["inputs/product_front.jpg"],
)
```

### Figma MCP 실행 (Claude)

파이프라인 실행 후 `result.detail_page_actions`와 `result.banner_actions`에
Figma MCP 도구 호출 시퀀스가 담겨 있다. Claude가 이 시퀀스를 순차 실행한다.

```python
# 상세페이지 액션 실행
for action in result.detail_page_actions:
    # action.tool: "create_frame", "create_text", "set_node_image_fill" 등
    # action.params: 도구 파라미터
    # action.depends_on: 부모 노드 참조 (parentId 주입 필요)
    pass

# 채널 배너 액션 실행
for channel, actions in result.banner_actions.items():
    for action in actions:
        pass
```

---

## 산출물

```
Fnf_studio_outputs/ecommerce/{timestamp}_{description}/
+-- detail_page/
|   +-- images/
|   |   +-- model_1.jpg ~ model_5.jpg (AI 생성)
|   |   +-- product_front.jpg, product_back.jpg
|   |   +-- logo_detail.jpg, label_detail.jpg, fabric_detail.jpg
|   +-- config.json
|   +-- validation.json
+-- figma_actions/
|   +-- detail_page_actions.json
|   +-- banner_naver_actions.json
|   +-- banner_google_actions.json
|   +-- banner_kakao_actions.json
|   +-- banner_meta_actions.json
|   +-- banner_youtube_actions.json
+-- pipeline_config.json
```

---

## 코드 모듈

| 파일 | 역할 |
|------|------|
| `core/ecommerce/pipeline.py` | E2E 파이프라인 오케스트레이터 |
| `core/ecommerce/detail_page.py` | AI 이미지 세트 생성기 (모델컷 5장 + 제품 누끼 + 디테일) |
| `core/ecommerce/figma_builder.py` | Figma 상세페이지 빌더 (MCP 도구 호출 시퀀스) |
| `core/ecommerce/generator.py` | 이커머스 이미지 생성 + 검수 (generate_with_validation) |
| `core/ecommerce/analyzer.py` | 착장/얼굴 VLM 분석 |
| `core/ecommerce/validator.py` | 이커머스 검증기 |
| `core/ecommerce/template_presets.py` | 상세페이지 템플릿 설정 |
| `core/banner/figma_banner_builder.py` | Figma 배너 빌더 (MCP 도구 호출 시퀀스) |
| `core/banner/layout_engine.py` | 배너 레이아웃 자동 계산 |
| `db/ecommerce_templates.json` | 상세페이지 레이아웃 DB |
| `db/channel_specs.json` | 채널별 배너 스펙 DB |
| `db/banner_templates.json` | 배너 레이아웃 패턴 DB |

---

## PipelineConfig 전체 옵션

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `product_name` | str | "" | 상품명 |
| `brand` | str | "MLB" | 브랜드 |
| `price` | str? | None | 가격 (예: "59,000") |
| `discount` | str? | None | 할인 (예: "20%") |
| `model_spec` | dict? | None | {"height": "175", "fitting_size": "S / 240mm"} |
| `fabric_info` | dict? | None | {"icon": "SPAN", "description": "..."} |
| `face_image_dir` | str? | None | 얼굴 이미지 폴더 경로 |
| `outfit_image_dir` | str? | None | 착장 이미지 폴더 경로 |
| `product_image_paths` | list | [] | 제품 이미지 경로 [앞면, 뒷면] |
| `detail_image_paths` | list | [] | 디테일 이미지 경로 [로고, 라벨, 원단] |
| `model_image_paths` | list | [] | 기존 모델 이미지 (AI 생성 안 할 때) |
| `generate_model_shots` | bool | True | AI 이미지 생성 여부 |
| `aspect_ratio` | str | "3:4" | 비율 |
| `resolution` | str | "2K" | 해상도 |
| `background_preset` | str | "white_studio" | 배경 프리셋 |
| `channels` | list | [전체] | 배너 채널 리스트 |
| `cta_text` | str | "자세히 보기" | CTA 버튼 텍스트 |
| `detail_page_template` | str | "mlb_standard" | 상세페이지 템플릿 ID |
| `image_base_url` | str | "http://localhost:8000/outputs" | 이미지 서빙 URL |
| `client` | Any? | None | Google GenAI 클라이언트 (외부 주입) |
| `api_key` | str? | None | Gemini API 키 (client 없을 때 사용) |

---

## 비용 예상

| 항목 | 수량 | 단가 | 소계 |
|------|------|------|------|
| 모델컷 AI 생성 | 5장 | 190원 (2K) | 950원 |
| 검수 VLM 호출 | 5회 | ~50원 | 250원 |
| 재생성 (평균) | 2장 | 190원 | 380원 |
| **합계** | | | **~1,580원** |

(배너는 Figma 레이아웃만 생성하므로 추가 API 비용 없음)

---

## 주의사항

1. **Figma 연결 필수**: Phase 2/3의 액션을 실행하려면 Figma MCP 연결(join_channel)이 필요하다.
2. **이미지 서빙**: Figma에서 이미지를 로드하려면 `image_base_url`에 이미지 서버가 필요하다. 로컬 개발 시 `http://localhost:8000`으로 FastAPI 서버를 띄워 사용한다.
3. **API 키**: AI 이미지 생성(Phase 1)에는 Gemini API 키가 필요하다. `.env`의 `GEMINI_API_KEY` 사용.
4. **Phase 1 건너뛰기**: 기존 모델 이미지가 있으면 `generate_model_shots=False`로 설정하고 `model_image_paths`에 경로를 지정한다.

---

**버전**: 1.0.0
**작성일**: 2026-03-04
