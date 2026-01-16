---
name: skill-sync
description: |
  팀 Private GitHub 저장소에서 스킬을 동기화합니다.
  "스킬 동기화", "팀 스킬 가져와", "skill sync", "팀 저장소 동기화" 등의 요청 시 사용하세요.
---

# Skill Sync - 팀 저장소 스킬 동기화

팀 Private GitHub 저장소(CC_ax_team)에서 최신 스킬을 가져와 `team/` 폴더에 동기화합니다.
기존 로컬 스킬은 그대로 유지되며, 팀 스킬과 분리 관리됩니다.

## When to Use This Skill

다음과 같은 요청 시 이 스킬을 사용하세요:
- "팀 스킬 동기화해줘"
- "CC_ax_team에서 스킬 가져와"
- "skill sync"
- "팀 저장소 최신 스킬 받아줘"
- "팀 스킬 업데이트해줘"

## Configuration

```
TEAM_REPO_URL: https://github.com/davidcho0326/CC_ax_team.git
SKILLS_BASE_DIR: C:/Users/AC1059/.claude/skills/
TEAM_SKILLS_DIR: C:/Users/AC1059/.claude/skills/team/
TEMP_CLONE_DIR: C:/Users/AC1059/.claude/skills/.team_repo_temp/
```

## Your Task

### Step 1: 팀 저장소 동기화

1. **TEMP_CLONE_DIR 존재 확인**
   ```bash
   # 폴더가 없으면 클론
   if [ ! -d "C:/Users/AC1059/.claude/skills/.team_repo_temp" ]; then
     git clone https://github.com/davidcho0326/CC_ax_team.git "C:/Users/AC1059/.claude/skills/.team_repo_temp"
   else
     # 폴더가 있으면 풀
     cd "C:/Users/AC1059/.claude/skills/.team_repo_temp" && git pull
   fi
   ```

2. **Git Credential Manager가 자동으로 인증 처리**
   - Windows Credential Manager에 저장된 GitHub 자격증명 사용
   - 추가 로그인 없이 자동 진행

### Step 2: 스킬 복사

1. **기존 team/ 폴더 확인**
   - team/ 폴더에 기존 스킬이 있으면 백업 생성 (선택적)

2. **스킬 복사 실행**
   ```bash
   # .team_repo_temp/skills/ 내용을 team/ 폴더로 복사
   cp -r "C:/Users/AC1059/.claude/skills/.team_repo_temp/skills/"* "C:/Users/AC1059/.claude/skills/team/"
   ```

3. **복사된 스킬 목록 확인**
   ```bash
   ls -la "C:/Users/AC1059/.claude/skills/team/"
   ```

### Step 3: 변경 사항 분석

다음 정보를 수집하여 리포트 생성:

1. **새로 추가된 스킬**: team/에 새로 생긴 폴더
2. **업데이트된 스킬**: 기존 대비 변경된 파일
3. **변경 없는 스킬**: 동일한 상태 유지

### Step 4: 결과 리포트 출력

다음 형식으로 결과를 사용자에게 보고:

```markdown
## 팀 스킬 동기화 완료

- **동기화 일시**: YYYY-MM-DD HH:MM:SS
- **저장소**: CC_ax_team (Private)
- **브랜치**: main

### 변경 사항
| 스킬 | 상태 | 설명 |
|------|------|------|
| session-summary | 🆕 새로 추가 | 세션 요약 생성 스킬 |
| ceo-ppt | 🔄 업데이트 | SKILL.md 변경됨 |
| kpop-sns | ✅ 변경 없음 | - |

### 디렉토리 구조
- **로컬 스킬**: ~/.claude/skills/ (루트)
- **팀 스킬**: ~/.claude/skills/team/

### 스킬 호출 방법
- 로컬 스킬: `/ceo-ppt` 또는 "PPT 만들어"
- 팀 스킬: `/team:ceo-ppt` 또는 "팀 ceo-ppt로 PPT 만들어"
```

## Error Handling

### 인증 실패
```
Git 인증에 실패했습니다.
해결 방법:
1. Windows 자격 증명 관리자에서 GitHub 항목 확인
2. `git credential-manager` 설정 확인
3. GitHub 토큰 만료 여부 확인
```

### 네트워크 오류
```
네트워크 연결에 실패했습니다.
- 인터넷 연결 상태 확인
- VPN 연결 상태 확인 (회사 네트워크인 경우)
```

### 저장소 없음
```
저장소를 찾을 수 없습니다.
- 저장소 URL 확인: https://github.com/davidcho0326/CC_ax_team
- 저장소 접근 권한 확인
```

## Important Notes

1. **로컬 스킬은 절대 덮어쓰지 않음**
   - 루트 폴더의 기존 스킬은 그대로 유지
   - 팀 스킬은 항상 `team/` 폴더에만 저장

2. **충돌 없음**
   - 같은 이름의 스킬이 루트와 team/에 동시에 존재 가능
   - 루트 스킬이 우선, `team:` 접두사로 팀 버전 호출

3. **자동 인증**
   - Git Credential Manager가 설정되어 있으면 추가 인증 없이 진행
   - Private 저장소도 자동 접근 가능
