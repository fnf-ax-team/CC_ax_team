# 🚀 AX팀 Claude Code 스킬 공유 레포지토리

> **AX팀 전용** Claude Code 커스텀 스킬 모음집입니다. 팀원들이 자유롭게 스킬을 추가/수정하고 공유할 수 있습니다.

---

## ⭐ 핵심 기능: 스킬 푸시 (skill-push)

> **스킬 수정 후 GitHub 업데이트가 필요할 때, 아래 명령 하나로 끝!**

```
"스킬 업데이트해줘" 또는 "스킬 푸시해줘"
```

### skill-push 스킬이란?

| 기능 | 설명 |
|------|------|
| 📝 **자동 커밋** | 변경된 스킬 파일들을 자동으로 커밋 |
| 📤 **GitHub 푸시** | 한 번에 원격 저장소에 푸시 |
| 📋 **README 자동 업데이트** | 스킬 목록과 사용법을 자동으로 갱신 |

### 사용 방법

1. 스킬 파일(.md)을 수정하거나 새로 만듭니다
2. Claude Code에서 **"스킬 푸시해줘"** 라고 요청합니다
3. 자동으로 커밋 & 푸시 완료!

```
✅ 스킬 GitHub 푸시 완료!

📝 커밋 메시지: Update kpop-sns skill
📁 변경된 파일: skills/kpop-sns/SKILL.md
🔗 저장소: https://github.com/davidcho0326/CC_ax_team
```

---

## 📁 스킬 목록

| 카테고리 | 스킬명 | 설명 |
|----------|--------|------|
| 🔧 **관리** | **skill-push** | 스킬 변경사항 GitHub 푸시 & README 자동 업데이트 |
| 🎵 **K-pop** | kpop-sns | K-pop 그룹 공식 SNS 계정 검색 & 엑셀 저장 |
| 📚 **문서** | llm-api-docs | LLM API 공식 문서 수집 (Playwright MCP) |
| 📋 **세션 관리** | session-summary | 종합 세션 요약 문서 생성 |
| ⚡ **세션 관리** | quick-recap | 빠른 진행 상황 요약 (파일 생성 없음) |
| 💾 **세션 관리** | save-conversation | 원본 대화 내역 저장 |
| 💻 **세션 관리** | code-summary | 코드 변경 사항 집중 정리 |
| 🗂️ **세션 관리** | create-index | 세션 문서 네비게이션 인덱스 생성 |

---

## 📥 설치 방법

### 1. 레포지토리 클론

```bash
# Windows
cd C:\Users\{사용자명}\.claude
git clone https://github.com/davidcho0326/CC_ax_team.git skills

# Mac/Linux
cd ~/.claude
git clone https://github.com/davidcho0326/CC_ax_team.git skills
```

### 2. 기존 스킬 폴더가 있는 경우

```bash
# 기존 폴더 백업
mv skills skills_backup

# 새로 클론
git clone https://github.com/davidcho0326/CC_ax_team.git skills

# 필요한 기존 스킬 복사
cp -r skills_backup/* skills/
```

### 3. Claude Code 재시작

VSCode에서 `Ctrl+Shift+P` → "Developer: Reload Window"

---

## 📝 스킬 사용법

### 🔧 skill-push
스킬 변경사항을 GitHub에 푸시하고 README를 자동 업데이트합니다.

**사용 예시:**
- "스킬 업데이트해줘"
- "스킬 푸시해줘"
- "스킬 깃허브에 올려줘"

---

### 🎵 kpop-sns
K-pop 아티스트/그룹의 공식 SNS 계정을 검색하고 엑셀에 저장합니다.

**사용 예시:**
- "BTS 공식 계정 알려줘"
- "aespa 인스타 주소 찾아줘"
- "NewJeans SNS 계정 정리해줘"

---

### 📚 llm-api-docs
LLM API 공식 문서를 Playwright MCP로 수집합니다.

**사용 예시:**
- "Gemini API 문서 가져와줘"
- "Claude 최신 모델 정보 알려줘"
- "Grok API 가격 정리해줘"

**필수 요구사항:** Playwright MCP 설치 필요 (스킬 실행 시 자동 안내)

---

### 📋 session-summary
전체 대화 세션을 분석하여 상세한 마크다운 문서를 생성합니다.

**사용 예시:**
- "/session-summary"
- "세션 요약해줘"
- "대화 정리해줘"

---

### ⚡ quick-recap
현재 진행 상황을 빠르게 요약합니다 (파일 생성 없음).

**사용 예시:**
- "/quick-recap"
- "빠른 요약"
- "지금까지 뭐했지?"

---

### 💾 save-conversation
원본 대화 내역을 가공 없이 저장합니다.

**사용 예시:**
- "/save-conversation"
- "대화 저장해줘"
- "대화 백업해줘"

---

### 💻 code-summary
세션 중 작성/수정된 코드를 집중적으로 정리합니다.

**사용 예시:**
- "/code-summary"
- "코드 변경 요약해줘"
- "코드 정리해줘"

---

### 🗂️ create-index
세션에서 생성된 모든 문서의 네비게이션 인덱스를 만듭니다.

**사용 예시:**
- "/create-index"
- "인덱스 만들어줘"
- "파일 목록 정리해줘"

---

## 🔧 스킬 수정/추가 방법

### 1. 새 스킬 추가

```bash
# 새 스킬 폴더 생성
mkdir skills/새스킬명

# SKILL.md 파일 생성 (아래 템플릿 참고)
```

### 2. SKILL.md 템플릿

```markdown
---
name: 스킬-이름
description: 스킬에 대한 간단한 설명. 트리거 문구 예시를 포함하세요.
---

# 스킬 제목

스킬에 대한 상세 설명

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "트리거 문구 1"
- "트리거 문구 2"

## Your Task

1. 첫 번째 할 일
2. 두 번째 할 일
3. ...

## Output Format

출력 형식 설명

## Edge Cases

예외 상황 처리 방법
```

### 3. GitHub에 반영

```
"스킬 푸시해줘"
```

---

## 👥 팀 기여 가이드

1. **스킬 추가 시**: 팀원들에게 유용한 스킬인지 고려
2. **스킬 수정 시**: 기존 기능 호환성 유지
3. **커밋 메시지**: 명확하게 변경 내용 기술
4. **테스트**: 스킬 추가/수정 후 직접 테스트 필수

---

## 📂 폴더 구조

```
CC_ax_team/
├── README.md                    # 이 파일
├── skills/
│   ├── skill-push/
│   │   └── SKILL.md            # 스킬 푸시 스킬
│   ├── kpop-sns/
│   │   └── SKILL.md            # K-pop SNS 검색
│   ├── llm-api-docs/
│   │   └── SKILL.md            # LLM API 문서 수집
│   ├── session-summary/
│   │   └── SKILL.md            # 세션 요약
│   ├── quick-recap/
│   │   └── SKILL.md            # 빠른 요약
│   ├── save-conversation/
│   │   └── SKILL.md            # 대화 저장
│   ├── code-summary/
│   │   └── SKILL.md            # 코드 요약
│   └── create-index/
│       └── SKILL.md            # 인덱스 생성
```

---

## ⚠️ 주의사항

- 스킬 파일 경로에 **한글 폴더명**이 있으면 문제가 발생할 수 있음
- Playwright MCP가 필요한 스킬은 사전 설치 필요
- 엑셀 파일 수정 스킬은 **파일이 닫혀있어야** 정상 작동

---

## 📞 문의

스킬 관련 문의나 제안은 AX팀 Slack 채널에서!

---

**Made with ❤️ by AX Team**

_Last Updated: 2026-01-16_
