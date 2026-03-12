# Suno API BGM 참조

> SKILL.md에서 참조하는 서포트 파일. Suno 모델, BGM 프리셋, 사용법 상세.
> 모든 코드: `core/beauty_video/bgm.py`

## 규칙

1. **Suno API** (`https://api.sunoapi.org/api/v1/generate`) 사용
2. **인스트루멘탈 모드 기본** — 뷰티 영상 BGM은 보통 가사 없음
3. **프롬프트는 영어** — Suno API는 영어 프롬프트가 품질 좋음
4. **폴링 방식**: taskId 발급 → 10초 간격 폴링 → 완료 시 다운로드
5. **생성 시간**: ~30초 (stream URL) ~ 2~3분 (download URL)

## Suno 모델

| 모델 | 설명 | 기본 |
|------|------|------|
| `V4` | V4 기본 | |
| `V4_5` | V4.5 기본 추천 | O |
| `V4_5PLUS` | V4.5 고품질 | |
| `V5` | 최신 | |

## BGM 프리셋

| 이름 | 스타일 | 적합한 컷 |
|------|--------|----------|
| `beauty_lofi` | lo-fi bedroom pop | Hook, Apply |
| `beauty_upbeat` | K-pop instrumental | CTA, Highlight |
| `beauty_elegant` | Piano + strings | 럭셔리 브랜드 |
| `beauty_cafe` | Cafe jazz | Proof, 일상 |
| `beauty_dreamy` | Synth pop | 스킨케어, 몽환 |

## 사용법

```python
from core.beauty_video.bgm import (
    generate_bgm,
    generate_bgm_for_preset,
    overlay_bgm_on_video,
    BGM_PRESETS,
)

# 프리셋으로 BGM 생성
bgm_path = generate_bgm_for_preset(
    preset_name="beauty_lofi",
    output_path="output/bgm_lofi.mp3",
)

# 커스텀 프롬프트로 생성
bgm_path = generate_bgm(
    prompt="trendy lo-fi bedroom pop, cozy aesthetic",
    output_path="output/bgm_custom.mp3",
    model="V4_5",
    instrumental=True,
    duration=30,
)

# 영상에 BGM 오버레이 (15% 볼륨, 페이드인/아웃)
overlay_bgm_on_video(
    video_path="output/video_with_tts.mp4",
    bgm_path="output/bgm_lofi.mp3",
    output_path="output/final.mp4",
    bgm_vol=0.15,
    fade_in=1.0,
    fade_out=2.0,
)
```

## 비용

| 항목 | 단가 |
|------|------|
| Suno API (Pro plan) | ~$0.05 / 곡 |
| 30초 BGM 1곡 | ~$0.05 (~70원) |
