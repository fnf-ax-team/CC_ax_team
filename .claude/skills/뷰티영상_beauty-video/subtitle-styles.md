# 숏폼 자막 스타일 상세

> SKILL.md에서 참조하는 서포트 파일. 자막 베이킹 (Phase 1.5) + 싱크 자막 (Phase 6) 상세 사양.

## 이미지 자막 베이킹 (Phase 1.5)

시나리오 컷에 `subtitle` 필드가 있으면 I2V 전에 스타트프레임에 자막을 자동 베이킹.

```
스타트프레임 이미지 (Gemini)
    ↓
[Phase 1.5] subtitle 필드 있으면 → apply_subtitle_to_image()
    ↓
자막 베이킹된 이미지
    ↓
[Phase 2] KlingAI I2V → 영상 첫 프레임부터 자막 표시
```

### subtitle 필드 구조

```json
{
  "subtitle": {
    "style": "thumbnail",
    "texts": { "..." },
    "position": "bottom"
  }
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| `style` | O | `"thumbnail"` 또는 `"broadcast"` |
| `texts` | O | 스타일별 텍스트 딕셔너리 |
| `position` | X | broadcast만 적용 (`"top"`, `"center"`, `"bottom"`) |

### 적용 원리

- `subtitle` 필드 없는 컷 → 자막 없이 그대로 I2V
- `subtitle` 필드 있는 컷 → 자막이 스타트프레임에 베이킹 → 영상 첫 프레임부터 자막 표시
- 원본 이미지는 `_original_image_path`로 보존됨

---

## Style A: 유튜브 썸네일 (thumbnail)

| 항목 | 설정 |
|------|------|
| 폰트 | G마켓 산스 볼드 (`GmarketSansBold.otf`) |
| 기울기 | shear 0.18 (이탤릭) |
| 테두리 | 3~5px 검정 외곽선 |
| 텍스트 색상 | 흰색 `#FFFFFF` (메인), 강조색 팔레트 |
| 이모지 | Apple 3D 스타일 (`pilmoji`), **첫 줄 인라인에만** |
| 정렬 | 가운데 정렬 |
| 배경 | 반투명 검정 그라디언트 (텍스트 영역) |
| 용도 | 제품 소개, 비교 리뷰, 썸네일 |

텍스트 구조:
```
소제목;;               <- 작은 글씨 + 인라인 이모지
메인 텍스트            <- 가장 큰 글씨, 흰색
서브 텍스트            <- 큰 글씨, 흰색
브랜드/강조            <- 중간 글씨, 강조색 (accent_color)
                       (하단)
가격/CTA              <- 강조색 (accent_color)
```

### 강조색 팔레트 (accent_color)

| 키 | 색상 | Hex | 용도 |
|------|------|-----|------|
| `coral` | 코랄 로즈 | `#D4847A` | 뷰티, 스킨케어, 로맨틱 (기본값) |
| `lime` | 소프트 라임 | `#A8C97A` | 프레시, 자연, 건강 |
| `yellow` | 머스타드 옐로 | `#D4B86A` | 세일, 할인, 포인트 |
| `lavender` | 더스티 라벤더 | `#9B8EC4` | 프리미엄, 고급, 트렌디 |
| `peach` | 밀키 피치 | `#E8A88A` | 따뜻한, 일상, 데일리 |

texts에 `"accent_color": "lime"` 추가하면 강조색 변경 가능.

---

## Style B: 방송 자막 바 (broadcast)

| 항목 | 설정 |
|------|------|
| 폰트 | G마켓 산스 볼드 (`GmarketSansBold.otf`) |
| 기울기 | 없음 (정자) |
| 테두리 | 없음 |
| 텍스트 색상 | 검정 `#000000` |
| 배경 바 | 흰색 반투명 `rgba(255,255,255,0.85)`, 라운드 코너 |
| 정렬 | 가운데 정렬 |
| 용도 | 나레이션 자막, 설명 자막, 인터뷰 |

