# 서버 안정화

서버 문제 발생 시 진단하고 복구합니다.

## 실행 순서

### 1. 포트 점검
```powershell
# 3200 포트 (백엔드)
netstat -ano | findstr :3200

# 5200 포트 (프론트엔드)
netstat -ano | findstr :5200
```

### 2. 좀비 프로세스 정리
포트를 점유하고 있는 프로세스가 있으면 PID를 확인하고 종료:
```powershell
# PID로 프로세스 종료
taskkill /F /PID <PID>

# 또는 모든 node 프로세스 종료 (주의)
taskkill /F /IM node.exe
```

### 3. 헬스체크
서버가 실행 중이면 API 응답 확인:
```powershell
curl -s http://localhost:3200/api/kpi | head -c 200
```

### 4. 서버 재시작
문제가 있으면 서버 재시작:
```bash
npm run dev
```

## 응답 형식

진단 결과를 간략히 보고:
- 포트 상태 (사용중/비어있음)
- 정리한 프로세스 수
- 헬스체크 결과 (정상/실패)
- 취한 조치

문제가 없으면: "서버 정상 작동 중"
문제 해결 시: "서버 안정화 완료 - [조치 내용]"
