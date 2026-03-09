# PR Review Command

Review changes for a pull request.

## Git Repository
This project's git repository is located at `fnf-marketing-dashboard/` directory.
**All git commands must be executed with `-C fnf-marketing-dashboard` option.**

## Target
$ARGUMENTS

Argument should be a branch name, PR number, or file paths to review.

## PR Review Process

### 1. Understand the Changes
- What is the purpose of this PR?
- What files were modified?
- What is the scope of impact?

### 2. Code Quality Check
- [ ] Code follows project conventions
- [ ] No unnecessary complexity
- [ ] Proper error handling
- [ ] No debug code or console.logs left
- [ ] Types are properly defined

### 3. Functionality Review
- [ ] Logic is correct
- [ ] Edge cases are handled
- [ ] No breaking changes (or properly documented)
- [ ] API contracts maintained

### 4. Testing Considerations
- [ ] New code is testable
- [ ] Existing tests still pass
- [ ] Test coverage for new functionality

### 5. Security Check
- [ ] No sensitive data exposure
- [ ] Input validation present
- [ ] No injection vulnerabilities

### 6. Performance Impact
- [ ] No N+1 queries
- [ ] Proper memoization
- [ ] No memory leaks

## Instructions

1. Get the current branch status and changes:
   ```bash
   # View current branch
   git -C fnf-marketing-dashboard branch --show-current

   # View all branches
   git -C fnf-marketing-dashboard branch -a

   # View recent commits
   git -C fnf-marketing-dashboard log --oneline -10

   # Get the diff of changes vs main
   git -C fnf-marketing-dashboard diff main...HEAD

   # Or diff specific branch
   git -C fnf-marketing-dashboard diff main...<branch>

   # View specific commit
   git -C fnf-marketing-dashboard show <commit>
   ```

2. Review each changed file

3. Provide feedback with specific line references

## Output Format

```
## PR Review: [Brief Description]

### Summary
[1-2 sentence summary of changes]

### Changes Reviewed
- file1.ts (+X/-Y lines)
- file2.tsx (+X/-Y lines)

### Approval Status
[ ] Approved
[ ] Approved with suggestions
[ ] Changes requested

### Required Changes
[Must fix before merge]

### Suggestions
[Optional improvements]

### Questions
[Clarifications needed]
```

## Begin PR Review

Analyze the changes and provide comprehensive feedback.
