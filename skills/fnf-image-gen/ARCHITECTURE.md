# FNF Studio Architecture

> FNF Studio는 패션 브랜드를 위한 AI 이미지 생성 플랫폼입니다.
> Gemini API 기반으로 브랜드컷, 배경교체, 시딩UGC, 일상컷 4가지 워크플로를 제공합니다.

---

## 1. 시스템 전체 구조

```mermaid
graph TB
    subgraph USER["사용자 인터페이스"]
        UI[Streamlit Web UI<br/>app_background_studio.py]
        API[FastAPI Backend<br/>api/main.py]
    end

    subgraph ROUTING["요청 라우팅"]
        BR[Brand Routing<br/>브랜드 매칭]
        SR[Style Routing<br/>워크플로 매칭]
    end

    subgraph WORKFLOWS["4대 워크플로"]
        WF1["Brand Cut<br/>브랜드컷 에디토리얼"]
        WF2["Background Swap<br/>배경교체"]
        WF3["Seeding UGC<br/>시딩UGC"]
        WF4["Daily Casual<br/>일상컷"]
    end

    subgraph SHARED["공유 인프라"]
        GEMINI["Gemini API<br/>gemini-3-pro-image-preview"]
        KEYS["API Key Rotation<br/>thread-safe"]
        VALID["Quality Validation<br/>워크플로별 기준"]
        RETRY["Auto-Retry Pipeline<br/>validate - diagnose - enhance - retry"]
    end

    subgraph ASSETS["브랜드 자산"]
        DNA["Brand DNA<br/>6개 브랜드 JSON"]
        TPL["Prompt Templates<br/>editorial, selfie, daily, ugc"]
        DIR["Director Personas<br/>7개 디렉터"]
        POSE["Pose Library<br/>스타일별 포즈 130+"]
    end

    subgraph OUTPUT["출력"]
        OUT["Fnf_studio_outputs/<br/>brand/workflow/"]
        REL["release/"]
        REV["manual_review/"]
    end

    UI --> BR
    API --> BR
    BR --> SR
    SR --> WF1
    SR --> WF2
    SR --> WF3
    SR --> WF4

    WF1 --> DNA
    WF1 --> TPL
    WF1 --> DIR
    WF1 --> POSE
    WF3 --> DNA
    WF3 --> DIR
    WF4 --> DNA

    WF1 --> GEMINI
    WF2 --> GEMINI
    WF3 --> GEMINI
    WF4 --> GEMINI
    GEMINI --> KEYS

    WF1 --> VALID
    WF2 --> VALID
    WF3 --> VALID
    WF4 --> VALID
    VALID -->|Pass| REL
    VALID -->|Fail| RETRY
    RETRY --> GEMINI
    RETRY -->|최종 실패| REV

    REL --> OUT
    REV --> OUT
```

---

## 2. 문서 계층 구조 (CLAUDE.md vs SKILL.md)

