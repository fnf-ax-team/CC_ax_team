---
name: create-index
description: 세션 중 생성된 모든 문서/스크립트의 네비게이션 인덱스를 생성합니다. "/create-index", "인덱스 만들어줘", "파일 목록 정리해줘" 등의 요청 시 사용하세요.
---

# Create Index Command

Generate a navigation index file for all documentation created during the session.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "/create-index"
- "인덱스 만들어줘"
- "파일 목록 정리해줘"
- "네비게이션 가이드 생성"
- "프로젝트 인덱스 만들어줘"

## Your Task

Create a master index file that helps users navigate all documents, scripts, and resources created.

## Structure

1. **Overview Section**
   - Session date and duration
   - Main achievements
   - Quick links to important files

2. **Documentation Inventory**
   - List all .md files created
   - Brief description of each
   - Recommended reading order

3. **Scripts & Utilities**
   - List all .py/.sh/.js files created
   - Purpose of each
   - Usage examples with commands

4. **Quick Start Guides**
   - "If you want to X, start with Y"
   - Different paths for different user goals

5. **Project Structure Diagram**
   - ASCII tree showing file organization
   - Annotations for important directories

6. **External Resources**
   - Links to related documentation
   - Relevant GitHub repos
   - Tutorial references

## File Naming

Save as: `SESSION_INDEX.md` or `PROJECT_INDEX.md` depending on scope.

## Special Features

- Use emoji for visual navigation (📚 📁 🛠️ 🎯)
- Include "Jump to" links for long sections
- Provide command examples that can be copy-pasted
- Add "Last Updated" timestamp

## Example Output

```markdown
# Project Session Index

📅 **Date**: 2025-10-14
⏱️ **Duration**: 3 hours
🎯 **Focus**: Knowledge Graph Setup & Documentation

---

## 📚 Quick Navigation

| Goal | Start Here |
|------|------------|
| Learn graph basics | → `graph_basics_tutorial.md` |
| Set up project | → `SETUP_GUIDE.md` |
| Understand design | → `QA_Session_2025-10-14.md` |

[Continue with detailed sections...]
```

Make it serve as both an index and a README for the session's output.
