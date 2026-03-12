# Data Processing (`data_stats_utils.py`)

KG API 데이터 로드, Polars/DuckDB 기반 통계 분석 유틸리티.
Python 실행 규칙은 `CLAUDE.md` "Bash로 파일 실행 규칙"을 따를 것.

## 임포트

```python
from src.util.data_stats_utils import (
    load_json_as_df, load_csv_as_df, basic_info, describe_stats,
    category_distribution, crosstab,
    group_agg_duckdb, custom_query_duckdb,
    run_full_stats,
)
```

## 함수 목록

| 함수 | 설명 |
|------|------|
| `load_json_as_df(file_path)` | JSON 파일 → Polars DataFrame 로드 |
| `load_csv_as_df(file_path, **kwargs)` | CSV 파일 → Polars DataFrame 로드 |
| `basic_info(df)` | 행/열 수, 컬럼 타입, NULL 수 반환 |
| `describe_stats(df)` | Polars `describe()` 기술통계 반환 |
| `category_distribution(df, column)` | 범주형 컬럼 빈도분포 (count, pct) |
| `crosstab(df, row_col, col_col)` | 두 범주형 컬럼 교차표 (피벗) |
| `group_agg_duckdb(df, group_cols, agg_expr)` | DuckDB SQL 그룹별 집계 |
| `custom_query_duckdb(df, sql, table_name)` | DuckDB 임의 SQL 실행 |
| `run_full_stats(file_path)` | 전체 기본 통계 일괄 실행 |

## 사용 예시

```python
# JSON → DataFrame
df = load_json_as_df("src/download/result.json")

# CSV → DataFrame
df = load_csv_as_df("src/download/result.csv")

# 기본 정보
info = basic_info(df)  # {"shape": ..., "columns": ..., "null_counts": ...}

# 기술통계
stats = describe_stats(df)

# 범주형 빈도분포
dist = category_distribution(df, "BRAND_CD")

# 교차표
ct = crosstab(df, "BRAND_CD", "PRDT_KIND_NM")

# DuckDB 그룹 집계
agg = group_agg_duckdb(df, ["BRAND_CD"], "SUM(SALE_AMT) AS total_amt")

# DuckDB 임의 SQL
result = custom_query_duckdb(df, "SELECT * FROM tbl WHERE SALE_AMT > 1000000")

# 전체 기본 통계 일괄
full = run_full_stats("src/download/result.json")
# → {"info": ..., "describe": ..., "distributions": {...}}
```

## 교차검증 예시

KG API 데이터를 context에서 수작업 합산하면 오류가 발생할 수 있다.
반드시 코드 기반으로 검증할 것.

### 검증 프로세스

```
1. 데이터 사이즈별 처리 규칙은 dcsai-tools.md를 따를 것
2. Polars DataFrame 변환
   → 파일: load_json_as_df()
   → context: pl.DataFrame(api_response_data)
3. group_agg_duckdb()로 그룹별 합계 산출
4. custom_query_duckdb()로 CY vs LY JOIN 비교
5. 부분합 == 전체합 일치 assert 검증
```

### 예시 1: API 응답을 파일 저장 후 검증

```python
from src.util.data_stats_utils import load_json_as_df, group_agg_duckdb, custom_query_duckdb

# 1) dcs-ai-cli로 저장한 파일 로드 (파일명: {name}_{timestamp}.json 패턴)
import tempfile, os, glob
tmpdir = tempfile.gettempdir()
cy_file = sorted(glob.glob(os.path.join(tmpdir, "dcs-ai-cli", "cy_weekly_*.json")))[-1]
ly_file = sorted(glob.glob(os.path.join(tmpdir, "dcs-ai-cli", "ly_weekly_*.json")))[-1]
cy_df = load_json_as_df(cy_file)
ly_df = load_json_as_df(ly_file)

# 2) 브랜드별 합계
cy_sum = group_agg_duckdb(cy_df, ["BRD_CD", "BRD_NM"],
    "SUM(SALE_AMT) AS cy_amt, SUM(SALE_QTY) AS cy_qty")
ly_sum = group_agg_duckdb(ly_df, ["BRD_CD", "BRD_NM"],
    "SUM(SALE_AMT) AS ly_amt, SUM(SALE_QTY) AS ly_qty")

# 3) 부분합 == 전체합 일치 검증
cy_total = cy_df["SALE_AMT"].sum()
cy_brand_total = cy_sum["cy_amt"].sum()
assert cy_total == cy_brand_total, f"합계 불일치! {cy_total} != {cy_brand_total}"
print(f"합계 검증 통과: {cy_total:,}원")
```

