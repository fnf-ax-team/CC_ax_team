# PowerPoint Report (`pptx_utils.py`)

python-pptx 기반 프레젠테이션 생성 유틸리티. White Minimal 테마.

## 임포트

```python
from pptx.util import Inches, Pt
from src.util.pptx_utils import (
    create_presentation, set_slide_bg,
    add_textbox, add_rounded_rect,
    add_kpi_card, create_styled_table,
    add_title_bar, add_section_divider,
    add_bullet_box, add_cover_slide, add_chart_image,
    THEME_DARK, THEME_LIGHT, FONT_SIZES,
    COLOR_POSITIVE, COLOR_NEGATIVE, COLOR_WARN,
    COLOR_PURPLE, COLOR_TEAL,
)
```

## 기본 구조

```python
# 16:9 프레젠테이션 생성
prs = create_presentation()  # 13.333 x 7.5 inches

# 표지 슬라이드
add_cover_slide(prs, "리포트 제목", "부제목", "2025.01.15", theme="light")

# 빈 슬라이드 추가
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, THEME_LIGHT["bg"])

# 저장
prs.save("src/output/report.pptx")
```

## 폰트 크기 기준 (`FONT_SIZES`)

모든 함수는 `FONT_SIZES` 딕셔너리를 기본값으로 사용하며, 파라미터로 오버라이드 가능.

| 키 | 기본값(pt) | 적용 위치 |
|-----|-----------|----------|
| `cover_title` | 38 | 표지 제목 |
| `cover_subtitle` | 18 | 표지 부제목 |
| `cover_date` | 14 | 표지 날짜 |
| `title_bar` | 20 | 타이틀 바 제목 |
| `title_bar_sub` | 12 | 타이틀 바 부제목 |
| `section_divider` | 13 | 섹션 구분선 제목 |
| `kpi_label` | 12 | KPI 카드 라벨 |
| `kpi_value` | 24 | KPI 카드 값 |
| `kpi_sub` | 11 | KPI 카드 보조 텍스트 |
| `table_cell` | 12 | 테이블 셀 |
| `bullet_title` | 13 | 인사이트 박스 제목 |
| `bullet_item` | 11 | 인사이트 박스 항목 |

## 테마 색상

### 공통 테마 키

| 키 | Dark | Light | 용도 |
|-----|------|-------|------|
| `bg` | #1E293B | #FAFAFC | 배경 |
| `primary` | #006AE6 | #006AE6 | 메인 강조 |
| `accent` | #FFA000 | #FFA000 | 보조 강조 |
| `card` | #2A364A | #F0F2F5 | 카드 배경 (기본) |
| `text` | #FFFFFF | #2D2D2D | 텍스트 |
| `text_sub` | #8A8A9A | #8A8A9A | 보조 텍스트 |
| `table_header` | #006AE6 | #006AE6 | 테이블 헤더 배경 |
| `table_row1` | #232E3F | #FFFFFF | 테이블 홀수행 |
| `table_row2` | #2A364A | #F0F2F5 | 테이블 짝수행 |
| `border` | #3A465A | #C0C4CC | 테두리 |

### Light 전용 키

| 키 | 값 | 용도 |
|-----|------|------|
| `card_blue` | #E3F0FF | KPI 카드 파란 배경 |
| `card_green` | #E3F8F0 | KPI 카드 초록 배경 |
| `card_orange` | #FFF3E0 | KPI 카드 주황 배경 |
| `divider` | #C0C4CC | 구분선 |
| `divider_light` | #E8EAEE | 얇은 구분선 |

### 시그널 색상 상수

| 상수 | 색상 | 용도 |
|------|------|------|
| `COLOR_POSITIVE` | #00B894 (초록) | 긍정 시그널 |
| `COLOR_NEGATIVE` | #FF6352 (빨강) | 부정 시그널 |
| `COLOR_WARN` | #FFA000 (주황) | 경고 |
| `COLOR_PURPLE` | #6C5CE7 (보라) | 보조 강조 |
| `COLOR_TEAL` | #009688 (틸) | 보조 강조 |

## 타이틀 바

