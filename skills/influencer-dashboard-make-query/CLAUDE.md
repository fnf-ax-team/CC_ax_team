# F&F MKT 대시보드 프로젝트

## 현재 상태
- **PHASE 1 쿼리 완료** (21개 SQL 파일) - 2026-01-09
- **C 섹션 개선** (2026-01-12): P_CHANNEL/P_SALE_TYPE 파라미터 제거, 채널/유통별 컬럼 방식으로 변경
- **D 섹션 개선**: D01 YoY 추가, D02 정렬/VIEW/중복제거, D04 IMP 비중 변경
- **D 섹션 월간/MTD 쿼리 추가** (2026-01-12): D01M~D04M 월간 4개 + MTD 4개 = 8개 추가
- **E 섹션 정리**: E01 삭제, E02->E01, E03->E02, E04 재작성->E03 (4개->3개)
- **E 섹션 개선** (2026-01-12): 경쟁사도 BRD_CD/ADULT_KIDS 기준 필터링 적용
- **E 섹션 월간 쿼리 추가** (2026-01-12): E01M, E02M, E03M 월간 3개 추가
- **E03/E03M YoY 로직 수정** (2026-01-12): 증감률(`(당해-전년)/전년*100`)에서 비율(`당해/전년*100`)로 변경
- **MTD 쿼리 추가** (2026-01-12): 당월 전용 쿼리 4개 추가 (C02M_mtd, E01M_mtd, E02M_mtd, E03M_mtd)
- **B_summary MTD 쿼리 추가** (2026-01-12): B01M_mtd, B02M_mtd, B03M_mtd 3개 추가
- **B03 YoY 추가** (2026-01-12): B03, B03M에 전년비 컬럼 추가 (prev_year_imp/eng, yoy_imp/eng_rate)
- **B 섹션 brand_cd 컬럼 추가** (2026-01-12): B01~B03 주간/월간 쿼리에 brand_cd 컬럼 추가
- **DB_SCS_M 컬럼 표준화** (2026-01-12): AC_ prefix 컬럼 대신 일반 컬럼(SALE_NML_*) 사용으로 통일
- **C01 정상/이월 로직 변경** (2026-01-12): 기준일자 기반에서 P_SESN_LIST 기반으로 변경
- **VW_CONTENT_BASE 뷰 배포 완료** (Snowflake)
- **SP_DW_INFLUENCER_CAMPAIGN_CONTENT v3.1** (2026-01-13): PREV_LIKE/COMMENT 로직 전면 개선
  - CTE 기반 + SEQ 컬럼 활용으로 변경 (서브쿼리 LIMIT 9 방식 제거)
  - ACCOUNT_ID 조인으로 변경 (INFLUENCER_CRAWL_ID 매칭 실패 해결)
  - POST_DT 이후 최초 크롤링 날짜 기준으로 변경
  - CONTENT_TYPE = 'photo' 필터 추가 (이미지 게시글만 합산)
- **시즌 필터 + 상품상태 로직 리팩토링** (2026-01-15): 백엔드 → 프론트엔드 이동
  - 백엔드: `ALL_SEASONS` 상수, `buildSeasonList`, `sesnToNum`, `getPrevSF` 메서드 제거
  - 백엔드: `productStatus` 파라미터 제거 (DTO, Service, Controller)
  - 프론트엔드: `allSeasons` 데이터 + `resolvedSeasons` useMemo로 시즌 계산
  - 처리 흐름: 프론트엔드에서 계산된 시즌 목록만 백엔드에 전달
- **다음 단계**: 데이터 파이프라인 점검 (LIKE_CNT/COMMENT_CNT NULL 이슈) 및 API 개발

## 테스트 결과 요약
- 정상 작동: A01~A03, B01~B03M (MTD 포함), C01~C02M (MTD 포함), D01~D04M (MTD 포함), E01~E03M (MTD 포함)
- 데이터 이슈: D01~D04 (LIKE_CNT/COMMENT_CNT NULL → ENG=0, 파이프라인 점검 필요)

## 쿼리 파일 위치
> **경로 변경 (2026-01-12)**: 쿼리 파일이 `fnf-marketing-dashboard/` 레포 내부로 이동됨

