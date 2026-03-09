# 전체 캐시 삭제 + 재캐싱

모든 데이터 캐시를 삭제하고 새로 캐싱합니다.

## 실행 순서

### 1. 전체 캐시 삭제
```bash
curl -X DELETE http://localhost:3200/api/cache/data
```

### 2. Overview 페이지 재캐싱
```bash
# KPI
curl -s http://localhost:3200/api/kpi > /dev/null

# Categories
curl -s http://localhost:3200/api/categories > /dev/null

# Weekly Sales
curl -s http://localhost:3200/api/weekly-sales > /dev/null

# Forecast
curl -s http://localhost:3200/api/forecast/closing > /dev/null
```

### 3. Best 페이지 재캐싱
```bash
# Category Best (25FW)
curl -s "http://localhost:3200/api/products/category/women-down?season=25FW" > /dev/null

# Weekly Best (25FW)
curl -s "http://localhost:3200/api/products/weekly/women-down?season=25FW" > /dev/null

# Trending (25FW)
curl -s "http://localhost:3200/api/products/trending?season=25FW" > /dev/null

# LOT Analysis
curl -s "http://localhost:3200/api/products/lot-analysis/women-down" > /dev/null
```

## 응답 형식

```
🗑️ 전체 캐시 삭제 완료 (X개)
🔄 재캐싱 완료
   - Overview: KPI, Categories, Weekly, Forecast
   - Best: Category, Weekly, Trending, LOT
```
