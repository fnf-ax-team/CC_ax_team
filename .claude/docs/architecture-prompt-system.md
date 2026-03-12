# FNF Studio — 프롬프트 시스템 아키텍처

> 작성일: 2026-03-06
> 대상 독자: AX팀 개발/운영 담당자
> 목적: 코어 모듈 조합 기반의 워크플로 확장 구조 이해

---

## 핵심 컨셉: 코어 모듈 조합으로 워크플로를 만든다

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │   "새 워크플로 = 기존 코어 모듈 조합 + 워크플로 전용 로직"              │
  │                                                                         │
  │   착장 분석기 ─┐                                                        │
  │   포즈 분석기 ─┼─ 조합 ──► 새 워크플로 모듈 ──► 검증기 등록            │
  │   배경 분석기 ─┤          (prompt_builder +      (ValidatorRegistry)    │
  │   표정 분석기 ─┤           generator)                                   │
  │   프리셋 DB  ──┘                                                        │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 워크플로 현황 한눈에 보기

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FNF Studio 워크플로 현황 (2026.03)                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  [LIVE] 운영 중                                                            ║
║  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐       ║
║  │  브랜드컷   │ │ AI 인플루언서│ │  배경 교체    │ │  착장 변경   │       ║
║  │  brandcut   │ │ai_influencer│ │background_   │ │ outfit_swap  │       ║
║  │             │ │             │ │    swap       │ │              │       ║
║  │ 20파일      │ │ 15파일      │ │ 8파일        │ │ 6파일        │       ║
║  │ 880KB       │ │ 556KB       │ │ 212KB        │ │ 164KB        │       ║
║  └─────────────┘ └─────────────┘ └──────────────┘ └──────────────┘       ║
║                                                                            ║
║  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  ║
║                                                                            ║
║  [DEV] 개발 중  (코어 모듈 조합으로 구현 완료, 실무 테스트 단계)           ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐             ║
║  │ 얼굴 교체  │ │  셀카      │ │ 포즈 변경  │ │ 포즈 복제  │             ║
║  │ face_swap  │ │  selfie    │ │pose_change │ │ pose_copy  │             ║
║  │ 11파일     │ │ 8파일      │ │ 7파일      │ │ 6파일      │             ║
║  └────────────┘ └────────────┘ └────────────┘ └────────────┘             ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐             ║
║  │ 다중 얼굴  │ │ 이커머스   │ │ 핏 변형    │ │ 시딩 UGC   │             ║
║  │multi_face  │ │ ecommerce  │ │fit_varia-  │ │seeding_ugc │             ║
║  │   _swap    │ │            │ │   tion     │ │            │             ║
║  │ 7파일      │ │ 11파일     │ │ 7파일      │ │ 2파일      │             ║
║  └────────────┘ └────────────┘ └────────────┘ └────────────┘             ║
║                                                                            ║
║  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  ║
║                                                                            ║
║  [PLAN] 개발 예정  (코어 모듈 재활용 가능, 신규 코드 최소화)               ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐             ║
║  │ 제품 디자인│ │ 소재 생성  │ │  슈즈 3D   │ │ 제품 연출  │             ║
║  │ product_   │ │ fabric_    │ │ shoes_3d   │ │ product_   │             ║
║  │  design    │ │generation  │ │            │ │  styled    │             ║
║  │ 코어 없음  │ │ DB만 존재  │ │ 코어 없음  │ │ 코어 없음  │             ║
║  └────────────┘ └────────────┘ └────────────┘ └────────────┘             ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐             ║
║  │ 그래픽     │ │ 마네킹     │ │ 채널 배너  │ │ 레퍼런스   │             ║
║  │ graphics   │ │ mannequin  │ │ channel_   │ │ reference_ │             ║
║  │            │ │            │ │  banner    │ │  brandcut  │             ║
║  │ 코어 없음  │ │ 코어 없음  │ │ Figma만    │ │ 스킬만     │             ║
║  └────────────┘ └────────────┘ └────────────┘ └────────────┘             ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 상태 정의

| 상태 | 의미 | 기준 |
|------|------|------|
| **[LIVE]** 운영 중 | 실무 투입 가능 | 4단계 파이프라인 완성 + 실무 검증 완료 |
| **[DEV]** 개발 중 | 코드 구현 완료, 테스트 단계 | 코어 모듈 조합 완료, 실무 테스트 진행 중 |
| **[PLAN]** 개발 예정 | 설계 완료, 코드 미작성 | 기존 코어 모듈 조합으로 빠르게 구현 가능 |

---

