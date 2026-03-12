---
name: beauty-video
description: 뷰티 영상 워크플로 - Gemini 이미지 + KlingAI I2V + TTS + BGM + 자막
user-invocable: true
---

# 뷰티 영상 워크플로 (Beauty Video)

> Banila Co 뷰티 릴스 End-to-End 파이프라인.
> 모든 코드: `core/beauty_video/`

## 절대 규칙

1. **이미지 생성은 Gemini `gemini-3-pro-image-preview`만 사용** (`from core.config import IMAGE_MODEL`)
2. **비디오 생성은 KlingAI** — 모델/키는 `core/beauty_video/config.py`에서 import
3. **영상은 항상 무음 생성** (`enable_audio=False`), TTS/BGM은 후처리 Phase에서 추가
4. **나레이션은 ElevenLabs TTS**, **BGM은 Suno API** — gTTS 등 저품질 TTS 금지
5. **항상 병렬/배치 처리** (`asyncio.gather`)
6. **비디오 URL은 즉시 다운로드** (CDN URL ~30일 만료)

## 모듈 구조

| 파일 | 역할 |
|------|------|
| `config.py` | VideoGenerationConfig + KLING_* 설정 |
| `client.py` | KlingAI API 클라이언트 (JWT 인증, 30분 TTL) |
| `generator.py` | T2V/I2V 고수준 생성 함수 |
| `pipeline.py` | 뷰티 릴스 End-to-End 파이프라인 (6 Phase) |
| `startframe.py` | Gemini 스타트프레임 이미지 자동 생성 (Phase 1) |
| `subtitle_style.py` | 숏폼 자막 이미지 베이킹 (Phase 1.5) |
| `video_subtitle.py` | 싱크 자막 영상 오버레이 (Phase 6) |
| `tts.py` | ElevenLabs TTS 나레이션 (Phase 4) |
| `bgm.py` | Suno API BGM 음악 (Phase 5) |
| `presets.py` | 뷰티 카메라/컷 프리셋 |
| `prompt_builder.py` | 패션 비디오 프롬프트 빌더 |

---

## 파이프라인

```
Phase 1:   스타트프레임 이미지 자동 생성 (Gemini, 병렬)
    ↓ image_path 없는 컷만 → asyncio.gather
Phase 1.5: 자막 이미지 베이킹 (subtitle 필드 있는 컷만)
    ↓
Phase 2:   I2V 영상 생성 (KlingAI, 병렬, 무음)
    ↓ enable_audio=False
Phase 3:   최종 연결 (moviepy concatenate)
    ↓
Phase 4:   TTS 나레이션 (ElevenLabs) + 속도 조절
    ↓
Phase 5:   BGM 생성 + 오버레이 (Suno API)
    ↓
Phase 6:   싱크 자막 오버레이 (reels/broadcast 스타일)
    ↓ 이미지 구운 자막 컷은 자동 스킵
Final:     릴스 MP4 출력
```

---

## 대화형 워크플로

> 원칙: 사용자 입력 먼저 → 옵션 → 비용 → 실행
> 브랜드는 **Banila Co 고정** — 브랜드 선택 질문 불필요

### Step 1: 사용자 입력 수집

3가지를 한번에 확인:

1. **시나리오** — 제품/컷별 구성
2. **모델 얼굴 참조 이미지** — 인물 동일성 유지용 (최대 3장)
3. **제품 이미지** — 제품 정확도 유지용 (최대 3장)

```
Q1: "어떤 Banila Co 제품의 릴스를 만들까요? 시나리오가 있으면 함께 알려주세요."
Q2: "모델 얼굴 참조 이미지가 있나요?"
Q3: "제품 이미지가 있나요?"
```

### Step 2: 옵션 선택

| 옵션 | 선택지 | 기본값 |
|------|--------|--------|
| 비율 | 9:16, 16:9, 1:1 | 9:16 |
| 길이 | 5초 | 5초 (고정) |
| 비디오 모드 | Standard, Pro | Pro |
| 이미지 해상도 | 1K, 2K | 2K |

### Step 3: 비용 안내

> Kling I2V: **0.168 USD/초** (5초 = 0.84 USD). 환율은 당일 기준 계산.

