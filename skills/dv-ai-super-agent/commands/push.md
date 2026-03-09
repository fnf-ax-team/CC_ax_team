# Git 푸시

로컬 커밋을 원격 저장소(GitHub)에 업로드합니다.

## 실행 절차

### 0. input 폴더 파일 체크 (필수!)
```bash
git status input/ --porcelain
```
- **untracked 파일(??)**이 있으면 커밋되지 않은 데이터 파일 존재
- ⚠️ untracked 파일 발견 시:
  1. `git add input/`
  2. `git commit -m "data: input 데이터 파일 추가"`
  3. 그 후 push 진행
- input 폴더의 모든 파일(csv, json, md 등)은 반드시 GitHub에 포함되어야 함

### 1. 현재 상태 확인
```bash
git status
git log origin/main..HEAD --oneline
```

### 2. 원격 저장소 정보 확인
```bash
git remote -v
git branch -vv
```

### 3. 푸시 대상 요약
- 푸시할 커밋 개수
- 현재 브랜치명
- 원격 브랜치명

### 4. 사용자 확인 후 푸시
```bash
git push origin [브랜치명]
```

### 5. 결과 확인
```bash
git status
```

## 출력 형식

### input 폴더 체크 결과
- ✅ input 폴더: 모든 파일 추적 중
- ⚠️ input 폴더: untracked 파일 [N]개 발견 → 커밋 후 push

### 푸시 대상
- **브랜치**: [현재 브랜치] → origin/[원격 브랜치]
- **커밋 수**: [N]개
- **커밋 목록**:
  - [해시] [메시지]
  - ...

### 실행 결과
- 푸시 완료/실패
- GitHub URL: https://github.com/[org]/[repo]
