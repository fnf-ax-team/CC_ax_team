---
name: autoskill
description: |
  노션 DB에서 새로운 스킬 입력(Status=new URL)을 확인하고 autoskill 파이프라인을 실행합니다.
  "신규 스킬 확인", "새 스킬 있어?", "autoskill 실행", "autoskill 돌려줘" 등의 요청 시 사용하세요.
disable-model-invocation: true
allowed-tools: Bash(python*), Bash(cd*), Bash(tail*), Read
---

# Autoskill 파이프라인 트리거

노션 DB에서 새로운 URL 입력을 확인하고, 자동 스킬 생성 파이프라인을 실행합니다.

## 프로젝트 위치

```
/Users/chohansol/cursor/autoskill/
```

## 실행 순서

### Step 1: 상태 확인

먼저 노션 DB의 현재 상태를 확인합니다:

```bash
cd /Users/chohansol/cursor/autoskill && python3 check_status.py
```

출력 예시:
```
=== Autoskill 파이프라인 상태 ===
  new      : 3개 (대기 중)
  analyzing: 0개
  matched  : 5개
  done     : 12개
  error    : 0개

새 입력 URL:
  - https://example.com/article1
  - https://example.com/article2
```

### Step 2: 파이프라인 실행

**새 입력(Status=new)이 있는 경우에만** 파이프라인을 실행합니다:

```bash
cd /Users/chohansol/cursor/autoskill && python3 pipeline.py
```

파이프라인 처리 단계:
1. URL 콘텐츠 추출 (Trafilatura/Jina Reader)
2. Claude로 스킬 생성
3. 주간회의록에서 관련 태스크 매칭
4. 완료 처리 (Status: new → analyzing → matched → done)

### Step 3: 결과 확인

파이프라인 실행 후 로그를 확인합니다:

```bash
tail -30 /Users/chohansol/cursor/autoskill/pipeline.log
```

## 결과 보고 형식

처리 완료 후 다음 형식으로 사용자에게 보고하세요:

```markdown
## Autoskill 파이프라인 실행 결과

### 처리 현황
- 처리된 URL: X개
- 성공: X개
- 실패: X개

### 생성된 스킬 요약
[각 URL별 생성된 스킬 간략 요약]

### 매칭된 태스크
[주간회의록과 매칭된 태스크 목록]
```

## 새 입력이 없는 경우

새 입력이 없으면 다음과 같이 보고하세요:

```markdown
## Autoskill 상태

현재 새로운 입력(Status=new)이 없습니다.

### 현재 상태
- 대기 중: 0개
- 처리 완료: X개
- 에러: X개

노션 DB에 새 URL을 추가하면 다시 확인해드리겠습니다.
```

## 에러 처리

### 환경변수 오류
```
환경변수가 설정되지 않았습니다.
/Users/chohansol/cursor/autoskill/.env 파일을 확인하세요.

필수 환경변수:
- NOTION_TOKEN
- SKILL_INPUT_DB_ID
- WEEKLY_MEETING_DB_ID
```

### Kill Switch 활성화
```
파이프라인이 일시 중지 상태입니다.
EMERGENCY_STOP 파일이 존재합니다.

재개하려면: rm /Users/chohansol/cursor/autoskill/EMERGENCY_STOP
```

### Circuit Breaker 열림
```
연속 실패로 인해 파이프라인이 일시 중단되었습니다.
300초 후 자동으로 재시도됩니다.

로그 확인: tail -50 /Users/chohansol/cursor/autoskill/pipeline.log
```

## 주의사항

- 파이프라인 실행 시 Claude CLI가 호출되므로 API 비용이 발생합니다
- 한 번에 여러 URL을 처리하면 시간이 소요될 수 있습니다 (URL당 1-5분)
- 노션 API Rate Limit에 주의하세요