```
fnf-marketing-dashboard/queries/
├── _views/
│   └── VW_CONTENT_BASE.sql         # 콘텐츠 베이스 뷰 (배포 완료)
├── A_filter/
│   ├── A01_brand_master.sql        # 브랜드 필터
│   ├── A02_sesn_master.sql         # 시즌 필터
│   └── A03_category_master.sql     # 카테고리 필터 (2레벨)
├── B_summary/
│   ├── B01_sales_summary.sql               # 주간 매출 (YoY)
│   ├── B01M_sales_summary_monthly.sql      # 월간 매출 (YoY)
│   ├── B01M_mtd_sales_summary.sql          # 당월 MTD 매출 (YoY)
│   ├── B02_search_summary.sql              # 주간 검색량 (YoY)
│   ├── B02M_search_summary_monthly.sql     # 월간 검색량 (YoY)
│   ├── B02M_mtd_search_summary.sql         # 당월 MTD 검색량 (YoY)
│   ├── B03_influencer_imp_eng.sql          # 인플루언서 IMP/ENG (주간, YoY)
│   ├── B03M_influencer_imp_eng_monthly.sql # 인플루언서 IMP/ENG (월간, YoY)
│   └── B03M_mtd_influencer_imp_eng.sql     # 당월 MTD IMP/ENG (YoY)
├── C_brand_trend/
│   ├── C01_sale_best.sql           # 제품 베스트 테이블 (5대 필터)
│   ├── C01M_sale_best_monthly.sql  # 제품 베스트 월간
│   ├── C02_sales_trend_extended.sql  # 차트용 (매출+전년+검색+IF_IMP/CNT)
│   ├── C02M_sales_trend_extended_monthly.sql # 차트용 월간
│   └── C02M_mtd_sales_trend_extended.sql # 차트용 당월 MTD (일별 테이블)
├── D_influencer/
│   ├── D01_content_summary.sql             # 콘텐츠 요약 (주간, YoY)
│   ├── D01M_content_summary_monthly.sql    # 콘텐츠 요약 (월간, YoY)
│   ├── D01M_mtd_content_summary.sql        # 콘텐츠 요약 (당월 MTD, YoY)
│   ├── D02_top_influencers.sql             # 우수 인플루언서 (주간)
│   ├── D02M_top_influencers_monthly.sql    # 우수 인플루언서 (월간)
│   ├── D02M_mtd_top_influencers.sql        # 우수 인플루언서 (당월 MTD)
│   ├── D03_content_detail.sql              # 콘텐츠 상세 (주간)
│   ├── D03M_content_detail_monthly.sql     # 콘텐츠 상세 (월간)
│   ├── D03M_mtd_content_detail.sql         # 콘텐츠 상세 (당월 MTD)
│   ├── D04_content_distribution.sql        # 콘텐츠 분포 (주간, IMP 비중)
│   ├── D04M_content_distribution_monthly.sql # 콘텐츠 분포 (월간)
│   └── D04M_mtd_content_distribution.sql   # 콘텐츠 분포 (당월 MTD)
└── E_search/
    ├── E01_market_search_top20.sql         # 마켓 TOP20 + 자사 순위 (주간)
    ├── E01M_market_search_top20_monthly.sql # 마켓 TOP20 + 자사 순위 (월간)
    ├── E01M_mtd_market_search_top20.sql    # 마켓 TOP20 + 자사 순위 (당월 MTD)
    ├── E02_yoy_keyword_top5.sql            # [자사] 급상승 TOP5 (주간 YoY)
    ├── E02M_yoy_keyword_top5_monthly.sql   # [자사] 급상승 TOP5 (월간 YoY)
    ├── E02M_mtd_yoy_keyword_top5.sql       # [자사] 급상승 TOP5 (당월 MTD)
    ├── E03_market_rising_top5.sql          # [마켓] 급상승 TOP5 (주간 YoY)
    ├── E03M_market_rising_top5_monthly.sql # [마켓] 급상승 TOP5 (월간 YoY)
    └── E03M_mtd_market_rising_top5.sql     # [마켓] 급상승 TOP5 (당월 MTD)
```

## 브랜드 코드 매핑 (중요!)

### 브랜드 마스터 테이블
- **테이블**: `FNF.MKT.DW_SYS_BRD` (쿼리에서 직접 사용)
- **원천**: `INFLUENCER.BRAND`
- **프로시저**: `mkt.SP_DW_SYS_BRD`

> **참고**: VW_BRAND_CODE_MAP 뷰는 더 이상 사용하지 않음. 모든 쿼리에서 DW_SYS_BRD 테이블을 CTE로 직접 조인하여 사용.

### DW_SYS_BRD 테이블 구조 (4개 컬럼)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| SYS_BRD_CD | NUMBER | 시스템 브랜드 코드 (PK) |
| SYS_BRD_NM | VARCHAR | 브랜드명 |
| BRD_CD | VARCHAR | 브랜드 코드 (M, I, X, ST, V, A, W) |
| ADULT_KIDS | VARCHAR | 성인/키즈 ('성인', '키즈') |

