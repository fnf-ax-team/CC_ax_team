# CLAUDE.md - FNF AI Studio

> Claude Code가 이미지 생성 작업 시 참조하는 절대 규칙.

## Project Overview

FNF Studio — AI 이미지 생성 플랫폼.
패션 브랜드 화보, 배경 교체, 인플루언서 컨텐츠, 제품 연출 등
다양한 워크플로를 Gemini API 기반으로 실행한다.

---

## 사용자 컨텍스트

### 담당자 정보

| 항목 | 내용 |
|------|------|
| **소속** | F&F / F&Co (패션·뷰티 브랜드 기업) |
| **팀** | AX팀 (AI Transformation) |
| **역할** | 생성형 AI 비주얼 담당 |

### 업무 목표

**오프라인 촬영 업무 → AI 전환**

현재 스튜디오에서 실제로 찍고 있는 다음 업무들을 AI로 대체:

| 업무 유형 | 설명 | 핵심 요구사항 |
|----------|------|--------------|
| 화보컷 | 브랜드 캠페인, 시즌 룩북 | 브랜드 톤 & 무드 일치 |
| 이커머스 | 상세페이지, 스튜디오 촬영 | 착장 디테일 정확도 |
| 제품 디자인 | 신제품 시안, 그래픽 | 브랜드 DNA 반영 |
| 마케팅 콘텐츠 | SNS, 광고 소재 | 자연스러움 + 브랜드 일관성 |

### 브랜드 톤 기본 방향

**모던함이 베이스** — 여기에 브랜드별 컨셉이 레이어링됨

### 워크플로 카테고리 (자동 적용)

새 워크플로 생성 시 카테고리만 지정하면 제약 조건 자동 적용.

| 카테고리 | 얼굴 | 착장 | 브랜드톤 | 해당 워크플로 |
|----------|-----|------|---------|--------------|
| **인물-정규** | 필수 | 필수 | 필수 | 화보컷, 이커머스, 브랜드컷 |
| **인물-자유** | 필수 | 제공시 | 중요 | 인플루언서, UGC, 셀카 |
| **스왑** | 상황별 | 상황별 | 중요 | 얼굴교체, 착장스왑, 포즈변경 |
| **배경** | 유지 | 유지 | 중요 | 배경 교체, 배경 합성 |
| **제품** | X | X | 필수 | 제품 디자인, 제품 연출, 슈즈 3D |
| **그래픽** | X | X | 필수 | 그래픽 생성, 소재 생성 |
| **VMD** | X | 필수 | 중요 | 마네킹 착장, 마네킹 포즈 |
| **수정** | 유지 | 유지 | - | 후보정, 인페인팅, 재질 조절 |

**스왑 카테고리 세부:**
- 얼굴교체: 얼굴만 변경, 착장/포즈 유지
- 착장스왑: 착장만 변경, 얼굴/포즈 유지
- 포즈변경: 포즈만 변경, 얼굴/착장 유지

**착장 규칙:**
- 착장 이미지 제공됨 → 디테일 정확히 재현 필수
- 착장 이미지 없음 → 브랜드 톤 내에서 자유

### 담당 브랜드 (우선순위)

| 순위 | 브랜드 | 특징 | 상태 |
|------|--------|------|------|
| 1 | **MLB** | 스트릿/캐주얼, 빅로고 | **집중** |
| 2 | Discovery | 아웃도어/액티브 | 예정 |
| 3 | Duvetica | 프리미엄 다운 | 예정 |
| 4 | Sergio Tacchini | 스포츠/레트로 | 예정 |
| 5 | Banila Co | K-뷰티/스킨케어 | 예정 |

> 브랜드 DNA는 **워크플로 스킬 폴더 내 치트시트**로 관리한다.
> 예: `.claude/skills/브랜드컷_brand-cut/mlb-prompt-cheatsheet.md`

### Claude에게 바라는 점

- **워크플로별 제약 조건 구분** — 모든 워크플로에 동일 규칙 적용 X
- **브랜드 규칙 준수** — 치트시트에 없는 스타일 임의 적용 금지
- **품질 > 속도** — 검수 탈락보다 처음부터 정확하게
- **애매하면 질문** — 브랜드/스타일 불명확 시 먼저 확인
- **MLB 우선** — 현재 MLB 브랜드에 집중

---

## Gemini API 절대 규칙

모든 이미지 생성 작업에 항상 적용. 위반 시 전체 삭제 후 재생성.

### 모델

| 용도 | 모델 | 비고 |
|------|------|------|
| 이미지 생성 | `gemini-3-pro-image-preview` | 유일하게 허용 |
| VLM 분석 | `gemini-3-flash-preview` | 착장/컨셉/검수 분석 |

```python
from core.config import IMAGE_MODEL, VISION_MODEL
# 절대 금지: gemini-2.0-flash-exp, gemini-2.0-flash, gemini-2.5-flash
```

### 해상도

| 설정 | 해상도 | 용도 |
|------|--------|------|
| `1K` | 1024px | 테스트 |
| `2K` | 2048px | **기본값** |
| `4K` | 4096px | 최종 결과물 |

### API 키 관리

```bash
# .env format - multiple keys for rate limit rotation
GEMINI_API_KEY=key1,key2,key3,key4,key5
```

반드시 `get_next_api_key()` 패턴으로 thread-safe 로테이션 사용. 단일 키 하드코딩 금지.

### 에러 처리 표준

| 에러 | 코드 | 재시도 가능 |
|------|------|------------|
| 429 / rate limit | RATE_LIMIT | Yes (대기 후) |
| 503 / overloaded | SERVER_OVERLOAD | Yes (대기 후) |
| timeout | TIMEOUT | Yes (대기 후) |
| 401 / api key | AUTH_ERROR | No |
| safety / blocked | SAFETY_BLOCK | No |

재시도 시 `(attempt + 1) * 5`초 대기, 최대 3회.

### API 설정 패턴

```python
config=types.GenerateContentConfig(
    temperature=0.7,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="3:4",
        image_size="2K"
    )
)
```

---

## 공통 워크플로 패턴

모든 워크플로는 이 4단계를 따른다:

```
1. 분석 (VLM)     — gemini-3-flash-preview로 참조 이미지 분석
2. 생성 (Image)   — gemini-3-pro-image-preview로 이미지 생성
3. 검수 (VLM)     — gemini-3-pro-image-preview로 워크플로별 검수 기준으로 품질 판정
4. 재생성 (Loop)   — gemini-3-flash-preview로 탈락 시 원인 진단 → 프롬프트 수정 → gemini-3-pro-image-preview로 재생성 (최대 2회)
```

### 검수+재생성 로직 필수 (CRITICAL)

**모든 이미지 생성 워크플로는 반드시 검수+재생성 로직을 포함해야 한다.**

위반 시: 검수 없이 생성된 이미지는 품질 보장 불가 → 사용자에게 불량 이미지 전달 위험

#### 필수 패턴 (2가지 중 택 1)

**방법 1: 워크플로 모듈의 generate_with_validation() 사용**
```python
from core.brandcut import generate_with_validation

result = generate_with_validation(
    prompt_json=prompt,
    face_images=face_imgs,
    outfit_images=outfit_imgs,
    api_key=api_key,
    max_retries=2,  # 필수: 최소 2회 재시도
)
# result = {"image": PIL.Image, "score": int, "passed": bool, "criteria": dict, "history": list}
```

**방법 2: 통합 generate_with_workflow_validation() 사용**
```python
from core.generators import generate_with_workflow_validation
from core.validators import WorkflowType

result = generate_with_workflow_validation(
    workflow_type=WorkflowType.BRANDCUT,  # 워크플로 타입 지정
    generate_func=my_generate_func,        # 생성 함수
    prompt=prompt,
    reference_images={"face": [...], "outfit": [...]},
    config={"temperature": 0.7},
    max_retries=2,  # 필수: 최소 2회 재시도
)
```

#### 워크플로별 검증기 및 모듈

| 워크플로 | WorkflowType | 모듈 | 검증기 |
|---------|--------------|------|--------|
| 브랜드컷 | `BRANDCUT` | `core.brandcut` | `BrandcutValidator` |
| 배경교체 | `BACKGROUND_SWAP` | `core.background_swap` | `BackgroundSwapValidator` |
| UGC/셀피 | `UGC` / `SELFIE` | `core.selfie` | `UGCValidator` |
| 레퍼런스 브랜드컷 | `REFERENCE_BRANDCUT` | `core.brandcut` | (브랜드컷 검증기 사용) |

#### 금지 패턴

```python
# ❌ 금지: 검수 없이 직접 생성만 호출
image = generate_brandcut(prompt, face_imgs, outfit_imgs)
save_image(image)  # 검수 없이 저장 → 불량 이미지 위험!

# ❌ 금지: max_retries=0 또는 생략
result = generate_with_validation(..., max_retries=0)  # 재시도 없음 → 품질 보장 불가

# ✅ 필수: 항상 generate_with_validation() 또는 generate_with_workflow_validation() 사용
result = generate_with_validation(..., max_retries=2)
if result["passed"]:
    save_image(result["image"])
else:
    # 사용자에게 재생성 제안 또는 경고
```

#### 새 워크플로 추가 시 체크리스트

- [ ] `core/{workflow}/validator.py`에 검증기 구현 (`@ValidatorRegistry.register`)
- [ ] `core/{workflow}/generator.py`에 `generate_with_validation()` 함수 구현
- [ ] 검수 기준 및 우선순위 정의
- [ ] `core/validators/__init__.py`에서 검증기 import 추가
- [ ] CLAUDE.md 품질 검증 기준 섹션에 추가

#### 검증기 위치 (CRITICAL)

**각 워크플로 폴더 안에 검증기 파일이 있어야 한다:**

| 워크플로 | 검증기 파일 | 클래스 |
|----------|-------------|--------|
| 브랜드컷 | `core/brandcut/validator.py` | `BrandcutValidator` |
| 배경교체 | `core/background_swap/workflow_validator.py` | `BackgroundSwapWorkflowValidator` |
| 셀카 | `core/selfie/validator.py` | `SelfieWorkflowValidator` |
| 시딩UGC | `core/seeding_ugc/validator.py` | `UGCValidator` |

**사용법:**
```python
from core.validators import ValidatorRegistry, WorkflowType

validator = ValidatorRegistry.get(WorkflowType.BRANDCUT, client)
result = validator.validate(generated_img, reference_images)
```

### 콘텐츠 타입별 기본 설정

| 타입 | Aspect Ratio | Temperature |
|------|--------------|-------------|
| Brand Cut (에디토리얼) | 3:4 | 0.7 |
| Reference Brand Cut | 3:4 | 0.7 |
| Background Swap | Original | 0.7 |
| Influencer | 9:16 | 0.7 |
| Selfie | 9:16 | 0.7 |
| Daily Casual | 4:5 | 0.7 |
| Seeding UGC | 9:16 | 0.7 |
| Product Shot | 1:1 / 3:4 | 0.7 |
| 자유 생성 | - | 0.7 |
| 실험적/아트 | - | 0.8 |

### 필수 질문 옵션 (모든 이미지 생성 스킬)

**⚠️ 이미지 생성 스킬 실행 시 반드시 아래 옵션들을 사용자에게 질문해야 한다.**

**📌 Single Source of Truth: `core/options.py`**

모든 옵션(비율/해상도/비용)은 `core/options.py`에서 import해서 사용한다. **하드코딩 금지!**

```python
from core.options import (
    ASPECT_RATIOS, RESOLUTIONS, COST_TABLE,
    DEFAULT_ASPECT_RATIO, DEFAULT_RESOLUTION,
    get_cost, get_resolution_px, format_options_for_user
)
```

#### 비율 (Aspect Ratio)

> 정의: `core/options.py` → `ASPECT_RATIOS`

