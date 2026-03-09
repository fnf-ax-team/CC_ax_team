---
name: skill-push
description: |
  스킬 폴더의 변경사항을 GitHub에 푸시합니다.
  "스킬 푸시", "skill push", "스킬 업데이트", "스킬 커밋" 등의 요청 시 사용하세요.
---

# 스킬 GitHub 푸시 스킬

현재 스킬 폴더의 변경사항을 GitHub 저장소에 푸시하고, README.md도 자동으로 업데이트합니다.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "스킬 업데이트해줘"
- "스킬 푸시해줘"
- "스킬 깃허브에 올려줘"
- "스킬 커밋해줘"
- "skill push"

## Your Task

1. OS 확인 (macOS vs Windows)
2. 스킬 폴더의 현재 상태 확인
3. **README.md 자동 업데이트** (스킬 목록 및 사용법 갱신)
4. 변경사항이 있으면 커밋 & 푸시
5. 결과 보고

## Commands to Execute

### 0단계: OS 및 스킬 폴더 경로 확인

**macOS/Linux:**
```bash
# 스킬 폴더 경로
SKILLS_DIR="$HOME/.claude/skills"
echo "Skills directory: $SKILLS_DIR"
```

**Windows (PowerShell):**
```powershell
$SKILLS_DIR = "$env:USERPROFILE\.claude\skills"
Write-Host "Skills directory: $SKILLS_DIR"
```

### 1단계: 스킬 폴더 목록 확인

**macOS/Linux:**
```bash
ls -d ~/.claude/skills/*/ 2>/dev/null | xargs -I {} basename {}
```

**Windows (PowerShell):**
```powershell
Get-ChildItem "$env:USERPROFILE\.claude\skills" -Directory | Select-Object -ExpandProperty Name
```

### 2단계: README.md 업데이트

스킬 폴더를 스캔하여 README.md의 스킬 목록 테이블과 사용법 섹션을 자동으로 업데이트합니다.

**README.md 스킬 목록 테이블 형식:**

```markdown
## 스킬 목록

| 스킬명 | 설명 |
|--------|------|
| kpop-sns | K-pop 그룹 공식 SNS 계정 검색 & 엑셀 저장 |
| skill-push | 스킬 변경사항 GitHub 푸시 & README 자동 업데이트 |
```

**각 스킬의 사용법 섹션도 추가:**

```markdown
## 스킬 사용법

### 스킬명
스킬 설명 (SKILL.md 첫 문단에서 추출)

**사용 예시:**
- "트리거 문구 1"
- "트리거 문구 2"
```

각 스킬 폴더의 SKILL.md 파일을 읽어서:
- 첫 번째 문단 → 스킬 설명
- "When to Use This Skill" 섹션의 트리거 문구 → 사용 예시

### 3단계: Git 상태 확인

**macOS/Linux:**
```bash
cd ~/.claude/skills && git status
```

**Windows (PowerShell):**
```powershell
cd "$env:USERPROFILE\.claude\skills"; git status
```

### 4단계: 변경사항 커밋 & 푸시

**macOS/Linux:**
```bash
cd ~/.claude/skills && git add . && git commit -m "커밋메시지" && git push
```

**Windows (PowerShell):**
```powershell
cd "$env:USERPROFILE\.claude\skills"; git add .; git commit -m "커밋메시지"; git push
```

## 인증 문제 해결

### macOS에서 push 실패 시

1. **HTTPS URL + PAT 사용:**
```bash
# remote URL에 토큰 포함 (일회성)
git push https://USERNAME:TOKEN@github.com/ORG/REPO.git main

# 또는 credential helper 설정
git config --global credential.helper osxkeychain
```

2. **SSH 사용 (권장):**
```bash
# SSH 키 생성
ssh-keygen -t ed25519 -C "your_email@example.com"

# GitHub에 공개키 등록 후 remote 변경
git remote set-url origin git@github.com:ORG/REPO.git
```

### Windows에서 push 실패 시

1. **Git Credential Manager 사용:**
```powershell
git config --global credential.helper manager
```

2. **PAT 직접 입력:**
```powershell
git push https://USERNAME:TOKEN@github.com/ORG/REPO.git main
```

## Commit Message Guidelines

커밋 메시지는 변경 내용에 맞게 자동 생성:

- 새 스킬 추가: `Add new skill: 스킬명`
- 스킬 수정: `Update 스킬명 skill`
- README 수정: `Update README`
- 여러 변경: `Update skills`

## Output Format

```
스킬 GitHub 푸시 완료!

커밋 메시지: {커밋 메시지}
변경된 파일: {파일 목록}
저장소: https://github.com/{username}/{repo}
```

## Edge Cases

- **변경사항 없음**: "변경사항이 없습니다. 이미 최신 상태입니다." 출력
- **푸시 실패**: 에러 메시지 표시 및 해결 방법 안내 (위 인증 문제 해결 섹션 참고)
- **Git 미설치**: "git이 설치되어 있지 않습니다. 먼저 git을 설치해주세요." 출력