### DW_SYS_BRD 데이터 (8개)
| SYS_BRD_CD | SYS_BRD_NM | BRD_CD | ADULT_KIDS |
|:----------:|------------|:------:|:----------:|
| 1 | MLB | M | 성인 |
| 2 | MLB Kids | I | 키즈 |
| 3 | Discovery | X | 성인 |
| 4 | Duvetica | V | 성인 |
| 5 | Stretch angels | A | 성인 |
| 6 | Supra | W | 성인 |
| 7 | Discovery_Kids | X | 키즈 |
| 8 | Sergio Tacchini | ST | 성인 |

### 브랜드 코드 매핑 (원천 시스템 → DW_SYS_BRD)
매출/인플루언서 데이터의 BRD_CD와 DW_SYS_BRD.BRD_CD 변환:
| 원천 BRD_CD | DW_SYS_BRD.BRD_CD | 브랜드명 |
|:-----------:|:-----------------:|----------|
| M | M | MLB |
| X | I | MLB Kids |
| D | X | Discovery |
| S | ST | Sergio Tacchini |
| V | V | Duvetica |

### 브랜드 필터 조인 규칙 (중요!)

**파라미터 흐름**: `SYS_BRD_CD` (1~8) → `BRD_CD` + `ADULT_KIDS`로 실제 필터

#### ADULT_KIDS 컬럼 매핑
| 테이블 | 컬럼명 | 값 | 조인 시 사용 |
|--------|--------|------|-------------|
| DW_SYS_BRD | ADULT_KIDS | '성인', '키즈' | 기준 |
| DB_PRDT | ADULT_KIDS | 'A', 'K' | X |
| DB_PRDT | **ADULT_KIDS_NM** | '성인', '키즈' | O |
| DB_SRCH_KWD_NAVER_MST | ADULT_KIDS | '성인', '키즈' | O |

#### 왜 필요한가?
Discovery와 Discovery Kids는 둘 다 `BRD_CD = 'X'`:
- SYS_BRD_CD = 3 (Discovery) → BRD_CD='X', ADULT_KIDS='성인'
- SYS_BRD_CD = 7 (Discovery Kids) → BRD_CD='X', ADULT_KIDS='키즈'

**BRD_CD만으로는 구분 불가 → ADULT_KIDS 필수!**

#### 올바른 조인 조건
```sql
-- DB_PRDT 조인: ADULT_KIDS_NM 사용
INNER JOIN FNF.MKT.DW_SYS_BRD b
    ON p.BRD_CD = b.BRD_CD
   AND p.ADULT_KIDS_NM = b.ADULT_KIDS

-- 검색 마스터 조인: ADULT_KIDS 사용
INNER JOIN FNF.MKT.DW_SYS_BRD b
    ON m.BRD_CD = b.BRD_CD
   AND m.ADULT_KIDS = b.ADULT_KIDS
```

### 브랜드 코드 사용 패턴
- **제품 쿼리** (A02, A03, C01 등): `BRD_CD + ADULT_KIDS_NM` 조인
- **검색 쿼리** (E01~E03, C02): `BRD_CD + ADULT_KIDS` 조인
- **매출/인플루언서 쿼리** (B01, B03, D02, D03): CASE 문으로 변환 후 조인

## 쿼리 작성 규칙 (2026-01-09)

### 1. 매출 계산 로직 (DB_SCS_W)

```sql
-- 올바른 매출 계산
SUM(s.SALE_NML_QTY_CNS + s.SALE_RET_QTY_CNS) AS SALE_QTY
SUM(s.SALE_NML_SALE_AMT_CNS + s.SALE_RET_SALE_AMT_CNS) AS SALE_AMT
```

| 규칙 | 설명 |
|------|------|
| CNS만 사용 | CNS = RTL + NOTAX + RF + DOME 이미 포함 |
| NML + RET | RET이 이미 음수값이므로 빼기가 아닌 더하기 |
| SALE_AMT 사용 | TAG_AMT(택가) 말고 SALE_AMT(판매가) 사용 |
| WSL 제외 | 사입(WSL)은 사용 안함 |
| COALESCE 불필요 | SUM()이 NULL 자동 처리 |

### 2. 필터 파라미터 처리 (다중 선택)

```sql
-- 백엔드에서 동적으로 조건 추가/제거
WHERE b.SYS_BRD_CD IN (1, 2)
  AND p.PRDT_KIND_CD IN ('DJ')
  AND p.CAT_NM IN ('모자')
```

