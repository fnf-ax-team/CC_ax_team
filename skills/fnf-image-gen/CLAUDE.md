# CLAUDE.md - FNF 이미지 생성 스킬 규칙

> 이 파일은 Claude Code가 이미지 생성 작업 시 참조하는 절대 규칙입니다.
> `skills/fnf-image-gen/` 폴더에 위치하여 팀원 전체에게 적용됩니다.

## Project Overview

FNF Studio is an AI-powered image generation platform for fashion brand photography. It uses the Gemini API to generate and edit images with background replacement, brand-specific styling, and quality validation workflows.

---

## Gemini API 절대 규칙

이 섹션의 규칙은 **모든 이미지 생성 작업에 항상 적용**됩니다. 위반 시 생성물 전체 삭제 후 재생성 필요.

### 모델 선택

```python
# 무조건 이것만 사용
IMAGE_MODEL = "gemini-3-pro-image-preview"

# 절대 금지 (아래 모델 사용 금지)
# "gemini-2.0-flash-exp-image-generation"  → 인물 축소, 배경 합성 품질 낮음, 색감 불일치
# "gemini-2.0-flash"                       → 위와 동일
# "gemini-2.5-flash"                       → 텍스트 전용, 최대 1024px만 지원
```

### 해상도 설정

| 설정 | 해상도 (1:1 기준) | 용도 |
|------|------------------|------|
| `1K` | 1024x1024 | 테스트용 |
| `2K` | 2048x2048 | **일반 제작용 (기본값)** |
| `4K` | 4096x4096 | 고품질 최종 결과물 |

### 콘텐츠 타입별 기본 설정 (Template + Aspect Ratio + Temperature)

| 타입 | Template | Aspect Ratio | Temperature | 설명 |
|------|----------|--------------|-------------|------|
| Editorial/Brand Cut | editorial.json | 3:4 | 0.2 ~ 0.3 | 전문 브랜드 화보 (착장 충실도 유지) |
| Selfie | selfie.json | 9:16 | 0.3 | 셀카/SNS (자연스러운 변형) |
| Daily Casual | daily_casual.json | 4:5 | 0.3 | 일상컷 (자연스러운 변형) |
| Seeding UGC | seeding_ugc.json | 9:16 | 0.35 | 인플루언서 시딩 (자연스러운 다양성) |
| Background Swap | background-swap.json | Original | 0.2 | 배경 교체 (충실도 최대) |
| 자유 생성 | - | - | 0.3 ~ 0.5 | 창의적 다양성 |
| 실험적/아트 | - | - | 0.7 ~ 0.9 | 다양한 결과 |

### API 설정 코드 패턴

```python
config=types.GenerateContentConfig(
    temperature=0.2,
    response_modalities=["IMAGE", "TEXT"],
    image_config=types.ImageConfig(
        aspect_ratio="3:4",
        image_size="2K"
    )
)
```

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

---

## 브랜드 라우팅 테이블

모든 브랜드 관련 작업에서 이 테이블로 매칭합니다.

| 트리거 키워드 | 브랜드 | DNA 파일 | 디렉터 페르소나 |
|--------------|--------|----------|----------------|
| MLB, 영앤리치, 프리미엄, 시크, 마케팅 화보 | MLB 마케팅 | `mlb-marketing.json` | `(MLB마케팅)_시티미니멀_tyrone-lebon` |
| MLB 그래픽, 스트릿, 올드스쿨, 바시티 | MLB 그래픽 | `mlb-graphic.json` | `(MLB그래픽)_스트릿레전드_shawn-stussy` |
| Discovery, 아웃도어, 고프코어, 테크니컬 | Discovery | `discovery.json` | `(Discovery)_테크니컬유틸리티_yosuke-aizawa` |
| Duvetica, 럭셔리, 다운, 이탈리안, 장인 | Duvetica | `duvetica.json` | `(Duvetica)_럭셔리장인_brunello-cucinelli` |
| Sergio, 테니스, 레트로, 80s, 슬림 | Sergio Tacchini | `sergio-tacchini.json` | `(SergioTacchini)_실루엣혁명_hedi-slimane` |
| Banila, 뷰티, 색조, 맑은, K-뷰티 | Banillaco | `banillaco.json` | `(Banillaco)_맑은뷰티_ahn-joo-young` |
| 제품컷, 제품 연출, 플랫레이, 행잉, 히어로샷, 이커머스 | 제품연출 (전 브랜드) | 해당 브랜드 DNA | `(제품연출)_한국힙이커머스_musinsa-29cm` |

브랜드 미감지 시 사용자에게 질문: "어떤 브랜드의 이미지를 생성할까요?"

---

## 스타일 매칭

| 트리거 키워드 | 스타일 | 워크플로 |
|--------------|--------|---------|
| 화보, 에디토리얼, 매거진, 패션 | editorial | `brand-cut` |
| 셀피, 일상, SNS, 캐주얼 | selfie | `brand-cut` |
| 배경 교체, 배경 바꿔 | background-swap | `background-swap` |
| 시딩, UGC, 인플루언서, 틱톡, 릴스 | seeding_ugc | `seeding-ugc` |
| 일상컷, 남친샷, 산책, 데일리 | daily_casual | `daily-casual` |
| 제품컷, 물촬, 상세페이지 | product | `product-shoot` |