```mermaid
graph TD
    CLAUDE["CLAUDE.md<br/><b>절대 규칙 - Single Source of Truth</b>"]

    subgraph RULES["CLAUDE.md 관할 (불변 규칙)"]
        R1["Gemini API 규칙<br/>모델, 해상도, Temperature"]
        R2["브랜드 라우팅 테이블<br/>6 브랜드 + 제품연출"]
        R3["품질 검증 기준 요약<br/>3가지 검증 타입"]
        R4["워크플로 라우팅<br/>키워드 - 워크플로 매핑"]
        R5["API Key 관리<br/>로테이션, 에러 처리"]
        R6["출력 디렉토리 구조<br/>Fnf_studio_outputs/"]
    end

    CLAUDE --> R1
    CLAUDE --> R2
    CLAUDE --> R3
    CLAUDE --> R4
    CLAUDE --> R5
    CLAUDE --> R6

    subgraph SKILLS[".claude/skills/ 관할 (실행 로직)"]
        S_REF["이미지생성_레퍼런스<br/>코드 패턴, 유틸리티, 템플릿"]
        S_BC["브랜드컷_brand-cut<br/>6단계 파이프라인"]
        S_BG["배경교체_background-swap<br/>7단계 파이프라인"]
        S_UGC["시딩UGC_seeding-ugc<br/>6단계 파이프라인"]
        S_DC["일상컷_daily-casual<br/>5단계 파이프라인"]
        S_SRL["스튜디오리라이팅<br/>조명 변환"]
        S_VID["비디오처리<br/>영상 파이프라인"]
    end

    subgraph BRAND_ASSETS["브랜드 자산 파일"]
        BA_DNA["brand-dna/<br/>6개 JSON"]
        BA_TPL["prompt-templates/<br/>템플릿 + 포즈 라이브러리"]
        BA_DIR["Director Personas 7개<br/>MLB마케팅, MLB그래픽, Discovery<br/>Duvetica, SergioTacchini<br/>Banillaco, 제품연출"]
    end

    CLAUDE -.->|참조| SKILLS
    S_BC --> BA_DNA
    S_BC --> BA_TPL
    S_BC --> BA_DIR

    style CLAUDE fill:#ff6b6b,color:#fff,stroke:#333
    style RULES fill:#ffe0e0,stroke:#ff6b6b
    style SKILLS fill:#e0f0ff,stroke:#4a9eff
    style BRAND_ASSETS fill:#e8f5e9,stroke:#66bb6a
```

**핵심 원칙**: CLAUDE.md는 "무엇을 지켜야 하는가" (규칙), SKILL.md는 "어떻게 실행하는가" (로직)

---

## 3. 사용자 요청 라우팅

```mermaid
flowchart TD
    INPUT["사용자 입력<br/>예: MLB 프리미엄 화보 콘크리트 배경"]

    INPUT --> BRAND_DETECT{"브랜드 키워드 감지"}

    BRAND_DETECT -->|"MLB, 영앤리치, 프리미엄"| MLB_MKT["MLB 마케팅<br/>mlb-marketing.json"]
    BRAND_DETECT -->|"MLB 그래픽, 스트릿"| MLB_GFX["MLB 그래픽<br/>mlb-graphic.json"]
    BRAND_DETECT -->|"Discovery, 아웃도어"| DISC["Discovery<br/>discovery.json"]
    BRAND_DETECT -->|"Duvetica, 럭셔리"| DUVET["Duvetica<br/>duvetica.json"]
    BRAND_DETECT -->|"Sergio, 테니스"| SERGIO["Sergio Tacchini<br/>sergio-tacchini.json"]
    BRAND_DETECT -->|"Banila, 뷰티"| BANI["Banillaco<br/>banillaco.json"]
    BRAND_DETECT -->|"제품컷, 플랫레이"| PROD["제품연출<br/>해당 브랜드 DNA"]
    BRAND_DETECT -->|"미감지"| ASK["사용자에게 질문<br/>어떤 브랜드?"]

    MLB_MKT --> STYLE_DETECT
    MLB_GFX --> STYLE_DETECT
    DISC --> STYLE_DETECT
    DUVET --> STYLE_DETECT
    SERGIO --> STYLE_DETECT
    BANI --> STYLE_DETECT
    PROD --> WF_PROD["제품연출 워크플로"]

    STYLE_DETECT{"스타일 키워드 감지"}

    STYLE_DETECT -->|"화보, 에디토리얼, 매거진"| WF1["Brand Cut<br/>브랜드컷 워크플로"]
    STYLE_DETECT -->|"셀피, 일상, SNS"| WF1
    STYLE_DETECT -->|"배경 교체, 배경 바꿔"| WF2["Background Swap<br/>배경교체 워크플로"]
    STYLE_DETECT -->|"시딩, UGC, 인플루언서"| WF3["Seeding UGC<br/>시딩UGC 워크플로"]
    STYLE_DETECT -->|"일상컷, 남친샷, 데일리"| WF4["Daily Casual<br/>일상컷 워크플로"]

    style INPUT fill:#e3f2fd,stroke:#1976d2
    style WF1 fill:#c8e6c9,stroke:#388e3c
    style WF2 fill:#fff9c4,stroke:#f9a825
    style WF3 fill:#f3e5f5,stroke:#8e24aa
    style WF4 fill:#ffe0b2,stroke:#ef6c00
    style WF_PROD fill:#e0e0e0,stroke:#616161
    style ASK fill:#ffcdd2,stroke:#c62828
```

