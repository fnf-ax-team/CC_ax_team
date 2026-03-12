"""Suno API BGM module for beauty video background music.

Supports:
- AI music generation via Suno API (V4, V4.5, V5 models)
- Custom/auto lyrics + instrumental modes
- Async polling with stream URL + download URL
- ffmpeg integration for video BGM overlay
"""

import os
import time
import subprocess
import json
from pathlib import Path
from typing import Optional


# ============================================================
# Suno API 설정
# ============================================================
SUNO_API_BASE = "https://api.sunoapi.org/api/v1"

# 모델 옵션
SUNO_MODELS = {
    "V4": "V4",
    "V4_5": "V4_5",  # 기본 추천
    "V4_5PLUS": "V4_5PLUS",  # 고품질
    "V4_5ALL": "V4_5ALL",
    "V5": "V5",  # 최신
}

DEFAULT_SUNO_MODEL = "V4_5"

# 뷰티 영상용 BGM 프리셋
BGM_PRESETS = {
    "beauty_lofi": {
        "prompt": "trendy lo-fi bedroom pop, soft female vocal humming, "
        "cozy aesthetic, beauty vlog background music",
        "style": "lo-fi pop",
        "instrumental": True,
        "duration": 30,
    },
    "beauty_upbeat": {
        "prompt": "upbeat trendy K-pop inspired instrumental, "
        "bright and energetic, beauty product showcase",
        "style": "K-pop instrumental",
        "instrumental": True,
        "duration": 30,
    },
    "beauty_elegant": {
        "prompt": "elegant piano and strings, luxury cosmetics commercial, "
        "sophisticated and feminine, soft ambient",
        "style": "cinematic elegant",
        "instrumental": True,
        "duration": 30,
    },
    "beauty_cafe": {
        "prompt": "warm cafe jazz, gentle acoustic guitar, "
        "cozy afternoon vibe, beauty content background",
        "style": "cafe jazz",
        "instrumental": True,
        "duration": 30,
    },
    "beauty_dreamy": {
        "prompt": "dreamy synth pop, ethereal pads, soft beat, "
        "pastel aesthetic, skincare routine background",
        "style": "synth pop",
        "instrumental": True,
        "duration": 30,
    },
}


