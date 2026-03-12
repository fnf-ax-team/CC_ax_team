"""
비디오 생성 모듈

KlingAI API를 사용한 텍스트-투-비디오(T2V), 이미지-투-비디오(I2V) 생성.
표준 출력 폴더 구조(prompt.json, prompt.txt, config.json)를 따른다.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.config import OUTPUT_BASE_DIR  # OUTPUT_BASE_DIR만 core.config에서
from .config import (
    KLING_DEFAULT_MODEL,
    VideoGenerationConfig,
    validate_video_aspect_ratio,
    get_video_cost,
)
from .client import KlingAIClient, KlingAPIError


async def generate_text_to_video(
    prompt: str,
    output_dir: Optional[str] = None,
    description: str = "t2v",
    config: Optional[VideoGenerationConfig] = None,
    negative_prompt: str = "",
    camera_control: Optional[Dict] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    텍스트-투-비디오(T2V) 생성

    프롬프트로 비디오를 생성하고 표준 폴더 구조로 저장한다.

    Args:
        prompt: 비디오 프롬프트
        output_dir: 저장 디렉토리 (없으면 자동 생성)
        description: 설명 (폴더명에 포함, 영어_언더스코어)
        config: 비디오 생성 설정 (없으면 기본값)
        negative_prompt: 네거티브 프롬프트
        camera_control: 카메라 컨트롤 (V1.x 모델만)
        access_key: KlingAI Access Key (없으면 .env에서)
        secret_key: KlingAI Secret Key (없으면 .env에서)

    Returns:
        dict: {
            "video_path": str,     # 저장된 비디오 경로
            "task_id": str,        # KlingAI 태스크 ID
            "prompt": str,         # 사용된 프롬프트
            "config": dict,        # 생성 설정
            "output_dir": str,     # 출력 폴더 경로
            "duration": str,       # 비디오 길이
        }
    """
    config = config or VideoGenerationConfig()

    if not validate_video_aspect_ratio(config.aspect_ratio):
        raise ValueError(
            f"Invalid video aspect_ratio: {config.aspect_ratio}. "
            f"Allowed: 16:9, 9:16, 1:1"
        )

    # 출력 폴더 생성
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(
            Path(OUTPUT_BASE_DIR) / "video_generation" / f"{timestamp}_{description}"
        )

    out_path = Path(output_dir)
    videos_dir = out_path / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # API 클라이언트 생성
    client = KlingAIClient(access_key=access_key, secret_key=secret_key)

    # 태스크 제출
    print(
        f"[VIDEO] Submitting T2V task (model={config.model_name}, "
        f"mode={config.mode}, duration={config.duration}s)..."
    )
    task_id = await client.text_to_video(
        prompt=prompt,
        model_name=config.model_name,
        mode=config.mode,
        aspect_ratio=config.aspect_ratio,
        duration=config.duration,
        cfg_scale=config.cfg_scale,
        negative_prompt=negative_prompt,
        camera_control=camera_control,
    )
    print(f"[VIDEO] Task submitted: {task_id}")

    # 폴링 (비디오 생성 대기)
    print(f"[VIDEO] Waiting for video generation (max {config.poll_timeout}s)...")
    result = await client.poll_task(
        task_id=task_id,
        task_type="text2video",
        max_wait=config.poll_timeout,
        poll_interval=config.poll_interval,
    )

    # 비디오 다운로드
    videos = result["task_result"]["videos"]
    video_paths = []
    for i, video in enumerate(videos):
        video_path = str(videos_dir / f"output_{i + 1:03d}.mp4")
        await client.download_video(video["url"], video_path)
        video_paths.append(video_path)
        print(f"[VIDEO] Downloaded: {video_path}")

    # 메타데이터 저장
    _save_metadata(
        output_dir=str(out_path),
        prompt=prompt,
        negative_prompt=negative_prompt,
        config=config,
        task_id=task_id,
        mode="text2video",
    )

    print(f"[VIDEO] Complete! Output: {out_path}")
    return {
        "video_path": video_paths[0] if video_paths else "",
        "video_paths": video_paths,
        "task_id": task_id,
        "prompt": prompt,
        "config": {
            "model_name": config.model_name,
            "mode": config.mode,
            "duration": config.duration,
            "aspect_ratio": config.aspect_ratio,
            "cfg_scale": config.cfg_scale,
        },
        "output_dir": str(out_path),
        "duration": config.duration,
    }