| 항목 | 설명 |
|------|------|
| IN 절 사용 | 다중 선택 지원 |
| 백엔드 동적 SQL | 선택 없으면 해당 WHERE 조건 제거 |
| 백엔드 파라미터 | $1, $2, $3... |
| DBeaver 파라미터 | :P_START_DT, :P_SYS_BRD_CD 등 |

### 2.1 날짜 파라미터 사용 패턴 (2026-01-09)

```sql
-- 권장: WHERE 문에 직접 사용 (간결)
WHERE s.BASE_DT BETWEEN :P_START_DT::DATE AND :P_END_DT::DATE

-- 비권장: PARAMS CTE 사용 (불필요한 복잡성)
WITH PARAMS AS (SELECT :P_START_DT::DATE AS START_DT, :P_END_DT::DATE AS END_DT)
SELECT ... FROM ... CROSS JOIN PARAMS WHERE s.BASE_DT BETWEEN PARAMS.START_DT AND PARAMS.END_DT
```

| 규칙 | 설명 |
|------|------|
| 직접 사용 | `:P_START_DT::DATE` 형태로 WHERE 문에 직접 사용 |
| PARAMS CTE 불필요 | 단순 파라미터 전달에는 CTE 사용 안함 |
| 형변환 명시 | `::DATE` 형변환을 파라미터에 직접 적용 |

### 2.1.1 주간 테이블 날짜 조건 (DB_SCS_W, DB_SRCH_KWD_NAVER_W)

```sql
-- 주간 테이블: END_DT만 사용 (START_DT는 월요일, END_DT는 일요일로 고정)
WHERE 1=1
  AND s.END_DT = :P_END_DT::DATE

-- 전주 데이터
WHERE 1=1
  AND s.END_DT = DATEADD(week, -1, :P_END_DT::DATE)
```

| 규칙 | 설명 |
|------|------|
| END_DT만 사용 | START_DT는 자동 계산됨 (월~일 고정) |
| **일요일 필수** | P_END_DT는 반드시 일요일 날짜 전달 (DB_SCS_W, DB_SRCH_KWD_NAVER_W는 일요일만 존재) |
| WHERE 1=1 | 동적 SQL 가시성 확보 |
| 전주 계산 | `DATEADD(week, -1, :P_END_DT::DATE)` |

### 2.2 YoY 비율 계산 (2026-01-09)

```sql
-- 전년 대비 비율 (%) = 현재 / 전년 * 100
CASE
    WHEN COALESCE(prev_year_value, 0) = 0 THEN 0
    ELSE ROUND(curr_value::NUMERIC / prev_year_value * 100, 1)
END AS yoy_change_rate
```

| 항목 | 설명 |
|------|------|
| 계산 방식 | `현재값 / 전년값 * 100` (비율) |
| 해석 | 100% = 동일, 150% = 1.5배, 50% = 절반 |
| 형변환 | `::NUMERIC` 으로 정밀 계산 |
| 0 처리 | 전년값 0이면 결과도 0 |
| 주간 전년비 | `DATEADD(day, -364, :P_END_DT::DATE)` (52주 전) |
| 월간 전년비 | `DATEADD(year, -1, :P_YYMM)` |

### 2.2.1 MTD (Month-To-Date) YoY 비교 로직 (2026-01-12)

> **당월 데이터 조회 시 공정한 전년 비교를 위한 특별 처리**

**[문제 상황]**
- 당월 조회 시 월간 테이블(DB_SCS_M, DB_SRCH_KWD_NAVER_M)은 이미 MTD 누적값
- 전년 동월은 전체 월 데이터 → 불공정한 비교

**[해결 방법]**
- 당월 데이터: 월간 테이블 사용 (이미 MTD)
- 전년 데이터: **일별 테이블**에서 같은 일수만 집계

```sql
-- MTD 전년 비교: 일별 테이블 사용
-- 예: 2026-01 조회 시 오늘이 12일이면
-- 전년 데이터 = 2025-01-01 ~ 2025-01-12 (12일간)

-- 전년 기간 계산
DATEADD(year, -1, DATE_TRUNC('month', :P_YYMM))  -- 시작: 2025-01-01
DATEADD(year, -1, CURRENT_DATE())                 -- 종료: 2025-01-12
```

**[MTD 쿼리 파일 명명 규칙]**
| 파일명 패턴 | 설명 | 사용 테이블 |
|-------------|------|-------------|
| *M_*.sql | 일반 월간 쿼리 | 월간 테이블 (M) |
| *M_mtd_*.sql | 당월 MTD 쿼리 | 월간 + 일별 테이블 (M + D) |

