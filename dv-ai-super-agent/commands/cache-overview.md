# Overview 캐시 삭제 + 재캐싱

Overview 페이지 캐시만 삭제하고 새로 캐싱합니다.
(Categories 페이지도 동일한 캐시를 공유합니다)

## 실행 순서

### 1. Overview 캐시 삭제
```bash
curl -X DELETE http://localhost:3200/api/cache/page/overview
```

### 2. 재캐싱 (API 호출)
```bash
# KPI (5분 TTL)
curl -s http://localhost:3200/api/kpi > /dev/null

# Categories (10분 TTL)
curl -s http://localhost:3200/api/categories > /dev/null

# Weekly Sales (30분 TTL)
curl -s http://localhost:3200/api/weekly-sales > /dev/null

# Forecast (1시간 TTL)
curl -s http://localhost:3200/api/forecast/closing > /dev/null
```

## 응답 형식

```
🗑️ Overview 캐시 삭제 완료 (X개)
🔄 재캐싱 완료
   - KPI ✓
   - Categories ✓
   - Weekly Sales ✓
   - Forecast ✓
```

## 사용 시나리오

- KPI 계산 로직 수정 후
- 카테고리 분류 변경 후
- 주간 매출 데이터 수정 후