async def generate_image_to_video(
    image_path: str,
    prompt: str = "",
    output_dir: Optional[str] = None,
    description: str = "i2v",
    config: Optional[VideoGenerationConfig] = None,
    negative_prompt: str = "",
    image_tail_path: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    이미지-투-비디오(I2V) 생성

    소스 이미지로 비디오를 생성하고 표준 폴더 구조로 저장한다.

    Args:
        image_path: 소스 이미지 경로 (로컬 파일 또는 URL)
        prompt: 모션 프롬프트 (선택)
        output_dir: 저장 디렉토리 (없으면 자동 생성)
        description: 설명 (폴더명에 포함)
        config: 비디오 생성 설정
        negative_prompt: 네거티브 프롬프트
        image_tail_path: 끝 프레임 이미지 경로 (선택)
        access_key: KlingAI Access Key
        secret_key: KlingAI Secret Key

    Returns:
        dict: generate_text_to_video()와 동일한 구조
    """
    config = config or VideoGenerationConfig()

    # 출력 폴더 생성
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(
            Path(OUTPUT_BASE_DIR) / "video_generation" / f"{timestamp}_{description}"
        )

    out_path = Path(output_dir)
    videos_dir = out_path / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # 인풋 이미지 복사 (표준 출력 구조)
    input_images = {}
    src_path = Path(image_path)
    if src_path.exists():
        dest = videos_dir / f"input_source_01{src_path.suffix}"
        shutil.copy(str(src_path), str(dest))
        input_images["source"] = [str(dest)]

    if image_tail_path:
        tail_path = Path(image_tail_path)
        if tail_path.exists():
            dest = videos_dir / f"input_tail_01{tail_path.suffix}"
            shutil.copy(str(tail_path), str(dest))
            input_images["tail"] = [str(dest)]

    # 이미지를 API용으로 변환 (로컬 → base64, URL → 그대로)
    if src_path.exists():
        image_data = KlingAIClient.image_to_base64(image_path)
    else:
        # URL로 간주
        image_data = image_path

    image_tail_data = None
    if image_tail_path:
        if Path(image_tail_path).exists():
            image_tail_data = KlingAIClient.image_to_base64(image_tail_path)
        else:
            image_tail_data = image_tail_path

    # API 클라이언트 생성
    client = KlingAIClient(access_key=access_key, secret_key=secret_key)

    # 태스크 제출
    print(
        f"[VIDEO] Submitting I2V task (model={config.model_name}, "
        f"mode={config.mode}, duration={config.duration}s)..."
    )
    task_id = await client.image_to_video(
        image=image_data,
        prompt=prompt,
        model_name=config.model_name,
        mode=config.mode,
        duration=config.duration,
        cfg_scale=config.cfg_scale,
        negative_prompt=negative_prompt,
        image_tail=image_tail_data,
        enable_audio=config.enable_audio,
    )
    print(f"[VIDEO] Task submitted: {task_id}")

    # 폴링
    print(f"[VIDEO] Waiting for video generation (max {config.poll_timeout}s)...")
    result = await client.poll_task(
        task_id=task_id,
        task_type="image2video",
        max_wait=config.poll_timeout,
        poll_interval=config.poll_interval,
    )

    # 비디오 다운로드
    videos = result["task_result"]["videos"]
    video_paths = []
    video_id = ""
    for i, video in enumerate(videos):
        video_path = str(videos_dir / f"output_{i + 1:03d}.mp4")
        await client.download_video(video["url"], video_path)
        video_paths.append(video_path)
        if i == 0:
            video_id = video.get("id", task_id)
        print(f"[VIDEO] Downloaded: {video_path}")

    # 메타데이터 저장
    _save_metadata(
        output_dir=str(out_path),
        prompt=prompt,
        negative_prompt=negative_prompt,
        config=config,
        task_id=task_id,
        mode="image2video",
        input_images=input_images,
    )

    print(f"[VIDEO] Complete! Output: {out_path}")
    return {
        "video_path": video_paths[0] if video_paths else "",
        "video_paths": video_paths,
        "task_id": task_id,
        "video_id": video_id,  # V2A에 필요한 비디오 리소스 ID
        "prompt": prompt,
        "config": {
            "model_name": config.model_name,
            "mode": config.mode,
            "duration": config.duration,
            "aspect_ratio": config.aspect_ratio,
            "cfg_scale": config.cfg_scale,
        },
        "output_dir": str(out_path),
        "duration": config.duration,
        "input_images": input_images,
    }


async def generate_video_to_audio(
    video_id: str,
    output_dir: str,
    sound_effect_prompt: str = "",
    background_music_prompt: str = "",
    asmr_mode: bool = False,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    비디오-투-오디오(V2A) - 기존 비디오에 AI 오디오 추가

    KlingAI V2A API로 효과음 + BGM을 생성하여 비디오에 합성한다.

    Args:
        video_id: I2V/T2V 생성 결과의 task_id
        output_dir: 저장 디렉토리
        sound_effect_prompt: 효과음 프롬프트 (영어)
        background_music_prompt: 배경음악 프롬프트 (영어)
        asmr_mode: ASMR 모드
        access_key: KlingAI Access Key
        secret_key: KlingAI Secret Key

    Returns:
        dict: {
            "video_path": str,     # 오디오가 합성된 비디오 경로
            "audio_path": str,     # 별도 오디오 파일 경로 (있으면)
            "task_id": str,        # V2A 태스크 ID
            "output_dir": str,     # 출력 폴더 경로
        }
    """
    out_path = Path(output_dir)
    videos_dir = out_path / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # API 클라이언트 생성
    client = KlingAIClient(access_key=access_key, secret_key=secret_key)

    # V2A 태스크 제출
    print(f"[V2A] Submitting V2A task for video {video_id[:8]}...")
    task_id = await client.video_to_audio(
        video_id=video_id,
        sound_effect_prompt=sound_effect_prompt,
        background_music_prompt=background_music_prompt,
        asmr_mode=asmr_mode,
    )
    print(f"[V2A] Task submitted: {task_id}")

    # 폴링 (V2A는 ~30초 소요)
    print("[V2A] Waiting for audio generation...")
    result = await client.poll_v2a_task(task_id=task_id)

    # 오디오 합성 비디오 다운로드
    videos = result.get("task_result", {}).get("videos", [])
    video_path = ""
    if videos:
        video_path = str(videos_dir / "output_with_audio.mp4")
        await client.download_video(videos[0]["url"], video_path)
        print(f"[V2A] Downloaded video+audio: {video_path}")

    # 별도 오디오 파일 다운로드 (있으면)
    audio_path = ""
    works = result.get("task_result", {}).get("works", [])
    if works:
        resource = works[0].get("resource", {}).get("resource", "")
        if resource:
            audio_ext = ".mp3"
            audio_path = str(videos_dir / f"audio{audio_ext}")
            await client.download_video(resource, audio_path)
            print(f"[V2A] Downloaded audio: {audio_path}")

    # V2A 메타데이터 저장
    v2a_meta = {
        "mode": "video_to_audio",
        "video_id": video_id,
        "v2a_task_id": task_id,
        "sound_effect_prompt": sound_effect_prompt,
        "background_music_prompt": background_music_prompt,
        "asmr_mode": asmr_mode,
    }
    with open(out_path / "v2a_config.json", "w", encoding="utf-8") as f:
        json.dump(v2a_meta, f, ensure_ascii=False, indent=2)

    print(f"[V2A] Complete! Output: {out_path}")
    return {
        "video_path": video_path,
        "audio_path": audio_path,
        "task_id": task_id,
        "output_dir": str(out_path),
    }


def _save_metadata(
    output_dir: str,
    prompt: str,
    negative_prompt: str,
    config: VideoGenerationConfig,
    task_id: str,
    mode: str,
    input_images: Optional[Dict[str, List[str]]] = None,
):
    """
    표준 출력 폴더 구조로 메타데이터 저장

    Args:
        output_dir: 출력 폴더 경로
        prompt: 프롬프트
        negative_prompt: 네거티브 프롬프트
        config: 비디오 생성 설정
        task_id: KlingAI 태스크 ID
        mode: "text2video" 또는 "image2video"
        input_images: 인풋 이미지 딕셔너리 (선택)
    """
    out = Path(output_dir)

    # prompt.json
    prompt_data = {
        "mode": mode,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
    }
    with open(out / "prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2)

    # prompt.txt (가독용)
    input_section = ""
    if input_images:
        input_lines = []
        for category, paths in input_images.items():
            for p in paths:
                input_lines.append(f"  {category}: {Path(p).name}")
        input_section = f"\n=== INPUTS ===\n" + "\n".join(input_lines) + "\n"

    prompt_txt = f"""=== VIDEO GENERATION INFO ===
Mode: {mode}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Task ID: {task_id}
{input_section}
=== PROMPT ===
{prompt}

=== NEGATIVE PROMPT ===
{negative_prompt or "(none)"}

=== CONFIG ===
Model: {config.model_name}
Quality Mode: {config.mode}
Duration: {config.duration}s
Aspect Ratio: {config.aspect_ratio}
CFG Scale: {config.cfg_scale}
Cost: ~{get_video_cost(config.mode, config.duration):,}원
"""
    with open(out / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    # config.json
    config_data = {
        "workflow": "video_generation",
        "timestamp": datetime.now().isoformat(),
        "api": "klingai",
        "model": config.model_name,
        "mode": config.mode,
        "duration": config.duration,
        "aspect_ratio": config.aspect_ratio,
        "cfg_scale": config.cfg_scale,
        "task_id": task_id,
        "generation_mode": mode,
        "cost": get_video_cost(config.mode, config.duration),
    }
    if input_images:
        config_data["input_images"] = {
            k: [Path(p).name for p in v] for k, v in input_images.items()
        }
    with open(out / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
