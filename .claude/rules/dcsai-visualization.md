
<!-- DCS-AI-PLUGIN-CONFIG -->
---
DCS AI 시각화 자동 선택 규칙
---

## 개요
사용자가 시각화를 요청하면서 차트 유형을 명시하지 않은 경우, 분석 의도에 따라 아래 매핑 테이블을 참조하여 자동으로 적절한 차트를 선택한다.

## 차트 선택 우선순위
1. **사용자 명시 지정** — 사용자가 차트 유형을 직접 지정하면 매핑 무시하고 해당 유형 사용
2. **의도별 매핑 테이블** — 아래 테이블에서 분석 의도에 해당하는 기본 차트 선택
3. **데이터 특성 판단** — 매핑에 없는 의도는 데이터 형태(시계열/비교/구성비/흐름)로 판단

## 출력 형태별 라이브러리 선택

| 출력 형태 | 단순 차트 (bar/line/pie/도넛/가로막대/comparison) | 복잡 차트 (treemap/sankey/funnel/heatmap/multi_axis) |
|----------|------------------------------------------------|-----------------------------------------------------|
| **PPTX** | `chart-visualization` 스킬 (matplotlib) | `chart-visualization-plotly` 스킬 (Plotly) |
| **HTML** | `html-report` 스킬 (Chart.js) | `chart-visualization-plotly` 스킬 → `chart_to_html_plotly()` |
| **이미지/불명** | `chart-visualization` 스킬 (matplotlib) | `chart-visualization-plotly` 스킬 (Plotly) |

## 의도별 기본 차트 매핑 테이블

### 채널 매출 분석

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| 한국 채널 매출 분석 일간/기간 | bar (당해 vs 전년) | chart_utils | X:채널, Y:매출액 | — |
| 한국 채널 매출 분석 주간/주차별 | line (당해 vs 전년) | chart_utils | X:주차, Y:매출액 | — |
| 한국 채널 매출 분석 월간/년간 | bar (당해 vs 전년) | chart_utils | X:월, Y:매출액 | — |
| 한국 채널 매출 종합분석 | multi_axis | plotly_utils | 좌:매출액(bar), 우:목표비/전년비(line) | — |
| 한국 채널 매출 월간 목표 | multi_axis | plotly_utils | 좌:실적(bar), 우:달성률(line) | — |
| 한국 채널 매출 + 구성비/비중 | treemap | plotly_utils | 채널유형>채널별 매출 비중 | "구성비", "비중", "점유율" |
| 한국 채널 매출 + 흐름/분포 | sankey | plotly_utils | 채널유형→카테고리 매출 흐름 | "흐름", "분포", "이동" |
| 유통사 자사-경쟁사 대비율 | multi_axis | plotly_utils | 좌:매출액(bar), 우:대비율/순위(line) | — |

### 상품 매출 분석

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| 한국 상품 매출 분석 일간/기간 | bar (당해 vs 전년) | chart_utils | X:카테고리, Y:매출액 | — |
| 한국 상품 매출 분석 주간/주차별 | line (당해 vs 전년) | chart_utils | X:주차, Y:매출액 | — |
| 한국 상품 매출 분석 월간/월별 | bar (당해 vs 전년) | chart_utils | X:월, Y:매출액 | — |
| 한국 상품 매출 + 계층/구성 | treemap | plotly_utils | 대분류>중분류>아이템 매출 비중 | "계층", "구성", "구성비" |
| 한국 상품 매출 시즌 의류 | multi_axis | plotly_utils | 좌:판매금액(bar), 우:판매율(line) | — |
| 용품/신발 기간판매분석 | multi_axis | plotly_utils | 좌:재고금액(bar), 우:재고주수(line) | — |
| 스타일 랭킹 | horizontal_bar | chart_utils | X:판매액, Y:스타일명 (TOP N) | — |
| 최근 판매 급상승 상품 | multi_axis | plotly_utils | 좌:판매수량(bar), 우:증가율(line) | — |

### SCM / 발주 / 입고

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| SCM 분석 | sankey | plotly_utils | 생산국→운송방법→도착지 흐름 | — |
| 시즌 발주/입고 분석 | funnel | plotly_utils | 발주→입고→판매 단계별 전환 | — |
| 시즌 발주/입고 + 흐름 | sankey | plotly_utils | 협력사→브랜드→카테고리 흐름 | "흐름", "공급망" |

### CS / VOC / 클레임

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| 소비자클레임/CS 분석 | heatmap | plotly_utils | X:기간, Y:불량유형, Z:건수 | — |
| 기간 소비자클레임 접수/조치 건 | funnel | plotly_utils | 접수→조치중→조치완료 전환 | — |
| 기간 소비자클레임 + 협력사 비교 | heatmap | plotly_utils | X:협력사, Y:불량유형, Z:건수 | "협력사", "업체" |
| 매장 VOC 분석 | heatmap | plotly_utils | X:VOC유형, Y:매장, Z:빈도 | — |

### 마케팅 / 소셜

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| 인플루언서 마케팅 성과 분석 | multi_axis | plotly_utils | 좌:조회수(bar), 우:인게이지먼트율(line) | — |
| 인플루언서 마케팅 컨텐츠 분석 | funnel | plotly_utils | 노출→조회→좋아요→댓글 전환 | — |
| 인플루언서 캠페인-상품 분석 | sankey | plotly_utils | 캠페인→카테고리→상품 흐름 | — |
| 네이버 검색량 조회 | line | chart_utils | X:기간, Y:검색량 | — |
| 네이버 검색량 + 비교 | heatmap | plotly_utils | X:기간, Y:키워드, Z:검색량 | "비교", "키워드별" |

### 기타

| 의도 | 기본 차트 | 라이브러리 | 축/시리즈 구성 | 트리거 키워드 |
|------|----------|-----------|---------------|-------------|
| 날씨 조회 + 시각화 | heatmap | plotly_utils | X:일자, Y:지역, Z:기온/강수 | "분포", "비교" |
| 상품 카테고리 분류체계 | treemap | plotly_utils | 대분류>중분류>아이템 계층 구조 | — |

## 복수 차트 생성 규칙
- 데이터가 충분하고 분석 관점이 2개 이상인 경우, **기본 차트 + 보조 차트**를 함께 제공
- 예시: 채널 매출 분석 → bar(당해 vs 전년) + treemap(구성비) 또는 sankey(흐름)
- 보조 차트는 사용자에게 "추가 시각화도 함께 제공합니다"로 안내

## 매핑에 없는 의도의 차트 선택 기준

| 데이터 특성 | 추천 차트 | 라이브러리 |
|------------|----------|-----------|
| 시계열 추이 (기간별 변화) | line | chart_utils |
| 항목 간 크기 비교 | bar / horizontal_bar | chart_utils |
| 구성비/점유율 | pie/donut 또는 treemap | chart_utils / plotly_utils |
| 계층 구조 (2단계 이상) | treemap | plotly_utils |
| 흐름/이동 (A→B) | sankey | plotly_utils |
| 단계별 전환/감소 | funnel | plotly_utils |
| 2차원 매트릭스 분포 | heatmap | plotly_utils |
| 두 가지 단위 동시 표현 | multi_axis | plotly_utils |
| TOP N 랭킹 | horizontal_bar | chart_utils |
| 당해 vs 전년 비교 | comparison_bars | chart_utils |
<!-- /DCS-AI-PLUGIN-CONFIG -->
