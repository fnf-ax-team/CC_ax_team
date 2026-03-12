# FNF AI Studio 쇼케이스 빌더

> FNF AI Studio 쇼케이스 사이트를 구축/업데이트하는 스킬.
> 디자인 가이드(`frontend/DESIGN_GUIDE.md`)를 반드시 참조한다.

## 트리거

- "쇼케이스 만들어", "페이지 만들어", "사이트 업데이트"
- "새 워크플로 섹션 추가", "이미지 교체"
- "쇼케이스 빌드", "showcase build"

## 핵심 원칙

1. **디자인 가이드 필수 참조** — `frontend/DESIGN_GUIDE.md` 로드 후 작업 시작
2. **showcase_data.json이 CMS** — 모든 콘텐츠는 이 파일로 관리
3. **컴포넌트 재사용** — 기존 컴포넌트 조합으로 구축, 불필요한 새 컴포넌트 금지
4. **Figma 동기화** — 사이트 변경 시 Figma도 함께 업데이트 (MCP 연결 시)

---

## 사전 준비

스킬 실행 전 반드시 로드:

```python
# 1. 디자인 가이드 로드
Read("frontend/DESIGN_GUIDE.md")

# 2. 현재 쇼케이스 데이터 확인
Read("data/showcase_data.json")

# 3. 워크플로 UI 설정 확인
Read("frontend/src/data/workflows.ts")

# 4. 타입 정의 확인
Read("frontend/src/types/index.ts")
```

---

## 아키텍처

### 사이트 구조

```
메인 페이지 (/)
├── ScrollIndicator          # 스크롤 진행 바
├── Navbar                   # 고정 네비게이션
├── Hero                     # 100vh 배경 슬라이더
├── GallerySection[]         # 워크플로별 갤러리 (showcase_data.json 순서)
│   ├── display_mode: grid         → ImageGrid → ImageCard[]
│   └── display_mode: before_after → BeforeAfterSlider[]
├── PromptLibrarySection     # 플로우 다이어그램 + 통계
├── Footer                   # 하단 푸터
└── ImageDetailModal         # 이미지 클릭 모달 (전역)

서브 페이지
├── /dashboard               # 팀 대시보드
└── /ax                      # AX 내부 운영 도구
```

### 데이터 흐름

```
이미지 폴더 (페이지에쓸이미지/)
    ↓ 복사
Fnf_studio_outputs/{workflow}/showcase/images/
    ↓ 경로 참조
data/showcase_data.json
    ↓ API 서빙
FastAPI GET /api/v1/showcase
    ↓ fetch
useShowcaseData() 훅
    ↓ props
App.tsx → GallerySection → ImageCard / BeforeAfterSlider
    ↓ 이미지 src
/outputs/{image_path} → StaticFiles(Fnf_studio_outputs/)
```

### 핵심 타입

```typescript
// 이미지
interface ShowcaseImage {
  id: string                          // 전역 고유 ID (예: "bc_001")
  title: string                       // 표시 제목
  image_path: string                  // Fnf_studio_outputs/ 기준 상대 경로
  before_image_path?: string | null   // before_after 모드에서 원본 경로
  description?: string                // 설명
  metadata?: Record<string, unknown>  // 모달 배지 (최대 4개)
}

// 워크플로
interface ShowcaseWorkflow {
  id: WorkflowType
  name: string                        // 영문명
  name_ko: string                     // 한국어명
  description: string
  description_ko: string
  display_mode: 'grid' | 'before_after'
  images: ShowcaseImage[]
}

// 전체 데이터
interface ShowcaseData {
  hero: ShowcaseImage[]
  workflows: ShowcaseWorkflow[]
}
```

### 워크플로 UI 설정

```typescript
// frontend/src/data/workflows.ts
const WORKFLOW_CONFIG: Record<WorkflowType, WorkflowConfig> = {
  brand_cut:        { aspectRatio: 'aspect-[3/4]',  gridCols: 'grid-cols-3' },
  ai_influencer:    { aspectRatio: 'aspect-[9/16]', gridCols: 'grid-cols-3' },
  background_swap:  { aspectRatio: 'aspect-[3/4]',  gridCols: 'grid-cols-2' },
  outfit_swap:      { aspectRatio: 'aspect-[3/4]',  gridCols: 'grid-cols-3' },
}
```

---

## 작업 유형별 실행 가이드

### 1. 이미지 교체 (가장 빈번)

사용자가 이미지 폴더를 지정하면:

```
단계 1: 이미지 폴더 스캔
- 폴더 구조 확인 (원본/결과, before/after 쌍)
- 이미지 파일 목록 수집

단계 2: Fnf_studio_outputs 복사
- 대상: Fnf_studio_outputs/{workflow}/showcase/images/
- 네이밍: {prefix}_{번호}.{ext} (예: inf_test1_001.jpg)
- before/after 쌍이면: before_{id}.jpg, after_{id}.png

단계 3: showcase_data.json 업데이트
- 해당 워크플로의 images 배열 교체
- hero 이미지도 필요시 교체
- id는 고유하게 생성 (예: bg_001, inf_001)

단계 4: API reload
- POST http://localhost:8000/api/v1/showcase/reload
- 응답 확인 (workflows 수, total_images 수)

단계 5: Figma 동기화 (MCP 연결 시)
- 해당 섹션의 카드 노드에 set_node_image_fill
- 이미지 URL: http://localhost:8000/outputs/{image_path}
```

### 2. 새 워크플로 섹션 추가

```
단계 1: 워크플로 정의
- id, name, name_ko, description, description_ko
- display_mode: 'grid' 또는 'before_after'

단계 2: 타입 확장 (필요시)
- frontend/src/types/index.ts → WorkflowType에 새 값 추가

단계 3: UI 설정 추가
- frontend/src/data/workflows.ts → WORKFLOW_CONFIG에 비율/그리드 추가

단계 4: 네비게이션 추가
- frontend/src/components/layout/Navbar.tsx → 네비 링크 추가

단계 5: showcase_data.json에 워크플로 추가
- workflows 배열에 새 항목 추가 (순서 = 페이지 렌더링 순서)

단계 6: Figma 섹션 추가 (MCP 연결 시)
- 디자인 가이드 참조하여 새 섹션 프레임 생성
```

### 3. 전체 페이지 빌드 (처음부터)

```
단계 1: 디자인 가이드 참조
- frontend/DESIGN_GUIDE.md 전체 로드

단계 2: 이미지 수집 및 정리
- 각 워크플로별 이미지 폴더 스캔
- Fnf_studio_outputs/ 구조로 복사

단계 3: showcase_data.json 생성
- hero 이미지 선정 (워크플로별 베스트 1장씩)
- workflows 배열 구성

단계 4: 프론트엔드 빌드 확인
- npm run dev 실행
- 브라우저에서 렌더링 확인

단계 5: Figma 동기화
- 전체 페이지 프레임 생성 (1440px 너비)
- 섹션별 컴포넌트 배치
- 실제 이미지 적용
```

---

## 디자인 규칙 (DESIGN_GUIDE.md 요약)

### 컬러 시스템

| 토큰 | HEX | 용도 |
|------|-----|------|
| bg-primary | #0A0A0A | 페이지 배경 |
| bg-secondary | #141414 | 보조 배경 |
| bg-card | #1A1A1A | 카드 배경 |
| text-primary | #FAFAFA | 주요 텍스트 |
| text-secondary | #A0A0A0 | 보조 텍스트 |
| text-muted | #666666 | 비활성 텍스트 |
| accent-good | #4ADE80 | 긍정 상태 |
| accent-bad | #F87171 | 부정 상태 |
| accent-brand | #E5E5E5 | 브랜드 강조 |
| border-subtle | #222222 | 기본 보더 |
| border-hover | #333333 | 호버 보더 |

### 타이포그래피

| 용도 | 폰트 | 스타일 |
|------|------|--------|
| Hero Title | Playfair Display | Italic 700, 72px (데스크톱) |
| Section Title | Playfair Display | Italic 700, 48px |
| Section Title KO | Pretendard | 400, 18px |
| UI 텍스트 | Inter | 400/500/600 |
| 한국어 | Pretendard | 400/500 |
| Eyebrow Label | Inter | 400, 10px, tracking-widest |

### 레이아웃

| 항목 | 값 |
|------|-----|
| 최대 너비 | 1400px |
| 섹션 간격 | 160px (section-gap) |
| 콘텐츠 패딩 | 64px 좌우 |
| 카드 라운딩 | 8px |
| 카드 gap | 24px (grid gap-6) |

### 컴포넌트 스펙

**ImageCard:**
- 라운딩: 8px
- 호버: scale 1.03 (300ms ease-out)
- 오버레이: 하단 그라데이션 (transparent → black/60)
- 제목: 호버 시 translateY(0) + opacity(1) 전환

**BeforeAfterSlider:**
- 디바이더: 흰색 2px
- 핸들: 32px 원형, 흰색, shadow-lg
- BEFORE/AFTER 라벨: 10px 흰색 80% opacity
- clipPath 방식으로 이미지 마스킹

**GallerySection:**
- Eyebrow: "WORKFLOW" 텍스트, text-muted, tracking-widest
- 제목: Playfair Display Italic
- 한국어 제목: text-secondary
- 디바이더: 48px x 1px, border-hover 색상

---

## Figma 동기화 규칙

### 연결 확인

```
1. WebSocket 서버 실행: bunx cursor-talk-to-figma-socket (포트 3055)
2. Figma 플러그인에서 채널 연결
3. join_channel로 채널 조인
```

### 섹션 생성 패턴