### 예시 2: CY vs LY 전년비 자동 비교

```python
import duckdb

conn = duckdb.connect(":memory:")
conn.register("cy", cy_sum.to_arrow())
conn.register("ly", ly_sum.to_arrow())
compare = conn.execute("""
    SELECT c.BRD_CD, c.BRD_NM,
           c.cy_amt,
           l.ly_amt,
           ROUND((c.cy_amt::FLOAT / l.ly_amt - 1) * 100, 1) AS yoy_pct,
           c.cy_amt - l.ly_amt AS diff
    FROM cy c
    LEFT JOIN ly l ON c.BRD_CD = l.BRD_CD
    ORDER BY c.cy_amt DESC
""").pl()
conn.close()
print(compare)
```

### 예시 3: context 데이터를 직접 DataFrame으로 변환하여 검증

API 응답이 context에 있고 파일 저장이 불필요한 경우 (dcsai-tools.md 토큰 기준 참조):

```python
import polars as pl
from src.util.data_stats_utils import custom_query_duckdb

# API 응답 데이터를 직접 DataFrame으로
cy_df = pl.DataFrame([
    {"BRD_CD": "M", "ITEM_GROUP": "볼캡/햇/비니", "SALE_AMT": 3320867021, "SALE_QTY": 87647},
    {"BRD_CD": "X", "ITEM_GROUP": "가방",         "SALE_AMT": 2126345062, "SALE_QTY": 14383},
    # ... API 응답 전체
])

# DuckDB SQL로 한 번에 검증
validation = custom_query_duckdb(cy_df, """
    SELECT BRD_CD,
           SUM(SALE_AMT) AS total_amt,
           SUM(SALE_QTY) AS total_qty,
           COUNT(*) AS category_count
    FROM tbl
    GROUP BY BRD_CD
    ORDER BY total_amt DESC
""")
print(validation)
```

### 예시 4: 카테고리별 합계와 전체 합계 일치 검증

```python
from src.util.data_stats_utils import group_agg_duckdb

# 카테고리별 합계
cat_sum = group_agg_duckdb(cy_df, ["BRD_CD", "ITEM_GROUP"],
    "SUM(SALE_AMT) AS cat_amt")

# 브랜드별 합계
brd_sum = group_agg_duckdb(cy_df, ["BRD_CD"],
    "SUM(SALE_AMT) AS brd_amt")

# 카테고리 합계를 브랜드로 재집계하여 비교
cat_to_brd = group_agg_duckdb(cat_sum, ["BRD_CD"],
    "SUM(cat_amt) AS cat_total")

# 두 결과 비교
import duckdb
conn = duckdb.connect(":memory:")
conn.register("a", brd_sum.to_arrow())
conn.register("b", cat_to_brd.to_arrow())
check = conn.execute("""
    SELECT a.BRD_CD,
           a.brd_amt,
           b.cat_total,
           a.brd_amt = b.cat_total AS is_match
    FROM a JOIN b ON a.BRD_CD = b.BRD_CD
""").pl()
conn.close()
print(check)
assert check["is_match"].all(), "카테고리 합계 != 브랜드 합계"
```

## 주의사항

- 반품(RET) 컬럼은 이미 음수값. 합계 = NML + RET (빼면 안 됨)
- KG API 데이터를 context에서 수작업 합산하지 말 것. 반드시 코드 기반 검증 수행
- 당해/전년 비교 시 두 데이터를 병렬 조회 후 JOIN으로 비교할 것