텍스트 구조:
```
+----------------------------------+
|  이렇게 뭐 용량이 많을 필요도     |  <- 흰색 바 + 검정 텍스트
|  없을 것 같긴 해요               |
+----------------------------------+
```

---

## 사용법

```python
from core.beauty_video import apply_subtitle, apply_subtitle_to_image

# Style A: 썸네일 스타일
result = apply_subtitle(
    image_path="input.jpg",
    style="thumbnail",
    texts={
        "subtitle": "압도적 빔력;;",
        "main": ["하이라이터", "5종 비교"],
        "brand": "BANILA CO",
        "price": "16,000원",
    },
)

# Style B: 방송 자막 바
result = apply_subtitle(
    image_path="input.jpg",
    style="broadcast",
    texts={
        "lines": ["이렇게 뭐 용량이 많을 필요도", "없을 것 같긴 해요"],
    },
    position="bottom",  # top, center, bottom
)

# PIL Image 직접 처리
from PIL import Image

img = Image.open("startframe.jpg")
result = apply_subtitle_to_image(
    img,
    style="broadcast",
    texts={"lines": ["이렇게 뭐 용량이 많을 필요도", "없을 것 같긴 해요"]},
    position="bottom",
)
result.save("startframe_subtitled.jpg")
```

---

## 싱크 자막 (Phase 6)

TTS 나레이션에 맞춰 실시간 싱크 자막을 영상 위에 오버레이.

```python
from core.beauty_video.video_subtitle import (
    add_synced_subtitles,
    calculate_phrase_timings,
    get_audio_duration,
)

# 타이밍 계산
timings = calculate_phrase_timings(
    phrases_per_cut=[
        ["아침에 바른 이 광채,", "밤까지 가면", "믿으시겠어요?"],
        ["프라이머 명가답게", "모공 부각 0."],
    ],
    tts_duration=15.2,
    tts_delay=0.3,
    pause_between_cuts=0.4,
)

# 자막 오버레이
add_synced_subtitles(
    video_path="input.mp4",
    timings=timings,
    output_path="output.mp4",
    style="reels",              # "reels" 또는 "broadcast"
    margin_bottom_ratio=0.10,
)
```

### 싱크 자막 스타일

| 스타일 | 설명 | 외관 |
|--------|------|------|
| `broadcast` | 흰색 반투명 바 + 검정 글씨 | 방송 뉴스 느낌 |
| `reels` | 흰색 글씨 + 아웃라인 + 그림자 | 인스타 릴스/틱톡 |

### 이미지 구운 자막 스킵

`subtitle` 필드가 있는 컷(Phase 1.5에서 베이킹된 컷)은 Phase 6 싱크 자막에서 자동 스킵. 겹침 방지.

```python
# pipeline.py Phase 6 로직
subtitle_cut_indices = {i for i, cut in enumerate(cuts) if cut.get("subtitle")}
filtered_phrases = [p for i, p in enumerate(phrases) if i not in subtitle_cut_indices]
```

### TTS-자막 싱크 계산 (컷 스킵 시)

TTS가 전체 N컷을 읽지만 자막은 일부 컷만 표시할 때, 글자 수 비율로 유효 TTS 시간을 계산:

```python
effective_dur = tts_dur * (displayed_chars / total_chars)
```

---

## 디자인 원칙

1. **이모지는 의미있는 위치에만** — 아무데나 붙이지 않는다
2. **색상 변화로 시각적 재미** — 이모지 대신 색상 분리 활용
3. **텍스트 블록 밀착** — 줄간 최소화, 한 덩어리로 구성
4. **가운데 정렬** — 모든 텍스트 중앙 정렬
5. **폰트 통일** — G마켓 산스 볼드 단일 폰트

## 의존성

- `Pillow` (PIL), `pilmoji` (Apple 3D 이모지 렌더링)
- 폰트: `C:/Windows/Fonts/GmarketSansBold.otf` 또는 `~/AppData/Local/Microsoft/Windows/Fonts/GmarketSansBold.otf`
