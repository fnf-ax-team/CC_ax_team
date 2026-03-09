# 개발 서버 시작

개발 환경을 빠르게 시작합니다.

## 실행 전 확인사항

1. 현재 실행 중인 프로세스가 있는지 확인
2. 필요한 포트(3200, 5200)가 사용 가능한지 확인

## 실행 명령어

```bash
npm run dev
```

## 포트 충돌 시 해결

Windows에서 포트 충돌 시:
```powershell
taskkill /F /IM node.exe
```

## 접속 URL

- **프론트엔드**: http://localhost:5200
- **백엔드 API**: http://localhost:3200/api

서버를 시작하면 준비 완료 메시지를 출력하세요.
