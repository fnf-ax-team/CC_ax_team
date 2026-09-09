---
name: skill-sync
description: |
  팀 Private GitHub 저장소에서 스킬을 동기화합니다.
  전체 또는 특정 스킬만 선택하여 가져올 수 있습니다.
  "스킬 동기화", "팀 스킬 가져와", "skill sync", "팀 저장소 동기화" 등의 요청 시 사용하세요.
---

# Skill Sync - 팀 저장소 스킬 동기화 (선택적)

팀 Private GitHub 저장소(CC_ax_team)에서 최신 스킬을 가져와 `team/` 폴더에 동기화합니다.
**전체 동기화** 또는 **특정 스킬만 선택**하여 가져올 수 있습니다.
기존 로컬 스킬은 그대로 유지되며, 팀 스킬과 분리 관리됩니다.

## When to Use This Skill

다음과 같은 요청 시 이 스킬을 사용하세요:
- "팀 스킬 동기화해줘"
- "CC_ax_team에서 스킬 가져와"
- "skill sync"
- "팀 저장소 최신 스킬 받아줘"
- "팀 스킬 업데이트해줘"
- "특정 스킬만 가져와줘"

## Configuration

경로는 사용자마다 다르므로 반드시 `$HOME` 기준으로 쓴다 (하드코딩 금지):

```
TEAM_REPO_URL: https://github.com/fnf-ax-team/CC_ax_team.git
SKILLS_BASE_DIR: $HOME/.claude/skills/
TEAM_SKILLS_DIR: $HOME/.claude/skills/team/
TEMP_CLONE_DIR: $HOME/.claude/skills/.team_repo_temp/
CODEX_SKILLS_DIR: $HOME/.codex/skills/          # Codex 사용자만 존재
```

**레포 구조 주의**: 스킬은 두 곳에 있다.
- **레포 루트** (`workstart/`, `workend/`, `log/` 등) — 파트 공용 워크플로 스킬. 엔진 스크립트가 `$HOME/.claude/skills/<스킬명>/...` 절대경로로 서로를 참조하므로 **반드시 루트(`$HOME/.claude/skills/<스킬명>`)에 복사**한다 (team/ 아래에 넣으면 경로가 깨짐)
- **`skills/` 하위폴더** (ceo-ppt 등 개인 제작 스킬 모음) — 기존대로 `team/`에 복사

## Your Task

### Step 1: 팀 저장소 동기화

1. **TEMP_CLONE_DIR 존재 확인**
   ```bash
   # 폴더가 없으면 클론
   if [ ! -d "$HOME/.claude/skills/.team_repo_temp" ]; then
     git clone https://github.com/fnf-ax-team/CC_ax_team.git "$HOME/.claude/skills/.team_repo_temp"
   else
     # 폴더가 있으면 풀
     cd "$HOME/.claude/skills/.team_repo_temp" && git pull
   fi
   ```

2. **Git Credential Manager가 자동으로 인증 처리**
   - Windows Credential Manager에 저장된 GitHub 자격증명 사용
   - 추가 로그인 없이 자동 진행

### Step 2: 스킬 목록 파싱 ⭐

팀 레포에서 사용 가능한 스킬 목록을 조회합니다.

1. **스킬 폴더 목록 조회 — 루트와 skills/ 양쪽 모두**
   ```bash
   # 레포 루트의 워크플로 스킬 (SKILL.md 를 가진 폴더만)
   for d in "$HOME/.claude/skills/.team_repo_temp"/*/; do
     [ -f "$d/SKILL.md" ] && echo "[루트] $(basename "$d")"
   done
   # 개인 제작 스킬 모음
   ls "$HOME/.claude/skills/.team_repo_temp/skills/"
   ```

2. **각 스킬의 설명 추출**
   각 스킬 폴더의 SKILL.md 파일에서 `description` 필드를 읽어 사용자에게 보여줄 정보를 수집합니다.

   ```bash
   # 예시: 스킬별 설명 추출
   for skill_dir in $HOME/.claude/skills/.team_repo_temp/skills/*/; do
     skill_name=$(basename "$skill_dir")
     echo "- $skill_name"
   done
   ```

3. **스킬 목록 정리**
   파싱된 정보를 테이블 형식으로 정리:

   | 스킬명 | 설명 |
   |--------|------|
   | ceo-ppt | 회장님 보고용 PPT 자동 생성 |
   | kpop-sns | K-pop SNS 계정 검색 |
   | llm-api-docs | LLM API 문서 수집 |
   | session-summary | 세션 요약 생성 |
   | skill-push | 스킬 GitHub 푸시 |
   | skill-sync | 팀 스킬 동기화 |

### Step 3: 사용자 선택 요청 ⭐

**AskUserQuestion** 도구를 사용하여 사용자에게 동기화할 스킬을 선택받습니다.

**중요**: 반드시 `AskUserQuestion` 도구를 호출하여 사용자의 선택을 받아야 합니다.

