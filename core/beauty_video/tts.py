"""ElevenLabs TTS module for beauty video narration.

Supports:
- Multiple voice presets (Hanna, Emma as defaults)
- eleven_multilingual_v2 model for Korean
- MP3 generation -> WAV conversion via ffmpeg
- Speed adjustment to match video duration
"""

import os
import wave
import subprocess
from pathlib import Path


# ============================================================
# 보이스 프리셋 (Voice Presets)
# ElevenLabs Voice Library에서 voice_id 확인 가능
# ============================================================
VOICE_PRESETS = {
    "rachel": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "desc": "Female, clear, warm narration",
        "note": "Built-in voice",
    },
    "nicole": {
        "voice_id": "piTKgcLEGmPE4e6mEKli",
        "desc": "Female, soft, whisper-like ASMR",
        "note": "Built-in voice - default",
    },
    "hanna": {
        "voice_id": "",  # Voice Library에서 복사 필요 (한국어 여성 음성)
        "desc": "Korean female, natural and clear",
        "note": "Voice Library - copy ID from ElevenLabs site",
    },
    "sarah": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "desc": "Young female, soft, warm",
        "note": "Built-in voice",
    },
    "charlotte": {
        "voice_id": "XB0fDUnXU5powFXDhCwa",
        "desc": "Female, youthful, Swedish-English",
        "note": "Built-in voice",
    },
    "alice": {
        "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
        "desc": "Female, confident, middle-aged",
        "note": "Built-in voice",
    },
    "jessica": {
        "voice_id": "cgSgspJ2msm6clMCkdW9",
        "desc": "Young female, playful, bright, warm",
        "note": "Built-in voice",
    },
    "matilda": {
        "voice_id": "XrExE9yKIg1WjnnlVkGX",
        "desc": "Female, knowledgeable, professional",
        "note": "Built-in voice",
    },
    "lily": {
        "voice_id": "pFZP5JQG7iQjIQuC4Bku",
        "desc": "Female, velvety actress",
        "note": "Built-in voice",
    },
}

# 기본 TTS 모델 - 한국어 지원
DEFAULT_TTS_MODEL = "eleven_multilingual_v2"

# TTS 음성 설정 기본값
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}


def get_wav_duration(wav_path: str) -> float:
    """WAV 파일의 재생 시간(초)을 반환한다.

    Args:
        wav_path: WAV 파일 경로

    Returns:
        재생 시간 (초, float)

    Raises:
        FileNotFoundError: 파일이 없을 때
        wave.Error: WAV 파일 파싱 실패 시
    """
    wav_path = str(wav_path)
    if not Path(wav_path).exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    with wave.open(wav_path, "rb") as wf:
        # 프레임 수 / 샘플레이트 = 재생 시간
        n_frames = wf.getnframes()
        frame_rate = wf.getframerate()
        duration = n_frames / float(frame_rate)

    return duration


