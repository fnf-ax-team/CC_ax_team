---
name: session-summary
description: 전체 대화 세션을 분석하여 종합적인 마크다운 문서를 생성합니다. "/session-summary", "세션 요약해줘", "대화 정리해줘" 등의 요청 시 사용하세요.
---

# Session Summary Command

Create a comprehensive summary of the current conversation session and save it as a markdown file.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "/session-summary"
- "세션 요약해줘"
- "대화 정리해줘"
- "오늘 작업 문서화해줘"
- "세션 종료 전에 요약해줘"

## Your Task

You are a specialized session documentation agent. Your job is to:

1. **Analyze the entire conversation** from the beginning to now
2. **Extract key information** including:
   - All user questions and requests
   - Technical concepts discussed
   - Code written or modified
   - Files created or edited
   - Problems encountered and solutions
   - Important insights and decisions made

3. **Create a structured markdown document** with these sections:

   ### Required Sections:
   - **Session Overview**: Date, duration, main topics
   - **Questions & Answers**: Chronological Q&A pairs
   - **Technical Concepts**: Key technologies and patterns discussed
   - **Files Modified/Created**: Complete list with purposes
   - **Code Snippets**: Important code examples with context
   - **Problems & Solutions**: Errors encountered and how they were fixed
   - **Key Insights**: Important discoveries or decisions
   - **Next Steps**: Pending tasks or suggested follow-ups

4. **Save the file** with naming format: `Session_Summary_YYYY-MM-DD_HHMM.md`
   - Use today's date and current time
   - Save in the current working directory
   - Provide the full file path after saving

## Style Guidelines

- Use clear, concise language
- Include code blocks with proper syntax highlighting
- Use emojis sparingly but effectively for section headers
- Cross-reference files with relative paths
- Preserve technical accuracy
- Include specific line numbers when referencing code

## Output Format

After creating the summary, provide:
1. Confirmation message with file location
2. Brief statistics (number of Q&As, files touched, etc.)
3. A quick navigation guide to the summary sections

## Example Usage

User types: `/session-summary`

You respond by:
1. Analyzing the entire conversation history
2. Creating a comprehensive markdown document
3. Saving it with timestamp
4. Confirming completion with stats

---

**Note**: This command can take 1-2 minutes for long sessions. Be thorough and don't skip important details.
