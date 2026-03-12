# FNF AI Studio

F&F AX팀의 AI 이미지 생성 플랫폼.
패션 브랜드 화보, 배경 교체, AI 인플루언서, 셀카, 제품 연출 등 다양한 워크플로를 Gemini API 기반으로 실행한다.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 담당 | F&F / AX팀 (AI Transformation) |
| API | Gemini API (gemini-3-pro-image-preview / gemini-3-flash-preview) |
| 현재 집중 브랜드 | MLB |
| 목적 | 오프라인 스튜디오 촬영 업무 AI 전환 |

---

## 폴더 구조

```
fnf-studio/
├── .claude/
│   ├── CLAUDE.md               # 프로젝트 절대 규칙
│   ├── rules/                  # 정책 규칙
│   │   ├── gemini-policy.md    # Gemini API 모델/키/재시도 규칙
│   │   ├── image-options.md    # 비율/해상도/비용 옵션 규칙
│   │   ├── workflow-template.md # 워크플로 4단계 구조 규칙
│   │   ├── outfit-analysis-rules.md
│   │   └── vlm-prompt-rules.md
│   ├── skills/                 # 워크플로 스킬 (SKILL.md 기반)
│   │   ├── 브랜드컷_brand-cut/
│   │   ├── 셀카_selfie/
│   │   ├── 얼굴교체_face-swap/
│   │   ├── 포즈변경_pose-change/
│   │   ├── 포즈따라하기_pose-copy/
│   │   ├── 이커머스_ecommerce/
│   │   ├── 제품디자인_product-design/
│   │   ├── 제품연출_product-styled/
│   │   ├── 슈즈3D_shoes-3d/
│   │   ├── 소재생성_fabric-generation/
│   │   └── ...
│   └── templates/
│       └── workflow-prd.md
├── core/                       # 핵심 코어 모듈
│   ├── modules/                # 워크플로 팩토리 (선언적 설정)
│   │   ├── workflow_config.py  # 18개 워크플로 카테고리 설정
│   │   └── workflow_factory.py # WorkflowFactory.create()
│   ├── ai_influencer/          # AI 인플루언서 생성
│   ├── brandcut/               # 브랜드컷 (MLB 프리셋 로더 포함)
│   ├── selfie/                 # 셀카 모듈
│   ├── background_swap/        # 배경 교체
│   ├── outfit_swap/            # 착장 스왑
│   ├── face_swap/              # 얼굴 교체
│   ├── multi_face_swap/        # 다중 얼굴 교체
│   ├── pose_change/            # 포즈 변경
│   ├── pose_copy/              # 포즈 따라하기
│   ├── ecommerce/              # 이커머스
│   ├── seeding_ugc/            # 시딩 UGC
│   ├── beauty_video/           # 뷰티 영상
│   ├── upscale/                # 화질 개선 (4K)
│   ├── fit_variation/          # 핏 베리에이션
│   ├── banner/                 # 채널 배너
│   ├── shoe_rack_mockup/       # 신발장 목업
│   ├── validators/             # 워크플로별 검증기
│   ├── generators/             # 통합 생성기
│   ├── config.py               # 모델 설정 (IMAGE_MODEL, VISION_MODEL)
│   ├── options.py              # 비율/해상도/비용 (Single Source of Truth)
│   ├── api.py                  # API 키 로테이션 (get_next_api_key)
│   └── storage.py              # S3/로컬 스토리지
├── db/
│   ├── presets/                # 워크플로별 프리셋 JSON
│   │   ├── common/             # 공용 (포즈/표정/배경)
│   │   ├── influencer/         # AI 인플루언서 전용
│   │   ├── brandcut/mlb/       # MLB 브랜드컷 전용
│   │   └── selfie/             # 셀카 전용
│   └── mlb_style/              # MLB 참조 이미지 + 스타일 분석
├── fnf_studio_mcp/
│   └── server.py               # MCP 서버 (브랜드컷/배경교체/착장교체/인플루언서)
├── tests/                      # 테스트 코드
│   ├── brandcut/
│   ├── background/
│   ├── influencer/
│   ├── selfie/
│   ├── face_swap/
│   ├── pose_change/
│   ├── ecommerce/
│   ├── validation/
│   ├── integration/
│   ├── unit/
│   └── experiments/
├── scripts/                    # 유틸리티 스크립트
├── docs/                       # 문서
│   └── MCP_DEPLOYMENT_GUIDE.md
└── .env                        # API 키 (로컬, Git 미포함)
```

