# Git 커밋

변경사항을 확인하고 커밋합니다.

## 실행 절차

### 0. input 폴더 파일 체크 (필수!)
```bash
git status input/ --porcelain
```
- **untracked 파일(??)**이 있으면 반드시 `git add input/` 실행
- input 폴더의 모든 파일(csv, json, md 등)은 GitHub에 포함되어야 함
- ⚠️ untracked 파일이 있는데 add하지 않으면 커밋 중단

### 1. 변경사항 확인
```bash
git status
git diff --stat
```

### 2. 커밋 메시지 생성
- 변경된 파일과 내용을 분석하여 적절한 커밋 메시지 제안
- 형식: `type(scope): description`
- type: feat, fix, refactor, docs, style, chore 등

### 3. 스테이징 및 커밋
```bash
# input 폴더 untracked 파일 먼저 추가
git add input/

# 나머지 변경사항 추가
git add -A
git commit -m "커밋 메시지"
```

### 4. 푸시 여부 확인
- 사용자에게 push 여부 물어보기
- 승인 시 `git push origin [브랜치명]` 실행

## 커밋 메시지 컨벤션

```
feat: 새 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링
docs: 문서 수정
style: 코드 스타일 변경 (포맷팅 등)
chore: 빌드, 설정 변경
perf: 성능 개선
data: input 데이터 파일 추가/수정
```

## 출력 형식

### input 폴더 체크 결과
- ✅ input 폴더: 모든 파일 추적 중
- ⚠️ input 폴더: untracked 파일 [N]개 발견 → 자동 추가

### 변경 요약
- **수정**: [파일 수]개
- **추가**: [파일 수]개
- **삭제**: [파일 수]개

### 제안 커밋 메시지
```
[type](scope): [description]

- [변경사항 1]
- [변경사항 2]
```

### 실행 결과
- 커밋 완료: [커밋 해시]
- 푸시 완료/스킵
