# 전역 개발 환경 설정

## 공용 자료 저장소

모든 프로젝트에서 참고할 수 있는 공용 자료가 있습니다:

**위치**: `~/shared-resources/`

```
shared-resources/
├── ddl/           # 데이터베이스 DDL, 스키마
├── domain/        # 도메인 지식, 비즈니스 로직
├── contacts/      # 담당자 정보, 연락처
└── docs/          # 기타 문서
```

## 사용 가능한 에이전트

### shared-search
공용 자료를 검색할 때 사용합니다.
- "customer 테이블 DDL 찾아줘"
- "주문 도메인 정보 알려줘"
- "데이터팀 담당자 누구야?"

### shared-update
공용 자료를 추가/수정/삭제할 때 사용합니다.
- "이 DDL 공용 자료에 추가해줘"
- "도메인 문서 업데이트해줘"
- "담당자 정보 수정해줘"

## 슬래시 명령어

### /shared-add
빠르게 정보를 추가합니다.
```
/shared-add ddl [DB명] [테이블명]
/shared-add domain [도메인명]
/shared-add contact [팀명] [이름] [역할] [연락처]
```
