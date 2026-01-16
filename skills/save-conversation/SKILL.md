---
name: save-conversation
description: 원본 대화 내역을 가공 없이 마크다운 파일로 저장합니다. "/save-conversation", "대화 저장해줘", "대화 백업" 등의 요청 시 사용하세요.
---

# Save Conversation Command

Export the raw conversation history as a markdown file for archival purposes.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "/save-conversation"
- "대화 저장해줘"
- "대화 백업해줘"
- "원본 대화 내보내기"
- "트랜스크립트 저장"

## Your Task

Create a simple, chronological transcript of the entire conversation with minimal formatting.

## Format

```markdown
# Conversation Log - [Date] [Time]

## Message 1 - User
[User message content]

## Message 2 - Assistant
[Assistant response content]

## Message 3 - User
[User message content]

...

---
Total Messages: X
Started: [Timestamp]
Ended: [Timestamp]
```

## File Naming

Save as: `Conversation_Log_YYYY-MM-DD_HHMM.md`

## Purpose

This is a raw backup, different from `/session-summary` which provides analysis and structure. This is just the transcript.

Use this when you want a complete, unedited record of everything said.
