# Plotly Chart Visualization (`plotly_utils.py`)

Plotly 기반 고급 차트 생성 유틸리티. treemap, sankey, funnel, heatmap, 복합 축 등 복잡한 시각화 전용.

## 사용 시점
- **복잡한 차트** (treemap, sankey, funnel, heatmap, multi_axis) → 이 스킬 사용 (PPTX/HTML 모두)
- **PPTX에 삽입할 단순 차트** (bar, line, pie, 도넛 등) → matplotlib (`chart_utils.py` → `chart-visualization` 스킬) 사용
- **HTML 대시보드의 단순 차트** (bar, line, pie, 도넛 등) → Chart.js (`html_utils.py` → `html-report` 스킬) 사용

## 임포트

```python
from src.util.plotly_utils import (
    create_treemap, create_sankey, create_funnel,
    create_heatmap, create_multi_axis,
    chart_to_html_plotly, chart_to_image_plotly, apply_theme,
    CHART_COLORS_CY, CHART_COLORS_PY,
)
```

## 색상 팔레트

`chart_utils.py`의 색상 상수를 재사용:

| 상수 | 용도 |
|------|------|
| `CHART_COLORS_CY` | 당해 시리즈 (진한 색) |
| `CHART_COLORS_PY` | 전년 시리즈 (연한 색) |

기준 디자인: `FNF_AI_Native_OptA_WhiteMinimal.pptx`

## 차트 생성

### Treemap (계층 구조)

```python
fig = create_treemap(
    labels=["전체", "아우터", "신발", "다운", "플리스", "운동화", "슬리퍼"],
    parents=["", "전체", "전체", "아우터", "아우터", "신발", "신발"],
    values=[0, 0, 0, 5000, 3000, 4000, 2000],  # 중간 노드는 0
    title="카테고리별 매출 구성",
)
```

### Sankey (흐름도)

```python
fig = create_sankey(
    node_labels=["자사몰", "제휴몰", "오프라인", "아우터", "신발", "잡화"],
    source=[0, 0, 1, 1, 2, 2],   # 소스 노드 인덱스
    target=[3, 4, 4, 5, 3, 5],   # 타겟 노드 인덱스
    value=[500, 300, 400, 200, 600, 100],
    title="채널 -> 카테고리 매출 흐름",
)
```

### Funnel (퍼널)

```python
fig = create_funnel(
    stages=["방문", "상품조회", "장바구니", "결제시도", "결제완료"],
    values=[10000, 5000, 2000, 1200, 800],
    title="구매 전환 퍼널",
)
```

### Heatmap (히트맵)

```python
fig = create_heatmap(
    z=[[10, 20, 30], [40, 50, 60], [70, 80, 90]],
    x_labels=["월", "화", "수"],
    y_labels=["오전", "오후", "야간"],
    title="시간대별 매출 분포",
    colorscale="Blues",       # 색상 스케일
    show_text=True,           # 셀 내 값 표시
    text_fmt=".0f",           # 텍스트 포맷
)
```

### 복합 축 (Multi-Axis)

```python
fig = create_multi_axis(
    categories=["1월", "2월", "3월"],
    series_left={"매출": [100, 120, 130]},
    series_right={"성장률": [5.2, 8.1, 12.3]},
    title="매출 & 성장률",
    ylabel_left="매출(억원)",
    ylabel_right="성장률(%)",
    left_type="bar",          # 좌측: "bar" 또는 "scatter"
    right_type="scatter",     # 우측: "bar" 또는 "scatter"
)
```

## HTML 변환

```python
# Plotly Figure → HTML div 문자열
plotly_div = chart_to_html_plotly(fig, include_plotlyjs="cdn")

# html_utils의 save_html과 조합
from src.util.html_utils import save_html
body = f"""
<div class="section">{plotly_div}</div>
"""
save_html("src/output/report.html", "리포트", body)
```

## 이미지 변환

```python
# Figure → BytesIO (PNG)
buf = chart_to_image_plotly(fig, width=1200, height=700, scale=2)

# PowerPoint에 삽입할 때
from pptx.util import Inches
slide.shapes.add_picture(buf, Inches(1), Inches(2), Inches(6), Inches(4))
```

## 테마 적용

```python
fig = create_treemap(...)
apply_theme(fig, theme="dark")   # 다크 배경 (#1E293B)
apply_theme(fig, theme="light")  # 라이트 배경 (white, 기본)
```

## 주의사항

- 단순 차트(bar, line, pie 등): PPTX → matplotlib(`chart_utils.py`), HTML → Chart.js(`html_utils.py`). Plotly는 복잡한 차트 전용
- `chart_to_image_plotly()`는 `kaleido` 패키지 필요 (설치 완료)
- OS별 폰트 자동 감지 (Windows: Malgun Gothic, macOS: AppleSDGothicNeo, Linux: NanumGothic)
- `chart_to_html_plotly()`의 `include_plotlyjs="cdn"`은 온라인 환경 필요
- PPTX 삽입 시 `Inches` 단위 사용 (슬라이드: 13.333" x 7.5")