## 전체 시스템 아키텍처

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                         FNF Studio — AI 이미지 생성 플랫폼                          ║
║                   (Gemini API 기반 패션 브랜드 비주얼 생성 시스템)                   ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5 : 스킬 / 사용자 인터페이스                                                   │
│                                                                                      │
│  .claude/skills/                                                                     │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ brand-cut   │ │background-   │ │ai-influencer│ │ selfie/      │ │ ecommerce   │ │
│  │ SKILL.md    │ │swap SKILL.md │ │ SKILL.md    │ │ seeding-ugc  │ │ SKILL.md    │ │
│  │ cheatsheet  │ │              │ │             │ │ SKILL.md     │ │             │ │
│  └──────┬──────┘ └──────┬───────┘ └──────┬──────┘ └──────┬───────┘ └──────┬──────┘ │
└─────────┼───────────────┼────────────────┼───────────────┼────────────────┼─────────┘
          │               │                │               │                │
          ▼               ▼                ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4 : 워크플로 모듈  (core/{workflow}/)                                          │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  각 워크플로 모듈 표준 구조                                                   │    │
│  │                                                                              │    │
│  │  analyzer.py ──► prompt_builder.py ──► generator.py ──► validator.py        │    │
│  │       │                │                    │                │              │    │
│  │  VLM 분석          JSON 스키마           이미지 생성        품질 검수        │    │
│  │  결과 생성          프롬프트 조립         API 호출          pass/fail        │    │
│  │                        │                                     │              │    │
│  │                   templates.py                        retry_generator.py   │    │
│  │                 (브랜드별 템플릿)                       (재시도 로직)         │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  [LIVE] 운영 중 ────────────────────────────────────────────────────────────────     │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐                 │
│  │  brandcut  │  │ ai_influencer│  │background   │  │outfit_swap │                 │
│  │ [LIVE]     │  │ [LIVE]       │  │   _swap     │  │ [LIVE]     │                 │
│  ├────────────┤  ├──────────────┤  │ [LIVE]      │  ├────────────┤                 │
│  │analyzer    │  │pose_analyzer │  ├─────────────┤  │analyzer    │                 │
│  │prompt_bld  │  │expr_analyzer │  │analyzer     │  │prompt_bld  │                 │
│  │generator   │  │hair_analyzer │  │prompt_bld   │  │generator   │                 │
│  │validator   │  │face_analyzer │  │generator    │  │validator   │                 │
│  │templates   │  │bg_analyzer   │  │validator    │  └────────────┘                 │
│  │retry_gen   │  │presets.py    │  └─────────────┘                                  │
│  │style_dir   │  │pipeline.py   │                                                   │
│  │clip_val    │  │prompt_builder│                                                   │
│  └────────────┘  │validator     │                                                   │
│                  └──────────────┘                                                   │
│                                                                                      │
│  [DEV] 개발 중 ─────────────────────────────────────────────────────────────────     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────┐                   │
│  │ face_swap  │  │  selfie    │  │ pose_change │  │ pose_copy  │                   │
│  │ [DEV]      │  │ [DEV]      │  │ [DEV]       │  │ [DEV]      │                   │
│  ├────────────┤  ├────────────┤  ├─────────────┤  ├────────────┤                   │
│  │analyzer    │  │db_loader   │  │presets      │  │analyzer    │                   │
│  │prompt_bld  │  │prompt_bld  │  │prompt_bld   │  │prompt_bld  │                   │
│  │generator   │  │generator   │  │generator    │  │generator   │                   │
│  │validator   │  │validator   │  │validator    │  │validator   │                   │
│  │templates*6 │  │compat.     │  └─────────────┘  └────────────┘                   │
│  └────────────┘  └────────────┘                                                     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────┐                   │
│  │multi_face  │  │ ecommerce  │  │fit_variation│  │seeding_ugc │                   │
│  │  _swap     │  │ [DEV]      │  │ [DEV]       │  │ [DEV]      │                   │
│  │ [DEV]      │  ├────────────┤  ├─────────────┤  ├────────────┤                   │
│  ├────────────┤  │detail_page │  │analyzer     │  │validator   │                   │
│  │detector    │  │figma_buildr│  │fit_presets  │  │(selfie     │                   │
│  │prompt_bld  │  │pipeline    │  │prompt_bld   │  │ 기반)      │                   │
│  │generator   │  │template_   │  │generator    │  └────────────┘                   │
│  │validator   │  │  presets   │  │validator    │                                    │
│  └────────────┘  └────────────┘  └─────────────┘                                   │
│                                                                                      │
│  [PLAN] 개발 예정 ──────────────────────────────────────────────────────────────     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────┐                   │
│  │제품 디자인 │  │ 소재 생성  │  │  슈즈 3D   │  │ 제품 연출  │                   │
│  │ [PLAN]     │  │ [PLAN]     │  │ [PLAN]      │  │ [PLAN]     │                   │
│  ├────────────┤  ├────────────┤  ├─────────────┤  ├────────────┤                   │
│  │ 필요 코어: │  │ 필요 코어: │  │ 필요 코어: │  │ 필요 코어: │                   │
│  │ outfit_    │  │ (신규 분석 │  │ (신규 3D   │  │ outfit_    │                   │
│  │  analyzer  │  │  기 필요)  │  │  파이프라인)│  │  analyzer  │                   │
│  │ bg_analyzer│  │ fabric_    │  │             │  │ bg_analyzer│                   │
│  │ presets    │  │  library   │  │             │  │ presets    │                   │
│  └────────────┘  └────────────┘  └─────────────┘  └────────────┘                   │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────┐                   │
│  │ 그래픽     │  │ 마네킹 착장│  │마네킹 포즈  │  │ 채널 배너  │                   │
│  │ [PLAN]     │  │ [PLAN]     │  │ [PLAN]      │  │ [PLAN]     │                   │
│  ├────────────┤  ├────────────┤  ├─────────────┤  ├────────────┤                   │
│  │ 필요 코어: │  │ 필요 코어: │  │ 필요 코어: │  │ 필요 코어: │                   │
│  │ (신규 그래 │  │ outfit_    │  │ pose_       │  │ Figma API  │                   │
│  │  픽 엔진)  │  │  analyzer  │  │  analyzer   │  │ (기존 코드 │                   │
│  │            │  │ pose_      │  │ outfit_     │  │  존재)     │                   │
│  │            │  │  analyzer  │  │  analyzer   │  │            │                   │
│  └────────────┘  └────────────┘  └─────────────┘  └────────────┘                   │
└──────────────────┬──────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3 : 프리셋 데이터베이스  (db/)                                                 │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ pose_presets.json│  │expression_presets│  │background_presets│                   │
│  │                  │  │     .json        │  │      .json       │                   │
│  │ 사용처:          │  │                  │  │                  │                   │
│  │ - brandcut       │  │ 사용처:          │  │ 사용처:          │                   │
│  │ - ai_influencer  │  │ - brandcut       │  │ - background_swap│                   │
│  │ - selfie         │  │ - ai_influencer  │  │ - brandcut       │                   │
│  │ - ecommerce      │  └──────────────────┘  └──────────────────┘                   │
│  └──────────────────┘                                                                │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ scene_presets    │  │  fit_presets.json│  │  fabric_library  │                   │
│  │     .json        │  │                  │  │     .json        │                   │
│  │                  │  │ 사용처:          │  │                  │                   │
│  │ 사용처:          │  │ - fit_variation  │  │ 사용처:          │                   │
│  │ - selfie         │  └──────────────────┘  │ - [PLAN] fabric  │                   │
│  └──────────────────┘                        └──────────────────┘                   │
│                                                                                      │
│  DB 로더:                                                                            │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                         │
│  │ core/ai_influencer/      │  │ core/selfie/             │                         │
│  │   presets.py             │  │   db_loader.py           │                         │
│  │ (pose, expr 로드)        │  │ (scene, pose 로드)       │                         │
│  └──────────────────────────┘  └──────────────────────────┘                         │
└──────────────────────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2 : 공유 분석기  (VLM 기반)   ★ 새 워크플로의 핵심 재료 ★                    │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐                │
│  │  core/ (루트 레벨 공유 분석기)                                    │                │
│  │                                                                  │                │
│  │  outfit_analyzer.py          background_analyzer.py             │                │
│  │  ┌────────────────────┐      ┌────────────────────────┐         │                │
│  │  │ OutfitAnalysis     │      │ 배경 텍스트 설명 생성  │         │                │
│  │  │ - items[]          │      │ - 장소/분위기          │         │                │
│  │  │ - colors           │      │ - 조명/색감            │         │                │
│  │  │ - logos            │      │ - 호환 포즈 체크       │         │                │
│  │  │ - silhouette       │      └────────┬───────────────┘         │                │
│  │  │ - brand            │               │ 사용처:                  │                │
│  │  └────────┬───────────┘               │ [LIVE] background_swap  │                │
│  │           │ 사용처:                   │ [LIVE] brandcut          │                │
│  │           │ [LIVE] brandcut           │ [PLAN] 제품연출          │                │
│  │           │ [LIVE] ai_influencer      └─────────────────         │                │
│  │           │ [LIVE] outfit_swap                                   │                │
│  │           │ [PLAN] 제품디자인                                    │                │
│  │           │ [PLAN] 마네킹 착장                                   │                │
│  │           └──────────────────────────────────                   │                │
│  └──────────────────────────────────────────────────────────────────┘                │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐                │
│  │  core/ai_influencer/ (공유 분석기 — 다른 워크플로도 사용)         │                │
│  │                                                                  │                │
│  │  pose_analyzer.py         expression_analyzer.py                │                │
│  │  ┌────────────────────┐   ┌─────────────────────────┐          │                │
│  │  │ PoseAnalysisResult │   │ ExpressionAnalysisResult│          │                │
│  │  │ - stance           │   │ - base_expression       │          │                │
│  │  │ - framing          │   │ - eye_type              │          │                │
│  │  │ - angle            │   │ - lip_state             │          │                │
│  │  │ - left/right arm   │   │ - gaze_direction        │          │                │
│  │  │ - left/right leg   │   └───────────┬─────────────┘          │                │
│  │  └──────────┬──────────┘              │ 사용처:                 │                │
│  │             │ 사용처:                 │ [LIVE] brandcut          │                │
│  │             │ [LIVE] brandcut         │ [LIVE] ai_influencer     │                │
│  │             │ [LIVE] ai_influencer    └────────────────          │                │
│  │             │ [DEV]  pose_change                                │                │
│  │             │ [DEV]  pose_copy                                  │                │
│  │             │ [PLAN] 마네킹 포즈                                 │                │
│  │             └────────────────────────────────────               │                │
│  │                                                                  │                │
│  │  hair_analyzer.py   face_analyzer.py   background_analyzer.py  │                │
│  │  (ai_influencer 전용 분석기)                                     │                │
│  └──────────────────────────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1 : 공유 인프라  (모든 워크플로 공통)                                          │
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  core/config.py │  │  core/api.py    │  │ core/options.py │  │ core/policy.py  │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ IMAGE_MODEL     │  │ GeminiClient    │  │ ASPECT_RATIOS   │  │ ALLOWED_MODELS  │ │
│  │ VISION_MODEL    │  │ get_next_       │  │ RESOLUTIONS     │  │ FORBIDDEN_      │ │
│  │ PipelineConfig  │  │   api_key()     │  │ COST_TABLE      │  │   MODELS        │ │
│  │                 │  │ (thread-safe    │  │ WORKFLOW_       │  │ is_forbidden_   │ │
│  │ 모든 워크플로가 │  │  key rotation)  │  │   DEFAULTS      │  │   model()       │ │
│  │ 여기서 import   │  │                 │  │ get_cost()      │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  core/utils.py                                                                  │ │
│  │  pil_to_part()  /  image_to_base64()  /  resize_image()  /  save_pil_image()   │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  검증 프레임워크  (core/validators/ + core/generators/)                         │ │
│  │                                                                                  │ │
│  │  WorkflowType (enum)          ValidatorRegistry                                │ │
│  │  ┌──────────────────────┐     ┌────────────────────────────────────────────┐    │ │
│  │  │ BRANDCUT       [LIVE]│     │ @ValidatorRegistry.register(WorkflowType) │    │ │
│  │  │ BACKGROUND_SWAP[LIVE]│     │                                            │    │ │
│  │  │ AI_INFLUENCER  [LIVE]│     │ 12개 검증기 등록 완료                       │    │ │
│  │  │ OUTFIT_SWAP    [LIVE]│ ◄── │ [PLAN] 워크플로도 여기에 등록하면 끝       │    │ │
│  │  │ FACE_SWAP      [DEV] │     └────────────────────────────────────────────┘    │ │
│  │  │ SELFIE         [DEV] │                                                       │ │
│  │  │ POSE_CHANGE    [DEV] │     generate_with_workflow_validation()               │ │
│  │  │ POSE_COPY      [DEV] │     ┌────────────────────────────────────────────┐    │ │
│  │  │ MULTI_FACE_SWAP[DEV] │     │  1. generate_func() 호출                   │    │ │
│  │  │ ECOMMERCE      [DEV] │     │  2. validator.validate() 호출              │    │ │
│  │  │ FIT_VARIATION   [DEV] │     │  3. 실패 시 재시도 (max 2회)              │    │ │
│  │  │ SEEDING_UGC    [DEV] │     │  → 모든 워크플로가 이 루프를 공유          │    │ │
│  │  └──────────────────────┘     └────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4단계 파이프라인 플로우

