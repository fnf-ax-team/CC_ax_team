# Best 캐시 삭제 + 재캐싱

Best 페이지 캐시만 삭제하고 새로 캐싱합니다.

## 실행 순서

### 1. Best 캐시 삭제
```bash
curl -X DELETE http://localhost:3200/api/cache/page/best
```

### 2. 재캐싱 (API 호출)
```bash
# Category Best - 25FW (10분 TTL)
curl -s "http://localhost:3200/api/products/category/women-down?season=25FW&limit=10" > /dev/null

# Category Best - 24FW
curl -s "http://localhost:3200/api/products/category/women-down?season=24FW&limit=10" > /dev/null

# Weekly Best - 25FW (10분 TTL)
curl -s "http://localhost:3200/api/products/weekly/women-down?season=25FW&limit=10" > /dev/null

# Weekly Best - 24FW
curl -s "http://localhost:3200/api/products/weekly/women-down?season=24FW&limit=10" > /dev/null

# Trending - 25FW (10분 TTL)
curl -s "http://localhost:3200/api/products/trending?category=women-down&season=25FW" > /dev/null

# Trending - 24FW
curl -s "http://localhost:3200/api/products/trending?category=women-down&season=24FW" > /dev/null

# LOT Analysis (30분 TTL)
curl -s "http://localhost:3200/api/products/lot-analysis/women-down" > /dev/null
```

## 응답 형식

```
🗑️ Best 캐시 삭제 완료 (X개)
🔄 재캐싱 완료
   - Category Best (25FW, 24FW) ✓
   - Weekly Best (25FW, 24FW) ✓
   - Trending (25FW, 24FW) ✓
   - LOT Analysis ✓
```

## 사용 시나리오

- BEST 상품 순위 로직 수정 후
- 급상승 계산 방식 변경 후
- LOT 분석 기준 변경 후