---

## 워크플로 (18개 등록)

### WorkflowFactory

`core/modules/workflow_config.py`에 18개 워크플로가 선언적으로 등록되어 있다.
`core/modules/workflow_factory.py`의 `WorkflowFactory.create()`로 워크플로를 2-5줄로 생성할 수 있다.

```python
from core.modules.workflow_factory import WorkflowFactory

# 워크플로 생성
wf = WorkflowFactory.create("brandcut", brand="MLB")
wf.analyze(face_images, outfit_images)
result = wf.generate()
```

### 카테고리

| 카테고리 | 얼굴 | 착장 | 브랜드톤 | 해당 워크플로 |
|----------|-----|------|---------|-------------|
| 인물-정규 | 필수 | 필수 | 필수 | 브랜드컷, 레퍼런스 브랜드컷, 이커머스 |
| 인물-자유 | 필수 | 선택 | 중요 | 인플루언서, 셀카, 시딩UGC |
| 스왑 | 상황별 | 상황별 | 중요 | 얼굴교체, 다중얼굴교체, 착장스왑, 포즈변경, 포즈따라하기 |
| 배경 | 유지 | 유지 | 중요 | 배경교체 |
| 제품 | X | X | 필수 | 제품디자인, 제품연출, 슈즈3D, 소재생성 |
| VMD | X | 필수 | 중요 | 마네킹착장, 마네킹포즈 |

### 구현 완료 (검증됨)

| 워크플로 | 카테고리 | core 모듈 | 설명 |
|---------|----------|----------|------|
| 브랜드컷 | 인물-정규 | `core/brandcut/` | MLB 브랜드 화보 생성 (5-Gate 검수) |
| 레퍼런스 브랜드컷 | 인물-정규 | `core/brandcut/` | 페이스스왑 + 착장스왑 + 배경변경 |
| AI 인플루언서 | 인물-자유 | `core/ai_influencer/` | 인플루언서 이미지 생성 (포즈/표정 프리셋) |
| 배경 교체 | 배경 | `core/background_swap/` | 인물 보존 배경 교체 (9-criteria 검수) |
| 셀카 | 인물-자유 | `core/selfie/` | 셀카 / 인스타 스타일 생성 |
| 착장 스왑 | 스왑 | `core/outfit_swap/` | 착장만 변경, 얼굴/포즈 유지 |
| 시딩 UGC | 인물-자유 | `core/seeding_ugc/` | UGC 스타일 자연스러운 콘텐츠 |

### 구현 완료 (미테스트)

코드 구현은 완료되었으나 실 환경 테스트가 아직 필요한 워크플로.

| 워크플로 | 카테고리 | core 모듈 | 설명 |
|---------|----------|----------|------|
| 얼굴 교체 | 스왑 | `core/face_swap/` | 단일 얼굴 스왑 |
| 다중 얼굴 교체 | 스왑 | `core/multi_face_swap/` | 단체 사진 여러 얼굴 동시 교체 |
| 포즈 변경 | 스왑 | `core/pose_change/` | 기존 이미지 포즈 변경 |
| 포즈 따라하기 | 스왑 | `core/pose_copy/` | 레퍼런스 포즈 복제 |
| 이커머스 | 인물-정규 | `core/ecommerce/` | 이커머스용 모델 이미지 |
| 뷰티 영상 | - | `core/beauty_video/` | 비디오 생성 + 자막 + 릴스 |
| 화질 개선 | - | `core/upscale/` | 4K 업스케일 |
| 핏 베리에이션 | - | `core/fit_variation/` | 핏/사이즈 베리에이션 |
| 채널 배너 | - | `core/banner/` | 채널별 광고 배너 자동 생성 |
| 신발장 목업 | - | `core/shoe_rack_mockup/` | 신발장 렌더링에 신발 목업 합성 |