---

## 4. 워크플로 파이프라인 상세

### 4-1. Brand Cut (브랜드컷)

```mermaid
flowchart LR
    A["1. Brand Routing<br/>브랜드 매칭"] --> B["2. DNA Load<br/>브랜드 DNA 로드"]
    B --> C["3. Template Load<br/>프롬프트 템플릿"]
    C --> D["4. Director Persona<br/>디렉터 페르소나 로드"]
    D --> E["5. Outfit Analysis<br/>VLM 착장 분석"]
    E --> F["6. Director Vision<br/>포즈/앵글/표정 결정"]
    F --> G["7. Prompt Assembly<br/>프롬프트 조립"]
    G --> H["8. Image Generation<br/>Gemini 이미지 생성"]
    H --> I{"9. Quality Validation<br/>6 criteria"}

    I -->|"Pass<br/>avg>=90 AND<br/>anatomy>=90 AND<br/>photorealism>=85"| J["release/"]
    I -->|"Fail"| K["Retry or<br/>manual_review/"]

    style A fill:#bbdefb
    style E fill:#c8e6c9
    style F fill:#c8e6c9
    style H fill:#fff9c4
    style I fill:#ffcdd2
    style J fill:#a5d6a7
    style K fill:#ef9a9a
```

**검증 기준 (6 criteria)**:
| Criterion | 설명 |
|-----------|------|
| photorealism | 사진 같은 리얼리즘 (>= 85 필수) |
| anatomy | 해부학적 정확성 (>= 90 필수) |
| brand_compliance | 브랜드 DNA 준수도 |
| outfit_accuracy | 착장 정확도 |
| composition | 구도/프레이밍 |
| lighting_mood | 조명/분위기 |

**Pass 조건**: `weighted_avg >= 90 AND anatomy >= 90 AND photorealism >= 85`

---

### 4-2. Background Swap (배경교체)

```mermaid
flowchart LR
    A["1. Input Analysis<br/>VFX + VLM<br/>원본 분석"] --> B["2. Object Preservation<br/>인물+차량 보존<br/>ONE UNIT 처리"]
    B --> C["3. Prompt Assembly<br/>배경 프롬프트 조립"]
    C --> D["4. Image Generation<br/>Gemini 생성"]
    D --> E{"5. 7-Criteria<br/>Validation"}

    E -->|"Pass<br/>model=100 AND<br/>physics>=50 AND<br/>total>=95"| F["release/"]
    E -->|"Fail"| G["6. Diagnosis<br/>실패 원인 진단"]
    G --> H["7. Prompt Enhancement<br/>진단 기반 프롬프트 보정"]
    H --> D

    style A fill:#fff9c4
    style B fill:#ffecb3
    style D fill:#fff9c4
    style E fill:#ffcdd2
    style F fill:#a5d6a7
    style G fill:#ef9a9a
    style H fill:#ffcc80
```

**검증 기준 (7 criteria, weighted)**:
| Criterion | Weight | 설명 |
|-----------|--------|------|
| model_preservation | 30% | 인물 보존도 (100 필수) |
| physics_plausibility | 15% | 물리적 타당성 (>= 50 필수) |
| ground_contact | 13% | 지면 접촉 자연스러움 |
| lighting_match | 12% | 조명 일치도 |
| prop_style_consistency | 12% | 소품/스타일 일관성 |
| edge_quality | 10% | 경계 품질 |
| perspective_match | 8% | 원근감 일치도 |

**Pass 조건**: `model_preservation = 100 AND physics_plausibility >= 50 AND weighted_total >= 95`

