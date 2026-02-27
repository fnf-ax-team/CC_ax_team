---
name: kpop-sns
description: K-pop 그룹/아티스트의 공식 SNS 계정(Instagram, X, YouTube, TikTok)을 검색하고 정리합니다. "K-pop SNS 찾아줘", "아이돌 공식 계정 검색", "그룹 인스타그램 주소", "공식 트위터 알려줘", "유튜브 채널 찾아줘" 등의 요청 시 사용하세요.
---

# K-pop 공식 SNS 계정 검색 스킬

K-pop 아티스트/그룹의 공식 소셜 미디어 계정을 검색하고, 마크다운 테이블로 정리하며, 지정된 엑셀 파일에 자동으로 추가합니다.

## When to Use This Skill

다음과 같은 요청이 들어올 때 이 스킬을 활성화하세요:

- "RIIZE 공식 계정 알려줘"
- "aespa 인스타 주소 찾아줘"
- "NCT WISH SNS 계정 정리해줘"
- "이 그룹들의 공식 소셜미디어 찾아줘"
- "K-pop 그룹 트위터/유튜브/틱톡 검색"
- "K-pop SNS 검색해서 엑셀에 추가해줘"

## Your Task

1. **Parse the input** - Extract K-pop group/artist names
   - Handle both Korean (한글) and English names
   - Names separated by commas, newlines, or listed separately

2. **Search for official accounts** on these platforms:
   - Instagram (공식 인스타그램)
   - X/Twitter (공식 트위터)
   - YouTube (공식 유튜브 채널)
   - TikTok (공식 틱톡)

3. **Verify accounts** - Ensure URLs are for OFFICIAL accounts
   - Look for "official" in handle names (e.g., @riize_official)
   - Cross-reference with kprofiles.com, Wikipedia, Kpop Wiki Fandom
   - Distinguish from fan accounts

4. **Format results** as markdown tables - One section per group

5. **Save to Excel** - Add results to the designated Excel file (see Excel Integration section)

6. **Save to markdown** - Also create `kpop_groups_official_sns.md` in current directory

## Search Strategy

For each group, use WebSearch with queries like:
- `{그룹명} official Instagram Twitter YouTube TikTok accounts`
- `{그룹명} official SNS accounts 2025`

## Output Format (Markdown)

```markdown
# K-pop 그룹 공식 SNS 계정

검색일: YYYY-MM-DD

---

## 1. 그룹명

| 플랫폼 | 계정 | URL |
|--------|------|-----|
| Instagram | @account | https://www.instagram.com/account/ |
| X (Twitter) | @account | https://x.com/account |
| YouTube | Channel Name | https://www.youtube.com/@channel |
| TikTok | @account | https://www.tiktok.com/@account |
```

## Excel Integration

### Target File
사용자 환경에 맞게 엑셀 파일 경로를 설정하세요.

### Excel Format (Columns B, C, D)

| B (그룹명) | C (플랫폼) | D (URL) |
|-----------|-----------|---------|
| 그룹명 | instagram | https://www.instagram.com/... |
| (빈칸) | x | https://x.com/... |
| (빈칸) | youtube | https://www.youtube.com/... |
| (빈칸) | tiktok | https://www.tiktok.com/... |

**Note**: 그룹명은 첫 번째 행(instagram)에만 입력하고, 나머지 플랫폼 행은 빈칸으로 둡니다.

### Python Code for Excel Update

```python
from openpyxl import load_workbook

file_path = r'엑셀파일경로.xlsx'
wb = load_workbook(file_path)
ws = wb['Sheet1']

# 마지막 행 찾기
last_row = ws.max_row

# 데이터 추가 (예: NewJeans)
data = [
    ['그룹명', 'instagram', 'https://www.instagram.com/...'],
    ['', 'x', 'https://x.com/...'],
    ['', 'youtube', 'https://www.youtube.com/...'],
    ['', 'tiktok', 'https://www.tiktok.com/...'],
]

for i, row_data in enumerate(data):
    row_num = last_row + 1 + i
    ws.cell(row=row_num, column=2, value=row_data[0])  # B열
    ws.cell(row=row_num, column=3, value=row_data[1])  # C열
    ws.cell(row=row_num, column=4, value=row_data[2])  # D열

wb.save(file_path)
```

## Edge Cases

- **계정 없음**: Mark as "N/A" or "공식 계정 없음"
- **일본 계정**: Include both main and JP accounts
- **공유 계정**: Note shared accounts (e.g., NCT subunits)
- **멤버 계정**: Only include GROUP official accounts
- **엑셀 파일 열림**: 파일이 열려있으면 닫고 다시 시도하라고 안내

## After Completion

1. Display all results as formatted markdown tables
2. **Add to Excel file** (해당 시트)
3. Save to `kpop_groups_official_sns.md`
4. Include sources at the bottom
5. Confirm completion: "검색 완료! {N}개 그룹의 공식 SNS 계정을 정리했습니다. 엑셀 파일에 추가되었습니다."
