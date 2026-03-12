"""영상 자막 오버레이 모듈 (Video Subtitle Overlay).

TTS 싱크 자막을 영상 프레임 위에 렌더링한다.

스타일:
  - broadcast: 흰색 바 + 검은 굵은 글씨 (방송 자막)
  - reels: 배경 없이 흰색 둥근 텍스트 + 아웃라인 (릴스/숏폼 자막)

사용법:
    from core.beauty_video.video_subtitle import add_synced_subtitles

    timings = [
        (0.3, 2.5, "아침에 바른 이 광채,"),
        (2.5, 4.0, "밤까지 가면"),
        (4.0, 5.0, "믿으시겠어요?"),
    ]
    add_synced_subtitles(
        video_path="input.mp4",
        timings=timings,
        output_path="output.mp4",
        style="broadcast",  # or "reels"
    )
"""

import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# 폰트 로딩
# ============================================================
_FONT_PATHS_BOLD = [
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts/GmarketSansBold.otf",
    Path("C:/Windows/Fonts/GmarketSansBold.otf"),
    Path("C:/Windows/Fonts/malgunbd.ttf"),
]

_FONT_PATHS_REGULAR = [
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts/GmarketSansMedium.otf",
    Path("C:/Windows/Fonts/GmarketSansMedium.otf"),
    Path("C:/Windows/Fonts/malgun.ttf"),
]


def _find_font(paths):
    for fp in paths:
        if fp.exists():
            return str(fp)
    return None


_bold_font_path = _find_font(_FONT_PATHS_BOLD)
_regular_font_path = _find_font(_FONT_PATHS_REGULAR)


def _font_bold(size: int) -> ImageFont.FreeTypeFont:
    if _bold_font_path:
        return ImageFont.truetype(_bold_font_path, size)
    return ImageFont.load_default()


def _font_regular(size: int) -> ImageFont.FreeTypeFont:
    if _regular_font_path:
        return ImageFont.truetype(_regular_font_path, size)
    return _font_bold(size)