```
  사용자 입력
  + 참조 이미지
  (얼굴 / 착장 / 배경 / 포즈 레퍼런스)
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1 : ANALYZE  (VLM 분석)                                      │
│  모델: gemini-3-flash-preview                                        │
│                                                                     │
│  착장 이미지 ──► outfit_analyzer.py ──► OutfitAnalysis              │
│                   (items, colors, logos, silhouette, brand)         │
│                                                                     │
│  포즈 레퍼런스 ──► pose_analyzer.py ──► PoseAnalysisResult          │
│                    (stance, framing, angle, left/right arm/leg)     │
│                                                                     │
│  표정 레퍼런스 ──► expression_analyzer.py ──► ExpressionAnalysisResult│
│                    (base_expr, eye_type, lip_state, gaze)           │
│                                                                     │
│  배경 레퍼런스 ──► background_analyzer.py ──► 텍스트 설명           │
│                    (장소, 분위기, 조명, 색감, 호환 포즈)            │
└─────────────────────────────────────────────────────────────────────┘
          │
          │  분석 결과 (dataclasses)
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 2 : BUILD PROMPT  (프롬프트 조립)                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  입력 소스                                                    │   │
│  │                                                               │   │
│  │  분석 결과      ──┐                                          │   │
│  │  (Phase 1)        │                                          │   │
│  │                   │                                          │   │
│  │  프리셋 DB   ──────┼──► prompt_builder.py                   │   │
│  │  (db/*.json)      │                                          │   │
│  │                   │    ↓ 출력: 한국어 JSON 스키마 프롬프트   │   │
│  │  사용자 옵션 ──────┤                                          │   │
│  │  (비율/해상도)     │    {                                     │   │
│  │                   │      "주제": {...},                       │   │
│  │  브랜드 치트시트 ──┘      "모델": {...},                       │   │
│  │  (mlb-prompt-             "포즈": {                           │   │
│  │   cheatsheet.md)            "preset_id": "P-001"            │   │
│  │                           },                                 │   │
│  │                           "착장": {...},                      │   │
│  │                           "배경": {...},                      │   │
│  │                           "조명색감": {...}                    │   │
│  │                         }                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │
          │  JSON 스키마 프롬프트
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 3 : GENERATE  (이미지 생성)                                   │
│  모델: gemini-3-pro-image-preview                                    │
│                                                                     │
│  프롬프트 (JSON)                                                     │
│  + 얼굴 이미지  (PIL -> pil_to_part())  ──►  Gemini API             │
│  + 착장 이미지  (PIL -> pil_to_part())       generate_content()     │
│  + 배경 이미지  (선택, PIL)                  │                       │
│                                              ▼                      │
│                                         PIL Image                   │
│                                         (생성된 이미지)              │
│                                                                     │
│  API 키 로테이션: get_next_api_key() (thread-safe, rate-limit 대응) │
│  에러 처리: 429/503 -> 재시도 (최대 3회, 지수 백오프)                │
└─────────────────────────────────────────────────────────────────────┘
          │
          │  PIL Image
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 4 : VALIDATE + RETRY  (검수 + 재생성)                        │
│                                                                     │
│  ValidatorRegistry.get(WorkflowType.X, client)                     │
│          │                                                          │
│          ▼                                                          │
│  validator.validate(generated_img, reference_images)               │
│          │                                                          │
│          ▼                                                          │
│  CommonValidationResult                                             │
│  {                                                                  │
│    passed: bool,                                                    │
│    total_score: int,                                                │
│    criteria: { ... },                                               │
│    issues: [...]                                                    │
│  }                                                                  │
│          │                                                          │
│    ┌─────┴──────┐                                                   │
│    │ passed ?   │                                                   │
│    └─────┬──────┘                                                   │
│        Yes│              No (재시도 횟수 < 2)                        │
│           │              │                                          │
│           │         ┌────▼──────────────────────────────────────┐  │
│           │         │ retry_generator.py                        │  │
│           │         │  1. VLM으로 실패 원인 진단                │  │
│           │         │  2. 프롬프트 수정 (탈락 Gate 집중)        │  │
│           │         │  3. Phase 3 재실행                        │  │
│           │         └────┬──────────────────────────────────────┘  │
│           │              │                                          │
│           │         (max 2회 초과 시 -> 안전 폴백 또는 경고)        │
│           ▼              ▼ (재시도 후 Phase 4 반복)                 │
│     ┌─────────────────────────────────────────────────────────┐    │
│     │  Fnf_studio_outputs/{workflow}/{timestamp}_{desc}/      │    │
│     │  +-- images/                                            │    │
│     │  │   +-- input_face_01.jpg                              │    │
│     │  │   +-- input_outfit_01.jpg                            │    │
│     │  │   +-- output_001.jpg                                 │    │
│     │  +-- prompt.json    (API 전송 원본)                      │    │
│     │  +-- prompt.txt     (가독용)                             │    │
│     │  +-- config.json    (비율/해상도/비용 등)                │    │
│     │  +-- validation.json (검수 결과)                         │    │
│     └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 코어 모듈 조합 맵: 새 워크플로를 어떻게 만드는가

> 기존 코어 모듈을 레고처럼 조합하면 새 워크플로의 70~90%가 완성된다.

```
                        ┌─────────────────────────────────┐
                        │     재사용 가능한 코어 모듈      │
                        │         (공유 레고 블록)          │
                        └─────────────────────────────────┘

    분석기 블록                 프리셋 블록              인프라 블록
    ─────────────             ──────────────           ──────────────
    ┌──────────────┐          ┌──────────────┐        ┌──────────────┐
    │ outfit_      │          │ pose_presets │        │ config.py    │
    │  analyzer    │          │   .json      │        │ api.py       │
    │              │          ├──────────────┤        │ options.py   │
    │ 착장 분석    │          │ expression_  │        │ utils.py     │
    │ (색상,로고,  │          │  presets.json│        │ policy.py    │
    │  실루엣)     │          ├──────────────┤        │              │
    ├──────────────┤          │ background_  │        │ 모든 워크플로│
    │ background_  │          │  presets.json│        │ 에서 import  │
    │  analyzer    │          ├──────────────┤        └──────────────┘
    │              │          │ scene_presets│
    │ 배경 분석    │          │   .json      │        ┌──────────────┐
    │ (장소,조명)  │          ├──────────────┤        │ Validator    │
    ├──────────────┤          │ fit_presets  │        │  Registry    │
    │ pose_        │          │   .json      │        │              │
    │  analyzer    │          ├──────────────┤        │ 검증기 등록  │
    │              │          │ fabric_      │        │ 만 하면      │
    │ 포즈 분석    │          │  library.json│        │ 자동 연결    │
    │ (관절,앵글)  │          └──────────────┘        └──────────────┘
    ├──────────────┤
    │ expression_  │
    │  analyzer    │
    │              │
    │ 표정 분석    │
    │ (시선,입)    │
    ├──────────────┤
    │ hair_analyzer│
    │ face_analyzer│
    └──────────────┘


    새 워크플로 조합 예시
    ════════════════════════════════════════════════════════════════════

    [PLAN] 마네킹 착장
    ─────────────────
    outfit_analyzer  ──┐
    pose_analyzer    ──┼──► 신규 prompt_builder ──► generator ──► validator
    pose_presets     ──┘    (마네킹 전용 로직     (기존 패턴   (기존 패턴
                            만 새로 작성)          복제)        복제+커스텀)

    → 신규 코드: prompt_builder.py + validator.py 기준 작성분만
    → 재사용:    분석기 3개 + 프리셋 2개 + 인프라 전체


    [PLAN] 제품 디자인
    ─────────────────
    outfit_analyzer  ──┐
    bg_analyzer      ──┼──► 신규 prompt_builder ──► generator ──► validator
    (신규: product_  ──┘    (제품 디자인 전용)
     analyzer)

    → 신규 코드: product_analyzer.py + prompt_builder.py + validator.py
    → 재사용:    분석기 2개 + 인프라 전체


    [PLAN] 제품 연출
    ─────────────────
    outfit_analyzer  ──┐
    bg_analyzer      ──┼──► 신규 prompt_builder ──► generator ──► validator
    scene_presets    ──┘    (연출컷 전용)

    → 신규 코드: prompt_builder.py + validator.py + templates.py
    → 재사용:    분석기 2개 + 프리셋 1개 + 인프라 전체


    [PLAN] 마네킹 포즈
    ─────────────────
    pose_analyzer    ──┐
    outfit_analyzer  ──┼──► 신규 prompt_builder ──► generator ──► validator
    pose_presets     ──┘    (마네킹+포즈 변경)

    → 신규 코드: prompt_builder.py + validator.py
    → 재사용:    분석기 2개 + 프리셋 1개 + 인프라 전체