| 항목 | 단가 | 4컷 기준 |
|------|------|----------|
| 스타트프레임 (Gemini 2K) | 190원/장 | 760원 |
| I2V (Kling 5초) | ~1,231원 | ~4,924원 |
| **합계** | | **~5,684원** |

> 전체 비용 테이블: [pricing.md](./pricing.md) 참조

### Step 4: 생성 실행

```python
from core.beauty_video import generate_beauty_reels, VideoGenerationConfig

result = await generate_beauty_reels(
    scenario=scenario,
    source_images={"face": [...], "product": [...]},
    output_dir=output_dir,
    video_config=VideoGenerationConfig(
        model_name="kling-v2-6",
        mode="pro",
        duration="5",
        aspect_ratio="9:16",
    ),
    enable_audio=False,
    concat=True,
)
```

---

## 시나리오 구조

```json
{
  "brand": "Banila Co",
  "product": "B. Highlighter",
  "description": "highlighter_reels",
  "narration": {
    "cut01_hook": "아침에 바른 이 광채, 밤까지 가면 믿으시겠어요?",
    "cut02_apply": "프라이머 명가답게 모공 부각 0."
  },
  "phrases": [
    ["아침에 바른 이 광채,", "밤까지 가면", "믿으시겠어요?"],
    ["프라이머 명가답게", "모공 부각 0."]
  ],
  "cuts": [
    {
      "id": "cut01_hook",
      "name": "Hook",
      "type": "hook",
      "scene_description": "Korean beauty influencer holding highlighter...",
      "motion_prompt": "The woman holds up the compact toward camera...",
      "subtitle": {
        "style": "thumbnail",
        "texts": {
          "subtitle": "압도적 빔력;;",
          "main": ["하이라이터", "5종 비교"],
          "brand": "BANILA CO",
          "price": "16,000원"
        }
      }
    }
  ]
}
```

**소스 이미지:**
```python
source_images = {
    "face": ["face1.jpg", "face2.jpg"],     # 최대 3장, 인물 동일성
    "product": ["product.jpg"],               # 최대 3장, 제품 정확도
}
```

---

## Phase 1: 스타트프레임 자동 생성

`image_path`가 없는 컷에 대해 Gemini로 자동 생성.

```python
from core.beauty_video.startframe import generate_startframes

frame_paths = await generate_startframes(
    scenario=scenario,
    source_images={"face": ["face.jpg"], "product": ["product.jpg"]},
    output_dir="outputs/startframes",
    aspect_ratio="9:16",
    resolution="2K",
)
```

- 컷 타입별 프롬프트 자동 생성 (`BEAUTY_CUT_TYPES` 참조)
- 커스텀 프롬프트: 컷에 `image_prompt` 필드가 있으면 사용
- 재시도: 429/503 → `(attempt+1)*5`초 대기, 최대 3회

---

## Phase 1.5: 자막 이미지 베이킹

컷에 `subtitle` 필드가 있으면 스타트프레임에 자막을 베이킹 → I2V 후 영상 첫 프레임부터 자막 표시.

- `thumbnail` 스타일: 유튜브 썸네일 (G마켓 산스 볼드, 이탤릭, 강조색 팔레트)
- `broadcast` 스타일: 방송 자막 바 (흰색 반투명 바 + 검정 텍스트)

> 스타일 상세 사양: [subtitle-styles.md](./subtitle-styles.md) 참조

---

## Phase 4: TTS 나레이션

ElevenLabs TTS로 한국어 나레이션 생성. 기본 보이스: nicole (ASMR).

```python
from core.beauty_video.tts import generate_tts_for_voice_preset, overlay_tts_on_video

wav = generate_tts_for_voice_preset("nicole", text, "output/tts.wav")
overlay_tts_on_video("video.mp4", wav, "output/with_tts.mp4", bgm_vol=0.3)
```

> 보이스 프리셋/사용법 상세: [tts-reference.md](./tts-reference.md) 참조

---

## Phase 5: BGM 생성

Suno API로 인스트루멘탈 BGM 생성. 기본 모델: V4_5.

