---
name: code-summary
description: 세션 중 작성/수정된 코드 변경 사항을 집중적으로 정리합니다. "/code-summary", "코드 변경 요약", "코드 정리해줘" 등의 요청 시 사용하세요.
---

# Code Summary Command

Create a focused summary of all code written or modified during this session.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "/code-summary"
- "코드 변경 요약해줘"
- "코드 정리해줘"
- "작성한 코드 문서화해줘"
- "코드 리뷰 준비해줘"

## Your Task

Extract and document all code changes made during the conversation.

## Required Sections

### 1. Files Created
List each new file with:
- Full path
- Purpose
- Key functions/classes
- Dependencies

### 2. Files Modified
For each modified file:
- What changed (specific functions/sections)
- Why it was changed
- Before/after comparison (if significant)

### 3. Code Patterns Used
- Design patterns implemented
- Notable algorithms
- Best practices applied

### 4. Testing & Verification
- Commands run to test code
- Verification scripts created
- Test results

### 5. Dependencies Added
- New packages installed
- Version requirements
- Configuration changes

## Output Format

Save as: `Code_Summary_YYYY-MM-DD.md` in the current directory.

Include executable commands in code blocks so the summary serves as both documentation and runbook.

## Example Section

```markdown
## Files Created

### `src/graph_analyzer.py`
**Purpose**: Analyze Neo4j graph structure and generate statistics

**Key Functions**:
- `analyze_hierarchy()` - Calculates depth and branching
- `count_relationships()` - Relationship type statistics

**Dependencies**:
```python
from neo4j import GraphDatabase
from utils.database import Neo4jDB
```

**Usage**:
```bash
python src/graph_analyzer.py
```
```

Be comprehensive but concise. Focus on "what" and "why", not just "what".
