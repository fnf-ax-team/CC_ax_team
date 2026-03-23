# 에러 워처 실행

대시보드 개발 중 발생하는 에러를 실시간으로 모니터링합니다.

## 기능

- **실시간 에러 감지**: TypeScript, Vite, Node 런타임, API 에러
- **콘솔 하이라이트**: 에러는 빨간색, 경고는 노란색으로 표시
- **로그 파일 저장**: `logs/errors-YYYY-MM-DD.log`
- **시스템 알림**: Windows 토스트 알림 (5초 쿨다운)

## 실행 명령어

```bash
node scripts/error-watcher.js
```

## 감지되는 에러 유형

| 유형 | 패턴 |
|------|------|
| TypeScript | `error TS`, `Type error`, `Cannot find module` |
| Vite | `[vite] error`, `Failed to resolve import` |
| Runtime | `Error:`, `TypeError:`, `ReferenceError:` |
| API | `ECONNREFUSED`, `status code 4xx/5xx`, `AxiosError` |

## 종료

`Ctrl+C`로 종료합니다.

## 출력 예시

에러 워처 실행 후 발생하는 에러를 실시간으로 보여주고, 알림을 발송합니다:

```
========================================
  Error Watcher - Dashboard Monitor
========================================
[2026-01-20 10:00:00] 에러 모니터링 시작
로그 파일: logs/errors-2026-01-20.log
종료: Ctrl+C

 ERROR  [TypeScript] error TS2339: Property 'foo' does not exist...
 WARN   [Warning] 'xyz' is deprecated...
```

스크립트를 실행하고 에러 발생 시 사용자에게 알려주세요.