```
질문: "어떤 스킬을 동기화할까요?"
헤더: "스킬 선택"
멀티셀렉트: true (여러 스킬 선택 가능)

옵션:
1. "전체 동기화 (Recommended)" - 팀 레포의 모든 스킬을 가져옵니다
2. "ceo-ppt" - 회장님 보고용 PPT
3. "kpop-sns" - K-pop SNS 검색
4. "llm-api-docs" - LLM API 문서 수집
5. "session-summary" - 세션 요약 생성
6. "skill-push" - 스킬 GitHub 푸시
7. "skill-sync" - 팀 스킬 동기화
```

**AskUserQuestion 도구 호출 예시:**
```json
{
  "questions": [{
    "question": "어떤 스킬을 동기화할까요?",
    "header": "스킬 선택",
    "multiSelect": true,
    "options": [
      {"label": "전체 동기화 (Recommended)", "description": "팀 레포의 모든 스킬을 가져옵니다"},
      {"label": "ceo-ppt", "description": "회장님 보고용 PPT"},
      {"label": "kpop-sns", "description": "K-pop SNS 검색"},
      {"label": "llm-api-docs", "description": "LLM API 문서 수집"},
      {"label": "session-summary", "description": "세션 요약 생성"},
      {"label": "skill-push", "description": "스킬 GitHub 푸시"},
      {"label": "skill-sync", "description": "팀 스킬 동기화"}
    ]
  }]
}
```

### Step 4: 선택된 스킬 복사

사용자의 선택에 따라 스킬을 복사합니다.

1. **team/ 폴더 생성 확인**
   ```bash
   mkdir -p "$HOME/.claude/skills/team/"
   ```

2. **선택에 따른 복사 실행 — 출처에 따라 목적지가 다르다**

   **레포 루트 스킬 (workstart·workend·log 등) → 루트로:**
   ```bash
   for s in workstart workend log; do
     cp -r "$HOME/.claude/skills/.team_repo_temp/$s/." "$HOME/.claude/skills/$s/"
   done
   ```
   (`.env`·캐시 파일은 gitignore 라 레포에 없음 — 기존 본인 설정은 안 덮인다)

   **skills/ 하위 스킬 (ceo-ppt 등) → team/ 으로:**
   ```bash
   cp -r "$HOME/.claude/skills/.team_repo_temp/skills/ceo-ppt" "$HOME/.claude/skills/team/"
   ```
   "전체 동기화" 선택 시 양쪽 모두 실행.

3. **Codex 복사 (Codex 사용자만 — `~/.codex` 폴더가 있을 때)**

   동기화한 스킬 중 `codex/SKILL.md` 가 있는 스킬은 Codex 쪽에도 반영한다.
   `~/.codex` 가 없으면(Codex 미사용) 조용히 건너뛴다:
   ```bash
   if [ -d "$HOME/.codex" ]; then
     mkdir -p "$HOME/.codex/skills"
     for d in "$HOME/.claude/skills/.team_repo_temp"/*/codex/; do
       s=$(basename "$(dirname "$d")")
       mkdir -p "$HOME/.codex/skills/$s"
       cp "$d/SKILL.md" "$HOME/.codex/skills/$s/SKILL.md"
       echo "codex 반영: $s"
     done
   fi
   ```
   (Codex용 SKILL.md 도 엔진 스크립트는 `$HOME/.claude/skills/` 쪽 것을 호출하므로
   루트 복사가 선행돼야 한다)

4. **복사 결과 확인**
   ```bash
   ls -la "$HOME/.claude/skills/team/"
   ```

### Step 5: 결과 리포트 출력

다음 형식으로 결과를 사용자에게 보고:

```markdown
## ✅ 팀 스킬 동기화 완료

- **동기화 일시**: YYYY-MM-DD HH:MM:SS
- **저장소**: CC_ax_team (Private)
- **브랜치**: main
- **동기화 모드**: 전체 / 선택적 (선택한 스킬 수)

### 동기화된 스킬
| 스킬 | 상태 | 설명 |
|------|------|------|
| ceo-ppt | ✅ 동기화됨 | 회장님 보고용 PPT |
| kpop-sns | ✅ 동기화됨 | K-pop SNS 검색 |
| ... | ... | ... |

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
- 저장소 URL 확인: https://github.com/fnf-ax-team/CC_ax_team
- 저장소 접근 권한 확인
```

## Important Notes

1. **개인 스킬은 절대 덮어쓰지 않음**
   - 본인이 직접 만든(레포에 없는) 스킬 폴더는 어떤 경우에도 건드리지 않는다
   - 루트로 덮어쓰는 것은 **레포 루트에 있는 파트 공용 스킬**(workstart·workend·log 등)뿐
   - 본인 설정(`.env`)·캐시는 레포에 없으므로 루트 덮어쓰기에도 보존된다
   - skills/ 하위의 개인 제작 스킬 모음은 항상 `team/` 폴더에만 저장

2. **충돌 없음**
   - 같은 이름의 스킬이 루트와 team/에 동시에 존재 가능
   - 루트 스킬이 우선, `team:` 접두사로 팀 버전 호출

3. **자동 인증**
   - Git Credential Manager가 설정되어 있으면 추가 인증 없이 진행
   - Private 저장소도 자동 접근 가능

4. **선택적 동기화** ⭐
   - 전체 동기화 또는 특정 스킬만 선택 가능
   - 사용자가 명시적으로 선택해야 복사 진행
   - "Other" 옵션으로 직접 스킬명 입력도 가능
