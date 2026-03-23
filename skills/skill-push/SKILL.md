---
name: skill-push
description: |
  로컬 스킬을 선택적으로 팀 GitHub 레포에 푸시합니다.
  프로젝트(스킬 폴더) 단위로 유저가 선택하여 세밀하게 커밋합니다.
  "스킬 푸시", "skill push", "스킬 업데이트", "스킬 커밋" 등의 요청 시 사용하세요.
---

# 스킬 선택적 GitHub 푸시

로컬 스킬 폴더에서 **유저가 선택한 프로젝트(스킬)만** 팀 GitHub 레포에 푸시합니다.
전체를 무차별 커밋하지 않고, 프로젝트 단위로 세밀하게 관리합니다.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:
- "스킬 업데이트해줘"
- "스킬 푸시해줘"
- "스킬 깃허브에 올려줘"
- "스킬 커밋해줘"
- "skill push"

## Configuration

- **로컬 스킬 폴더**: `C:\Users\AC1059\.claude\skills\`
- **팀 GitHub 레포**: `https://github.com/fnf-ax-team/CC_ax_team`
- **레포 내 스킬 경로**: `skills/`
- **기본 브랜치**: `main`

## Your Task

### 1단계: 로컬 스킬 현황 스캔

로컬 스킬 폴더를 스캔하여 각 스킬의 상태를 파악합니다.

```bash
ls -d C:/Users/AC1059/.claude/skills/*/ | xargs -I {} basename {}
```

다음 폴더는 **제외**합니다 (메타/내부용):
- `team/` (팀 동기화용 임시 폴더)
- `.team_repo_temp/` (동기화 캐시)
- `study/` (개인 학습용)

### 2단계: 원격 레포 현황 비교

팀 레포의 현재 `skills/` 폴더와 로컬을 비교합니다.

```bash
# 원격 레포의 스킬 목록 확인
gh api repos/fnf-ax-team/CC_ax_team/git/trees/main?recursive=1 \
  --jq '.tree[] | select(.type=="tree") | .path' | grep -E "^skills/[^/]+$"
```

각 스킬을 다음 3가지로 분류하여 유저에게 표시:

| 상태 | 설명 |
|------|------|
| NEW | 로컬에만 있고 원격에 없음 (신규 스킬) |
| MODIFIED | 양쪽 다 있지만 내용이 다름 (업데이트) |
| UNCHANGED | 양쪽 동일 (변경 없음) |

### 3단계: 유저에게 선택 요청 (핵심!)

**반드시 유저에게 질문하여 어떤 스킬을 푸시할지 확인합니다.**

다음 형식으로 표시:

```
팀 레포 스킬 푸시 현황:

[NEW]      data-integrity-test  - 대시보드 데이터 정합성 검증
[NEW]      instagram-dm         - 인스타그램 DM 확인/답변
[MODIFIED] kpop-sns             - K-pop 공식 SNS 검색 (SKILL.md 변경)
[MODIFIED] skill-push           - 스킬 푸시 (SKILL.md 변경)
[UNCHANGED] ceo-ppt             - (변경 없음)
[UNCHANGED] llm-api-docs        - (변경 없음)

어떤 스킬을 푸시할까요?
- 번호 또는 스킬명으로 선택 (예: "1,3", "kpop-sns", "전부")
- "전부" 입력 시 NEW + MODIFIED 전체 푸시
```

### 4단계: 선택된 스킬만 정밀 푸시

선택된 스킬만 레포에 반영합니다.

#### 4-1. 임시 작업 디렉토리 준비

```bash
# 레포를 shallow clone
git clone --depth 1 https://github.com/fnf-ax-team/CC_ax_team.git /tmp/CC_ax_team_push
```

#### 4-2. 선택된 스킬 폴더만 복사

```bash
# 예: kpop-sns만 선택한 경우
cp -r C:/Users/AC1059/.claude/skills/kpop-sns/ /tmp/CC_ax_team_push/skills/kpop-sns/
```

- NEW 스킬: 새 폴더 생성
- MODIFIED 스킬: 기존 폴더를 삭제 후 새로 복사 (깔끔한 교체)

#### 4-3. 커밋 메시지 자동 생성

변경 내용에 맞게 커밋 메시지를 생성합니다:

| 상황 | 커밋 메시지 형식 |
|------|-----------------|
| 신규 1개 | `feat: add 스킬명 skill` |
| 수정 1개 | `update: 스킬명 skill` |
| 여러 개 | `update: 스킬1, 스킬2 skills` |

#### 4-4. 커밋 & 푸시

```bash
cd /tmp/CC_ax_team_push
git add skills/선택된스킬/
git commit -m "커밋메시지"
git push origin main
```

**주의**: `git add`는 반드시 선택된 스킬 폴더 경로만 지정합니다. 절대 `git add .` 사용 금지!

#### 4-5. 정리

```bash
rm -rf /tmp/CC_ax_team_push
```

### 5단계: README.md 업데이트 (선택사항)

NEW 스킬이 추가된 경우에만 README.md의 스킬 목록 테이블을 업데이트합니다.
유저에게 "README도 업데이트할까요?" 확인 후 진행합니다.

## Output Format

```
스킬 푸시 완료!

푸시된 스킬:
  - kpop-sns (MODIFIED)
  - data-integrity-test (NEW)

커밋: abc1234 - "update: kpop-sns, data-integrity-test skills"
레포: https://github.com/fnf-ax-team/CC_ax_team
```

## Edge Cases

- **변경사항 없음**: "모든 스킬이 최신 상태입니다." 출력
- **푸시 실패**: 에러 메시지 표시 + `gh auth status` 확인 안내
- **충돌 발생**: 원격에 먼저 변경이 있으면 pull 후 재시도
- **gh CLI 미인증**: `gh auth login` 안내