---

### 4-3. Seeding UGC (시딩UGC)

```mermaid
flowchart LR
    A["1. Brand Routing<br/>브랜드 매칭"] --> B["2. AI Scenario<br/>Selection<br/>시나리오 자동 선택"]
    B --> C["3. Prompt Assembly<br/>5-Layer UGC 프롬프트"]
    C --> D["4. Image Generation<br/>Gemini 생성<br/>temp=0.35"]
    D --> E{"5. Realism<br/>Validation"}

    E -->|"Pass"| F["release/ +<br/>Seeding Guide"]
    E -->|"Fail<br/>너무 완벽하면 실패"| G["Retry<br/>더 자연스럽게"]
    G --> D

    style A fill:#e1bee7
    style B fill:#ce93d8
    style C fill:#e1bee7
    style D fill:#f3e5f5
    style E fill:#ffcdd2
    style F fill:#a5d6a7
    style G fill:#ef9a9a
```

**핵심 원칙**: "너무 잘 나오면 실패" - 폰으로 대충 찍은 것 같아야 성공

**검증 기준 (5 criteria, UGC 전용)**:
| Criterion | Weight | 설명 |
|-----------|--------|------|
| ugc_realism | 35% | 실제 폰 촬영 같은 자연스러움 |
| person_preservation | 25% | 인물 보존도 |
| scenario_fit | 20% | 시나리오 적합성 |
| skin_condition | 10% | 피부 상태 자연스러움 |
| anti_polish | 10% | 과도한 보정 방지 (높을수록 좋음) |

---

### 4-4. Daily Casual (일상컷)

```mermaid
flowchart LR
    A["1. Brand Routing<br/>브랜드 매칭"] --> B["2. AI Selection<br/>샷/포즈/조명<br/>자동 선택"]
    B --> C["3. Prompt Assembly<br/>일상컷 프롬프트"]
    C --> D["4. Image Generation<br/>Gemini 생성<br/>temp=0.3"]
    D --> E{"5. Validation<br/>자연스러움 중심"}

    E -->|"Pass"| F["release/"]
    E -->|"Fail"| G["Retry"]
    G --> D

    style A fill:#ffe0b2
    style B fill:#ffcc80
    style C fill:#ffe0b2
    style D fill:#fff3e0
    style E fill:#ffcdd2
    style F fill:#a5d6a7
    style G fill:#ef9a9a
```

**검증 기준 (5 criteria)**:
| Criterion | Weight | 설명 |
|-----------|--------|------|
| naturalness | 30% | 전반적 자연스러움 |
| person_preservation | 25% | 인물 보존도 |
| camera_realism | 20% | 카메라 촬영 리얼리즘 |
| outfit_accuracy | 15% | 착장 정확도 |
| background_fit | 10% | 배경 적합성 |

---

## 5. 품질 검증 비교표

```mermaid
graph LR
    subgraph BC["Brand Cut"]
        BC1["photorealism"]
        BC2["anatomy"]
        BC3["brand_compliance"]
        BC4["outfit_accuracy"]
        BC5["composition"]
        BC6["lighting_mood"]
    end

    subgraph BG["Background Swap"]
        BG1["model_preservation 30%"]
        BG2["physics_plausibility 15%"]
        BG3["ground_contact 13%"]
        BG4["lighting_match 12%"]
        BG5["prop_style 12%"]
        BG6["edge_quality 10%"]
        BG7["perspective 8%"]
    end

    subgraph UGC["Seeding UGC"]
        UGC1["ugc_realism 35%"]
        UGC2["person_preservation 25%"]
        UGC3["scenario_fit 20%"]
        UGC4["skin_condition 10%"]
        UGC5["anti_polish 10%"]
    end

    subgraph DC["Daily Casual"]
        DC1["naturalness 30%"]
        DC2["person_preservation 25%"]
        DC3["camera_realism 20%"]
        DC4["outfit_accuracy 15%"]
        DC5["background_fit 10%"]
    end

    style BC fill:#c8e6c9,stroke:#388e3c
    style BG fill:#fff9c4,stroke:#f9a825
    style UGC fill:#f3e5f5,stroke:#8e24aa
    style DC fill:#ffe0b2,stroke:#ef6c00
```

