---
name: quick-recap
description: 현재 세션의 빠른 요약을 화면에 출력합니다 (파일 생성 없음). "/quick-recap", "빠른 요약", "지금까지 뭐했지?" 등의 요청 시 사용하세요.
---

# Quick Recap Command

Provide a brief, bullet-point summary of the current session without creating a file.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "/quick-recap"
- "빠른 요약"
- "지금까지 뭐했지?"
- "현재 상태 알려줘"
- "진행 상황 정리해줘"

## Your Task

Generate a concise summary of the conversation so far, focusing on:

1. **Main Topics** (3-5 bullet points)
2. **Files Changed** (list with brief descriptions)
3. **Key Decisions** (important choices made)
4. **Current Status** (what's working, what's pending)

## Output Format

```
📋 Quick Session Recap
━━━━━━━━━━━━━━━━━━━━━━

🎯 Main Topics:
   • Topic 1
   • Topic 2
   • Topic 3

📁 Files Modified/Created:
   • file1.py - Description
   • file2.md - Description

💡 Key Decisions:
   • Decision 1
   • Decision 2

✅ Current Status:
   • What's working
   • What's pending

⏱️ Session Duration: ~X minutes
```

Keep it under 20 lines. This is for quick reference, not comprehensive documentation.
