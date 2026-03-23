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
│   │   ├── 배경교체_background-swap (예정)
│   │   └── ...
│   └── templates/
│       └── workflow-prd.md
├── core/                       # 핵심 코어 모듈
│   ├── ai_influencer/          # AI 인플루언서 생성
│   ├── brandcut/               # 브랜드컷 (MLB 프리셋 로더 포함)
│   ├── selfie/                 # 셀카 모듈
│   ├── background_swap/        # 배경 교체
│   ├── validators/             # 워크플로별 검증기
│   ├── config.py               # 모델 설정 (IMAGE_MODEL, VISION_MODEL)
│   ├── options.py              # 비율/해상도/비용 (Single Source of Truth)
│   ├── api.py                  # API 키 로테이션 (get_next_api_key)
│   └── storage.py              # S3/로컬 스토리지
├── db/
│   └── presets/                # 워크플로별 프리셋 JSON
│       ├── common/             # 공용 (포즈/표정/배경)
│       │   ├── pose_presets.json
│       │   ├── expression_presets.json
│       │   └── background_presets.json
│       ├── influencer/         # AI 인플루언서 전용
│       │   ├── camera_presets.json
│       │   ├── styling_preset_db.json
│       │   └── prompt_schema.json
│       ├── brandcut/mlb/       # MLB 브랜드컷 전용
│       │   ├── mlb_pose_presets.json
│       │   ├── mlb_expression_presets.json
│       │   ├── mlb_background_presets.json
│       │   ├── mlb_camera_presets.json
│       │   ├── mlb_model_presets.json
│       │   └── mlb_styling_presets.json
│       └── selfie/             # 셀카 전용
│           └── scene_presets.json
├── fnf_studio_mcp/
│   └── server.py               # MCP 서버 (브랜드컷/배경교체/착장교체/인플루언서)
├── tests/                      # 테스트 코드
│   ├── brandcut/
│   ├── background/
│   ├── influencer/
│   ├── selfie/
│   ├── validation/
│   ├── integration/
│   └── experiments/
├── scripts/                    # 유틸리티 스크립트
├── docs/                       # 문서
│   └── MCP_DEPLOYMENT_GUIDE.md
└── .env                        # API 키 (로컬, Git 미포함)
```

---

## 워크플로

### 구현 완료

| 워크플로 | 스킬 폴더 | 설명 |
|---------|----------|------|
| 브랜드컷 | 브랜드컷_brand-cut | MLB 브랜드 화보 생성 (5-Gate 검수) |
| 레퍼런스 브랜드컷 | (레퍼런스브랜드컷_reference-brandcut) | 페이스스왑 + 착장스왑 + 배경변경 |
| AI 인플루언서 | AI인플루언서_ai-influencer | 인플루언서 이미지 생성 (포즈/표정 프리셋) |
| 배경 교체 | 배경교체_background-swap | 인물 보존 배경 교체 (9-criteria 검수) |
| 셀카 | 셀카_selfie | 셀카 / 인스타 스타일 생성 |
| 착장 스왑 | 착장_outfit-swap | 착장만 변경, 얼굴/포즈 유지 |

### 개발 예정

| 워크플로 | 설명 |
|---------|------|
| 얼굴 교체 | 단일/다중 얼굴 스왑 |
| 포즈 변경 | 기존 이미지 포즈 변경 |
| 이커머스 | 이커머스용 모델 이미지 |
| 제품 연출 | 제품 상세페이지 / 연출컷 |
| 슈즈 3D | 신발 3D 모델 생성 |
| VMD | 마네킹 착장 / 포즈 변경 |

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