**[백엔드 쿼리 선택 로직]**
```python
def get_monthly_query(query_name, p_yymm):
    current_month = datetime.now().strftime('%Y-%m')
    if p_yymm == current_month:
        return f"{query_name}_mtd.sql"  # MTD 쿼리
    else:
        return f"{query_name}.sql"       # 일반 월간 쿼리
```

**[MTD 쿼리 적용 대상]**
| 섹션 | MTD 쿼리 | 일별 테이블 |
|------|----------|-------------|
| B01 | B01M_mtd_sales_summary.sql | DW_SCS_D |
| B02 | B02M_mtd_search_summary.sql | DB_SRCH_KWD_NAVER_D |
| B03 | B03M_mtd_influencer_imp_eng.sql | VW_CONTENT_BASE (POST_DT) |
| C02 | C02M_mtd_sales_trend_extended.sql | DW_SCS_D |
| D01 | D01M_mtd_content_summary.sql | VW_CONTENT_BASE (POST_DT) |
| D02 | D02M_mtd_top_influencers.sql | VW_CONTENT_BASE (POST_DT) |
| D03 | D03M_mtd_content_detail.sql | VW_CONTENT_BASE (POST_DT) |
| D04 | D04M_mtd_content_distribution.sql | VW_CONTENT_BASE (POST_DT) |
| E01 | E01M_mtd_market_search_top20.sql | DB_SRCH_KWD_NAVER_D |
| E02 | E02M_mtd_yoy_keyword_top5.sql | DB_SRCH_KWD_NAVER_D |
| E03 | E03M_mtd_market_rising_top5.sql | DB_SRCH_KWD_NAVER_D |

> **참고**: C01M은 YoY 비교가 없으므로 MTD 쿼리 불필요 (월간 테이블 그대로 사용)
> **참고**: B03M_mtd, D01M~D04M_mtd는 VW_CONTENT_BASE의 POST_DT 컬럼으로 일별 필터링 (별도 일별 테이블 없음)

### 2.3 시즌 YoY 파라미터 처리 (중요!) (2026-01-09, 2026-01-15 업데이트)

전년 매출 비교 시, 시즌 필터가 있으면 **전년 시즌도 별도 파라미터로 전달**해야 합니다.

> **변경사항 (2026-01-15)**: 시즌 계산 로직이 백엔드에서 프론트엔드로 이동됨

```sql
-- 당해 매출: P_SESN_LIST 사용
AND p.SESN IN (:P_SESN_LIST)

-- 전년 매출: P_SESN_LIST_PREV 사용
AND p.SESN IN (:P_SESN_LIST_PREV)
```

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| :P_SESN_LIST | 당해 시즌 | ['25S', '25F'] |
| :P_SESN_LIST_PREV | 전년 시즌 (년도-1) | ['24S', '24F'] |

**[프론트엔드 계산 로직 (TypeScript)]**
```typescript
// client/components/dashboard/sales-trend-chart.tsx

// 시즌 코드 → 숫자 변환
const sesnToNum = (sesn: string): number => {
  const year = parseInt(sesn.slice(0, 2), 10);
  const suffix = sesn.slice(2);
  const suffixMap: Record<string, number> = { S: 1, N: 2, F: 3 };
  return year * 10 + (suffixMap[suffix] || 0);
};

// 전년 S/F 시즌 계산
const getPrevSF = (sesn: string): string => {
  const year = parseInt(sesn.slice(0, 2), 10);
  const suffix = sesn.slice(2);
  return `${(year - 1).toString().padStart(2, '0')}${suffix}`;
};

// resolvedSeasons: useMemo로 계산
// - productStatusFilter가 '정상'이면: 선택된 시즌만
// - productStatusFilter가 '이월'이면: 선택된 시즌보다 오래된 시즌들
// - productStatusFilter가 '전체'이면: 전체 시즌
const resolvedSeasons = useMemo(() => {
  // allSeasons: useSeasonData 훅에서 조회한 전체 시즌 목록
  // selectedSeasons: 사용자가 선택한 시즌
  // productStatusParam: 상품상태 필터 ('정상'/'이월'/'전체')
  // ... 계산 로직
}, [allSeasons, selectedSeasons, productStatusParam]);
```

**[백엔드 처리 (NestJS)]**
```typescript
// server/src/sales-trend/sales-trend.service.ts
// 프론트엔드에서 계산된 시즌 목록을 그대로 수신하여 SQL에 전달
const seasonArray = seasons?.split(',').filter(s => s.trim()) || [];
// → SQL P_SESN_LIST 파라미터로 사용
```

