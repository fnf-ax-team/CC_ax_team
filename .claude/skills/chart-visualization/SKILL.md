# Chart Visualization (`chart_utils.py`)

matplotlib 기반 차트 생성 유틸리티. 한글 폰트 자동 설정, OS별 대응.

## 사용 시점
- **PPTX에 삽입할 단순 차트** (bar, line, pie, 도넛, 가로막대, comparison) → 이 스킬 사용
- **HTML 대시보드의 단순 차트** → Chart.js (`html_utils.py` → `html-report` 스킬) 사용
- **복잡한 차트** (treemap, sankey, funnel, heatmap, multi_axis) → Plotly (`plotly_utils.py` → `chart-visualization-plotly` 스킬) 사용

## 임포트

```python
from src.util.chart_utils import (
    create_bar_chart, create_horizontal_bar,
    create_pie_chart, create_line_chart, create_comparison_bars,
    chart_to_image, apply_dark_theme, apply_light_theme,
    add_bar_labels, setup_korean_font, apply_comma_format,
    CHART_COLORS_CY, CHART_COLORS_PY,
)
```

## 색상 팔레트

| 상수 | 용도 |
|------|------|
| `CHART_COLORS_CY` | 당해 시리즈 (진한 색) |
| `CHART_COLORS_PY` | 전년 시리즈 (연한 색) |
| `DARK_CHART_COLORS` | 다크 테마용 |

기준 디자인: `FNF_AI_Native_OptA_WhiteMinimal.pptx`

## 차트 생성

### 묶은 세로 막대

```python
fig = create_bar_chart(
    categories=["1월", "2월", "3월"],
    series_data={"당해": [100, 120, 130], "전년": [90, 110, 100]},
    title="월별 매출",
    ylabel="억원",
)
```

### 시계열 라인

```python
fig = create_line_chart(
    categories=["01/04", "01/11", "01/18", "01/25"],
    series_data={"당해": [100, 120, 130, 150], "전년": [90, 110, 100, 120]},
    title="주차별 매출 추이",
    ylabel="억원",
    show_labels=True,
)
```

### 당해 vs 전년 비교 (단축)

```python
fig = create_comparison_bars(
    categories=["1월", "2월", "3월"],
    cur_vals=[100, 120, 130],
    prev_vals=[90, 110, 100],
    title="매출 비교",
    labels=("당해", "전년"),     # 시리즈명 변경 가능 (기본: "당해", "전년")
    figsize=(8, 5),              # 차트 크기
    label_fmt="{:.1f}",          # 데이터 라벨 포맷
)
```

### 가로 막대

```python
fig = create_horizontal_bar(
    categories=["A", "B", "C"],
    values=[300, 200, 100],
    title="브랜드별 매출",
)
```

### 파이/도넛

```python
fig = create_pie_chart(
    labels=["MLB", "디스커버리", "MLB KIDS"],
    values=[50, 30, 20],
    title="브랜드 구성비",
    donut=True,           # 도넛형
    text_color="#333",    # 라벨/퍼센트 텍스트 색상 (다크 배경 시 "white" 사용)
    label_fontsize=11,    # 카테고리 라벨 폰트 크기
    pct_fontsize=10,      # 퍼센트 텍스트 폰트 크기
)
```

## 이미지 변환

```python
# Figure → BytesIO (PNG)
buf = chart_to_image(fig, dpi=150)

# PowerPoint에 삽입할 때
from src.util.pptx_utils import add_chart_image
add_chart_image(slide, fig, left, top, width, height)
```

## 테마 적용

```python
fig, ax = plt.subplots()
# ... 차트 생성 ...
apply_dark_theme(fig, ax)   # 다크 배경 (#1E293B)
apply_light_theme(fig, ax)  # 라이트 배경 (white)
```

## 축 숫자 천 단위 콤마

- `create_bar_chart`, `create_line_chart`는 Y축에 자동 적용
- `create_horizontal_bar`는 X축(값 축)에 자동 적용
- 직접 사용 시:

```python
fig, ax = plt.subplots()
# ... 차트 생성 ...
apply_comma_format(ax, axis="y")     # Y축만 (기본)
apply_comma_format(ax, axis="x")     # X축만
apply_comma_format(ax, axis="both")  # 양축 모두
```

## 데이터 라벨

```python
bars = ax.bar(x, values)
add_bar_labels(ax, bars, fmt="{:,.0f}", fontsize=8)
```

## 시계열 차트 라벨 규칙
- 주차별 차트의 X축은 **당해 기준 END_DT(일요일 마감일)**를 사용할 것
  - 형식: `MM/DD` (예: `01/04`, `02/08`)
  - 전년 데이터도 당해 주차 순서에 맞춰 동일 X축 라벨 사용 (전년 날짜 아님)
- 라벨이 겹칠 경우 `rotation=45` 또는 간격 조정으로 가독성 확보

## 주의사항

- `setup_korean_font()` — 각 차트 생성 함수가 내부에서 자동 호출, 직접 호출 불필요
- OS별 폰트 자동 감지 (Windows: Malgun Gothic, macOS: AppleSDGothicNeo, Linux: NanumGothic)
- `chart_to_image()` 호출 시 `plt.close(fig)` 자동 실행 → Figure 재사용 불가