| 워크플로 | Pass 조건 | 특이사항 |
|----------|----------|---------|
| **Brand Cut** | avg >= 90, anatomy >= 90, photorealism >= 85 | 브랜드 준수 + 해부학 정확성 중심 |
| **Background Swap** | model = 100, physics >= 50, total >= 95 | 인물 절대 보존 + 물리 타당성 |
| **Seeding UGC** | UGC 리얼리즘 기반 | "너무 완벽하면 실패" 원칙 |
| **Daily Casual** | 자연스러움 기반 종합 평가 | 카메라 리얼리즘 중시 |

---

## 6. 공유 인프라

### 6-1. Gemini API 설정

```mermaid
flowchart TD
    REQ["이미지 생성 요청"] --> GEN3["gemini-3-pro-image-preview"]

    GEN3 --> RES{"해상도 설정"}
    RES -->|"테스트"| R1K["1K: 1024x1024"]
    RES -->|"일반 제작 (기본)"| R2K["2K: 2048x2048"]
    RES -->|"최종 결과물"| R4K["4K: 4096x4096"]

    GEN3 --> TEMP{"Temperature"}
    TEMP -->|"배경교체/참조보존"| T02["0.2"]
    TEMP -->|"브랜드컷"| T023["0.2 - 0.3"]
    TEMP -->|"셀피/일상컷"| T03["0.3"]
    TEMP -->|"시딩 UGC"| T035["0.35"]

    style GEN3 fill:#c8e6c9,stroke:#388e3c
    style R2K fill:#bbdefb,stroke:#1976d2,stroke-width:3px
```

### 6-2. API Key 로테이션 및 에러 처리

```mermaid
flowchart TD
    CALL["API 호출"] --> GETKEY["get_next_api_key()<br/>thread-safe 로테이션"]
    GETKEY --> SEND["Gemini API 호출"]

    SEND --> RESULT{"응답"}
    RESULT -->|"성공"| OK["이미지 반환"]
    RESULT -->|"429 Rate Limit"| WAIT["대기: attempt * 5초"]
    RESULT -->|"503 Overloaded"| WAIT
    RESULT -->|"Timeout"| WAIT
    RESULT -->|"401 Auth Error"| FAIL_HARD["즉시 실패<br/>재시도 불가"]
    RESULT -->|"Safety Blocked"| FAIL_HARD

    WAIT --> RETRY{"재시도 횟수?"}
    RETRY -->|"< 3회"| GETKEY
    RETRY -->|">= 3회"| FAIL_SOFT["최종 실패<br/>manual_review/"]

    style OK fill:#a5d6a7
    style FAIL_HARD fill:#ef9a9a
    style FAIL_SOFT fill:#ffcc80
    style WAIT fill:#fff9c4
```

### 6-3. 출력 디렉토리 구조

```mermaid
graph TD
    ROOT["Fnf_studio_outputs/"]

    ROOT --> B1["mlb-marketing/"]
    ROOT --> B2["mlb-graphic/"]
    ROOT --> B3["discovery/"]
    ROOT --> B4["duvetica/"]
    ROOT --> B5["sergio-tacchini/"]
    ROOT --> B6["banillaco/"]
    ROOT --> SUGC["seeding_ugc/"]
    ROOT --> EDIT["edit/"]
    ROOT --> LOGS["logs/"]

    B1 --> W1["brand-cut/"]
    B1 --> W2["background-swap/"]

    W1 --> REL["release/<br/>품질 통과"]
    W1 --> MR["manual_review/<br/>자동 재시도 실패"]
    W1 --> LOG["logs/<br/>파이프라인 리포트"]
    W1 --> TMP["_temp/<br/>임시 파일"]

    MR --> DIAG["diagnosis/<br/>JSON 진단 파일"]

    style ROOT fill:#e3f2fd,stroke:#1976d2
    style REL fill:#a5d6a7,stroke:#388e3c
    style MR fill:#ffcc80,stroke:#ef6c00
    style TMP fill:#e0e0e0,stroke:#9e9e9e
```