```python
from core.beauty_video.bgm import generate_bgm_for_preset, overlay_bgm_on_video

bgm = generate_bgm_for_preset("beauty_lofi", "output/bgm.mp3")
overlay_bgm_on_video("video.mp4", bgm, "output/final.mp4", bgm_vol=0.15)
```

> BGM 프리셋/사용법 상세: [bgm-reference.md](./bgm-reference.md) 참조

---

## Phase 6: 싱크 자막

TTS에 맞춰 실시간 싱크 자막 오버레이. `subtitle` 필드 있는 컷(Phase 1.5에서 베이킹)은 자동 스킵.

| 스타일 | 외관 |
|--------|------|
| `reels` | 흰색 글씨 + 아웃라인 + 그림자 (인스타 릴스) |
| `broadcast` | 흰색 반투명 바 + 검정 글씨 (방송 뉴스) |

> 싱크 자막 상세: [subtitle-styles.md](./subtitle-styles.md) 참조

---

## 단독 T2V/I2V

파이프라인 없이 단독으로 비디오 생성할 때는 [kling-reference.md](./kling-reference.md) 참조.

---

## 뷰티 프리셋

```python
from core.beauty_video.presets import (
    BEAUTY_CAMERA_MOVES,     # selfie_zoom, product_pan, mirror_static 등
    BEAUTY_NEGATIVE_PROMPT,  # 공통 네거티브 프롬프트
    BEAUTY_CUT_TYPES,        # hook, apply, proof, cta 컷 타입
)
```

---

## 출력 폴더 구조

```
Fnf_studio_outputs/beauty_video/
└── {YYYYMMDD_HHMMSS}_{description}/
    ├── startframes/              # Phase 1 생성 이미지
    ├── cut01_hook/
    │   ├── images/
    │   │   └── input_source_01.jpg
    │   ├── videos/
    │   │   └── output_001.mp4
    │   ├── prompt.json
    │   └── config.json
    ├── cut02_apply/
    ├── cut03_proof/
    ├── cut04_cta/
    ├── tts/                      # Phase 4 TTS 오디오
    ├── final_reels.mp4           # 최종 릴스
    └── summary.json
```

---

## .env 설정

```bash
# KlingAI (비디오 생성)
KLING_ACCESS_KEY=your_access_key_here
KLING_SECRET_KEY=your_secret_key_here

# ElevenLabs (TTS 나레이션)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Suno (BGM 생성)
SUNO_API_KEY=your_suno_api_key_here

# Gemini (이미지 생성) - CLAUDE.md에서 공통 관리
GEMINI_API_KEY=key1,key2,key3
```

---

## 서포트 파일

| 파일 | 내용 |
|------|------|
| [subtitle-styles.md](./subtitle-styles.md) | 자막 스타일 상세 (thumbnail/broadcast, 싱크 자막) |
| [tts-reference.md](./tts-reference.md) | TTS 보이스 프리셋, 사용법, v3 감정 태그 |
| [bgm-reference.md](./bgm-reference.md) | BGM Suno 모델, 프리셋, 사용법 |
| [kling-reference.md](./kling-reference.md) | 단독 T2V/I2V 사용법, 에러 핸들링 |
| [pricing.md](./pricing.md) | 전체 비용 테이블 (Kling, Veo 3.1, Gemini, TTS, BGM) |

---

## 버전

| 버전 | 날짜 | 변경 |
|------|------|------|
| v1.0 | 2026-03-10 | 초기 버전 - Banila Co 하이라이터 캠페인으로 검증 |
| v2.0 | 2026-03-11 | T2V/I2V + 숏폼자막 + 파이프라인 통합 |
| v3.0 | 2026-03-11 | TTS + BGM 추가, 7 Phase 확장 |
| v4.0 | 2026-03-11 | Phase 1 스타트프레임 + Phase 7 싱크 자막 + 이미지 구운 자막 스킵 |
| v5.0 | 2026-03-12 | V2A 제거 (무음 영상), Banila Co 고정, 대화형 4단계, USD 가격 |
| v6.0 | 2026-03-12 | SKILL.md 간소화 (906→~280줄), 상세 참조를 서포트 파일 5개로 분리 |