def generate_tts(
    voice_id: str,
    text: str,
    output_path: str,
    model: str = DEFAULT_TTS_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
) -> str:
    """ElevenLabs TTS로 음성 파일(WAV)을 생성한다.

    MP3로 먼저 생성한 후 ffmpeg으로 WAV(pcm_s16le, 44100Hz, mono)로 변환한다.

    Args:
        voice_id: ElevenLabs voice ID (VOICE_PRESETS 딕셔너리 또는 직접 입력)
        text: TTS 변환할 텍스트
        output_path: 출력 WAV 파일 경로
        model: ElevenLabs 모델 ID (기본: eleven_multilingual_v2)
        stability: 음성 안정성 (0.0~1.0, 기본: 0.5)
        similarity_boost: 음성 유사도 부스트 (0.0~1.0, 기본: 0.75)
        style: 스타일 강도 (0.0~1.0, 기본: 0.0)
        use_speaker_boost: 스피커 부스트 활성화 (기본: True)

    Returns:
        생성된 WAV 파일 경로

    Raises:
        ImportError: elevenlabs 패키지 미설치 시
        ValueError: voice_id가 비어있을 때
        RuntimeError: TTS 생성 또는 ffmpeg 변환 실패 시
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings
    except ImportError:
        raise ImportError(
            "elevenlabs 패키지가 필요합니다. 설치: pip install elevenlabs"
        )

    # voice_id 유효성 검사
    if not voice_id:
        raise ValueError(
            "voice_id가 비어있습니다. VOICE_PRESETS에서 voice_id를 확인하거나 직접 입력하세요."
        )

    # API 키 로드
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요."
        )

    # 출력 경로 준비
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # MP3 임시 파일 경로 (.wav 확장자를 .mp3로 변경)
    mp3_path = output_path.with_suffix(".mp3")

    print(f"[TTS] Generating audio: voice={voice_id[:8]}... model={model}")
    print(
        f"[TTS] Text ({len(text)} chars): {text[:50]}{'...' if len(text) > 50 else ''}"
    )

    # ElevenLabs 클라이언트 초기화 및 TTS 생성
    client = ElevenLabs(api_key=api_key)

    try:
        # MP3 스트리밍 생성 (mp3_44100_128 포맷)
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model,
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost,
            ),
            output_format="mp3_44100_128",
        )

        # 스트림을 파일로 저장
        with open(mp3_path, "wb") as mp3_file:
            for chunk in audio_generator:
                if chunk:
                    mp3_file.write(chunk)

        print(f"[TTS] MP3 saved: {mp3_path}")

    except Exception as e:
        raise RuntimeError(f"ElevenLabs TTS 생성 실패: {e}")

    # MP3 -> WAV 변환 (ffmpeg, pcm_s16le, 44100Hz, mono)
    wav_path = str(output_path.with_suffix(".wav"))
    _convert_mp3_to_wav(str(mp3_path), wav_path)

    # 임시 MP3 파일 삭제
    if mp3_path.exists():
        mp3_path.unlink()
        print(f"[TTS] Temp MP3 removed: {mp3_path}")

    print(f"[TTS] WAV output: {wav_path}")
    return wav_path


def _convert_mp3_to_wav(mp3_path: str, wav_path: str) -> str:
    """ffmpeg으로 MP3를 WAV(pcm_s16le, 44100Hz, mono)로 변환한다.

    Args:
        mp3_path: 입력 MP3 파일 경로
        wav_path: 출력 WAV 파일 경로

    Returns:
        생성된 WAV 파일 경로

    Raises:
        RuntimeError: ffmpeg 변환 실패 시
    """
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        # imageio_ffmpeg 없으면 시스템 ffmpeg 사용
        ffmpeg_exe = "ffmpeg"

    cmd = [
        ffmpeg_exe,
        "-y",  # 덮어쓰기 허용
        "-i",
        mp3_path,  # 입력 파일
        "-acodec",
        "pcm_s16le",  # 16-bit PCM
        "-ar",
        "44100",  # 샘플레이트 44100Hz
        "-ac",
        "1",  # 모노 채널
        wav_path,  # 출력 파일
    ]

    print(f"[TTS] Converting MP3 -> WAV...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg MP3->WAV 변환 실패 (returncode={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    return wav_path


def speed_adjust_tts(
    input_path: str,
    target_duration: float,
    output_path: str,
) -> str:
    """TTS 오디오 속도를 영상 길이에 맞게 조절한다.

    ffmpeg의 atempo 필터를 사용한다.
    atempo는 0.5~2.0 범위만 지원하므로, 2.0배 이상이면 체이닝한다.
    예: 3.0배속 = atempo=2.0,atempo=1.5

    Args:
        input_path: 입력 WAV 파일 경로
        target_duration: 목표 재생 시간 (초)
        output_path: 출력 WAV 파일 경로

    Returns:
        속도 조절된 WAV 파일 경로

    Raises:
        FileNotFoundError: 입력 파일이 없을 때
        ValueError: target_duration이 0 이하일 때
        RuntimeError: ffmpeg 처리 실패 시
    """
    input_path = str(input_path)
    output_path = str(output_path)

    if not Path(input_path).exists():
        raise FileNotFoundError(f"Input WAV not found: {input_path}")

    if target_duration <= 0:
        raise ValueError(f"target_duration must be > 0, got: {target_duration}")

    # 현재 오디오 길이 확인
    current_duration = get_wav_duration(input_path)
    if current_duration <= 0:
        raise RuntimeError(f"Invalid WAV duration: {current_duration}s")

    # 속도 배수 계산 (current / target = speed factor)
    # target이 짧을수록 빠르게, 길수록 느리게
    speed_factor = current_duration / target_duration

    print(
        f"[TTS] Speed adjust: {current_duration:.2f}s -> {target_duration:.2f}s "
        f"(factor={speed_factor:.3f}x)"
    )

    # 속도 변경이 거의 없으면 그냥 복사
    if abs(speed_factor - 1.0) < 0.01:
        import shutil

        shutil.copy2(input_path, output_path)
        print(f"[TTS] Speed unchanged, copied: {output_path}")
        return output_path

    # atempo 필터 체인 구성 (atempo 범위: 0.5~2.0)
    atempo_filters = _build_atempo_filter(speed_factor)
    print(f"[TTS] atempo filter: {atempo_filters}")

    # 출력 경로 디렉토리 생성
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_exe = "ffmpeg"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        input_path,
        "-filter:a",
        atempo_filters,
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "1",
        output_path,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 속도 조절 실패 (returncode={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    # 결과 확인
    adjusted_duration = get_wav_duration(output_path)
    print(
        f"[TTS] Speed adjusted: {adjusted_duration:.2f}s (target: {target_duration:.2f}s)"
    )

    return output_path


def _build_atempo_filter(speed_factor: float) -> str:
    """속도 배수에 맞는 ffmpeg atempo 필터 문자열을 반환한다.

    atempo 필터는 0.5~2.0 범위만 허용하므로
    범위를 벗어나면 여러 atempo를 체이닝한다.

    Args:
        speed_factor: 속도 배수 (예: 1.5, 2.5, 0.3)

    Returns:
        ffmpeg -filter:a 인수 문자열 (예: "atempo=1.5" 또는 "atempo=2.0,atempo=1.25")
    """
    filters = []
    remaining = speed_factor

    if speed_factor > 1.0:
        # 빠르게: 2.0씩 나누어 체이닝
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        filters.append(f"atempo={remaining:.4f}")
    elif speed_factor < 1.0:
        # 느리게: 0.5씩 나누어 체이닝
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining:.4f}")
    else:
        filters.append("atempo=1.0")

    return ",".join(filters)


def overlay_tts_on_video(
    video_path: str,
    tts_path: str,
    output_path: str,
    bgm_vol: float = 0.3,
    tts_delay_ms: int = 300,
) -> str:
    """TTS 오디오를 영상에 합성한다.

    영상에 기존 오디오가 있으면 볼륨을 줄이고 TTS와 amix한다.
    영상에 오디오가 없으면 TTS를 adelay로 지연 후 추가한다.

    Args:
        video_path: 입력 영상 파일 경로 (MP4 등)
        tts_path: TTS WAV 파일 경로
        output_path: 출력 영상 파일 경로
        bgm_vol: 기존 BGM 볼륨 축소 비율 (0.0~1.0, 기본: 0.3 = 30%)
        tts_delay_ms: TTS 시작 지연 시간 (밀리초, 기본: 300ms)

    Returns:
        합성된 영상 파일 경로

    Raises:
        FileNotFoundError: 입력 파일이 없을 때
        RuntimeError: ffmpeg 합성 실패 시
    """
    video_path = str(video_path)
    tts_path = str(tts_path)
    output_path = str(output_path)

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not Path(tts_path).exists():
        raise FileNotFoundError(f"TTS WAV file not found: {tts_path}")

    # 출력 경로 디렉토리 생성
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_exe = "ffmpeg"

    # 영상에 오디오 스트림이 있는지 확인
    has_audio = _check_video_has_audio(video_path, ffmpeg_exe)
    print(f"[TTS] Video has audio: {has_audio}")

    if has_audio:
        # 기존 BGM 볼륨 축소 + TTS 지연 후 amix 합성
        # filter_complex 설명:
        #   [0:a]volume={bgm_vol}[bgm]  - 기존 오디오 볼륨 축소
        #   [1:a]adelay={delay}|{delay}[tts]  - TTS 지연 적용
        #   [bgm][tts]amix=inputs=2:duration=first[aout]  - 두 오디오 믹싱
        filter_complex = (
            f"[0:a]volume={bgm_vol}[bgm];"
            f"[1:a]adelay={tts_delay_ms}|{tts_delay_ms}[tts];"
            f"[bgm][tts]amix=inputs=2:duration=first[aout]"
        )
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            video_path,  # 입력 0: 영상 (비디오 + 기존 오디오)
            "-i",
            tts_path,  # 입력 1: TTS
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",  # 비디오 스트림: 원본 영상에서
            "-map",
            "[aout]",  # 오디오 스트림: 믹싱 결과
            "-c:v",
            "copy",  # 비디오 재인코딩 없이 복사
            "-c:a",
            "aac",  # 오디오 AAC 인코딩
            "-b:a",
            "192k",
            "-shortest",  # 가장 짧은 스트림 길이로 맞춤
            output_path,
        ]
        print(
            f"[TTS] Overlaying TTS on video with BGM (bgm_vol={bgm_vol}, "
            f"delay={tts_delay_ms}ms)..."
        )
    else:
        # 오디오 없는 영상: TTS를 adelay로 지연 후 추가
        filter_complex = f"[1:a]adelay={tts_delay_ms}|{tts_delay_ms}[tts]"
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            video_path,  # 입력 0: 영상 (비디오만)
            "-i",
            tts_path,  # 입력 1: TTS
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",  # 비디오 스트림: 원본 영상에서
            "-map",
            "[tts]",  # 오디오 스트림: 지연된 TTS
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            output_path,
        ]
        print(f"[TTS] Adding TTS to silent video (delay={tts_delay_ms}ms)...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg TTS 합성 실패 (returncode={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    print(f"[TTS] Overlay complete: {output_path}")
    return output_path


def _check_video_has_audio(video_path: str, ffmpeg_exe: str = "ffmpeg") -> bool:
    """영상 파일에 오디오 스트림이 있는지 확인한다.

    ffprobe(또는 ffmpeg)로 스트림 정보를 파싱한다.

    Args:
        video_path: 영상 파일 경로
        ffmpeg_exe: ffmpeg 실행 파일 경로

    Returns:
        오디오 스트림 존재 여부
    """
    # ffprobe 경로 추론 (ffmpeg과 같은 디렉토리에 있음)
    ffprobe_exe = str(Path(ffmpeg_exe).parent / "ffprobe")
    if not Path(ffprobe_exe).exists():
        # 시스템 경로에서 탐색
        ffprobe_exe = "ffprobe"

    cmd = [
        ffprobe_exe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        "a",  # 오디오 스트림만 조회
        video_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            import json

            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            return len(streams) > 0
    except Exception:
        pass

    # ffprobe 실패 시 ffmpeg stdout으로 대체 탐색
    cmd_fallback = [
        ffmpeg_exe,
        "-v",
        "quiet",
        "-i",
        video_path,
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            cmd_fallback,
            capture_output=True,
            text=True,
        )
        # stderr에서 "Audio:" 포함 여부로 오디오 스트림 존재 확인
        return "Audio:" in result.stderr
    except Exception:
        # 확인 불가 시 오디오 없음으로 가정
        return False


def generate_tts_for_voice_preset(
    preset_name: str,
    text: str,
    output_path: str,
    model: str = DEFAULT_TTS_MODEL,
) -> str:
    """보이스 프리셋 이름으로 TTS를 생성한다.

    VOICE_PRESETS 딕셔너리에서 preset_name에 해당하는 voice_id를 찾아
    generate_tts()를 호출하는 편의 함수.

    Args:
        preset_name: 프리셋 이름 (예: "emma", "jessica")
        text: TTS 변환 텍스트
        output_path: 출력 WAV 파일 경로
        model: ElevenLabs 모델 ID

    Returns:
        생성된 WAV 파일 경로

    Raises:
        KeyError: preset_name이 VOICE_PRESETS에 없을 때
        ValueError: 프리셋의 voice_id가 비어있을 때
    """
    if preset_name not in VOICE_PRESETS:
        available = list(VOICE_PRESETS.keys())
        raise KeyError(
            f"Unknown voice preset: '{preset_name}'. " f"Available presets: {available}"
        )

    preset = VOICE_PRESETS[preset_name]
    voice_id = preset["voice_id"]

    if not voice_id:
        raise ValueError(
            f"Voice preset '{preset_name}'의 voice_id가 비어있습니다. "
            f"ElevenLabs Voice Library에서 ID를 복사하여 VOICE_PRESETS에 입력하세요.\n"
            f"Note: {preset.get('note', '')}"
        )

    print(f"[TTS] Using preset '{preset_name}': {preset['desc']}")
    return generate_tts(
        voice_id=voice_id,
        text=text,
        output_path=output_path,
        model=model,
    )