| 비율 | 용도 | 시각화 |
|------|------|--------|
| `1:1` | 정사각/프로필/SNS | `□` |
| `2:3` | 세로 포트레이트 | `▯` |
| `3:2` | 가로 랜드스케이프 | `▭` |
| `3:4` | 세로 화보 (기본) | `▯` |
| `4:3` | 가로 화보 | `▭` |
| `4:5` | 인스타 피드 | `▯` |
| `5:4` | 가로 피드 | `▭` |
| `9:16` | 스토리/릴스/숏폼 | `▯` |
| `16:9` | 유튜브/가로 영상 | `▭` |
| `21:9` | 시네마틱/울트라와이드 | `▭▭` |

#### 수량 & 비용

> 정의: `core/options.py` → `COST_TABLE`, `get_cost()`

| 수량 | 1K~2K 비용 | 4K 비용 |
|------|-----------|---------|
| 1장 | ₩190 | ₩380 |
| 3장 | ₩570 | ₩1,140 |
| 5장 | ₩950 | ₩1,900 |
| 10장 | ₩1,900 | ₩3,800 |

> Gemini API 기준 (2026.02)

#### 화질 (Resolution)

> 정의: `core/options.py` → `RESOLUTIONS`, `get_resolution_px()`

| 화질 | 해상도 | 용도 | 장당 비용 |
|------|--------|------|----------|
| `1K` | 1024px | 테스트/미리보기 | ₩190 |
| `2K` | 2048px | **기본값** (SNS/웹) | ₩190 |
| `4K` | 4096px | 최종 결과물/인쇄 | ₩380 |

#### 워크플로별 기본값

> 정의: `core/options.py` → `WORKFLOW_DEFAULTS`, `get_workflow_defaults()`

```python
from core.options import get_workflow_defaults

defaults = get_workflow_defaults("brandcut")
aspect_ratio = defaults.aspect_ratio  # "3:4"
temperature = defaults.temperature    # 0.7
```

---

## 브랜드 규칙

- 이미지 생성 전 반드시 해당 브랜드의 **치트시트 로드**
- 치트시트에 없는 스타일 임의 적용 금지
- 브랜드 미감지 시 사용자에게 질문

### 브랜드 치트시트 (Brand Cheatsheet)

브랜드별 치트시트에 브랜드 DNA, 프롬프트 옵션, 조합규칙, 금지 조합이 모두 포함.

**위치**: `.claude/skills/{워크플로_스킬폴더}/{브랜드}-prompt-cheatsheet.md`

| 브랜드 | 치트시트 | 상태 |
|--------|---------|------|
| MLB | `브랜드컷_brand-cut/mlb-prompt-cheatsheet.md` | ✅ |
| Discovery | (예정) | 🔜 |
| Duvetica | (예정) | 🔜 |
| Sergio Tacchini | (예정) | 🔜 |
| Banila Co | (예정) | 🔜 |