```python
# 기본 (다크 테마 primary 배경)
add_title_bar(slide, "슬라이드 제목")

# theme 파라미터로 간편 지정
add_title_bar(slide, "슬라이드 제목", subtitle="부제목 텍스트", theme="light")

# 직접 색상 지정 (theme보다 우선)
add_title_bar(
    slide, "슬라이드 제목",
    subtitle="부제목",
    bg_color=THEME_LIGHT["primary"],
    text_color=RGBColor(0xFF, 0xFF, 0xFF),
    bar_height=0.7,
    title_fontsize=22,       # 오버라이드 (기본: FONT_SIZES["title_bar"])
    subtitle_fontsize=14,    # 오버라이드 (기본: FONT_SIZES["title_bar_sub"])
)
```

## 섹션 구분선

```python
add_section_divider(
    slide,
    left=Inches(0.5), top=Inches(2.0), width=Inches(12),
    title="섹션 제목",
    color=THEME_LIGHT["primary"],
    title_fontsize=14,       # 오버라이드 (기본: FONT_SIZES["section_divider"])
)
```

## KPI 카드

```python
add_kpi_card(
    slide,
    left=Inches(0.5), top=Inches(1.0),
    width=Inches(2.8), height=Inches(1.2),
    label="총매출",
    value="1,523억",
    sub_text="+12.3% vs 전년",
    accent_color=COLOR_POSITIVE,
    card_bg=THEME_LIGHT["card_blue"],     # card_blue / card_green / card_orange / card
    text_color=THEME_LIGHT["text"],
    label_color=THEME_LIGHT["text_sub"],  # 라벨 색상 (기본: #8A8A9A)
    label_fontsize=14,                    # 오버라이드 (기본: FONT_SIZES["kpi_label"])
    value_fontsize=28,                    # 오버라이드 (기본: FONT_SIZES["kpi_value"])
    sub_fontsize=12,                      # 오버라이드 (기본: FONT_SIZES["kpi_sub"])
)
```

## 테이블

```python
data = [
    ["브랜드", "매출", "전년비"],
    ["MLB", "800억", "+15%"],
    ["디스커버리", "500억", "+8%"],
]
create_styled_table(
    slide,
    left=Inches(0.5), top=Inches(2.0), width=Inches(12),
    data=data,
    col_widths=[Inches(3), Inches(4), Inches(5)],  # 개별 컬럼 너비 (None이면 균등 분배)
    theme="light",
    cell_fontsize=14,                                # 오버라이드 (기본: FONT_SIZES["table_cell"])
)
```

## 인사이트 박스

```python
# Positive (초록 액센트) + Watch (빨강 액센트) 가로 배치
add_bullet_box(
    slide,
    left=Inches(0.5), top=Inches(5.8),
    width=Inches(6.0), height=Inches(1.4),
    items=["MLB 매출 전년비 +15% 성장", "디스커버리 신규 라인 호조"],
    title="Positive Signal",
    positive=True,
    card_bg=THEME_LIGHT["card_green"],
    title_fontsize=15,                   # 오버라이드 (기본: FONT_SIZES["bullet_title"])
    item_fontsize=13,                    # 오버라이드 (기본: FONT_SIZES["bullet_item"])
)
add_bullet_box(
    slide,
    left=Inches(6.8), top=Inches(5.8),
    width=Inches(6.0), height=Inches(1.4),
    items=["재고 회전율 하락 추세"],
    title="Watch Point",
    positive=False,
)
```

## 차트 이미지 삽입

```python
from src.util.chart_utils import create_bar_chart

fig = create_bar_chart(...)
add_chart_image(slide, fig, Inches(1), Inches(2), Inches(6), Inches(4))
# Figure 자동 close → BytesIO 변환 → 슬라이드 삽입
```

## 레이아웃 가이드

- 슬라이드: 13.333" x 7.5" (16:9)
- 좌우 마진: 0.5"
- 타이틀 바: 높이 0.7"
- KPI 카드: 높이 1.2", 4개 가로 배치 시 너비 ~2.95", 간격 0.2"
- 테이블: 전체 너비 12.3" (좌우 마진 제외)
- 인사이트 박스 2개 가로 배치: 각 너비 6.0", 좌측 left=0.5" / 우측 left=6.8"
