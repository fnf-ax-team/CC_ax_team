# Vercel 배포 스킬

> FNF AI Studio 프론트엔드 및 정적 사이트를 Vercel에 배포하는 스킬

## 용도

- **FNF AI Studio 프론트엔드** (React + Vite) 배포
- HTML 리포트/쇼케이스 정적 배포
- 어떤 컴퓨터에서든 동일하게 보이도록 호스팅

## 전제 조건

- Node.js 설치됨
- Vercel CLI 설치: `npm i -g vercel`
- Vercel 로그인 완료: `vercel login`

## 계정 정보

- **Vercel 팀**: yrsongs-projects
- **대시보드**: https://vercel.com/yrsongs-projects

---

## A. 프론트엔드 배포 (React + Vite)

### 최초 배포

```bash
cd frontend
vercel --yes
```

- 자동으로 Vite 프레임워크 감지
- `vercel.json`에 SPA 라우팅 설정 포함됨
- 빌드: `npm run build` → `dist/` 출력

### 프로덕션 배포

```bash
cd frontend
vercel --prod
```

### 환경 변수 설정 (필요 시)

```bash
# API 백엔드 URL 설정 (백엔드 별도 배포 시)
vercel env add VITE_API_BASE_URL production
```

### 프로젝트 구조

```
frontend/
├── vercel.json          # Vercel 배포 설정 (SPA rewrites)
├── package.json         # build: tsc -b && vite build
├── vite.config.ts       # Vite 설정 + 경로 alias
├── dist/                # 빌드 출력 (자동 생성)
└── src/                 # 소스 코드
```

---

## B. 정적 HTML 배포 (리포트/쇼케이스)

### 1단계: 배포 폴더 준비

```bash
cd D:/FNF_Studio_TEST/New-fnf-studio

# 배포 폴더 초기화
rm -rf deploy2
mkdir -p deploy2

# HTML 파일 복사 (index.html로)
cp {소스_HTML} deploy2/index.html

# HTML에서 참조하는 에셋 추출 및 복사
grep -oP 'src="([^"]+\.(png|jpg|jpeg|gif|svg|mp4|webm|webp))"' deploy2/index.html \
  | sed 's/src="//; s/"$//' | sort -u | while IFS= read -r f; do
  if [ -f "$f" ]; then
    mkdir -p "deploy2/$(dirname "$f")"
    cp "$f" "deploy2/$(dirname "$f")/"
  fi
done
```

### 2단계: 배포

```bash
# 프리뷰 배포 (확인용)
vercel deploy2/

# 프로덕션 배포
vercel deploy2/ --prod
```

### 실제 예시

```bash
# FnF AI Marketing Report 배포
cp FnF_AI_Marketing_Report.html deploy2/index.html
vercel deploy2/ --prod
```

---

## CLI 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `vercel` | 프리뷰 배포 |
| `vercel --prod` | 프로덕션 배포 |
| `vercel ls` | 배포 목록 조회 |
| `vercel inspect <url>` | 배포 상세 정보 |
| `vercel logs <url>` | 배포 로그 |
| `vercel rm <name>` | 프로젝트 삭제 |
| `vercel env ls` | 환경 변수 목록 |
| `vercel domains ls` | 도메인 목록 |

## 비용

- **무료** (Vercel Hobby 플랜)
- 월 100GB 대역폭
- 빌드 시간 월 6,000분
- HTTPS 자동 적용
- 글로벌 CDN (Edge Network)
- 서버리스 함수 지원

## 주의사항

- 에셋 경로는 상대경로 사용
- SPA 라우팅: `vercel.json`의 rewrites로 처리됨
- 한글 폴더명/파일명 지원됨
- 프리뷰 URL은 커밋마다 자동 생성 (Git 연동 시)
- API 프록시는 Vercel Rewrites 또는 Serverless Functions로 처리 가능