---

## 7. 코드 레이어

```mermaid
graph TD
    subgraph UI_LAYER["UI Layer"]
        STREAMLIT["app_background_studio.py<br/>Streamlit Web UI"]
        FASTAPI["api/main.py<br/>FastAPI Backend"]
    end

    subgraph API_LAYER["API Layer"]
        ROUTER["api/routers/tasks.py<br/>Task CRUD"]
        DB["api/database.py<br/>SQLite + SQLAlchemy"]
        CONFIG_API["api/config.py<br/>Pydantic Settings"]
    end

    subgraph PIPELINE_LAYER["Pipeline Layer"]
        PIPE["pipeline.py<br/>Batch Orchestrator"]
        AUTO["auto_retry_pipeline/<br/>Smart Retry System"]
        AUTO_V["validator.py"]
        AUTO_D["diagnoser.py"]
        AUTO_E["enhancer.py"]
        AUTO_P["pipeline.py"]
    end

    subgraph CONFIG_LAYER["Configuration"]
        CORE_CFG["core/config.py<br/>Central Config"]
        ENV[".env<br/>API Keys"]
    end

    FASTAPI --> ROUTER
    ROUTER --> DB
    FASTAPI --> CONFIG_API
    CONFIG_API --> ENV

    STREAMLIT --> PIPE
    PIPE --> AUTO
    AUTO --> AUTO_V
    AUTO --> AUTO_D
    AUTO --> AUTO_E
    AUTO --> AUTO_P

    PIPE --> CORE_CFG
    CORE_CFG --> ENV

    style UI_LAYER fill:#e3f2fd,stroke:#1976d2
    style API_LAYER fill:#e8f5e9,stroke:#388e3c
    style PIPELINE_LAYER fill:#fff3e0,stroke:#ef6c00
    style CONFIG_LAYER fill:#f3e5f5,stroke:#8e24aa
```

---

## 8. Brand Cut 상세 흐름도 (ASCII)

아래는 브랜드컷 에디토리얼 워크플로의 단계별 상세 흐름입니다.