**[적용 쿼리]**
- C02_sales_trend_extended.sql (주간 매출 추세)

> **전체 선택 시**: P_SESN_LIST, P_SESN_LIST_PREV 두 조건 모두 SQL에서 제거

### 3. B 쿼리 필터 테이블 조인

모든 B 쿼리는 필터 테이블과 조인 필요:
- `FNF.MKT.DW_SYS_BRD` (브랜드 필터)
- `FNF.MKT.DB_PRDT` (카테고리 필터)

### 4. 브랜드 코드 매핑 (원천 → DW_SYS_BRD)

| 원천 BRD_CD | DW_SYS_BRD.BRD_CD | 브랜드명 |
|:-----------:|:-----------------:|----------|
| M | M | MLB |
| X | I | MLB Kids |
| D | X | Discovery |
| S | ST | Sergio Tacchini |
| V | V | Duvetica |

### 5. C 쿼리 필터 (5대 필터) (2026-01-12)

#### C01, C02 공통 필터 (5대 기본 필터)

> **변경사항 (2026-01-12)**: P_CHANNEL, P_SALE_TYPE 파라미터 제거됨. 채널/유통별 매출은 컬럼으로 분리하여 한 번에 반환. 프론트엔드에서 필터 선택 시 즉시 전환 가능.

**[기본 필터 5개]**
| 파라미터 | 설명 | 처리 |
|----------|------|------|
| :P_END_DT | 기준주차 종료일 | 필수 |
| :P_SYS_BRD_CD_LIST | 브랜드 코드 (1~8) | IN 절, 전체 시 조건 제거 |
| :P_SESN_LIST | 시즌 코드 | IN 절, 전체 시 조건 제거 |
| :P_PRDT_KIND_CD_LIST | 중분류 코드 | IN 절, 전체 시 조건 제거 |
| :P_CAT_NM_LIST | 카테고리명 (2레벨) | IN 절, 전체 시 조건 제거 |

**[백엔드 처리 방식]**
- 다중 선택: `AND b.SYS_BRD_CD IN (1, 2, 3)` 형태로 값 바인딩
- 전체 선택: 해당 WHERE 조건 자체를 SQL에서 제거

> **참고**: 상품상태(정상/이월)는 C01에서 `product_status` 컬럼으로 반환되어 프론트엔드에서 필터링

#### 채널/유통별 매출 컬럼 (C01, C02 공통)

**[C01 제품 베스트 - 매출 컬럼 10개]**
| 수량 컬럼 | 금액 컬럼 | 설명 |
|-----------|-----------|------|
| sales_qty_all | sales_amt_all | 한국전체 (CNS) |
| sales_qty_on | sales_amt_on | 온라인 |
| sales_qty_off | sales_amt_off | 오프라인 |
| sales_qty_rtl | sales_amt_rtl | 국내 |
| sales_qty_etc | sales_amt_etc | 면세/RF/도매 |

**[C02 매출 추세 - 당해/전년 매출 컬럼 10개]**
| 당해 매출 | 전년 매출 | 설명 |
|-----------|-----------|------|
| sales_amt_all | sales_amt_prev_all | 한국전체 (CNS) |
| sales_amt_on | sales_amt_prev_on | 온라인 |
| sales_amt_off | sales_amt_prev_off | 오프라인 |
| sales_amt_rtl | sales_amt_prev_rtl | 국내 |
| sales_amt_etc | sales_amt_prev_etc | 면세/RF/도매 |

#### 프론트엔드 채널/유통 필터 처리

| 채널 선택 | 유통 선택 | 사용할 컬럼 (_all/_on/_off/_rtl/_etc) |
|-----------|-----------|--------------------------------------|
| 한국전체 | 전체 | `*_all` |
| 한국전체 | 온라인 | `*_on` |
| 한국전체 | 오프라인 | `*_off` |
| 국내 | (무시) | `*_rtl` |
| 면세/RF/도매 | (무시) | `*_etc` |

> **주의**: 국내(RTL), 면세/RF/도매(ETC) 선택 시 온/오프 구분 불가

#### 정상/이월 판단 로직 - P_SESN_LIST 기준 (2026-01-12 변경, 2026-01-15 업데이트)

> **변경사항 (2026-01-12)**: 기준일자(P_END_DT/P_YYMM) 기반에서 **P_SESN_LIST 기반**으로 변경됨
> **변경사항 (2026-01-15)**: 정상/이월 시즌 계산 로직이 **백엔드에서 프론트엔드로 이동**됨