```
메인 프레임 (1440 x auto, VERTICAL, #0A0A0A)
├── Navbar (1440 x 64, HORIZONTAL, SPACE_BETWEEN)
├── Hero Section (1440 x 900)
├── Section - {Workflow Name} (1440 x auto, VERTICAL)
│   ├── Section Header (auto, VERTICAL)
│   │   ├── Eyebrow Label (10px, #666666)
│   │   ├── Section Title (48px, Playfair Display)
│   │   ├── Section Title KO (18px, #A0A0A0)
│   │   └── Section Divider (48x1, #333333)
│   └── Image Grid (auto, HORIZONTAL, WRAP)
│       ├── Card 1 (width x height, 8px radius, IMAGE fill)
│       ├── Card 2 ...
│       └── Card N ...
├── Prompt Library Section
└── Footer
```

### 이미지 적용

```
// 로컬 이미지를 Figma 카드에 적용
set_node_image_fill(
  nodeId: "카드노드ID",
  imageUrl: "http://localhost:8000/outputs/{image_path}",
  scaleMode: "FILL"
)
```

### 컨테이너 투명 처리

Figma에서 컨테이너 프레임은 투명하게:
```
set_fill_color(nodeId, r: 0.04, g: 0.04, b: 0.04, a: 0.01)
```

---

## showcase_data.json 스키마

### 필수 필드

```json
{
  "hero": [
    {
      "image_path": "string (필수)",
      "title": "string (필수)",
      "workflow": "string (필수, WorkflowType)"
    }
  ],
  "workflows": [
    {
      "id": "string (필수, WorkflowType)",
      "name": "string (필수, 영문)",
      "name_ko": "string (필수, 한국어)",
      "description": "string (필수, 영문)",
      "description_ko": "string (필수, 한국어)",
      "display_mode": "grid | before_after (필수)",
      "images": [
        {
          "id": "string (필수, 전역 고유)",
          "title": "string (필수)",
          "image_path": "string (필수, Fnf_studio_outputs 기준 상대 경로)",
          "before_image_path": "string | null (before_after 모드에서 필수)",
          "description": "string (선택)"
        }
      ]
    }
  ]
}
```

### ID 네이밍 규칙

| 워크플로 | ID prefix | 예시 |
|---------|-----------|------|
| brand_cut | bc_ | bc_001, bc_002 |
| ai_influencer | inf_ | inf_001, inf_002 |
| background_swap | bg_ | bg_001, bg_002 |
| outfit_swap | os_ | os_001, os_002 |

### 이미지 경로 규칙

```
Fnf_studio_outputs/
└── {workflow}/
    └── showcase/
        └── images/
            ├── {descriptive_name}.jpg    # grid 모드
            ├── before_{id}.jpg           # before_after 모드
            └── after_{id}.png            # before_after 모드
```

---

## 이미지 폴더 입력 컨벤션

사용자가 이미지를 제공할 때의 기대 폴더 구조:

```
페이지에쓸이미지/
├── 최상단/           # Hero 이미지
├── 브랜드컷/         # Brand Cut 이미지
├── 인플루언서/       # AI Influencer 이미지
├── 배경교체/         # Background Swap (원본/결과 하위 폴더)
│   ├── MLB원본/
│   ├── MLB결과/
│   ├── DX원본/
│   └── DX결과/
├── 착장교체/         # Outfit Swap 이미지
└── {새워크플로}/     # 추가 워크플로
```

**배경교체 매칭 규칙:**
- 원본/결과 폴더의 파일명 접두사로 쌍 매칭
- 예: `M16_2525.jpg` (원본) ↔ `M16_2525_bg_swap.png` (결과)

---

## 체크리스트

### 이미지 교체 시

- [ ] 이미지 폴더 스캔 완료
- [ ] Fnf_studio_outputs/ 복사 완료
- [ ] showcase_data.json 업데이트 완료
- [ ] API reload 성공 (POST /api/v1/showcase/reload)
- [ ] 브라우저에서 이미지 로딩 확인
- [ ] Figma 카드 이미지 업데이트 (MCP 연결 시)

### 새 워크플로 추가 시

- [ ] WorkflowType 타입 추가
- [ ] WORKFLOW_CONFIG 설정 추가
- [ ] Navbar 링크 추가
- [ ] showcase_data.json에 워크플로 추가
- [ ] 이미지 복사 및 경로 설정
- [ ] API reload 성공
- [ ] Figma 섹션 프레임 추가 (MCP 연결 시)

### 전체 빌드 시

- [ ] DESIGN_GUIDE.md 로드
- [ ] 모든 워크플로 이미지 정리
- [ ] showcase_data.json 완성
- [ ] 프론트엔드 빌드 성공 (npm run build)
- [ ] API 서버 정상 응답
- [ ] 브라우저 전체 페이지 렌더링 확인
- [ ] Figma 전체 페이지 동기화 (MCP 연결 시)
