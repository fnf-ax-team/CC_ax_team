"""
뷰티 영상 릴스 파이프라인

시나리오 → 스타트프레임 이미지(Gemini) → 영상(KlingAI I2V, 무음)
→ 연결(moviepy) → TTS(ElevenLabs) → BGM(Suno) → 싱크자막(video_subtitle)

모든 단계에서 병렬 처리를 사용한다.
Phase 4~6은 최종 연결 영상에 순차 적용된다.
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.config import OUTPUT_BASE_DIR
from .config import (
    VideoGenerationConfig,
    get_video_cost,
    VIDEO_COST_TABLE,
    TTS_COST_PER_200_CHARS,
    BGM_COST_PER_SONG,
)
from .subtitle_style import build_subtitle_prompt
from .generator import generate_image_to_video
from .client import KlingAIClient
from .presets import (
    BEAUTY_CAMERA_MOVES,
    BEAUTY_AUDIO_PROMPTS,
    BEAUTY_CUT_TYPES,
    BEAUTY_NEGATIVE_PROMPT,
)


# 기본 비디오 설정 (뷰티 릴스용)
DEFAULT_BEAUTY_VIDEO_CONFIG = VideoGenerationConfig(
    model_name="kling-v2-6",
    mode="pro",
    duration="5",
    aspect_ratio="9:16",
    cfg_scale=0.5,
)


async def generate_beauty_reels(
    scenario: Dict[str, Any],
    source_images: Optional[Dict[str, List[str]]] = None,
    output_dir: Optional[str] = None,
    video_config: Optional[VideoGenerationConfig] = None,
    concat: bool = True,
    # TTS 설정
    enable_tts: bool = True,
    tts_voice: str = "nicole",
    tts_speed_match: bool = True,
    # BGM 설정
    enable_bgm: bool = False,
    bgm_preset: Optional[str] = None,
    bgm_prompt: Optional[str] = None,
    bgm_vol: float = 0.15,
    # 자막 설정
    enable_subtitle: bool = True,
    subtitle_style: str = "reels",
    # Kling 키
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    뷰티 인플루언서 릴스 End-to-End 생성

    시나리오를 받아 스타트프레임 이미지 → 영상 → 오디오 → 연결
    → TTS 나레이션 → BGM → 싱크 자막까지 전 과정을 실행한다.

    Args:
        scenario: 시나리오 딕셔너리
            {
                "brand": "Banila Co",
                "product": "B. Highlighter",
                "description": "highlighter_reels",
                "narration": {                         # TTS 나레이션 (Phase 4)
                    "cut01_hook": "아침에 바른 이 광채...",
                    "cut02_middle": "프라이머 명가답게...",
                },
                "phrases": [                           # 싱크 자막 프레이즈 (Phase 6)
                    ["아침에 바른 이 광채,", "밤까지 가면", "믿으시겠어요?"],
                    ["프라이머 명가답게", "모공 부각 0."],
                ],
                "cuts": [
                    {
                        "id": "cut01_hook",
                        "name": "Hook",
                        "type": "hook",
                        "image_path": "path/to/img",
                        "motion_prompt": "...",
                        "audio": {"sfx": "...", "bgm": "..."}
                    },
                    ...
                ]
            }
        source_images: 소스 이미지 딕셔너리 (선택)
        output_dir: 출력 디렉토리 (없으면 자동 생성)
        video_config: 비디오 생성 설정 (없으면 기본값)
        concat: 최종 연결 여부
        enable_tts: TTS 나레이션 추가 (기본: True)
        tts_voice: TTS 보이스 프리셋 이름 (기본: "nicole")
        tts_speed_match: TTS 속도를 영상 길이에 맞춤 (기본: True)
        enable_bgm: Suno BGM 생성 및 오버레이 (기본: False — API 키 필요)
        bgm_preset: BGM 프리셋 이름 (beauty_lofi, beauty_upbeat 등)
        bgm_prompt: BGM 커스텀 프롬프트 (preset보다 우선)
        bgm_vol: BGM 볼륨 (0.0~1.0, 기본 0.15)
        enable_subtitle: 싱크 자막 오버레이 (기본: True)
        subtitle_style: 자막 스타일 ("reels" 또는 "broadcast")
        access_key: KlingAI Access Key
        secret_key: KlingAI Secret Key

    Returns:
        dict: {
            "cuts": list,           # 컷별 결과
            "final_path": str,      # 최종 릴스 경로 (자막+TTS+BGM 포함)
            "total_cost": int,      # 총 비용 (원)
            "output_dir": str,      # 출력 폴더 경로
            "summary_path": str,    # summary.json 경로
        }
    """
    config = video_config or DEFAULT_BEAUTY_VIDEO_CONFIG
    cuts = scenario.get("cuts", [])
    brand = scenario.get("brand", "Unknown")
    product = scenario.get("product", "")
    description = scenario.get("description", "beauty_reels")

    # 출력 폴더 생성
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(
            Path(OUTPUT_BASE_DIR) / "beauty_video" / f"{timestamp}_{description}"
        )
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    total_cuts = len(cuts)
    i2v_cost = get_video_cost(config.mode, config.duration)

    print("=" * 60)
    print(f"[Beauty Reels] {brand} - {product}")
    print("=" * 60)
    print(f"  Cuts: {total_cuts}")
    print(
        f"  Video: {config.model_name} / {config.mode} / {config.duration}s / {config.aspect_ratio}"
    )
    print(f"  Cost per cut: I2V={i2v_cost:,}won")
    print(f"  Total estimate: ~{i2v_cost * total_cuts:,}won")
    print("=" * 60)

    # ============================================================
    # Phase 1: 스타트프레임 이미지 자동 생성 (image_path 없는 컷만)
    # ============================================================
    cuts_need_image = [
        c for c in cuts if not c.get("image_path") or not Path(c["image_path"]).exists()
    ]

    if cuts_need_image and source_images:
        print(f"\n[Phase 1] Generating {len(cuts_need_image)} startframe images...")
        try:
            from .startframe import generate_startframes

            frame_paths = await generate_startframes(
                scenario=scenario,
                source_images=source_images,
                output_dir=str(out_path / "startframes"),
                aspect_ratio=config.aspect_ratio,
                resolution="2K",
            )

            # 생성된 이미지 경로를 컷에 자동 채우기
            for cut in cuts:
                if cut["id"] in frame_paths:
                    cut["image_path"] = frame_paths[cut["id"]]
                    print(f"  [Phase 1] {cut['id']}: image_path set")

        except Exception as e:
            print(f"  [FAIL] Phase 1 startframe generation: {e}")
    elif cuts_need_image and not source_images:
        print(
            f"\n[Phase 1] SKIP: {len(cuts_need_image)} cuts need images "
            f"but no source_images provided"
        )

    # ============================================================
    # Phase 1.5: 자막 프롬프트 합체 (subtitle 필드가 있는 컷만)
    # 이미지 생성 프롬프트(image_prompt)에 자막 스타일 가이드를 합체
    # Gemini가 이미지 생성 시 해당 스타일로 자막을 직접 렌더링
    # ============================================================
    subtitle_cuts = [c for c in cuts if c.get("subtitle")]
    if subtitle_cuts:
        print(
            f"\n[Phase 1.5] Merging subtitle style into {len(subtitle_cuts)} cut prompts..."
        )

        for cut in subtitle_cuts:
            sub_config = cut["subtitle"]
            style = sub_config.get("style", "broadcast")
            texts = sub_config.get("texts", {})
            position = sub_config.get("position", "bottom")

            try:
                subtitle_fragment = build_subtitle_prompt(style, texts, position)

                # image_prompt가 있으면 합체
                if cut.get("image_prompt"):
                    cut["image_prompt"] = (
                        f"{cut['image_prompt']}\n\n{subtitle_fragment}"
                    )
                    print(f"  [OK] {cut['id']}: {style} subtitle prompt merged")
                else:
                    # image_prompt 없이 subtitle만 있으면 별도 저장
                    cut["_subtitle_prompt"] = subtitle_fragment
                    print(f"  [OK] {cut['id']}: {style} subtitle prompt stored")
            except Exception as e:
                print(f"  [FAIL] {cut['id']}: subtitle prompt build failed ({e})")

    # ============================================================
    # Phase 2: I2V 영상 병렬 생성
    # (Phase 1 스타트프레임은 시나리오에 image_path로 제공된다고 가정)
    # ============================================================
    print(f"\n[Phase 2] Generating {total_cuts} videos (PARALLEL)...")

    async def generate_cut_video(cut: dict) -> dict:
        """단일 컷 I2V 생성"""
        cut_id = cut["id"]
        image_path = cut.get("image_path", "")

        if not image_path or not Path(image_path).exists():
            print(f"  [SKIP] {cut_id}: image not found ({image_path})")
            return {
                "cut_id": cut_id,
                "name": cut.get("name", cut_id),
                "success": False,
                "error": f"Image not found: {image_path}",
            }

        cut_output_dir = str(out_path / cut_id)

        try:
            result = await generate_image_to_video(
                image_path=image_path,
                prompt=cut.get("motion_prompt", ""),
                output_dir=cut_output_dir,
                description=cut_id,
                config=config,
                negative_prompt=BEAUTY_NEGATIVE_PROMPT,
                access_key=access_key,
                secret_key=secret_key,
            )
            print(f"  [OK] {cut_id}: {result['video_path']}")
            return {
                "cut_id": cut_id,
                "name": cut.get("name", cut_id),
                "success": True,
                "video_path": result["video_path"],
                "task_id": result["task_id"],
                "output_dir": cut_output_dir,
            }
        except Exception as e:
            print(f"  [FAIL] {cut_id}: {e}")
            return {
                "cut_id": cut_id,
                "name": cut.get("name", cut_id),
                "success": False,
                "error": str(e),
            }

    i2v_results = await asyncio.gather(*[generate_cut_video(cut) for cut in cuts])
    i2v_results = list(i2v_results)

    ok_i2v = [r for r in i2v_results if r.get("success")]
    print(f"\n  [I2V] {len(ok_i2v)}/{total_cuts} videos generated")

    # ============================================================
    # Phase 3: 최종 연결
    # ============================================================
    final_path = ""
    if concat and len(ok_i2v) >= 2:
        print(f"\n[Phase 3] Concatenating {len(ok_i2v)} clips...")
        try:
            from moviepy import VideoFileClip, concatenate_videoclips

            clip_paths = []
            for r in sorted(ok_i2v, key=lambda x: x["cut_id"]):
                video_path = r.get("video_path", "")
                if video_path and Path(video_path).exists():
                    clip_paths.append(video_path)

            if len(clip_paths) >= 2:
                clips = [VideoFileClip(p) for p in clip_paths]
                final = concatenate_videoclips(clips, method="compose")
                final_path = str(out_path / "final_reels.mp4")
                final.write_videofile(
                    final_path, codec="libx264", audio_codec="aac", audio=True
                )
                total_duration = final.duration
                final.close()
                for c in clips:
                    c.close()
                print(f"  [OK] Final reels: {final_path} ({total_duration:.1f}s)")
            else:
                print("  [SKIP] Not enough clips to concatenate")
        except Exception as e:
            print(f"  [FAIL] Concatenation: {e}")

    # ============================================================
    # Phase 4: TTS 나레이션 (ElevenLabs)
    # ============================================================
    tts_cost = 0
    tts_path = ""
    current_video = final_path  # Phase 3의 결과물부터 시작

    narration = scenario.get("narration", {})
    cut_ids = [c["id"] for c in cuts]

    if enable_tts and current_video and narration:
        print(f"\n[Phase 4] ElevenLabs TTS (voice: {tts_voice})...")
        try:
            from .tts import (
                generate_tts_for_voice_preset,
                speed_adjust_tts,
                overlay_tts_on_video,
                VOICE_PRESETS,
            )

            # 전체 나레이션 텍스트 합성
            combined_text = " ... ".join(
                narration[cid] for cid in cut_ids if cid in narration
            )

            tts_dir = out_path / "tts"
            tts_dir.mkdir(parents=True, exist_ok=True)

            # TTS 생성 (mp3 -> wav 자동 변환, mp3 삭제됨)
            raw_tts_path = str(tts_dir / f"{tts_voice}_raw.wav")
            raw_tts = generate_tts_for_voice_preset(
                preset_name=tts_voice,
                text=combined_text,
                output_path=raw_tts_path,
            )
            print(f"  TTS generated: {raw_tts}")

            # 속도 조정 (영상 길이에 맞춤)
            if tts_speed_match:
                from moviepy import VideoFileClip as VFC

                v = VFC(current_video)
                video_dur = v.duration
                v.close()

                adj_tts = str(tts_dir / f"{tts_voice}_adj.wav")
                tts_path = speed_adjust_tts(
                    input_path=raw_tts,
                    target_duration=video_dur,
                    output_path=adj_tts,
                )
            else:
                tts_path = raw_tts

            # TTS 오버레이
            tts_video = str(out_path / "with_tts.mp4")
            overlay_tts_on_video(
                video_path=current_video,
                tts_path=tts_path,
                output_path=tts_video,
                bgm_vol=0.3,  # 기존 오디오 볼륨 낮추기
                tts_delay_ms=300,
            )
            current_video = tts_video
            tts_cost = TTS_COST_PER_200_CHARS  # ElevenLabs Pro plan 기준
            print(f"  [OK] TTS overlay: {current_video}")

        except Exception as e:
            print(f"  [FAIL] TTS: {e}")

    # ============================================================
    # Phase 5: BGM (Suno API)
    # ============================================================
    bgm_cost = 0
    if enable_bgm and current_video:
        print(f"\n[Phase 5] Suno BGM (preset: {bgm_preset or 'custom'})...")
        try:
            from .bgm import (
                generate_bgm,
                generate_bgm_for_preset,
                overlay_bgm_on_video,
            )

            bgm_dir = out_path / "bgm"
            bgm_dir.mkdir(parents=True, exist_ok=True)
            bgm_audio = str(bgm_dir / "bgm.mp3")

            if bgm_prompt:
                generate_bgm(
                    prompt=bgm_prompt,
                    output_path=bgm_audio,
                )
            elif bgm_preset:
                generate_bgm_for_preset(
                    preset_name=bgm_preset,
                    output_path=bgm_audio,
                )
            else:
                # 기본: beauty_lofi
                generate_bgm_for_preset(
                    preset_name="beauty_lofi",
                    output_path=bgm_audio,
                )

            # BGM 오버레이
            bgm_video = str(out_path / "with_bgm.mp4")
            overlay_bgm_on_video(
                video_path=current_video,
                bgm_path=bgm_audio,
                output_path=bgm_video,
                bgm_vol=bgm_vol,
            )
            current_video = bgm_video
            bgm_cost = BGM_COST_PER_SONG  # Suno API 기준
            print(f"  [OK] BGM overlay: {current_video}")

        except Exception as e:
            print(f"  [FAIL] BGM: {e}")

    # ============================================================
    # Phase 6: 싱크 자막 (기본 ON)
    # ============================================================
    phrases = scenario.get("phrases", [])
    if enable_subtitle and current_video and phrases and tts_path:
        print(f"\n[Phase 6] Synced subtitles (style: {subtitle_style})...")
        try:
            from .video_subtitle import (
                add_synced_subtitles,
                calculate_phrase_timings,
                get_audio_duration,
            )

            # 이미지 구운 자막이 있는 컷의 phrases 스킵
            # (subtitle 필드가 있는 컷 = 이미지에 이미 자막이 포함됨)
            subtitle_cut_indices = set()
            for i, cut in enumerate(cuts):
                if cut.get("subtitle"):
                    subtitle_cut_indices.add(i)

            if subtitle_cut_indices:
                filtered_phrases = [
                    p for i, p in enumerate(phrases) if i not in subtitle_cut_indices
                ]
                skipped = len(phrases) - len(filtered_phrases)
                print(
                    f"  Skipping {skipped} cut(s) with image-baked subtitles: "
                    f"{sorted(subtitle_cut_indices)}"
                )
            else:
                filtered_phrases = phrases

            # TTS 길이 기반 타이밍 계산
            tts_dur = get_audio_duration(tts_path)
            timings = calculate_phrase_timings(
                phrases_per_cut=filtered_phrases,
                tts_duration=tts_dur,
                tts_delay=0.3,
                pause_between_cuts=0.4,
            )

            # 자막 오버레이
            subtitle_video = str(out_path / "final_with_subtitle.mp4")
            add_synced_subtitles(
                video_path=current_video,
                timings=timings,
                output_path=subtitle_video,
                style=subtitle_style,
            )
            current_video = subtitle_video
            print(f"  [OK] Subtitles: {current_video}")

        except Exception as e:
            print(f"  [FAIL] Subtitles: {e}")

    # 자막 없이 TTS만 있는 경우 (phrases 미제공)
    elif enable_subtitle and current_video and narration and tts_path and not phrases:
        print("\n[Phase 6] SKIP: 'phrases' not in scenario (자막 타이밍 데이터 필요)")

    # ============================================================
    # 최종 경로 갱신
    # ============================================================
    final_path = current_video or final_path

    # ============================================================
    # Summary 저장
    # ============================================================
    success_count = len(ok_i2v)
    total_i2v_cost = i2v_cost * success_count
    total_cost = total_i2v_cost + tts_cost + bgm_cost

    summary = {
        "workflow": "beauty_video",
        "brand": brand,
        "product": product,
        "description": description,
        "timestamp": datetime.now().isoformat(),
        "video_config": {
            "model": config.model_name,
            "mode": config.mode,
            "duration": config.duration,
            "aspect_ratio": config.aspect_ratio,
            "cfg_scale": config.cfg_scale,
        },
        "tts_enabled": enable_tts,
        "tts_voice": tts_voice if enable_tts else None,
        "bgm_enabled": enable_bgm,
        "bgm_preset": bgm_preset if enable_bgm else None,
        "subtitle_enabled": enable_subtitle,
        "subtitle_style": subtitle_style if enable_subtitle else None,
        "total_cuts": total_cuts,
        "total_success": success_count,
        "total_cost": total_cost,
        "cost_breakdown": {
            "i2v": total_i2v_cost,
            "tts": tts_cost,
            "bgm": bgm_cost,
        },
        "results": i2v_results,
    }
    if final_path:
        summary["final_reels"] = final_path

    summary_path = str(out_path / "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("[SUMMARY]")
    print(f"  Videos: {success_count}/{total_cuts}")
    print(f"  TTS: {'ON (' + tts_voice + ')' if enable_tts and narration else 'OFF'}")
    print(f"  BGM: {'ON' if enable_bgm else 'OFF'}")
    print(f"  Subtitle: {'ON (' + subtitle_style + ')' if enable_subtitle else 'OFF'}")
    print(
        f"  Cost: ~{total_cost:,}won "
        f"(I2V={total_i2v_cost:,} + TTS={tts_cost:,} + BGM={bgm_cost:,})"
    )
    print(f"  Output: {out_path}")
    if final_path:
        print(f"  Final: {final_path}")
    for r in i2v_results:
        status = "[OK]" if r.get("success") else "[FAIL]"
        print(f"  {status} {r.get('name', r['cut_id'])}")
    print("=" * 60)

    return {
        "cuts": i2v_results,
        "final_path": final_path,
        "total_cost": total_cost,
        "output_dir": str(out_path),
        "summary_path": summary_path,
    }