```
                    [User Input: "MLB 프리미엄 화보 무대 백스테이지"]
                                        |
                                        v
+===============================================================================+
|  STEP 1: 브랜드 라우팅 (route_brand)                                           |
+===============================================================================+
|  brand-dna/_index.json                                                         |
|  +-----------------------------------------------------------------------+    |
|  | "MLB" in input?                                                        |    |
|  |   +-- "프리미엄, 시크, 화보" --> mlb-marketing                        |    |
|  |   +-- "스트릿, 그래픽"      --> mlb-graphic                           |    |
|  +-----------------------------------------------------------------------+    |
|  Output: brand = "mlb-marketing"                                               |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 1.5: 스타일 라우팅 (route_style)                                         |
+===============================================================================+
|  brand-dna/_index.json --> prompt_engines                                      |
|  +-----------------------------------------------------------------------+    |
|  | "화보, 에디토리얼, 매거진" --> editorial                               |    |
|  | "셀피, SNS, 캐주얼"       --> selfie                                   |    |
|  +-----------------------------------------------------------------------+    |
|  Output: style = "editorial"                                                   |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 2: 브랜드 DNA 로드 (load_brand_dna)                                      |
+===============================================================================+
|  brand-dna/mlb-marketing.json                                                  |
|  +-----------------------------------------------------------------------+    |
|  | _metadata: { persona: "Tyrone Lebon", brand: "MLB" }                   |    |
|  | identity:  { philosophy: ["가장 완벽한 공간을..."], mood: ["cool"] }   |    |
|  | keywords:  { style: ["old money meets streetwear"], ... }              |    |
|  | forbidden_keywords: { pose: ["활짝 웃는"], background: ["그래피티"] }  |    |
|  +-----------------------------------------------------------------------+    |
|  Output: brand_dna = { ... }                                                   |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 2.5: 프롬프트 템플릿 로드 (load_template)                                |
+===============================================================================+
|  prompt-templates/MLB_editorial.json (우선)                                    |
|  prompt-templates/editorial.json (fallback)                                    |
|  +-----------------------------------------------------------------------+    |
|  | meta:      { aspect_ratio: "4:5", quality: "8k" }                      |    |
|  | subject:   { expression: "{brand_dna.xxx|confident}" }                 |    |
|  | outfit:    { style: "{brand_dna.keywords.style[0]}" }                  |    |
|  | pose:      { attitude: "bored chic, rebellious" }                      |    |
|  | scene:     { location: "{input.location|concrete garage}" }            |    |
|  | lighting:  { type: "hard directional", color_temp: "6500K" }           |    |
|  | technical: { camera: "Sony A7R V", lens: "35mm f/1.4" }                |    |
|  +-----------------------------------------------------------------------+    |
|  Output: template = { ... }                                                    |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 3: 디렉터 페르소나 로드 (load_brand_director_skill)                       |
+===============================================================================+
|  (MLB마케팅)_시티미니멀_tyrone-lebon/SKILL.md                                  |
|  +-----------------------------------------------------------------------+    |
|  | 페르소나: Tyrone Lebon (The Old Money Rebel)                           |    |
|  | 철학:     "가장 완벽한 공간을, 가장 지루해하는 표정으로 장악"           |    |
|  | 스타일:   old money, bored rich kid, arrogant luxury                    |    |
|  | DO:       완벽한 배경에 삐딱하게 기대기, 시선 피하기                    |    |
|  | DON'T:    그래피티, 뒷골목, 활짝 웃음, 역동적 포즈                     |    |
|  | 포즈 130개 가이드라인                                                  |    |
|  +-----------------------------------------------------------------------+    |
|  Output: director_directives = { persona, philosophy, do_rules, ... }          |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 4: 착장 분석 VLM (analyze_outfit)                                         |
+===============================================================================+
|  Gemini 2.0 Flash (3회 재시도)                                                  |
|  +-----------------------------------------------------------------------+    |
|  | 분석 항목:                                                             |    |
|  | +-- headwear: beanie, no_brim, mohair, fuzzy                          |    |
|  | +-- outer:    varsity jacket, satin, Red Sox script                   |    |
|  | +-- top:      tank top, black, MLB logo                               |    |
|  | +-- bottom:   cargo jeans, wide leg, NY logo                          |    |
|  | +-- bag:      shoulder bag, knit, NY pattern                          |    |
|  |                                                                        |    |
|  | ** 로고 위치 정확도 체크 (front_right, not front_center)               |    |
|  +-----------------------------------------------------------------------+    |
|  Output: outfit_analysis = { garments: [...], outfit_description: "..." }      |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 5: 디렉터 비전 생성 (generate_director_vision)                            |
+===============================================================================+
|  Gemini 2.0 Flash (페르소나 롤플레이)                                           |
|  +-----------------------------------------------------------------------+    |
|  | variation_index=0~9 --> 10가지 포즈 라이브러리에서 강제 선택            |    |
|  |                                                                        |    |
|  | EDITORIAL 포즈 라이브러리:                                             |    |
|  | +-- 0: The Foot Rest (발 올리기, 로우앵글)                             |    |
|  | +-- 1: The Hood Lounger (보닛 위, 45도)                                |    |
|  | +-- 2: 쭈그려 앉아 턱 괴기 (로우앵글)                                   |    |
|  | +-- 3: 걷다가 뒤돌아보기 (측면)                                        |    |
|  | +-- 4: 바닥에 앉아서 (하이앵글)                                        |    |
|  | +-- ... (총 10가지)                                                    |    |
|  |                                                                        |    |
|  | ** 강제 적용: VLM 결과 위에 forced_pose/angle/expression 덮어쓰기     |    |
|  +-----------------------------------------------------------------------+    |
|  Output: director_vision = { pose_full, expression, camera_angle, ... }        |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 6: 프롬프트 조립 (build_prompt_from_template)                             |
+===============================================================================+
|  변수 치환 + 병합                                                               |
|  +-----------------------------------------------------------------------+    |
|  | {                                                                      |    |
|  |   "meta":    { aspect_ratio, quality, camera, lens }                   |    |
|  |   "subject": { gender, age, expression <-- 강제적용, skin }            |    |
|  |   "outfit":  { items <-- 착장분석 or fallback, style }                 |    |
|  |   "pose":    { style <-- 강제적용, selfie_type, arm_position }         |    |
|  |   "scene":   { location <-- 디렉터비전, background, atmosphere }       |    |
|  |   "camera":  { angle <-- 강제적용, framing <-- 강제적용, lens }        |    |
|  |   "lighting": { type <-- 디렉터비전, quality, color_temp }             |    |
|  |   "style":   { persona, direction }                                    |    |
|  | }                                                                      |    |
|  |                                                                        |    |
|  | ** outfit.items 비어있으면 --> director_vision.outfit_highlight 사용    |    |
|  +-----------------------------------------------------------------------+    |
|  Output: prompt_json, negative_prompt                                          |
+===============================================================================+
                                        |
                                        v
+===============================================================================+
|  STEP 7: 이미지 생성 (generate_single)                                          |
+===============================================================================+
|  Gemini gemini-3-pro-image-preview                                              |
|  +-----------------------------------------------------------------------+    |
|  | 입력:                                                                  |    |
|  | +-- 모델 이미지 (얼굴 참조)                                           |    |
|  | +-- 착장 이미지 (옷 참조)                                             |    |
|  | +-- 최종 프롬프트                                                     |    |
|  | +-- 네거티브 프롬프트                                                 |    |
|  |                                                                        |    |
|  | 출력: PIL.Image                                                        |    |
|  +-----------------------------------------------------------------------+    |
+===============================================================================+
                                        |
                                        v
                              [생성된 이미지 저장 + 품질 검증]
```