```

---

## 크로스-모듈 의존성 다이어그램

```
공유 분석기 → 워크플로 의존성 (누가 누구를 쓰는가)
──────────────────────────────────────────────────────────────────────

core/outfit_analyzer.py (OutfitAnalysis)
  │
  ├──► [LIVE] brandcut          착장 분석 필수
  ├──► [LIVE] ai_influencer     착장 연출 참조
  ├──► [LIVE] outfit_swap       착장 교체 기준
  ├──► [PLAN] 제품 디자인       착장 요소 추출
  ├──► [PLAN] 제품 연출         제품 특징 분석
  └──► [PLAN] 마네킹 착장       마네킹 착장 매칭

core/background_analyzer.py
  │
  ├──► [LIVE] background_swap   배경 분석 필수
  ├──► [LIVE] brandcut          배경 텍스트 변환
  └──► [PLAN] 제품 연출         배경 연출 분석

core/modules/pose_analyzer.py (PoseAnalysisResult)
  │
  ├──► [LIVE] brandcut          포즈 프리셋 매핑
  ├──► [LIVE] ai_influencer     인플루언서 포즈 제어
  ├──► [DEV]  pose_change       포즈 변경 기준
  ├──► [DEV]  pose_copy         포즈 복제 기준
  └──► [PLAN] 마네킹 포즈       마네킹 포즈 변경