**[판단 기준]**
- P_SESN_LIST 중 **가장 오래된 시즌(MIN값)** 이상 = **정상**
- P_SESN_LIST 중 **가장 오래된 시즌(MIN값)** 미만 = **이월**

**[시즌 코드 → 숫자 변환]**
```
25S → 251, 25N → 252, 25F → 253
26S → 261, 26N → 262, 26F → 263
```

**[SQL 로직]**
```sql
-- 상품상태 계산 (정상/이월) - P_SESN_LIST 기준
CASE
    WHEN (
        LEFT(p.SESN, 2)::INT * 10 +
        CASE RIGHT(p.SESN, 1) WHEN 'S' THEN 1 WHEN 'N' THEN 2 WHEN 'F' THEN 3 ELSE 0 END
    ) >= :P_MIN_SESN_NUM
    THEN '정상'
    ELSE '이월'
END AS PRODUCT_STATUS
```

**[프론트엔드 처리 흐름 (2026-01-15)]**
```
프론트엔드:
  selectedSeasons + productStatusFilter
  → productStatusParam 계산 (정상/이월/전체)
  → resolvedSeasons 계산 (allSeasons 데이터 활용)
  → API 호출 시 resolvedSeasons만 전달

백엔드:
  seasons 파라미터 수신
  → split(',')으로 배열 변환
  → SQL P_SESN_LIST 파라미터로 그대로 전달
```

**[프론트엔드 계산 로직 (TypeScript)]**
```typescript
// client/components/dashboard/sales-trend-chart.tsx
const sesnToNum = (sesn: string): number => {
  const year = parseInt(sesn.slice(0, 2), 10);
  const suffix = sesn.slice(2);
  const suffixMap: Record<string, number> = { S: 1, N: 2, F: 3 };
  return year * 10 + (suffixMap[suffix] || 0);
};

// resolvedSeasons: useMemo로 정상/이월에 따른 시즌 목록 계산
// allSeasons: useSeasonData 훅에서 A02 쿼리로 조회한 전체 시즌
```

**[예시]**
| selectedSeasons | productStatusFilter | resolvedSeasons (계산 결과) |
|-----------------|---------------------|----------------------------|
| ['26S'] | 정상 | ['26S'] |
| ['26S'] | 이월 | ['25F', '25N', '25S', ...] (26S 미만 시즌들) |
| ['25N', '25F'] | 정상 | ['25N', '25F'] |
| 전체 | 전체 | (조건 제거) |

**[적용 쿼리]**
- C01_sale_best.sql (주간)
- C01M_sale_best_monthly.sql (월간)

**[변경된 파일 목록 (2026-01-15)]**
| 구분 | 파일 | 변경 내용 |
|------|------|----------|
| 백엔드 | sales-trend.service.ts | ALL_SEASONS, buildSeasonList, sesnToNum, getPrevSF 제거 |
| 백엔드 | sales-trend.dto.ts | productStatus 필드 제거 |
| 백엔드 | sales-trend.controller.ts | productStatus 파라미터 제거 |
| 프론트엔드 | client.ts | getSalesTrendData, getBestProducts에서 productStatus 제거 |
| 프론트엔드 | useSalesTrendData.ts | productStatus 옵션 제거 |
| 프론트엔드 | useBestProductsData.ts | productStatus 옵션 제거 |
| 프론트엔드 | sales-trend-chart.tsx | resolvedSeasons useMemo 유지, API 호출에서 productStatus 제거 |

### 6. E 쿼리 경쟁사 필터링 (2026-01-12)

> **중요**: 검색 마스터(DB_SRCH_KWD_NAVER_MST)에서 경쟁사도 BRD_CD/ADULT_KIDS로 관리됨

#### 경쟁사 브랜드 매핑 구조
| BRD_CD | ADULT_KIDS | 자사 브랜드 | 경쟁사 브랜드 수 |
|--------|------------|-------------|-----------------|
| M | 성인 | MLB | 566개 |
| I | 키즈 | MLB Kids | 77개 |
| ST | 성인 | Sergio Tacchini | 225개 |
| X | 성인 | Discovery | 없음 |
| X | 키즈 | Discovery Kids | 없음 |
| V | 성인 | Duvetica | 없음 |

