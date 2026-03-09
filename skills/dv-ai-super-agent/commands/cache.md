# 캐시 상태 확인

데이터 캐시 현황을 확인합니다.

## 실행

```bash
# Redis 연결 상태
curl -s http://localhost:3200/api/cache/health

# 페이지별 캐시 키 목록
curl -s http://localhost:3200/api/cache/data-keys
```

## 응답 형식

```
📊 캐시 상태
- Redis: 연결됨/연결안됨
- Overview 캐시: X개
- Best 캐시: Y개
- 기타: Z개
```

## 관련 커맨드

- `/cache-clear` - 전체 캐시 삭제 + 재캐싱
- `/cache-overview` - Overview 캐시만 삭제 + 재캐싱
- `/cache-best` - Best 캐시만 삭제 + 재캐싱

## 캐싱 현황

| 페이지 | 캐싱 | TTL |
|--------|------|-----|
| Overview | O | KPI 5분, Categories 10분, Weekly 30분, Forecast 1시간 |
| Categories | O | (Overview와 공유) |
| Best | O | Category/Weekly/Trending 10분, LOT 30분 |
| Products | X | 캐싱 미적용 (즉시 반영) |
