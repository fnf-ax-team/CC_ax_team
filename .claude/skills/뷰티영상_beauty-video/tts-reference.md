# ElevenLabs TTS 나레이션 참조

> SKILL.md에서 참조하는 서포트 파일. TTS 보이스 프리셋, 사용법, 감정 태그 상세.
> 모든 코드: `core/beauty_video/tts.py`

## 규칙

1. **ElevenLabs TTS로 나레이션 생성** — 영상 자체는 무음, TTS는 후처리 Phase에서 추가
2. **기본 보이스**: nicole (soft, whisper-like ASMR)
3. **eleven_multilingual_v2 모델** 사용 (한국어 지원)
4. **MP3 → WAV 변환**: ffmpeg pcm_s16le, 44100Hz, mono
5. **속도 조절**: 영상 길이에 맞게 atempo 필터 자동 적용

## 보이스 프리셋

| 이름 | voice_id | 설명 | 기본 |
|------|----------|------|------|
| `nicole` | `piTKgcLEGmPE4e6mEKli` | Female, soft, whisper-like ASMR | **O** |
| `rachel` | `21m00Tcm4TlvDq8ikWAM` | Female, clear, warm narration | |
| `sarah` | `EXAVITQu4vr4xnSDxMaL` | Young female, soft, warm | |
| `charlotte` | `XB0fDUnXU5powFXDhCwa` | Female, youthful, Swedish-English | |
| `alice` | `Xb7hH8MSUJpSbSDYk0k2` | Female, confident, middle-aged | |
| `jessica` | `cgSgspJ2msm6clMCkdW9` | Young female, playful, bright, warm | |
| `matilda` | `XrExE9yKIg1WjnnlVkGX` | Female, knowledgeable, professional | |
| `lily` | `pFZP5JQG7iQjIQuC4Bku` | Female, velvety actress | |
| `hanna` | (Voice Library) | Korean female, natural and clear | |

> hanna voice_id는 ElevenLabs Voice Library에서 복사 필요 (현재 빈 값)

## 사용법

```python
from core.beauty_video.tts import (
    generate_tts,
    generate_tts_for_voice_preset,
    speed_adjust_tts,
    overlay_tts_on_video,
    VOICE_PRESETS,
)

# 프리셋으로 TTS 생성 (기본: nicole)
wav_path = generate_tts_for_voice_preset(
    preset_name="nicole",
    text="아침에 바른 이 광채, 밤까지 가면 믿으시겠어요?",
    output_path="output/tts_nicole.wav",
)

# voice_id 직접 사용
wav_path = generate_tts(
    voice_id="YA32deq2ptJFAupM9cWf",
    text="내 피부 톤에 맞는 광채를 찾으세요.",
    output_path="output/tts_raw.wav",
    stability=0.5,
    similarity_boost=0.75,
)

# 영상 길이에 맞게 속도 조절
adjusted = speed_adjust_tts(
    input_path="output/tts_raw.wav",
    target_duration=20.0,
    output_path="output/tts_adjusted.wav",
)

# 영상에 TTS 오버레이 (기존 BGM 볼륨 30%로 축소)
overlay_tts_on_video(
    video_path="output/video.mp4",
    tts_path="output/tts_adjusted.wav",
    output_path="output/video_with_tts.mp4",
    bgm_vol=0.3,
    tts_delay_ms=300,
)
```

## ElevenLabs v3 감정 태그

v3 모델(`model="eleven_v3"`)은 오디오 태그로 감정 표현 가능:

| 태그 | 설명 | 예시 |
|------|------|------|
| `[laughing]` | 웃음 | `[laughing] 진짜요?` |
| `[sad]` | 슬픔 | `[sad] 아쉽지만...` |
| `[excited]` | 흥분 | `[excited] 대박이에요!` |
| `[whisper]` | 속삭임 | `[whisper] 비밀인데요` |
| `[sigh]` | 한숨 | `[sigh] 피곤해요` |

## 비용

| 항목 | 단가 |
|------|------|
| ElevenLabs TTS (Creator plan) | ~$0.10 / 1,000자 |
| 4컷 나레이션 (~200자) | ~$0.02 (~30원) |