core/ai_influencer/expression_analyzer.py (ExpressionAnalysisResult)
  │
  ├──► [LIVE] brandcut          표정 프리셋 매핑
  └──► [LIVE] ai_influencer     인플루언서 표정 제어


프리셋 DB → 워크플로 의존성
──────────────────────────────────────────────────────────────────────

db/pose_presets.json
  ├──► [LIVE] brandcut          포즈 preset_id 참조
  ├──► [LIVE] ai_influencer     인플루언서 포즈 선택
  ├──► [DEV]  selfie            셀카 포즈 선택
  └──► [DEV]  ecommerce         이커머스 포즈 선택

db/expression_presets.json
  ├──► [LIVE] brandcut          표정 preset_id 참조
  └──► [LIVE] ai_influencer     인플루언서 표정 선택

db/background_presets.json
  ├──► [LIVE] background_swap   배경 선택
  └──► [LIVE] brandcut          배경 옵션 제공

db/scene_presets.json
  └──► [DEV]  selfie            시나리오 선택

db/fit_presets.json
  └──► [DEV]  fit_variation     핏 변형 옵션

db/fabric_library.json
  └──► [PLAN] fabric_generation 소재 텍스처 매칭


검증기 등록 현황
──────────────────────────────────────────────────────────────────────

ValidatorRegistry
  ├──► [LIVE] BrandcutValidator
  ├──► [LIVE] BackgroundSwapWorkflowValidator
  ├──► [LIVE] AiInfluencerValidator
  ├──► [LIVE] OutfitSwapValidator
  ├──► [DEV]  FaceSwapValidator
  ├──► [DEV]  SelfieWorkflowValidator
  ├──► [DEV]  UGCValidator
  ├──► [DEV]  PoseChangeValidator
  ├──► [DEV]  PoseCopyValidator
  ├──► [DEV]  MultiFaceSwapValidator
  ├──► [DEV]  EcommerceValidator
  └──► [DEV]  FitVariationValidator