def _text_size(text: str, font: ImageFont.FreeTypeFont, stroke_width: int = 0):
    """텍스트의 (width, height) 반환."""
    tmp = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(tmp).textbbox(
        (0, 0), text, font=font, anchor="lt", stroke_width=stroke_width
    )
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ============================================================
# 스타일: broadcast (방송 자막 바)
# ============================================================
def _render_broadcast(
    text: str,
    video_w: int,
    video_h: int,
    font_scale: float = 1.0,
    margin_bottom_ratio: float = 0.10,
) -> np.ndarray:
    """broadcast 스타일 — 흰색 라운드 바 + 검은 굵은 글씨.

    Args:
        text: 자막 텍스트
        video_w: 영상 가로 픽셀
        video_h: 영상 세로 픽셀
        font_scale: 폰트 크기 배율 (기본 1.0)
        margin_bottom_ratio: 하단 여백 비율

    Returns:
        RGBA numpy array (video_h, video_w, 4)
    """
    # 폰트 크기 — 영상 폭 기준
    font_size = int(video_w * 0.048 * font_scale)
    fnt = _font_bold(font_size)

    tw, th = _text_size(text, fnt)

    # 바 크기
    pad_x = int(video_w * 0.04)
    pad_y = int(font_size * 0.5)
    bar_w = tw + pad_x * 2
    bar_h = th + pad_y * 2
    radius = int(font_size * 0.35)

    # 바 위치 (하단 중앙)
    bar_x = (video_w - bar_w) // 2
    bar_y = int(video_h * (1.0 - margin_bottom_ratio)) - bar_h

    # RGBA 캔버스
    img = Image.new("RGBA", (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 그림자 (살짝)
    shadow_off = max(2, int(font_size * 0.06))
    draw.rounded_rectangle(
        [
            bar_x + shadow_off,
            bar_y + shadow_off,
            bar_x + bar_w + shadow_off,
            bar_y + bar_h + shadow_off,
        ],
        radius=radius,
        fill=(0, 0, 0, 35),
    )

    # 흰색 바
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=radius,
        fill=(255, 255, 255, 225),
    )

    # 검정 텍스트 (중앙 정렬)
    text_x = video_w // 2
    text_y = bar_y + bar_h // 2
    draw.text(
        (text_x, text_y),
        text,
        font=fnt,
        fill=(0, 0, 0, 255),
        anchor="mm",
    )

    return np.array(img)


# ============================================================
# 스타일: reels (릴스/숏폼 자막)
# ============================================================
def _render_reels(
    text: str,
    video_w: int,
    video_h: int,
    font_scale: float = 1.0,
    margin_bottom_ratio: float = 0.10,
) -> np.ndarray:
    """reels 스타일 — 배경 없이 흰색 텍스트 + 두꺼운 아웃라인.

    릴스/숏폼에서 흔히 쓰는 깔끔한 자막 스타일.
    흰색 둥근 텍스트 + 검정 아웃라인 + 살짝 드롭섀도우.

    Args:
        text: 자막 텍스트
        video_w: 영상 가로 픽셀
        video_h: 영상 세로 픽셀
        font_scale: 폰트 크기 배율 (기본 1.0)
        margin_bottom_ratio: 하단 여백 비율

    Returns:
        RGBA numpy array (video_h, video_w, 4)
    """
    # 폰트 크기
    font_size = int(video_w * 0.055 * font_scale)
    fnt = _font_bold(font_size)
    stroke_w = max(3, int(font_size * 0.12))

    tw, th = _text_size(text, fnt, stroke_w)

    # 위치 (하단 중앙)
    text_x = video_w // 2
    text_y = int(video_h * (1.0 - margin_bottom_ratio)) - th // 2

    # RGBA 캔버스
    img = Image.new("RGBA", (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 드롭 섀도우 (부드럽게)
    shadow_off = max(2, int(font_size * 0.06))
    draw.text(
        (text_x + shadow_off, text_y + shadow_off),
        text,
        font=fnt,
        fill=(0, 0, 0, 100),
        anchor="mm",
        stroke_width=stroke_w + 1,
        stroke_fill=(0, 0, 0, 80),
    )

    # 메인 텍스트 (흰색 + 검정 아웃라인)
    draw.text(
        (text_x, text_y),
        text,
        font=fnt,
        fill=(255, 255, 255, 255),
        anchor="mm",
        stroke_width=stroke_w,
        stroke_fill=(0, 0, 0, 220),
    )

    return np.array(img)


# ============================================================
# 스타일 레지스트리
# ============================================================
SUBTITLE_STYLES = {
    "broadcast": _render_broadcast,
    "reels": _render_reels,
}

DEFAULT_STYLE = "reels"


# ============================================================
# 프레임 캐시 (동일 텍스트는 한 번만 렌더링)
# ============================================================
class _FrameCache:
    """동일 텍스트 프레임을 캐싱하여 moviepy 렌더링 속도 향상."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str, render_fn, *args, **kwargs):
        if key not in self._cache:
            self._cache[key] = render_fn(*args, **kwargs)
        return self._cache[key]

    def clear(self):
        self._cache.clear()


# ============================================================
# 메인: 영상에 싱크 자막 오버레이
# ============================================================
def add_synced_subtitles(
    video_path: str,
    timings: list,
    output_path: str,
    style: str = DEFAULT_STYLE,
    font_scale: float = 1.0,
    margin_bottom_ratio: float = 0.10,
    fade_duration: float = 0.15,
) -> str:
    """영상에 TTS 싱크 자막을 오버레이한다.

    Args:
        video_path: 입력 영상 파일 경로
        timings: [(start_sec, end_sec, text), ...] 형태의 자막 타이밍 리스트
        output_path: 출력 영상 파일 경로
        style: 자막 스타일 ("broadcast" 또는 "reels")
        font_scale: 폰트 크기 배율 (기본 1.0)
        margin_bottom_ratio: 하단 여백 비율 (기본 0.10 = 하단 10%)
        fade_duration: 자막 페이드인/아웃 시간 (초, 기본 0.15)

    Returns:
        출력 영상 파일 경로

    Raises:
        FileNotFoundError: 입력 파일 미존재
        ValueError: 알 수 없는 스타일
        ImportError: moviepy 미설치
    """
    try:
        from moviepy import (
            VideoFileClip,
            ImageClip,
            CompositeVideoClip,
        )
    except ImportError:
        raise ImportError("moviepy 패키지가 필요합니다. 설치: pip install moviepy")

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if style not in SUBTITLE_STYLES:
        raise ValueError(
            f"Unknown style: '{style}'. Available: {list(SUBTITLE_STYLES.keys())}"
        )

    render_fn = SUBTITLE_STYLES[style]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"[SUBTITLE] Style: {style}, phrases: {len(timings)}, fade: {fade_duration}s")

    video = VideoFileClip(video_path)
    w, h = video.size
    video_dur = video.duration

    cache = _FrameCache()
    overlays = []

    for start, end, text in timings:
        if start >= video_dur:
            break
        end = min(end, video_dur)
        dur = end - start
        if dur < 0.1:
            continue

        # 프레임 렌더링 (캐시)
        rgba = cache.get(
            f"{style}:{text}",
            render_fn,
            text,
            w,
            h,
            font_scale=font_scale,
            margin_bottom_ratio=margin_bottom_ratio,
        )

        # RGB / Alpha 분리
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3] / 255.0

        rgb_clip = ImageClip(rgb)
        mask_clip = ImageClip(alpha, is_mask=True)

        sub_clip = rgb_clip.with_mask(mask_clip).with_start(start).with_duration(dur)

        # 페이드인/아웃 (자연스러운 전환)
        if fade_duration > 0 and dur > fade_duration * 2:
            try:
                from moviepy.video.fx import CrossFadeIn, CrossFadeOut

                sub_clip = sub_clip.with_effects(
                    [
                        CrossFadeIn(fade_duration),
                        CrossFadeOut(fade_duration),
                    ]
                )
            except (ImportError, AttributeError):
                # moviepy 버전에 따라 다름 — 페이드 없이 진행
                pass

        overlays.append(sub_clip)

    if not overlays:
        print("[SUBTITLE] No valid timings, copying video as-is")
        video.close()
        import shutil

        shutil.copy(video_path, output_path)
        return output_path

    final = CompositeVideoClip([video] + overlays)
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        audio=True,
        logger=None,
    )

    # 리소스 해제
    final.close()
    video.close()
    for o in overlays:
        o.close()
    cache.clear()

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"[SUBTITLE] Done: {output_path} ({size_mb:.1f}MB)")
    return output_path


# ============================================================
# 유틸: TTS 기반 자막 타이밍 계산
# ============================================================
def calculate_phrase_timings(
    phrases_per_cut: list,
    tts_duration: float,
    tts_delay: float = 0.3,
    pause_between_cuts: float = 0.4,
) -> list:
    """TTS 전체 길이 기반으로 프레이즈별 타이밍을 비례 배분한다.

    Args:
        phrases_per_cut: [["프레이즈1", "프레이즈2"], ["프레이즈3", ...], ...]
            컷별 프레이즈 리스트
        tts_duration: TTS 오디오 전체 길이 (초)
        tts_delay: TTS 시작 딜레이 (초, 기본 0.3)
        pause_between_cuts: 컷 사이 무음 구간 (초, 기본 0.4)

    Returns:
        [(start, end, text), ...] 형태의 타이밍 리스트
    """
    all_phrases = []
    cut_char_counts = []
    for cut_phrases in phrases_per_cut:
        cut_chars = sum(len(p) for p in cut_phrases)
        cut_char_counts.append(cut_chars)
        all_phrases.extend(cut_phrases)

    total_chars = sum(cut_char_counts)
    if total_chars == 0:
        return []

    n_gaps = len(phrases_per_cut) - 1
    total_pause = pause_between_cuts * n_gaps
    speech_time = tts_duration - total_pause

    timings = []
    t = tts_delay

    for cut_idx, cut_phrases in enumerate(phrases_per_cut):
        cut_chars = cut_char_counts[cut_idx]
        cut_duration = speech_time * (cut_chars / total_chars)

        phrase_chars = [len(p) for p in cut_phrases]
        pc_total = sum(phrase_chars)

        for phrase, pc in zip(cut_phrases, phrase_chars):
            phrase_dur = cut_duration * (pc / pc_total) if pc_total > 0 else 0.5
            timings.append((t, t + phrase_dur, phrase))
            t += phrase_dur

        if cut_idx < n_gaps:
            t += pause_between_cuts

    return timings


# ============================================================
# 유틸: WAV 파일 길이 확인
# ============================================================
def get_audio_duration(audio_path: str) -> float:
    """오디오 파일의 길이(초)를 반환한다.

    WAV 파일은 wave 모듈, 그 외는 ffprobe를 사용한다.
    """
    path = Path(audio_path)

    if path.suffix.lower() == ".wav":
        import wave

        with wave.open(str(path), "rb") as wf:
            return wf.getnframes() / wf.getframerate()

    # ffprobe fallback
    import subprocess
    import json

    try:
        import imageio_ffmpeg

        ffprobe_exe = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent / "ffprobe")
    except ImportError:
        ffprobe_exe = "ffprobe"

    cmd = [
        ffprobe_exe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        info = json.loads(result.stdout)
        dur = info.get("format", {}).get("duration")
        if dur:
            return float(dur)

    return 0.0
