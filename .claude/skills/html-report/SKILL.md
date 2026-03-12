# HTML Report (`html_utils.py`)

White Minimal 테마 기반 HTML 리포트 생성 유틸리티. Chart.js 연동.

## 차트 라이브러리 선택 기준
- **HTML 대시보드 + 단순 차트** (bar, line, pie, 도넛) → 이 스킬의 Chart.js 사용
- **HTML 대시보드 + 복잡한 차트** (treemap, sankey, funnel, heatmap, multi_axis) → Plotly (`plotly_utils.py` → `chart-visualization-plotly` 스킬)의 `chart_to_html_plotly()`로 div 생성 후 `save_html()`에 삽입

## 임포트

```python
from src.util.html_utils import (
    save_html, get_white_minimal_css,
    render_kpi_card, render_table,
    render_bullet_box, render_section_header,
    render_chart_placeholder, render_product_ranking_grid,
    get_chartjs_config, HTML_COLORS, CHART_COLORS,
)
```

## 기본 구조

```python
body = f"""
<div class="hero">
    <div class="brand">F&F · DCS AI</div>
    <h1>리포트 제목</h1>
    <div class="subtitle">2025.01.15 기준</div>
</div>

<div class="section">
    {render_section_header("매출 현황", "전년 동기 대비")}
    <div class="kpi-row">
        {render_kpi_card("총매출", "1,523억", "+12.3%")}
        {render_kpi_card("판매수량", "85만", "+8.5%", accent_color=HTML_COLORS["positive"])}
    </div>
</div>
"""

save_html("src/output/report.html", "매출 분석", body)
```

## KPI 카드

```python
render_kpi_card(
    label="총매출",
    value="1,523억",
    sub_text="+12.3% vs 전년",
    accent_color=HTML_COLORS["primary"],   # 상단 바 색상
    bg_color=HTML_COLORS["card_blue"],     # 카드 배경
    sub_color=HTML_COLORS["positive"],     # sub_text 색상
)
```

배경 프리셋: `card_blue`, `card_green`, `card_orange`, `card`(회색)

## 테이블

```python
data = [
    ["브랜드", "매출", "전년비"],
    ["MLB", "800억", "+15%"],
    ["디스커버리", "500억", "+8%"],
]
render_table(data)  # data[0]이 헤더
```

## 인사이트 박스

```python
# Positive (초록)
render_bullet_box(
    items=["MLB 매출 전년비 +15% 성장"],
    title="Positive Signal",
    positive=True,
)

# Watch (빨강)
render_bullet_box(
    items=["재고 회전율 하락"],
    title="Watch Point",
    positive=False,
)
```

## Chart.js 연동

```python
# 1. canvas placeholder 배치
chart_html = render_chart_placeholder("salesChart", height="350px")

# 2. 차트 설정 생성
config = get_chartjs_config("bar", {
    "labels": ["1월", "2월", "3월"],
    "datasets": [{
        "label": "매출",
        "data": [100, 120, 130],
        "backgroundColor": CHART_COLORS[0],
    }],
})

# 3. JavaScript 초기화 코드
charts_js = f"new Chart(document.getElementById('salesChart'), {config});"

# 4. 저장
save_html("src/output/report.html", "매출 분석", body + chart_html, charts_js)
```

## 상품 랭킹 그리드

```python
products = [
    {"PRDT_IMG_URL": "...", "PRDT_NM": "양키스 모노그램", "PRDT_CD": "3ACPM...",
     "ITEM_GROUP": "모자", "TAG_PRICE": 49000,
     "AC_SALE_AMT": 5_000_000_000, "AC_SALE_QTY": 50000, "SALE_RT": 0.85},
]

grid_html = render_product_ranking_grid(
    products,
    metrics_config=[
        ("AC_SALE_AMT", "누적판매액", "amt"),
        ("AC_SALE_QTY", "판매Qty", "qty"),
        ("SALE_RT", "판매율", "pct"),
    ],
)
```

## 색상 상수

`HTML_COLORS` — pptx_utils `THEME_LIGHT`와 동기화:

| 키 | 값 | 용도 |
|----|-----|------|
| `primary` | #006AE6 | 메인 강조 |
| `accent` | #FFA000 | 보조 강조 |
| `positive` | #00B894 | 긍정 시그널 |
| `negative` | #FF6352 | 부정 시그널 |
| `purple` | #6C5CE7 | 보조 색상 |
| `teal` | #009688 | 보조 색상 |

`CHART_COLORS` — Chart.js 시리즈용 8색 팔레트

## 레이아웃 CSS 클래스

| 클래스 | 용도 |
|--------|------|
| `.report-container` | 최대 1200px, 좌측 파란 바 |
| `.hero` | 타이틀 영역 + key-metrics 카드 |
| `.kpi-row` | KPI 카드 가로 배치 (flex) |
| `.flex-row` | 차트 + 테이블 가로 배치 |
| `.chart-col` / `.table-col` | flex 3:2 비율 |
| `.section` | 섹션 블록 (margin-bottom 40px) |
| `.product-grid` | 상품 카드 그리드 (auto-fill) |

반응형: 768px 이하에서 세로 배치 전환