```

---

## brandcut <-> ai_influencer 상세 의존성

> 이 두 모듈은 가장 긴밀하게 연결된 관계. ai_influencer가 "공유 분석 라이브러리" 역할도 겸한다.

```
  core/ai_influencer/                    core/brandcut/
  ────────────────────                   ──────────────────
  pose_analyzer.py   ─────────────────► analyzer.py
    PoseAnalysisResult                   (포즈 분석 결과 수신)
                                               │
  expression_analyzer.py ─────────────►       │
    ExpressionAnalysisResult             prompt_builder.py
                                         (프리셋 ID 매핑)
  presets.py         ─────────────────►       │
    load_pose_presets()                        │
    load_expression_presets()            generator.py ──► validator.py
                                         (이미지 생성)     (5-Gate 검수)
  hair_analyzer.py   ─────────────────►
    (brandcut에서는 미사용,              retry_generator_v2.py
     ai_influencer 전용)                 (탈락 시 프롬프트 수정)
```

---

## 레이어별 설명

### Layer 1 -- 공유 인프라

| 파일 | 역할 |
|------|------|
| `core/config.py` | 허용 모델명 상수 정의. 모든 워크플로가 `IMAGE_MODEL`, `VISION_MODEL` import |
| `core/api.py` | Gemini API 래퍼. API 키 로테이션(thread-safe), 재시도 로직 포함 |
| `core/options.py` | 비율/해상도/비용의 단일 진실 공급원(SSOT). 하드코딩 금지 |
| `core/policy.py` | 금지 모델 목록 관리. Hook에서 자동 감지에 사용 |
| `core/utils.py` | PIL<->API 변환 유틸. `pil_to_part()` 등 공통 함수 |

### Layer 2 -- 공유 분석기 (VLM 기반)

| 분석기 | 출력 타입 | [LIVE] 사용처 | [PLAN] 확장 가능 |
|--------|-----------|---------------|-------------------|
| `outfit_analyzer.py` | `OutfitAnalysis` | brandcut, ai_influencer, outfit_swap | 제품디자인, 마네킹착장 |
| `background_analyzer.py` | 텍스트 설명 | background_swap, brandcut | 제품연출 |
| `pose_analyzer.py` | `PoseAnalysisResult` | brandcut, ai_influencer | 마네킹포즈, pose_change |
| `expression_analyzer.py` | `ExpressionAnalysisResult` | brandcut, ai_influencer | - |
| `hair_analyzer.py` | 헤어 설명 | ai_influencer 전용 | - |
| `face_analyzer.py` | 얼굴 특징 | ai_influencer 전용 | - |

### Layer 3 -- 프리셋 데이터베이스

| DB 파일 | 내용 | 로더 | 상태 |
|---------|------|------|------|
| `pose_presets.json` | 포즈 ID -> 프롬프트 매핑 | `ai_influencer/presets.py` | [LIVE] |
| `expression_presets.json` | 표정 ID -> 프롬프트 매핑 | `ai_influencer/presets.py` | [LIVE] |
| `background_presets.json` | 배경 ID -> 배경 설명 | (직접 로드) | [LIVE] |
| `scene_presets.json` | 시나리오 -> UGC/셀카 배경 | `selfie/db_loader.py` | [DEV] |
| `fit_presets.json` | 핏 변형 옵션 | (직접 로드) | [DEV] |
| `fabric_library.json` | 원단/소재 텍스처 | (미구현) | [PLAN] |

### Layer 4 -- 워크플로 모듈

각 워크플로는 표준 4-파일 구조를 따른다:

```
{workflow}/
+-- analyzer.py          <- VLM 분석 (Phase 1)
+-- prompt_builder.py    <- 프롬프트 조립 (Phase 2)
+-- generator.py         <- 이미지 생성 (Phase 3)
+-- validator.py         <- 품질 검수 (Phase 4)
+-- retry_generator.py   <- 재시도 로직 (Phase 4)
+-- templates.py         <- 브랜드별 프롬프트 템플릿
```

### 검증 프레임워크

```python
@ValidatorRegistry.register(WorkflowType.BRANDCUT)
class BrandcutValidator(WorkflowValidator):
    def validate(self, generated, references) -> CommonValidationResult:
        ...
