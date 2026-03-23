---
name: shared-add
description: 공용 자료에 빠르게 정보를 추가합니다
user-invocable: true
---

# 공용 자료 빠른 추가

사용자가 제공한 정보를 공용 자료에 추가합니다.

## 사용법

```
/shared-add ddl [DB명] [테이블명]
[DDL 내용]

/shared-add domain [도메인명]
[도메인 설명]

/shared-add contact [팀명] [이름] [역할] [연락처]
```

## 저장 위치

- `ddl` → `~/shared-resources/ddl/[db명]/[테이블명].sql`
- `domain` → `~/shared-resources/domain/[도메인명].md`
- `contact` → `~/shared-resources/contacts/[팀명].md` (추가/업데이트)
- `doc` → `~/shared-resources/docs/[제목].md`

## 동작

1. 사용자 입력 파싱
2. 적절한 폴더에 파일 생성/업데이트
3. 결과 확인 메시지 출력

입력이 불완전하면 사용자에게 추가 정보 요청하세요.