**치트시트 구성**:
- JSON 스키마 (프롬프트 구조)
- 기본값 (미입력시 자동 적용)
- 브랜드 DNA (DO & DON'T)
- 옵션 → 프롬프트 매핑표
- 호환 규칙 / 금지 조합
- 네거티브 프롬프트

### 프롬프트 스키마 규칙 (CRITICAL)

**브랜드컷 등 인물 워크플로는 반드시 JSON 스키마 형태로 프롬프트를 구성한다.**

1. **전체 한국어 작성** — 필드명, 값, 주석 모두 한국어로 작성 (담당자가 직접 검토/수정 가능하도록)
2. **문장형 프롬프트** — 단어 나열이 아닌, 맥락을 이해할 수 있는 완전한 문장으로 작성
3. **주석으로 규칙 명시** — `[필수]`, `[선택]`, `[고정]` 태그 사용
4. **기본값 명시** — 미입력 시 적용될 값 표기
5. **호환 규칙 참조** — 조합 제약사항 명시

> **왜 한국어 + 문장형?**
> - 담당자가 프롬프트를 직접 검토/수정할 수 있음
> - AI가 맥락을 정확히 이해하여 의도대로 생성
> - 브랜드 용어의 뉘앙스를 정확히 전달

**표준 스키마 구조**:

```json
{
  "주제": {
    "character": "필름 그레인 질감, 에디토리얼 패션 사진 스타일"
  },
  "모델": {
    "민족": "",               // [필수] 기본값: korean
    "성별": "",               // [필수] 기본값: female
    "나이": ""                // [선택] 기본값: early_20s
  },
  "헤어": {
    "스타일": "",             // [선택] 기본값: straight_loose
    "컬러": "",               // [선택] 기본값: dark_brown
    "질감": ""                // [선택] 기본값: sleek
  },
  "메이크업": {
    "베이스": "",             // [선택] 기본값: natural
    "블러셔": "",             // [선택]
    "립": "",                 // [선택]
    "아이": ""                // [선택]
  },
  "촬영": {
    "프레이밍": "",           // [필수]
    "렌즈": "",               // [선택] 기본값: 50mm
    "앵글": "",               // [선택] 기본값: 3/4측면
    "높이": "",               // [선택] 기본값: 살짝로앵글
    "구도": "",               // [선택] 기본값: 중앙
    "조리개": ""              // [고정] f/2.8
  },
  "포즈": {
    "preset_id": "",          // [권장] 프리셋 ID 사용
    "custom_mode": false,     // true면 아래 custom 필드 사용
    "custom": {
      "stance": "",           // stand, lean_wall, sit, walk
      "왼팔": "",
      "오른팔": "",
      "왼손": "",
      "오른손": "",
      "왼다리": "",
      "오른다리": "",
      "힙": ""                // weight distribution
    }
  },
  "표정": {
    "베이스": "",             // [필수] cool, natural, dreamy
    "바이브": "",             // [선택] mysterious, approachable
    "눈": "",                 // [필수] 기본값: 큰 아몬드눈 (MLB 브랜드 DNA)
    "시선": "",               // [선택] 기본값: direct
    "입": ""                  // [선택] 기본값: closed
  },
  "착장": {
    "아우터": "",             // [선택]
    "상의": "",               // [필수] "MLB {색상} {아이템} with {로고색} logo"
    "하의": "",               // [필수]
    "신발": "",               // [선택]
    "헤드웨어": "",           // [선택]
    "주얼리": "",             // [선택]
    "가방": "",               // [선택]
    "벨트": ""                // [선택]
  },
  "코디방법": {
    "아우터": "",             // [선택] 정상착용, 어깨걸침, 지퍼오픈 등
    "상의": "",               // [선택] 크롭, 넣어입기, 한쪽어깨노출 등
    "하의": "",               // [선택]
    "신발": "",               // [선택]
    "헤드웨어": "",           // [선택] 뒤로쓰기, 옆으로쓰기 등
    "주얼리": "",             // [선택]
    "가방": "",               // [선택]
    "벨트": ""                // [선택]
  },
  "배경": {
    "장소": "",               // [필수] ⚠️ 포즈와 호환 확인
    "배경상세": ""            // [선택]
  },
  "조명색감": {
    "조명": "",               // [선택] 기본값: 소프트박스 ⚠️ 골든아워 금지
    "색보정": ""              // [선택] 기본값: 뉴트럴쿨 ⚠️ 따뜻한 톤 금지
  },
  "출력품질": "professional fashion photography, high-end editorial, sharp focus, 8K quality",
  "네거티브": ""              // [필수] 기본: bright smile, teeth showing, golden hour, warm amber
}
```

**주석 태그 규칙**:

| 태그 | 의미 | 처리 |
|------|------|------|
| `[필수]` | 반드시 입력 | 누락 시 에러 |
| `[선택]` | 선택 입력 | 누락 시 기본값 또는 생략 |
| `[고정]` | 변경 불가 | 항상 고정값 사용 |
| `[권장]` | 사용 권장 | 프리셋 ID 등 |

---

## 워크플로 & 스킬

### 인물

| 워크플로 | 스킬 | 설명 | 상태 |
|---------|------|------|------|
| 브랜드컷 | `brand-cut` | 브랜드 화보 생성 | ✅ |
| 레퍼런스 브랜드컷 | `reference-brandcut` | 페이스스왑+착장스왑+배경변경 | ✅ |
| 인플루언서 | `influencer` | 인플루언서/셀럽 이미지 | ✅ |
| 배경 합성 | `background-swap` | 배경 교체 | ✅ |
| 시딩 UGC | `seeding-ugc` | UGC 생성 | ✅ |

## 개발 예정 워크플로 & 스킬

### 인물

| 워크플로 | 스킬 | 설명 | 상태 |
|---------|------|------|------|
| 얼굴 교체 | - | 얼굴 스왑 | 🔜 |
| 다중 얼굴 교체 | - | 단체 사진 얼굴 교체 | 🔜 |
| 포즈 변경 | - | 기존 이미지 포즈 변경 | 🔜 |
| 포즈 따라하기 | - | 레퍼런스 포즈 복제 | 🔜 |
| 착장 | - | 착장 스왑 | 🔜 |
| 이커머스 | - | 이커머스용 모델 이미지 | 🔜 |

### 제품

| 워크플로 | 스킬 | 설명 | 상태 |
|---------|------|------|------|
| AI 제품 디자인 | `product-design` | AI 제품 디자인 생성/변형 | ✅ |
| 캐드 실사화 | - | CAD → 실사 렌더링 | ✅ |
| 소재 이미지 생성 | `fabric-generation` | 원단/소재 텍스처 생성 | ✅ |
| 제품 턴테이블 | - | 제품 360도 뷰 | ✅ |
| 제품 연출컷 | `product-styled` | 제품 상세페이지/연출 | ✅ |
| 슈즈 3D | `shoes-3d` | 신발 3D 모델 생성 | ✅ |

### 그래픽

| 워크플로 | 설명 | 상태 |
|---------|------|------|
| 그래픽 생성 | 빅럭셔리, 메가로고, 커서브, 핫서머, 바시티, 빈티지 | 🔜 |

### VMD/인테리어

| 워크플로 | 설명 | 상태 |
|---------|------|------|
| 마네킹 착장 | 마네킹에 착장 입히기 | 🔜 |
| 마네킹 포즈 변경 | 마네킹 포즈 변경 | 🔜 |

### 비디오

| 워크플로 | 설명 | 상태 |
|---------|------|------|
| 참조 비디오 따라하기 | 레퍼런스 비디오 기반 생성 | 🔜 |
| 영상 부분 샷 수정 | 비디오 특정 구간 수정 | 🔜 |
| 유튜브 다운로드 | 유튜브 영상 다운로드 | 🔜 |

### 수정/후처리

| 워크플로 | 설명 | 상태 |
|---------|------|------|
| 후보정 | 이미지 후보정 | 🔜 |
| 재질 광택 조절 | 소재 질감/광택 수정 | 🔜 |
| 빨간 펜 피드백 | 피드백 기반 수정 | 🔜 |
| 인페인팅 | 부분 영역 재생성 | 🔜 |

### 검수 스킬

| 스킬 | 설명 |
|------|------|
| `validate-brandcut` | 브랜드컷 5-Gate 검수 (참조 이미지 기반) |
| 배경교체 검수표 | 9-criteria 검수 |

### 유틸리티 스킬

| 스킬 | 설명 |
|------|------|
| `image-gen-reference` | 공통 코드 패턴, 유틸리티 함수, 프롬프트 템플릿 |
| `showcase-builder` | 쇼케이스 사이트 구축/업데이트 (디자인 가이드 필수 참조) |

---

## 품질 검증 기준

### 브랜드컷 — 5-Gate 순차 검증

탈락 시 다음 Gate 안 봄.

| Gate | 체크 대상 | 탈락 조건 | 비교 대상 |
|------|----------|----------|----------|
| 1 | 착장 | 누락/색상/로고/디테일/실루엣 불일치 | 착장 이미지 |
| 2 | 얼굴 | 다른 사람/비율/피부톤 불일치 | 얼굴 이미지 |
| 3 | 포즈 | 관절/체중/손가락/접지/배경호환 어색 | 자체 판단 |
| 4 | 브랜드 톤 | 치트시트 금지 요소 위반 | 브랜드 치트시트 |
| 5 | 품질 마감 | ⚠️ 3개 이상 | 자체 판단 |

- Gate 1~4: FAIL → 즉시 재생성
- Gate 5: ⚠️ 0개=100, 1개=98, 2개=95, 3개+=재생성
- 재생성 최대 2회. 같은 Gate 2연속 → 안전 폴백

### 배경교체 — 9-criteria 검증

| # | 항목 | 영문 | 비중 | Pass 기준 |
|---|------|------|------|----------|
| 1 | 인물 보존 | model_preservation | 25% | = 100 (필수) |
| 2 | 리라이트 자연스러움 | relight_naturalness | 15% | - |
| 3 | 조명 일치 | lighting_match | 12% | - |
| 4 | 접지감 | ground_contact | 12% | - |
| 5 | 물리 타당성 | physics_plausibility | 10% | ≥ 50 (필수) |
| 6 | 경계 품질 | edge_quality | 8% | - |
| 7 | 스타일 일치 | prop_style_consistency | 8% | - |
| 8 | 색온도 준수 | color_temperature_compliance | 5% | ≥ 80 (필수) |
| 9 | 원근 일치 | perspective_match | 5% | - |

Pass: `인물보존 = 100` AND `물리타당성 ≥ 50` AND `색온도 ≥ 80` AND `총점 ≥ 90`

### UGC, 셀피 검증

| 항목 | 비중 |
|------|------|
| realism | 35% |
| person_preservation | 25% |
| scenario_fit | 20% |
| skin_condition | 10% |
| anti_polish_factor | 10% |

원칙: "너무 잘 나오면 실패"

### 공통 Auto-Fail (모든 워크플로)

- 손가락 6개 이상 / 기형적 손가락
- 얼굴 다른 사람
- 착장 색상/로고 불일치
- 체형 불일치
- 누런 톤 (golden/amber/warm cast)
- 의도하지 않은 텍스트/워터마크
- AI 특유 플라스틱 피부

---

## VLM 검수 프롬프트 작성 원칙 (CRITICAL)

**VLM에게 비교/평가를 요청할 때 반드시 지켜야 할 원칙.**

### 문제: VLM은 지시를 건너뛴다

```
❌ 잘못된 방식:
"[POSE REFERENCE]와 비교하세요. 다르면 70점 이하!"

→ VLM이 "비교하라"는 지시를 무시하고 일반 평가만 함
→ 레퍼런스와 완전히 달라도 92점
```

### 원칙 1: 지시만 하지 말고 강제하라

```
❌ "A와 B를 비교하세요"
✅ "STEP 1: A 분석하여 적으세요, STEP 2: B 분석하여 적으세요, STEP 3: 비교하세요"
```

VLM이 건너뛸 수 없도록 **단계별로 출력을 강제**한다.

### 원칙 2: 출력 형식을 명시하라

```
❌ "사유를 적으세요"
✅ "reason 필수 형식: 'REF:~, GEN:~, 감점:~'"
```

형식이 없으면 VLM은 모호한 답변을 한다. **구체적 형식을 강제**한다.

### 원칙 3: 계산을 강제하라

```
❌ "다르면 -20점"
✅ "앵글: 같음(0) / 다름(-20) → 감점 합계 = ?점, 최종 = 100 - 감점"
```

VLM이 계산을 건너뛰지 않도록 **공식을 명시**한다.

### 적용 예시 (pose_quality)

```
### 12. pose_quality ★★★ [POSE REFERENCE]와 반드시 비교! ★★★

[STEP 1] POSE REFERENCE 분석:
- REF 앵글 = ?
- REF 프레이밍 = ?

[STEP 2] GENERATED IMAGE 분석:
- GEN 앵글 = ?
- GEN 프레이밍 = ?

[STEP 3] 비교 및 감점:
- 앵글: 같음(0) / 다름(-20)
- 프레이밍: 같음(0) / 다름(-15)
- 합계 감점 = ?

[STEP 4] 최종 점수 = 100 - 합계 감점

reason 필수 형식: "REF:로우앵글+전신, GEN:아이레벨+무릎위, 감점:-35"
```

### 검증 방법

VLM 검수 결과의 `reason` 필드를 확인하여:
- 형식이 지켜졌는지 (REF:~, GEN:~, 감점:~)
- 비교가 실제로 수행되었는지
- 감점 계산이 맞는지

확인한다. 형식이 안 지켜졌으면 프롬프트 수정 필요.

---

## 검수 결과 출력 규칙 (CRITICAL)

**모든 검수 결과는 반드시 아래 형식을 따라야 한다.**

### 언어
- **검수 관련 모든 출력은 한국어로 한다**
- 점수, 등급, 통과 여부, 이슈 사항 등 모두 한국어

### 표 형식 필수

검수 완료 시 반드시 아래 형식의 표를 출력한다:

```
## 검수 결과

| 항목 | 점수 | 기준 | 통과 |
|------|------|------|------|
| 착장 정확도 | 92 | ≥70 | ✓ |
| 얼굴 동일성 | 88 | ≥70 | ✓ |
| 포즈 자연스러움 | 75 | ≥60 | ✓ |
| 브랜드 톤 | 65 | ≥70 | ✗ |
| 품질 마감 | 90 | ≥85 | ✓ |

**총점**: 82/100 | **등급**: B | **판정**: 재검토 필요

### 탈락 사유
- 브랜드 톤: 쿨톤 유지 필요, 현재 약간 웜톤
```

### 워크플로별 검수 항목

**브랜드컷 (5-Gate)**
| 항목 | 영문 | 설명 |
|------|------|------|
| 착장 정확도 | outfit_accuracy | 착장 색상/로고/디테일 일치 |
| 얼굴 동일성 | face_identity | 동일 인물 여부 |
| 포즈 자연스러움 | pose_anatomy | 관절/손가락/접지 |
| 브랜드 톤 | brand_compliance | 브랜드 치트시트 준수 |
| 품질 마감 | quality_finish | 해상도/아티팩트 |

**배경교체 (9-criteria)**
| 항목 | 영문 | 설명 |
|------|------|------|
| 인물 보존 | model_preservation | 인물 완벽 보존 (필수 100) |
| 리라이트 자연스러움 | relight_naturalness | 인물에 배경 조명 반영 |
| 조명 일치 | lighting_match | 광원 방향 일치 |
| 접지감 | ground_contact | 바닥 접촉 자연스러움 |
| 물리 타당성 | physics_plausibility | 물리적 자연스러움 (필수 ≥50) |
| 경계 품질 | edge_quality | 인물-배경 경계 |
| 스타일 일치 | prop_style_consistency | 소품과 배경 조화 |
| 색온도 준수 | color_temperature_compliance | 누런 톤 없음 (필수 ≥80) |
| 원근 일치 | perspective_match | 원근감 일치 |

**UGC/셀피 (5-criteria)**
| 항목 | 영문 | 설명 |
|------|------|------|
| 리얼리즘 | realism | 실제 사진 같은지 |
| 인물 보존 | person_preservation | 인물 동일성 |
| 시나리오 적합성 | scenario_fit | 상황 자연스러움 |
| 피부 상태 | skin_condition | 피부 텍스처 자연스러움 |
| 역검증 | anti_polish_factor | 너무 완벽하면 감점 |

### 검수 모듈 위치

```python
from core.validators import WorkflowType, ValidatorRegistry
from core.generators import generate_with_workflow_validation

# 검증기 가져오기
validator = ValidatorRegistry.get(WorkflowType.BRANDCUT, client)

# 통합 생성+검증
result = generate_with_workflow_validation(
    workflow_type=WorkflowType.BRANDCUT,
    generate_func=my_func,
    prompt=prompt,
    reference_images={"face": [...], "outfit": [...]},
    config={"temperature": 0.7},
)
```

---

## 이미지 전송 규칙

### 브랜드컷 우선순위

| 순위 | 항목 |
|------|------|
| 1 (최우선) | 착장 이미지 전체 전송 (1개도 빠뜨리면 안됨) |
| 2 | 얼굴 이미지 반드시 전송 (1~3장) |
| 3 | 배경/조명 |

### 브랜드컷 (brand-cut) 전송 순서

```
1. 프롬프트 (텍스트) — 컨셉 분석 결과 포함!
2. 얼굴 이미지 (API 직접 전달)
3. 착장 이미지 (API 직접 전달)
```

- 배경: VLM 분석 → 텍스트로만 전달

### 레퍼런스 브랜드컷 (reference-brandcut) 전송 순서 — V4

```
1. 프롬프트 (텍스트) — 각 IMAGE 역할 명시
2. IMAGE 1: 레퍼런스 이미지 (API 직접 전달 — 포즈/표정/구도 보존)
3. IMAGE 2: 얼굴 이미지 (Face Swap)
4. IMAGE 3: 착장 이미지 (Outfit Swap)
5. IMAGE 4: 배경 이미지 (Background Reference) ← V4 추가!
```

- 레퍼런스: API에 직접 전달 (포즈/표정/앵글 정확 보존)
- 배경: **V4에서 API에 직접 전달** (정확한 배경 재현, 인물 무시 지시 필요)

---

## 출력 폴더 구조 (CRITICAL)

**모든 테스트/생성 결과물은 반드시 프롬프트, 인풋, 결과를 함께 저장해야 한다.**

### 기본 구조

```
Fnf_studio_outputs/
└── {workflow}/
    └── {YYYYMMDD_HHMMSS}_{description}/
        ├── images/                    # 인풋 + 아웃풋 통합 (비교 용이)
        │   ├── input_face_01.jpg
        │   ├── input_face_02.jpg
        │   ├── input_outfit_01.jpg
        │   ├── input_outfit_02.jpg
        │   ├── input_reference_01.jpg   # (옵션) 포즈/컨셉 레퍼런스
        │   ├── input_background_01.jpg  # (옵션) 배경 레퍼런스
        │   ├── output_001.jpg
        │   ├── output_002.jpg
        │   └── output_003.jpg
        ├── prompt.json                # 사용된 프롬프트 (JSON)
        ├── prompt.txt                 # 사용된 프롬프트 (가독용 텍스트)
        ├── config.json                # 생성 설정 (비율, 해상도, temperature 등)
        ├── validation.json            # 검수 결과 (점수, 통과 여부, 상세)
        └── README.md                  # (옵션) 실험 목적, 메모
```

### 워크플로별 예시

**브랜드컷:**
```
Fnf_studio_outputs/
└── brand_cut/
    └── 20260220_143052_mlb_summer_casual/
        ├── images/
        │   ├── input_face_01.jpg
        │   ├── input_outfit_01_tanktop.jpg
        │   ├── input_outfit_02_cargo_denim.jpg
        │   ├── output_001.jpg
        │   ├── output_002.jpg
        │   └── output_003.jpg
        ├── prompt.json
        ├── prompt.txt
        ├── config.json
        └── validation.json
```

**배경교체:**
```
Fnf_studio_outputs/
└── background_swap/
    └── 20260220_151230_beach_sunset/
        ├── images/
        │   ├── input_source_model.jpg      # 원본 인물 이미지
        │   ├── input_target_background.jpg # 대체할 배경
        │   └── output_001.jpg
        ├── prompt.json
        ├── config.json
        └── validation.json
```

### 필수 저장 파일

| 파일 | 필수 | 내용 |
|------|------|------|
| `images/` | O | 인풋(`input_*`) + 아웃풋(`output_*`) 통합 폴더 |
| `prompt.json` | O | API에 전송된 프롬프트 (JSON 원본) |
| `prompt.txt` | O | 프롬프트 가독용 텍스트 버전 |
| `config.json` | O | 생성 설정 (aspect_ratio, resolution, temperature 등) |
| `validation.json` | △ | 검수 결과 (검수 실행 시) |
| `README.md` | △ | 실험 목적, 특이사항 메모 |

**파일명 규칙:**
- 인풋: `input_{category}_{번호}.jpg` (예: `input_face_01.jpg`, `input_outfit_01.jpg`)
- 아웃풋: `output_{번호}.jpg` (예: `output_001.jpg`)

### config.json 형식

```json
{
  "workflow": "brand_cut",
  "timestamp": "2026-02-20T14:30:52",
  "model": "gemini-3-pro-image-preview",
  "aspect_ratio": "3:4",
  "resolution": "2K",
  "temperature": 0.7,
  "num_images": 3,
  "cost_per_image": 190,
  "total_cost": 570,
  "retry_count": 1,
  "brand": "MLB"
}
```

### prompt.txt 형식

```
=== PROMPT INFO ===
Workflow: brand_cut
Generated: 2026-02-20 14:30:52
Brand: MLB

=== INPUTS ===
Face: face_01.jpg
Outfits: outfit_tanktop.jpg, outfit_cargo_denim.jpg

=== PROMPT (Korean) ===
[주제]
- character: 필름 그레인 질감, 에디토리얼 패션 사진 스타일
- mood: cool, confident

[모델]
- 민족: korean
- 성별: female
- 나이: early_20s

[착장]
- 상의: MLB white tank top with NY logo
- 하의: MLB cargo denim with NY embroidery

... (전체 프롬프트)

=== CONFIG ===
Aspect Ratio: 3:4
Resolution: 2K
Temperature: 0.7
```

### validation.json 형식

```json
{
  "workflow": "brand_cut",
  "passed": true,
  "total_score": 92,
  "grade": "A",
  "criteria": {
    "outfit_accuracy": {"score": 95, "threshold": 70, "passed": true},
    "face_identity": {"score": 90, "threshold": 70, "passed": true},
    "pose_anatomy": {"score": 88, "threshold": 60, "passed": true},
    "brand_compliance": {"score": 92, "threshold": 70, "passed": true},
    "quality_finish": {"score": 95, "threshold": 85, "passed": true}
  },
  "issues": [],
  "retry_count": 0
}
```

### 저장 코드 패턴 (필수)

```python
from pathlib import Path
from datetime import datetime
import json
import shutil

def save_generation_result(
    workflow: str,
    description: str,
    input_images: dict,      # {"face": [...], "outfit": [...], ...}
    output_images: list,     # [PIL.Image, ...]
    prompt_json: dict,
    config: dict,
    validation: dict = None
):
    """생성 결과를 표준 폴더 구조로 저장"""

    # 폴더 생성 (인풋/아웃풋 통합)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"Fnf_studio_outputs/{workflow}/{timestamp}_{description}")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 1. 인풋 이미지 복사 (input_ 접두사)
    for category, images in input_images.items():
        for i, img_path in enumerate(images):
            dest = images_dir / f"input_{category}_{i+1:02d}{Path(img_path).suffix}"
            shutil.copy(img_path, dest)

    # 2. 결과 이미지 저장 (output_ 접두사)
    for i, img in enumerate(output_images):
        img.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)

    # 3. prompt.json 저장
    with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_json, f, ensure_ascii=False, indent=2)

    # 4. prompt.txt 저장 (가독용)
    prompt_txt = format_prompt_txt(workflow, input_images, prompt_json, config)
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    # 5. config.json 저장
    config["timestamp"] = datetime.now().isoformat()
    config["workflow"] = workflow
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 6. validation.json 저장 (있으면)
    if validation:
        with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
            json.dump(validation, f, ensure_ascii=False, indent=2)

    return output_dir
```

### 금지 패턴

```python
# 결과만 저장하고 프롬프트/인풋 미저장
result.save("output.jpg")  # FORBIDDEN

# timestamp 폴더만 만들고 상세 구조 없음
output_dir = f"outputs/{timestamp}/"
result.save(f"{output_dir}/result.jpg")  # FORBIDDEN
```

### 왜 필요한가?

1. **재현성** — 동일 프롬프트+인풋으로 결과 재생성 가능
2. **디버깅** — 문제 발생 시 원인 추적 (어떤 인풋? 어떤 프롬프트?)
3. **비교** — 다른 설정 간 A/B 테스트 용이
4. **히스토리** — 시간순 변화 추적, 베스트 결과물 선별
5. **공유** — 팀원에게 정확한 재현 조건 전달

---

## 코딩 컨벤션

- 한국어 주석
- 함수명/변수명 영어 snake_case
- 모델명은 `core/config.py`에서 import
- **옵션(비율/해상도/비용)은 `core/options.py`에서 import** (하드코딩 금지!)
- API 키는 `.env`에서 로드
- 에러 시 최대 3회 재시도 (`(attempt + 1) * 5`초 대기)

---

## 정책 규칙 (.claude/rules/)

각 정책 파일에서 상세 규칙 참조:

| 파일 | 내용 |
|------|------|
| `gemini-policy.md` | Gemini API 모델/키/재시도 규칙 |
| `image-options.md` | 비율/해상도/비용 (core/options.py 참조) |
| `workflow-template.md` | 워크플로 4단계 구조, 검수+재생성 필수 |

---

## 자동 검증 Hooks

| Hook | 감지 대상 | 결과 |
|------|----------|------|
| `validate_gemini_model.py` | 금지 모델 사용 | 경고 + 피드백 |
| `validate_options.py` | 옵션 하드코딩 | 경고 + import 안내 |
| `validate_workflow.py` | 검수 없는 저장 | 경고 + 필수 패턴 안내 |

**위반 시 Claude에게 피드백 전달 → 자동 수정 유도**

---

## 테스트 코드 규칙

**모든 테스트/실험 코드는 `tests/` 폴더에 작성한다. 루트에 test_*, temp_*, run_* 파일 생성 금지.**

### 폴더 구조

```
tests/
├── brandcut/       # 브랜드컷 테스트
├── background/     # 배경 교체 테스트
├── influencer/     # 인플루언서 테스트
├── validation/     # 검수/검증 테스트
├── integration/    # 전체 파이프라인 테스트
├── pipeline/       # 배치/파이프라인 실행 스크립트
├── style/          # 스타일/컨셉 테스트
├── vlm/            # VLM 분석 테스트
└── experiments/    # 일회성 실험 (날짜 prefix 권장)
```

### 파일 네이밍

| 폴더 | 네이밍 패턴 | 예시 |
|------|------------|------|
| 워크플로별 | `test_{기능}_{상세}.py` | `test_mlb_brandcut_v2.py` |
| experiments | `{날짜}_{설명}.py` | `2026-02-11_fabric_test.py` |
| pipeline | `run_{워크플로}_{배치명}.py` | `run_berlin_full_batch.py` |

### 규칙

1. **새 테스트 생성 시** 해당 워크플로 폴더에 작성
2. **일회성 실험**은 `experiments/`에 날짜 prefix로 작성
3. **루트 폴더**에 테스트 파일 직접 생성 금지
4. **공용 유틸**은 `tests/conftest.py` 또는 `tests/utils.py`에 작성

### 필수 패턴 (테스트 코드 작성 시)

**1. .env 로드 (API 키)**

```python
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드 - 반드시 core 모듈 import 전에!
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 이제 core 모듈 import
from core.api import get_next_api_key
```

**2. 이모지 사용 금지 (Windows cp949 인코딩 이슈)**

```python
# ❌ 금지 - UnicodeEncodeError 발생
print("📷 이미지 생성 완료!")
print("✅ 저장됨")

# ✅ 권장 - ASCII 문자만 사용
print("[IMAGE] Generation complete!")
print("[OK] Saved")
```

**3. 한글 출력도 주의**

```python
# 콘솔에서 한글 깨질 수 있음
# 중요한 정보는 영어로, 부가 정보만 한글로
print(f"[OUTPUT] {output_path}")  # 경로는 영어
print(f"# Generating image {i+1}/{total}...")  # 상태도 영어
```

**4. 이미지 생성 옵션 (필수 주석)**

```python
# ============================================================
# OPTIONS (change these values)
# ============================================================
# aspect_ratio: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
# resolution: "1K", "2K", "4K"
# num_images: 1, 3, 5, 10
# cost: 1K~2K = 190원/장, 4K = 380원/장
# ============================================================
NUM_IMAGES = 3
ASPECT_RATIO = "3:4"  # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
RESOLUTION = "2K"     # "1K", "2K", "4K"
```

**5. 결과 저장 필수 패턴 (CRITICAL)**

> "출력 폴더 구조" 섹션의 표준 패턴을 테스트 코드에서도 반드시 적용한다.

```python
from pathlib import Path
from datetime import datetime
import json
import shutil

def run_test():
    # ============================================================
    # TEST CONFIG
    # ============================================================
    WORKFLOW = "brand_cut"
    DESCRIPTION = "mlb_summer_tanktop"  # 테스트 설명 (영어, 언더스코어)

    # 인풋 이미지 경로
    FACE_IMAGES = ["inputs/face_model_a.jpg"]
    OUTFIT_IMAGES = ["inputs/outfit_tanktop.jpg", "inputs/outfit_cargo.jpg"]

    # ============================================================
    # OUTPUT SETUP (수정 금지)
    # ============================================================
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"Fnf_studio_outputs/{WORKFLOW}/{timestamp}_{DESCRIPTION}")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1. 인풋 이미지 복사 (input_ 접두사로 구분)
    # ============================================================
    for i, img_path in enumerate(FACE_IMAGES):
        shutil.copy(img_path, images_dir / f"input_face_{i+1:02d}{Path(img_path).suffix}")
    for i, img_path in enumerate(OUTFIT_IMAGES):
        shutil.copy(img_path, images_dir / f"input_outfit_{i+1:02d}{Path(img_path).suffix}")

    # ============================================================
    # 2. 프롬프트 생성 (워크플로별 모듈 사용)
    # ============================================================
    prompt = build_prompt(...)  # 워크플로별 프롬프트 빌더

    # ============================================================
    # 3. 이미지 생성
    # ============================================================
    result = generate_with_validation(
        prompt_json=prompt,
        face_images=FACE_IMAGES,
        outfit_images=OUTFIT_IMAGES,
        max_retries=2,
    )

    # ============================================================
    # 4. 결과 저장 (프롬프트 + 설정 + 검수 결과 포함)
    # ============================================================
    # 4-1. 결과 이미지 (output_ 접두사로 구분)
    for i, img in enumerate(result["images"]):
        img.save(images_dir / f"output_{i+1:03d}.jpg", quality=95)

    # 4-2. prompt.json (API에 전송된 원본)
    with open(output_dir / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt, f, ensure_ascii=False, indent=2)

    # 4-3. prompt.txt (가독용)
    prompt_txt = f"""=== TEST INFO ===
Workflow: {WORKFLOW}
Description: {DESCRIPTION}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

=== INPUTS ===
Face: {", ".join(FACE_IMAGES)}
Outfits: {", ".join(OUTFIT_IMAGES)}

=== PROMPT ===
{json.dumps(prompt, ensure_ascii=False, indent=2)}

=== CONFIG ===
Aspect Ratio: {ASPECT_RATIO}
Resolution: {RESOLUTION}
Temperature: 0.7
Num Images: {NUM_IMAGES}
"""
    with open(output_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    # 4-4. config.json
    config = {
        "workflow": WORKFLOW,
        "description": DESCRIPTION,
        "timestamp": datetime.now().isoformat(),
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "temperature": 0.7,
        "num_images": NUM_IMAGES,
        "cost_per_image": 190,
        "total_cost": NUM_IMAGES * 190,
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 4-5. validation.json (검수 결과)
    if result.get("validation"):
        with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
            json.dump(result["validation"], f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved to: {output_dir}")
    return output_dir
```

### 테스트 결과 저장 체크리스트

테스트 코드 작성/수정 시 반드시 확인:

- [ ] `images/` 폴더에 인풋(`input_*`) 이미지 복사됨
- [ ] `images/` 폴더에 아웃풋(`output_*`) 이미지 저장됨
- [ ] `prompt.json` 저장됨 (API 전송 원본)
- [ ] `prompt.txt` 저장됨 (가독용)
- [ ] `config.json` 저장됨 (비율, 해상도, temperature 등)
- [ ] `validation.json` 저장됨 (검수 실행 시)

### 테스트 금지 패턴

```python
# FORBIDDEN: 결과만 저장
result.save("test_output.jpg")

# FORBIDDEN: 프롬프트 미저장
for i, img in enumerate(results):
    img.save(f"output_{i}.jpg")

# FORBIDDEN: 인풋 미복사
output_dir = Path("outputs/test1")
# 인풋 복사 없이 바로 생성...
```