```

`generate_with_workflow_validation()`이 레지스트리에서 해당 워크플로의 검증기를
자동으로 조회하여 생성 -> 검증 -> 재시도 루프를 실행한다.

---

## 범례

```
상태 표시
  [LIVE]   운영 중 — 실무 투입 가능, 검증 완료
  [DEV]    개발 중 — 코드 구현 완료, 실무 테스트 단계
  [PLAN]   개발 예정 — 코어 모듈 조합으로 빠르게 구현 가능

기호
  ──►   데이터 흐름 / 호출 방향
  ├──   분기 (여러 대상으로 전달)
  │     계층 구분선
  ┌─┐   모듈 / 컴포넌트 박스
  ╔═╗   시스템 경계 박스

Phase 구분
  Phase 1  : ANALYZE   — gemini-3-flash-preview (VLM)
  Phase 2  : BUILD     — 프롬프트 조립 (코드 로직)
  Phase 3  : GENERATE  — gemini-3-pro-image-preview (이미지)
  Phase 4  : VALIDATE  — VLM 검수 + 재시도 루프

워크플로 수 (2026.03 기준)
  [LIVE]  4개    brandcut, ai_influencer, background_swap, outfit_swap
  [DEV]   8개    face_swap, selfie, pose_change, pose_copy,
                 multi_face_swap, ecommerce, fit_variation, seeding_ugc
  [PLAN]  8개+   제품디자인, 소재생성, 슈즈3D, 제품연출,
                 그래픽, 마네킹착장, 마네킹포즈, 채널배너 ...
```