### 개발 예정

| 워크플로 | 카테고리 | 설명 |
|---------|----------|------|
| 제품 연출 | 제품 | 제품 상세페이지 / 연출컷 |
| 슈즈 3D | 제품 | 신발 3D 모델 생성 |
| 제품 디자인 | 제품 | AI 제품 디자인 생성/변형 |
| 소재 생성 | 제품 | 원단/소재 텍스처 생성 |
| 마네킹 착장 | VMD | 마네킹에 착장 입히기 |
| 마네킹 포즈 | VMD | 마네킹 포즈 변경 |

---

## 핵심 규칙

### 모델

| 용도 | 모델 상수 | 실제 모델명 |
|------|----------|------------|
| 이미지 생성 | `IMAGE_MODEL` | gemini-3-pro-image-preview |
| VLM 분석 / 검수 | `VISION_MODEL` | gemini-3-flash-preview |

```python
from core.config import IMAGE_MODEL, VISION_MODEL
# 모델명 직접 하드코딩 금지
```

### 워크플로 4단계 구조

모든 이미지 생성 워크플로는 반드시 이 4단계를 따른다.

```
1. 분석 (VLM)     - VISION_MODEL로 참조 이미지 분석
2. 생성 (Image)   - IMAGE_MODEL로 이미지 생성
3. 검수 (VLM)     - 워크플로별 검수 기준으로 품질 판정
4. 재생성 (Loop)  - 탈락 시 원인 진단 -> 프롬프트 수정 -> 재생성 (최대 2회)
```

검수 없이 이미지를 저장하는 것은 금지이다.

### 옵션 (비율/해상도/비용)

```python
from core.options import (
    ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,
    get_cost, get_workflow_defaults
)
# 비율, 해상도, 비용 하드코딩 금지
```

| 화질 | 해상도 | 장당 비용 |
|------|--------|----------|
| 1K | 1024px | 190원 |
| 2K | 2048px (기본값) | 190원 |
| 4K | 4096px | 380원 |

---

## 환경 설정

```bash
# .env
GEMINI_API_KEY=key1,key2,key3  # 복수 키, 쉼표 구분 (rate limit 로테이션)
```

```python
from core.api import get_next_api_key

api_key = get_next_api_key()  # thread-safe 자동 로테이션
```

---

## MCP 서버

`fnf_studio_mcp/server.py` — Claude Code에서 직접 워크플로를 실행할 수 있는 MCP 엔드포인트.

배포 방법은 `docs/MCP_DEPLOYMENT_GUIDE.md` 참조.

---

## 테스트

모든 테스트/실험 코드는 `tests/` 폴더에 작성한다. 루트에 `test_*`, `temp_*`, `run_*` 파일 직접 생성은 금지이다.

```bash
# 프로젝트 루트에서 실행
PYTHONPATH=. .venv/Scripts/python tests/brandcut/test_mlb_brandcut.py
```

---

## 브랜드 치트시트

브랜드별 프롬프트 규칙은 `.claude/skills/{스킬폴더}/{브랜드}-prompt-cheatsheet.md`에서 관리한다.

| 브랜드 | 치트시트 | 상태 |
|--------|---------|------|
| MLB | 브랜드컷_brand-cut/mlb-prompt-cheatsheet.md | 완료 |
| Discovery | (예정) | 준비 중 |
| Duvetica | (예정) | 준비 중 |
| Sergio Tacchini | (예정) | 준비 중 |
| Banila Co | (예정) | 준비 중 |

---

## 기술 스택

- Python 3.11+
- Gemini API (google-genai)
- MCP (Model Context Protocol)
- PIL/Pillow
- python-dotenv

---

_Last Updated: 2026-03-11_