---

## 9. 디렉터 페르소나 매핑

| 브랜드 | 디렉터 | 페르소나 특징 |
|--------|--------|-------------|
| MLB 마케팅 | Tyrone Lebon | 시티 미니멀, old money rebel, 무드 있는 권태로움 |
| MLB 그래픽 | Shawn Stussy | 스트릿 레전드, 올드스쿨, 그래픽 타이포그래피 |
| Discovery | Yosuke Aizawa | 테크니컬 유틸리티, 고프코어, 구조적 실루엣 |
| Duvetica | Brunello Cucinelli | 이탈리안 럭셔리, 장인정신, 절제된 우아함 |
| Sergio Tacchini | Hedi Slimane | 실루엣 혁명, 슬림핏, 록 앤 롤 미학 |
| Banillaco | Ahn Joo-young | 맑은 뷰티, Glass Skin, 투명 발색 |
| 제품연출 | Musinsa/29CM | 한국 힙 이커머스, 클린 미니멀, 감성 연출 |

---

## 10. 콘텐츠 타입별 기본 설정

| 타입 | Template | Aspect Ratio | Temperature | Model |
|------|----------|-------------|-------------|-------|
| Editorial / Brand Cut | editorial.json | 3:4 | 0.2 | gemini-3-pro-image-preview |
| Selfie | selfie.json | 9:16 | 0.3 | gemini-3-pro-image-preview |
| Daily Casual | daily_casual.json | 4:5 | 0.3 | gemini-3-pro-image-preview |
| Seeding UGC | seeding_ugc.json | 9:16 | 0.35 | gemini-3-pro-image-preview |
| Background Swap | background-swap.json | Original | 0.2 | gemini-3-pro-image-preview |
