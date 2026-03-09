# 듀베티카 원가 조회 쿼리 (Snowflake)

## 개요
- DB: Snowflake (FNF)
- 스키마: PRCS
- 브랜드 코드: 'V' (듀베티카)
- 시즌 형식: '25F' (25FW)

## 1. 기본 원가 조회 (마스터)

```sql
-- 듀베티카 25FW 원가 마스터 조회
SELECT
    PRDT_CD AS "품번",
    PART_CD AS "파트코드",
    SESN AS "시즌",
    MFAC_OFFER_COST AS "견적단가_원화",
    MFAC_COST_AMT AS "예상제조원가",
    TAG_AMT AS "판매가",
    HQ_SUPPLY_AMT AS "본사공급자재단가",
    EXTRA_AMT AS "부대비용",
    MFAC_COMPY AS "협력사코드",
    PO_NO AS "발주번호"
FROM FNF.PRCS.DB_COST_MST
WHERE BRD_CD = 'V'           -- 듀베티카
  AND SESN = '25F'           -- 25FW 시즌
ORDER BY PRDT_CD;
```

## 2. 원가 상세 조회 (자재별)

```sql
-- 듀베티카 25FW 자재별 원가 상세
SELECT
    PRDT_CD AS "품번",
    TYPE1 AS "타입",
    TYPE2 AS "분류",
    MFAC_OFFER_COST AS "협력사제시단가",
    MFAC_NEGO_COST AS "본사협의단가",
    CURRENCY AS "통화"
FROM FNF.PRCS.DB_COST_DTL
WHERE BRD_CD = 'V'
  AND SESN = '25F'
ORDER BY PRDT_CD, TYPE1;
```

## 3. MARKUP 계산 포함 조회

```sql
-- 듀베티카 25FW MARKUP 분석
-- MARKUP = 판매가 / (예상제조원가 × 1.1)
SELECT
    PRDT_CD AS "품번",
    MFAC_COST_AMT AS "예상제조원가",
    TAG_AMT AS "판매가",
    ROUND(TAG_AMT / NULLIF(MFAC_COST_AMT * 1.1, 0), 2) AS "MARKUP"
FROM FNF.PRCS.DB_COST_MST
WHERE BRD_CD = 'V'
  AND SESN = '25F'
  AND MFAC_COST_AMT > 0
ORDER BY "MARKUP" DESC;
```

## 4. 시즌 코드 확인

```sql
-- 듀베티카 시즌 코드 목록 확인
SELECT DISTINCT SESN AS "시즌코드"
FROM FNF.PRCS.DB_COST_MST
WHERE BRD_CD = 'V'
ORDER BY SESN DESC;
```

## 5. 원가 요약 통계

```sql
-- 듀베티카 25FW 원가 요약
SELECT
    COUNT(DISTINCT PRDT_CD) AS "품번수",
    ROUND(AVG(MFAC_COST_AMT), 0) AS "평균제조원가",
    ROUND(AVG(TAG_AMT), 0) AS "평균판매가",
    ROUND(AVG(TAG_AMT / NULLIF(MFAC_COST_AMT * 1.1, 0)), 2) AS "평균MARKUP"
FROM FNF.PRCS.DB_COST_MST
WHERE BRD_CD = 'V'
  AND SESN = '25F'
  AND MFAC_COST_AMT > 0;
```

## 참고 테이블
- `FNF.PRCS.DB_COST_MST`: 원가 마스터
- `FNF.PRCS.DB_COST_DTL`: 원가 디테일 (자재별)
- `FNF.PRCS.DB_PRDT`: 상품 마스터

## Snowflake 문법 참고
- 한글 별칭은 쌍따옴표("")로 감싸야 함
- NULLIF로 0 나누기 방지
- ROUND 함수로 소수점 처리