---

## 품질 검증 기준

### 브랜드컷 검증 (Brand Cut)

AI 생성 화보의 **스타일 완성도**를 평가합니다.

| Criterion | Weight | Pass 기준 | 설명 |
|-----------|--------|-----------|------|
| photorealism | 20% | ≥ 85 | 실제 사진처럼 보이는지 |
| anatomy | 15% | ≥ 90 | 해부학적 정확성 (손가락, 비율, 관절) |
| face_identity | 15% | ≥ 90 | **얼굴 동일성 (참조 인물과 같은 사람인지)** |
| outfit_accuracy | 15% | ≥ 85 | **착장 재현도 (참조 이미지와 색상/로고/소재 정확 일치)** |
| body_type | 10% | ≥ 85 | **체형 보존 (참조 인물과 같은 체형)** |
| brand_compliance | 10% | ≥ 80 | 브랜드 톤앤매너 준수 (색온도, 무드) |
| composition | 8% | ≥ 80 | 구도/프레이밍 퀄리티 |
| lighting_mood | 7% | ≥ 80 | 조명/분위기 (디렉터 의도 반영) |

**Pass 조건**: 가중 평균 ≥ 90 AND `anatomy ≥ 90` AND `photorealism ≥ 85` AND `face_identity ≥ 90`

**Auto-Fail** (점수 무관 즉시 재생성):
- 손가락 6개 이상 / 기형적 손가락
- **얼굴 다른 사람** (face_identity < 70)
- **착장 색상/로고 불일치** (outfit_accuracy < 70)
- **체형 불일치 (날씬→뚱뚱 등)** (body_type < 70)
- **누런 톤 (golden/amber/warm cast)** → 색온도 규칙 위반
- 의도하지 않은 텍스트/워터마크
- 브랜드 금지 요소 위반
- AI 특유 플라스틱 피부

### 배경교체 검증 (Background Swap)

배경 **합성 품질**을 평가합니다. 인물 보존이 핵심.

| Criterion | Weight | Pass 기준 | 설명 |
|-----------|--------|-----------|------|
| model_preservation | 30% | = 100 (필수) | 인물 보존 (포즈, 얼굴, 의상, 스케일) |
| physics_plausibility | 15% | ≥ 50 (필수) | 물리적 타당성 (앉기→의자, 기대기→벽) |
| ground_contact | 13% | - | 접지감 (발/그림자 자연스러움) |
| lighting_match | 12% | - | 조명 방향/강도 일치 |
| prop_style_consistency | 12% | - | 소품-배경 스타일 일치 |
| edge_quality | 10% | - | 인물 경계면 깔끔함 |
| perspective_match | 8% | - | 카메라 앵글/원근 일치 |

**Pass 조건**: `model_preservation = 100` AND `physics_plausibility ≥ 50` AND `total ≥ 95`

### UGC 검증 (시딩 UGC 전용)

| Criterion | Weight | 설명 |
|-----------|--------|------|
| realism | 35% | 실제 폰 촬영 같은 자연스러움 |
| person_preservation | 25% | 인물 보존도 |
| scenario_fit | 20% | 시나리오 적합성 |
| skin_condition | 10% | 피부 상태 자연스러움 |
| anti_polish_factor | 10% | 과도한 보정 방지 |

**UGC 원칙**: "너무 잘 나오면 실패" - 폰으로 대충 찍은 것 같아야 성공

---

## 스킬 참조 가이드

이미지 생성 코드 작성 시 아래 스킬을 참조하세요:

| 스킬 | 경로 | 참조 시점 |
|------|------|----------|
| 이미지생성 레퍼런스 | `fnf-image-gen/SKILL.md` | 코드 패턴, 유틸리티 함수, 프롬프트 템플릿 필요 시 |
| 브랜드컷 워크플로 | `fnf-image-gen/workflows/brand-cut.md` | 브랜드 화보 파이프라인 구현 시 |
| 배경교체 워크플로 | `fnf-image-gen/workflows/background-swap.md` | 배경 교체 파이프라인 구현 시 |
| 시딩UGC 워크플로 | `seeding-ugc/SKILL.md` | UGC 생성 파이프라인 구현 시 |

---

## 워크플로 아키텍처

```
User Input → Brand Routing → Load Brand DNA → Load Template →
Outfit Analysis (VLM) → Director Vision → Prompt Assembly → Image Generation
```

모든 워크플로는 다음 단계를 따릅니다:
1. **라우팅**: 키워드 → 브랜드/스타일 매칭
2. **분석**: VLM으로 참조 이미지 분석 (착장, 무드, 포즈)
3. **프롬프트 조립**: Brand DNA + Template + Director Vision
4. **생성**: Gemini API 호출
5. **검증**: 품질 기준에 따른 자동 검증
6. **리트라이**: 실패 시 진단 → 프롬프트 개선 → 재생성