def generate_bgm(
    prompt: str,
    output_path: str,
    model: str = DEFAULT_SUNO_MODEL,
    instrumental: bool = True,
    duration: int = 30,
    title: str = "Beauty BGM",
    poll_interval: int = 10,
    max_wait: int = 300,
) -> str:
    """Suno API로 BGM을 생성하고 파일로 저장한다.

    Args:
        prompt: 음악 스타일/분위기 프롬프트 (영어 권장)
        output_path: 출력 파일 경로 (.mp3)
        model: Suno 모델 (V4, V4_5, V4_5PLUS, V5)
        instrumental: 가사 없는 인스트루멘탈 모드 (기본: True)
        duration: 음악 길이 (초, 기본: 30)
        title: 음악 제목
        poll_interval: 폴링 간격 (초, 기본: 10)
        max_wait: 최대 대기 시간 (초, 기본: 300)

    Returns:
        저장된 파일 경로

    Raises:
        ImportError: requests 패키지 미설치 시
        RuntimeError: API 호출 또는 다운로드 실패 시
    """
    try:
        import requests
    except ImportError:
        raise ImportError("requests 패키지가 필요합니다. 설치: pip install requests")

    # API 키 로드
    api_key = os.getenv("SUNO_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SUNO_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요."
        )

    # 출력 경로 준비
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 요청 payload 구성
    payload = {
        "model": model,
        "prompt": prompt,
        "title": title,
        "customMode": True,
        "instrumental": instrumental,
        "callBackUrl": "https://localhost/callback",  # polling 방식이므로 더미 URL
    }

    # 가사 모드일 경우 lyrics 필드 필요 (instrumental=False)
    if not instrumental:
        payload["lyrics"] = prompt  # 프롬프트를 가사로도 사용

    print(f"[BGM] Generating: model={model}, instrumental={instrumental}")
    print(f"[BGM] Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    # Step 1: 생성 요청
    resp = requests.post(
        f"{SUNO_API_BASE}/generate",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Suno API 생성 요청 실패 (status={resp.status_code}): {resp.text}"
        )

    result = resp.json()
    # taskId가 최상위 또는 data 내부에 있을 수 있음
    task_id = (
        result.get("taskId")
        or result.get("task_id")
        or (result.get("data") or {}).get("taskId")
        or (result.get("data") or {}).get("task_id")
    )

    if not task_id:
        # 일부 API 응답에서 직접 URL 반환하는 경우
        audio_url = _extract_audio_url(result)
        if audio_url:
            return _download_audio(audio_url, str(output_path))
        raise RuntimeError(f"Suno API 응답에서 taskId를 찾을 수 없습니다: {result}")

    print(f"[BGM] Task submitted: {task_id}")

    # Step 2: 폴링으로 완료 대기
    elapsed = 0
    audio_url = None

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        print(f"[BGM] Polling... ({elapsed}s / {max_wait}s)")

        status_resp = requests.get(
            f"{SUNO_API_BASE}/generate/record-info",
            headers=headers,
            params={"taskId": task_id},
            timeout=15,
        )

        if status_resp.status_code != 200:
            print(f"[BGM] Poll failed (status={status_resp.status_code}), retrying...")
            continue

        status_data = status_resp.json()
        # 응답 구조: {"code":200, "data": {"status":"SUCCESS", "response": {"sunoData": [...]}}}
        inner = status_data.get("data", {})
        task_status = inner.get("status", "") or status_data.get("status", "")

        print(f"[BGM] Status: {task_status}")

        if task_status.upper() in ("SUCCESS", "COMPLETE", "COMPLETED"):
            # sunoData에서 audioUrl 추출
            suno_data = inner.get("response", {}).get("sunoData", [])
            if suno_data and isinstance(suno_data, list):
                audio_url = suno_data[0].get("audioUrl") or suno_data[0].get(
                    "sourceAudioUrl"
                )
            if not audio_url:
                audio_url = _extract_audio_url(status_data)
            if audio_url:
                break

        if task_status.upper() in ("FAILED", "ERROR"):
            raise RuntimeError(f"Suno BGM 생성 실패: {status_data}")

    if not audio_url:
        raise RuntimeError(
            f"Suno BGM 생성 타임아웃 ({max_wait}초 초과). taskId={task_id}"
        )

    # Step 3: 오디오 다운로드
    return _download_audio(audio_url, str(output_path))


def _extract_audio_url(data: dict) -> Optional[str]:
    """Suno API 응답에서 오디오 URL을 추출한다.

    다양한 응답 형식을 처리한다.
    """
    # 직접 URL 필드
    for key in ("audio_url", "audioUrl", "download_url", "downloadUrl", "stream_url"):
        if key in data and data[key]:
            return data[key]

    # data 중첩 구조
    inner = data.get("data", {})
    if isinstance(inner, dict):
        for key in (
            "audio_url",
            "audioUrl",
            "download_url",
            "downloadUrl",
            "stream_url",
        ):
            if key in inner and inner[key]:
                return inner[key]

        # songs/tracks 배열
        songs = inner.get("songs") or inner.get("tracks") or inner.get("clips", [])
        if songs and isinstance(songs, list):
            song = songs[0]
            for key in ("audio_url", "audioUrl", "download_url", "downloadUrl"):
                if key in song and song[key]:
                    return song[key]

    # result 배열
    results = data.get("result") or data.get("results", [])
    if isinstance(results, list) and results:
        item = results[0]
        for key in ("audio_url", "audioUrl", "download_url", "downloadUrl"):
            if key in item and item[key]:
                return item[key]

    return None


def _download_audio(url: str, output_path: str) -> str:
    """URL에서 오디오 파일을 다운로드한다."""
    import requests

    print(f"[BGM] Downloading: {url[:80]}...")

    resp = requests.get(url, timeout=60, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"오디오 다운로드 실패 (status={resp.status_code})")

    output_path = Path(output_path)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    size_kb = output_path.stat().st_size / 1024
    print(f"[BGM] Downloaded: {output_path} ({size_kb:.0f}KB)")
    return str(output_path)


def generate_bgm_for_preset(
    preset_name: str,
    output_path: str,
    model: str = DEFAULT_SUNO_MODEL,
) -> str:
    """BGM 프리셋 이름으로 BGM을 생성한다.

    Args:
        preset_name: 프리셋 이름 (예: "beauty_lofi", "beauty_upbeat")
        output_path: 출력 파일 경로
        model: Suno 모델 ID

    Returns:
        생성된 파일 경로

    Raises:
        KeyError: preset_name이 BGM_PRESETS에 없을 때
    """
    if preset_name not in BGM_PRESETS:
        available = list(BGM_PRESETS.keys())
        raise KeyError(
            f"Unknown BGM preset: '{preset_name}'. " f"Available presets: {available}"
        )

    preset = BGM_PRESETS[preset_name]
    print(f"[BGM] Using preset '{preset_name}': {preset['style']}")

    return generate_bgm(
        prompt=preset["prompt"],
        output_path=output_path,
        model=model,
        instrumental=preset.get("instrumental", True),
        duration=preset.get("duration", 30),
        title=f"Beauty BGM - {preset['style']}",
    )


def overlay_bgm_on_video(
    video_path: str,
    bgm_path: str,
    output_path: str,
    bgm_vol: float = 0.15,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
) -> str:
    """영상에 BGM을 오버레이한다.

    기존 오디오가 있으면 amix로 합성한다.
    BGM은 fade-in/fade-out 적용하여 자연스럽게 깔린다.

    Args:
        video_path: 입력 영상 파일 경로
        bgm_path: BGM 오디오 파일 경로 (MP3/WAV)
        output_path: 출력 영상 파일 경로
        bgm_vol: BGM 볼륨 (0.0~1.0, 기본: 0.15 = 15%)
        fade_in: BGM 페이드인 시간 (초, 기본: 1.0)
        fade_out: BGM 페이드아웃 시간 (초, 기본: 2.0)

    Returns:
        합성된 영상 파일 경로

    Raises:
        FileNotFoundError: 입력 파일이 없을 때
        RuntimeError: ffmpeg 합성 실패 시
    """
    video_path = str(video_path)
    bgm_path = str(bgm_path)
    output_path = str(output_path)

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not Path(bgm_path).exists():
        raise FileNotFoundError(f"BGM not found: {bgm_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_exe = "ffmpeg"

    # 영상 길이 확인 (ffprobe)
    video_dur = _get_media_duration(video_path, ffmpeg_exe)

    # BGM 필터: 볼륨 + 페이드인 + 페이드아웃 + 영상 길이에 맞게 자르기
    bgm_filter = f"volume={bgm_vol}" f",afade=t=in:st=0:d={fade_in}"
    if video_dur and video_dur > fade_out:
        bgm_filter += f",afade=t=out:st={video_dur - fade_out}:d={fade_out}"

    # 기존 오디오 존재 여부 확인
    has_audio = _check_has_audio(video_path, ffmpeg_exe)

    if has_audio:
        # 기존 오디오 + BGM 합성
        filter_complex = (
            f"[1:a]{bgm_filter}[bgm];" f"[0:a][bgm]amix=inputs=2:duration=first[aout]"
        )
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            video_path,
            "-i",
            bgm_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            output_path,
        ]
    else:
        # 영상에 오디오 없음 → BGM만 추가
        filter_complex = f"[1:a]{bgm_filter}[bgm]"
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            video_path,
            "-i",
            bgm_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[bgm]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            output_path,
        ]

    print(
        f"[BGM] Overlaying BGM (vol={bgm_vol}, fade_in={fade_in}s, fade_out={fade_out}s)..."
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg BGM 합성 실패 (returncode={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    print(f"[BGM] Overlay complete: {output_path}")
    return output_path


def _get_media_duration(path: str, ffmpeg_exe: str = "ffmpeg") -> Optional[float]:
    """ffprobe로 미디어 길이(초)를 확인한다."""
    ffprobe_exe = str(Path(ffmpeg_exe).parent / "ffprobe")
    if not Path(ffprobe_exe).exists():
        ffprobe_exe = "ffprobe"

    cmd = [
        ffprobe_exe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            dur = info.get("format", {}).get("duration")
            if dur:
                return float(dur)
    except Exception:
        pass

    return None


def _check_has_audio(path: str, ffmpeg_exe: str = "ffmpeg") -> bool:
    """영상에 오디오 스트림이 있는지 확인한다."""
    ffprobe_exe = str(Path(ffmpeg_exe).parent / "ffprobe")
    if not Path(ffprobe_exe).exists():
        ffprobe_exe = "ffprobe"

    cmd = [
        ffprobe_exe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        "a",
        path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return len(info.get("streams", [])) > 0
    except Exception:
        pass

    # fallback: ffmpeg stderr에서 Audio: 탐색
    try:
        result = subprocess.run(
            [ffmpeg_exe, "-i", path, "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        return "Audio:" in result.stderr
    except Exception:
        return False