#### E01, E03 경쟁사 필터링 로직
```sql
-- BRAND_FILTER CTE 사용 (자사/경쟁사 공통)
WITH BRAND_FILTER AS (
    SELECT SYS_BRD_CD, SYS_BRD_NM, BRD_CD, ADULT_KIDS
    FROM FNF.MKT.DW_SYS_BRD
    WHERE SYS_BRD_CD IN (:P_SYS_BRD_CD_LIST)
),

-- 경쟁사 키워드 조회 시 BRAND_FILTER 조인
CURR_WEEK_COMPETITOR AS (
    SELECT m.COMP_BRD_NM AS BRAND, ...
    FROM FNF.PRCS.DB_SRCH_KWD_NAVER_W w
    INNER JOIN FNF.PRCS.DB_SRCH_KWD_NAVER_MST m ON w.KWD = m.KWD_NM
    INNER JOIN BRAND_FILTER bf ON m.BRD_CD = bf.BRD_CD AND m.ADULT_KIDS = bf.ADULT_KIDS
    WHERE m.COMP_TYPE = '경쟁사'
    ...
)
```

#### 파라미터 요약
| 쿼리 | 파라미터 | 설명 |
|------|----------|------|
| E01 | P_END_DT, P_SYS_BRD_CD_LIST, P_CAT_NM_LIST | 마켓 TOP20 + 자사 순위 |
| E02 | P_END_DT, P_SYS_BRD_CD_LIST, P_CAT_NM_LIST | 자사 급상승 TOP5 |
| E03 | P_END_DT, P_SYS_BRD_CD_LIST, P_CAT_NM_LIST | 마켓 급상승 TOP5 |

> **주의**: Discovery, Duvetica는 경쟁사 데이터가 없으므로 E01, E03에서 경쟁사 결과 없음

---

## 테스트 파라미터 기본값
```sql
:P_START_DT = DATEADD(week, -4, CURRENT_DATE())
:P_END_DT = CURRENT_DATE()
:P_BRD_CD = NULL
:P_CATEGORY_CD = NULL
```

## DB 정보
- Platform: Snowflake
- Database: **FNF** (fully qualified name 필수)
- Schemas: `FNF.MKT`, `FNF.PRCS`

### 주요 테이블 (주간/월간/일별)

| 구분 | 테이블 | 용도 |
|------|--------|------|
| 매출 주간 | FNF.MKT.DB_SCS_W | 주간 매출 (END_DT=일요일) |
| 매출 월간 | FNF.PRCS.DB_SCS_M | 월간 매출 (YYMM) |
| 매출 일별 | FNF.PRCS.DW_SCS_D | 일별 매출 (DT) - MTD 전년비 계산용 |
| 검색 주간 | FNF.PRCS.DB_SRCH_KWD_NAVER_W | 주간 검색량 (END_DT=일요일) |
| 검색 월간 | FNF.PRCS.DB_SRCH_KWD_NAVER_M | 월간 검색량 (YYMM) |
| 검색 일별 | FNF.PRCS.DB_SRCH_KWD_NAVER_D | 일별 검색량 (SRCH_DT) - MTD 전년비 계산용 |

> **참고**: 일별 테이블(DW_SCS_D, DB_SRCH_KWD_NAVER_D)은 MTD 쿼리에서만 사용 (전년 동기간 비교용).

### DB_SCS_M 컬럼 사용 규칙 (2026-01-12)

> **중요**: DB_SCS_M 월간 테이블에서는 **AC_ prefix 컬럼을 사용하지 않음**

| 컬럼 유형 | 사용 여부 | 설명 |
|-----------|:--------:|------|
| SALE_NML_QTY_CNS | O | 해당 월 정상 수량 (당월=MTD) |
| SALE_RET_QTY_CNS | O | 해당 월 반품 수량 (당월=MTD) |
| SALE_NML_SALE_AMT_CNS | O | 해당 월 정상 매출 (당월=MTD) |
| SALE_RET_SALE_AMT_CNS | O | 해당 월 반품 매출 (당월=MTD) |
| AC_SALE_NML_QTY_CNS | X | 기초부터 누적 (사용 안함) |
| AC_SALE_NML_SALE_AMT_CNS | X | 기초부터 누적 (사용 안함) |

**[이유]**
- DB_SCS_M 테이블은 매일 갱신되며, 일반 컬럼(SALE_NML_*)은 해당 월의 MTD 누적값을 자동 반영
- AC_ prefix 컬럼은 기초(시즌 시작)부터의 누적값으로, 월간 분석에 적합하지 않음
- 따라서 일반 월간 쿼리와 MTD 쿼리 모두 동일하게 일반 컬럼 사용

## 계획서 및 보고서
- 쿼리 계획서: `dashboard_query_plan.md`
- 테스트 보고서: `QUERY_TEST_REPORT.md`
