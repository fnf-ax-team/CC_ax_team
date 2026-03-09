# 공용 자료 저장소

여러 프로젝트에서 참고하는 공용 정보를 관리합니다.

## 폴더 구조

```
shared-resources/
├── ddl/           # 데이터베이스 DDL, 스키마 정보
├── domain/        # 도메인 지식, 비즈니스 로직 문서
├── contacts/      # 담당자 정보, 연락처
└── docs/          # 기타 문서, 가이드
```

## 사용 방법

### 검색 (어느 프로젝트에서든)
```
고객 테이블 DDL 찾아줘
주문 도메인 정보 알려줘
데이터팀 담당자 누구야?
```
→ `shared-search` 에이전트가 자동으로 검색

### 추가/수정
```
/shared-add ddl main customer
CREATE TABLE customer (...)

또는

이 DDL 공용 자료에 추가해줘: [DDL 내용]
```
→ `shared-update` 에이전트가 처리

## 파일 명명 규칙

- 소문자 사용
- 단어 구분: 하이픈 (`-`)
- 예: `customer-order.sql`, `payment-domain.md`
